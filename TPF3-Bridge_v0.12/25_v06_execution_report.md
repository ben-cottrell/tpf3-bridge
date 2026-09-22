# Version 0.6 execution evidence and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.6.0 · **Date:** 20 September 2026  
**Executed:** **500 test methods**, comprising 414 preserved methods and 86 new station methods. No failures, errors or skipped tests in the acceptance run. Three station families and twelve scenarios produce **36 operating comparisons**.

## 1. Delivered and executed

The new `railstation` package implements physical bank composition, imported recovery-component placement, matched study sections, a combined resource model, multi-group complete visits, independent result checking, site/vehicle/numerical assessment attachment and guarded decision packets.

The full test suite and all five demo runners were executed in the conversation's Linux runtime with Python **3.13.5**. The runtime dependencies are standard-library modules. This is not Windows, desktop-control or TPF3 validation.

```sh
cd proof
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
python -m railclear.demo --output clearance_results
python -m railstation.demo --output station_results
```

Keep `evidence/` next to `proof/`. No source PDF, game connection or model API is required to rerun the authored examples. Test duration in the JSON report is one measured execution, not an interactive performance promise or plan-credit saving.

## 2. Evidence files

| Artifact | What it establishes |
|---|---|
| [Current test report](proof/results/test_report.json) | Exact method IDs, counts, environment and tested code/input hashes |
| [Current test log](proof/results/test_log.txt) | Individual test outcomes |
| [Historical v0.5 report](proof/results/v05_test_report.json) | Preserved 414-test acceptance record |
| [Station fixture](proof/station_fixtures/release.json) | Declared station, traffic, motion, vehicle and work-budget inputs |
| [Station summary](proof/station_results/summary.json) | Candidate inventories and all 36 result rows |
| [Comparison](proof/station_results/comparison.md) | Scheduled, completed, unscheduled, residual, delay and recovery metrics |
| [Compiled A-to-B station](proof/station_results/a_to_b__compiled.json) | Physical network, legal routes, curve bounds and resources |
| [Candidate assessment](proof/station_results/a_to_b__assessment.json) | Original/proposed site checks, independence, component and UK-profile status |
| [Vehicle assessment](proof/station_results/a_to_b__vehicle.json) | All selected route sweeps, listed pair studies, assumptions and hashes |
| [A-bank closure result](proof/station_results/a_to_b__bank_a_platforms_closed.json) | Actual recovery assignments, locks, timing and independent verification |
| [Decision packets](proof/station_results/decision_packets.json) | Completion-first operating choices, joint recovery failure and unresolved build gates |
| [Release validation](release_validation.json) | Link/JSON/hash checks and comparison with v0.5 |
| [Manifest](manifest.json) | Package byte inventory with explicit self-exclusions |

The code reuses the existing body solver and motion model within their documented scope. A source/profile hash identifies the actual bytes or normalised record used; it is not evidence that an unreviewed source is authoritative.

## 3. New tests

| Module | Methods | Principal behaviours |
|---|---:|---|
| `test_station_composition.py` | 22 | Identity, four boundaries/eight roads, heterogeneous platforms, directional recovery, imported geometry, legal connectivity, matched sections, joint compilation and invalid fits |
| `test_station_operations.py` | 24 | Simultaneous normal entries, complete recovery, closure location, policy permissions, long trains, missing exits, stock, storage, budgets and horizon accounting |
| `test_station_checks.py` | 25 | Independent overlap/state checks, corrupt outputs, site/port/reservation failures and completion-first decisions with stale-input protection |
| `test_station_demo.py` | 15 | Closed fixture schema, end-to-end comparisons, byte-identical replay, evidence joins, vehicle coverage and unresolved UK/site gates |

Counts refer to test methods, not assertions, national standards, independent railway approvals or completed production requirements. Earlier test files are unchanged. The existing 75 requirement IDs, 32 pattern families and 41 broad project benchmarks still cover a larger system than this proof.

The independent output checker uses a separately implemented interval sweep rather than the scheduler's calendar conflict routine. Tamper tests remove storage locks, change point states and stock lengths, introduce overlapping reservations, discard required demand and attach stale hashes. Those modifications are rejected. It remains implementation verification, not validation against observed railway behaviour.

## 4. Executed findings

Every candidate has eight physical platform roads. The isolated instance has 16 service routes and eight turnouts; linked instances have 24 routes and ten turnouts. The whole-network compiler checks cross-bank edge pairs rather than trusting a union of previously independent subassemblies.

All 64 normal cross-bank route pairs are independent in each compiled resource model. Normal demand completes in all three instances with identical scheduled timings under the matched study sections. The selective links preserve that normal separation when unused.

A-to-B recovery completes all 24 visits with A platforms unavailable; B-to-A does the corresponding job when B platforms are unavailable. No tested candidate completes both separate bank-closure scenarios. An A fan closure can be bypassed by the A-to-B link, whereas an A arrival-lead closure cannot. These are different failure locations, not interchangeable versions of the same test.

The candidate assessments cover 64 representative-body route sweeps and 58 listed route-pair studies across the three instances. The tested normal pairs are separated within the supported static-polyline model; recovery path sweeps contact shared space. No result removes an existing rail/control/proximity resource or certifies full dynamic gauging.

All three candidates fail the original footprint and three exact approach-position requirements. Their actual rail-port span is 1,970 m. A separately labelled larger test rectangle passes only the declared planar/hull/reservation checks. None is authorised for construction or labelled a complete fulfilment of the original brief.

## 5. Regression and packaging

All **41 earlier model/test source files** compared with the v0.5 ZIP are byte-identical. The four earlier demo runners were executed again; **78 earlier deterministic JSON/Markdown output files** also match v0.5 exactly. Current test reports/timings are deliberately excluded from deterministic historical-output comparison. The test runner itself was expanded for the new package and test prefix.

The new integration suite runs the station demo twice with a smaller declared fixture and compares every produced file byte-for-byte. The separately delivered full study uses twelve pairs and all twelve scenarios. Replay on this runtime is not a guarantee of identical floating bytes across every platform/Python version.

Local Markdown targets and fragments, JSON validity, current test input/source hashes, the package manifest and ZIP integrity are checked. The standalone `verify_release.py` can repeat local validation; supplying `--baseline` additionally checks the preceding ZIP when that file is available.

## 6. Research and realism status

This is an integration increment, not a new source-acquisition release. The 63-source register and existing numerical/vehicle records are retained. No additional authentic pointwork, bogie dimensions, dynamic allowance or national clause is claimed to have been acquired.

The public manufacturer full-unit lengths continue into operational fit and tail clearance. The static body study still uses explicit rectangular-body/pivot assumptions. The imported recovery geometry is authored synthetic data; bank fans remain authored generators. Individual sourced radius/cant checks are attached to the candidate, but strict UK input admission remains blocked.

The production target is still a realistic UK network, not permanent use of these proof dimensions. Source-backed component families, full vehicle and platform interfaces, speed-dependent engineering, appropriate operating profiles and game capability verification remain mandatory workstreams.

## 7. Acceptance and next engineering gate

Accepted: an integrated four-approach/eight-road candidate family, combined geometry/resource compilation, asymmetric recovery, complete-visit operation, retained demand, candidate-bound assessments and compact decision packets.

Not accepted: the original small site, both-direction recovery in one instance, authentic UK pointwork, full gauging, a realistic-capacity prediction, spatial queues, passenger circulation, a production MCP server, TPF3 construction or measured plan usage savings.

The next useful engineering gate is **site-constrained approach sorting and compact recovery topology search**. It should retain the real eight-road boarding requirements and explicit service goals, replace the overlong direct cross-bank arrangement where possible, and return the actual remaining constraints rather than quietly editing the original brief.
