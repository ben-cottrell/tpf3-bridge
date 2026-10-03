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

29client/fake-worker tests passed;14unchanged quiet-runner tests reused. Run:

```powershell
python tools/quiet_checks.py --suite live_client --label live-client
```

Raw acceptance logs are intentionally local, not required to use the source.
`STATE.md` identifies reports. Unprobed: train traversal, continuous geometry proof,
native save/load identity, arbitrary-version compatibility and production transport.
Detailed station modelling and train physics remain outside this milestone.
Usage unavailable; no invented credit savings.
