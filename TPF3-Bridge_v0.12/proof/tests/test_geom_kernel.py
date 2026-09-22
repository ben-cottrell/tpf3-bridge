import math
import random
import unittest
from railgeom.curves import Bezier, line, eased_branch, flatten, continuous_proximity, segment_distance, distance, point_segment, join_check


class GeometryKernelTests(unittest.TestCase):
    def test_line_length_bounds(self):
        c=line((0.,0.),(3.,4.)); leaves=flatten(c)
        self.assertLessEqual(sum(l.lower_length_m for l in leaves),5)
        self.assertGreaterEqual(sum(l.upper_length_m for l in leaves),5)

    def test_line_zero_curvature(self):
        c=line((0.,0.),(100.,0.))
        self.assertEqual(c.curvature(.5),0);self.assertEqual(c.curvature_upper(),0)

    def test_branch_exact_endpoints(self):
        c=eased_branch(40,.075)
        self.assertEqual(c.at(0),(0.,0.));self.assertEqual(c.at(1),(40.,1.5))

    def test_branch_endpoint_tangents(self):
        c=eased_branch(40,.075)
        self.assertEqual(c.tangent(0),(1.,0.))
        self.assertAlmostEqual(c.tangent(1)[1]/c.tangent(1)[0],.075)

    def test_branch_endpoint_curvatures(self):
        c=eased_branch(50,.1)
        self.assertAlmostEqual(c.curvature(0),0);self.assertAlmostEqual(c.curvature(1),0)

    def test_analytic_polynomial_matches_de_casteljau(self):
        c=eased_branch(50,.1)
        for i in range(101):
            u=i/100; x,y=c.at(u)
            self.assertAlmostEqual(x,50*u,places=11)
            self.assertAlmostEqual(y,5*(u**3-u**4/2),places=11)

    def test_subdivision_parameter_consistency(self):
        c=eased_branch(40,.075);a,b=c.split()
        for i in range(11):
            t=i/10
            self.assertLess(distance(a.at(t),c.at(t/2)),1e-12)
            self.assertLess(distance(b.at(t),c.at(.5+t/2)),1e-12)

    def test_reverse_position_and_curvature(self):
        c=eased_branch(50,.1);r=c.reversed()
        for t in (0,.1,.4,.8,1):
            self.assertLess(distance(r.at(t),c.at(1-t)),1e-12)
            self.assertAlmostEqual(r.curvature(t),-c.curvature(1-t),places=12)

    def test_rigid_transform_preserves_length(self):
        c=eased_branch(40,.075); r=c.transformed(100,250,.78)
        x,y=flatten(c),flatten(r)
        self.assertAlmostEqual(sum(a.upper_length_m for a in x),sum(a.upper_length_m for a in y),places=8)

    def test_mirror_changes_curvature_sign(self):
        c=eased_branch(50,.1);r=c.transformed(mirror=True)
        for t in (.1,.5,.9):self.assertAlmostEqual(c.curvature(t),-r.curvature(t),places=12)

    def test_curvature_bound_dominates_independent_analytic_value(self):
        # Independent polynomial derivatives, not Bezier.curvature().
        for L,m in ((40,.075),(50,.1),(30,.2)):
            bound=eased_branch(L,m).curvature_upper()
            for i in range(1001):
                u=i/1000; yp=m*(3*u*u-2*u**3); ypp=6*m/L*u*(1-u)
                self.assertGreaterEqual(bound,abs(ypp)/(1+yp*yp)**1.5)

    def test_arclength_brackets_independent_simpson_quadrature(self):
        L,m=50.,.1;n=10000
        def speed(u):return L*math.sqrt(1+(m*(3*u*u-2*u**3))**2)
        value=(speed(0)+speed(1)+sum((4 if i%2 else 2)*speed(i/n) for i in range(1,n)))/(3*n)
        leaves=flatten(eased_branch(L,m))
        self.assertLessEqual(sum(l.lower_length_m for l in leaves),value)
        self.assertGreaterEqual(sum(l.upper_length_m for l in leaves),value)

    def test_length_gap_budget(self):
        leaves=flatten(eased_branch(50,.1),length_gap_m=.0001)
        gap=sum(l.upper_length_m-l.lower_length_m for l in leaves)
        self.assertLessEqual(gap,.0001+2e-8*len(leaves)+1e-9)

    def test_leaf_capsules_contain_dense_curve_points(self):
        c=eased_branch(50,.1)
        for leaf in flatten(c):
            for i in range(11):
                p=c.at(leaf.t0+(leaf.t1-leaf.t0)*i/10)
                self.assertLessEqual(point_segment(p,leaf.a,leaf.b),leaf.hull_radius_m+1e-9)

    def test_capsules_detect_contact_that_endpoint_chord_misses(self):
        c=Bezier(((0.,0.),(10.,10.),(20.,0.)))
        straight=line((0.,5.1),(20.,5.1))
        self.assertGreater(segment_distance(c.at(0),c.at(1),straight.at(0),straight.at(1)),5)
        self.assertIsNotNone(continuous_proximity(flatten(c),flatten(straight),.2))

    def test_separated_parallel_segments(self):
        a=flatten(line((0.,0.),(100.,0.)));b=flatten(line((0.,4.5),(100.,4.5)))
        self.assertIsNone(continuous_proximity(a,b,4.0))

    def test_touching_threshold_is_conservative_contact(self):
        a=flatten(line((0.,0.),(100.,0.)));b=flatten(line((0.,4.),(100.,4.)))
        self.assertIsNotNone(continuous_proximity(a,b,4.))

    def test_segment_crossing_and_parallel_distance(self):
        self.assertEqual(segment_distance((-1.,0.),(1.,0.),(0.,-1.),(0.,1.)),0)
        self.assertEqual(segment_distance((0.,0.),(1.,0.),(0.,2.),(1.,2.)),2)

    def test_collinear_segment_overlap(self):
        self.assertEqual(segment_distance((0.,0.),(10.,0.),(5.,0.),(15.,0.)),0)

    def test_join_checks_heading_not_only_position(self):
        a=line((0.,0.),(10.,0.));b=line((10.,0.),(10.,10.))
        self.assertFalse(join_check(a,b)['pass'])

    def test_valid_tangent_join(self):
        a=eased_branch(40,.075);p=a.at(1);v=a.tangent(1)
        b=line(p,(p[0]+30*v[0],p[1]+30*v[1]))
        self.assertTrue(join_check(a,b)['pass'])

    def test_subdivision_budget_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'budget_exhausted'):flatten(eased_branch(50,.1),max_leaves=1)

    def test_invalid_coordinates(self):
        for value in (float('nan'),float('inf'),True,1e8):
            with self.subTest(value=value),self.assertRaises(ValueError):line((0.,0.),(value,1.))

    def test_zero_length_curve_rejected(self):
        with self.assertRaises(ValueError):line((0.,0.),(0.,0.))

    def test_degenerate_tangent_rejected(self):
        with self.assertRaises(ValueError):Bezier(((0.,0.),(0.,0.),(1.,0.)))

    def test_out_of_range_parameter_rejected(self):
        for u in (-.1,1.1,float('nan'),True):
            with self.subTest(u=u),self.assertRaises(ValueError):eased_branch(40,.075).at(u)

    def test_invalid_tessellation_controls(self):
        c=eased_branch(40,.075)
        for args in ({'flatness_m':0},{'length_gap_m':-1},{'max_leaves':True}):
            with self.subTest(args=args),self.assertRaises(ValueError):flatten(c,**args)

    def test_geometric_bounds_change_after_compression(self):
        a=eased_branch(50,.1);b=eased_branch(25,.1)
        self.assertGreater(b.curvature_upper(),1.9*a.curvature_upper())

    def test_deterministic_bounds(self):
        c=eased_branch(50,.1)
        self.assertEqual(flatten(c),flatten(c));self.assertEqual(c.curvature_upper(),c.curvature_upper())
