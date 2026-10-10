# Plan-driven native operator

The operator executes a recorded railway design sequentially using `bridge_live`.
It does not choose topology or call a model. Keep the spatial design/revision under
the railway design procedure; material changes return to the designer. The game
and staged semantic adapter must already be healthy and running.

## CLI and data

Run from this project directory. The core CLI uses only the standard library:

```powershell
python bridge_operator.py status
python bridge_operator.py survey --input site.json
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
Inspect reads are chunked16 edges, terrain reads8 selected points. No silent truncation.
Branch/crossover preparation still has its existing800 local route limit: specify
a step `max_route_length` if the overall review bound is larger.

Ports may supply `grade` along their declared attachment direction. Stub `grade`
follows its construction direction and is bounded by the existing native0.04 limit
and selected `max_grade`. Extension targets use relative z plus origin and explicit
target grade. Structured guides use relative `position`, `travel_direction`, `grade`;
the existing native fitter/preview decides suitability. Nonzero branch/crossover
guide grades require a structured `connect` instead of the level guided recipe.

`connect` adds `source_interior`/`target_interior` for a mixed free/interior or
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
native `original_edge`/`replacement_edges` receipt lineage, retaining old evidence.

Attachment alternatives are an ordered `attachments:[{source,target},...]` list
within designer-authored absolute `attachment_windows:{source:{min,max},target:{min,max}}`.
At most8 attachment×shape evaluations, no inferred permutations. Each complete
native proposal is evaluated; the first accepted prepared proposal is reused.
Candidate receipts/reasons remain in run state and native files. Route order,
profile, corridor and hard limits are not automatically changed. Mutations are
never retried by this search.

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

## Integrated native evidence — 10 October 2026

Challenge03 R5b completed on build40420: standalone level bridge first, normal earth
ramps, native removal and fresh binding across save/load, explicit remaining-work
continuation,4/4 directed paths and both route-bound crossing observations. Native
camera, screenshot-file completion and checkpoint-file completion passed. R4 had
also exercised honest partial review. See railway-design/examples/challenge03/DESIGN.md.
38 operator tests and423 shared-client regressions passed in the standalone-structure
implementation milestone; no code changed for the final native design fitting.

Current attachment limitation: interior discovery accepts only parameters0.05–0.95
of a native edge. This is an adapter restriction, not a proven native turnout rule;
its current no_supported_interior_location error can also cover locate failure.
A role at an existing connected endpoint is not a free/interior port. Inspect the
actual edge and choose a deliberate local alternative; do not label this native
construction rejection. Numeric bounded terrain editing remains unsupported.
