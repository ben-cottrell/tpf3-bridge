# Plan-driven native operator

The operator executes a recorded railway design sequentially using `bridge_live`.
It does not choose topology or call a model. Keep the spatial design/revision under
the railway design procedure; material changes return to the designer. The game
and staged semantic adapter must already be healthy and running.

## CLI and data

For native curve speed feedback, use the existing read-only request:
`client.request('inspect', {'edge_ids':[edge_id], 'movement_speeds':True})`.
Node-owned turnout movements can be read with
`{'edge_ids':[], 'entity_ids':[node_id], 'movement_speeds':True}`. Existing limits
remain16 track edges /8 exact entities. Per entity, speed readback examines at most64
network rows and returns at most16 TRAIN movements with at most4 connections each.
`movement_speeds.rows` contains `network_entity`, zero-based `movement_index`,
`entity_kind`, native `speedLimit` and `curveSpeedLimit`, plus field availability
states. `units` is explicitly `unknown_native_units`; the installed primary Edge
definitions do not establish units. Inspect `available`, `complete`, `truncated`
and each row's `connections_truncated` before assessing a route. These are native
movement limits, distinct from structure asset limits, sampled radius and current
vehicle speed. Include relevant node movements when comparing turnout paths.
This additive readback awaits native qualification at the next adapter reload.

Run from this project directory. The core CLI uses only the standard library:

```powershell
python bridge_operator.py status
python bridge_operator.py survey --input site.json
python bridge_operator.py track-catalogue
python bridge_operator.py plan --input implementation/operator/example_plan.json
python bridge_operator.py execute --run <returned-run>
python bridge_operator.py summary --run <returned-run>
python bridge_operator.py review --run <returned-run>
```

Planning writes local files without construction. Execution constructs the plan.
The example is the tested four-step fixture, not a recommendation to rebuild its
occupied location. Survey and select an authorised site before adapting it.
`--context` selects an existing bridge context; the local default is
`.local_runs/live_python_interface/p02/context.json`.

For sparse disconnected guide tracks, `track-catalogue` / MCP `track_catalogue`
reads the native `streetSystem.getNode2TrackEdgeMap` incidence map once, avoiding a
rectangular map sweep. Optional
input is `{"max_examined_edges":65536,"max_tracks":512,"summary_limit":32}`.
Examined-edge bounds are1..65536, returned external tracks1..512, component summary
limit1..128. Native enumeration deduplicates track edge IDs; only the requested
number of edges is examined. This read-only operation has passed native qualification
on the current game build.

The catalogue excludes every construction-owned TRACK, including station frozen
rails. It returns examined/returned/excluded counts and explicit scan, track and
metadata truncation flags; `complete:false` never claims full coverage. Compact
connected components provide control-point bounds, edge IDs, structure counts,
observed endpoints and named signals. `free:true` comes from native whole-node
incidence, rather than just the returned graph. Component detail lists are limited
to16 endpoints/names/signals; the separate named-signal list is limited to64.
Summary truncation is separate from native catalogue completeness. Full current
geometry/resources/objects and component details overwrite the local
`operator_track_catalogue.json` working snapshot, identified by `evidence`.
No historical catalogue is retained; identities are current-session observations.

For long disposable corridor rehearsals, `corridor-plan --input brief.json` / MCP
`plan_corridor(brief)` compiles one authored data file into bounded local plans.
`corridor-build --run <run>` / `build_corridor(run)` executes them sequentially;
`corridor-status` / `corridor_status` returns compact current progress. No model calls
are made between sections. The coordinator supplies every track position, construction
direction, grade, guide, structure and section region; the compiler does not interpolate
new waypoints or choose railway layout. Planning is offline and submits no native reads.

The corridor brief uses version1, revision, surveyed adapter session, native track
resources, max_grade, explicit stub_length5..60, named waypoints and1..128 ordered
sections. A waypoint maps track names to `{position:[x,y,z],direction:[dx,dy],grade:g}`.
The compiler centres an ordinary native stub on each selected waypoint, once per track;
the specified direction follows construction progress, independently of train running
direction. Existing outer leads may instead provide exact `front` or `back` selectors
`{chain:<binding>,edge_id:<id>,node_id:<id>}` backed by `bindings` edge snapshots.
Each section has `name`, `source`, `target`, an explicit world `region`, and2/4 distinct
`members`. Member fields are `track` plus the existing optional guided structured-connect
settings. Guides use world coordinates. Example section:

```json
{"name":"leg01","source":"w0","target":"w1",
 "region":{"min":[-20,-20,0],"max":[620,40,40]},
 "members":[{"track":"up"},{"track":"down"}]}
```

The native1km plan envelope, ordinary-stub0.04 grade limit, fitting rules and grouped
segment limits remain in force. Offline compilation rejects out-of-region stub ends,
legs whose direct length exceeds800, and proposals requiring more than20
segments; native fitting still decides the actual curve length and segment count.
Every next window imports exact prior stub receipts,
and `port_refs` checks the discovered edge/node against its named binding. Recorded
replacement receipts update carried bindings; invalidated waypoint bindings stop
continuation before another window starts. Native
rejection leaves completed leads/sections and the current child run available for
inspection. `corridor-continue --run <run>` / `continue_corridor(run)` skips an already
built child or executes a still-unattempted child; it never retries an attempted child.
For a stopped child, use existing `continue_layout`/`continue` after inspection and
required reconciliation, then pass its returned run as `section_run` to
`continue_corridor`. Current corridor/child files are working construction state,
subject to the existing temporary-file policy. Route, signal and service acceptance
remain separate work.

Native qualification has succeeded for one four-track corridor section with
NORMAL/TUNNEL/NORMAL legs and exact grouped readback. Full ordinary corridor batches
still require qualification. Reuse its exact retained outer anchors in separate
remaining-work briefs; omit the built section rather than replaying it.

Version1 plans require `revision`, world `origin`, absolute world `region`, named
`ports`, native `track.template`/`track.style`, `max_grade`, `steps` and `routes`.
Port/guide positions are relative to origin; directions are horizontal vectors.
Origin supplies translation; rotate the vectors/positions explicitly for a rotated
design. Version1 defaults retain level stub/end conditions; version2 supports
explicit grades, structures and wider bounded layouts (see below). Selected native
dimensions and constraints govern; it supplies no real-world conversion factor.

| Step | Required fields beyond unique `name`/`kind` |
|---|---|
| `stub` | named `port`, `length`5–60; optional construction `direction` |
| `extend` | `source`, named `target`; optional existing fitter `radius` |
| `connect` | `source`, `target`; optional `guides`, `structures`, `handle_scale` |
| `branch` | `source`, `target`; optional native junction `candidates` |
| `crossover` | `source`, `target`; optional native crossover `candidates` |

References are named ports or `{"curve":"earlier-step","u":0.5}` on a prior
single native curve, with interior parameter0.05–0.95. A multi-edge chain needs
named ports. Port directions describe attachment intent; at free route endpoints
they point outward. Stub construction direction can oppose that direction.
The bounded native discovery resolves actual attachment identity; proximity alone
never establishes connection. Ambiguity/rejection stops the run.

Direction meaning depends on the operation; do not apply a universal target flip.
An existing edge's outward attachment vector points away from that edge at its
endpoint. A travel tangent points along the proposed railway from source to target.

| Operation | Source direction | Target direction |
|---|---|---|
| `connect`, existing free endpoints or replacement boundaries | outward from retained source edge | outward from retained target edge; fitter negates it for arrival |
| `connect` with an interior endpoint | interior side uses travel tangent | interior side uses travel tangent; free side retains outward convention |
| `branch` | travel tangent at interior source | outward from existing free target edge; fitter negates it |
| `crossover` | travel tangent at source interior | travel tangent at target interior; no inversion |
| `extend` | outward from existing source edge | travel tangent at proposed new free end |
| `structure_seed` | virtual span outward, opposite proposed departure | virtual span outward, along proposed arrival |

For an eastward free-end `connect`, the port directions are source`[1,0]`,
target`[-1,0]`. For an eastward ordinary `crossover` from local`[0,0,0]` to
`[35,5,0]`, both port directions are`[1,0]`:

```json
{"ports":{"a":{"position":[0,0,0],"direction":[1,0]},
          "b":{"position":[35,5,0],"direction":[1,0]}},
 "steps":[{"name":"eastward_xo","kind":"crossover","source":"a","target":"b"}]}
```

This is a partial schema illustration requiring fresh native interior identities,
resources and an authorised region. An opposing target travel tangent asks for
different geometry; it is not the free-end arrival convention. Complex geometry
may legitimately have opposing tangents, so no global rejection gate is imposed.

Connect guides have `position`, `travel_direction`, `grade`; structure entries
use the existing native chain contract. Optional diagram `curves` contain cubic
`p0,p1,t0,t1` in local coordinates; these draw intent and do not dictate every
native control. Native candidate/structure semantics remain those of `bridge_live`.
Maximum32 steps, region400 per horizontal axis, route bound800; underlying native
search/read limits still apply. No automatic constraint relaxation.

Routes name required directed connections between free named ports. Review checks
native TRAIN paths and draws an equal-scale actual geometry overlay. Failed or
empty route sets return `needs_attention`; geometry, train operation, visual design
quality and saved-file integrity remain separate conclusions.

Review also accepts a stopped `needs_attention` run when its failed step has known
no-mutation effects and no pending native request or execution lock exists. It reads
fresh geometry and writes actual plan/profile overlays for visual review of completed
families. Missing or ambiguous route attachments are reported as unverified routes.
Incomplete construction always returns `needs_attention`, even if all existing routes
pass; review never changes construction state or resumes work. Uncertain/partial
mutation effects require reconciliation first. Native read failures remain errors.

Version2 `structure_seed` creates one standalone bridge span directly from two named
ports, with no elevated NORMAL stubs or existing attachments. Each port must give
local XYZ, outward `direction` and explicit outward `grade`. Travel from source to
target negates the source outward direction/grade and uses the target outward values.
For example, a span travelling east has westward source and eastward target ports.

```json
{"name":"overpass_seed","kind":"structure_seed","source":"deck_start","target":"deck_end",
 "structure":{"classification":"BRIDGE","resource_name":"::/infrastructure/bridge/stone.bridge"},
 "radius":0,"handle_scale":1}
```

Use the actually observed track/bridge resources and authorised region. This narrow
seed accepts one endpoint cubic (3D endpoint distance and sampled length at most800),
no guides, junctions or replacement. Native preparation evaluates the complete bridge
proposal; execution reuses that accepted session-local handle without refitting.
Readback verifies the exact receipt edge/two new node identities, free endpoints,
track and bridge resources, controls and sampled grade/radius/region bounds. Native
rejection stops before execution; uncertain or mismatched effects remain visible.
Connect ramps afterwards through fresh discovery of the seed's actual free endpoints.
This new branch requires normal staging/load and a native test before it is demonstrated.

Continuation can remove a carried named bridge with `kind:"remove"`, `chain:<name>`,
`allow_structures:true`; ordinary stubs use the same removal step without that option.
Exact current TRACK geometry/resource bindings are rechecked, and removed bindings
are invalidated. No proximity deletion or automatic replay is implied.

## Optional local stdio MCP

The MCP process retains imported Python modules for its lifetime. After offline
operator changes, use a fresh CLI process for construction when the running MCP
module is stale; editing source does not refresh that process. Existing receipt,
continuation and uncertain-mutation gates still apply.

Only this boundary needs `mcp==2.3.0` (`requirements-operator.txt`). This installation
already has `.local_tools/operator312/Scripts/python.exe`; no new dependency or
network service is necessary. Actual protocol use without another model:

```powershell
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py list
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py plan_layout --input plan_payload.json --output .local_runs/operator/plan_reply.json
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py build_layout --input run_payload.json --output .local_runs/operator/build_reply.json
```

`plan_payload.json` wraps the plan as `{"plan":{...}}`; `run_payload.json` is
`{"run":"<returned-run>"}`. Output files are exclusive-create. Non-success
semantic status gives a nonzero client exit code. Stdout decodes the semantic JSON
without the SDK envelope/escaped formatting; full protocol evidence stays unchanged
in `--output`. Responses over4096 UTF-8 bytes return their status and evidence pointer.

Tools: `session_status`, `survey_site`, `plan_layout`, `build_layout`, `run_status`,
`review_layout`, `continue_layout`, `frame_view`, `capture_view`, `save_checkpoint`. Survey accepts
`region` and optional bounded `terrain_points`; frame accepts world `center` and
positive `distance`; save accepts a unique plain `name`.

The local Codex configuration now contains the following entry, using the
[documented stdio settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli):

```toml
[mcp_servers.tpf3_operator]
command = "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12/.local_tools/operator312/Scripts/python.exe"
args = ["-u", "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12/bridge_operator_mcp.py"]
cwd = "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12"
startup_timeout_sec = 30
tool_timeout_sec = 600
```

It preserves other settings. The current chat has not demonstrated a refreshed
tool catalogue; actual SDK stdio calls have passed. This session's sandbox stalled
subprocess protocol startup, while approved local execution worked. That observation
does not authorise permissions/environment repair or require full-access workers.

## Evidence and stop behaviour

Plans, progress and SVGs live under `.local_runs/operator/<run>/`; native request
receipts remain in the existing session evidence directory. Run summaries are
compact. One MCP operation owns the adapter at a time; execution also holds a local
exclusive lock. Use one operator/game owner, not multiple independent servers.

Attempted, completed, failed and interrupted builds cannot be blindly replayed.
Inspect partial effects and receipts before issuing a new approved plan. A retained
run error includes the native status and up to three distinct bounded evaluation
messages (for example `no_accepted_candidate: Too Much Curvature`); full candidate
diagnostics remain in the original native response. A retained
execution lock needs reconciliation; this is not crash-resilient automatic resume.
After save/load, fresh native identity discovery is required; old-session reviews
are rejected. Run evidence is historical, not automatically current world truth.

Camera changes use native APIs. Screenshot completion requires a newly observed,
nonempty stable file; save requires native callback plus observed stable unique
`.sav`. Both record path/size/SHA256. The10-second file observation is finite;
`file_completion_unobserved` is not success. Do not blindly repeat an uncertain
save. Concurrent manual screenshots would make attribution ambiguous, so retain
exclusive game ownership during capture. Saves never overwrite an existing name.

Build40420 demonstration: resource-based first track, two stubs, extension,
connection, both directed routes, camera, screenshot, save and normal reload.
Branch/crossover wrappers reuse existing tested native recipes but were not freshly
built through this new operator fixture. No new train traversal or universal layout
reliability claim. Standalone Lua syntax checking remains unavailable; changed
native code loaded and executed in the game.

Affected checks:

```powershell
python tools/quiet_checks.py --suite operator --label operator-check
python tools/quiet_checks.py --suite live_client --label operator-live-check
git diff --check
```

Use a usable local TEMP/TMP for test fixtures. Keep full logs, local environments,
screenshots, saves and protocol records ignored; no credits are inferred from time.

## Version2: graded and structured plans

Version1 remains compatible. Version2 permits1000 native XY units per region axis,
400Z and review routes up to8000. Surveys subdivide broad/truncated regions, with a
finite64-query limit and deduplicated exact IDs; incomplete coverage fails honestly.
Inspect reads are chunked16 edges. Point-only terrain reads take1..128 selected XY
positions in one native `terrain_samples` request, retaining caller region validation
and exact ordered response identities. Current/base heights come directly from native
terrain; this point-only operation has passed native qualification. No object discovery
or spatial tile sweep is performed. Site/object inspection
still supports its existing8 terrain points. No silent truncation.
Branch/crossover preparation still has its existing800 local route limit: specify
a step `max_route_length` if the overall review bound is larger.

Ports may supply `grade` along their declared attachment direction. Stub `grade`
follows its construction direction and is bounded by the existing native0.04 limit
and selected `max_grade`. Extension targets use relative z plus origin and explicit
target grade. Structured guides use relative `position`, `travel_direction`, `grade`;
the existing native fitter/preview decides suitability. Nonzero branch/crossover
guide grades require a structured `connect` instead of the level guided recipe.

Finish depot branches and other track splitting before placing signals on those
edges. Current split preparation rejects `split_edge_objects_present`; a signal
is an edge object. If sequencing has already caused this concrete blocker, remove
the exact obstructing signal through an authorised supported operation, complete
the branch, then restore/rebind the intended signal against fresh replacement
edge identity. Do not silently discard objects or weaken the split check.

A rejected native proposal is not by itself a bridge defect. Try a finite set of
already-supported representations/handle choices that retain the brief's actual
constraints. `connect` adds `source_interior`/`target_interior` for a mixed free/interior or
two-interior proposal, evaluated together with its through-track replacements.
`representation`/`leg_representations`, `handle_scale`, `fit_radius` and optional
hard `radius` retain the existing native contracts. Up to6 guides and16 segments.
Structures have `classification:NORMAL|BRIDGE|TUNNEL`; bridge/tunnel require an
actually observed `resource_name`. One entry per leg; an entry may have up to3
ordered `spans` with `until_u` ending at1. Native resources are not guessed.

```json
{"name":"graded_connection","kind":"connect","source":"main_turnout",
 "source_interior":true,"target":"branch_mouth",
 "guides":[{"position":[220,25,15.5],"travel_direction":[1,0],"grade":0},
           {"position":[330,-80,15.5],"travel_direction":[0.81915,-0.57358],"grade":0}],
 "structures":[{"classification":"NORMAL"},
               {"classification":"BRIDGE","resource_name":"<observed resource>"},
               {"classification":"NORMAL"}]}
```

This is schema illustration, requiring authored ports/site/resources; it is not an
automatically executable challenge. For a coupled pair, `kind:group` takes2 or4
such members under `groups`, with free distinct attachments only; their complete
proposal is prepared/built together, max20 segments. Native parallel-strip readback
is retained; this does not certify constant normal spacing from map-axis offsets.
The existing native normal-offset path needs an unconsumed mixed prepared reference
and is not exposed as an automatic operation on already-built chains.

`kind:remove, chain:<name>` uses an exact freshly inspected earlier chain/binding,
max16 edges, optional `allow_structures:true`. A `connect` with
`replace_chain:<name>` uses the existing native replacement-chain proposal between
connected external attachments. `bindings` map names to `{"edges":[<observed exact
edge snapshots>]}`; every binding is freshly read/compared before use. Group output
is retained in member receipt order. Multi-edge curve references use sampled native
chain length fractions, or explicit one-based `segment` for segment-local `u`.
Distinct chains require an explicit segment. Through replacements follow exact
native `original_edge`/`replacement_edges` receipt lineage, retaining required lineage while the operation is unresolved.

Attachment alternatives are an ordered `attachments:[{source,target},...]` list
within designer-authored absolute `attachment_windows:{source:{min,max},target:{min,max}}`.
At most8 attachment×shape evaluations, no inferred permutations. Each complete
native proposal is evaluated; the first accepted prepared proposal is reused.
Candidate receipts/reasons remain in run state and native files. Route order,
profile, corridor and hard limits are not automatically changed. Mutations are
never retried by this search.

For optimistic local fitting, `branch`/`crossover` may instead opt into metre-based
`fit_variation`. Keep nominal `source`/`target` references and native `candidates`;
the operator tries nominal first, then nearest offsets along the same named chains:

```json
"fit_variation": {
  "source": {"max_shift":20,"step":5,"direction":"both"},
  "max_attempts":32,
  "max_requests":256,
  "intent":{"max_extra_inflections":0}
}
```

Positive offsets follow the chain's canonical direction; negative offsets reverse
it. `direction` may be `forward`, `backward`, or `both` (default). A crossover may
declare a corresponding `target` window. Named free ends/station identities stay
exact; a branch's free target is resolved once and reused. Segment-local references
stay within that segment. Windows clip to strict chain interiors, with at most512
resolution intervals per end. The final window boundary is included if the step
does not divide its extent. Combined offsets use nearest Euclidean distance,
source before target on ties, positive before negative. Stop at the first suitable
native acceptance; no automatic boundary survey or demolition occurs.

This automates attachment trials validated by the native complete proposal. It
does not reproduce the manual tool's interactive fitting or invent new shape
candidates. Endpoint cubics use the existing scripted controls, whose native report
may say `native_fit_invoked:false`; native proposal acceptance is a separate fact.
`native_parts` retains its existing explicit radius/fit-radius prerequisites.

This mode has no8-position limit. Defaults are32 attachment attempts and256 native
fit/read requests; explicit bounds permit up to256 attempts/4096 requests. Native
shape candidates retain their existing per-proposal limit. Exact chain readback is
cached during this mutation-free search; every native proposal still verifies its
current snapshots. Prepared construction and subsequent readback occur after the
fit budget, and never retry an uncertain mutation. A stopped run needs the existing
inspection/continuation workflow; executing it again is prohibited.

Available prepared `fit.controls` are sampled for the plan region (or an explicit
absolute `intent.envelope`), longitudinal backtracking, and extra curvature reversals
relative to the nominal endpoint-control model. A normal S fan's nominal inflection
is allowed. `intent.longitudinal_axis:[x,y]` overrides the nominal chord axis;
`max_extra_inflections` defaults to0. These are sampled design checks, without new
radius/physics limits or a continuous clearance claim. If explicit intent checks
cannot be evaluated, construction stops before build. Without explicit intent,
missing geometry is reported unverified; native acceptance may still be consumed.
Rejected intent candidates retain session-local prepared handles; existing native
capacity/errors may stop the bounded search. No new native discard API is assumed.

Run state `fit_variations[step]` reports attempt/request counts, requested offsets,
actual offsets derived from selected native attachment parameters, geometry-check
availability and the sampled rejection range. That range is not a proven feasibility
boundary. Manual `attachments` and `fit_variation` cannot be combined.

Numeric local terrain editing is **unsupported**. Normal native construction
cut/fill, or explicitly prepared terrain, is the precondition. Optional
`kind:terrain_check, positions:[[localx,localy],...], absolute_floor:<worldz>` checks
up to128 declared samples before dependent steps. It reports sampled evidence,
not a continuous floor guarantee or terrain modification. No universal floor is
introduced; steep terrain alone is not an acceptance failure.

Planning also writes `profile.svg`; review writes `profile-overlay.svg`. Optional
`profile_axis` (default[1,0]) selects a local projected longitudinal axis, not route
chainage. `profile_exaggeration` defaults4; axes give native coordinate units and
absolute z. Up to8 declared `crossings` supply `name`, local XY `position`, relative
`upper_height`/`lower_height`, `upper_route` and `lower_routes`. Optional absolute
`window` bounds the observation, and `required_structure` defaultsBRIDGE.
Review identifies roles through actual native route entity IDs, then retains local
sampled height ranges, structure/parallel-strip data and shared endpoint-node IDs.
Missing required structure or separate identities gives `needs_attention`.
Centreline differences and distinct local nodes do not certify physical clearance,
all topology or train operation; native proposal acceptance remains separate.

## Explicit remaining-work continuation

```powershell
python bridge_operator.py continue --run <stopped-parent> --input continuation.json
```

`continue_layout` and CLI accept `revision` (must change), optional remaining-only
`steps`, `updates`, `bindings`, `reconciled_step`. Updates are explicit designer
ports/curves/region/profile/crossing/grade/route fields. Omitting steps retains only
unfinished work. Completed step names cannot reappear. The new plan records parent
state hash, session, skipped steps and freshly checked exact geometry; parent run
and receipts are unchanged. Execution rechecks parent/session/bindings.

Only a stopped `built`/`needs_attention` source in the same current session qualifies.
Pending native journal requests block. Unknown/partial mutation effects must first
be reconciled through existing bridge readback; an explicit `reconciled_step:{name,
edges:[<expected exact current snapshots>]}` can carry a demonstrated completed
step after the pending journal is resolved. A later harmless read error cannot erase
earlier mutation effects. External changes require explicit fresh bindings; a
save/load epoch requires a newly inspected design. This is not crash recovery.

Grade02 wrappers/profile/continuation are offline tested; the coordinator's flying
junction will supply their new integrated live evidence. No native scripts/API
bindings, staged files, model loops or host recovery were added by this extension.

## District interfaces and operations

`station-survey --input brief.json` (MCP `survey_station`) reuses the bounded exact
station survey. Large station reads distinguish all frozen entities (including
pedestrian edges) from TRACK entities. Defaults:16384 frozen entities inspected,
2048 confirmed TRACK edges,4096 distinct track nodes,64 external lead edges. Optional
`max_frozen_entities`/`max_frozen_tracks` can lower those budgets. Exhaustion returns
an explicit incomplete outcome with total/processed counts and limits, never success
or silent truncation. The18-position station is not reduced to suit wrapper bounds.

`diagnose --input intent.json` / MCP `diagnose_attachment(intent,mode)` accepts
`free`, `interior`, `connected` or `station_exit`, queries bounded native attachment eligibility and
records full candidate/rejection evidence locally. It distinguishes ownership,
incomplete incidence, direction/location mismatch, unsupported connected endpoints,
split objects/type and locate failures. It submits no native proposal. An eligible
attachment is not proof that a subsequent railway proposal will be accepted.

`station-exits --input brief.json` / MCP `survey_station_exits(brief)` handles a
station with no external leads. It derives degree-one nodes from the exact frozen
TRACK incidence graph, inspects those edge identities and confirms current endpoint
incidence through small bounded queries (at most64 candidate endpoints). Full results
stay local; the summary shows up to8 exits. Empty Lua list tables are normalised only
for declared station array fields. Zero leads does not imply a terrain survey passed.

Use `mode:"station_exit"` for an exposed construction-owned frozen endpoint. Exact
station membership and current single-edge incidence qualify it; terminal association
uses the same frozen TRACK component, not nearest coordinates. This mode supports
deliberate `extend` lead tasks only. After building a lead, resolve a normal external
role from fresh observations. Native construction and TRAIN path acceptance remain
separate from graph association. Existing free/interior ownership rules stay intact.
When terminal `vehicle_edges` is empty, its exact `vehicle_node.entity` may qualify
membership in that frozen TRACK component. The same check qualifies an external
lead through its recorded frozen-edge association; coordinate resemblance cannot.

Register station-associated roles with `register-interfaces --input roles.json` /
MCP `register_interfaces(name,revision,roles)`, for example:

```json
{"name":"mid_west_c","revision":"R1","roles":{"MW_up":{
 "station":{"name":"Mid West C","construction":{"resource":"<observed native resource>","position":[0,0,0]},"terminal_index":1},
 "intent":{"region":{"min":[-1,-1,-1],"max":[1,1,1]},"guide_xyz":[0,0,0],"travel_direction":[1,0],"placement_tolerance":0.15,"heading_tolerance_deg":2},
 "mode":"free"}}}
```

Replace illustrative coordinates/resource with actual bounded observations. The
station name and construction selector must be unique; exact TRACK incidence links
the native candidate to that construction. Position/direction only filter that
qualified set; nearest-point ranking never supplies identity. Optional terminal
selection requires an exact frozen-edge/terminal association. It is a one-based
station-survey index; the returned `operating_terminal` uses the native line command's
zero-based station/terminal indices. This association does not prove a TRAIN path.
Omit terminal selection to retain an explicitly unqualified lead role.

`resolve-interfaces --input selector.json` / MCP `resolve_interfaces(name,revision,names)`
reacquires current identities/topology, even after load; optional `names` selects
only needed roles. Ambiguous, missing or incomplete associations stop. Save identity
remains unknown; this is semantic role reacquisition in the current world, not a
cross-save identity guarantee. Temporary observations stay local; summaries show up to8
roles. Registry revisions bind current roles; discard superseded records after dependent work completes.

Plans can declare `interface_registry`, `interface_revision` and
`role_refs:{"port_alias":"MW_up"}` and omit those ports' coordinate boilerplate.
Planning resolves the used roles and records their exact session/bindings; execution
rechecks them before any mutation. Changed role geometry, session or registry requires
a fresh plan. Material role changes require a new registry revision. Mode must match
the deliberate construction attachment choice; the operator does not change topology.

Version2 adds `signal_chain` for deterministic one-way blocks along freshly inspected
named track chains. Build junctions/depot branches first. Example step:

```json
{"name":"main_blocks","kind":"signal_chain","chains":["main_west","main_east"],
 "forward":true,"spacing":300,"start_offset":100,"end_clearance":100,"max_count":32}
```

Chains must supply a simple connected ordered sequence of at most64 distinct native
edges. `forward:true` follows their declared order, handling reversed native edges;
`false` traverses the whole sequence backwards. For one edge, true means node0 to node1.
Spacing/start offset are positive native distances; end clearance is nonnegative.
Distances use sampled 3D cubic arc length. Placement at an exact native node fails
before construction; adjust the offset. `max_count` is1..64, and an exceeded count
fails before placing any signals. An existing native signal template is still required
by the usual placement preparation. Every signal uses fresh native preparation and
updates exact replacement identities before the next placement. Partial successes
remain in `signal_chains` working state; inspect/reconcile them before continuation,
and never replay an attempted run. This checks signal attachment/orientation, while
intended directed routes still require normal route review.

For large maps, supply optional `seed_id` on `signal_chain` or a `place_signal`
brief. Read-only `operating_inspect` with `{"signal_seed":{"seed_id":232597}}`
qualifies that exact observed signal directly: SignalList, TRACK attachment,
native resource and current revision. Preparation and build recheck it without
global entity enumeration; invalid or stale seeds fail before submission. The ID
above is an example and must be observed in the current map. Without `seed_id`,
the existing bounded global fallback remains and may report search exhaustion.

For an explicitly rejected signal addition, `bridge_live.reconcile_rejected_signal(
client, request_id, prior_observation)` performs one exact target/object read.
It requires the original pre-placement receipt and unchanged target revision,
nodes and complete objects, records the requested addition absent, and never
replays it. Other effects remain unknown. The current explicit rejected callback
clears its native guard; preserve successful placements and prepare only remaining
work afterwards.

`place_signal` and a version2 `signal` brief optionally accept
`"fit_offsets_m":[-2,-5,-10,-20]`. Offsets are sampled metres in the requested
travel direction on the same exact edge; negative values stay earlier in travel.
Supply1..8 distinct finite nonzero offsets within20m. Nominal native preflight
comes first; out-of-edge candidates are skipped, then the first native-accepted
candidate is submitted once. All rejections stop without a command; unknown
build effects stop without retry. Existing-signal replacement remains exact and
cannot use this option. Receipts report candidate parameters, sampled displacement
and attempts; they do not prove a global feasibility boundary.

Signals subdivide a BASE_EDGE into native TRAIN movement rows. Route attachment
selects the unique row at the requested physical endpoint; native continuity,
one-way direction and required-edge checks still apply across the complete path.
Replacement lineage must include endpoint identities because native IDs may be
recycled. Refresh current bindings and requalify affected routes after placement.

Version2 task kinds `signal`, `station`, `depot` use the existing respective placement
briefs/preparation/readback. `operating` uses existing `brief.action` values:
`vehicle_buy`, `line_create`, `line_update`, `vehicle_assign`, `vehicle_stop`,
`vehicle_manual_departure`. `observe` accepts one explicit vehicle/track/signal ID
list (1..16) and performs one read, without simulation or repeated polling. Operating
brief positions are native world coordinates. Basic station placement retains its
existing supported templates/parameters; advanced18-position module assembly is not
added. Primary and up to8 alternative terminals per stop are explicit native choices.

The installed built-in modular passenger template5 is a terminus, not a through
station. Its default head building is at negative localY; the open approach is
positive localY, with world direction`[-sin(angle),cos(angle),0]`. This is a
source-qualified hint for the untouched template, not a universal station rule or
native buildability guarantee. The current catalogue exposes
template parameters; it does not expose an explicit approach-end/buildable-port
field. Registry endpoint qualification establishes identity/incidence, not clearance
past buildings/buffers. Check the selected native template/orientation and actual
proposal; do not infer an API defect or globally reject endpoints from geometry.
Edited modules may change the layout. Replacing/rotating a station requires fresh
group/terminal/lead identities before applying old operating recipes.

Use `{"result":"earlier_task","path":["vehicle","id"]}` for exact prior receipts,
or `{"role":"MW_up","field":"edge_id"}` / `field:"operating_terminal"` for freshly
qualified roles. Forward references are rejected. Vehicle/line updates recheck current
revisions; purchase preparation checks explicit depot revision and selected assets.

Signal `forward=true` requests travel along the current edge's node0→node1
orientation; `false` requests node1→node0. Keep caller tangent calculations in that
convention. The adapter maps native `EdgeObject.left = not forward` and qualifies
`SignalList.edgePr`'s reversed bit as `forward`. Verify intended travel independently; attachment/type/orientation bits alone do not
prove a directed route on the intended running road.

Corrected placement reports `travel_forward`, `native_left` and
`directed_route_verified:false`. Native route acceptance and observed operation
remain separate. An available path may use the opposite running track/crossovers:
require the intended exact corridor edges using existing route `required_edges`
and inspect their direction before claiming the selected running-track policy.
Previously placed signals require explicit fresh-identity replacement after the
corrected adapter is staged and normally loaded; changing code does not repair
existing map signals. Keep only unresolved state needed for correction; discard
completed receipts and temporary route diagnostics after use.
Operating effects remain separate from railway construction: unknown operating effects
block continuation/review even when `game_constructed:false`. Partial effects remain
visible and no rollback/replay is assumed. Observation/purchase/path availability do
not establish a completed train journey, capacity, signalling or visual design quality.

Signal placement updates named track bindings from the native exact edge-replacement
receipt and fresh readback; later tasks must use that current identity.

Plain approach coalescing is an explicit version2 `connect` task with
`replace_chain:"named_exact_chain"`, `coalesce_plain:true`, and
`replacement_boundaries:{"source":{"anchor_edge":ID,"edges":[outside snapshots]},
"target":{"anchor_edge":ID,"edges":[outside snapshots]}}`. Each boundary names
its primary retained edge and all1..2 outside TRACK edges. The removed chain is
1..16 exact edges; internal nodes must remain exclusive degree two. Boundary nodes
may be degree two or three only with this complete opt-in evidence. An added or
missing outside edge, owner or stale snapshot stops preparation. Generic free/
connected selection and default replacement degree-two rules are unchanged.
The local octree may return only a removed-chain edge at a boundary. Complete
exact node incidence can establish that boundary; fresh inspection of the named
retained primary supplies its native outward tangent and geometry. The witness's
edge/direction is not substituted for the primary, and no proximity identity or
larger query region is needed. Repeated witnesses for the same exact node agree
on one attachment rather than creating spurious ambiguity.

This mode allows only collinear NORMAL track with unchanged resources, no guides,
one NORMAL structure, endpoint-cubic representation and handle scale1. Original
Bezier controls must lie monotonically on the boundary line within the existing
0.001 native snapshot tolerance. Runtime fresh inspection must establish NORMAL;
an offline recipe with missing old metadata cannot waive that check. Native
preparation/execution rechecks the same exact chain/outside snapshots. After build,
each boundary must retain all outside edges/geometry and exactly one new chain
edge; the receipt reports actual incidence, including the third edge. Only internal
chain nodes are removed. This is coalescing, not a general degree-three junction
replacement or implicit branch deletion. Native acceptance and any benefit to
crossover fitting require a specific native experiment.

RN qualification is a separate input-direction lesson: run`9288f7b2af0d4790`
on the same build/session built both original35-unit crossovers after changing only
their target travel tangents to match departure (14calls,7.031seconds native-call
time). No merge, longer crossover or station move was used. The prepared RN merge/
50–45-unit alternative remained unused. This isolates the earlier RN rejection to
the mistaken free-end target convention; it does not extend the north segmentation
conclusion to RN. South coalescing`156bd800a9394ae5` and mirrored crossovers
`9a2f100b55e9481c` also succeeded; these are specific native fixtures, not a new gate.

`station-routes --input routes.json` / MCP `review_station_routes(brief)` reviews
up to8 named `arrival`/`departure` paths. Brief fields are registry `name`, `revision`
and `routes`; each route has `name`, `purpose`, `source`, `target`, `max_length`.
Endpoints require native `guide_xyz` and explicit travel direction. Arrival target
or departure source also names a registered terminal `role`. This reads the role's
construction/terminal selector directly and freshly qualifies its exact frozen
TRACK component; it does not resolve an obsolete free/station_exit build attachment.
An opposite buffer end is a valid directed path endpoint. Current connected leads
and construction ownership do not disqualify this read-only terminal check.
No nearest identity or free-port buildability is inferred.

Each role endpoint may specify `registry_name` and `registry_revision`; omitted
fields independently default to the brief's `name` and `revision`. Distinct
registries are loaded once each and their exact revisions checked. Station
identity/frozen surveys are reused by station name. This permits connected
station-to-station review without re-registering construction roles as free ports.
For example, a route's endpoints can use:

```json
{
  "source": {"role":"C_up", "registry_name":"mid_west_c", "registry_revision":"exposed_leads_R1", "guide_xyz":[0,0,0], "travel_direction":[1,0]},
  "target": {"role":"RN_primary", "registry_name":"district04_destinations", "registry_revision":"R1", "guide_xyz":[100,0,0], "travel_direction":[1,0]}
}
```

These coordinates/role labels are illustrative; use registered role names and
current terminal endpoint geometry. Registry overrides require `role`; ordinary
free-boundary endpoints retain their existing discovery/ownership checks.

For an explicitly rejected resource-seeded `test_approach` fixture, use
`bridge_live.reconcile_rejected_fixture(client)` or fresh CLI `reconcile-fixture`
with empty params and the current context. It verifies saved request/session/error,
finite seed/resources/native bounds and a complete bounded zero-TRACK footprint.
An anchored fixture still requires its original `discovery`. Reconciliation sends
only reads, preserves unknown other effects and never replays construction. It
closes Python pending evidence; the native mutation guard remains until normal
save/load. Original operator uncertainty is retained and blocks direct continuation.

For an already-built structured replacement left `mutation_unverified`, use
`bridge_live.reconcile_constructed_replacement(client, original_client=None,
acceptance_revision={"original_request": "<build request>", "max_route_length":
2000, "reason": "<explicit reason>", "authority": "<authoriser>"})`.
The number is illustrative, not an automatic relaxed default. Native route length
covers the complete boundary-to-boundary path, including retained approach edges.
The helper only reads current state: exact prepared controls/structures, sampled
engineering bounds, original edge removal, preserved outside geometry and boundary
incidence, then native TRAIN route with every replacement edge required. It records
the original/revised criteria and source hashes; failed proof leaves pending intact.
It never rebuilds, refits or rewrites the original receipts. Success clears only
the original Python journal. It does **not** clear the native mutation guard:
perform normal authorised save/load and reacquire the current session before further
mutation, confirming the fresh adapter is usable. No process restart is implied.

An already-built interior branch has the same explicit readback-budget option:
`bridge_live.reconcile_constructed_interior(client, original_client=None,
acceptance_revision={"original_request":"<build request>", "max_route_length":2000,
"reason":"<complete movement exceeds the original readback budget>",
"authority":"<authoriser>"})`. Only that readback criterion may change (up to
8000 native units); source/target identities, prepared shape, region, radius and
grade remain unchanged. Native verification must still prove both split movements,
exact junction identity and branch geometry. Failure retains pending; success clears
only Python pending and still requires normal save/load before another mutation.
The new curve's existing construction length limit remains unchanged.

Optional endpoint placement/heading tolerances default to0.15/2degrees. Geometry
only filters exact terminal-component endpoints. Explicit travel direction determines
entry versus exit orientation and is checked against current edge tangent. Ordinary
outer boundary endpoints omit `role` and use fresh free-boundary discovery. The
existing native TRAIN route check requires both current endpoint edges and reports
actual direction/length acceptance. Missing/ambiguous/incomplete or changed station
state stops review. Summaries show at most4 routes; full responses stay local.
Terminal review requests `lookup_scope:"identity_frozen"`: station group,
construction, terminal and frozen TRACK identity only, without walking the growing
external district. Both identity/frozen completeness must be true. Default external
station surveys and interface registration retain their64-edge external bound and
reject incomplete reads; identity-only data cannot qualify an external role.
An explicit identity-only station survey reports external ports as unobserved,
not zero. No external graph limit is raised for this fix.

Route review explicitly defaults `max_path_entries` to256 because a station path
can already exceed120 native entries before its external approach. Brief may select
1..512 entries; overflow is `routes_unverified` with actual count/truncation evidence.
Ordinary route API calls retain64 unless an explicit limit is supplied. These limits
bound returned/processed observations, not the native pathfinder's internal search.
This establishes native directed path availability, not line operation, train arrival,
stopping behaviour or physical traversal. Saved-file integrity remains separate.

The coordinator demonstrated the station-only read repair and a30-unit extension
from exact frozen station node69229/edge71764, producing edge45887/node45876 with
connected readback. This demonstrates that attachment on that build/context, not
train traversal or all exits. The complete operator additions and split diagnostics
still require the coordinator's normal staging/load and specific qualification; no new API,
dependency, physics, server, watchdog or environment recovery is introduced.

Completed working records and diagnostics are disposable. Keep only current functional
state; remove completed logs and superseded plans after use.
