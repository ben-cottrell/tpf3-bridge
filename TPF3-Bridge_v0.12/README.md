# TPF3-Bridge — implementation-ready handoff

Current shared `parallel-layout` also supports UD/UDUD and either explicit UP reference.
P22 demonstrated UD decreasing-UP and UDUD increasing-UP on build40408, with fresh
inspection, sampled geometry/spacing and145passing tests. See the compact command,
domain and partial-effect notes in [live-interface usage](implementation/live_python_interface/README.md#ordered-patterns-and-reversed-up-reference-p22-demonstrated).

## Current native junction workflow — P21, 4 October 2026

The standalone brief [portable_junction_example.json](implementation/live_python_interface/portable_junction_example.json)
drives plan/build/inspect through `bridge_live.py`. It needs a healthy running native
adapter/context and a bounded `asset_region` containing a suitable native TRACK/template
seed with five-unit spacing. No historical P19 receipt or native entity ID is required.
Choose suitable land and set origin, heading, authorised region and asset region for
the current world; the supplied coordinates describe the demonstrated sandbox site.

```sh
python bridge_live.py reciprocal-layout --params implementation/live_python_interface/portable_junction_example.json
python bridge_live.py reciprocal-layout --context CONTEXT.json --params implementation/live_python_interface/portable_junction_example.json --execute --timeout 60
python bridge_live.py reciprocal-layout-inspect --context CONTEXT.json --params implementation/live_python_interface/portable_junction_example.json --layout-record RUN.json --timeout 60
python bridge_live.py reciprocal-layout --context CONTEXT.json --params implementation/live_python_interface/portable_junction_example.json --execute --layout-record RUN.json --timeout 60
```

`CONTEXT.json` identifies the configured native adapter; `RUN.json` is the saved compact
build summary or its full receipt. The last command is explicit continuation: it
freshly inspects before reusing completed stages and builds only proven missing work.
A completed run is checked without construction. Partial inspection reports each
declared movement, completed/absent/unknown stages, prior effects and next action.
Pending/uncertain effects require reconciliation; no blind replay, automatic resume
or assumed rollback. Mid-throat partial construction without a completed pair receipt
requires focused semantic reconciliation, rather than replaying the whole throat.
Original failures remain immutable. Existing P18–P20 interfaces/receipts are retained.

Supported: level UUDD with increasing-coordinate UP intent, four through movements,
two outer branches and both same-direction transfers on each pair; translated/rotated
placement, retained five-unit approach spacing and widened switching zones. Hard radius
120 and reference-track radius160 remain binding. No direct five-unit crossover or
opposite-direction transfer is promised. Build40408 demonstrated a complete fresh-base
build at `(2800,3200,33)`, heading20°, followed by fresh-process inspection: ten TRAIN
routes, four exact transfer connectors, ten functional junctions and 66 TRACK edges.
Independent17-point sampling found radius122.281179, grade0 and approach spacing
4.999922–5.000161. Geometry evidence is sampled, not a continuous clearance proof.

An earlier site rejected its third fixture after two stubs were built. Those partial
effects and failure records remain; other incidental effects are unknown. Relocation
succeeded without lowering constraints. No universal site buildability claim follows.
Train traversal, signals/reservations, operational direction enforcement and save/load
identity are unprobed. Affected quiet acceptance:141passed; compact local evidence in
`.local_runs/live_python_interface/p21/` and the exact report in `STATE.md`.

The following release handoff is historical; use `SPDD_SCOPE.md`,
`NATIVE_FIRST_ARCHITECTURE.md` and current `STATE.md` for governing scope and evidence.

**Version 0.12.0 · 21 September 2026**  
**Purpose:** turn the existing engineering proofs into a practical UK-inspired Transport Fever 3 construction bridge.  
**Status:** consolidated specification, checked domain contracts and implementation handoff; not a running production bridge or live game integration.

## Start here — the current specification

| Document | Read it for |
|---|---|
| **[IMPLEMENTATION_SPEC.md](IMPLEMENTATION_SPEC.md)** | Current product scope, responsibilities, one canonical architecture, normal construction workflow, UK realism and acceptance boundary |
| [GAME_ADAPTER_CONTRACT.md](GAME_ADAPTER_CONTRACT.md) | Native reads/writes, capability evidence, snapshots, assets, save/load, safe reconciliation and fifteen concrete probe definitions |
| [AGENT_API_AND_HANDOFF.md](AGENT_API_AND_HANDOFF.md) | Eight proposed Astra-facing tools, local job/control policy, source extraction map, nine work packages and five live acceptance workflows |
| [V012_RELEASE_NOTES.md](V012_RELEASE_NOTES.md) | What changed, what was executed, validation results and what remains unimplemented |

These documents supersede historical **next-step priorities**, not historical observations. The preceding numbered chapters remain available for engineering detail, sources and regression context. A developer should not have to read every release narrative to find the current product boundary.

## The scope correction is explicit

Detailed grade-sensitive traction, braking/restart, microscopic queues, crowd/lift/evacuation analysis and further station furniture modelling are optional deferred work. They are **not prerequisites** for ordinary game-oriented railway construction.

Keep credible UK geometry, smooth gradients, train/platform fit, enough waiting length, useful route connections, supported native assets, bounded local repair and actual construction verification. The game remains authoritative for its own running behaviour. The normal mode is GB reference-inspired; specialist certification is an optional separate profile.

The next live milestone is a **create-only track connection between existing stubs**, not another home-grown simulator. Follow it with native junctions/structures, practical signals and carefully scoped existing-layout changes.

## Machine-readable handoff

[Contracts](contracts/README.md) contain **38 schema definitions**, **eight proposed tool descriptors**, **17 indexed validation examples/records** and **nineteen unprobed game capability records**. Examples are authored shapes, not generated native plans or real approval credentials.

[Implementation metadata](implementation/README.md) contains a sixteen-feature support matrix, a disposition for **all 75 original requirement IDs**, an actual source/symbol inventory, nine work packages and five acceptance workflows. The current architecture calls for one production core; this release does not claim that its source extraction/refactor has already happened.

## Executed in v0.12

**34 contract/policy/handoff tests passed**, with no failures, errors or skipped tests in the completed acceptance run. The example validator checks all seventeen indexed examples/records. See the [current contract report](validation/contract_test_report.json) and [example validation](validation/example_validation.json).

The earlier engineering code, fixtures, results and evidence are preserved. Their last complete suite remains the **985-method v0.11 record**, not a new execution claim. The old full suite and full-study demos were **not rerun** for this specification release. Byte preservation and current file integrity are checked separately in [release_validation.json](release_validation.json).

## Run the new checks

From the package root:

```sh
python -m pip install -r requirements-contracts.txt
python contract_checks.py
python run_contract_tests.py
python verify_release.py
```

`jsonschema` is a pinned **development-only** dependency of the new contract checks. The preserved engineering `proof/` retains its existing standard-library dependencies. These commands do not call a model or a game, start a server, install a mod or grant construction authority.

The optional baseline command compares the preserved proof and evidence with the preceding archive:

```sh
python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.11.zip
```

## Existing research and proofs

| Area | Historical / detailed references |
|---|---|
| UK station and junction atlas | [02](02_reference_atlas.md), [03](03_birmingham_new_street.md), [04](04_london_termini_and_junctions.md), [05](05_regional_passenger_hubs.md) |
| Requirements and original architecture | [06](06_passenger_engine_specification.md), [07](07_pattern_catalogue.md), [08](08_data_contracts_and_orchestration.md), [09](09_validation_benchmarks_and_roadmap.md) |
| UK numbers and component/vehicle records | [17](17_uk_numerical_profiles.md), [20](20_vehicle_envelopes_and_clearance.md), [21](21_component_catalogue_import.md), [29](29_uk_platform_datums_and_interfaces.md) |
| Compact station proof | [26](26_compact_site_and_recovery_design.md), [27](27_compact_station_results.md) |
| Corridor and connected junction proofs | [32](32_corridors_junctions_and_game_fit.md), [35](35_connected_passenger_branch_junctions.md), [38](38_terrain_aware_junction_placement.md) |
| Last full engineering execution | [40](40_v011_execution_and_handoff.md), [preserved test report](proof/results/test_report.json) |
| Source register and release history | [10](10_source_register.md), [CHANGELOG](CHANGELOG.md) |

## What is still not delivered

No native TPF3 function mapping has been demonstrated. No production orchestrator, MCP server, durable job store, authenticated game transport or first live construction has been implemented. Mock results and schema validity do not change those states. No Astra plan-usage saving is measured.

The package is supplied as files in this conversation. Shared Project Files membership has not been changed. Source documents are linked, not redistributed. Previous release archives remain separate.
