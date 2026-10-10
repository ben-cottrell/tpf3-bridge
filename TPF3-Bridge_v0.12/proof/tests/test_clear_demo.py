import copy
import json
from pathlib import Path
import tempfile
import unittest
from railclear.demo import run, read_fixture, extended_route, ROOT, EVIDENCE
from railclear.catalogue import import_component, read_json, place_synthetic
from railclear.model import Body, distance
from railgeom.patterns import build_crossover, Assembly, GeometryProfile
from railgeom.compiler import compile_assembly

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)
        cls.summary=run(ROOT/'clearance_fixtures/release.json',cls.out)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def read(self,name):return json.loads((self.out/name).read_text())
    def test_spacing_rows(self):self.assertEqual(self.summary['spacing_rows'],18)
    def test_crossover_distinct_vs_shared(self):self.assertEqual(self.summary['crossover_statuses'],['clear_within_polyline_static_model','sampled_body_contact','sampled_body_contact'])
    def test_refinement_not_changed_dimensions(self):
        r=self.read('straight_refinement.json');self.assertFalse(r['dimensions_changed']);self.assertEqual([s['status'] for s in r['runs']],['unresolved_between_poses','clear_within_polyline_static_model'])
    def test_no_removed_resources(self):self.assertEqual(self.summary['resource_mutations'],[])
    def test_parent_geometry_unchanged(self):self.assertTrue(self.read('crossover_clearance_overlay.json')['unchanged_network_hash'])
    def test_overhang_witness(self):self.assertEqual(self.summary['obstacle_status'],'sampled_body_contact')
    def test_actual_unit_lengths(self):
        r=self.read('published_formation_length_trial.json')['rows'];self.assertEqual([x['published_unit_length_m'] for x in r],[162.,242.6]);self.assertGreater(r[1]['arrival_stop_ms'],r[0]['arrival_stop_ms'])
    def test_fit_margins(self):
        r=self.read('published_formation_length_trial.json')['rows'];self.assertAlmostEqual(r[1]['spare_after_margins_m'],7.4);self.assertTrue(all(x['scalar_fit'] for x in r))
    def test_full_train_not_a_rigid_car(self):
        self.assertEqual(self.read('bank_route_sweep.json')['sweep']['whole_formation'],'not_modelled')
    def test_pending_authentic_component(self):
        r=self.read('component_import_results.json');self.assertFalse(r['authentic_component_imported']);self.assertEqual(r['pending_external']['status'],'reference_only_missing_geometry')
    def test_import_reaches_resource_compiler(self):
        r=self.read('component_import_results.json')['compiled_imported_geometry'];self.assertEqual(set(r['routes']),{'normal','reverse'})
        self.assertIn('component_body:SYNTH_IMPORT_T40',[x['resource'] for x in r['routes']['reverse']['requirements']])
    def test_generated_route_chord_errors(self):
        data=self.read('bank_route_sweep.json')['sweep'];B=data['body']['bogie_centres_m']
        self.assertGreater(data['pose_count'],100)
        for p in data['poses']:self.assertAlmostEqual(distance(p['front_bogie'],p['rear_bogie']),B,places=6)
    def test_profile_stays_unassessed(self):self.assertEqual(self.summary['assessments']['authentic_vehicle_gauge'],'unassessed')
    def test_report_demand_not_a_capacity_claim(self):self.assertFalse(self.read('decision_packet.json')['construction_authorised'])
    def test_record_hashes_present(self):self.assertEqual(len(self.summary['vehicle_record_hash']),64)
    def test_replay_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            other=Path(td);s=run(ROOT/'clearance_fixtures/release.json',other);self.assertEqual(s,self.summary)
            for p in self.out.iterdir():self.assertEqual(p.read_bytes(),(other/p.name).read_bytes())

class FixtureTests(unittest.TestCase):
    def setUp(self):self.f=read_fixture(ROOT/'clearance_fixtures/release.json')
    def bad(self,edit):
        edit(self.f)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'f.json';p.write_text(json.dumps(self.f))
            with self.assertRaises(ValueError):read_fixture(p)
    def test_bad_version(self):self.bad(lambda f:f.update(schema_version='0.6.0'))
    def test_no_authority(self):self.bad(lambda f:f.update(fidelity='UK_verified'))
    def test_unknown_fields(self):self.bad(lambda f:f.update(run_shell='bad'))
    def test_missing_assumption(self):self.bad(lambda f:f['assumptions'].pop('bogie_centres_m'))
    def test_unbounded_sensitivity(self):self.bad(lambda f:f.update(curve_radii_m=[400]*51))
    def test_bad_budget(self):self.bad(lambda f:f.update(max_pairs=True))
    def test_no_path_in_id(self):self.bad(lambda f:f.update(scenario_id='../../x'))
    def test_explicit_supports(self):
        a=build_crossover();p=extended_route(a,'lower_through',35)
        self.assertEqual(p.points[0],(-35.,0.));self.assertAlmostEqual(p.points[-1][0],135.)
    def test_missing_support_not_hidden(self):
        with self.assertRaises(ValueError):extended_route(build_crossover(),'lower_through',0)
