# London passenger termini, approaches and junctions

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

Version **0.2.0** · 20 September 2026 · Reference records **R03–R13, R22–R25**

The documented observations below are deliberately bounded. The proposed abstractions and experiments are engineering recommendations for the bridge, not claims to have reconstructed each station's full track plan.

## 1. Waterloo: large terminal banks and service-group separation

### Documented basis

The July 2025 station map labels mainline platforms 1–24. Network Rail's historical 2016 Wessex specification discusses the approach corridor and the planned reuse of former international platforms, including a service-segregation rationale. The older document must not be used as today's platform or timetable inventory. [S004](10_source_register.md#s004), [S005](10_source_register.md#s005)

### Proposed abstraction

Represent a large terminus as several platform banks connected to corridor groups, with a limited set of cross-bank alternatives. Avoid a default all-to-all ladder joining every approach to every platform. Give each bank a normal role, compatible train lengths and optional recovery connections.

Separate the final platform fan from the earlier sorting of approach tracks. An approach may need to establish the useful track order before the throat. A solver that considers only the final fan can inadvertently force avoidable crossings into the last available space.

### Experiments

Compare a common ladder, grouped ladders and earlier service sorting under the same synthetic service/stock pattern. Measure conflicting traversal time, turnround recovery, long-train compatibility, passenger redirection and queued trains outside the station.

Treat Waterloo East as a distinct rail station linked through the passenger model, not extra terminal roads available to a Waterloo train. Require technical evidence before importing exact corridor-to-platform eligibility.

## 2. Victoria: operating groups and phased infrastructure versions

### Documented basis

The map labels platforms 1–19. Network Rail describes a phased programme of track and signalling upgrades on the South London approaches, with completed and ongoing phases distinguished. [S006](10_source_register.md#s006), [S007](10_source_register.md#s007)

### Proposed abstraction

Use platform groups with explicit normal and exceptional route eligibility. The initial fixture should test whether routinely crossing between groups spreads delay to otherwise independent services. Cross-access should be an evaluated recovery feature, not a design goal in itself.

A separate infrastructure-version model should describe construction stages. The state used for one simulation must not combine old pointwork, future signalling and a current platform map merely because the sources share the station name.

### Experiments and gaps

Close a selected approach group, then compare partial operation, cross-group rerouting and reduced service. Score passenger-platform changes as well as train delay. Acquire a dated technical approach plan and explicit platform/route grouping before assigning real service groups to numbered platforms. The current research does not certify a platform-by-platform Kent/Sussex route table.

## 3. Euston: turnrounds, stock cycles and useful spare platforms

### Documented basis

The current station information reports 16 platforms; the consulted map is a July 2025 passenger layout. These sources do not define future HS2 infrastructure or a complete present-day route table. [S008](10_source_register.md#s008), [S009](10_source_register.md#s009)

### Proposed abstraction

Make stock availability a first-class constraint. A terminal platform plan is incomplete without the arrival that supplies the next departure, a replacement stock movement, or an explicit independent-stock assumption.

Useful spare capacity is train-class dependent. A nominally available road may have insufficient usable length, incompatible access, a blocked exit or an unsuitable passenger route. Model an operational reserve as a set of feasible movement opportunities, not one permanently empty platform count.

### Experiments

Delay one long-distance arrival and propagate its linked departure. Compare holding the departure, changing stock, changing berth and moving empty stock to a servicing/stabling interface. Report what assumptions are synthetic. Do not infer that the game supports realistic coupling, servicing or stock substitution until the adapter demonstrates it.

## 4. Liverpool Street: a station complex is not one train-routing graph

### Documented basis

The January 2026 map labels seventeen mainline platforms and shows the separate Elizabeth line passenger interface. [S010](10_source_register.md#s010)

### Proposed abstraction

Separate the terminal rail subsystem from a cross-city subsystem while allowing passenger transfers between them. Attach system, electrification, train-eligibility and access-policy attributes to the relevant subgraphs.

The platform-assignment solver must reject an apparent spare platform in another subsystem unless a verified physical route and operating permission exist. Shared branding, a station name, a concourse connection or a geographic overlap must not override that check.

### Experiments and gaps

Apply concentrated transfers between a terminal arrival and cross-city departures; include a failed vertical-circulation element. Separately test a terminal-throat disruption. Exact approach groupings and upstream junction geometry remain technical-source acquisition tasks; the wayfinding map is not sufficient.

## 5. Paddington: staggered lengths and separate through-service interfaces

### Documented basis

The June 2026 map's mainline labels are 1–12 and 14. It also identifies distinct Underground and Elizabeth line access. [S011](10_source_register.md#s011)

### Proposed abstraction

Use nonuniform platform lengths and staggered buffer-end positions as variables rather than forcing a rectangular fan. The platform edge, track end and stopping position need separate coordinates. A train may geometrically fit a track while not fitting its usable boarding interval.

Maintain service-eligibility sets and pedestrian paths to other systems. Do not merge terminal and subsurface rail resources to make platform assignment easier.

### Experiments

Allocate a mixture of long and short trains to a staggered terminal fixture; compare static service zoning with limited dynamic reassignment. Penalise unnecessary long walking transfers and late platform changes. Re-solve the entire crossover assembly when platform spacing or throat position changes.

The maximum displayed number must not become the station capacity: this map is also a regression case for non-contiguous numbering.

## 6. King's Cross and Gasworks Tunnel: simplify under fixed boundaries

### Documented basis

The station page lists eleven platforms numbered 0–10. A February 2021 project announcement describes throat simplification and reopening a disused Gasworks Tunnel bore for two tracks. The announcement is evidence of scheme intent, not by itself a record of final commissioning geometry. [S012](10_source_register.md#s012), [S013](10_source_register.md#s013)

### Proposed abstraction

Constrain the approach at fixed portal positions, headings and available track corridors. Allow the station-side topology to vary. The solver should find useful independent movements with fewer obstructive connections rather than maximise the number of possible geometric paths.

Opening an additional corridor in a synthetic comparison changes the boundary conditions, not just the number of terminal platforms. Compare like-for-like service scenarios to identify whether the benefit arises from route independence, shorter resource occupation or extra access capacity.

### Experiments

Use a baseline with constrained approach ports; compare simplified specialwork, an additional approach pair and a platform-allocation change. Keep the civil interventions explicit. A mathematical connection that requires an unsupported crossing type should return `not_representable`, not silently substitute a different topology.

## 7. St Pancras: eligibility groups and passenger-processing zones

### Documented basis

The owner identifies Thameslink A/B below the main level, East Midlands platforms 1–4, international platforms 5–10, and Southeastern platforms 11–13. [S014](10_source_register.md#s014)

### Proposed abstraction

This is the strongest initial reference for **grouped eligibility**. Model a station complex with several rail subsystems and passenger zones. A platform assignment must satisfy route connectivity, train compatibility, system scope and any specified passenger-processing requirements.

The optional passenger model should represent controlled-zone entry and associated queues where the chosen scenario includes them. Such a zone is not interchangeable with an ordinary open platform access path. The bridge need not reproduce actual border-processing operations to model the resulting spatial constraint.

### Experiments

Inject an unavailable platform within one group. The recovery solver should search compatible alternatives, not jump into another group merely because the total station complex has spare labels. The explanatory packet should distinguish “no spare platform in this operating group” from “every platform in the complex is occupied”.

## 8. London Bridge: station function and approach function together

### Documented basis

The current station page reports fifteen platforms and describes the lower concourse. A 2013 redevelopment announcement proposed changing the balance from six through/nine terminal to nine through/six terminal platforms. The consulted current map is primarily a concourse map, not proof of all as-built track connections. [S015](10_source_register.md#s015), [S016](10_source_register.md#s016), [S017](10_source_register.md#s017)

### Proposed abstraction

Allow platform roles to change during candidate generation: a road can be designed for through operation, terminal use or a permitted combination. This changes its required connections, buffer/overrun treatment, service eligibility and stock cycle.

Optimise the station and adjoining track-order arrangement together. Additional through platforms have little value if every extra movement still traverses the same blocking resource. Passenger circulation must also cope with the changed platform distribution.

### Experiments

Compare two synthetic fifteen-label layouts with different through/terminal role assignments, the same service demand and the same external corridor boundary. Then change the corridor topology and measure the combined effect. Keep the result labelled synthetic; do not attribute it to actual London Bridge capacity.

## 9. Bermondsey: targeted grade separation

### Documented basis

The project announcement identifies separation of Thameslink and Kent traffic as the purpose of the diveunder. [S018](10_source_register.md#s018)

### Proposed abstraction

A grade-separation pattern starts with a named conflict between movement families. It then solves horizontal alignment, vertical separation, transition lengths, crossing structure and downstream connections. The chosen route may go above or below; “diveunder” is not a requirement to place an isolated tunnel beneath otherwise unchanged tracks.

### Experiments

Compare a flat crossing, selective separation and a changed track order. Count conflicts at the next merge and queues at the next station as well as at the crossing. Reject a candidate that only moves the bottleneck outside the assessment boundary. Include drainage feasibility and structural envelopes as assessed or explicitly unassessed fields; this is not detailed civil certification.

## 10. Clapham Junction: several railway flows, one passenger interchange

### Documented basis

The official material supports the seventeen-platform inventory. The reviewed National Rail plan shows the platform arrangements and bridge/subway circulation; it does not establish the complete train-route table or regular stopping permissions. [S019](10_source_register.md#s019), [S020](10_source_register.md#s020)

### Proposed abstraction

Model parallel corridor groups with explicit links where proven, plus a separate pedestrian interchange graph. Do not treat all seventeen labels as a common pool of train berths. Likewise, a track with a platform label must not automatically acquire a stopping permission for every service.

The design domain should include both approaches far enough to capture branching, merging and turnbacks relevant to the specified services. Exact pointwork is a separate acquisition task, not a reconstruction from the curved lines of a passenger map.

The passenger model should distribute transfers between specific arriving and departing services. A “central footbridge” object with unlimited instantaneous capacity is insufficient for evaluating a major interchange. Represent path length, usable width, vertical travel, queues, accessibility and the location of access relative to train stopping positions.

### Experiments

Test simultaneous arrivals in several groups, uneven demand across a long train, a lift unavailable for an accessible route, a missed connection and a late platform change. Train paths may remain conflict-free while the passenger model fails its transfer or crowding objective. Keep those outcomes separate.

## 11. Willesden Junction: topology, levels and false connections

### Documented basis

The National Rail plan shows five platform labels in distinct crossing arrangements with passenger links. TfL identifies the interchange's current line context. The GLA's 2018 feasibility study was located but exceeded the available PDF retrieval limit and was **not reviewed**. [S021](10_source_register.md#s021), [S022](10_source_register.md#s022), [S023](10_source_register.md#s023)

### Proposed abstraction

Create distinct rail layers and attach passenger-transfer edges between the accessible parts of the station. Do not create a rail junction where the layers intersect geometrically. A bay or turnback should be a functional component with its own permitted entry, stopping, reversal and departure sequence.

Potential nearby through tracks, sidings or depot connections must be represented only after their actual connectivity is verified. Proximity is not permission to join them. The initial model should retain unknown boundaries rather than confidently fabricate a complete Willesden railway district.

### Experiments

Place two rail corridors at different heights and crossing angles. Verify no train can switch between them without an explicit connecting route, while passengers can interchange through a permitted path. Add a synthetic bay and test that reversal cannot block a protected through route through a false graph connection.

This is a high-priority exact-topology acquisition case because it tests more than an ordinary large terminal fan.

## 12. Smaller termini as controls

Network Rail reports six platforms at Charing Cross and seven at Cannon Street. National Rail provides preliminary access records for Marylebone and Fenchurch Street; detailed approach plans for the latter two have not yet been acquired. [S051](10_source_register.md#s051)–[S054](10_source_register.md#s054)

Use these as smaller control cases, not as substitutes for the requested large stations. A pattern library should show when a simple fan is sufficient, when approach constraints dominate and when extra connectivity adds little. For these controls, obtain actual topology before assigning real junction names, track counts beyond the station, portal positions or route speeds.

## 13. Shared London design contracts

The generator should expose platform-bank count, service-group eligibility, permitted normal/recovery connections, approach-port order, train-length classes, turnround policy, fixed civil boundaries and passenger-transfer goals. These are the meaningful parameters that Astra should set or approve.

Python should decide the individual switches, route candidates, stopping positions, resource timings and local geometry within those contracts. A station-inspired visual style may guide canopies, roof alignment and restrained specialwork, but must not replace the engineering checks.

For every candidate, return three distinct questions answered: **Can the intended trains move? Can the intended passengers interchange? Can the game represent and execute the design?**

## 14. Waterloo technical fragment: a useful dated schematic

### 14.1 Newly reviewed evidence

RAIB Report 19/2018 supplies a Waterloo schematic and a point-group detail for the August 2017 incident state. Figure 4 excludes sidings and platforms 20–24 and predates the platform 1–4 modifications. The report names eight approach lines in east-to-west order. Figure 5 and paragraphs 21–22 describe 1524A/B/C as three point ends intended to operate together. [S055, PDF pp. 11 and 13](10_source_register.md#s055)

The exact imported names and group membership are retained once in [reference_fragments.json](evidence/reference_fragments.json). This is stronger topology evidence than a passenger map, but it remains an incomplete historical fragment with no measured coordinates and no imported full control table.

### 14.2 Consequence for component modelling

Do not assume `one visible point end = one independently controllable switch`. The production model needs both `PointEnd` and `PointGroup`. A route requests an allowed **group state**, while its physical path and fouling resources are recorded independently.

A group-state dictionary should permit only states that the component's evidence/catalogue defines. It must not infer that every Cartesian combination of visible ends is available. Mirroring a component changes its geometry and port correspondence but must preserve or explicitly transform that allowed-state relation.

The proof demonstrates this at the resource level: claims on different ends are normalised to one logical group lock before checking compatibility. Agreeing group states can coexist as state requirements; their associated running-space claims can still conflict. That unit test does not reproduce Waterloo's interlocking.

### 14.3 Construction state as part of the reference

A construction diagram needs at least three independent attributes: infrastructure that physically exists, movements permitted in the named stage, and infrastructure intended for a later stage. A line shown closed is not necessarily absent. A future connection cannot serve a current-stage train.

The evidence importer should attach `asset_validity` and `operating_availability` separately. The geometry optimiser may reuse existing physical assets, while the operational evaluator respects closures. The executor then needs an explicit sequence of approved intermediate states rather than assuming the end-state can be installed atomically.

### 14.4 Corridor and stock-access context

The 2016 Wessex route specifications describe corridor roles and proposed work at Queenstown Road associated with empty-stock access to Clapham Yard. These are historical planning statements, not proof of subsequent construction or current platform permissions. [S056, SRS C.01, PDF p. 3](10_source_register.md#s056)

The design lesson is to place the depot/yard boundary far enough out to reveal its conflicts. An empty-stock departure is not merely a passenger service with zero passengers: it may require a different corridor connection and a later service dependency. In this release's proof, the outgoing activity type is retained and occupies resources, but the yard beyond the portal is not modelled.

## 15. Clapham: an explicit next technical boundary

The new corridor source makes the next acquisition task more specific. Seek a coherent dated layout covering platform approaches, route-group interfaces and the relevant stock-access connection—not simply a count of tracks crossing the station site. The complete Clapham route table remains missing.

The production fixture should have distinct corridor groups and physical holding sections. It should test both passenger interchange and train-operation disturbance without allowing the pedestrian graph to create rail connectivity. The current proof has a small graph-separation test only; it has no Clapham passenger-demand or queue calibration.

A junction-region candidate must state whether the optimisation boundary contains the entire affected connection. If it does not, it can return a local geometry concept but not a corridor performance verdict.

## 16. Willesden: distinguish a station study from an operating railway plan

### 16.1 New evidence and a remaining retrieval gap

An OPDC hearing response referring to an upcoming June 2019 meeting summarises central, dual and offset access-link options from a **2017** study. Its 1:20-or-better criterion concerns walking/cycling routes, not railway track. The document leaves detailed bridge alignment work outstanding. [S057, paragraphs 1.5–1.8](10_source_register.md#s057)

A 2017 TfL response records that consultant and technical material was disclosed, but the attachments themselves were not acquired in this release. [S059](10_source_register.md#s059) The separate June 2018 full study registered as S023 remains unreviewed after another unsuccessful retrieval attempt. None of those records substitutes for having read that specific report.

### 16.2 Domain-qualified numerical rules

Every geometric rule needs a domain field. `pedestrian_route.gradient` and `rail_alignment.gradient` are different quantities with different applicability even when both are written as ratios. A source mentioning a bridge does not establish whether it carries trains, people, cycles or roads.

The rule importer must reject a rule whose domain does not match the target evaluator. Merely converting 1:20 to 0.05 would be mathematically correct but could still be a severe engineering-category error. Unit correctness is necessary, not sufficient.

### 16.3 Proposed instance structure

Represent the station complex as rail-layer instances connected through explicit passenger links. Each rail layer has ports, lawful route pairs, platform roads and its own level/elevation evidence. An access-link option is a separate civil/passenger candidate that may cross railway envelopes without creating a train connection.

For the next exact-topology dossier, resolve the actual boundary connections and bay/turnback relationships from technical railway evidence. Preserve design-study alternatives as alternatives rather than merge them into one fictional existing layout.

## 17. What this changes in the worked design

The worked example uses ordered approach ports, grouped platform access, complete stock activities, distinct resource kinds and a typed evidence ledger. Its three layout families are original synthetic abstractions. They are not extracted scale models of Waterloo, Clapham or Willesden and should never inherit those stations' names as measured-capacity labels.

## 18. Version 0.3: a reference idea becomes a tested data distinction

The dated Waterloo material in S055 continues to inform the distinction between a logical point-control group and the physical track occupied by a train. The new synthetic crossover tests allow compatible control-state sharing while independently enforcing running-space and proximity conflicts. They do not reconstruct Waterloo's component geometry or control tables.

The generated bank is also deliberately smaller than Waterloo: four roads and one bidirectional approach. Its value is testing the compiler and complete-visit contract before composing the multiple approach/service groups required for a large terminus. See [14](14_geometry_components_and_resource_compiler.md) and [15](15_worked_geometry_examples.md).
