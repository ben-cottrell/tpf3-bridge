"""Finite runner tests. Every worker is a local fake; no Codex sessions."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch

from tools import task_runner as runner


FAKE = r'''
import json,sys,time,uuid
from pathlib import Path
root=Path.cwd(); control=root/'.task_batch'
plan=json.loads((control/'fake_plan.json').read_text())
seen=list(control.glob('seen_*.json')); n=len(seen)
prompt=sys.stdin.read(); task=json.loads(prompt.split('\nTask card:\n')[1].split('\nShort state:\n')[0])
action=plan[min(n,len(plan)-1)]
session=sys.argv[1] if len(sys.argv)>1 else str(uuid.uuid5(uuid.NAMESPACE_DNS,task['id']))
(control/f'seen_{n}.json').write_text(json.dumps({'session':session,'resume':len(sys.argv)>1,'task':task['id']}))
if action=='timeout': time.sleep(30)
if action=='wrong_session': session=str(uuid.uuid4())
print(json.dumps({'type':'thread.started','thread_id':session}),flush=True)
if action=='scope': (root/'unrelated.txt').write_text('changed')
if action=='queue': (root/'tools/task_queue.json').write_text('{}')
if action=='card': (root/'CURRENT_TASK.md').write_text('relaxed scope')
if action=='journal': (control/'state.json').write_text('{}')
if action in ('permission','auth','usage'):
    message={'permission':'Permission denied','auth':'authentication failed','usage':'usage limit exceeded'}[action]
    print(json.dumps({'type':'error','message':message}));sys.exit(1)
if action=='blocked':
    print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'BLOCKED: permission denied'}}));sys.exit(0)
(root/'edit.txt').write_text('bad' if action=='fail' else 'ok')
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}))
sys.exit(1 if action=='worker_fail' else 0)
'''


class BatchTests(unittest.TestCase):
    def setUp(self):
        # Use ordinary project directories, avoiding restrictive Windows mkdtemp ACLs.
        self.root = runner.ROOT / '.local_checks' / ('fake_batch_' + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        def cleanup():
            self.assertEqual(self.root.resolve().parent, (runner.ROOT / '.local_checks').resolve())
            shutil.rmtree(self.root)
        self.addCleanup(cleanup)
        (self.root / 'tools').mkdir()
        (self.root / 'tools/fake.py').write_text(FAKE, encoding='utf-8')
        (self.root / 'STATE.md').write_text('L02 complete; short test state.')
        (self.root / 'AGENTS.md').write_text('Preserve instructions.')
        (self.root / 'unrelated.txt').write_text('user work')
        (self.root / runner.CONTROL).mkdir()
        self.queue = {'version': 1, 'tasks': [dict(
            id=name, card='Fake test task', pointers=['edit.txt'], write_files=['edit.txt', 'STATE.md'],
            acceptance=[['python', '-c',
                         'import json,sys; from pathlib import Path; ok=Path("edit.txt").read_text()=="ok"; '
                         'print(json.dumps({"status":"passed" if ok else "failed","tests_run":1})); sys.exit(0 if ok else 1)']])
            for name in ('L03', 'L04', 'L05')]}
        (self.root / runner.QUEUE).write_text(json.dumps(self.queue))
        self.limits = dict(runner.LIMITS)
        self.launches = []

    def launch(self, command, root, out, timeout, prompt=None):
        self.launches.append((command, prompt))
        if prompt is not None:
            fake = [sys.executable, str(root / 'tools/fake.py')]
            if 'resume' in command:
                fake.append(command[-2])
            return runner.process(fake, root, out, timeout, prompt)
        return runner.process(command, root, out, timeout)

    def run_batch(self, actions=None):
        if actions is not None:
            (self.root / runner.CONTROL / 'fake_plan.json').write_text(json.dumps(actions))
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run_batch(self.root, self.queue, self.limits, 'FAKE_NOT_CODEX',
                                    launch=self.launch, authenticate=False)

    def record(self):
        return json.loads((self.root / runner.CONTROL / 'state.json').read_text())

    def test_sequential_new_sessions_acceptance_and_usage(self):
        result = self.run_batch(['ok'])
        self.assertEqual(result['completed'], ['L03', 'L04', 'L05'])
        self.assertEqual(result['invocations'], 3)
        self.assertEqual([prompt is not None for _, prompt in self.launches], [True, False] * 3)
        attempts = self.record()['attempts']
        self.assertEqual(len({a['session_id'] for a in attempts}), 3)
        self.assertEqual(attempts[0]['usage_events'], [{'input_tokens': 10, 'output_tokens': 2}])
        self.assertEqual((self.root / 'unrelated.txt').read_text(), 'user work')

    def test_single_repair_uses_exact_session(self):
        self.run_batch(['fail', 'ok'])
        workers = [c for c, p in self.launches if p is not None]
        record = self.record()
        self.assertEqual(record['invocations'], 4)
        self.assertEqual(record['attempts'][0]['session_id'], record['attempts'][1]['session_id'])
        self.assertIn('resume', workers[1])
        self.assertEqual(workers[1][-2], record['attempts'][0]['session_id'])
        self.assertNotIn('--last', workers[1])

    def test_failed_repair_stops_without_next_task(self):
        with self.assertRaisesRegex(runner.Stop, 'unrepaired'):
            self.run_batch(['fail'])
        self.assertEqual(self.record()['invocations'], 2)
        self.assertEqual(self.record()['completed'], [])

    def test_limit_caps_repair_and_task_count(self):
        self.limits['invocations'] = 1
        with self.assertRaisesRegex(runner.Stop, 'invocation limit'):
            self.run_batch(['fail'])
        self.assertEqual(self.record()['invocations'], 1)

    def test_three_tasks_six_invocations_maximum(self):
        result = self.run_batch(['fail', 'ok', 'fail', 'ok', 'fail', 'ok'])
        self.assertEqual(result['invocations'], 6)
        self.assertEqual(result['status'], 'queue_exhausted')

    def test_completed_restart_does_not_launch(self):
        self.run_batch(['ok'])
        self.launches.clear()
        self.assertEqual(self.run_batch()['status'], 'queue_exhausted')
        self.assertEqual(self.launches, [])

    def test_interrupted_restart_requires_reconciliation(self):
        (self.root / runner.CONTROL / 'fake_plan.json').write_text('["ok"]')
        with patch.object(self, 'launch', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_batch()
        self.assertEqual(self.record()['invocations'], 1)
        with self.assertRaisesRegex(runner.Stop, 'reconciliation'):
            self.run_batch()
        self.assertEqual(self.launches, [])

    def test_stale_lock_requires_reconciliation(self):
        (self.root / runner.CONTROL / 'lock').write_text('old process; unknown state')
        with self.assertRaisesRegex(runner.Stop, 'locked'):
            self.run_batch(['ok'])
        self.assertEqual(self.launches, [])

    def test_queue_and_limit_changes_are_not_new_approval(self):
        self.limits['tasks'] = 1
        self.assertEqual(self.run_batch(['ok'])['status'], 'task_limit_reached')
        self.launches.clear()
        self.limits['tasks'] = 3
        with self.assertRaisesRegex(runner.Stop, 'scope, limits'):
            self.run_batch()
        self.assertEqual(self.launches, [])

    def test_permission_usage_and_auth_stop_without_repair(self):
        for kind in ('permission', 'usage', 'auth', 'blocked'):
            with self.subTest(kind=kind):
                other = self.root / kind
                shutil.copytree(self.root / 'tools', other / 'tools')
                for name in ('STATE.md', 'AGENTS.md', 'unrelated.txt'):
                    shutil.copyfile(self.root / name, other / name)
                (other / runner.CONTROL).mkdir()
                (other / runner.CONTROL / 'fake_plan.json').write_text(json.dumps([kind]))
                with self.assertRaisesRegex(runner.Stop, 'permission/authentication/usage'):
                    runner.run_batch(other, self.queue, self.limits, 'FAKE_NOT_CODEX', launch=self.launch, authenticate=False)
                record = json.loads((other / runner.CONTROL / 'state.json').read_text())
                self.assertEqual(record['invocations'], 1)

    def test_scope_violation_stops_before_acceptance(self):
        with self.assertRaisesRegex(runner.Stop, 'out-of-scope'):
            self.run_batch(['scope'])
        self.assertEqual(len(self.launches), 1)
        # No reset: preserve evidence for human reconciliation.
        self.assertEqual((self.root / 'unrelated.txt').read_text(), 'changed')

    def test_worker_cannot_enlarge_queue(self):
        with self.assertRaisesRegex(runner.Stop, 'out-of-scope'):
            self.run_batch(['queue'])
        self.assertEqual(self.record()['invocations'], 1)

    def test_worker_cannot_rewrite_own_card_or_journal(self):
        with self.assertRaisesRegex(runner.Stop, 'approved task card'):
            self.run_batch(['card'])
        self.assertEqual(self.record()['invocations'], 1)

    def test_worker_journal_tampering_stops(self):
        with self.assertRaisesRegex(runner.Stop, 'worker changed runner journal'):
            self.run_batch(['journal'])
        self.assertEqual(self.record()['invocations'], 1)

    def test_worker_exit_failure_is_not_hidden_by_passing_checks(self):
        result = self.run_batch(['worker_fail', 'ok'])
        self.assertEqual(result['invocations'], 4)
        self.assertEqual(self.record()['attempts'][0]['exit_code'], 1)

    def test_changed_workspace_cannot_restart(self):
        self.run_batch(['ok'])
        self.launches.clear()
        (self.root / 'unrelated.txt').write_text('new external edit')
        with self.assertRaisesRegex(runner.Stop, 'workspace changed'):
            self.run_batch()
        self.assertEqual(self.launches, [])

    def test_resume_must_report_the_same_session(self):
        with self.assertRaisesRegex(runner.Stop, 'session ID'):
            self.run_batch(['fail', 'wrong_session'])
        self.assertEqual(self.record()['invocations'], 2)

    def test_timeout_stops_without_repair(self):
        self.limits['timeout'] = 1
        with self.assertRaisesRegex(runner.Stop, 'timeout'):
            self.run_batch(['timeout'])
        self.assertEqual(self.record()['invocations'], 1)

    def test_dry_run_never_launches(self):
        with patch.object(runner.shutil, 'which', return_value='FAKE_NOT_CODEX'), patch.object(runner, 'process') as process:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(runner.main(['--dry-run']), 0)
            record = json.loads(stdout.getvalue())
            self.assertEqual(len(record['tasks']), 3)
            self.assertEqual(record['limits']['invocations'], 6)
            self.assertFalse(record['hard_credit_cap'])
            process.assert_not_called()

    def test_command_keeps_restricted_permissions_and_model(self):
        command = runner.codex_command('codex', self.root)
        self.assertIn('workspace-write', command)
        self.assertIn('never', command)
        self.assertIn('sandbox_workspace_write.network_access=false', command)
        for forbidden in ('--dangerously-bypass-approvals-and-sandbox', 'danger-full-access', '--model', '--ignore-rules', '--ignore-user-config'):
            self.assertNotIn(forbidden, command)

    def test_mcp_override_uses_cli_dotted_key_syntax(self):
        with patch.object(Path, 'exists', return_value=True), patch.object(Path, 'read_text', return_value='[mcp_servers.node_repl]\ncommand="unused"'):
            command = runner.codex_command('codex', self.root)
        self.assertIn('mcp_servers.node_repl.enabled=false', command)

    def test_nonfinite_or_unbounded_limits_are_rejected(self):
        # Exercise error logging against a saved fake journal, never the real batch.
        (self.root / runner.CONTROL / 'state.json').write_text('{}')
        with patch.object(runner, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()), patch.object(runner, 'run_batch') as batch:
            self.assertEqual(runner.main(['--timeout', '0']), 1)
            self.assertEqual(runner.main(['--timeout', '3601']), 1)
            batch.assert_not_called()
        self.assertIn('timeout must be finite',
                      (self.root / runner.CONTROL / 'runner_errors.log').read_text())
        self.assertEqual((self.root / runner.CONTROL / 'state.json').read_text(), '{}')

    def reconcile_for_test(self):
        journal = self.record()
        journal.update(phase='idle', checkpoint=runner.snapshot(self.root),
                       reconciled_repair={'task': 'L03', 'session_id': journal['attempts'][0]['session_id'],
                                          'reason': 'Human reviewed permission stop; keep the one-repair limit.'})
        runner.write_json(self.root / runner.CONTROL / 'state.json', journal)

    def test_explicit_reconciliation_preserves_session_and_budget(self):
        with self.assertRaises(runner.Stop):
            self.run_batch(['permission', 'ok'])
        original = self.record()['attempts'][0]['session_id']
        self.reconcile_for_test()
        result = self.run_batch()
        self.assertEqual(result['invocations'], 4)
        record = self.record()
        self.assertEqual(record['attempts'][1]['session_id'], original)
        self.assertEqual(record['attempts'][1]['attempt'], 1)
        self.assertNotIn('reconciled_repair', record)

    def test_reconciled_failure_cannot_get_a_second_repair(self):
        with self.assertRaises(runner.Stop):
            self.run_batch(['permission', 'fail'])
        self.reconcile_for_test()
        with self.assertRaisesRegex(runner.Stop, 'unrepaired'):
            self.run_batch()
        self.assertEqual(self.record()['invocations'], 2)
        with self.assertRaisesRegex(runner.Stop, 'reconciliation'):
            self.run_batch()

    def test_prompt_avoids_unrelated_permission_probes(self):
        prompt = runner.prompt_for(self.queue['tasks'][0], 'state')
        self.assertIn('Do not run unscoped git status', prompt)
        self.assertIn('Do not', prompt)

    def test_host_source_snapshots_preserve_originals(self):
        (self.root / 'edit.txt').write_text('original source')
        self.run_batch(['ok'])
        original = self.root / runner.CONTROL / 'L03_0_1/sources/edit.txt'
        self.assertEqual(original.read_text(), 'original source')
        self.assertEqual((self.root / 'edit.txt').read_text(), 'ok')
        prompt = (original.parents[1] / 'prompt.txt').read_text()
        self.assertIn(str(original.parent), prompt)
        self.assertIn('do not make your own backups', prompt)

    def approve_extra_for_test(self):
        self.reconcile_for_test()
        journal = self.record()
        journal['reconciled_repair']['approved_extra_attempt'] = 2
        runner.write_json(self.root / runner.CONTROL / 'state.json', journal)

    def test_approved_extra_uses_original_session_and_total_cap(self):
        with self.assertRaises(runner.Stop):
            self.run_batch(['fail', 'fail', 'ok'])
        self.approve_extra_for_test()
        result = self.run_batch()
        self.assertEqual(result['invocations'], 5)
        attempts = self.record()['attempts']
        self.assertEqual(attempts[2]['attempt'], 2)
        self.assertEqual(attempts[2]['session_id'], attempts[0]['session_id'])
        self.assertEqual(self.record()['seal']['limits']['invocations'], 6)

    def test_extra_failure_cannot_get_another_exception(self):
        with self.assertRaises(runner.Stop):
            self.run_batch(['fail'])
        self.approve_extra_for_test()
        with self.assertRaisesRegex(runner.Stop, 'unrepaired'):
            self.run_batch()
        self.assertEqual(self.record()['invocations'], 3)
        self.approve_extra_for_test()
        with self.assertRaisesRegex(runner.Stop, 'invalid reconciled repair'):
            self.run_batch()
        self.assertEqual(self.record()['invocations'], 3)

    def prepare_named_batch(self):
        self.run_batch(['ok'])
        self.previous = (self.root / runner.CONTROL / 'state.json').read_bytes()
        self.batch_id = 'connection-l06-l08'
        control = self.root / runner.CONTROL / self.batch_id
        control.mkdir()
        (control / 'fake_plan.json').write_text('["ok"]')
        (self.root / 'tools/fake.py').write_text(
            FAKE.replace("control=root/'.task_batch'", "control=root/'.task_batch/connection-l06-l08'"))
        self.named_queue = json.loads(json.dumps(self.queue))
        for task, name in zip(self.named_queue['tasks'], ('L06', 'L07', 'L08')):
            task['id'] = name
        self.launches.clear()
        return control

    def run_named(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run_batch(self.root, self.named_queue, self.limits, 'FAKE_NOT_CODEX',
                                    launch=self.launch, authenticate=False, batch_id=self.batch_id)

    def test_named_batch_preserves_old_ledger_and_restarts_without_workers(self):
        control = self.prepare_named_batch()
        result = self.run_named()
        self.assertEqual(result['completed'], ['L06', 'L07', 'L08'])
        self.assertEqual(result['invocations'], 3)
        self.assertEqual((self.root / runner.CONTROL / 'state.json').read_bytes(), self.previous)
        self.assertEqual(json.loads((control / 'state.json').read_text())['seal']['batch_id'], self.batch_id)
        self.launches.clear()
        self.assertEqual(self.run_named()['status'], 'queue_exhausted')
        self.assertEqual(self.launches, [])

    def test_named_batch_requires_completed_predecessor_and_shared_lock(self):
        self.prepare_named_batch()
        path = self.root / runner.CONTROL / 'state.json'
        old = json.loads(self.previous)
        old['phase'] = 'invoking'
        runner.write_json(path, old)
        with self.assertRaisesRegex(runner.Stop, 'previous batch'):
            self.run_named()
        self.assertEqual(self.launches, [])
        path.write_bytes(self.previous)
        (path.parent / 'lock').write_text('another runner')
        with self.assertRaisesRegex(runner.Stop, 'locked'):
            self.run_named()

    def test_named_batch_failed_repair_and_restart_keep_limits(self):
        control = self.prepare_named_batch()
        (control / 'fake_plan.json').write_text('["fail"]')
        with self.assertRaisesRegex(runner.Stop, 'unrepaired'):
            self.run_named()
        journal = (control / 'state.json').read_bytes()
        self.assertEqual(json.loads(journal)['invocations'], 2)
        self.launches.clear()
        with self.assertRaisesRegex(runner.Stop, 'reconciliation'):
            self.run_named()
        self.assertEqual(self.launches, [])
        self.assertEqual((control / 'state.json').read_bytes(), journal)
        self.assertEqual((self.root / runner.CONTROL / 'state.json').read_bytes(), self.previous)

    def test_named_batch_history_mutation_stops(self):
        self.prepare_named_batch()
        fake = self.root / 'tools/fake.py'
        fake.write_text(fake.read_text() + "\n")
        original = self.launch
        def tamper(command, root, out, timeout, prompt=None):
            result = original(command, root, out, timeout, prompt)
            if prompt:
                (root / runner.CONTROL / 'old.log').write_text('unauthorised history change')
            return result
        with patch.object(self, 'launch', side_effect=tamper):
            with self.assertRaisesRegex(runner.Stop, 'out-of-scope'):
                self.run_named()

    def test_named_dry_run_is_read_only_and_queue_is_pinned(self):
        with patch.object(runner.shutil, 'which', return_value='FAKE_NOT_CODEX'), patch.object(runner, 'run_batch') as batch:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(runner.main(['--batch', 'connection-l06-l08', '--dry-run']), 0)
            value = json.loads(stdout.getvalue())
            self.assertEqual([t['id'] for t in value['tasks']], ['L06', 'L07', 'L08'])
            self.assertIn('connection-l06-l08', value['record'])
            self.assertEqual(value['limits'], runner.LIMITS)
            with patch.object(runner, 'digest', return_value='changed'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(['--batch', 'connection-l06-l08', '--dry-run']), 1)
            batch.assert_not_called()

    def test_named_batch_six_invocations_include_repairs(self):
        control = self.prepare_named_batch()
        (control / 'fake_plan.json').write_text('["fail", "ok", "fail", "ok", "fail", "ok"]')
        result = self.run_named()
        self.assertEqual(result['invocations'], 6)
        self.assertEqual(result['status'], 'queue_exhausted')
        attempts = json.loads((control / 'state.json').read_text())['attempts']
        for first, repair in zip(attempts[::2], attempts[1::2]):
            self.assertEqual(first['session_id'], repair['session_id'])

    def test_named_interrupted_restart_does_not_spend_another_invocation(self):
        control = self.prepare_named_batch()
        with patch.object(self, 'launch', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_named()
        before = (control / 'state.json').read_bytes()
        self.assertEqual(json.loads(before)['invocations'], 1)
        with self.assertRaisesRegex(runner.Stop, 'reconciliation'):
            self.run_named()
        self.assertEqual((control / 'state.json').read_bytes(), before)
        self.assertEqual(self.launches, [])

    def test_rejected_named_fingerprint_change_preserves_completed_record(self):
        control = self.prepare_named_batch()
        self.run_named()
        before = (control / 'state.json').read_bytes()
        self.limits['timeout'] += 1
        self.launches.clear()
        with self.assertRaisesRegex(runner.Stop, 'scope, limits'):
            self.run_named()
        self.assertEqual((control / 'state.json').read_bytes(), before)
        self.assertEqual(self.launches, [])


if __name__ == '__main__':
    unittest.main()
