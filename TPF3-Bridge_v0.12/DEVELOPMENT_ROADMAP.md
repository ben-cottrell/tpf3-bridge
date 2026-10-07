# Development roadmap

Updated 7 October 2026. Current priorities supplement the historical work packages
in implementation/work_packages.json; their old status labels are not a live
capability inventory. Completed native evidence is recorded in CURRENT_TASK.md.

## Completed baseline: Complex Junction construction

P60-P65 demonstrated native structure readback, new and replacement bridge/tunnel
chains, graded junctions, mixed free/interior attachments, fitting and collision
inspection. All 18 required directed native paths pass. This is a bridge capability
demonstrator, not accepted railway-design quality or observed train-operation proof.
The user's whole-layout review identified excessive detours, reverse curves and
fragmented related alignments. These are shortcomings of the design process.

## Railway-design agent exercise — captured and queued

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
not success. Skill implementation and redesign remain queued; this entry records
intent and does not dispatch them or mutate the current game.

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

## Next challenge: basic native station construction

User direction, 7 October: the current map lacks suitable platform stations for
non-branch services. Build this capability next, before extending representative
non-branch train operation. Existing named reference stations do not establish that
usable platforms exist for every intended track role.

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
remains a separate queued exercise. This documentation update selects the next
challenge; it does not claim an implementation or alter the current save.
