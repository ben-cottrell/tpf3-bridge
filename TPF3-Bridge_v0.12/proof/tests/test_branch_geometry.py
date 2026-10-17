import math
import unittest
from dataclasses import replace,asdict
from copy import deepcopy
from railbranch.geometry import *
from railbranch.operations import verify_candidate,compile_resources

class BranchGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.js={m:build(mode=m) for m in MODES}
    def test_four_complete_routes(self):
        self.assertEqual(set(self.js['flat'].routes),set(ROUTES))
        self.assertTrue(all(j.assessment['complete_required_routes_connected'] for j in self.js.values()))
    def test_internal_ports_not_dangling(self):
        n=self.js['flat'].network;count={p:0 for p in n.ports}
        for e in n.edges.values():count[e.u]+=1;count[e.v]+=1
        self.assertEqual({p for p,k in count.items() if k==1},{'W_E','W_W','E_E','E_W','B_IN','B_OUT'})
    def test_exact_main_interfaces(self):
        p=self.js['flat'].assessment['ports_xyz_m']
        self.assertEqual(p['W_E'],(0.,1.7,20.));self.assertEqual(p['E_W'],(6000.,-1.7,20.))
    def test_exact_branch_spacing(self):
        p=self.js['flat'].assessment['ports_xyz_m'];self.assertAlmostEqual(math.dist(p['B_IN'],p['B_OUT']),3.4)
    def test_two_turnouts_fourteen_edges(self):
        j=self.js['flat'];self.assertEqual(len(j.network.turnouts),2);self.assertEqual(len(j.network.edges),14)
    def test_same_plan_for_modes(self):
        self.assertEqual(self.js['flat'].network.canonical(),self.js['flyover'].network.canonical())
    def test_flat_and_vertical_separation(self):
        self.assertEqual(self.js['flat'].assessment['crossing']['minimum_rail_separation_m'],0)
        for m in ('flyover','diveunder'):self.assertEqual(self.js[m].assessment['crossing']['minimum_rail_separation_m'],7.5)
    def test_grade_sign_is_preserved(self):
        a=self.js['flyover'];b=self.js['diveunder'];x=a.assessment['crossing']['x_m']
        self.assertEqual(a.z('return_connector',x),27.5);self.assertEqual(b.z('return_connector',x),12.5)
    def test_crossing_root_is_actual_geometry(self):
        j=self.js['flat'];c=j.assessment['crossing'];self.assertAlmostEqual(j.point('return_connector',c['x_m'])[1],1.7,10)
    def test_complete_footprint_not_single_point(self):
        j=self.js['flyover'];a,b=j.assessment['crossing']['footprint_x_m']
        self.assertGreater(b-a,40)
        for k in range(101):self.assertGreaterEqual(j.z('return_connector',a+(b-a)*k/100)-20,6.8)
    def test_separated_topology_does_not_join_at_crossing(self):
        for j in self.js.values():
            self.assertEqual(j.assessment['crossing']['turning_connections'],[])
            a,b=(j.network.edges[e] for e in j.assessment['crossing']['edge_ids'])
            self.assertFalse({a.u,a.v}&{b.u,b.v})
    def test_illegal_normal_to_reverse_turn_excluded(self):
        j=self.js['flat'];t=next(iter(j.network.turnouts.values()))
        self.assertEqual(j.network.enumerate_paths(t.normal,t.reverse),[])
    def test_out_and_return_order_is_bound_not_sample(self):
        self.assertGreater(self.js['flat'].assessment['out_return_y_order_lower_bound_m'],3.39999)
    def test_order_bound_against_dense_samples(self):
        j=self.js['flat'];a=j.network.edges['out_connector'].curve;b=j.network.edges['return_connector'].curve
        bound=j.assessment['out_return_y_order_lower_bound_m']
        for i in range(501):
            x=a.at(0)[0]+(a.at(1)[0]-a.at(0)[0])*i/500
            self.assertGreaterEqual(state(a,x)[0]-state(b,x)[0]+1e-9,bound)
    def test_3d_shared_port_positions(self):
        j=self.js['flyover'];pts={}
        for eid,e in j.network.edges.items():
            for p,x in [(e.u,e.curve.at(0)[0]),(e.v,e.curve.at(1)[0])]:
                q=j.point(eid,x)
                if p in pts:self.assertLess(math.dist(q,pts[p]),1e-7)
                pts[p]=q
    def test_all_edges_level_at_connections(self):
        j=self.js['flyover']
        for eid,a in j.height.items():
            for x in (a.knots[0].x,a.knots[-1].x):self.assertAlmostEqual(a.state(x)['zp'],0.,12)
    def test_full_grade_bound_checks_dense_samples(self):
        j=self.js['flyover']
        for row in j.assessment['curve_checks']:
            e=j.network.edges[row['edge_id']];a,b=e.curve.at(0)[0],e.curve.at(1)[0]
            for k in range(101):
                x=a+(b-a)*k/100;yp=state(e.curve,x)[1];zp=j.height[e.id].state(x)['zp']
                self.assertLessEqual(abs(zp/math.hypot(1,yp)),row['grade_upper']+1e-10)
    def test_600m_ramp_rejected_without_geometry_deletion(self):
        j=build(replace(JunctionSpec(),ramp_m=600),mode='flyover')
        self.assertFalse(j.assessment['accepted_for_reference_comparison']);self.assertTrue(j.assessment['complete_required_routes_connected'])
        with self.assertRaises(ValueError):compile_resources(j)
    def test_900m_ramp_fits(self):self.assertTrue(build(replace(JunctionSpec(),ramp_m=900),'diveunder').assessment['accepted_for_reference_comparison'])
    def test_1050m_ramp_cannot_enter_turnout(self):
        with self.assertRaisesRegex(ValueError,'full ramp'):build(replace(JunctionSpec(),ramp_m=1050),'flyover')
    def test_insufficient_height_rejected(self):
        a=build(replace(JunctionSpec(),level_change_m=6.5),'flyover').assessment
        self.assertIn('crossing_envelope_insufficient',a['failed_checks'])
    def test_stronger_radius_not_silently_relaxed(self):
        j=build(replace(JunctionSpec(),minimum_radius_m=1000),'flat')
        self.assertFalse(j.assessment['accepted_for_reference_comparison'])
        self.assertEqual(j.spec.minimum_radius_m,1000)
    def test_clipped_site_fails(self):
        j=build(replace(JunctionSpec(),site_y_min_m=-50));self.assertFalse(j.assessment['site_plan_pass'])
    def test_direct_length_and_graded_increment(self):
        self.assertAlmostEqual(self.js['flat'].assessment['routes']['main_east']['length_m'],6000)
        self.assertGreater(self.js['flyover'].assessment['routes']['branch_in']['length_m'],self.js['flat'].assessment['routes']['branch_in']['length_m'])
    def test_length_against_dense_3d_chords(self):
        j=self.js['flyover'];eid='return_connector';c=j.network.edges[eid].curve;a,b=c.at(0)[0],c.at(1)[0]
        ps=[j.point(eid,a+(b-a)*i/3000) for i in range(3001)]
        self.assertAlmostEqual(j.length(eid),sum(math.dist(x,y) for x,y in zip(ps,ps[1:])),places=3)
    def test_lowered_curve_midpoints_under_bound(self):
        j=self.js['flyover'];eid='return_connector';p=j.polyline(eid)
        self.assertLess(p['position_error_bound_m'],.020001)
        for a,b in zip(p['points'],p['points'][1:]):
            exact=j.point(eid,(a[0]+b[0])/2);linear=tuple((x+y)/2 for x,y in zip(a,b))
            self.assertLessEqual(math.dist(exact,linear),p['position_error_bound_m']+1e-8)
    def test_long_unit_holds_clear_at_2200(self):self.assertTrue(holding_assessment(self.js['flat'],242.6)['fits_clear'])
    def test_short_holding_fouls_crossing(self):
        r=holding_assessment(self.js['flat'],242.6,stop_x=2300)
        self.assertFalse(r['fits_clear']);self.assertTrue(r['crossing_fouled_by_held_formation'])
    def test_margins_can_fail_without_tail_fouling(self):
        r=holding_assessment(self.js['flat'],300)
        self.assertFalse(r['fits_clear']);self.assertFalse(r['crossing_fouled_by_held_formation'])
    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):build(mode='magic')
    def test_nonfinite_and_bool_spec_rejected(self):
        for v in (math.inf,math.nan,True):
            with self.subTest(v=v),self.assertRaises(ValueError):JunctionSpec(ramp_m=v)
    def test_bad_topological_order_rejected(self):
        with self.assertRaises(ValueError):JunctionSpec(diverge_x_m=1000)
    def test_stale_candidate_hash_rejected(self):
        j=deepcopy(self.js['flat']);j.assessment['mode']='flyover'
        with self.assertRaises(ValueError):verify_candidate(j)
    def test_physical_network_mutation_rejected(self):
        j=deepcopy(self.js['flat']);j.network.metadata['changed']=True
        with self.assertRaises(ValueError):verify_candidate(j)
    def test_no_construction_or_old_terrain_claim(self):
        for j in self.js.values():
            self.assertFalse(j.assessment['construction_authorised']);self.assertIn('not_performed',j.assessment['terrain_assessment'])
    def test_component_record_not_stretched(self):
        j=self.js['flat']
        for t in j.network.turnouts.values():
            self.assertAlmostEqual(j.network.ports[t.normal].position[0]-j.network.ports[t.toe].position[0],40)
            self.assertAlmostEqual(j.network.ports[t.reverse].position[1]-j.network.ports[t.toe].position[1],1.5)
