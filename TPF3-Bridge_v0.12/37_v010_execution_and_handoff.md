# v0.10 execution evidence and implementation handoff

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.10.0 · **Date:** 21 September 2026  
**Executed:** **917 test methods**, including **107 new methods**, with no failures, errors or skipped tests. The new full demonstration contains 17 geometry trials, 30 operating comparisons and eleven mock execution cases.

## 1. What was actually run

The full unit/integration suite and the new `railbranch` demonstration were executed in this conversation's Linux runtime, using Python **3.13.5**. Runtime dependencies remain Python standard-library modules. The exact environment, method IDs, inputs and source hashes are recorded in [test_report.json](proof/results/test_report.json).

The recorded suite elapsed time is one container measurement, approximately **24.627 seconds**. It is not total release-writing time, Windows performance, a p50/p95 latency promise or a measured plan-credit saving. No model, desktop or game calls occur inside the demonstration runner.

From `proof/`:

```sh
python run_tests.py
python -m railbranch.demo --output branch_results
```

Keep the root `evidence/` directory alongside `proof/`. The runner uses local authored and reviewed records; third-party PDFs do not need to be downloaded to repeat it.

The eight preceding packages and their old full-study outputs remain regression references. The full suite includes earlier integration tests, but the historical full-study outputs are **preserved and byte-compared**, not all advertised as freshly rerun full demonstrations. The new demonstration is rerun in its integration tests and independently as the delivered full study.

## 2. New code and verification coverage

| Test module | Methods | Principal checks |
|---|---:|---|
| `test_branch_geometry.py` | 36 | Four complete movements, actual merge, fixed components, boundary and derivative joins, crossing location/height/footprint, ramp-fit and gradient failures, numeric lengths, lowering bounds and holding distinctions |
| `test_branch_operations.py` | 35 | Geometry-derived claims, crossing removal without merge removal, tail clearance, common pulse scenarios, closures, preserved demand, budgets, fixed blocks, horizon accounting and tampered-result rejection |
| `test_branch_adapter.py` | 25 | Unique physical construction, turnout semantics, no crossing turns, capability/preflight checks, idempotency, receipt recovery, current-object inspection, partial effects and final route verification |
| `test_branch_demo.py` | 11 | Closed fixture parsing, complete replay, search and scenario accounting, source-input binding, common comparisons and no game/terrain approval |

The 810 earlier test methods are retained. These counts describe Python methods, not independently certified railway rules or completion of the original 75 requirements and 41 broad benchmarks.

Independent checks include explicit route and component inventories, dense numerical comparisons of geometry/length/interpolation, direct holding-length assertions, and a separately implemented event sweep for incompatible reservations. The latter does not call the scheduling calendar's conflict routine, although it intentionally shares the declared geometry/timing model for expected claims. It verifies internal consistency, not the empirical validity of that physical model.

Negative tests alter route/state claims, omit demand, remove expected resources, tamper with current physical state, change source identities and attempt invented crossing connections. A received `passed` flag is not trusted as its own evidence.

## 3. Inspectable artifacts

| Artifact | Evidence |
|---|---|
| [Current test report](proof/results/test_report.json) | 917 method results, exact environment and tested source/fixture/evidence hashes |
| [Test log](proof/results/test_log.txt) | Individual method outcomes |
| [Historical v0.9 report](proof/results/v09_test_report.json) | Preserved 810-test acceptance record |
| [Fixture](proof/branch_fixtures/release.json) | Exact local-site, ramp, motion, search and demand inputs |
| [Input provenance](proof/branch_results/input_provenance.json) | Sourced formation field, nominal spacing, assumptions and new-site status |
| [Geometry search](proof/branch_results/geometry_search.json) | 17 trials, five accepted screens and selected mode instances |
| [Limited search](proof/branch_results/limited_search.json) | Explicit incomplete work-budget outcomes |
| [Flyover geometry](proof/branch_results/flyover__geometry.json) | Shared physical network, heights, route lengths, component origin and crossing-fit results |
| [Flat resources](proof/branch_results/flat__resources.json) | Explicit crossing, component and running-track claims |
| [Flyover resources](proof/branch_results/flyover__resources.json) | Named crossing absent; shared merge resources retained |
| [Common scenarios](proof/branch_results/scenarios.json) | Reused request times, closures and stress inputs |
| [Comparison](proof/branch_results/comparison.md) | All 30 rows, with unscheduled/residual work and scheduled-only entry delay |
| [Merge trace](proof/branch_results/flyover__merge_pulse.json) | Actual competing reservations after grade separation |
| [Holding trials](proof/branch_results/holding_geometry_trials.json) | Full train length versus margins, with no constructed stop claim |
| [Mock flyover plan](proof/branch_results/flyover__mock_plan.json) | 14 ordered physical/component/crossing-reservation operations |
| [Mock cases](proof/branch_results/mock_execution_cases.json) | Successful semantic read-back and bounded failure/recovery outcomes |
| [Unprobed capabilities](proof/branch_results/tpf3_unprobed_capabilities.json) | No invented live API support |
| [Decision packets](proof/branch_results/decision_packets.json) | Crossing alternatives versus still-failed merge objectives |
| [Release validation](release_validation.json) | Local links/JSON, tested-input hashes, baseline comparison and manifest checks |

Hashes refer to actual bytes or explicitly normalised records. A normalised JSON hash and a raw-file hash may differ; neither is an attestation from a manufacturer. Source URLs are not assigned invented file hashes.

## 4. Acceptance and limits by layer

| Layer | Accepted in this release | Still unresolved |
|---|---|---|
| Branch topology | Four complete boundary movements and explicit shared merge | Other branch directions, alternative topologies and arbitrary site headings |
| Local geometry | Fitted component joins, full ramp approaches, crossing-band separation and restricted plan-order checks | Complete vehicle/civil clearance, authentic specialwork, canted profiles |
| Site | New declared local planar enclosure | Actual terrain, protected land, civil toes and insertion into the v0.9 landscape |
| Operations | Whole-pass time-space reservations, crossing/merge counterexamples, tail-aware accounting | Grade-sensitive traction, live/game signalling, internal stopping and spatial queues |
| Holding | Curved-path available length, physical tail versus selected margins | Constructed signals, braking/restart and usable queue capacity |
| Construction | Semantic mock plan, current-object read-back, no duplicate effects | Real TPF3 functions, structure assets and observed traversal |
| UK realism | Retained nominal spacing and sourced complete-unit length, explicit project targets | No new complete UK turnout family, national geometry table or exact gauge |
| Model usage | No model calls inside local search/scheduling/mock loops | No observed plan-credit saving or production agent benchmark |

The crossing-pulse result shows the intended local benefit; the merge and downstream-closure tests prevent overclaiming. Completing requests within a generous reporting horizon does not establish a useful timetable. Raised/lowered timing equality is an artefact of the level-track performance law, not a real engineering conclusion.

## 5. Regression and packaging

The previous model packages and earlier test files are unchanged. New code lives in `railbranch`; the test runner and release verifier are maintenance exceptions. Earlier current acceptance records are preserved separately before the new report replaces them.

The verifier compared **84 prior model/test source files** and **239 prior deterministic output files** against the actual v0.9 ZIP; all were byte-identical. Exact paths and mismatch arrays are in [release_validation.json](release_validation.json). Documentation updates, the expanded runner/verifier, current test logs and elapsed times are deliberately excluded from historical byte-equality claims.

From the root:

```sh
python verify_release.py
python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.9.zip
```

The manifest excludes itself and the separate validation record to avoid recursive dependencies. Local links and fragments, finite JSON, tested-byte hashes and test-count consistency are checked. ZIP integrity is checked during packaging. A successful validation command does not rerun the simulation or convert historical outputs into newly executed results.

## 6. Research and next implementation gate

One dated infrastructure-owner project record, [S070](10_source_register.md#s070), adds a selective grade-separation reference. It supplies context, not a numeric input or replica geometry. The source register now contains 70 records with differing reviewed scopes. Existing UK numerical/component limitations remain visible rather than being overwritten by a larger synthetic demonstration.

The next integration target is **terrain-aware placement of this connected junction into the corridor**. Preserve the actual external ports and model the spread-track land take, structure reservations and remaining merge. Where the terrain forces a different arrangement, regenerate and re-evaluate the candidate rather than carrying across old passes.

Grade-aware practical performance and physical holding are important follow-on checks. Actual game capability probing remains separate and must use a named build. More detailed station internals, crowd simulation and specialist real-world certification are not the default next workstream.
