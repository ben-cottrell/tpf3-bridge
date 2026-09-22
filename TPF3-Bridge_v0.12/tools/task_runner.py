"""Finite development batch. No worker is launched by --dry-run or --acceptance."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tomllib
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
QUEUE = 'tools/task_queue.json'
APPROVED_QUEUE_SHA256 = 'af747ce78b765ae31a78ffc79c5dd759e95ee4217843e9fe14b89bceae1d769e'
CONTROL = '.task_batch'
LIMITS = {'tasks': 3, 'invocations': 6, 'timeout': 900, 'check_timeout': 240}
FATAL = re.compile(r'usage.limit|rate.limit|quota|insufficient.credit|authentication|unauthorized|'
                   r'not.logged.in|permission.denied|access.is.denied|approval.required|sandbox.denied|'
                   r'too.many.requests|\b(?:401|403|429)\b', re.I)


class Stop(RuntimeError):
    pass


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def snapshot(root):
    """Hash locally, including existing evidence; never send the tree to a model."""
    files = {}
    for folder, dirs, names in os.walk(root, onerror=lambda e: (_ for _ in ()).throw(e)):
        dirs[:] = [n for n in dirs if n not in ('.git', '__pycache__', CONTROL)]
        for name in dirs + names:
            p = Path(folder) / name
            if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
                raise Stop('Linked project paths need manual review: ' + str(p))
        for name in names:
            p = Path(folder) / name
            files[p.relative_to(root).as_posix()] = digest(p)
    return files


def scope_changes(before, after, allowed):
    changed = [p for p in before.keys() | after.keys() if before.get(p) != after.get(p)]
    return sorted(p for p in changed if p not in allowed and not (
        p not in before and p.startswith(('.local_checks/', '.local_runs/batch_'))))


def test_names(root):
    return sorted(f'{p.name}:{node.name}' for p in (root / 'tests').glob('test_cli*.py')
                  for node in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
                  if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'))


def process(command, root, out, timeout, prompt=None):
    """Bounded subprocess with complete local output and descendant termination."""
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    with (out / 'stdout.log').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
        proc = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                env=env, start_new_session=os.name != 'nt')
        try:
            proc.communicate(None if prompt is None else prompt.encode('utf-8'), timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            tree_stopped = False
            try:
                if os.name == 'nt':
                    killed = subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                            stdout=stderr, stderr=stderr, timeout=15, check=False)
                    tree_stopped = killed.returncode == 0
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                    tree_stopped = True
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=5)
            raise Stop('timeout_or_interruption; reconcile before restarting; ' +
                       ('process tree terminated' if tree_stopped else 'descendant termination unconfirmed'))
    return proc.returncode


def worker_events(out):
    sessions, usage, errors, completed = set(), [], [], False
    with (out / 'stdout.log').open(encoding='utf-8') as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get('type')
            if kind == 'thread.started':
                sessions.add(str(uuid.UUID(event['thread_id'])))
            if kind == 'turn.completed':
                completed = True
                if 'usage' in event:
                    usage.append(event['usage'])
            if kind in ('error', 'turn.failed'):
                errors.append(json.dumps(event)[:1000])
            if kind == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                message = event['item'].get('text', '')
                if 'BLOCKED' in message or FATAL.search(message):
                    errors.append(message[:1000])
    return sessions, usage, errors, completed


def codex_command(executable, root, session=None):
    # Narrow permissions per invocation; retain account/model, instructions and rules.
    command = [executable, '--ask-for-approval', 'never', '--sandbox', 'workspace-write',
               '-C', str(root), '-c', 'sandbox_workspace_write.writable_roots=[]',
               '-c', 'sandbox_workspace_write.network_access=false',
               '-c', 'sandbox_workspace_write.exclude_slash_tmp=true',
               '-c', 'sandbox_workspace_write.exclude_tmpdir_env_var=true',
               '-c', 'forced_login_method="chatgpt"']
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    config = home / 'config.toml'
    settings = tomllib.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
    for name in settings.get('mcp_servers', {}):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise Stop('MCP configuration key needs explicit review before unattended execution')
        command += ['-c', 'mcp_servers.' + name + '.enabled=false']
    command += ['exec']
    return command + (['resume', '--json', session, '-'] if session else ['--json', '-'])


def preflight(executable, root, out):
    if any(os.environ.get(k) for k in ('OPENAI_API_KEY', 'CODEX_API_KEY')):
        raise Stop('API-key environment present; will not switch billing')
    for name, args, expected in [('auth', ['login', 'status'], 'Logged in using ChatGPT'),
                                 ('exec', ['exec', '--help'], '--json'),
                                 ('resume', ['exec', 'resume', '--help'], 'SESSION_ID')]:
        folder = out / name
        folder.mkdir()
        code = process([executable, *args], root, folder, 30)
        text = ''.join((folder / f'{part}.log').read_text(encoding='utf-8') for part in ('stdout', 'stderr'))
        if code or expected not in text or FATAL.search(text):
            raise Stop('permission/authentication/CLI preflight failed; see ' + str(folder))
    command = codex_command(executable, root)
    folder = out / 'policy'
    folder.mkdir()
    code = process(command[:command.index('exec')] + ['doctor', '--json'], root, folder, 30)
    if code:
        raise Stop('restricted invocation policy/preflight failed; see ' + str(folder))


def instructions(root):
    paths = []
    for folder in (root, *root.parents):
        for name in ('AGENTS.md', 'AGENTS.override.md', '.codex/config.toml'):
            path = folder / name
            if path.is_file():
                paths.append(path)
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    paths += [home / n for n in ('config.toml', 'AGENTS.md', 'AGENTS.override.md') if (home / n).is_file()]
    return {str(p): digest(p) for p in paths}


def source_snapshots(root, run, task):
    destination = run / 'sources'
    destination.mkdir()
    for name in task['write_files']:
        source = root / name
        if source.is_file():
            copy = destination / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(source.read_bytes())
    return destination


def prompt_for(task, state, repair=None, sources=None):
    header = ('Implement only the current approved task card below. Follow AGENTS.md and all applicable '
              'parent instructions. CURRENT_TASK.md contains this card. Read only the named source/test '
              'sections and necessary dependencies; do not read historical specifications or audit the repo. '
              'Do not run unscoped git status or scan old .local_checks directories: their ACLs may '
              'differ from the worker sandbox, and the runner already checks workspace scope. '
              'For a diff, use explicit task source paths only. Use the supplied state as prior evidence; '
              'the host runner reads check reports and executes acceptance outside the worker sandbox. '
              'The host supplies original source snapshots: do not make your own backups or scratch '
              'directories. In particular, do not use tempfile.mkdtemp or TemporaryDirectory during '
              'worker execution: their private-directory ACLs can deny subsequent Windows sandbox '
              'writes. Edit the declared source files directly; use host snapshots for diffs. '
              'One worker only: no child agents, CLI workers, plugins/MCP, network services, installation, '
              'game/save writes, physics, git reset/commit/push, or permission changes. Preserve unrelated '
              'local work and old evidence. Never edit the queue, runner, acceptance commands, execution '
              'limits, .task_batch, or instruction files. If permission/auth/usage is blocked, stop and '
              'report BLOCKED with the reason. Tests/logs may create new .local_checks files or '
              '.local_runs/batch_* files only; never modify old evidence. The runner independently runs '
              'acceptance after you exit; do not duplicate the queued acceptance commands in the worker. '
              'Update the short STATE.md, recording actual checks only and marking runner checks pending. Stop '
              'after this task; no next-task work.\n')
    if repair:
        header += 'One authorized recovery invocation, same session. Failure summary: ' + repair[:1500] + '\n'
    if sources:
        header += 'Read-only original source snapshots: ' + str(sources) + '\n'
    return header + '\nTask card:\n' + json.dumps(task, indent=2) + '\nShort state:\n' + state


def run_batch(root, queue, limits, executable, *, launch=process, authenticate=True):
    """No retries on restart: only this live invocation can spend its one repair."""
    root = root.resolve()
    control = root / CONTROL
    control.mkdir(exist_ok=True)
    lock = control / 'lock'
    try:
        with lock.open('x') as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        raise Stop('batch locked; possible interruption or another runner; manual reconciliation required')
    journal_path = control / 'state.json'
    journal = None
    try:
        seal = {'queue': queue, 'limits': limits, 'instructions': instructions(root),
                'runner_sha256': digest(Path(__file__)), 'python': sys.executable,
                'codex': executable}
        if journal_path.exists():
            journal = json.loads(journal_path.read_text(encoding='utf-8'))
            if journal['seal'] != seal:
                changed = ', '.join(k for k in seal if journal['seal'].get(k) != seal[k])
                raise Stop('approved scope, limits, environment or instructions changed (' + changed +
                           '); manual reconciliation required')
            if journal['phase'] != 'idle':
                raise Stop('unfinished/stopped task requires manual reconciliation; it is not known to be running')
            if (journal['completed'] != [t['id'] for t in queue['tasks'][:len(journal['completed'])]]
                    or len(journal['completed']) > len(queue['tasks'])
                    or not 0 <= journal['invocations'] <= limits['invocations']):
                raise Stop('invalid durable task record; manual reconciliation required')
            if snapshot(root) != journal['checkpoint']:
                raise Stop('workspace changed since checkpoint; manual reconciliation required')
        else:
            journal = dict(version=1, seal=seal, phase='idle', completed=[], invocations=0,
                           attempts=[], checkpoint=snapshot(root), baseline_tests=test_names(root))
            write_json(journal_path, journal)
        for task in queue['tasks'][len(journal['completed']):limits['tasks']]:
            if journal['invocations'] >= limits['invocations']:
                raise Stop('agent invocation limit reached')
            if snapshot(root) != journal['checkpoint']:
                raise Stop('workspace changed between tasks')
            before = journal['checkpoint']
            session = None
            repair = None
            first_attempt = 0
            pending = journal.get('reconciled_repair')
            if pending:
                # Only an explicit human reconciliation may create this record.
                # Normal reconciliation consumes the one repair. Only the user's
                # explicit L03 exception permits attempt 2; it cannot recur.
                previous = journal['attempts'][-1]
                extra = (task['id'] == 'L03' and previous['attempt'] == 1
                         and pending.get('approved_extra_attempt') == 2)
                if (pending.get('task') != task['id'] or previous['task'] != task['id']
                        or (previous['attempt'] != 0 and not extra)
                        or pending.get('session_id') != previous['session_id']
                        or not pending.get('reason')):
                    raise Stop('invalid reconciled repair; manual reconciliation required')
                session, repair = pending['session_id'], pending['reason']
                first_attempt = 2 if extra else 1
            for attempt in range(first_attempt, max(2, first_attempt + 1)):
                if journal['invocations'] >= limits['invocations']:
                    raise Stop('agent invocation limit reached')
                run = control / f"{task['id']}_{attempt}_{journal['invocations'] + 1}"
                run.mkdir()
                if authenticate:
                    preflight(executable, root, run)
                if attempt == 0:
                    (root / 'CURRENT_TASK.md').write_text('# Approved batch task\n\n' + json.dumps(task, indent=2) + '\n', encoding='utf-8')
                card_hash = digest(root / 'CURRENT_TASK.md')
                state = (root / 'STATE.md').read_text(encoding='utf-8')
                if len(state.encode('utf-8')) > 16000:
                    raise Stop('STATE.md exceeds short-state budget; compact manually')
                sources = source_snapshots(root, run, task)
                prompt = prompt_for(task, state, repair, sources)
                (run / 'prompt.txt').write_text(prompt, encoding='utf-8')
                command = codex_command(executable, root, session)
                write_json(run / 'command.json', command)
                journal.update(phase='invoking', task=task['id'])
                journal.pop('reconciled_repair', None)
                journal['invocations'] += 1
                write_json(journal_path, journal)  # Claim BEFORE launch; never repeat an uncertain attempt.
                journal_hash = digest(journal_path)
                code = launch(command, root, run, limits['timeout'], prompt)
                if digest(journal_path) != journal_hash:
                    raise Stop('worker changed runner journal')
                if instructions(root) != seal['instructions']:
                    raise Stop('instruction/configuration scope changed')
                after = snapshot(root)
                allowed = set(task['write_files']) | {'CURRENT_TASK.md'}
                violations = scope_changes(before, after, allowed)
                if violations:
                    write_json(run / 'scope_violations.json', violations)
                    raise Stop('out-of-scope changes; see scope_violations.json; no automatic rollback')
                if after.get('CURRENT_TASK.md') != card_hash:
                    raise Stop('worker changed approved task card')
                if not set(journal['baseline_tests']) <= set(test_names(root)):
                    raise Stop('worker removed existing acceptance cases')
                sessions, usage, errors, completed = worker_events(run)
                if len(sessions) != 1 or (session is not None and sessions != {session}):
                    raise Stop('missing or inconsistent exact session ID; no repair')
                session = next(iter(sessions))
                if any(a['session_id'] == session and a['task'] != task['id'] for a in journal['attempts']):
                    raise Stop('new task reused a previous session; no repair')
                entry = dict(task=task['id'], attempt=attempt, session_id=session,
                             exit_code=code, usage_events=usage or None, log=str(run.relative_to(root)))
                journal['attempts'].append(entry)
                journal['phase'] = 'checking'
                write_json(journal_path, journal)
                checking_hash = digest(journal_path)
                stderr = (run / 'stderr.log').read_text(encoding='utf-8')
                if FATAL.search(stderr + '\n'.join(errors)):
                    detail = errors[-1] if errors else stderr
                    raise Stop('permission/authentication/usage-limit problem; no repair: ' + detail[:300])
                # A worker narrative is never acceptance evidence.
                failures = []
                for index, acceptance in enumerate(task['acceptance']):
                    check = run / f'check_{index}'
                    check.mkdir()
                    check_command = [sys.executable, *acceptance[1:]]
                    result = launch(check_command, root, check, limits['check_timeout'])
                    if (scope_changes(before, snapshot(root), allowed)
                            or instructions(root) != seal['instructions']
                            or digest(root / 'CURRENT_TASK.md') != card_hash
                            or digest(journal_path) != checking_hash):
                        raise Stop('acceptance changed protected scope; manual reconciliation required')
                    output = (check / 'stdout.log').read_text(encoding='utf-8')
                    error = (check / 'stderr.log').read_text(encoding='utf-8')
                    if FATAL.search(error):
                        raise Stop('acceptance permission/authentication problem; no repair')
                    try:
                        record = json.loads(output)
                    except ValueError:
                        record = {'status': 'invalid_check_output'}
                    if record.get('status') in ('timeout', 'runner_error'):
                        raise Stop('acceptance infrastructure failure; inspect ' + str(check))
                    minimum = max(1, len(journal['baseline_tests'])) if 'application' in acceptance else 1
                    if result or record.get('status') != 'passed' or record.get('tests_run', 1) < minimum:
                        failures.append({'command': acceptance, 'status': record.get('status'),
                                         'first_issues': record.get('first_issues', [])[:3], 'log': str(check.relative_to(root))})
                violations = scope_changes(before, snapshot(root), allowed)
                if (violations or instructions(root) != seal['instructions']
                        or digest(root / 'CURRENT_TASK.md') != card_hash):
                    raise Stop('acceptance changed protected scope; manual reconciliation required')
                if not code and completed and not errors and not failures:
                    journal['completed'].append(task['id'])
                    journal.update(phase='idle', checkpoint=snapshot(root))
                    write_json(journal_path, journal)
                    print(json.dumps({'status': 'completed', 'task': task['id'], 'invocations': journal['invocations']}))
                    break
                repair = json.dumps({'worker_exit': code, 'worker_errors': errors[:1], 'checks': failures})
                if attempt:
                    raise Stop('unrepaired task failure; no further invocations')
        return {'status': 'queue_exhausted' if len(journal['completed']) == len(queue['tasks']) else 'task_limit_reached',
                'completed': journal['completed'], 'invocations': journal['invocations'], 'record': str(journal_path)}
    except BaseException as exc:
        if journal is not None:
            journal['phase'] = 'stopped_requires_reconciliation'
            journal['stop_reason'] = str(exc)[:1000]
            write_json(journal_path, journal)
        raise
    finally:
        lock.unlink(missing_ok=True)


def acceptance(task):
    """Frozen smoke checks supplement worker-editable application tests."""
    import contextlib
    import io
    base = ROOT / '.local_runs' / ('batch_acceptance_' + uuid.uuid4().hex)
    base.mkdir(parents=True)
    fixture = ROOT / 'proof/corridor_fixtures/release.json'

    def cli(*args, ok=True):
        p = subprocess.run([sys.executable, str(ROOT / 'bridge_cli.py'), *map(str, args)],
                           cwd=ROOT, capture_output=True, timeout=45)
        assert (p.returncode == 0) == ok, p.stderr.decode(errors='replace')
        assert len(p.stdout) <= 4096
        result = json.loads(p.stdout)
        assert result['game_constructed'] is False
        return result

    for mock in (False, True):
        out = base / ('mock' if mock else 'design')
        result = cli('design', '--fixture', fixture, '--output', out, *(['--mock-execute'] if mock else []))
        assert result['status'] == ('mock_verified' if mock else 'design_ready')
        before = snapshot(out)
        assert cli('status', '--run', out)['status'] == result['status']
        assert cli('verify', '--run', out)['status'] == 'integrity_verified'
        assert snapshot(out) == before
        original = (out / 'candidate.json').read_bytes()
        (out / 'candidate.json').write_bytes(b'corrupt')
        changed = snapshot(out)
        failure = cli('verify', '--run', out, ok=False)
        assert failure['status'] == 'integrity_failed' and 'candidate.json' in failure['changed_files']
        assert snapshot(out) == changed
        (out / 'candidate.json').unlink()
        assert 'candidate.json' in cli('verify', '--run', out, ok=False)['missing_files']
        (out / 'candidate.json').write_bytes(original)
        cli('design', '--fixture', fixture, '--output', out, ok=False)
        assert snapshot(out) == before
    legacy = base / 'legacy'
    legacy.mkdir()
    assert cli('verify', '--run', legacy, ok=False)['status'] == 'verification_unavailable'
    assert not list(legacy.iterdir())
    if task in ('L04', 'L05'):
        sys.path.insert(0, str(ROOT))
        import bridge_app
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = bridge_app.design(fixture, base / 'api', mock_execute=False)
            assert result['status'] == 'design_ready'
            assert bridge_app.status(base / 'api')['status'] == 'design_ready'
            assert bridge_app.verify(base / 'api')['status'] == 'integrity_verified'
        assert not stdout.getvalue()
    if task == 'L05':
        assert (ROOT / 'USAGE.md').stat().st_size > 100
    return {'status': 'passed', 'task': task, 'evidence': str(base)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--acceptance', choices=['L03', 'L04', 'L05'])
    parser.add_argument('--max-tasks', type=int, default=3, choices=range(1, 4))
    parser.add_argument('--max-invocations', type=int, default=6, choices=range(1, 7))
    parser.add_argument('--timeout', type=int, default=900, metavar='SECONDS')
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.timeout <= 3600:
            raise Stop('timeout must be finite, from 1 to 3600 seconds')
        if args.acceptance:
            result = acceptance(args.acceptance)
        else:
            if digest(ROOT / QUEUE) != APPROVED_QUEUE_SHA256:
                raise Stop('approved queue changed; review and approval required')
            queue = json.loads((ROOT / QUEUE).read_text(encoding='utf-8'))
            limits = {**LIMITS, 'tasks': args.max_tasks, 'invocations': args.max_invocations, 'timeout': args.timeout}
            executable = shutil.which('codex')
            if not executable:
                raise Stop('Codex CLI not installed/on PATH; no installation attempted')
            if args.dry_run:
                result = dict(status='dry_run', project=str(ROOT), limits=limits, tasks=queue['tasks'],
                              new_session=codex_command(executable, ROOT),
                              repair=codex_command(executable, ROOT, '<EXACT_SESSION_ID>'),
                              write_scope='task write_files; runner-owned CURRENT_TASK.md; new local evidence only',
                              model='existing CLI account/model settings; no override', hard_credit_cap=False)
            else:
                result = run_batch(ROOT, queue, limits, executable)
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        record = ROOT / CONTROL / 'state.json'
        log = None
        if record.is_file() and not args.dry_run:
            try:
                log = record.parent / 'runner_errors.log'
                with log.open('a', encoding='utf-8') as stream:
                    stream.write(traceback.format_exc() + '\n')
            except OSError:
                log = None
        print(json.dumps({'status': 'stopped', 'reason': str(exc)[:400],
                          'record': str(record) if record.is_file() else None,
                          'log': str(log) if log else None}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
