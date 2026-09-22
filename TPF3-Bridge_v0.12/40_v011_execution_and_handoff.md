# v0.11 execution evidence and implementation handoff

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.11.0 · **Date:** 21 September 2026  
**Completed execution:** 985 test methods, including 68 new terrain-placement methods. No failures, errors or skipped tests in the recorded acceptance run. The demonstration evaluates 24 placement candidates, three selected crossing forms, 12 operating comparisons and 12 mock cases.

## 1. Delivered scope

The new `railterrain` package refits a complete passenger branch against the original synthetic corridor terrain and immutable main-line interfaces. It preserves imported component shape, reapplies the original main-line project targets, assesses every physical edge against water/land constraints, retains source-qualified inputs, and joins terrain evidence to operation results and mock construction.

This is an unbuilt-design replacement between fixed ports, **not live replacement of existing game assets**. No station interiors, terrain or external service were changed. Six candidates pass the declared reference-design screens; actual structures and game behaviour remain unassessed.

The terrain is the authored field from v0.9, not newly acquired real topography or a live game snapshot. No new standards clauses or authentic pointwork were imported. The source register remains at 70 records with its existing evidence limitations.

## 2. Run the release

From `proof/`:

```sh
python run_tests.py
python -m railterrain.demo --output terrain_results
```

Keep the root `evidence/` directory with `proof/`. Runtime dependencies remain Python standard-library modules. The test runner records exact method IDs, environment and tested source/fixture/evidence hashes in [test_report.json](proof/results/test_report.json).

The completed full-suite run used Python **3.13.5** on the reported Linux runtime and took approximately **44.782 seconds**. This is one observed execution measurement, not a production latency, total development duration, Windows result, performance percentile or plan-credit saving. An earlier full-suite invocation was interrupted by its tool timeout; the acceptance report comes from the subsequent completed run.

The full suite and new demonstration ran. Older full-study output files were preserved and compared with the v0.10 archive; they are not all described as newly rerun full studies. Earlier integration tests still run as part of the full suite.

## 3. New tests and interpretation

| Test module | Methods | Principal checks |
|---|---:|---|
| `test_terrain_geometry.py` | 18 | Fixed external ports, rigid component translation, explicit approach sorting, legal routes, inherited main-line targets, continuous order and independent derivative/curvature checks |
| `test_terrain_planning.py` | 22 | All-edge terrain coverage, river boundaries, protected-land witnesses, unsupported structural pointwork, changing water/site, ground bounds, reservation unions, quantity/refinement semantics and recomputed evidence |
| `test_terrain_adapter.py` | 18 | Land-before-track dependency, unique physical construction, receipt recovery, current-state inspection, changed terrain without a new label, mid-execution invalidation and bounded partial failure |
| `test_terrain_demo.py` | 10 | Complete grid accounting, candidate selection, common scenario identity, retained merge constraints, joined-result rejection and byte-identical replay |

Counts refer to test methods, not the number of railway standards, certified assets or complete original requirements. The 917 earlier methods remain unchanged. The original 75 high-level requirements and 41 broad benchmark definitions still describe a larger production bridge.

Independent checks include dense ground samples against analytic bounds, a separate unit-cell calculation of rectangle-union area, dense curvature/rate calculations against sufficient bounds, actual imported-coordinate differences, and the inherited independent event-sweep checker. These verify the implemented models, not their empirical adequacy for an actual railway.

## 4. Inspectable evidence

| Artifact | Evidence |
|---|---|
| [Current test report](proof/results/test_report.json) | Exact method outcomes, environment and tested bytes |
| [Current test log](proof/results/test_log.txt) | Per-method outcomes |
| [Historical v0.10 report](proof/results/v010_test_report.json) | Preserved 917-test acceptance record |
| [New fixture](proof/terrain_fixtures/release.json) | Allowed placements, modes, budgets and civil support policy |
| [Source/input provenance](proof/terrain_results/input_provenance.json) | Frozen corridor/branch references, actual terrain hash and retained profiles |
| [Placement search](proof/terrain_results/placement_search.json) | All 24 candidates, six accepted screens, failed constraints and selected alternatives |
| [Flyover geometry](proof/terrain_results/flyover__geometry.json) | Placed track, unmodified imported shapes, boundary positions and connected routes |
| [Flyover terrain binding](proof/terrain_results/flyover__terrain_binding.json) | Main-line checks, 515 terrain intervals, reservations and source identity |
| [Flyover resources](proof/terrain_results/flyover__resources.json) | Removed crossing exclusion and retained physical merge/exit |
| [Common scenarios](proof/terrain_results/common_scenarios.json) | The same requests used across crossing forms |
| [Comparison](proof/terrain_results/comparison.md) | Placement, terrain quantities and all 12 operating rows |
| [Changed constraints/refinement](proof/terrain_results/changed_constraints_and_refinement.json) | Narrow-site and high-water failures, incomplete searches and grid sensitivity |
| [Construction plan](proof/terrain_results/selected_mock_plan.json) | 17 dependency-ordered memory operations |
| [Mock cases](proof/terrain_results/mock_execution_cases.json) | Successful read-back, no duplicates and environment/fault handling |
| [Unprobed game manifest](proof/terrain_results/tpf3_unprobed_capabilities.json) | No claimed real API demonstration |
| [Decision packets](proof/terrain_results/decision_packets.json) | Terrain/operation alternatives without blanket build approval |
| [Release validation](release_validation.json) | Links, finite JSON, test hashes, baseline equality and manifest checks |

Hash records identify actual input bytes or explicitly normalised content. They are not external attestations, engineering certification or substitutes for an execution-authority policy. The mock remains an internal engineering interface, not an exposed arbitrary-command endpoint.

## 5. Material findings

The baseline local point arrangement encounters water and protected land that were absent from its original local assessment. Moving the toes east and refitting northern approaches produces reference-design candidates while keeping all external ports and the main-line profile fixed. A still-wider detour is rejected by the original main-line radius screen, even though its terrain classification looks attractive.

Terrain-qualified flat, flyover and diveunder forms now have different civil planning quantities. The crossing-pulse test still favours separation within its declared model; the merge and blocked-exit tests still delay trains in every form. No previous crossing benefit is misreported as a solved whole corridor.

Changing terrain contents while keeping its revision label is detected before writes. A change injected after the first reservation stops the next operation and preserves partial state. No atomic rollback or real game capability is assumed.

## 6. Regression and package integrity

All **93 preceding model/test source files** and **291 preceding deterministic output files** covered by the baseline verifier match the actual v0.10 ZIP byte-for-byte. The exact file counts, paths and any mismatches are in [release_validation.json](release_validation.json). Earlier source modules and their tests are frozen; updated documentation, the test runner, verifier and current reports are deliberate maintenance exceptions.

The new demonstration is run twice inside the integration suite, and every generated file is byte-compared on this runtime. That does not promise identical floating-point bytes across every operating system or Python build.

From the package root:

```sh
python verify_release.py
python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.10.zip
```

The validator checks local Markdown targets/fragments, finite JSON, tested hashes, method-count consistency and manifest membership. The manifest excludes itself and the validation record to avoid recursive hashing. ZIP integrity is checked when the archive is produced. Validation does not rerun the demonstration or turn preserved files into fresh observations.

## 7. Acceptance and next task

**Implemented:** boundary-preserving corridor/junction design composition; rigid component placement with re-fitted plain line; original main-line project screens; analytic-test-terrain and protected-land checks; physical-edge accounting; explicit civil reservations; terrain-bound operation results; current-snapshot checks and semantic mock construction.

**Not implemented or not established:** arbitrary map headings; full transverse earthwork toes or ground stability; finished bridge/tunnel assets and portals; groundwater/drainage design; exact/dynamic vehicle gauging; authentic UK pointwork ratings; grade-sensitive traction/braking; constructed internal holding signals, restarting and spatial queues; live terrain/API probing; built-world replacement or TPF3 execution; measured Astra plan savings.

The next engineering task is **grade-sensitive performance and internal holding/restart behaviour on the same placed geometry**. Actual structure selection and live game probing remain separate integration tasks. Further station internals or specialist certification are not prerequisites for ordinary reference-inspired game design.
