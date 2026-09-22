# Regional passenger hubs and comparative lessons

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

Version **0.2.0** · 20 September 2026 · Reference records **R14–R21**

These cases broaden the model beyond London termini. The observations are sourced; the proposed experiments are original bridge requirements and remain synthetic until a dated technical dataset is imported.

## 1. Leeds: platform zero, mixed roles and asymmetric access

The live station page reports eighteen platforms and lists platform 0, while the reviewed July 2025 map omits 0. Project sources also use different January/May 2021 completion milestones. Store these observations separately instead of silently harmonising dates or treating the map as a complete inventory. [S024](10_source_register.md#s024)–[S027](10_source_register.md#s027)

### Proposed model

Use a station with mixed through and terminating roles, nonuniform platform lengths and asymmetric approach connections. Do not assume the two ends are mirrored. Make a service's preferred exit side and next working part of platform allocation.

Introduce a new platform by adding a physical asset and aliases, not by shifting every existing integer identifier. Historical snapshots must remain valid after a renumbering or addition.

### Test programme

Compare a terminating service assigned to a through road against an appropriate bay/terminal role. Evaluate whether the change reduces through conflicts, then check its impact on approach crossings, passenger access and rolling-stock readiness. Test the importer against a missing label in one map: it should flag evidence completeness, not delete a known platform.

Exact bay-to-line and through-platform route eligibility must be obtained from a dated technical plan. The map's drawn fan cannot supply measured geometry or a full conflict matrix.

## 2. Edinburgh Waverley: longitudinal platform identity

The October 2025 map contains numbered labels 1–20 and east/west subdivisions. It is a particularly useful warning against equating numbered labels with independent parallel roads. [S028](10_source_register.md#s028)

### Proposed model

Represent long platform roads as intervals, with labelled boarding positions and permitted berth configurations. Different trains can use different parts of the same physical edge at different times. Any simultaneous occupation needs explicit operating and protection rules.

The train's arrival end, departure end and reversing requirement matter. A short train occupying the convenient end of a long road can prevent another train reaching an otherwise empty interval. That is a route-access constraint, not a simple length-summing problem.

### Test programme

Use an opposed-end synthetic station with two short-train berth options and one long-train option. Demonstrate that total free metres do not imply a reachable berth, and that a long train can invalidate both short options. Add an approach closure and check whether the remaining end actually reaches the intended berth.

The physical pairing of real labels, exact crossover locations and authorised simultaneous occupation remain evidence tasks. This package does not assert that every apparent section on the passenger map is independently signalled.

## 3. Glasgow Central: seventeen at complex level, fifteen in the terminal

Network Rail explicitly separates high-level platforms 1–15 from low-level platforms 16–17. The high-level map shows access towards the low-level system rather than a common seventeen-road throat. [S029](10_source_register.md#s029), [S030](10_source_register.md#s030)

### Proposed model

Use one passenger station complex containing a terminal rail subsystem and a separate through subsystem. Assign each rail layer its own connectivity, route eligibility, resources and train classes. Connect the layers through a pedestrian graph where the access model permits.

A shared display name must not permit a high-level service to select a low-level berth automatically. The same rule applies when several game stations are grouped into one interchange for planning purposes.

### Test programme

Delay a high-level departure and increase transfer demand towards the through system. Evaluate passengers and trains separately. Test a broken vertical link: the trains may continue while a particular accessible passenger transfer becomes unavailable. Do not invent a rail connection to solve a pedestrian problem.

## 4. Reading: the station is part of a corridor-scale civil scheme

Network Rail Consulting's project record includes platform additions, eastern/western grade-separation work, depot/chord changes and a passenger transfer deck within the redevelopment scope. [S031](10_source_register.md#s031)

### Proposed model

Reading should inspire an integrated station-area generator rather than a standalone platform prefab. The object should own platform groups, approach track order, crossing/merging movements, grade-separation envelopes, stock access and pedestrian circulation.

Candidate evaluation must include the sequence in which a train encounters these resources. A grade-separated crossing can still feed a constrained merge, and a depot movement can still consume useful passenger paths. Conversely, a modest change in track order may remove a conflict without requiring every route to be grade-separated.

### Test programme

Keep the same synthetic demand and compare station-only enlargement, corridor sorting, selective grade separation and integrated stock access. Measure completed journeys, residual queues, conflicting resource occupation and passenger transfer performance. The project record's benefits must not be copied into the simulator as a universal capacity multiplier.

This case should eventually anchor the civil/operating integration benchmark, after suitable measured and route-specific evidence is acquired.

## 5. Manchester Piccadilly: terminal capacity is not through-corridor capacity

The station information reports fourteen platforms. The map distinguishes the main terminal bank from access to platforms 13/14. The source is sufficient for the passenger-layout distinction, but not all approach connections. [S032](10_source_register.md#s032), [S033](10_source_register.md#s033)

### Proposed model

Represent a terminal subsystem and a constrained through-corridor interface with explicitly different route eligibility. The solver must reject an alternative terminal berth for a through service when no compatible complete route exists. Spare track somewhere in a station complex is not automatically useful capacity for every flow.

Passenger paths to a remote platform group should be evaluated using their actual graph distance and vertical movements in the model. A last-minute change between groups can have a substantial modelled consequence even when both train routes are feasible.

### Test programme

Load the through corridor while leaving some terminal berths unused. Verify the optimiser does not “solve” the corridor problem by teleporting through trains into incompatible terminal roads. Then introduce a genuine synthetic connection and assess the new arrival/departure conflicts it creates.

## 6. Oxford Road/Castlefield: assess holding positions and spillback

Network Rail's remodelling page describes proposals addressing the corridor between Deansgate and Piccadilly, including approach signalling intended to allow trains to wait outside Oxford Road rather than occupy the upstream station. Those are proposals and intended benefits, not measured completed outcomes. [S034](10_source_register.md#s034)

### Proposed model

A holding position is an engineered operating resource. It needs a usable train-length interval, compatible stopping conditions, a release rule and a downstream route. A signal graphic alone does not establish useful holding capacity.

A train queue may block a previous platform or junction before the next station becomes visibly full. The model therefore needs network spillback and a boundary-expansion trigger.

### Test programme

Run a bunched-arrival scenario with and without a valid intermediate holding resource. Measure upstream platform occupation and total delay, not just the downstream station's apparent flow. Introduce an overlength train: it must not be considered clear merely because its front has passed the holding marker.

## 7. Bristol Temple Meads/East Junction: sectioning and civil interfaces

The generic station page says sixteen platforms, while the reviewed map shows thirteen distinct labels: 1, 3–13 and 15. The sources are not reconciled, so this release does not present Bristol as an unqualified sixteen-platform station. The regeneration timeline also links subway works to the 2021 East Junction upgrade. [S035](10_source_register.md#s035)–[S037](10_source_register.md#s037)

### Proposed model

Use curved/staggered platform geometry, longitudinal label relationships and a passenger subway reserved before track/civil placement. Do not infer that each label requires a distinct full-length road, or use a schematic line as a measured track centreline.

Make passenger structures part of the civil collision/clearance model. A bridge support, subway envelope, retaining wall or access shaft can prevent an otherwise mathematically valid track arrangement.

### Test programme

Import conflicting inventory claims and require explicit resolution. Then test a synthetic sectioned station where the shortest throat arrangement collides with the reserved passenger structure. The solver should reconfigure geometry or return a material trade-off; it must not delete the pedestrian connection silently.

## 8. Liverpool Lime Street: reject uncertain inventory before construction

The station page reports ten platforms; the July 2025 map image additionally shows a label 00 alongside 01–10. The map is therefore not sufficient evidence of a commissioned extra platform. Both sources also identify the separate Merseyrail passenger connection. [S038](10_source_register.md#s038), [S039](10_source_register.md#s039)

### Proposed model

Use a high-level terminal with a separate passenger-connected subsystem. Treat the label discrepancy as an importer regression test. A generated replica must stop for unresolved physical inventory, while a synthetic terminal can proceed with an explicitly chosen inventory that is not claimed to be the real station.

### Test programme

Feed the importer the page count and map labels as separate claims. It should produce a discrepancy record and avoid creating an extra physical road automatically. Once an authoritative inventory is acquired, resolve the claims without erasing their original provenance.

## 9. Cross-case lessons for the specification

**Inventory is not geometry.** Label counts, physical edges, platform roads and independent berths require separate entities.

**Geometry is not routing.** A connecting curve must belong to a permitted route with compatible point/protection requirements.

**Routing is not operating capacity.** Train length, readiness, dwell, route release and disruption determine time-dependent feasibility.

**Train capacity is not passenger capacity.** A valid timetable can still have inadequate interchange, queues or inaccessible paths.

**A plausible model is not a game guarantee.** The adapter must verify representability and compare observed behaviour with the shadow model.

These are the architectural invariants the regional examples should test. The next release should deepen a few reference instances to technical-topology level rather than merely add more passenger maps.

## 10. Version 0.2 applicability note

The regional dossiers are retained as the v0.1 research baseline; no new exact Leeds, Edinburgh, Glasgow, Reading, Manchester, Bristol or Liverpool topology has been imported in this release. Their reference ideas now map to executable **sub-behaviour** tests where applicable: labels independent of physical IDs, separate pedestrian/rail connectivity, train fit and onward route eligibility.

The running proof does not implement longitudinal split berths, coupling or permissive simultaneous occupation. In particular, passing its whole-platform tests is not evidence that the Edinburgh- or Birmingham-inspired sectioned-road model is complete.

Next regional work should select one precisely bounded component with adequate technical evidence and use it to challenge the generator. Repeatedly adding a generic station description would not close the missing geometry and permission fields.
