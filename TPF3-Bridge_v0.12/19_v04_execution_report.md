# Version 0.4 execution evidence and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.4.0 · **Date:** 20 September 2026  
**Executed:** **284 test methods**: 83 preserved v0.2 tests, 93 preserved v0.3 tests and 108 new tests. Zero failures, errors or skipped tests in the recorded acceptance run.

## 1. Delivered and run

The release adds a generated two-approach four-platform bank, analytic stopping/continuing trajectories, spatial resource footprints, two comparable release policies, finer finite-horizon accounting, source-backed numerical helpers and explicit profile-admission gates.

The code was executed with Python 3.13.5 in the conversation's Linux runtime. All runtime dependencies are from the standard library. No model, desktop or game calls occur in the demo runners.

```sh
cd proof
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
```

The package is self-contained. Numerical evaluators load `evidence/uk_parameters.json` using the package location, so keep that directory alongside `proof/` when moving it. No source PDF needs to be downloaded to rerun the authored examples.

Recorded suite duration is one execution measurement, not production latency, a p50/p95 result, Windows validation or a model-credit saving. Exact environment and elapsed time are in the report.

## 2. Inspectable evidence

| Artifact | What it records |
|---|---|
| [Current test report](proof/results/v04_test_report.json) | 284 exact test IDs, results, environment, code/fixture hashes and numerical-register hash |
| [Current test log](proof/results/v04_test_log.txt) | Individual method results |
| [Preserved v0.3 report](proof/results/v03_test_report.json) | Historical 176-test record |
| [Preserved v0.2 report](proof/results/v02_test_report.json) | Historical 83-test record |
| [v0.4 fixture](proof/sectional_fixtures/release.json) | Geometry, access, motion, visits and nine scenario definitions |
| [Compiled two-approach assembly](proof/sectional_results/dual_access_compiled.json) | Explicit route graph, geometry bounds and resource provenance |
| [Release-policy comparison](proof/sectional_results/comparison.md) | All eighteen paired-policy results |
| [Example legs](proof/sectional_results/example_legs.json) | Motion phases, resource footprints, front/tail times and release intervals |
| [Numerical examples](proof/sectional_results/uk_numerical_checks.json) | Scoped reference lookups, clause results and partial guidance calculation |
| [Checks on the generated bank](proof/sectional_results/generated_bank_uk_checks.json) | Selected scalar checks tied to the actual geometry compile hash |
| [Spacing proxy trial](proof/sectional_results/gb_spacing_proxy_trial.json) | Real nominal reference versus the unchanged synthetic corridor proxy |
| [Summary](proof/sectional_results/summary.json) | Inputs, compile hash, result rows and explicit assessment boundaries |
| [Decision packet](proof/sectional_results/decision_packet.json) | Bounded result summary and links to detailed local evidence |
| [Release validation](v04_release_validation.json) | Local link/JSON/hash and prior-output regression checks |
| [Manifest](v04_manifest.json) | SHA-256 inventory with declared self-exclusions |

The third-party documents are linked and their reviewed locations recorded, not repackaged. No source-byte hashes are invented for remote PDFs that were not archived.

## 3. New test coverage

| Test module | Methods | Coverage |
|---|---:|---|
| `test_ops_motion.py` | 21 | Phase construction, endpoint conditions, inverse/time-distance consistency, monotonicity, speed cap, independent speed integration and invalid inputs |
| `test_ops_sectional.py` | 39 | Directed access, shared resource/state semantics, joins, footprints, release policy, tail clearance, complete visits, stock, fit, horizon and budget outcomes |
| `test_ops_demo.py` | 17 | Strict fixture parsing, output-path identifiers, paired scenario hashes, realistic-spacing proxy mismatch and generated-bank numerical checks |
| `test_uk_profiles.py` | 31 | Imported values, units, clause applicability, nominal versus pass status, boundary conditions, missing inputs and strict-mode admission |

A method can contain several assertions or subcases; the report counts methods rather than inflating those into separately validated engineering standards. Existing test files were not modified to make the new implementation pass.

The independently structured checks include numerical integration of speed, exact kinematic identities, pairwise inspection of all committed intervals, explicit resource-set comparisons and conservation of required work. They verify the implemented model. They do not validate its predictions against a physical railway or the game.

## 4. Executed observations

The new default assembly has two external directional leads, four platform roads, eight selected routes, thirty physical edges and seventy-nine resource records. It retains a shared access component and distribution fan.

The release comparison holds demand and geometry constant within each scenario. Under the nominal fixture both policies schedule all twelve visits. Whole-route release accumulates 16,779.354 seconds of departure delay; the synthetic sectional policy accumulates 10,568.224 seconds. This is a result of the declared resource model and greedy schedule, not a general percentage improvement for UK stations.

The P4 arrival example releases the access component earlier under the sectional policy while preserving stopping motion and downstream occupation. Tests prevent release at front-clear time instead of tail-clear time.

Closure, overlength and exhausted-budget scenarios keep required but unscheduled work. A short observation window keeps all residual work and distinguishes future requests from already-waiting visits.

The sourced nominal track-centre lookup resolves while the generic corridor proxy cannot establish independent passage. This demonstrates why replacing a constant is not equivalent to implementing real vehicle gauging.

Selected scalar checks also run on the actual generated bank: the conservative global radius lower bound is approximately 334.052 m; its straight platform roads and declared zero cant meet the selected individual checks. Full GB geometry remains unassessed. No component or vehicle approval is inferred from those results.

## 5. Regression discipline

The v0.2 and v0.3 modules remain unchanged. Their runners were executed again, with legacy JSON and Markdown outputs compared against the v0.3 archive. Exact comparison scope and any exclusions are in `release_validation.json`; current test reports and timings are intentionally not compared as historical outputs.

The new geometry export identifies the reused compiler as version 0.3.0 but uses a version 0.4.0 wrapper that does not repeat the old whole-leg timing field as a current result. Timing is a separate `railops` assessment. Geometry hashes do not substitute for the motion/release-profile hash or full result record.

The current test runner hashes new code, all three fixture families and the numerical register. A changed numerical source value, train profile or component invalidates the corresponding prior result even when platform counts stay the same.

## 6. Source-backed versus synthetic coverage

| Layer | Current status |
|---|---|
| Selected source values | Eleven numerical records with source issue, locator, units, type and scope; individual helpers executed |
| Platform numerical checks | Two previously implemented clause checks retained and exercised; some checks now tied to generated bank geometry |
| Platform demand sizing | Partial Zone B/C guidance helper; no full platform-width or crowd-model approval |
| Track and specialwork | Authored level, zero-cant synthetic centreline components |
| Physical clearance | Conservative corridor proxy; actual vehicle swept envelopes unresolved |
| Longitudinal motion | Analytic level-track constant acceleration/braking; one route-wide project speed cap; uncalibrated |
| Release semantics | All-at-once acquisition and synthetic edge-sectional release, not actual signal sections or control tables |
| Train conservation | Complete visits, stock dependencies, held storage and explicit residual demand |
| Station completeness | One four-road bank with two external leads, not the original two-bank/eight-platform design |
| Game and construction | Not connected or tested; no construction authority |

The full 75 production requirements, 32 pattern contracts and 41 broad benchmark definitions remain larger than this proof. Passing 284 unit methods is not a claim that those complete contracts have all been implemented.

## 7. Known limits that affect interpretation

The shared fan still constrains simultaneous operation. Sectional release may free upstream track sooner, but cannot invent another path. The scheduler is greedy, reserves routes in advance and does not backtrack earlier choices.

Storage occupation remains deliberately conservative. Arrival trajectories start at rest at the external boundary. Departures assume a clear continuation beyond the boundary long enough to clear the train tail. There is no spatial upstream queue, authentic braking curve, full signal-aspect model or measured train-performance calibration.

Current geometry is planar. Full 3D envelopes, structural clearances, drainage, electrification, platform offsets and buffer-stop engineering remain separate gates. The sourced vertical-radius helper evaluates an input value; it does not generate a complete flyover or vertical station approach.

Rule applicability is an explicit caller decision in the narrow evaluator. A future profile resolver needs stronger route/system/epoch coverage. Current strict-mode input admission prevents synthetic component promotion but is not an exhaustive standards-completeness checker.

## 8. Acceptance and next engineering gate

Accepted for continued offline development: explicit directional access, stopping and tail-clear trajectories, conservative sectional release, complete-visit invariants, measurable policy comparisons and a first executable source-backed numerical-profile layer.

Not accepted for a UK-compliant network, real signalling design, the original full station brief or game construction. The next engineering gate should prioritise a representative vehicle-envelope model and authentic component-data admission, then compose the two-bank station with genuinely demonstrated independent and recovery movements.
