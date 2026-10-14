"""Explicit tunnel waypoint compilation, independent of native acceptance."""
import copy
import unittest

from bridge_corridor import compile_corridor
from test_corridor_operator import brief


TUNNEL={'classification':'TUNNEL','resource_name':'observed.tunnel'}


def tunnel_brief():
    b=brief()
    for section in b['sections']:
        for member in section['members']:member['structures']=[copy.deepcopy(TUNNEL)]
    for profile in b['waypoints']['w1'].values():profile['seed_structure']=copy.deepcopy(TUNNEL)
    return b


class SeedTests(unittest.TestCase):
    def test_omitted_seed_keeps_exact_normal_stub_defaults(self):
        p=compile_corridor(brief())['sections'][0]['plan']
        self.assertEqual(p['steps'][0],{'name':'corr_seed_0_up','kind':'stub','port':'seed_origin_0','direction':[1,0],'grade':.01,'length':10})
        self.assertFalse(any(s['kind']=='structure_seed' for s in p['steps']))
        self.assertFalse(any(n.startswith('seed_end_') for n in p['ports']))

    def test_same_centred_positions_outward_grades_identity_and_later_binding(self):
        compiled=compile_corridor(tunnel_brief());p=compiled['sections'][0]['plan']
        seed=next(s for s in p['steps'] if s['name']=='corr_seed_1_up')
        self.assertEqual(seed['kind'],'structure_seed');self.assertEqual(seed['structure'],TUNNEL)
        self.assertEqual(p['ports'][seed['source']],{'position':[595,0,15.95],'direction':[-1,0],'grade':-.01})
        self.assertEqual(p['ports'][seed['target']],{'position':[605,0,16.05],'direction':[1,0],'grade':.01})
        self.assertEqual(p['port_refs']['back_1'],{'chain':'corr_seed_1_up','end':'node0'})
        self.assertIn('corr_seed_1_up',compiled['sections'][1]['required_bindings'])
        self.assertFalse(any(s['name']=='corr_seed_1_up' for s in compiled['sections'][1]['plan']['steps']))

    def test_invalid_seed_and_each_incident_resource_or_class_mismatch(self):
        for invalid in ({'classification':'NORMAL','resource_name':'x'},
                        {'classification':'BRIDGE','resource_name':'x'},
                        {'classification':'TUNNEL','resource_name':''},{'classification':'TUNNEL'}):
            b=tunnel_brief();b['waypoints']['w1']['up']['seed_structure']=invalid
            with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,'seed_structure'):compile_corridor(b)
        for section in (0,1):
            for bad in ({'classification':'NORMAL'},TUNNEL|{'resource_name':'other'}):
                b=tunnel_brief();b['sections'][section]['members'][0]['structures']=[bad]
                with self.subTest(section=section,bad=bad),self.assertRaisesRegex(ValueError,'adjoining'):compile_corridor(b)

    def test_only_adjoining_terminal_span_and_reversed_inheritance(self):
        b=brief();b['waypoints']['w1']['up']['seed_structure']=copy.deepcopy(TUNNEL)
        # Reference arrives tunnel, leaves tunnel. Reversed derivative arrives
        # NORMAL and leaves NORMAL: its boundary order must be swapped.
        for i,section in enumerate(b['sections']):
            spans=([{'classification':'NORMAL','until_u':.5},TUNNEL|{'until_u':1}]
                   if i==0 else [TUNNEL|{'until_u':.5},{'classification':'NORMAL','until_u':1}])
            section['members'][0]['structures']=[{'spans':spans}]
            section['members'][1]={'track':'down','normal_offset_from':{'group_index':1,'spacing':5,'reverse':True}}
        compile_corridor(b)
        b['waypoints']['w1']['down']['seed_structure']=copy.deepcopy(TUNNEL)
        with self.assertRaisesRegex(ValueError,'adjoining'):compile_corridor(b)
        for section in b['sections']:section['members'][1]['normal_offset_from']['reverse']=False
        compile_corridor(b)


if __name__=='__main__':unittest.main()
