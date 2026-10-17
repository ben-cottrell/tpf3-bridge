"""Pair application evidence; each test retains only newly created local records."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

import bridge_app
import bridge_cli
import bridge_pair
import bridge_pair_mock
from tools.pair_acceptance import fixture, snapshot

ROOT = Path(bridge_app.__file__).parent


class PairAppTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / '.local_checks' / ('pair_app_' + uuid.uuid4().hex)
        self.base.mkdir(parents=True)
        self.record = fixture(opposing=True)
        self.source = self.base / 'input.json'
        self.source.write_text(json.dumps(self.record), encoding='utf-8')
        self.snap = self.base / 'authored.json'
        self.snap.write_text(json.dumps(snapshot(self.record)), encoding='utf-8')
        self.out = self.base / 'output'

    def read(self, name):
        return json.loads((self.out / name).read_text(encoding='utf-8'))

    def run_pair(self, mock=False):
        return bridge_app.connect_pair(self.source, self.out, mock, self.snap if mock else None)

    def cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, '-B', str(ROOT / 'bridge_cli.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=90)
        self.assertEqual(proc.stderr, b'')
        self.assertEqual(proc.returncode, 0 if ok else 1, proc.stdout)
        self.assertLessEqual(len(proc.stdout), 4096)
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        result = json.loads(proc.stdout)
        self.assertIs(result['game_constructed'], False)
        return result

    def test_design_evidence_and_cli_parity(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.run_pair()
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(result['status'], 'pair_ready')
        self.assertLessEqual(len(json.dumps(result).encode()), 4096)
        self.assertEqual(set(p.name for p in self.out.iterdir()),
                         {'fixture.json', 'context.json', 'search.json', 'candidate.json', 'summary.json', 'run.json'})
        self.assertEqual(self.read('search.json')['candidate'], self.read('candidate.json'))
        self.assertEqual(self.read('context.json')['provenance'], self.record['provenance'])
        self.assertEqual(self.read('run.json')['input_identity']['sha256'],
                         hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(bridge_app.status(self.out)['status'], 'pair_ready')
        other = self.base / 'cli'
        cli = self.cli('connect-pair', '--input', self.source, '--output', other)
        for key in ('status', 'candidate_hash', 'evaluated', 'accepted', 'scope'):
            self.assertEqual(cli[key], result[key])
        self.assertEqual((other / 'candidate.json').read_bytes(), (self.out / 'candidate.json').read_bytes())

    def test_explicit_mock_one_instance_and_readback(self):
        with patch.object(bridge_pair_mock, 'PairMock', wraps=bridge_pair_mock.PairMock) as constructor:
            result = self.run_pair(True)
        constructor.assert_called_once()
        self.assertEqual(result['status'], 'mock_verified')
        execution = self.read('execution.json')
        self.assertEqual(execution['current_state']['writes'], 2)
        self.assertEqual(len(execution['current_state']['effects']), 2)
        self.assertEqual(len(execution['current_state']['receipts']), 2)
        self.assertEqual(len(execution['current_state']['tracks']), 3)
        self.assertEqual((self.out / 'snapshot.json').read_bytes(), self.snap.read_bytes())
        plan = self.read('plan.json')
        self.assertEqual(plan['snapshot_hash'], bridge_pair_mock.digest(self.read('snapshot.json')))
        self.assertEqual(plan['candidate_hash'], self.read('candidate.json')['candidate_hash'])
        other = self.base / 'cli'
        self.assertEqual(self.cli('connect-pair', '--input', self.source, '--output', other,
                                 '--mock-execute', '--snapshot', self.snap)['status'], 'mock_verified')
        self.assertEqual((other / 'execution.json').read_bytes(), (self.out / 'execution.json').read_bytes())

    def test_explicit_snapshot_requirement(self):
        for i, (execute, snap) in enumerate(((True, None), (False, self.snap))):
            with patch.object(bridge_pair_mock, 'PairMock', side_effect=AssertionError('constructed')):
                result = bridge_app.connect_pair(self.source, self.base / str(i), execute, snap)
            self.assertEqual(result['status'], 'invalid_input')
        self.assertEqual(self.cli('connect-pair', '--input', self.source, '--output', self.out,
                                 '--mock-execute', ok=False)['status'], 'invalid_input')
        self.assertEqual(self.cli('connect-pair', ok=False)['status'], 'invalid_input')

    def test_fresh_design_forbids_adapter_imports(self):
        code = """import sys
class Guard:
    def find_spec(self, fullname, *args):
        if fullname in ('bridge_pair_mock', 'railcorridor.adapter', 'railcorridor.planning', 'railbranch.adapter'):
            raise AssertionError('forbidden import: ' + fullname)
sys.meta_path.insert(0, Guard())
import bridge_app
assert bridge_app.connect_pair(sys.argv[1], sys.argv[2])['status'] == 'pair_ready'
"""
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(self.source), str(self.out)],
                              cwd=ROOT, capture_output=True, timeout=90)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def test_fresh_inspection_no_imports_calls_or_writes(self):
        for mock in (False, True):
            self.out = self.base / str(mock)
            expected = self.run_pair(mock)['status']
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.out.iterdir()}
            code = """import sys
class Guard:
    def find_spec(self, fullname, *args):
        if fullname.startswith(('rail', 'bridge_pair', 'bridge_connection')):
            raise AssertionError('engine import: ' + fullname)
sys.meta_path.insert(0, Guard())
import bridge_app
def forbidden(*a, **k):
    raise AssertionError('design called')
bridge_app.design = bridge_app.connect = bridge_app.connect_pair = forbidden
assert bridge_app.status(sys.argv[1])['status'] == sys.argv[2]
assert bridge_app.verify(sys.argv[1])['status'] == 'integrity_verified'
"""
            proc = subprocess.run([sys.executable, '-B', '-c', code, str(self.out), expected],
                                  cwd=ROOT, capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            with patch.object(bridge_pair, 'fit_pair', side_effect=AssertionError('fit')), \
                 patch.object(bridge_pair_mock, 'execute_pair', side_effect=AssertionError('execute')), \
                 patch.object(bridge_pair_mock, 'compile_pair_plan', side_effect=AssertionError('compile')), \
                 patch.object(bridge_pair_mock, 'PairMock', side_effect=AssertionError('world')):
                self.assertEqual(bridge_app.status(self.out)['status'], expected)
                self.assertEqual(bridge_app.verify(self.out)['status'], 'integrity_verified')
            self.cli('status', '--run', self.out)
            self.cli('verify', '--run', self.out)
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.out.iterdir()})

    def test_invalid_and_failed_designs(self):
        for i, (key, value, expected) in enumerate((('cant_mm', 1, 'unsupported_input'),
                ('max_candidates', -1, 'invalid_input'), ('max_length_m', 1, 'no_accepted_candidate'),
                ('max_candidates', 1, 'incomplete_search'))):
            record = copy.deepcopy(self.record)
            record['constraints'][key] = value
            self.source.write_text(json.dumps(record), encoding='utf-8')
            self.out = self.base / str(i)
            self.assertEqual(self.run_pair()['status'], expected)
            self.assertEqual(bridge_app.status(self.out)['status'], expected)
            self.assertEqual(bridge_app.verify(self.out)['status'], 'integrity_verified')
            self.assertFalse((self.out / 'candidate.json').exists())
        for i, raw in enumerate((b'{', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff')):
            self.source.write_bytes(raw)
            self.out = self.base / ('bad' + str(i))
            self.assertEqual(self.run_pair()['status'], 'invalid_input')
        self.source = self.base / 'absent'
        self.out = self.base / 'missing'
        self.assertEqual(self.run_pair()['status'], 'invalid_input')

    def test_rejects_incomplete_passing_checks(self):
        result = bridge_pair.fit_pair(self.record)
        result['candidate_checks'][result['selected_index']]['checks']['separation']['pass'] = False
        with patch.object(bridge_pair, 'fit_pair', return_value=result):
            self.assertEqual(self.run_pair()['status'], 'failed_checks')
        self.assertFalse((self.out / 'candidate.json').exists())

    def test_bad_missing_and_stale_snapshot(self):
        stale = snapshot(self.record)
        stale['ports'][0]['position_m'][0] += 1
        for i, raw in enumerate((b'{', b'{"x":1,"x":2}', json.dumps(stale).encode(), b'\xff')):
            self.snap.write_bytes(raw)
            self.out = self.base / str(i)
            self.assertEqual(self.run_pair(True)['status'], 'mock_failed')
            self.assertEqual(bridge_app.status(self.out)['status'], 'mock_failed')
            self.assertEqual(bridge_app.verify(self.out)['status'], 'integrity_verified')
            self.assertFalse((self.out / 'execution.json').exists())
        self.snap = self.base / 'absent'
        self.out = self.base / 'missing'
        self.assertEqual(self.run_pair(True)['status'], 'mock_failed')

    def test_partial_effects_and_stale_live_world(self):
        constructor = bridge_pair_mock.PairMock
        for i, kind in enumerate(('partial', 'stale')):
            def make(snap):
                world = constructor(snap)
                if kind == 'partial':
                    world.fail_at = 1
                else:
                    world.revision += 1
                return world
            self.out = self.base / str(i)
            with patch.object(bridge_pair_mock, 'PairMock', side_effect=make):
                self.assertEqual(self.run_pair(True)['status'], 'mock_failed')
            execution = self.read('execution.json')
            self.assertEqual(execution['status'], 'partial_failure' if kind == 'partial' else 'preflight_blocked')
            self.assertEqual(execution['current_state']['writes'], 1 if kind == 'partial' else 0)
            self.assertFalse(execution['rollback_attempted'])
            self.assertEqual(bridge_app.status(self.out)['status'], 'mock_failed')

    def test_interrupt_exception_and_publication_failure(self):
        with patch.object(bridge_pair, 'fit_pair', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pair()
        self.assertEqual(bridge_app.status(self.out)['status'], 'run_incomplete')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')
        self.out = self.base / 'exception'
        with patch.object(bridge_pair, 'fit_pair', side_effect=RuntimeError('failed')):
            self.assertEqual(self.run_pair()['status'], 'unexpected_failure')
        self.assertEqual(bridge_app.status(self.out)['status'], 'unexpected_failure')
        self.out = self.base / 'publish'
        publish = bridge_app.atomic_json
        def fail(path, value):
            if path.name == 'run.json' and value['record_state'] == 'final':
                raise OSError('publication failure')
            return publish(path, value)
        with patch.object(bridge_app, 'atomic_json', side_effect=fail):
            self.assertEqual(self.run_pair()['status'], 'unexpected_failure')
        self.assertEqual(bridge_app.status(self.out)['status'], 'run_incomplete')

    def test_interrupted_execution_retains_current_effects(self):
        def interrupted(plan, world):
            op = plan['operations'][0]
            world.apply(op, plan['direction_metadata'][op['payload']['asset_key']], plan['plan_hash'])
            raise KeyboardInterrupt
        with patch.object(bridge_pair_mock, 'execute_pair', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.run_pair(True)
        self.assertEqual(self.read('execution.json')['current_state']['writes'], 1)
        self.assertEqual(self.read('execution.json')['status'], 'execution_unfinished')
        self.assertEqual(bridge_app.status(self.out)['status'], 'run_incomplete')

    def test_corrupt_missing_and_wrong_mode_records(self):
        self.run_pair(True)
        (self.out / 'candidate.json').write_text('{}', encoding='utf-8')
        self.assertEqual(bridge_app.verify(self.out)['changed_files'], ['candidate.json'])
        self.assertEqual(bridge_app.status(self.out)['status'], 'status_unavailable')
        (self.out / 'candidate.json').unlink()
        self.assertEqual(bridge_app.verify(self.out)['missing_files'], ['candidate.json'])
        manifest = self.read('run.json')
        for mode in ('design', 'mock', 'connection', 'pair', 'unknown'):
            manifest['mode'] = mode
            (self.out / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')
            self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')
        (self.out / 'run.json').write_text('{', encoding='utf-8')
        self.assertEqual(bridge_app.status(self.out)['status'], 'status_unavailable')
        (self.out / 'run.json').unlink()
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')

    def test_mock_success_requires_snapshot_and_execution_metadata(self):
        self.run_pair(True)
        original = self.read('run.json')
        for name in ('snapshot.json', 'plan.json', 'execution.json'):
            manifest = copy.deepcopy(original)
            del manifest['artifact_sha256'][name]
            del manifest['summary']['paths'][name]
            (self.out / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')
            self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')
        manifest = copy.deepcopy(original)
        manifest['summary']['mock_status'] = 'partial_failure'
        (self.out / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(bridge_app.status(self.out)['status'], 'status_unavailable')
        (self.out / 'run.json').write_text(json.dumps(original), encoding='utf-8')
        (self.out / 'snapshot.json').write_text('{}', encoding='utf-8')
        self.assertEqual(bridge_app.verify(self.out)['changed_files'], ['snapshot.json'])
        (self.out / 'snapshot.json').unlink()
        self.assertEqual(bridge_app.verify(self.out)['missing_files'], ['snapshot.json'])

    def test_output_protection(self):
        self.out.mkdir()
        marker = self.out / 'keep'
        marker.write_bytes(b'preserve')
        before = marker.stat().st_mtime_ns
        with patch.object(bridge_pair, 'fit_pair', side_effect=AssertionError('fit')):
            self.assertEqual(self.run_pair()['status'], 'output_refused')
            self.assertEqual(bridge_app.connect_pair(self.source, marker)['status'], 'output_refused')
        self.assertEqual(marker.read_bytes(), b'preserve')
        self.assertEqual(marker.stat().st_mtime_ns, before)
        self.out = self.base / 'empty'
        self.out.mkdir()
        self.assertEqual(self.run_pair()['status'], 'pair_ready')

    def test_compact_dispatch(self):
        result = dict(bridge_app.initial_summary(), status='pair_ready', scope=bridge_app.PAIR_SCOPE)
        result['paths'] = {name: '\u00e9' * 4000 for name in ('fixture.json', 'summary.json')}
        result = bridge_app.compact_connection_summary(result)
        output = io.StringIO()
        with patch.object(bridge_app, 'connect_pair', return_value=result) as call:
            with contextlib.redirect_stdout(output):
                self.assertEqual(bridge_cli.main(['connect-pair', '--input', 'a', '--output', 'b',
                                                 '--mock-execute', '--snapshot', 'c']), 0)
        call.assert_called_once_with(Path('a'), Path('b'), True, Path('c'))
        self.assertLessEqual(len(output.getvalue().encode()), 4096)


if __name__ == '__main__':
    unittest.main()
