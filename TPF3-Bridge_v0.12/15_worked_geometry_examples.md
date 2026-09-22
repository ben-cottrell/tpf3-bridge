# Worked geometry examples and actual operating results

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.3.0 · **Date:** 20 September 2026  
**Fidelity:** Synthetic planar component geometry and geometry-derived whole-leg resources. No real-station reproduction, UK design approval or game construction is claimed.

## 1. Reproducible inputs and boundaries

The complete input is [release.json](proof/geometry_fixtures/release.json). The executed outputs are [summary.json](proof/geometry_results/summary.json) and [comparison.md](proof/geometry_results/comparison.md). All dimensions, service times, corridor widths and component shapes below are authored synthetic inputs.

There are two independent examples: a complete crossover and a four-road terminal bank. The second has only **one bidirectional approach**. These are building blocks for the four-approach, eight-platform terminus in [12](12_worked_station_design.md), not completion of that brief. The seven historical v0.2 scenarios and their 21 comparisons remain a separate resource-template experiment.

## 2. Example A — A crossover between parallel tracks

| Input | Value | Meaning |
|---|---:|---|
| Parent-track spacing | 4.5 m | Centreline spacing in the synthetic fixture |
| Eased component span `L` | 40 m | Span of each authored synthetic turnout centreline |
| Divergent terminal slope `m` | 0.075 | Tangent gradient in plan, not crossing angle or speed classification |
| Selected minimum-radius profile | 300 m | Synthetic bound checked by the compiler |
| Maximum permitted longitudinal span | 120 m | Fixture footprint constraint |
| Default linked-control model | Enabled | Both component controllers request common N/R states |

The fitted toe-to-toe longitudinal span is `40 + 4.5/0.075 = 100 m`. The tangent connector is positive and all selected routes pass the implemented position/tangent/curvature join checks.

The compiled crossing-route length lies between approximately **100.139606 m and 100.139695 m**. This measured curved distance, rather than the 100 m longitudinal projection, is supplied to the timing model. The interval is a numerical arc-length bracket, not a surveyed length.

The output contains seven physical edges, four exposed route definitions and 22 resource records. Resource count includes overlapping physical, component, controller and proximity descriptions; it is not a signal count, point count, capacity score or cost estimate. Inspect [crossover_compiled.json](proof/geometry_results/crossover_compiled.json) for individual provenance.

### 2.1 Parallel and crossing movements

All three requests have relative request time zero, train length 160 m, speed surrogate 8 m/s, setup 5 seconds and release 3 seconds. The declared request order is lower-through, upper-through, crossing. It is not a globally optimised timetable.

| Movement | Scheduled start | Clear time | Waiting |
|---|---:|---:|---:|
| Lower straight-through route | 0.000 s | 40.501 s | 0.000 s |
| Upper straight-through route | 0.000 s | 40.501 s | 0.000 s |
| Supported crossing route | 40.501 s | 81.019 s | 40.501 s |

The two straight movements share a compatible controller state but not exclusive running space under this fixture. The crossing movement requires conflicting resources and waits. This is a concrete result from [crossover_route_test.json](proof/geometry_results/crossover_route_test.json), not a manually populated conflict matrix.

The outward length bound and integer-millisecond rounding can add a millisecond to an otherwise round-looking time. The output deliberately preserves this conservatism rather than formatting the result as an exact analytic travel time.

A route on the opposite diagonal is not available. The graph rejects it instead of treating the four exposed ends as an unrestricted junction.

## 3. Local fitting without Astra retries

The fitter enumerates 35 declared combinations: five branch slopes and seven spans. It holds the supplied parent spacing and maximum longitudinal span fixed. Every candidate is regenerated, compiled and checked; rejected candidates remain in the local search record.

| Request | Actual result | Correct interpretation |
|---|---|---|
| Fit within 100 m | Three candidates found in the full 35-combination grid; selected candidate spans 95 m | A fit exists within this synthetic catalogue and finite search |
| Fit within 70 m | No candidate in the 35-combination grid | Not a proof that no other component, geometry or topology could fit |
| One-evaluation budget | `search_exhausted` | Search did not complete; no global infeasibility claim |

The selected 95 m candidate uses `L=45 m`, `m=0.09`. Its geometry must not be confused with the separate 100 m crossover used in the route timing demonstration. Selection favours shorter span among the enumerated fitting candidates; it is not an assessment of real maintenance, speed or civil cost.

The full [search record](proof/geometry_results/crossover_search.json) exposes attempted parameters, reasons and retained candidates. A future agent would receive only the compact result and any required design decision, not 35 individual calls asking it to adjust the points.

## 4. Example B — A four-platform single-approach bank

| Input | Value |
|---|---:|
| Platform roads | 4 |
| Centreline y positions | 0, 12, 24, 36 m |
| Initial turnout toe | x = 50 m |
| Subsequent toe step | 150 m |
| Synthetic turnout span / slope | 50 m / 0.1 |
| Boarding intervals | x = 650 to 910 m |
| Platform rear-stop markers | x = 655 m |
| Margin at each boarding end | 5 m |
| Site end | x = 1000 m |

The three main-spine diverging components occur at x=50, 200 and 350 m. Branches serve the farthest road first. Their return curves finish at x=460, 490 and 520 m respectively, before the boarding region.

The full compiled bank has 23 physical track edges, eight exposed routes and 60 resource records. Three divergent paths return to parallel tangents; the spine serves the fourth road. This geometry is generated from the component/specification inputs, not traced from a station passenger map.

| Platform | Arrival-path upper length to marker |
|---|---:|
| P1 | 655.000000 m |
| P2 | 655.534567 m |
| P3 | 656.133074 m |
| P4 | 656.731582 m |

Displayed values are rounded; the [compiled JSON](proof/geometry_results/fan_compiled.json) retains the full brackets and edge-chainage records. Reverse routes are explicit legal paths and are checked independently of mere reachability to the platform.

### 4.1 Stopping position is part of the model

A train berthed under this fixture has its rear at x=655 m, and its front one train length farther along the road. A 160 m train therefore occupies x=655 to 815 m; a 240 m train occupies x=655 to 895 m. Reversal starts the departing front at x=655 m.

The maximum fitting length is 250 m after the two 5 m margins. Tests reject a formation just above that limit as well as the 280 m overlength scenario. The physical track length beyond a boarding edge cannot rescue an overlength passenger-platform assignment.

This near-entry rear-marker convention is explicit and synthetic. It is not a universal UK terminal stopping policy. A future fixed-front buffer-end stop target requires a different movement-to-stop contract, rather than reusing these timings without adjustment.

The storage edge and its proximity resources stay reserved throughout the complete visit. A train waiting for departure therefore continues to block any conflicting held space. The model deliberately does not release the platform when the incoming front merely reaches the station.

## 5. Bank service scenario

The base demand contains twelve visits on corridor group A, one every 300 seconds. Each train is 160 m long. Planned departure is 370 seconds after requested entry. The serial activity assumption is 60 seconds dwell, 180 seconds turnaround/readiness and 20 seconds dispatch. Two outgoing activities are labelled empty stock but still occupy track.

The new timing model uses each generated path's upper length, plus train length, at the declared constant-speed surrogate. Unlike v0.2's eight-platform example, no hand-entered 160/280 m throat distance is used. No actual UK timetable, train-performance measurement or TPF3 reservation rule is implied.

The scheduler is greedy and deterministic. It considers complete fitting incoming–berth–outgoing opportunities and retains the chosen earlier assignments. It does not backtrack to prove a global optimum. Departure delay is reported only for scheduled visits, alongside the work that was not scheduled.

## 6. Actual bank results

| Scenario | Scheduled / required | Completed by horizon | Unscheduled | Scheduled residual | Total departure delay of scheduled visits |
|---|---:|---:|---:|---:|---:|
| Nominal | 12 / 12 | 12 | 0 | 0 | 1,078.842 s |
| P1 closed | 12 / 12 | 12 | 0 | 0 | 1,079.849 s |
| P1–P3 closed | 12 / 12 | 12 | 0 | 0 | 11,893.248 s |
| All platforms closed | 0 / 12 | 0 | 12 | 0 | 0 s |
| 240 m trains | 12 / 12 | 12 | 0 | 0 | 1,909.494 s |
| 280 m trains | 0 / 12 | 0 | 12 | 0 | 0 s |
| 1,200 s reporting horizon | 12 / 12 | 3 | 0 | 9 | 1,078.842 s |
| Zero search budget | 0 / 12 | 0 | 12 | 0 | 0 s |

Every row comes from the included [comparison](proof/geometry_results/comparison.md) and individual trace files. The closed/overlength/budget rows do not receive a favourable score for zero delay: required work was not performed. The short-horizon residual includes work beyond the reporting cutoff; it is not a count of physical trains queued outside the station.

The severe three-platform closure still schedules all visits within the deliberately generous entry-wait bound. That is not evidence of acceptable passenger service. A production brief must apply explicit lateness, recovery and service-completion objectives before approving such a candidate.

## 7. Geometry sensitivity without a false layout ranking

The runner also compiles compact, baseline and extended bank variants. Their approach distances and compile hashes change. All three happen to retain the same 60 resources, including 31 proximity pairs, under the selected profile.

This is useful evidence that resource cardinality alone is an inadequate description: equal counts can coexist with different route distances and parameter values. It does not demonstrate a change in conflict-pair count for those three cases. Separate automated tests do exercise nearby unconnected tracks that gain a proximity conflict while retaining separate rail graphs.

The variants use different platform-start/site conditions. They are explicitly a boundary sensitivity study, not a like-for-like claim that one complete station is better than another. See [fan_geometry_sensitivity.json](proof/geometry_results/fan_geometry_sensitivity.json).

## 8. Compact result and engineering decision

The executed [decision packet](proof/geometry_results/decision_packet.json) points to the full traces and preserves unresolved engineering/game domains. It does not send all subdivision leaves, edge pairs or calendar iterations to Astra.

The justified next decision is to use these subassemblies as the basis for composing a bank with separate arrival/departure approaches. Construction is not yet authorised: the synthetic catalogue, full gauging, signalling, passenger/civil interfaces and game representation remain unresolved.

The experiment establishes a working link from fitted component geometry to a reproducible operating comparison. It does not complete the whole railway engineer, prove a real station's capacity or measure model-plan credit savings.
