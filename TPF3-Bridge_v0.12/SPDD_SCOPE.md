## Functional railway equivalents - user clarification, 3 October 2026
Real-world research layouts are references for useful railway functions, not exact
replica requirements. User accepts reasonable equivalents within the game's bounds.
Prioritise intended approach/branch connections and supported native movements over
matching real-world dimensions, pointwork or specialised arrangements. Use practical
native alternatives when game limitations make literal reproduction unproductive;
report material differences or unsupported movements honestly rather than claiming
equivalence merely from visual similarity. Do not spend time chasing replica fidelity.
This guides current junction work and the proposed integrated multi-track throat
demonstrator; it does not add platform/station modelling or physical train-operation
proof. Convey at the next idle handoff; do not interrupt active P12.
## Junction and branching-route scope - user approval, 3 October 2026
User approved the proposed next capability, "junction construction and connecting
branching routes", with "I agree with your next step - continue with the same process".
Native junction/turnout construction and branching-route connection through the reusable
Python/mod interface are now authorised, including practical disposable-map construction,
clearance/terrain changes, routine fixes/tests/docs and local milestone commits. Continue
automated integrated handoffs; no per-API approval pauses. This supersedes earlier
endpoint-only/topology-expansion restrictions for this scope. Existing map-owner delegation
and external tool review apply. Stations, unrelated services and remote pushes remain
outside this task. Keep exact topology/path evidence distinct from physical train traversal.
## Explicit disposable-map ownership delegation - 3 October 2026
User directly approved the prepared P09 short approach fixture and approximately
1500-unit three-leg corridor experiment, including native attachment/TRAIN route checks,
after being told construction has no guaranteed rollback. Exact user statement:
"approved - to re-confirm, ALL forms of destruction, bulldozing, terrain manipulation etc are fine and lack of rollback is not a reason to block. I want you as the design/orchestrator agent to act as the owner and have final authority over these maps."
The design/orchestrator has delegated owner authority for in-game map decisions in this
work. Construction, demolition, bulldozing, terrain modification and incidental losses
are authorised; no per-action human permission or rollback prerequisite. This covers
map operations, not unrelated host/filesystem destruction. Report actual effects honestly
and inspect uncertain outcomes for engineering correctness. External tool review still
applies: present this direct user approval truthfully; do not bypass a denial.
## Integrated outcome scope - user direction, 3 October 2026
Prefer substantial end-to-end implementation tasks over one-API micro-tasks. Combine
endpoint discovery/selection, native curved and graded fitting, construction, attachment
and route verification in a useful connection workflow from a brief. Use documented,
low-uncertainty API capabilities together and validate the resulting outcome; each new
API call does not require a separate experiment or handoff. Narrow scope for concrete
failures, contradictory contracts or material uncertainty, not hypothetical risk.
Routine fixes and affected checks belong inside the same task. Group cleanup/local
commits around useful milestones. Preserve honest native evidence and existing product
boundaries. Finish current grade task uninterrupted, then use this integrated approach
for the longer practical connection; automated handoffs continue.
## Automated milestone commits - user instruction, 3 October 2026
At notable verified milestones, the coordinator should instruct the existing implementation
agent to clean up Git scope and make a local milestone commit, then continue approved
development automatically. No user pause or repeated approval is needed. Keep runtime
artifacts and raw evidence local and ignored; retain useful source, tests and concise docs.
This supersedes historical no-commit rules for milestone commits. Remote pushes require
applicable publication authority; no force push or history rewrite. Deliver this policy
at the next idle handoff without interrupting active implementation.
## Disposable-map testing clarification - 3 October 2026
User observes tests close to a city/existing infrastructure may be failing due to
obstructions. The entire game map is disposable; all destructive in-game actions
needed for these tests are permitted. Prefer ample clear land, relocate experiments
or clear obstructing city/track/road/other map objects rather than repeatedly diagnose
site-induced collisions as API defects. Distinguish an actual interface/geometry bug
from unsuitable test placement using practical evidence. This permission concerns
the game map, not unrelated host/filesystem destruction. No new approval needed for
relevant in-game clearance. Avoid spending time preserving incidental map objects.

## Live Python interface development - user resumption, 3 October 2026
User reports the last disposable save reloaded and authorises resumed development
and automated handoffs, with coordinator discretion over continuation, intervention,
model/reasoning and heartbeat timing. Current objective: a reusable Python-to-mod
request/response interface using demonstrated native fitting, construction and readback.
Relevant local communication implementation is now in scope, superseding earlier
source-only/no-IPC restrictions. Prefer existing capabilities and standard libraries;
no unrelated services, dependencies or host recovery. Disposable test-world construction,
normal simulation/save/load, mod staging and routine repairs remain authorised.
Do not stop for arbitrary slice quotas or repeated permission. Keep native-first mechanics,
proportionate verification and honest errors. The earlier pause is lifted.

## Adaptive implementation model authority - 2 October 2026
The user delegates model and reasoning selection to the coordinator. This supersedes
older instructions to preserve GPT-6.1 Sol / Medium. Reuse the same implementation
chat; choose settings for each authorised handoff without repeated permission.
Sol Medium is the default for integration; Sol Low or Luna may suit simple, isolated
mechanical work. Use Sol High or Astra Medium/High for difficult API/geometry diagnosis
or substantial design decisions, returning to lighter settings when justified.
Optimise completed correct work, elapsed time and actual usage when available; account
for retries and do not claim measured savings without data. Record a short rationale
when changing settings. This authority does not resume the user's requested pause.

## Current experimental policy — user correction, 2 October 2026
User: "Where have these additional gates, checks and blockers come from? It feels like
some unnecessary rules are being invented - nothing needs protecting". The game saves
and world used for this work are disposable tests. This instruction supersedes older
coordinator-imposed preservation gates, fixed load/repair/sample quotas and per-slice
permission stops for the authorised native track-layout experiments. Do not require
unchanged test-save hashes, protection of incidental test-world content, a ten-second
simulation cap, or another task card merely to fix a routine implementation error.
Normal test-world construction, simulation, save/load and relevant repairs may proceed
as needed toward the requested connection outcome. Use proportionate checks: correct
API use, whether the intended track was built and actually connected, and useful failure
diagnostics. Prefer practical experiments; speculative validation is not a prerequisite
unless a concrete issue makes it necessary. Keep useful logs/history without turning
preservation audits into acceptance gates. Report attempted versus verified results honestly.
Observe current state before repeating a command whose outcome is uncertain, to avoid
confusing the experiment. Stop unproductive repetition based on evidence, not arbitrary
quotas. Production identity/preview requirements are not experimental entry gates.
This does not authorise unrelated filesystem deletion, host recovery, commits or pushes.
External tool approval review still applies; never bypass a rejection. Supply actual user
scope and accurate action effects. Same implementation chat and automated handoffs continue.

# TPF3-Bridge — authoritative product boundary

This scope lock governs production and task adoption. It is not a new feature
queue, permission to deploy, or a replacement for task-specific evidence.

Authority, highest first:
1. Current explicit user/design-orchestrator instruction.
2. This document, SPDD_SCOPE.md.
3. NATIVE_FIRST_ARCHITECTURE.md.
4. CURRENT_TASK.md and applicable STATE.md.
5. Task-specific evidence/research.
6. Historical specifications, prototypes and tests.

A lower layer may clarify implementation details but cannot expand a higher-level
boundary. Resolve relevant conflicts within the named task; do not undertake a
repository-wide reconciliation. Historical material remains preserved unless a
separately adopted task requires changes.

## R — Requirements

TPF3-Bridge is a practical British-railway construction assistant for an
already-running, healthy Transport Fever 3 sandbox session. The intended world is
loaded; the semantic adapter and required local environment are available.

Astra/model supplies railway intent, material design choices and genuinely novel
decisions. Python supplies UK railway engineering, game-scale constraints, bounded
strategy/pattern selection, orchestration, engineering acceptance and bounded
repair. The semantic adapter supplies native capability translation, supported
commands, native identities, bounded observations and committed-state readback.

TPF3 owns detailed native geometric realisation, snapping, terrain treatment,
structure generation, native topology/pathfinding, reservation behaviour,
vehicle/passenger simulation, asset lifecycle and other native mechanics wherever
the released game provides adequate support. Unknown internal mechanics are not
an instruction to reproduce them in Python.

The target is a credible, functional British railway at TPF3 scale, not metre-for-
metre reconstruction of Britain. GPT/model usage efficiency is a first-class
project requirement in development and runtime. Preserve explicit user constraints;
distinguish them from project defaults and optional real-world references.

## E — Entities

Normal production reasoning uses bounded semantic project entities: construction
briefs, railway interfaces/attachments, explicit protections and required functions,
native proposal/operation handles, selected assets, relevant engineering
observations, committed results and acceptance results.

Do not create or maintain a complete duplicate model of the TPF3 world unless a
named task demonstrates its necessity for an approved outcome. Prefer semantic
summaries; request bounded geometry/state for relevant calculations. Keep raw native
diagnostics local to the specific adapter question. Inspection does not create a
preservation obligation or promote temporary identity to committed truth.

## A — Approach

Use native-tool-first construction. Investigate supported native workflows before
promoting custom geometry into live construction. Python need not calculate exact
curves, control handles, node positions, parallel offsets or terrain shaping when
TPF3 can satisfactorily determine them.

Python may calculate detailed geometry when a native operation requires it, a
relevant engineering requirement must be checked, meaningful alternatives must be
compared, or a demonstrated native gap requires a bounded fallback. Retain existing
geometry as engineering/regression/fallback material until native replacement is
demonstrated; do not remove it speculatively.

Accept realised geometry against relevant finished requirements rather than exact
equality with preliminary Python geometry. Correct connectivity and exact attachment
identity matter more than coordinate resemblance. Keep intended, preview and
committed evidence distinct; reacquire committed identity after native operations.
Do not globally relax tolerances or weaken genuine hard requirements.

Existing terrain slope is not automatically a blocker. Ordinary treatments include
native terrain modification, cutting, embankment, bridge/viaduct, tunnel and rerouting.
Engineering gradient/curvature/clearance and explicit protection remain constraints.
Terrain/civil estimates are lightweight diagnostics unless a demonstrated limitation
or explicit brief requires more. No implicit penalty for terrain change or treatment.

Use native asset/world dimensions. Coordinate/unit conversion is distinct from
geographic/gameplay compression; no universal real-world-to-game factor is assumed.
UK evidence informs functional topology, railway character, design families and
explicitly selected targets. Preserve train/platform/holding fit, routes, native
structures and selected limits; reassess curves/ramps after layout compression.

## S — Structure

Retain the chain: **Astra/model → Python engineering/orchestration → semantic native
adapter → TPF3**. The mod is technically capable but strategically a semantic
adapter, not a second planner. It maps canonical project identity to exact native
identity and load epoch where available; geometry verifies rather than invents identity.

The development runner is development tooling, not runtime game/OS supervision.
Keep existing completed batches and evidence intact. This scope lock creates no
new service, dependency, worker architecture or transport requirement.

## O — Operations

Each task has an explicit outcome, bounded source/compute/write budgets, named
acceptance evidence and clear stop conditions. Research findings, available APIs,
historical prototypes and old tests do not create implementation requirements.
Additional task families require explicit adoption/authority. Do not silently
continue from one completed task into another.

The target runtime loop is intent, deterministic design, native preview where
supported, engineering assessment, authority/checkpoint gate, native build, fresh
committed semantic readback, then acceptance or bounded railway repair/escalation.
Each operation needs its own applicable authority; research/preparation is not
construction authority. Checkpoint means a demonstrated recovery mechanism, never
assumed transaction/undo/rollback support.

## N — Norms

Before adding a production module, subsystem or acceptance gate, name the approved
railway-construction outcome requiring it, why TPF3/native behaviour or a simpler
check is insufficient, and its bounded success criterion. Ordinary implementation
decisions within an approved task remain autonomous.

Keep small task cards, exact pointers, short state and detailed local logs. Send
compact model-visible evidence and decision packets. Use deterministic local loops;
do not routinely invoke another model for geometry search, polling, ordinary
verification or repair. Record actual usage only when exposed; infer no credits
from time, words or invocation counts.

Reuse valid acceptance for unchanged inputs/environment. Historical tests enforcing
superseded requirements may be reclassified when the governing requirement changes;
do not weaken tests merely to obtain a pass. Saved-file integrity, engineering
acceptance and native committed-state acceptance are separate facts.

## S — Safeguards

Outside normal product responsibility are game/Steam launch or restart, crash
recovery, process/watchdog management, OS repair/reboot, filesystem/permission
repair, authentication repair, firewall/antivirus/network repair and mod/game
reinstall/update repair. Stop with a precise terminal blocker when an external
runtime precondition is unavailable; do not expand into environment management.
Ordinary save/load while the game remains healthy requires fresh world identity,
not host recovery. Persistence supports evidence/history and in-session semantic
reconciliation, not crash-resilient continuation across broken host environments.

Also excluded are universal map preservation, detailed station crowd/access/furniture
simulation, detailed traction/braking/adhesion simulation, a complete signalling/
reservation simulator, full civil/geotechnical/regulatory certification, reconstruction
of every internal engine mutation, open-ended autonomous map improvement, and
tycoon/fleet/revenue management.

Ordinary content inside the authorised project/effect region is redevelopable unless
explicitly protected or functionally required. Named protection tolerances and
required functions remain binding; incidental neighbours do not acquire protection
through inspection. No implicit demolition, vegetation, road, development or terrain
cost applies without an explicit preference. Authorised effects must remain inside
their scope. Verify requested infrastructure/functions, explicit protections and
named hard constraints, using final state where it can establish the required facts.

## User decision: investigate demonstrated problems (2 October 2026)
Trust native internal modelling unless a concrete failure, violated explicit
requirement or task-critical missing contract makes investigation necessary.
Unexplained implementation details alone do not justify repeated research or new
acceptance gates. The C13 approximately0.53 vertical difference is recorded as a
non-blocking observation, plausibly normal internal modelling; cause remains
unconfirmed. No correction, forced equality or further offset investigation unless
it manifests in a concrete downstream problem. Keep base attachment coordinates
and movement-path samples distinct. This decision does not fabricate native proof,
waive exact identity/freshness requirements or authorise construction.

## Development method preference — 2 October 2026
Prefer bounded practical experimentation when it can resolve a concrete uncertainty
more usefully than further speculative research. Preserve evidence and finite limits;
this preference alone grants no construction, expanded mutation or host recovery scope.

## Controlled development build authority — 2 October 2026
User approved one controlled isolated straight-track construction experiment in a
separate test save, after native fitting and source proposal assembly discovery.
Normal test-copy save/load and routine scoped fixes are authorised. C09 card bounds
location/effects/one submission/readback; no original-save overwrite, route expansion,
attachment milestone or host recovery. This test does not close production identity/
preview gates: retain those unknowns and use recorded controlled-test provenance.

## Automated connection handoffs — user clarification, 2 October 2026
The user clarified that the request for more automation means resuming coordinator-managed
handoffs, rather than pausing after each successful construction experiment. Continue
bounded practical steps toward the small native connection outcome in the owned test save,
starting with exact endpoint attachment to C09 track. Coordinator reviews each result and
may approve the next evidence-based finite card, including required controlled construction,
without repeated human permission. This supersedes C09-only and per-success pause wording
for subsequent cards; C09 historical limits/evidence remain unchanged. Never treat this as
open-ended map improvement or permission for unrelated milestones. Preserve original save,
all cumulative counts, failed/unknown outcomes and production identity/preview unknowns.
No retry of unknown mutation, host recovery, new services/dependencies or commit/push.
Escalate material effect/scope decisions, unavailable external prerequisites or an impasse;
notify meaningful progress. Stop the sequence at verified small-connection outcome for review.

## More ambitious native connection work — 2 October 2026
User requested moving beyond short straight track while keeping automated handoffs.
Proceed with native-fitted curved and multi-segment alignments, then useful connection
between verified test endpoints, in the owned test save. Coordinator scopes and reviews
finite practical slices autonomously, including necessary controlled builds. Retain
railway constraints, original-save protection, exact attachment/final-state checks,
all cumulative failures and unknowns; no host recovery or unrelated station/fleet work.
Do not pause merely because a straight attachment is demonstrated. Current C11 card
sets concrete curve test bounds; later justified cards must explicitly bound effects
and attempts before execution. No custom Python spline replacement by default.

## Test-save operational scope — user clarification 2 October 2026
After Resume was rejected for possible simulation advancement, the user said:
"the review seems too strict, the save games are only for testing". Together with the
prior direct "ok no need for my authorisation, continue", routine navigation and brief
simulation advancement needed for authorised experiments in the owned test save are
within task scope. Do not request human approval for each menu action. This does not
waive tool approval review, permit bypass, host recovery or original-save overwrite.
For the pending C13 Resume action, allow one resume/pause cycle with at most10seconds
advancement, pause promptly, observe actual state and recheck native construction
preconditions before the existing single build. Preserve both earlier rejections.
