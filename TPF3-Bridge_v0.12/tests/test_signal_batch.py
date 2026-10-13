"""Bulk signalling contract and operator sequencing; fake adapter, no game calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_live as live
from bridge_operator import Operator, no_step_effects, signal_batch_chunks, signal_chain_locations, validate_plan


def edge(ident=1,length=700):
    return {'id':ident,'node0':2,'node1':3,'p0':[0,0,2],'p1':[length,0,2],
            't0':[length,0,0],'t1':[length,0,0],'template':'track','style':'style','road_type':'TRACK'}


def brief():
    return {'edges':[edge()],'seed_id':99,'start_node':2,'placements':[
        {'edge_id':1,'parameter':u,'forward':True,'one_way':True,'distance':700*u} for u in (.1,.5,.9)]}


class Fake:
    session='test'
    evidence=Path('.')
    def __init__(self):
        self.calls=[];self.rows={1:edge()};self.accepted=True;self.outcome='ok';self.proof=True;self.changed=False
    def request(self,operation,p,**kwargs):
        self.calls.append((operation,copy.deepcopy(p)));rid=str(len(self.calls))
        if operation=='inspect':result={'edges':[copy.deepcopy(self.rows[i]) for i in p['edge_ids']]}
        elif 'signal_chain_check' in p:result={'signal_chain_check':{'checked':True}}
        elif 'signal_batch' in p:
            for row in p['signal_batch']['edges']:assert row['id'] in self.rows
            for key in ('before_edge','after_edge'):
                if key in p['signal_batch']:assert p['signal_batch'][key] in self.rows
            self.prepared=p['signal_batch'];self.handle=rid
            result={'signal_batch':{'accepted':self.accepted,'native_proposal_evaluated':True,
                'input_hash':self.prepared['input_hash'],'prepared_handle':rid,'seed':{'id':99}}}
        elif operation=='operating_control':
            assert p['prepared_handle']==self.handle and p['input_hash']==self.prepared['input_hash']
            if self.outcome!='ok':return {'status':self.outcome,'request_id':rid,'result':{'game_constructed':'unknown','operating_effects':'unknown','retry':False}}
            self.changed=True;mapping=[];changed={}
            for old in dict.fromkeys(q['edge_id'] for q in self.prepared['placements']):
                new=copy.deepcopy(self.rows.pop(old));new['id']=old+100;new['revision']=[1,2,3];self.rows[new['id']]=new;changed[old]=new
                mapping.append({'replaced_edge':old,'replacement_edge':new['id'],'snapshot':new})
            result={'input_hash':self.prepared['input_hash'],'prepared_handle':self.handle,
                'game_constructed':True,'track_geometry_verified':self.proof,'existing_objects_retained':True,
                'functional_signals_verified':True,'mapping':mapping,
                'placements':[{'replaced_edge':q['edge_id'],'replacement_edge':changed[q['edge_id']]['id'],'travel_forward':q['forward'],
                               'signal':{'id':1000*len(self.calls)+i,'param':q['parameter']}} for i,q in enumerate(self.prepared['placements'])]}
        else:raise AssertionError((operation,p))
        return {'status':'ok','request_id':rid,'result':result}


def plan():
    return {'version':2,'revision':'bulk','origin':[0,0,2],'region':{'min':[-10,-10,0],'max':[800,10,10]},
            'ports':{'a':{'position':[0,0,0],'direction':[1,0]}},'track':{'template':'track','style':'style'},'max_grade':.025,'routes':[],'curves':{},
            'bindings':{'road':{'edges':[edge()]},'alias':{'edges':[edge()]}},
            'steps':[{'name':'blocks','kind':'signal_chain','chains':['road'],'forward':True,
                      'spacing':300,'start_offset':50,'end_clearance':50,'max_count':4,'seed_id':99,'placement_mode':'batch'}]}


class BatchTests(unittest.TestCase):
    def test_multiple_objects_one_prepared_execution_no_individual_inspect(self):
        c=Fake();q=brief();r=live.place_signal_batch(c,q,execute=True)
        self.assertEqual([op for op,p in c.calls],['operating_inspect','operating_control'])
        self.assertEqual(c.calls[1][1]['action'],'signal_batch')
        changed=live.signal_batch_replacements(q,r['result']);self.assertEqual(changed[1]['id'],101)
        self.assertEqual(len(r['result']['placements']),3)
        self.assertEqual(q,brief())

    def test_rejected_preview_and_read_only_do_not_execute(self):
        for rejected in (False,True):
            c=Fake();c.accepted=not rejected
            r=live.place_signal_batch(c,brief(),execute=rejected)
            self.assertEqual(len(c.calls),1);self.assertFalse(c.changed)
            self.assertEqual(r['status'],'error' if rejected else 'ok')

    def test_rejection_preserves_native_evaluation_identity_and_diagnostics_without_execution(self):
        c=Fake();c.accepted=False;request=c.request;captured=[]
        def native_response(op,q,**kw):
            r=request(op,q,**kw)
            r['result']['signal_batch']['evaluation']={'critical':False,'messages':['Collision'],'message_count':1,
                'collision_entities':[123,-1],'collision_count':2,'collision_output_truncated':False,'collision_info_available':True}
            r['result']['player']=3892;captured.append(copy.deepcopy(r));return r
        with patch.object(c,'request',side_effect=native_response):r=live.place_signal_batch(c,brief(),execute=True)
        self.assertEqual(len(c.calls),1);self.assertFalse(c.changed)
        self.assertEqual(r['status'],'error');self.assertEqual(r['request_id'],captured[0]['request_id'])
        self.assertEqual(r['result']['signal_batch'],captured[0]['result']['signal_batch'])
        self.assertEqual(r['result']['player'],3892);self.assertFalse(r['result']['game_constructed'])
        self.assertEqual(captured[0]['status'],'ok');self.assertNotIn('error',captured[0]['result'])

    def test_geometry_snapshot_payload_stays_within_existing_request_bound(self):
        q=brief();q['edges']=[];q['placements']=[]
        for i in range(16):
            row=edge(i+1);row.update(node0=i+1,node1=i+2,unused_diagnostics='x'*40000);q['edges'].append(row)
            for j in range(4):q['placements'].append({'edge_id':i+1,'parameter':.1+.2*j,'forward':True,'one_way':True})
        params=live._signal_batch_input(q)
        self.assertNotIn('unused_diagnostics',params['edges'][0])
        self.assertLess(len(live.lua_literal({'version':1,'session':'test','sequence':1,'request_id':'probe','operation':'operating_inspect','params':{'signal_batch':params}}).encode()),32768)

    def test_unknown_partial_never_replays_or_falls_back(self):
        for status in ('mutation_unverified','error'):
            c=Fake();c.outcome=status
            with patch('bridge_live.place_signal',side_effect=AssertionError('individual fallback')):
                self.assertEqual(live.place_signal_batch(c,brief(),execute=True)['status'],status)
            self.assertEqual(len(c.calls),2)

    def test_limits_duplicates_and_exclusions_rejected_before_calls(self):
        for change in (lambda q:q.update(seed_id=True),lambda q:q.update(edges=q['edges']*17),
                       lambda q:q.update(placements=q['placements']*22),
                       lambda q:q['placements'].append(q['placements'][0]),
                       lambda q:q.update(excluded_intervals=[[60,80]])):
            q=brief();change(q);c=Fake()
            with self.subTest(q=q),self.assertRaises(ValueError):live.place_signal_batch(c,q,execute=True)
            self.assertEqual(c.calls,[])

    def test_mismatched_handle_hash_seed_do_not_execute(self):
        for key,value in (('prepared_handle','wrong'),('input_hash','0'*64),('seed',{'id':98})):
            c=Fake();original=c.request
            def request(op,p,**kw):
                r=original(op,p,**kw);r['result']['signal_batch'][key]=value;return r
            with patch.object(c,'request',side_effect=request),self.assertRaises(live.LiveError):live.place_signal_batch(c,brief(),execute=True)
            self.assertEqual(len(c.calls),1)

    def test_native_proof_and_exact_mapping_required(self):
        c=Fake();q=brief();value=live.place_signal_batch(c,q,execute=True)['result']
        for change in (lambda v:v.update(existing_objects_retained=False),lambda v:v.update(mapping=[]),
                       lambda v:v['mapping'][0]['snapshot'].update(node0=999),
                       lambda v:v.update(input_hash='0'*64),lambda v:v['placements'][0].update(travel_forward=False),
                       lambda v:v['placements'][0]['signal'].update(param=.2),
                       lambda v:v['mapping'][0]['snapshot'].update(p0=[]),
                       lambda v:v['mapping'][0]['snapshot'].update(p0=[float('nan'),0,2]),
                       lambda v:v['placements'][0]['signal'].update(id=0)):
            v=copy.deepcopy(value);change(v)
            with self.subTest(v=v),self.assertRaises(live.LiveError):live.signal_batch_replacements(q,v)

    def test_chunk_bounds_exclusions_preserve_global_300m_phase(self):
        rows=[]
        for i in range(33):
            r=edge(i+1,300);r.update(node0=i+1,node1=i+2,p0=[300*i,0,2],p1=[300*(i+1),0,2]);rows.append(r)
        locations,length=signal_chain_locations(rows,True,300,150,150,64)
        chunks=signal_batch_chunks(rows,locations,99,[[450,750]])
        kept=[q['distance'] for c in chunks for q in c['locations']]
        self.assertEqual(kept,[q['distance'] for q in locations if not 450<=q['distance']<=750])
        self.assertTrue(all(len(c['brief']['edges'])<=16 and len(c['brief']['placements'])<=64 for c in chunks))
        self.assertTrue(all((x-150)%300==0 for x in kept));self.assertEqual(length,9900)

    def test_reversed_edges_and_whole_chain_reverse(self):
        a=edge(1,400);b=edge(2,400);b.update(node0=4,node1=3,p0=[800,0,2],p1=[400,0,2],t0=[-400,0,0],t1=[-400,0,0])
        for forward in (True,False):
            locations,_=signal_chain_locations([a,b],forward,300,150,150,4)
            chunks=signal_batch_chunks([a,b],locations,99)
            byedge={q['edge_id']:q['forward'] for c in chunks for q in c['brief']['placements']}
            self.assertEqual(byedge,{1:forward,2:not forward})

    def test_operator_updates_all_alias_bindings_once_without_post_signal_inspect(self):
        with tempfile.TemporaryDirectory() as td:
            c=Fake();o=Operator(runs=td,client=c);run=o.plan(plan())['run']
            r=o.execute(run);self.assertEqual(r['status'],'built',r)
            state=json.loads((o.path(run)/'state.json').read_text())
            self.assertEqual([state['bindings'][n]['edges'][0]['id'] for n in ('road','alias')],[101,101])
            self.assertEqual(len(state['lineage']),1);self.assertEqual(len(state['signal_chains']['blocks']['placements']),3)
            self.assertFalse(any(op=='inspect' and p['edge_ids']==[101] for op,p in c.calls))
            with self.assertRaisesRegex(ValueError,'already attempted'):o.execute(run)

    def test_operator_unknown_or_missing_proof_retains_effect_and_blocks_resume(self):
        for unknown in (True,False):
            with tempfile.TemporaryDirectory() as td:
                c=Fake();c.outcome='mutation_unverified' if unknown else 'ok';c.proof=False
                o=Operator(runs=td,client=c);run=o.plan(plan())['run'];r=o.execute(run)
                self.assertEqual(r['status'],'needs_attention',r)
                state=json.loads((o.path(run)/'state.json').read_text());self.assertFalse(no_step_effects(state))
                if not unknown:self.assertEqual(len(state['signal_chains']['blocks']['batches']),1)
                with self.assertRaisesRegex(ValueError,'partial effects'):o.continue_plan(run,'retry')
                self.assertEqual(sum(op=='operating_control' for op,p in c.calls),1)

    def test_operator_more_than16_edges_updates_boundary_ids_between_batches(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[]
            for i in range(33):
                r=edge(i+1,20);r.update(node0=i+1,node1=i+2,p0=[20*i,0,2],p1=[20*(i+1),0,2]);rows.append(r)
            p=plan();p['bindings']={name:{'edges':copy.deepcopy(rows)} for name in ('road','alias')}
            p['steps'][0].update(spacing=20,start_offset=10,end_clearance=10,max_count=64)
            c=Fake();c.rows={r['id']:copy.deepcopy(r) for r in rows};o=Operator(runs=td,client=c);run=o.plan(p)['run']
            result=o.execute(run);self.assertEqual(result['status'],'built',result)
            batches=[q['signal_batch'] for op,q in c.calls if 'signal_batch' in q]
            self.assertEqual([len(q['edges']) for q in batches],[16,16,1])
            self.assertEqual(batches[0]['after_edge'],17);self.assertEqual(batches[1]['before_edge'],116)
            self.assertEqual(batches[1]['after_edge'],33);self.assertEqual(batches[2]['before_edge'],132)
            state=json.loads((o.path(run)/'state.json').read_text())
            self.assertEqual([r['id'] for r in state['bindings']['alias']['edges']],list(range(101,134)))
            self.assertEqual(len(state['signal_chains']['blocks']['placements']),33)

    def test_exclusion_split_replaces_same_edge_again_using_fresh_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=plan();p['steps'][0]['excluded_intervals']=[[200,500]]
            c=Fake();o=Operator(runs=td,client=c);run=o.plan(p)['run'];result=o.execute(run)
            self.assertEqual(result['status'],'built',result)
            batches=[q['signal_batch'] for op,q in c.calls if 'signal_batch' in q]
            self.assertEqual([q['edges'][0]['id'] for q in batches],[1,101])
            state=json.loads((o.path(run)/'state.json').read_text())
            self.assertEqual(state['bindings']['road']['edges'][0]['id'],201)
            self.assertEqual([q['distance'] for q in state['signal_chains']['blocks']['placements']],[50,650])

    def test_batch_requires_seed_and_disjoint_exclusions(self):
        for change in (lambda p:p['steps'][0].pop('seed_id'),lambda p:p['steps'][0].update(excluded_intervals=[[100,200],[150,250]])):
            p=plan();change(p)
            with self.assertRaises(ValueError):validate_plan(p)


if __name__=='__main__':unittest.main()
