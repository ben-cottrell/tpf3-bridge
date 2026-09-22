# Version 0.5 execution report and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.5.0 · **Date:** 20 September 2026  
**Executed:** 414 test methods: 284 retained from earlier releases and 130 new methods. No failures, errors or skipped tests in the recorded acceptance run.

## 1. What was delivered and executed

The release adds the `railclear` package, one new study fixture, a manufacturer-dimension reference record, synthetic and pending-external component records, and three new main specification documents. The code executes the rigid-body pivot solver, analytic circular references, bounded polyline sweeps, polygon contacts, a read-only generated-route overlay, published-unit-length trials and data-driven component placement/resource compilation.

The full suite and all four demo runners were executed in the conversation's Linux runtime. The exact Python version, elapsed test time and tested byte hashes are in the [test report](proof/results/v05_test_report.json). Runtime dependencies are from the standard library. This does not establish Windows or TPF3 compatibility, a production latency target, or plan-credit savings.

```sh
cd proof
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
python -m railclear.demo --output clearance_results
```

Keep the root `evidence/` directory with `proof/`. The new runner reads the local reviewed records; rerunning it does not require a web request or a downloaded third-party PDF.

## 2. New test coverage

| Test file | Methods | Main checks |
|---|---:|---|
| `test_clear_model.py` | 37 | Fixed bogie chord, path support, symmetry/transform/reversal, analytic circle bands, invalid numerical domains and published-dimension-informed gap calculations |
| `test_clear_sweep.py` | 25 | Convex polygon contact, between-pose bound, dense independent checks, all-relative-phase pairs, obstacle checks, refinement, budgets and no resource mutation |
| `test_clear_catalogue.py` | 43 | Closed schemas, unit conversion, toe/curve continuity, legal traversals, source-review separation, hashes, malformed files, missing speed applicability and explicit vehicle assumptions |
| `test_clear_demo.py` | 25 | End-to-end generation/import, pose-chord invariants, replay, published formation lengths, fit/motion integration, support declarations and fixture rejection |

Counts are test methods, not the number of assertions, independent railway standards or completed production features. The original 75 requirements, 32 pattern families and 41 broad benchmark definitions remain wider than these proofs.

Independent checks include circle identities, corner/radial comparisons, a dense polyline cross-check of the circular model, dense intermediate-pose displacement checks, direct endpoint/chord assertions and byte-for-byte replay of the new runner's output. The tests verify the authored models; they do not validate a particular train's dynamics against measurements.

## 3. Inspectable results

| Artifact | Evidence |
|---|---|
| [Test report](proof/results/v05_test_report.json) | Current execution counts, exact method IDs, source/fixture/evidence hashes and environment |
| [Test log](proof/results/v05_test_log.txt) | Per-method outcomes |
| [Historical v0.4 report](proof/results/v04_test_report.json) | Preserved 284-test acceptance record |
| [Comparison](proof/clearance_results/comparison.md) | Eighteen base spacing rows, generated-route pair results and two formation-length trials |
| [Vehicle resolution](proof/clearance_results/vehicle_resolution.json) | Sourced dimensions separated from body/pivot assumptions |
| [Spacing sensitivity](proof/clearance_results/spacing_sensitivity.json) | Circular/straight calculations and a synthetic long-body overlap counterexample |
| [Straight refinement](proof/clearance_results/straight_refinement.json) | Same geometry/vehicle; finer sampling resolves the static-polyline bound |
| [Crossover overlay](proof/clearance_results/crossover_clearance_overlay.json) | Three all-phase route-pair studies with unchanged legacy geometry/resources |
| [Crossover poses](proof/clearance_results/crossover_forward_sweep.json) | Individual front/rear pivots and body corners |
| [Curve obstruction](proof/clearance_results/curve_overhang_obstacle.json) | Contact with a body's inward overhang |
| [Bank route sweep](proof/clearance_results/bank_route_sweep.json) | Representative body poses along a generated arrival with declared supports |
| [Formation-length trial](proof/clearance_results/published_formation_length_trial.json) | Published total unit lengths passed to existing scalar fit and longitudinal motion |
| [Component import](proof/clearance_results/component_import_results.json) | Normalised supplied geometry, placed network, actual compiled resources and the quarantined source gap |
| [Summary](proof/clearance_results/summary.json) | Reproducible result counts, hashes and assessment scope |
| [Decision packet](proof/clearance_results/decision_packet.json) | Compact result/next-gate record without exporting all poses to Astra |
| [Release validation](v05_release_validation.json) | Link, JSON, hash, source-regression and earlier-output comparisons |

## 4. Material findings

The new study explains a positive static body gap at the British nominal straight-track interval without shrinking the old arbitrary proxy. A realistic published width is used in a separately labelled vehicle model. Its missing dynamic and exact-geometry dependencies remain visible.

For the baseline assumed body, the straight raw gap is 0.6 m. At 400 m circular radius it is approximately 0.475953 m. Neither is an available engineering allowance or a full dynamic clearance verdict. The reference-informed pivot/body assumptions are necessary to interpret the second number.

The coarse straight sweep is inconclusive while the refined sweep is clear within the polyline static model. This is a local computation refinement, not a change of railway dimensions. The new code preserves the distinction between uncertainty and a physical clash.

The generated crossover's through-route pair is separated in the new model; its crossing route contacts each through route's body sweep. The route overlay does not infer a train collision, new track connectivity or an interlocking approval from that contact. It performs no changes to existing reservations.

The imported synthetic turnout now follows a full JSON → normalised geometry → placed network → compiled-resource path. The external supplier reference does not: it remains explicitly short of a dimensional drawing and cannot provide an authentic component instance.

Published full-unit lengths produce different platform-fit margins and tail-clear timing. They are not rounded down to nominal body length multiplied by car count. The performance law remains the existing uncalibrated project model.

## 5. Regression discipline

The v0.2, v0.3 and v0.4 model packages and their existing test files are retained unchanged. The test runner is expanded to include the new package/fixture/evidence hashes and distinguish the new method prefix.

Earlier deterministic demo outputs are rerun and compared with the v0.4 ZIP. Current execution reports/timing files are excluded from deterministic-output comparison because they intentionally describe this new suite. Exact comparison scope and any mismatches are recorded in `release_validation.json`; old reports and manifests are preserved separately.

The new demo is also run twice inside its integration tests, with every produced file compared byte-for-byte. That verifies replay on this runtime, not portability of every floating result to all Python/platform versions.

## 6. Acceptance boundary

Accepted for further offline development: a meaningful vehicle-shape model, fixed-pivot geometry, analytically justified between-pose bounds on supported polylines, source/assumption separation, evidence-qualified component ingestion, generated-route audits and real catalogue unit lengths reaching the operating model.

Not accepted: an exact model of the selected fleet, a complete formation sweep, full 3D/dynamic/canted gauging, a certified body-error transfer from Bezier to polyline, an authentic UK turnout catalogue, a finished four-approach/eight-platform station, a production MCP server, game integration or measured agent usage savings.

The next station composition may proceed in declared reference-informed mode while evidence acquisition continues. Its normal independence and recovery movements must still be demonstrated, and the original site boundary must be tested rather than assumed to fit. Strict UK and game-construction gates remain separate.
