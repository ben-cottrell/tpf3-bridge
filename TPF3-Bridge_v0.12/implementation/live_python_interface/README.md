# Live Python development interface

`bridge_live.py` supplies a standard-library callable/CLI boundary to an active
TPF3 development mod. Offline `bridge_cli.py` commands retain their original
design/mock meanings. No service, model call or UI action is needed per operation
once the mod and world are loaded.

## Activation

Copy the **contents** of `implementation/n01_probe/prepared_mod/` into the normal
TPF3 user staging directory under `tpf3_bridge_n01_c04_20261001`; `mod.json`,
`_metadata/` and `content/` must be directly beneath that mod folder. Enable
**TPF3 Bridge N01 Activation** when loading an authorised disposable test save
through the normal game UI. Do not edit base-game files. Normal save-load activation
is demonstrated; hot callback reload is not assumed.

The adapter can **construct railway** when explicitly requested. Its historical
N01 identity remains stable. The game must already be healthy and running;
the bridge does not launch/restart it or repair the environment. Staging location
and game `stdout.txt` vary: use actual user-data locations, not another account's path.

## Context and brief

Create local JSON files outside tracked source. Example `context.json`:

```json
{
  "mod_directory": "<actual staging directory>/tpf3_bridge_n01_c04_20261001",
  "log": "<actual user-data directory>/crash_dump/stdout.txt",
  "session_evidence_root": "<one shared local evidence root>"
}
```

Relative paths resolve beside the context file. Python discovers the latest READY
and matching SESSION handshake. This ephemeral token is transport identity, not a
save GUID/load epoch; a fresh operation establishes responsiveness. Use **one shared
journal root and one client** for the active adapter session.

```powershell
python bridge_live.py inspect --context context.json --params inspect.json
```

`inspect.json` contains `{"edge_ids":[<exact current TRACK edge ID>]}` from a
source-backed native observation. Proximity does not establish attachment identity.
Never reuse another world's recorded IDs.

An extension brief contains exactly:

```json
{
  "anchor_edge": 123,
  "anchor_node": 456,
  "end_xy": [100, 200],
  "end_direction": [1, 0],
  "radius": 100,
  "region": {"min": [0, 0, -20], "max": [300, 300, 20]}
}
```

These numbers illustrate the schema, not a valid construction target. Use freshly
inspected exact IDs, native coordinates and a deliberately selected brief. There
is no pixel conversion or universal real-world scale factor.

```powershell
python bridge_live.py extend --context context.json --params extension.json
python bridge_live.py extend --context context.json --params extension.json --execute
```

First command fits only. Second performs fresh inspection → native fit → explicit
build → fresh readback. Callable equivalents: `client_from_context(path)` and
`extend(client, brief, execute=False)`.

Native `findDubinsPath` supplies forward ARC/STRAIGHT pieces. Bounds: 400×400 XY
region, length≤800 and ≤8pieces; inherited constant anchor grade, selected minimum
radius and sampled geometry/region checks. TPF3 owns native construction/validity.
This is a local extension, not general routing or a station connection guarantee.

## Completion and failures

The workflow sends one correlated `extension` request. Dependent fit/build data
stays within that invocation: separate callback state proved unreliable. After
construction's initial verification, a second fresh native component/geometry query
checks actual TRACK IDs, exact nodes, resources, region and sampled shape. It is
independent of the receipt, but not another Python request. Low-level operations
remain available; cached fit persistence across callbacks/loads is not guaranteed.

Stdout targets≤4096bytes; full requests/responses/new log output/workflow records
stay locally. Files publish atomically. Finite timeout defaults30seconds, maximum300.
Native command ACK is distinct from semantic railway acceptance.

Failed inspect/fit never builds. Uncertain construction retains its journal and
blocks new mutations. **Never rerun `--execute` to collect a missing result.**
Read-only inspection remains possible but does not automatically clear uncertain
effects. `reconcile_pending()` collects a matching late response without sending
another operation. This is in-session reconciliation, not crash recovery, automatic
resume or general idempotency across new journals/loads. No rollback guarantee;
proposal placeholders/counts are not realised entities/effects.

## Connect two existing endpoints

`bridge_live.connect(client, brief, execute=False)` and the live `connect` command
reuse the compound workflow. This is distinct from the offline `bridge_cli.py connect`.

```powershell
python bridge_live.py connect --context context.json --params connection.json
python bridge_live.py connect --context context.json --params connection.json --execute
```

`connection.json` contains exactly `anchor_edge`, `anchor_node`, `target_edge`,
`target_node`, `radius` and `region` (same XYZ bounds schema). All four identities
are exact current native IDs. Native inspection derives positions and outward source
travel; the arrival direction points **into** the target edge. No supplied tangent
is silently reversed, because endpoint travel is derived from the explicitly chosen
edge/node orientation. Matching track template/style is required.

Initial vertical domain: one constant grade compatible with **both** endpoints.
Source grade and incoming target grade must agree within1e-6; fitted length must
reach target height within0.001native units. These are numerical compatibility
tolerances, not permission to ignore a height/grade mismatch. Exact native target
XYZ and slope are used at the boundary. Incompatible height/grade, reverse native
fit pieces or differing assets return an explicit unsupported reason without build.
No general vertical-profile solver is added.

The final proposal reuses the target's positive node ID; it does not create a
coincident replacement node. Fresh readback must end on that exact node and verify
the source/target existing edges still meet those nodes with compatible directions
and resources. Returned incident-edge lists prove the two named attachments, not
complete topology or train traversal. Uncertain construction has the same no-replay
rules as `extend`.

Development-only `test_approach` can create one short independent test stub from
an extension brief's native-fitted finish (length5–60, explicit `authorised:true`).
It is a disposable-world fixture for testing two-ended attachment, not a railway
planner or normal construction workflow. Its observed native IDs must be inspected
before use; the fixture's intended location is not authoritative identity.

## Native route verification

`bridge_live.route(client, brief)` is read-only:

```powershell
python bridge_live.py route --context context.json --params route.json
```

The brief contains exactly `source_edge`, `source_node`, `target_edge`,
`target_node`, `mode` (`TRAIN` or `ELECTRIC_TRAIN`), `max_length` (0–800,
exclusive zero, native units) and `required_edges` (1–16 distinct current TRACK IDs).
Choose the source approach's entrance node and target approach's exit node.
The adapter reacquires current BaseEdge and transport lane identities; ambiguous
lanes or incompatible orientation are rejected. It calls native
`api.engine.util.pathfinding.findPathNodeToNode` with exact transport NodeIds.
Python does not calculate a replacement graph/path.

Acceptance checks exact transport continuity, mode availability, native forward-only
flags, both requested approach lanes and travel directions, required TRACK presence
and total native path length. `required_edges` means presence, not a prescribed
sequence. At most64path entries are retained; truncation fails acceptance.
`max_length` is a **returned-path acceptance limit**: this native API exposes no
search-length bound. Client timeout does not cancel engine computation. Node-to-node
routing exposes no initial-direction parameter; the returned direction is checked,
not forced. A rejected native path does not prove all alternative paths impossible.

`status:ok` means the native query completed; `requested_route_verified:true` means
the named route passed. CLI exits0 only for verified routes, otherwise1. Full evidence
stays local and stdout≤4096bytes. Read-only queries neither replay nor reconcile an
uncertain construction. This is native transport routing evidence, not train traversal,
signal/reservation availability or a production transport guarantee.

## Discover and select free endpoints

`bridge_live.discover(client, brief)` queries a native-coordinate XYZ box:

```json
{"region":{"min":[1010,7175,-40],"max":[1286,7445,44]},"max_edges":16}
```

These example coordinates are task-specific, not a universal map location. Bounds
must be ordered and span≤400native units per axis; max_edges is1–16. Native octree
callbacks may continue after the observation cap: all callback hits are counted, but
at most256candidates receive component inspection. Only confirmed TRACK edges are
retained. Edge overflow or the component cap sets truncated=true/complete=false;
there is no pagination or claim of all endpoints in a truncated region.

For each in-box endpoint, native `streetSystem.getNodeSegments` checks **full**
incidence, including edges outside the spatial sample. Native construction ownership
is checked too. Eligibility means one incident TRACK edge and no construction owner;
it is a plain free-endpoint domain, not a guarantee of construction approval or a
preservation policy. Positions, outward directions, grades and resource identities
come from fresh native components. At most16incident IDs are printed per endpoint;
full incident count and output truncation are explicit. No world graph is exported.

```powershell
python bridge_live.py discover --context context.json --params area.json
python bridge_live.py connect-selected --context context.json --discovery RESPONSE_FILE --params selection.json
```

Discovery stdout provides a full-response path and bounded candidate preview when
necessary. Select the displayed `ref` values rather than copying hidden native IDs.
`selection.json` contains exactly source_ref, target_ref, radius and region. The
callable is `connect_selected(client, discovery_response, selection_brief)`.
For endpoints in different small regions, pass a list of two full discovery
responses, or save that list as the CLI's `--discovery` JSON file. Both records
must belong to the current session; duplicate records/ambiguous references fail.
References belong to that recorded discovery and current adapter session; they are
not persistent world identities. Selection rechecks exact geometry/resources and
full incidence inside the engine before using the existing two-ended fitter.
Changed snapshots, nonfree endpoints and old sessions are rejected. A truncated
area does not invalidate a retained endpoint's independent full-incidence check.

This command is **fit-only**; `--execute` is rejected. Discovery and fit-only selection
preserve unresolved mutation journals and do not replay/clear them. Existing native
fitter limits still apply. P05 demonstrated6TRACK/11candidates in one complete local
query and3free endpoints in a truncated query. Selected opposing-heading endpoints
reached native fitting but returned unsupported_reverse_geometry; successful fitting
of that arrangement is not claimed. P06 selected compatible forward approaches from
two local records: source130757/node130371 to test approach131245/node131187,
heading change about4degrees, three native pieces, length110.001569, radius100,
zero grade and sampled XY error0.000492081. The opposite stub end was explicitly
rejected as reverse geometry. There is no claim of unrestricted heading support or
continuous geometry proof. The fitted connection was not constructed.

Explicit failed-fixture reconciliation is available as
`reconcile_rejected_fixture(client, original_discovery)` or:

```powershell
python bridge_live.py reconcile-fixture --context context.json --params empty.json --discovery original_discovery.json
```

`empty.json` contains `{}`. This supports only a pending `test_approach` with a
recorded native rejection. Fresh native reads must show the original anchor unchanged
and the complete intended footprint without TRACK; changed, occupied or truncated
observations retain the block. It records the original pending job/receipt and fresh
observations durably before closing that Python pending record. Other effects remain
unknown. It never resends the command or claims rollback; the native session guard
may still require a separately authorised ordinary load. P06 reconciled the P05
collision this way before loading again, then built a different20-unit fixture on
clear land. The old failure and its unknown incidental effects remain in local history.

## Demonstration and checks

Build40408, disposable world: P01 demonstrated separate calls; P02 demonstrated
the complete command, building three TRACK pieces, length296.165783native units,
selected radius100, exact connected endpoints and sampled XY error0.00048828125.
A later independent inspection confirmed actual IDs/node chain. Native fit-only,
invalid attachment and region rejection produced no further construction. A collision
was rejected; its effects remain unknown in preserved local history.

P03 connected two existing native endpoints through edges131239/131240/131241,
nodes131226→131237→131238→131215, retaining source131229 and target131235 incident
at the exact ends. Native fit length60.001331, selected radius100, compatible grade
0.002264303; independent inspection confirmed both connections and matching assets.
Fit-only and invalid/reversed target checks were exercised without construction.
Two earlier test-stub collision rejections remain unknown in blocked local journals;
a nearby gentle approach supplied the successful target fixture. A straight candidate
was rejected as reverse geometry by the current native fitter; straight fitting is
not claimed universally supported. The disposable save was saved normally.

P04 native TRAIN path on build40408: 131229→131239→131240→131241→131235,
transport nodes131225→131226→131237→131238→131215→131234 (index0), length88.659898.
Both approach directions and all required edges passed. Excess length, invalid
endpoint, absent required edge and wrong entry direction were rejected without build.
The separately declared bounded `findPath` route failed with error300; its constructor
was unavailable at runtime. That unresolved contract is not used by this operation.

56client/fake-worker tests passed;14unchanged quiet-runner tests reused. Run:

```powershell
python tools/quiet_checks.py --suite live_client --label live-client
```

Raw acceptance logs are intentionally local, not required to use the source.
`STATE.md` identifies reports. Unprobed: train traversal, continuous geometry proof,
native save/load identity, arbitrary-version compatibility and production transport.
Detailed station modelling and train physics remain outside this milestone.
Usage unavailable; no invented credit savings.

## Native height and grade (P07)

The same `extend`, `connect` and fit-only `connect-selected` commands accept an
optional `vertical` field in their JSON brief. For an extension, supply
`{"end_height":5.5,"end_grade":0.005,"max_grade":0.04}`. Heights use native world
coordinates; grade is rise divided by horizontal distance, with its sign in the
selected travel direction. For a connection/selection, supply only
`{"max_grade":0.04}`: target height and incoming grade come from the exact native
attachment. Explicit constraints are never silently changed. Without `vertical`,
the existing constant-grade-compatible endpoint domain remains in force.

Native Dubins fitting supplies XY ARC/STRAIGHT pieces. The adapter supplies one
native `EdgeGeometry` cubic height profile's endpoint heights/tangent grades over
the cumulative native XY length; TPF3 evaluates its interpolation. Per-piece
heights/tangents preserve those endpoints and join grades. This is a selected
native cubic profile, not a higher-level native vertical routing/optimisation API.
Five samples per piece check XYZ region, grade and subdivision; fresh readback
checks actual BaseEdge controls/geometry and exact attachment identity. These are
sampled checks, not continuous proofs. Movement geometry Z remains distinct from
the BaseEdge height profile. Forward-family/reverse-geometry limitations remain.

Build40408 demonstrated a roughly100-unit connection rising2 native height units
between grades0.005 and0.015, selected radius100/max_grade0.04. Exact realised
TRACK131258/131259/131260 connected nodes131248→131256→131257→131251.
A further100-unit extension rose1 unit to grade0.005 through TRACK131265/131266/
131267. Native TRAIN pathfinding verified the whole240.031993-unit chain. A strict
grade limit, out-of-region profile and omitted vertical option were rejected before
construction. A normal save/load reacquired current-session attachment facts.
These IDs describe that disposable demonstration; never reuse them as a brief.

One station-adjacent connection was rejected with native Collision. Another was
built but a subsequent callback cache lookup failed. Neither was blindly replayed.
Narrow callable reconciliation is available for those recorded outcomes:
`reconcile_rejected_connection(client, original_discoveries)` requires explicit
native rejection plus fresh unchanged/free exact attachments; incidental effects
remain unknown. `reconcile_constructed_connection(client, original_discoveries,
observed_edge_ids)` requires reported native success, recorded fit controls, fresh
exact directed chain/resource checks and a native TRAIN route. It records evidence
before closing the Python pending record. Both are read-only, in-session, never
resend construction and provide no rollback/crash-recovery guarantee. Native
mutation guards can still require an authorised ordinary load. The repaired
compound callback now captures its fit locally and preserves returned identities
if a later readback fails; the new extension verified that repair at runtime.

## Brief-driven connection (P08)

`connect_brief(client, brief, execute=False)` and the CLI below discover/select
endpoints and perform the native fit in one workflow. Add `--execute` to build,
read back exact attachments and require a native TRAIN route through every built
edge and both approach tracks. Fit-only is the default. No manual entity IDs or
model calls are needed inside the workflow.

```powershell
python bridge_live.py connect-brief --context context.json --params connection.json
python bridge_live.py connect-brief --context context.json --params connection.json --execute
```

Example shape (replace coordinates/directions with the intended native map sites):

```json
{
  "source": {
    "region": {"min":[85,185,-40],"max":[115,215,60]},
    "max_edges":8, "guide_xyz":[100,200,5],
    "travel_direction":[0.308,-0.951], "heading_tolerance_deg":5
  },
  "target": {
    "region": {"min":[309,-371,-40],"max":[339,-341,60]},
    "max_edges":8, "guide_xyz":[324,-356,11],
    "travel_direction":[0.437,-0.899], "heading_tolerance_deg":5
  },
  "region":{"min":[0,-456,-40],"max":[424,300,60]},
  "radius":120, "vertical":{"max_grade":0.04},
  "max_fit_attempts":4, "max_route_length":750
}
```

Each search is bounded to400 native units per axis and1–16TRACK edges. Fully
verified free endpoints must match the brief's heading tolerance. Source direction
is travel **away** from its approach; target direction is travel **into** its
approach. Supplied tangents are never altered to match a criterion. Guide proximity
ranks already-identified candidates; it does not establish identity/connectivity.
Pairs sort by summed squared guide distance, then summed heading error, then exact
native edge/node IDs for ties. Complete and truncated discovery remain explicit.

At most1–16candidate fits may be attempted. Only explicit pre-build fit rejection
with `game_constructed:false` permits another pair; construction rejection, timeout,
unknown effects or verification failure stop immediately. An unfinished journal
blocks execution. Native snapshots/full incidence are revalidated immediately before
the compound fit/build. Normal success needs four native requests: two discoveries,
one compound connection and one route query. Local workflow files correlate all
receipts; stdout remains compact. There is no automatic mutation retry/resume.

`no_eligible_candidates` describes the observed selection; `no_accepted_candidate`
describes all observed pairs tried; `search_budget_exhausted` means pairs remain.
None claims global impossibility, especially with incomplete discovery.
`native_route_unverified` after building keeps `game_constructed:true`; it is not
rollback. The route limit includes approach edges and is an acceptance bound,
not a bound imposed on TPF3's internal pathfinder.

P08 built600.013514 native units with about8degrees overall heading change/rise6,
endpoint grades0.005→0.015, radius120/max_grade0.04. Exact TRACK131275/131276/
131277 connected nodes131264→131273→131274→131255; independent inspection and
native TRAIN route623.538651 passed. Sampled grade0.015000001, zero join-height gap.
Wrong direction and out-of-region briefs were rejected before building. The initial
old400-unit fitting envelope rejected the fixture before any proposal; the finite
fit envelope is now1000 XY units per axis. Total fit length≤800, at most8pieces and
five samples/piece remain. Discovery bounds were unchanged. Geometry/grade remain
sampled; physical train traversal, unrestricted routing and save identity are unprobed.

## Ordered multi-leg corridor (P09)

`connect_corridor(client, brief, execute=False)` reuses the connection brief and adds
`guides`:1–3 ordered intermediate alignment requirements. Each guide contains native
XYZ `position`, nonzero XY `travel_direction` and signed `grade`, for example:

```json
{"position":[1500,5800,16],"travel_direction":[0.5,-0.866],"grade":0.005}
```

These are deliberately selected alignment anchors, including height/grade; they are
not native identities, screen coordinates or guessed attachments. The source/target
search regions and deterministic direction/guide criteria remain as in P08.

```powershell
python bridge_live.py connect-corridor --context context.json --params corridor.json
python bridge_live.py connect-corridor --context context.json --params corridor.json --execute
```

The prepared mod fits every leg with the existing native Dubins/cubic-height mechanics
before construction. It joins the controls into one native proposal, sharing node
references across leg boundaries. Fit-only reports each leg and explicitly leaves
guide-node identity unrealised. Execution must reacquire exact guide nodes, matching
selected guide positions/directions/grades and final discovered endpoint attachments,
then verify one native TRAIN route through every new edge and both approach tracks.
No overall success is returned merely because fitting or native construction succeeded.

Finite scope:2–4legs,≤800native units/8pieces per leg,≤3200units/32pieces overall,
≤3000XY units per overall-region axis, five geometry samples/piece, and≤4000route
acceptance length. Native path observation remains≤64entries. Discovery bounds are
unchanged. The route helper now allows≤4000length/32required edges; single-fit
`connect-brief` retains its≤800route and1000XY region bounds. Native pathfinder
execution itself is not length-bounded. There is no replacement Python curve fitter.

Only explicit pre-build fit rejection may try another selected endpoint pair. A partial,
rejected or uncertain construction result stops and retains the full receipt/journal;
no automatic replay, rollback or crash continuation. Geometry and grade checks are
sampled, and physical train traversal remains unprobed.

56client tests passed, including fit-only identity honesty, exact guide verification,
partial/unknown mutation stops, invalid guides/constraints and CLI/default execution.
On build40408 the integrated CLI built three500-unit native-fitted legs,1500.004925
units overall with12-unit rise, endpoint grades0.015 and intermediate grades0.005/0.01.
Nine TRACK edges131295–131303 attach source131271/node131270 to target131285/node131283;
guide nodes131289/131292 are exact shared identities. Independent inspection and native
TRAIN route1540.063845 through all pieces passed. Sampled maximum grade0.015000001,
zero join-height gap; radius120/max_grade0.04. Wrong-direction and strict-grade briefs
stopped before construction. Fit-only did not report realised guide-node identity.

At the P09 checkpoint, the first authored layout and three fit-only variants were
rejected by a guard against backward-parametrised native pieces. A distinct gradual
bend passed without relaxing constraints. P10 resolves that particular limitation
below; arbitrary guide arrangements and unrestricted routing remain unclaimed.
Actual node identities come from the build receipt/readback, never fit placeholders.
The initial automatic-review denial was resolved by the user's explicit approval;
two short disposable target fixtures and one coherent corridor were built. There is
no transaction/rollback claim. Full failed/successful receipts remain local.

## Native orientation and alternating bends (P10)

The installed `findDubinsPath` declaration returns geometry plus a direction flag.
The adapter passes that flag to native `calcPositionAndDirection` for endpoint,
tangent and comparison samples. Backward parametrisation is not a requirement to
reverse a supplied railway direction. Native samples must independently establish
reversed canonical endpoints/opposed canonical tangents, then pass the same exact
travel endpoints, joins, radius, grade, region and sampled-conversion checks. No
global tolerance or constraint was relaxed. Height interpolation remains native.
Compact fit summaries include `native_orientation` counts; full orientation evidence
stays in local receipts. No extra input fields or execution option are required.

Build40408 demonstrated the previously rejected relative pattern: three500-unit
chords at+12°/−8°/+4°, corresponding guide/final directions, rise4/7/12 and grades
0.005/0.01/0.015, translated/rotated from a fresh native attachment. Native fit length
1501.283859 contained six forward and three backward-parametrised pieces. Nine TRACK
edges131319–131327 connected source131250/node131232 to target131268/node131160,
with exact shared guide nodes131313/131316. Independent committed inspection and
native TRAIN route1541.342245 passed. Radius120/max_grade0.04 were unchanged;
sampledXYerror0.005695,Zerror0.000003815,maximum grade0.015000002,zero join-height gap.
Legacy straight/forward curved fits and wrong-direction/strict-grade rejection passed.
57affected client tests passed. Geometry/grade remain sampled, native routing is not
physical train traversal, and one proposal provides no rollback guarantee.


## Junction branch connection (P11)

Use `connect_junction(client, brief, execute=False)` or:

```powershell
python bridge_live.py connect-junction --context context.json --params junction_brief.json
python bridge_live.py connect-junction --context context.json --params junction_brief.json --execute
```

The brief uses the existing connection schema: bounded source/target regions,
guide XYZ locations, explicit travel directions/heading tolerances, minimum radius,
authorised XYZ region, maximum grade, finite fit attempts and route-length acceptance.
Source discovery requires an exact existing node with two compatible TRACK edges,
aligned travel tangents/grades and no construction owner; the target remains a free
endpoint. `discover(..., junction=True)` / CLI `discover_junction` exposes these
candidates without changing ordinary free-end eligibility. No native edge splitting,
station connection, crossover or general junction routing is claimed.

Fit-only checks the existing through TRAIN route and proposed branch. The native fitter
uses 1.05 times the requested radius as a modest conversion margin; compact output
separates `fit.radius` from `fit.requested_min_radius`. The requested minimum is never
lowered. Execution rechecks snapshots/incidence, submits one proposal, reacquires exact
TRACK/node identities, checks the three incident edges and verifies incoming-to-through
and incoming-to-branch TRAIN paths in their specified directions. A third edge alone
is insufficient. Native node-owned transport connectors are included in path evidence.

TPF3 trims movement curves at turnouts and exposes indexed native transport ports.
Junction verification uses those exact identities rather than requiring trimmed curves
to equal a preliminary sketch. BaseEdge controls, attachments and joins still match;
realised branch and turnout movement geometry must pass sampled radius, grade and region
checks. Five samples per geometry are not continuous curvature or clearance proof.
Free-end/corridor tolerances remain unchanged. Physical train traversal, reservation,
all possible junction movements and general save identity remain unprobed.

A native rejection or uncertain result stops mutation. For an explicitly rejected
junction, `reconcile_rejected_junction(client)` performs fresh fit-only snapshot/incidence
and through-route checks before clearing its pending journal. Other effects remain
unknown; it neither rolls back nor replays. Fit-only observations remain available
while a mutation is pending, but another construction is blocked.

Build40408 demonstrated a curved/graded 350.987255-unit branch from node131316,
TRACK132538/69391/44868 to target132441/node21454. Through TRAIN27.697297 and branch
TRAIN372.902615 passed; sampled realised minimum radius124.509571 exceeds requested120,
maximum grade0.015 is below0.04. An initial branch failed geometry verification and
remains failed evidence; a distinct near-parallel proposal was natively rejected and
reconciled before the diverging layout passed. No rollback or automatic replay occurred.


## Interior junction placement (P12)

Use `connect_junction_at(client, brief, execute=False)` or:

```powershell
python bridge_live.py connect-junction-at --context context.json --params interior_brief.json
python bridge_live.py connect-junction-at --context context.json --params interior_brief.json --execute
```

Use the P11 brief plus explicit `placement_tolerance` (greater than zero, maximum10
native coordinate units). Source guide XYZ and travel direction select a native point
near the interior of an ordinary unowned TRACK edge. Native `EdgeGeometry:locate`
returns parameter0.05–0.95; stated spatial/heading tolerances remain binding. Either
canonical direction is supported without reversing the supplied railway direction.
Target remains an exact free end. Edges with objects/construction owners are unsupported.
Include the entire replacement through edge and branch in the authorised XYZ region.

Native evaluation supplies both through subdivisions; sampled position, direction,
radius, grade and region checks precede construction. One proposal removes the original
edge, clones its properties into two replacements and attaches the native-fitted branch.
Fresh exact identities, controls/resources, three-way incidence and through/branch TRAIN
paths establish the result. Final-state absence establishes removal; receipt counters
alone do not establish the railway. No Python spline fitter or rollback guarantee.

Uncertain construction stops. `reconcile_constructed_interior(client, original_client=None)`
reads the explicitly returned IDs against recorded native controls and fresh native paths;
only successful verification clears its pending journal. Original failure evidence remains.
After an authorised normal save/load, use the original client as an evidence reference and
the current client for fresh native reads. This is explicit reconciliation, not automatic
crash recovery or general save-identity mapping. No fitting/build is repeated; transient
engine effects remain incomplete. Full observations stay local; CLI summaries remain compact.

Build40408 demonstrated node135148 at parameter0.50390625 on original131326. Through
TRACK135522/135548 retain outer nodes131317/131318; branch135425/8641/131653 reaches
node11085. Native fitted length350.125965, rise2.991768, grade0.008900871 to0.015,
requested radius120/native fitting margin126, realised sampled minimum124.535004.
Through TRAIN473.756048 and branch TRAIN608.866104 passed. An initial receipt check
failed after construction; final state was verified without rebuilding. Stale source,
misplaced guide, wrong heading, strict grade and excluded region fail honestly.
Geometry remains sampled. Physical traversal, reservation, all movements and general
native save identity are unprobed. P11 existing-node/free-end/corridor workflows remain.

## Integrated multi-track throat (P13)

Use `connect_throat(client, brief, execute=False)` or:

```powershell
python bridge_live.py connect-throat --context context.json --params throat_brief.json
python bridge_live.py connect-throat --context context.json --params throat_brief.json --execute
```

The brief declares `roles` (exactly two `approach` roles, at least three `destination`
roles), ordered `steps`, and directed `required_routes` before construction. Each role
has `kind` and an existing connection `endpoint` intent: bounded region, guide XYZ,
travel direction, heading tolerance and discovery budget. Approach travel points into
the throat; destination travel points out. Each step has `name`, `kind` (`crossover`
or `branch`), `source` and `target` intents. A crossover joins two ordinary native
through-edge interiors; a branch joins an interior to a free destination endpoint.
Each route has `from`, `to`, and `via` step names identifying required branch edges.
Every role and construction step must be exercised. The brief also supplies `radius`,
`region`, `vertical.max_grade`, `placement_tolerance`, `max_fit_attempts` and
`max_route_length`; existing connection limits apply, with route acceptance up to3000.
Bounds:5–10roles,2–6steps,3–16required movements. No automatic fixture creation.

Native fitting, subdivision and construction are reused. The crossover fitter uses
1.25 times the selected minimum as a conversion margin; final acceptance still checks
the selected minimum. All affected roles are reacquired after each mutation. Guide
proximity selects a role; exact native TRACK/node identities establish attachments.
After all steps, fresh directed TRAIN paths must contain every requested approach,
destination and `via` branch, including native node-owned turnout connectors. Sampled
radius, grade and authorised region are checked over every final path. Fit-only checks
individual proposals and explicitly does not verify a future assembled network.

Stop on failed or uncertain construction; completed partial effects remain visible.
Explicit `reconcile_constructed_crossover` checks recorded receipts against fresh native
state without fitting/building. Optional `--reconciled-crossover <record>` requires
`--execute`, matching approved first-step constraints and another read-only check;
it is not automatic resume. This continuation path has local tests and the P15 native
demonstration below. `remove_branch` is a bounded, explicitly authorised native repair
of an exact observed exclusive branch; it is not rollback.

Build40408 demonstrated two approaches, four destinations, one crossover and two ladder
branches on translated/rotated open land. Seven declared movements passed on the final
network: A1→D1/D2/D3/D4 and A2→D2/D3/D4. A2→D1 is not claimed. Fresh inspection of29
TRACK edges independently gave sampled BaseEdge minimum radius122.816940 (selected120),
grade0; final native movement geometry also passed. Missing required branch, excluded
region and stale split attachment fail honestly. The initial crossover failed realised
radius; its branch was explicitly removed, then a distinct shorter layout passed without
lowering constraints. CLI output799bytes;81affected client tests passed.
This demonstrates native connectivity/routing, not train traversal, reservations,
capacity, continuous clearance/curvature proof or unrestricted throat routing.

## Native adjacent-track approach (P14 partial)

`connect_adjacent(client, brief, execute=False)` / CLI:

```powershell
python bridge_live.py connect-adjacent --context context.json --params adjacent_brief.json
python bridge_live.py connect-adjacent --context context.json --params adjacent_brief.json --execute
```

Use the ordinary connection brief plus `side` (`left`/`right` in directed reference
travel) and explicit `spacing_tolerance` greater than0, maximum0.1 native units. Source
and target select free ends of an existing ordinary TRACK route. The reference must be
a level, unowned, object-free chain of at most16edges without node-owned movement
connectors. `trackDistance` is read from its actual native StreetTemplate; there is no
assumed real-world conversion/default spacing. Missing resource data is unavailable.

The mod uses native `CUBIC_OFFSET_SPLINE` and `calcPositionAndDirection` to obtain a
normal-offset curve, then checks a bounded cubic representation with native sampling.
It does not translate a curve along a map axis or run a Python fitter. One native
proposal constructs an independent chain. Current TRACK/node identities, resource and
control readback, directed TRAIN route, selected radius/grade/region, and17samples per
reference piece establish the result. Native nearest-parameter queries compare geometry;
they do not establish attachment identity. Sampled adjacency is not continuous clearance
or vehicle-gauging proof. Fit-only performs no construction. New `inspect` parameter
`resources:true` exposes relevant trackDistance/minimum-radius metadata read-only.

Build40408 demonstrated a curved, translated/rotated reference and12-edge adjacent
track at the actual simple-catenary template spacing5. Fresh independent17-sample
BaseEdge checks found signed spacing4.999835–5.000129 and sampled minimum radius151.616767
against the pair's selected120. Both tracks' directed TRAIN routes pass with independent
native node identities. Left-side construction is demonstrated; right-side delivery
has local tests only. This is native offset sampling/construction, not demonstrated
player-style parallel snapping or a dedicated native parallel-track tool API.

P14's original direct close crossover/branch outcome remains blocked. Existing P13 crossover
proposals at spacing5, selected radius120 and two distinct60/90-unit lead layouts were
natively rejected as Construction Not Possible. Fresh through-edge/preflight checks
reconciled both rejections without rebuilding; other effects remain unknown. Five
required throat movements were declared; only the two independent through movements
existed at that checkpoint. P14 did not establish crossover/branch/final-matrix success.
P15 below delivers a wider equivalent. The direct rejection does not establish that
TPF3's player tools cannot build an equivalent.

The initial reference site collided and was relocated; its rejected corridor was also
reconciled read-only. `reconcile_rejected_corridor` / `reconcile_rejected_crossover` are
explicit bounded current-state checks, not rollback or automatic resume. The reference
fixture's native fit input160 produced sampled BaseEdge minimum157.374230: its separate
160-radius acceptance is false. The final adjacent workflow explicitly checks120 on both
realised tracks and passes; native fit radius alone is not a realised-radius guarantee.
P15 below fixes that acceptance gap while preserving the original conversion diagnostic.
87client tests pass. No physical traversal/reservations/capacity claim.

## Widened native connection and realised constraints (P15)

The existing `connect-throat` command demonstrated all five movements A1→D1/D2/D3
and A2→D2/D3 on build40408. This is a disclosed functional alternative: a100-unit
five-metre adjacent approach fans out locally to a widened destination and a branch.
The original direct5m crossover remains unresolved. The new D2 ends near local(620,105)
and D3 near(1120,460), with parallel destination headings, in the translated/rotated
brief frame. It does not preserve the earlier full curved adjacent run. Old incidental
test tracks crossing the new corridor were explicitly removed; historical acceptance
records remain evidence of those earlier tests, not promises about the current map.

```powershell
python bridge_live.py connect-throat --context context.json --params throat_brief.json
python bridge_live.py connect-throat --context context.json --params throat_brief.json --execute
```

Native fitting controls and hard realised requirements are separate. Ordinary fitting
uses a1.05 radius margin; crossover fitting uses1.25. Neither margin is an acceptance
guarantee. Converted proposals and current BaseEdge/readback geometry must pass the
selected hard radius, grade and region with17samples per piece. Missing engineering
evidence fails; a straight-only result explicitly represents an infinite sampled radius.
The old160-fit/157.374-realised shortfall now rejects, while the selected120 pair passes.
`inspect` accepts `geometry_constraints` (`radius`, `max_grade`, `region`) for fresh
read-only checks. Constructed-connection reconciliation also requires these bounds.

Fresh independent checks of28TRACK edges gave minimum sampled radius122.281680≥120,
grade0≤0.04 and retained approach spacing4.999835–4.999948. All five directed native
paths, including turnout connectors, pass. Missing required movement, excluded region,
hard160 radius and stale original attachment reject. Explicit retained-crossover
continuation was demonstrated without rebuilding it. Rejected interior junctions can
be reconciled through `reconcile_rejected_junction`; its fit-only check retains unknown
effects. `remove_branch` with explicit `free_ends:true` supports an exact exclusive chain
of at most16ordinary edges between two-edge attachments, leaving verified free stubs;
the ordinary removal bound remains8. These are authorised local operations, not rollback
or automatic resume.89client tests pass. Geometry is sampled, not a continuous proof;
physical train traversal, reservations/capacity and general save identity remain unprobed.

## Compact junction recipe

`junction_recipe_example.json` supplies placement, heading, native asset-selection
region and engineering limits for `widened_two_approach_three_exit_v1`. No native IDs
or per-step construction proposals are required. Use an unused suitable land site;
the example coordinates describe the demonstrated disposable map, not a universal site.

```powershell
python bridge_live.py junction-recipe --params implementation/live_python_interface/junction_recipe_example.json --evidence .local_runs/recipe_plans
python bridge_live.py junction-recipe --context context.json --params implementation/live_python_interface/junction_recipe_example.json --recipe-plan PLAN.json --execute
```

The first command is offline and publishes a hashed DESIGN plan, footprint, operation
sequence and five required movements. `PLAN.json` is its returned evidence path.
Execution discovers an actual native asset family, prepares five short interfaces,
builds native reference/fanout corridors, derives junction guides from current native
geometry, constructs crossover/branch and verifies all five directed TRAIN paths.
It uses the existing transport/journal and retains durable per-step receipts.

Supported intent is fixed level geometry, radius120, native spacing5, max_grade in
(0,0.04], arbitrary finite map translation and heading within[-180,180]. The reference
uses a stronger design radius160; final hard radius remains120. No scaling, mirroring,
arbitrary topology or direct5m crossover is supported. The widened footprint is about
1720×540 native units before rotation. Only the first100-unit straight approach claims
5m spacing; the fanout is not a constant normal offset.

Failure stops execution with completed steps and unknown/partial effects preserved.
There is no automatic resume or clearance. An explicit `--prepared-recipe RECORD.json`
may reuse five exact freshly reacquired stubs only when the matching plan stopped
before reference construction, or that reference rejection was explicitly reconciled
as absent. That legacy option does not retry later completed stages. Use the recipe-level
inspection/checked continuation below for current-state completion.

Build40408 demonstration at(1700,5200,33),heading−50 completed with explicit site
clearance and lower-level throat continuation after native Collision; failed recipe
receipts remain failed. Fresh checks found all five paths,28TRACK edges, sampled
radius122.279890≥120,grade0 and approach spacing4.999938–4.999943. No rollback, continuous
geometry proof, arbitrary-site success or physical train traversal is claimed.
The removal primitive additionally permits one explicitly isolated, unowned ordinary
test fixture (`isolated_fixture:true`), verifying its edge and both nodes are removed.
Tiny native ARC parts may be omitted only within a collective0.001 length/position
and0.001° heading bound; hard radius/join/endpoint checks still apply.


### Inspect or continue a recipe

```powershell
python bridge_live.py junction-recipe-inspect --context context.json --params implementation/live_python_interface/junction_recipe_example.json --recipe-record RECORD.json
python bridge_live.py junction-recipe-continue --context context.json --params implementation/live_python_interface/junction_recipe_example.json --recipe-record RECORD.json --execute
```

`RECORD.json` may be the invocation's full record, its compact CLI summary, a full
inspection receipt, or a successful continuation receipt. Use the same original
brief; no nested step brief or native IDs need to be extracted. The callable equivalents
are `inspect_junction_recipe(client, record_path)` and
`continue_junction_recipe(client, record_path)`.

Inspection performs bounded native reads and writes a new local receipt. It reacquires
five semantic interfaces, checks their actual geometry/assets, evaluates current TRAIN
paths, confirms exact current three-edge junction incidence and required path visits,
and samples spacing across the complete retained100-unit straight approach. It reports
completed/absent/failed/unknown stages. Native IDs in historical receipts are not reused
as current authority; guide geometry is checked against the original native guide receipt.

Explicit continuation assesses first. An already complete network receives a new
successful recipe receipt without construction. Otherwise it may build absent reference/
fanout stages, a wholly absent throat, or an absent branch after a verified crossover.
Fresh available attachments/unsplit through geometry must establish absence. Missing
interfaces, changed geometry/assets, truncated observations and ambiguous or failed checks
stop; missing fixtures are reported, not automatically recreated. Unfinished steps and
unknown historical effects require explicit matching reconciliation even across sessions.
No automatic replay, site clearance, crash recovery or rewritten failure is provided.

`game_constructed:false` on a successful no-build continuation means that invocation
made no construction; `final_network_verified:true` records the existing realised railway.
`new_mutations` counts attempted mutating recipe steps (a compound throat step can include
multiple native commands), not individual engine writes. Individual receipts retain effects.

P17 build40408 acceptance used the P16 network, without another build: five fresh native
TRAIN paths, exact current joins, retained100-unit spacing4.999938-4.999975,18read-only
queries and603-byte successful continuation summary. Repeated fresh-process continuation
also made no builds. P16 collision receipts remain failed and unchanged.110client tests
cover changed/reused identities, changed geometry/assets, wrong joins, partial/unknown
state, durable interrupted steps, missing-stage continuation and duplicate suppression.
This establishes checked continuation on the demonstrated network, not arbitrary-site
success, continuous geometry proof, signalling permission or physical train traversal.


## Ordered running-direction layout (P18 prepared)

`parallel_layout_example.json` declares UP-UP-DOWN-DOWN, the ordered track IDs, an
explicit route reference and six required functional movements. UP means increasing
that reference in this example; DOWN means decreasing. Track order increases along
the reference's left normal, independent of map rotation. UP/DOWN does not label the
native edge's stored p0/p1 or its construction direction.

```powershell
python bridge_live.py parallel-layout --params implementation/live_python_interface/parallel_layout_example.json --evidence .local_runs/layout_plans
python bridge_live.py parallel-layout --context context.json --params implementation/live_python_interface/parallel_layout_example.json --execute
python bridge_live.py parallel-layout-inspect --context context.json --params implementation/live_python_interface/parallel_layout_example.json --layout-record RECORD.json
```

The first command is offline and publishes a reviewable hashed plan. Callable
interfaces: plan_parallel_layout, publish_parallel_layout, execute_parallel_layout
and inspect_parallel_layout. `native_execution_supported` identifies the prepared
execution domain; `native_runtime_demonstrated:false` on a DESIGN plan makes no game
capability claim. The execution command has not yet passed native acceptance.

Planning validates UP-DOWN, UP-DOWN-UP-DOWN and UP-UP-DOWN-DOWN, including reversed
UP/reference convention and rotation. Native execution is narrowly prepared for
four-track UUDD with increasing-reference UP, level radius120/spacing5. It creates
four straight through tracks, a diverging UP branch from the low outer track, and a
DOWN branch merging into the high outer track. Outward branches avoid a close
crossover; no switching among the four tracks is supplied. Other patterns can be
planned but native execution stops as unsupported until separately demonstrated.

Every declared through/outer-branch movement must appear once. Opposing-direction,
unknown-port, cross-track switching or omitted movements fail before native requests.
Native construction uses the increasing geometric reference; DOWN traffic is checked
with reversed source/target attachment roles. This does not reverse supplied native
construction tangents or claim that TPF3 enforces traffic direction. An unsignalled
native reverse path does not authorise a movement contrary to the design brief.

Prepared execution uses existing native fixtures, corridor fitting and interior
junction construction. Fresh verification reacquires all functional ports and exact
junction incidence, checks directed TRAIN paths with selected radius/grade/region,
and17spacing samples for each of three retained100-unit adjacent approach pairs.
Partial effects/unfinished steps stay in durable evidence. No automatic retry,
clearance, crash resume, rollback or operational/signal enforcement is provided.

P18 currently has117passing client tests, including deterministic pattern/direction
transforms and fake-native execution/readback. The attempted native experiment was
rejected by automatic approval review before process execution; no P18 construction
occurred. P17's five-route evidence remains valid for P17, not a four-track proof.
Concrete native approval is pending for the supplied disposable-map example at
(1700,6500,33),heading-50 within[1300,5000,0]..[3350,7200,80], including necessary map
clearance/terrain effects. Physical traversal, reservations and signals remain unprobed.
