import tempfile
from pathlib import Path
from copy import deepcopy
import json
import unittest
from railbranch.demo import *

class BranchDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.f=read_json(ROOT/'proof/branch_fixtures/release.json')
    def test_grid_scope_and_fits(self):
        r=search_geometry(self.f);self.assertEqual((r['grid_size'],r['evaluated'],r['accepted_count']),(17,17,5))
        self.assertEqual(r['selected_by_mode']['flyover']['ramp_m'],750)
    def test_zero_search_not_infeasibility(self):
        r=search_geometry(self.f,0);self.assertEqual(r['status'],'search_exhausted');self.assertEqual(r['evaluated'],0)
    def test_small_budget_distinct_from_complete_grid(self):self.assertEqual(search_geometry(self.f,2)['status'],'search_exhausted')
    def test_unknown_fixture_field_rejected(self):
        f=deepcopy(self.f);f['ignore_constraints']=True
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_fidelity_cannot_claim_authentic(self):
        f=deepcopy(self.f);f['fidelity']='authentic_uk'
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_missing_junction_field_rejected(self):
        f=deepcopy(self.f);f['junction'].pop('ramp_m')
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_duplicate_search_values_rejected(self):
        f=deepcopy(self.f);f['ramp_trials_m']=[750,750]
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_unknown_manufacturer_field_rejected(self):
        f=deepcopy(self.f);f['formation_reference_key']='assumed_bogie_spacing'
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_repetition_budget_enforced(self):
        f=deepcopy(self.f);f['repetitions']=10000
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_complete_demo_and_replay(self):
        f=deepcopy(self.f);f['repetitions']=1
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';r=run(f,a);q=run(f,b)
            self.assertEqual(r,q);self.assertEqual(r['operating_comparisons'],30)
            self.assertEqual(sorted(p.name for p in a.iterdir()),sorted(p.name for p in b.iterdir()))
            for p in a.iterdir():self.assertEqual(p.read_bytes(),(b/p.name).read_bytes(),p.name)
            self.assertFalse(r['same_as_v09_terrain_route']);self.assertFalse(r['construction_authorised'])
            inp=json.loads((a/'input_provenance.json').read_text());self.assertEqual(inp['formation_length_m'],242.6)
            self.assertEqual(inp['gb_nominal_centres_reference']['status'],'reference_value')
            ds=json.loads((a/'decision_packets.json').read_text());self.assertEqual(ds[1]['alternatives'],[])
