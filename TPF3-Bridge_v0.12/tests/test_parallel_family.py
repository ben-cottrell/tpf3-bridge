"""Offline family input/dependency/forwarding tests; native geometry is not simulated."""
import copy
import json
import math
import tempfile
import unittest
from unittest.mock import patch

from bridge_corridor import compile_corridor
from bridge_operator import Operator, validate_group_offsets
from test_corridor_operator import Native, brief


def family(roads=2,graded=False):
    b=brief(roads)
    b['max_grade']=.025
    for index,profiles in enumerate(b['waypoints'].values()):
        angle=math.radians(index*5);d=(math.cos(angle),math.sin(angle))
        for j,(name,p) in enumerate(profiles.items()):
            p.update(position=[index*600-j*5*d[1],index*30+j*5*d[0],10+(index*3 if graded else 0)],direction=list(d),grade=0)
    for section in b['sections']:
        section['region']={'min':[int(section['name'][-1])*600-30,-30,0],
                           'max':[(int(section['name'][-1])+1)*600+30,150,40]}
        section['members'][0]['representation']='native_parts'
        for i,member in enumerate(section['members'][1:],1):
            member['normal_offset_from']={'group_index':1,'spacing':5*i,'reverse':False}
    return b


class FamilyTests(unittest.TestCase):
    def test_curved_level_and_graded2_and4_keep_one_reference_and_constraints(self):
        for count in (2,4):
            for graded in (False,True):
                b=family(count,graded);compiled=compile_corridor(b)
                for section in compiled['sections']:
                    members=section['plan']['steps'][-1]['groups']
                    self.assertEqual(len(members),count);self.assertNotIn('normal_offset_from',members[0])
                    self.assertEqual(members[0]['representation'],'native_parts')
                    self.assertEqual(section['plan']['max_grade'],.025)
                    self.assertTrue(all(m['normal_offset_from']['group_index']==1 for m in members[1:]))
                    self.assertTrue(all('structures' not in m for m in members[1:]))

    def test_order_dependencies_spacing_and_inherited_only_fields(self):
        members=compile_corridor(family(4))['sections'][0]['plan']['steps'][-1]['groups']
        mutations=[lambda v:v[0].update(normal_offset_from={'group_index':1,'spacing':5,'reverse':False}),
                   lambda v:v[1]['normal_offset_from'].update(group_index=2),
                   lambda v:v[1]['normal_offset_from'].update(group_index=True),
                   lambda v:v[1]['normal_offset_from'].update(prepared_request='old'),
                   lambda v:v[1]['normal_offset_from'].update(spacing=0),
                   lambda v:v[1]['normal_offset_from'].update(spacing=float('nan')),
                   lambda v:v[1]['normal_offset_from'].update(spacing=61),
                   lambda v:v[1]['normal_offset_from'].update(reverse=1),
                   lambda v:v[1].update(structures=[{'classification':'NORMAL'}]),
                   lambda v:v[1].update(representation='endpoint_cubic'),
                   lambda v:v[2].pop('normal_offset_from'),
                   lambda v:v[2]['normal_offset_from'].update(spacing=5)]
        for change in mutations:
            value=copy.deepcopy(members);change(value)
            with self.subTest(value=value),self.assertRaises(ValueError):validate_group_offsets(value)
        members[2]['normal_offset_from'].update(group_index=2,spacing=5)
        validate_group_offsets(members)

    def test_reverse_dependency_offset_is_interpreted_in_reference_direction(self):
        members=compile_corridor(family(4))['sections'][0]['plan']['steps'][-1]['groups']
        members[1]['normal_offset_from']['reverse']=True
        members[2]['normal_offset_from'].update(group_index=2,spacing=5)
        with self.assertRaisesRegex(ValueError,'repeats'):validate_group_offsets(members)
        members[2]['normal_offset_from']['spacing']=-5;validate_group_offsets(members)

    def test_inherited_structure_minimum_keeps20_total_bound(self):
        b=family(4)
        # Three spans on each of two reference guide legs imply24 family segments.
        for s in b['sections']:
            a=b['waypoints'][s['source']]['up']['position'];z=b['waypoints'][s['target']]['up']['position']
            s['members'][0]['guides']=[{'position':[(x+y)/2 for x,y in zip(a,z)],'travel_direction':[1,0],'grade':0}]
            s['members'][0]['structures']=[{'spans':[{'classification':'NORMAL','until_u':u} for u in (.3,.6,1)]}]*2
        with self.assertRaisesRegex(ValueError,'20 grouped segments'):compile_corridor(b)

    def test_bridge_tunnel_intent_lives_on_reference(self):
        for classification in ('BRIDGE','TUNNEL'):
            b=family(4)
            for section in b['sections']:section['members'][0]['structures']=[{'classification':classification,'resource_name':'observed_resource'}]
            compiled=compile_corridor(b)
            for section in compiled['sections']:
                groups=section['plan']['steps'][-1]['groups']
                self.assertEqual(groups[0]['structures'][0]['classification'],classification)
                self.assertTrue(all('structures' not in g for g in groups[1:]))

    def test_operator_forwards_local_selector_without_independent_sibling_fit_controls(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);operator=Operator(runs=td,client=native)
            run=operator.plan_corridor(family(4,True))['run']
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):result=operator.build_corridor(run)
            self.assertEqual(result['status'],'built',result)
            preparations=[p for op,p in native.calls if op=='structured_chain' and p.get('prepare')]
            self.assertEqual(len(preparations),2)
            for p in preparations:
                self.assertEqual(p['groups'][0]['representation'],'native_parts')
                for g in p['groups'][1:]:
                    self.assertEqual(g['normal_offset_from']['group_index'],1)
                    self.assertEqual(g['vertical']['max_grade'],.025)
                    self.assertTrue(all(key not in g for key in ('representation','structures','handle_scale','fit_radius')))
                    self.assertIn('edge_snapshot',g['source']);self.assertIn('edge_snapshot',g['target'])

    def test_unknown_group_result_stops_without_repeating_family(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);native.unknown_group=1;operator=Operator(runs=td,client=native)
            run=operator.plan_corridor(family())['run']
            with patch('bridge_operator.live._select_throat_port',side_effect=native.select):
                result=operator.build_corridor(run);self.assertEqual(result['status'],'needs_attention')
                before=len(native.calls);again=operator.continue_corridor(run)
            self.assertEqual(again['status'],'needs_attention');self.assertEqual(len(native.calls),before)


if __name__=='__main__':unittest.main()
