from dataclasses import replace
import copy
import unittest
from railcompact.composition import build_compact,CompactSpec
from railcompact.compiler import compile_assembly
from railclear.model import digest
from railinterface.platforms import *
from railinterface.demo import gate_platforms

class PlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=build_compact('scissors',CompactSpec(first_fan_toe_x_m=205))
        cls.c=compile_assembly(cls.s.assembly)
        cls.speeds={pid:15. for pid in cls.s.assembly.platforms}
        cls.a=make_platforms(cls.s,cls.c,permissible_speeds_mph=cls.speeds)
    def island(self):return copy.deepcopy(self.a['islands'][2])
    def facility(self,offset=0,width=4):
        i=self.island();mid=sum(i['surface_bounds_xy_m'][2:])/2
        return Facility(width,20,810,mid+offset)
    def test_four_islands_eight_faces(self):
        self.assertEqual(len(self.a['islands']),4);self.assertEqual(len(self.a['faces']),8)
    def test_width_accounts_for_both_half_gauges(self):
        for island in self.a['islands']:self.assertAlmostEqual(island['width_m'],12-1.435-2*.7375)
    def test_face_height_and_coordinates(self):
        f=self.a['faces']['B1'];self.assertEqual(f['side'],1)
        self.assertAlmostEqual(f['edge_start_xyz_m'][1],7.455);self.assertAlmostEqual(f['edge_start_xyz_m'][2],.915)
    def test_exact_boarding_intervals_unchanged(self):
        for pid,f in self.a['faces'].items():
            self.assertEqual(f['edge_start_xyz_m'][0],710 if pid[-1] in '12' else 650)
            self.assertEqual(f['edge_end_xyz_m'][0],970)
    def test_scissors_not_under_boarding_slab(self):
        self.assertTrue(all(i['centreline_hull_check']['status']=='disjoint_hulls' for i in self.a['islands']))
    def test_all_reference_dimensions_pass_without_current_claim(self):
        for f in self.a['faces'].values():
            self.assertEqual(f['height_check']['status'],'reference_clause_pass');self.assertEqual(f['offset_check']['status'],'reference_clause_pass')
        self.assertEqual(self.a['current_uk_compliance'],'unassessed')
    def test_immutable_track_and_resources(self):
        before=self.s.assembly.network.digest();compiled=digest(self.c.export())
        make_platforms(self.s,self.c,permissible_speeds_mph=self.speeds)
        self.assertEqual(before,self.s.assembly.network.digest());self.assertEqual(compiled,digest(self.c.export()))
    def test_unknown_permissible_speed_is_unassessed(self):
        a=make_platforms(self.s,self.c)
        self.assertTrue(all(i['width_check']['status']=='unassessed' for i in a['islands']))
    def test_missing_speed_inventory_rejected(self):
        with self.assertRaises(ValueError):make_platforms(self.s,self.c,permissible_speeds_mph={'B1':15})
    def test_wrong_gauge_not_silently_imported(self):
        with self.assertRaises(ValueError):PlatformProfile(gauge_mm=1000)
    def test_bad_profile_datums(self):
        for kw in ({'nearest_rail_offset_mm':True},{'height_mm':-1},{'offset_case':'centreline'}):
            with self.assertRaises(ValueError):PlatformProfile(**kw)
    def test_stale_rail_geometry(self):
        s=copy.deepcopy(self.s);s.assembly.network.metadata['new_geometry']='changed'
        with self.assertRaises(ValueError):make_platforms(s,self.c,permissible_speeds_mph=self.speeds)
    def test_compiled_platform_changes_rejected(self):
        s=copy.deepcopy(self.s);s.assembly.platforms['B1']['usable_length_m']=200
        with self.assertRaises(ValueError):make_platforms(s,self.c,permissible_speeds_mph=self.speeds)
    def test_canted_platform_adapter_rejects_instead_of_ignoring(self):
        s=copy.deepcopy(self.s);s.assembly.network.metadata['cant_mm']=20;c=compile_assembly(s.assembly)
        with self.assertRaises(ValueError):make_platforms(s,c,permissible_speeds_mph=self.speeds)
    def test_assessment_hash_checks_changes(self):
        a=copy.deepcopy(self.a);a['islands'][0]['width_m']=100
        with self.assertRaises(ValueError):verify_assessment(a,self.c)
    def test_assessment_valid(self):self.assertTrue(verify_assessment(self.a,self.c))
    def test_wrong_compile_join(self):
        a=copy.deepcopy(self.a);a['compile_hash']='other'
        with self.assertRaises(ValueError):verify_assessment(a,self.c)
    def test_centred_facility_2545mm_each_side(self):
        r=facility_check(self.island(),self.facility())
        self.assertEqual(r['status'],'reference_clause_pass')
        for gap in r['edge_gaps_m']:self.assertAlmostEqual(gap,2.545)
    def test_displaced_facility_blocks_only_near_face(self):
        r=facility_check(self.island(),self.facility(-1))
        self.assertEqual(r['failed_platform_faces'],['B1']);self.assertAlmostEqual(r['edge_gaps_m'][0],1.545)
    def test_nearest_authorised_fit_preserves_size(self):
        r=fit_facility(self.island(),self.facility(-1),allowed_centre_y_m=[10,14])
        self.assertEqual(r['status'],'fitted_within_reference_model');self.assertEqual(r['selected']['width_m'],4)
        self.assertAlmostEqual(r['lateral_move_m'],.955);self.assertFalse(r['track_moved'])
    def test_oversize_requires110mm_more_space(self):
        r=fit_facility(self.island(),self.facility(width=4.2),allowed_centre_y_m=[10,14])
        self.assertEqual(r['status'],'infeasible_fixed_section');self.assertAlmostEqual(r['extra_width_needed_m'],.11)
    def test_high_speed_not_motion_speed(self):
        i=self.island();i['width_check']=width_requirement([125,125])
        r=fit_facility(i,self.facility(),allowed_centre_y_m=[10,14])
        self.assertEqual(r['status'],'infeasible_fixed_section');self.assertAlmostEqual(r['extra_width_needed_m'],.91)
    def test_no_lateral_authority(self):
        f=self.facility(-1)
        r=fit_facility(self.island(),f,allowed_centre_y_m=[f.centre_y_m]*2)
        self.assertEqual(r['status'],'outside_authorised_moves')
    def test_zero_budget_is_not_infeasible(self):
        r=fit_facility(self.island(),self.facility(),allowed_centre_y_m=[10,14],budget=0)
        self.assertEqual(r['status'],'search_exhausted');self.assertEqual(r['evaluations'],0)
    def test_longitudinal_fit_required(self):
        f=replace(self.facility(),centre_x_m=709)
        self.assertEqual(fit_facility(self.island(),f,allowed_centre_y_m=[10,14])['status'],'infeasible_fixed_section')
    def test_boundary_feasible_facility(self):
        r=fit_facility(self.island(),self.facility(width=4.09),allowed_centre_y_m=[10,14])
        self.assertEqual(r['status'],'fitted_within_reference_model')
    def test_invalid_fit_bounds(self):
        for bounds in ([12],[14,10],[float('nan'),14]):
            with self.assertRaises(ValueError):fit_facility(self.island(),self.facility(),allowed_centre_y_m=bounds)
    def test_invalid_fit_budget(self):
        with self.assertRaises(ValueError):fit_facility(self.island(),self.facility(),allowed_centre_y_m=[10,14],budget=True)
    def test_invalid_facility_dimensions(self):
        for vals in ((0,20,810,12),(4,-1,810,12),(4,20,float('nan'),12)):
            with self.assertRaises(ValueError):Facility(*vals)
    def test_unknown_speed_keeps_fit_unassessed(self):
        i=self.island();i['width_check']=width_requirement([None,None])
        self.assertEqual(fit_facility(i,self.facility(),allowed_centre_y_m=[10,14])['status'],'unassessed')
    def test_planning_exclusion_is_explicit_not_track_closure(self):
        chk=facility_check(self.island(),self.facility(-1));r=gate_platforms(self.a,self.c,chk,exclude_failed=True)
        self.assertEqual(r['excluded_platform_ids'],['B1']);self.assertFalse(r['is_physical_track_closure'])
    def test_diagnostic_mode_does_not_close_platform(self):
        chk=facility_check(self.island(),self.facility(-1));r=gate_platforms(self.a,self.c,chk,exclude_failed=False)
        self.assertEqual(r['excluded_platform_ids'],[])
    def test_changed_facility_result_not_trusted(self):
        chk=facility_check(self.island(),self.facility(-1));chk['failed_platform_faces']=[]
        with self.assertRaises(ValueError):gate_platforms(self.a,self.c,chk,exclude_failed=True)
    def test_other_island_result_cannot_be_attached(self):
        chk=facility_check(self.island(),self.facility(-1));chk['island_id']='IA12'
        with self.assertRaises(ValueError):gate_platforms(self.a,self.c,chk,exclude_failed=True)
    def test_no_general_approval_from_facility_fit(self):
        chk=facility_check(self.island(),self.facility())
        self.assertEqual(chk['current_uk_compliance'],'unassessed');self.assertFalse(chk['construction_authorised'])
    def test_contact_is_included_in_hull_screen(self):
        self.assertTrue(rectangles_overlap([0,1,0,1],[1,2,1,2]));self.assertFalse(rectangles_overlap([0,1,0,1],[2,3,0,1]))

    def test_height_failure_is_not_hidden_by_obstacle_pass(self):
        a=make_platforms(self.s,self.c,profile=PlatformProfile(height_mm=925),permissible_speeds_mph=self.speeds)
        island=a['islands'][2];chk=facility_check(island,self.facility())
        gate=gate_platforms(a,self.c,chk,exclude_failed=True)
        self.assertEqual(set(gate['excluded_platform_ids']),set(a['faces']))
    def test_unknown_width_keeps_joint_gate_unassessed(self):
        a=make_platforms(self.s,self.c);chk=facility_check(a['islands'][2],self.facility())
        self.assertEqual(gate_platforms(a,self.c,chk,exclude_failed=True)['status'],'unassessed')
    def test_offset_failure_is_not_hidden_by_obstacle_pass(self):
        a=make_platforms(self.s,self.c,profile=PlatformProfile(nearest_rail_offset_mm=800),permissible_speeds_mph=self.speeds)
        chk=facility_check(a['islands'][2],self.facility())
        self.assertEqual(len(gate_platforms(a,self.c,chk,exclude_failed=True)['excluded_platform_ids']),8)
