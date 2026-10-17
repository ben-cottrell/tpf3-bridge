"""Read-only immutable criteria revisions over owned built children."""
import copy
import tempfile
import unittest
from pathlib import Path

import bridge_approach as approach
import bridge_live as live
from bridge_operator import Operator,digest
from bridge_prepared_approach import qualify_receipt
from test_approach import brief
from test_prepared_approach import World,packet


class ReviewWorld(World):
    fail_review=False
    def request(self,operation,q,**kw):
        if operation=='route':
            self.calls.append((operation,copy.deepcopy(q)))
            passed=q['source_node']==self.mouth['node0'] and not self.fail_review
            return {'status':'ok','request_id':'route','result':{'native_path_found':True,'requested_route_verified':passed,'truncated':False,'path_count':2}}
        return super().request(operation,q,**kw)


class ReviewRevisionTests(unittest.TestCase):
    def source(self,td):
        w=ReviewWorld(td);op=Operator(runs=td,client=w);b,_=packet(w);f=b['families'][0];f['exports']['mouth']='mouth'
        b['checks']=[{'name':'movement','kind':'route','families':['seed'],'shared_effects':[],
            'bindings':{'road':'seed.road','mouth':'seed.mouth'},'payload':{
            'source':{'binding':'mouth','edge_id':w.mouth['id'],'node_id':w.mouth['node1']},
            'target':{'binding':'road','end':'node1'},'required_bindings':['road'],'mode':'TRAIN','max_length':1500,'max_path_entries':256}}]
        run=op.plan_approach(b)['run'];self.assertEqual(op.build_approach(run)['status'],'built');op.review_approach(run)
        checks=copy.deepcopy(b['checks']);checks[0]['payload']['source']['node_id']=w.mouth['node0']
        return w,op,run,checks,digest(approach.load(op.path(run)/'state.json'))

    def test_new_inner_node_review_reuses_children_without_construction_or_parent_write(self):
        with tempfile.TemporaryDirectory() as td:
            w,op,run,checks,proof=self.source(td);before=(op.path(run)/'state.json').read_bytes();calls=len(w.calls)
            result=op.revise_approach_review(run,'inner_review',checks,proof)
            self.assertEqual(result['status'],'reviewed',result);self.assertFalse(result['construction_replayed'])
            self.assertEqual((op.path(run)/'state.json').read_bytes(),before)
            self.assertTrue(all(operation in ('inspect','station_lookup','operating_inspect','route') for operation,_ in w.calls[calls:]))
            revised=result['run'];s=approach.load(op.path(revised)/'state.json');old=approach.load(op.path(run)/'state.json')
            self.assertEqual(s['families'],old['families']);self.assertEqual(s['bindings'],old['bindings']);self.assertEqual(s['review_origin']['run'],run)
            self.assertEqual(s['phase_metrics']['approach_review']['aggregate']['mutation_request_attempts'],0)
            with self.assertRaisesRegex(ValueError,'review-only'):op.build_approach(revised)
            binding,_,_=__import__('bridge_prepared_approach').receipt_source(op,{'approach':revised,'export':'seed.road'},'test')
            self.assertEqual(len(binding['edges']),1)

    def test_changed_check_scope_or_nonendpoint_rejected_before_publication(self):
        for case in ('name','kind','bound','required','edge','node','binding','count'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w,op,run,checks,proof=self.source(td);calls=len(w.calls);folders=set(Path(td).iterdir())
                c=checks[0]
                if case=='name':c['name']='different'
                elif case=='kind':c['kind']='geometry'
                elif case=='bound':c['payload']['max_length']=8000
                elif case=='required':c['payload']['required_bindings']=[]
                elif case=='edge':c['payload']['source']['edge_id']=999
                elif case=='node':c['payload']['source']['node_id']=999
                elif case=='binding':c['bindings']['mouth']='seed.road'
                else:checks=[]
                with self.assertRaises(ValueError):op.revise_approach_review(run,'changed',checks,proof)
                self.assertEqual(len(w.calls),calls);self.assertEqual(set(Path(td).iterdir()),folders)

    def test_stale_state_session_pending_or_unbuilt_child_stop(self):
        for case in ('state','session','pending','child'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as td:
                w,op,run,checks,proof=self.source(td);calls=len(w.calls)
                if case=='state':proof='stale'
                elif case=='session':w.session='other'
                elif case=='pending':w.journal=Path(td)/'pending.json';live.atomic_json(w.journal,{'pending':True})
                else:
                    s=approach.load(op.path(run)/'state.json');child=s['families']['seed']['run'];cs=approach.load(op.path(child)/'state.json');cs['status']='needs_attention';live.atomic_json(op.path(child)/'state.json',cs)
                with self.assertRaises(ValueError):op.revise_approach_review(run,'changed',checks,proof)
                self.assertEqual(len(w.calls),calls)

    def test_failed_new_review_not_exported_or_promoted(self):
        with tempfile.TemporaryDirectory() as td:
            w,op,run,checks,proof=self.source(td);w.fail_review=True
            result=op.revise_approach_review(run,'inner_review',checks,proof)
            self.assertEqual(result['status'],'needs_attention');self.assertEqual(result['review_of'],run)
            self.assertFalse(approach.load(op.path(result['run'])/'state.json')['checks']['movement']['passed'])
            with self.assertRaisesRegex(ValueError,'reviewed'):qualify_receipt(op,{'approach':result['run'],'export':'seed.road'},'test',['node1'])

    def test_parent_change_invalidates_review_and_export(self):
        with tempfile.TemporaryDirectory() as td:
            w,op,run,checks,proof=self.source(td);revised=op.revise_approach_review(run,'inner_review',checks,proof)['run']
            s=approach.load(op.path(run)/'state.json');s['extra']='changed';live.atomic_json(op.path(run)/'state.json',s);calls=len(w.calls)
            with self.assertRaisesRegex(ValueError,'source hash'):op.review_approach(revised)
            with self.assertRaisesRegex(ValueError,'source hash'):qualify_receipt(op,{'approach':revised,'export':'seed.road'},'test',['node1'])
            self.assertEqual(len(w.calls),calls)


if __name__=='__main__':unittest.main()
