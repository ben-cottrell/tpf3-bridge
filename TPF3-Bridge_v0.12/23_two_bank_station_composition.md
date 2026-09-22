# Two-bank passenger-station composition

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.6.0 · **Date:** 20 September 2026  
**Status:** Executed four-approach/eight-platform reference-informed study with authored track components. The composed family does **not** fit the original site brief. No construction is authorised.

## 1. Purpose and implemented boundary

This increment joins the earlier engineering layers into one candidate. A station now has eight physical platform roads, four directional external boundaries, explicit service-group eligibility, complete arrival–berth–departure opportunities, fitted component geometry, one combined resource compilation, vehicle assessments and scenario results referring to the same compile identity.

It is not sufficient to build two banks, schedule them independently and concatenate the timetables. A connection, common controller, clearance exclusion or passenger reservation can invalidate that composition. `railstation` instead constructs a single physical network and re-runs the geometry/resource compiler across **every pair of physical edges**, including pairs originating in different banks. It then schedules all required trains against one calendar.

The frozen v0.2–v0.5 modules remain intact. The new package composes their contracts rather than changing historical experiments until they pass. See [execution evidence](25_v06_execution_report.md) for regression scope.

## 2. Candidate families and their contracts

Three fitted instances share the same approach positions, platform positions, train profile, study boundary and demand:

| Family | Normal working | Additional complete recovery cycle |
|---|---|---|
| `isolated` | A services use A1–A4; B services use B1–B4 | None |
| `a_to_b` | The same bank-specific normal working | A arrival enters a B-bank berth; the reversed train returns through the link to A departure |
| `b_to_a` | The same bank-specific normal working | B arrival enters an A-bank berth; the reversed train returns through the link to B departure |

A single crossover has a direction-dependent topology. Allowing trains to traverse it in either travel direction does **not** mean either inbound corridor can reach either platform bank. `a_to_b` supplies an A-in → B-platform → A-out cycle. It does not supply B-in → A-platform → B-out. The enumerated legal routes establish this distinction; the names are not used to invent connections.

The isolated instance has 16 directed service routes. Each linked instance has 24. A route is an explicit ordered traversal of admitted component ports; two geometric lines crossing or meeting on a plan do not create a new movement.

This is a restricted family comparison, not exhaustive station design. In particular, a second crossover, earlier track sorting, different fan arrangements or grade separation could change the recovery capability and footprint. None is assumed to exist in these instances.

## 3. Geometry and original-brief traceability

The bank construction retains the original eight road ordinates and the original division between shorter and longer boarding intervals. It does not retain the original absolute longitudinal positions or three of the exact approach ordinates.

| Feature | Original illustrative brief | Composed family |
|---|---|---|
| Platform road y positions | −42, −30, −18, −6, 6, 18, 30, 42 m | Retained |
| A1/A2/B1/B2 boarding lengths | 260 m | Retained |
| A3/A4/B3/B4 boarding lengths | 320 m | Retained |
| Short boarding x intervals | 710–970 m | 1,710–1,970 m |
| Long boarding x intervals | 650–970 m | 1,650–1,970 m |
| A arrival boundary | (0, −18) m | (0, −42) m |
| A departure boundary | (0, −6) m | (0, −54) m |
| B arrival boundary | (0, 6) m | Retained |
| B departure boundary | (0, 18) m | (0, −6) m |
| Site x interval | 0–1,200 m | Actual track endpoints span 0–1,970 m |
| Concourse reservation | x = 1,020–1,180 m | Separate proposed reservation at x = 2,020–2,180 m |

These are project geometry choices, **not British dimensional standards**. The numerical lengths are traceable to the original synthetic brief in [12](12_worked_station_design.md). The source-backed numerical layer is distinct, as specified in [17](17_uk_numerical_profiles.md).

Shortening a boarding interval changes the physical stopping marker and storage edge as well as its scalar length. A1/A2/B1/B2 have rear markers at x = 1,715 m; the longer roads have rear markers at x = 1,655 m. Each uses the explicit five-metre project stopping margin. No label change creates additional platform capacity.

The existing terminal-limit representation is not a completed buffer-stop or overrun design. The reservation beyond the tracks is not a complete concourse, accessible path or station building. Those interfaces remain unassessed.

### 3.1 Footprint assessment, not silent enlargement

`site_check()` records three separate questions:

1. Are actual rail ports inside the requested rectangle?
2. Does the complete Bezier control-hull enclosure, with an explicitly selected padding, fit?
3. Do exact approach requirements and supplied reserved volumes remain satisfied?

An actual port outside the boundary establishes a failure for that geometry. A hull extending outside without an actual-point witness is only a failure to certify containment by that bound. These statuses are deliberately different.

The default family has actual ports 1,970 m apart longitudinally. Consequently no **translation of this fixed, fixed-orientation candidate** can fit a 1,200 m longitudinal window. This is a narrow geometric certificate; it does not prove that another topology, another fit or a rotated/reconfigured station cannot fit.

A larger **test** rectangle, x = −5 to 2,200 m and y = −90 to 90 m, contains the declared 1.75 m centreline padding and the separate concourse reservation. Passing that check is not authorisation to enlarge the original site. The decision packet keeps the original failure, proposed alternative and unresolved interfaces separate. See the [candidate assessment](proof/station_results/a_to_b__assessment.json).

## 4. Component composition and import

Each bank reuses its authored fan and two-lead access geometry. Every port, edge, turnout and controller receives a bank namespace. `A:ACCESS` and `B:ACCESS` remain different physical components; labels cannot merge their control identity.

The recovery pair is instantiated from the supplied v0.5 synthetic component record through the actual importer and placement functions. Its local geometry is not recreated from an informal turnout name. Two rigid placements preserve the source geometry; the second is rotated, and the B-to-A variant uses the supported reflection. The records retain the exact import hash, normalised geometry hash and instance transforms.

For the particular authored record, the branch has a 40 m longitudinal span, 1.5 m exit offset and 0.075 exit slope. Joining two such components across the 48 m trunk separation gives a 680 m toe-to-toe span:

`2 × 40 + (48 − 2 × 1.5) / 0.075 = 680 m`.

This is a derivation from the **synthetic imported geometry**, not a UK crossing-ratio or turnout-speed rule. The long direct cross-bank link is one reason the family does not meet the initial footprint. Changing the approach sorting or the component family should be investigated rather than distorting a reviewed component to make the arithmetic convenient.

No authentic UK turnout has been imported. Existing bank components remain authored generators; the two recovery instances use authored imported data. Both origins stay visible in the whole-candidate component report. The external acquisition target remains quarantined as described in [21](21_component_catalogue_import.md).

## 5. Recompiling the combined railway

The isolated station has 68 physical edges and eight turnouts. Each linked station has 71 edges and ten turnouts. Additional plain-line subdivisions are intentional study-section boundaries, not additional switches.

Compilation validates legal continuations, endpoints, tangents and curvature conditions; checks the declared synthetic radius bound; rejects unmodelled centreline intersections; derives track, component-body, controller-state and proximity resources; and creates route-length brackets from the fitted curves. Storage roads retain their own occupation and neighbouring exclusion resources.

Normal bank-to-bank independence is tested for all 8 × 8 = **64 pairs of normal arrival/departure routes**. Those pairs have no incompatible shared resource in each compiled instance. This establishes independence in the selected resource model, not a real interlocking approval or complete dynamic-gauge finding.

A recovery route does acquire resources of the affected receiving bank and crossover. Its later operating cost follows from the actual compiled movement, rather than a hand-written instruction that a recovery move should be slow or expensive.

### 5.1 Matched section boundaries

A subtle comparison hazard is that adding a crossover also adds graph vertices. If every edge becomes a release section, the linked candidate could gain earlier release solely because its geometry was split into more pieces.

The comparison therefore partitions the common corridor at x = **280, 320, 920 and 960 m** in every family, including the isolated case. The locations are derived from the same component geometry. The resulting normal path lengths and nominal scheduled timings match in the executed comparison.

These are explicit synthetic section boundaries. They are not newly inferred track circuits, overlaps or signal positions. A production operating profile must supply actual or deliberately designed section/protection logic independently of CAD tessellation.

## 6. Complete movement and closure evaluation

The scheduler accepts inbound and outbound group separately. It requires a fitting berth and both corresponding routes. It checks closures against all incoming/outgoing physical edges and the storage edge, then reserves the complete visit against one station-wide calendar.

A platform-bank closure, a fan closure and an arrival-lead closure are different failures. A link located before the A fan can bypass a closed A fan when using B platforms. It cannot bypass an unavailable A arrival lead that every A train must traverse before reaching the link.

Recovery also requires permission. `allow_recovery: false` rejects otherwise reachable cross-bank assignments. Extra physical connectivity is not authority to change the user's operating policy.

The reused motion model accounts for train length, acceleration, braking, stopping and tail-clear release. Storage remains held from arrival activation until the outgoing movement clears, including departure waiting. Linked stock workings retain predecessor and external-cycle requirements. The scheduler is greedy and does not claim global optimality, live dispatch behaviour or spatial queue capacity.

## 7. Integrated evidence and independent verification

Every result carries the compiled geometry hash, candidate-assessment hash, vehicle-record hash, scenario hash and explicit construction status. A result from another fit cannot be attached to the current clearance assessment merely because both have eight platforms.

`check_result()` independently inspects the output. Its interval-sweep implementation does not call the scheduling calendar's conflict checker. It verifies conservation of required demand; valid arrival/departure routes; closure and recovery permissions; fit, stock, readiness and horizon accounting; held storage; correct control-state acquisition; and incompatible reservation overlap. End events precede starts at equal timestamps to preserve half-open interval semantics.

This verification checks implementation consistency. It does not independently validate the underlying train physics, actual signalling or vehicle data. The existing lower-level tests and explicit evidence gaps remain necessary.

## 8. Acceptance boundary

Accepted for offline development: physical two-bank composition, directional recovery topology, one geometry-derived resource model, complete multi-group visits, combined evidence and bounded decision packets.

Not accepted: the original 1,200 m site, all requested exact approach positions, bidirectional cross-bank recovery in one candidate, authentic pointwork, a complete platform/vehicle interface, real signalling, passenger circulation or TPF3 construction. The next useful design search should target the failed site and recovery requirements without relaxing them invisibly.
