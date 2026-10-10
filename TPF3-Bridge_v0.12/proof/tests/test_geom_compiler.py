from dataclasses import replace
import copy
import unittest
from railgeom.curves import line,join_check,distance
from railgeom.network import Network,RailPath,Step
from railgeom.patterns import *
from railgeom.compiler import *
from railgeom.operations import make_claims
from railproof.model import conflict


class GeometryCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cross=build_crossover();cls.c=compile_assembly(cls.cross)
        cls.fan=build_fan();cls.f=compile_assembly(cls.fan)

    def test_crossover_complete_inventory(self):
        self.assertEqual(len(self.cross.network.turnouts),2)
        self.assertEqual(len(self.cross.network.edges),7)
        self.assertEqual(len(self.c.routes),4)

    def test_crossover_expected_endpoints(self):
        self.assertEqual(self.cross.network.ports['T2:T'].position,(100.,4.5))
        self.assertEqual(self.cross.network.metadata['span_m'],100)

    def test_cross_route_length_exceeds_straight(self):
        a=self.c.routes['cross_forward'];b=self.c.routes['lower_through']
        self.assertGreater(a.length_lower_m,b.length_upper_m)

    def test_reverse_route_same_length(self):
        a=self.c.routes['cross_forward'];b=self.c.routes['cross_reverse']
        self.assertAlmostEqual(a.length_upper_m,b.length_upper_m)

    def test_parallel_through_routes_only_share_compatible_control(self):
        a=make_claims(self.c.routes['lower_through'].requirements,0,100,'A')
        b=make_claims(self.c.routes['upper_through'].requirements,0,100,'B')
        self.assertFalse(any(conflict(x,y) for x in a for y in b))
        shared={x.resource for x in a}&{x.resource for x in b}
        self.assertEqual(shared,{'control:CROSSOVER_CONTROL'})

    def test_crossing_route_conflicts_with_both_mains(self):
        a=make_claims(self.c.routes['cross_forward'].requirements,0,100,'X')
        for name in ('lower_through','upper_through'):
            b=make_claims(self.c.routes[name].requirements,0,100,name)
            self.assertTrue(any(conflict(x,y) for x in a for y in b))

    def test_opposite_direction_same_track_conflicts(self):
        a=make_claims(self.c.routes['cross_forward'].requirements,0,100,'A')
        b=make_claims(self.c.routes['cross_reverse'].requirements,0,100,'B')
        self.assertTrue(any(conflict(x,y) for x in a for y in b))

    def test_wrong_diagonal_does_not_exist(self):
        n=self.cross.network
        self.assertEqual(n.enumerate_paths('HIGH_W','LOW_E'),[])

    def test_turnout_normal_to_reverse_not_a_legal_turn(self):
        n=self.cross.network
        self.assertEqual(n.enumerate_paths('T1:N','T1:R'),[])

    def test_manual_illegal_route_rejected(self):
        a=copy.deepcopy(self.cross)
        a.routes={'bad':RailPath('bad','T1:N','T1:R',(Step('T1:normal',False),Step('T1:reverse',True)))}
        with self.assertRaisesRegex(ValueError,'traversal contract'):compile_assembly(a)

    def test_graph_search_budget_reported(self):
        with self.assertRaisesRegex(ValueError,'search_exhausted'):
            self.cross.network.enumerate_paths('T1:T','T2:T',max_expansions=1)

    def test_coordinates_do_not_merge_nodes(self):
        n=Network('coincident')
        n.port('a',(0.,0.));n.port('b',(10.,0.));n.port('c',(10.,0.));n.port('d',(20.,0.))
        n.edge('one','a','b',line((0.,0.),(10.,0.)));n.edge('two','c','d',line((10.,0.),(20.,0.)))
        self.assertEqual(n.enumerate_paths('a','d'),[])
        with self.assertRaisesRegex(ValueError,'centreline_contact'):compile_assembly(Assembly(n,{}, {},GeometryProfile()))

    def test_unmodelled_crossing_rejected_not_connected(self):
        n=Network('crossing')
        for id,p in [('a',(-10.,0.)),('b',(10.,0.)),('c',(0.,-10.)),('d',(0.,10.))]:n.port(id,p)
        n.edge('one','a','b',line(n.ports['a'].position,n.ports['b'].position))
        n.edge('two','c','d',line(n.ports['c'].position,n.ports['d'].position))
        with self.assertRaisesRegex(ValueError,'centreline_contact'):compile_assembly(Assembly(n,{}, {},GeometryProfile()))
        self.assertEqual(n.enumerate_paths('a','d'),[])

    def test_near_parallel_edges_acquire_geometric_exclusion(self):
        n=Network('near')
        for id,p in [('a',(0.,0.)),('b',(100.,0.)),('c',(0.,3.)),('d',(100.,3.))]:n.port(id,p)
        n.edge('one','a','b',line(n.ports['a'].position,n.ports['b'].position))
        n.edge('two','c','d',line(n.ports['c'].position,n.ports['d'].position))
        c=compile_assembly(Assembly(n,{}, {},GeometryProfile()))
        self.assertEqual(len(c.provenance['proximity_contacts']),1)
        self.assertEqual(n.enumerate_paths('a','d'),[])

    def test_invalid_port_geometry_rejected(self):
        a=copy.deepcopy(self.cross);e=a.network.edges['diagonal']
        a.network.edges[e.id]=replace(e,curve=e.curve.transformed(dy=1))
        with self.assertRaisesRegex(ValueError,'Port/geometry mismatch'):compile_assembly(a)

    def test_conflicting_linked_state_mapping_rejected(self):
        a=copy.deepcopy(self.cross);n=a.network
        t=n.turnouts['T2'];n.turnouts['T2']=replace(t,normal_state='R',reverse_state='N')
        for id in ('T2:normal','T2:reverse'):
            e=n.edges[id];n.edges[id]=replace(e,state='R' if e.state=='N' else 'N')
        with self.assertRaisesRegex(ValueError,'internally_incompatible'):compile_assembly(a)

    def test_fan_four_roads_eight_movements(self):
        self.assertEqual(len(self.f.platforms),4);self.assertEqual(len(self.f.routes),8)
        self.assertEqual(len(self.fan.network.turnouts),3)

    def test_fan_full_routes_have_continuous_geometry(self):
        n=self.fan.network
        for path in self.fan.routes.values():
            curves=[n.oriented_curve(s) for s in path.steps]
            for a,b in zip(curves,curves[1:]):self.assertTrue(join_check(a,b)['pass'])

    def test_fan_outside_route_longer_than_spine(self):
        self.assertGreater(self.f.routes['P4:in'].length_lower_m,self.f.routes['P1:in'].length_upper_m)

    def test_storage_is_separate_from_arrival_path(self):
        for id,p in self.f.platforms.items():
            self.assertNotIn(p['storage_edge'],self.f.routes[id+':in'].edge_ids)
            self.assertIn(p['storage_edge'],self.f.edge_requirements)

    def test_route_chainage_contiguous_intervals(self):
        for r in self.f.routes.values():
            end=[0.,0.]
            for s in r.segments:
                self.assertEqual(s['entry_chainage_interval_m'],end)
                end=s['exit_chainage_interval_m']
            self.assertEqual(end,[r.length_lower_m,r.length_upper_m])

    def test_every_requirement_has_provenance(self):
        for c in (self.c,self.f):
            for route in c.routes.values():
                for r in route.requirements:self.assertIn(r.resource,c.provenance['resources'])

    def test_geometry_changes_distances_and_hashes(self):
        a=compile_assembly(build_fan(FanSpec(platform_start_x_m=700)))
        self.assertNotEqual(a.compile_hash,self.f.compile_hash)
        self.assertAlmostEqual(a.routes['P1:in'].length_upper_m-self.f.routes['P1:in'].length_upper_m,50,places=6)

    def test_profile_change_invalidates_compile_hash(self):
        a=build_crossover();a.profile=GeometryProfile(envelope_half_width_m=1.8)
        self.assertNotEqual(compile_assembly(a).compile_hash,self.c.compile_hash)

    def test_compilation_deterministic(self):
        self.assertEqual(compile_assembly(build_crossover()).export(),self.c.export())

    def test_all_curve_radius_bounds_pass_declared_profile(self):
        for c in (self.c,self.f):
            self.assertLessEqual(max(x['curvature_upper_per_m'] for x in c.provenance['curves'].values()),1/300)

    def test_radius_failure_is_not_false_impossibility_proof(self):
        with self.assertRaisesRegex(ValueError,'not a proof'):
            compile_assembly(build_crossover(CrossoverSpec(turnout_span_m=20)))

    def test_authorised_crossover_span_preserved(self):
        with self.assertRaisesRegex(ValueError,'authorised_span'):build_crossover(CrossoverSpec(maximum_span_m=70))

    def test_positive_tangent_required(self):
        with self.assertRaisesRegex(ValueError,'positive connecting tangent'):
            build_crossover(CrossoverSpec(turnout_span_m=60))

    def test_fan_spine_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlap'):FanSpec(toe_step_m=40)

    def test_fan_clear_of_platform_start(self):
        with self.assertRaisesRegex(ValueError,'platform_start'):build_fan(FanSpec(platform_start_x_m=450))

    def test_narrow_parallel_track_contract_rejected(self):
        with self.assertRaisesRegex(ValueError,'separation'):build_crossover(CrossoverSpec(spacing_m=3))

    def test_unknown_uk_profile_rejected(self):
        with self.assertRaises(ValueError):GeometryProfile(fidelity='UK_approved')

    def test_game_and_full_gauging_remain_unassessed(self):
        a=self.c.provenance['assessments']
        self.assertEqual(a['full_vehicle_gauging'],'unassessed');self.assertEqual(a['game_construction'],'not_tested')
