"""Offline family composition/acceptance tests; no native or UI calls."""
import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_approach as approach
import bridge_live as live
from bridge_operator import Operator
from test_operator import fixture
import test_operator
import test_operator_fit_variation as fitting
from test_corridor_operator import Native,brief as corridor_brief


def brief():
    p=fixture();p['version']=2
    f={'name':'seed','kind':'operator','phase':'ordinary','envelopes':[copy.deepcopy(p['region'])],
       'payload':p,'imports':{},'exports':{'road':'one'},'shared_effects':[]}
    return {'version':1,'revision':'A1','session':'test','station':{'name':'Station','construction':{'resource':'station','position':[0,0,2]}},
        'interfaces':{},'families':[f],'checks':[{'name':'alignment','kind':'geometry','families':['seed'],'shared_effects':[],
            'bindings':{'road':'seed.road'},'payload':{'region':p['region'],'max_grade':.01}}]}


class World(Native):
    def __init__(self,directory):
        super().__init__(directory);self.objects={};self.revisions={};self.extra_incidence={};self.node_owners={};self.station_revision=1
    def request(self,op,q,**kwargs):
        if op=='inspect':
            r=super().request(op,q,**kwargs)
            if 'incidence_edge_ids' in q:
                selected=q['incidence_edge_ids'];nodes=sorted({self.edges[i][k] for i in selected for k in ('node0','node1')});rows=[]
                for node in nodes:
                    incident=sorted({e['id'] for e in self.edges.values() if node in (e['node0'],e['node1'])}|set(self.extra_incidence.get(node,[])))
                    rows.append({'node_id':node,'incident_edges':incident,'incident_count':len(incident),'incidence_complete':True,'incident_output_truncated':False,'construction_owner':self.node_owners.get(node,'none')})
                r['result']['endpoint_incidence']={'edge_ids':selected,'nodes':rows,'node_count':len(rows),'complete':True,'truncated':False}
            return r
        if op=='station_lookup':
            self.calls.append((op,copy.deepcopy(q)))
            return {'status':'ok','request_id':'station','result':{'identity_complete':True,'frozen_complete':True,
                'group_revision':self.station_revision,'constructions':[{'construction_id':42,'resource':'station','position':[0,0,2]}]}}
        if op=='operating_inspect':
            self.calls.append((op,copy.deepcopy(q)))
            rows=[{'id':i,'node0':self.edges[i]['node0'],'node1':self.edges[i]['node1'],'revision':self.revisions.get(i,[1,0,0]),'objects':copy.deepcopy(self.objects.get(i,[]))} for i in q['track_ids']]
            return {'status':'ok','request_id':'objects','result':{'tracks':{'records':rows,'count':len(rows),'truncated':False}}}
        if op=='discover':
            self.calls.append((op,copy.deepcopy(q)));candidates=[]
            for e in self.edges.values():
                for end in (0,1):
                    pos=e['p'+str(end)];node=e['node'+str(end)]
                    if not all(q['region']['min'][i]<=pos[i]<=q['region']['max'][i] for i in range(3)):continue
                    incident=sorted({row['id'] for row in self.edges.values() if node in (row['node0'],row['node1'])}|set(self.extra_incidence.get(node,[])))
                    candidates.append({'edge_id':e['id'],'node_id':node,'incident_edges':incident,'incident_count':len(incident),'incidence_complete':True,'incident_output_truncated':False,'construction_owner':self.node_owners.get(node,'none')})
            return {'status':'ok','request_id':'incidence','result':{'complete':True,'candidates':candidates}}
        return super().request(op,q,**kwargs)


class ApproachTests(unittest.TestCase):
    def test_offline_plan_then_build_review_and_affected_only_cache(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();run=o.plan_approach(b)['run']
            self.assertEqual(c.calls,[])
            result=o.build_approach(run);self.assertEqual(result['status'],'built');self.assertEqual(result['completed_families'],1)
            result=o.review_approach(run);self.assertEqual(result['status'],'reviewed');self.assertEqual(result['checks_run'],1)
            self.assertLess(len(json.dumps(result).encode()),4096)
            calls=len(c.calls);self.assertEqual(o.review_approach(run)['checks_run'],0)
            self.assertEqual([op for op,_ in c.calls[calls:]],['inspect'])
            with self.assertRaisesRegex(ValueError,'already attempted'):o.build_approach(run)

    def test_backwards_only_bounded_and_authorised_windows(self):
        for change in ('forward','count','envelope','phase'):
            b=brief()
            if change=='forward':b['families'][0]['imports']={'road':'later.road'}
            elif change=='count':b['families']*=9
            elif change=='envelope':b['families'][0]['envelopes'][0]['max'][0]=10
            else:b['families'][0]['phase']='leads'
            with self.subTest(change=change),self.assertRaises(ValueError):approach.compile_brief(b)

    def test_stale_session_and_pending_request_stop_before_any_native_work(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);run=o.plan_approach(brief())['run'];c.session='new'
            with self.assertRaisesRegex(ValueError,'session changed'):o.build_approach(run)
            c.session='test';c.journal=Path(td)/'journal.json';c.journal.write_text('{"pending":true}')
            with self.assertRaisesRegex(ValueError,'reconciliation'):o.build_approach(run)
            self.assertEqual(c.calls,[])

    def test_completed_child_consumed_after_parent_interruption_without_replay(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);run=o.plan_approach(brief())['run'];original=live.atomic_json;interrupted=False
            def write(path,value):
                nonlocal interrupted
                if path==o.path(run)/'state.json' and value.get('family_index')==1 and not interrupted:
                    interrupted=True;raise SystemExit('simulated interruption before advance')
                original(path,value)
            with patch.object(live,'atomic_json',side_effect=write),self.assertRaises(SystemExit):o.build_approach(run)
            state=approach.load(o.path(run)/'state.json');self.assertEqual(state['family_index'],0)
            self.assertEqual(state['families']['seed']['status'],'built')
            result=o.continue_approach(run);self.assertEqual(result['status'],'built')
            self.assertEqual(sum(op=='test_approach' for op,_ in c.calls),1)

    def test_family_completion_and_counters_survive_atomic_propagation_state_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);run=o.plan_approach(brief())['run'];original=approach.propagate
            def propagate(b,s,child,signal_only,receipt=None):
                original(b,s,child,signal_only,receipt=receipt)
                new=copy.deepcopy(s);s.clear();s.update(new)
            with patch('bridge_approach.propagate',side_effect=propagate):result=o.build_approach(run)
            entry=approach.load(o.path(run)/'state.json')['families']['seed'];child=approach.load(o.path(entry['run'])/'state.json')
            self.assertEqual(result['status'],'built');self.assertEqual(entry['status'],'built')
            self.assertEqual(entry['calls'],child['calls']);self.assertEqual(entry['native_seconds'],child['native_seconds'])
            self.assertGreater(entry['calls'],0)

    def test_unknown_mutation_never_replayed_on_continue(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);run=o.plan_approach(brief())['run'];original=c.request
            def request(op,q,**kw):
                if op=='test_approach':
                    c.calls.append((op,q));return {'status':'mutation_unverified','request_id':'unknown','result':{'game_constructed':'unknown','error':'lost ack'}}
                return original(op,q,**kw)
            with patch.object(c,'request',side_effect=request):
                self.assertEqual(o.build_approach(run)['status'],'needs_attention')
                self.assertEqual(o.continue_approach(run)['status'],'needs_attention')
            self.assertEqual(sum(op=='test_approach' for op,_ in c.calls),1)

    def test_dependency_refresh_once_then_child_keeps_mutation_freshness(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();second=copy.deepcopy(b['families'][0]);second.update(name='later',imports={'a':'seed.road','b':'seed.road'},exports={'road':'a'})
            second['payload']['steps'][0]['name']='later_seed';b['families'].append(second)
            run=o.plan_approach(b)['run'];self.assertEqual(o.build_approach(run)['status'],'built')
            state=approach.load(o.path(run)/'state.json');self.assertEqual(state['bindings']['seed.road'],state['bindings']['later.road'])
            # One phase-entry observation per shared reference, plus child bindings
            # freshness and committed export qualification (not a skipped native gate).
            inspections=[q for op,q in c.calls if op=='inspect' and q['edge_ids']==[1]]
            self.assertEqual(len(inspections),5)

    def test_corridor_family_exports_exact_ordered_road(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();p=corridor_brief(2)
            b['families']=[{'name':'corridor','kind':'corridor','phase':'ordinary','envelopes':[s['region'] for s in p['sections']],
                'payload':p,'imports':{},'exports':{'up':{'road':{'track':'up','sections':['leg0','leg1']}}},'shared_effects':[]}];b['checks']=[]
            run=o.plan_approach(b)['run']
            with patch('bridge_live._select_throat_port',side_effect=c.select):result=o.build_approach(run)
            self.assertEqual(result['status'],'built',result)
            rows=approach.load(o.path(run)/'state.json')['bindings']['corridor.up']['edges'];self.assertEqual(len(rows),5)
            self.assertTrue(all(a['node1']==z['node0'] for a,z in zip(rows,rows[1:])))

    def test_signal_identity_mapping_preserves_geometry_but_invalidates_direction(self):
        b=brief();b['checks'].append({'name':'direction','kind':'route','families':['seed'],'shared_effects':[], 'bindings':{'road':'seed.road'},'payload':{}})
        edge={'id':1,'node0':2,'node1':3,'p0':[0,0,0],'p1':[20,0,0],'t0':[20,0,0],'t1':[20,0,0],'road_type':'TRACK'}
        s={'bindings':{'seed.road':{'edges':[edge]}},'checks':{'alignment':{'valid':True},'direction':{'valid':True}}}
        new=edge|{'id':9};child={'bindings':{'road':{'edges':[new]}},'lineage':[{'original_edge':1,'replacement_edges':[9]}]}
        approach.propagate(b,s,child,True)
        self.assertTrue(s['checks']['alignment']['valid']);self.assertFalse(s['checks']['direction']['valid']);self.assertEqual(s['bindings']['seed.road']['edges'][0]['id'],9)
        moved=new|{'id':10,'p1':[20,0,1]};child={'bindings':{'road':{'edges':[moved]}},'lineage':[{'original_edge':9,'replacement_edges':[10]}]}
        approach.propagate(b,s,child,True);self.assertFalse(s['checks']['alignment']['valid'])

    def test_shared_crossing_effect_invalidates_other_family_check_only(self):
        b={'checks':[{'name':'crossing','kind':'crossing','families':['lower','upper'],'shared_effects':['overlap']},
                     {'name':'distant','kind':'route','families':['other'],'shared_effects':[]}]}
        s={'checks':{'crossing':{'valid':True},'distant':{'valid':True}}}
        self.assertEqual(approach.invalidate(b,s,['flyover'],['overlap']),['crossing']);self.assertTrue(s['checks']['distant']['valid'])

    def test_incomplete_mapping_does_not_guess_identity(self):
        s={'bindings':{'seed.road':{'edges':[{'id':1}]}},'checks':{}}
        with self.assertRaisesRegex(ValueError,'incomplete'):approach.propagate(brief(),s,{'lineage':[{'original_edge':1,'replacement_edges':[99]}]},False)

    def test_repeated_and_split_replacement_maps_to_final_receipts(self):
        edge={'id':1,'node0':2,'node1':3};s={'bindings':{'seed.road':{'edges':[edge]}},'checks':{}}
        left={'id':8,'node0':2,'node1':20};right={'id':9,'node0':20,'node1':3}
        child={'bindings':{'parent':{'edges':[left,right]}},'lineage':[{'original_edge':1,'replacement_edges':[5]}, {'original_edge':5,'replacement_edges':[8,9]}]}
        approach.propagate(brief(),s,child,False)
        self.assertEqual([e['id'] for e in s['bindings']['seed.road']['edges']],[8,9])
        self.assertEqual(approach.imported_endpoint(s,'seed.road',{'edge_id':1,'node_id':2},s['bindings']['seed.road']['edges'])['id'],8)

    def test_chronological_recycled_ids_do_not_cross_bindings_or_replay_receipts(self):
        a={'id':1,'node0':10,'node1':20};z={'id':2,'node0':30,'node1':40}
        s={'bindings':{'seed.in':{'edges':[a]},'seed.out':{'edges':[z]}},'checks':{}}
        rows=[{'id':3,'node0':10,'node1':11},{'id':2,'node0':11,'node1':12},{'id':9,'node0':12,'node1':13},{'id':10,'node0':13,'node1':20},
              {'id':5,'node0':30,'node1':31},{'id':7,'node0':31,'node1':32},{'id':1,'node0':32,'node1':40}]
        child={'bindings':{'current':{'edges':rows}},'steps':{'new_branch':{'edges':[{'id':6,'node0':13,'node1':99}]}},'lineage':[
            {'request_id':'first','original_edge':1,'replacement_edges':[3,4]}, {'request_id':'first','original_edge':2,'replacement_edges':[5,6]},
            {'request_id':'second','original_edge':6,'replacement_edges':[7,1]}, {'request_id':'second','original_edge':4,'replacement_edges':[2,8]},
            {'request_id':'third','original_edge':8,'replacement_edges':[9,10]}]}
        approach.propagate(brief(),s,child,False,receipt='native_child')
        self.assertEqual([e['id'] for e in s['bindings']['seed.in']['edges']],[3,2,9,10])
        self.assertEqual([e['id'] for e in s['bindings']['seed.out']['edges']],[5,7,1])
        self.assertEqual(approach.imported_endpoint(s,'seed.out',{'edge_id':2,'node_id':40},s['bindings']['seed.out']['edges'])['id'],1)
        before=copy.deepcopy(s);approach.propagate(brief(),s,child,False,receipt='native_child');self.assertEqual(s,before)

    def test_atomic_command_recycling_is_not_a_transitive_id_graph(self):
        s={'bindings':{'seed.a':{'edges':[{'id':1,'node0':10,'node1':20}]},'seed.b':{'edges':[{'id':2,'node0':30,'node1':40}]}},'checks':{}}
        child={'bindings':{'current':{'edges':[{'id':2,'node0':10,'node1':20},{'id':3,'node0':30,'node1':40}]}},'lineage':[
            {'request_id':'atomic','original_edge':1,'replacement_edges':[2]},{'request_id':'atomic','original_edge':2,'replacement_edges':[3]}]}
        approach.propagate(brief(),s,child,False)
        self.assertEqual([e['id'] for e in s['bindings']['seed.a']['edges']],[2]);self.assertEqual([e['id'] for e in s['bindings']['seed.b']['edges']],[3])

    def test_failed_generation_mapping_does_not_leave_partial_binding_or_cursor(self):
        s={'bindings':{'seed.a':{'edges':[{'id':1,'node0':10,'node1':20}]}},'checks':{}};before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,'incomplete'):approach.propagate(brief(),s,{'lineage':[{'original_edge':1,'replacement_edges':[9]}]},False,receipt='bad')
        self.assertEqual(s,before)

    def test_imported_port_uses_current_receipt_geometry_not_preliminary_coordinates(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();later=copy.deepcopy(b['families'][0]);later.update(name='later',imports={'parent':'seed.road'},exports={'road':'later_seed'})
            later['payload']['ports']['a']['position']=[5,0,0]
            later['payload']['port_refs']={'a':{'chain':'parent','end':'node1'}};later['payload']['steps'][0]['name']='later_seed'
            b['families'].append(later);run=o.plan_approach(b)['run'];result=o.build_approach(run)
            self.assertEqual(result['status'],'built',result)
            requests=[q for op,q in c.calls if op=='test_approach'];self.assertEqual(requests[1]['fixture']['position'],[20,0,2])

    def test_nearby_fit_displacement_controls_later_exact_attachment(self):
        with tempfile.TemporaryDirectory() as td:
            c=fitting.Client(reject=1);c.evidence=Path(td);o=Operator(runs=td,client=c);b=brief();p=fitting.plan(c)
            f=b['families'][0];f.update(name='fan',payload=p,envelopes=[p['region']],exports={'road':'fan'})
            later=copy.deepcopy(f);later.update(name='later',imports={'parent':'fan.road'},exports={})
            later['payload']=fixture();later['payload'].update(version=2,origin=[0,0,0],region=p['region'],port_refs={'a':{'chain':'parent','end':'node0'}})
            later['payload']['ports']['a']['position']=[30,0,2];b['families'].append(later);b['checks']=[]
            original=c.request;new={};placements=[]
            def request(op,q,**kw):
                if op=='station_lookup':return World(td).request(op,q)
                if op=='test_approach':placements.append(q['fixture']['position']);return {'status':'ok','request_id':'later','result':{'edges':[],'game_constructed':True}}
                if op=='inspect' and q['edge_ids']==[3]:return {'status':'ok','request_id':'read','result':{'edges':[new['edge']]}}
                r=original(op,q,**kw)
                if q.get('execute'):
                    row=fitting.edge(3,c.prepares[-1]['source']['pos'],c.prepares[-1]['target']['pos']);new['edge']=row;r['result']['edges']=[row]
                return r
            with patch.object(c,'request',side_effect=request),patch('bridge_live._select_throat_port',side_effect=c.select):
                run=o.plan_approach(b)['run'];result=o.build_approach(run)
            self.assertEqual(result['status'],'built',result);self.assertEqual(len(placements),1)
            for actual,expected in zip(placements[0],[35,0,2]):self.assertAlmostEqual(actual,expected,places=12)
            self.assertEqual(result['families'][0]['fit'][0]['attempt_count'],2)

    def test_interface_phases_qualify_once_in_order_without_consumed_role_requalification(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();lead=copy.deepcopy(b['families'][0]);lead['phase']='leads';lead['name']='leads';lead['payload']['steps']=[{'name':'lead','kind':'extend','source':'a','target':'b'}];lead['payload']['ports']['b']={'position':[30,0,0],'direction':[1,0]};lead['exports']={}
            b['families'].insert(0,lead);b['interfaces']={'station':{'name':'station_roles','revision':'R1','roles':{}},'ordinary':{'name':'ordinary_roles','revision':'R1','roles':{}}}
            # Compile structural phases independently from native registry details.
            events=[]
            def qualify(op,b,s,phase):
                if phase not in s['interfaces']:events.append(phase);s['interfaces'].append(phase)
            def execute(child):
                path=o.path(child)/'state.json';state=approach.load(path);state.update(status='built',steps={});live.atomic_json(path,state);events.append('lead_built')
                return {'status':'built'}
            original=o.execute
            def run_child(child):
                p=approach.load(o.path(child)/'plan.json')
                return execute(child) if p['steps'][0]['kind']=='extend' else original(child)
            run=o.plan_approach(b)['run']
            with patch('bridge_approach.qualify_interfaces',side_effect=qualify),patch.object(o,'execute',side_effect=run_child):result=o.build_approach(run)
            self.assertEqual(result['status'],'built',result);self.assertEqual(events,['station','lead_built','ordinary'])

    def test_station_leads_observe_mirrored_lateral_terminal_order_and_grade(self):
        for direction,expected in (([1,0],[4,2,7,1]),([-1,0],[1,7,2,4])):
            with self.subTest(direction=direction),tempfile.TemporaryDirectory() as td:
                c=World(td);o=Operator(runs=td,client=c);selector=brief()['station'];records=[]
                for y,terminal in zip((-7.5,-2.5,2.5,7.5),(4,2,7,1)):
                    records.append({'edge_id':terminal,'node_id':terminal*2,'pos':[0,y,2],'outward_direction':direction,'grade':.01,
                        'association':{'construction_id':42,'terminal_identity_matches':[{'terminal_index':terminal}]}})
                records.reverse();path=Path(td)/'exits.json';live.atomic_json(path,{'station':{'constructions':[{'construction_id':42,**selector['construction']}]},'exits':records})
                with patch('bridge_station.inspect_exits',return_value={'evidence':str(path)}) as survey:
                    result=approach.station_leads(o,selector,outward_direction=direction,ordered_roles=['P1','P2','P3','P4'],lead_length=30,registry_name='station_roles',revision='R1',track={'template':'track','style':'style'},max_grade=.02,region={'min':[-50,-20,0],'max':[50,20,10]})
                    data=approach.load(path);data['session']='test';live.atomic_json(path,data)
                    reused=approach.station_leads(o,selector,outward_direction=direction,ordered_roles=['P1','P2','P3','P4'],lead_length=30,registry_name='station_roles',revision='R1',track={'template':'track','style':'style'},max_grade=.02,region={'min':[-50,-20,0],'max':[50,20,10]},exit_evidence=path)
                    self.assertEqual(result,reused);self.assertEqual(survey.call_count,1)
                self.assertEqual([r['station']['terminal_index'] for r in result['station_interfaces']['roles'].values()],expected)
                self.assertEqual(result['mouth_datum'],[0,0,2]);self.assertAlmostEqual(result['payload']['ports']['P1_end']['position'][2],.3)
                self.assertEqual(result['payload']['ports']['P1_end']['position'][0],30*direction[0]);self.assertEqual(c.calls,[])

    def test_partial_four_lead_continuation_does_not_resolve_consumed_station_exits(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);p=fixture();p.update(version=2,origin=[0,0,0],region={'min':[-5,-20,0],'max':[65,20,5]},ports={},steps=[],role_refs={},interface_registry='station_roles',interface_revision='R1')
            observed={}
            for i in range(4):
                name=f'P{i+1}';source=name+'_exit';target=name+'_end';pos=[0,i*5,2]
                p['role_refs'][source]=name;p['ports'][target]={'position':[30,i*5,2],'direction':[1,0],'grade':0}
                p['steps'].append({'name':name+'_lead','kind':'extend','source':source,'target':target})
                observed[name]={'mode':'station_exit','candidate':{'edge_id':i+1,'node_id':i+2,'pos':pos,'outward_direction':[1,0],'grade':0}}
            resolved=[]
            def resolve(self,client,name,revision,names=None):
                resolved.append(list(names));return {'resolved':{n:observed[n] for n in names}}
            ok={'status':'ok','request_id':'lead','result':{'game_constructed':True,'edges':[]}}
            fail={'status':'no_accepted_candidate','request_id':'rejected','result':{'game_constructed':False,'error':'rejected'}}
            with patch('bridge_interfaces.InterfaceRegistry.resolve',new=resolve),patch('bridge_operator.live.extend',side_effect=[ok,ok,fail]):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'needs_attention')
            resolved.clear()
            with patch('bridge_interfaces.InterfaceRegistry.resolve',new=resolve),patch('bridge_operator.live.extend',return_value=ok) as extend:
                next_run=o.continue_plan(run,'R2')['run'];self.assertEqual(o.execute(next_run)['status'],'built')
            self.assertTrue(all(set(names)=={'P3','P4'} for names in resolved));self.assertEqual(extend.call_count,2)
            value=approach.exported_binding(o,next_run,approach.load(o.path(next_run)/'state.json'),'P1_lead')
            self.assertEqual(value['status'],'built') # Prefix remains exportable without resolving consumed roles.

    def test_worst_bounded_summary_stays_compact(self):
        b=brief();b['families']=[];s={'status':'needs_attention','session':'s'*160,'family_index':7,'families':{},'checks':{},'error':'e'*350}
        for i in range(8):
            name=str(i)+'f'*79;b['families'].append({'name':name})
            s['families'][name]={'status':'built','run':'a'*16,'calls':123456,'native_seconds':123.456789,'fit':[{'attempt_count':16,'requests_used':128,'selected_actual_shift_m':{'source':-123.456789,'target':123.456789}}]*4}
        b['checks']=[{'name':str(i)+'c'*78} for i in range(32)]
        out=approach.summary('a'*16,b,s)
        out.update(check_results=[{'name':c['name'],'passed':False} for c in b['checks'][:8]])
        self.assertLess(len(json.dumps(out).encode()),4096)

    def test_negative_route_requires_explicit_native_absence_not_failed_required_path(self):
        cases=[({'requested_route_verified':False,'native_path_found':True,'reason':'required_edges_missing','truncated':False},False),
               ({'requested_route_verified':False,'native_path_found':True,'reason':'path_truncated','truncated':True},False),
               ({'requested_route_verified':False},False),
               ({'requested_route_verified':False,'native_path_found':False,'reason':'no_native_path_returned'},True)]
        for value,expected in cases:
            with self.subTest(value=value),tempfile.TemporaryDirectory() as td:
                c=World(td);o=Operator(runs=td,client=c);b=brief()
                b['checks']=[{'name':'reverse_blocked','kind':'route','families':['seed'],'shared_effects':[],
                    'bindings':{'road':'seed.road'},'payload':{'source':{'binding':'road','end':'node1'},'target':{'binding':'road','end':'node0'},
                        'required_bindings':['road'],'mode':'TRAIN','max_length':1000,'expected':False}}]
                run=o.plan_approach(b)['run'];o.build_approach(run)
                with patch('bridge_approach.live.route',return_value={'status':'ok','result':value}):result=o.review_approach(run)
                self.assertEqual(result['check_results'],[{'name':'reverse_blocked','passed':expected}])

    def route_check(self,name='forward'):
        return {'name':name,'kind':'route','families':['seed'],'shared_effects':[], 'bindings':{'road':'seed.road'},
            'payload':{'source':{'binding':'road','end':'node0'},'target':{'binding':'road','end':'node1'},'required_bindings':['road'],'mode':'TRAIN','max_length':1000}}

    def test_cached_route_dependencies_refresh_once_without_unchanged_route_calls(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();b['checks']=[self.route_check(),self.route_check('second')]
            run=o.plan_approach(b)['run'];o.build_approach(run)
            value={'status':'ok','result':{'requested_route_verified':True,'path_count':1,'truncated':False}}
            with patch('bridge_approach.live.route',return_value=value) as route:
                self.assertEqual(o.review_approach(run)['status'],'reviewed');self.assertEqual(route.call_count,2)
                calls=len(c.calls);out=o.review_approach(run)
                self.assertEqual(out['checks_run'],0);self.assertEqual(route.call_count,2)
            observed=[op for op,_ in c.calls[calls:]]
            self.assertEqual(observed.count('inspect'),1);self.assertEqual(observed.count('operating_inspect'),1);self.assertEqual(observed.count('discover'),0)

    def test_legacy_benchmark_incidence_witness_can_be_another_edge_at_the_same_exact_native_node(self):
        from bridge_dependency_benchmark import LegacyDependencies
        for problem in (None,'different_node','missing_edge','truncated','conflicting'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                c=World(td);row=c.make_edge([0,0,2],[20,0,2],[20,0,0],[20,0,0]);original=c.request
                def request(op,q,**kw):
                    r=original(op,q,**kw)
                    if op=='discover':
                        witness=r['result']['candidates'][0];witness['edge_id']=99;witness['eligible']=False
                        witness['incident_edges']=[row['id'],99];witness['incident_count']=2
                        if problem=='different_node':witness['node_id']=500
                        elif problem=='missing_edge':witness.update(incident_edges=[99],incident_count=1)
                        elif problem=='truncated':witness['incident_output_truncated']=True
                        elif problem=='conflicting':r['result']['candidates'].append(witness|{'incident_edges':[row['id'],100]})
                    return r
                deps=LegacyDependencies(c)
                with patch.object(c,'request',side_effect=request):
                    if problem:
                        with self.assertRaises(ValueError):deps.observe_semantics([row['id']])
                    else:
                        deps.observe_semantics([row['id']]);self.assertEqual(deps.nodes[row['node1']]['incident_edges'],[row['id'],99])

    def test_changed_cached_geometry_signal_revision_or_incidence_requires_reconciliation(self):
        for change in ('geometry','signal','revision','incidence'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                c=World(td);o=Operator(runs=td,client=c);b=brief();b['checks'].append(self.route_check());run=o.plan_approach(b)['run'];o.build_approach(run)
                value={'status':'ok','result':{'requested_route_verified':True,'path_count':1,'truncated':False}}
                with patch('bridge_approach.live.route',return_value=value) as route:
                    self.assertEqual(o.review_approach(run)['status'],'reviewed')
                    if change=='geometry':c.edges[1]['p1'][2]+=1
                    elif change=='signal':c.objects[1]=[{'id':80,'signal':{'one_way':True,'forward':False}}]
                    elif change=='revision':c.revisions[1]=[2,0,0]
                    else:c.extra_incidence[c.edges[1]['node1']]=[99]
                    out=o.review_approach(run);self.assertEqual(out['status'],'needs_attention');self.assertEqual(out['checks_run'],0);self.assertEqual(route.call_count,1)
                state=approach.load(o.path(run)/'state.json');self.assertFalse(state['checks']['forward']['valid'])
                self.assertEqual(state['checks']['alignment']['valid'],change!='geometry')

    def test_unaliased_exported_family_rail_changes_invalidate_positive_and_negative_proofs(self):
        for change in ('signal','revision','incidence','owner'):
            for negative in (False,True):
                with self.subTest(change=change,negative=negative),tempfile.TemporaryDirectory() as td:
                    c=World(td);o=Operator(runs=td,client=c);b=brief();f=b['families'][0]
                    f['payload']['ports']['b']={'position':[20,0,0],'direction':[1,0]}
                    f['payload']['steps'].append({'name':'shared_fan','kind':'stub','port':'b','length':20});f['exports']['shared_fan']='shared_fan'
                    check=self.route_check();check['payload']['expected']=not negative;b['checks']=[check]
                    run=o.plan_approach(b)['run'];o.build_approach(run)
                    value={'status':'ok','result':{'requested_route_verified':False,'native_path_found':False,'reason':'no_native_path_returned'}} if negative else {'status':'ok','result':{'requested_route_verified':True,'path_count':1,'truncated':False}}
                    with patch('bridge_approach.live.route',return_value=value) as route:
                        self.assertEqual(o.review_approach(run)['status'],'reviewed');self.assertEqual(o.review_approach(run)['checks_run'],0)
                        proof=approach.load(o.path(run)/'state.json')['checks']['forward'];self.assertIn('2',proof['dependencies']['geometry'])
                        if change=='signal':c.objects[2]=[{'id':80,'signal':{'one_way':True,'forward':False}}]
                        elif change=='revision':c.revisions[2]=[2,0,0]
                        elif change=='owner':c.node_owners[c.edges[2]['node1']]=42
                        else:c.extra_incidence[c.edges[2]['node1']]=[99]
                        out=o.review_approach(run);self.assertEqual(out['status'],'needs_attention');self.assertEqual(out['checks_run'],0);self.assertEqual(route.call_count,1)

    def test_cached_station_identity_change_invalidates_station_route_proof(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();selector=b['station']
            o.interfaces().path('station_roles').write_text(json.dumps({'revision':'R1','roles':{'P1':{'station':selector}}}))
            b['checks']=[{'name':'arrival','kind':'station_routes','families':['seed'],'shared_effects':[],'bindings':{'road':'seed.road'},
                'payload':{'name':'station_roles','revision':'R1','routes':[{'name':'arrival','purpose':'arrival','source':{},'target':{'role':'P1'},'required_bindings':['road'],'max_length':1000}]}}]
            run=o.plan_approach(b)['run'];o.build_approach(run)
            with patch.object(o,'review_station_routes',return_value={'status':'ok','routes':[]}) as route:
                self.assertEqual(o.review_approach(run)['status'],'reviewed');self.assertEqual(o.review_approach(run)['checks_run'],0)
                c.station_revision=2;out=o.review_approach(run)
                self.assertEqual(out['status'],'needs_attention');self.assertEqual(route.call_count,1)
                self.assertEqual(out['changed_dependencies'],['arrival'])

    def test_actual_station_route_endpoint_outside_aliases_is_a_cached_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();selector=b['station']
            o.interfaces().path('station_roles').write_text(json.dumps({'revision':'R1','roles':{'P1':{'station':selector}}}))
            b['checks']=[{'name':'arrival','kind':'station_routes','families':['seed'],'shared_effects':[],'bindings':{'road':'seed.road'},
                'payload':{'name':'station_roles','revision':'R1','routes':[{'name':'arrival','purpose':'arrival','source':{},'target':{'role':'P1'},'max_length':1000}]}}]
            run=o.plan_approach(b)['run'];o.build_approach(run);external=c.make_edge([20,0,2],[40,0,2],[20,0,0],[20,0,0])
            with patch.object(o,'review_station_routes',return_value={'status':'ok','routes':[{'source':{'edge':external['id']},'target':{'edge':1}}]}) as route:
                self.assertEqual(o.review_approach(run)['status'],'reviewed');self.assertEqual(o.review_approach(run)['checks_run'],0)
                self.assertTrue(any(op=='inspect' and q.get('incidence_edge_ids')==[external['id']] for op,q in c.calls))
                external['t1'][1]=1
                self.assertEqual(o.review_approach(run)['status'],'needs_attention');self.assertEqual(route.call_count,1)

    def test_verified_signal_mapping_preserves_cached_geometry_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();run=o.plan_approach(b)['run'];o.build_approach(run);o.review_approach(run)
            path=o.path(run)/'state.json';s=approach.load(path);row=copy.deepcopy(c.edges.pop(1));row['id']=9;c.edges[9]=row
            approach.propagate(b,s,{'bindings':{'road':{'edges':[row]}},'lineage':[{'original_edge':1,'replacement_edges':[9]}]},True);live.atomic_json(path,s)
            self.assertEqual(o.review_approach(run)['checks_run'],0)
            self.assertEqual(approach.load(path)['status'],'reviewed')

    def test_changed_criteria_cannot_reuse_previous_proof(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);run=o.plan_approach(brief())['run'];o.build_approach(run);o.review_approach(run)
            path=o.path(run)/'approach.json';b=approach.load(path);b['checks'][0]['payload']['max_grade']=0;path.write_text(json.dumps(b))
            with self.assertRaisesRegex(ValueError,'brief changed'):o.review_approach(run)

    def test_sampled_grade_uses_vertical_native_derivative(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);o=Operator(runs=td,client=c);b=brief();run=o.plan_approach(b)['run'];o.build_approach(run)
            state=approach.load(o.path(run)/'state.json');row=state['bindings']['seed.road']['edges'][0];row['t0'][2]=10;c.edges[1]=copy.deepcopy(row)
            live.atomic_json(o.path(run)/'state.json',state)
            self.assertEqual(o.review_approach(run)['check_results'],[{'name':'alignment','passed':False}])


class RequiredRoadTests(unittest.TestCase):
    def test_station_endpoint_path_cannot_prove_new_required_interior_road(self):
        with tempfile.TemporaryDirectory() as td:
            helper=test_operator.OperatorTest();client,o,v,edge,b,queries,original=helper.station_route_fixture(td)
            interior=copy.deepcopy(edge);interior['id']=9;b['bindings']={'crossover':{'edges':[interior]}}
            for route in b['routes']:route['required_bindings']=['crossover']
            def request(op,q,**kw):
                if op=='inspect' and q['edge_ids']==[9]:
                    queries.append((op,q));return {'status':'ok','request_id':'interior','result':{'edges':[interior]}}
                r=original(op,q,**kw)
                if op=='route':r['result']['requested_route_verified']=9 not in q['required_edges']
                return r
            with patch.object(client,'request',side_effect=request),patch('bridge_station_routes.live._select_throat_port',return_value=({'edge_id':8,'node_id':17},'free')):
                result=o.review_station_routes(b)
            self.assertEqual(result['status'],'routes_unverified')
            self.assertTrue(all(9 in q['required_edges'] for op,q in queries if op=='route'))
            self.assertEqual(sum(op=='inspect' and q['edge_ids']==[9] for op,q in queries),1)

    def test_missing_required_binding_rejected_before_queries(self):
        with tempfile.TemporaryDirectory() as td:
            helper=test_operator.OperatorTest();c,o,v,e,b,queries,request=helper.station_route_fixture(td);b['routes'][0]['required_bindings']=['missing']
            with self.assertRaisesRegex(ValueError,'bindings unavailable'):o.review_station_routes(b)
            self.assertEqual(c.calls,[])
