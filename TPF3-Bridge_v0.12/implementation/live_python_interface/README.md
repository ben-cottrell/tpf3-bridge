## Exact structured-track removal (P75 preparation)

client.remove_exact_chain(edge_ids, allow_structures=True) explicitly permits a
named bridge/tunnel chain. It reads fresh structure metadata; the mod checks exact
geometry, structure type/resource, unowned exclusive internal nodes and retained
endpoint incidence. Edge objects and unknown types remain unsupported. The default
stays NORMAL-only. 416 affected tests pass; native execution remains untested.
P75 candidates are superseded by the human whole-junction correction.

## P73: basic native stations and representative services

See [STATIONS.md](STATIONS.md) for native passenger templates, processed modules,
exact station/group/terminal identities and approach connections. See [SIGNALS.md](SIGNALS.md)
for explicit exact-object direction replacement and native direction checks.
Construction, configuration, path readback and physical operation are separate evidence.

## P72: native depot placement and service access

See [DEPOTS.md](DEPOTS.md) for processed native construction parameters, exact
depot/exit identities and native Depot-to-service readback. Build40408 demonstrated
a DS-connected depot; full proposal errors reject even when critical=false.

## P71: native signal placement

See [SIGNALS.md](SIGNALS.md) for place_signal, automatic template discovery,
explicit placement/direction and final-state verification. Build40408 demonstrated
a new E inbound one-way signal; all8 D/E terminal routes remain available.
Depot creation remains separate.

## P40: opt-in complete level crossover representation

The public `crossover` request and a `connect_throat` crossover step accept optional
`representation: "single_cubic_level"`. Omitted or `"native_parts"` retains the
existing native-part lowering. This opt-in is not available on branch steps.
It uses native endpoint headings and total fit length, retaining original controls.
Level fits only: <=8 original parts, total length <=800 native units. Every part is
compared at335 points; combined native conversion/repartition error must remain<=0.1.
Exact endpoint positions/directions, authorised region, requested radius and level
grade remain binding. All geometry evidence is sampled, not continuous proof.

Build40408 accepted the coordinator's same5-spacing/140-span/hard600 crossover after
the original three-part export was rejected. One connector94188, four replacement
through tracks94184-94187 and degree3 turnout nodes94182/94183 were confirmed by
fresh-process exact readback; both through routes and both crossover directions pass
native TRAIN path checks. Sampled minimum radius654.331, grade0, combined fit error
0.082411. Hardradius660 and an unknown representation fail read-only. This proves
this case, not a general segmentation cause, engine minimum or full scissors layout.
No train traversal/reservation proof or complete incidental effect history follows.
Local evidence: `.local_runs/live_python_interface/p40/native/` and STATE.md.

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

Request publication retains durable intent before touching staging. The sequence
advances only after the complete slot is published exclusively. Write/permission
failure returns `request_publication_failed`; ambiguous rename/post-publication
failure returns `request_publication_uncertain`; occupied slots remain untouched.
Failed publication or a pending read blocks new slot allocation. Published uncertain
mutations still permit the existing read-only inspection/reconciliation operations.

For an explicitly verified missing read slot, call
`client.reconcile_read_publications([OLDEST_READ_ID, NEXT_READ_ID])` (one or two IDs).
It checks current session, exact saved envelopes, slot/temporary contents and existing
responses/ACKs. It publishes only a proven unpublished original read, retains any
published successor, and consumes both responses without rewinding or filler calls.
Mutations, mismatched/partial files and uncertain absent rename outcomes are refused.
Each reconciliation attempt retains separate local evidence; errors do not become
successful native observations. This repairs an in-session publication gap, not
filesystem permissions, game/host recovery or automatic job continuation. Staging
writes still require the host's appropriate tool permission.


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


## Ordered patterns and reversed UP reference (P22 demonstrated)

The same `parallel-layout` plan/build/inspect interface now executes UD, UDUD and
UUDD with explicit increasing or decreasing UP along the route reference. New
`ud_layout_example.json` declares decreasing-UP UD; `udud_layout_example.json`
declares increasing-UP UDUD. Track order still follows increasing left-normal offset;
west/east are reference-coordinate ends, not traffic directions. Native construction
tangents remain forward. Reversing UP swaps entry/exit and merge/diverge semantics:
the UD example requires U1east->U1west, D1west->D1east, branch_up->U1west and
D1west->branch_down. An available unsignalled reverse path is not traffic enforcement.

```powershell
python bridge_live.py parallel-layout --params implementation/live_python_interface/ud_layout_example.json --evidence .local_runs/layout_plans
python bridge_live.py parallel-layout --context context.json --params implementation/live_python_interface/ud_layout_example.json --execute --timeout 60
python bridge_live.py parallel-layout-inspect --context context.json --params implementation/live_python_interface/ud_layout_example.json --layout-record RECORD.json --timeout 60
```

Use `udud_layout_example.json` for the four-track interleaved arrangement. Supply a
healthy configured adapter/context, suitable bounded native TRACK/template seed
region and an authorised site. Examples describe the demonstrated world, not universal
map locations. Same level/radius120/spacing5 constraints and outward branch family;
no crossing the intervening DOWN track to switch the two UP tracks. Unsupported
requested movements reject before native requests; they are never silently omitted.
Accepted UUDD/P18-P21 plan hashes and receipts remain compatible.

On build40408, UD decreasing-UP at(1200,2400,33),heading-50 built four required routes
and two exact three-edge junctions. Fresh-process inspection and independent17-point
sampling:18TRACK edges,radius124.122312,grade0,region,spacing4.999938-4.999965.
UDUD increasing-UP at(600,4200,33),heading-50 built six required routes/two junctions:
26TRACK,radius124.121004,grade0,region,three adjacent approach pairs4.999915-5.000003.
Other pattern/reference combinations and rotations have deterministic test evidence;
the unchanged increasing-UP UUDD native evidence remains the P18 baseline below.
No live Cartesian-product sweep was performed.

An initial UDUD site rejected its first through corridor after ten fixture stubs.
Read-only reconciliation found the complete corridor absent; other effects unknown.
Fresh partial inspection reports all ten current interfaces completed, missing
junctions/spacing unavailable and six movements unverified. Original failure receipts
remain; relocation succeeded without replay or constraint relaxation. Inspection is
read-only and reports each movement, prior effects and next action. A failed final
spacing check cannot turn verified paths into full acceptance. No automatic retry,
crash resume or rollback. Geometry is sampled only; no continuous clearance proof,
signals/reservations, operational direction enforcement or physical traversal claim.
Affected quiet suite:145passed; exact report and local P22 evidence in `STATE.md`.

## Ordered running-direction layout (P18 historical baseline)

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
and inspect_parallel_layout. `native_execution_supported` identifies the supported
execution domain; `native_runtime_demonstrated:false` on a DESIGN plan makes no game
capability claim. Native execution/read-only inspection have passed on build40408.

Planning validates UP-DOWN, UP-DOWN-UP-DOWN and UP-UP-DOWN-DOWN, including reversed
UP/reference convention and rotation. Native execution is demonstrated for
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

Execution uses existing native fixtures, corridor fitting and interior
junction construction. Fresh verification reacquires all functional ports and exact
junction incidence, checks directed TRAIN paths with selected radius/grade/region,
and17spacing samples for each of three retained100-unit adjacent approach pairs.
Partial effects/unfinished steps stay in durable evidence. No automatic retry,
clearance, crash resume, rollback or operational/signal enforcement is provided.

P18 has117passing client tests, including deterministic pattern/direction transforms,
fake-native execution/readback, partial failures and pending-operation stops. On
build40408, the example at(1700,6500,33),heading-50 built four through tracks and two
outward branches, then verified all six declared TRAIN paths. A fresh-process
parallel-layout-inspect repeated acceptance without construction. Independent samples
of26current TRACK BaseEdges measured minimum radius124.118567>=hard120 and grade0;
three adjacent retained100-unit approaches each passed17signed spacing samples,
4.999878-5.000075. Exact current junction incidence and attachment IDs were checked.
This is sampled geometry evidence, not a continuous proof. All source/tests stayed
unchanged after the117-test report; original approval denials and receipts remain local.
The disposable test world was saved and left paused/non-maximised. Physical train
traversal, direction enforcement, reservations and signals remain unprobed. Other
patterns/reversed-UP conventions have planning/test evidence only. No cross-track
switching or close crossover is supplied; P17's separate five-route receipt is retained.

## Widened four-track switching (P19 demonstrated)

`switching_layout_example.json` declares a level UUDD layout: four through routes,
the outer UP/DOWN branch functions, UP transfer U2:west->U1:east and DOWN transfer
D2:east->D1:west. Other transfer matrices/patterns/UP conventions are unsupported.
The retained four-track approach has5m spacing; outgoing ports and switching zones
are widened. This is a functional junction, not a constant-spacing close crossover.
Translation/rotation and explicit radius120/selected max_grade/region remain binding.

```powershell
python bridge_live.py switching-layout --params implementation/live_python_interface/switching_layout_example.json --evidence .local_runs/switching_plans
python bridge_live.py switching-layout --context context.json --params implementation/live_python_interface/switching_layout_example.json --execute
python bridge_live.py switching-layout-inspect --context context.json --params implementation/live_python_interface/switching_layout_example.json --layout-record RECORD.json
```

Callable interfaces: plan_switching_layout, publish_switching_layout,
execute_switching_layout, inspect_switching_layout. Planning is offline/default;
native execution is explicit and leaves partial/unfinished steps visible. The
workflow reuses native corridor/fanout/interior-junction/crossover primitives;
Python supplies the existing widened guide pattern, not a replacement curve fitter.
UP controls face outward; DOWN native construction retains increasing reference
orientation while required traffic paths run in the opposite direction.

Fresh inspection reacquires10functional ports/six exact three-track junctions and
requires all eight paths, including both transfer junctions and the exact freshly
inspected built connector edges. Changed throat receipts or stale connectors fail.
Current sampled radius/grade/region and17spacing samples across each of three
retained100-unit approach pairs are checked. Saved receipt integrity is distinct
from native semantic acceptance. No automatic retry/resume/clearance/rollback,
signal/reservation/direction enforcement or train-traversal claim. P18 remains
compatible with its original six-movement brief/hash and receipt format.

126client tests pass, including malformed/stale/partial receipts, unsupported direction
matrices and intended-connector/junction checks. Build40408 demonstrated all eight
routes at(3500,6500,33),heading-50, after explicit observed-stage continuations.
Fresh-process switching-layout-inspect repeated acceptance without construction;
52TRACK independent17samples each:radius122.278962>=120,grade0 and region pass.
Three retained100-unit approach pairs/17samples each:spacing4.999844-5.000128.
Wrong required transfer connector and strict200 radius are natively rejected.

The first attempt built five UP fixtures, then stopped at a reference fit below its
selected160limit. The final guide was aligned with its fixed12degree endpoint without
lowering either160reference or120final limits. Explicit --prepared-switching RECORD
reuses only exact freshly inspected matching fixtures from that prebuild failure.
A later DOWN-fanout degenerate fit left completed UP/reference work visible.
Native straight-guide input now uses the actual stored end tangent within the existing
0.001conversion/heading tolerances. The local rounded-chord alternative was rejected
before the fan-out query/build; no tolerance was widened. Original failed receipts stay failed.

Callable continue_switching_layout and CLI switching-layout-continue --execute
--layout-record RECORD --params BRIEF --context CONTEXT accept only that known
prebuild DOWN-fanout failure with completed UP/reference and exact current fixtures.
Fresh reference route/readback is mandatory; only missing DOWN stages run. No blind
replay, general stage resume, crash recovery or automatic continuation is supplied.
The successful current-state receipt proves this assembled layout, not universal
unattended success on every placement. Game-world side-effect history is incomplete.
Geometry is sampled; physical traversal, reservation, signalling and direction
enforcement remain unprobed. Other patterns/transfers are unsupported; P18 unchanged.

## Reciprocal UUDD track choice (P20 demonstrated)

`reciprocal_layout_example.json` retains all eight P19 functions and adds
UP U1:west->U2:east and DOWN D1:east->D2:west. Four through, two outer branch and
four same-direction transfer movements are explicit. Level, increasing-reference
UP, radius120 and retained5m ordered approaches remain the supported domain.
Translation/rotation are supported; switching zones widen. This is not scissors,
slips, opposite-direction switching or a constant5m crossover.

```powershell
python bridge_live.py reciprocal-layout --params implementation/live_python_interface/reciprocal_layout_example.json --evidence .local_runs/reciprocal_plans
python bridge_live.py reciprocal-layout --context context.json --params implementation/live_python_interface/reciprocal_layout_example.json --execute
python bridge_live.py reciprocal-layout --context context.json --params implementation/live_python_interface/reciprocal_layout_example.json --execute --base-layout-record COMPLETED_P19_RECORD.json
python bridge_live.py reciprocal-layout-inspect --context context.json --params implementation/live_python_interface/reciprocal_layout_example.json --layout-record RECORD.json
```

Callable interfaces: plan_reciprocal_layout, publish_reciprocal_layout,
execute_reciprocal_layout, inspect_reciprocal_layout. Offline planning is default.
Execution composes the existing switching layout, two native fan-track extensions
and two single-crossover modules through connect_throat. An explicit matching
completed P19 receipt may be supplied; all eight current routes/ports/junctions
must pass fresh readback before extending it. It is not automatic cached continuation.
Malformed, unfinished or stale base evidence stops before new construction.
The stored native end-tangent guide correction is retained in ordinary base execution.

Return switches use fan local x750 and a unique straight native reference segment
at x1000. Actual reference geometry/direction is read from the verified through route,
then exact native interior attachments are acquired. Fan east interfaces move from
x620 to x1220; reference/branch interfaces stay unchanged. The declared footprint
remains local x[-60,1660], normal[-500,515], with the selected authorised XYZ region.
Incidental map content is redevelopable. Partial effects/unfinished stages stay visible;
no automatic replay, clearance, rollback or crash continuation is supplied.

Fresh inspection requires ten distinct functional ports, ten current three-TRACK
junctions, all ten native TRAIN paths and all four exact built transfer connectors.
Through paths must visit their intended switching/branch junctions. Sampled
radius/grade/region and three100-unit approach spacing checks remain binding.
Receipt hashes establish saved-file consistency separately from native acceptance.

Build40408 demonstration extended the accepted P19 network in one successful
construction invocation, without construction repair: ten fresh-process routes,
66current TRACK edges/17independent samples each, minimum radius122.278962>=120,
grade0 and spacing4.999844-5.000128. Wrong original/return connectors, strict200
radius and an excluded region reject.134client tests pass. The fresh-network base
creation path is composed/tested; this native demonstration reused the matching
P19 base rather than constructing another duplicate site. P18/P19 brief hashes and
receipt formats remain unchanged; older native evidence describes historical state.
No physical traversal, signalling, reservation, direction enforcement or complete
side-effect/save-load identity claim. Detailed evidence remains local under p20.


### Connected layouts (P23)

`bridge_network.plan_layout_network`, `execute_layout_network`, and
`inspect_layout_network` compose two existing, completed parallel/reciprocal layout
receipts. `layout_network_example.json` names explicit UP/DOWN ports and full
movements. Replace its two receipt paths with your own local completed records;
its coordinates describe the demonstrated P21 junction plus a nearby UD equivalent.
For different sites, select compatible free ports and bounded native guide corridors.
No layout is constructed by the network planner itself.

```
python bridge_live.py layout-network --params NETWORK.json --evidence .local_runs/network_plans
python bridge_live.py layout-network --context CONTEXT.json --params NETWORK.json --execute
python bridge_live.py layout-network-inspect --context CONTEXT.json --params NETWORK.json --layout-record RECEIPT.json
```

Offline planning binds canonical parent receipts and explicit direction/function roles.
Execution freshly verifies every local movement and both free link endpoints before
building the two native corridors serially. Inspection is read-only in a fresh process:
it checks current degree-two attachment roles, exact connector chains, all prior local
movements, and the complete ordered UP/DOWN paths through the intended components.
Parent/connector receipts stay local and hash-bound; retain them for later inspection.
Changed identities/receipts or partial/unknown effects stop acceptance; no automatic
replay, resume, rollback or guessed proximity correspondence is provided. An explicit
`layout-network --execute --layout-record PARTIAL_RECEIPT.json` first re-inspects
completed connectors/local movements and builds only missing links. Reconcile pending
native mutation before this command. Only guides for an uncompleted link may change;
completed links, movements, parents and limits remain bound to their original intent.

Supported initial domain: existing level layouts with compatible native endpoint
grade/height, explicit UP/DOWN travel intent and 1�3 guides per link. Native fitting
retains all radius/grade/region checks. Corridor proposals now use a 1.25� native
radius margin to accommodate sampled ARC-to-cubic conversion; the selected minimum
is still checked on realised geometry. This changes proposals, not acceptance limits.
Each connection retains its 4,000-unit length envelope and existing native fit bounds.
Combined route acceptance may select up to 8,000 native units (example:6,000), with
the existing 64-row readback cap. Native pathfinder search itself is not length bounded;
that number is a final acceptance limit, not a search-work guarantee.

Connecting lines can widen and are not asserted to maintain constant parallel spacing.
The selected 65-samples/edge pair-separation screen is a diagnostic/acceptance sample,
not continuous clearance or dynamic gauging proof. Native collision checks still apply.
Direction is declared routing intent, not signalling enforcement; train traversal,
reservations, save/load identity and arbitrary versions remain unprobed.


### Native curved paired connection (P24)

Callable `bridge_parallel.plan_paired_connection`, `publish_paired_connection`,
`execute_paired_connection`, `inspect_paired_connection`: one native UP reference
corridor plus genuine `CUBIC_OFFSET_SPLINE` DOWN alignment. Four explicit project
IDs/endpoint intents supply opposing traffic directions. DOWN construction follows
UP parameter orientation; its intended route runs in reverse.

```
python bridge_live.py paired-connection --params implementation/live_python_interface/paired_connection_example.json --evidence .local_runs/paired_plans
python bridge_live.py paired-connection --context CONTEXT.json --params PAIR.json --execute
python bridge_live.py paired-connection-inspect --context CONTEXT.json --params PAIR.json --layout-record RECEIPT.json
```

Initial domain: level native BaseEdges, equal actual endpoint heights, template
trackDistance5, compatible fixed normal-offset pairs, explicit left/right side and
1-3 native guides. Radius, grade envelope, region, route length and minimum curved
section remain hard limits. Graded or splayed arrangements are unsupported; there
is no new elevation solver, automatic widening transition or tolerance relaxation.
Actual heights are retained. Translation/rotation and both sides are supported by
the contract; native demonstration uses left. Prior corridor/network receipts remain
compatible. The entire connector is the shared section; compatible anchors need no
widening transitions. The retained straight approaches are outside that section.

Native sampling generates the offset; Python does not fit curves. Cubic conversion
is checked before building. Fresh inspection proves exact four attachment IDs,
degree-two TRACK incidence, complete ordered chains, UP/DOWN TRAIN routes and sampled
radius/grade/region limits. It records17samples/reference piece: reference-u, located
offset-u, actual signed normal spacing, tangential residual and positional error.
Curved-section length sums chords of curved reference pieces with >=1degree endpoint
heading change; this is a conservative measure, not integrated arc length. Clearance
is sampled, not continuous or dynamic gauging proof. No signals, reservations,
operational direction enforcement or physical train traversal is inferred.

Partial/unknown builds remain visible; pending mutation stops execution. Inspection
never builds. An explicit `--execute --layout-record FAILED.json` continuation handles
only a reported reference `construction_receipt_incomplete`: fresh unchanged anchors,
free DOWN ports, exact returned UP TRACK chain, full route and geometry are mandatory.
Only DOWN is built; UP is not replayed. It cannot clear an unresolved current-session
journal. Preserve old receipts/journals; after an authorised ordinary mod reload, a
new healthy session must still prove the reference. This is focused semantic
reconciliation, not automatic resume or crash restoration. Other failures require
focused inspection. Native incidental non-TRACK additions are recorded separately
from connector identities. Unknown historical effects remain unknown.


### Curved multitrack corridor (P25)

`bridge_parallel.plan_multitrack_connection`, `publish_multitrack_connection`,
`execute_multitrack_connection`, `inspect_multitrack_connection` support explicit
ordered UD, UUDD and UDUD connections. Each track has a stable project ID, UP/DOWN
intent and two named directed endpoint intents; `reference_up` declares increasing
or decreasing UP traffic relative to construction. Track order advances along the
selected normal side of that construction reference. Opposing traffic is never
inferred from proximity or implemented by changing supplied travel tangents.

```
python bridge_live.py multitrack-connection --params implementation/live_python_interface/multitrack_connection_example.json --evidence .local_runs/multitrack_plans
python bridge_live.py multitrack-connection --context CONTEXT.json --params MULTI.json --execute
python bridge_live.py multitrack-connection-inspect --context CONTEXT.json --params MULTI.json --layout-record RECEIPT.json
```

P24's compatible level/equal-height/native-template-spacing5 boundary applies:
1-3guides, explicit hard radius/grade/region/route and curved-section length.
No graded or splayed transitions, stations, crossovers or train operations are
provided by this corridor. First track uses the native corridor; subsequent tracks
use successive native5m offsets. Fresh acceptance checks every exact attachment,
separate track nodes, ordered connector chains, tangent joins and complete native
routes in declared traffic direction. All neighboring tracks undergo signed-normal
correspondence checks; outer tracks are also checked at10/15m against the original
reference, with the same selected tolerance, to bound sampled cumulative drift.
No Python curve fitting or independent curves labelled parallel.

Spacing and clearance are sampled, not continuous/dynamic proofs. Curved-section
chord length remains a conservative measure. Direction metadata is routing intent,
not operational direction enforcement. Native demonstration is UUDD increasing-UP;
UD/UDUD, reversed UP and other contract combinations have deterministic tests.
Partial/unknown effects remain visible; inspection is read-only. An explicit
`--execute --layout-record PREFIX.json` may continue only an exact acknowledged
incomplete ordered prefix after fresh route/geometry/spacing/attachment inspection
and confirmation that remaining ports are free. Pending journals, unfinished or
unknown mutations, changed plans and completed runs reject. Completed tracks are
not replayed; old records remain untouched. Unacknowledged effects require separate
reconciliation and cannot be promoted to success by this continuation.


### Curved main line with outward branches (P26)

`bridge_branching.plan_branching_corridor`, `publish_branching_corridor`,
`execute_branching_corridor`, `inspect_branching_corridor` compose a completed
UUDD multitrack receipt with two outgoing outer-track branches. The receipt is
hash-bound as DESIGN input; its old native attachment handles are not required
to survive legitimate approach splits. Provide four through and two branch
movements explicitly, using track IDs and named project endpoints.

```
python bridge_live.py branching-corridor --params implementation/live_python_interface/branching_corridor_example.json --evidence .local_runs/branching_plans
python bridge_live.py branching-corridor --context CONTEXT.json --params BRANCHES.json --execute
python bridge_live.py branching-corridor-inspect --context CONTEXT.json --params BRANCHES.json --layout-record RECEIPT.json
```

The example references the local accepted P25 receipt; supply your own completed
main record for another site. The initial domain is level UUDD with straight
outgoing tangent approaches. Explicit lead_length is zero for the original
approach, or100-600native units for a straight native lead; the split lies in
its middle25-75percent. One outward branch belongs to each outer UP/DOWN track.
Native20unit through/branch target stubs are authored from the actual main track resource. The full movements start at
the unchanged entry approach's outer free endpoints and terminate at through/branch outer
free endpoints, including the retained curved corridor and junction approach.
The user-supplied branch target guide names the build attachment; acceptance
includes its20unit stub to the outer endpoint. No signals, stations or train
traversal are implied.

The original curved connector is the retained shared section. Its neighboring
and cumulative normal-offset checks remain binding. Source/target region boxes
in the junction-zone record are observation locators: the tangent approach and
entire divergent branch are excluded from the shared-spacing requirement.
Every final native path must traverse its complete ordered main connector in the
stated traffic direction and, where applicable, the exact current three-TRACK
junction. Through/branch paths must use distinct exits and a common incoming
edge at that fork. All current route geometry has selected radius/grade/region
checks. Native identities come from bounded observations and exact connectivity;
coordinate resemblance alone does not establish attachment or movement.

Inspection reacquires semantic outer roles after native splits/replacements and
records old/current approach handles, current junction incidence and ordered
paths. It does not claim the standalone P25 receipt remains fresh after splitting.
Partial/unknown effects remain visible; there is no automatic replay or resume.
Pending mutation, stale main input or existing target/lead fixtures stop construction
for focused reconciliation. Inspection never builds. Shared spacing and geometry
checks are sampled; no continuous clearance or save/load identity guarantee.

P26 native acceptance passed on build40408: all four through and both outward
branch movements, with exact current three-track forks and retained normal spacing.
Independent fresh46-edge checks used33observations/edge: min radius416.905464,
maximum grade0. Road collisions were resolved by explicit bounded site observation
and authorised exact road removal; no constraint was lowered. Previous failures
and unknown incidental effects remain recorded locally.

An optional explicit lead_record may reuse only a matching acknowledged straight
connection receipt after fresh route/geometry checks; its hash is plan-bound.
For a partial composition, the callable accepts continuation_record, or use:

```
python bridge_live.py branching-corridor --context CONTEXT.json --params BRANCHES.json --execute --layout-record PARTIAL.json
```

The prior canonical main/constraints/movement matrix and each completed branch
intent must match. Fresh inspection must establish all four through routes and
exactly the acknowledged completed forks/branch paths. Those branches are not
rebuilt; only unfinished intent is executed. Unknown pending requests block it.
Changing an unfinished branch is an explicit new brief, never automatic repair.
A remaining isolated target fixture needs explicit reconciliation/cleanup rather
than blind recreation. Completed receipts cannot be continued. No cross-crash job
restoration or complete native mutation history is promised.

For focused site diagnosis, low-level inspect accepts optional site with a native
XYZ region <=400units per axis and up to8XY terrain positions. It retains at most
32BASE_EDGE/TOWN_BUILDING/CONSTRUCTION observations, processes at most256query
callbacks, and reports truncation; other categories are not exhaustively exported.
Low-level clear_obstructions requires authorised:true and1-8exact observed non-TRACK
ordinary edge snapshots plus a bounded region. It checks current identity/geometry,
rejects construction-owned edges, removes named roads using a native proposal and
checks disappearance. It is an explicit map mutation with possible incidental
native effects, never an automatic clearance policy or generic world bulldozer.
Raw diagnostic responses stay in local request evidence.


## Portable complete curved branching layout (P27)

`bridge_complete.plan_complete_layout` prepares a level UUDD brief without a live
client or historical P25/P26 receipts. `execute_complete_layout` authors approach
fixtures, native curved main lines and two outward branches; `inspect_complete_layout`
reacquires current semantic attachments/forks and all six native TRAIN paths.

```
python bridge_live.py complete-layout --params implementation/live_python_interface/complete_layout_example.json --evidence .local_runs/complete_plans
python bridge_live.py complete-layout --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py complete-layout-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
python bridge_live.py complete-layout --context CONTEXT.json --params BRIEF.json --execute --layout-record PARTIAL.json
```

Adapt reference XYZ/directions/guides, outer branch targets, authorised region and
an exact current native seed_edge to the actual site. The seed supplies an existing
track asset/style, not a historical layout prerequisite. Native template spacing5,
compatible level anchors, ordered UUDD and outward tangent leads100-600 are supported.
Overall translation/rotation is supported; no generic routing or station modelling.

The explicit site_policy is observe or clear_roads. Bounded native observations cover
approaches and native fitted control bounds; terrain and unsupported objects are
recorded. clear_roads removes exact observed ordinary non-TRACK edges within the
region. Observations are practical screening, not exhaustive collision/effect proof.
Native construction still decides terrain/structure realisation and validity.

Every stage has local receipts and honest partial/unknown effects. Explicit same-brief
continuation freshly checks acknowledged fixtures and completed stages, skips them,
and adopts only independently proven main/branch progress. Pending requests, missing
receipts, failed fixtures and unclaimed target/lead effects require reconciliation;
they are never blindly recreated. This is not crash recovery. A completed-record
execution returns checked existing state without construction. Use inspection to
resolve stale identities; saved geometry/proximity alone is not attachment proof.

Normal output stays compact. Full observations/native fit controls stay local.
Route/direction/spacing/geometry checks do not demonstrate physical train traversal,
signalling/reservation behaviour, continuous clearance or complete mutation history.


## Graded curved paired and multitrack connection (P28)

Existing paired-connection and multitrack-connection now accept explicit
vertical_mode: native_shared_height_v1 and vertical_tolerance in native coordinate
units, positive and <=min(0.05,spacing_tolerance). Omitting both retains the old
level domain and receipts. Compatible normal-offset anchors share corresponding
heights; reference guide heights/grades and actual attachment grades are binding.
Offset guide grades are derived by the declared length conversion.
UP/DOWN describes route intent, not native direction enforcement.

Python supplies the brief and acceptance. The mod uses native fitted horizontal
curves and CUBIC_OFFSET_SPLINE XY offsets. Spacing is horizontal signed normal,
not constant3D distance or a map-axis translation. For nonlevel tracks it preserves
reference piece-boundary heights and transfers grades using a bounded native-sampled
reference/offset XY chain-length ratio. Actual fixed attachment grades take precedence.
Native cubic height interpolation joins at those heights/grades; sampled interior Z
may differ from the reference only within the explicitly selected vertical_tolerance.
This is a bounded representation transfer, not an exact3D normal offset, new vertical
optimiser or continuous proof. Incompatible joins, endpoints, radius, max_grade,
region, normal spacing or height drift fail; constraints are never lowered.

```
python bridge_live.py multitrack-connection --params implementation/live_python_interface/graded_multitrack_connection_example.json --evidence .local_runs/graded_plans
python bridge_live.py multitrack-connection --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py multitrack-connection-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
```

The example describes four UUDD tracks rising33->39 with a36-height guide and
0.012 reference guide grade. Adapt all endpoint boxes/native coordinates to actual
free graded approaches; the example does not automatically create attachments.
The paired API uses the same optional fields with its four explicit UP/DOWN roles.
Inspection is fresh/read-only and includes current grade/height checks; it never fits
or builds. Keep partial receipts; only explicitly reconciled acknowledged prefixes
may continue. Pending/unknown effects must not be replayed.

Native build40408 demonstrated the four-track composition and both directions.
Nonzero-endpoint-grade P28 cores cannot enter level pointwork; see P29 for level endpoint composition.
Train traversal, signalling, continuous clearance and general save/load identity are
not established. Saved evidence integrity remains separate from native acceptance.


## Portable graded main with level endpoint branches (P29)

Use complete-layout and complete-layout-inspect with
implementation/live_python_interface/graded_complete_layout_example.json. Planning
is offline by default; --execute and a healthy current --context authorise native
construction. --layout-record selects explicit partial continuation or completed
read-only verification without rebuilding; inspection never constructs.

The optional native_shared_height_v1/vertical_tolerance fields reach the existing
four-track core unchanged. Reference start/finish may be at different native heights;
their optional grade field must be zero (omission means zero). All actual endpoint
approaches must also be level. Fixtures, tangent leads and local junctions are level
at each end's own height; the curved shared core alone changes elevation. Explicit
branch targets must match their local junction height. Nonzero-endpoint-grade P28
connections remain supported by the lower-level API but cannot enter this composition.

Native shared-height transfer, horizontal normal spacing and its sampled limits remain
as documented for P28. Exact current paths/forks, actual level junction geometry, core
height/grade joins, engineering bounds and spacing are freshly checked. No sloping
pointwork, new fitter, vertical optimiser, train traversal or continuous clearance
proof is added. Original level complete-layout plans/receipts remain compatible.

```
python bridge_live.py complete-layout --params implementation/live_python_interface/graded_complete_layout_example.json --evidence .local_runs/graded_complete_plans
python bridge_live.py complete-layout --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py complete-layout-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
python bridge_live.py complete-layout --context CONTEXT.json --params BRIEF.json --execute --layout-record RESULT.json
```

Use actual current seed_edge/native coordinates in the brief. Native construction
and explicitly selected clear_roads may alter the authorised disposable map; receipts
retain known/partial effects and do not promise rollback or complete incidental history.


## Portable UD, UUDD and UDUD orders (P30)

The same complete-layout application/CLI accepts ordered UP-DOWN,
UP-UP-DOWN-DOWN and UP-DOWN-UP-DOWN roles. Optional reference_up is increasing
(default, preserving old briefs/hashes) or decreasing. Physical order follows the
selected normal side along the construction reference; UP/DOWN specifies intended
route traversal, not native one-way enforcement. Every track retains explicit
source/target identity. One outward branch follows each outer track's traffic;
no branch crosses an opposing track or changes the shared core order.

Two tracks have two through plus two branch movements; four tracks have four through
plus two branch movements. Fixtures, roles, receipt continuation, shared-spacing and
current fork/path acceptance use the declared count. Increasing/decreasing UP and
left/right are validated before construction. Local junction grades remain zero;
P29's explicitly bounded graded core may connect differing endpoint heights.

Examples: ud_complete_layout_example.json (reversed-UP, level UD) and
udud_complete_layout_example.json (increasing-UP, graded UDUD). All examples use the
existing complete-layout/complete-layout-inspect commands and explicit current native
seed/coordinates. Adapt the brief to the actual authorised site. No new native
pointwork, crossings, signalling or operational direction enforcement is added.

```
python bridge_live.py complete-layout --params implementation/live_python_interface/ud_complete_layout_example.json --evidence .local_runs/ud_plans
python bridge_live.py complete-layout --params implementation/live_python_interface/udud_complete_layout_example.json --evidence .local_runs/udud_plans
```

Use --context CONTEXT.json --execute for construction. Explicit --layout-record
RESULT.json rechecks a completed record without rebuilding or adopts a proven partial
prefix under the existing no-replay rules. Fresh complete-layout-inspect is read-only.
Existing UUDD commands/briefs and receipts remain compatible; unchanged engineering
acceptance evidence is reused. Physical train traversal and continuous clearance are
not established by native route or sampled geometry checks.


## Fixed-interface two-ladder throat (P31)

ladder-layout plans or constructs four parallel approach interfaces distributing to
six aligned destination interfaces. ladder-layout-inspect freshly checks the assembled
native railway. Callable functions are in bridge_ladder.py. The input names actual
free TRACK attachment roles, two explicit groups and twelve directed movements:
each destination has inbound from its group's first approach and outbound to its
second approach. It is not an all-to-all throat or Birmingham replica.

Each group has a native-fitted spine, a widened outbound arm, one merge and two
successive fan turnouts. The outer destination diverges before the inner destination;
route acceptance requires the named exact current turnout nodes in traversal order.
This shared-neck functional alternative avoids assuming crossings or slips. Both
approach tracks may physically carry either direction; intended inbound/outbound is
not native one-way enforcement. Destination tracks are railway interfaces, not stations.

The current domain is level aligned approach/destination fans with parallel declared
construction headings, selected minimum interface spacing and bounded native guides.
Translation/rotation are supported through the supplied native coordinates/directions.
The selected native spine/turnout fitting radii may exceed, never lower, the hard
minimum. Existing native limits apply: 800-unit fit legs, 1,000-unit extension envelope,
3,000-unit corridor envelope and up to three spine guides. Unknown/rejected geometry
is reported, not made successful by lowering tolerances or limits.

The example ladder_layout_example.json uses fixed existing endpoints and explicit
radius120, turnout radius400, widened fan spacing80 and native approach spacing5.
Create or select the ten actual free interfaces in the authorised world first; the
production workflow does not create fixture stand-ins or assume native IDs from pixels.
It binds current exact native nodes and confirms TRACK/type/direction; current edge
handles may change at native splits, while a changed fixed node requires reconciliation.

```
python bridge_live.py ladder-layout --params implementation/live_python_interface/ladder_layout_example.json --evidence .local_runs/ladder_plans
python bridge_live.py ladder-layout --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py ladder-layout-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
```

--layout-record on execution checks an already completed result without rebuilding.
An explicitly supplied partial receipt may adopt only a matching freshly proved
completed prefix, with the next failed stage independently established unbuilt by
no-attempt discovery failure/native pre-build rejection or the existing exact
rejection-reconciliation record.
Unknown outcomes, changed completed stages/roles, stale attachments or pending commands
stop; no blind replay, automatic resume or assumed rollback. Partial effects and
original failed receipts remain visible. Fresh full TRAIN paths prove connections and
turnout transitions, not physical train operation, capacity or signalling.
Observed geometry/route overview is development evidence; sampled acceptance does not
constitute continuous clearance proof or complete native incidental-effect history.


## Compact endpoint-derived planning (P32)

The same ladder-layout/ladder-layout-inspect commands accept
native_compact_two_ladder_v1 briefs. Callable plan_compact_ladder takes ten named
fixed position/travel_direction/kind roles, two explicitly paired groups with ordered
destinations, twelve explicitly approved from/to movements and selected limits.
It derives one native alignment guide, a short outward arm and three ordered turnout
intents per group. Fan locations use selected radii/actual lateral offsets and a
cheap two-arc screening envelope with margin; native fitting/acceptance remains
authoritative. Users supply interfaces and traffic, not hand-authored pointwork.
The saved canonical plan retains the input and deterministic derivation provenance.

Supported domain: level aligned parallel banks 200..800 native units apart; the
outbound approach and explicitly ordered fan lie outward of the inbound/inner track.
Native fitting still determines every curve; derived controls are intents, not a
guaranteed feasible proposal or globally minimal layout. Unsupported arrangements
or native rejections stop honestly. Low-level explicit P31 briefs remain supported.

compact_ladder_example.json selects a low-speed game throat minimum radius60 and
merge100, outer fan200 and inner fan60 fitting radii explicitly, not P31's400. Four approaches
are at5-unit centres. Six station-free destinations have centre offsets0,5,15,20,30,35
(the 10-unit gaps model a requested5-unit platform strip; no platform assets/clearance
are constructed or certified). This bank is centred on the approaches: inner spine
attachments align, the arms widen outward locally and routes return to fixed ports.
The example uses450-unit bank separation; source/output stub lengths belong to the
authored fixture demonstration, not the production planner. Adapt positions/limits
to actual native observations. No arbitrary native entity IDs or local logs required.

```
python bridge_live.py ladder-layout --params implementation/live_python_interface/compact_ladder_example.json --evidence .local_runs/compact_plans
python bridge_live.py ladder-layout --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py ladder-layout-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
```

Explicit partial-receipt adoption and completed-record read-only checking use the
existing guarded ladder mechanism. Report realised longitudinal/transverse footprint
and bank span from native readback; an equal-scale diagram must not conceal spreading.
Native paths prove selected connectivity/turnout traversal, not trains or signalling.

## Observed destination heights and graded approaches (P33)

See [height_ladder.md](height_ladder.md) and height_ladder_example.json for native
read-only planning, construction, fresh inspection and checked-existing use. The
compact pointwork uses observed destination height; four graded external leads
add their own footprint. Current native geometry overrides bounded position hints.

## General movement-set topology inspection (P34)

See [route_set.md](route_set.md) and route_set_example.json. Read-only
route-set-inspect reports exact shared rails (including reverse use), junctions
and endpoints; complete topology-disjoint, overlap or unknown. No capacity claim.
