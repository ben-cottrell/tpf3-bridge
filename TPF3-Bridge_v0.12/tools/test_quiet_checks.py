"""Tests for the handoff utility, not railway functionality."""
from pathlib import Path
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest

from quiet_checks import run_suite


class QuietChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tests = self.root / 'proof' / 'tests'
        self.tests.mkdir(parents=True)

    def write_test(self, body):
        (self.tests / 'test_corridor_example.py').write_text(body, encoding='utf-8')

    def run_check(self, timeout=10):
        return run_suite(self.root, 'corridor', 'sample', timeout)

    def test_success_is_counted(self):
        self.write_test('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertEqual(1,1)\n')
        summary, code = self.run_check()
        self.assertEqual((summary['status'], summary['tests_run'], code), ('passed', 1, 0))
        self.assertTrue((self.root / summary['report']).is_file())
        self.assertIn('test_corridor_example.py', str(json.loads((self.root/summary['report']).read_text())['input_sha256']))

    def test_failure_not_pass(self):
        self.write_test('import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail("detail retained")\n')
        summary, code = self.run_check()
        self.assertEqual(summary['status'], 'failed')
        self.assertNotEqual(code, 0)
        self.assertIn('detail retained', (self.root/summary['log']).read_text())

    def test_import_error_not_pass(self):
        self.write_test('raise RuntimeError("bad import")\n')
        summary, code = self.run_check()
        self.assertEqual(summary['errors'], 1)
        self.assertNotEqual(code, 0)

    def test_zero_tests_not_pass(self):
        summary, code = self.run_check()
        self.assertEqual(summary['status'], 'no_tests')
        self.assertNotEqual(code, 0)

    def test_missing_application_suite_not_pass(self):
        summary, code = run_suite(self.root, 'application', 'missing', 10)
        self.assertEqual(summary['status'], 'suite_unavailable')
        self.assertNotEqual(code, 0)

    def test_skip_not_clean_pass(self):
        self.write_test('import unittest\nclass T(unittest.TestCase):\n @unittest.skip("pending")\n def test_pending(self): pass\n')
        summary, code = self.run_check()
        self.assertEqual(summary['status'], 'passed_with_exceptions')
        self.assertEqual(summary['skipped'], 1)
        self.assertNotEqual(code, 0)

    def test_timeout_visible(self):
        self.write_test('import time\ntime.sleep(10)\n')
        summary, code = self.run_check(timeout=.1)
        self.assertEqual(summary['status'], 'timeout')
        self.assertNotEqual(code, 0)

    def test_no_stdout_leak_and_full_log_retained(self):
        self.write_test('import unittest\nprint("NOISY"*10000)\nclass T(unittest.TestCase):\n def test_ok(self): pass\n')
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            summary, code = self.run_check()
        self.assertEqual(captured.getvalue(), '')
        self.assertEqual(code, 0)
        self.assertGreater((self.root/summary['log']).stat().st_size, 50000)
        self.assertLess(len(json.dumps(summary).encode()), 4096)

    def test_reports_never_overwritten(self):
        a, _ = self.run_check()
        before = (self.root/a['report']).read_bytes()
        b, _ = self.run_check()
        self.assertNotEqual(a['report'], b['report'])
        self.assertEqual((self.root/a['report']).read_bytes(), before)

    def test_labels_cannot_escape(self):
        for label in ('../outside', 'a/b', '', 'x'*41):
            with self.subTest(label=label), self.assertRaises(ValueError):
                run_suite(self.root, 'corridor', label, 10)

    def test_invalid_timeout_rejected(self):
        for timeout in (True, 0, -1, float('nan'), float('inf'), 4000):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.run_check(timeout=timeout)

    def test_unknown_suite_rejected(self):
        with self.assertRaises(ValueError):
            run_suite(self.root, 'everything', 'test', 10)

    def test_all_issues_saved_with_compact_preview(self):
        body = 'import unittest\nclass T(unittest.TestCase):\n'
        body += ''.join(f' def test_bad_{i}(self): self.fail("failure {i}")\n' for i in range(8))
        self.write_test(body)
        summary, _ = self.run_check()
        self.assertEqual((summary['issue_count'], len(summary['first_issues']), summary['additional_issues']), (8, 3, 5))
        report = json.loads((self.root/summary['report']).read_text())
        self.assertEqual(len(report['result']['issues']), 8)

    def test_cli_prints_single_json(self):
        tools = self.root/'tools'
        tools.mkdir()
        original = Path(__file__).with_name('quiet_checks.py')
        script = tools/'quiet_checks.py'
        script.write_bytes(original.read_bytes())
        self.write_test('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): pass\n')
        result = subprocess.run([sys.executable, str(script), '--suite', 'corridor'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertEqual(json.loads(result.stdout)['status'], 'passed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
