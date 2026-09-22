# Finite development batches

The original L03-L05 batch is complete. Its queue remains `tools/task_queue.json`
and its ledger/logs remain in `.task_batch/`. Do not delete or replace them.
The separately approved next batch is **connection-l06-l08**:
L06 connection input, L07 bounded endpoint fitting, L08 application integration.
Task cards, exact acceptance commands and permitted files are in
`tools/task_queue_connection.json`.

From this project directory in a persistent local terminal:

```powershell
python tools/task_runner.py --batch connection-l06-l08 --dry-run
python tools/task_runner.py --batch connection-l06-l08
```

Dry-run shows tasks, commands, write scope, limits and the selected ledger; it
launches nothing and writes no state. The launch creates the distinct ledger
`.task_batch/connection-l06-l08/state.json` only after confirming the predecessor
completed. A shared `.task_batch/lock` prevents overlapping batches. Prior ledger
and log bytes are included in the new batch's protected workspace checkpoint.
No old fingerprint is overwritten or ignored to resume the old batch. The new
batch takes its own initial workspace checkpoint and seals its own queue/identity.
The default command still selects the old queue; it does not start new work.
Old runner fingerprints may now reject a restart; that rejection preserves the
ledger and is not an instruction to reconcile or clear the completed batch.

Batch identities are explicitly registered with a fixed queue SHA-256 in the
runner. There is no arbitrary queue/path or automatic next-batch discovery.
Another future identity requires explicit approval; changing an existing identity,
queue, runner, limits, instructions or checkpoint stops it for reconciliation.
Do not modify these files after launching a batch.

Defaults remain one worker, three tasks, six total invocations, one repair per
task, 900 seconds per invocation and 240 seconds per acceptance command.
`--timeout` accepts 1-3600 seconds; `--max-tasks` 1-3 and `--max-invocations` 1-6.
Settings are pinned on first launch. No limit is increased automatically.
Each task starts a new session; a repair resumes its exact session ID, never
`--last`. The separately approved historical third L03 invocation is not a
new-batch allowance. Unknown usage remains unknown; limits are not credit caps.

Existing CLI ChatGPT authentication/model settings and parent instructions remain
in force. Workspace-write stays restricted to the project, with network disabled,
no extra writable roots and approval policy never. No full-access/bypass flags,
new dependencies, API billing switch, authentication changes, game/save writes,
nested workers, automatic push or destructive Git reset. Worker invocations keep
configured MCP servers disabled. Startup checks CLI authentication and supported
non-interactive execution without installing or repairing the environment.

Full commands, prompts, source snapshots, JSONL output and usage events stay under
the selected batch directory. Quiet check logs go to `.local_checks`; independent
connection acceptance evidence goes to new `.local_runs/batch_connection_*`
folders. Worker narratives are not acceptance. The host runs task commands after
exit and checks protected files, test names, instruction hashes and the journal
before advancement. Frozen `tools/connection_acceptance.py` checks L06-L08;
workers cannot edit it, the quiet runner, queue or batch runner.

Workers use host source snapshots for diffs. They must not create private Python
temporary directories or inspect old evidence; Windows sandbox ACLs can deny
those paths. Host tests use ordinary local directories outside the worker sandbox.
All setup worker tests are fake processes and consume no model calls.

Completion is atomic. An unchanged exhausted batch launches nothing. Interrupted,
stopped, locked or changed records require manual reconciliation; they do not
prove a worker is still running. Confirm no worker/descendant is alive and inspect
the relevant ledger/evidence before explicitly reconciling. Never delete state
or reset counters to retry. At most one same-session repair is available for each
new task. There is no automatic resume, polling, daemon, scheduler or rollback.
The guards detect changes; they are not a separate security boundary against a
malicious process.
