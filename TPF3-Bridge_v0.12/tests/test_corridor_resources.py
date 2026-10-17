"""Per-road seed resources; no native conversion or attachment relaxation."""
import copy
import tempfile
import unittest

from bridge_corridor import compile_corridor
from bridge_operator import Operator
from test_corridor_operator import brief,Native


SLOW={'template':'slow.track','style':'slow.style'}
TUNNEL={'classification':'TUNNEL','resource_name':'observed.tunnel'}


class ResourceTests(unittest.TestCase):
    def test_default_output_unchanged_and_mixed_normal_tunnel_seed_overrides(self):
        b=brief(4);base=compile_corridor(b)
        self.assertFalse(any('track' in s for row in base['sections'] for s in row['plan']['steps']))
        b['track_by_road']={'up':SLOW,'down':SLOW}
        for section in b['sections']:
            for member in section['members']:member['structures']=[copy.deepcopy(TUNNEL)]
        for profile in b['waypoints']['w1'].values():profile['seed_structure']=copy.deepcopy(TUNNEL)
        c=compile_corridor(b)
        seeds=[s for row in c['sections'] for s in row['plan']['steps'] if s['kind'] in ('stub','structure_seed')]
        self.assertTrue(any(s['kind']=='stub' and s.get('track')==SLOW for s in seeds))
        self.assertTrue(any(s['kind']=='structure_seed' and s.get('track')==SLOW for s in seeds))
        self.assertTrue(all('track' not in s for s in seeds if s['name'].endswith(('fast_up','fast_down'))))
        for old,new in zip(base['sections'],c['sections']):
            self.assertEqual(old['created_bindings'],new['created_bindings'])
            self.assertEqual(old['required_bindings'],new['required_bindings'])

    def test_selected_import_mismatch_rejected_before_publishing_or_effects(self):
        with tempfile.TemporaryDirectory() as td:
            native=Native(td);op=Operator(runs=td,client=native);b=brief(4);b['bindings']={}
            for i,road in enumerate(b['waypoints']['w0']):
                row=native.make_edge([-10,i*5,9.9],[0,i*5,10],[10,0,.1],[10,0,.1])
                if road in ('up','down'):row.update(SLOW)
                b['bindings'][road]={'edges':[row]}
                b['waypoints']['w0'][road]={'front':{'chain':road,'edge_id':row['id'],'node_id':row['node1']}}
            with self.assertRaisesRegex(ValueError,'imported waypoint track resources'):op.plan_corridor(b)
            self.assertEqual(native.calls,[])
            b['track_by_road']={'up':SLOW,'down':SLOW}
            compiled=compile_corridor(b)
            self.assertEqual(len(compiled['sections'][0]['created_bindings']),4)
            self.assertEqual(len(compiled['sections'][0]['plan']['steps'][-1]['groups']),4)
            b['bindings']['fast_down']['edges'][0]['style']='other'
            with self.assertRaisesRegex(ValueError,'imported waypoint track resources'):compile_corridor(b)

    def test_invalid_unknown_or_incomplete_resources(self):
        for overrides in ({'unknown':SLOW},{'up':{}},{'up':{'template':'x','style':''}},
                          {'up':SLOW|{'extra':True}},['up']):
            b=brief(4);b['track_by_road']=overrides
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):compile_corridor(b)

    def test_derived_reference_requires_identical_resources_including_reverse(self):
        for reverse in (False,True):
            b=brief();b['track_by_road']={'down':SLOW}
            for section in b['sections']:
                section['members'][1]={'track':'down','normal_offset_from':{'group_index':1,'spacing':5,'reverse':reverse}}
            with self.assertRaisesRegex(ValueError,'derived family requires matching'):compile_corridor(b)
            b['track_by_road']['up']=SLOW;compile_corridor(b)


if __name__=='__main__':unittest.main()
