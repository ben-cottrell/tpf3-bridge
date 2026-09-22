import unittest
import tempfile
from pathlib import Path
import json
from railcorridor.demo import run
from railcorridor.planning import parse_json,validate_fixture


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.f=validate_fixture(parse_json(Path(__file__).parents[1]/'corridor_fixtures/release.json'))
        cls.s=run(cls.f,cls.root/'a');run(cls.f,cls.root/'b')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def get(self,name):return json.loads((self.root/'a'/name).read_text())
    def test_replay_exact(self):
        a=self.root/'a';b=self.root/'b'
        self.assertEqual(sorted(p.name for p in a.iterdir()),sorted(p.name for p in b.iterdir()))
        for p in a.iterdir():self.assertEqual(p.read_bytes(),(b/p.name).read_bytes(),p.name)
    def test_all_candidates_accounted(self):self.assertEqual(len(self.s['corridor_rows']),12)
    def test_station_frozen(self):self.assertFalse(self.s['station_internal_edits'])
    def test_no_game_calls(self):self.assertEqual(self.s['actual_game_calls'],0);self.assertFalse(self.s['real_network_constructed'])
    def test_no_complete_junction_claim(self):self.assertFalse(self.s['complete_branch_junction'])
    def test_same_parameters_for_parallel_tracks(self):
        r=self.get('selected_track_polylines.json')
        self.assertEqual(r['eastbound']['parent_alignment_hash'],r['westbound']['parent_alignment_hash'])
    def test_changed_speed_keeps_target(self):
        r=self.get('bounded_and_changed_brief_trials.json');self.assertEqual(r['higher_speed']['speed_mph'],100)
        self.assertLess(r['higher_speed']['accepted'],9)
    def test_crossing_ramp_grid_retains_failures(self):
        r=self.get('crossing_cells.json');self.assertEqual(len(r),9);self.assertEqual(sum(x['project_cell_geometry_pass'] for x in r),7)
    def test_no_infinite_json(self):
        for p in (self.root/'a').glob('*.json'):
            json.loads(p.read_text(),parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    def test_plan_bound_to_chosen_candidate(self):
        p=self.get('mock_construction_plan.json');c=self.get('selected_corridor.json')
        self.assertEqual(p['candidate_hash'],c['candidate_hash'])
    def test_unchanged_dimensions_in_shorter_trial(self):self.assertFalse(self.get('bounded_and_changed_brief_trials.json')['shorter_corridor']['train_lengths_rescaled'])
    def test_default_capabilities_still_unknown(self):
        c=self.get('tpf3_unprobed_capabilities.json')
        self.assertTrue(all(x['state']=='unknown' for x in c['capabilities'].values()))
