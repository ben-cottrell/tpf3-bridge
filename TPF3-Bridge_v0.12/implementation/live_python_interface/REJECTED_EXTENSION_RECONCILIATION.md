# Explicitly rejected extension reconciliation

`bridge_live.reconcile_rejected_extension(client, original_discovery)` closes only
a current-session pending `extension` with `execute:true` and a correlated response
reporting `native_construction_rejected`, `native_command_success:false`, stage `build`.
Supply the saved current-session native discovery containing the exact original anchor.

The helper binds its edge/node and position to the rejected fit, then issues one small
native discovery around that anchor. Complete, untruncated incidence must establish
exactly the original TRACK at the unchanged endpoint, with no construction ownership.
The edge snapshot must still match. Missing, ambiguous, occupied, changed or unavailable
observations leave the pending operation unresolved. A concurrent pending/session change
also prevents reconciliation. No fit, construction command, deletion or replay is sent.

An unchanged free anchor proves the requested attached extension is absent. It does not
prove global rollback or absence of detached/orphaned objects, terrain changes or other
incidental effects. The durable reconciliation preserves the original failure, states
`other_effects:unknown` and `automatic_replay:false`, and records fresh observation IDs
before removing the pending entry. Existing mutation protection and other helpers remain
unchanged. The caller chooses any subsequent design operation separately.

P49 demonstrated this on build40408/sessionpif_1791139669_139218306 for rejected request
652b52b39bb249ca92dfa89a2f8ac07e, exact TRACK95451/node95449. Fresh discovery
f52da73a660e4df9be86cd50f33b8321 established complete incidence `[95451]`; pending cleared.
No construction, reload or save was performed. Detailed receipts remain local under
`.local_runs/live_python_interface/p49/` and the original session evidence directory.
