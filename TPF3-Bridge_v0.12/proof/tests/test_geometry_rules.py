import math
import unittest
from railproof.geometry import PlainLineShift, sufficient_length
from railproof.rules import platform_cant, platform_radius, gb_platform_interface


class GeometryTests(unittest.TestCase):
    def test_endpoints(self):
        s=PlainLineShift(100,4.5)
        a,b=s.evaluate(0),s.evaluate(100)
        self.assertEqual(a['y_m'],0);self.assertEqual(b['y_m'],4.5)
        for r in (a,b):
            self.assertEqual(r['dy_dx'],0);self.assertEqual(r['d2y_dx2'],0)

    def test_mirror_reverses_signs(self):
        a,b=PlainLineShift(100,4.5),PlainLineShift(100,-4.5)
        self.assertEqual(a.curvature_upper_bound(),b.curvature_upper_bound())
        self.assertAlmostEqual(a.evaluate(23)['curvature_per_m'],-b.evaluate(23)['curvature_per_m'])

    def test_bound_contains_sampled_curvature(self):
        # Numerical cross-check of an analytically derived bound, not its proof.
        for length in (10,50,100):
            s=PlainLineShift(length,4.5)
            self.assertTrue(all(abs(s.evaluate(length*i/1000)['curvature_per_m'])<=s.curvature_upper_bound()+1e-12 for i in range(1001)))

    def test_compression_revalidates(self):
        self.assertEqual(PlainLineShift(100,4.5).certify_radius(300)['status'],'pass_sufficient_bound')
        self.assertEqual(PlainLineShift(60,4.5).certify_radius(300)['status'],'not_certified_by_bound')

    def test_sufficient_length_value(self):
        self.assertAlmostEqual(sufficient_length(4.5,300),math.sqrt(10/math.sqrt(3)*4.5*300))

    def test_straight_shift_zero(self):
        self.assertEqual(PlainLineShift(10,0).curvature_upper_bound(),0)

    def test_invalid_length(self):
        with self.assertRaises(ValueError):PlainLineShift(0,4)

    def test_coordinate_outside(self):
        with self.assertRaises(ValueError):PlainLineShift(10,4).evaluate(11)

    def test_boolean_offset_rejected(self):
        with self.assertRaises(ValueError):PlainLineShift(10,True)

    def test_string_offset_rejected(self):
        with self.assertRaises(ValueError):sufficient_length("4.5",300)

    def test_nonfinite_offset(self):
        with self.assertRaises(ValueError):PlainLineShift(10,float('nan'))


class ClauseTests(unittest.TestCase):
    def test_cant_boundary(self):
        self.assertEqual(platform_cant(110,applicable=True,normal_service_stop=True)['status'],'pass')
        self.assertEqual(platform_cant(110.001,applicable=True,normal_service_stop=True)['status'],'fail')

    def test_cant_missing(self):
        self.assertEqual(platform_cant(None,applicable=True,normal_service_stop=True)['status'],'unassessed')

    def test_cant_no_normal_stop(self):
        self.assertEqual(platform_cant(150,applicable=True,normal_service_stop=False)['status'],'not_applicable')

    def test_unknown_scope(self):
        self.assertEqual(platform_cant(0,applicable=None,normal_service_stop=True)['status'],'unassessed')

    def test_pending_override(self):
        self.assertEqual(platform_cant(0,applicable=True,normal_service_stop=True,override_pending=True)['status'],'unassessed')

    def test_radius_boundary(self):
        self.assertEqual(platform_radius(300,applicable=True,new_line=True)['status'],'pass')
        self.assertEqual(platform_radius(299.999,applicable=True,new_line=True)['status'],'fail')

    def test_existing_track_not_passed(self):
        self.assertEqual(platform_radius(250,applicable=True,new_line=False)['status'],'not_applicable')

    def test_unknown_line_status(self):
        self.assertEqual(platform_radius(300,applicable=True,new_line=None)['status'],'unassessed')

    def test_straight_explicit(self):
        self.assertEqual(platform_radius(None,applicable=True,new_line=True,straight=True)['status'],'pass')

    def test_infinite_radius_not_serialised(self):
        with self.assertRaises(ValueError):platform_radius(float('inf'),applicable=True,new_line=True)

    def test_conflicting_straight_inputs(self):
        with self.assertRaises(ValueError):platform_radius(300,applicable=True,new_line=True,straight=True)

    def test_national_interface_unknown(self):
        self.assertEqual(gb_platform_interface()['status'],'unassessed')

    def test_invalid_scope_type(self):
        with self.assertRaises(ValueError):platform_cant(0,applicable='yes',normal_service_stop=True)

    def test_negative_cant_magnitude(self):
        with self.assertRaises(ValueError):platform_cant(-1,applicable=True,normal_service_stop=True)
