import math
import unittest
from railops.motion import MotionProfile, make_motion

class MotionTests(unittest.TestCase):
    def test_project_speed_conversion(self):
        self.assertAlmostEqual(MotionProfile().speed_mps,15*1609.344/3600)
    def test_long_arrival_has_three_phases(self):
        self.assertEqual(len(make_motion(1000,MotionProfile(),stop_at_end=True).phases),3)
    def test_short_arrival_is_triangular(self):
        m=make_motion(2,MotionProfile(),stop_at_end=True)
        self.assertEqual(len(m.phases),2); self.assertLess(m.peak_speed_mps,MotionProfile().speed_mps)
    def test_start_and_stop(self):
        m=make_motion(100,MotionProfile(),stop_at_end=True)
        self.assertEqual(m.at(0),(0,0)); self.assertAlmostEqual(m.at(m.duration_s)[1],0)
    def test_departure_continues(self):
        m=make_motion(1000,MotionProfile(),stop_at_end=False)
        self.assertAlmostEqual(m.at(m.duration_s)[1],MotionProfile().speed_mps)
    def test_short_departure_accelerates_only(self):
        m=make_motion(1,MotionProfile(),stop_at_end=False)
        self.assertEqual(len(m.phases),1)
        self.assertAlmostEqual(m.duration_s,math.sqrt(2/0.6))
    def test_trapezoid_duration_independent_formula(self):
        p=MotionProfile(); d=1000
        expected=p.speed_mps/p.acceleration_mps2+p.speed_mps/p.braking_mps2+(d-p.speed_mps**2/(2*p.acceleration_mps2)-p.speed_mps**2/(2*p.braking_mps2))/p.speed_mps
        self.assertAlmostEqual(make_motion(d,p,stop_at_end=True).duration_s,expected)
    def test_triangular_peak_independent_formula(self):
        p=MotionProfile(acceleration_mps2=1,braking_mps2=1)
        m=make_motion(9,p,stop_at_end=True)
        self.assertAlmostEqual(m.peak_speed_mps,3); self.assertAlmostEqual(m.duration_s,6)
    def test_phase_continuity(self):
        for stop in (True,False):
            m=make_motion(1000,MotionProfile(),stop_at_end=stop)
            for a,b in zip(m.phases,m.phases[1:]):
                self.assertAlmostEqual(a.end_m,b.start_m);self.assertAlmostEqual(a.end_s,b.start_s)
                self.assertAlmostEqual(a.start_speed_mps+a.acceleration_mps2*a.duration_s,b.start_speed_mps)
    def test_time_distance_inverse(self):
        for d in (0.01,10,100,1000):
            for stop in (True,False):
                m=make_motion(d,MotionProfile(),stop_at_end=stop)
                for i in range(101):
                    x=d*i/100
                    self.assertAlmostEqual(m.at(m.time_at(x))[0],x,places=6)
    def test_monotonic_motion(self):
        m=make_motion(500,MotionProfile(),stop_at_end=True)
        values=[m.at(m.duration_s*i/500)[0] for i in range(501)]
        self.assertEqual(values,sorted(values))
    def test_speed_cap(self):
        p=MotionProfile();m=make_motion(500,p,stop_at_end=True)
        self.assertTrue(all(m.at(m.duration_s*i/1000)[1]<=p.speed_mps+1e-10 for i in range(1001)))
    def test_independent_numerical_speed_integral(self):
        m=make_motion(400,MotionProfile(),stop_at_end=True);n=20000;dt=m.duration_s/n
        # Midpoint quadrature does not call the distance evaluator or inverse.
        def v(t):
            p=next(p for p in m.phases if t<=p.end_s)
            return p.start_speed_mps+p.acceleration_mps2*(t-p.start_s)
        self.assertAlmostEqual(sum(v((i+.5)*dt)*dt for i in range(n)),400,places=4)
    def test_weaker_brakes_take_longer(self):
        a=make_motion(500,MotionProfile(braking_mps2=.3),stop_at_end=True)
        b=make_motion(500,MotionProfile(braking_mps2=.7),stop_at_end=True)
        self.assertGreater(a.duration_s,b.duration_s)
    def test_export_replay(self):
        self.assertEqual(make_motion(100,MotionProfile(),stop_at_end=True).export(),make_motion(100,MotionProfile(),stop_at_end=True).export())
    def test_bad_profile_numbers(self):
        for key in ('speed_mps','acceleration_mps2','braking_mps2'):
            for x in (0,-1,True,float('nan'),float('inf')):
                with self.subTest(key=key,x=x),self.assertRaises(ValueError): MotionProfile(**{key:x})
    def test_time_units_reject_float(self):
        with self.assertRaises(ValueError): MotionProfile(setup_ms=1.5)
    def test_cannot_claim_approved_profile(self):
        with self.assertRaises(ValueError): MotionProfile(provenance='approved_UK')
    def test_distance_domain(self):
        for x in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError): make_motion(x,MotionProfile(),stop_at_end=True)
    def test_stop_flag(self):
        with self.assertRaises(ValueError): make_motion(10,MotionProfile(),stop_at_end=1)
    def test_queries_do_not_extrapolate(self):
        m=make_motion(100,MotionProfile(),stop_at_end=True)
        for x in (-1,101,float('nan'),True):
            with self.assertRaises(ValueError): m.time_at(x)
        with self.assertRaises(ValueError):m.at(m.duration_s+1)
