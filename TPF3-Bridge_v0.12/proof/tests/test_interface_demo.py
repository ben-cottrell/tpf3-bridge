import copy
import json
from pathlib import Path
import tempfile
import unittest
from railinterface.demo import read_fixture,run,ROOT

class InterfaceDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.f=read_fixture(ROOT/'interface_fixtures/release.json');cls.f['operating_pairs']=2
        cls.fixture=cls.root/'fixture.json';cls.fixture.write_text(json.dumps(cls.f))
        cls.summary=run(cls.fixture,cls.root/'one')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def read(self,name):return json.loads((self.root/'one'/name).read_text())
    def changed(self,key,value):
        f=copy.deepcopy(self.f);f[key]=value
        p=self.root/'bad.json';p.write_text(json.dumps(f));return p
    def test_nine_verified_comparisons(self):
        self.assertEqual(self.summary['comparison_count'],9);self.assertTrue(self.summary['all_independent_checks_passed'])
    def test_generated_face_count(self):self.assertEqual(self.summary['boarding_faces'],8)
    def test_platform_surfaces_fit_original_site(self):self.assertEqual(self.summary['original_plan_with_platform_reservations'],'pass_within_scope')
    def test_initial_loses_A_bank_recovery(self):
        r=self.read('initial__bank_a_platforms_closed.json')
        self.assertEqual(r['required_visits'],4);self.assertEqual(r['scheduled_visits'],2)
        self.assertEqual(r['planning_exclusion']['excluded_platform_ids'],['B1'])
    def test_refit_restores_same_required_demand(self):
        r=self.read('locally_refitted__bank_a_platforms_closed.json')
        self.assertEqual(r['required_visits'],4);self.assertEqual(r['completed_within_horizon'],4)
    def test_oversize_still_loses_recovery(self):
        r=self.read('oversize__bank_a_platforms_closed.json')
        self.assertEqual(r['scheduled_visits'],2);self.assertEqual(r['planning_exclusion']['excluded_platform_ids'],['B1','B2'])
    def test_refit_does_not_change_track_identity(self):
        a=self.read('initial__bank_a_platforms_closed.json');b=self.read('locally_refitted__bank_a_platforms_closed.json')
        self.assertEqual(a['compile_hash'],b['compile_hash']);self.assertEqual(a['platform_assessment_hash'],b['platform_assessment_hash'])
        self.assertNotEqual(a['facility_check_hash'],b['facility_check_hash'])
    def test_real_values_no_full_component_claim(self):
        r=self.read('component_evidence_audit.json');self.assertFalse(r['authentic_complete_turnout_imported']);self.assertTrue(r['station_pointwork_unchanged'])
    def test_source_datum_regression(self):
        r=self.read('datum_and_clause_examples.json');self.assertEqual(r['wrong_datum_check']['status'],'reference_clause_fail')
    def test_current_uk_scope_not_silently_promoted(self):
        self.assertEqual(self.summary['current_uk_compliance'],'unassessed');self.assertFalse(self.summary['construction_authorised'])
    def test_nearest_fit_and_centred_margin_distinct(self):
        r=self.read('facility_search.json')
        self.assertAlmostEqual(r['nearest_authorised_fit']['check']['edge_gaps_m'][0],2.5)
        self.assertAlmostEqual(r['centred_same_size']['edge_gaps_m'][0],2.545)
    def test_no_hidden_track_move_for_oversize(self):
        r=self.read('speed_and_space_sensitivity.json')
        self.assertAlmostEqual(r['minimum_centres_for_oversize_facility_m'],12.11);self.assertFalse(r['track_movement_authorised'])
    def test_full_replay_is_byte_identical(self):
        run(self.fixture,self.root/'two')
        a={p.name:p.read_bytes() for p in (self.root/'one').iterdir()}
        b={p.name:p.read_bytes() for p in (self.root/'two').iterdir()}
        self.assertEqual(a,b)
    def test_zero_fit_budget_no_fabricated_refit_case(self):
        p=self.changed('fit_budget',0);s=run(p,self.root/'zero')
        self.assertEqual(s['comparison_count'],6);self.assertEqual(s['local_fit_status'],'search_exhausted')
    def test_no_exclusion_without_policy(self):
        p=self.changed('exclude_failed_boarding_faces',False);s=run(p,self.root/'diagnostic')
        self.assertTrue(all(not r['excluded_faces'] for r in s['comparison_rows']))
    def test_unknown_fixture_field(self):
        p=self.changed('arbitrary_python','ignored')
        with self.assertRaises(ValueError):read_fixture(p)
    def test_wrong_fixture_version(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('schema_version','0.9.0'))
    def test_invalid_family(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('family','../scissors'))
    def test_invalid_pairs(self):
        for value in (0,True,25):
            with self.assertRaises(ValueError):read_fixture(self.changed('operating_pairs',value))
    def test_invalid_permission(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('exclude_failed_boarding_faces',1))
    def test_missing_speed_origin(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('permissible_speed_origin',''))
    def test_duplicate_scenarios(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('operating_scenarios',['nominal','nominal']))
    def test_unknown_scenario(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('operating_scenarios',['live_game']))
    def test_malformed_numeric_fixture(self):
        with self.assertRaises(ValueError):read_fixture(self.changed('facility_width_m',float('nan')))
