"""Exact signal removal client/proof tests, fake adapter only."""
import copy
import json
import unittest

import bridge_live as live


def brief():
    return {'session':'test','edge_snapshot':{'id':10,'revision':[1,2,3],
        'node0':1,'node1':2,'p0':[0,0,2],'p1':[100,0,2],'t0':[100,0,0],'t1':[100,0,0],
        'template':'track','style':'style','road_type':'TRACK','node_positions':[[0,0,2],[100,0,2]],
        'structure':{'classification':'NORMAL','type_index':0,'resource_name':''}},
        'signals':[{'id':90,'revision':[3,2,1]},{'id':91,'revision':[4,2,1]}]}


class Fake:
    session='test'
    def __init__(self):self.calls=[];self.accepted=True;self.status='ok';self.bad_handle=False;self.bad_proof=None
    def request(self,op,p):
        self.calls.append((op,copy.deepcopy(p)))
        if op=='operating_inspect':
            self.q=p['signal_removal']
            return {'status':'ok','request_id':'prepared','result':{'signal_removal':{
                'native_proposal_evaluated':True,'accepted':self.accepted,'input_hash':self.q['input_hash'],
                'prepared_handle':'wrong' if self.bad_handle else 'prepared'}}}
        if self.status!='ok':return {'status':self.status,'result':{'retry':False,'operating_effects':'unknown'}}
        assert p=={'action':'signal_remove','execute':True,'prepared_handle':'prepared','input_hash':self.q['input_hash']}
        new=copy.deepcopy(self.q['edge_snapshot']);new.update(id=20,revision=[2,2,3])
        value={'input_hash':self.q['input_hash'],'replaced_edge':10,'replacement_edge':20,'snapshot':new,
               'removed_signals':[90,91],'selected_signals_absent':True,'existing_objects_retained':True,
               'functional_signals_verified':True,'track_geometry_verified':True,'structure_verified':True,
               'ownership_verified':True,'game_constructed':True}
        if self.bad_proof:value[self.bad_proof]=False
        return {'status':'ok','result':value}


class SignalRemovalTests(unittest.TestCase):
    def test_exact_one_edge_prepare_then_one_execution_with_complete_lineage(self):
        c=Fake();q=brief();before=copy.deepcopy(q);r=live.remove_signals(c,q,execute=True)
        self.assertEqual(q,before);self.assertEqual([op for op,_ in c.calls],['operating_inspect','operating_control'])
        self.assertEqual(live.signal_removal_replacement(q,r['result'])['id'],20)
        self.assertEqual(c.calls[0][1]['signal_removal']['signals'],q['signals'])
        self.assertLess(len(live.lua_literal(c.calls[0][1]).encode()),32768)

    def test_readonly_and_rejected_proposal_never_execute(self):
        for execute,accepted in ((False,True),(True,False)):
            c=Fake();c.accepted=accepted;live.remove_signals(c,brief(),execute=execute)
            self.assertEqual(len(c.calls),1)

    def test_changed_session_or_bad_prepared_handle_never_execute(self):
        c=Fake();c.session='other'
        with self.assertRaises(live.LiveError):live.remove_signals(c,brief(),execute=True)
        self.assertEqual(c.calls,[])
        c=Fake();c.bad_handle=True
        with self.assertRaises(live.LiveError):live.remove_signals(c,brief(),execute=True)
        self.assertEqual(len(c.calls),1)

    def test_unknown_effects_never_replay_or_fallback(self):
        for status in ('error','mutation_unverified'):
            c=Fake();c.status=status;r=live.remove_signals(c,brief(),execute=True)
            self.assertEqual(r['status'],status);self.assertEqual(len(c.calls),2)

    def test_every_missing_native_proof_stops_acceptance_without_repeat(self):
        for field in ('selected_signals_absent','existing_objects_retained','functional_signals_verified',
                      'track_geometry_verified','structure_verified','ownership_verified','game_constructed'):
            c=Fake();c.bad_proof=field
            with self.subTest(field=field),self.assertRaises(live.LiveError):live.remove_signals(c,brief(),execute=True)
            self.assertEqual(len(c.calls),2)

    def test_changed_geometry_nodes_structure_resources_or_lineage_rejected(self):
        c=Fake();v=live.remove_signals(c,brief(),execute=True)['result']
        for field in ('p0','node0','structure','template','node_positions','road_type','id'):
            bad=copy.deepcopy(v)
            if field=='p0':bad['snapshot'][field][0]+=.01
            elif field=='node_positions':bad['snapshot'][field][0][0]+=.01
            elif field=='structure':bad['snapshot'][field]['classification']='BRIDGE'
            else:bad['snapshot'][field]='different'
            with self.subTest(field=field),self.assertRaises(live.LiveError):live.signal_removal_replacement(brief(),bad)
        bad=copy.deepcopy(v);bad['removed_signals']=[90]
        with self.assertRaises(live.LiveError):live.signal_removal_replacement(brief(),bad)

    def test_input_ids_revisions_membership_bounds_and_finite_snapshot(self):
        for fault in ('duplicate','too_many','revision','finite','road','nodes','signal','extra'):
            q=brief()
            if fault=='duplicate':q['signals'][1]=copy.deepcopy(q['signals'][0])
            elif fault=='too_many':q['signals']=[{'id':x+1,'revision':[1,2,3]} for x in range(17)]
            elif fault=='revision':q['signals'][0]['revision']=[True,2,3]
            elif fault=='finite':q['edge_snapshot']['t1'][0]=float('inf')
            elif fault=='road':q['edge_snapshot']['road_type']='STREET'
            elif fault=='nodes':q['edge_snapshot']['node_positions']=None
            elif fault=='signal':q['signals'][0]['id']=True
            else:q['unknown']=1
            c=Fake()
            with self.subTest(fault=fault),self.assertRaises(ValueError):live.remove_signals(c,q,execute=True)
            self.assertEqual(c.calls,[])

    def test_normal_structure_has_no_invented_resource_and_malformed_proof_rejects(self):
        q=brief();del q['edge_snapshot']['structure']['resource_name']
        r=live.remove_signals(Fake(),q,execute=True)
        self.assertNotIn('resource_name',r['result']['snapshot']['structure'])
        for bad in (None,[],{'snapshot':[]}):
            with self.assertRaises(live.LiveError):live.signal_removal_replacement(q,bad)


if __name__=='__main__':unittest.main()
