import math
import unittest
from railinterface.reference import *
from railinterface.datums import RailSection

class DatumTests(unittest.TestCase):
    def test_nearest_running_edge_is_not_track_centre(self):
        y,z=RailSection().edge(nearest_rail_offset_mm=737.5,height_mm=915,side=1)
        self.assertAlmostEqual(y,1.455);self.assertAlmostEqual(z,.915)
    def test_mirrored_side(self):
        a=RailSection().edge(nearest_rail_offset_mm=737.5,height_mm=915,side=1)
        b=RailSection().edge(nearest_rail_offset_mm=737.5,height_mm=915,side=-1)
        self.assertEqual(a,(-b[0],b[1]))
    def test_nominal_730_reference(self):
        self.assertAlmostEqual(RailSection().edge(nearest_rail_offset_mm=730,height_mm=915,side=1)[0],1.4475)
    def test_wrong_datum_exposes_20mm_not_737(self):
        self.assertAlmostEqual(RailSection().measure((.7375,.915),side=1)['nearest_rail_offset_mm'],20)
    def test_roundtrip_rotated_translated(self):
        for angle in (-.12,0,.12):
            for side in (-1,1):
                section=RailSection(1435,30,5,angle)
                p=section.edge(nearest_rail_offset_mm=742,height_mm=908,side=side)
                r=section.measure(p,side=side)
                self.assertAlmostEqual(r['nearest_rail_offset_mm'],742,places=9)
                self.assertAlmostEqual(r['height_mm_perpendicular_to_rail_plane'],908,places=9)
    def test_rotation_preserves_distance(self):
        p=RailSection(1435,0,0,.1).edge(nearest_rail_offset_mm=737.5,height_mm=915,side=1)
        self.assertAlmostEqual(math.hypot(*p),math.hypot(1.455,.915))
    def test_wrong_side_rejected(self):
        with self.assertRaises(ValueError):RailSection().measure((1.455,.915),side=-1)
    def test_invalid_side(self):
        for side in (0,2,True,1.0):
            with self.assertRaises(ValueError):RailSection().edge(nearest_rail_offset_mm=730,height_mm=915,side=side)
    def test_invalid_section_inputs(self):
        for kwargs in ({'gauge_mm':0},{'gauge_mm':True},{'rail_plane_angle_rad':math.pi/4},{'origin_y_m':float('nan')},{'origin_z_m':float('inf')}):
            with self.assertRaises(ValueError):RailSection(**kwargs)
    def test_missing_coordinates(self):
        with self.assertRaises(ValueError):RailSection().measure((1,),side=1)
    def test_invalid_edge_inputs(self):
        for off,h in ((0,915),(730,-1),(False,915),(730,float('inf'))):
            with self.assertRaises(ValueError):RailSection().edge(nearest_rail_offset_mm=off,height_mm=h,side=1)
    def test_signed_plane_not_track_gauge_cant_inference(self):
        sec=RailSection(1435,0,0,.05)
        r=sec.measure(sec.edge(nearest_rail_offset_mm=737.5,height_mm=915,side=1),side=1)
        self.assertAlmostEqual(r['height_mm_perpendicular_to_rail_plane'],915)

class ReferenceTests(unittest.TestCase):
    def test_reviewed_record_is_not_current_admission(self):
        r=reference();self.assertFalse(r['current_full_issue_reviewed']);self.assertFalse(r['strict_uk_admitted'])
    def test_normal_design_height_boundaries(self):
        for height,status in ((900,'reference_clause_pass'),(915,'reference_clause_pass'),(899.999,'reference_clause_fail'),(915.001,'reference_clause_fail')):
            self.assertEqual(height_check(height,applicable=True)['status'],status)
    def test_legacy_height_not_default(self):
        self.assertEqual(height_check(890,applicable=True,legacy_stock=True)['status'],'reference_clause_pass')
        self.assertEqual(height_check(890,applicable=True)['status'],'reference_clause_fail')
    def test_build_tolerance_never_design_permission(self):
        self.assertEqual(height_check(925,applicable=True)['status'],'reference_clause_fail')
    def test_build_allowance_requires_linked_adjustment(self):
        for state in (None,False):
            self.assertEqual(height_check(925,applicable=True,stage='build_maintenance',linked_lower_sector_adjustment_confirmed=state)['status'],'unassessed')
    def test_build_explicitly_confirmed(self):
        self.assertEqual(height_check(925,applicable=True,stage='build_maintenance',linked_lower_sector_adjustment_confirmed=True)['status'],'reference_clause_pass')
        self.assertEqual(height_check(925.01,applicable=True,stage='build_maintenance',linked_lower_sector_adjustment_confirmed=True)['status'],'reference_clause_fail')
    def test_missing_height_scope(self):
        for h,scope in ((None,True),(915,None)):
            self.assertEqual(height_check(h,applicable=scope)['status'],'unassessed')
    def test_height_not_applicable(self):
        self.assertEqual(height_check(None,applicable=False)['status'],'not_applicable')
    def test_invalid_height_flags(self):
        for kw in ({'applicable':1},{'applicable':True,'legacy_stock':1},{'applicable':True,'stage':'operation'}):
            with self.assertRaises(ValueError):height_check(915,**kw)
    def test_offset_bounds(self):
        for value,status in ((730,'reference_clause_pass'),(745,'reference_clause_pass'),(729.99,'reference_clause_fail'),(745.01,'reference_clause_fail')):
            self.assertEqual(offset_check(value,applicable=True,resolved_minimum_mm=730,minimum_origin='explicit_standard_case_reference')['status'],status)
    def test_offset_requires_resolved_minimum(self):
        self.assertEqual(offset_check(737.5,applicable=True,resolved_minimum_mm=None,minimum_origin='unresolved')['status'],'unassessed')
    def test_offset_cannot_hide_curve_minimum(self):
        minimum=draft_curve_offset(300,standard_case_confirmed=True)['minimum_offset_mm']
        self.assertEqual(offset_check(737.5,applicable=True,resolved_minimum_mm=minimum,minimum_origin='draft_curve_example')['status'],'reference_clause_fail')
    def test_width_single_face(self):
        self.assertEqual(width_requirement([100])['minimum_width_m'],2.5)
        self.assertEqual(width_requirement([100.001])['minimum_width_m'],3)
    def test_island_width_speed_combinations(self):
        for speeds,value in (([15,15],4),([100,100],4),([101,100],5.5),([125,125],6)):
            self.assertEqual(width_requirement(speeds)['minimum_width_m'],value)
    def test_general_obstacle_minima_distinct_from_gross_width(self):
        r=width_requirement([15,15]);self.assertEqual(r['minimum_width_m'],4);self.assertEqual(sum(r['edge_obstacle_clearances_m']),5)
    def test_speed_order_preserved(self):
        self.assertEqual(width_requirement([101,15])['edge_obstacle_clearances_m'],[3,2.5])
    def test_unknown_speed_does_not_use_motion_target(self):
        self.assertEqual(width_requirement([15,None])['status'],'unassessed')
    def test_invalid_speed_inputs(self):
        for speeds in ([],[1,2,3],[-1],[True],[float('nan')]):
            with self.assertRaises(ValueError):width_requirement(speeds)
    def test_no_unapproved_width_exceptions(self):
        self.assertFalse(width_requirement([15,15])['exceptional_reductions_applied'])
    def test_taper_lengths(self):
        self.assertAlmostEqual(taper_length(15,'height')['minimum_longitudinal_length_m'],.6)
        self.assertAlmostEqual(taper_length(-15,'offset')['minimum_longitudinal_length_m'],1.2)
    def test_taper_does_not_approve_coping(self):
        self.assertEqual(taper_length(15,'offset')['coping_unit_compatibility'],'unassessed')
    def test_invalid_taper_kind(self):
        with self.assertRaises(ValueError):taper_length(15,'gauge')
    def test_draft_curve_breakpoints(self):
        for radius,value in ((400,730),(360,730),(300,658+26000/300),(160,820.5)):
            self.assertAlmostEqual(draft_curve_offset(radius,standard_case_confirmed=True)['minimum_offset_mm'],value)
    def test_rounded_example_table_is_not_formula(self):
        self.assertAlmostEqual(draft_curve_offset(300,standard_case_confirmed=True)['minimum_offset_mm'],744.6666666666666)
    def test_draft_domain_not_extended(self):
        self.assertEqual(draft_curve_offset(159,standard_case_confirmed=True)['status'],'outside_reviewed_draft_domain')
    def test_draft_special_case_not_assumed(self):
        self.assertEqual(draft_curve_offset(400)['status'],'unassessed')
    def test_draft_straight_explicit(self):
        self.assertEqual(draft_curve_offset(None,straight=True,standard_case_confirmed=True)['minimum_offset_mm'],730)
    def test_draft_invalid_scope(self):
        with self.assertRaises(ValueError):draft_curve_offset(400,straight=True)
    def test_all_positive_checks_leave_uk_unassessed(self):
        for check in (height_check(915,applicable=True),width_requirement([15,15]),draft_curve_offset(400,standard_case_confirmed=True)):
            self.assertEqual(check['current_uk_compliance'],'unassessed');self.assertFalse(check['construction_authorised'])
