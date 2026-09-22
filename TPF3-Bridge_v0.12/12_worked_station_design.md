# Worked station design — synthetic eight-platform passenger terminus

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

> **Full brief retained.** The v0.2 results below remain a hand-authored resource-template baseline. Version 0.3 adds a fitted crossover and a **single-approach four-road bank** in [15](15_worked_geometry_examples.md); it does not complete or reduce the four-approach eight-platform brief.

**Version:** 0.2.0 · **Date:** 20 September 2026  
**Status:** Worked design specification plus an executed, deliberately detached operating-model experiment. No complete throat geometry has been generated or constructed.

## 1. Design intent

> Design an eight-platform British-style passenger terminus with four approach tracks and two principal service groups. Provide normal independent bank operation where feasible, retain the specified train lengths and empty-stock departures, and investigate recovery when one platform bank is unavailable. Python should compare meaningful arrangements locally and return a small decision record.

This is a fictional site. It is not a scale model of Waterloo, New Street, Clapham or another reference station. The operating ideas are informed by the research library; all site coordinates, traffic, stock lengths, timings and resource-template assumptions below are synthetic.

The production objective is a full engineered station. This release deliberately tests the operational slice before implementing that geometry pipeline. Consequently, an operating result cannot pass the missing geometry gate or become an approved construction plan.

## 2. A proposed site envelope, not a fitted track plan

Use a local engineering coordinate frame in metres. The proposed site is flat, with an illustrative boundary `0 <= x <= 1200`, `-90 <= y <= 90`. Approach travel towards the terminus follows increasing x. Direction permission belongs to each rail port independently of coordinate orientation.

| Element | Proposed value | Assessment status |
|---|---|---|
| Four approach ports | `x=0`, y positions `-18, -6, 6, 18`; roles A-in, A-out, B-in, B-out | Synthetic boundary condition only |
| Platform road centre positions | y = `-42, -30, -18, -6, 6, 18, 30, 42` | Provisional parallel-road reservation |
| P1, P2, P5, P6 boarding intervals | x from 710 to 970: 260 m | Scalar boarding-length checks executed; full interface unassessed |
| P3, P4, P7, P8 boarding intervals | x from 650 to 970: 320 m | Scalar boarding-length checks executed; full interface unassessed |
| Proposed buffer-end line | x = 1000 | Buffer/overrun engineering unassessed |
| Initial throat fitting region | x from 150 to 650 | No complete fitted fan or crossover yet |
| Concourse reservation beyond buffers | x from 1020 to 1180 | Access/clearance/width design unassessed |
| Vertical alignment and cant | Provisional level track and zero cant | No full formation, drainage or electrical design |

The twelve-metre road spacing, margins and buffer/concourse positions are illustrative design variables, **not UK standards**. The generator must later solve boarding edges, islands/side platforms, access routes, structure positions, overrun treatment and envelopes together. A generous rectangle is not proof that those elements fit.

The operational proof does not use these coordinates to calculate its route distances. That missing geometry-to-resource link is the main next implementation task.

## 3. Train and service brief

The base scenario has 24 complete visits: twelve for group A and twelve for group B. A pair is requested every 150 seconds, with B offset by 60 seconds. The first A request defines time zero; these are relative synthetic times, not a real clock timetable.

Each base train is 160 m long. Every platform applies an illustrative 5 m margin at each boarding-interval end. A train fits only when its length plus both margins is no greater than the usable boarding length.

The proof uses serial activities: 60 seconds dwell, 180 seconds turnback/readiness, and 20 seconds dispatch. This explicit serial sum is a modelling choice; it is not a universal British minimum turnaround rule. A more detailed activity graph may later allow particular activities to overlap.

Four of the visits have their outgoing working labelled empty stock. They still occupy route resources. The external yard or line beyond the portal is not modelled, so the result does not prove that the intended external stock destination can be reached.

The base planned departure is 308 seconds after requested entry. This matches the base surrogate incoming claim duration plus the declared readiness sum. Long-train and late-stock scenarios deliberately retain relevant baseline planned times so their timing effects remain visible.

## 4. Required movement matrix

The initial normal bank assignment is P1–P4 for A and P5–P8 for B. Every permitted visit needs both entry and exit routes and a fitting berth.

| Family | Group A normal/recovery eligibility | Group B normal/recovery eligibility | Declared shared resources |
|---|---|---|---|
| `common` | Any fitting open platform | Any fitting open platform | All throat movements share one exclusive region |
| `banked` | A bank only | B bank only | One exclusive throat region per bank |
| `linked` | A bank normally; fitting B-bank alternatives permitted | B bank normally; fitting A-bank alternatives permitted | Own-bank movements use own throat; a cross-bank leg uses both throats and the link |

The common family's universal sharing is a deliberately conservative **template assumption**, not a statement about every common ladder in Britain. The proof does not derive any of these resources from component geometry.

Cross-bank access is evaluated as a complete opportunity. An A arrival into a B-bank berth needs a legal B-bank-to-A outgoing path as well. Adding only the arrival connection does not meet the contract.

## 5. Synthetic timing model and its limits

The route surrogate uses 160 m distance for an own-bank leg, 280 m for a cross-bank leg, an 8 m/s constant traversal speed, 5 seconds setup and 3 seconds release. Claim time includes the train's full length and rounds outward to integer milliseconds:

\[
T=5000+\lceil1000(D+L_{train})/8\rceil+3000.
\]

For a 160 m base train, this gives 48 seconds for an own-bank leg and 63 seconds for a cross-bank leg. These are explicit synthetic values, not inferred turnout speeds, measured platform approach times or a braking calculation.

The whole berth is conservatively reserved from incoming activation until the outgoing train has cleared. The selected model therefore cannot accidentally reuse the platform while a train waits for its departure route. It may reserve the berth earlier or longer than a detailed physical model would; that bias is part of the declared fidelity.

For one isolated base visit at time zero, the proof returns entry 0, berthed 48, departure 308 and outgoing-clear 356 seconds. It checks that tuple directly. When the departure is blocked, the berth remains reserved through the later outgoing clearance.

## 6. Local search and escalation policy

The scheduling proof considers fitting, eligible platforms in stable ID order. For each, it finds an incoming interval, calculates readiness, finds an outgoing interval and verifies the continuous berth interval. It may shift the arrival and repeat locally when an earlier reservation prevents the complete visit.

The selected candidate minimises departure delay, then cross-bank legs, then entry time and platform ID. Earlier choices are not backtracked. The result is deterministic but not globally optimal.

The base fixtures allow 100,000 calendar-search evaluations and a 7,200-second entry-wait bound. These are declared local budgets. They are not estimates of interactive performance or railway tolerances. A budget failure cannot be reported as a physical impossibility proof.

Astra has no role in those iterations. A production version should ask for a decision only when the design needs a changed boundary, operating capability, train profile or other non-authorised compromise. The present runner has no model API calls and no game API calls.

## 7. Executed scenarios

| Scenario | Change from the base fixture | Main question |
|---|---|---|
| `nominal` | None | Can each family schedule the requested complete visits? |
| `bunched` | A/B arrivals requested together; paired planned times adjusted equally | What happens when use of the shared resources is concentrated? |
| `platform_p1_closed` | P1 unavailable for the experiment | Can the same demand use the remaining eligible roads? |
| `bank_a_platforms_closed` | P1–P4 unavailable; A approach/throat still available | Does cross-bank access supply a real recovery opportunity? |
| `long_trains` | Every third pair uses 300 m trains | Are fit and longer tail-clear times propagated? |
| `late_stock_cycle` | V01 enters 180 s late; V13 reuses its stock after an explicit 600 s external cycle | Does readiness propagate without duplication or teleportation? |
| `short_horizon` | Nominal demand, 1,200 s reporting cutoff | Does the report retain unfinished and future work? |

All three families receive the same fixture for each comparison. Demand is not reduced when a family lacks a recovery path. The short-horizon case retains visits beyond the horizon in its declared work; it is an accounting regression, not a capacity estimate.

## 8. Selected actual results

These numbers were produced by the included Python runner. See the complete [21-row table](proof/results/comparison.md), [summary JSON](proof/results/summary.json), individual traces in `proof/results/`, and [test acceptance record](proof/results/test_report.json).

| Scenario | Family | Scheduled / required | Completed by horizon | Unscheduled | Total departure delay, scheduled visits only |
|---|---|---:|---:|---:|---:|
| Nominal | Common | 24 / 24 | 24 | 0 | 7,732 s |
| Nominal | Banked | 24 / 24 | 24 | 0 | 672 s |
| Nominal | Linked | 24 / 24 | 24 | 0 | 672 s |
| A-bank platforms closed | Common | 24 / 24 | 24 | 0 | 15,486 s |
| A-bank platforms closed | Banked | 12 / 24 | 12 | 12 | 336 s |
| A-bank platforms closed | Linked | 24 / 24 | 24 | 0 | 15,486 s |

### 8.1 What the result actually establishes

Within the specified resources and greedy policy, bank separation reduces the nominal conflict cost. The linked family retains that normal resource separation when the cross-access is unused. When A-bank platforms close, the cross-bank connection permits all the visits to be scheduled, but the shared remaining resources impose substantially greater delay.

The banked closure row's low delay is not an advantage: it excludes twelve unscheduled required visits. This is exactly the reporting failure the specification is designed to prevent.

The common and linked closure rows coincide in this fixture because the remaining paths share the constrained B-side resource and use equivalent surrogate travel assumptions. It is not evidence that their physical designs, construction effort or general capabilities are equivalent.

### 8.2 What it does not establish

These results do not measure Waterloo capacity, prove that a particular throat fits, validate a signalling system, or determine the best layout for a real site. They do not include passenger walking/dwell feedback, microscopic acceleration/braking, actual approach queues or game routing.

The observed differences largely follow from the declared resource graphs. The next important experiment is to replace those assumed graphs with resources compiled from fitted component geometry. Until then, do not attach a numerical construction-footprint or UK-compliance verdict to any row.

### 8.3 Finite-horizon evidence

At the 1,200-second cutoff, the common case has completed ten visits and retains fourteen scheduled residuals. The banked and linked cases each complete twelve and retain twelve scheduled residuals. None drops the rest of the work or labels every scheduled visit completed.

Some residual visits have not yet reached their requested entry; the current aggregate residual is therefore not synonymous with “a physical train queue”. A production report should distinguish not-yet-due, waiting outside the boundary, running, berthed and departing states using an explicit physical model.

## 9. Geometry and rule demonstrations alongside the example

The separate analytic shift has a 4.5 m offset and a synthetic 300 m minimum-radius target. The sufficient-length calculation yields approximately **88.285 m**. A 100 m instance passes that conservative bound; a 60 m instance is not certified by it. Failure of that sufficient bound is not itself a proof of a radius violation.

This shift is plain-line mathematics, not a crossover or throat. It does not generate catalogued switches, cant transitions or vehicle envelopes. Its purpose here is to test an engineering representation that can survive mirroring and compression checks.

The two scoped platform-clause demonstrations also run independently. Their source, condition and values are in [rules.json](evidence/rules.json). A passed example does not evaluate this station's complete geometry, and the national-rule platform-interface branch remains unassessed.

## 10. Decision for the next engineering stage

For this synthetic brief, carry the banked and linked concepts into detailed geometry work. If serving every visit during the A-platform-bank closure is mandatory, the current banked resource family does not meet that scenario. The linked family supplies the missing access in the model, but its geometry and cost remain unresolved.

Do not approve construction yet. First obtain or author an explicitly scoped turnout/crossover component catalogue, fit a complete bank fan and cross-access assembly, check clearances and platform interfaces, and compile the resource model from that result. Then rerun exactly these fixtures and explain any change in performance.

The delivered compact packet is a simple report/reference object, not a general automatic Pareto selector. The long-term intent remains that Python performs this whole comparison and asks Astra only about the material design trade-off.

## 11. Version 0.3 continuation: the first generated subassemblies

The geometry-to-resource link is now implemented for two smaller synthetic assemblies. Their actual paths, resources and operation results are documented in [14](14_geometry_components_and_resource_compiler.md) and [15](15_worked_geometry_examples.md).

Do not replace the eight-platform template rows above with the new bank rows: they use different topology, demand, site boundaries and stopping contracts. The original comparisons remain useful regression evidence for platform-group recovery, while the new experiments validate a lower-level compiler.

The next station-level task is to compose explicit arriving and departing corridor ports with bank fans, then implement justified cross-bank recovery connections. The original mandatory movement matrix, train lengths, scenario comparison discipline and authorised footprint remain the acceptance contract.

## Version 0.4 progress against this full brief

The new implementation supplies a four-road bank with separate directional external arrival/departure leads, actual stopping trajectories and synthetic sectional release. It remains one shared distribution fan, not the required complete two-bank/eight-platform station.

The access experiment has new negative-x boundary coordinates and is not claimed to fit this document's original illustrative site rectangle. Full composition must reconcile external ports, site authority, track ordering, passenger space and recovery movements together. [18](18_arrival_departure_and_sectional_occupation.md)

Source-backed numerical checks now coexist with explicitly synthetic geometry. Real UK component dimensions and vehicle envelopes remain promotion gates, not optional cosmetic adjustments. [17](17_uk_numerical_profiles.md)

## Version 0.6 continuation: generated structure, failed original site

The two-bank structure is now generated and tested as described in [23](23_two_bank_station_composition.md) and [24](24_integrated_station_results.md). It retains the original eight road ordinates and the four 260 m/four 320 m boarding-length requirement, and provides four directional external boundaries.

It does **not** complete this original site brief: the generated rail-port span is 1,970 m, three approach ordinates change and absolute station/concourse positions move. A larger test rectangle is evaluated separately. The original 1,200 m footprint is not silently revised, and no construction approval follows from the operating results.

## Version 0.7 — Original plan geometry now fitted by a new family

The original values in this chapter are retained. [26](26_compact_site_and_recovery_design.md) supplies a new generated family with exact four approach positions, eight original road ordinates, the four 260 m/four 320 m intervals, x = 1,000 m terminal markers and the original concourse reservation. The unpadded centreline control hull fits the 1,200 m site.

This supersedes the v0.6 **failure for that older family**, not the historical result itself. It does not certify full vehicle/civil site containment or complete platform design. The new scissors supplies targeted A-to-B1 and B-to-A4 recovery, not general cross-bank access. The original v0.2 resource-template outputs and later source/runtime limits remain documented at their actual fidelity.

Actual v0.7 operating results and complete failure cases are in [27](27_compact_station_results.md). Neither nominal zero departure delay nor completion in the bank-closure fixtures constitutes approval to build the station in TPF3 or on a real railway.


## Version 0.8 continuation — platforms challenge the compact result

The v0.7 compact plan is retained. The new [platform geometry](proof/interface_results/platform_geometry.json) adds four paired-island boarding reservations and eight source-qualified coping positions. The same scissors recovery can fail a declared passenger-interface requirement when B1 is excluded, and recover after an authorised same-size facility move. [30](30_platform_refit_and_component_evidence.md) traces that complete experiment. No original site, track or train dimension was silently relaxed.
