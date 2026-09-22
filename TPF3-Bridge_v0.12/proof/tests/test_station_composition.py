import copy
import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from railstation.composition import *
from railstation.checks import independence
from railgeom.curves import line
from station_support import station

class StationCompositionTests(unittest.TestCase):
    def test_eight_roads_and_four_external_roles(self):
        s,c=station();self.assertEqual(len(c.platforms),8)
        self.assertEqual(sum(p.role.endswith('_only_boundary') for p in s.assembly.network.ports.values()),4)
    def test_all_ids_are_namespaced_and_unique(self):
        s,c=station('a_to_b');n=s.assembly.network
        self.assertEqual(len(n.turnouts),10);self.assertEqual(len(n.edges),len(set(n.edges)))
        self.assertNotEqual(n.turnouts['A:ACCESS'].controller,n.turnouts['B:ACCESS'].controller)
    def test_platform_ordinates_match_original_set(self):
        s,c=station()
        ys=sorted(s.assembly.network.ports[p['marker_port']].position[1] for p in c.platforms.values())
        self.assertEqual(ys,[-42.,-30.,-18.,-6.,6.,18.,30.,42.])
    def test_four_short_and_four_long_intervals(self):
        s,c=station();self.assertEqual(sorted(p['usable_length_m'] for p in c.platforms.values()),[260.]*4+[320.]*4)
        for p in c.platforms.values():self.assertEqual(p['boarding_interval_x_m'][1]-p['boarding_interval_x_m'][0],p['usable_length_m'])
    def test_short_markers_and_storage_are_physically_moved(self):
        s,c=station();n=s.assembly.network
        for p in c.platforms.values():
            marker=n.ports[p['marker_port']].position[0]
            self.assertEqual(marker,p['boarding_interval_x_m'][0]+p['margin_each_end_m'])
            self.assertEqual(n.edges[p['storage_edge']].curve.at(0)[0],marker)
    def test_isolated_has_no_recovery_routes(self):
        s,c=station();self.assertEqual(len(c.routes),16)
        self.assertNotIn('A:B1:in',c.routes);self.assertNotIn('B:A1:out',c.routes)
    def test_a_link_supplies_both_legs_for_a_recovery(self):
        s,c=station('a_to_b');self.assertEqual(len(c.routes),24)
        for i in range(1,5):
            self.assertIn(f'A:B{i}:in',c.routes);self.assertIn(f'A:B{i}:out',c.routes)
            self.assertNotIn(f'B:A{i}:in',c.routes)
    def test_b_link_supplies_opposite_recovery_only(self):
        s,c=station('b_to_a')
        self.assertIn('B:A1:in',c.routes);self.assertIn('B:A1:out',c.routes)
        self.assertNotIn('A:B1:in',c.routes)
    def test_normal_route_resource_independence(self):
        for f in FAMILIES:
            with self.subTest(f=f):
                r=independence(station(f)[1]);self.assertEqual(r['route_pair_count'],64)
                self.assertTrue(all(not x['conflicts'] for x in r['pairs']))
    def test_recovery_has_actual_shared_resources(self):
        c=station('a_to_b')[1]
        a={r.resource for r in c.routes['A:B1:in'].requirements};b={r.resource for r in c.routes['B:B1:in'].requirements}
        self.assertTrue(a&b);self.assertIn('track:recovery_diagonal',a)
    def test_imported_component_data_and_hashes_propagate(self):
        s,c=station('a_to_b');items=s.component_report['imported_instances']
        self.assertEqual(len(items),2);self.assertEqual(items[0]['geometry_hash'],items[1]['geometry_hash'])
        self.assertEqual(s.assembly.network.metadata['link_span_m'],680.)
        self.assertFalse(s.component_report['authentic_UK_components'])
    def test_no_branch_to_branch_shortcut(self):
        n=station('a_to_b')[0].assembly.network
        # This network has no alternate loop permitting a traversal between the
        # normal and reverse exits of the same imported component.
        self.assertEqual(n.enumerate_paths('LINK_W:N','LINK_W:R'),[])
    def test_matched_common_section_breaks(self):
        rows=[station(f)[0].assembly.network.metadata['synthetic_section_policy'] for f in FAMILIES]
        self.assertTrue(all(r==rows[0] for r in rows));self.assertEqual(rows[0]['common_x_breaks_m'],[280.,320.,920.,960.])
    def test_normal_lengths_same_across_families(self):
        base=station()[1]
        for f in FAMILIES[1:]:
            c=station(f)[1]
            for rid,r in base.routes.items():self.assertAlmostEqual(r.length_upper_m,c.routes[rid].length_upper_m,places=6)
    def test_combined_pair_compile_covers_cross_bank_pairs(self):
        s,c=station();n=len(s.assembly.network.edges)
        self.assertEqual(c.provenance['pair_evaluations'],n*(n-1)//2)
    def test_invalid_family_rejected(self):
        with self.assertRaises(ValueError):build_station('fully_connected_by_name')
    def test_overlapping_banks_rejected(self):
        with self.assertRaises(ValueError):StationSpec(bank_separation_m=36.)
    def test_invalid_numbers_and_lengths_rejected(self):
        for kw in ({'lead_length_m':True},{'bank_a_y_m':float('nan')},{'boarding_length_m':200.},{'platform_spacing_m':0.}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):StationSpec(**kw)
    def test_link_outside_corridor_rejected(self):
        with self.assertRaises(ValueError):build_station('a_to_b',StationSpec(link_west_x_m=400.))
    def test_unreviewed_external_record_cannot_be_placed(self):
        with self.assertRaises(ValueError):build_station('a_to_b',component_path=EVIDENCE/'component_import_pending.json')
    def test_replay_has_identical_compile_hash(self):
        self.assertEqual(compile_station(build_station('a_to_b')).compile_hash,station('a_to_b')[1].compile_hash)
    def test_duplicate_namespace_cannot_merge(self):
        a=Network('test');src=station()[0].assembly.network
        merge_network(a,src,'D')
        with self.assertRaises(ValueError):merge_network(a,src,'D')
