# Compact original-site station and targeted recovery design

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.7.0 · **Date:** 20 September 2026  
**Status:** Generated and tested synthetic station geometry satisfying the original **plan contract**. Not complete UK, civil, vehicle-gauge, signalling or game approval.

## 1. The engineering question

The v0.6 arrangement correctly reported a 1,970 m longitudinal rail-port span and three wrong approach ordinates. It also demonstrated that a single directional connection did not provide both complete recovery cycles. Those historical findings remain in [23](23_two_bank_station_composition.md) and [24](24_integrated_station_results.md); the previous code and results have not been rewritten.

The v0.7 question is narrower than designing an arbitrary large station: can a different arrangement retain the original eight platform roads, original entry positions and original site, while offering useful recovery in **both separate platform-bank closure scenarios**?

The answer from the delivered synthetic models is yes, but with a consequential restriction. The compact links reach **one inner road in the opposite bank**, not every opposite-bank platform. They are also downstream of the fans. Consequently they cannot replace the earlier arrangement's ability to bypass a failed fan.

This is not merely a shorter copy of the old connection. Python changes the topology and the fan's authored parameters, then rechecks the entire geometry, route/resource model and operating scenarios. It does not stretch the imported component, lower the radius target, change the train length or enlarge the site to manufacture a successful result.

## 2. Frozen plan contract

The original brief is in [12](12_worked_station_design.md). This generator deliberately freezes the following values rather than presenting them as search variables.

| Required item | v0.7 retained position or extent |
|---|---|
| Site | x = 0–1,200 m; y = −90–90 m |
| A arrival / departure | (0, −18) m / (0, −6) m |
| B arrival / departure | (0, 6) m / (0, 18) m |
| A platform roads | y = −42, −30, −18, −6 m |
| B platform roads | y = 6, 18, 30, 42 m |
| A1/A2/B1/B2 boarding intervals | x = 710–970 m; 260 m usable |
| A3/A4/B3/B4 boarding intervals | x = 650–970 m; 320 m usable |
| Rear stopping markers | x = 715 m or 655 m, with the existing 5 m project margin |
| Terminal/buffer location markers | x = 1,000 m |
| Throat specialwork region | x = 150–650 m |
| Supplied concourse reservation | x = 1,020–1,180 m; y = −75–75 m |

These are **project brief dimensions**, not national railway standards. The 12 m platform-road interval includes space intended for eventual platform/access design; it is not being substituted for the separate GB running-track-centre reference.

The terminal marker is now physically distinct from the end of the boarding interval. Storage track continues to x = 1,000 m, but this does not increase boarding length to 290 m or 350 m. No energy-absorbing buffer, overrun provision or safe distance to a concourse is inferred from the marker.

The footprint assessment checks actual ports and the complete Bezier **control-hull enclosure**, rather than a small set of sampled centreline points. In the selected model the enclosure is x = 0–1,000 m, y approximately −42–42 m; the concourse reservation is separately contained and has no possible centreline-hull contact.

This is an **unpadded planar contract**. Vehicle envelopes at open external interfaces, full structures, platform islands, access stairs, formation, drainage and three-dimensional clearance remain separate gates. The output therefore records `plan_contract_passed: true` and `full_original_brief_satisfied: false` together, without contradiction.

## 3. Topology: inner-road recovery after the fans

Each service group retains its own arrival/departure merge and its own platform fan. A's fan opens towards negative y; B's opens towards positive y. This preserves a clear central corridor between inner roads A4 and B1.

The normal relationships are:

- A arrival → an A berth → A departure.
- B arrival → a B berth → B departure.

The optional additional **complete cycles** are:

- A arrival → B1 → A departure.
- B arrival → A4 → B departure.

The last two include reversal/readiness at the berth and an explicit return route. An arrival-only connection does not meet the cycle contract. No path is invented between a branch and a normal exit through the same turnout toe.

| Candidate | Normal service routes | Recovery service routes | Total routes | Turnouts | Declared diamonds |
|---|---:|---:|---:|---:|---:|
| `isolated` | 16 | 0 | 16 | 8 | 0 |
| `a_to_b` | 16 | 2 | 18 | 10 | 0 |
| `b_to_a` | 16 | 2 | 18 | 10 | 0 |
| `scissors` | 16 | 4 | 20 | 12 | 1 |

A route count is an inventory, not a capacity measure. The recovery routes share resources with receiving-bank trains and with each other where appropriate. Physical availability also does not override `allow_recovery: false`.

The receiving inner platforms are not equivalent. B1 is a 260 m platform; A4 is 320 m. The longer synthetic train therefore changes the two recovery scenarios differently. That consequence is carried into [27](27_compact_station_results.md), not hidden by a station-wide platform count.

## 4. Fitted component geometry

### 4.1 Fixed imported components

The arrival/departure merges and recovery switches use the existing authored component record through [the importer](21_component_catalogue_import.md). Each instance retains the record hash, normalised geometry hash and rigid placement transform.

That record has a 40 m longitudinal span, 1.5 m branch offset and 0.075 branch exit slope. These are authored centreline quantities, **not a verified UK switch designation or turnout rating**.

Across the 12 m inner-road separation, two opposing components leave a 9 m lateral gap between their branch exits. Joining those exits at the fixed slope gives:

\[
X = 2(40) + \frac{12-2(1.5)}{0.075} = 200\;\mathrm{m}.
\]

This formula derives from the supplied curve ports and tangents. It is not a formula for all British crossovers. The existing record is not scaled or distorted; a component with an incompatible return-geometry definition is rejected by this limited adapter.

The external merges use the same 12 m approach-track separation. Their toe is x = 200 m, with component geometry at x = 160–200 m and a plain-line return farther west. The exact four external positions remain fixed.

### 4.2 The separately parameterised fan

The fan uses the existing authored eased-branch primitive, not the immutable imported recovery component. Its explored variables are the first toe position, the longitudinal turnout span and the step between successive toes. Its branch slope remains the explicit project value 0.15.

The selected fit has:

| Variable / result | Value |
|---|---:|
| First fan toe | 205 m |
| Fan turnout longitudinal span | 70 m |
| Toe step | 75 m |
| Minimum project plain-line gap | 5 m |
| Last fan normal exit | 425 m |
| Recovery west / east toes | 430 m / 630 m |
| Declared diamond location | (530 m, 0 m) |
| Last recovery point to long-platform boarding start | 20 m |
| Last recovery point to rear stopping marker | 25 m |
| Conservative whole-candidate radius lower bound | Approximately 312.619 m |

The existing **300 m project minimum-radius target** is retained. The compiler's conservative curvature bound checks every edge before the candidate reaches operations. A tighter 400 m test profile rejects this family instance instead of silently reducing that target.

A 5 m programming/design gap is not an imported maintenance or hardware rule. Likewise, the radius bound does not certify the 15 mph operating target. Real switch blades, crossing noses, check rails, flangeways, bearers and allowable component interaction still require authentic catalogue data.

## 5. Explicit diamond admission

The old compiler rejects unexplained centreline intersections. The new compiler preserves that behaviour except for a **strictly declared pair of straight interior crossing paths**.

A diamond record names two existing edge IDs, the expected intersection position, an authored origin and an unresolved hardware status. Validation checks that the edges are distinct, non-component straight lines, non-parallel, and intersect strictly inside both segments at the declared location. They must not share a port. Duplicate records, missing edges, false hardware approval and unsupported slip types are rejected.

The compiler then adds `diamond:INNER_DIAMOND` as an **exclusive resource** to both paths. It does not join their topology, create turning movements, delete track locks or remove existing proximity exclusions. A standalone regression fixture verifies that a train entering one diamond route cannot leave by the other route's endpoint.

In the scissors arrangement, the ordinary through routes do not traverse the diamond and do not reserve its named crossing resource. Both recovery cycles do. The existing point-body and point-state constraints remain present, so compatibility is not reduced to a single crossing flag.

This model does not specify the hardware of a real fixed diamond. Its occupation footprint conservatively covers the implicated complete connector edges. A future component/resource definition may locate a smaller conflict zone, but only with explicit geometry and operating assumptions.

The `railcompact.compiler` module is a documented fork of the frozen v0.3 compiler. Its exception handling and added resource are separate from the prior code so the historical no-diamond tests remain valid. A production refactor should extract a tested component-admission interface rather than maintain multiple increasingly divergent compilers indefinitely.

## 6. Bounded local search

The executed grid contains 27 combinations:

| Axis | Values |
|---|---|
| First fan toe x | 205, 215, 225 m |
| Fan component span | 65, 70, 75 m |
| Fan toe step | 70, 75, 80 m |

All candidates use the same site, original platform geometry, fixed imported component, 300 m radius target and recovery family. Six candidates pass the scoped geometric gates. Rejections identify insufficient inter-component space, failure to clear a stopping marker, or failure of the conservative curvature certificate.

Among passing candidates, the current policy minimises the final specialwork x position, then uses deterministic parameter tie-breaking. It does **not** claim to minimise complete construction cost, passenger delay or all possible footprint designs. The selected geometry is then used consistently for the four family/scenario comparisons.

Three outcomes stay distinct:

| Outcome | Meaning |
|---|---|
| `grid_complete_candidates_found` | Every configured combination was examined and at least one passed |
| `grid_complete_no_candidate` | No configured combination passed; other parameters/topologies remain untested |
| `search_exhausted` | The computational budget ended before the configured grid was complete |

An additional experiment limits final specialwork to x = 600 m. It finds no candidate in this grid. That is not a proof that a different fan, component or topology cannot fit. Zero- and restricted-budget examples are also exported.

The source curves, profile, selected parameters and actual results are retained in [geometry_search.json](proof/compact_results/geometry_search.json). Astra does not participate in individual fitting attempts.

## 7. Fair operating comparison

An optional crossover creates geometric vertices that could inadvertently become extra release sections. The isolated and one-link candidates therefore retain equivalent plain-line section slots at all four recovery-switch positions. Normal route lengths and the corresponding synthetic section breaks match the scissors candidate.

The four candidates consequently have identical normal scheduled timings in the supplied fixture. Adding unused recovery pointwork does not receive an artificial nominal benefit from extra tessellation.

These are authored **study sections**, not inferred British track circuits or signalling release boundaries. Route activation, tail-clear release, conservative berth holding and stock dependencies remain those of the retained operating model.

All 64 cross-bank normal arrival/departure route pairs are independent in each compiled resource model. That is not proof of complete dynamic gauging or an approved interlocking. The read-only body audit and source-qualified UK checks remain separately attached to each candidate.

## 8. Meaning for the production specification

The useful reusable pattern is not simply “put a scissors near the platforms”. It is:

> Generate a bounded recovery connection for the required complete movements; identify which berths and failures it covers; fit it under immutable site/platform constraints; derive conflicts; then test the specified disruptions and vehicle classes.

This increment supplies a practical example of a smaller topology satisfying a narrower recovery contract. It also provides counterexamples: fan failure, loss of the receiving inner berth, recovery disabled by policy, and a train too long for that berth.

The remaining acceptance boundary is explicit. Original plan positions and selected synthetic operations pass; authentic UK pointwork, full platform design, realistic speed applicability, dynamic/3D gauging, physical approach queues and TPF3 construction do not follow from that result.
