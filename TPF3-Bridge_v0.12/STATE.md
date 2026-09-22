# State: v0.12 completed application and development batch

## Completion and boundary
L01 complete: design-only CLI and explicit in-memory mock execution reuse the
existing corridor search. Nonempty output directories are protected; incomplete
searches never select or execute. Historical proof modules and evidence are unchanged.

L02 complete: atomic, versioned run metadata supports fresh-process, read-only
`status --run`. Missing/corrupt records are unavailable; unfinished records are
incomplete with process state unknown. No resume or repeated engine operation.

L03 complete: `verify --run` reports changed/missing artifacts and old records
without verification data honestly, without rewriting saved results.
L04 complete: `bridge_app.design`, `status`, and `verify` provide a callable API;
the CLI preserves compact JSON and exit behaviour.
L05 complete: combined acceptance passed and `USAGE.md` documents the behaviours
and limitations. The finite development runner records L03-L05 completed, idle,
with five invocations used. The approved queue is exhausted; no further task is
approved. The exceptional third L03 invocation was separately user-approved.

Normal stdout stays within the 4,096-byte JSON target. Geometry remains the
existing restricted synthetic-terrain model. Mock state is in memory only;
`game_constructed` remains false. No game/save edits, railway physics, new
dependencies or broad refactor. Fixture/API schema remains 0.9.0.

## Verification
L01 recorded acceptance: `python tools/quiet_checks.py --suite application
--label acceptance_cli` passed 11 tests; `python tools/quiet_checks.py --suite
corridor --label acceptance_corridor` passed 100.
L02 recorded acceptance: `python tools/quiet_checks.py --suite application
--label acceptance_l02` passed 20 tests; unchanged corridor evidence was reused.

Final host-owned L05 acceptance:

| Exact command | Result | Local evidence |
|---|---|---|
| `python tools/quiet_checks.py --suite application --label batch_l05` | 59 passed | `.local_checks/batch_l05_hcrpte41/report.json` |
| `python tools/quiet_checks.py --suite corridor --label batch_l05_corridor` | 100 passed | `.local_checks/batch_l05_corridor_mxsfcael/report.json` |
| `python tools/task_runner.py --acceptance L05` | passed | `.task_batch/L05_0_5/check_2/stdout.log` |

Both final suites had zero failures, errors or skips. For Git preparation,
all recorded input hashes and Python/platform identity were reconfirmed unchanged;
application, test and runner files also match the completed batch checkpoint.
Existing evidence was reused without redundant test or worker invocations.

## Files and local records
Deliverables: `bridge_cli.py`, `bridge_app.py`, `tests/test_cli.py`,
`tests/test_cli_batch.py`, `tools/task_runner.py`, `tools/task_queue.json`,
`tools/BATCH_RUNNER.md`, `USAGE.md`, `CURRENT_TASK.md`, and `STATE.md`.
Git preparation adds `.gitignore` and updates this completion record. Staging
excludes `.local_checks`, `.local_runs`, and `.task_batch`; their contents are
preserved on disk. Keep the durable batch ledger for restart/reconciliation.
Earlier detailed handoffs are preserved in `.local_checks/pre_git_STATE.md`.
Do not clear the ledger to rerun the completed batch. Post-batch documentation
changes are outside its saved checkpoint and may trigger its reconciliation guard.

Staged paths and diff were reviewed; `git diff --cached --check` passed.
No remaining implementation blockers. Actual setup-session usage is unavailable;
worker usage events, where emitted, remain in local batch logs. No credit estimate.
