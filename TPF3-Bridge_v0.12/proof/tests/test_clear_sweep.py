import math
import unittest
from railclear.model import *
from railclear.sweep import *

class PolygonTests(unittest.TestCase):
    def setUp(self):self.a=((0.,0.),(2.,0.),(2.,2.),(0.,2.))
    def test_overlap(self):self.assertEqual(polygon_gap(self.a,((1.,1.),(3.,1.),(3.,3.),(1.,3.))),0)
    def test_containment(self):self.assertEqual(polygon_gap(self.a,((.2,.2),(.4,.2),(.4,.4),(.2,.4))),0)
    def test_touch(self):self.assertEqual(polygon_gap(self.a,((2.,0.),(3.,0.),(3.,2.),(2.,2.))),0)
    def test_separated(self):self.assertAlmostEqual(polygon_gap(self.a,((3.,0.),(4.,0.),(4.,2.),(3.,2.))),1)
    def test_diagonal(self):self.assertAlmostEqual(polygon_gap(self.a,((3.,3.),(4.,3.),(4.,4.),(3.,4.))),math.sqrt(2))
    def test_valid_both_windings(self):self.assertEqual(validate_polygon(self.a),self.a);self.assertEqual(validate_polygon(tuple(reversed(self.a))),tuple(reversed(self.a)))
    def test_nonconvex_rejected(self):
        with self.assertRaises(ValueError):validate_polygon(((0.,0.),(2.,0.),(1.,1.),(2.,2.),(0.,2.)))
    def test_degenerate_rejected(self):
        for p in [((0,0),(0,0),(1,1)),((0,0),(1,0),(2,0)),((0,0),(2,2),(0,2),(2,0)),((0,0),(1e9,0),(0,1))]:
            with self.subTest(p=p),self.assertRaises(ValueError):validate_polygon(p)

class SweepTests(unittest.TestCase):
    def setUp(self):self.b=Body(20.,2.8,14.);self.a=Polyline(((0.,0.),(100.,0.)));self.c=Polyline(((0.,3.4),(100.,3.4)))
    def test_count_and_exact_ends(self):
        s=sweep(self.a,self.b,20,40,3);self.assertEqual(len(s.poses),8);self.assertEqual(s.poses[0].front_bogie_s_m,20);self.assertEqual(s.poses[-1].front_bogie_s_m,40)
    def test_straight_padding(self):self.assertAlmostEqual(sweep(self.a,self.b,20,40,.1).between_pose_padding_m,.05,places=6)
    def test_refinement_without_changed_vehicle(self):
        coarse=pair_screen(sweep(self.a,self.b,20,40,1),sweep(self.c,self.b,20,40,1))
        fine=pair_screen(sweep(self.a,self.b,20,40,.1),sweep(self.c,self.b,20,40,.1))
        self.assertEqual(coarse['status'],'unresolved_between_poses');self.assertEqual(fine['status'],'clear_within_polyline_static_model')
        self.assertAlmostEqual(coarse['minimum_sample_gap_m'],fine['minimum_sample_gap_m'])
    def test_dense_poses_inside_bound(self):
        p=Polyline(((0.,0.),(20.,0.),(35.,4.),(60.,0.),(100.,0.)))
        s=sweep(p,self.b,20,80,2)
        for i in range(1201):
            x=20+60*i/1200;actual=p.pose(x,self.b)
            nearest=min(s.poses,key=lambda q:abs(q.front_bogie_s_m-x))
            for a,b in zip(actual.corners,nearest.corners):self.assertLessEqual(distance(a,b),s.between_pose_padding_m+1e-6)
    def test_bound_rotating_body(self):
        p=Polyline(((0.,0.),(25.,8.),(50.,0.),(75.,-8.),(100.,0.)))
        s=sweep(p,self.b,22,85,1.7)
        for i in range(1000):
            x=22+63*i/999;actual=p.pose(x,self.b);nearest=min(s.poses,key=lambda q:abs(q.front_bogie_s_m-x))
            self.assertLessEqual(max(distance(a,b) for a,b in zip(actual.corners,nearest.corners)),s.between_pose_padding_m+1e-6)
    def test_missing_support_rejected(self):
        with self.assertRaises(ValueError):sweep(self.a,self.b,5,60,1)
    def test_interval_bounds_rejected(self):
        for start,end in [(40,20),(20,101),(-1,20),(20,20)]:
            with self.subTest(x=(start,end)),self.assertRaises(ValueError):sweep(self.a,self.b,start,end)
    def test_pose_budget(self):
        with self.assertRaisesRegex(RuntimeError,'budget'):sweep(self.a,self.b,20,80,.001,max_poses=100)
    def test_invalid_step(self):
        with self.assertRaises(ValueError):sweep(self.a,self.b,20,80,0)
    def test_pair_budget(self):
        r=pair_screen(sweep(self.a,self.b,20,40),sweep(self.c,self.b,20,40),1)
        self.assertEqual(r['status'],'search_exhausted');self.assertFalse(r['may_remove_existing_resource'])
    def test_nonmatching_phase_collision(self):
        # Same path; samples at different chainages overlap via body length.
        a=sweep(self.a,self.b,20,25,1);b=sweep(self.a,self.b,35,40,1)
        r=pair_screen(a,b);self.assertEqual(r['status'],'sampled_body_contact')
        self.assertNotEqual(r['sample_witness']['a_front_s_m'],r['sample_witness']['b_front_s_m'])
    def test_obstacle_contact(self):
        r=obstacle_screen(sweep(self.a,self.b,20,40),((29.,1.),(31.,1.),(31.,2.),(29.,2.)))
        self.assertEqual(r['status'],'sampled_body_contact')
    def test_obstacle_clear_bound(self):
        r=obstacle_screen(sweep(self.a,self.b,20,40,.1),((29.,4.),(31.,4.),(31.,5.),(29.,5.)))
        self.assertEqual(r['status'],'clear_within_polyline_static_model')
    def test_obstacle_budget(self):self.assertEqual(obstacle_screen(sweep(self.a,self.b,20,40),((0.,4.),(1.,4.),(1.,5.),(0.,5.)),1)['status'],'search_exhausted')
    def test_parent_error_not_promoted(self):
        s=sweep(self.a,self.b,20,40,.1).export(False);self.assertEqual(s['parent_curve_body_error_bound'],'unassessed');self.assertEqual(s['dynamic_3D_gauging'],'unassessed')
    def test_overlay_no_mutation(self):
        sweeps={'A':sweep(self.a,self.b,20,40,.1),'B':sweep(self.c,self.b,20,40,.1)}
        hashes=[x.path.digest() for x in sweeps.values()];r=audit_pair_requests(sweeps,[('A','B')])
        self.assertEqual(r['resource_mutations'],[]);self.assertEqual(hashes,[x.path.digest() for x in sweeps.values()])
    def test_overlay_invalid(self):
        with self.assertRaises(ValueError):audit_pair_requests({'A':sweep(self.a,self.b,20,40)},[('A','A')])
