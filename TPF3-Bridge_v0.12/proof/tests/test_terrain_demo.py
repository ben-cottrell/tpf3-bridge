import unittest
import tempfile
from pathlib import Path
from copy import deepcopy
from terrain_support import inputs
from railclear.catalogue import read_json
from railterrain.planning import search,validate_fixture
from railterrain.demo import run,decisions

class TerrainDemoTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.f,cls.c,cls.b=inputs()
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  cls.r=run(cls.f,cls.root/'first')
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_full_grid_counts_actual_outcomes(self):
  self.assertEqual(self.r['evaluated'],24);self.assertEqual(self.r['accepted'],6)
 def test_all_chosen_offsets_and_interfaces(self):
  for row in self.r['selected_placements']:self.assertEqual(row['lateral_m'],280);self.assertEqual(row['layout'],'east_shifted_toes')
  self.assertEqual(self.r['preserved_external_interfaces'],6)
 def test_common_scenario_hashes(self):
  for scenario in {r['scenario'] for r in self.r['rows']}:
   rows=[r for r in self.r['rows'] if r['scenario']==scenario]
   self.assertEqual(len({r['scenario_hash'] for r in rows}),1)
 def test_complete_work_and_retained_merge(self):
  for r in self.r['rows']:
   self.assertEqual(r['completed']+r['unscheduled']+r['residual'],r['required'])
   if r['scenario']=='merge_pulse':self.assertGreater(r['delay_s'],0)
 def test_constrained_terrain_changes_the_civil_options(self):
  rows={r['mode']:r for r in self.r['selected_placements']}
  self.assertGreater(rows['diveunder']['tunnel_track_m'],rows['flyover']['tunnel_track_m'])
  self.assertGreater(rows['flyover']['elevated_track_m'],rows['flat']['elevated_track_m'])
 def test_no_site_station_game_or_dynamic_promotion(self):
  self.assertFalse(self.r['construction_authorised']);self.assertFalse(self.r['station_internal_edits'])
  self.assertFalse(self.r['actual_structures_built']);self.assertFalse(self.r['grade_sensitive_performance']);self.assertEqual(self.r['game_calls'],0)
 def test_replay_all_outputs_identical(self):
  run(self.f,self.root/'second')
  a={p.name:p.read_bytes() for p in (self.root/'first').iterdir()}
  b={p.name:p.read_bytes() for p in (self.root/'second').iterdir()}
  self.assertEqual(a,b)
 def test_rejected_grid_is_not_fabricated_comparison(self):
  f=deepcopy(self.f);f['candidate_budget']=0;r=run(f,self.root/'none')
  self.assertTrue(r['full_comparison_not_run']);self.assertEqual(r['status'],'search_exhausted')
 def test_stale_joined_result_rejected(self):
  bindings={m:read_json(self.root/'first'/f'{m}__terrain_binding.json') for m in ('flat','flyover','diveunder')}
  results={(m,'merge_pulse'):read_json(self.root/'first'/f'{m}__merge_pulse.json') for m in bindings}
  results[('flyover','merge_pulse')]['terrain_design_hash']='other'
  with self.assertRaises(ValueError):decisions(bindings,results,'merge_pulse',0)
 def test_decision_keeps_failed_merge_objective(self):
  p=read_json(self.root/'first'/'decision_packets.json')
  r=next(x for x in p if x['scenario']=='merge_pulse');self.assertEqual(r['alternatives'],[])
  self.assertEqual(r['status'],'no_tested_design_meets_outcome')
