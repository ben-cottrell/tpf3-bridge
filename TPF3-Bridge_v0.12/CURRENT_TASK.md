# Railway design procedure — foundation written (9 October 2026)

Current user direction: drive procedure development and suggest useful manually
built patterns. RAILWAY_DESIGN_PROCEDURE.md v0.1 defines spatial planning, native
trials, fitting versus redesign, family reviews and separate completion claims.
railway-design/SKILL.md is the repository-managed entry point loaded by AGENTS.md;
template, pattern cases, five regression cases and P75 retrospective support it.
Prospective effectiveness and independent regression replay are not yet demonstrated.

Next useful input: a compact three-track fan with approach direction and intended
connections identified, optionally a mirrored/tighter variation. Inspect and capture
that example, then plan a fresh variant. Existing evidence is sufficient to draft
the procedure; a new example is for evaluation, not an approval or prerequisite gate.
No live construction, worker dispatch, automation restart or remote push in this task.
P75 remains closed; its completed construction evidence follows.

# P75 — integrated junction and station services complete (9 October 2026)

Build40420, sessionpif_1791546949_22682802. All10 access movements/18 directed
infrastructure TRAIN paths and16 station terminal routes verify; four forbidden
fast/slow transfers absent. C slow crossovers and direct A common post-merge return
built; temporary reversing feeder/wrong return removed. D/E arrival signals fixed.
Slow69269 and direct67394/67414 made actual native round trips;5vehicles no_path=false,
three current depot routes verify. Four fast TRACK geometries unchanged.

Evidence root .local_runs/live_python_interface/p75/branch_coupled/turnarounds/:
HANDOFF.md,completion_result.json,restored03_infrastructure.json,
restored03_station.json,restored04_forbidden_transfers.json,roundtrip_observations.json,
depots_services_final_summary.json,C_accepted_terrain.json (80,min1,0belowfloor),
C_accepted_post_terrain_geometry_checks.json (28unchanged),actual_geometry.json
(287TRACKs),final_asbuilt_plan.png,final_asbuilt_profiles.png,checkpoint_complete.json.
Prior E96/min1.2000046 and mainline525/min1.1500015 sampled evidence reused.

423tests PASS evidence reused after158input hashes and Python3.14.7 matched:
python tools/quiet_checks.py --suite live_client --label p75-bridge-junction-support
.local_checks/p75-bridge-junction-support_pskbjtzj/report.json;test_evidence_reuse.json.
Exact structured-junction read-only reconciliation/bridge splits/grouped pair support
in bridge_live.py,pif_native.lua,tests/test_live_client.py. Diff reviewed.
Unique TPF3_P75_Complete_Operating_20261009.sav saved43146578bytes,
SHA256c51dd06f0748d99b86544a8cdab34b96ba5dbadf45ddcee7d0c694d3ac4a51ba;
not reloaded. Prior0583d5c and old checkpoints retained; local completion revision in
completion_result.json. Healthy paused2099x1284 non-maximised game.

Limits:69270 stale home68943 remains but service functions; alternatives configured,
not claimed observed under contention; sampled terrain/clearance only, no capacity,
physics or whole-map audit. Lua standalone syntax unverified; native loaded on40420.
No remaining acceptance blocker or pending user approval; no host repair or remote push.
Stop at P75 completion; no unsolicited next task. Actual usage unavailable.
