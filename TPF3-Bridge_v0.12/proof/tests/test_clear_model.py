import math
import unittest
from dataclasses import replace
from railclear.model import *
from railgeom.curves import line, eased_branch

class BodyTests(unittest.TestCase):
    def test_body_dimensions(self):self.assertEqual(Body(20,2.8,14).half_width_m,1.4)
    def test_allowance_separate(self):self.assertAlmostEqual(Body(20,2.8,14,.1).half_width_m,1.5)
    def test_invalid_dimensions(self):
        for args in [(0,2.8,14),(20,0,14),(20,2.8,20),(20,2.8,-1),(162,2.8,14),(True,2.8,14),(20,math.nan,14),(20,2.8,14,-.1)]:
            with self.subTest(args=args),self.assertRaises(ValueError):Body(*args)
    def test_no_authenticity_promotion(self):
        with self.assertRaises(ValueError):Body(20,2.8,14,fidelity='verified')
    def test_hash_assumptions(self):self.assertNotEqual(Body(20,2.8,14).digest(),Body(20,2.8,16).digest())
    def test_invalid_profile(self):
        with self.assertRaises(ValueError):Body(20,2.8,14,profile_id='')

class PathTests(unittest.TestCase):
    def setUp(self):self.body=Body(20,2.8,14);self.path=Polyline(((0.,0.),(25.,0.),(100.,0.)))
    def test_chainage_and_endpoints(self):
        self.assertEqual(self.path.chainages,(0.,25.,100.));self.assertEqual(self.path.at(25),(25,0));self.assertEqual(self.path.at(100),(100,0))
    def test_position_interpolation(self):self.assertEqual(self.path.at(10),(10,0))
    def test_pose_chord(self):
        p=self.path.pose(50,self.body);self.assertAlmostEqual(distance(p.front_bogie,p.rear_bogie),14);self.assertAlmostEqual(p.rear_bogie_s_m,36)
    def test_cross_segment_pose(self):self.assertAlmostEqual(self.path.pose(30,self.body).rear_bogie_s_m,16)
    def test_rear_at_start(self):self.assertEqual(self.path.pose(14,self.body).rear_bogie,(0,0))
    def test_missing_continuation(self):
        with self.assertRaisesRegex(ValueError,'continuation'):self.path.pose(13,self.body)
    def test_no_extrapolation(self):
        for x in [-1,101,math.nan,True]:
            with self.subTest(x=x),self.assertRaises(ValueError):self.path.at(x)
    def test_bounded_root(self):
        p=Polyline(tuple((float(i),0.) for i in range(100)))
        with self.assertRaisesRegex(RuntimeError,'exhausted'):p.pose(50,self.body,max_segments=2)
    def test_invalid_root_budget(self):
        with self.assertRaises(ValueError):self.path.pose(50,self.body,max_segments=True)
    def test_invalid_path(self):
        for pts in [((0,0),(0,0)),((0,0),(1,0),(0,0)),((0,0),(1,0),(1,10)),((0,0),(1,2,3)),((0,0),(1e8,0))]:
            with self.subTest(points=pts),self.assertRaises(ValueError):Polyline(pts)
    def test_straight_corners(self):
        p=self.path.pose(50,self.body);self.assertEqual(p.corners,((33.,-1.4),(53.,-1.4),(53.,1.4),(33.,1.4)))
    def test_mirrored_pose(self):
        p=Polyline(((0.,0.),(20.,2.),(70.,0.)));q=Polyline(tuple((x,-y) for x,y in p.points))
        a=p.pose(40,self.body);b=q.pose(40,self.body)
        self.assertAlmostEqual(a.centre[0],b.centre[0]);self.assertAlmostEqual(a.centre[1],-b.centre[1])
    def test_reversed_path_body(self):
        q=Polyline(tuple(reversed(self.path.points)));a=self.path.pose(50,self.body);b=q.pose(self.path.length_m-a.rear_bogie_s_m,self.body)
        self.assertEqual(set(a.corners),set(b.corners))
    def test_transform_pose(self):
        q=Polyline(tuple((x+10,y+20) for x,y in self.path.points));a=q.pose(50,self.body)
        self.assertEqual(a.centre,(53,20))
    def test_non_arc_bogie_constraint(self):
        p=Polyline(((0.,0.),(30.,0.),(60.,10.)));a=p.pose(40,self.body)
        self.assertGreater(a.front_bogie_s_m-a.rear_bogie_s_m,14);self.assertAlmostEqual(distance(a.front_bogie,a.rear_bogie),14)
    def test_curves_flattened_with_parent(self):
        p=from_curves((eased_branch(40,.075),),'sourcehash');self.assertEqual(p.parent_hash,'sourcehash');self.assertGreater(p.length_m,40)
    def test_disconnected_curves(self):
        with self.assertRaises(ValueError):from_curves((line((0.,0.),(1.,0.)),line((2.,0.),(3.,0.))))
    def test_empty_curves(self):
        with self.assertRaises(ValueError):from_curves(())

class AnalyticTests(unittest.TestCase):
    def setUp(self):self.b=Body(20,2.8,14)
    def test_straight_reference_gap(self):self.assertAlmostEqual(parallel_gap(3.4,self.b,self.b)['gap_m'],.6)
    def test_straight_allowance(self):
        b=replace(self.b,lateral_allowance_m=.1);self.assertAlmostEqual(parallel_gap(3.4,b,b)['gap_m'],.4)
    def test_parallel_touch(self):self.assertEqual(parallel_gap(2.8,self.b,self.b)['status'],'geometric_contact_or_overlap')
    def test_centre_throw_identity(self):
        x=circular_band(400,self.b);self.assertAlmostEqual(x['centre_inthrow_m'],400-math.sqrt(400**2-7**2))
    def test_bogie_arc_longer_than_chord(self):self.assertGreater(circular_band(150,self.b)['bogie_arc_separation_m'],14)
    def test_circle_pose_chord(self):
        for angle in [0,.2,1,3]:
            p=circular_pose(150,angle,self.b);self.assertAlmostEqual(distance(p.front_bogie,p.rear_bogie),14)
    def test_circle_bounds_independent_corner_check(self):
        band=circular_band(400,self.b)
        for angle in [0,.5,1.,2.]:
            p=circular_pose(400,angle,self.b)
            self.assertAlmostEqual(max(norm(x) for x in p.corners),band['outer_radius_m'])
            # The closest point is on the centre of an inner side, not a corner.
            mid=tuple((p.corners[2][j]+p.corners[3][j])/2 for j in (0,1))
            self.assertAlmostEqual(norm(mid),band['inner_radius_m'])
    def test_circle_approaches_straight(self):self.assertAlmostEqual(concentric_gap(1e6,3.4,self.b,self.b)['gap_m'],.6,places=3)
    def test_radius_reduction_reduces_gap(self):self.assertLess(concentric_gap(150,3.4,self.b,self.b)['gap_m'],concentric_gap(400,3.4,self.b,self.b)['gap_m'])
    def test_long_body_stress(self):
        b=Body(26,2.8,19,.1);self.assertLess(concentric_gap(150,3.4,b,b)['gap_m'],0)
    def test_circle_invalid_domain(self):
        for r in [0,-1,6,math.inf,1e20]:
            with self.subTest(r=r),self.assertRaises(ValueError):circular_band(r,self.b)
    def test_polyline_agrees_with_circle(self):
        R=400.;pts=tuple((R*math.sin(i*.0001),R*(1-math.cos(i*.0001))) for i in range(1001))
        p=Polyline(pts);state=p.pose(30,self.b)
        rho=math.hypot(state.centre[0],state.centre[1]-R)
        self.assertAlmostEqual(rho,math.sqrt(R*R-49),places=5)
    def test_analytic_never_grants_gauging(self):
        d=parallel_gap(3.4,self.b,self.b);self.assertEqual(d['full_UK_gauging'],'unassessed');self.assertFalse(d['may_remove_existing_resource'])
