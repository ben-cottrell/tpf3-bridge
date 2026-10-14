"""Explicit remaining-family contract correction, never parent replay."""
import copy
import json
import tempfile
import unittest
from unittest.mock import patch

import bridge_approach as approach
from bridge_operator import Operator,digest,validate_plan
from test_approach import World,brief


def payload():
    p=copy.deepcopy(brief()['families'][0]['payload'])
    p['ports']['out']={'position':[20,0,0],'direction':[1,0],'grade':0}
    p['port_refs']={'out':{'chain':'one','end':'node1'}}
    p['steps'].append({'name':'merge','kind':'branch','source':'out','target':{'curve':'one','u':.68},'radius':0})
    return p


def corrected(p):
    p=copy.deepcopy(p);p['steps'][-1].update(kind='connect',target_interior=True);return p


class ContractTests(unittest.TestCase):
    def test_unused_input_export_follows_immutable_parent_binding_not_fake_step(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);op=Operator(runs=td,client=c);parent='d'*16;child='e'*16
            for ident in (parent,child):op.path(ident).mkdir()
            edge=c.make_edge([0,0,2],[20,0,2],[20,0,0],[20,0,0])
            old={'status':'needs_attention','session':'test','steps':{'prefix':{'edges':[edge]},'unfinished':{'edges':[edge]}},
                 'bindings':{'mouth':{'edges':[edge]}}}
            approach.live.atomic_json(op.path(parent)/'state.json',old)
            approach.live.atomic_json(op.path(parent)/'plan.json',{})
            link={'run':parent,'state_hash':digest(old),'session':'test','skipped_steps':['prefix']}
            approach.live.atomic_json(op.path(child)/'plan.json',{'continuation':link})
            current={'status':'built','session':'test','steps':{},'bindings':{}}
            value=approach.exported_binding(op,child,current,'mouth')
            self.assertEqual(value,old['bindings']['mouth'])
            from bridge_operator import fresh_binding
            self.assertEqual(fresh_binding(op.client(),value),[edge])
            self.assertIsNone(approach.exported_binding(op,child,current,'unfinished'))
            self.assertEqual(approach.exported_binding(op,child,current,'prefix'),old['steps']['prefix'])
            old['invalidated_bindings']=['mouth'];approach.live.atomic_json(op.path(parent)/'state.json',old)
            with self.assertRaisesRegex(ValueError,'parent changed'):approach.exported_binding(op,child,current,'mouth')
            link['state_hash']=digest(old);approach.live.atomic_json(op.path(child)/'plan.json',{'continuation':link})
            with self.assertRaisesRegex(ValueError,'invalidated'):approach.exported_binding(op,child,current,'mouth')
            old.pop('invalidated_bindings');old['session']='other';link['state_hash']=digest(old)
            approach.live.atomic_json(op.path(parent)/'state.json',old)
            approach.live.atomic_json(op.path(child)/'plan.json',{'continuation':link})
            with self.assertRaisesRegex(ValueError,'session changed'):approach.exported_binding(op,child,current,'mouth')

    def test_only_contract_diff_and_unstarted_family_isolation(self):
        f=brief()['families'][0];f['payload']=payload();b={'families':[f]}
        for change in ('geometry','source','radius','extra','limit','count'):
            p=corrected(f['payload'])
            if change=='geometry':p['ports']['out']['position'][0]+=1
            elif change=='source':p['steps'][-1]['source']='a'
            elif change=='radius':p['steps'][-1]['radius']=1
            elif change=='extra':p['steps'][-1]['source_interior']=False
            elif change=='limit':p['max_route_length']=8000
            else:p['steps'].pop()
            with self.subTest(change=change),self.assertRaises(ValueError):approach.corrected_contract(f['payload'],p)
        for entry,index in (({'run':'a'*16},0),({'status':'built'},0),({},1)):
            s={'family_index':index,'families':{'seed':entry}};before=copy.deepcopy(s)
            with self.assertRaisesRegex(ValueError,'unstarted'):approach.revise_remaining(b,s,{'seed':corrected(f['payload'])})
            self.assertEqual(s,before)

    def test_adopt_completed_active_child_then_correct_unstarted_family_without_replay(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);op=Operator(runs=td,client=c);b=brief();later=copy.deepcopy(b['families'][0])
            later.update(name='later',payload=payload());b['families'].append(later)
            # Represents a brief accepted before the new branch preflight gate.
            def legacy(p):
                q=corrected(p) if p['steps'][-1].get('kind')=='branch' else p
                validate_plan(q);return p
            with patch('bridge_operator.validate_plan',side_effect=legacy):run=op.plan_approach(b)['run']
            old='b'*16;adopted='c'*16
            edge=c.make_edge([0,0,2],[20,0,2],[20,0,0],[20,0,0])
            for ident,status in ((old,'needs_attention'),(adopted,'built')):
                op.path(ident).mkdir()
                p=copy.deepcopy(b['families'][0]['payload'])
                if ident==adopted:p['continuation']={'run':old}
                approach.live.atomic_json(op.path(ident)/'plan.json',p)
                approach.live.atomic_json(op.path(ident)/'state.json',{'status':status,'steps':{'one':{'edges':[edge]}},'bindings':{},'lineage':[]})
            s=approach.load(op.path(run)/'state.json');s.update(status='needs_attention',current_family='seed')
            s['families']['seed']={'run':old,'status':'needs_attention'}
            approach.live.atomic_json(op.path(run)/'state.json',s)
            immutable=(op.path(run)/'approach.json').read_bytes();old_state=(op.path(old)/'state.json').read_bytes()
            executed=[]
            def execute(child):
                p=approach.load(op.path(child)/'plan.json');executed.append(child)
                self.assertEqual(p['steps'][-1]['kind'],'connect');self.assertTrue(p['steps'][-1]['target_interior'])
                state=approach.load(op.path(child)/'state.json')
                row=c.make_edge([0,0,2],[20,0,2],[20,0,0],[20,0,0])
                state.update(status='built',steps={'one':{'edges':[row]}},bindings={},lineage=[])
                approach.live.atomic_json(op.path(child)/'state.json',state)
                return {'status':'built'}
            with patch.object(op,'execute',side_effect=execute):
                result=op.continue_approach(run,family_run=adopted,remaining_families={'later':corrected(later['payload'])})
            self.assertEqual(result['status'],'built',result);self.assertEqual(len(executed),1)
            self.assertNotIn(old,executed);self.assertNotIn(adopted,executed)
            self.assertEqual((op.path(run)/'approach.json').read_bytes(),immutable)
            self.assertEqual((op.path(old)/'state.json').read_bytes(),old_state)
            state=approach.load(op.path(run)/'state.json')
            self.assertEqual(state['families']['seed']['run'],adopted)
            self.assertEqual(state['remaining_family_contracts']['later']['source_hash'],digest(later['payload']))


if __name__=='__main__':unittest.main()
