# Offline proof, execution evidence and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

> **Historical v0.2 acceptance record.** The statements and counts below describe that release. Current geometry-derived implementation and the 176-test record are in [16](16_v03_execution_report.md).

**Version:** 0.2.0 · **Date:** 20 September 2026  
**Execution status:** 83 test methods run; 0 failures; 0 errors; 0 skipped. Seven scenarios evaluated against three predefined resource families: **21 comparisons**.

## 1. What was actually executed

The delivered Python package was run in the conversation's container using Python **3.13.5**. The authored tests and demonstration runner completed. This is a real offline execution, not an estimate of what tests might do.

The commands were `python run_tests.py` and `python -m railproof.demo --output results`, from the `proof/` directory. The standalone runner has no model, desktop-control or game calls. This does not measure any plan-credit saving from a future agent workflow.

The recorded unit-suite elapsed time in the current acceptance file is **0.437 seconds**, from one container run. That is not a p50/p95 result, cross-machine benchmark, production latency commitment or total time spent researching and writing the release.

## 2. Inspectable evidence

| Artifact | What it establishes |
|---|---|
| [test_report.json](proof/results/v02_test_report.json) | Counts, exact Python version, elapsed time, success flag and code/test SHA-256 hashes |
| [test_log.txt](proof/results/v02_test_log.txt) | Individual test names and outcomes |
| [comparison.md](proof/results/comparison.md) | All 21 family/scenario result rows |
| [summary.json](proof/results/summary.json) | Input hashes, metrics, analytic geometry and scoped rule examples |
| [decision_packet.json](proof/results/decision_packet.json) | Small executed-result packet pointing to detailed evidence |
| [Example full trace](proof/results/nominal__linked.json) | Assignments, claims, witnesses, events and unresolved assessments |

Hashes identify the bytes actually present. The source PDF files were not archived, and no source-byte hashes were invented. Re-running the test runner refreshes its timing and code hashes; re-running the demo refreshes scenario results.

## 3. Verified model behaviours

The suite tests physical identity independently of platform labels, train fit including margins, declared route eligibility, invalid input handling, stock predecessor consistency, state-versus-running-space conflicts and exact interval boundaries.

It also tests the complete-visit behaviour: a missing outgoing route rejects an apparently reachable berth; a blocked departure continues to occupy the berth; a berth conflict causes reconsideration of the incoming time; tail-clear timing includes train length; a late predecessor constrains the next working; and empty-stock movements still occupy the railway.

A small integer-time brute-force oracle checks the event-calendar search. Scenario-level checks independently inspect resource overlaps, timing, fit, closure eligibility, stock readiness and retained demand. Deterministic replay and finite-horizon residuals are tested.

The geometry suite verifies analytic endpoint conditions, mirroring, compression revalidation, finite input handling and a sampled cross-check of the analytic curvature bound. The rule suite verifies boundary values, missing inputs, applicability, existing-track scope and an unresolved national-interface branch.

## 4. What the tests do not prove

**They do not complete the 75 production requirements or 41 full project benchmarks.** The mapping in [09](09_validation_benchmarks_and_roadmap.md) identifies narrower behaviours exercised and remaining gaps.

The program does not yet generate a physical station throat. It has no actual turnout catalogue, geometry-derived route resources, vehicle swept-envelope system, microscopic train motion, spatial approach queues, complete passenger model or TPF3 integration. Its two clause checks do not establish an approved UK profile.

The resource families are assumptions supplied to the experiment. Differences in their results show what follows from those assumptions and the selected greedy policy, not which real station layout is universally best. No numerical land take, construction cost or realistic trains-per-hour capacity is inferred from the rows.

## 5. The most useful regression finding

In the A-bank-platform closure fixture, the isolated-bank family schedules twelve of twenty-four visits. Its small delay total applies only to those twelve. The common and linked families schedule all twenty-four but with much larger delay under the declared shared resources.

A comparison that considered delay alone would be misleading. The report therefore retains required, scheduled, completed, unscheduled and residual work separately, and the production specification requires hard completion checks before preference scoring.

The closure affects A-bank platforms, not the A approach or throat. Reusing that test result to claim recovery from a throat closure would be incorrect.

## 6. Geometry experiment in context

The isolated plain-line shift gives a sufficient length of approximately 88.285 m for the declared 4.5 m offset and synthetic radius target. The 100 m example passes its conservative curvature bound; the compressed 60 m example is not certified by that bound.

This is deliberately a narrow mathematical check. It does not produce a UK crossover, prove dynamic comfort or fit the proposed eight-platform throat. A failed sufficient bound is not automatically a proof that the exact curvature violates the target.

## 7. Acceptance statement for v0.2

**Delivered:** a continued Markdown specification; deeper targeted technical research; five new source records; original machine-readable evidence/rule records; a worked passenger-terminal brief; a runnable standard-library Python proof; actual test/scenario outputs; and explicit source, geometry and game limitations.

**Not delivered:** a complete railway engineering engine, exact station replicas, finished throat geometry, a production MCP server, an in-game mod, live API verification or measured plan-usage savings.

The next implementation gate is a complete crossover/fan component geometry pipeline whose derived resources replace one of the proof's assumptions. That is the link needed to move from a useful operating experiment towards Python acting as the railway engineer.
