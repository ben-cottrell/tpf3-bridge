# Finite development batch

L02 passed before setup. `task_queue.json` contains the complete approved batch:
L03 integrity diagnostics (reuse L02 hashes), L04 a callable application interface,
and L05 combined acceptance and usage notes. Setup does not implement these tasks
or launch a real worker. All setup worker tests use a fake process.

From the extracted project directory, in a persistent local terminal:

```powershell
python tools/task_runner.py
```

Preview without creating a session or writing batch state:

```powershell
python tools/task_runner.py --dry-run
```

Defaults: one worker, three tasks, six total invocations including at most one
repair per task, 900 seconds per invocation, 240 seconds per acceptance command.
`--timeout 1800` selects a finite timeout (1–3600 seconds). `--max-tasks` (1–3)
and `--max-invocations` (1–6) may reduce the batch. Options are pinned on first run;
changing them after a checkpoint requires review, not an automatic restart.

Each task starts a new `codex exec --json` session. A single repair uses
`codex exec resume --json <exact-session-id>`, never `--last`. Existing CLI
ChatGPT authentication and model settings are retained. API-key environments
are rejected. Worker shell permissions use project workspace-write, no extra
writable roots, no network, and approval policy `never`; no bypass/full-access
flags, installations, or authentication changes. Explicitly configured MCP
servers are disabled for the invocation only. Parent instructions and rules
remain loaded. No nested workers are permitted.

The runner pins queue content, limits, instruction/configuration hashes, its own
code and a workspace checkpoint. It compares file hashes before advancement,
protects existing evidence/unrelated files, and refuses missing existing tests.
Task acceptance commands and runner smoke checks cannot be edited by workers.
These are detection/stop guards, not rollback or a separate security boundary
against a malicious process. Use the restricted worker sandbox; do not weaken it.

Full prompts, commands, JSONL events, stderr, check logs and usage events are in
`.task_batch/`; quiet checks also write `.local_checks/`. Smoke evidence goes to
new `.local_runs/batch_*` directories. Normal output is compact progress JSON.
The host prepares original source copies in each invocation's `sources/` folder.
Workers use those copies for diffs instead of creating backup/scratch directories:
Python private temporary-directory ACLs can fail inside the Windows sandbox.
Only actual CLI usage events are recorded; absent usage is null. Fake test usage
is test data. Invocation/time limits are not a hard token, credit or money cap.

Completion is saved atomically before proceeding. Re-running an exhausted batch
launches nothing. A lock, stopped record, unfinished invocation, changed scope,
or changed checkpoint stops immediately. Do not delete state to retry: that would
discard the completed-task ledger. For reconciliation, inspect `.task_batch/state.json`,
the exact session's logs and workspace diff; confirm no worker/descendant is alive,
then ask for an explicit reconciliation of that task and its acceptance evidence.
There is deliberately no automatic unlock, resume, rollback, queue expansion,
polling, daemon, scheduler, database or Git reset/push.

After an explicit human reconciliation, the journal may contain `reconciled_repair`.
It must identify the recorded task and its original session. The next manual run
consumes that task's single repair and retains the prior invocation count; it
does not restart the task in a new session or grant another repair. Workers must
not perform unscoped `git status` or inspect old check directories; the host
runner performs scope checks and independent acceptance. Config fingerprint
changes still stop the batch and require review.

The user has approved one exceptional third L03 invocation after the two
environment-blocked attempts. It is recorded explicitly in the journal, resumes
the original session, consumes the normal total budget, and allows no further L03
repair. The default policy for all other tasks is unchanged.

CLI invocation options follow the installed help and
[official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).
