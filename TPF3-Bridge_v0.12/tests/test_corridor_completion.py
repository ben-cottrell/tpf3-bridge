"""Named-road completion under fake adapters; no native/game acceptance."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_corridor as corridor
import bridge_live as live
import bridge_signal_benchmark as benchmark
from bridge_operator import Operator
from test_signal_benchmark import World, config


class CompletionTests(unittest.TestCase):
    def built(self,td,authored=False):
        native=World(td);op=Operator(runs=td,client=native);brief=benchmark.fixtures(config())[1][1]
        roads=benchmark.completion_roads(brief,99)
        if authored:brief['roads']=roads
        run=op.plan_corridor(brief)['run']
        with patch('bridge_operator.live._select_throat_port',side_effect=native.select):result=op.build_corridor(run)
        self.assertEqual(result['status'],'built',result)
        return native,op,run,roads

    def test_whole_roads20signals4batches8outcomes_no_duplicate_refresh(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads);before=len(native.calls)
            result=op.complete_corridor(run)
            self.assertEqual(result['completion']['status'],'completed',result)
            self.assertEqual((result['completion']['signals'],result['completion']['checks']),(20,8))
            calls=native.calls[before:]
            self.assertEqual(len(calls),24)
            self.assertEqual(sum(o=='inspect' for o,p in calls),4)
            self.assertEqual(sum('signal_chain_check' in p for o,p in calls),4)
            self.assertEqual(sum('signal_batch' in p for o,p in calls),4)
            self.assertEqual(sum(o=='operating_control' for o,p in calls),4)
            self.assertEqual(sum(o=='route' for o,p in calls),8)
            before=len(native.calls);op.complete_corridor(run,continuing=True);self.assertEqual(len(native.calls),before)
            self.assertLess(len(json.dumps(result).encode()),4096)

    def test_optional_authored_completion_and_explicit_single_road_checks(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,_=self.built(td,True)
            self.assertEqual(op.corridor_status(run)['completion']['status'],'completed')
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            self.assertEqual(op.complete_corridor(run,phase='signal')['completion']['signals'],20)
            before=len(native.calls);result=op.complete_corridor(run,phase='qualify',road='fast_down')
            self.assertEqual(len(native.calls)-before,2);self.assertEqual(result['completion']['checks'],2)
            self.assertEqual(result['completion']['status'],'ready')

    def test_unknown_chunk_stops_dependent_checks_without_replay(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads);native.unknown=True
            result=op.complete_corridor(run);self.assertEqual(result['completion']['status'],'needs_attention')
            self.assertEqual(native.route_count,0);before=len(native.calls)
            with self.assertRaisesRegex(ValueError,'already attempted'):op.complete_corridor(run)
            result=op.complete_corridor(run,continuing=True)
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(len(native.calls),before)
            result=op.complete_corridor(run,continuing=True,phase='qualify',road='fast_down')
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(len(native.calls),before)

    def test_completed_child_continuation_consumes_receipt_without_replay(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            original=live.atomic_json;interrupted=False
            def write(path,value):
                nonlocal interrupted
                original(path,value)
                if value.get('kind')=='corridor_signal_chunk' and value.get('status')=='built' and not interrupted:
                    interrupted=True;raise OSError('interruption after durable child receipt')
            with patch('bridge_corridor.live.atomic_json',side_effect=write):result=op.complete_corridor(run,phase='signal')
            self.assertEqual(result['completion']['status'],'needs_attention')
            result=op.complete_corridor(run,continuing=True)
            self.assertEqual(result['completion']['status'],'completed',result)
            self.assertEqual(sum(o=='operating_control' for o,p in native.calls),4)
            self.assertEqual(result['completion']['signals'],20)

    def test_native_bound_chunk_failure_keeps_first_receipt_and_blocks_checks(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);roads=roads[:1];roads[0].update(spacing=50,start_offset=25.5)
            op.attach_corridor_completion(run,roads)
            rows=[native.make_edge([45*i,0,3],[45*(i+1),0,3],[45,0,0],[45,0,0],1000000+i,1000001+i) for i in range(33)]
            original=native.request;mutations=0
            def request(operation,params,**kwargs):
                nonlocal mutations
                if operation=='operating_control':
                    mutations+=1
                    if mutations==2:native.unknown=True
                return original(operation,params,**kwargs)
            envelope={'min':[-30,-30,0],'max':[1800,30,10]}
            with patch('bridge_corridor.recover_road',return_value=(rows,[envelope])),patch.object(native,'request',side_effect=request):result=op.complete_corridor(run)
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(native.route_count,0)
            state=json.loads((op.path(run)/'state.json').read_text())['completion']['roads']['up']
            self.assertEqual(state['chunk_index'],1,result);self.assertGreater(len(state['placements']),0)
            self.assertTrue(any(a['id']!=b['id'] for a,b in zip(rows,state['edges'])))
            before=len(native.calls);op.continue_corridor(run);self.assertEqual(len(native.calls),before)

    def test_pending_journal_blocks_qualification_even_through_benchmark_wrapper(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads);op.complete_corridor(run,phase='signal')
            native.journal=Path(td)/'client_state.json';native.journal.write_text(json.dumps({'pending':{'request_id':'unresolved'}}))
            wrapped=Operator(runs=td,client=benchmark.Counted(native));before=len(native.calls)
            result=wrapped.complete_corridor(run,phase='qualify')
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertIn('requires reconciliation',result['completion']['error'])
            self.assertEqual(result['completion']['checks'],0);self.assertEqual(len(native.calls),before)
            self.assertTrue(json.loads(native.journal.read_text())['pending'])

    def test_selected_later_road_interruption_default_continuation_consumes_owner_first(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            original=live.atomic_json;interrupted=False
            def write(path,value):
                nonlocal interrupted
                original(path,value)
                if value.get('kind')=='corridor_signal_chunk' and value.get('status')=='built' and not interrupted:
                    interrupted=True;raise OSError('interrupted later road after durable receipt')
            with patch('bridge_corridor.live.atomic_json',side_effect=write):result=op.complete_corridor(run,phase='signal',road='fast_down')
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(sum(o=='operating_control' for o,p in native.calls),1)
            # Mutable UI/current-road context is not authoritative child ownership.
            path=op.path(run)/'state.json';state=json.loads(path.read_text());state['completion']['road']='up';original(path,state)
            result=op.continue_corridor(run)
            self.assertEqual(result['completion']['status'],'completed',result)
            self.assertEqual(result['completion']['signals'],20);self.assertEqual(result['completion']['checks'],8)
            self.assertEqual(sum(o=='operating_control' for o,p in native.calls),4)
            batch_seeds=[p for o,p in native.calls if o=='operating_inspect' and 'signal_batch' in p];self.assertEqual(len(batch_seeds),4)

    def test_pending_after_receipt_blocks_advance_until_existing_reconciliation(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            native.journal=Path(td)/'client_state.json';native.journal.write_text('{}');original=native.request
            def request(operation,params,**kwargs):
                result=original(operation,params,**kwargs)
                if operation=='operating_control':native.journal.write_text(json.dumps({'pending':{'request_id':result['request_id']}}))
                return result
            with patch.object(native,'request',side_effect=request):result=op.complete_corridor(run)
            self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(native.route_count,0)
            state=json.loads((op.path(run)/'state.json').read_text())['completion']
            self.assertEqual(state['roads']['up']['chunk_index'],0)
            self.assertEqual(json.loads((op.path(state['current_child'])/'state.json').read_text())['status'],'built')
            native.journal.write_text('{}') # fake existing reconciliation; production never clears this
            result=op.continue_corridor(run)
            self.assertEqual(result['completion']['status'],'completed',result)
            self.assertEqual(sum(o=='operating_control' for o,p in native.calls),4)

    def test_attached_scope_is_immutable_and_stale_session_has_no_calls(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            altered=copy.deepcopy(roads);altered[0]['spacing']=200
            with self.assertRaisesRegex(ValueError,'scope changed'):op.attach_corridor_completion(run,altered)
            native.session='other';before=len(native.calls)
            result=op.complete_corridor(run);self.assertEqual(result['completion']['status'],'needs_attention');self.assertEqual(len(native.calls),before)

    def test_envelope_union_is_not_a_bounding_box_permission(self):
        with tempfile.TemporaryDirectory() as td:
            native,op,run,roads=self.built(td);op.attach_corridor_completion(run,roads)
            original=corridor.recover_road
            def narrowed(*args):
                rows,_=original(*args);return rows,[{'min':[-1,-1,0],'max':[1,1,4]}]
            with patch('bridge_corridor.recover_road',side_effect=narrowed):result=op.complete_corridor(run)
            self.assertIn('envelope union',result['completion']['error']);self.assertEqual(sum(o=='operating_control' for o,p in native.calls),0)

    def test_benchmark_opt_in_preserves_default_and_attaches_without_rebuilding(self):
        with tempfile.TemporaryDirectory() as td:
            native=World(td);op=Operator(runs=td,client=native);c=config();c['production_completion']=True
            run=benchmark.prepare(op,c)['run']
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select),patch('bridge_operator.live.place_signal',side_effect=lambda client,q,execute:client.request('operating_control',q|{'action':'single','execute':True})):
                self.assertEqual(benchmark.execute(op,run,'build')['status'],'ready');built_calls=sum(o=='structured_chain' for o,p in native.calls)
                self.assertEqual(benchmark.execute(op,run,'signal')['status'],'ready')
                result=benchmark.execute(op,run,'qualify')
            self.assertEqual(result['status'],'completed',result)
            self.assertEqual(result['counts']['batch_signals']['requests'],16)
            self.assertEqual(result['counts']['batch_signals']['mutations'],4)
            self.assertEqual(sum(o=='structured_chain' for o,p in native.calls),built_calls)

    def test_road_validation_rejects_implicit_direction_or_changed_pairing(self):
        brief=benchmark.fixtures(config())[1][1];roads=benchmark.completion_roads(brief,99)
        for change in (lambda r:r[0].pop('forward'),lambda r:r[0].update(sections=['CD','AB']),lambda r:r[0].update(track='missing'),lambda r:r[0].update(checks=['something']),lambda r:r[0].update(max_count=65)):
            value=copy.deepcopy(roads);change(value)
            with self.assertRaises(ValueError):corridor.validate_roads(brief,value)

    def test_existing_cli_exposes_completion_without_another_runner(self):
        import bridge_operator
        with patch('sys.argv',['bridge_operator.py','corridor-complete','--run','example']),patch.object(Operator,'complete_corridor',return_value={'status':'built'}) as method,patch('sys.stdout',new_callable=io.StringIO) as out:
            bridge_operator.main();method.assert_called_once_with('example');self.assertEqual(json.loads(out.getvalue()),{'status':'built'})


if __name__=='__main__':unittest.main()
