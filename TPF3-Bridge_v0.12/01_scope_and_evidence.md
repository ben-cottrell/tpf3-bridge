# Scope, evidence and architectural decisions

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

Version **0.2.0** · 20 September 2026 · Status: **proposed specification and initial research baseline**

## 1. Product objective

Build a passenger-focused UK railway engineering layer for the TPF3 Bridge. Astra supplies the design brief and resolves meaningful trade-offs. Python generates and evaluates railway layouts, performs local simulation and bounded repair, and returns compact evidence-backed decisions. A proposed Lua game adapter exposes authoritative game state and supported operations. The adapter language and API details must be confirmed against actual TPF3 modding interfaces.

The user’s operating assumption is full sandbox mode with all assets unlocked. Construction cost may remain a proxy for land take, civil complexity or visual restraint, but commercial profitability and tycoon management are not primary objectives. Freight remains a compatibility and interference class rather than the organising theme of this release.

### Baseline success condition

A user can request a large passenger station and its connecting corridor by function, service pattern and character. Python produces a buildable, explainable candidate without asking Astra to place every turnout or repeatedly repair spline geometry. The result has separate engineering, operating-model and game-validation statuses.

## 2. Ownership boundary

| Responsibility | Astra | Python | Game adapter |
|---|---|---|---|
| Purpose, era, service priorities, site boundary | Decides | Normalises and checks completeness | Reports actual site/assets |
| Topology, track order, platform grouping | Chooses material alternatives | Generates and evaluates candidates | Confirms representability |
| Curves, turnouts, vertical profiles, clearances | Approves exceptional compromises | Solves and validates | Builds supported primitives |
| Platform allocation and local service simulation | Sets policy | Executes locally | Provides measured game behaviour |
| Routine repair | Receives summary only | Owns bounded search | Returns authoritative errors |
| Change to brief or irreversible scope expansion | Approves | Explains alternatives | Executes only authorised scope |
| Evidence and uncertainty | Sees decisions and material gaps | Stores full lineage and unknowns | Reports telemetry coverage |

## 3. In scope for the passenger core

The first implementation should cover through stations, large termini, mixed through/terminal layouts, multi-level complexes, corridor interchange stations, turnbacks, bays, connecting junctions, selective grade separation, empty coaching stock movements and simple servicing/stabling interfaces.

Design is operational before it is decorative. Platform allocation, approach queues, conflicting routes, turnrounds, train lengths, passenger interchange and accessible circulation are part of the station problem. Buildings and canopy placement must not consume space already required for track/vehicle clearance or passenger movement.

Out of scope for initial certification: real-world railway approval, structural member design, signalling safety certification, fire-engineering certification, geotechnical design and exact reconstruction of every named station. The bridge can provide approximate feasibility indicators in these areas but must not label them certified designs.

## 4. Profiles instead of universal “UK rules”

Start with `gb_conventional_passenger_modern`. Add separate `gb_mixed_traffic`, `gb_historical_reference` and `game_compressed` profiles. Do not silently apply these to high-speed, metro or Northern Ireland infrastructure.

A profile references applicable source issues, train classes, geometry constraints, electrification, operating assumptions, era and explicit compromises. An aesthetic historical preference is not a safety requirement. An existing constrained layout is not automatically an acceptable new-build template.

The current public RSSB catalogue identifies relevant platform, track and clearance documents, but complete clause-level extraction has not been performed. This release intentionally contains no invented universal UK platform length, turnout speed, minimum curve radius, maximum gradient or junction headway. See [S043–S047](10_source_register.md#s043).

## 5. Evidence types

| Level | Meaning | Permitted use |
|---|---|---|
| R0 | Source identified but not inspected | Acquisition queue only |
| R1 | Primary descriptive record or wayfinding plan reviewed | Labels, context, passenger connections and documented features |
| R2 | Relevant project engineering or operational assessment reviewed | Documented constraints, scheme purpose and bounded design lessons |
| R3 | Dated technical topology, applicable rules and adequate geometry acquired | Site-specific reconstruction input, with uncertainty fields |
| R4 | Imported instance checked against evidence and measured game output | Validated game reference for its declared scope |

No station in this release is claimed to be R3/R4 across its entire approach and throat. Evidence depth is per feature, not an all-or-nothing badge for a station. Birmingham has stronger operational evidence than most current station maps, but still lacks a complete imported interlocking route table.

Claims must carry `source_id`, locator, valid period, asset scope, assertion type, confidence and review state. Numerical fields require units and origin. A value estimated from an image must be marked estimated, not measured.

## 6. Baseline architectural decisions

**ADR-001 — Canonical engineering model.** Design topology, alignment and operations in Python independently of engine spline representation. Lower into game primitives through an adapter and revalidate the realised result.

**ADR-002 — Separate graphs.** Maintain rail connectivity, legal routes/resource locking, train/stock activities and passenger circulation as related but distinct models. Crossing in plan, sharing a station name or sharing a pedestrian bridge does not create a train connection.

**ADR-003 — Time-dependent capacity.** Evaluate complete arrival–berth–departure opportunities rather than count empty platforms. This responds to the access-conflict issue identified in the Birmingham assessment; see [case study](03_birmingham_new_street.md).

**ADR-004 — Versioned physical identity.** Display labels are aliases, not database keys. A platform can be renumbered without changing its physical identity; a label can also refer to different physical layouts at different dates.

**ADR-005 — Functional patterns.** A pattern specifies legal movements and required independent operations as well as geometry. Scaling or mirroring triggers fresh engineering, operating and game checks.

**ADR-006 — Bounded autonomy.** Python may vary parameters and repair within the approved brief. It may not relax a hard constraint, change service priorities or enlarge land take beyond authorisation merely to obtain a successful build.

**ADR-007 — Honest outcomes.** Distinguish `pass`, `fail`, `unassessed`, `not_applicable` and `not_representable`. Distinguish proof of infeasibility from exhausted search budget.

**ADR-008 — Two operating models.** Keep the UK-inspired railway shadow model separate from the game-calibrated reservation/routing model. Official published TPF3 features do not demonstrate the API needed to control or inspect them. [S001](10_source_register.md#s001)

**ADR-009 — Passenger functionality before decoration.** Reserve accessible paths, vertical circulation and waiting space during layout generation. Use simplified passenger models first, with an optional detailed model later.

**ADR-010 — Compact feedback with retrievable detail.** Astra receives decision packets, not raw event streams. Python retains exact diagnostics, source versions, search history and reproducible simulation artifacts.

## 7. Terminology contract

| Term | Meaning in this bridge |
|---|---|
| Station complex | Passenger interchange entity that can contain several rail systems/levels |
| Platform road | Track interval alongside one or more passenger stopping positions |
| Platform edge | Physical boarding boundary with geometric identity |
| Platform label | Passenger-facing name or number, potentially date-dependent |
| Berth | A permitted train stopping interval/configuration; not automatically independent |
| Platform section | A label/operating subdivision whose physical and signalling constraints must be explicit |
| Throat | Track/route assembly that distributes movements between approaches and platform roads |
| Route | A permitted movement with geometry, point requirements and temporal resource use |
| Fouling envelope | Space/resources that another movement must not intrude upon under the selected model |
| Turnround | Arrival-to-next-departure process, including readiness and stock dependencies |
| Independent movements | Movements demonstrated to be simultaneously compatible under the selected resource model |
| Capacity | A result conditional on service mix, timetable, controls, disturbances and model scope |

These are software modelling definitions. Formal railway terms and protection requirements must be reconciled against applicable sources before use in a compliance-oriented profile.

## 8. Research-to-code admission gate

A fact can enter a reference note at R1. A hard solver rule needs a verified clause or an explicitly user-approved synthetic constraint. An exact station prefab needs R3 geometry/topology and a capability-qualified game translation. A benchmark based only on design lessons must be named `synthetic_*_inspired`, never `as_built_*`.

The release gate should reject unsupported claims even when the resulting picture looks convincing. The evidence gaps are enumerated in [the research backlog](11_research_backlog.md).

## 10. Version 0.2 implementation boundary

The product goal remains generation and construction of passenger railways. The new `proof/` directory is a **small executable experiment**, not the production implementation of the source tree described above. It accepts predefined platform inventories and resource-template families, schedules complete visits, retains conflicts and dispositions, checks selected invariants, and demonstrates one analytic alignment primitive and two narrowly scoped clause evaluators.

This separation is intentional: a testable operating model helps specify what the future geometry generator must supply. It does not establish that a resource template has a physically realisable track arrangement. No candidate in this release is authorised for construction.

Three independent labels are now required on every release result:

| Dimension | Examples | Meaning |
|---|---|---|
| Evidence origin | `synthetic`, `historical_technical_fragment`, `measured_game` | Where its inputs came from |
| Implemented fidelity | `resource_templates`, `engineered_geometry`, `game_observed` | What the implementation actually evaluated |
| Assessment outcome | `pass`, `fail`, `unassessed`, `not_applicable` | Result for a named criterion within that fidelity |

The same record may have synthetic traffic, a documented historical point-group identity, unmeasured geometry and an unassessed game representation. A single overall “verified” flag would lose these distinctions.

**ADR-011 — Complete visits before global sophistication.** The first running proof uses a deterministic greedy complete-visit scheduler. It does not claim global optimality, microscopic train dynamics or full network simulation. A later solver may replace its scheduling strategy while preserving its input/output and invariant tests.

**ADR-012 — Evidence-derived topology is not automatically measured geometry.** A dated technical diagram can supply a port name or linked point-end relationship without supplying radius, chainage or every permitted route. Such a fragment does not promote an entire station to R3.

**ADR-013 — Explicit unresolved geometry.** Operating results derived from hand-authored resource templates carry `throat_geometry: unassessed`. They cannot enter the game execution state machine as approved build plans.

**ADR-014 — Clause checks are individually scoped.** Two numerical evaluators have been added from S058, with applicability and missing-input tests. They do not complete the RSSB imports, the project applicability review or the UK engineering profile. The source/condition/value lineage is in [the rule records](evidence/rules.json).

**ADR-015 — Recovery has a named failure case.** A connection receives credit for recovery only against a specified disruption and retained demand. The closure of platform roads is distinct from closure of the approach throat used to reach them.

No claims are made about Codex, Work or Chat plan entitlements. The delivered proof is ordinary local Python code and the attached result files record the execution performed in this conversation's runtime.


## Version 0.9 — Scope pivot authorised by the user

Detailed station internals are frozen at the v0.8 level. Earlier suggestions to implement increasingly detailed access, lifts, passenger circulation and facility models are superseded as the main workstream. Preserve practical platform lengths, track/boarding compatibility, game passenger connectivity and station boundary contracts; do not require full specialist station simulation for ordinary corridor design.

The default intended product mode is **GB reference-inspired, game-oriented design**. Source-qualified numerical requirements and representative UK practice still matter, but absent certification-grade data must be exposed as an approximation or unresolved domain rather than automatically blocking every useful preview. Engine construction failures, required connectivity, authorised boundaries and known hard physical conflicts cannot be ignored under that mode. Strict research/assurance profiles remain separate.

The next unit of useful work is a railway corridor with terrain, structures and consequential junctions. A source-informed design, a mock-constructed result and a real-game observation have separate states. The user has not authorised an actual game edit by approving this documentation/proof release. [32](32_corridors_junctions_and_game_fit.md)
