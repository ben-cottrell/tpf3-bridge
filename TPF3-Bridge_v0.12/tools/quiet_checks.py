#!/usr/bin/env python3
"""Run a named local test suite; retain full diagnostics and emit compact JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import unittest

SUITES = {
    'batch_setup': ('.', 'tests', 'test_cli_batch.py'),
    'connection_input': ('.', 'tests', 'test_connection_input.py'),
    'connection_geometry': ('.', 'tests', 'test_connection_geometry.py'),
    'connection_application': ('.', 'tests', 'test_connection_app.py'),
    'geometry': ('proof', 'tests', 'test_geom*.py'),
    'branch': ('proof', 'tests', 'test_branch*.py'),
    'corridor': ('proof', 'tests', 'test_corridor_*.py'),
    'application': ('.', 'tests', 'test_cli*.py'),
    'legacy': ('proof', 'tests', 'test_*.py'),
}


def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def input_hashes(root: Path) -> dict[str, str]:
    """Record relevant local bytes. This is provenance, not a cache or environment proof."""
    paths: set[Path] = set()
    for folder, pattern in [('proof', '*.py'), ('evidence', '*.json'), ('tests', '*.py')]:
        paths.update((root / folder).rglob(pattern))
    for name in ['bridge_cli.py', 'bridge_app.py', 'bridge_connection.py',
                 'tools/quiet_checks.py', 'tools/task_runner.py',
                 'tools/connection_acceptance.py', 'tools/task_queue_connection.json']:
        p = root / name
        if p.is_file():
            paths.add(p)
    for folder in (root / 'proof').glob('*_fixtures'):
        paths.update(folder.rglob('*.json'))
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file() and '__pycache__' not in p.parts}


def child(cwd: Path, start: str, pattern: str, report: Path) -> int:
    os.chdir(cwd)
    sys.path.insert(0, str(cwd))
    begin = time.monotonic()
    try:
        suite = unittest.defaultTestLoader.discover(start_dir=start, pattern=pattern)
        result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
        issues = ([{'kind': 'failure', 'test': t.id()} for t, _ in result.failures]
                  + [{'kind': 'error', 'test': t.id()} for t, _ in result.errors]
                  + [{'kind': 'unexpected_success', 'test': t.id()} for t in result.unexpectedSuccesses]
                  + [{'kind': 'skipped', 'test': t.id(), 'reason': why} for t, why in result.skipped]
                  + [{'kind': 'expected_failure', 'test': t.id()} for t, _ in result.expectedFailures])
        if result.testsRun == 0:
            status = 'no_tests'
        elif not result.wasSuccessful():
            status = 'failed'
        elif result.skipped or result.expectedFailures:
            status = 'passed_with_exceptions'
        else:
            status = 'passed'
        data = dict(status=status, tests_run=result.testsRun, failures=len(result.failures),
                    errors=len(result.errors), skipped=len(result.skipped),
                    expected_failures=len(result.expectedFailures),
                    unexpected_successes=len(result.unexpectedSuccesses), issues=issues)
    except Exception as exc:
        import traceback
        traceback.print_exc(file=sys.stdout)
        data = {'status': 'discovery_error', 'message': str(exc), 'tests_run': 0}
    data['elapsed_seconds'] = time.monotonic() - begin
    write_json(report, data)
    return 0 if data['status'] == 'passed' else 1


def run_suite(root: Path, suite: str, label: str, timeout: float) -> tuple[dict, int]:
    root = root.resolve()
    if suite not in SUITES:
        raise ValueError('Unknown suite')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', label):
        raise ValueError('Label must contain 1–40 letters, digits, hyphens or underscores')
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('Timeout must be finite and in (0, 3600] seconds')
    parent = (root / '.local_checks').resolve()
    if not parent.is_relative_to(root):
        raise ValueError('Local check destination must remain inside the project')
    parent.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=label + '_', dir=parent))
    cwd_name, start, pattern = SUITES[suite]
    cwd = (root / cwd_name).resolve()
    log_path, report_path = out / 'full.log', out / 'report.json'
    child_path = out / 'test_result.json'
    command = [sys.executable, str(Path(__file__).resolve()), '--child', str(cwd), start, pattern, str(child_path)]
    report = {'suite': suite, 'command': command, 'cwd': str(cwd),
              'python': sys.version, 'platform': platform.platform(),
              'hash_scope': 'local proof Python, evidence JSON, proof fixture JSON, application tests, wrapper and runner; no cache',
              'input_sha256': input_hashes(root), 'timeout_seconds': timeout}
    begin = time.monotonic()
    if not (cwd / start).is_dir():
        detail = {'status': 'suite_unavailable', 'message': f'Missing test directory: {cwd / start}', 'tests_run': 0}
        log_path.write_text(detail['message'] + '\n', encoding='utf-8')
    else:
        with log_path.open('w', encoding='utf-8') as log:
            try:
                proc = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                      timeout=timeout, check=False,
                                      env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
                if child_path.is_file():
                    detail = json.loads(child_path.read_text(encoding='utf-8'))
                    if proc.returncode != 0 and detail.get('status') == 'passed':
                        detail['status'] = 'runner_error'
                else:
                    detail = {'status': 'runner_error', 'message': 'Test process did not create a result record', 'tests_run': None}
                detail['exit_code'] = proc.returncode
            except subprocess.TimeoutExpired:
                detail = {'status': 'timeout', 'tests_run': None, 'message': 'Test process exceeded its limit; inspect full.log'}
            except OSError as exc:
                log.write(str(exc) + '\n')
                detail = {'status': 'runner_error', 'tests_run': None, 'message': str(exc)}
    report.update(result=detail, elapsed_seconds=time.monotonic() - begin)
    write_json(report_path, report)
    issues = detail.get('issues', [])
    summary = {'status': detail['status'], 'suite': suite, 'tests_run': detail.get('tests_run'),
               'failures': detail.get('failures'), 'errors': detail.get('errors'),
               'skipped': detail.get('skipped'), 'issue_count': len(issues),
               'first_issues': [{'kind': i['kind'], 'test': i['test'][:160]} for i in issues[:3]],
               'additional_issues': max(0, len(issues) - 3),
               'report': report_path.relative_to(root).as_posix(),
               'log': log_path.relative_to(root).as_posix()}
    write_json(out / 'summary.json', summary)
    return summary, 0 if detail['status'] == 'passed' else 1


def main(argv: list[str] | None = None) -> int:
    args_in = sys.argv[1:] if argv is None else argv
    if args_in and args_in[0] == '--child':
        if len(args_in) != 5:
            raise SystemExit('Invalid internal test invocation')
        return child(Path(args_in[1]), args_in[2], args_in[3], Path(args_in[4]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=SUITES, default='corridor')
    parser.add_argument('--label', default='check')
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args(args_in)
    try:
        summary, code = run_suite(Path(__file__).resolve().parents[1], args.suite, args.label, args.timeout)
    except (OSError, ValueError) as exc:
        summary, code = {'status': 'runner_error', 'message': str(exc)[:400], 'report': None}, 2
    print(json.dumps(summary, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
