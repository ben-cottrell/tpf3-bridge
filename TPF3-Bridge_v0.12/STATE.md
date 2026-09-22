# State: offline milestone closed; paused

L01-L14 are accepted. The approved queues remain exhausted; no new batch, worker,
polling or schedule is authorised. L09-L14 used six invocations and zero repairs.
Previous ledgers/logs/counts and local evidence are preserved.

## Revision and checkpoint
Git revision: `c1caceffff2f9a0caec1aa3c492b0def7564c560`.
Completed batch checkpoint: `.task_batch/pair-l09-l14/state.json` (`checkpoint`).
SHA-256 of that checkpoint's sorted compact JSON:
`8309937c427acf19f74b231a740e1b7b46e0c60c8405e15c3c231fa72cad0254`.
Current tested source hashes and Python/platform identity match the saved final
reports. Only STATE.md and CURRENT_TASK.md are changed for this closeout, left
uncommitted; no push or ledger/checkpoint rewrite. Documentation changes after
completion are expected checkpoint differences, not a reason to rearm a batch.

## Implemented commands and scope
- `python bridge_cli.py design --fixture FILE --output DIR [--mock-execute]`
- `python bridge_cli.py connect --input FILE --output DIR`
- `python bridge_cli.py connect-pair --input FILE --output DIR [--mock-execute --snapshot FILE]`
- `python bridge_cli.py status --run DIR`
- `python bridge_cli.py verify --run DIR`
Callable equivalents: bridge_app.design, connect, connect_pair, status and verify.
See USAGE.md for shipped examples and the implementation-to-test mapping.

Single connections support level, zero-cant geometry, positive forward span and
relative travel headings within +/-45 degrees, with overall translation/rotation.
Pairs require compatible parallel endpoint pairs, equal normal spacing, explicit
four-port pairing/directions and the same heading domain. Genuine normal offsets,
continuous conservative bounds and finite searches retain approximation limits.
Existing restricted corridor behaviour remains supported; no unrestricted routing.

## Accepted evidence (no rerun for closeout)
| Suite | Passed | Exact report path |
|---|---:|---|
| Pair combined | 53 | `.local_checks/batch_l14_pair_e3di3_kv/report.json` |
| Application | 73 | `.local_checks/batch_l14_cli_h2tulk1d/report.json` |
| Single input | 9 | `.local_checks/batch_l14_single_input_1_86u3iy/report.json` |
| Single geometry | 9 | `.local_checks/batch_l14_single_geom_prc_8har/report.json` |
| Single application | 12 | `.local_checks/batch_l14_single_app_3qss9ypy/report.json` |
| Geometry | 118 | `.local_checks/batch_l14_kernel_psl1_5no/report.json` |
| Corridor | 100 | `.local_checks/batch_l14_corridor_ncgfreg9/report.json` |
| Branch | 107 | `.local_checks/batch_l14_branch_v5nma0qr/report.json` |
All have zero failures/errors/skips. Independent L14 acceptance also passed:
`.local_runs/batch_pair_5ef4682fd126404ea379936e33ca3643/result.json`.
Exact commands and check outputs remain in the sealed queue and
`.task_batch/pair-l09-l14/L14_0_6/check_*/stdout.log`. No missing/stale evidence found.

## Limitations and next milestone
Physical plans, attachment IDs/assets and current-state geometry/connectivity/
direction/neighbour read-back are demonstrated only in an authored in-memory mock.
Same-instance repeat protection is not persistent/cross-process replay protection.
Saved-file integrity does not prove game construction or current native game state.
`game_constructed:false`; real assets, snapping, coordinates and API remain unprobed.

Next milestone: read-only native TPF3 probe, BLOCKED / NOT AUTHORISED TO RUN YET.
Blocker: a runnable local game and verified native API mapping. Resume only when
those are available and the user explicitly authorises a bounded read-only probe.
Reuse the existing adapter contract to identify actual game/mod build, loaded save,
coordinate mapping, and bounded terrain/track/available-asset coverage. No native
function names or TF2 compatibility are assumed. Raw results stay local; normal
output is limited to identities, coverage, counts and blockers. CURRENT_TASK.md
contains the brief boundary; no speculative mod or new implementation batch exists.
