"""Shipped-example acceptance chain; detailed records stay in new local evidence."""
import json
from pathlib import Path
import unittest
import uuid

import bridge_app
from bridge_pair_mock import digest


ROOT = Path(bridge_app.__file__).resolve().parent


class PairAcceptanceTests(unittest.TestCase):
    def test_shipped_examples_design_bound_plan_and_current_readback(self):
        base = ROOT / '.local_checks' / ('pair_acceptance_' + uuid.uuid4().hex)
        base.mkdir(parents=True)
        source = ROOT / 'pair_example.json'
        snapshot = ROOT / 'pair_snapshot_example.json'
        record = json.loads(source.read_text(encoding='utf-8'))
        authored = json.loads(snapshot.read_text(encoding='utf-8'))
        design, executed = base / 'design', base / 'mock'

        def read(folder, name):
            return json.loads((folder / name).read_text(encoding='utf-8'))

        result = bridge_app.connect_pair(source, design)
        self.assertEqual(result['status'], 'pair_ready')
        self.assertIs(result['game_constructed'], False)
        candidate = read(design, 'candidate.json')
        search = read(design, 'search.json')
        self.assertEqual(search['search_status'], 'complete')
        self.assertEqual(search['evaluated'], len(search['grid']))
        self.assertEqual(search['candidate'], candidate)
        self.assertTrue(all(c['pass'] for c in candidate['pair_certificates'].values()))
        self.assertEqual(candidate['input'], record)
        self.assertEqual(candidate['provenance'], record['provenance'])
        self.assertFalse((design / 'plan.json').exists())

        result = bridge_app.connect_pair(source, executed, True, snapshot)
        self.assertEqual(result['status'], 'mock_verified')
        self.assertIs(result['game_constructed'], False)
        self.assertEqual(read(executed, 'candidate.json'), candidate)
        self.assertEqual((executed / 'fixture.json').read_bytes(), source.read_bytes())
        self.assertEqual((executed / 'snapshot.json').read_bytes(), snapshot.read_bytes())
        plan = read(executed, 'plan.json')
        self.assertEqual(plan['input_hash'], digest(record))
        self.assertEqual(plan['candidate_hash'], candidate['candidate_hash'])
        self.assertEqual(plan['snapshot_hash'], digest(authored))
        self.assertEqual(plan['expected_world_revision'], authored['revision'])
        self.assertEqual(plan['plan_hash'], digest({k: v for k, v in plan.items() if k != 'plan_hash'}))
        self.assertIs(plan['real_game_execution_authorised'], False)
        state = read(executed, 'execution.json')['current_state']
        self.assertEqual(state['writes'], 2)
        self.assertEqual(state['revision'], authored['revision'] + 2)
        self.assertEqual(len(state['receipts']), 2)
        self.assertEqual(len(state['effects']), 2)
        self.assertEqual(len(plan['operations']), 2)
        self.assertEqual(set(state['tracks']), set(plan['expected_physical_edge_ids']) | set(authored['neighbours']))
        connections = {c['track_id']: c for c in record['connections']}
        self.assertEqual({m['track_id'] for m in plan['direction_metadata'].values()}, set(connections))
        for op in plan['operations']:
            payload = op['payload']
            metadata = plan['direction_metadata'][payload['asset_key']]
            actual = state['tracks'][payload['asset_key']]
            self.assertEqual(actual, dict(payload, **metadata))
            connection = connections[metadata['track_id']]
            for side in ('start', 'end'):
                self.assertEqual(actual[side + '_node'], connection[side + '_port'])
        for port in authored['ports']:
            self.assertEqual(state['nodes'][port['port_id']], port['position_m'])
        for key, neighbour in authored['neighbours'].items():
            self.assertEqual(state['tracks'][key], neighbour)
            for side, index in (('start_node', 0), ('end_node', -1)):
                self.assertEqual(state['nodes'][neighbour[side]], neighbour['points'][index])
        self.assertEqual(bridge_app.verify(executed)['status'], 'integrity_verified')

        # Corrupt current read-back evidence, retaining the original manifest.
        (executed / 'execution.json').write_text('{}', encoding='utf-8')
        integrity = bridge_app.verify(executed)
        self.assertEqual(integrity['status'], 'integrity_failed')
        self.assertEqual(integrity['changed_files'], ['execution.json'])
        self.assertEqual(bridge_app.status(executed)['status'], 'status_unavailable')


if __name__ == '__main__':
    unittest.main()
