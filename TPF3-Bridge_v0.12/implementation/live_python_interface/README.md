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

The first authored layout and three fit-only variants were rejected because a native
leg contained reverse geometry. A distinct gradual-bend layout passed; no constraint
was relaxed and rejected inputs remain rejected. Only forward native pieces are
supported, not arbitrary guide arrangements or unrestricted routing. Actual node
identities are acquired from the build receipt/readback, never fit placeholders.
The initial automatic-review denial was resolved by the user's explicit approval;
two short disposable target fixtures and one coherent corridor were built. There is
no transaction/rollback claim. Full failed/successful receipts remain local.
