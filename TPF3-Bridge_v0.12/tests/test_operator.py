import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from bridge_live import LiveError
from bridge_interfaces import InterfaceRegistry, diagnose
from bridge_operator_tasks import perform, references
from bridge_operator import Operator, validate_plan, cubic, native_failure, inspect_edges, fresh_binding, discover_region, chain_point, crossing_observations, render_profile, replacement_boundary, check_plain_coalescing
from tools.operator_mcp_client import semantic_result, compact_stdout


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
    def station_exit_fixture(self):
        v,c,roles,request=self.role_fixture()
        v['ports']={}
        v['constructions'][0]['frozen_tracks']=[{'edge_id':1,'node0':2,'node1':3}]
        v['stations'][0].update(construction_id=5,terminals=[{'index':1,'vehicle_edges':[1]}])
        c.update(eligible=False,construction_owner=5)
        roles['MW_up']['mode']='station_exit'
        return v,c,roles,request

    def test_owned_station_exit_resolves_without_external_leads_and_extends_exact_node(self):
        with tempfile.TemporaryDirectory() as td:
            client=FakeClient();o=Operator(runs=td,client=client);v,c,roles,request=self.station_exit_fixture()
            p=self.grade_plan();p['ports'].pop('a')
            p.update(role_refs={'mw':'MW_up'},interface_registry='district',interface_revision='R1')
            p['steps']=[{'name':'lead','kind':'extend','source':'mw','target':'b'}]
            with patch.object(client,'request',side_effect=request),patch('bridge_operator.live._select_throat_port') as generic,patch('bridge_operator.live.extend',return_value={'status':'ok','result':{'edges':[]}}) as extend:
                o.register_interfaces('district','R1',roles)
                resolved=o.interfaces().resolve(client,'district','R1')['resolved']['MW_up']
                self.assertEqual(resolved['operating_terminal'],{'station_group':7,'station':0,'terminal':0})
                self.assertEqual(resolved['associations'][0]['native_TRAIN_route'],'unprobed')
                self.assertEqual(o.execute(o.plan(p)['run'])['status'],'built')
            generic.assert_not_called()
            self.assertEqual((extend.call_args.args[1]['anchor_edge'],extend.call_args.args[1]['anchor_node']),(1,3))

    def test_station_exit_requires_exact_frozen_incidence_not_nearby_geometry(self):
        for problem in ('identity','external','terminal','owned_free'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                client=FakeClient();v,c,roles,request=self.station_exit_fixture()
                if problem=='identity':v['constructions'][0]['frozen_tracks'][0]['edge_id']=77
                elif problem=='external':c.update(incident_count=2,incident_edges=[1,77])
                elif problem=='terminal':v['stations'][0]['terminals'][0]['vehicle_edges']=[77]
                else:roles['MW_up']['mode']='free'
                with patch.object(client,'request',side_effect=request),self.assertRaises(LiveError):
                    InterfaceRegistry(td).register(client,'district','R1',roles)

    def test_terminal_node_identity_qualifies_frozen_exit_and_external_lead(self):
        for mode in ('station_exit','free'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                client=FakeClient();v,c,roles,request=self.station_exit_fixture()
                v['stations'][0]['terminals']=[{'index':1,'vehicle_edges':{},'vehicle_node':{'entity':2,'index':0}}]
                if mode=='free':
                    c.update(eligible=True,construction_owner='none')
                    v['ports']=[c|{'association':{'construction_id':5,'frozen_edge':1,'edge_ids':[1],'terminal_identity_matches':{}}}]
                    roles['MW_up']['mode']='free'
                with patch.object(client,'request',side_effect=request):
                    registry=InterfaceRegistry(td);registry.register(client,'district','R1',roles)
                    self.assertEqual(registry.resolve(client,'district','R1')['resolved']['MW_up']['operating_terminal']['terminal'],0)
                    v['stations'][0]['terminals'][0]['vehicle_node']['entity']=77
                    with self.assertRaises(LiveError):registry.resolve(client,'district','R1')

    def station_route_fixture(self,td):
        client=FakeClient();client.evidence=Path(td);o=Operator(runs=td,client=client)
        v,c,roles,_=self.station_exit_fixture();edge=self.native_edge()
        v.update(lookup_scope='identity_frozen',identity_complete=True,frozen_complete=True,external_complete=False,external_observation='not_requested')
        v['stations'][0]['terminals']=[{'index':1,'vehicle_edges':{},'vehicle_node':{'entity':2,'index':0}}]
        o.interfaces().path('district').write_text(json.dumps({'name':'district','revision':'R1','roles':roles}))
        terminal={'role':'MW_up','guide_xyz':edge['p0'],'travel_direction':[-1,0]}
        boundary={'guide_xyz':[200,0,2],'travel_direction':[-1,0]}
        brief={'name':'district','revision':'R1','routes':[{'name':'arrival','purpose':'arrival','source':boundary,'target':terminal,'max_length':1000},
            {'name':'departure','purpose':'departure','source':terminal|{'travel_direction':[1,0]},'target':boundary|{'travel_direction':[1,0]},'max_length':1000}]}
        queries=[]
        def request(op,q,**kwargs):
            queries.append((op,q))
            if op=='station_lookup':self.assertEqual(q['lookup_scope'],'identity_frozen')
            result=v if op=='station_lookup' else {'edges':[edge]} if op=='inspect' else {'requested_route_verified':True,'total_path_length':200,'path_count':130,'truncated':False,'max_path_entries':q['max_path_entries']}
            return {'status':'ok','request_id':op,'result':copy.deepcopy(result)}
        return client,o,v,edge,brief,queries,request

    def test_station_route_reviews_connected_owned_chain_with_explicit_arrival_and_departure(self):
        with tempfile.TemporaryDirectory() as td:
            client,o,v,edge,brief,queries,request=self.station_route_fixture(td)
            # Stored station_exit is no longer a buildable free port. Terminal
            # review requalifies the frozen chain, without resolving that role.
            v['ports']=[{'node_id':3,'incident_count':2}]
            with patch.object(client,'request',side_effect=request),patch('bridge_station_routes.live._select_throat_port',return_value=({'edge_id':8,'node_id':17},'free')) as boundary:
                result=o.review_station_routes(brief)
            self.assertEqual(result['status'],'ok');self.assertEqual(boundary.call_count,2)
            route=[q for op,q in queries if op=='route']
            self.assertEqual((route[0]['source_edge'],route[0]['target_edge'],route[0]['target_node']),(8,1,2))
            self.assertEqual((route[1]['source_edge'],route[1]['source_node'],route[1]['target_edge']),(1,2,8))
            self.assertTrue(all(q['max_path_entries']==256 for q in route))
            self.assertEqual([r['purpose'] for r in result['routes']],['arrival','departure'])
            self.assertEqual(result['line_operation'],'unprobed');self.assertFalse(result['game_constructed'])
            self.assertTrue(all(op in ('station_lookup','inspect','route') for op,_ in queries))

    def test_station_routes_use_distinct_endpoint_registries_and_reuse_station_survey(self):
        with tempfile.TemporaryDirectory() as td:
            client,o,v,edge,brief,queries,request=self.station_route_fixture(td)
            record=o.interfaces().load('district')
            other_edge=self.native_edge(11,200,300)
            v['constructions'].append({'construction_id':15,'resource':'station','position':[200,0,2],
                                       'frozen_tracks':[{'edge_id':11,'node0':22,'node1':23}]})
            v['stations'].append({'station_id':19,'construction_id':15,'terminals':[
                {'index':1,'vehicle_edges':{},'vehicle_node':{'entity':22,'index':0}}]})
            other_role=copy.deepcopy(record['roles']['MW_up'])
            other_role['station']['construction']['position']=[200,0,2]
            o.interfaces().path('outer').write_text(json.dumps({'name':'outer','revision':'R3','roles':{'other_terminal':other_role}}))
            source={'role':'MW_up','guide_xyz':edge['p0'],'travel_direction':[1,0]}
            target=source|{'role':'other_terminal','registry_name':'outer','registry_revision':'R3','guide_xyz':other_edge['p0'],'travel_direction':[-1,0]}
            brief['routes']=[{'name':'station_pair','purpose':'arrival','source':source,'target':target,'max_length':1000},
                             {'name':'repeat','purpose':'departure','source':source,'target':target,'max_length':1000}]
            def current_request(op,q,**kwargs):
                response=request(op,q,**kwargs)
                if op=='inspect':response['result']['edges']=[edge if eid==1 else other_edge for eid in q['edge_ids']]
                return response
            with patch.object(client,'request',side_effect=current_request),patch.object(InterfaceRegistry,'load',autospec=True,side_effect=InterfaceRegistry.load) as loads,patch('bridge_station_routes.live._select_throat_port') as boundary:
                result=o.review_station_routes(brief)
            self.assertEqual(result['status'],'ok');boundary.assert_not_called()
            self.assertEqual([call.args[1] for call in loads.call_args_list],['district','outer'])
            self.assertEqual(sum(op=='station_lookup' for op,_ in queries),2) # one survey plus final freshness check
            row=result['routes'][0]
            self.assertEqual((row['source']['registry_name'],row['source']['registry_revision']),('district','R1'))
            self.assertEqual((row['target']['registry_name'],row['target']['registry_revision']),('outer','R3'))
            self.assertEqual(row['target']['qualification'],'exact_registered_terminal_frozen_TRACK_component')
            self.assertEqual((row['source']['edge'],row['target']['edge']),(1,11))

    def test_station_route_endpoint_registry_revision_mismatch_stops_before_route(self):
        for mismatch in ('other','cached_default','independent_default','free_endpoint'):
            with self.subTest(mismatch=mismatch),tempfile.TemporaryDirectory() as td:
                client,o,v,edge,brief,queries,request=self.station_route_fixture(td)
                record=o.interfaces().load('district')
                o.interfaces().path('outer').write_text(json.dumps(dict(record,name='outer',revision='R3')))
                if mismatch=='other':brief['routes'][0]['target'].update(registry_name='outer',registry_revision='R2')
                elif mismatch=='cached_default':brief['routes'][0]['target']['registry_revision']='R2'
                elif mismatch=='independent_default':brief['routes'][0]['target']['registry_name']='outer'
                else:brief['routes'][0]['source']['registry_name']='district'
                with patch.object(client,'request',side_effect=request),patch('bridge_station_routes.live._select_throat_port',return_value=({'edge_id':8,'node_id':17},'free')),self.assertRaises(ValueError):
                    o.review_station_routes(brief)
                self.assertFalse(any(op=='route' for op,_ in queries))

    def test_station_route_scope_and_path_bounds_do_not_promote_incomplete_records(self):
        for problem in ('frozen_incomplete','identity_incomplete','wrong_scope','path_overflow','path_unknown','reported_truncation'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                client,o,v,edge,brief,queries,request=self.station_route_fixture(td)
                if problem=='frozen_incomplete':v['frozen_complete']=False
                elif problem=='identity_incomplete':v['identity_complete']=False
                elif problem=='wrong_scope':v['lookup_scope']='external'
                def changed(op,q,**kwargs):
                    r=request(op,q,**kwargs)
                    if op=='route':
                        if problem=='path_overflow':r['result']['path_count']=257
                        elif problem=='path_unknown':r['result'].pop('path_count')
                        elif problem=='reported_truncation':r['result']['truncated']=True
                    return r
                with patch.object(client,'request',side_effect=changed),patch('bridge_station_routes.live._select_throat_port',return_value=({'edge_id':8,'node_id':17},'free')):
                    if problem in ('frozen_incomplete','identity_incomplete','wrong_scope'):
                        with self.assertRaises(LiveError):o.review_station_routes(brief)
                        self.assertFalse(any(op=='route' for op,_ in queries))
                    else:self.assertEqual(o.review_station_routes(brief)['status'],'routes_unverified')

    def test_external_role_does_not_accept_identity_only_scope(self):
        with tempfile.TemporaryDirectory() as td:
            client=FakeClient();v,c,roles,request=self.role_fixture()
            v.update(lookup_scope='identity_frozen',identity_complete=True,frozen_complete=True,external_complete=False)
            with patch.object(client,'request',side_effect=request),self.assertRaises(LiveError):InterfaceRegistry(td).register(client,'district','R1',roles)

    def test_station_routes_reject_missing_ambiguous_incomplete_or_wrong_direction_identity(self):
        for problem in ('missing_node','ambiguous','incomplete','wrong_direction','changed_endpoint','stale'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                client,o,v,edge,brief,queries,request=self.station_route_fixture(td)
                if problem=='missing_node':v['stations'][0]['terminals'][0]['vehicle_node']['entity']=77
                elif problem=='ambiguous':v['constructions'].append(copy.deepcopy(v['constructions'][0]))
                elif problem=='incomplete':v['complete']=False
                elif problem=='wrong_direction':brief['routes'][0]['target']['travel_direction']=[1,0]
                elif problem=='changed_endpoint':edge['node0']=77
                def changed(op,q,**kwargs):
                    r=request(op,q,**kwargs)
                    if problem=='stale' and op=='station_lookup' and sum(op=='station_lookup' for op,_ in queries)>1:r['result']['group_id']=99
                    return r
                with patch.object(client,'request',side_effect=changed),patch('bridge_station_routes.live._select_throat_port',return_value=({'edge_id':8,'node_id':17},'free')),self.assertRaises(LiveError):o.review_station_routes(brief)

    def test_station_exit_cannot_be_used_as_generic_connected_attachment(self):
        with tempfile.TemporaryDirectory() as td:
            client=FakeClient();o=Operator(runs=td,client=client);v,c,roles,request=self.station_exit_fixture()
            p=self.grade_plan();p['ports'].pop('a')
            p.update(role_refs={'mw':'MW_up'},interface_registry='district',interface_revision='R1')
            p['steps']=[{'name':'connect','kind':'connect','source':'mw','target':'b'}]
            with patch.object(client,'request',side_effect=request),patch('bridge_operator.live.connect') as build:
                o.register_interfaces('district','R1',roles)
                r=o.execute(o.plan(p)['run'])
            self.assertEqual(r['status'],'needs_attention');build.assert_not_called()

    def role_fixture(self):
        edge=self.native_edge();c={'edge_id':1,'node_id':3,'pos':edge['p1'],'outward_direction':[1,0,0],'grade':0,'edge_snapshot':edge,
            'eligible':True,'incident_count':1,'incident_edges':[1],'incidence_complete':True,'incident_output_truncated':False,'construction_owner':'none','ref':'request-scoped'}
        assoc={'construction_id':5,'frozen_edge':99,'edge_ids':[1],
               'terminal_identity_matches':[{'station_id':9,'terminal_index':1,'vehicle_edge':99}]}
        v={'outcome':'resolved','complete':True,'group_id':7,'constructions':[{'construction_id':5,'resource':'station','position':[0,0,2]}],
           'stations':[{'station_id':9}],'ports':[c|{'association':assoc}]}
        intent={'region':{'min':[99,-1,1],'max':[101,1,3]},'guide_xyz':[100,0,2],'travel_direction':[1,0]}
        roles={'MW_up':{'station':{'name':'Mid West C','construction':{'resource':'station','position':[0,0,2]},'terminal_index':1},'intent':intent,'mode':'free'}}
        def request(op,q,**kwargs):
            return {'status':'ok','request_id':op,'result':copy.deepcopy(v) if op=='station_lookup' else {'complete':True,'candidates':[copy.deepcopy(c)],'edges':[edge]}}
        return v,c,roles,request

    def test_registry_reacquires_station_identity_and_preserves_old_revision(self):
        with tempfile.TemporaryDirectory() as td:
            registry=InterfaceRegistry(td);client=FakeClient();v,c,roles,request=self.role_fixture()
            with patch.object(client,'request',side_effect=request):
                registry.register(client,'district','R1',roles);first=registry.resolve(client,'district','R1')
                self.assertEqual(first['resolved']['MW_up']['operating_terminal'],{'station_group':7,'station':0,'terminal':0})
                client.session='loaded_again';v['group_id']=17;v['constructions'][0]['construction_id']=15
                v['ports'][0]['association']['construction_id']=15
                second=registry.resolve(client,'district','R1')
                self.assertEqual(second['resolved']['MW_up']['group_id'],17);self.assertEqual(second['resolved']['MW_up']['session'],'loaded_again')
                registry.register(client,'district','R2',roles)
                with self.assertRaisesRegex(ValueError,'revision changed'):registry.resolve(client,'district','R1')
            self.assertEqual(len(list(Path(td).glob('*.previous.json'))),1)

    def test_registry_refuses_geometry_without_station_chain_and_ambiguous_terminals(self):
        for problem in ['chain','duplicates','incomplete','terminal','construction']:
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                registry=InterfaceRegistry(td);client=FakeClient();v,c,roles,request=self.role_fixture()
                if problem=='chain':v['ports'][0]['edge_id']=55
                elif problem=='terminal':v['ports'][0]['association']['terminal_identity_matches']=[]
                elif problem=='construction':v['constructions'].append(copy.deepcopy(v['constructions'][0]))
                elif problem=='incomplete':v['complete']=False
                def queried(op,q,**kwargs):
                    r=request(op,q,**kwargs)
                    if problem=='duplicates' and op=='discover':r['result']['candidates']*=2
                    return r
                with patch.object(client,'request',side_effect=queried),self.assertRaises(LiveError):registry.register(client,'district','R1',roles)
                self.assertFalse(registry.path('district').exists())

    def test_named_role_plan_revalidates_before_effects_and_ignores_request_refs(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);v,port,roles,request=self.role_fixture()
            p=self.grade_plan();p['ports'].pop('a');p.update(role_refs={'mw':'MW_up'},interface_registry='district',interface_revision='R1')
            p['steps']=[{'name':'extend_lead','kind':'stub','port':'mw','length':20}]
            with patch.object(c,'request',side_effect=request):
                o.register_interfaces('district','R1',roles);run=o.plan(p)['run'];port['ref']='another-request'
                self.assertEqual(o.execute(run)['status'],'built')
                run=o.plan(p)['run'];v['ports'][0]['association']['terminal_identity_matches']=[]
                result=o.execute(run)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['completed_steps'],0)
            self.assertIsNone(json.loads((o.path(run)/'state.json').read_text()).get('step_mutation'))

    def test_attachment_diagnostics_separate_adapter_exclusion_and_no_native_proposal(self):
        c=FakeClient();v,port,roles,_=self.role_fixture();port.update(eligible=False,incident_count=3,construction_owner=5,outward_direction=[-1,0,0])
        with patch.object(c,'request',return_value={'status':'ok','request_id':'diagnostic','result':{'complete':True,'candidates':[port]}}):
            r=diagnose(c,roles['MW_up']['intent'])
        reasons=r['candidates'][0]['reasons'];self.assertIn('construction_owned',reasons);self.assertIn('direction_mismatch',reasons)
        self.assertIn('connected_endpoint_unsupported',reasons);self.assertFalse(r['native_proposal_evaluated'])
        with patch.object(c,'request',return_value={'status':'ok','result':{'complete':False}}):self.assertEqual(diagnose(c,roles['MW_up']['intent'])['status'],'incomplete')

    def test_operating_steps_use_exact_named_purchase_result_and_fresh_revision(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[{'name':'buy','kind':'operating','brief':{'action':'vehicle_buy','depot_id':50,'revision':[1,2,3],'parts':[{'resource':'native.train','reversed':False}]}},
                {'name':'stop','kind':'operating','brief':{'action':'vehicle_stop','vehicle_id':{'result':'buy','path':['vehicle','id']},'value':True}}]
            responses=[{'status':'ok','request_id':'prepare','result':{}},
                {'status':'ok','request_id':'buy','result':{'vehicle':{'id':60},'game_constructed':False,'native_operating_state_changed':True}},
                {'status':'ok','request_id':'read','result':{'vehicles':{'records':[{'id':60,'revision':[2,3,4]}]}}},
                {'status':'ok','request_id':'stop','result':{'vehicle':{'id':60,'user_stopped':True},'game_constructed':False,'native_operating_state_changed':True}}]
            with patch.object(c,'request',side_effect=responses) as request:
                run=o.plan(p)['run'];r=o.execute(run)
            self.assertEqual(r['status'],'built');self.assertEqual(request.call_args_list[-1].args[1]['revision'],[2,3,4])
            self.assertEqual(request.call_args_list[-1].args[1]['vehicle_id'],60)
            self.assertEqual(json.loads((o.path(run)/'state.json').read_text())['steps']['stop']['result']['vehicle']['id'],60)

    def test_operating_unknown_effects_cannot_be_treated_as_harmless_geometry_failure(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan();p['steps']=[{'name':'service','kind':'operating','brief':{'action':'line_create','name':'test','stops':[{'station_group':1,'station':0,'terminal':0},{'station_group':2,'station':0,'terminal':0}]}}]
            with patch.object(c,'request',return_value={'status':'error','request_id':'failed','result':{'game_constructed':False,'operating_effects':'unknown','error':'lost_ack'}}):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'needs_attention')
            with self.assertRaisesRegex(ValueError,'uncertain/partial'):o.continue_plan(run,'R2')
            with self.assertRaisesRegex(ValueError,'uncertain/partial'):o.review(run)

    def test_observation_is_one_bounded_read_and_not_a_physical_traversal_claim(self):
        c=FakeClient()
        with patch.object(c,'request',return_value={'status':'ok','result':{'vehicles':{'records':[{'id':1,'speed':0,'no_path':False}]}}}) as request:
            perform(c,'observe',{'vehicle_ids':[1]})
        self.assertEqual(request.call_args.args,('operating_inspect',{'vehicle_ids':[1]}))
        with self.assertRaises(ValueError):perform(c,'observe',{'vehicle_ids':list(range(1,18))})
        with self.assertRaises(ValueError):references({'result':'x','path':['vehicle']*9},{'x':{}},{})

    def test_operating_only_role_plan_does_not_resolve_unrelated_roles(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);v,port,roles,request=self.role_fixture()
            roles['unused']=copy.deepcopy(roles['MW_up']);roles['unused']['station']['name']='Not In This Task'
            p=self.grade_plan();p.update(interface_registry='district',interface_revision='R1')
            p['steps']=[{'name':'inspect','kind':'observe','brief':{'track_ids':[{'role':'MW_up','field':'edge_id'}]}}]
            registry={'version':1,'name':'district','revision':'R1','roles':roles}
            o.interfaces().path('district').write_text(json.dumps(registry))
            calls=[]
            def observed(op,q,**kwargs):
                calls.append((op,q))
                if op=='station_lookup':self.assertEqual(q['name'],'Mid West C')
                return request(op,q,**kwargs)
            with patch.object(c,'request',side_effect=observed):run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'built')
            self.assertEqual(calls[-1],('operating_inspect',{'track_ids':[1]}))

    def test_forward_operating_result_reference_fails_before_any_native_effect(self):
        p=self.grade_plan();p['steps']=[{'name':'observe','kind':'observe','brief':{'vehicle_ids':[{'result':'future','path':['vehicle','id']}]}}]
        with self.assertRaisesRegex(ValueError,'earlier task'):validate_plan(p)

    def test_signal_receipt_updates_prior_exact_chain_identity(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps'].append({'name':'signal','kind':'signal','brief':{'edge_id':1,'parameter':.5,'forward':True,'one_way':True}})
            replacement=self.native_edge(2)
            replies=[{'status':'ok','request_id':'seed','result':{'game_constructed':True,'edges':[self.native_edge(1)]}},
                {'status':'ok','request_id':'signal','result':{'game_constructed':True,'replaced_edge':1,'replacement_edge':2}},
                {'status':'ok','request_id':'read','result':{'edges':[replacement]}}]
            with patch.object(c,'request',side_effect=replies),patch('bridge_operator.tasks.perform',side_effect=lambda client,*_:client.request('operating_control',{})):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'built')
            state=json.loads((o.path(run)/'state.json').read_text());self.assertEqual(state['steps']['one']['edges'][0]['id'],2)
            self.assertEqual(state['lineage'][0]['original_edge'],1);self.assertEqual(state['lineage'][0]['replacement_edges'],[2])

    def seed_plan(self):
        p=self.grade_plan();p['ports']['a']['grade']=0;p['ports']['a']['direction']=[-1,0]
        p['ports']['b']['direction']=[1,0]
        p['steps']=[{'name':'deck','kind':'structure_seed','source':'a','target':'b',
                     'structure':{'classification':'BRIDGE','resource_name':'observed.bridge'}}]
        return p

    def test_standalone_bridge_uses_one_native_proposal_without_stub_or_discovery(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.seed_plan();p['ports']['a']['grade']=-.02;p['ports']['b']['grade']=.03
            edge=self.native_edge()
            responses=[{'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                       {'status':'ok','request_id':'built','result':{'game_constructed':True,'ordered_edges':[1]}},
                       {'status':'ok','request_id':'read','result':{'edges':[edge]}}]
            with patch.object(c,'request',side_effect=responses) as request,patch('bridge_operator.live._select_throat_port') as select:
                run=o.plan(p)['run'];result=o.execute(run)
            self.assertEqual(result['status'],'built');select.assert_not_called()
            calls=request.call_args_list;self.assertEqual([x.args[0] for x in calls],['structured_chain','structured_chain','inspect'])
            q=calls[0].args[1];self.assertTrue(q['freestanding']);self.assertEqual(q['guides'],[])
            self.assertEqual(q['source'],{'position':[0,0,2],'travel_direction':[1,0],'grade':.02})
            self.assertEqual(q['target'],{'position':[100,0,12],'travel_direction':[1,0],'grade':.03})
            self.assertEqual(q['structures'],[p['steps'][0]['structure']]);self.assertEqual(q['track'],p['track'])
            self.assertEqual(calls[1].args[1],{'execute':True,'prepared_request':'prepared'})
            self.assertEqual(json.loads((o.path(run)/'state.json').read_text())['steps']['deck']['edges'],[edge])

    def test_standalone_rejection_never_executes_or_hides_uncertain_readback(self):
        for failure in ['prepare','readback']:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as td:
                c=FakeClient();o=Operator(runs=td,client=c)
                if failure=='prepare':responses=[{'status':'no_accepted_candidate','request_id':'rejected','result':{'game_constructed':False,'evaluation':{'messages':['Too Much Incline']}}}]
                else:responses=[{'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                    {'status':'ok','request_id':'built','result':{'game_constructed':True,'ordered_edges':[1]}},
                    {'status':'error','request_id':'read','result':{'game_constructed':False,'error':'unavailable'}}]
                with patch.object(c,'request',side_effect=responses) as request:
                    run=o.plan(self.seed_plan())['run'];result=o.execute(run)
                self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['completed_steps'],0)
                state=json.loads((o.path(run)/'state.json').read_text())
                if failure=='prepare':
                    self.assertEqual(len(request.call_args_list),1);self.assertIsNone(state['step_mutation']);self.assertIn('Too Much Incline',result['error'])
                else:
                    self.assertTrue(state['step_mutation']['game_constructed'])
                    with self.assertRaisesRegex(ValueError,'uncertain/partial'):o.continue_plan(run,'R2')

    def test_standalone_bridge_rejects_implicit_grades_or_attached_variants(self):
        changes=[lambda p:p['ports']['a'].pop('grade'),lambda p:p['steps'][0].update(source={'curve':'older','u':.5}),
                 lambda p:p['steps'][0].update(guides=[]),lambda p:p['steps'][0]['structure'].update(resource_name=''),
                 lambda p:p.update(version=1),lambda p:p['steps'][0].update(handle_scale=0)]
        for change in changes:
            with self.subTest(change=change):
                p=self.seed_plan();change(p)
                with self.assertRaises(ValueError):validate_plan(p)

    def grade_plan(self):
        p=fixture();p.update(version=2,max_grade=.18)
        p['region']={'min':[-10,-10,-5],'max':[600,30,30]}
        p['ports']['b']={'position':[100,0,10],'direction':[-1,0],'grade':0}
        return p

    def native_edge(self,id=1,x0=0,x1=100,z=2):
        return {'id':id,'node0':id*2,'node1':id*2+1,'p0':[x0,0,z],'p1':[x1,0,z],
                't0':[x1-x0,0,0],'t1':[x1-x0,0,0],'template':'track','style':'style',
                'road_type':'TRACK','structure':{'classification':'NORMAL'}}

    def test_version2_grades_and_native_group_bounds_validate(self):
        p=self.grade_plan();p['ports']['a']['grade']=.02;p['steps'][0]['grade']=.02
        self.assertEqual(validate_plan(p)['version'],2)
        p['steps'][0]['grade']=.05
        with self.assertRaises(ValueError):validate_plan(p)
        p=self.grade_plan();p['steps']=[{'name':'pair','kind':'group','groups':[{'source':'a','target':'b'},{'source':'a','target':'b'}]}]
        validate_plan(p)
        p['steps'][0]['groups'][0]['source_interior']=True
        with self.assertRaises(ValueError):validate_plan(p)

    def test_graded_stub_and_extension_keep_absolute_height_and_signed_grade(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan();p['steps'][0]['grade']=.02
            self.assertEqual(o.execute(o.plan(p)['run'])['status'],'built')
            self.assertEqual(c.calls[0][1]['fixture']['grade'],.02)
            p=self.grade_plan();p['ports']['b']['grade']=-.03;p['steps']=[{'name':'extend','kind':'extend','source':'a','target':'b'}]
            def extend(_,q,**kwargs):
                self.assertEqual(q['vertical']['end_height'],12);self.assertEqual(q['vertical']['end_grade'],-.03)
                return {'status':'ok','result':{'edges':[]}}
            with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),patch('bridge_operator.live.extend',side_effect=extend):
                self.assertEqual(o.execute(o.plan(p)['run'])['status'],'built')

    def test_mixed_structure_alternatives_reuse_one_accepted_full_proposal(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[{'name':'flyover','kind':'connect','source':'a','target':'b','source_interior':True,
                         'guides':[{'position':[50,0,12],'travel_direction':[1,0],'grade':0}],
                         'structures':[{'classification':'BRIDGE','resource_name':'observed.bridge'},{'classification':'NORMAL'}],
                         'attachments':[{'source':'a','target':'b'},{'source':'a','target':'b'}],
                         'attachment_windows':{'source':p['region'],'target':p['region']}}]
            rejected={'status':'no_accepted_candidate','request_id':'rejected','result':{'game_constructed':False,'evaluation':{'messages':['Too Much Curvature']}}}
            accepted={'status':'ok','request_id':'accepted','result':{'game_constructed':False}}
            built={'status':'ok','request_id':'built','result':{'game_constructed':True,'edges':[]}}
            with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),patch.object(c,'request',side_effect=[rejected,accepted,built]) as requests:
                run=o.plan(p)['run'];result=o.execute(run)
            self.assertEqual(result['status'],'built')
            queries=[call.args[1] for call in requests.call_args_list]
            self.assertTrue(queries[0]['junctions']);self.assertEqual(queries[0]['guides'][0]['position'],[50,0,14])
            self.assertEqual(queries[-1],{'execute':True,'prepared_request':'accepted'})
            state=json.loads((o.path(run)/'state.json').read_text());self.assertIn('Too Much Curvature',state['candidates']['flyover'][0]['reason'])

    def test_group_build_chunked_exact_readback_preserves_all_members(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[{'name':'group','kind':'group','groups':[{'source':'a','target':'b'},{'source':'a','target':'b'}]}]
            ids=list(range(1,21));responses=[{'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                {'status':'ok','request_id':'built','result':{'game_constructed':True,'groups':[{'readback':{'ordered_edges':ids[:10]}},{'readback':{'ordered_edges':ids[10:]}}]}},
                {'status':'ok','request_id':'read1','result':{'edges':[self.native_edge(i) for i in ids[:16]]}},
                {'status':'ok','request_id':'read2','result':{'edges':[self.native_edge(i) for i in ids[16:]]}}]
            with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),patch.object(c,'request',side_effect=responses):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'built')
            self.assertEqual(len(json.loads((o.path(run)/'state.json').read_text())['steps']['group']['edges']),20)

    def test_adaptive_survey_reports_complete_only_after_subdivision(self):
        c=FakeClient();region={'min':[0,0,0],'max':[600,20,30]}
        responses=[{'status':'ok','request_id':'dense','result':{'complete':False,'edges':[]}}]+[
            {'status':'ok','request_id':'read','result':{'complete':True,'edges':[self.native_edge()]}}]*3
        with patch.object(c,'request',side_effect=responses):rows,calls=discover_region(c,region)
        self.assertEqual(calls,4);self.assertEqual(len(rows),1)
        with patch.object(c,'request',return_value={'status':'ok','request_id':'dense','result':{'complete':False}}):
            with self.assertRaisesRegex(ValueError,'budget exhausted'):discover_region(c,region,max_queries=1)

    def test_multi_edge_reference_and_stale_binding_are_honest(self):
        rows=[self.native_edge(1,0,20),self.native_edge(2,20,100)]
        rows[1]['node0']=rows[0]['node1']
        point,direction=chain_point(rows,.5);self.assertAlmostEqual(point[0],50);self.assertEqual(direction,[1,0])
        self.assertAlmostEqual(chain_point(rows,.5,segment=1)[0][0],10)
        c=FakeClient();changed=copy.deepcopy(rows);changed[0]['p0'][0]=1
        with patch.object(c,'request',return_value={'status':'ok','request_id':'read','result':{'edges':changed}}):
            with self.assertRaisesRegex(ValueError,'binding changed'):fresh_binding(c,{'edges':rows})

    def test_continuation_generates_remaining_only_and_rechecks_parent_bindings(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan();p['steps'].append({**p['steps'][0],'name':'two'})
            edge=self.native_edge()
            responses=[{'status':'ok','request_id':'one','result':{'game_constructed':True,'edges':[edge]}},
                       {'status':'error','request_id':'two','result':{'game_constructed':False,'error':'rejected'}}]
            with patch.object(c,'request',side_effect=responses):
                original=o.plan(p)['run'];self.assertEqual(o.execute(original)['status'],'needs_attention')
            read={'status':'ok','request_id':'read','result':{'game_constructed':False,'edges':[edge]}}
            with patch.object(c,'request',return_value=read):next_run=o.continue_plan(original,'R2')['run']
            new=json.loads((o.path(next_run)/'plan.json').read_text());self.assertEqual([s['name'] for s in new['steps']],['two'])
            self.assertEqual(new['continuation']['skipped_steps'],['one'])
            with patch.object(c,'request',side_effect=[read,{'status':'ok','request_id':'remaining','result':{'game_constructed':True,'edges':[]}}]) as request:
                self.assertEqual(o.execute(next_run)['status'],'built')
            self.assertEqual([call.args[0] for call in request.call_args_list],['inspect','test_approach'])
            with self.assertRaises(ValueError):o.execute(original)

    def test_uncertain_effect_not_erased_by_later_read_failure(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[{'name':'join','kind':'connect','source':'a','target':'b'}]
            responses=[{'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                       {'status':'ok','request_id':'applied','result':{'game_constructed':True,'ordered_edges':[1]}},
                       {'status':'error','request_id':'read','result':{'game_constructed':False,'error':'read unavailable'}}]
            with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),patch.object(c,'request',side_effect=responses):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'needs_attention')
            with self.assertRaisesRegex(ValueError,'uncertain/partial'):o.continue_plan(run,'R2')
            state=json.loads((o.path(run)/'state.json').read_text());self.assertTrue(state['step_mutation']['game_constructed'])

    def test_continuation_rejects_session_change_pending_journal_and_prefix_replay(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan();run=o.plan(p)['run'];o.execute(run)
            with self.assertRaisesRegex(ValueError,'replay successful'):o.continue_plan(run,'R2',steps=p['steps'])
            c.journal=Path(td)/'journal.json';c.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
            with self.assertRaisesRegex(ValueError,'unresolved native'):o.continue_plan(run,'R2',steps=[{**p['steps'][0],'name':'new'}])
            c.session='new'
            with self.assertRaisesRegex(ValueError,'session changed'):o.continue_plan(run,'R2')

    def test_native_replacement_receipt_updates_exact_prior_chain_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[p['steps'][0],{'name':'junction','kind':'connect','source':'a','target':'b','source_interior':True}]
            original=self.native_edge(1);left=self.native_edge(2,0,40);right=self.native_edge(3,40,100)
            responses=[{'status':'ok','request_id':'seed','result':{'game_constructed':True,'edges':[original]}},
                {'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                {'status':'ok','request_id':'built','result':{'game_constructed':True,'edges':[],
                    'placements':[{'original_edge':1,'replacement_edges':[2,3]}]}},
                {'status':'ok','request_id':'read','result':{'edges':[left,right]}}]
            with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),patch.object(c,'request',side_effect=responses):
                run=o.plan(p)['run'];self.assertEqual(o.execute(run)['status'],'built')
            state=json.loads((o.path(run)/'state.json').read_text())
            self.assertEqual([e['id'] for e in state['steps']['one']['edges']],[2,3]);self.assertEqual(state['lineage'][0]['original_edge'],1)

    def test_attachment_windows_and_budget_cannot_be_silently_expanded(self):
        p=self.grade_plan();p['steps']=[{'name':'connect','kind':'connect','source':'a','target':'b','attachments':[{'source':'a','target':'b'}]*9}]
        with self.assertRaises(ValueError):validate_plan(p)
        p['steps'][0]['attachments']=[{'source':'a','target':'b'}]
        with self.assertRaisesRegex(ValueError,'windows'):validate_plan(p)
        p['steps'][0]['attachment_windows']={'source':{'min':[50,0,0],'max':[60,1,5]},'target':p['region']}
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);result=o.execute(o.plan(p)['run'])
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(c.calls,[])

    def test_replacement_and_removal_use_fresh_exact_chain_without_widening_selection(self):
        edge=self.native_edge()
        for kind in ('remove','connect'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan();p['bindings']={'old':{'edges':[edge]}}
                p['steps']=[{'name':'change','kind':'remove','chain':'old'}] if kind=='remove' else [
                    {'name':'change','kind':'connect','source':'a','target':'b','replace_chain':'old'}]
                read={'status':'ok','request_id':'read','result':{'game_constructed':False,'edges':[edge]}}
                responses=[read,read,read,{'status':'ok','request_id':'removed','result':{'game_constructed':True,'removed_edges':[1]}}] if kind=='remove' else [
                    read,read,{'status':'ok','request_id':'prepared','result':{'game_constructed':False}},
                    {'status':'ok','request_id':'built','result':{'game_constructed':True,'edges':[]}}]
                with patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':2,'node_id':4,'grade':0},'found')) as select,patch.object(c,'request',side_effect=responses) as request:
                    run=o.plan(p)['run'];result=o.execute(run)
                self.assertEqual(result['status'],'built')
                if kind=='remove':self.assertEqual(request.call_args.args[0],'remove_branch');self.assertEqual(request.call_args.args[1]['edges'],[edge])
                else:
                    self.assertTrue(select.call_args.kwargs['connected']);self.assertEqual(request.call_args_list[-2].args[1]['replace_chain'],[edge])
                self.assertEqual(json.loads((o.path(run)/'state.json').read_text())['invalidated_bindings'],['old'])

    def replacement_fixture(self):
        chain=self.native_edge();left=self.native_edge(2,-30,0);left.update(node0=4,node1=2)
        right=self.native_edge(3,100,130);right.update(node0=3,node1=6)
        branch=self.native_edge(4,100,140);branch.update(node0=3,node1=8)
        candidate={'edge_id':3,'node_id':3,'pos':[100,0,2],'outward_direction':[-1,0,0],'grade':0,'edge_snapshot':right,
                   'incident_count':3,'incident_edges':[1,3,4],'incidence_complete':True,'incident_output_truncated':False,'construction_owner':'none','eligible':False}
        intent={'region':{'min':[99,-1,1],'max':[101,1,3]},'max_edges':16,'guide_xyz':[100,0,2],'travel_direction':[-1,0],'heading_tolerance_deg':2,'placement_tolerance':.15}
        return chain,left,right,branch,candidate,intent

    def test_explicit_replacement_boundary_qualifies_degree_three_by_all_exact_outside_edges(self):
        chain,left,right,branch,candidate,intent=self.replacement_fixture();client=FakeClient()
        def request(op,q,**kwargs):
            return {'status':'ok','request_id':op,'result':{'edges':[right,branch]} if op=='inspect' else {'complete':True,'candidates':[candidate]}}
        with patch.object(client,'request',side_effect=request):
            r=replacement_boundary(client,intent,[chain],{'anchor_edge':3,'edges':[right,branch]})
        self.assertEqual((r['edge_id'],r['node_id']),(3,3));self.assertFalse(r['eligible'])

    def test_replacement_boundary_uses_exact_primary_when_octree_only_returns_chain_edge(self):
        chain,left,right,branch,candidate,intent=self.replacement_fixture();client=FakeClient()
        witness=candidate|{'edge_id':1,'edge_snapshot':chain,'outward_direction':[1,0,0]}
        def request(op,q,**kwargs):
            return {'status':'ok','request_id':'exact_incidence','result':{'edges':[right,branch]} if op=='inspect' else {'complete':True,'candidates':[witness]}}
        with patch.object(client,'request',side_effect=request):
            r=replacement_boundary(client,intent,[chain],{'anchor_edge':3,'edges':[right,branch]})
        self.assertEqual((r['edge_id'],r['node_id']),(3,3));self.assertEqual(r['outward_direction'],[-1,0,0]);self.assertEqual(r['edge_snapshot'],right)
        self.assertEqual(r['ref'],'exact_incidence:E3:N3');self.assertEqual(r['incident_edges'],[1,3,4])

    def test_replacement_boundary_deduplicates_exact_node_witnesses_and_rejects_wrong_position(self):
        for wrong in (False,True):
            chain,left,right,branch,candidate,intent=self.replacement_fixture();client=FakeClient()
            witness=candidate|{'edge_id':1,'edge_snapshot':chain,'outward_direction':[1,0,0]}
            if wrong:witness['pos']=[100,.01,2]
            def request(op,q,**kwargs):
                return {'status':'ok','request_id':'exact_incidence','result':{'edges':[right,branch]} if op=='inspect' else {'complete':True,'candidates':[witness,witness]}}
            with patch.object(client,'request',side_effect=request):
                if wrong:
                    with self.assertRaises(LiveError):replacement_boundary(client,intent,[chain],{'anchor_edge':3,'edges':[right,branch]})
                else:self.assertEqual(replacement_boundary(client,intent,[chain],{'anchor_edge':3,'edges':[right,branch]})['edge_id'],3)

    def test_replacement_boundary_rejects_unlisted_incidence_stale_outside_and_internal_node(self):
        for problem in ('unlisted','missing','incomplete','owned','stale','internal'):
            with self.subTest(problem=problem):
                chain,left,right,branch,candidate,intent=self.replacement_fixture();client=FakeClient();expected=copy.deepcopy(branch)
                if problem=='unlisted':candidate.update(incident_count=4,incident_edges=[1,3,4,5])
                elif problem=='missing':candidate.update(incident_count=2,incident_edges=[1,3])
                elif problem=='incomplete':candidate['incidence_complete']=False
                elif problem=='owned':candidate['construction_owner']=5
                elif problem=='stale':branch['p1'][1]=1
                other=self.native_edge(5,100,110);other.update(node0=3,node1=9)
                def request(op,q,**kwargs):return {'status':'ok','request_id':op,'result':{'edges':[right,branch]} if op=='inspect' else {'complete':True,'candidates':[candidate]}}
                with patch.object(client,'request',side_effect=request),self.assertRaises((LiveError,ValueError)):
                    replacement_boundary(client,intent,[chain,other] if problem=='internal' else [chain],{'anchor_edge':3,'edges':[right,expected]})

    def test_coalescing_operator_transmits_exact_outside_snapshots_without_global_port_relaxation(self):
        chain,left,right,branch,candidate,intent=self.replacement_fixture()
        p=self.grade_plan();p['bindings']={'old':{'edges':[chain]}};p['ports']['b']['position']=[100,0,0]
        step={'name':'merge','kind':'connect','source':'a','target':'b','replace_chain':'old','coalesce_plain':True,
              'replacement_boundaries':{'source':{'anchor_edge':2,'edges':[left]},'target':{'anchor_edge':3,'edges':[right,branch]}}}
        p['steps']=[step]
        with tempfile.TemporaryDirectory() as td:
            client=FakeClient();o=Operator(runs=td,client=client)
            source=candidate|{'edge_id':2,'node_id':2,'pos':[0,0,2],'outward_direction':[1,0,0],'edge_snapshot':left}
            def request(op,q,**kwargs):
                if op=='inspect':value={'edges':[chain]}
                elif q.get('prepare'):value={'game_constructed':False,'prepared_request':'merge_handle'}
                else:value={'game_constructed':True,'edges':[]}
                return {'status':'ok','request_id':op,'result':value}
            with patch.object(client,'request',side_effect=request) as requests,patch('bridge_operator.replacement_boundary',side_effect=[source,candidate]),patch('bridge_operator.live._select_throat_port') as generic:
                self.assertEqual(o.execute(o.plan(p)['run'])['status'],'built')
            generic.assert_not_called();prepared=next(q for call in requests.call_args_list if (q:=call.args[1]).get('prepare'))
            self.assertTrue(prepared['coalesce_plain']);self.assertEqual(prepared['replacement_boundaries'],step['replacement_boundaries']);self.assertEqual(prepared['replace_chain'],[chain])
        for field,value in [('coalesce_plain',False),('guides',[{'position':[50,0,0],'travel_direction':[1,0],'grade':0}]),('replacement_boundaries',{}),('handle_scale',2)]:
            changed=copy.deepcopy(p);changed['steps'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_plan(changed)

    def test_plain_coalescing_preserves_bezier_alignment_and_resources(self):
        chain,left,right,branch,target,intent=self.replacement_fixture()
        source={'pos':[0,0,2],'edge_snapshot':left}
        check_plain_coalescing([chain],source,target)
        reverse=copy.deepcopy(chain);reverse.update(p0=chain['p1'],p1=chain['p0'],t0=[-100,0,0],t1=[-100,0,0])
        check_plain_coalescing([reverse],source,target)
        missing=copy.deepcopy(chain);missing.pop('structure')
        with self.assertRaises(ValueError):check_plain_coalescing([missing],source,target)
        check_plain_coalescing([missing],source,target,require_structure=False)
        for problem in ('bend','structure','resource','backtrack'):
            e=copy.deepcopy(chain)
            if problem=='bend':e['t0'][1]=1
            elif problem=='structure':e['structure']['classification']='BRIDGE'
            elif problem=='resource':e['template']='other'
            else:e['t0'][0]=400
            with self.subTest(problem=problem),self.assertRaises(ValueError):check_plain_coalescing([e],source,target)

    def test_explicit_floor_check_is_sampled_and_never_numeric_edit(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps']=[{'name':'floor','kind':'terrain_check','absolute_floor':1.2,'positions':[[0,0],[10,0]]}]
            response={'status':'ok','request_id':'terrain','result':{'game_constructed':False,'site':{'terrain':[{'xy':[0,0],'height':1.5,'valid':True},{'xy':[10,0],'height':1.1,'valid':True}]}}}
            with patch.object(c,'request',return_value=response) as request:
                run=o.plan(p)['run'];result=o.execute(run)
            self.assertEqual(result['status'],'needs_attention');self.assertIn('below explicit absolute floor',result['error'])
            self.assertEqual(request.call_args.args[0],'inspect');self.assertTrue(json.loads((o.path(run)/'state.json').read_text())['terrain']['floor']['sampled_only'])

    def test_profile_and_crossing_readback_separate_identity_from_clearance(self):
        upper=self.native_edge(1,0,100,18.5);upper['structure']={'classification':'BRIDGE','resource_name':'observed.bridge'}
        lower=self.native_edge(2,0,100,3)
        p=self.grade_plan();p['curves']={'upper':{k:upper[k] for k in ('p0','p1','t0','t1')}}
        p['crossings']=[{'name':'cross','position':[50,0],'upper_height':16.5,'lower_height':1,'upper_route':'up','lower_routes':['low']}]
        paths={'up':[{'edge':{'entity':1},'confirmed_TRACK':True}],'low':[{'edge':{'entity':2},'confirmed_TRACK':True}]}
        observed=crossing_observations(p,[upper,lower],paths)[0]
        self.assertTrue(observed['separate_endpoint_identities_observed']);self.assertTrue(observed['required_structure_observed']);self.assertFalse(observed['clearance_certified'])
        self.assertEqual(observed['upper']['sampled_height_range'],[18.5,18.5])
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'profile.svg';render_profile(p,[upper,lower],path);text=path.read_text()
            self.assertIn('vertical exaggeration 4',text);self.assertIn('absolute z axis',text);self.assertIn('planned upper z=18.50',text)

    def test_mcp_stdout_decodes_semantics_without_changing_protocol_record(self):
        result={'status':'built','run':'a'*16,'completed_steps':4}
        data={'content':[{'type':'text','text':json.dumps(result,indent=2)}],'is_error':False,'meta':{'server':'test'}}
        original=copy.deepcopy(data)
        decoded,failed=semantic_result(data)
        self.assertEqual(json.loads(compact_stdout(decoded,None)),result)
        self.assertFalse(failed);self.assertEqual(data,original)

    def test_mcp_errors_stay_non_successful_and_large_stdout_stays_bounded(self):
        decoded,failed=semantic_result({'content':[{'type':'text','text':'Native tool error'}],'is_error':True})
        self.assertTrue(failed);self.assertEqual(decoded['status'],'error')
        decoded,failed=semantic_result({'content':[{'type':'text','text':json.dumps({'status':'needs_attention','details':'é'*5000})}]})
        out=compact_stdout(decoded,Path('full.json'))
        self.assertTrue(failed);self.assertLessEqual(len(out.encode('utf-8')),4096)
        self.assertEqual(json.loads(out)['status'],'needs_attention');self.assertEqual(json.loads(out)['evidence'],'full.json')

    def test_candidate_failure_retains_status_and_distinct_native_messages(self):
        response={'status':'no_accepted_candidate','request_id':'rejected','result':{'candidate_rejections':[
            {'evaluation':{'messages':['Too Much Curvature']}},
            {'evaluation':{'messages':['Too Much Curvature','Collision']}},
            {'evaluation':{'messages':['x'*1000]}}]}}
        message=native_failure(response)
        self.assertIn('no_accepted_candidate',message);self.assertEqual(message.count('Too Much Curvature'),1)
        self.assertIn('Collision',message);self.assertLessEqual(len(message),400)
        self.assertEqual(native_failure({'status':'error','result':{'error':'lost_ack','candidate_rejections':{}}}), 'error: lost_ack')
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run']
            with patch.object(c,'request',return_value=response):result=o.execute(run)
            self.assertEqual(result['status'],'needs_attention');self.assertIn('Too Much Curvature',result['error'])
            self.assertEqual(json.loads((o.path(run)/'state.json').read_text())['last_request'],'rejected')

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
            with (patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),
                  patch.object(c,'request',side_effect=[{'status':'ok','request_id':'route','result':{'requested_route_verified':False}},
                      {'status':'ok','request_id':'survey','result':{'complete':True,'edges':[]}}])):
                result=o.review(run)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['verified_routes'],0)
            self.assertFalse(json.loads((o.path(run)/'review.json').read_text())['all_routes_verified'])

    def test_stopped_partial_review_keeps_missing_routes_and_fresh_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=self.grade_plan()
            p['steps'].append({**p['steps'][0],'name':'remaining'})
            p['routes']=[{'name':'existing','source':'a','target':'a'},{'name':'missing','source':'a','target':'b'}]
            run=o.plan(p)['run'];o.execute(run);path=o.path(run)/'state.json';state=json.loads(path.read_text())
            state.update(status='needs_attention',step_mutation=None);state['steps'].pop('remaining');path.write_text(json.dumps(state))
            original=path.read_bytes();edge=self.native_edge()
            def select(client,intent,**kwargs):
                if intent['guide_xyz'][0]>0:raise LiveError('no_eligible_candidates','no current attachment','missing-port')
                return {'edge_id':1,'node_id':2},'found'
            with (patch('bridge_operator.live._select_throat_port',side_effect=select),
                  patch('bridge_operator.discover_region',return_value=([edge],1)),
                  patch('bridge_operator.inspect_edges',return_value=[edge]) as inspect,
                  patch.object(c,'request',return_value={'status':'ok','request_id':'route','result':{'requested_route_verified':True,'path':[]}}) as request):
                result=o.review(run)
            self.assertEqual(result['status'],'needs_attention');self.assertFalse(result['construction_complete'])
            self.assertEqual(result['verified_routes'],1);self.assertEqual(result['required_routes'],2)
            report=json.loads((o.path(run)/'review.json').read_text());self.assertEqual(report['edges'],[edge])
            self.assertEqual(report['routes'][1]['status'],'attachment_unavailable')
            self.assertEqual(inspect.call_args.args[1],[1]);self.assertEqual([x.args[0] for x in request.call_args_list],['route'])
            self.assertEqual(path.read_bytes(),original)
            for name in ['overlay.svg','profile-overlay.svg']:
                ET.parse(o.path(run)/name)

    def test_partial_review_never_completes_even_when_all_routes_pass(self):
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient();o=Operator(runs=td,client=c);p=fixture();p['routes']=[{'name':'existing','source':'a','target':'a'}]
            run=o.plan(p)['run'];o.execute(run);path=o.path(run)/'state.json';state=json.loads(path.read_text())
            state.update(status='needs_attention',step_mutation={'game_constructed':False});path.write_text(json.dumps(state))
            with (patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2},'found')),
                  patch('bridge_operator.discover_region',return_value=([],1)),
                  patch.object(c,'request',return_value={'status':'ok','request_id':'route','result':{'requested_route_verified':True}})):
                result=o.review(run)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['verified_routes'],1)
            self.assertTrue(json.loads((o.path(run)/'review.json').read_text())['all_routes_verified'])

    def test_review_refuses_unfinished_or_unreconciled_native_effects(self):
        cases=[('running',None,False,False),('needs_attention',{'game_constructed':'unknown'},False,False),
               ('needs_attention',{'game_constructed':True},False,False),('needs_attention',None,True,False),
               ('needs_attention',None,False,True)]
        for status,mutation,pending,locked in cases:
            with self.subTest(status=status,mutation=mutation,pending=pending,locked=locked),tempfile.TemporaryDirectory() as td:
                c=FakeClient();o=Operator(runs=td,client=c);run=o.plan(fixture())['run'];o.execute(run)
                path=o.path(run)/'state.json';state=json.loads(path.read_text());state.update(status=status,step_mutation=mutation);path.write_text(json.dumps(state))
                if pending:
                    c.journal=Path(td)/'journal.json';c.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
                if locked:(Path(td)/'execution.lock').touch()
                c.calls=[]
                with self.assertRaises(ValueError):o.review(run)
                self.assertEqual(c.calls,[]);self.assertFalse((o.path(run)/'review.json').exists())

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
            with (patch('bridge_operator.live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':0},'found')),
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
