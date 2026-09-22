# Parametric passenger railway pattern catalogue

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Current integration:** v0.6 addendum at the end of this document; earlier sections retain their version-specific status. Current execution evidence is in [25](25_v06_execution_report.md).

Version **0.3.0** · 20 September 2026 · **32 proposed pattern families**

These are functional, parameterised engineering contracts, not completed game prefabs. Reference associations identify research inspiration, not proof that an exact component exists at that location. Generic components without a verified site inventory are labelled accordingly. Source evidence for reference IDs is in [the atlas](02_reference_atlas.md).

## 1. Common pattern contract

Every pattern must declare its purpose, mandatory movements, ports, applicable train/era profiles, geometry parameters, civil reservations, passenger interfaces, operating resources, required game capabilities, adjustment budget, evidence lineage and validation tests.

A port is more than a position: it carries direction, heading, elevation, grade, track/system role and connection conditions. A pattern returns a candidate topology, engineered alignment, route/resource model, passenger links, footprint and unresolved assessments. It must not return an unexplained spline collection.

### Composition rules

Two patterns can be joined only when their port contracts are compatible. The composed assembly then requires fresh clearance, route, release, passenger and queue checks. Local correctness is necessary but not sufficient for whole-station correctness.

Mirroring changes handedness and may change directional service relationships. Compression changes length, radius, gradient, train fit and resource occupation; it is a new engineering solve. Neither transformation inherits the parent's pass status.

## 2. Pattern records

<a id="p01"></a>
### P01 — Grouped terminal banks

**Reference context:** R03 Waterloo; R04 Victoria.  
**Principal parameters:** Bank count; approach-group order; required and recovery eligibility; train-length classes.

**Required behaviour:** Generate a separate fan for each normal service group and only the cross-bank connections justified by the brief. Return a complete movement matrix and resource graph.

**Guard/failure conditions:** Reject a spare berth that cannot be reached within its eligibility group. Compare against a common-ladder alternative, not against an assumed perfect baseline.

**Requirements:** TOP-001, TOP-003, OPS-002. **Benchmarks:** B005, B017 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p02"></a>
### P02 — Mixed through and terminal station

**Reference context:** R10 London Bridge; R14 Leeds.  
**Principal parameters:** Road roles; through-service pairs; terminating services; turnround/stock policy.

**Required behaviour:** Generate through connections and terminal ends as distinct roles. Preserve the onward route for every through working and the next activity for every terminating working.

**Guard/failure conditions:** Do not count an arrival-only connection as a through route. A buffer-ended road cannot substitute for a through path without a complete authorised operating alternative.

**Requirements:** TOP-002, TOP-004, TOP-005. **Benchmarks:** B005, B009, B017 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p03"></a>
### P03 — Split throat ladders with bounded cross-access

**Reference context:** R01 Birmingham; R03 Waterloo.  
**Principal parameters:** Throat sectors; normal group access; recovery movements; crossing-resource budget.

**Required behaviour:** Generate several smaller route-distribution assemblies and optional links between them. Evaluate independence against point and protection requirements, not just geometric separation.

**Guard/failure conditions:** Additional crossovers must demonstrate a useful movement or resilience benefit. Do not maximise route count without checking conflict occupation.

**Requirements:** TOP-003, TOP-008, OPT-002. **Benchmarks:** B006, B040 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p04"></a>
### P04 — Staggered terminal fan

**Reference context:** R07 Paddington; R05 Euston.  
**Principal parameters:** Buffer-end offsets; edge lengths; track lengths; approach envelope; train classes.

**Required behaviour:** Fit nonuniform platform roads and stopping intervals while reserving concourse/access space. Return each platform edge separately from the track end.

**Guard/failure conditions:** A long track is not automatically a long boarding platform. Check stopping tolerance, structures and the whole connecting fan after an offset changes.

**Requirements:** GEO-002, GEO-007, GEO-009. **Benchmarks:** B010, B021, B037 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p05"></a>
### P05 — Sectioned long platform road

**Reference context:** R01 Birmingham; R15 Edinburgh.  
**Principal parameters:** Physical road/edge interval; label intervals; train lengths; permitted occupation configurations.

**Required behaviour:** Offer mutually constrained full-length and short-berth configurations. Permit simultaneous occupation only when explicitly enabled by the operating and capability profiles.

**Guard/failure conditions:** Reject overlap, blocked access to a free section, or invented split-berth permission. Labels must never create capacity by themselves.

**Requirements:** DAT-001, DAT-003, OPS-007. **Benchmarks:** B001, B008 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p06"></a>
### P06 — Opposed-end berth groups

**Reference context:** R15 Edinburgh.  
**Principal parameters:** Approach ends; berth reachability; reversing permissions; conflict/release model.

**Required behaviour:** Fit stopping opportunities reached from different ends while retaining shared-road resources. Route selection includes the exit or next stock movement.

**Guard/failure conditions:** Free metres at the far end do not prove a reachable berth. Check whether an intervening train blocks access or release.

**Requirements:** TOP-004, OPS-002, OPS-004. **Benchmarks:** B005, B007, B008 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p07"></a>
### P07 — Single crossover assembly

**Reference context:** Component-level proposal for the whole atlas.  
**Principal parameters:** Adjacent-track geometry; spacing; connection direction; component catalogue; speed profile.

**Required behaviour:** Solve the two turnouts and connecting alignment as one component assembly, including transitions into the parent tracks and clearance envelopes.

**Guard/failure conditions:** Reject a short reverse curve or incompatible cant/grade even when each turnout individually passes. No universal turnout-speed inference from crossing angle.

**Requirements:** GEO-003, GEO-004, GEO-005. **Benchmarks:** B010, B011 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p08"></a>
### P08 — Paired crossovers and approach sorting

**Reference context:** R03 Waterloo-inspired corridor; R04 Victoria-inspired grouping.  
**Principal parameters:** Desired exchange movements; crossover separation; holding lengths; available corridor.

**Required behaviour:** Place opposite crossover directions only where the required movement set needs them. Include the intermediate resource occupation and any usable holding function.

**Guard/failure conditions:** Do not assume both crossover movements are simultaneous or that the intervening track can hold the design train.

**Requirements:** TOP-008, GEO-004, OPS-008. **Benchmarks:** B006, B010, B015 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p09"></a>
### P09 — Scissors crossover

**Reference context:** Generic compact-throat proposal; not an asserted exact site component.  
**Principal parameters:** Track spacing; two crossover routes; crossing type; supported asset catalogue.

**Required behaviour:** Treat the intersecting crossover paths and crossing as a unified geometric and resource object. Compare against a longer paired-crossover solution.

**Guard/failure conditions:** Reject unsupported diamond/specialwork or false independent movements. A compact drawing can have a restrictive conflict graph.

**Requirements:** DAT-004, GEO-003, GEO-004, EXE-002. **Benchmarks:** B004, B006, B025 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p10"></a>
### P10 — Diamond or slip crossing module

**Reference context:** Generic specialwork proposal; site inventories still pending.  
**Principal parameters:** Explicit legal route pairs; crossing geometry; fixed/movable type; operating profile.

**Required behaviour:** Encode each permitted traversal independently from physical intersection. A slip variant adds only its defined connecting routes.

**Guard/failure conditions:** Never create an all-directions graph node at the crossing. Reject a variant the game cannot faithfully represent.

**Requirements:** DAT-004, GEO-003, EXE-001. **Benchmarks:** B004, B025 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p11"></a>
### P11 — Curved or skewed throat fan

**Reference context:** R20 Bristol-inspired geometry; R12 Clapham-inspired context.  
**Principal parameters:** Parent-track curvature; terminal directions; catalogue compatibility; swept envelopes.

**Required behaviour:** Solve an entire multi-track fan within the curved corridor using compatible components and joint clearance constraints. Preserve geometric and operating asymmetry.

**Guard/failure conditions:** Do not warp a straight prefab into shape. Reject new clearance infringements and components lacking applicable curved-geometry support.

**Requirements:** GEO-003, GEO-005, GEO-006, GEO-010. **Benchmarks:** B011, B012, B028 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p12"></a>
### P12 — Asymmetric add-on platform

**Reference context:** R14 Leeds.  
**Principal parameters:** Existing asset identities; available side corridor; required new movements; access connection.

**Required behaviour:** Add a platform/road without renumbering physical IDs or assuming a mirrored throat. Evaluate the incremental movement matrix and passenger access.

**Guard/failure conditions:** A new label alone creates no track. An additional road with no useful arrival/departure opportunity must not be scored as added operating capacity.

**Requirements:** DAT-002, TOP-002, TOP-004. **Benchmarks:** B002, B005 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p13"></a>
### P13 — Parallel-corridor passenger interchange

**Reference context:** R12 Clapham Junction.  
**Principal parameters:** Rail corridor groups; verified cross-links; service-transfer demand; circulation structures.

**Required behaviour:** Keep each corridor operationally explicit and join passenger flows through a separate access graph. Add rail links only where evidence or the synthetic brief defines them.

**Guard/failure conditions:** Do not allocate trains across groups through pedestrian connectivity. Test simultaneous passenger pulses even when rail routes are independent.

**Requirements:** DAT-004, PAX-001, PAX-002, PAX-003. **Benchmarks:** B003, B018 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p14"></a>
### P14 — Multi-level interchange

**Reference context:** R13 Willesden; R16 Glasgow Central.  
**Principal parameters:** Layer elevations and systems; physical rail links; passenger links; accessible routes.

**Required behaviour:** Create separate rail graphs and a three-dimensional pedestrian interchange. Preserve independent operating assessments for each rail subsystem.

**Guard/failure conditions:** A plan-view intersection cannot create a turnout. A lift outage must not silently remove accessibility status from the affected transfer.

**Requirements:** DAT-001, DAT-004, PAX-004. **Benchmarks:** B003, B019 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p15"></a>
### P15 — Service-eligibility-zoned station complex

**Reference context:** R09 St Pancras; R06 Liverpool Street.  
**Principal parameters:** Operating groups; allowed train classes; traction/system constraints; passenger access zones.

**Required behaviour:** Maintain platform eligibility and controlled/ordinary passenger zones as distinct constraints. Show spare capacity by compatible group as well as by complex.

**Guard/failure conditions:** Reject an incompatible alternative even when physically nearby. Do not infer rail integration from common branding.

**Requirements:** DAT-005, PAX-001, OPS-002. **Benchmarks:** B017, B036 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p16"></a>
### P16 — Peripheral bay turnback

**Reference context:** Mixed-station proposal inspired by R14/R15.  
**Principal parameters:** Bay side; service entry/exit; usable length; reversal/readiness; through-route priority.

**Required behaviour:** Place a terminating facility at the edge of the operating group where useful. Evaluate its crossing movements against retaining the train on a through road.

**Guard/failure conditions:** A bay is not automatically conflict-free. Its departure may cross the dominant flow; include that movement and stock readiness.

**Requirements:** TOP-005, OPS-005, OPS-006. **Benchmarks:** B009, B017 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p17"></a>
### P17 — Centre turnback

**Reference context:** Generic passenger-corridor proposal, not a claimed site replica.  
**Principal parameters:** Running-line order; centre-road envelope; entry/departure directions; reversal capability.

**Required behaviour:** Offer a central turnback between directional flows when the complete route and civil geometry fit the brief. Evaluate against a peripheral bay.

**Guard/failure conditions:** Reject unsupported reversal, insufficient stopping length, or a turnback access route that defeats the required independent through movements.

**Requirements:** TOP-001, GEO-007, OPS-007. **Benchmarks:** B005, B008, B037 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p18"></a>
### P18 — Tail-track reversal facility

**Reference context:** Generic through-station proposal.  
**Principal parameters:** Tail-track length; end constraints; reversal profile; return route; stock dwell.

**Required behaviour:** Move reversing trains beyond the passenger berth where supported, then route them back to their departure opportunity. Reserve the complete out-and-back cycle.

**Guard/failure conditions:** Do not remove platform occupation without adding tail-track travel and readiness time. Prevent a returning train from conflicting with the next arrival.

**Requirements:** TOP-005, OPS-005, OPS-007. **Benchmarks:** B009, B035 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p19"></a>
### P19 — Off-platform stabling/servicing interface

**Reference context:** R05 Euston-inspired stock model; R17 Reading project context.  
**Principal parameters:** Stock cycle; stabling capacity; service times; access side; engine-supported activities.

**Required behaviour:** Represent a bounded interface rather than a full depot simulation initially. Include every empty-stock arrival/departure through the passenger throat.

**Guard/failure conditions:** No teleportation or duplicate stock. If servicing is not modelled in the game, keep it an explicit shadow-model assumption.

**Requirements:** OPS-006, OPS-007, OPS-012. **Benchmarks:** B009, B039 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p20"></a>
### P20 — Approach holding section

**Reference context:** R19 Oxford Road proposal.  
**Principal parameters:** Train length; hold location; upstream fouling/resource boundary; downstream route; stopping profile.

**Required behaviour:** Create a usable train-holding opportunity and include it in queue propagation. Distinguish physical room from permitted/protected stopping.

**Guard/failure conditions:** A train front beyond a signal is not proof the tail clears the upstream platform or junction.

**Requirements:** OPS-004, OPS-008, OPS-009. **Benchmarks:** B007, B015, B016 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p21"></a>
### P21 — Selective flying junction

**Reference context:** R11 Bermondsey conflict-removal principle; R17 Reading.  
**Principal parameters:** Conflicting movements; upper/lower choice; target ports; vertical budget; train profiles.

**Required behaviour:** Raise the selected movement and solve both ramps, transitions, crossing structure and connecting junctions as one assembly. Compare against lowering the other route.

**Guard/failure conditions:** Check footprint and full swept clearance, then the next merge. Never report universal capacity gain from the presence of a flyover.

**Requirements:** TOP-006, GEO-008, OPT-002. **Benchmarks:** B013, B014 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p22"></a>
### P22 — Selective diveunder

**Reference context:** R11 Bermondsey; R17 Reading.  
**Principal parameters:** Crossing movement; lower profile; structural envelope; ground/water assumptions; approach constraints.

**Required behaviour:** Lower the selected movement, reserve retaining/structure/drainage envelopes, and evaluate train performance and downstream conflict.

**Guard/failure conditions:** Unknown ground or drainage requirements remain unassessed. A short visually neat ramp cannot override the gradient/transition profile.

**Requirements:** GEO-005, GEO-008, EVD-002. **Benchmarks:** B013, B014, B038 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p23"></a>
### P23 — Track-order rearrangement

**Reference context:** R03/R04 grouped approaches; R11 corridor separation.  
**Principal parameters:** Incoming/outgoing ordered track groups; required movement mapping; spatial envelope.

**Required behaviour:** Solve the permutation of tracks and choose flat, split-level or earlier sorting alternatives. Treat track order as a design variable with operating consequences.

**Guard/failure conditions:** Do not force a last-minute crossing into the station throat when an earlier arrangement changes the conflict structure.

**Requirements:** TOP-003, TOP-006, TOP-007. **Benchmarks:** B014, B016, B040 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p24"></a>
### P24 — Fixed-portal approach to terminal

**Reference context:** R08 King's Cross/Gasworks Tunnel.  
**Principal parameters:** Portal positions/headings/elevations; usable track corridors; platform movement matrix.

**Required behaviour:** Hold civil boundary conditions fixed and vary the throat topology and local geometry. An extra portal corridor is a separate scoped intervention.

**Guard/failure conditions:** Do not shift tunnel portals silently to make a candidate fit. Escalate when the approved corridor cannot support the required movements.

**Requirements:** BRF-003, GEO-002, OPT-004. **Benchmarks:** B010, B029 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p25"></a>
### P25 — Separated arrival/departure approach groups

**Reference context:** Generic large-terminal candidate.  
**Principal parameters:** Arrival/departure flows; platform groups; reversal/stock cycle; merge interfaces.

**Required behaviour:** Compare directional access grouping with service-family grouping using the same demand and boundary. Include how each departure reaches its onward corridor.

**Guard/failure conditions:** Do not label groups independent merely because their final approach tracks differ; point/protection or downstream resources may still conflict.

**Requirements:** TOP-003, TOP-008, OPS-002. **Benchmarks:** B005, B006, B040 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p26"></a>
### P26 — Integrated station-area redevelopment

**Reference context:** R17 Reading; R10/R11 London Bridge corridor.  
**Principal parameters:** Station role changes; grade separation; stock access; passenger deck; construction phases.

**Required behaviour:** Compose several validated patterns under one boundary and re-evaluate their interfaces. Optimise the integrated movement and passenger model, not the sum of isolated component scores.

**Guard/failure conditions:** A passing station and passing junction do not guarantee their composition passes. Recheck inter-pattern geometry, resources and queues.

**Requirements:** TOP-006, GEO-009, OPS-009. **Benchmarks:** B013, B014, B016, B033 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p27"></a>
### P27 — Passenger transfer deck

**Reference context:** R17 Reading.  
**Principal parameters:** Platform access locations; flow matrix; usable deck area; vertical links; civil support envelope.

**Required behaviour:** Reserve the deck and supports early. Size/evaluate the passenger graph using explicit demand and declared capacity assumptions.

**Guard/failure conditions:** Do not place piers within the required swept envelope or give the deck unlimited walking/queuing capacity.

**Requirements:** GEO-009, PAX-003, PAX-005. **Benchmarks:** B012, B018, B021 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p28"></a>
### P28 — Passenger subway and station entrances

**Reference context:** R20 Bristol; R10 London Bridge circulation context.  
**Principal parameters:** Entrance locations; levels; subway envelope; vertical links; accessibility; construction constraints.

**Required behaviour:** Connect entrances and platform access through a separate passenger structure model. Preserve its geometry when the track arrangement changes.

**Guard/failure conditions:** A rail optimisation cannot delete the only accessible connection. Underground structure/terrain requirements may remain unassessed, not automatically safe.

**Requirements:** GEO-009, PAX-001, PAX-004. **Benchmarks:** B019, B021, B038 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p29"></a>
### P29 — Distributed platform access

**Reference context:** R12 Clapham; R10 London Bridge.  
**Principal parameters:** Door/boarding zones; entrances; access positions; crowd pulses; accessible alternatives.

**Required behaviour:** Evaluate several access points along platforms rather than one idealised central link. Include local queues and the influence of access position on passenger distribution.

**Guard/failure conditions:** Average platform area or average walking time must not hide a local pinch point or inaccessible transfer.

**Requirements:** PAX-002, PAX-003, PAX-005. **Benchmarks:** B018, B019, B021 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p30"></a>
### P30 — Staged throat remodelling

**Reference context:** R04 Victoria programme; R17 Reading project context.  
**Principal parameters:** Baseline; target; allowed possessions; temporary connections; minimum retained service.

**Required behaviour:** Generate explicit infrastructure versions and allowed transitions. Re-run train/passenger checks at each stage rather than only for the final layout.

**Guard/failure conditions:** No mixed-stage topology or assumed atomic rebuild. Partial execution needs a recovery/compensation record.

**Requirements:** DAT-007, EXE-004, EXE-008. **Benchmarks:** B022, B027, B033 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p31"></a>
### P31 — Curved platform and stopping-position assembly

**Reference context:** R20 Bristol-inspired geometry.  
**Principal parameters:** Track curve; vehicle/door model; boarding-edge offset; stopping range; passenger access.

**Required behaviour:** Solve track, platform edge and stopping positions jointly. Use a declared swept-envelope and platform-gap approximation until a validated model exists.

**Guard/failure conditions:** A centreline offset alone cannot certify the train/platform interface. Mark unverified gap/dispatch requirements unassessed.

**Requirements:** GEO-006, GEO-007, EVD-002. **Benchmarks:** B012, B024, B037 in [09](09_validation_benchmarks_and_roadmap.md).

<a id="p32"></a>
### P32 — Coupled station/junction corridor

**Reference context:** R01/R02 Birmingham; R18/R19 Manchester.  
**Principal parameters:** Boundary stations; junction resources; service/stock chain; holding locations; analysis horizon.

**Required behaviour:** Compose several station and junction objects into one temporal resource system. Expand the assessment boundary when queues or route choices have external effects.

**Guard/failure conditions:** Do not improve one station score by exporting delay or abandoning residual trains at the observation horizon.

**Requirements:** TOP-007, OPS-009, OPS-011. **Benchmarks:** B016, B031, B035 in [09](09_validation_benchmarks_and_roadmap.md).

## 3. Example full contract: selective grade separation

All values and IDs below describe a **synthetic contract**, not a UK standard or a measured real scheme.

```yaml
pattern_id: P21
pattern_version: 0.1.0
instance_id: synthetic_flying_junction_01
purpose: separate_branch_departure_from_opposing_through_flow
mandatory_movements:
  - branch_departure
  - main_through_forward
  - main_through_reverse
required_independent_pairs:
  - [branch_departure, main_through_reverse]
ports:
  - branch_departure_entry
  - branch_departure_exit
  - main_forward_entry
  - main_forward_exit
  - main_reverse_entry
  - main_reverse_exit
engineering_profile_ref: synthetic_geometry_profile_v1
train_profile_refs: [synthetic_short_emu, synthetic_long_passenger]
variables:
  - crossing_chainage
  - upper_route_choice
  - horizontal_alignment_family
  - approach_vertical_profiles
  - structure_envelope_choice
hard_constraints:
  - preserve_all_required_ports
  - stay_inside_authorised_site
  - satisfy_profile_geometry
  - maintain_required_swept_clearance
  - preserve_passenger_access_reservations
checks:
  - geometry_and_component_compatibility
  - full_envelope_clearance
  - complete_route_resource_independence
  - downstream_merge_and_queue_effect
  - train_performance
  - engine_representability
capabilities_required:
  - construction.track_alignment
  - construction.grade_separated_crossing
fallback_policy: propose_alternative_topology_without_committing
on_unknown_critical_rule: unassessed
on_search_budget_exhausted: search_exhausted
```

The profile contains actual numeric inputs only when their origin is declared. A pattern library should never use a plausible-looking bridge height or ramp slope to conceal an unresolved clearance or train-performance requirement.

## 4. Geometry lower bounds and early rejection

For a constant-gradient segment, a height change `delta_h` at maximum grade magnitude `q` requires at least `abs(delta_h)/q` horizontal distance. This is a lower bound before vertical transitions and other constraints, not a complete ramp design. Use it to reject impossible compact candidates cheaply, then solve the full profile.

For a platform bank, begin with required usable boarding intervals and access/civil reservations. The shortest fan in plan is not necessarily the best solution if it introduces unsuitable specialwork, excessive reverse curvature or long conflicting traversals.

## 5. Pattern admission and promotion

`proposed` means this document defines the contract. `implemented_synthetic` requires executable generation and benchmark evidence. `reference_calibrated` additionally requires appropriate dated source data. `game_validated` requires successful construction and observed operation on a named game/mod version. The v0.1/v0.2 full pattern records remained `proposed`. The v0.3 subassembly implementation scope is stated in section 9; no complete UK/game-validated family is implied.

## 6. Version 0.2: executable contracts for the first terminal families

The 32 family IDs remain stable. The new proof exercises **resource-template approximations** related to P01/P03; it does not instantiate their full engineering contracts.

### 6.1 Shared terminal inputs

A complete terminal generator takes approach ports with direction/system/position/heading, a site envelope, platform-road and boarding-edge requirements, train profiles, service groups, normal and recovery movement sets, permitted specialwork, passenger reservations and an engineering profile. Unknown component geometry is retained as unknown.

Outputs include the family/parameter record, all platform assignments that the topology permits, component inventory, engineered routes, resource compiler output, civil/passenger reservations, checks, search history and a candidate hash. A JSON list of track segments is not the whole output contract.

### 6.2 P01 — Grouped terminal banks, detailed generation procedure

Choose a platform partition compatible with the brief. Prefer contiguous groups as an initial search restriction where appropriate, but retain that restriction in the explored-scope record. Establish a distribution backbone for each bank and place candidate turnout components along it. The chosen turnout handedness follows actual connection geometry, not a language-model guess based on left/right labels.

Solve the component placements and interconnecting alignments jointly. Check the outermost routes and short inner connections as carefully as the longest route: the shortest connecting segment can be the limiting one for transitions. Return all route opportunities and their shared resources.

Normal independent groups must not share an exclusive synthetic throat resource merely for programming convenience. If the true geometry or operating protection does introduce sharing, record it and remove the independence claim.

**Parameters:** bank membership; approach-port allocation; backbone location; component family; minimum and preferred speeds by movement; optional recovery eligibility; platform offsets; boarding intervals; permitted footprint adjustment.

**Hard checks:** complete mandatory movements, component compatibility, platform fit, continuity, swept clearance, passenger reservation preservation and named independence requirements.

**Not implemented yet:** catalogued fan fitting, precise point count, train-speed profiles, whole-assembly envelopes and game lowering.

### 6.3 P03 — Split throats with bounded cross-access

Begin with accepted bank subassemblies, then identify the exact missing recovery movements. Generate links for those movements only, comparing upstream sorting, a cross-bank connection near the fan, or another allowed location.

A recovery route acquires every resource it physically traverses. Do not preserve a normal-route independence claim while silently adding a shared crossing into it. Conversely, the mere existence of a rarely used connection should not force unrelated normal movements to reserve it.

The proof's `linked` template conservatively claims both bank throats and a `cross_access` resource when crossing banks. This is a declared modelling assumption. A future geometry-derived compiler must calculate the actual set; it may be less or more restrictive depending on the layout and protection model.

**Recovery contract:** name the disruption, retained service set, operating restrictions, required access and allowed delay/footprint trade-off. Closing A-bank platforms while retaining A's approach is a different fixture from losing the A throat itself.

**Failure condition:** a new connection that permits arrival but not the required departure has not supplied the recovery movement.

### 6.4 Common distribution throat — comparison baseline

The proof's `common` family permits both service groups to use any fitting platform and places every throat movement on one exclusive resource. It is a deliberately restrictive baseline useful for validating conflict accounting.

This is **not** a universal statement that every real common ladder serialises all movements. A production common-throat pattern must derive its resource structure from its actual topology and geometry. Do not use the proof's result as evidence that independent banks are always the preferred real design.

A common arrangement may remain useful under a particular boundary, demand or permitted component set. It must be judged by the same hard constraints and scenarios as its alternatives.

## 7. Component contract refinements

### 7.1 Linked point ends

Add a `PointGroup` record with constituent end IDs, allowed state mapping, state evidence, and separate commanded/detected/physical observation fields. A partially observed group cannot be certified from one end alone. The dated Waterloo fragment demonstrates why this relationship belongs in the schema; see [04](04_london_termini_and_junctions.md).

The proof covers only normalised state-lock compatibility. It does not issue point commands or model detection circuitry. Production handling of state disagreement is an execution stop/reconciliation case, not an instruction to bypass a game or railway safety condition.

### 7.2 P07/P08 — Complete crossovers before bigger fans

For a single crossover, fix the two parent-track boundary conditions and enumerate compatible turnout pairs. Solve the connecting alignment between their defined ports, then validate both parent-route transitions and the connecting route as one assembly.

For paired crossovers, the spacing is a variable with operational meaning. It may or may not provide a usable holding interval for the selected train. The route compiler must check tail clearance and point/protection extents before claiming independent operation or a holding berth.

The analytic shift in `proof/railproof/geometry.py` is a numerical-test primitive only. It is neither P07 nor a substitute for two turnout components. A future P07 implementation must pass B010 with actual component geometry before being promoted.

### 7.3 P04/P31 — Platform geometry and stopping positions

Record platform-edge interval separately from track extent. A buffer end farther along the track does not add boarding length. A stopping target needs its own tolerance and train-door/formation assumptions where those interfaces are modelled.

A curved platform requires an evaluated train/platform interface and the relevant scoped rules, not merely a long enough centreline. For the first worked example, platform roads are proposed straight and stopping fit is checked against synthetic boarding intervals; the wider station fit remains pending.

### 7.4 P21/P22 — Grade separation remains a later generated family

Retain the grade-separation contracts and lower-bound checks from the catalogue. Do not promote them to implemented status because the offline scheduler supports crossing resources. Removing a conflict resource from a synthetic graph does not prove a flyover or diveunder can be built.

The admission gate requires the full level change, approach/transition geometry, envelope and structural reservations, plus post-crossing route feasibility. Civil fields without adequate evidence remain unassessed even after a geometrical fit.

## 8. Pattern assembly and search contracts

A production `instantiate()` call should return either a candidate assembly or a typed failure with its explored scope. It receives a bounded parameter domain, not an unrestricted prompt. A candidate stores which parameters Python changed and whether the change was pre-authorised.

Component composition requires compatible port roles, units, coordinate frames, heading, elevation, profile and allowed movement direction. After joining, rerun the checks that cross the component boundary. Two separately valid structures can still form an invalid combined throat.

A cache key must distinguish template identity from instance geometry and from dynamic schedule. Changing a platform label should not trigger a geometry solve; changing usable length, track position, train formation or component state mapping should invalidate the relevant checks.

### Initial search-order recommendation

For a terminal brief, test grouped and common families at coarse fidelity; fit the simplest legal components; assess normal operation; test mandatory disruptions; add bounded cross-access only where justified; then compare footprint, specialwork and passenger implications among geometrically valid alternatives.

This is a proposed default policy, not a proof of optimality. A tightly constrained historical site may justify another ordering. Astra can choose the high-level policy once; Python should not repeatedly ask for approval to move an individual insertion chainage within the authorised range.

## 9. Version 0.3 implementation matrix

| Contract | New implementation | Promotion boundary |
|---|---|---|
| P07 — Single crossover | Two authored eased components, tangent connector, all exposed legal routes, joint continuity/radius checks and compiled resources | `implemented_synthetic_subassembly`; no real S&C catalogue, dynamic clearance or game representation |
| P01 — Grouped terminal banks | A generated one-approach fan serving 2–8 roads; release demonstration uses four | Bank subassembly only; no multi-bank/four-approach station completion |
| P03 — Split throat/cross-access | Existing v0.2 hand-authored resource approximation retained | Actual cross-bank recovery geometry remains proposed |
| P04/P31 — Platform geometry/fit | Boarding intervals, rear-stop marker and storage resources for the synthetic fan | No complete platform edge, civil, passenger-access or buffer-stop design |
| P08–P10 — Paired crossovers/scissors/diamonds/slips | Explicit illegal-route tests prevent accidental substitute connections | Full generated assemblies not implemented |
| Grade separation families | Earlier contracts and bounds retained | No new generated flyover/diveunder in v0.3 |

The component parameters, family formulae, admission limits and partial promotion status are also recorded in [component_catalogue.json](evidence/component_catalogue.json). They are synthetic project definitions, not source-derived UK dimensions.

An assembly result must include explicit component ports and legal traversals, curve bounds, compiled route/resource provenance, stop/holding semantics and the actual unresolved domains. A successful synthetic subassembly cannot transfer its status to a scaled or combined station without fresh checks.

The detailed crossover and farthest-branch-first fan contracts are in [14](14_geometry_components_and_resource_compiler.md); actual dimensions and results are in [15](15_worked_geometry_examples.md).

## Version 0.4 pattern status: directional access is not an independent bank

The existing 32 pattern IDs remain stable. A new authored access subassembly supplies separate arrival/departure boundary roles around the four-road fan. It reuses the synthetic eased component family and retains a shared access turnout. This advances the building blocks of P01/P03 without completing the original grouped-bank or cross-recovery contracts.

Every pattern instance must now carry a numerical-profile admission result. A resolved UK nominal value cannot promote a synthetic turnout family. Actual component geometry, vehicle envelopes and applicability remain separate gates. The realistic-spacing proxy test is a required counterexample for future catalogue import. [17](17_uk_numerical_profiles.md)

Stopping and resource-footprint contracts are implemented for the restricted level-track bank. A larger station must recompile all shared resources, preserve explicit stopping space and prove required movement independence; it cannot inherit the four-road subassembly's pass status. [18](18_arrival_departure_and_sectional_occupation.md)

## Version 0.5 pattern status: vehicle and import prerequisites

No new pattern ID is added and no full family is promoted to authentic UK or game-validated status. P07's generated synthetic crossover now has an independent rigid-body clearance overlay. The through/crossing route distinctions are inspected using vehicle shapes, not only a constant centreline strip. The overlay is not a new interlocking control table.

P01/P03 bank composition can use the new vehicle/profile contracts. However, the demonstrated P4 scan is a single representative body on the existing shared bank, not a complete eight-platform network. Full formation, cant and dynamic gauging remain distinct gates.

The imported synthetic turnout demonstrates that future admitted catalogue geometry can be supplied as data and reach the resource compiler. This does not create an authentic UK component from the existing synthetic curve. The pending real-source record is kept separate and has no manufactured dimensions.

Before any new dense station instance is promoted, report the vehicle and component source profiles, all body/pivot assumptions, the interpreted clearance domain, source/geometry versions, route movement contract, curve-approximation status and engine capabilities. A template inherits none of these checks automatically from a superficially similar previous instance.

## Version 0.6 pattern status: composed banks and selective recovery

P01/P03 now have an implemented **synthetic composition subset**: two four-road banks, explicit arrival/departure boundaries, normal bank-specific routes and an optional one-direction recovery cycle. The cross-bank link uses two rigidly placed instances of the imported authored record. It supplies A-in → B-berth → A-out or the converse, not both in one instance. [23](23_two_bank_station_composition.md)

This does not promote the complete P01/P03 contracts to reference-calibrated or game-validated status. The generated family fails the original footprint; full platform interfaces, vehicles, actual pointwork and operating protection remain unresolved. The parameterised rules and admission stages defined earlier remain in force.

P07/P08 contribute a complete connection pattern to the station rather than an isolated demonstration. Their section boundaries are explicitly matched to the isolated comparison. Recovery geometry acquires all the receiving-bank and component resources it uses; a rarely used link does not automatically force unrelated normal routes to acquire each other's bank.

P04/P31 now retain four 260 m and four 320 m boarding intervals in the composed example. Short intervals move real stopping markers and storage geometry as well as scalar fit fields. These are retained project-brief dimensions, not a national platform-length rule.

The next composition search should examine earlier approach sorting, adjacent-track crossover placement, paired links or another fan grammar to meet both site and resilience requirements. It must return its explored parameter/family scope. Adding another arbitrary edge or renaming a point cannot provide an unmodelled movement.

## Version 0.7 — Compact inner-road recovery and scissors subset

P01/P03 now have an additional fixed-original-plan, outward-facing two-bank instance. P09/P10 gain an **implemented synthetic subset**: a scissors assembled from four rigid placements of the existing authored component, with two connector paths and one declared fixed diamond. This is not promotion of the whole pattern to reference-calibrated or game-validated status.

The contract explicitly lists A-in → B1 → A-out and B-in → A4 → B-out. Other cross-bank berths remain unreachable. Failure scope is platform-bank closure with the associated fan and approach available. A failed fan, receiving inner berth, forbidden recovery policy or incompatible formation invalidates the affected opportunity.

The domain uses a finite first-toe/span/toe-step grid, while site positions and the imported crossover component stay fixed. The 300 m radius target remains hard. Whole-network compilation, complete-visit checks and candidate-bound vehicle/numerical assessments are rerun after composition. See [26](26_compact_site_and_recovery_design.md) and [27](27_compact_station_results.md).

Hardware envelopes, real crossing geometry, permitted speed, track-circuit/protection boundaries, platform islands and full gauging remain outside this synthetic subset. A future authentic component may invalidate this compact fit; the design must then be repaired or rejected rather than silently distorted.


## Version 0.8 — Platform slab and facility subcontracts

The platform-interface portion of the catalogue now has an implemented straight, level paired-island reservation. It consumes actual boarding roads/intervals, source-qualified rail-edge offsets and height, separate permissible speeds and a declared measurement datum. It does not move the existing track or convert track length to boarding length.

The local facility subpattern has fixed width/length and a permitted centre-position interval. An exact interval solve either places that footprint while retaining both edge clearances, reports a fixed-section width deficit, reports lack of authority, or remains unassessed. See [30](30_platform_refit_and_component_evidence.md). The higher-level complete platform/access contracts remain proposed.

Primary-study component quantities now have typed acquisition records. A crossing ratio is not treated as a component-exit slope, and a moving switch beam is not treated as the complete turnout envelope. No authentic complete turnout/diamond pattern is promoted in v0.8.


## Version 0.9 — Corridor primitives and partial crossing-family admission

The existing 32 family IDs remain stable. A new runnable corridor composition uses smooth polynomial spans, true normal-offset track pairs and project-selected civil treatment. It is a restricted reference-inspired study family, not an authentic turnout catalogue or a universal railway alignment generator.

P21/P22's grade-separation work now has **implemented synthetic crossing subcells** with both ramps, a level crossing plateau, explicit approach boundary positions and a whole-crossing vertical-budget check. Do not promote the full families to implemented connected junctions: their branch switching, approach routing, merge and complete civil/vehicle envelope remain outside this increment.

Civil modes such as river bridge, tunnel or viaduct are planning labels tied to surveyed-or-synthetic terrain provenance. A tunnel label does not instantiate portals; a bridge label does not demonstrate a valid span/support asset. The game-facing resolver must bind a constructible asset or return an unsupported/unknown result.

Pattern output now also needs explicit open ports, missing required connections and engine capability dependencies. A lowered corridor cannot claim to include a branch merely because a separate crossing cell was plotted against the same datum. [32](32_corridors_junctions_and_game_fit.md), [33](33_worked_corridor_and_adapter_results.md)

## v0.10 addendum — selective branch separation with a retained merge

The new local pattern combines divergence, a two-track branch interface, a return crossing and a shared downstream merge. Its mandatory movement contract is main east, main west, branch outbound and branch inbound. Flat, raised and lowered return variants preserve that graph and its exact component identities. [Connected pattern](35_connected_passenger_branch_junctions.md)

The implemented pattern is **reference-inspired local geometry using authored components**, not a promoted authentic UK turnout/flying-junction product or a completed real-terrain corridor. Its spread-track footprint is deliberate and remains to be placed against an actual terrain snapshot.

Pattern outputs include legal route inventory, complete vertical approach lengths, crossing-footprint separation, merge resources, explicit geometric holding checks and unresolved terrain/gauge/structure fields. A no-delay crossing experiment does not satisfy a no-delay merge requirement. The tested counterexample remains part of admission.

The search explores 17 declared ramp/mode/height combinations; five pass the scoped screens. It does not exhaust junction topology or minimise national-network cost. Wider parameter families require new interface and clearance checks, rather than stretching the fixed imported component.


## v0.11 — Placed branch pattern admission

A branch pattern may carry four complete movements yet still fail its actual site. Its new admission sequence is boundary preservation, rigid component placement, plain-line refit, per-route profile checks, all-edge terrain/protected-land screening and combined operating evaluation. [38](38_terrain_aware_junction_placement.md) demonstrates the restricted family. No whole pattern family is promoted to authentic UK or game-validated status.

Keep primitive placement, terrain-qualified design, actual structure selection and live construction as distinct stages. The synthetic support gate for pointwork over structures is a missing component/asset integration, not a national prohibition. A conservative reservation intersection is distinct from a physical track-centre witness.
