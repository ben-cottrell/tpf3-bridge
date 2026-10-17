"""Authored multi-window construction against an in-memory native adapter."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bridge_corridor import compile_corridor
from bridge_operator import Operator


def brief(roads=2):
    names=['up','down','fast_up','fast_down'][:roads]
    return {'version':1,'revision':'C1','session':'test','track':{'template':'track','style':'style'},
            'max_grade':.025,'stub_length':10,
            'waypoints':{f'w{i}':{name:{'position':[i*600,j*5,10+i*6],'direction':[1,0],'grade':.01}
                                  for j,name in enumerate(names)} for i in range(3)},
            'sections':[{'name':f'leg{i}','source':f'w{i}','target':f'w{i+1}',
                         'region':{'min':[i*600-20,-20,0],'max':[(i+1)*600+20,40,40]},
                         'members':[{'track':name} for name in names]} for i in range(2)]}


class Native:
    session='test'
    def __init__(self,directory):
        self.evidence=Path(directory);self.edges={};self.calls=[];self.counter=0;self.prepared={};self.reject_group=None;self.unknown_group=None;self.group_count=0
    def make_edge(self,p0,p1,t0,t1,node0=None,node1=None):
        ident=len(self.edges)+1
        row={'id':ident,'node0':node0 or ident*2,'node1':node1 or ident*2+1,'p0':p0,'p1':p1,'t0':t0,'t1':t1,
             'template':'track','style':'style','road_type':'TRACK','structure':{'classification':'NORMAL'}}
        self.edges[ident]=row;return row
    def select(self,client,intent,**kwargs):
        for edge in self.edges.values():
            for end in (0,1):
                if math.dist(edge[f'p{end}'],intent['guide_xyz'])<.0001:
                    return {'edge_id':edge['id'],'node_id':edge[f'node{end}'],'pos':edge[f'p{end}'],
                            'outward_direction':intent['travel_direction'],'grade':(-1 if end==0 else 1)*edge[f't{end}'][2]/math.hypot(*edge[f't{end}'][:2]),
                            'edge_snapshot':copy.deepcopy(edge)},None
        raise ValueError('fake exact port missing')
    def request(self,operation,params,**kwargs):
        self.counter+=1;self.calls.append((operation,copy.deepcopy(params)));rid=str(self.counter)
        if operation=='test_approach':
            q=params['fixture'];p0=q['position'];length=params['length'];d=q['travel_direction'];t=[length*d[0],length*d[1],length*q['grade']]
            p1=[a+b for a,b in zip(p0,t)];result={'edges':[self.make_edge(p0,p1,t,t)],'game_constructed':True}
        elif operation=='inspect':result={'edges':[copy.deepcopy(self.edges[i]) for i in params['edge_ids']]}
        elif operation=='structured_chain' and params.get('prepare'):
            self.group_count+=1
            if self.reject_group==self.group_count:return {'status':'no_accepted_candidate','request_id':rid,'result':{'error':'selected native fit rejected','game_constructed':False}}
            self.prepared[rid]=params;result={'game_constructed':False}
        elif operation=='structured_chain':
            if self.unknown_group==self.group_count:return {'status':'mutation_unverified','request_id':rid,'result':{'error':'unknown grouped effect','game_constructed':'unknown','retry':False}}
            groups=[]
            for group in self.prepared[params['prepared_request']]['groups']:
                a,b=group['source'],group['target'];delta=[y-x for x,y in zip(a['pos'],b['pos'])]
                edge=self.make_edge(a['pos'],b['pos'],delta,delta,a['node_id'],b['node_id'])
                groups.append({'readback':{'ordered_edges':[edge['id']]}})
            result={'groups':groups,'game_constructed':True}
        else:raise AssertionError(operation)
        return {'status':'ok','request_id':rid,'result':result}


class CorridorTests(unittest.TestCase):
    def test_compile_centred_profiles_and_existing_native_limits(self):
        compiled=compile_corridor(brief(4));first,second=compiled['sections']
        self.assertEqual(len(first['created_bindings']),8);self.assertEqual(len(second['created_bindings']),4)
        self.assertEqual(len(second['required_bindings']),4)
        p=first['plan'];stub=p['steps'][0];port=p['ports'][stub['port']]
        self.assertEqual(port['position'],[-5,0,9.95]);self.assertEqual(stub['grade'],.01)
        self.assertEqual(p['ports']['front_0']['position'],[5,0,10.05])
        self.assertEqual(p['ports']['back_1']['position'],[595,0,15.95])
        self.assertEqual(p['ports']['back_1']['grade'],-.01)
        self.assertNotIn('bindings',p) # unresolved slots never become executable fake geometry
        bad=brief();bad['sections'][1]['region']['max'][0]=1900
        with self.assertRaisesRegex(ValueError,'1000'):compile_corridor(bad)
        bad=brief();bad['waypoints']['w2']['up']['grade']=.05
        with self.assertRaisesRegex(ValueError,'stub grade'):compile_corridor(bad)

    def test_existing_outer_endpoints_are_bound_without_new_stubs(self):
        b=brief();b['bindings']={}
        for index,road in enumerate(('up','down')):
            ident=index+1;edge={'id':ident,'node0':ident*2,'node1':ident*2+1,'p0':[-10,index*5,9.9],
                'p1':[0,index*5,10],'t0':[10,0,.1],'t1':[10,0,.1],
                'template':'track','style':'style'}
            name=f'outer_{road}';b['bindings'][name]={'edges':[edge]}
            b['waypoints']['w0'][road]={'front':{'chain':name,'edge_id':ident,'node_id':ident*2+1}}
        first=compile_corridor(b)['sections'][0]
        self.assertEqual(len(first['created_bindings']),2)
        self.assertEqual(first['required_bindings'],['outer_down','outer_up'])
        self.assertEqual(first['plan']['port_refs']['front_0']['edge_id'],1)

    def test_existing_reversed_node0_uses_outward_direction_and_grade(self):
        b=brief();b['bindings']={}
        for i,road in enumerate(('up','down')):
            edge={'id':i+1,'node0':i*2+2,'node1':i*2+3,'p0':[0,i*5,10],
                  'p1':[-10,i*5,9.9],'t0':[-10,0,-.1],'t1':[-10,0,-.1],
                  'template':'track','style':'style'}
            b['bindings'][road]={'edges':[edge]}
            b['waypoints']['w0'][road]={'front':{'chain':road,'edge_id':edge['id'],'node_id':edge['node0']}}
        port=compile_corridor(b)['sections'][0]['plan']['ports']['front_0']
        self.assertEqual(port['direction'],[1,0]);self.assertEqual(port['grade'],.01)

    def test_compile_rejects_target_far_end_and_native_lower_bounds(self):
        b=brief();b['sections'][0]['region']['max'][0]=600
        with self.assertRaisesRegex(ValueError,'entire waypoint stub'):compile_corridor(b)
        b=brief();b['waypoints']['w1']['up']['position'][0]=850;b['sections'][0]['region']['max'][0]=870
        with self.assertRaisesRegex(ValueError,'native800'):compile_corridor(b)
        b=brief(4)
        for member in b['sections'][0]['members']:
            y=b['waypoints']['w0'][member['track']]['position'][1]
            member['guides']=[{'position':[x,y,10+x*.01],'travel_direction':[1,0],'grade':.01} for x in range(80,481,80)]
        with self.assertRaisesRegex(ValueError,'native20'):compile_corridor(b)

    def test_built_child_invalidated_waypoint_stops_before_next_window(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run'];original=o._execute
            def invalidate(child):
                original(child);path=o.path(child)/'state.json';state=json.loads(path.read_text())
                state['invalidated_bindings']=['corr_seed_1_up'];path.write_text(json.dumps(state))
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select),patch.object(o,'_execute',side_effect=invalidate):result=o.build_corridor(run)
            self.assertEqual(result['status'],'needs_attention');self.assertIn('invalidated',result['error'])
            self.assertEqual(sum(op=='test_approach' for op,_ in native.calls),4)
            self.assertEqual(native.group_count,1)

    def test_next_window_uses_updated_exact_waypoint_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run'];original=o._execute;children=[]
            def replace(child):
                original(child);children.append(child)
                if len(children)==1:
                    path=o.path(child)/'state.json';state=json.loads(path.read_text());binding=state['steps']['corr_seed_1_up']
                    row=copy.deepcopy(binding['edges'][0]);old=row['id'];row['id']=900
                    native.edges.pop(old);native.edges[900]=row;binding['edges']=[row]
                    state['lineage']=[{'original_edge':old,'replacement_edges':[900]}];path.write_text(json.dumps(state))
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select),patch.object(o,'_execute',side_effect=replace):result=o.build_corridor(run)
            self.assertEqual(result['status'],'built')
            following=json.loads((o.path(children[1])/'plan.json').read_text())
            self.assertEqual(following['bindings']['corr_seed_1_up']['edges'][0]['id'],900)
            self.assertEqual(sum(op=='test_approach' for op,_ in native.calls),6)

    def test_build_four_tracks_carries_exact_stubs_and_never_duplicates_shared_waypoint(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native)
            run=o.plan_corridor(brief(4))['run'];self.assertFalse(native.calls)
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):result=o.build_corridor(run)
            self.assertEqual(result['status'],'built');self.assertEqual(result['completed_sections'],2)
            self.assertEqual(sum(op=='test_approach' for op,_ in native.calls),12)
            parent=json.loads((o.path(run)/'state.json').read_text());child=json.loads((o.path(parent['section_runs'][1]['run'])/'plan.json').read_text())
            for binding in child['bindings'].values():self.assertIn(binding['edges'][0]['id'],native.edges)
            with self.assertRaisesRegex(ValueError,'already attempted'):o.build_corridor(run)

    def test_stopped_section_requires_explicit_existing_plan_continuation(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);native.reject_group=2;o=Operator(runs=td,client=native)
            run=o.plan_corridor(brief())['run']
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):
                result=o.build_corridor(run);self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['completed_sections'],1)
                calls=len(native.calls);again=o.continue_corridor(run)
                self.assertEqual(again['status'],'needs_attention');self.assertEqual(len(native.calls),calls)
                resumed=o.continue_plan(result['current_run'],'C2')
                native.reject_group=None
                self.assertEqual(o.continue_corridor(run,resumed['run'])['status'],'built')
            self.assertEqual(sum(op=='test_approach' for op,_ in native.calls),6)

    def test_interrupted_parent_accepts_built_child_without_replaying_it(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run'];original=o._execute
            def interrupt(child):original(child);raise SystemExit('interrupted after successful child')
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):
                with patch.object(o,'_execute',side_effect=interrupt),self.assertRaises(SystemExit):o.build_corridor(run)
                self.assertEqual(o.corridor_status(run)['status'],'running')
                self.assertEqual(o.continue_corridor(run)['status'],'built')
            self.assertEqual(sum(op=='test_approach' for op,_ in native.calls),6)
            self.assertFalse((Path(td)/'execution.lock').exists())

    def test_unknown_group_effect_retains_child_state_and_refuses_replay(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);native.unknown_group=2;o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run']
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):result=o.build_corridor(run)
            self.assertEqual(result['completed_sections'],1);self.assertEqual(result['status'],'needs_attention')
            child=json.loads((o.path(result['current_run'])/'state.json').read_text())
            self.assertEqual(child['step_mutation']['game_constructed'],'unknown')
            self.assertEqual(len(child['steps']),2) # second section's waypoint stubs remain recorded
            calls=len(native.calls);self.assertEqual(o.continue_corridor(run)['status'],'needs_attention');self.assertEqual(len(native.calls),calls)
            with self.assertRaisesRegex(ValueError,'partial effects'):o.continue_plan(result['current_run'],'C2')

    def test_session_change_stops_before_any_effect(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run'];native.session='loaded_again'
            with self.assertRaisesRegex(ValueError,'session changed'):o.build_corridor(run)
            self.assertFalse(native.calls)

    def test_exact_port_rejects_coordinate_lookalike(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);o=Operator(runs=td,client=native);run=o.plan_corridor(brief())['run']
            def wrong(*args,**kwargs):
                candidate,other=native.select(*args,**kwargs);candidate['edge_id']=999;return candidate,other
            with patch('bridge_operator.live._select_throat_port',side_effect=wrong):result=o.build_corridor(run)
            self.assertEqual(result['status'],'needs_attention');self.assertIn('exact authored',result['error'])
            self.assertFalse(any(op=='structured_chain' for op,_ in native.calls))


if __name__=='__main__':unittest.main()
