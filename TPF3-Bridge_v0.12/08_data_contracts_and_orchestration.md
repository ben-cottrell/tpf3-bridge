# Data contracts, orchestration and low-usage control

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Current integration:** v0.6 addendum at the end of this document; earlier sections retain their version-specific status. Current execution evidence is in [25](25_v06_execution_report.md).

Version **0.3.0** · 20 September 2026 · Status: **proposed interfaces, not implemented APIs**

## 1. Contract principles

Astra should send intent and receive decisions. Python should keep geometry, route enumeration, event traces, solver iterations and repair loops local. The game adapter should expose only the capabilities actually available and report authoritative realised state.

Use a transport-neutral, versioned message protocol. A local socket, file-based exchange or another game-compatible mechanism can implement it after the mod environment is tested. Do not assume Lua has unrestricted filesystem/network access or that TPF3 supports atomic construction transactions.

Official TPF3 material describes path-based reservation and alternative routes, plus modding features. That does not establish route inspection, route forcing, detailed passenger telemetry or any particular construction function. These remain capability probes. [S001](10_source_register.md#s001)

## 2. Core records

| Record | Essential fields | Important invariant |
|---|---|---|
| `DesignBrief` | ID/version, mode, profile, boundary, movements, service groups, passenger goals, hard constraints, preferences, authority limits | Explicit user constraints cannot become silent defaults. |
| `WorldSnapshot` | Topology/terrain/asset revisions, coordinate transform, region, observation cursor, completeness | Dynamic train observations are not the same revision domain as static topology. |
| `EvidenceClaim` | Source/locator, scope, valid period, claim kind, units, confidence, review state | A current retrieval timestamp does not make an old layout current. |
| `StationComplex` | Stable ID, rail subsystems, levels, passenger graph, display aliases | Shared station identity never implies train connectivity. |
| `PlatformRoad` | Track interval, edge IDs, berth configurations, route eligibility | Display labels are not independent capacity resources. |
| `PlatformEdge` | Geometry, boarding interval, height/offset profile, obstacles, access links | The edge and the full track length can differ. |
| `BerthConfiguration` | Train fit, stop interval/tolerance, maximum occupation, required permission/protection | Simultaneous use requires an explicit applicable model. |
| `RouteDefinition` | Ordered rail ports/segments, point requirements, resource footprints, release profile | Geometric reachability is necessary but not sufficient. |
| `TrainActivity` | Train profile, incoming/outgoing working, routes, berth, readiness, passenger exchange | The next departure must have actual or explicitly assumed stock. |
| `PassengerCohort` | Time-dependent origin/destination, service links, mobility profile, access eligibility | An unrestricted shortest path does not establish an accessible path. |
| `CandidateDesign` | Brief/snapshot refs, topology, geometry, patterns, checks, assumptions, footprint | A candidate is not a constructed or observed result. |
| `ExecutionPlan` | Authorised region, expected revisions, staged operations, capability refs, recovery policy | No unsupported rollback guarantee. |
| `DecisionPacket` | Status, material alternatives, bottlenecks, trade-offs, missing decisions, trace refs | Summaries preserve unknowns and failed required checks. |

## 3. Stable identity and platform aliases

The following is an illustrative schema instance, not a measured station:

```json
{
  "schema_version": "0.1.0",
  "station_complex_id": "synthetic_complex_01",
  "rail_subsystem_id": "surface_passenger",
  "platform_road_id": "road_7f2a",
  "platform_edge_id": "edge_91c0",
  "aliases": [
    {
      "label": "0",
      "valid_from": "synthetic_epoch_1",
      "valid_to": null,
      "evidence_kind": "synthetic"
    }
  ],
  "boarding_interval_m": [20.0, 260.0],
  "stopping_tolerance_m": null,
  "split_occupation": {
    "permission": "unknown",
    "enabled": false
  },
  "engine_entity_ids": [],
  "engineering_assessment": "unassessed"
}
```

`null` is not a zero-length tolerance and not a pass. A physical edge may have several valid aliases; alias reuse across historical snapshots must not merge different assets. Engine IDs may change after a rebuild, so keep a reconciliation map with lineage.

## 4. Rule record

```yaml
rule_id: UK_PLATFORM_INTERFACE_PENDING_001
kind: engineering_requirement_candidate
source_id: S043
source_issue: "2.2"
clause_locator: null
applicability:
  profile: gb_conventional_passenger_modern
  scope_status: pending_review
quantity: platform_interface_constraint
value: null
units: null
verification_status: catalogue_only
executable: false
on_missing_evidence: unassessed
```

This illustrates why a source register alone is not a rule engine. A future verified rule also needs the exact condition, comparison operator, exception handling and input requirements. A game heuristic uses a different `kind` and cannot masquerade as this rule.

## 5. Capability manifest

```json
{
  "schema_version": "0.1.0",
  "adapter_id": "proposed_tpf3_lua_adapter",
  "game_version": null,
  "mod_version": null,
  "capabilities": {
    "query.track_geometry": {"state": "unknown", "evidence": []},
    "query.route_reservations": {"state": "unknown", "evidence": []},
    "query.passenger_flows": {"state": "unknown", "evidence": []},
    "construction.track_alignment": {"state": "unknown", "evidence": []},
    "construction.specialwork": {"state": "unknown", "evidence": []},
    "construction.grade_separated_crossing": {"state": "unknown", "evidence": []},
    "construction.station_modules": {"state": "unknown", "evidence": []},
    "control.train_reversal": {"state": "unknown", "evidence": []},
    "control.alternative_platforms": {"state": "unknown", "evidence": []},
    "transaction.atomic_commit": {"state": "unknown", "evidence": []},
    "transaction.rollback": {"state": "unknown", "evidence": []}
  }
}
```

These are **proposed bridge capability names**, not TPF3 API identifiers. `supported` requires evidence appropriate to the claim, ideally a reproducible adapter probe on a named version. Parameter ranges and representational limits belong in the manifest as well as the yes/no state. A feature can be available in the UI but unavailable through the mod API.

## 6. High-level agent interface

The proposed MCP-facing tools should be few and domain-oriented:

| Proposed tool | Input | Default output |
|---|---|---|
| `rail.design_station_area` | Brief, region/snapshot reference, search budget | Decision packet and local candidate references |
| `rail.revise_design` | Candidate reference and approved brief changes | Revised alternatives and changed-check summary |
| `rail.explain` | Result reference, question or diagnostic category | Bounded explanation with evidence/trace pointers |
| `rail.commit_design` | Approved candidate, authority token, expected revisions | Staged execution status and realised checks |
| `rail.observe` | Region/result reference, observation window, summary policy | Compact bottleneck/performance digest |
| `rail.cancel_job` | Job reference | Cancellation/recovery status |

Primitive track operations remain internal or available as explicit diagnostics. They should not be the normal agent interface for designing a major station.

## 7. Local orchestration state machine

Use explicit states:

`received → brief_validated → evidence_resolved → topology_candidates → geometry_fitted → engineering_checked → operations_tested → passenger_tested → decision_ready → approved → execution_preflight → staged_execution → realised_validation → observation → completed`

Branches include `awaiting_decision`, `unassessed`, `not_representable`, `search_exhausted`, `proven_infeasible_within_model`, `stale_snapshot`, `partial_failure` and `cancelled`.

Not every task needs every expensive stage. A quick feasibility query can stop before detailed passenger simulation or construction, but its status must identify the omitted checks. No candidate may skip a required hard check merely to reach `completed`.

### Budget policy

Allocate local budgets by stage: candidate count, solver evaluations, elapsed compute time, game construction attempts and observation volume. Values are configuration choices to benchmark, not UK engineering standards or claimed current performance.

Use cheap rejection and memoisation before detailed simulation. Stop repairing a fundamentally wrong topology; try another permitted family. When all bounded options are exhausted, send Astra the smallest material choice that can change feasibility.

A long-running local job should not require Astra to poll every solver iteration. Use host-supported completion events where available; otherwise expose a bounded status query and keep all intermediate work local. This is an application design requirement, not a claim that the current chat session can run unattended jobs.

## 8. Idempotent execution and partial failure

Bind the execution plan to static topology/terrain/asset revisions. A moving train's timestamp should not invalidate an unrelated geometry plan, but occupancy relevant to a live edit must still be checked.

Each operation receives a stable operation ID, dependency list, intended effect and expected preconditions. Record submitted, acknowledged, realised and verified states separately. On timeout, query/reconcile the operation before retrying. An acknowledgement missing from the connection does not prove the game failed to act.

Where the engine lacks rollback, use approved checkpoints and compensating operations. A compensation may fail or be lossy; report that explicitly. Never describe demolishing newly built infrastructure as a guaranteed restoration of the previous world state.

## 9. Decision packet example

The following contains **illustrative statuses only**; no solver or game has produced these results.

```json
{
  "packet_kind": "example_only",
  "brief_ref": "synthetic_station_brief_v1",
  "result_ref": "example_result_01",
  "status": "awaiting_design_decision",
  "summary": "Two topology families remain within the synthetic brief.",
  "alternatives": [
    {
      "candidate_ref": "example_grouped_throat",
      "trade_off": "Smaller footprint; fewer recovery movements."
    },
    {
      "candidate_ref": "example_split_approach",
      "trade_off": "More approach space; additional independent movement."
    }
  ],
  "material_question": "Prioritise the smaller footprint or the additional recovery movement?",
  "engineering_status": "unassessed_pending_rule_import",
  "game_status": "not_tested",
  "trace_ref": "local_result_store/example_result_01",
  "source_refs": [],
  "synthetic": true
}
```

An actual packet should include the principal tested scenarios and a small number of key metrics with units, uncertainty and measurement origin. It should not include every rejected segment or every event in a train simulation.

## 10. Observation and caching strategy

Use spatially indexed world queries and changed-region updates where the adapter supports them. Cache geometry and resource definitions separately from dynamic train observations. Invalidate dependent results when a relevant train profile, rule issue, source claim, topology, terrain, capability or solver version changes.

A normal observation digest should identify changed bottlenecks, unserved required movements, residual queues, platform conflicts, passenger-access issues and model/engine mismatch. A full trace is retrieved only when needed to resolve a decision or diagnose a failed invariant.

## 11. Measuring actual Astra usage savings

Compare the same accepted design tasks through a primitive-operation workflow and the proposed high-level workflow. Hold model configuration, completion criteria, game scenario and starting world as constant as practical. Record failed attempts as well as successful runs.

Measure model calls, messages, text/visual observations, tokens where available, elapsed agent involvement and actual plan credits when observable. Also measure local compute, accepted-design rate and engineering/game failures. A reduction in tokens is not automatically the same percentage reduction in plan credits.

No savings percentage is claimed in this specification. The target is structural: model involvement should grow mainly with material decisions, not track count, candidate count or routine repair iterations.

## 12. Local control security

Keep the command surface local by default and authenticate any exposed endpoint. Validate schemas, operation allowlists, world revisions and edit boundaries. Do not expose arbitrary Python execution, Lua evaluation or filesystem writes as ordinary game-control commands. Record who/what authorised a destructive edit and provide a cancellation mechanism.

Evidence imports and mod responses are data, not instructions to change the assistant's permissions or run arbitrary code. The bridge should reject unexpected command fields rather than attempting a permissive interpretation.

## 13. Version 0.2 data contracts and migrations

The examples above remain proposed full-bridge interfaces. The standalone proof uses its own explicitly restricted `0.2.0` fixture contract and does not implement an MCP server or game transport. Do not point an agent at its internal functions as though they were authorised world-editing tools.

### 13.1 Integer time and distinct geometric units

Proof times use nonnegative integer milliseconds. Floating times, booleans and negative durations are rejected. Resource intervals are half-open: `[start_ms, end_ms)`. Exact endpoint contact is compatible; a one-millisecond overlap is not hidden by an epsilon.

Lengths are metres; cant magnitude is millimetres; curvature is inverse metres; angles in the future geometry contract are radians. Straight geometry is represented explicitly, not by serialising floating infinity as a radius.

The proof's `read_fixture()` rejects unknown top-level fields and unknown fields in typed platform/visit records. Its scenario IDs are constrained before use in output filenames. The CLI reads only local JSON and writes results; it exposes no remote execution endpoint.

### 13.2 Minimal executable fixture contract

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | Exact string `0.2.0` | Proof contract, not a TPF3 API version |
| `fidelity` | Exact string `synthetic` | Prevents accidentally relabelling a real station as assessed |
| `scenario_id` | Restricted string | Stable fixture/result identity |
| `platforms` | Typed records | Physical IDs, labels, bank, usable length and explicit margins |
| `visits` | Typed records | Corridor pair, formation length, times, stock dependency and outgoing activity |
| `closed_platform_ids` | Unique ID list | Whole-experiment platform availability; not a throat closure |
| `horizon_ms` | Positive integer | Reporting cutoff, not permission to drop unfinished work |
| `max_wait_ms` | Nonnegative integer | Bound on entry scheduling relative to the requested entry |
| `evaluation_budget` | Nonnegative integer | Local event-search work limit |
| `description` | Text | Origin and scenario interpretation |

The default route resources and surrogate travel parameters are presently defined in code and described in [12](12_worked_station_design.md). A production API must move them into a versioned, validated geometry/resource profile. This is an intentional proof simplification, not a recommended permanent hard-coding pattern.

### 13.3 Stock and activity identity

A visit refers to one stock identity. A repeated visit requires a predecessor, the same stock identity and formation length, and an explicit positive external-cycle duration. The proof rejects duplicate independent roots, missing predecessors, forks and cycles. It does not implement coupling, splitting or substitution.

The external-cycle duration is an assumed time beyond the model boundary. It prevents instantaneous reuse but does not prove an actual depot/line journey exists. Production records must replace it with a modelled movement chain when that journey affects the design.

Passenger departure and empty-stock departure retain different activity labels but both reserve railway resources. Passenger counts are not used to decide whether a train occupies track.

### 13.4 Return status rather than ambiguous success

The proof reports `required`, `scheduled`, `completed_within_horizon`, `scheduled_residual` and `unscheduled` counts separately. `all_required_scheduled` does not imply completion before the horizon.

Unscheduled reasons distinguish no legal complete opportunity in the declared family, a blocked predecessor, an entry-wait bound and exhausted computation. The last two do not prove physical infeasibility.

Every result carries per-domain assessments. The current whole-station geometry, passenger circulation, spatial queue spillback and UK engineering statuses are unassessed; game construction and observation are not tested. These fields are present in JSON, not just caveats in the accompanying prose.

## 14. Production orchestration: compile once, repair locally

The future `rail.design_station_area` operation should accept an immutable brief and return a job/result reference. A local process performs family search, fitting, validation, scenario evaluation and bounded repair. Intermediate candidate failures stay in the local trace store.

A production decision packet should contain the remaining materially distinct alternatives, required-activity completion, important delay/queue results, geometry/capability gates, unresolved source questions and a limited approval request. It should not contain thousands of resource events.

The proof emits a compact packet with a fixed next-stage instruction and links to its actual comparison results. It does **not** yet perform general Pareto selection or formulate an autonomous design recommendation. The separation between small packet and full trace is demonstrated; the full decision engine is specified, not implemented.

### 14.1 Cache keys by dependency domain

Use distinct hashes for canonical topology, geometry, train/operating profile, static resource compilation, dynamic scenario and solver configuration. A full evaluation key references all of them plus rule/evidence/capability versions. Do not include display-only labels in physical identity, but retain label versions for user-facing explanation.

The proof records SHA-256 hashes of its actual fixture bytes and code in its acceptance record. It does not yet implement a persistent cache or incremental invalidation. A hash in a report is provenance, not proof that caching is correct.

### 14.2 Comparison integrity

Before comparing candidate results, verify their scenario ID/hash, demand, horizon policy and train profiles. A family with a closure-induced shortfall cannot appear to win because its delay total excludes the missing trains.

Filtering by hard completion requirements must precede preference scoring. Where none completes the required work, retain the shortfalls and return a redesign decision; do not lower the demand invisibly. Geometry and game unknowns remain gates outside that provisional operating comparison.

### 14.3 Implementation handoff

The offline package runs with the Python standard library and no game connection. A later development environment can reuse the fixture data, invariants and contract tests, then replace the hand-authored resource templates with the geometry compiler. Keep the proof as a regression reference rather than extending it indefinitely into an unstructured production engine.

No actual model-plan credit saving has been measured. The runner makes no model or game API calls; that verifies its local execution structure, not the billing effect of an eventual agent workflow.

## 15. Version 0.3 compiler and result contracts

The legacy proof fixture remains `0.2.0`; the geometry fixture is `0.3.0`. The two output families are not silently merged. `railgeom` is a local Python library/CLI, not a new public MCP tool or TPF3 API.

### 15.1 CompiledRoute

A compiled route has `id`, `start`, `end`, ordered `edge_ids`, `length_lower_m`, `length_upper_m`, typed `requirements`, `source_hash` and per-edge direction/chainage brackets in `segments`. An empty or illegal path is rejected before scheduling. Distances come from the instantiated geometry, not a family-name lookup.

A requirement has `resource` and optional `state`. An absent state identifies exclusive occupation; a state identifies declared compatible-state locking. The calendar still checks exclusive running space separately. A controller ID is an explicit logical relationship, not a rounded coordinate.

### 15.2 CompiledAssembly

The assembly exports its source and compile hashes, route dictionary, per-edge requirements, platform/storage records and a provenance record. Provenance retains original topology, curve bounds, pair witnesses, profile values and per-domain assessments. `continuous_corridor_proxy: compiled` does not mean `full_vehicle_gauging: pass`.

The physical source hash and compile hash are distinct. The latter includes the profile, route requests and platform contract as well as the source geometry. Reusing a curve-evaluation cache is not proof that a previous schedule or whole-world observation is still valid.

### 15.3 Stop and storage contract

The fan's marker identifies the arrival rear and reversed departure front. Storage-edge occupation is held across the complete visit. A different stopping policy must change the contract and timing generation; it must not be introduced merely by moving a display label.

The geometry-backed scheduler currently accepts only the fan's single group-A approach semantics. An unsupported second corridor is rejected rather than treated as connected. This protects the original four-approach brief from silent simplification.

### 15.4 Local fit result

The finite fitter returns the explored parameter grid, evaluations, fitting candidates and selected candidate, plus one of `candidate_found_in_enumerated_set`, `no_candidate_in_enumerated_set` or `search_exhausted`. Failures retain their geometric reason and scope. The production tool should keep that trace local and surface only a consequential decision.

The demo packet includes result references and unresolved assessments. It has no authorisation token for game edits and makes no claim of measured plan-credit savings. A future commit stage must still pass source, capability, world-revision and realised-geometry checks.

## Version 0.4 contracts: numerical kind, motion and release

The new `0.4.0` fixture remains explicitly `synthetic_geometry_with_separate_UK_reference_checks`. Its fields are `geometry_profile`, `fan`, `access`, `motion`, `visits` and `scenarios`, with a description and version. The strict reader rejects unknown fields, invalid/duplicate scenario names, noninteger times and malformed closures. [Fixture](proof/sectional_fixtures/release.json)

`NumericalParameter` contains ID, value, units, kind, source/issue, locator, applicability and review status. Lookup outcomes distinguish `reference_value`, `guidance_calculation`, `pass`, `fail`, `not_applicable` and `unassessed`. A sufficient curvature bound that cannot certify returns `not_certified_by_bound`, not an exact geometric violation.

`Motion` contains total path distance, stopping condition and constant-acceleration phases. `ResourceFootprint` contains canonical resource/state, first/last chainage and contributing edges. `Leg` binds these to train length, profile and release mode, exporting both physical-occupation approximations and actual model-lock intervals. All route locks start at activation; no just-in-time acquisition is hidden in the new schema.

Geometry remains compiled by the unchanged `0.3.0` kernel. Its new exported wrapper identifies that version and replaces inherited historical timing text with an explicit separate-assessment marker. Geometry hashes bind geometry inputs; scenario, motion, register and result hashes bind other correctness dependencies.

The decision packet contains the paired-mode outcomes and unresolved UK/profile gates. It does not claim an automatic global Pareto optimiser, game commit or measured billing saving. [Current packet](proof/sectional_results/decision_packet.json)

## Version 0.5 contracts: scoped clearances and record admission

The offline `railclear` functions are internal engineering interfaces, not a shipped MCP service. Inputs and outputs are described in [20](20_vehicle_envelopes_and_clearance.md) and [21](21_component_catalogue_import.md).

A `VehicleReference` contains published quantities with source/issue/locator, while a separate explicit assumption record produces a `Body` for the current rigid-plan study. Missing bogie data never defaults silently. Complete unit length, body length and coupler/formation layout retain separate meanings.

A `Sweep` carries body/path/parent hashes, the front-pivot coverage interval, support assumptions, sample step, heading span, between-pose padding and scope statuses. Pair results add all-relative-phase contact witnesses, computational work and the continuous-polyline lower bound. Every result retains unresolved parent-curve body error, dynamic/3D assessment and real gauge applicability.

A `ComponentImport` carries the full record hash separately from its normalised geometry hash. Imported fields cannot carry their own admission authority. The trusted exact-record review registry is a caller policy outside the JSON; current real external geometry is not admitted. The named application profile is not yet an executable speed-applicability predicate.

A favourable clearance overlay cannot mutate existing resources. Its `resource_mutations` list is empty. A later policy that removes a conservative exclusion must record the replacement proof, admitted vehicle/profile set, continuation coverage and invalidation dependencies. Shared track and incompatible point states cannot be removed by a geometric gap check.

The runner's compact decision packet links to the local detailed evidence. Neither thousands of poses nor rejected import fields should be streamed to Astra during routine design. This structural separation has been demonstrated without claiming a measured billing reduction.

## Version 0.6 contracts: station identity and comparison integrity

The standalone station fixture uses schema `0.6.0`. Its top-level keys and nested station/motion records are closed; duplicate JSON keys, unsupported fidelity labels, unknown scenarios, noninteger budgets and unrecognised parameters are rejected. Scenario IDs come from a fixed supported set rather than being arbitrary output paths. [Fixture](proof/station_fixtures/release.json)

A `Station` now holds the combined `Assembly`, `StationSpec`, family identity, component-admission report and group/platform eligibility table. Route IDs encode the required corridor, physical platform and direction, while graph ports independently enforce actual connectivity. Names are a lookup convention, not authority to create a route.

A candidate assessment includes `compile_hash`, `original_brief_site`, `proposed_larger_test_site`, `normal_independence`, `component_admission`, `selected_numerical_checks`, `strict_UK_input_gate`, `vehicle_summary`, `changed_brief_fields` and `construction_authorised`. It retains the exact source/assumption scope rather than reducing all domains to one success flag.

Each operating result references that assessment and the vehicle record, and carries a scenario hash containing demand, closures, horizon, local budget, motion profile, release mode and recovery policy. A different candidate compile is permitted in a comparison; a different demand/profile is not silently comparable.

`decision_packet()` checks that every required scenario exists, its input hash matches across families, result/assessment compile hashes agree and the independent result check passed. Required completion precedes operating-delay ordering. A low-delay candidate missing trains is ineligible. The output may identify an **operating-only** candidate while all original-site, strict-UK and game-construction gates remain open.

No MCP endpoint or remote job service has been implemented in this release. The functions are local proof interfaces, not authenticated world-editing tools. Intermediate poses, claims, attempts and rejected opportunities remain in local results; the decision packets return the material requirement gap and trace references. [Executed packets](proof/station_results/decision_packets.json)

The exported `CompiledAssembly` retains the reused compiler's `0.3.0` schema, with `station_compiler_version: 0.6.0` in its provenance wrapper. The station fixture, assessment, scheduler result and decision packet use their own v0.6 contracts. A consumer must inspect these distinct version fields rather than assume that the package release rewrites every preserved interface.

## Version 0.7 — Search status, fixed plan and diamond records

The standalone `railcompact` fixture is version 0.7.0. It contains a closed search-domain record, explicit geometry/scheduling budgets, retained vehicle assumptions and permitted scenario names. It exposes no model or game endpoint. Unknown fields, invalid numbers and unsafe scenario names are rejected.

New records are `geometry_search`, `diamond_crossings`, `plan_contract_gates` and a completion/site-first `decision_packets` result. The geometry search reports evaluated combinations, rejected reasons, accepted candidates, whether the grid completed and whether its selected candidate is final **within that grid**. The input hash includes the domain, profile, work budget and optional final-specialwork limit.

The diamond input carries two existing edge IDs and an expected intersection. It never carries an executable command or authorises a graph connection. Its hardware status is unresolved. The compiler emits a named exclusive resource in addition to physical track, point-state and proximity resources.

The retained network/export and scheduler schemas keep their own historic versions; the new wrapper records release 0.7.0 and the diamond-aware compiler version. Changing a wrapper's label does not relabel synthetic geometry as an authentic component.

Each operating result is bound to the exact compile hash and complete candidate-assessment hash. The decision function checks scenario comparability, verified results, scoped site/plan gates and required completion before applying the stated simplicity preference. No packet grants construction authority.

The current source/profile hashes establish provenance, not a production persistent cache or a secure user-permission system. Detailed geometric/search/operation records stay local. Astra receives the required recovery choice and unresolved engineering gates, not the 27 fitting iterations or every scheduled resource interval.


## Version 0.8 — Platform and facility assessment joins

`PlatformProfile` distinguishes gauge, rail-edge offset, perpendicular height, resolved offset minimum and explicit source-case applicability. `RailSection` declares the rail-plane datum and signed side. `Facility` carries a fixed rectangle; the local fitter receives separate authorised movement bounds and a budget. These are offline internal contracts, not game API names.

An operating comparison now carries `compile_hash`, `platform_assessment_hash`, `facility_check_hash`, `vehicle_reference_hash` and `design_case_hash`. Moving a facility leaves rail resources unchanged but invalidates the facility-dependent boarding-eligibility result. An earlier rail-only vehicle audit cannot approve a newly added platform surface.

The joint interface gate verifies assessment joins and recomputes the facility result. It retains reference-copy/draft provenance and leaves current national conformity and construction authority unresolved. Hashes support provenance and stale-input detection; they are not evidence-signing or reviewer-authentication mechanisms.

The local repair is a single bounded geometric calculation followed by an independent check and scenario reruns. No segment-by-segment interaction with Astra is required. Usage savings remain unmeasured; the runner records zero model/game API calls rather than inventing credits.


## Version 0.9 — Capability-qualified corridor execution

The new executable package uses a closed `0.9.0` local fixture, immutable design/terrain revisions, content hashes, deterministic operation IDs and declared edit bounds. These are **proposed bridge contracts**, not real TPF3 function names. `evidence/game_capability_research.json` records published behaviour; a demonstrated adapter manifest is a different object.

An in-memory mock supports track-polyline and civil-reservation operations plus read-back/receipt queries. Before its first write, the orchestrator validates plan identity, dependencies, node consistency, environment, terrain/world revisions, authority bounds and every operation's capability. Required capabilities are recomputed from the actual operations; deleting a summary field cannot hide an unsupported command.

The engine advances revisions for its own committed effects. An unrelated revision prevents continuation. A lost acknowledgement triggers receipt reconciliation before retry; replaying the same operation ID with different content is invalid. A geometry read-back mismatch stops with the actual applied-operation count and leaves the partial state visible. No rollback is assumed.

The implemented read-back checks ordered vertices and declared node/payload identities in the mock. It is not independent real-game route, asset, physics or passenger verification. A production adapter must add actual connectivity and engine geometry checks rather than inherit the mock's result label.

The returned packet exposes two corridor trade-offs and references the full search. It keeps geometry screens, sampled terrain estimates, missing branch connectivity and real-game unknowns distinct. Full debug traces remain local; the runner makes no model or game calls. [Mock results](proof/corridor_results/mock_execution_cases.json)

## v0.10 addendum — junction identity and semantic read-back

`railbranch` provides a restricted local implementation, described in [36](36_branch_junction_results_and_game_contract.md). The fixture schema is `0.10.0`; it identifies a new synthetic local junction site. Candidate, resource, scenario, performance and result hashes remain distinct, with explicit links between them. Historical corridor or vehicle results cannot be attached solely because a track name matches.

The mock plan's physical asset set includes shared plain track, two-state turnout objects, a non-connecting crossing relation and optional civil reservation. Proposed capability names are versioned bridge contracts, not discovered TPF3 API identifiers. Unknown real-game capabilities block writes; mock success does not change those capabilities.

A receipt resolves whether an operation acted. Current geometry/topology read-back establishes whether the resulting object still matches. Both are needed after acknowledgement loss. The executable tests reject a mutated current object even when its earlier receipt exists. Positional tolerance never relaxes exact legal routes, point states, identities or a crossing's no-turn semantics.

Compact decisions preserve unscheduled work, the applicable delay threshold, merge/crossing witnesses, candidate scope and unassessed terrain/game domains. Python conducts the bounded geometry and timing trials without per-trial model calls. This structural separation does not establish a measured billing saving.


## v0.11 — Content-bound terrain and live-state invalidation contract

A `TerrainBoundDesign` joins canonical geometry, the source corridor and branch contracts, terrain content and revision, protected land, per-route engineering profile, civil policy and operation scenarios. `verify_binding()` regenerates the supported assessment instead of trusting its pass flag. Terrain-qualified operation records retain both submodel and wrapper hashes. [39](39_terrain_placement_results_and_mock_contract.md)

The new mock preflight checks snapshot bytes in addition to revision labels, and repeats the snapshot check before each operation and after receipt. A changed snapshot stops further writes and preserves partial effects. Land/structure reservations precede track operations. An operation receipt proves an earlier effect, not the current correctness of that asset.

These interfaces remain local engineering functions; content hashes are not external attestations or a substitute for production authorisation. No real TPF3 API, terrain grid, existing-track deletion, atomic rollback or measured usage saving is implied.
