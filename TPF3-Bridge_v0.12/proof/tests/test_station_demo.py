import copy
import json
import tempfile
import unittest
from pathlib import Path
from railstation.demo import read_fixture,run
from railstation.assessment import vehicle_audit,assess_candidate
from station_support import ROOT,fixture,station

class StationFixtureTests(unittest.TestCase):
    def read_changed(self,key,value):
        f=copy.deepcopy(fixture());f[key]=value
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.json';p.write_text(json.dumps(f))
            return read_fixture(p)
    def test_valid_fixture(self):self.assertEqual(fixture()['schema_version'],'0.6.0')
    def test_unknown_top_level_field_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('arbitrary_command','execute')
    def test_duplicate_scenarios_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('scenarios',['nominal','nominal'])
    def test_path_like_scenario_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('scenarios',['../other'])
    def test_false_fidelity_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('fidelity','UK_approved')
    def test_unknown_station_parameter_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('station',{'secret_speed':99})
    def test_noninteger_budget_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('evaluation_budget',1.5)
    def test_invalid_vehicle_assumptions_rejected(self):
        with self.assertRaises(ValueError):self.read_changed('vehicle_assumptions',{})

class StationIntegratedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        f=copy.deepcopy(fixture());f['pairs']=2
        cls.path=cls.root/'fixture.json';cls.path.write_text(json.dumps(f))
        cls.summary=run(cls.path,cls.root/'first')
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def read(self,name):return json.loads((self.root/'first'/name).read_text())
    def test_full_36_comparison_pipeline(self):
        self.assertEqual(self.summary['comparison_count'],36);self.assertTrue(self.summary['all_independent_result_checks_passed'])
    def test_replay_is_byte_identical(self):
        run(self.path,self.root/'second')
        a={p.name:p.read_bytes() for p in (self.root/'first').iterdir()}
        b={p.name:p.read_bytes() for p in (self.root/'second').iterdir()}
        self.assertEqual(a,b)
    def test_all_selected_routes_have_vehicle_audit(self):
        v=self.read('a_to_b__vehicle.json');c=self.read('a_to_b__compiled.json')
        self.assertEqual({r['route_id'] for r in v['routes']},set(c['routes']))
        self.assertEqual(v['compile_hash'],c['compile_hash']);self.assertEqual(v['resource_mutations'],[])
    def test_static_normal_clearance_and_recovery_contact(self):
        rows=self.read('a_to_b__vehicle.json')['pairs']
        self.assertTrue(all(r['status']=='clear_within_polyline_static_model' for r in rows[:18]))
        self.assertTrue(all(r['status']=='sampled_body_contact' for r in rows[18:]))
    def test_sourced_rule_results_do_not_pass_strict_gate(self):
        a=self.read('a_to_b__assessment.json')
        self.assertEqual(a['selected_numerical_checks']['A1']['platform_cant']['status'],'pass')
        self.assertEqual(a['selected_numerical_checks']['A1']['GB_interface']['status'],'unassessed')
        self.assertFalse(a['strict_UK_input_gate']['offline_analysis_allowed']);self.assertFalse(a['construction_authorised'])
    def test_site_and_port_mismatches_recorded(self):
        a=self.read('a_to_b__assessment.json')
        self.assertEqual(a['original_brief_site']['status'],'fail')
        self.assertEqual(len(a['original_brief_site']['required_port_mismatches']),3)
        self.assertEqual(a['proposed_larger_test_site']['status'],'pass_within_scope')
        self.assertEqual(a['original_brief_site']['fixed_orientation_translation_certificate']['actual_port_x_span_m'],1970.)
    def test_each_scenario_points_to_same_candidate_assessment(self):
        a=self.read('a_to_b__nominal.json');b=self.read('a_to_b__bank_a_platforms_closed.json')
        self.assertEqual(a['candidate_assessment_hash'],b['candidate_assessment_hash'])
        self.assertEqual(a['compile_hash'],b['compile_hash'])
