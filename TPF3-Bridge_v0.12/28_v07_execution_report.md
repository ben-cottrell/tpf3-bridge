# Version 0.7 execution evidence and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.7.0 · **Date:** 20 September 2026  
**Executed:** **592 test methods**, including **92 new compact-station methods**. No failures, errors or skipped tests in the recorded acceptance run.

## 1. Delivered scope

The `railcompact` package supplies a fixed-original-site station family, bounded fan-geometry search, strict declared-diamond admission, a crossing-aware compiler, candidate-bound plan/vehicle/numerical assessments, sixteen operating scenarios and guarded offline design choices.

Four candidates and sixteen scenarios produce **64 full-study operating comparisons**. Each output passes the independently structured complete-visit and interval checker inherited from v0.6. The test suite also deliberately corrupts resources and evidence joins to verify that incorrect outputs are rejected.

This is an original software/design increment, not a new standards-acquisition release. The retained 63-source register has not been presented as newly researched. No authentic UK turnout or diamond drawing, exact vehicle bogie dimension, dynamic allowance or game API has been acquired in this increment.

## 2. Run the package

From `proof/`:

```sh
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
python -m railclear.demo --output clearance_results
python -m railstation.demo --output station_results
python -m railcompact.demo --output compact_results
```

The commands were executed in this conversation's Linux runtime. Runtime dependencies are Python standard-library modules. Exact Python/platform details, elapsed suite time and tested-byte hashes are in [test_report.json](proof/results/v07_test_report.json). The test duration is a single runtime measurement, not a production latency or usage-saving estimate.

Keep the root `evidence/` directory alongside `proof/`. The runners use local authored and reviewed records; they do not need to download third-party PDFs to reproduce the delivered experiments. Windows, desktop control and TPF3 are not tested by this execution.

## 3. New tests

| Module | Methods | Main behaviours |
|---|---:|---|
| `test_compact_geometry.py` | 28 | Exact boundary/platform/buffer positions, concourse conflicts, unchanged radius target, legal route inventory, immutable import dimensions, matched route lengths and bounded search |
| `test_compact_crossings.py` | 16 | No diamond turning connection, compulsory crossing resources, no false normal-route claim, missing/malformed crossing rejection and preservation of the old compiler's guard |
| `test_compact_operations.py` | 21 | Complete normal/recovery visits, failure location, train-length asymmetry, policy, closed diamond, storage/diamond tamper detection and finite-horizon accounting |
| `test_compact_demo.py` | 27 | Strict inputs, end-to-end replay, vehicle coverage, candidate identity, completion/site-first choice, failed strict-UK admission and stale-result rejection |

The 500 earlier methods are retained. Counts are test methods, not the number of asserted railway standards, certified components or completed production requirements.

The supported geometry model has independent evidence from fixed endpoint/dimension checks, explicit route inventories, analytic component bounds, resource-set inspection and standalone diamond fixtures. Operating verification uses a separate interval sweep rather than the scheduling calendar's conflict routine. Underlying physical models remain uncalibrated.

## 4. Evidence files

| Artifact | Evidence |
|---|---|
| [Test report](proof/results/v07_test_report.json) | Exact 592 test IDs, counts, environment and source/fixture/evidence hashes |
| [Test log](proof/results/v07_test_log.txt) | Individual test outcomes |
| [Historical v0.6 report](proof/results/v06_test_report.json) | Preserved 500-test record |
| [Geometry search](proof/compact_results/geometry_search.json) | All 27 candidates, six accepted fits, reasons and selected parameters |
| [Restricted searches](proof/compact_results/restricted_search_examples.json) | Zero/limited work budgets and no candidate under the added 600 m specialwork limit |
| [Fixture](proof/compact_fixtures/release.json) | Frozen source-informed/synthetic assumptions and scenario definitions |
| [Summary](proof/compact_results/summary.json) | Family inventory, 64 result rows and explicit incomplete full-design status |
| [Comparison](proof/compact_results/comparison.md) | Completed, unscheduled, residual and delay metrics |
| [Scissors network](proof/compact_results/scissors__compiled.json) | Actual placed geometry, explicit diamond and resource provenance |
| [Scissors assessment](proof/compact_results/scissors__assessment.json) | Original plan checks, scoped UK checks and unresolved approval gates |
| [Scissors vehicle audit](proof/compact_results/scissors__vehicle.json) | All selected route sweeps and 23 listed pair studies for that candidate |
| [A-bank closure trace](proof/compact_results/scissors__bank_a_platforms_closed.json) | Actual B1 recovery assignments, reservations and checker result |
| [Decision packets](proof/compact_results/decision_packets.json) | Required-scenario-driven choices with no construction authority |
| [Release validation](v07_release_validation.json) | Local links/JSON, tested-input and preceding-release regression checks |
| [Manifest](v07_manifest.json) | SHA-256 inventory with declared self-exclusions |

The integration tests run a smaller, explicitly declared fixture twice and compare every resulting file byte-for-byte. The delivered full study uses twelve pairs and all sixteen scenarios. Replay on this runtime does not guarantee identical floating-point bytes on every platform/version.

## 5. Important findings

The generated plan has exact original approach ports, original boarding intervals, original road ordinates, terminal markers at x = 1,000 m and a non-overlapping concourse reservation. Its track centreline control hull fits the original rectangle. The selected specialwork extent is x = 160–630 m.

The scissors candidate completes all 24 visits during either platform-bank closure separately. It cannot bypass a failed fan or arrival lead, and its two directions have different long-train compatibility because their receiving berths differ. Normal timings match all four candidate families under the matched-section experiment.

Seventy-two representative-body route sweeps and eighty-one listed pair studies are delivered. Their result scope remains static-polyline, single-body and read-only. The nine studied recovery-space contacts retain scheduling exclusions.

The best grid candidate is not a globally optimal railway design. A failed 600 m grid search is not an impossibility proof. No geometry result, test count or low delay grants strict UK or game-construction authority.

## 6. Regression and package validation

All **52 prior model/test source files** and **126 prior deterministic JSON/Markdown output files** compared with the v0.6 archive are byte-identical. This includes the v0.6 `railstation` model and its output, not only older subpackages. All six demo runners were executed for this release.

Updated specification chapters, the test runner, release verifier and current acceptance files are deliberately outside the frozen-source comparison. Historical acceptance reports are preserved separately; elapsed test times are not compared as deterministic simulation outputs.

The standalone verifier checks local Markdown targets/fragments, strict finite JSON, tested source/input hashes, test-count consistency and manifest integrity. With the preceding archive supplied, it also checks the stated baseline file sets. No third-party source document is repackaged as part of this authored release.

## 7. Acceptance boundary

**Accepted for continued offline development:** original-plan geometry, targeted two-direction recovery through an explicit scissors, restricted fixed-diamond topology, a bounded geometric grid, integrated source-qualified assessments and completion-first decisions.

**Not accepted:** full site engineering, authentic UK pointwork/diamond hardware, a speed-rated component catalogue, complete platforms/access, full dynamic/3D gauging, actual signalling, physically modelled approach queues, calibrated railway capacity, TPF3 construction, or measured plan-credit savings.

The original 75 requirements, 32 pattern families and 41 broad benchmarks still describe a larger system than this increment. The next work should challenge the compact layout with stronger component and platform/vehicle data rather than treating synthetic success as final UK-network readiness.
