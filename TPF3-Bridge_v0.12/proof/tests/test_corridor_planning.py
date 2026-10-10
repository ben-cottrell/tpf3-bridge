import unittest
from copy import deepcopy
from pathlib import Path
import tempfile
from railcorridor.planning import *
from railcorridor.junction import *


def fixture():return validate_fixture(parse_json(Path(__file__).parents[1]/'corridor_fixtures/release.json'))


class PlanningTests(unittest.TestCase):
    def setUp(self):self.f=fixture()
    def test_grid_count_and_retained_rejections(self):
        s=search(self.f);self.assertEqual(s['evaluated'],12);self.assertEqual(len(s['candidates']),12);self.assertEqual(s['accepted'],9)
    def test_zero_budget_not_impossibility(self):
        s=search(self.f,budget=0);self.assertEqual(s['status'],'search_exhausted');self.assertEqual(s['evaluated'],0)
    def test_partial_grid_not_complete(self):self.assertEqual(search(self.f,budget=2)['status'],'search_exhausted')
    def test_budget_boolean_rejected(self):
        with self.assertRaises(ValueError):search(self.f,budget=True)
    def test_direct_has_tunnel(self):self.assertGreater(candidate(self.f,0,20)['terrain']['lengths_m']['tunnel'],0)
    def test_bypass_avoids_tunnel(self):self.assertEqual(candidate(self.f,280,20)['terrain']['lengths_m']['tunnel'],0)
    def test_every_candidate_crosses_river(self):
        for c in search(self.f)['candidates']:self.assertGreaterEqual(c['terrain']['lengths_m']['river_bridge'],250)
    def test_south_obstacle_witness(self):
        c=candidate(self.f,-280,20);self.assertFalse(c['accepted_for_reference_comparison']);self.assertTrue(c['site']['actual_formation_witnesses'])
    def test_no_station_edit(self):self.assertFalse(candidate(self.f,280,20)['station_interfaces']['station_internal_edits'])
    def test_nominal_reference_not_clearance_approval(self):
        c=candidate(self.f,280,20)
        self.assertTrue(c['selected_spacing_matches_nominal_reference']);self.assertEqual(c['uk_complete_assessment'],'unassessed')
    def test_water_clearance_hard_failure(self):
        f=deepcopy(self.f);f['terrain']['water_level_m']=22
        c=candidate(f,0,20);self.assertFalse(c['accepted_for_reference_comparison']);self.assertTrue(c['terrain']['river_clearance_failures'])
    def test_terrain_revision_invalidates_candidate(self):
        f=deepcopy(self.f);f['terrain']['revision']='new'
        self.assertNotEqual(candidate(f,0,20)['candidate_hash'],candidate(self.f,0,20)['candidate_hash'])
    def test_civil_choice_changes_estimate(self):
        f=deepcopy(self.f);f['civil']['formation_width_m']=10
        self.assertNotEqual(candidate(f,0,20)['terrain']['cut_estimate_m3'],candidate(self.f,0,20)['terrain']['cut_estimate_m3'])
    def test_earthworks_counted_once(self):
        r=candidate(self.f,280,20)['terrain'];self.assertIn('one double-track formation',r['units'])
    def test_no_terrain_gaps(self):
        r=candidate(self.f,0,20)['terrain']['runs']
        self.assertEqual(r[0]['x0'],0);self.assertEqual(r[-1]['x1'],6000)
        for a,b in zip(r,r[1:]):self.assertEqual(a['x1'],b['x0'])
    def test_pareto_contains_only_accepted(self):
        s=search(self.f);valid={c['candidate_hash'] for c in s['candidates'] if c['accepted_for_reference_comparison']}
        self.assertTrue(set(s['pareto_candidate_hashes'])<=valid)
    def test_strict_unknown_field(self):
        f=deepcopy(self.f);f['fake_api']=1
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_duplicate_axis(self):
        f=deepcopy(self.f);f['search']['lateral_offsets_m']=[0,0]
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_bad_river(self):
        f=deepcopy(self.f);f['terrain']['river_x1_m']=1000
        with self.assertRaises(ValueError):validate_fixture(f)
    def test_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):parse_json(p)
    def test_nan_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):parse_json(p)
    def test_source_input_not_mutated(self):
        old=deepcopy(self.f);candidate(self.f,0,20);self.assertEqual(old,self.f)


class CrossingTests(unittest.TestCase):
    def setUp(self):self.f=fixture()
    def test_short_ramp_rejected_despite_clear_crossing(self):
        c=crossing_cell(self.f,'flyover',600)
        self.assertGreater(c['clearance_margin_m'],0);self.assertFalse(c['project_cell_geometry_pass'])
        self.assertEqual(c['crossing_conflicts_with_main'],2)
    def test_longer_ramp_preserves_grade_target(self):
        c=crossing_cell(self.f,'flyover',750)
        self.assertTrue(c['project_cell_geometry_pass']);self.assertLess(c['bounds']['grade_upper'],.02)
    def test_full_ramp_span_included(self):self.assertEqual(crossing_cell(self.f,'flyover',750)['total_approach_span_m'],1600)
    def test_diveunder_sign_and_drainage(self):
        c=crossing_cell(self.f,'diveunder',750)
        self.assertLess(min(p[2] for p in c['branch_polyline']),c['main_rail_z_m'])
        self.assertIn('drainage/groundwater for diveunder',c['unassessed'])
    def test_flat_keeps_both_crossings(self):
        c=crossing_cell(self.f,'flat',750);self.assertEqual(c['crossing_conflicts_with_main'],2)
    def test_grade_separation_not_turning_connection(self):
        c=crossing_cell(self.f,'flyover',750)
        self.assertEqual(c['crossing_conflicts_with_main'],0);self.assertEqual(c['turning_connections_at_crossing'],[])
    def test_missing_turnouts_not_claimed_connected(self):self.assertFalse(crossing_cell(self.f,'flyover',750)['full_branch_junction_connected'])
    def test_low_height_rejected(self):self.assertFalse(crossing_cell(self.f,'flyover',750,height_m=6)['project_cell_geometry_pass'])
    def test_full_footprint_not_centre_only(self):
        c=crossing_cell(self.f,'flyover',750,height_m=6.8,plateau_m=1)
        self.assertLess(c['minimum_rail_separation_m'],c['required_project_separation_m'])
    def test_grade_end_conditions(self):
        c=crossing_cell(self.f,'flyover',750)
        self.assertEqual(c['branch_ports'][0][2],20);self.assertEqual(c['branch_ports'][1][2],20)
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):crossing_cell(self.f,'viaductish',750)
    def test_holding_fit_uses_whole_formation(self):
        self.assertFalse(holding_check(250,242.6,10,10)['fits_clear'])
        self.assertTrue(holding_check(275,242.6,10,10)['fits_clear'])
    def test_braking_is_separate_from_static_fit(self):
        self.assertTrue(holding_check(300,242.6,10,10)['fits_clear'])
        self.assertFalse(braking_screen(60,.7,2,300)['sufficient_within_model'])
    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):holding_check(250,162,-1,10)
    def test_braking_formula_oracle(self):
        v=60*.44704;self.assertAlmostEqual(braking_screen(60,.7,2,600)['required_m'],2*v+v*v/1.4)

    def test_cell_cannot_claim_site_fit_outside_region(self):
        f=deepcopy(self.f);f['corridor']['site']=[-5,-600,6005,600]
        c=crossing_cell(f,'flyover',750)
        self.assertTrue(c['project_cell_geometry_pass']);self.assertFalse(c['accepted_for_cell_comparison'])
