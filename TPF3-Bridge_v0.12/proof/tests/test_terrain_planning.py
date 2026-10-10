import unittest
import math
from copy import deepcopy
from terrain_support import model,inputs
from railterrain.planning import bind,verify_binding,search,validate_fixture,boundary_check
from railterrain.terrain import assess,ground_range,bell_range,rectangle_union_area
from railcorridor.planning import ground
from railcorridor.geometry import digest

class TerrainPlanningTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.f,cls.c,cls.b,cls.j=model();cls.a=bind(cls.j,cls.c,cls.f)
 def test_all_physical_edges_assessed(self):
  t=self.a['terrain'];self.assertEqual(t['unique_physical_edges_assessed'],16)
  self.assertEqual({r['edge_id'] for r in t['terrain_rows']},set(self.j.network.edges))
 def test_river_boundaries_are_not_skipped(self):
  lo,hi=self.c['terrain']['river_x0_m'],self.c['terrain']['river_x1_m']
  wet=[r for r in self.a['terrain']['terrain_rows'] if r['kind']=='river_bridge']
  self.assertTrue(wet)
  for r in wet:
   self.assertGreaterEqual(r['x_interval_m'][0],lo);self.assertLessEqual(r['x_interval_m'][1],hi)
   self.assertGreater(r['river_clearance_margin_m'],0)
 def test_original_turnouts_over_river_are_rejected(self):
  f,c,_,j=model(offset=0,layout_index=0);a=bind(j,c,f)
  self.assertIn('specialwork_structure_interface_unsupported',a['failures'])
 def test_protected_land_crossing_has_physical_witness(self):
  f,c,_,j=model(offset=0);a=bind(j,c,f)
  w=[r for r in a['terrain']['hard_failures'] if r['reason'].startswith('track_enters_protected_land')]
  self.assertTrue(w);self.assertTrue(any(r['edge_id']=='west_approach' for r in w))
 def test_selected_placement_passes_scoped_screen(self):self.assertTrue(self.a['accepted_for_reference_design'])
 def test_original_interfaces_and_targets_remain(self):
  self.assertTrue(self.a['boundary_check']['passed']);self.assertEqual(self.a['mainline_profile']['profile'],self.c['profile'])
 def test_narrow_site_is_not_silently_enlarged(self):
  c=deepcopy(self.c);c['corridor']['site']=[-5,-150,6005,300];a=bind(self.j,c,self.f)
  self.assertFalse(a['accepted_for_reference_design']);self.assertIn('reservation_outside_site',a['failures'])
 def test_raised_water_blocks_clearance(self):
  c=deepcopy(self.c);c['terrain']['water_level_m']=18;a=bind(self.j,c,self.f)
  self.assertIn('river_deck_clearance_failed',a['failures'])
 def test_changed_terrain_with_same_label_changes_hash(self):
  c=deepcopy(self.c);c['terrain']['ridge_height_m']+=1;a=bind(self.j,c,self.f)
  self.assertEqual(a['terrain_revision'],self.a['terrain_revision']);self.assertNotEqual(a['terrain_hash'],self.a['terrain_hash'])
 def test_ground_range_contains_dense_samples(self):
  t=self.c['terrain']
  for box in ([2400,100,2850,280],[3200,-200,3500,100],[2250,-340,2450,-100]):
   lo,hi=ground_range(t,box)
   for i in range(21):
    for k in range(21):
     v=ground(t,box[0]+(box[2]-box[0])*i/20,box[1]+(box[3]-box[1])*k/20)
     self.assertGreaterEqual(v,lo-1e-9);self.assertLessEqual(v,hi+1e-9)
 def test_bell_range_covers_peak_and_outside_support(self):
  self.assertEqual(bell_range(-2,2,0,1),(0.,1.));self.assertEqual(bell_range(2,3,0,1),(0.,0.))
 def test_rectangle_union_not_double_counting(self):
  self.assertEqual(rectangle_union_area([[0,0,2,2],[1,0,3,2]]),6)
  self.assertEqual(rectangle_union_area([[0,0,2,2],[0,0,2,2],[.5,.5,1,1]]),4)
 def test_rectangle_union_matches_independent_unit_grid(self):
  boxes=[[0,0,3,2],[1,1,4,4],[4,0,5,1]]
  expected=sum(any(a<=x+.5<c and b<=y+.5<d for a,b,c,d in boxes) for x in range(5) for y in range(4))
  self.assertEqual(rectangle_union_area(boxes),expected)
 def test_track_lengths_count_edges_not_route_multiplicity(self):
  total=sum(self.a['terrain']['track_length_by_kind_m'].values())
  exact=sum(self.j.length(eid,steps=256) for eid in self.j.network.edges)
  self.assertAlmostEqual(total,exact,delta=.1)
  self.assertGreater(sum(r['length_m'] for r in self.j.assessment['routes'].values()),total)
 def test_union_area_is_less_than_sum_of_boxes(self):
  t=self.a['terrain'];total=sum((r['reservation_box_m'][2]-r['reservation_box_m'][0])*(r['reservation_box_m'][3]-r['reservation_box_m'][1]) for r in t['terrain_rows'])
  self.assertGreater(total,t['plan_reservation_union_area_m2'])
 def test_finer_grid_does_not_change_physical_geometry(self):
  p=deepcopy(self.f['civil_policy']);p['grid_step_m']=20;t=assess(self.j,self.c,p)
  self.assertEqual(t['geometry_hash'],self.a['geometry_hash']);self.assertEqual(t['terrain_hash'],self.a['terrain_hash'])
  self.assertGreater(len(t['terrain_rows']),len(self.a['terrain']['terrain_rows']))
 def test_no_input_terrain_or_station_edit(self):
  before=digest([self.c,self.f,self.j.assessment]);bind(self.j,self.c,self.f)
  self.assertEqual(before,digest([self.c,self.f,self.j.assessment]));self.assertFalse(self.a['station_internal_edits'])
 def test_binding_recomputed_not_pass_flag_trusted(self):
  a=deepcopy(self.a);a['terrain']['track_length_by_kind_m']['tunnel']=0;a['design_hash']=digest({k:v for k,v in a.items() if k!='design_hash'})
  with self.assertRaises(ValueError):verify_binding(self.j,self.c,self.f,a)
 def test_valid_binding_verified(self):self.assertTrue(verify_binding(self.j,self.c,self.f,self.a))
 def test_zero_and_limited_search_not_impossibility(self):
  for budget in (0,2):
   r,_=search(self.f,self.c,self.b,budget);self.assertEqual(r['status'],'search_exhausted');self.assertEqual(r['evaluated'],budget);self.assertFalse(r['global_optimum_claim'])
 def test_strict_fixture_fields_and_domains(self):
  for key,value in [('extra',1),('source_corridor','../../outside.json'),('lateral_offsets_m',[0,0]),('candidate_budget',True),('modes',['flat','bad']),('operation_scenarios',['unknown'])]:
   f=deepcopy(self.f);f[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):validate_fixture(f)
 def test_unsupported_structure_policy_not_uk_prohibition(self):
  self.assertEqual(self.a['terrain']['policy']['specialwork_on_structures'],'unsupported_in_this_study')
  p=deepcopy(self.f['civil_policy']);p['specialwork_on_structures']=True
  with self.assertRaises(ValueError):assess(self.j,self.c,p)
