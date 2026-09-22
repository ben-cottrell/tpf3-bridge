# Integrated station experiment and decision records

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.6.0 · **Date:** 20 September 2026  
**Execution:** Three fitted family instances × twelve scenarios = **36 operating comparisons**, each checked independently. These are synthetic station studies, not estimates of a real station's capacity.

## 1. Reproduce the experiment

From `proof/`, run:

```sh
python -m railstation.demo --output station_results
```

The runner reads [station_fixtures/release.json](proof/station_fixtures/release.json), the retained manufacturer-dimension record and the authored component import. It builds the whole railway, compiles resources, audits representative vehicle paths, checks both site interpretations and numerical-profile gates, schedules the scenarios and emits compact decision packets. It makes no model or game API calls.

The [comparison table](proof/station_results/comparison.md) contains every operating row. [summary.json](proof/station_results/summary.json) contains counts, candidate hashes and interpretation boundaries. Each individual result includes complete assignments, claims, conflicts and its independent-check result.

## 2. Inputs and provenance

The base demand contains 24 complete visits, twelve for each group. A requests are spaced 300 seconds apart; B requests follow their paired A requests by 90 seconds. Planned departure is 700 seconds after each requested entry. Dwell, turnback and dispatch are separate serial activities of 60, 180 and 20 seconds. Four departures are labelled empty stock and still occupy the railway.

Those service frequencies, readiness times and planning offsets are **project-selected synthetic inputs**, not British timetable-planning rules. The four-hour horizon and four-hour entry-wait budget are experimental bounds, not an acceptable-delay target.

The normal formation uses the 162 m full-unit value retained from the Siemens reference; the long-unit scenario uses 242.6 m. They remain separate from the representative 20 m by 2.8 m body and assumed 14 m pivot spacing used for static clearance. No 162 m rectangle is swept as if it were a single vehicle. Source scope and missing exact geometry remain in [S060](10_source_register.md#s060) and [20](20_vehicle_envelopes_and_clearance.md).

The additional 300 m formation is expressly a synthetic train-fit stress case. It is not assigned the manufacturer's identity. All motion uses the unchanged project-selected level-track profile: 15 mph target, 0.6 m/s² acceleration and 0.7 m/s² braking, with the existing setup/release assumptions. Those values have not become manufacturer performance data or turnout ratings.

The three family instances share the outer track ports, platform geometry and study boundary. Their common-corridor release subdivisions are matched, as described in [23](23_two_bank_station_composition.md). Scenario input hashes match across the candidate comparison.

## 3. Scenario definitions

| Scenario | What changes | What must remain visible |
|---|---|---|
| `nominal` | Base demand | Complete movement feasibility and residual work |
| `bunched` | Groups of three pairs request together | Increased contention without deleting trains |
| `bank_a_platforms_closed` | All four A berths unavailable | A approach remains available; recovery may be possible |
| `bank_b_platforms_closed` | All four B berths unavailable | The reverse recovery requirement is evaluated separately |
| `a_fan_closed` | Both traversals of A:F1 unavailable | A pre-fan link may bypass the failed distribution component |
| `a_arrival_closed` | A's incoming lead unavailable | A route to the link itself is absent |
| `published_long_units` | Full-unit length becomes 242.6 m | Longer stopping/tail timing uses the same performance assumptions |
| `synthetic_300m` | Formation length becomes 300 m | Only the four 320 m boarding intervals fit with the stated margins |
| `all_platforms_closed` | All eight berths unavailable | All required visits remain unscheduled, not “zero-delay success” |
| `short_horizon` | Report at 1,200 seconds | Future, waiting, active and unfinished work remains counted |
| `zero_budget` | No scheduling evaluations permitted | `search_exhausted`, not a physical impossibility claim |
| `a_bank_closed_recovery_forbidden` | A berths closed; cross-bank policy disabled | Reachability cannot override the operating brief |

Closure checks apply to actual edges and storage in the compiled network. A failed lead must not be treated as though only its platforms were unavailable. Unknown closure IDs are rejected rather than ignored.

## 4. Selected executed results

All completion counts below refer to the declared four-hour horizon. Delay is summed **only across scheduled visits**; the unscheduled column must be considered before any preference ordering.

| Scenario | Family | Completed / required | Unscheduled | Departure delay, scheduled visits only |
|---|---|---:|---:|---:|
| Nominal | Isolated | 24 / 24 | 0 | 30,492.490 s |
| Nominal | A-to-B | 24 / 24 | 0 | 30,492.490 s |
| Nominal | B-to-A | 24 / 24 | 0 | 30,492.490 s |
| A platform bank closed | Isolated | 12 / 24 | 12 | 15,246.245 s |
| A platform bank closed | A-to-B | 24 / 24 | 0 | 97,158.473 s |
| A platform bank closed | B-to-A | 12 / 24 | 12 | 15,246.245 s |
| B platform bank closed | Isolated | 12 / 24 | 12 | 15,246.245 s |
| B platform bank closed | A-to-B | 12 / 24 | 12 | 15,246.245 s |
| B platform bank closed | B-to-A | 24 / 24 | 0 | 97,120.782 s |

The normal timings coincide because no recovery movement is selected, normal resource independence is preserved and the relevant geometry/section comparisons are matched. The existence of a link does not automatically force an ordinary train to reserve the other bank's fan.

The lower delay in a failed isolated-bank closure case is **not** better service: half the trains have no complete opportunity. The decision stage filters required completion before considering delay.

The large delays are also a warning. Completing the demand within a generous horizon is not evidence that the station provides an attractive or robust timetable. The long common approach, synthetic reservation model and supplied demand remain restrictive. No trains-per-hour or real-station improvement claim should be derived from these rows.

### 4.1 Failure location changes the useful repair

With A:F1 closed, the A-to-B candidate again completes all 24 visits because its A trains leave the A trunk before that fan and use B berths. With the A arrival lead closed, **every** tested candidate leaves twelve visits unscheduled: the trains cannot reach the cross-bank link.

This distinction belongs in Python's failure explanation. “A side unavailable” is too vague to justify a recovery recommendation. The explanation must identify the failed resource and the complete alternative movement that avoids it.

### 4.2 Long trains and heterogeneous platforms

The 300 m stress scenario is assigned only to A3/A4/B3/B4. The four shorter boarding intervals cannot acquire eligibility merely because all eight roads have a long track somewhere nearby. Both stopping-marker geometry and scalar fit are checked.

Longer formations affect route motion and resource tail clearance; they do not merely change a label in the platform allocator. The independent checker also rejects a result whose stored train length differs from its required formation.

## 5. Vehicle assessment follows the whole candidate

Every selected route receives a representative-body sweep: 16 routes for the isolated station and 24 for each linked station, giving **64 route audits** across the three instances. Each records parent geometry identity, actual polyline support, body assumptions, pose count and the between-pose bound.

The pair studies cover all sixteen cross-bank normal-arrival pairs, plus two additional representative normal arrival/departure comparisons per instance. Each linked candidate also includes two recovery interactions. That is **58 listed route-pair studies** in total, not every possible pair of routes or every car in every train.

In this executed fixture, the 54 tested normal-route pairs establish separation within the static polyline model. The four recovery pairs have sampled body contact/overlap, consistent with their use of shared rail space. A contact between path sweeps is a spatial conflict—not a prediction of a collision in the scheduled timetable.

The whole-pose bounding box provides a cheap conservative first check. Only a positive box-distance lower bound after subtracting both between-pose paddings can establish separation at that stage. Other pairs use the existing explicit polygon-pair screen and its work budget. A coarse or exhausted check cannot become a pass.

The assessment remains read-only: **no existing track, point-state or proximity resource is deleted**. Exact body geometry, full formations, dynamics, cant, 3D interfaces and the body-error transfer from Bezier curves to polylines remain unassessed. Route supports extend 35 m beyond each reported path for the representative-body study and are declared assumptions, not surveyed external railway.

Inspect [A-to-B vehicle evidence](proof/station_results/a_to_b__vehicle.json) and its matching [compiled station](proof/station_results/a_to_b__compiled.json).

## 6. Numerical requirements are attached without blanket approval

The candidate assessment carries the earlier source-backed base-radius and platform-cant/radius evaluators onto the current generated geometry. Platform straightness is read from the storage-edge geometry; the declared zero cant is obtained from the model metadata. The checks retain their source/condition scope. [S058](10_source_register.md#s058)

Passing those individual checks does not establish component authenticity, a diverging speed rating, complete national platform dimensions or a dynamic gauge. The strict-UK input gate stays blocked. This increment adds **no newly verified standards clauses or authentic turnout drawings**; it integrates existing dated evidence into the composed station rather than increasing the source count.

The actual authentic component and exact vehicle-data acquisition tasks therefore remain open. They must not disappear from the production plan because this larger synthetic layout can now run.

## 7. What Astra receives

Three example decisions are generated from the same verified results:

| Required scenario set | Operating-only outcome | Construction outcome |
|---|---|---|
| Nominal + A-bank closure | A-to-B supplies the tested complete recovery | Not authorised; original site and engineering gates remain open |
| Nominal + B-bank closure | B-to-A supplies the tested complete recovery | Not authorised; the same gates remain open |
| Nominal + both bank-closure scenarios | No tested candidate satisfies the set | A different topology or additional connection must be investigated |

“Both” means surviving either bank closure in separate scenarios, not simultaneously closing every platform. Even that narrower two-scenario resilience objective is not achieved by a single selective link in these instances.

The decision function rejects mismatched scenario hashes, stale candidate assessments, missing scenarios and unverified operating results. It cannot attach a clearance report from one fit to the schedule of another. It returns a provisional operating candidate only after required completion, never a build approval based on delay alone.

See [decision_packets.json](proof/station_results/decision_packets.json). Detailed traces remain local; the packet contains the material missing capability, the original-site failure and the necessary next design choice.

## 8. Interpretation and next search

This experiment closes the earlier gap between isolated demonstrations: component placement, combined geometry/resources, vehicle assessment, numerical checks and operating results now share one station identity.

It also identifies the next substantive design problem. The fixed family occupies a 1,970 m track span and fails three exact approach ordinates of the original brief. Its diagonal cross-bank arrangement is deliberately simple and long. The next search should compare earlier track sorting, compact paired crossovers and alternative fan organisation under fixed site and service requirements—not quietly enlarge the original rectangle or reduce the demand.

A useful future local search should return either a candidate meeting those constraints, a precise subset of unmet requirements, or a bounded-search result. It should not require Astra to move each individual turnout, and it should not call every unsuccessful fit an impossibility proof.
