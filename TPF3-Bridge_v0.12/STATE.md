# Current state

## Current accepted rehearsal
Giganto1 is user-accepted. `Giganto1 Corridor Review Ready` completed, including
220 ordinary block signals and34 station/junction boundary signals (254 total).
All58 directed station/junction checks and24 corridor/handoff checks passed.
Native stopping line233671 is configured with verified readback; no train traversal
or contention-dependent alternate-platform use is claimed. No layout repair is requested.

## Accepted application
Challenge04 (Mid West C) is user-accepted; no rebuilding requested. Both station
approaches, station-reordering flyovers, regional branches and independent Cross
service are built, with seven destination stations, four depots and24 one-way signals.
All36 intended directed station routes cover the18 C platforms. Six representative
trains completed return sequences, including the four-stop express circuit. All14
service stops have verified passenger loading; line warnings cleared.

Accepted save: Design Challenge 04 - Mid West C Ready for Review.sav. Saved and
left paused; a final reload is not claimed. Accepted earlier design examples remain
reference material, not a task queue. Use the [handbook](RAILWAY_DESIGN_GUIDE.md) and
[procedure](RAILWAY_DESIGN_PROCEDURE.md) for current lessons.

## Implemented capabilities
Offline bridge_cli.py/bridge_app.py: design, single/pair connections, explicit mock
execution, saved-run status and integrity verification. Offline/mock results do not
claim game construction. Level/zero-cant connections and compatible parallel pairs
retain their existing bounded input/fitting domain.

Live bridge_live.py and the semantic mod: bounded native inspection/discovery,
fitting, exact attachment, graded connections, junctions, bridges/tunnels, explicit
replacement/removal, native path checks, basic stations, signals, depots and services.
bridge_operator.py provides named plans, fresh station/interface roles, scoped terminal
route review, cross-registry endpoints, coalescing, operating tasks, review/continuation,
camera/capture/save and existing local stdio integration. bridge_corridor.py adds
bounded authored multi-window corridor plans over the same operator primitives;
sparse track catalogue, point terrain reads, nearby fitting and signal-chain placement
are reusable. No route-design engine or exact native-geometry reconstruction is implied. Native signal direction and
passenger stop loading are corrected and qualified on build40420.

Working source and reusable tests are retained. Completed reports and activity logs
are not retained under the current policy.

## Limits and current decisions
Native path availability, train operation and design quality are distinct. Alternative
platforms are configured/reachable; forced occupied-platform choice was not tested for
this district. No passenger-demand, capacity, deadlock-free or general-version guarantee.
Save identity remains unestablished; sampled geometry is not continuous clearance proof.
Bounded numeric terrain editing is not implemented; native track terrain treatment is.
Detailed station internals and train-physics expansion remain deferred.

Future design guidance includes urban space reservations, coherent compact approaches,
speed/curve progression and sensible lead/signal placement. Handbook/procedure dimensions
are contextual guidance, not new universal engineering gates; speed estimates are unmeasured.

The baseline is published at7530353; approved completed-run cleanup is resolved.
Slice1 adds prepared bulk signal proposals over the existing adapter: exact seed,
session/input-bound one-use handle,16 edges/64 placements,16 objects per resulting
edge, full native functional/retention proof and one named-binding update per batch.
Sampled spacing phase survives chunks/exclusions; uncertain effects require existing
reconciliation with no replay or individual fallback. Compatibility mode is explicit
individual placement; new plans opt into batch mode. Coordinator qualified equivalent
~1.8km fixtures with20 functional signals each and directed/reverse-blocked routes.
The reusable bridge_signal_benchmark.py now exposes offline dry-run/plan/inspect
and one-attempt build/signal/qualify phases. It uses exact receipt topology,
independent equivalent sites, bounded1000-unit signal windows, sampled300-unit
phase and measured per-phase counters. Optional parallel_family:true fits one
reference per section and derives siblings at surveyed native spacing; default unchanged.

Qualified parallel-family source prepares ordered local normal_offset_from.group_index
derivatives for2/4-member families, preserves the external prepared_request contract,
inherits structures/shared vertical parameter, and uses native shared trackDistance.
Strict exact/free endpoints, spacing multiples, bounds and20 total segments remain.
Conversion is sampled XY, not continuous3D clearance proof. Coordinator qualified
both plain curved/graded2/4-road fixtures first try, including positive/negative
offsets +d/-d/+2d, exact group readback and compact/coherent visual arrangement.
Construction:49 requests/17 mutations each,24.452s/24.611s request wait.
No standalone Lua checker is installed.
Reusable fake Lua fixtures tests/native/test_signal_batch.lua and
tests/native/test_parallel_family.lua remain prepared, unexecuted.
Family fixture includes reordered successful receipts/exact recovery, stale
post-prepare geometry/incidence/spacing with zero submission and mixed
NORMAL/BRIDGE/NORMAL inheritance. Grouped committed readback now compares
classification/resource per exact intended segment. Parallel-family bridge/tunnel
qualification is unclaimed; demonstrated family scope is plain curves/grades.
Qualified named-road completion is optional/immutable within existing corridor runs.
Exact receipts recover roads; one phase-entry refresh and bounded chain checks
precede bulk signals. Original section envelope union remains binding; no general
construction-region increase. Chunk receipts and exact replacement bindings persist
before advance; completed child continuation does not replay unknown mutations.
Pending native journal blocks advancement/qualification, including counted clients;
default continuation consumes the immutable pending-child owner before other roads.
Only authored affected-road directed checks run. Existing benchmark optional
production_completion:true retains defaults. Coordinator demonstrated20 signals
in4 native batches:16 signal requests/4 mutations/8.282s request wait;8/8
directed/reverse-blocked checks took3.875s. Signal-phase baselines: window bulk
50 requests/10 mutations/25.609s; individual100/20/50.767s. Whole-road completion
is ~6x faster than individual in this measured signal phase only; no whole-map,
credit-saving, continuous clearance or train-traversal guarantee follows.
Affected quiet Python validation:576 distinct tests passed,0 failures/errors across
test_corridor_completion.py, test_parallel_family.py, test_corridor_operator.py, test_operator.py,
test_signal_batch.py, test_signal_benchmark.py and test_live_client.py.
Command: `.local_tools/operator312/Scripts/python.exe -` with unittest discovery
and TextTestRunner(stream=io.StringIO(),verbosity=0). Latest targeted33 pass:
test_corridor_completion.py, test_signal_benchmark.py, test_corridor_operator.py;
unchanged remaining-suite evidence is reused from the573-test combined check.
Python AST checks and git diff --check passed. Source checkpoint8b593ae is qualified
within the scope above. Baseline upstream remains7530353, with no new push.
Milestone complete; coordinator owns final save/minimal current state and completed
diagnostic cleanup.
See OPERATOR_USAGE.md for family/completion contracts and existing benchmark commands.
Detailed station internals and train physics remain deferred.

## Approach composition
Qualified on build40420 in session pif_1791837108_17074876, approach run
7c35e56939694be7. Operator/CLI approach-plan/build/continue/review compose at most8
ordered existing operator/corridor families with station exits/leads before ordinary
interfaces, exact exported receipt bindings, bounded local fitting, replacement
propagation, pending/session guards and affected-only named acceptance.
The seven-family station/fan/crossover/flyover example passed all13 check records,
including12 positive platform movements,3 wrong-way probes and sampled geometry.
All geometry used the first native fit; selected fan displacement was approximately
-0.1002 native units. Later whole-alignment review found an unwanted merge/ramp bow despite the shallow
deck; functional qualification did not establish whole-family design quality. No
train traversal, speed, continuous clearance or general-version guarantee follows.

Cached proofs cover every exported rail binding in explicitly declared check families,
actual route endpoints and scoped station identity. Old narrow proofs correctly
invalidated6 route checks while retaining7 geometry checks. Explicit continuation
performed no construction; fresh affected review passed6 checks with15 route requests.
It used116 requests,59.656s request wait/59.891s elapsed. Unchanged cached review ran0
checks/route requests:52 dependency requests (3 inspect,3 operating_inspect,45 discover,
1 station_lookup),26.5s wait/26.546s elapsed. Bounded Lua batch observation is a possible
future optimisation, not implemented or authorised by this completion.
Construction children used169 requests/84.842s wait; station bootstrap separately
used2/1.141s. Parent registry/refresh costs are excluded; these are not total build time.
The coordinator subsequently saved/reloaded; current session is pif_1791865071_25864.
Prior-session identities require current reacquisition, not blind replay. Current native
receipts remain functional review/reconciliation state.

Read-only station_leads reuses observed terminal ordering/grades and same-session exit
evidence. Required interior bindings constrain station routes; negative checks require
explicit native path absence. Partial continuation prunes consumed roles without replay.
Native IDs are recyclable: chronological per-command generations, qualified endpoint
aliases and receipt cursors preserve correspondence. Complete native incidence at an
exact node may be witnessed by a sibling edge; proximity never proves attachment.
Individual signal chains allow one_way:false; batch mode remains true-only.

Quiet affected validation:138 tests passed,0 failures/errors across test_approach.py,
test_operator.py, test_corridor_operator.py and test_signal_batch.py;33 approach tests.
Command: `.local_tools/operator312/Scripts/python.exe -`, unittest discovery for those
patterns with TextTestRunner(stream=io.StringIO(),verbosity=0). Both example JSONs parse;
the executable compiles to7 families/13 checks. AST and git diff --check passed.
Reuse valid unchanged-suite evidence from the605 combined check. No permanent reports.
Current contracts/examples are in OPERATOR_USAGE.md and railway-design/examples/.
This local qualification checkpoint follows2544725; upstream remains7530353, no push.
Functional composition is qualified; the resumed flyover design revision is coordinator-
owned. Saved-file integrity is separate from
native acceptance. Detailed station internals and train physics remain deferred.

## Combined design feedback
Offline Operator.render_approach / CLI approach-render combines selected named families,
supplied full controls and recorded exports into plan/profile SVGs with shared horizontal
scale, explicit evidence epochs, deck/ramp styles and signal/merge/interface markers.
Missing controls remain unavailable; no native queries, fit prediction or job mutation.
Procedure/guide/R6/R7 require independent designer/reviewer prebuild assessment at
material coupled changes; routine fitting remains deterministic without model gates.
A temporary horizontal landing about450 native units before the deck decoupled the
merge/ramp, producing a25 ->32.14 ->15 lateral bow. Native endpoint-cubic acceptance
is not whole-alignment fitting. No new exact geometry requirement follows.
Quiet affected checks:132 tests passed,0 failures/errors (8 renderer tests plus
approach/operator/corridor_operator). Command `.local_tools/operator312/Scripts/python.exe -`
with unittest discovery for test_approach_render.py, test_approach.py, test_operator.py,
test_corridor_operator.py and TextTestRunner(stream=io.StringIO(),verbosity=0).
AST and git diff --check pass. No native calls or live state rewrites by worker.
Exact-chain removal/replacement still reject tracks with objects. Approved narrow
signal removal now has Python prepare/execute/proof helpers and a prepared Lua
same-edge replacement with zero object additions, one-track/1..16 exact-signal limit,
session/hash one-use handle and fresh membership/revisions. Selected components
must disappear; retained IDs/category/params/resource/function, both nodes, geometry,
structure and PlayerOwned.player must match. Unknown effects stop without replay.
Primary installed declarations confirm Engine.Entity removal lists (api/type.d.tl2797)
and PlayerOwned.player (api/engine.d.tl855); existing signal_command supplies the
populated same-edge replacement/removal pattern. No speculative native API.
Final affected quiet checks:599 passed,0 failures/errors across test_signal_remove.py,
test_signal_batch.py, test_live_client.py, test_approach_render.py, test_approach.py,
test_operator.py and test_corridor_operator.py with the same quiet discovery command.
AST/diff checks pass. Renderer now uses numbered controls, a bounded off-track legend
and cropped canvases without changing scale. Optional tests/native/test_signal_remove.lua
is prepared, unexecuted: no installed Lua runtime/checker. Current native attempt in
session pif_1791870329_5284063 executed first removal but reported mutation_unverified:
getComponent on deleted edge60645 raised Invalid entity. No replay; second removal
unattempted. The source fix uses entityExists (installed engine.d.tl1723); getComponent
requires a live entity (1686-1690). Fake Lua reads now throw for deleted IDs, cover
recycled IDs and retain observation errors. Python code unchanged:599-test evidence
reused; current diff check passes, no Lua execution claim.
Original callback lost its raw native receipt and consumed preparation before failure.
Recovery decision: coordinator will reload the saved pre-mutation Efficiency1 baseline
with the fixed module and a fresh runtime/evidence directory, then verify all three
original signals and topology before a new prepared request. Restoration is not yet
observed here. Old c3061a pending journal/evidence remain untouched/unresolved; this
is baseline reset, not old-operation replay or fabricated historical reconciliation.
No general recovery framework or ownership assumption is added.
Worker performs no native observations, staging/reload, live state edits or push.
Worker renderer/procedure scope is offline; native snapshot/design/review/build belong
to the coordinator. No flyover repair or new-session native qualification is claimed here.

Keep only current context and state needed to reconcile uncertain live mutations. Temporary
diagnostics are removed after use; no permanent journals, audits, handoff archives or
completed-run logs. Do not erase pending operations to enable duplicate execution.
