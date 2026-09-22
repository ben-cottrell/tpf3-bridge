# Birmingham New Street, Proof House and Grand Junction

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

Version **0.2.0** · reference records **R01–R02** · Status: **operationally informed specification, not an as-built replica**

## 1. Evidence baseline

Network Rail's June 2025 representation to ORR evaluates a developing timetable and applications. It explains that lower platform occupation does not necessarily provide usable capacity because access can conflict with adjacent movements. The assessment also discusses New Street throat and Proof House constraints, crossing movements at Grand Junction, and the interaction between Stour and Derby line routing. These are findings about that assessment, not measured September 2026 performance. [S002, PDF pp. 7–9](10_source_register.md#s002)

The October 2025 passenger map shows numbered platforms 1–12 with A/B labels, plus 4C. It does not establish complete route permissions, lengths, release conditions or exact throat geometry. [S003](10_source_register.md#s003)

These two sources support different things. The first motivates an operating model; the second supports passenger-label and circulation interpretation. Neither is a substitute for the missing detailed track and signalling record.

## 2. Proposed engineering abstraction

Model the reference as a **two-ended passenger station coupled to consequential approach junctions**, rather than a rectangle with a twelve-way fan at each end. The initial abstract fixture may reproduce the engineering problem without claiming to reproduce every actual connection.

The model needs four nested boundaries:

1. Physical platform roads, usable stopping intervals and passenger edges.
2. Both throat resource groups, including the last fouling points beyond the platforms.
3. Approach interfaces carrying the competing service groups.
4. Consequential junctions and holding sections where a changed station route can move a conflict or queue.

The boundary must expand when a candidate's queue reaches its edge. An optimiser must not improve an internal delay score by pushing waiting trains outside the simulated area. Compare common entry-to-exit journeys, and account for trains still waiting at the horizon.

## 3. Platform sections are not independent slots

A/B labels should resolve to physical intervals and permitted stopping configurations. They must not generate two independent whole-length platforms automatically.

For each platform road, represent:

- Physical track extent and boarding-edge extent.
- Labels and their valid dates.
- Permitted berth configurations for the selected train classes.
- Arrival and departure ends, with route eligibility separately recorded.
- Shared track/resource occupancy, release dependencies and protective conditions.
- Passenger access zones and any consequences of a short train stopping at one end.

A full-length train can invalidate both short-berth configurations. Two short trains may only be admitted together where the selected signalling/operating model explicitly permits it. The existence of two passenger labels is not that permission.

A separate named berth such as 4C should retain its own identity and evidence status. Do not infer its exact length or all its connections from the passenger map.

### Synthetic interval example

This example tests the model; the dimensions and permissions are **not Birmingham data**.

```yaml
platform_road_id: synthetic_road_01
track_interval_m: [0.0, 420.0]
platform_edge_interval_m: [10.0, 410.0]
labels:
  - {label: "1A", nominal_interval_m: [10.0, 200.0]}
  - {label: "1B", nominal_interval_m: [220.0, 410.0]}
berth_configurations:
  - id: one_long_train
    usable_interval_m: [10.0, 410.0]
    maximum_trains: 1
  - id: two_short_trains
    requires: [verified_split_berth_permission, verified_protection_model]
    enabled: false
```

The central interval is deliberately not treated as a sufficient safety margin: permissions, separation and release rules still require explicit evidence.

## 4. Arrival, dwell and departure must be one design object

A platform assignment is feasible only if it has compatible access, train fit, required dwell/turnround, and a feasible subsequent movement. For a through service, the departure route is part of the candidate. For a terminating service, the linked departure or empty-stock path must be represented.

Let a candidate assignment be:

\[
a=(r_{in},b,t_{arr},t_{ready},r_{out},t_{dep})
\]

where the route objects contain resource requirements, not just lists of graph edges. The solver must not accept a free berth and defer discovery of an impossible exit until execution.

A useful local heuristic is to rank *complete movement opportunities*. Score candidates by required-route availability, passenger transfer cost, conflict exposure, stock readiness and recovery margin. A berth with slightly higher average occupation may offer a better complete opportunity than a less-used berth with awkward access.

## 5. Throat conflict model

Use a directed rail graph to enumerate possible paths, then a separate legal-route model to reject impossible turns and unapproved point combinations. Each route reserves temporal resources for running lines, point positions, crossing zones and any protective areas represented by the selected profile.

A geometrically non-overlapping pair can still conflict through protection or point requirements. A pair sharing a long corridor at different times can be compatible. Therefore a static conflict matrix is a useful explanation view, but not the whole simulator.

### Synthetic conflict fixture

The table below is a deliberately invented teaching fixture, not a Birmingham route table.

| Movement | Arrival A | Departure B | Through C | Empty-stock D |
|---|---:|---:|---:|---:|
| Arrival A | — | Conflicts | Independent if protection allows | Conflicts |
| Departure B | Conflicts | — | Independent if protection allows | Independent |
| Through C | Conditional | Conditional | — | Conflicts |
| Empty-stock D | Conflicts | Independent | Conflicts | — |

The implementation must supply a resource witness for each conflict. “These lines look as though they cross” is not sufficient. Equally, a missing control table means independence is unknown rather than verified.

For each resource, release when the selected release conditions hold. Train-front position alone must not free a crossing still occupied by the tail. A staged release profile must identify which resource can release before the complete route is clear.

## 6. The Proof House/Grand Junction lesson

The proposed design domain must carry station decisions into the adjoining corridor. A route that is convenient within the station can occupy a competing approach movement or require another crossing farther out.

Build three cooperating layers:

**Macro layer:** service groups, station-end choices, route families and approach track order.

**Meso layer:** platform groups, throat sectors, junction crossing/merge resources and holding locations.

**Micro layer:** component geometry, exact resource lengths, train kinematics and time-dependent occupation.

The macro solver should not generate every platform-by-route combination indiscriminately. Prune combinations with incompatible service direction, train fit, electrification, required interchange or known path restrictions. Retain alternatives that offer genuinely different conflict patterns.

The geographic relationship, track naming and actual point/route identifiers must be imported from dated technical evidence before creating an exact Proof House prefab. This document deliberately does not invent that missing route map.

## 7. Candidate strategies to compare locally

These are proposed alternatives for a New Street-inspired fixture, not claims about a real approved scheme.

**Service-group zoning:** prefer stable platform groups for compatible flows; quantify the reduction in crossing movements and the loss of disruption flexibility.

**Independent through paths:** retain selected through movements without forcing them across terminating services. Check the whole arrival-to-departure route, not just the platform approach.

**Turnback containment:** move or assign terminating services so their reversal and departure interfere with fewer dominant flows. Include cab-change/readiness and stock dependencies, using profile values rather than invented universal minima.

**Bounded cross-access:** add only connections with a demonstrated operational benefit. Reject a complex ladder that increases slow traversals or conflicts without improving the required service scenarios.

**Approach holding:** test whether a waiting train can be held clear of the important junction and still reach its platform on time. A holding section needs sufficient usable train length and suitable modelled protection.

**Selective grade separation:** test only when the named crossing conflict remains a binding constraint after simpler options. Include gradients, vertical transitions, structure envelope, approach footprint and the next merge.

## 8. Scenario set

The first synthetic test set should cover:

| Scenario | What it tests | Required outcome type |
|---|---|---|
| Regular mixed passenger pattern | Through versus terminating interaction | Feasible schedule or explicit conflict witnesses |
| Long train substituted for short train | Sectioned-berth invalidation | No overlapping allocation |
| Delayed arrival with linked departure | Delay propagation through stock cycle | Readiness respected; no instant stock teleportation |
| One throat sector unavailable | Recovery platforming and rerouting | Bounded reassignment, with passenger impact |
| Two arrivals bunched at an approach junction | Queue location and spillback | Account for queues beyond station limits |
| Unplanned empty-stock move | Non-passenger movement interference | Include resources even without passenger demand |
| Late platform change | Passenger redirection and dwell feedback | Added transfer/boarding consequence or unassessed flag |
| Unsupported specialwork in game | Adapter capability | Explicit alternative or not-representable result |

Demand rates and disturbance magnitudes belong to named synthetic fixtures until a lawful, dated operating dataset is acquired. Do not call the result an estimate of actual New Street capacity.

## 9. Compact explanation to Astra

The decision packet should identify the bottleneck by function and resource, not return thousands of events. For example:

> Candidate A satisfies the through-service requirement but not the delayed-turnback scenario. The conflict is between the terminating service's departure and the following approach movement. Candidate B changes the platform grouping and resolves that fixture without new grade separation. Candidate C also resolves it but requires a longer corridor and more specialwork. The route permissions remain synthetic pending technical-source import.

No numbers in this example are actual simulation results. The future packet should include tested scenario IDs, a trace pointer and a clear model-validity statement.

## 10. Evidence required for an exact reference instance

Acquire a dated track diagram covering both station ends, Proof House and Grand Junction; an applicable platform/berth inventory; permitted routes and protection/release data where accessible; route/track speeds and usable holding lengths; and a matching service/stock scenario. NESA and regional Timetable Planning Rules are acquisition routes, not already-extracted site data. [S048](10_source_register.md#s048), [S049](10_source_register.md#s049)

Use authorised technical material only. A signalling control table may not be publicly available; in that case retain an explicitly simplified shadow model and do not claim to reproduce the interlocking.

## 11. Implementation gate

The Birmingham-inspired benchmark is complete when it demonstrates all of the following: an empty platform can be correctly rejected for access reasons; section labels cannot create false parallel capacity; tail clearance governs release; an approach queue is not hidden by the simulation boundary; and a material redesign can be explained in one decision packet with a reproducible detailed trace.

That gate proves model behaviour, not real-world station capacity or a faithful Birmingham reconstruction.

## 12. Version 0.2 technical dossier: what the assessment can establish

### 12.1 Scope of the evidence

S002's investigation uses a developing December 2025 timetable with additional requested services and a selected weekday assessment window. It is not measured September 2026 operation. The platform-occupation table and access discussion concern different constraints. Its separate six-minute proximity analysis deliberately omits platform/line distinctions; that screening measure cannot supply a route-conflict matrix. [S002, PDF pp. 6–9](10_source_register.md#s002)

The bridge should therefore import three separate evidence objects: an occupation observation/estimate for a stated interval; a documented qualitative access constraint; and a coarse screening method with explicit omissions. None should be converted directly into a universal maximum utilisation percentage.

### 12.2 A reconstruction-ready data envelope

The following records define the missing information precisely. The absence of values is a research task, not an invitation for the generator to invent them.

| Record | Required content | Present status |
|---|---|---|
| `StationEndInterface` | Stable end identity, approach-port names/order/directions, valid infrastructure date | Abstract end identities possible; complete technical inventory pending |
| `PhysicalPlatformRoad` | Track extent, boarding edges and chainage reference | Labels known from S003; metric inventory unresolved |
| `BerthPermission` | Permitted full/split configurations and access/release restrictions | No simultaneous-use permission imported |
| `JunctionMovement` | Entry/exit ports, direction, legal traversal and route variants | Qualitative interactions known; complete movements pending |
| `ProtectionResource` | Physical occupation versus control/protection state, release conditions | Simplified shadow model only |
| `ApproachHoldingPosition` | Usable length and how a waiting train affects adjacent movements | No measured holding inventory imported |
| `OperatingScenario` | Versioned requests, stock chains, timing origin and disturbance definitions | Synthetic scenarios available; actual matched local timetable not imported |

Stable symbolic region boundaries may be created now, but their names must not imply precise signal locations. The station's two ends and consequential approach junctions remain one composed design problem.

### 12.3 From constraint evidence to a testable question

For each design alternative, ask whether every requested visit has at least one **complete opportunity**. An opportunity includes the incoming route, usable berth, passenger/turnround activities, outgoing route and any linked next stock working. Candidate generation should prune an impossible outgoing route before spending time fitting the arrival curve.

Once an opportunity exists, calculate its resource occupation. A scalar platform-occupation percentage is only a summary; it cannot tell the solver whether the next usable arrival and departure windows line up. The proof's blocked-departure test retains berth occupation until the delayed departure clears. That is a useful behaviour for this dossier, but it is not a simulated New Street timetable.

### 12.4 Proposed Birmingham-specific fixture, still not implemented

The next integrated fixture should contain two station-end regions, two passenger flow groups using different approach alternatives, one terminating service, a longitudinally sectioned platform road, and one consequential crossing resource outside the immediate throat. Every number and connection would remain synthetic until the evidence gate is met.

Its first experiment should compare three ways to reduce a conflict: platform-group reassignment, a changed approach route, and an additional independent connection. Use the same end-to-end reporting boundary and demand. Record which resource stopped constraining the timetable and whether another became limiting.

The acceptance test must deliberately send a queue to the model boundary. A current proof can report waiting before its abstract entry portal; it cannot place that queue along actual approach tracks. The future fixture must add physical holding sections before it claims to assess the Proof House/Grand Junction propagation problem.

### 12.5 Research priority after this release

The most valuable new document would be a dated technical plan that identifies **both station ends and their connected approach routes in the same infrastructure state**. After that, resolve road/edge/berth lengths and section permissions. A further passenger map would be lower value for these tasks.

Until then, Birmingham remains an operationally informative reference and source of difficult test cases, not the geometrical basis of the worked eight-platform terminus in [12](12_worked_station_design.md).
