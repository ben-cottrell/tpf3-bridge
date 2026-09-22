import unittest
from railops.uk_profiles import *

class UKProfileTests(unittest.TestCase):
    def test_register_has_traceable_unique_values(self):
        rs=register()['parameters'];self.assertEqual(len(rs),11)
        self.assertEqual(len({r['id'] for r in rs}),len(rs))
        self.assertTrue(all(r['clause'] and r['printed_page'] and r['source_id'] for r in rs))
    def test_nominal_gauge_not_tolerance_pass(self):
        r=nominal_gauge(applicable=True);self.assertEqual(r['value'],1435);self.assertEqual(r['status'],'reference_value')
    def test_gauge_scope_missing(self):self.assertEqual(nominal_gauge(applicable=None)['status'],'unassessed')
    def test_centres_straight(self):
        r=gb_track_centres(applicable=True,straight=True);self.assertEqual(r['value'],3.4)
        self.assertEqual(r['status'],'reference_value')
    def test_centres_radius_boundary(self):
        self.assertEqual(gb_track_centres(applicable=True,straight=False,radius_m=400)['value'],3.4)
        self.assertEqual(gb_track_centres(applicable=True,straight=False,radius_m=399.99)['status'],'unassessed')
    def test_centres_unknown_or_reduction(self):
        for opts in ({'straight':None},{'straight':False},{'straight':True,'reduction_pending':True}):
            self.assertEqual(gb_track_centres(applicable=True,**opts)['status'],'unassessed')
    def test_centres_inconsistent_geometry(self):
        with self.assertRaises(ValueError):gb_track_centres(applicable=True,straight=True,radius_m=400)
    def test_centres_does_not_use_generic_table(self):
        r=gb_track_centres(applicable=True,straight=False,radius_m=1000)
        self.assertEqual(r['clause'],'7.7.17.3(1)');self.assertNotEqual(r['value'],4.5)
    def test_newline_floor_boundary(self):
        for x,status in ((149.999,'fail'),(150,'pass'),(500,'pass')):
            self.assertEqual(new_line_radius(x,applicable=True,new_line=True)['status'],status)
    def test_existing_not_approved_by_newline_floor(self):
        self.assertEqual(new_line_radius(50,applicable=True,new_line=False)['status'],'not_applicable')
    def test_newline_straight_and_unknown(self):
        self.assertEqual(new_line_radius(None,applicable=True,new_line=True,straight=True)['status'],'pass')
        self.assertEqual(new_line_radius(None,applicable=True,new_line=True)['status'],'unassessed')
    def test_newline_floor_cannot_pass_platform_radius(self):
        self.assertEqual(new_line_radius(200,applicable=True,new_line=True)['status'],'pass')
        self.assertEqual(platform_radius(200,applicable=True,new_line=True)['status'],'fail')
    def test_gradient_units_and_boundary(self):
        for g,s in ((0.0025,'pass'),(.0025001,'fail')):
            self.assertEqual(coupling_platform_gradient(g,applicable=True,new_line=True,regular_attach_detach=True)['status'],s)
        self.assertEqual(1/parameter('NEW_COUPLING_PLATFORM_GRADIENT')['value'],400)
    def test_gradient_not_universal(self):
        self.assertEqual(coupling_platform_gradient(.1,applicable=True,new_line=True,regular_attach_detach=False)['status'],'not_applicable')
    def test_gradient_unknown_condition(self):
        self.assertEqual(coupling_platform_gradient(.001,applicable=True,new_line=True,regular_attach_detach=None)['status'],'unassessed')
    def test_vertical_asymmetry(self):
        self.assertEqual(vertical_radius(500,kind='crest',applicable=True)['status'],'pass')
        self.assertEqual(vertical_radius(500,kind='sag',applicable=True)['status'],'fail')
        self.assertEqual(vertical_radius(900,kind='sag',applicable=True)['status'],'pass')
    def test_hump_not_silently_passed(self):
        self.assertEqual(vertical_radius(200,kind='crest',applicable=True,marshalling_hump=True)['status'],'not_applicable')
    def test_bad_vertical_kind(self):
        with self.assertRaises(ValueError):vertical_radius(900,kind='level',applicable=True)
    def test_stop_cant_matches_register(self):
        n=parameter('STOPPING_PLATFORM_CANT')['value']
        self.assertEqual(platform_cant(n,applicable=True,normal_service_stop=True)['status'],'pass')
        self.assertEqual(platform_cant(n+.01,applicable=True,normal_service_stop=True)['status'],'fail')
    def test_platform_radius_matches_register(self):
        n=parameter('NEW_PLATFORM_RADIUS')['value']
        self.assertEqual(platform_radius(n,applicable=True,new_line=True)['status'],'pass')
    def test_platform_interface_not_invented(self):self.assertEqual(gb_platform_interface()['status'],'unassessed')
    def test_guidance_width_formula(self):
        r=platform_zone_widths(applicable=True,method='platform_waiting_method_two',block_passengers=80,block_length_m=20,circulation_peak_5min=200)
        self.assertAlmostEqual(r['zone_B_m'],3.72);self.assertEqual(r['zone_C_m'],1)
        self.assertEqual(r['status'],'guidance_calculation');self.assertEqual(r['full_platform_width_status'],'unassessed')
    def test_guidance_zero_circulation(self):
        r=platform_zone_widths(applicable=True,method='platform_waiting_method_two',block_passengers=0,block_length_m=20,circulation_peak_5min=0)
        self.assertEqual(r['zone_C_m'],0)
    def test_guidance_missing_or_different_method(self):
        for method,n in (('concourse_waiting',80),('platform_waiting_method_two',None)):
            self.assertEqual(platform_zone_widths(applicable=True,method=method,block_passengers=n,block_length_m=20,circulation_peak_5min=200)['status'],'unassessed')
    def test_guidance_bad_inputs(self):
        with self.assertRaises(ValueError):platform_zone_widths(applicable=True,method='platform_waiting_method_two',block_passengers=10,block_length_m=0,circulation_peak_5min=0)
    def test_strict_mode_blocks_synthetic_components(self):
        r=admission('gb_rules_strict',synthetic_components=True,mandatory_unknowns=[])
        self.assertFalse(r['offline_analysis_allowed']);self.assertFalse(r['construction_authorised'])
    def test_reference_mode_remains_labelled(self):
        r=admission('gb_reference_inspired',synthetic_components=True,mandatory_unknowns=['gauging'])
        self.assertTrue(r['offline_analysis_allowed']);self.assertEqual(r['UK_profile_gate'],'not_passed')
    def test_resolved_inputs_are_not_construction_authority(self):
        r=admission('gb_rules_strict',synthetic_components=False,mandatory_unknowns=[],game_tested=True)
        self.assertTrue(r['offline_analysis_allowed']);self.assertFalse(r['construction_authorised'])
    def test_numeric_and_flag_errors(self):
        with self.assertRaises(ValueError):new_line_radius(float('nan'),applicable=True,new_line=True)
        with self.assertRaises(ValueError):nominal_gauge(applicable=1)
        with self.assertRaises(ValueError):gb_track_centres(applicable=True,straight='yes')
    def test_override_pending(self):
        self.assertEqual(vertical_radius(900,kind='sag',applicable=True,override_pending=True)['status'],'unassessed')
    def test_invalid_lookup_or_mode(self):
        with self.assertRaises(ValueError):parameter('phantom')
        with self.assertRaises(ValueError):admission('uk_safe',synthetic_components=False,mandatory_unknowns=[])
