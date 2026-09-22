"""Connection integration tests; retain new evidence under .local_checks only."""
import contextlib
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
import bridge_connection

ROOT = Path(bridge_app.__file__).parent


class ConnectionAppTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / '.local_checks' / ('connection_app_' + uuid.uuid4().hex)
        self.base.mkdir(parents=True)
        self.source = self.base / 'input.json'
        self.source.write_bytes((ROOT / 'connection_example.json').read_bytes())
        self.out = self.base / 'output'

    def change(self, edit):
        data = json.loads(self.source.read_text(encoding='utf-8'))
        edit(data)
        self.source.write_text(json.dumps(data), encoding='utf-8')

    def read(self, name):
        return json.loads((self.out / name).read_text(encoding='utf-8'))

    def cli(self, *args, success=True):
        proc = subprocess.run([sys.executable, '-B', str(ROOT / 'bridge_cli.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(proc.stderr, b'')
        self.assertEqual(proc.returncode, 0 if success else 1)
        self.assertLessEqual(len(proc.stdout), 4096)
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        result = json.loads(proc.stdout)
        self.assertIs(result['game_constructed'], False)
        return result

    def test_api_full_evidence_and_provenance(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = bridge_app.connect(self.source, self.out)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(result['status'], 'connection_ready')
        self.assertIn('Offline', result['scope'])
        self.assertLessEqual(len(json.dumps(result).encode()), 4096)
        self.assertEqual(set(p.name for p in self.out.iterdir()),
                         {'fixture.json', 'context.json', 'search.json', 'candidate.json', 'summary.json', 'run.json'})
        manifest = self.read('run.json')
        self.assertEqual(manifest['input_identity']['sha256'], hashlib.sha256(self.source.read_bytes()).hexdigest())
        context = self.read('context.json')
        self.assertEqual(context['provenance'], json.loads(self.source.read_text())['provenance'])
        hashes = {p.replace('\\', '/'): h for p, h in context['source_sha256'].items()}
        for path in ('bridge_app.py', 'bridge_connection.py', 'proof/railgeom/curves.py',
                     'proof/railbranch/geometry.py', 'proof/railproof/model.py', 'proof/railcorridor/geometry.py'):
            self.assertEqual(hashes[path], hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        search = self.read('search.json')
        self.assertEqual(search['candidate'], self.read('candidate.json'))
        self.assertTrue(search['candidate_checks'][search['selected_index']]['pass'])
        self.assertEqual(bridge_app.status(self.out)['status'], 'connection_ready')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'integrity_verified')

    def test_cli_and_fresh_read_only_without_engine_imports(self):
        self.assertEqual(self.cli('connect', '--input', self.source, '--output', self.out)['status'], 'connection_ready')
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.out.iterdir()}
        code = '''import sys, json
class Guard:
    def find_spec(self, fullname, *args):
        if fullname.startswith(('rail', 'bridge_connection')):
            raise AssertionError('engine import: ' + fullname)
sys.meta_path.insert(0, Guard())
import bridge_app
assert bridge_app.status(sys.argv[1])['status'] == 'connection_ready'
assert bridge_app.verify(sys.argv[1])['status'] == 'integrity_verified'
'''
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(self.out)], cwd=ROOT,
                              capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(self.cli('status', '--run', self.out)['status'], 'connection_ready')
        self.assertEqual(self.cli('verify', '--run', self.out)['status'], 'integrity_verified')
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.out.iterdir()})

    def test_connect_forbids_corridor_search_and_adapters(self):
        code = '''import sys
class Guard:
    def find_spec(self, fullname, *args):
        if fullname in ('railcorridor.planning', 'railcorridor.adapter', 'railbranch.planning') or fullname.startswith('railops'):
            raise AssertionError('forbidden import: ' + fullname)
sys.meta_path.insert(0, Guard())
import bridge_app
def forbidden(*a, **k):
    raise AssertionError('corridor design called')
bridge_app.design = forbidden
assert bridge_app.connect(sys.argv[1], sys.argv[2])['status'] == 'connection_ready'
'''
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(self.source), str(self.out)],
                              cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def test_distinct_non_success_outcomes(self):
        cases = [
            ('unsupported_input', lambda d: d['constraints'].update(cant_mm=1), 'not_started'),
            ('unsupported_input', lambda d: d['end'].update(position_m=[-500, 0, 0]), 'not_started'),
            ('invalid_input', lambda d: d['constraints'].update(max_candidates=-1), 'not_started'),
            ('failed_checks', lambda d: d['region'].update(max_m=[100, 100, 1]), 'not_started'),
            ('no_accepted_candidate', lambda d: d['constraints'].update(max_length_m=1), 'complete'),
            ('incomplete_search', lambda d: d['constraints'].update(max_candidates=1), 'budget_exhausted'),
        ]
        for i, (expected, edit, search_status) in enumerate(cases):
            with self.subTest(expected=expected, i=i):
                self.source.write_bytes((ROOT / 'connection_example.json').read_bytes())
                self.change(edit)
                out = self.base / str(i)
                result = bridge_app.connect(self.source, out)
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['search_status'], search_status)
                self.assertIsNone(result['candidate_hash'])
                self.assertFalse((out / 'candidate.json').exists())
                self.assertEqual(bridge_app.status(out)['status'], expected)
                self.assertEqual(bridge_app.verify(out)['status'], 'integrity_verified')
                if expected == 'incomplete_search':
                    self.assertGreater(result['accepted'], 0)

    def test_malformed_and_missing_input(self):
        for i, data in enumerate((b'{', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff')):
            self.source.write_bytes(data)
            out = self.base / str(i)
            self.assertEqual(bridge_app.connect(self.source, out)['status'], 'invalid_input')
            self.assertEqual(bridge_app.status(out)['status'], 'invalid_input')
        self.assertEqual(bridge_app.connect(self.base / 'missing.json', self.out)['status'], 'invalid_input')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'integrity_verified')

    def test_interrupt_and_unexpected_failure(self):
        with patch.object(bridge_connection, 'fit_connection', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                bridge_app.connect(self.source, self.out)
        self.assertEqual(bridge_app.status(self.out)['status'], 'run_incomplete')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')
        out = self.base / 'failed'
        with patch.object(bridge_connection, 'fit_connection', side_effect=RuntimeError('fit failed')):
            self.assertEqual(bridge_app.connect(self.source, out)['status'], 'unexpected_failure')
        self.assertEqual(bridge_app.status(out)['status'], 'unexpected_failure')
        self.assertEqual(bridge_app.verify(out)['status'], 'integrity_verified')

    def test_rejects_claimed_success_without_complete_checks(self):
        result = bridge_connection.fit_connection(json.loads(self.source.read_text()))
        result['candidate_checks'][result['selected_index']]['checks']['length']['pass'] = False
        with patch.object(bridge_connection, 'fit_connection', return_value=result):
            self.assertEqual(bridge_app.connect(self.source, self.out)['status'], 'failed_checks')
        self.assertFalse((self.out / 'candidate.json').exists())
        self.assertEqual(bridge_app.status(self.out)['status'], 'failed_checks')

    def test_final_publication_failure_stays_unfinished(self):
        publish = bridge_app.atomic_json

        def fail_final(path, value):
            if path.name == 'run.json' and value['record_state'] == 'final':
                raise OSError('simulated publication failure')
            return publish(path, value)

        with patch.object(bridge_app, 'atomic_json', side_effect=fail_final):
            self.assertEqual(bridge_app.connect(self.source, self.out)['status'], 'unexpected_failure')
        self.assertEqual(self.read('run.json')['record_state'], 'unfinished')
        self.assertEqual(bridge_app.status(self.out)['status'], 'run_incomplete')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')

    def test_cli_budget_failure_and_invalid_arguments(self):
        self.change(lambda d: d['constraints'].update(max_candidates=1))
        result = self.cli('connect', '--input', self.source, '--output', self.out, success=False)
        self.assertEqual(result['status'], 'incomplete_search')
        self.assertEqual(self.cli('status', '--run', self.out, success=False)['status'], 'incomplete_search')
        self.assertEqual(self.cli('verify', '--run', self.out)['status'], 'integrity_verified')
        self.assertEqual(self.cli('connect', success=False)['status'], 'invalid_input')
        self.assertEqual(self.cli('connect', '--input', self.source, '--output', self.base / 'unused',
                                  '--mock-execute', success=False)['status'], 'invalid_input')

    def test_tamper_missing_and_corrupt_records(self):
        bridge_app.connect(self.source, self.out)
        (self.out / 'candidate.json').write_text('{}', encoding='utf-8')
        self.assertEqual(bridge_app.verify(self.out)['changed_files'], ['candidate.json'])
        self.assertEqual(bridge_app.status(self.out)['status'], 'status_unavailable')
        (self.out / 'candidate.json').unlink()
        self.assertEqual(bridge_app.verify(self.out)['missing_files'], ['candidate.json'])
        manifest = self.read('run.json')
        manifest['mode'] = 'design'
        (self.out / 'run.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')
        (self.out / 'run.json').write_text('{', encoding='utf-8')
        self.assertEqual(bridge_app.status(self.out)['status'], 'status_unavailable')
        (self.out / 'run.json').unlink()
        self.assertEqual(bridge_app.verify(self.out)['status'], 'verification_unavailable')

    def test_output_refusal_before_fit_and_empty_directory(self):
        self.out.mkdir()
        marker = self.out / 'keep'
        marker.write_bytes(b'preserve')
        before = marker.stat().st_mtime_ns
        with patch.object(bridge_connection, 'fit_connection', side_effect=AssertionError('called')):
            self.assertEqual(bridge_app.connect(self.source, self.out)['status'], 'output_refused')
            self.assertEqual(bridge_app.connect(self.source, marker)['status'], 'output_refused')
        self.assertEqual(marker.read_bytes(), b'preserve')
        self.assertEqual(marker.stat().st_mtime_ns, before)
        self.cli('connect', '--input', self.source, '--output', self.out, success=False)
        empty = self.base / 'empty'
        empty.mkdir()
        self.assertEqual(bridge_app.connect(self.source, empty)['status'], 'connection_ready')

    def test_cli_dispatch_and_compact_api_paths(self):
        result = {**bridge_app.initial_summary(), 'status': 'connection_ready', 'scope': bridge_app.CONNECTION_SCOPE}
        result.pop('mock_scope')
        result['paths'] = {name: '\u00e9' * 4000 for name in ('fixture.json', 'summary.json')}
        compact = bridge_app.compact_connection_summary(result)
        self.assertLessEqual(len(json.dumps(compact).encode()), 4096)
        stdout = io.StringIO()
        with patch.object(bridge_app, 'connect', return_value=compact) as call:
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(bridge_cli.main(['connect', '--input', 'a', '--output', 'b']), 0)
        call.assert_called_once_with(Path('a'), Path('b'))
        self.assertLessEqual(len(stdout.getvalue().encode()), 4096)
        self.assertEqual(json.loads(stdout.getvalue())['paths'], {name: name for name in result['paths']})


if __name__ == '__main__':
    unittest.main()
