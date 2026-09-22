"""Focused application contract tests; all generated evidence is temporary."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bridge_app
import bridge_cli
from railcorridor.planning import objective

ROOT = Path(bridge_cli.__file__).parent
FIXTURE = ROOT / 'proof/corridor_fixtures/release.json'


class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Hash immutable legacy inputs/results without loading them into model context.
        cls.legacy = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                      for folder in ('proof', 'evidence', 'validation', 'handoff_evidence')
                      for p in (ROOT / folder).rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts}

    @classmethod
    def tearDownClass(cls):
        changed = [str(p) for p, digest in cls.legacy.items()
                   if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest]
        if changed:
            raise AssertionError('Legacy files changed: ' + repr(changed))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.out = self.base / 'output'

    def fixture(self, change):
        data = json.loads(FIXTURE.read_text(encoding='utf-8'))
        change(data)
        path = self.base / 'fixture.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def run_cli(self, fixture=FIXTURE, mock=False, in_process=False):
        args = ['design', '--fixture', str(fixture), '--output', str(self.out)]
        if mock:
            args.append('--mock-execute')
        if in_process:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = bridge_cli.main(args)
            text = stdout.getvalue()
        else:
            proc = subprocess.run([sys.executable, str(ROOT / 'bridge_cli.py'), *args],
                                  cwd=self.base, capture_output=True, text=True, encoding='utf-8', timeout=30)
            code, text = proc.returncode, proc.stdout
            self.assertEqual(proc.stderr, '')
        self.assertLessEqual(len(text.encode('utf-8')), 4096)
        self.assertEqual(len(text.splitlines()), 1)
        summary = json.loads(text)
        self.assertIs(summary['game_constructed'], False)
        self.assertNotIn('candidates', summary)
        for path in summary['paths'].values():
            self.assertTrue(Path(path).is_file())
        return code, summary

    def read(self, name):
        return json.loads((self.out / name).read_text(encoding='utf-8'))

    def call_api(self, function, *args, **kwargs):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = function(*args, **kwargs)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')
        self.assertIsInstance(result, dict)
        self.assertIs(result['game_constructed'], False)
        return result

    def test_api_design_mock_and_read_only_cli_compatibility(self):
        class CompatiblePath:
            def __init__(self, path):
                self.path = path

            def __fspath__(self):
                return str(self.path)

        for mock, convert in ((False, Path), (True, str), (False, CompatiblePath)):
            self.out = self.base / f'api-{mock}-{convert.__name__}'
            result = self.call_api(bridge_app.design, convert(FIXTURE), convert(self.out), mock)
            self.assertEqual(result['status'], 'mock_verified' if mock else 'design_ready')
            self.assertEqual(result['evaluated'], 12)
            self.assertEqual(result['candidate_hash'], self.read('candidate.json')['candidate_hash'])
            provenance = self.read('context.json')['source_sha256']
            for name in ('bridge_app.py', 'bridge_cli.py'):
                self.assertEqual(provenance[name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in self.out.iterdir() if p.is_file()}
            for command in ('status', 'verify'):
                api = self.call_api(getattr(bridge_app, command), convert(self.out))
                code, cli = self.inspect(command=command)
                self.assertEqual(code, 0)
                self.assertEqual(api, cli)
            self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns)
                                      for p in self.out.iterdir() if p.is_file()})
            refused = self.call_api(bridge_app.design, convert(FIXTURE), convert(self.out))
            self.assertEqual(refused['status'], 'output_refused')
            self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns)
                                      for p in self.out.iterdir() if p.is_file()})

    def test_api_failed_design_and_integrity_results(self):
        fixture = self.fixture(lambda f: f['search'].update(candidate_budget=0))
        result = self.call_api(bridge_app.design, fixture, self.out, mock_execute=True)
        self.assertEqual(result['status'], 'incomplete_search')
        self.assertIsNone(result['candidate_hash'])
        self.assertFalse((self.out / 'plan.json').exists())
        self.assertEqual(self.call_api(bridge_app.verify, self.out)['status'], 'integrity_verified')
        (self.out / 'summary.json').write_bytes(b'changed')
        (self.out / 'search.json').unlink()
        for command in ('status', 'verify'):
            result = self.call_api(getattr(bridge_app, command), self.out)
            code, cli = self.inspect(command=command)
            self.assertEqual(code, 1)
            self.assertEqual(result, cli)
        self.assertEqual(result['changed_files'], ['summary.json'])
        self.assertEqual(result['missing_files'], ['search.json'])

    def test_api_unavailable_and_invalid_input(self):
        for command, expected in (('status', 'status_unavailable'), ('verify', 'verification_unavailable')):
            result = self.call_api(getattr(bridge_app, command), str(self.out))
            self.assertEqual(result['status'], expected)
            self.assertFalse(self.out.exists())
        fixture = self.fixture(lambda f: f['profile'].update(max_grade=-1))
        result = self.call_api(bridge_app.design, str(fixture), self.out)
        self.assertEqual(result['status'], 'invalid_input')
        self.assertEqual(self.call_api(bridge_app.status, self.out)['status'], 'invalid_input')
        self.assertEqual(self.call_api(bridge_app.verify, self.out)['status'], 'integrity_verified')

    def test_design_success_selection_and_full_evidence(self):
        code, summary = self.run_cli()
        self.assertEqual((code, summary['status']), (0, 'design_ready'))
        search = self.read('search.json')
        self.assertEqual(summary['evaluated'], 12)
        self.assertEqual(len(search['candidates']), 12)
        self.assertTrue(any(not c['accepted_for_reference_comparison'] for c in search['candidates']))
        chosen = min((c for c in search['candidates'] if c['accepted_for_reference_comparison']),
                     key=lambda c: (objective(c)[2], objective(c)[3], c['candidate_hash']))
        self.assertEqual(chosen, self.read('candidate.json'))
        self.assertEqual(summary['candidate_hash'], chosen['candidate_hash'])
        self.assertEqual(self.read('fixture.json')['schema_version'], '0.9.0')
        self.assertTrue(self.read('context.json')['source_sha256'])
        self.assertFalse((self.out / 'plan.json').exists())

    def test_explicit_mock_is_fresh_each_invocation(self):
        for name in ('first', 'second'):
            self.out = self.base / name
            code, summary = self.run_cli(mock=True)
            self.assertEqual((code, summary['status']), (0, 'mock_verified'))
            result = self.read('execution.json')
            self.assertFalse(result['real_game_constructed'])
            self.assertEqual(result['writes'], len(self.read('plan.json')['operations']))
            self.assertEqual(len(result['trace']), result['writes'])
            self.assertIn('no persistence', summary['mock_scope'])

    def test_malformed_and_duplicate_json(self):
        for index, text in enumerate(('{', '{"a":1,"a":2}')):
            self.out = self.base / str(index)
            path = self.base / 'bad.json'
            path.write_text(text, encoding='utf-8')
            code, summary = self.run_cli(path)
            self.assertNotEqual(code, 0)
            self.assertEqual(summary['status'], 'invalid_input')

    def test_invalid_profile(self):
        path = self.fixture(lambda f: f['profile'].update(max_grade=-1))
        code, summary = self.run_cli(path)
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'invalid_input')

    def test_zero_budget_and_partial_success_remain_incomplete(self):
        for budget in (0, 1):
            self.out = self.base / str(budget)
            path = self.fixture(lambda f: f['search'].update(candidate_budget=budget))
            code, summary = self.run_cli(path, mock=True)
            self.assertNotEqual(code, 0)
            self.assertEqual(summary['status'], 'incomplete_search')
            self.assertEqual(summary['evaluated'], budget)
            self.assertEqual(summary['accepted'], budget)
            self.assertIsNone(summary['candidate_hash'])
            self.assertFalse((self.out / 'plan.json').exists())
            self.assertFalse((self.out / 'candidate.json').exists())

    def test_no_acceptable_candidate(self):
        path = self.fixture(lambda f: f['search'].update(lateral_offsets_m=[-280]))
        code, summary = self.run_cli(path, mock=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'no_accepted_candidate')
        self.assertEqual(summary['search_status'], 'grid_complete_no_candidate')
        self.assertFalse((self.out / 'plan.json').exists())

    def test_protected_output_directory_and_file(self):
        self.out.mkdir()
        sentinel = self.out / 'summary.json'
        sentinel.write_bytes(b'previous evidence')
        code, summary = self.run_cli()
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'output_refused')
        self.assertEqual(sentinel.read_bytes(), b'previous evidence')
        self.assertEqual(list(self.out.iterdir()), [sentinel])
        self.out = sentinel
        code, summary = self.run_cli()
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'output_refused')
        self.assertEqual(sentinel.read_bytes(), b'previous evidence')

    def test_existing_empty_output_allowed(self):
        self.out.mkdir()
        self.assertEqual(self.run_cli()[0], 0)

    def test_mock_failure_retains_complete_result(self):
        from railcorridor.adapter import MockAdapter
        with patch('railcorridor.adapter.MockAdapter', side_effect=lambda: MockAdapter(fail_at=2)):
            code, summary = self.run_cli(mock=True, in_process=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'mock_failed')
        result = self.read('execution.json')
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual(result['writes'], 2)
        self.assertFalse(result['rollback_attempted'])

    def test_unexpected_failure_logged(self):
        with patch('railcorridor.planning.search', side_effect=RuntimeError('test failure')):
            code, summary = self.run_cli(in_process=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(summary['status'], 'unexpected_failure')
        self.assertIn('test failure', (self.out / 'error.log').read_text(encoding='utf-8'))

    def test_missing_log_not_claimed(self):
        original = Path.open

        def open_path(path, *args, **kwargs):
            if path.name == 'error.log':
                raise PermissionError('injected log failure')
            return original(path, *args, **kwargs)

        with patch('railcorridor.planning.search', side_effect=RuntimeError('test failure')), patch.object(Path, 'open', open_path):
            code, summary = self.run_cli(in_process=True)
        self.assertNotEqual(code, 0)
        self.assertNotIn('error.log', summary['paths'])

    def inspect(self, in_process=False, command='status'):
        args = [command, '--run', str(self.out)]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.out.rglob('*') if p.is_file()}
        if in_process:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = bridge_cli.main(args)
            text = stdout.getvalue()
        else:
            proc = subprocess.run([sys.executable, str(ROOT / 'bridge_cli.py'), *args],
                                  cwd=self.base, capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.stderr, '')
            code, text = proc.returncode, proc.stdout
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns)
                                 for p in self.out.rglob('*') if p.is_file()})
        self.assertLessEqual(len(text.encode('utf-8')), 4096)
        self.assertEqual(len(text.splitlines()), 1)
        summary = json.loads(text)
        self.assertIs(summary['game_constructed'], False)
        return code, summary

    def change_manifest(self, change):
        record = self.read('run.json')
        change(record)
        (self.out / 'run.json').write_text(json.dumps(record), encoding='utf-8')

    def test_verify_design_and_mock_fresh_process(self):
        for mock in (False, True):
            self.out = self.base / str(mock)
            self.run_cli(mock=mock)
            code, result = self.inspect(command='verify')
            self.assertEqual((code, result['status']), (0, 'integrity_verified'))
            self.assertEqual(result['changed_files'], [])
            self.assertEqual(result['missing_files'], [])

    def test_verify_reports_all_changed_and_missing_files(self):
        self.run_cli(mock=True)
        for name in ('summary.json', 'candidate.json'):
            (self.out / name).write_bytes(b'changed')
        for name in ('search.json', 'execution.json'):
            (self.out / name).unlink()
        code, result = self.inspect(command='verify')
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'integrity_failed')
        self.assertEqual(result['changed_files'], ['candidate.json', 'summary.json'])
        self.assertEqual(result['missing_files'], ['execution.json', 'search.json'])

    def test_verify_unavailable_metadata(self):
        def unavailable():
            code, result = self.inspect(command='verify')
            self.assertNotEqual(code, 0)
            self.assertEqual(result['status'], 'verification_unavailable')
            self.assertEqual(result['changed_files'], [])
            self.assertEqual(result['missing_files'], [])

        unavailable()
        self.assertFalse(self.out.exists())
        self.run_cli()
        path = self.out / 'run.json'
        original = path.read_bytes()
        path.unlink()
        unavailable()
        self.assertFalse(path.exists())
        for contents in (b'{', b'[]', b'{}', b'\xff', b'x' * 65537,
                         b'{"schema_version":"1.0","schema_version":"1.0"}'):
            path.write_bytes(contents)
            unavailable()
        for change in (lambda r: r.update(schema_version='old'),
                       lambda r: r.update(record_state='unfinished'),
                       lambda r: r.pop('artifact_sha256'),
                       lambda r: r.update(artifact_sha256={}),
                       lambda r: r['artifact_sha256'].update({'summary.json': 'invalid'}),
                       lambda r: r['artifact_sha256'].update({'../outside.json': '0' * 64}),
                       lambda r: r['summary'].update(paths={}),
                       lambda r: r['summary'].pop('search_status'),
                       lambda r: r['summary'].pop('candidate_hash'),
                       lambda r: r.update(game_constructed=True)):
            path.write_bytes(original)
            self.change_manifest(change)
            unavailable()

    def test_verify_final_failed_outcome_is_still_verifiable(self):
        fixture = self.fixture(lambda f: f['search'].update(candidate_budget=0))
        self.assertNotEqual(self.run_cli(fixture)[0], 0)
        self.assertEqual(self.read('run.json')['record_state'], 'final')
        code, result = self.inspect(command='verify')
        self.assertEqual((code, result['status']), (0, 'integrity_verified'))

    def test_verify_replaced_artifact_and_unreadable_evidence(self):
        self.run_cli()
        artifact = self.out / 'candidate.json'
        artifact.unlink()
        artifact.mkdir()
        code, result = self.inspect(command='verify')
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'integrity_failed')
        self.assertEqual(result['changed_files'], ['candidate.json'])
        self.assertEqual(result['missing_files'], [])
        with patch.object(bridge_app, 'file_hash', side_effect=OSError('unreadable')):
            code, result = self.inspect(in_process=True, command='verify')
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'verification_unavailable')

    def test_status_design_and_mock_fresh_process(self):
        for mock in (False, True):
            self.out = self.base / str(mock)
            _, original = self.run_cli(mock=mock)
            code, status = self.inspect()
            self.assertEqual(code, 0)
            for key in ('status', 'search_status', 'candidate_hash', 'accepted', 'evaluated', 'paths', 'blockers'):
                self.assertEqual(status[key], original[key])
            self.assertEqual(status['mode'], 'mock' if mock else 'design')
            self.assertEqual(status['record_state'], 'final')
            self.assertEqual(status['input_sha256'], hashlib.sha256(FIXTURE.read_bytes()).hexdigest())

    def test_status_missing_and_legacy_unchanged(self):
        code, status = self.inspect()
        self.assertNotEqual(code, 0)
        self.assertEqual(status['status'], 'status_unavailable')
        self.assertFalse(self.out.exists())
        self.run_cli()
        (self.out / 'run.json').unlink()
        code, status = self.inspect()
        self.assertNotEqual(code, 0)
        self.assertEqual(status['status'], 'status_unavailable')
        self.assertFalse((self.out / 'run.json').exists())

    def test_status_corrupt_records(self):
        self.run_cli()
        path = self.out / 'run.json'
        valid = path.read_bytes()
        for text in ('{', '[]', '{}', '{"schema_version":"1.0","schema_version":"1.0"}', 'x' * 65537):
            path.write_text(text, encoding='utf-8')
            code, status = self.inspect()
            self.assertNotEqual(code, 0)
            self.assertEqual(status['status'], 'status_unavailable')
        for change in (lambda r: r.update(schema_version='unknown'),
                       lambda r: r.update(game_constructed=True),
                       lambda r: r['summary'].update(candidate_hash=None),
                       lambda r: r['summary'].update(evaluated=True),
                       lambda r: r.update(mode='mock'),
                       lambda r: r['summary'].update(blockers=['\u2603' * 400] * 8),
                       lambda r: r['artifact_sha256'].update({'../outside.json': '0' * 64})):
            path.write_bytes(valid)
            self.change_manifest(change)
            code, status = self.inspect()
            self.assertNotEqual(code, 0)
            self.assertEqual(status['status'], 'status_unavailable')

    def test_status_missing_or_changed_evidence(self):
        self.run_cli()
        for name in ('summary.json', 'search.json', 'candidate.json'):
            path = self.out / name
            original = path.read_bytes()
            for contents in (None, b'corrupt'):
                if contents is None:
                    path.unlink()
                else:
                    path.write_bytes(contents)
                code, status = self.inspect()
                self.assertNotEqual(code, 0)
                self.assertEqual(status['status'], 'status_unavailable')
            path.write_bytes(original)

    def test_interrupted_run_is_incomplete_not_running(self):
        with patch('railcorridor.planning.search', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_cli(in_process=True)
        code, status = self.inspect()
        self.assertNotEqual(code, 0)
        self.assertEqual(status['status'], 'run_incomplete')
        self.assertIn('unknown', status['blockers'][0])

    def test_status_records_failed_and_incomplete_outcomes(self):
        for budget in (0, 1):
            self.out = self.base / str(budget)
            fixture = self.fixture(lambda f: f['search'].update(candidate_budget=budget))
            self.run_cli(fixture, mock=True)
            code, status = self.inspect()
            self.assertNotEqual(code, 0)
            self.assertEqual(status['status'], 'incomplete_search')
            self.assertEqual(status['record_state'], 'final')
        from railcorridor.adapter import MockAdapter
        self.out = self.base / 'failure'
        with patch('railcorridor.adapter.MockAdapter', side_effect=lambda: MockAdapter(fail_at=2)):
            self.run_cli(mock=True, in_process=True)
        code, status = self.inspect()
        self.assertNotEqual(code, 0)
        self.assertEqual(status['status'], 'mock_failed')

    def test_status_never_calls_design_or_execution(self):
        self.run_cli(mock=True)
        with contextlib.ExitStack() as stack:
            forbidden = [stack.enter_context(patch(name, side_effect=AssertionError('status invoked engine')))
                         for name in ('railcorridor.planning.parse_json', 'railcorridor.planning.validate_fixture',
                                      'railcorridor.planning.search', 'railcorridor.planning.objective',
                                      'railcorridor.adapter.compile_plan', 'railcorridor.adapter.MockAdapter',
                                      'railcorridor.adapter.execute')]
            self.assertEqual(self.inspect(in_process=True)[0], 0)
            self.assertEqual(self.inspect(in_process=True, command='verify')[0], 0)
            self.assertEqual(self.call_api(bridge_app.status, self.out)['status'], 'mock_verified')
            self.assertEqual(self.call_api(bridge_app.verify, self.out)['status'], 'integrity_verified')
            for function in forbidden:
                function.assert_not_called()
        # Also prove a fresh status process does not even import proof modules.
        script = ('import sys; sys.path.insert(0, sys.argv.pop(1)); import bridge_cli; '
                  'code=bridge_cli.main(); '
                  'assert not any(n.startswith(("railcorridor", "railops")) for n in sys.modules); '
                  'sys.exit(code)')
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT), 'status', '--run', str(self.out)],
                              capture_output=True, text=True, cwd=self.base, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'], 'mock_verified')
        proc = subprocess.run([sys.executable, '-c', script, str(ROOT), 'verify', '--run', str(self.out)],
                              capture_output=True, text=True, cwd=self.base, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'], 'integrity_verified')

    def test_atomic_finalization_failure_leaves_unfinished_manifest(self):
        replace = bridge_app.os.replace

        def fail_final(source, target):
            if target.name == 'run.json' and json.loads(source.read_text())['record_state'] == 'final':
                raise OSError('injected atomic publication failure')
            return replace(source, target)

        with patch.object(bridge_app.os, 'replace', side_effect=fail_final):
            code, result = self.run_cli(in_process=True)
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'unexpected_failure')
        self.assertEqual(self.inspect()[1]['status'], 'run_incomplete')
        self.assertFalse(list(self.out.glob('*.tmp')))

    def test_atomic_writer_preserves_previous_metadata_on_failure(self):
        path = self.base / 'record.json'
        bridge_app.atomic_json(path, {'original': True})
        with patch.object(bridge_app.os, 'replace', side_effect=OSError('injected')):
            with self.assertRaises(OSError):
                bridge_app.atomic_json(path, {'original': False})
        self.assertEqual(json.loads(path.read_text()), {'original': True})


class WrapperTests(unittest.TestCase):
    def test_cli_delegates_and_preserves_all_exit_codes(self):
        outcomes = (*bridge_app.OUTCOMES, 'output_refused', 'status_unavailable',
                    'run_incomplete', 'verification_unavailable', 'integrity_failed', 'integrity_verified')
        for command in ('design', 'status', 'verify'):
            args = (['design', '--fixture', 'fixture.json', '--output', 'output', '--mock-execute']
                    if command == 'design' else [command, '--run', 'output'])
            for outcome in outcomes:
                with self.subTest(command=command, outcome=outcome):
                    result = {**bridge_app.initial_summary(), 'status': outcome}
                    stdout = io.StringIO()
                    with patch.object(bridge_app, command, return_value=result) as function:
                        with contextlib.redirect_stdout(stdout):
                            code = bridge_cli.main(args)
                    if command == 'design':
                        function.assert_called_once_with(Path('fixture.json'), Path('output'), True)
                    else:
                        function.assert_called_once_with(Path('output'))
                    self.assertEqual(code, 0 if outcome in (*bridge_app.SUCCESS, 'integrity_verified') else 1)
                    self.assertEqual(json.loads(stdout.getvalue()), result)
                    self.assertEqual(len(stdout.getvalue().splitlines()), 1)
                    self.assertLessEqual(len(stdout.getvalue().encode('utf-8')), 4096)

    def test_argument_errors_remain_compact_invalid_input(self):
        for args in ([], ['unknown'], ['design'], ['status'], ['verify'],
                     ['design', '--fixture', 'a', '--output', 'b', '--unknown']):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(bridge_app, 'design') as design:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = bridge_cli.main(args)
            design.assert_not_called()
            self.assertEqual(code, 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result['status'], 'invalid_input')
            self.assertTrue(result['blockers'])
            self.assertIs(result['game_constructed'], False)
            self.assertEqual(stderr.getvalue(), '')
            self.assertEqual(len(stdout.getvalue().splitlines()), 1)
            self.assertLessEqual(len(stdout.getvalue().encode('utf-8')), 4096)

    def test_long_paths_are_compacted_only_by_cli(self):
        result = {**bridge_app.initial_summary(), 'status': 'design_ready',
                  'paths': {'summary.json': 'x' * 5000}}
        stdout = io.StringIO()
        with patch.object(bridge_app, 'design', return_value=result):
            with contextlib.redirect_stdout(stdout):
                code = bridge_cli.main(['design', '--fixture', 'a', '--output', 'b'])
        compact = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(compact['paths'], {'summary.json': 'summary.json'})
        self.assertEqual(compact['paths_relative_to'], 'caller-selected output directory')
        self.assertEqual(result['paths']['summary.json'], 'x' * 5000)
        self.assertLessEqual(len(stdout.getvalue().encode('utf-8')), 4096)


if __name__ == '__main__':
    unittest.main()
