"""Offline named preparation/fixed handoff; never contacts the game."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_live as live
import bridge_prepared_approach as prepared
import bridge_operator
from bridge_operator import Operator,digest
from test_approach import World as BaseWorld,brief
from test_corridor_operator import brief as corridor_brief


class World(BaseWorld):
    def __init__(self,directory):
        super().__init__(directory)
        self.mouth=self.make_edge([-10,0,2],[0,0,2],[10,0,0],[10,0,0])
        self.ambiguous=False;self.partial=False;self.seed_resource='signal'
    def request(self,operation,q,**kw):
        if operation=='station_lookup':
            self.calls.append((operation,copy.deepcopy(q)))
            if q.get('max_groups',8)<9:return {'status':'error','request_id':'station','result':{'error':'station_group_bound'}}
            c={'construction_id':42,'resource':'station','position':[0,0,2],
               'frozen_tracks':[{'edge_id':self.mouth['id'],'node0':self.mouth['node0'],'node1':self.mouth['node1']}]}
            return {'status':'ok','request_id':'station','result':{'outcome':'resolved','identity_complete':True,'frozen_complete':True,
                'constructions':[c]* (2 if self.ambiguous else 1),
                'stations':[{'construction_id':42,'station_id':43,'terminals':[
                    {'index':1,'vehicle_edges':[],'vehicle_node':{'entity':self.mouth['node0']}}]}]}}
        if operation=='track_catalogue':
            self.calls.append((operation,copy.deepcopy(q)))
            return {'status':'ok','request_id':'catalogue','result':{'complete':not self.partial,'truncated':self.partial,
                'edges':[copy.deepcopy(e)|{'construction_owner':'none'} for e in self.edges.values() if e['id']!=self.mouth['id']]}}
        if operation=='operating_inspect' and 'signal_seed' in q:
            self.calls.append((operation,copy.deepcopy(q)))
            return {'status':'ok','request_id':'seed','result':{'signal_seed':{'id':99,'resource':self.seed_resource}}}
        return super().request(operation,q,**kw)


def packet(world):
    b=brief();p=b['families'][0]['payload'];p['bindings']={'mouth':{'edges':[copy.deepcopy(world.mouth)]}}
    p['port_refs']={'a':{'chain':'mouth','end':'node1'}}
    return b,{'family_bindings':{'seed':{'mouth':{'edge_id':world.mouth['id'],'terminal_index':1,'end':'node1'}}},
              'catalogue_region':{'min':[-100,-100,-10],'max':[1500,100,100]},'signal_seed':{'seed_id':99,'resource':'signal'}}


def receipt_follow(world,source='self'):
    c=corridor_brief();c['sections']=c['sections'][:1];c['waypoints'].pop('w2')
    # Authored reference geometry is only for strict local preflight. The
    # self export's actual ID/geometry does not exist until its child commits.
    ref=copy.deepcopy(world.mouth);ref.update(id=500,node0=1000,node1=1001,p0=[0,0,2],p1=[20,0,2],t0=[20,0,0],t1=[20,0,0])
    c['bindings']={'future':{'edges':[ref]}};c['waypoints']['w0']['up']={'front':{'chain':'future','end':'node1'}}
    follow={'brief':c,'roads':[{'name':'up','track':'up','sections':['leg0'],'forward':True,'spacing':300,'start_offset':150,
        'end_clearance':150,'max_count':64,'seed_id':99,'max_route_length':1500,'checks':['forward','reverse_blocked']}],
        'whole_routes':{'roads':[{'name':'whole','road':'up','waypoint':'w0','root_binding':'seed.road',
            'new_receipt_pool':[{'family':'seed','step':'one'}],'existing_scaffold_edge_ids':[],'forward_root_to_main':True}]}}
    return follow,{'future':{'receipt':{'approach':source,'export':'seed.road'}}}


class PreparedTests(unittest.TestCase):
    def test_public_extension_inherits_exact_source_resources(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);b,inputs=packet(w);p=b['families'][0]['payload']
            p['bindings']['mouth']['edges'][0]['template']='slow_native'
            p['steps'][0]={'name':'one','kind':'extend','source':'a','target':'b','radius':1}
            p['ports']['b']={'position':[20,0,0],'direction':[1,0],'grade':0}
            _,_,track=prepared.public_export(b,'seed.road')
            self.assertEqual(track,{'template':'slow_native','style':'style'})

    def test_frozen_construction_endpoint_needs_membership_not_operating_terminal(self):
        for case in ('pass_through','wrong_construction','missing','wrong_end','occupied'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
                inputs['family_bindings']['seed']['mouth']={'edge_id':w.mouth['id'],'frozen':True,'end':'node1'}
                if case=='wrong_end':inputs['family_bindings']['seed']['mouth']['end']='node0'
                if case=='occupied':w.extra_incidence[w.mouth['node1']]=[999]
                original=w.request
                def request(operation,q,**kw):
                    r=original(operation,q,**kw)
                    if operation=='station_lookup' and r['status']=='ok':
                        v=r['result'];v['stations'][0]['terminals']=[]
                        if case in ('wrong_construction','missing'):
                            other=copy.deepcopy(v['constructions'][0]);v['constructions'][0]['frozen_tracks']=[]
                            if case=='wrong_construction':other.update(construction_id=99,position=[100,0,2]);v['constructions'].append(other)
                    return r
                with patch.object(w,'request',side_effect=request):result=op.prepare_approach(b,inputs)
                self.assertEqual(result['status'],'prepared' if case=='pass_through' else 'needs_attention',result)

    def test_explicit_no_extra_whole_routes_preserves_existing_checks(self):
        for case in ('empty','missing','malformed'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);follow,selectors=receipt_follow(w)
                inputs['corridor_bindings']=selectors
                follow['whole_routes']={'roads':[]} if case=='empty' else ({} if case=='missing' else {'roads':{}})
                result=op.prepare_approach(b,inputs,follow)
                if case!='empty':self.assertEqual(result['status'],'needs_attention');continue
                self.assertEqual(result['status'],'prepared',result);p=prepared.read(op.path(result['run'])/'prepared_approach.json')
                self.assertEqual(p['approach']['checks'],b['checks']);self.assertEqual(p['follow_on']['roads'],follow['roads'])
    def test_self_receipt_deferred_until_committed_then_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);follow,selectors=receipt_follow(w)
            inputs['corridor_bindings']=selectors;r=op.prepare_approach(b,inputs,follow)
            self.assertEqual(r['status'],'prepared',r);p=prepared.read(op.path(r['run'])/'prepared_approach.json')
            self.assertEqual(p['follow_on']['brief']['waypoints']['w0']['up']['front'],{'chain':'future','end':'node1'})
            self.assertIsNone(p['corridor_receipts']['future']['proof'])
            ar=op.plan_approach(p['approach'])['run'];self.assertEqual(op.build_approach(ar)['status'],'built')
            self.assertEqual(op.review_approach(ar)['status'],'reviewed')
            frozen=prepared.materialize_corridor(op,op.path(r['run']),p,ar);ref=frozen['brief']['waypoints']['w0']['up']['front']
            self.assertEqual(ref['chain'],'future');self.assertNotEqual(ref['edge_id'],500)
            self.assertEqual(frozen['brief']['bindings']['future']['edges'][0]['node1'],ref['node_id'])
            self.assertEqual(frozen['brief']['sections'],follow['brief']['sections'])
            self.assertEqual(frozen['provenance']['future']['selector']['approach'],ar)
            self.assertEqual(prepared.materialize_corridor(op,op.path(r['run']),p,ar),frozen)
            w.extra_incidence[ref['node_id']]=[999]
            with self.assertRaisesRegex(ValueError,'occupied'):prepared.materialize_corridor(op,op.path(r['run']),p,ar)

    def test_existing_source_hash_session_resources_and_ambiguity_stop(self):
        for case in ('source_hash','session','resource','occupied','ambiguous'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w=World(td);op=Operator(runs=td,client=w);ar=op.plan_approach(brief())['run']
                self.assertEqual(op.build_approach(ar)['status'],'built');op.review_approach(ar)
                selector={'approach':ar,'export':'seed.road'}
                binding,proof=prepared.qualify_receipt(op,selector,'test',['node1'])
                state=prepared.read(op.path(ar)/'state.json');child=state['families']['seed']['run'];cs=prepared.read(op.path(child)/'state.json')
                if case=='source_hash':state['checks']['extra']={};live.atomic_json(op.path(ar)/'state.json',state)
                elif case=='session':state['session']='other';live.atomic_json(op.path(ar)/'state.json',state)
                elif case=='resource':w.edges[binding['edges'][0]['id']]['template']='other'
                elif case=='occupied':w.extra_incidence[binding['edges'][0]['node1']]=[999]
                else:
                    cs['steps']['one']['edges']*=2;live.atomic_json(op.path(child)/'state.json',cs)
                with self.assertRaises(ValueError):prepared.qualify_receipt(op,selector,'test',['node1'],proof if case!='ambiguous' else None)

    def test_interrupted_corridor_child_reused_without_rebinding_consumed_export(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);follow,selectors=receipt_follow(w)
            inputs['corridor_bindings']=selectors;run=op.prepare_approach(b,inputs,follow)['run']
            def interrupted(child):
                state=prepared.read(op.path(child)/'state.json');state['status']='built';live.atomic_json(op.path(child)/'state.json',state)
                frozen=prepared.read(op.path(run)/'materialized_corridor.json');ref=frozen['brief']['waypoints']['w0']['up']['front']
                w.extra_incidence[ref['node_id']]=[999] # Already consumed by this child's construction.
                raise SystemExit('interrupted after owned child built')
            def complete(child,**kw):
                state=prepared.read(op.path(child)/'state.json');state['completion']['status']='completed';live.atomic_json(op.path(child)/'state.json',state);return state
            with patch.object(op,'build_corridor',side_effect=interrupted),self.assertRaises(SystemExit):op.build_prepared_approach(run)
            state=prepared.read(op.path(run)/'state.json');self.assertEqual(state['stage'],3);child=state['children']['corridor']
            before=(op.path(run)/'materialized_corridor.json').read_bytes()
            with patch.object(prepared,'materialize_corridor',side_effect=AssertionError('must not rematerialize')),\
                 patch.object(op,'build_corridor',side_effect=AssertionError('must not rebuild')),\
                 patch.object(op,'complete_corridor',side_effect=complete),patch.object(prepared,'whole_queries',return_value=[]):
                result=op.build_prepared_approach(run,continuing=True)
            self.assertEqual(result['status'],'completed',result);self.assertEqual(result['children']['corridor'],child)
            self.assertEqual((op.path(run)/'materialized_corridor.json').read_bytes(),before)

    def test_existing_source_proof_captured_and_invalid_future_contract_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);ar=op.plan_approach(brief())['run'];op.build_approach(ar);op.review_approach(ar)
            b,inputs=packet(w);follow,selectors=receipt_follow(w,ar);inputs['corridor_bindings']=selectors
            r=op.prepare_approach(b,inputs,follow);self.assertEqual(r['status'],'prepared',r)
            p=prepared.read(op.path(r['run'])/'prepared_approach.json')
            self.assertEqual(p['corridor_receipts']['future']['proof']['approach'],ar)
            for case in ('name','end','resource'):
                bad=copy.deepcopy(follow);spec=copy.deepcopy(inputs)
                if case=='name':spec['corridor_bindings']['future']['receipt']={'approach':'self','export':'seed.unknown'}
                elif case=='end':bad['brief']['waypoints']['w0']['up']['front']['end']='nearest'
                else:bad['brief']['bindings']['future']['edges'][0]['template']='different'
                self.assertEqual(op.prepare_approach(b,spec,bad)['status'],'needs_attention')

    def test_cli_success_and_failure_exit_codes_preserve_json(self):
        for state,expected in (('prepared',0),('completed',0),('needs_attention',1),('error',1)):
            with self.subTest(status=state),patch('bridge_operator.Operator') as factory,\
                 patch('sys.argv',['bridge_operator.py','prepared-approach-status','--run','a'*16]),\
                 patch('sys.stdout',new_callable=io.StringIO) as stdout:
                factory.return_value.prepared_approach_status.return_value={'status':state,'run':'a'*16}
                self.assertEqual(bridge_operator.main(),expected)
                self.assertEqual(json.loads(stdout.getvalue())['status'],state)

    def test_preparation_forwards_existing_bounds_for_nine_group_world(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
            self.assertEqual(w.request('station_lookup',{'name':'Station'})['status'],'error')
            w.calls.clear();r=op.prepare_approach(b,inputs);self.assertEqual(r['status'],'prepared',r)
            query=next(q for operation,q in w.calls if operation=='station_lookup')
            self.assertEqual(query,{'name':'Station','lookup_scope':'identity_frozen','max_groups':256,
                'max_external_edges':16,'max_lead_distance':800,'max_frozen_entities':16384,'max_frozen_tracks':2048})

    def test_named_materialisation_preserves_geometry_and_real_child_build(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);before=copy.deepcopy(b)
            w.session='fresh'
            result=op.prepare_approach(b,inputs);self.assertEqual(result['status'],'prepared',result)
            plan=prepared.read(op.path(result['run'])/'prepared_approach.json')
            expected=copy.deepcopy(before);expected['session']='fresh'
            self.assertEqual(plan['approach'],expected);self.assertEqual(b,before)
            self.assertFalse(any(q.get('execute') for _,q in w.calls))
            self.assertEqual(result['preparation']['request_counts']['requests'],len(w.calls))
            built=op.build_prepared_approach(result['run']);self.assertEqual(built['status'],'completed',built)
            self.assertEqual(set(built['children']),{'approach'})
            calls=len(w.calls);self.assertEqual(op.build_prepared_approach(result['run'])['status'],'completed')
            self.assertEqual(len(w.calls),calls)
            self.assertLess(len(json.dumps(built).encode()),4096)

    def test_missing_ambiguous_stale_and_incomplete_inputs_do_not_publish(self):
        for case in ('missing','terminal','end','ambiguous','stale','partial','seed','occupied'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
                if case=='missing':inputs['family_bindings']={}
                elif case=='terminal':inputs['family_bindings']['seed']['mouth']['terminal_index']=2
                elif case=='end':inputs['family_bindings']['seed']['mouth']['end']='node0'
                elif case=='ambiguous':w.ambiguous=True
                elif case=='stale':b['families'][0]['payload']['bindings']['mouth']['edges'][0]['t1'][1]=1
                elif case=='partial':w.partial=True
                elif case=='seed':w.seed_resource='different'
                elif case=='occupied':w.extra_incidence[w.mouth['node1']]=[999]
                result=op.prepare_approach(b,inputs)
                self.assertEqual(result['status'],'needs_attention',result)
                self.assertEqual(list(Path(td).glob('*/state.json')),[])
                self.assertFalse(any(q.get('execute') for _,q in w.calls))

    def test_pending_and_changed_session_stop_before_new_work(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
            w.journal=Path(td)/'journal.json';live.atomic_json(w.journal,{'pending':True})
            self.assertEqual(op.prepare_approach(b,inputs)['status'],'needs_attention');self.assertEqual(w.calls,[])
            live.atomic_json(w.journal,{'pending':False});r=op.prepare_approach(b,inputs);calls=len(w.calls)
            w.session='changed'
            with self.assertRaisesRegex(ValueError,'session changed'):op.build_prepared_approach(r['run'])
            self.assertEqual(len(w.calls),calls)

    def test_bootstrap_prediction_never_replaces_post_removal_incidence(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
            extra=w.make_edge([0,0,2],[10,0,2],[10,0,0],[10,0,0],w.mouth['node1'],9)
            boot=copy.deepcopy(b['families'][0]['payload']);boot.pop('port_refs');boot['bindings']={'remove':{'edges':[extra]}}
            boot['steps']=[{'name':'clear','kind':'remove','chain':'remove'}];inputs['bootstrap']=boot
            r=op.prepare_approach(b,inputs);self.assertEqual(r['status'],'prepared',r)
            plan=prepared.read(op.path(r['run'])/'prepared_approach.json')
            prepared.qualify_inputs(op,plan,after_bootstrap=False)
            with self.assertRaisesRegex(ValueError,'actually free'):prepared.qualify_inputs(op,plan,after_bootstrap=True)
            del w.edges[extra['id']];prepared.qualify_inputs(op,plan,after_bootstrap=True)
            # Fresh controls cannot be bypassed by a completed bootstrap receipt.
            w.edges[w.mouth['id']]['p1'][0]=1
            with self.assertRaisesRegex(ValueError,'geometry/resources'):prepared.qualify_inputs(op,plan,after_bootstrap=True)

    def test_follow_on_binds_exact_guides_and_keeps_mixed_resources(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);c=corridor_brief()
            c['sections']=c['sections'][:1];c['waypoints'].pop('w2');c['bindings']={}
            c['track_by_road']={'up':{'template':'track','style':'style'},'down':{'template':'fast','style':'style'}}
            inputs['corridor_bindings']={}
            for j,road in enumerate(('up','down')):
                e=w.make_edge([-10,j*5,9.9],[0,j*5,10],[10,0,.1],[10,0,.1])
                if road=='down':e['template']='fast'
                name='existing_'+road;c['bindings'][name]={'edges':[copy.deepcopy(e)]}
                c['waypoints']['w0'][road]={'front':{'chain':name,'edge_id':e['id'],'node_id':e['node1']}}
                inputs['corridor_bindings'][name]={'edge_id':e['id']}
            roads=[{'name':road,'track':road,'sections':['leg0'],'forward':j==0,'spacing':300,'start_offset':150,
                'end_clearance':150,'max_count':64,'seed_id':1,'max_route_length':1500,'checks':['forward','reverse_blocked']} for j,road in enumerate(('up','down'))]
            follow={'brief':c,'roads':roads,'whole_routes':{'roads':[{'name':'whole','road':'up','waypoint':'w0',
                'root_binding':'seed.road','new_receipt_pool':[{'family':'seed','step':'one'}],
                'existing_scaffold_edge_ids':[c['bindings']['existing_up']['edges'][0]['id']],'forward_root_to_main':True}]}}
            w.session='fresh';r=op.prepare_approach(b,inputs,follow);self.assertEqual(r['status'],'prepared',r)
            p=prepared.read(op.path(r['run'])/'prepared_approach.json');actual=p['follow_on']
            self.assertEqual(actual['brief']['track_by_road'],c['track_by_road'])
            self.assertEqual(actual['brief']['waypoints'],c['waypoints'])
            self.assertEqual(actual['brief']['session'],'fresh');self.assertTrue(all(x['seed_id']==99 for x in actual['roads']))
            self.assertEqual(actual['whole_routes'],follow['whole_routes'])

    def test_stopped_child_reference_durable_and_completed_child_not_repeated(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);r=op.prepare_approach(b,inputs);run=r['run']
            with patch.object(op,'build_approach',return_value={'status':'needs_attention'}) as call:
                stopped=op.build_prepared_approach(run)
            self.assertEqual(stopped['status'],'needs_attention');self.assertEqual(stopped['stage'],1)
            child=stopped['children']['approach'];self.assertEqual(call.call_args.args,(child,))
            self.assertTrue((op.path(child)/'approach.json').exists())
            with self.assertRaisesRegex(ValueError,'explicit continuation'):op.build_prepared_approach(run)
            with self.assertRaisesRegex(ValueError,'wrong stage'):op.build_prepared_approach(run,continuing=True,section_run='b'*16)
            result=op.build_prepared_approach(run,continuing=True);self.assertEqual(result['status'],'completed',result)
            self.assertEqual(result['children']['approach'],child)
            self.assertEqual(sum(x=='test_approach' for x,_ in w.calls),1)

    def test_explicit_whole_road_pool_excludes_fan_and_follows_signal_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w)
            rows=[]
            for n in range(4):rows.append(w.make_edge([n*10,0,2],[(n+1)*10,0,2],[10,0,0],[10,0,0],10+n,11+n))
            root,mid,main,fan=rows;ar='a'*16;child='b'*16;cr='c'*16
            for ident in (ar,child,cr):op.path(ident).mkdir()
            live.atomic_json(op.path(ar)/'state.json',{'status':'reviewed','families':{'f':{'run':child}},'bindings':{'f.root':{'edges':[root]}}})
            live.atomic_json(op.path(child)/'state.json',{'steps':{'root':{'edges':[root]},'mid':{'edges':[mid]},'fan':{'edges':[fan]}}})
            replacement=copy.deepcopy(main);replacement['id']=300
            w.edges.pop(main['id']);w.edges[300]=copy.deepcopy(replacement)
            live.atomic_json(op.path(cr)/'state.json',{'completion':{'roads':{'road':{'edges':[replacement],
                'placements':[{'replaced_edge':main['id'],'replacement_edge':300}]}}}})
            recipe={'name':'whole','road':'UF','waypoint':'w0','root_binding':'f.root','forward_root_to_main':True,
                'new_receipt_pool':[{'family':'f','step':'root'},{'family':'f','step':'mid'}],'existing_scaffold_edge_ids':[main['id']]}
            p={'session':'test','bootstrap':None,'guides':[main],'follow_on':{'whole_routes':{'roads':[recipe]},'roads':[{'name':'road','track':'UF'}],
                'brief':{'waypoints':{'w0':{'UF':{'front':{'edge_id':main['id'],'node_id':main['node1']}}}}}}}
            live.atomic_json(op.path(cr)/'corridor.json',{'brief':p['follow_on']['brief']})
            q=prepared.whole_queries(op,ar,p,cr)[0][1]
            self.assertEqual(q['required_edges'],[root['id'],mid['id'],300]);self.assertEqual(q['target_edge'],300)
            self.assertNotIn(fan['id'],q['required_edges'])
            # A deleted bootstrap integer may be recycled for a genuinely new
            # owned receipt. Current exact nodes/controls/resources prove it.
            p['bootstrap']={'bindings':{'old':{'edges':[{'id':root['id'],'node0':900,'node1':901}]}}}
            with self.subTest(case='owned_receipt_reuses_removed_native_integer'):
                self.assertEqual(prepared.whole_queries(op,ar,p,cr)[0][1]['required_edges'],[root['id'],mid['id'],300])
            recipe['forward_root_to_main']=False;q=prepared.whole_queries(op,ar,p,cr)[0][1]
            self.assertEqual(q['required_edges'],[300,mid['id'],root['id']]);self.assertEqual(q['source_edge'],300)
            concrete=p['follow_on']['brief'];concrete['waypoints']['w0']['UF']['back']=concrete['waypoints']['w0']['UF'].pop('front')
            live.atomic_json(op.path(cr)/'corridor.json',{'brief':concrete});recipe['waypoint_side']='back'
            self.assertEqual(prepared.whole_queries(op,ar,p,cr)[0][1]['source_edge'],300)
            w.edges[mid['id']]['t1'][1]=1
            with self.assertRaisesRegex(ValueError,'geometry/resources'):prepared.whole_queries(op,ar,p,cr)
            w.edges[mid['id']]['t1'][1]=0
            recipe['new_receipt_pool'].append({'family':'f','step':'fan'})
            with self.assertRaises(ValueError):prepared.whole_queries(op,ar,p,cr)

    def test_built_approach_reused_when_review_stops(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);run=op.prepare_approach(b,inputs)['run']
            with patch.object(op,'review_approach',side_effect=ValueError('review stopped')):
                r=op.build_prepared_approach(run)
            self.assertEqual(r['stage'],2);self.assertEqual(r['status'],'needs_attention')
            mutations=sum(x=='test_approach' for x,_ in w.calls)
            r=op.build_prepared_approach(run,continuing=True)
            self.assertEqual(r['status'],'completed',r)
            self.assertEqual(sum(x=='test_approach' for x,_ in w.calls),mutations)

    def test_fixed_follow_on_stages_and_explicit_route_retry(self):
        # Existing child geometry/signal contracts are covered in their own
        # suites. This checks handoff ownership, stage persistence and no replay.
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w);run=op.prepare_approach(b,inputs)['run']
            path=op.path(run);p=prepared.read(path/'prepared_approach.json');s=prepared.read(path/'state.json')
            p['follow_on']={'brief':{'revision':'fixed'},'roads':[{'name':'fixed'}],'whole_routes':{}}
            # Start at post-review stage; this is an explicitly authored fake
            # persisted child state, not a changed production record.
            s.update(stage=3,children={'approach':'b'*16},game_constructed=True,plan_hash=digest(p))
            live.atomic_json(path/'prepared_approach.json',p);live.atomic_json(path/'state.json',s)
            child='c'*16;events=[];queries=[]
            def plan(c):
                self.assertEqual(c,p['follow_on']['brief']);op.path(child).mkdir()
                live.atomic_json(op.path(child)/'state.json',{'status':'planned'});events.append('plan');return {'run':child}
            def build(c):
                self.assertEqual(prepared.read(path/'state.json')['children']['corridor'],c)
                live.atomic_json(op.path(c)/'state.json',{'status':'built'});events.append('build');return {'status':'built'}
            def attach(c,roads):
                self.assertEqual(roads,p['follow_on']['roads']);cs=prepared.read(op.path(c)/'state.json')
                cs['completion']={'status':'planned'};live.atomic_json(op.path(c)/'state.json',cs);events.append('attach')
            def complete(c,**kw):
                cs=prepared.read(op.path(c)/'state.json');cs['completion']['status']='completed'
                live.atomic_json(op.path(c)/'state.json',cs);events.append('complete');return cs
            original=w.request
            def request(operation,q,**kw):
                if operation!='route':return original(operation,q,**kw)
                queries.append(q);w.calls.append((operation,q));passed=len(queries)!=2
                return {'status':'ok','request_id':str(len(queries)),'result':{'native_path_found':passed,'requested_route_verified':passed,'truncated':False}}
            with patch.object(op,'plan_corridor',side_effect=plan),patch.object(op,'build_corridor',side_effect=build),\
                 patch.object(op,'attach_corridor_completion',side_effect=attach),patch.object(op,'complete_corridor',side_effect=complete),\
                 patch.object(w,'request',side_effect=request),patch.object(prepared,'whole_queries',return_value=[('one',{'road':1}),('two',{'road':2})]):
                r=op.build_prepared_approach(run);self.assertEqual(r['status'],'needs_attention');self.assertEqual(r['stage'],5)
                self.assertEqual(events,['plan','build','attach','complete'])
                w.journal=Path(td)/'journal.json';live.atomic_json(w.journal,{'pending':True})
                with self.assertRaisesRegex(ValueError,'reconciliation'):op.build_prepared_approach(run,continuing=True)
                self.assertEqual(len(queries),2)
                live.atomic_json(w.journal,{'pending':False});r=op.build_prepared_approach(run,continuing=True)
                self.assertEqual(r['status'],'completed',r);self.assertEqual(queries,[{'road':1},{'road':2},{'road':1},{'road':2}])
                self.assertEqual(events,['plan','build','attach','complete'])

    def test_bootstrap_continuation_scope_and_partial_removal_proof(self):
        with tempfile.TemporaryDirectory() as td:
            w=World(td);op=Operator(runs=td,client=w);b,inputs=packet(w)
            first=w.make_edge([0,0,2],[10,0,2],[10,0,0],[10,0,0],w.mouth['node1'],9)
            second=w.make_edge([20,0,2],[30,0,2],[10,0,0],[10,0,0])
            boot=copy.deepcopy(b['families'][0]['payload']);boot.pop('port_refs')
            boot['bindings']={'first':{'edges':[first]},'second':{'edges':[second]}}
            boot['steps']=[{'name':'clear_first','kind':'remove','chain':'first'},{'name':'clear_second','kind':'remove','chain':'second'}]
            inputs['bootstrap']=boot;r=op.prepare_approach(b,inputs);self.assertEqual(r['status'],'prepared',r)
            original=op.plan(boot)['run'];parent=prepared.read(op.path(original)/'state.json')
            parent.update(status='needs_attention',session='test',steps={'clear_first':{'status':'built','edges':[]}},
                current_step='clear_second',step_mutation=None)
            live.atomic_json(op.path(original)/'state.json',parent)
            new=copy.deepcopy(boot);new.update(version=2,revision='remaining',steps=[boot['steps'][1]],bindings={'second':{'edges':[second]}},
                continuation={'run':original,'state_hash':digest(parent),'session':'test','skipped_steps':['clear_first']})
            child=op.plan(new)['run'];removed=prepared.bootstrap_continuation(op,original,child,'test')
            self.assertEqual(removed,{first['id']})
            del w.edges[first['id']]
            p=prepared.read(op.path(r['run'])/'prepared_approach.json')
            prepared.qualify_inputs(op,p,after_bootstrap=False,completed_removals=removed)
            for case in ('steps','region','binding','hash','session'):
                bad=copy.deepcopy(new)
                if case=='steps':bad['steps']=[{'name':'new','kind':'stub','port':'a','length':20}]
                elif case=='region':bad['region']['max'][0]+=1
                elif case=='binding':bad['bindings']['second']['edges'][0]['id']=999
                elif case=='hash':bad['continuation']['state_hash']='wrong'
                else:bad['continuation']['session']='new'
                live.atomic_json(op.path(child)/'plan.json',bad)
                cs=prepared.read(op.path(child)/'state.json');cs['plan_hash']=digest(bad);live.atomic_json(op.path(child)/'state.json',cs)
                with self.subTest(case=case),self.assertRaises(ValueError):prepared.bootstrap_continuation(op,original,child,'test')


if __name__=='__main__':unittest.main()
