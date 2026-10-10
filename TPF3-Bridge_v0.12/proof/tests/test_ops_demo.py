import json
from pathlib import Path
import tempfile
import unittest
from railops.demo import read_fixture, run, spacing_proxy_trial, numerical_examples, generated_bank_rule_checks, export_geometry_for_operations

FIXTURE=Path(__file__).resolve().parents[1]/'sectional_fixtures'/'release.json'

class DemoTests(unittest.TestCase):
    def bad(self,change):
        o=json.loads(FIXTURE.read_text());change(o)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text(json.dumps(o))
            with self.assertRaises(ValueError):read_fixture(p)
    def test_good_fixture(self):self.assertEqual(len(read_fixture(FIXTURE)['scenarios']),9)
    def test_no_extra_command_field(self):self.bad(lambda o:o.update(execute='anything'))
    def test_wrong_fidelity(self):self.bad(lambda o:o.update(fidelity='UK_approved'))
    def test_duplicate_scenario(self):self.bad(lambda o:o['scenarios'].append(o['scenarios'][0]))
    def test_path_traversal_id(self):self.bad(lambda o:o['scenarios'][0].update(id='../outside'))
    def test_extra_nested_field(self):self.bad(lambda o:o['motion'].update(invoke='x'))
    def test_invalid_scenario_length(self):self.bad(lambda o:o['scenarios'][0].update(length_override_m=-1))
    def test_invalid_closure_container(self):self.bad(lambda o:o['scenarios'][0].update(closed_platform_ids='P1'))
    def test_invalid_budget_units(self):self.bad(lambda o:o['scenarios'][0].update(evaluation_budget=.5))
    def test_invalid_cycle_flag(self):self.bad(lambda o:o['scenarios'][0].update(late_stock_cycle=1))
    def test_zero_visits_rejected(self):self.bad(lambda o:o.update(visits=[]))
    def test_reference_spacing_exposes_proxy_limit(self):
        r=spacing_proxy_trial()
        self.assertEqual(r['track_centres_m'],3.4)
        self.assertEqual(r['synthetic_proxy_required_separation_m'],4)
        self.assertFalse(r['proxy_independence_established'])
        self.assertEqual(r['actual_vehicle_clearance'],'unassessed')
    def test_nominal_spacing_creates_no_connection(self):
        r=spacing_proxy_trial();c=r['compiled_model']
        self.assertEqual(len(c['routes']),2)
        self.assertTrue(all(not p['rail_connection_created'] for p in r['proximity_resources']))
    def test_full_demo_real_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);r=run(FIXTURE,out)
            self.assertEqual(len(r['operating_comparisons']),18)
            self.assertEqual(r['external_approach_tracks'],2)
            self.assertFalse(r['construction_authorised'])
            self.assertTrue((out/'comparison.md').is_file())
            rows=r['operating_comparisons']
            for a,b in zip(rows[::2],rows[1::2]):
                self.assertEqual(a['scenario_sha256'],b['scenario_sha256'])
                self.assertEqual(a['required_visits'],b['required_visits'])
            for p in out.glob('*.json'):
                self.assertIsNotNone(json.loads(p.read_text()))
    def test_scoped_rules_can_disagree_without_error(self):
        r=numerical_examples()
        self.assertEqual(r['new_line_radius_at_floor']['status'],'pass')
        self.assertEqual(r['same_radius_at_platform']['status'],'fail')

    def test_selected_UK_checks_use_actual_compiled_bank(self):
        from railops.access import build_dual_access
        from railgeom.compiler import compile_assembly
        c=compile_assembly(build_dual_access());r=generated_bank_rule_checks(c)
        self.assertEqual(r['compile_hash'],c.compile_hash)
        self.assertEqual(r['horizontal_floor_check']['status'],'pass')
        self.assertEqual(r['platform_checks']['P1']['new_line_radius']['status'],'pass')
        self.assertEqual(r['platform_height_offset']['status'],'unassessed')
    def test_operating_export_does_not_mutate_legacy_timing_metadata(self):
        from railops.access import build_dual_access
        from railgeom.compiler import compile_assembly
        c=compile_assembly(build_dual_access());before=c.export()['provenance']['time_model']
        out=export_geometry_for_operations(c)
        self.assertEqual(c.provenance['time_model'],before)
        self.assertEqual(out['schema_version'],'0.4.0')
        self.assertNotEqual(out['provenance']['time_model'],before)
