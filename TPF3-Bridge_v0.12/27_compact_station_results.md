# Compact station: executed results, limitations and decisions

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.7.0 · **Date:** 20 September 2026  
**Executed study:** Four fitted candidates × sixteen scenarios = **64 independently checked operating comparisons**.

## 1. Reproduce and inspect

From `proof/`, run:

```sh
python -m railcompact.demo --output compact_results
```

The runner reads [the closed-schema fixture](proof/compact_fixtures/release.json), searches the declared geometry grid, compiles every complete station, audits its representative vehicle paths, evaluates the original plan contract and selected UK numerical checks, and schedules the supplied services. It has no model API or game calls.

The principal outputs are [comparison.md](proof/compact_results/comparison.md), [summary.json](proof/compact_results/summary.json), [geometry_search.json](proof/compact_results/geometry_search.json), [scissors assessment](proof/compact_results/scissors__assessment.json) and [decision packets](proof/compact_results/decision_packets.json). Full candidate networks, traces and vehicle checks sit beside them.

The v0.6 experiment remains in `station_results/`. These new results do not retrospectively turn that overlong layout into a successful original-site fit.

## 2. Shared inputs and unchanged assumptions

The default experiment keeps the v0.6 traffic inputs: twelve visits per group, A requests 300 seconds apart, and paired B requests 90 seconds later. Planned departure is 700 seconds after requested entry. Dwell, reversal/readiness and dispatch are represented by separate serial activities of 60, 180 and 20 seconds.

These are **synthetic test requests**, not a real passenger timetable or UK timetable-planning minima. The four-hour horizon and four-hour permitted entry-wait bound are experiment limits. Completion inside that horizon does not establish acceptable punctuality.

The base formation length is the retained 162 m manufacturer value; the published-long-unit scenario uses 242.6 m. Their source scope and limitations remain in [S060](10_source_register.md#s060) and [20](20_vehicle_envelopes_and_clearance.md). The 300 m formation is a deliberately synthetic stress case, not a named manufacturer's train.

All motion retains the project-selected 15 mph cap, 0.6 m/s² acceleration and 0.7 m/s² braking. Those inputs are neither a newly verified vehicle performance curve nor a turnout-speed rating. Tail clearance uses the actual total formation length. Clearance studies separately use the existing nominal-body interpretation and assumed bogie spacing; they do not sweep a 162 m rigid rectangle.

## 3. Core results

The counts below are **completed visits within the stated horizon**, against the same required 24 visits in each scenario.

| Scenario | Isolated | A-to-B only | B-to-A only | Scissors |
|---|---:|---:|---:|---:|
| Nominal | 24/24 | 24/24 | 24/24 | 24/24 |
| A platform bank closed | 12/24 | 24/24 | 12/24 | 24/24 |
| B platform bank closed | 12/24 | 12/24 | 24/24 | 24/24 |
| A fan closed | 12/24 | 12/24 | 12/24 | 12/24 |
| B fan closed | 12/24 | 12/24 | 12/24 | 12/24 |
| A arrival lead closed | 12/24 | 12/24 | 12/24 | 12/24 |

The scissors provides either bank's recovery in **separate experiments**. It does not operate with all eight platforms closed simultaneously. It also does not permit every approach to use every platform.

Under A-bank closure, A trains use B1 and return to A's departure. Under B-bank closure, B trains use A4 and return to B's departure. Required movements through the respective fans remain intact in those scenarios. A fan closure removes the route to the recovery connection, so that different failure cannot be bypassed.

This is a meaningful change from the earlier pre-fan link: the compact arrangement meets the original plan footprint but sacrifices broad receiving-bank access and fan-bypass capability. It should not be described as an unqualified improvement over every possible larger arrangement.

### 3.1 Delay and completion must be read together

| Scissors scenario | Scheduled / required | Completed | Unscheduled | Total departure delay of scheduled visits |
|---|---:|---:|---:|---:|
| Nominal | 24/24 | 24 | 0 | 0.000 s |
| Bunched | 24/24 | 24 | 0 | 3,435.344 s |
| A bank closed | 24/24 | 24 | 0 | 16,547.982 s |
| B bank closed | 24/24 | 24 | 0 | 15,366.846 s |
| B bank closed; 300 m trains | 24/24 | 24 | 0 | 36,172.224 s |
| A fan closed | 12/24 | 12 | 12 | 0.000 s |
| All platforms closed | 0/24 | 0 | 24 | 0.000 s |

The last two zero-delay values are not efficient operation; they exclude required work that could not be scheduled. The decision function checks completion before ranking complexity or delay.

Nominal zero departure delay also has a limited meaning. It means the schedule meets the supplied departure requests under this model. It does not mean zero arrival waiting, zero route occupation, no passenger delay, no congestion risk or universally sufficient capacity. The scenario's 700-second requested turnaround offset is part of that result.

No percentage gain over a real station is inferred. A shorter synthetic approach, different topology, earlier stopping opportunities and declared release model all influence the comparison with older proof layouts.

## 4. Train length exposes asymmetric recovery

With a 5 m margin at each end, B1's 260 m interval cannot fit the 300 m synthetic train. A4's 320 m interval can.

The `a_bank_closed_300m` scenario therefore leaves all twelve A visits unscheduled even in the scissors candidate. The existence of a geometrical route does not override train fit. Conversely, `b_bank_closed_300m` completes all visits through the longer receiving A4 berth, with substantial delay.

The normal `synthetic_300m` scenario assigns trains only to A3, A4, B3 and B4. The track extension from the boarding end at x = 970 m to the terminal marker at x = 1,000 m never creates extra boarding capacity.

A separate scenario closes A's platforms and B1. The other three B platforms remain available for B services, but A has no valid recovery berth. Python reports twelve unscheduled A visits instead of inventing access to B2–B4.

These cases should become permanent regression fixtures for any future platform-assignment optimiser or component replacement.

## 5. Complete scenario catalogue

| Scenario | Changed condition | Expected distinction |
|---|---|---|
| `nominal` | Base request set | Same normal service across candidates |
| `bunched` | Several request pairs arrive together | Additional conflict without dropping requests |
| `bank_a_platforms_closed` | A1–A4 unusable | Recovery to B1, where provided |
| `bank_b_platforms_closed` | B1–B4 unusable | Recovery to A4, where provided |
| `a_fan_closed` | Both A:F1 traversals unavailable | No downstream-link bypass |
| `b_fan_closed` | Both B:F1 traversals unavailable | Same distinct failure on B |
| `a_arrival_closed` | A arrival lead unavailable | No route to the station's recovery point |
| `published_long_units` | Formation length 242.6 m | Full unit length affects fit/motion |
| `synthetic_300m` | Formation length 300 m | Only the four longer platforms fit |
| `all_platforms_closed` | All berths unavailable | Required demand retained as unscheduled |
| `short_horizon` | Reporting cutoff at 1,200 seconds | Completed and residual work remain separate |
| `zero_budget` | No scheduling evaluations | Search exhaustion, not railway infeasibility |
| `a_bank_closed_recovery_forbidden` | A bank closed; policy forbids recovery | Physical connectivity is not permission |
| `a_bank_closed_inner_b1_closed` | A bank and its receiving B1 unavailable | No invented cross-bank platform choices |
| `a_bank_closed_300m` | A bank closed; overlength receiving train | Route exists but berth is unsuitable |
| `b_bank_closed_300m` | B bank closed; long train fits A4 | Different usable recovery capability |

The short-horizon scissors result records three completed and twenty-one scheduled residual visits. Residual does not necessarily mean a spatial queue: some requests are not yet due. The inherited state categories distinguish future, waiting, active and held work, but the model still has no spatial approach queue.

## 6. Vehicle and numerical evidence stays candidate-bound

There are **72 representative-body route sweeps** across the four candidates and **81 explicitly listed pair studies**. Seventy-two normal-pair studies establish separation within the supported static-polyline model. Nine recovery interactions have sampled body contact/overlap in shared running space.

Those nine contacts are not predictions of a collision. They identify places where the paths can occupy common space; the resource model prevents incompatible scheduled occupation. For example, the opposing recovery arrivals share the declared diamond and cannot traverse it simultaneously.

The audit does not delete any point, track, crossing or proximity resource. Exact body outlines, dynamic allowances, cant, full formations, three-dimensional structures and the parent-curve-to-body error bound remain unresolved. All supplied tangent continuations outside a route's model boundary remain explicitly authored supports.

The selected source-backed radius and platform-cant checks are attached to the same compile hash. The whole-candidate synthetic radius lower bound is about 312.619 m, while the storage roads used for platform checks are straight and have declared zero cant. These scoped checks do not transform the generated fan or diamond into approved British pointwork.

See [scissors vehicle audit](proof/compact_results/scissors__vehicle.json), [compiled network](proof/compact_results/scissors__compiled.json) and [assessment](proof/compact_results/scissors__assessment.json).

## 7. What the decision engine returns

The new decision stage requires both the scoped original plan contract and completion of every required operating scenario. It then applies an explicit project preference: fewer turnouts, fewer diamonds, lower scheduled delay, and stable identifier tie-breaking. This is not a universal ranking of railway layout types.

| Required scenario set | Offline candidate selected |
|---|---|
| Nominal only | Isolated banks |
| Nominal + A-bank closure | A-to-B link |
| Nominal + B-bank closure | B-to-A link |
| Nominal + either bank closure, separately | Scissors |
| Nominal + either fan closure | None of the tested candidates |

The packet remains `construction_authorised: false`. It rejects missing scenarios, different demand hashes, stale compile/assessment joins and unverified operating results. The detailed logs stay local.

This is the intended low-usage behaviour: Astra sets the required resilience and accepts a meaningful topology choice, while Python searches geometry, checks every route, tests the service set and explains the actual limits.

## 8. The next engineering gate

The original **plan** mismatch is now resolved for this family, but the UK realism gap is not. Another larger synthetic layout would add less value than replacing or validating the component and interface assumptions that determine whether this geometry remains plausible.

The next specification work should prioritise an authentic-data-driven specialwork/diamond interface and speed-dependent component applicability, together with actual platform-side geometry and vehicle clearance. A useful next experiment must be allowed to reject or re-fit the compact candidate when a real component, platform island or clearance envelope occupies more space.

Spatial approach queues and external continuation checks should follow as an operating-model gate. Those are needed before claiming that recovery completion inside a generous horizon represents a workable passenger service. The project remains a game engineering tool, not a real infrastructure certification system.
