import math
import unittest
from railcorridor.geometry import *
from railcorridor.planning import parse_json, validate_fixture, make_alignment
from pathlib import Path


def fixture(): return validate_fixture(parse_json(Path(__file__).parents[1]/'corridor_fixtures/release.json'))


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture();self.a=make_alignment(self.f,280,24)
    def test_zero_endpoint_derivatives(self):
        for k in self.a.knots:
            s=self.a.state(k.x)
            for field in ('yp','ypp','zp','zpp'):self.assertAlmostEqual(s[field],0)
    def test_knot_coordinates_preserved(self):
        for k in self.a.knots:self.assertEqual(self.a.point(k.x),(k.x,k.y,k.z))
    def test_normal_spacing_exact(self):
        for x in range(0,6001,37):self.assertAlmostEqual(math.dist(self.a.point(x,-1.7),self.a.point(x,1.7)),3.4,places=10)
    def test_offset_is_not_y_translation(self):
        p=self.a.point(900,1.7)
        self.assertNotEqual(p[0],900);self.assertLess(p[1]-self.a.state(900)['y'],1.7)
    def test_endpoint_ports(self):
        self.assertEqual(self.a.point(0,-1.7),(0,-1.7,20))
        self.assertEqual(self.a.point(6000,1.7),(6000,1.7,20))
    def test_analytic_first_derivative(self):
        for x in (200,750,1200,3700):
            s=self.a.state(x);h=.01
            self.assertAlmostEqual((self.a.state(x+h)['y']-self.a.state(x-h)['y'])/(2*h),s['yp'],places=8)
    def test_analytic_second_derivative(self):
        for x in (200,750,1200,3700):
            s=self.a.state(x);h=.1
            self.assertAlmostEqual((self.a.state(x+h)['yp']-self.a.state(x-h)['yp'])/(2*h),s['ypp'],places=9)
    def test_grade_matches_track_metric(self):
        for x in (600,1100,3700):
            h=.01;p=self.a.point(x-h,1.7);q=self.a.point(x+h,1.7)
            observed=(q[2]-p[2])/math.hypot(q[0]-p[0],q[1]-p[1])
            self.assertAlmostEqual(observed,self.a.quantities(x,1.7)['grade'],places=9)
    def test_curvature_bounds_on_both_tracks(self):
        for d in (-1.7,1.7):
            b=self.a.bounds(d)
            for x in range(6001):
                q=self.a.quantities(x,d)
                self.assertLessEqual(abs(q['plan_curvature']),b['plan_curvature_upper']+1e-12)
                self.assertLessEqual(abs(q['grade']),b['grade_upper']+1e-12)
                self.assertLessEqual(abs(q['vertical_curvature']),b['vertical_curvature_upper']+1e-12)
    def test_polyline_midpoint_error_bound(self):
        for d in (-1.7,1.7):
            r=self.a.polyline(d,max_step=47,tolerance=.02)
            for i,(x,y) in enumerate(zip(r['parameters_x'],r['parameters_x'][1:])):
                for u in (.2,.5,.8):
                    target=self.a.point(x+(y-x)*u,d)
                    linear=tuple((1-u)*a+u*b for a,b in zip(r['points'][i],r['points'][i+1]))
                    self.assertLessEqual(math.dist(target,linear),r['positional_error_bound_m']+1e-8)
    def test_tighter_lowering_generates_more_points(self):
        self.assertGreater(len(self.a.polyline(tolerance=.001)['points']),len(self.a.polyline(tolerance=.1)['points']))
    def test_polyline_point_budget(self):
        with self.assertRaises(ValueError):self.a.polyline(point_budget=3)
    def test_straight_length(self):self.assertAlmostEqual(make_alignment(self.f,0,20).length(),6000)
    def test_curved_length_exceeds_chord(self):self.assertGreater(self.a.length(),6000)
    def test_length_matches_dense_chords(self):
        pts=[self.a.point(i) for i in range(6001)]
        approx=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
        self.assertAlmostEqual(self.a.length(),approx,places=3)
    def test_mirror_lengths(self):
        other=make_alignment(self.f,-280,24)
        self.assertAlmostEqual(self.a.length(1.7),other.length(-1.7),places=8)
    def test_no_false_infinite_radius_json(self):
        import json
        json.dumps(make_alignment(self.f,0,20).bounds(),allow_nan=False)
    def test_hash_changes_with_geometry(self):self.assertNotEqual(self.a.identity,make_alignment(self.f,281,24).identity)
    def test_no_extrapolation(self):
        for x in (-1,6001):
            with self.assertRaises(ValueError):self.a.point(x)
    def test_bad_knot_order(self):
        with self.assertRaises(ValueError):Alignment((Knot(10,0,0),Knot(0,0,0)))
    def test_mutable_knots_rejected(self):
        with self.assertRaises(ValueError):Alignment(list(self.a.knots))
    def test_nonfinite_and_boolean_rejected(self):
        for v in (True,float('nan'),float('inf')):
            with self.assertRaises(ValueError):Knot(v,0,0)
    def test_cant_not_ignored(self):
        p=dict(self.f['profile']);p['cant_mm']=100
        with self.assertRaises(ValueError):limits_check(self.a,3.4,p)
    def test_high_speed_not_silently_lowered(self):
        p=dict(self.f['profile']);p['speed_mph']=100
        r=limits_check(self.a,3.4,p)
        self.assertEqual(r['status'],'project_bounds_not_certified');self.assertAlmostEqual(r['speed_target_mps'],44.704)
    def test_project_grade_rejection(self):
        a=make_alignment(self.f,0,80)
        self.assertTrue(any('gradient' in x for x in limits_check(a,3.4,self.f['profile'])['failures']))
    def test_missing_profile_field(self):
        p=dict(self.f['profile']);p.pop('max_grade')
        with self.assertRaises(ValueError):limits_check(self.a,3.4,p)
