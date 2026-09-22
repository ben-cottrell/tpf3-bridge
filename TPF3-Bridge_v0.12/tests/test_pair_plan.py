"""Offline pair-plan identity, topology and conservative lowering contract."""
import copy
import math
import unittest
from unittest.mock import patch

from bridge_pair import fit_pair, point_at
from bridge_pair_mock import compile_pair_plan, digest, verify_operation
from tools.pair_acceptance import fixture, snapshot


class PairPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = fixture(True, True)
        cls.candidate = fit_pair(cls.record)['candidate']
        cls.source = snapshot(cls.record)

    def compile(self):
        return compile_pair_plan(self.candidate, self.record, self.source)

    def test_determinism_binding_and_no_effects(self):
        before = copy.deepcopy((self.candidate, self.record, self.source))
        plan = self.compile()
        self.assertEqual(plan, self.compile())
        self.assertEqual(before, (self.candidate, self.record, self.source))
        self.assertEqual(plan['snapshot_hash'], digest(self.source))
        self.assertEqual(plan['input_hash'], digest(self.record))
        self.assertEqual(plan['plan_hash'], digest({k: v for k, v in plan.items() if k != 'plan_hash'}))
        self.assertIs(plan['real_game_execution_authorised'], False)
        self.assertEqual(plan['protected_neighbours'], self.source['neighbours'])

    def test_explicit_pairing_capabilities_and_dependencies(self):
        plan = self.compile()
        self.assertEqual(len(plan['operations']), 2)
        self.assertEqual({(o['payload']['start_node'], o['payload']['end_node']) for o in plan['operations']},
                         {('a0', 'a1'), ('b1', 'b0')})
        self.assertEqual(plan['required_capabilities'], sorted({'construct.track_polyline3',
                          'query.operation_receipt', 'query.realised_geometry'}))
        known = set()
        ports = {p['port_id']: p for p in self.record['ports']}
        for op in plan['operations']:
            verify_operation(op)
            self.assertTrue(set(op['dependencies']) <= known)
            self.assertNotIn(op['operation_id'], known)
            known.add(op['operation_id'])
            payload = op['payload']
            self.assertNotIn(payload['asset_key'], self.source['neighbours'])
            metadata = plan['direction_metadata'][payload['asset_key']]
            for side, index in [('start', 0), ('end', -1)]:
                port = ports[payload[side+'_node']]
                self.assertLess(math.dist(payload['points'][index], port['position_m']), 1e-6)
                self.assertLess(math.dist(metadata[side+'_tangent'], port['forward_unit']), 1e-7)

    def test_forgery_and_input_mismatch(self):
        for rehash in (False, True):
            bad = copy.deepcopy(self.candidate)
            bad['centreline']['curves'][0]['controls'][0][0] += 1
            if rehash:
                bad['candidate_hash'] = digest({k: v for k, v in bad.items() if k != 'candidate_hash'})
            with self.assertRaises(ValueError):
                compile_pair_plan(bad, self.record, self.source)
        bad = copy.deepcopy(self.record)
        bad['constraints']['lowering_tolerance_m'] *= 2
        with self.assertRaises(ValueError):
            compile_pair_plan(self.candidate, bad, self.source)

    def test_snapshot_ports_and_unsupported_state(self):
        for field, value in [('position_m', [1, 2, 0]), ('forward_unit', [-1, 0, 0]), ('port_id', 'wrong')]:
            bad = copy.deepcopy(self.source)
            bad['ports'][0][field] = value
            with self.assertRaises(ValueError):
                compile_pair_plan(self.candidate, self.record, bad)
        for field, value in [('environment', 'game'), ('revision', -1), ('revision', True), ('schema_version', 'unknown')]:
            bad = copy.deepcopy(self.source)
            bad[field] = value
            with self.assertRaises(ValueError):
                compile_pair_plan(self.candidate, self.record, bad)

    def test_revision_and_content_staleness_binding(self):
        original = self.compile()
        for field in ('revision', 'neighbours'):
            changed = copy.deepcopy(self.source)
            if field == 'revision':
                changed[field] += 1
            else:
                changed[field]['protected-1']['points'][0][0] -= 1
            new = compile_pair_plan(self.candidate, self.record, changed)
            self.assertNotEqual(new['snapshot_hash'], original['snapshot_hash'])
            self.assertNotEqual(new['plan_hash'], original['plan_hash'])

    def test_duplicate_physical_track_forgery(self):
        bad = copy.deepcopy(self.candidate)
        bad['tracks'][1] = copy.deepcopy(bad['tracks'][0])
        bad['candidate_hash'] = digest({k: v for k, v in bad.items() if k != 'candidate_hash'})
        with self.assertRaises(ValueError):
            compile_pair_plan(bad, self.record, self.source)

    def test_lowering_bound_independent_witnesses(self):
        plan = self.compile()
        for op, cert in zip(plan['operations'], plan['lowering_certificates']):
            self.assertLessEqual(cert['point_count'], cert['point_budget'])
            self.assertLessEqual(cert['error_bound_m'], self.record['constraints']['realised_tolerance_m'])
            self.assertIs(cert['exact_smooth_curvature'], False)
            track = plan['direction_metadata'][op['payload']['asset_key']]['track_id']
            for a, b, t0, t1 in zip(op['payload']['points'], op['payload']['points'][1:],
                                    cert['parameters'], cert['parameters'][1:]):
                p = point_at(self.candidate, track, (t0+t1)/2)
                v = [y-x for x, y in zip(a, b)]
                u = max(0, min(1, sum((p[i]-a[i])*v[i] for i in range(3))/sum(x*x for x in v)))
                self.assertLessEqual(math.dist(p, [a[i]+u*v[i] for i in range(3)]), cert['error_bound_m'])

    def test_finite_budget_and_allowance_failures(self):
        with patch('bridge_pair_mock.POINT_BUDGET', 2), self.assertRaises(ValueError):
            self.compile()
        for kind in ('readback', 'spacing', 'region'):
            record = fixture()
            if kind == 'readback':
                record['constraints']['realised_tolerance_m'] = 1e-10
            elif kind == 'spacing':
                record['constraints']['min_separation_m'] = 4
            else:
                record['region']['min_m'][0] = 0
            candidate = fit_pair(record)['candidate']
            self.assertIsNotNone(candidate)
            with self.assertRaises(ValueError):
                compile_pair_plan(candidate, record, snapshot(record))


if __name__ == '__main__':
    unittest.main()
