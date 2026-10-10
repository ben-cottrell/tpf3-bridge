# Development roadmap

Updated 10 October 2026. Current priorities supplement the historical work packages
in implementation/work_packages.json; their old status labels are not a live
capability inventory. Completed native evidence is recorded in CURRENT_TASK.md.

## User-accepted — integrated Mid West C district

10 October: reusable additions since Challenge03 are consolidated in
[BRIDGE_OPERATOR.md](BRIDGE_OPERATOR.md): fresh station roles/exits, connected
terminal route review across registries, scoped identity/frozen observations,
named operating tasks, explicit plain-track coalescing and read-only reconciliation
of built replacements. Commands remain in OPERATOR_USAGE.md. Specific native
coalescing/crossover and station-extension cases are demonstrated; these do not
establish general layout reliability or whole-district service completion.

Signal direction inversion is corrected in279da44. Public `forward=true` means
node0→node1 travel; native `left=not forward`, with readback reversed bit equal to
`forward`. On build40420, after normal reload, the isolated required-edge test
allowed north and rejected south;24 district replacements have functional readback.
Evidence: `.local_runs/operator/district04/signal-direction-corrected-proof.json`
and `signals-R6-results.json` in that directory. Placement verifies orientation,
not the intended running path: exact corridor/direction checks and observed service
operation remain separate. Earlier opposite-direction receipts remain historical.

District04 is now user-accepted: all 36 directed station routes use the
intended running roads; six trains demonstrate regional, stopping, Cross and express
return sequences. Passenger loading repair e0e890c is natively qualified on all 14
stops, with cleared UI warnings. Latest affected checks: 67 operator / 434 shared.
Final save: Design Challenge 04 - Mid West C Ready for Review.sav.

Procedure 0.5 adds actual station/depot envelopes, explicit world-frame operating
directions, turnouts before signals, intended-road checks and native loading state.
The original district corridors survived; one avoidable depot-footprint omission
required local southern bypass widening. The user accepts the result and requests only future refinements. Keep accepted
Challenge01–04 and their evidence.
Next scope follows review; do not automatically launch a whole-map build.

### Forward work from accepted user review

Keep Challenge04 unchanged. Procedure0.6 and the handbook capture urban reservations,
narrow six-track approaches, compact slow fans, smooth adjacent flyover curves,
30 m straight platform leads and ordinary open-line signals around 300 m apart.
Real-map starting targets are flyovers around 1.2 km and regional branches around
3 km from hubs, with 15–20 km hub spacing on the 48 km map. Define station datums
and survey the actual site before converting this guidance into a build plan.

Worthwhile operator follow-ups for the next authorised build are reusable along-track
signal distribution that preserves station decision zones, and compact native curve
speed readback if the current interface cannot expose it. Inventory existing support
first; these are opportunities, not diagnosed defects or an implementation dispatch.
No rebuild, new capacity study or whole-map construction begins from this review.

## Completed baseline — graded operator and shallow flying junction

10 October: Challenge02 accepted by the user. OPERATOR-GRADE-02 and Challenge03
are complete for final visual review: four directed paths, short level12° bridge,
earth-supported approaches.38 operator and423 shared tests pass; native result in
railway-design/examples/challenge03/DESIGN.md. Earlier accepted cases remain intact.
Grade/profile plans, exact removal, grouped structures, bounded fitting, remaining-work
continuation, partial review and a freestanding structure seed are reusable now.

Next decisions should follow visual review. A concrete operator follow-up is replacing
opaque attachment failure with clear endpoint/interior eligibility diagnostics and
reviewing the existing5–95% adapter restriction against native behaviour; do not call
it a game limit. Bounded numeric terrain editing remains an actual capability gap,
but was unnecessary for this earth-ramp case. Broaden spatial design variation after
review; repeating the same flyover is not proof of general design competence.

## Earlier milestone — operator efficiency and second transfer case

9 October: Challenge01 was visually accepted by the user. Its original plan and
handbook remain the baseline. OPERATOR-01 now provides reusable named data plans,
local stdio MCP, native first-track/camera/capture/save and compact diagnostics.
No FastAPI listener or additional model loop.18 focused operator tests and423
live-client regressions pass. See OPERATOR_USAGE.md.

Challenge02 broadens the accepted exercise to six oblique receiving leads and
nested three-exit fans.12/12 directed paths pass, final native view reviewed by
designer, saved for user review. Zero bespoke operating scripts or Computer Use
actions were needed for this case. Original spatial arrangement survived local
native fitting without demolition. See railway-design/examples/challenge02/DESIGN.md.
No general design reliability or measured token-saving percentage is claimed.
Broader future variation should test different corridor/topology constraints after
this visual review, rather than repeat copies of the same successful family.

## Completed baseline: Complex Junction construction

P60-P65 demonstrated native structure readback, new and replacement bridge/tunnel
chains, graded junctions, mixed free/interior attachments, fitting and collision
inspection. All 18 required directed native paths pass. This is a bridge capability
demonstrator, not accepted railway-design quality or observed train-operation proof.
The user's whole-layout review identified excessive detours, reverse curves and
fragmented related alignments. These are shortcomings of the design process.

## Railway-design agent exercise — active

9 October: user authorises coordinator-led development of the design procedure,
including suggestions for manually built reference patterns. Version 0.1 is now in
[RAILWAY_DESIGN_PROCEDURE.md](RAILWAY_DESIGN_PROCEDURE.md), with a repository-managed
[skill entry point](railway-design/SKILL.md) explicitly loaded through AGENTS.md,
one design-record template, contextual patterns, five regression cases and a P75
retrospective. It is not installed as a personal skill. These documents establish
the workflow; independent replay and prospective design transfer remain untested.

Shefford reference now captured: two user-built staggered fans, 29 native tracks,
four junction nodes and six verified directional paths. Version 0.2 incorporates
two ordinary turnouts and an early middle branch from the outer sweep. Scaled plan,
geometry and limitations: railway-design/examples/SHEFFORD_FANS.md.
User clarifies the10/15offsets allow a5-wide platform; track-only5/10 is also useful.
The user subsequently supplied both5/10variants; four complete fans/12current routes
are now captured in railway-design/examples/SHEFFORD_TRACK_ONLY.md. This is reference
evidence, not agent-designed transfer. Procedurev0.3 proposes CHALLENGE_01.md: an
oblique2-to4terminal throat with full arrival/return access and a saved pre-fit plan,
followed by a changed receiving condition. No new layout is built by this proposal.
The current game layout remains unchanged. No new junction rebuild, worker dispatch
or scheduler restart follows from writing the procedure. P75 is a functional
baseline and a design counterexample, not the aesthetic target for regression.

User requested this separate exercise be added to the roadmap on 6 October 2026.
Purpose: reliably create coherent, compact game-appropriate railways through the
bridge, without repeated user correction of the same design mistakes.

Deliverables:
- One principal railway-design SKILL.md supported by RAILWAY_DESIGN_GUIDE.md.
  Do not multiply agents or skills before a demonstrated need.
- A pattern library of successful game-built fans, crossovers, flying junctions
  and tunnel approaches, including context, trade-offs and known failures.
  Example dimensions are observations, not universal rules.
- A small set of design challenges, including unfamiliar combinations, with
  separate assessments of construction, connectivity, operation and design quality.
- A whole-layout redesign of Complex Junction as a candidate first exercise,
  preserving its completed save as the capability demonstrator.

Required design practice:
1. Survey actual game geometry and express the required movements and track roles.
2. Compare plausible overall arrangements before building. Choose shared corridors,
   junction order, crossing relationships and broad vertical profiles together.
3. Establish the most constraining geometry first and reserve room for the rest.
4. Review the complete layout visually during construction for avoidable detours,
   reverse curves, inconsistent paired alignments and footprint growth.
5. Replan the affected group when local fixes damage the whole. Earlier accepted
   construction is expendable; it is not automatically a design constraint.
6. Use game-native acceptance and fitting without substituting them for design
   judgment. Exceptions to patterns need contextual reasoning, not blanket bans.

Acceptance: an improved overall plan visible before construction and a coherent
built result with less repeated human intervention. A longer handbook alone is
not success. On 7 October the user authorised coordinator-led improvement of the
completed junction. P74 surveyed the current geometry; P75 begins the first
integrated redesign of the four C connections and affected trunk crossings.
Astra's first replacement concept retained an awkward slow-return bend around
branch structures. The user corrected this priority before construction: establish
the A–B/C mainline split first, then relocate the D/E connections and crossings
around it. The existing return loops are observed design defects; the revised
mainline-first arrangement was subsequently built and the P75 redesign completed
on9October. The early UP(slow) fork compacted the central crossing; D/E access,
station turnarounds and services were rebuilt around it. Local milestone c64bea9
records18 infrastructure paths,16 station paths, four tested absent fast/slow
transfers, and observed slow/direct round trips. Final checkpoint:
`TPF3_P75_Complete_Operating_20261009.sav`. Evidence and limitations are in
`.local_runs/live_python_interface/p75/branch_coupled/turnarounds/HANDOFF.md`.

This completes the current redesign exercise, not the general railway-design
agent deliverable. Further work should turn the demonstrated practices into one
design skill and test transfer to a fresh challenge. P75 still required repeated
coordinator corrections of local fitting and turnout ordering; native acceptance
alone is not evidence that the design process is reliable or the footprint optimal.
Skills and reusable patterns should incorporate built outcomes and limitations,
rather than canonising a particular shape. Starting that next exercise is separate
from closing this requested redesign.

## Operating challenge — demonstrated baseline and remaining coverage

Build on WP-07 Practical signals and observation / WF-04 Signals and representative
passage. Challenge accepted by the user; native API availability remains to be
established. The clarification below supersedes historical waiting-clearance criteria
for this challenge.

Outcome: establish services over representative fast, slow, branch and direct D/E
routes on the current save; place and configure native signals and observe trains
traversing the selected routes. User accepted this challenge and clarified that
waiting trains obstructing junctions is a railway-design concern, not a bridge
acceptance criterion. Delegate signalling, reservations and routing to the game.

Capability sequence:
- Inspect native signals and support placement, orientation and removal with readback.
- Discover the native depot, vehicle and line operations needed to deploy and route
  a small set of test trains. Implement the minimal reusable operations required;
  report any actual unavailable API rather than inventing it.
- Observe train position, direction, assigned service and available movement/waiting
  state. Report unknown waiting causes when native telemetry does not explain them.
- Demonstrate service assignment and actual passage on representative routes.
  Do not require a conflicting-movement scenario, waiting-clearance audit or
  junction-efficiency assessment. Investigate concrete bridge command/readback
  failures; distinguish them from native operating behaviour and layout issues.

Evidence distinguishes native path availability from physical traversal. No general
capacity or deadlock-free claim, custom signalling simulator, detailed train physics,
or station expansion is implied. The final service brief determines necessary scope.

## Alternate-platform routing — accepted challenge extension

User explicitly includes native multiple-choice/alternate platforms in the operating
challenge. User reports that the final signal before a station is the decision point
for choosing an alternative to the primary platform. Treat this as the supplied
operating model; establish its actual native configuration and observed behaviour
without inventing API support.

- Select suitable existing station platforms and identify their exact native
  terminals, approach tracks and primary/alternative assignments.
- Add the station-approach crossovers needed to make the selected platforms
  reachable from the same approach. Plan the decision signal upstream of the
  divergence needed to reach either selected platform, so its position does not
  eliminate a choice. Use ordinary single crossovers where appropriate; station
  expansion is not implied.
- Expose native route/stop primary and alternative platform configuration with
  readback, alongside signal position and direction. Establish whether the API
  expresses these as terminals, platforms or another native identifier.
- Demonstrate a service using the configuration. Seek an observed native alternative
  selection in an ordinary scenario that makes it useful (for example, occupation
  of the primary platform), leaving the choice to the game. Report configuration,
  reachability and actual alternative use separately; configuration alone does not
  prove that an alternative was used. If native access is missing, report the concrete
  capability gap rather than substitute custom dispatch logic.
- This focused demonstration does not reinstate general waiting-clearance, blockage,
  capacity or deadlock audits. Ordinary waiting and queues are acceptable behaviour.

Directional UP/DOWN tracks normally start with one-way signal intent; deliberate
bidirectional sections require explicit treatment. The bridge applies and observes
native configuration; the design layer selects appropriate placement and direction.

## Subsequent candidates

- Expose further native signal or routing options when a concrete gameplay task
  needs them; traffic-layout optimisation belongs to the separate design exercise.
- Exercise save/load rediscovery during a useful operating workflow rather than as
  a separate repetitive construction validation campaign.

Select these by concrete gameplay outcomes. Do not launch all candidates as a batch.


## P66 operating milestone — observed 6 October 2026

Bridge purchase, service assignment and actual D/E travel demonstrated. Native
alternative selection at D observed: one train stopped at primary terminal0 while
a second arrived and stopped at alternative1; both manual holds then released.
UI depot/signal fixtures and the user's depot spur enabled the operating test;
At this historical milestone, bridge-native signal and depot construction were
unresolved. P71 and P72 below subsequently resolved those producer gaps.
Do not describe all representative route-operation coverage as complete. No need to repeat all route
combinations or add capacity/reservation audits. Preserve the successful fixture
and target remaining implementation work to concrete producer evidence.
Final save: TPF3_Complex_Junction_P66_AlternativePlatform_20261006.sav.
Local owned milestone commit880fdf8; 390 affected tests reused with matching hashes.
Evidence: .local_runs/live_python_interface/p66/alternative/HANDOFF.md.


## Existing-signal prerequisite — user direction7October

Proceed with an existing functional signal anywhere on the map as the technical
creation template. P71 demonstrated this mechanism using the actual native
edge-object construction resource and a new signal placeholder in a track proposal.
A template-free first signal remains unproven; an existing signal is the prerequisite.
Validate seed freshness and type, apply target position/direction explicitly, and
report existing_signal_required when no usable seed is found with honest discovery
coverage. Do not infer identical depot requirements. P70 recorded the initial gap;
P71 resolved it using the installed Auto Signals implementation as an API reference.


## P71/P72 completed construction capabilities — 7 October 2026

- P71 (`df96576`): reusable native signal placement from a discovered existing
  functional signal, explicit position/direction/one-way intent and native readback.
  E inbound one-way placement demonstrated before the platform choices. Other
  direction/type combinations are source-backed, not all demonstrated in game.
- P72 (`79cd4d1`): reusable native depot construction using processed construction
  parameters, plus exact depot/exit readback and a connected DS service approach.
  Native depot-to-platform path passes; physical dispatch from this depot is untested.
- P72 also rejects native collision errors even when critical=false and removes
  a redundant response-file replacement. The Windows denial's underlying cause
  remains unproved. Pending receipts were reconciled without replaying construction.
- 399 affected tests and 11 native route checks pass at P72. These complement P66
  actual D/E travel and observed alternative-platform use; they do not establish
  physical travel over every Complex Junction route.

Current useful checkpoint: `TPF3_Complex_Junction_P72_Service_Depot_20261007.sav`.
Usage: `implementation/live_python_interface/SIGNALS.md` and `DEPOTS.md`.
Detailed evidence remains in `.local_runs/live_python_interface/p71/` and `p72/`.
There is no current blocker. Existing capabilities do not need another general
validation campaign before progressing to a useful new construction challenge.

## P73 completed — basic native stations and representative services

User direction, 7 October: provide suitable basic native platforms for non-branch
services. P73 built dedicated two-track fast A/B terminals, four approach leads,
ordinary turnback crossovers and connected fast/slow service depots. Reusable
placement/configuration and exact station/group/terminal readback are implemented.
415 affected tests pass, including atomic-write contention handling; see
implementation/live_python_interface/STATIONS.md.

Fast A–B and slow A–C train travel and four loading stops demonstrated on build40408.
A new train physically dispatched from Depot68943 on D–E; P66 alternate-platform
evidence retained. Original storage failures preserved; replacement-only retry fix
and explicit old-read reconciliation permitted completion without native replay.
Final checkpoint: TPF3_Complex_Junction_P73_Operating_Complete_20261007.sav.
No capacity/reservation/whole-world guarantee. Source/result/checkpoint evidence in p73/.

Outcome: construct a simple native rail passenger station serving a selected
non-branch route, connect its native track interfaces to the railway, discover its
station/group/terminal identities and make it usable as a native service stop.
Survey current track roles and available station assets/templates first; select
placement, platform count, length and track arrangement from the intended service
and game capabilities. Do not assume a station-template API matches depot creation.
Preserve the intended distinction between stopping tracks and fast bypass tracks.

Implement only the reusable placement/configuration, connection and terminal
readback needed by that outcome. Use native construction and fitting. Demonstrate
actual station construction and connection; service configuration and a useful
arrival/departure can then close the operational loop when suitable rolling stock
and a second stop are available. Report these evidence levels separately.

Basic station construction is now in scope for this challenge. Detailed station
architecture, furniture/crowd modelling, broad station-modification support, road
network expansion and tycoon management are not implied. Railway-design skill work
remains a separate queued exercise. Do not dispatch it automatically from this
completed milestone. Detailed evidence and remaining limitations are in STATE.md and p73/.
