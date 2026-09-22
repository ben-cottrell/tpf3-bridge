"""Current-world reconciliation for two physical mock tracks; no game evidence."""
import copy
import unittest

from bridge_pair import fit_pair
from bridge_pair_mock import PairMock, compile_pair_plan, execute_pair, digest
from tools.pair_acceptance import fixture, snapshot


class PairMockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = fixture(True, True)
        cls.candidate = fit_pair(cls.record)['candidate']
        cls.source = snapshot(cls.record)
        cls.plan = compile_pair_plan(cls.candidate, cls.record, cls.source)

    def setUp(self):
        self.world = PairMock(self.source)
        self.key = self.plan['operations'][0]['payload']['asset_key']

    def execute(self):
        return execute_pair(self.plan, self.world)

    def verified(self):
        result = self.execute()
        self.assertEqual(result['status'], 'mock_verified', result)
        self.assertFalse(result['rollback_attempted'])
        self.assertFalse(result['game_constructed'])
        self.assertEqual(self.world.writes, 2)
        return result

    def test_clean_and_same_instance_repeat(self):
        before = copy.deepcopy((self.plan, self.source))
        self.verified()
        self.verified()
        self.assertEqual(self.world.revision, self.source['revision']+2)
        self.assertEqual(self.world.tracks['protected-1'], self.source['neighbours']['protected-1'])
        for port in self.source['ports']:
            self.assertEqual(self.world.nodes[port['port_id']], port['position_m'])
        self.assertEqual(before, (self.plan, self.source))
        fresh = PairMock(self.source)
        self.assertEqual(fresh.writes, 0)
        self.assertNotIn(self.key, fresh.tracks)

    def test_ack_lost_after_effect(self):
        for index in (0, 1):
            self.world = PairMock(self.source)
            self.world.drop_ack_at = index
            self.assertEqual(self.verified()['acknowledgements_reconciled'], 1)
            self.verified()

    def test_lost_ack_without_receipt_retains_effect(self):
        self.world.drop_ack_at = 0
        self.world.receipt = lambda oid: None
        result = self.execute()
        self.assertEqual(result['status'], 'uncertain_effect_stop')
        self.assertFalse(result['rollback_attempted'])
        self.assertEqual(self.world.writes, 1)
        self.assertIn(self.key, self.world.tracks)

    def test_partial_failure_and_explicit_retry(self):
        self.world.fail_at = 1
        result = self.execute()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertFalse(result['rollback_attempted'])
        self.assertEqual(self.world.writes, 1)
        first = copy.deepcopy(self.world.tracks[self.key])
        self.world.fail_at = None
        self.verified()
        self.assertEqual(self.world.tracks[self.key], first)

    def test_partial_retry_checks_existing_effect_before_writes(self):
        self.world.fail_at = 1
        self.execute()
        self.world.fail_at = None
        self.world.tracks[self.key]['points'][1][0] += 1
        self.assertNotEqual(self.execute()['status'], 'mock_verified')
        self.assertEqual(self.world.writes, 1)

    def test_snap_retained_and_not_hidden_by_receipt(self):
        self.world.snap_at = 0
        self.assertEqual(self.execute()['status'], 'realised_geometry_or_semantics_mismatch')
        self.assertEqual(self.world.writes, 1)
        self.world.snap_at = None
        self.assertNotEqual(self.execute()['status'], 'mock_verified')
        self.assertEqual(self.world.writes, 1)

    def test_displaced_missing_and_malformed_geometry(self):
        for change in ('displaced', 'missing', 'nan', 'malformed'):
            with self.subTest(change=change):
                self.world = PairMock(self.source)
                self.verified()
                receipts = copy.deepcopy(self.world.ledger)
                if change == 'missing':
                    del self.world.tracks[self.key]
                elif change == 'malformed':
                    self.world.tracks[self.key]['points'] = None
                else:
                    self.world.tracks[self.key]['points'][1][0] += 1 if change == 'displaced' else float('nan')
                self.assertNotEqual(self.execute()['status'], 'mock_verified')
                self.assertEqual(self.world.writes, 2)
                self.assertEqual(self.world.ledger, receipts)

    def test_bad_connection_direction_and_stable_nodes(self):
        for field, value in [('end_node', 'wrong-node'), ('direction', 'reverse'),
                             ('reversed_from_centreline', True), ('start_tangent', [0, 0, 1]),
                             ('node', [1, 2, 3])]:
            with self.subTest(field=field):
                self.world = PairMock(self.source)
                self.verified()
                if field == 'node':
                    self.world.nodes['a0'] = value
                else:
                    self.world.tracks[self.key][field] = value
                self.assertNotEqual(self.execute()['status'], 'mock_verified')
                self.assertEqual(self.world.writes, 2)

    def test_changed_neighbour_before_and_after_execution(self):
        for executed in (False, True):
            for field in ('points', 'direction', 'end_node'):
                self.world = PairMock(self.source)
                if executed:
                    self.verified()
                if field == 'points':
                    self.world.tracks['protected-1'][field][0][0] += 1
                else:
                    self.world.tracks['protected-1'][field] = 'changed'
                self.assertNotEqual(self.execute()['status'], 'mock_verified')
                self.assertEqual(self.world.writes, 2 if executed else 0)

    def test_stale_snapshot_revision_and_unrelated_effects(self):
        for fault in ('revision', 'snapshot', 'neighbour_snapshot', 'unrelated', 'receipt'):
            self.world = PairMock(self.source)
            if fault == 'revision':
                self.world.revision += 1
            elif fault == 'snapshot':
                self.world.snapshot['snapshot_id'] = 'changed'
            elif fault == 'neighbour_snapshot':
                self.world.snapshot['neighbours']['protected-1']['direction'] = 'reverse'
            elif fault == 'receipt':
                self.world.ledger['unrelated'] = {}
            else:
                self.world.tracks['unrelated'] = copy.deepcopy(self.world.tracks['protected-1'])
            self.assertEqual(self.execute()['status'], 'preflight_blocked')
            self.assertEqual(self.world.writes, 0)
        self.world = PairMock(self.source)
        self.world.fail_at = 1
        self.execute()
        self.world.revision += 1
        self.world.fail_at = None
        self.assertEqual(self.execute()['status'], 'preflight_blocked')
        self.assertEqual(self.world.writes, 1)

    def test_capability_denial_compile_and_execute(self):
        for capability in self.plan['required_capabilities']:
            self.world = PairMock(self.source)
            self.world.capabilities['capabilities'][capability]['state'] = 'unknown'
            self.assertEqual(self.execute()['status'], 'preflight_blocked')
            with self.assertRaises(ValueError):
                compile_pair_plan(self.candidate, self.record, self.source, adapter=self.world)
            self.assertEqual(self.world.writes, 0)
        self.world = PairMock(self.source)
        self.world.revision += 1
        with self.assertRaises(ValueError):
            compile_pair_plan(self.candidate, self.record, self.source, adapter=self.world)

    def test_different_plan_cannot_claim_known_partial_effect(self):
        self.world.fail_at = 1
        self.execute()
        other = copy.deepcopy(self.plan)
        other['scope'] += '; distinct plan identity with identical operations'
        other['plan_hash'] = digest({k: v for k, v in other.items() if k != 'plan_hash'})
        self.world.fail_at = None
        self.assertEqual(execute_pair(other, self.world)['status'], 'preflight_blocked')
        self.assertEqual(self.world.writes, 1)


if __name__ == '__main__':
    unittest.main()
