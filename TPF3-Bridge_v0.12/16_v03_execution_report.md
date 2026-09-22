# Version 0.3 execution evidence and acceptance report

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.3.0 · **Date:** 20 September 2026  
**Executed:** 176 authored test methods — 83 legacy v0.2 tests and 93 new geometry/compiler/operation tests — with zero failures, errors or skipped tests in the recorded release run.

## 1. What was run

The Python code was executed in the conversation's Linux runtime with Python 3.13.5. It uses the standard library and makes no model, game or desktop-control calls. This is an executed offline proof, not an estimate of what a future Codex session might achieve.

```sh
cd proof
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
```

The legacy runner remains version 0.2.0 deliberately. It reproduces the earlier 21 resource-template comparisons. The new geometry fixture/runner uses version 0.3.0 and produces a crossover route trial, eight bank scenarios, three finite-search requests and three geometric boundary-sensitivity records.

The current report records the elapsed duration of the individual suite run. That number is not a p50/p95 benchmark, a Windows compatibility result, total development time, a production latency promise or evidence of plan-credit savings.

## 2. Evidence inventory

| Artifact | Evidence supplied |
|---|---|
| [Current test report](proof/results/v03_test_report.json) | 176 outcomes, exact executed test IDs, environment, source hashes and fixture hashes |
| [Current test log](proof/results/v03_test_log.txt) | Individual test names and execution outcomes |
| [Preserved v0.2 test report](proof/results/v02_test_report.json) | Historical 83-test acceptance record, not silently overwritten by the new count |
| [Geometry fixture](proof/geometry_fixtures/release.json) | Synthetic components, geometry/profile inputs, services, timings and scenarios |
| [Geometry summary](proof/geometry_results/summary.json) | Actual compiled lengths/counts, scenarios, searches and provenance |
| [Crossover compiled model](proof/geometry_results/crossover_compiled.json) | All ports/edges, route paths, bounds, resource origins and unresolved assessments |
| [Fan compiled model](proof/geometry_results/fan_compiled.json) | Four-road single-approach assembly, route lengths and held storage exclusions |
| [Route concurrency trial](proof/geometry_results/crossover_route_test.json) | Independent straight routes and conflicting crossing request with claims/witnesses |
| [Bank comparison](proof/geometry_results/comparison.md) | Eight actual scenario rows, retaining unscheduled and residual work |
| [Finite search trace](proof/geometry_results/crossover_search.json) | Candidate parameters, rejection reasons, fitting candidates and budget outcomes |
| [Geometry decision packet](proof/geometry_results/decision_packet.json) | Bounded summary linked to detailed local evidence |
| [Release validation](v03_release_validation.json) | Local link/JSON/package checks and legacy-regression comparison |
| [Manifest](v03_manifest.json) | SHA-256 inventory with explicit self-exclusions |

The third-party source PDFs are not redistributed in this package. Source reinspection records describe the actual scope and do not invent hashes for unarchived external documents.

## 3. New test groups

| Test file | Methods | Principal checks |
|---|---:|---|
| `test_geom_kernel.py` | 29 | Analytic curve definition, derivatives, endpoint conditions, reversal/mirroring, arc-length brackets, curvature bounds, continuous proximity, invalid inputs and subdivision budgets |
| `test_geom_compiler.py` | 34 | Legal component traversals, explicit connectivity, whole-assembly joins, unmodelled intersections, linked states, proximity without connection, route lengths, storage resources, provenance, hashes and finite fitting |
| `test_geom_operations.py` | 30 | Parallel/crossing route outcomes, tail-clear timing, complete visits, fit limits, closures, stock readiness, held storage, search exits, horizon accounting, deterministic replay and fixture contracts |

The 83 legacy tests are unchanged. The 176 methods contain multiple assertions and fixtures, but the report does not inflate that into a claim of hundreds of independently validated engineering rules.

## 4. Checks with independently structured oracles

The curve tests compare generated geometry against its explicit polynomial and derivatives. An independently written numerical integral is compared with the subdivision length bracket. Representative curvature samples cross-check the conservative bound; the bound is not justified solely by those samples.

The proximity tests include a curve whose interior approaches another curve even though endpoint chords alone would miss it. The underlying check uses continuous leaf enclosures, rather than promoting a few sample points to a clearance proof.

The calendar tests compare event-boundary search with a small integer-time brute-force oracle and inspect committed claim compatibility. Geometry-operation tests also check identities, fit, readiness, closure eligibility and unserved work. Sharing the calendar implementation with the legacy proof preserves regression behaviour but does not constitute an independent real-world railway simulator.

The authored components are simple monotone local shapes. The suite is not an exhaustive proof over arbitrary curves, every component library or every possible floating-point input. Its explicit scope is part of the acceptance result.

## 5. Findings demonstrated by execution

The crossover allows two straight-through requests at the same time under the declared resources, while the crossing request waits. Linked point-state compatibility therefore does not automatically imply shared physical occupation or erase a real track conflict.

The four-road bank supplies actual fitted path lengths to the operating model. A platform assignment requires a fitting berth and both incoming and outgoing routes. Occupied storage resources remain held while a train waits for departure.

The finite crossover search found three fitting candidates in a declared 35-combination grid under a 100 m span limit, selecting a 95 m candidate. A 70 m limit returned no candidate in that grid; a one-evaluation budget returned an uncompleted search. These outcomes remain distinct.

All-platform closure, overlength trains and zero search budget retain all twelve unscheduled visits. Their zero delay totals cannot be interpreted as good service. The short-horizon run retains nine scheduled residuals rather than calling every scheduled visit completed.

## 6. What remains unimplemented or unassessed

| Domain | Current limit |
|---|---|
| Full station brief | Only a single-approach four-road bank; no four-approach eight-platform assembly |
| Real switches and crossings | Synthetic eased centreline component only; no approved dimensional catalogue or detailed rail hardware |
| Vehicle clearance | Continuous synthetic corridor proxy, not a kinematic swept envelope or full GB gauging assessment |
| Geometry generality | Level/zero-cant authored patterns; no general arbitrary component importer or full 3D conflict system |
| Signalling | Explicit synthetic state maps; no authentic control tables, overlaps, flank protection or signal-aspect simulation |
| Resource timing | Whole-leg constant-speed reservations; no sectional release, acceleration/braking or physical queue spillback |
| Platforms and passengers | Scalar fit plus held storage; no complete boarding-edge, accessibility, circulation or crowd model |
| Civil works | No structural, drainage, formation, electrification or buffer-stop design certification |
| Optimisation | Finite family-specific fitting and greedy scheduling, not a general global station optimiser |
| Integration | No MCP server, TPF3 mod, tested construction API or observed in-game behaviour |
| Economics/usage | No actual plan-credit saving, construction cost or real capacity estimate |

The two narrow platform-clause evaluators introduced in v0.2 remain available; they do not turn the new geometry profile into UK-compliant design. The full 75 production requirements, 32 pattern contracts and 41 project benchmark definitions remain broader than this implementation.

## 7. Reproducibility and release discipline

Run the commands above from a clean extracted directory. The suite writes its report and log; both demos write their outputs. Source and fixture hashes in the test report refer to the executed bytes. The release manifest adds hashes for authored documents and generated outputs, excluding itself and the release-validation record to avoid self-reference.

Changing a curve, profile, stock length, controller mapping or scenario invalidates the relevant previous result. Matching resource counts alone is not evidence of an unchanged model. The compile hash and detailed provenance should be used for comparison.

All previous source IDs and main requirement/pattern/benchmark IDs are retained. Research dossiers not edited for this release keep their earlier revision headers; they are carried-forward evidence, not newly verified exact station replicas.

## 8. Acceptance decision and next gate

**Accepted for:** a tested synthetic planar geometry-to-resource proof, a complete authored crossover subassembly, a small generated bank fan, bounded local fitting and inspectable operating results.

**Not accepted for:** automatic construction of the original station brief, an authentic UK switches-and-crossings design, signalling approval, real-world passenger-capacity prediction or game integration.

The next gate is to compose explicit arrival and departure access around a bank and preserve its complete movement contract. Then add sectional resource occupation with train stopping/performance semantics, cross-checking against the conservative whole-leg baseline. These steps should precede claims about a complete large passenger-station throat.

## Later release context

This is the historical v0.3 report. The current release adds a two-approach bank, stopping motion, sectional release and selected numerical profiles; see [19](19_v04_execution_report.md). Earlier statements about unimplemented sectional release describe v0.3 only.
