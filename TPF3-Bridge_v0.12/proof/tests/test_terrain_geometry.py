import math
import unittest
from copy import deepcopy
from dataclasses import replace
from terrain_support import model,inputs
from railbranch.geometry import build as local_build,state
from railbranch.operations import compile_resources,verify_candidate
from railterrain.geometry import build_placed,mainline_profile_check
from railterrain.planning import boundary_check
from railgeom.curves import evaluate

class TerrainGeometryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.f,cls.c,cls.b,cls.j=model()
 def test_fixed_six_boundary_positions(self):
  r=boundary_check(self.j,self.c);self.assertTrue(r['passed']);self.assertEqual(len(r['ports']),6)
 def test_routes_have_no_open_internal_ends(self):
  j=self.j;self.assertEqual(len(j.routes),4)
  external=set(('W_E','W_W','E_E','E_W','B_OUT','B_IN'))
  degrees={p:0 for p in j.network.ports}
  for e in j.network.edges.values():degrees[e.u]+=1;degrees[e.v]+=1
  self.assertEqual({p for p,d in degrees.items() if d==1},external)
 def test_physical_track_is_not_duplicated_per_route(self):
  self.assertEqual(len(self.j.network.edges),16)
  self.assertGreater(sum(len(p.steps) for p in self.j.routes.values()),16)
 def test_imported_component_shapes_only_translate(self):
  j=self.j;o=local_build(j.spec,j.mode)
  for eid,e in j.network.edges.items():
   if e.component:
    for a,b in zip(e.curve.controls,o.network.edges[eid].curve.controls):
     self.assertAlmostEqual(a[0],b[0]);self.assertAlmostEqual(a[1]-b[1],280)
  self.assertEqual(j.assessment['component_geometry_hash'],o.assessment['component_geometry_hash'])
 def test_sorted_approach_node_is_explicit(self):
  self.assertIn('EAST_SPREAD',self.j.network.ports)
  self.assertIn('east_sorted_approach',self.j.network.edges)
 def test_profile_does_not_inherit_local_300m_main_limit(self):
  r=mainline_profile_check(self.j,self.c['profile']);self.assertEqual(r['profile']['min_radius_m'],1500)
  self.assertEqual(r['status'],'project_mainline_bounds_pass')
 def test_overwide_offset_fails_main_but_not_local_floor(self):
  _,c,_,j=model(offset=360)
  self.assertTrue(j.assessment['accepted_for_reference_comparison'])
  r=mainline_profile_check(j,c['profile']);self.assertNotEqual(r['status'],'project_mainline_bounds_pass')
  self.assertTrue(any('main_radius_bound' in v['reasons'] for v in r['edges']))
 def test_curve_junctions_pass_existing_network_validator(self):self.j.network.validate();verify_candidate(self.j)
 def test_external_grade_and_heading_zero(self):
  for row in boundary_check(self.j,self.c)['ports']:self.assertEqual(row['reasons'],[])
 def test_dense_main_curvature_under_reported_bounds(self):
  for row in mainline_profile_check(self.j,self.c['profile'])['edges']:
   e=self.j.network.edges[row['edge_id']];L=e.curve.at(1)[0]-e.curve.at(0)[0]
   upper=row['zero_cant_lateral_accel_upper_mps2'];v=self.c['profile']['speed_mph']*.44704
   for i in range(101):
    t=i/100;d=evaluate(e.curve.derivative_controls(),t)[1]/L;dd=evaluate(e.curve.derivative_controls(2),t)[1]/L**2
    k=abs(dd)/(1+d*d)**1.5;self.assertLessEqual(v*v*k,upper+1e-7)
 def test_dense_curvature_rate_under_analytic_bound(self):
  v=self.c['profile']['speed_mph']*.44704
  for row in mainline_profile_check(self.j,self.c['profile'])['edges']:
   e=self.j.network.edges[row['edge_id']];L=e.curve.at(1)[0]-e.curve.at(0)[0]
   for i in range(101):
    d=[evaluate(e.curve.derivative_controls(k),i/100)[1]/L**k for k in (1,2,3)]
    w=math.hypot(1,d[0]);actual=abs(d[2]/w**4-3*d[0]*d[1]**2/w**6)
    self.assertLessEqual(v**3*actual,row['constant_speed_lateral_jerk_upper_mps3']+1e-7)
 def test_main_and_return_cross_only_at_declared_point(self):
  j=self.j;x=j.assessment['crossing']['x_m']
  self.assertAlmostEqual(j.point('east_continuation',x)[1],j.point('return_connector',x)[1],places=6)
  self.assertGreater(abs(j.point('east_continuation',x)[2]-j.point('return_connector',x)[2]),6.8)
 def test_separation_preserves_merge_resources(self):
  c=compile_resources(self.j)
  p=next(r for r in c['route_pairs'] if {r['a'],r['b']}=={'main_west','branch_in'})
  self.assertIn('track:west_exit',p['incompatible_shared_resources'])
  self.assertNotIn('crossing:RETURN_OVER_EAST',c['resources'])
 def test_flat_crossing_resource_present(self):
  *_,j=model(mode='flat');self.assertIn('crossing:RETURN_OVER_EAST',compile_resources(j)['resources'])
 def test_out_return_order_continuous_certificate(self):
  self.assertTrue(all(r['y_order_lower_bound_m']>0 for r in self.j.assessment['plan_order_checks']))
 def test_lowering_is_candidate_specific(self):
  j=self.j;p=j.polyline('east_approach');self.assertLessEqual(p['position_error_bound_m'],.02000001)
  self.assertAlmostEqual(p['points'][-1][1],281.7)
 def test_invalid_restore_and_offset_rejected(self):
  for y,x in ((True,4200),(float('nan'),4200),(280,2100),(280,6000)):
   with self.subTest(y=y,x=x),self.assertRaises(ValueError):build_placed(self.j.spec,'flyover',y,x)
 def test_forged_geometry_not_scheduled(self):
  j=deepcopy(self.j);j.assessment['network']['name']='forged'
  with self.assertRaises(ValueError):verify_candidate(j)
