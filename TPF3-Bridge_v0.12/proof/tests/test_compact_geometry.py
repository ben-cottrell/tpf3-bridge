import copy,json,math,unittest
from dataclasses import replace
from railcompact.composition import build_compact,CompactSpec,FAMILIES,EXPECTED_PORTS
from railcompact.compiler import compile_assembly
from railcompact.search import fit_grid
from railgeom.patterns import GeometryProfile
from railgeom.curves import line
from railstation.checks import site_check,independence
from compact_support import model,fixture

class CompactGeometryTests(unittest.TestCase):
    def test_four_exact_external_ports(self):
        for f in FAMILIES:
            n=model(f)[0].assembly.network
            for p,xy in EXPECTED_PORTS.items():self.assertLess(math.dist(n.ports[p].position,xy),1e-6)
    def test_all_eight_original_platform_positions(self):
        s,c=model()
        for bank in ('A','B'):
            for i in range(1,5):
                p=c.platforms[f'{bank}{i}'];m=s.assembly.network.ports[p['marker_port']]
                y=(-42 if bank=='A' else 6)+12*(i-1);start=710. if i<=2 else 650.
                self.assertEqual(p['boarding_interval_x_m'],[start,970.]);self.assertAlmostEqual(m.position[1],y)
                self.assertAlmostEqual(m.position[0],start+5.)
    def test_buffer_markers_not_boarding_lengths(self):
        s,c=model()
        for p in c.platforms.values():
            edge=s.assembly.network.edges[p['storage_edge']]
            self.assertAlmostEqual(s.assembly.network.ports[edge.v].position[0],1000.)
            self.assertIn(p['usable_length_m'],(260.,320.))
    def test_original_plan_site_and_concourse(self):
        for f in FAMILIES:
            r=site_check(model(f)[0],[0.,-90.,1200.,90.],expected_ports=EXPECTED_PORTS,reservations=[{'id':'concourse','box_m':[1020.,-75.,1180.,75.]}])
            self.assertEqual(r['status'],'pass_within_scope');self.assertFalse(r['required_port_mismatches'])
    def test_smaller_site_fails_without_enlargement(self):
        self.assertEqual(site_check(model()[0],[0.,-90.,900.,90.])['status'],'fail')
    def test_changed_required_port_fails(self):
        self.assertEqual(site_check(model()[0],[0.,-90.,1200.,90.],expected_ports={'A:ARRIVAL':[0.,-17.]})['status'],'fail')
    def test_concourse_contact_not_ignored(self):
        r=site_check(model()[0],[0.,-90.,1200.,90.],reservations=[{'id':'bad','box_m':[800.,-50.,900.,50.]}])
        self.assertEqual(r['status'],'fail')
    def test_all_components_in_original_throat_region(self):
        for e in model()[0].assembly.network.edges.values():
            if e.component:self.assertGreaterEqual(e.curve.bounds()[0],150.-1e-6);self.assertLessEqual(e.curve.bounds()[2],650.+1e-6)
    def test_radius_target_retained(self):
        c=model()[1];self.assertLessEqual(max(x['curvature_upper_per_m'] for x in c.provenance['curves'].values()),1/300.)
    def test_stricter_radius_not_silently_relaxed(self):
        with self.assertRaisesRegex(ValueError,'radius_bound'):compile_assembly(build_compact(profile=GeometryProfile(minimum_radius_m=400.)).assembly)
    def test_normal_independence_all_64_pairs(self):
        for f in FAMILIES:
            r=independence(model(f)[1]);self.assertEqual(r['route_pair_count'],64);self.assertEqual(r['status'],'independent_in_compiled_resource_model')
    def test_inner_road_recovery_only(self):
        c=model()[1]
        self.assertIn('A:B1:in',c.routes);self.assertIn('A:B1:out',c.routes)
        self.assertIn('B:A4:in',c.routes);self.assertIn('B:A4:out',c.routes)
        for p in ('B2','B3','B4'):self.assertNotIn(f'A:{p}:in',c.routes)
        for p in ('A1','A2','A3'):self.assertNotIn(f'B:{p}:in',c.routes)
    def test_family_route_counts(self):
        for f,k in [('isolated',16),('a_to_b',18),('b_to_a',18),('scissors',20)]:self.assertEqual(len(model(f)[1].routes),k)
    def test_imported_component_not_stretched(self):
        s,c=model()
        for e in s.assembly.network.edges.values():
            if e.component and e.component.startswith(('REC_','A:ACCESS','B:ACCESS')):
                self.assertAlmostEqual(abs(e.curve.at(1)[0]-e.curve.at(0)[0]),40.)
    def test_matched_normal_lengths(self):
        baseline=model('isolated')[1]
        for f in FAMILIES[1:]:
            c=model(f)[1]
            for rid,r in baseline.routes.items():self.assertAlmostEqual(r.length_upper_m,c.routes[rid].length_upper_m,places=5)
    def test_no_unmodelled_zero_length_links(self):
        for e in model()[0].assembly.network.edges.values():self.assertGreater(math.dist(e.curve.at(0),e.curve.at(1)),1e-7)
    def test_complete_default_network_validates(self):model()[0].assembly.network.validate()
    def test_invalid_geometry_parameters(self):
        for kw in ({'fan_branch_slope':True},{'fan_turnout_span_m':float('nan')},{'first_fan_toe_x_m':-1.},{'fan_toe_step_m':70.}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):CompactSpec(**kw)
    def test_access_gap_required(self):
        with self.assertRaisesRegex(ValueError,'access_fan'):build_compact(spec=CompactSpec(first_fan_toe_x_m=201.))
    def test_recovery_marker_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError,'recovery_does_not_clear'):build_compact(spec=CompactSpec(first_fan_toe_x_m=250.))
    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):build_compact('magical_all_to_all')
    def test_grid_reports_actual_complete_search(self):
        r=fit_grid(fixture()['search_domain']);self.assertEqual(r['evaluated'],27);self.assertEqual(r['accepted_count'],6)
        self.assertTrue(r['grid_complete']);self.assertEqual(r['selected']['specialwork_end_x_m'],630.)
    def test_grid_reordered_values_replay(self):
        d=fixture()['search_domain'];r=fit_grid(d)
        rev={k:list(reversed(v)) for k,v in d.items()};s=fit_grid(rev)
        self.assertEqual(r['rows'],s['rows']);self.assertEqual(r['selected'],s['selected'])
    def test_zero_search_budget(self):
        r=fit_grid(fixture()['search_domain'],budget=0);self.assertEqual(r['status'],'search_exhausted');self.assertIsNone(r['selected'])
    def test_partial_search_is_not_final_selection(self):
        r=fit_grid(fixture()['search_domain'],budget=14);self.assertEqual(r['status'],'search_exhausted');self.assertIsNotNone(r['selected']);self.assertFalse(r['selection_final_within_grid'])
    def test_tighter_limit_no_grid_candidate_not_global_proof(self):
        r=fit_grid(fixture()['search_domain'],maximum_specialwork_end_x_m=600.);self.assertEqual(r['status'],'grid_complete_no_candidate');self.assertIn('finite grid',r['scope'])
    def test_unknown_or_invalid_grid_inputs(self):
        for d in ({},{'first_fan_toe_x_m':[205.]},{**fixture()['search_domain'],'site_end':[2000.]},{**fixture()['search_domain'],'fan_toe_step_m':[True]}):
            with self.subTest(d=d),self.assertRaises(ValueError):fit_grid(d)
    def test_invalid_budget_or_limit_rejected(self):
        for kw in ({'budget':True},{'budget':-1},{'budget':10001},{'maximum_specialwork_end_x_m':float('inf')}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):fit_grid(fixture()['search_domain'],**kw)
