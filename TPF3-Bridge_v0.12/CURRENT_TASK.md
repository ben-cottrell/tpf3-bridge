# Challenge 01 — built, ready for visual feedback (9 October 2026)

Fresh empty map, session pif_1791576336_52069880. Original oblique four-lead
fixture built unchanged from the pre-fit R1 plan: two single crossovers and two
fans, all eight directed native TRAIN paths pass. No rejected construction
proposals, rebuilds or material replans. No train-operation claim or bridge changes.
Designer considers the composition coherent; user visual feedback is pending.
Record and overlay: railway-design/examples/challenge01/DESIGN.md.
Save: Design Challenge 01 - Oblique Throat R1. Next useful exercise, after this
review, changes the receiving heading/offset materially. General reliability
remains unproved. Sol stays idle; automation remains paused; no remote push.

# Railway design procedure — both Shefford cross-sections captured (9 October 2026)

Two additional user-built5/10fans captured read-only, alongside the10/15pair.
Four full components,56TRACKcontrols,8junctions,4signals; all12current directional
paths pass. New pair's node gaps27.47/27.44; measured offsets5/10. No game mutation.
Reference: railway-design/examples/SHEFFORD_TRACK_ONLY.md and comparison data/plan.
Raw evidence: .local_runs/design/shefford_track_only/. Procedurev0.3.
User asks for a design test with meaningful variation. Proposed CHALLENGE_01.md:
oblique two-directional-track/four-terminal-lead throat, all8arrivals/returns,
with pre-fit spatial plan and later changed boundary condition. Brief only; not built.
Manual references are not evidence of agent transfer. No additional example requested
as a prerequisite; optional user contribution is unsolved boundary tracks or a site limit.

# Railway design procedure — Shefford reference captured (9 October 2026)

Read-only native survey of the user's two mirrored staggered fans near Shefford
Station complete, build40420/sessionpif_1791572697_48431435. 29 track controls,
two complete components, four junctions and restored one-way signals captured.
Six intended native TRAIN paths pass; no train traversal or construction performed.
Reference: railway-design/examples/SHEFFORD_FANS.md, JSON and scaled SVG/PNG.
Raw evidence: .local_runs/design/shefford_fans/. Procedure v0.2 incorporates the
early middle branch from the outer sweep; 27–28-unit observed spacing is not a limit.
User clarification:10/15 outlet offsets include a5-wide platform in the first gap.
Next: scaled plan for a track-only5/10-offset variant,
before fitting/building. Fresh-variant success and design regression prevention remain
unproved. Adapter access resolved after user activation; no current external blocker.

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
