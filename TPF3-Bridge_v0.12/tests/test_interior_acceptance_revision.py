import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from bridge_live import reconcile_constructed_interior, LiveError


class InteriorAcceptanceRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.params={'execute':False,'prepare':True,'source':{'edge_id':10,'parameter':.5},'target':{'node_id':20},
                     'radius':0,'region':{'min':[0,0,0],'max':[600,600,30]},'vertical':{'max_grade':.15},'max_route_length':800}
        self.fit={'pieces':1,'controls':[{'p0':[0,0,0],'p1':[500,500,0],'t0':[500,0,0],'t1':[0,500,0]}]}
        self.pending={'operation':'interior_junction','request_id':'built','params':{'execute':True,'prepared_request':'prepared'}}
        self.client=SimpleNamespace(session='session',evidence=self.root,journal=self.root/'journal.json',request=self.request)
        self.calls=[]
        self.result={'reconciled_current_state':True,'readback':{'connected':True,'ordered_edges':[30]},
                     'placement':{'original_removed':True,'original_edge':10,'replacement_edges':[40,41]},
                     'junction':{'exact_native_identity':True,'branch_geometry_verified':True},
                     'through_after':{'requested_route_verified':True},'branch_after':{'requested_route_verified':True}}
        self.revision={'original_request':'built','max_route_length':2000,'reason':'full traversal includes incoming and retained lead',
                       'authority':'user delegated in-scope validation'}
        self.write('journal.json',{'session':'session','pending':self.pending})
        self.write('built.request.json',self.response('built','interior_junction')|{'params':self.pending['params']})
        self.write('built.response.json',self.response('built','interior_junction','mutation_unverified',{'game_constructed':True,'returned_edges':[40,41,30],'fit':self.fit}))
        self.write('prepared.request.json',self.response('prepared','interior_junction')|{'params':self.params})
        self.write('prepared.response.json',self.response('prepared','interior_junction',result={'fit':self.fit,'prepared_request':'prepared',
                   'game_constructed':False,'native_proposal_evaluated':True,'native_proposal_critical':False}))

    def tearDown(self):self.temp.cleanup()
    def write(self,name,value):(self.root/name).write_text(json.dumps(value))
    def response(self,rid,operation,status='ok',result=None):return {'session':'session','request_id':rid,'operation':operation,'status':status,'result':result or {}}
    def request(self,op,params):
        self.calls.append((op,copy.deepcopy(params)));return self.response('readback',op,result=self.result)
    def pending_retained(self):self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)

    def test_prepared_receipt_changes_only_readback_budget_and_clears_python_pending(self):
        v=reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
        q=self.calls[0][1];self.assertEqual(self.calls[0][0],'verify_interior');self.assertFalse(q['execute']);self.assertEqual(q['max_route_length'],2000)
        for key in ('source','target','region','radius','vertical'):self.assertEqual(q[key],self.params[key])
        self.assertEqual(q['fit'],self.fit);self.assertEqual(v['result']['acceptance_revision']['original_criteria'],{'max_route_length':800})
        self.assertFalse(v['result']['native_guard_cleared']);self.assertTrue(v['result']['next_mutation_requires_normal_save_load'])
        self.assertNotIn('pending',json.loads(self.client.journal.read_text()));self.assertEqual(len(self.calls),1)
        with self.assertRaises(LiveError):reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
        self.assertEqual(len(self.calls),1)

    def test_unrevised_prepared_path_keeps_original_criteria(self):
        reconcile_constructed_interior(self.client);self.assertEqual(self.calls[0][1]['max_route_length'],800)

    def test_revision_cannot_change_identity_or_shape_or_other_guards(self):
        for revision in (self.revision|{'original_request':'other'},self.revision|{'radius':0},self.revision|{'max_route_length':799},
                         self.revision|{'max_route_length':8001},self.revision|{'max_route_length':float('nan')},self.revision|{'authority':''}):
            with self.subTest(revision=revision),self.assertRaises(ValueError):reconcile_constructed_interior(self.client,acceptance_revision=revision)
            self.pending_retained()
        self.assertEqual(self.calls,[])

    def test_tampered_prepared_shape_or_execution_identity_stops_before_native(self):
        for filename,key in (('prepared.response.json','shape'),('built.request.json','identity')):
            old=json.loads((self.root/filename).read_text());changed=copy.deepcopy(old)
            if key=='shape':changed['result']['fit']['controls'][0]['p1'][0]+=1
            else:changed['params']['prepared_request']='other'
            self.write(filename,changed)
            with self.assertRaises(LiveError):reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
            self.pending_retained();self.write(filename,old)
        self.assertEqual(self.calls,[])

    def test_native_geometry_topology_or_movement_failure_preserves_pending(self):
        for key in ('geometry','identity','through','branch'):
            old=copy.deepcopy(self.result)
            if key=='geometry':self.result['junction']['branch_geometry_verified']=False
            elif key=='identity':self.result['placement']['original_edge']=11
            else:self.result[key+'_after']['requested_route_verified']=False
            with self.assertRaises(LiveError):reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
            self.pending_retained();self.result=old

    def test_wrong_current_session_or_pending_race_preserves_pending(self):
        original=self.client.request
        def wrong(op,q):return original(op,q)|{'session':'other'}
        self.client.request=wrong
        with self.assertRaises(LiveError):reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
        self.pending_retained()
        def race(op,q):
            answer=original(op,q);self.write('journal.json',{'pending':self.pending|{'request_id':'new'}});return answer
        self.client.request=race
        with self.assertRaises(LiveError):reconcile_constructed_interior(self.client,acceptance_revision=self.revision)
        self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'],'new')


if __name__=='__main__':unittest.main()
