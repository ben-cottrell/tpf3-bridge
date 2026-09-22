# State: v0.12 completed application and development batch

Current authoritative status: L06-L08 complete after user-approved L08 acceptance
reconciliation. All queued checks passed; three total worker invocations, no
repairs. Earlier preparation/worker-pending notes below are historical. Original
and pre-reconciliation ledgers/logs are preserved. No remaining batch blocker.

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
with five invocations used. That approved queue is exhausted.
The exceptional third L03 invocation was separately user-approved.

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

## Next batch prepared: connection-l06-l08
The user approved minimal named-batch support after the missing mechanism was
reported. L06-L08 are prepared, not implemented or executed. Cards with exact
file scopes and commands are in `tools/task_queue_connection.json`. L06 validates
a local record using v0.12 Port/Vec3/frame/region conventions. L07 reuses planar
Bezier/Hermite primitives for a line or at most two joined quintic pieces, forward
span and relative end heading within +/-45 degrees, arbitrary map translation/
rotation, level and zero cant. L08 adds `bridge_app.connect` and CLI `connect`,
reusing atomic run records/status/verify. No game construction or adapter lowering.

Use `python tools/task_runner.py --batch connection-l06-l08 --dry-run`, then
`python tools/task_runner.py --batch connection-l06-l08` in a persistent terminal.
The new ledger is `.task_batch/connection-l06-l08/state.json`; it does not exist
until launch. The old queue/ledger are preserved. Named batch identity and queue
hash are pinned, with a shared lock and protected previous history. Rejected
fingerprint/restart checks do not rewrite journals. One worker, three tasks,
six invocations, one repair per task, 900-second invocation / 240-second check
limits and existing restricted CLI/auth/model settings remain unchanged.

Preparation changes: `tools/task_runner.py`, `tests/test_cli_batch.py`,
`tools/quiet_checks.py`, `tools/BATCH_RUNNER.md`, `CURRENT_TASK.md`, `STATE.md`;
new `tools/task_queue_connection.json` and frozen `tools/connection_acceptance.py`.
No application/geometry source or historical contract changes. Quiet checks gain
named focused suites and hashes for application/connection/runner source files.

Exact setup checks:
- `python tools/quiet_checks.py --suite batch_setup --label named_batch_setup`:
  33 passed, `.local_checks/named_batch_setup__1abv888/report.json` (development).
- `python tools/quiet_checks.py --suite application --label named_batch_acceptance`:
  67 passed, zero failures/errors/skips, including 36 fake-worker tests;
  `.local_checks/named_batch_acceptance_5opbnqa6/report.json` (final).
- `python tools/task_runner.py --batch connection-l06-l08 --dry-run`: passed;
  `.local_checks/connection_batch_dry_run.json`. No ledger/session created.
- Inline AST/queue/scope/ledger checks passed; `git diff --check` passed.

Previous-batch closeout: L03 application 53 passed; L04 application 59 passed;
L05 application 59 and corridor 100 passed; each task's frozen acceptance passed.
Exact commands, compact results and usage extraction are retained in
`.local_checks/l03_l05_closeout.json`. Application checks were rerun only because
runner/tests/quiet tooling changed. Historical geometry code is unchanged; no
redundant corridor rerun. The new queue schedules geometry/branch/application/
corridor regressions at the relevant future tasks.
The original ledger SHA-256 still matches closeout and retains five invocations.
Its old stop_reason is historical; completed tasks/final acceptance confirm success.

Reported usage-field sums (input / cached input / output tokens):
L03, 3 invocations: 684162 / 618880 / 7140;
L04, 1 invocation: 364786 / 326016 / 6325;
L05, 1 invocation: 318877 / 289536 / 3125.
These are emitted-field sums, not independently measured billing totals;
resumed-session accounting semantics are not inferred. Credits/cost and this
preparation session's actual usage are unavailable. No real workers launched.
No remaining preparation blockers. L06-L08 acceptance is pending actual execution.

## L06 worker implementation (host acceptance pending)
Implemented only connection input validation in `bridge_connection.py`, with
`validate_connection(record)` returning the equal record without mutation and
`load_connection(path)` rejecting malformed/duplicate/nonfinite JSON. Validation
uses the frozen fixture fields and Port/Vec3/frame/region conventions, with exact
level/zero-grade/zero-cant restrictions and 1e-9 unit-length roundoff tolerance.
Provenance lists remain separate caller-supplied metadata. Out-of-region endpoints
remain unchanged for L07 geometric checks. No shared schema/application changes.

Changed files: `bridge_connection.py`, `connection_example.json`,
`tests/test_connection_input.py`, `STATE.md`. Reviewed the scoped source additions
against host snapshots; no trailing whitespace in the three new source files.
Actual development check: `python -B -m unittest discover -s tests -p
test_connection_input.py -q` passed 9 tests, zero failures/errors/skips.
Supplied prior evidence was reused; queued acceptance was not run by this worker.
Pending host checks: `python tools/quiet_checks.py --suite connection_input
--label batch_l06_input` and `python tools/connection_acceptance.py --task L06`.
No implementation blockers. Actual worker usage is unavailable here; no cost or
credit estimate. L07/L08 remain unimplemented by this worker. Stop at L06.

## L07 worker implementation (host acceptance pending)
Implemented `fit_connection(record)` in `bridge_connection.py`: deterministic
29-candidate line/quintic/two-quintic enumeration, explicit midpoint grid, local
start-tangent frame with map rotation/translation, and complete per-candidate
returned evidence. Budget exhaustion always returns a null candidate, including
when an evaluated candidate passed. Distinct input/domain/check/search outcomes
are preserved. Acceptance uses derivative projection, endpoint and G2 join
checks, continuous control-hull subdivision containment, kernel curvature bounds
and flattened conservative length bounds. Constraints and input remain unchanged.
Kernel floating-point tolerances apply; this is not interval certification or a
global feasibility claim. Historical geometry and application modules are unchanged.

Changed files: `bridge_connection.py`, `tests/test_connection_geometry.py`,
`STATE.md`. Reviewed source diffs against the supplied read-only host snapshots.
Actual development checks:
- `python -B -m unittest discover -s tests -p test_connection_geometry.py -q`:
  initial 8 tests passed, zero failures/errors/skips.
- `python -B -m unittest discover -s tests -p 'test_connection_*.py' -q`:
  final 18 tests passed (9 input, 9 geometry), zero failures/errors/skips.
Tests independently evaluate Bernstein polynomials, derivatives and numerical
length witnesses; cover 30-degree headings, large translated/rotated coordinates,
map-spanning connections, joins, hull subdivision, bounds and partial budgets.
Supplied baseline evidence reused; all five queued L07 host acceptance checks
(connection_input, connection_geometry, frozen L07, geometry, branch) remain
pending and were not duplicated by this worker. No implementation blockers.
Actual worker usage is unavailable; no credit/cost estimate. Stopped at L07;
L08 integration remains pending.

## L08 worker integration (host acceptance pending)
Implemented only `bridge_app.connect(input_path, output)` and CLI `connect`,
reusing L06/L07 and atomic versioned run records. Complete passing fits return
`connection_ready`; invalid, unsupported, failed-check, complete-no-candidate,
budget-exhausted and interrupted states remain distinct. Saved input bytes,
geometry/checks, source hashes including loaded geometry helpers, provenance
categories and domain/scope stay in the existing artifact filenames. Status and
verify remain read-only and need no geometry/search imports. Output protection,
compact connection API/CLI summaries and `game_constructed:false` are preserved.
USAGE.md documents commands, supported domain, independent checks and limitations.

Changed files: `bridge_app.py`, `bridge_cli.py`, `tests/test_connection_app.py`,
`USAGE.md`, `STATE.md`. Reviewed explicit source diffs against the host snapshots;
source whitespace checks passed. Diff evidence:
`.local_checks/l08_scoped_diff_ac9a4e22441a46fd82c622a4f45ad1dd.patch`.

Actual development checks (zero failures/errors/skips):
- `python -B -m unittest discover -s tests -p test_connection_app.py -q`:
  initial 10 passed; final 12 passed after additional failure-path tests.
- Existing `test_cli.WrapperTests`: 3 passed through an inline unittest loader.
  Exact command and results are recorded in `.local_checks/l08_worker_checks_2e832bd8562e4c5890df7b3367a71e77.json`.
Supplied prior baseline evidence was reused. All eight queued L08 acceptance
commands remain pending for the host; this worker did not duplicate them.
New test evidence was retained under `.local_checks/connection_app_*`; old evidence
and unrelated work are unchanged. No implementation blockers. Actual worker usage
is unavailable; no credit/cost estimate. Stop at L08; no further task work.

## L08 acceptance recovery: reconciled complete
The stop was caused by tests/test_cli_batch.py's invalid-timeout test invoking
runner.main against the real ROOT. It appended expected timeout diagnostics to
the old `.task_batch/runner_errors.log`; the named batch correctly detected that
protected-history change. Only this test is fixed: patch ROOT to the fake project,
assert local error logging and unchanged fake journal. No guard is relaxed and
no application code, ledger or invocation counter was changed in recovery.

L08 connection input (9), geometry (9), application (12) and frozen L08 acceptance
had already passed. Saved input hashes differ only in the now-fixed runner test;
those connection checks are reused. Exact remaining commands/results:
- `python tools/quiet_checks.py --suite application --label l08_isolated_acceptance`:
  67 passed; `.local_checks/l08_isolated_acceptance_t9l_nor8/report.json`.
- `python tools/quiet_checks.py --suite geometry --label batch_l08_kernel`:
  118 passed; `.local_checks/batch_l08_kernel_4iz34c4o/report.json`.
- `python tools/quiet_checks.py --suite branch --label batch_l08_branch`:
  107 passed; `.local_checks/batch_l08_branch_eqmsjykw/report.json`.
- `python tools/quiet_checks.py --suite corridor --label batch_l08_corridor`:
  100 passed; `.local_checks/batch_l08_corridor_t1oyxgqk/report.json`.
All zero failures/errors/skips. Test diff reviewed; scoped git diff --check passed.
Compact cause/hash comparison: `.local_checks/l08_scope_diagnosis.json`.
Both ledgers and the old error log remained byte-identical throughout recovery
checks; the original diagnostic append is retained, not erased. L06/L07 remain
recorded completed; L08 acceptance passed and the user explicitly approved durable
completion reconciliation. Three worker invocations remain recorded; no recovery
worker was launched and no repair was consumed.
