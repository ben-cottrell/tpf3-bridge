import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bridge_operator import Operator, validate_plan, cubic


def fixture():
    return {'version':1,'revision':'R1','origin':[0,0,2],
            'region':{'min':[-5,-5,0],'max':[65,10,5]},
            'ports':{'a':{'position':[0,0,0],'direction':[1,0]}},
            'track':{'template':'track','style':'style'},'max_grade':.01,
            'steps':[{'name':'one','kind':'stub','port':'a','length':20}], 'routes':[], 'curves':{}}


class FakeClient:
    session='test'
    evidence=Path('.')
    def __init__(self, failure=False):self.calls=[];self.failure=failure
    def request(self,op,q,**kwargs):
        self.calls.append((op,q))
        return {'status':'error' if self.failure else 'ok','request_id':'r1',
                'result':{'error':'native_rejection'} if self.failure else {'edges':[],'game_constructed':True}}


class OperatorTest(unittest.TestCase):
    def test_complete_run_cannot_be_replayed(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run']
            self.assertEqual(o.execute(run)['status'],'built')
            with self.assertRaises(ValueError):o.execute(run)
            self.assertEqual(len(c.calls),1)
            region=c.calls[0][1]['fixture']['region']
            for i in range(3):
                self.assertGreaterEqual(region['min'][i],fixture()['region']['min'][i])
                self.assertLessEqual(region['max'][i],fixture()['region']['max'][i])

    def test_native_rejection_stops_without_next_step_or_replay(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient(True);o=Operator(runs=td,client=c);p=fixture()
            p['steps'].append({**p['steps'][0],'name':'two'})
            run=o.plan(p)['run'];r=o.execute(run)
            self.assertEqual(r['status'],'needs_attention');self.assertEqual(r['completed_steps'],0)
            with self.assertRaises(ValueError):o.execute(run)
            self.assertEqual(len(c.calls),1)

    def test_changed_plan_rejected_before_native_calls(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run']
            p=fixture();p['steps'][0]['length']=25
            (o.path(run)/'plan.json').write_text(json.dumps(p))
            with self.assertRaises(ValueError):o.execute(run)
            self.assertEqual(c.calls,[])

    def test_session_change_prevents_stale_review(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run'];o.execute(run)
            c.session='new'
            with self.assertRaisesRegex(ValueError,'session changed'):o.review(run)

    def test_failed_required_route_is_not_successful_review(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture()
            p['routes']=[{'name':'required','source':'a','target':'a'}]
            run=o.plan(p)['run'];o.execute(run)
            with (patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2},'found')),
                  patch.object(c,'request',side_effect=[{'status':'ok','request_id':'route','result':{'requested_route_verified':False}},
                      {'status':'ok','request_id':'survey','result':{'complete':True,'edges':[]}}])):
                result=o.review(run)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['verified_routes'],0)
            self.assertFalse(json.loads((o.path(run)/'review.json').read_text())['all_routes_verified'])

    def test_reference_order_and_finite_geometry(self):
        p=fixture();p['ports']['a']['position'][0]=float('nan')
        with self.assertRaises(ValueError):validate_plan(p)
        p=fixture();p['steps'][0]={'name':'bad','kind':'branch','source':{'curve':'later','u':.5},'target':'a'}
        with self.assertRaises(ValueError):validate_plan(p)

    def test_curve_point_preserves_grade_and_heading(self):
        c={'p0':[0,0,2],'p1':[100,0,12],'t0':[100,0,10],'t1':[100,0,10]}
        p,d=cubic(c,.25);self.assertEqual(p,[25,0,4.5]);self.assertEqual(d,[1,0])

    def test_concurrent_build_lock_prevents_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run']
            (Path(td)/'execution.lock').touch()
            with self.assertRaises(ValueError):o.execute(run)
            self.assertEqual(c.calls,[])

    def test_stubs_can_be_constructed_opposite_to_attachment_direction(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture()
            p['ports']['a']['direction']=[-1,0];p['steps'][0]['direction']=[1,0]
            o.execute(o.plan(p)['run'])
            self.assertEqual(c.calls[0][1]['fixture']['travel_direction'],[1,0])

    def test_interrupted_run_requires_attention_not_replay(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run']
            path=o.path(run)/'state.json';state=json.loads(path.read_text());state['status']='running';path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'already attempted'):o.execute(run)
            self.assertEqual(c.calls,[])

    def test_oversized_region_and_out_of_scope_stub_do_not_mutate(self):
        p=fixture();p['region']['max'][0]=1000
        with self.assertRaises(ValueError):validate_plan(p)
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture();p['region']['max'][0]=10
            result=o.execute(o.plan(p)['run']);self.assertEqual(result['status'],'needs_attention');self.assertEqual(c.calls,[])

    def test_uncertain_mutation_retains_partial_steps_and_refuses_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture();p['steps'].append({**p['steps'][0],'name':'two'})
            run=o.plan(p)['run']
            with patch.object(c,'request',side_effect=[{'status':'ok','request_id':'first','result':{'edges':[]}},
                    {'status':'mutation_unverified','request_id':'uncertain','result':{'error':'lost_ack','game_constructed':'unknown'}}]):
                result=o.execute(run)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['completed_steps'],1)
            state=json.loads((o.path(run)/'state.json').read_text());self.assertEqual(state['last_request'],'uncertain')
            with self.assertRaises(ValueError):o.execute(run)

    def test_extension_wrapper_records_native_ids_as_geometry_for_later_steps(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture();p['ports']['b']={'position':[50,0,0],'direction':[1,0]}
            p['steps']=[{'name':'extension','kind':'extend','source':'a','target':'b'}]
            row={'id':42,'p0':[0,0,2],'p1':[50,0,2],'t0':[50,0,0],'t1':[50,0,0]}
            def extend(client,*args,**kwargs):
                self.assertEqual(client.evidence,c.evidence)
                client.request('extension',{},request_id='native-extension')
                return {'status':'ok','job_id':'native-extension','edges':[42]}
            with (patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2},'found')),
                 patch('bridge_operator.live.extend',side_effect=extend),
                 patch.object(c,'request',side_effect=[{'status':'ok','request_id':'native-extension','result':{}},
                     {'status':'ok','request_id':'read','result':{'edges':[row]}}])):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'built')
            self.assertEqual(json.loads((o.path(run)/'state.json').read_text())['steps']['extension']['edges'],[row])

    def test_capture_does_not_claim_success_without_a_new_file(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();c.log=Path(td)/'crash_dump/stdout.txt';c.evidence=Path(td)
            o=Operator(runs=Path(td)/'runs',client=c)
            with patch('bridge_operator.time.monotonic',side_effect=[0,11]):result=o.gui('capture')
            self.assertEqual(result['status'],'file_completion_unobserved');self.assertFalse(result['file_completed'])

    def test_save_will_not_overwrite_an_existing_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();c.log=Path(td)/'crash_dump/stdout.txt';c.evidence=Path(td)
            folder=Path(td)/'save';folder.mkdir();(folder/'already.sav').write_bytes(b'existing')
            o=Operator(runs=Path(td)/'runs',client=c)
            with self.assertRaisesRegex(ValueError,'already exists'):o.gui('save',name='already')
            self.assertEqual(c.calls,[])

if __name__=='__main__':unittest.main()
