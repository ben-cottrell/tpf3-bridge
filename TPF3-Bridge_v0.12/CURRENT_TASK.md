## Windows atomic-write retry — 7 October 2026

Implemented bounded retries of the same prepared JSON file replacement for Windows
errors5/32/33: at most6attempts with10/20/40/80/160ms delays (310ms total backoff).
Other errors fail immediately; persistent denial preserves the previous destination
and prepared temporary file. No native request or publication is retried by this fix.
415 affected tests pass, including post-publication journal contention without a
second mutation publication. Real single-writer stress completed10000writes while
recovering41transient denials; final contents verified. Exact OS actor remains unknown.
Evidence: .local_runs/write_error_diagnosis/fixed_stress_result.json and
.local_checks/windows-atomic-retry_v2zd9wia/report.json. No game commands issued in
this fix. P73 pending read still requires reconciliation before final observation.

# P73 blocked — stations built, operating acceptance incomplete

Authority: .local_runs/live_python_interface/p73/orchestrator/TASK.md.
Provide native fast A/B terminals outside the junction and a suitable slow-to-C
service; keep distinct fast/slow approaches and C fast bypass. Survey native
station modules and exact ports before building; record station/service plan.
Reuse P66 D/E travel/alternative-platform evidence and P72 depot/route baseline.
Normal staging/load/simulation and disposable-map construction authorised.
No process restart, host repair, new dependencies, runner change or remote push.

411 affected quiet tests pass; separate fast A/B terminals, four leads, turnback
crossovers, fast/slow depots and service assignment demonstrated on build40408.
Fast Train69268 travels A–B with exact B terminal1 stop; slow69269 travels A–C
with C terminal1 stop and A loading stop (arrival tuple unavailable). Train69270
physically dispatched from Depot68943 on D–E; P66 alternate-platform proof reused.
P73 is NOT complete: fast-A exact stop not yet captured. The finite observer twice
hit WinError5 replacing .local_runs/live_python_interface/p01/
pif_1791385541_13474088/client_state.json. Stop further bridge requests; no ACL/host
repair or alternate-path bypass. Pending READ a0a9edcef69948d6aa7e6f1bece95469,
sequence230, remains published; preserve and reconcile its existing response before
any continuation once local storage is functioning. Do not rebuild/rebuy/recreate
services or rerun unchanged tests. Evidence/results: .local_runs/live_python_interface/p73/.

# P72 complete — native depot and DS service connection

Authority: .local_runs/live_python_interface/p72/orchestrator/TASK.md.
Build40408: native processed-parameter construction created Depot68943 /
Construction68942; exact exit68944 connects to DS67047 through68962–68964.
Native Depot outNodes→D0 service route verified; required67386 retained.
All8 D/E terminal routes, both DS trunk directions and current D_in_near pass.
399 affected quiet checks and local evidence/diff checks pass.
Saved TPF3_Complex_Junction_P72_Service_Depot_20261007, paused/non-maximised.
No train dispatch/capacity proof, new services, process restart or host repair.
Original failures/unknown journals retained; no replay. Receipt duplicate-write
fix and exact successful-build reconciliation included; current pending none.
Evidence/checkpoint/commit: .local_runs/live_python_interface/p72/.
P72 accepted by coordinator; no current blocker or remote push.
