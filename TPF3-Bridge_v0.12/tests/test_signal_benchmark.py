"""Offline benchmark sequencing and exact receipt recovery, not native acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_signal_benchmark as benchmark
from bridge_operator import Operator
from test_corridor_operator import Native


def config():
    return {'version':1,'session':'test','origins':[[0,0,3],[0,300,3]],
            'track':{'template':'track','style':'style'},'track_distance':5,'seed_id':99}


class World(Native):
    def __init__(self,directory):
        super().__init__(directory);self.next_id=100000;self.prepared_signals={};self.route_count=0;self.unknown=False;self.reverse_has_path=False
    def request(self,operation,p,**kwargs):
        if operation not in ('operating_inspect','operating_control','route') and not p.get('resources'):
            return super().request(operation,p,**kwargs)
        self.counter+=1;rid=str(self.counter);self.calls.append((operation,copy.deepcopy(p)))
        if p.get('resources'):value={'edges':[{'id':90000,'template':'track','style':'style','resource':{'track_distance':5}}]}
        elif 'signal_seed' in p:value={'signal_seed':{'id':99,'edge':90000}}
        elif 'signal_chain_check' in p:value={'signal_chain_check':{'checked':True}}
        elif 'signal_batch' in p:
            q=p['signal_batch'];self.prepared_signals[rid]=q
            value={'signal_batch':{'accepted':True,'native_proposal_evaluated':True,'prepared_handle':rid,'input_hash':q['input_hash'],'seed':{'id':99}}}
        elif operation=='operating_control':
            if self.unknown:return {'status':'mutation_unverified','request_id':rid,'result':{'game_constructed':'unknown','retry':False}}
            if p.get('action')=='single':placements=[p];q=None
            else:q=self.prepared_signals[p['prepared_handle']];placements=q['placements']
            mapping=[];new={}
            for ident in dict.fromkeys(v['edge_id'] for v in placements):
                row=copy.deepcopy(self.edges.pop(ident));self.next_id+=1;row.update(id=self.next_id,revision=[1,2,3]);self.edges[row['id']]=row;new[ident]=row
                mapping.append({'replaced_edge':ident,'replacement_edge':row['id'],'snapshot':row})
            signals=[{'replaced_edge':v['edge_id'],'replacement_edge':new[v['edge_id']]['id'],'travel_forward':v['forward'],
                      'signal':{'id':self.next_id*100+i,'param':v['parameter']}} for i,v in enumerate(placements)]
            value={'game_constructed':True,'mapping':mapping,'placements':signals,'track_geometry_verified':True,
                   'existing_objects_retained':True,'functional_signals_verified':True}
            if q:value.update(input_hash=q['input_hash'],prepared_handle=p['prepared_handle'])
            else:value.update(signals[0])
        elif operation=='route':
            self.route_count+=1;forward=self.route_count%2==1
            value={'requested_route_verified':forward,'native_path_found':forward or self.reverse_has_path,'reason':'verified' if forward else 'no_native_path_returned'}
        else:raise AssertionError((operation,p))
        return {'status':'ok','request_id':rid,'result':value}


class BenchmarkTests(unittest.TestCase):
    def test_fixture_scope_and_local_equivalence(self):
        rows=benchmark.fixtures(config());self.assertEqual([m for m,b in rows],['individual','batch'])
        for mode,b in rows:
            self.assertEqual([len(s['members']) for s in b['sections']],[2,4,4])
            self.assertEqual(b['max_grade'],.025);self.assertEqual(b['stub_length'],10)
            self.assertTrue(all(p['grade']==0 for w in b['waypoints'].values() for p in w.values()))
            self.assertTrue(all(set(m)=={'track'} for s in b['sections'] for m in s['members']))
        a,b=rows[0][1],rows[1][1]
        for name in a['waypoints']:
            for road,p in a['waypoints'][name].items():
                self.assertAlmostEqual(b['waypoints'][name][road]['position'][1]-p['position'][1],300)
        c=config();c['rotation_degrees']=90;c['origins'][1]=[-300,0,3];benchmark.fixtures(c)
        c['origins'][1]=[0,0,3]
        with self.assertRaisesRegex(ValueError,'overlap'):benchmark.fixtures(c)

    def test_exact_path_recovery_ignores_coordinates_and_rejects_ambiguity(self):
        rows=[{'id':1,'node0':10,'node1':11,'p0':['irrelevant']},
              {'id':2,'node0':12,'node1':11,'p0':['same']},
              {'id':3,'node0':30,'node1':31,'p0':['same']}]
        self.assertEqual([r['id'] for r in benchmark.ordered_path(rows,10,12)],[1,2])
        with self.assertRaisesRegex(ValueError,'ambiguous'):benchmark.ordered_path(rows+[{'id':4,'node0':10,'node1':12}],10,12)

    def workflow(self,td,world=None):
        native=world or World(td);operator=Operator(runs=td,client=native);run=benchmark.prepare(operator,config())['run']
        return native,operator,run

    def test_phase_sequence_metrics_and_no_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            native,operator,run=self.workflow(td)
            self.assertEqual(native.calls,[])
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select),patch('bridge_operator.live.place_signal',
                       side_effect=lambda client,q,execute:client.request('operating_control',q|{'action':'single','execute':True})):
                result=benchmark.execute(operator,run,'build');self.assertEqual(result['status'],'ready',result)
                self.assertEqual(result['next_phase'],'signal')
                with self.assertRaisesRegex(ValueError,'out of order'):benchmark.execute(operator,run,'build')
                result=benchmark.execute(operator,run,'signal');self.assertEqual(result['status'],'ready',result)
                result=benchmark.execute(operator,run,'qualify');self.assertEqual(result['status'],'completed',result)
            self.assertEqual([r['route_checks'] for r in result['fixtures']],[8,8]);self.assertEqual(native.route_count,16)
            self.assertLess(result['counts']['batch_signals']['mutations'],result['counts']['individual_signals']['mutations'])
            self.assertLess(len(json.dumps(result).encode()),4096)
            with self.assertRaisesRegex(ValueError,'already attempted'):benchmark.execute(operator,run)

    def test_reverse_path_mismatch_is_not_proof_of_blocked_route(self):
        with tempfile.TemporaryDirectory() as td:
            native,operator,run=self.workflow(td);native.reverse_has_path=True
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select),patch('bridge_operator.live.place_signal',
                       side_effect=lambda client,q,execute:client.request('operating_control',q|{'action':'single','execute':True})):
                result=benchmark.execute(operator,run)
            self.assertEqual(result['status'],'needs_attention');self.assertIn('route acceptance',result['error'])
            self.assertEqual(native.route_count,2)

    def test_signal_windows_preserve_global_targets_under_existing_plan_bound(self):
        rows=[]
        for i in range(3):rows.append({'id':i+1,'node0':i+1,'node1':i+2,'p0':[600*i,0,3],'p1':[600*(i+1),0,3],'t0':[600,0,0],'t1':[600,0,0]})
        for forward in (True,False):
            windows=list(benchmark.signal_windows(rows,forward,[150,450,750,1050,1350,1650]))
            self.assertEqual(len(windows),3);self.assertEqual([w['start_distance'] for w in windows],[0,600,1200])
            self.assertEqual(sum(w['count'] for w in windows),6)
            self.assertTrue(all(w['start_offset']==150 and w['end_clearance']==150 for w in windows))
            self.assertTrue(all(w['region']['max'][0]-w['region']['min'][0]<=1000 for w in windows))

    def test_unknown_effect_stops_without_phase_replay(self):
        with tempfile.TemporaryDirectory() as td:
            native,operator,run=self.workflow(td)
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):
                self.assertEqual(benchmark.execute(operator,run,'build')['status'],'ready')
            native.unknown=True
            with patch('bridge_operator.live.place_signal',side_effect=lambda client,q,execute:client.request('operating_control',q|{'action':'single','execute':True})):
                result=benchmark.execute(operator,run,'signal');self.assertEqual(result['status'],'needs_attention')
            calls=len(native.calls)
            with self.assertRaisesRegex(ValueError,'already attempted'):benchmark.execute(operator,run,'signal')
            self.assertEqual(len(native.calls),calls)
            self.assertEqual(benchmark.inspect(operator,run)['status'],'needs_attention')

    def test_interrupted_run_or_changed_scope_never_opens_client(self):
        for status in ('running','completed','needs_attention'):
            with tempfile.TemporaryDirectory() as td:
                native,operator,run=self.workflow(td);path=operator.path(run)/'state.json';s=json.loads(path.read_text());s['status']=status;path.write_text(json.dumps(s))
                with patch.object(operator,'client',side_effect=AssertionError('no native calls')),self.assertRaises(ValueError):benchmark.execute(operator,run)


if __name__=='__main__':unittest.main()
