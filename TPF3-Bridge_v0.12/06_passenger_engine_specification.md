# Passenger railway engineering core specification

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Current integration:** v0.6 addendum at the end of this document; earlier sections retain their version-specific status. Current execution evidence is in [25](25_v06_execution_report.md).

> **v0.3 implementation note:** requirements remain production targets. Sections explicitly labelled v0.2 describe that historical proof. The current planar geometry/resource implementation is scoped in section 19 and [14–16](14_geometry_components_and_resource_compiler.md).

Version **0.3.0** · 20 September 2026 · **75 proposed requirements**

`SHALL` denotes a requirement on the proposed software, not a statement of a UK statutory or railway-standard obligation. The full requirements remain acceptance targets. A deliberately restricted offline proof now implements and tests selected behaviours; its coverage and omissions are recorded in [13](13_offline_proof_and_results.md). External engineering rules must pass the evidence gate in [01](01_scope_and_evidence.md).

## 1. System decomposition

The core should expose six cooperating services:

**Brief compiler:** resolves design intent into a typed, versioned contract with hard constraints, preferences, defaults, uncertainties and escalation permissions.

**World and evidence model:** maintains physical assets, source-backed claims, terrain, operating profiles, capabilities and stable identity across game rebuilds.

**Topology and geometry planner:** generates functional arrangements, solves continuous alignments and civil envelopes, and validates complete component assemblies.

**Passenger railway simulator:** evaluates train movements, routes, stock cycles, berths, queues and passenger interchange under declared scenarios.

**Optimiser and local repair controller:** performs bounded search, caches reusable results, compares alternatives and identifies the minimal material decision required from Astra.

**Execution and observation controller:** stages supported game operations, reconciles the realised result and compares observed behaviour with predicted behaviour.

The proposed source tree is `protocol/`, `world/`, `evidence/`, `planning/`, `geometry/`, `operations/`, `passengers/`, `execution/`, `analytics/`, `storage/`, `tests/`, `fixtures/` and `replay/`. This is a responsibility map, not a mandated dependency framework.

## 2. Brief and scope requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| BRF-001 | The compiler SHALL retain the user's site boundary, station function, era/profile, service priorities and requested operating capabilities as a versioned brief. | Round-trip serialisation preserves all explicit choices. |
| BRF-002 | It SHALL distinguish hard constraints, preferences, inferred defaults and unknowns. | A missing maximum gradient cannot become an unmarked hard-coded UK value. |
| BRF-003 | It SHALL define which changes Python may make autonomously and which require approval. | A local repair cannot enlarge the site or reduce a required service without escalation. |
| BRF-004 | It SHALL distinguish reconstruction, reference-inspired generation and wholly synthetic design. | Every output and benchmark carries its mode and evidence scope. |

## 3. Physical and temporal data requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| DAT-001 | The model SHALL separate station complex, rail subsystem, level, platform road, platform edge, berth and passenger label. | Glasgow/Willesden-inspired fixtures cannot form a false common rail throat. |
| DAT-002 | Physical asset IDs SHALL be independent of labels and engine entity IDs. | Renumbering and game rebuilds preserve traceable identity. |
| DAT-003 | Berths SHALL use explicit usable intervals, train-fit constraints and permitted occupation configurations. | A full-length train invalidates conflicting split-berth allocations. |
| DAT-004 | Rail connections SHALL use typed ports and permitted connectivity, not coordinate coincidence. | A diamond has no invented turning route; separated levels stay separate. |
| DAT-005 | The model SHALL retain direction permissions, operating role, system and traction/gauge compatibility independently. | A geometrically reachable but incompatible platform is rejected. |
| DAT-006 | Terrain, structures, track geometry and passenger circulation SHALL share a declared coordinate transform and units. | Round-trip conversion meets a profile-defined numerical tolerance. |
| DAT-007 | Every infrastructure snapshot SHALL have a coherent version and declared valid period. | Old pointwork cannot be silently combined with future signalling. |
| DAT-008 | Observations SHALL carry timestamps, snapshot IDs, coverage and quality status. | Missing telemetry remains unknown rather than interpreted as no trains. |

## 4. Topology and throat requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| TOP-001 | The planner SHALL derive a required movement/eligibility matrix before fitting geometry. | Every mandatory movement has a legal candidate or a specific failure. |
| TOP-002 | It SHALL support nonuniform platform roles and asymmetric approaches. | A mixed through/bay fixture is not forced into a mirrored fan. |
| TOP-003 | It SHALL generate grouped ladders and bounded cross-group access as alternatives to universal connectivity. | Alternatives have explicit movement differences and conflict witnesses. |
| TOP-004 | Through-service candidates SHALL include both arrival and departure feasibility. | A reachable platform with an impossible exit is rejected. |
| TOP-005 | Turning and empty-stock movements SHALL be part of the topology requirement when requested. | A passenger-only path count cannot hide an impossible next working. |
| TOP-006 | Grade separation SHALL name the movement conflict being removed and include downstream interfaces. | A relieved crossing is not reported as solved when its queue moves to the next merge. |
| TOP-007 | The model boundary SHALL include consequential junctions and extend or flag itself when queues reach the boundary. | Externalised delay is visible in candidate comparisons. |
| TOP-008 | Independent movements SHALL be demonstrated using resource compatibility, not visual separation alone. | A point/protection conflict can invalidate non-overlapping drawn paths. |

## 5. Geometry and infrastructure requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| GEO-001 | The geometry kernel SHALL store plan alignment, vertical profile, curvature and cant separately from engine splines. | Engineering quantities survive export/import within stated tolerance. |
| GEO-002 | Connections SHALL enforce the appropriate position, heading, curvature and grade boundary conditions. | The validator reports the location and magnitude of each discontinuity. |
| GEO-003 | Turnouts and crossings SHALL be catalogue components with complete route geometry and applicability metadata. | A crossing angle alone cannot establish a route speed. |
| GEO-004 | Crossovers, scissors and throat ladders SHALL be solved and checked as complete assemblies. | Individually valid points cannot conceal an invalid connecting reverse curve. |
| GEO-005 | Horizontal, vertical and cant constraints SHALL be checked jointly for the selected train/profile set. | A combined-geometry violation is detected despite valid isolated subchecks. |
| GEO-006 | Vehicle clearance SHALL use a declared swept-envelope model and include structures, adjacent tracks and platform interfaces. | A centreline-only clearance pass cannot override an envelope collision. |
| GEO-007 | Platform fitting SHALL distinguish boarding length, track extent, stopping tolerance and any permitted selective-door policy. | A nominally long track cannot count as an adequately long boarding platform. |
| GEO-008 | Flyover/diveunder design SHALL include approach ramps, vertical transitions, structure depth, crossing envelope and terrain/civil reservations. | A clear crossing centre cannot hide an approach or full-envelope conflict. |
| GEO-009 | Passenger structures and access space SHALL be reserved during rail/civil generation. | A pier or ladder cannot silently remove the only permitted passenger path. |
| GEO-010 | Compression, mirroring or engine snapping SHALL trigger relevant revalidation. | A scaled reference is not accepted solely because its unscaled parent passed. |

## 6. Train and railway operation requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| OPS-001 | Services SHALL carry train length, performance profile, route eligibility and stopping pattern. | Performance and fit are not inferred from one generic train. |
| OPS-002 | A platform allocation SHALL include arrival route, berth interval, readiness and onward route/activity. | An occupied or inaccessible exit causes an explicit infeasibility result. |
| OPS-003 | Temporal resources SHALL cover running sections, point requirements, crossing zones and modelled protection. | Every conflict explanation names the incompatible requirements. |
| OPS-004 | Release SHALL account for train tail position and the selected route-release model. | The crossing stays unavailable until its relevant release condition holds. |
| OPS-005 | Dwell, dispatch and turnround SHALL be separate activities with applicable scenario/profile parameters. | A terminating train cannot depart using only a through-stop dwell. |
| OPS-006 | Rolling-stock dependencies and empty-stock moves SHALL be represented when enabled. | Delayed incoming stock propagates to its next working unless an explicit substitute exists. |
| OPS-007 | Reversal, permissive occupation, coupling and splitting SHALL require explicit profile and engine support. | Unsupported behaviours are not achieved by teleportation or duplicate train identities. |
| OPS-008 | Approach holding positions SHALL have usable length, stopping and release constraints. | An overlength waiting train is not treated as clear of the upstream resource. |
| OPS-009 | The simulator SHALL model queues and blocking across connected stations/junctions. | A downstream dwell perturbation can block an upstream resource. |
| OPS-010 | Scenario runs SHALL be reproducible using immutable inputs, seeds and model versions. | Replay produces the same deterministic event sequence for a fixed configuration. |
| OPS-011 | Performance reports SHALL state warm-up, observation horizon, residual queues and completed/cancelled work. | A short horizon cannot hide unfinished trains or delayed spillback. |
| OPS-012 | UK-inspired and game-calibrated operating models SHALL remain distinguishable. | A game reservation discrepancy is reported without rewriting the engineering assessment. |

## 7. Passenger and station design requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| PAX-001 | The system SHALL maintain a passenger graph separate from rail connectivity. | A pedestrian interchange cannot create a train route. |
| PAX-002 | Passenger demand SHALL support station entry/exit and service-to-service transfers by time period. | Simultaneous arrivals generate the correct modelled transfer demand. |
| PAX-003 | Walking, waiting, queues and vertical travel SHALL use declared capacities/behaviour profiles, not unlimited instantaneous links. | A constrained connection can become the passenger bottleneck. |
| PAX-004 | Accessible paths SHALL be evaluated independently from unrestricted shortest paths. | Lift failure cannot be “solved” by directing the accessible cohort up stairs. |
| PAX-005 | Platform usable area SHALL exclude reserved edge zones, structures, furniture and circulation obstacles as specified by the selected profile. | Gross area cannot conceal a local pinch point. |
| PAX-006 | Platform reassignment SHALL include announcement/redirection and transfer consequences where the passenger model is enabled. | A late cross-group change has an explicit modelled cost or unassessed flag. |
| PAX-007 | Boarding/alighting and dwell coupling SHALL use calibrated or clearly synthetic assumptions. | Unknown door/boarding behaviour is not presented as measured station performance. |
| PAX-008 | Normal, disturbed and reduced-access scenarios SHALL be reported separately; emergency analysis SHALL not imply certification. | Lift loss, crowd surge and closure scenarios retain their distinct validity status. |

## 8. Optimisation and autonomy requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| OPT-001 | Search SHALL apply hard feasibility checks before preference scoring. | An attractive infeasible candidate cannot beat a feasible one through weighted averaging. |
| OPT-002 | The planner SHALL compare materially different topology families before expensive detailed fitting. | Search does not spend its full budget varying one fundamentally unsuitable fan. |
| OPT-003 | Results SHALL be cached using all correctness-relevant versions and assumptions. | A changed train length, rule issue or capability invalidates affected results. |
| OPT-004 | Local repair SHALL have explicit time/evaluation/attempt budgets and preserve the brief. | Budget exhaustion returns a bounded-search result, not a false impossibility proof. |
| OPT-005 | Candidate evaluation SHALL include disturbances and expose important sensitivity. | A nominal-only success is not labelled robust operation. |
| OPT-006 | The decision packet SHALL contain a small nondominated set, material trade-offs and an approval question only where needed. | Routine spline retries never become separate Astra decision requests. |

## 9. Game execution requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| EXE-001 | A capability manifest SHALL distinguish supported, unsupported and unknown operations, with evidence. | A published feature is not treated as a tested callable API. |
| EXE-002 | Design output SHALL compile into capability-qualified operations without inventing engine functions. | Unsupported specialwork has an explicit rejection or declared alternative. |
| EXE-003 | Each plan SHALL bind to a world version and authorised edit region. | A stale world or out-of-scope edit aborts or requires revalidation. |
| EXE-004 | Execution SHALL use staged validation and checkpoints appropriate to actual engine facilities. | The system makes no atomic transaction/rollback promise without demonstrated support. |
| EXE-005 | Operation IDs and acknowledgements SHALL support reconciliation after timeout/reconnect. | Retrying an uncertain acknowledgement cannot duplicate construction silently. |
| EXE-006 | The adapter SHALL report realised assets and mappings back to canonical IDs. | Engine snapping/resegmentation is discoverable and measurable. |
| EXE-007 | Realised geometry, connectivity and required routes SHALL be checked after construction. | Accepted commands alone cannot establish a successful design. |
| EXE-008 | Partial failure SHALL preserve a recovery record and stop unsafe automatic continuation. | A compensation action is labelled compensation, not guaranteed rollback. |

## 10. Observation and usage requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| OBS-001 | Full traces SHALL remain local and queryable by stable result references. | Astra can drill into a decision without receiving the entire event log by default. |
| OBS-002 | Reports SHALL identify bottleneck resources, scenarios, evidence gaps and rejected required movements. | “Station congested” alone is not an adequate failure explanation. |
| OBS-003 | Model calibration SHALL compare predicted and observed metrics with uncertainty and coverage. | A poor or unobservable fit prevents a calibrated-capacity claim. |
| OBS-004 | Change-driven observations SHALL support region/time summaries and bounded event digests. | No continuous full-world polling stream is sent to Astra unnecessarily. |
| OBS-005 | Usage experiments SHALL record model interactions, tokens/observations where available, and actual credits only when measured. | Wall-clock time is not converted into an invented plan-credit saving. |
| OBS-006 | Every result SHALL distinguish planned, simulated, constructed and observed status. | A prospective benefit cannot appear as an achieved result. |

## 11. Evidence and assurance requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| EVD-001 | Executable rules SHALL retain source, issue, clause/locator, applicability, units and review status. | An unverified catalogue synopsis cannot become a hard numerical standard. |
| EVD-002 | Missing applicable evidence SHALL produce `unassessed`, not `pass`. | The report can pass a synthetic game check while retaining an unassessed UK check. |
| EVD-003 | Conflicting claims SHALL remain visible until resolved by scope/date/evidence. | Bristol/Lime Street-style inventory conflicts are not silently averaged. |
| EVD-004 | Reference geometry SHALL identify measured, schematic, estimated and synthetic origins. | A passenger map cannot silently become surveyed metre coordinates. |
| EVD-005 | Reference-inspired tests SHALL state their synthetic status and avoid real-site capacity claims. | The benchmark name, report and exported artifact agree on fidelity. |

## 12. Proposed mathematical and algorithmic core

### 12.1 Canonical alignment

Use horizontal chainage `s` in metres, plan coordinates `x(s), y(s)`, vertical profile `z(s)`, heading `theta(s)`, plan curvature `kappa(s)`, gradient `dz/ds` and cant in declared units. Grade is stored as a dimensionless fraction; a displayed “1 in N” is a formatting conversion, not another internal unit.

Straight, arc and transition primitives should coexist with validated turnout/crossing components. Smoothness requirements depend on the component and profile; do not impose an inappropriate free-form smoothing pass that distorts catalogue specialwork.

Boundary conditions include position, heading, elevation, grade, curvature/cant compatibility and permitted connection direction. For a multi-track throat, solve the whole set with clearance/spacing constraints rather than independently fit every curve and hope they coexist.

### 12.2 Joint layout formulation

Let `K_i` be the permitted complete movement opportunities for train activity `i`. Each opportunity contains an arrival route, berth configuration and onward activity/route. Choose binary assignment `x_ik` with:

\[
\sum_{k\in K_i}x_{ik}=1
\]

for each required activity. Optional activities require explicit selection/cancellation penalties and must not disappear without being reported.

An opportunity claims resource intervals `I_ikq`. Mutually exclusive requirements on resource `q` cannot overlap. Resource-state compatibility handles cases where several routes require the same point position; occupying the same running space can remain exclusive even when point requirements agree. Capacity-limited passenger resources use a different rule from binary train-route resources.

Add stock-chain constraints such as:

\[
t_{departure,j}\ge t_{arrival,i}+T_{ready}(i,j)
\]

where `T_ready` is a scenario/profile function, not a universal UK constant. Include travel time for any stock movement between berths or servicing locations.

A macro/micro decomposition is a reasonable architecture to investigate; the referenced platforming paper is methodological support, not a ready-made UK or TPF3 solver. [S050](10_source_register.md#s050)

### 12.3 Evaluation order

First reject structural/topological impossibilities. Then reject geometry/train-compatibility failures. Then test nominal operating feasibility. Only surviving candidates receive expensive disturbed-operation and passenger evaluation. Finally lower to the engine and validate the realised layout.

Use optimistic bounds to prune, but label their assumptions. An early feasibility bound may establish impossibility only within its actual mathematical scope. A heuristic that finds no candidate does not prove impossibility.

### 12.4 Objective and trade-offs

After hard feasibility, evaluate a vector of passenger delay, missed connections, train delay, residual queues, land/civil footprint, specialwork complexity, recovery capability and declared aesthetic penalties. Do not combine seconds, square metres and counts using arbitrary unnormalised weights.

Prefer a small Pareto set for Astra. A suggested default preference is: preserve required movements and access; reduce conflict/queue exposure; preserve recovery; reduce footprint/complexity; then refine appearance. The user can choose another explicit ordering.

### 12.5 Passenger model progression

Start with a time-dependent node/edge queue model. Add train-specific arrival pulses, boarding zones and transfer demand. Later introduce spatial detail only where aggregate links conceal local pinch points. Couple dwell to boarding/alighting only with declared parameters and avoid double-counting passenger waiting both inside and outside the train event.

Network Rail's capacity guidance treats passenger movement, usable station space, validation and reporting as related assessment tasks. Its vertical-circulation manual separately addresses spatial planning and circulation elements. These support the domain split; this specification does not claim full numerical implementation of either manual. [S040](10_source_register.md#s040), [S041](10_source_register.md#s041)

### 12.6 Performance and replay

Cache route geometry, resource footprints and train-class traversal profiles. Recompute dirty subgraphs when a local asset changes. Use a staged fidelity ladder: fast structural rejection, approximate geometry, detailed local fitting, nominal discrete-event simulation, disturbed ensembles, and selective game validation.

A replay bundle must contain brief, snapshot, source/rule/capability versions, solver configuration, seeds, candidate decisions and execution observations. The same cache must not be reused across changed game geometry, changed train length or changed rule applicability.

## 13. Acceptance boundary

The first engineering-core release can be useful with synthetic rules and incomplete TPF3 integration. Its outputs must say exactly that. It is not acceptable to achieve apparent completeness by guessing UK numerical limits, inventing missing game APIs, or converting station maps into purportedly exact track plans.

Implementation sequence and test fixtures are defined in [09](09_validation_benchmarks_and_roadmap.md); proposed messages and ownership are in [08](08_data_contracts_and_orchestration.md).

## 14. Version 0.2: the station-design algorithm

This section refines existing requirements rather than adding a competing numbering scheme. It specifies the intended production algorithm. The implementation status of each stage is stated explicitly.

### 14.1 Four contracts between planning stages

A station candidate passes through four different contracts:

**Movement contract:** the required entry–activity–exit combinations, normal/recovery eligibility, service groups and independence requirements. A platform road is not itself a completed movement.

**Geometry contract:** realised canonical alignments, component identities, platform-edge intervals, stopping positions, structures and clearance envelopes. It must identify every unresolved geometric quantity.

**Resource contract:** lawful traversals, track occupation, linked point-group states, modelled protection, setup/release functions and permitted holding positions. It is derived from the accepted geometry and operating profile, not guessed from a decorative drawing.

**Performance contract:** completed work, stock continuity, finite-horizon residuals, disturbance sensitivity and uncertainty under fixed scenarios. This cannot certify a geometry that was never assessed.

The v0.2 proof supplies a restricted movement/resource/performance experiment with **hand-authored resources**. It does not yet provide the production geometry-to-resource compiler.

### 14.2 Stage A — Compile intent into testable movements

Resolve the station function before naming individual points. For each service class, define inbound corridor group, outbound group or next activity, train profile, normal berth eligibility, permitted recovery eligibility and whether the working is mandatory in each scenario.

Store `normal_required`, `recovery_required` and `optional` separately. A recovery connection cannot compensate for failing the normal brief unless the user explicitly authorises that trade. Conversely, a candidate cannot claim to satisfy a bank-closure requirement while dropping the displaced services from the simulation input.

The compiler should produce a typed rejection for ambiguous essentials. It may use a declared project default for optional preferences, but the resulting brief retains that origin. For example, a default train-length class must be visible and must participate in cache invalidation.

Check elementary contradictions before searching: an overlength mandatory train with no permitted platform extension; an outbound corridor absent from the authorised region; mutually incompatible operating-system requirements; or an explicitly forbidden connection that the brief simultaneously requires. An unknown numerical rule is not a contradiction and does not justify a false impossibility proof.

### 14.3 Stage B — Generate topology families

Start with a small grammar of functional arrangements. For the first terminus, enumerate a common distribution throat, independent platform banks, and banks with bounded cross-access. Additional families include separate arrival/departure distributions, staggered fans and earlier approach sorting.

For each family, choose platform-group membership, approach-port order, legal movement pairs and the location of optional inter-group links. Preserve the family identity throughout optimisation so many slight geometric variations of one family do not masquerade as diverse alternatives.

Useful pruning rules include train/platform fit, disconnected entry/exit ports, incompatible systems, unsupported mandatory component types and a rigorous geometric lower bound that already exceeds the site. A lower-bound rejection must state its assumptions. A rough drawing estimate is not such a proof.

An ordering-inversion count can be used as a **search heuristic** when comparing port assignments, but it does not directly determine how many flying junctions are necessary. Component topology, route direction, permissible sharing and vertical freedom still matter. The selected route graph must be generated explicitly.

The output is a graph of typed components and ports, with geometry variables rather than arbitrary final spline handles.

### 14.4 Stage C — Fit a complete throat, not independent curves

Let discrete decisions describe component type, handedness, allowed state and connection order. Let continuous variables describe insertion chainage, heading, alignment parameters, vertical profile and platform position. Freeze those that are fixed by existing infrastructure or the brief.

For every connection, enforce position and tangent compatibility, then the appropriate curvature, grade and cant boundary conditions for that component/profile. A catalogued turnout may contain intended changes that differ from a plain-line transition; do not apply generic smoothing that changes its defined geometry.

Solve the full local assembly with shared constraints. Independent best-fit curves can each look acceptable while colliding with one another, violating platform spacing or removing a passenger-access corridor. A geometry solution includes all running routes and all relevant envelopes.

An implementation should proceed from coarse feasible envelopes to detailed curves. Use multiple initial configurations when the problem is nonconvex. Hard constraints remain separate from soft objectives; a smaller residual sum must not hide one failed mandatory clearance.

The fitting loop returns `fitted_and_checked`, `candidate_not_fitted`, `search_exhausted`, or a scoped infeasibility certificate. It never returns a buildable station merely because the numerical optimiser stopped.

### 14.5 Stage D — Compile and verify resources

Every accepted traversal references its physical route and component states. Use different resource classes for exclusive running space, compatible-state locks, capacity-limited passenger links and deliberately conservative whole-region locks.

For a train with front position measured along its actual travel path, a spatial segment remains occupied until the tail has left that segment. Setup, release delay and protection can extend the required interval. Horizontal engineering chainage and train travel distance must not be confused on graded/curved geometry; the geometry compiler supplies the necessary mapping.

For each point group, store the allowed state combinations of its constituent point ends. Routes requesting the same group state may be state-compatible while still conflicting over running space. The compiler must retain both kinds of claims.

A route resource inferred from incomplete evidence has an assumption record. Conservatively grouping a whole throat into one exclusive resource is permissible for a declared bound or first experiment, but it can understate actual independence and must not become an exact station model by default.

### 14.6 Stage E — Evaluate operations and revise the candidate

Evaluate complete visits first, then linked stock chains and composed station-area queues. Check a fixed nominal scenario before applying disturbances. Service requests, horizon policy and train profiles remain comparable across alternatives.

The production scheduler may use constraint programming, mixed-integer optimisation, temporal search or a purpose-built dispatch algorithm. The contract does not mandate a particular third-party library. Every strategy must retain the same legality, occupancy and conservation checks.

For an optimisation formulation, each mandatory activity selects exactly one complete opportunity. Optional intervals represent the selected routes and berth. Disjunctive constraints prevent incompatible occupations, while precedence enforces readiness and stock continuity. Assigning a low penalty to cancellation is not an acceptable substitute for enforcing a mandatory service.

Evaluate the resulting schedule with an independently structured checker. The optimisation model and checker should not share every implementation shortcut: otherwise the same modelling omission can appear in both and falsely validate itself.

When a resource is limiting, first test bounded changes to platform assignment or permitted operating policy, then a geometry adjustment, then a topology alternative. Escalate only when the required change exceeds the brief. Do not ask Astra to choose every intermediate candidate.

## 15. Geometry kernel: implementable mathematical contracts

### 15.1 Canonical horizontal and vertical quantities

For horizontal chainage `s`, integrate heading and curvature using:

\[
\frac{dx}{ds}=\cos\theta(s),\qquad
\frac{dy}{ds}=\sin\theta(s),\qquad
\frac{d\theta}{ds}=\kappa(s).
\]

Retain `z(s)`, grade `q(s)=dz/ds` and cant separately. Units are metres, radians, inverse metres, dimensionless grade and explicitly named cant units. Conversion to game coordinates is an adapter operation, not a reason to discard these quantities.

A primitive returns evaluation, derivatives, its validity interval, numerical error bounds where available, and provenance. It must state whether chainage is analytic or numerically integrated. Geometry editing uses stable asset identities and reconstructs affected derivative/clearance data.

### 15.2 One implemented plain-line shift

The proof implements an analytic lateral shift between parallel tangents:

\[
y(x)=d(10u^3-15u^4+6u^5),\qquad u=x/L.
\]

Its end slopes and second derivatives are zero. Its horizontal curvature is `y''/(1+y'^2)^(3/2)`. Because the maximum absolute second derivative is `(10/sqrt(3))*abs(d)/L^2`, this is also a conservative upper bound on absolute curvature.

A sufficient length for a specified minimum radius is therefore:

\[
L\geq\sqrt{\frac{10}{\sqrt3}|d|R_{min}}.
\]

This result is a mathematical derivation for this primitive, **not a UK turnout rule**. A failed sufficient-bound check means “not certified by this bound”, not necessarily “the curve violates the radius”. It establishes neither cant/comfort suitability nor vehicle clearance, and it does not replace a switches-and-crossings catalogue.

The primitive is useful for testing endpoint handling, transformations, units and revalidation after compression. It is not used to fabricate turnout blades or crossings.

### 15.3 Catalogue specialwork

Each component instance needs canonical entry/exit ports, all running-path geometries, permitted traversal pairs, point-end/group relationships, applicable train/track profiles, switch/crossing type, construction envelope, maintenance reservation and source issue.

The geometry may be an analytic definition, validated point/curve data, or a parameterised manufacturer/infrastructure-owner definition imported with appropriate rights. A screenshot-derived estimate cannot become a measured catalogue component.

Do not infer a turnout speed from crossing angle alone. Until a component's geometry and applicable limits are imported, the production catalogue must report an unresolved value or restrict the component to a synthetic profile.

### 15.4 Vertical profile and grade-separation assemblies

For a linear grade transition from `q0` to `q1` over horizontal length `Lv`, the elevation change is `(q0+q1)*Lv/2`. Compose approach tangents and vertical curves to meet the required level difference while preserving boundary grades.

A grade-separated crossing's vertical budget contains the lower-route envelope, electrification space where relevant, structural depth, track construction and applicable allowances. Its horizontal budget includes approaches, transitions, abutments, piers, retaining works and drainage reservations. A minimum ramp-distance calculation is only a lower bound until all those elements are accommodated.

The solver should test lifting one route, lowering the other, sharing the change and moving the crossing point where the brief permits. Each solution must name the conflict removed and re-evaluate the downstream merge. Missing drainage, structural or ground information remains an unassessed civil check.

### 15.5 Clearances and numerical tolerance

Use broad-phase spatial bounds to locate possible conflicts, then narrower geometric checks for vehicle sweeps, structures, track-to-track interfaces and platforms. The relevant rolling-stock envelope must be explicit; centreline spacing alone is not sufficient.

Adaptive sampling can locate likely infringements, but a finite sample is not automatically a continuous clearance proof. Where a certified bound is unavailable, record sample spacing, approximation error and uncertainty. Tighten subdivision near high curvature, structure corners and changing cant.

Numerical tolerances should have separate names for solver convergence, coordinate conversion and engineering allowance. A solver epsilon must never silently enlarge a physical clearance or shrink a resource interval.

## 16. Local scheduling proof: exact scope and algorithm

The proof's `Calendar` stores half-open integer-millisecond claims. Each visit selects a single complete platform opportunity. Candidate platforms are inspected deterministically; earlier selected visits remain fixed.

For each candidate platform:

1. Reject train-fit or incoming/outgoing eligibility failures.
2. Find the earliest compatible incoming resource interval at or after the visit's readiness.
3. Calculate the synthetic berthed time and serial dwell/turnback/dispatch readiness.
4. Find the earliest outgoing interval at or after readiness and the planned departure.
5. Claim the berth continuously from entry activation until outgoing tail-clear time. This is intentionally conservative.
6. If an existing berth claim conflicts, move the arrival beyond that claim and repeat within the local budget.
7. Select by departure delay, then cross-bank legs, then entry time and stable platform ID. Commit the complete in-memory reservation only after all its claims are consistent.

This is a **greedy reservation scheduler with event-boundary search**. Its ordered event trace is not evidence of microscopic train simulation. It has no braking curves, dispatch-agent behaviour, signal aspect sequence or spatial approach queue. It does not backtrack earlier visits and makes no global optimum claim.

The proof's constant-speed clearance surrogate is:

\[
T_{claim}=T_{setup}+\lceil1000(D+L_{train})/v\rceil+T_{release}
\]

in milliseconds. The synthetic route distance, train length and speed are declared inputs. They are not measured Waterloo values and are not derived from the worked example's proposed throat envelope.

The event calendar jumps to conflicting reservation ends rather than incrementing time in tiny steps. The tests compare that primitive against a brute-force integer-time oracle on small cases. A budget exit is distinct from absence of any legal opportunity.

## 17. First clause-level numerical checks

Two individual checks from Infrastructure NTSN Issue 2 have been extracted: stopping-platform cant, and platform-adjacent curvature on new lines. GB platform height/offset follow a separately unresolved national-rule path in this release. Exact clauses, limits and applicability fields are recorded in [rules.json](evidence/rules.json), backed by [S058](10_source_register.md#s058).

The evaluators require an explicit applicability decision. `applicable: null` or a pending alternative requirement returns `unassessed`; an existing-track exception to a particular new-line criterion returns `not_applicable`, not general approval. Whole-station UK engineering remains unassessed even when an individual example passes.

The release does not import the full cant-deficiency tables, dynamic gauging calculations, turnout catalogues, speed-dependent transition rules or all national technical rules. Those are the next engineering-profile tasks, not hidden defaults.

## 18. Runtime, repair and stopping rules

Allocate budgets separately to family enumeration, geometry fitting, scheduling, disturbance evaluation and game attempts. The proof currently enforces scheduling evaluation and entry-wait budgets only. It has no implemented geometry-search or game-attempt loop.

The production repair controller should use typed failures. A short berth suggests platform extension or different eligibility; a tail-clear conflict suggests timing, holding or topology changes; a curvature failure suggests longer alignment or another component; an unsupported game component suggests a representable topology family. Repairs preserve all mandatory constraints and invalidate dependent results.

A result is constructible only after required geometry, source applicability, capability and execution-preflight gates pass. Unknowns cannot be turned into a favourable weighted score. A useful offline comparison may still be returned with those gates explicitly unresolved.

## 19. Version 0.3: geometry-derived resource implementation

This release implements a restricted part of GEO-001–GEO-004, GEO-010, DAT-004, TOP-008, OPS-002–OPS-004 and the provenance/budget requirements. It does not mark those broad production requirements wholly complete. The detailed mathematical and module contract is [14](14_geometry_components_and_resource_compiler.md).

### 19.1 Compiler inputs and admission scope

A compiler input contains named ports, physical edges, synthetic component instances, an explicit normal/reverse state mapping, requested legal traversals, a bounded geometry profile and platform storage records. The authored monotone planar catalogue is the accepted scope; arbitrary third-party curves need a separate admission validator.

Generate and check the complete assembly, then derive length brackets and conflict resources. Never insert a conflict matrix selected solely to produce the expected performance comparison. Conversely, do not infer a real control-table permission from geometry.

### 19.2 Separate occupation from control compatibility

Each physical edge carries exclusive track occupation. Components carry a conservative traversal-body exclusion. A control resource compares declared state requirements; matching state is necessary where applicable but does not override physical or geometric exclusions. Proximity resources come from continuous curve enclosures under a synthetic corridor profile and do not add rail connectivity.

This distinction is executed in the crossover trial: two straight movements coexist under the linked normal state; the crossing movement waits for conflicting resources. Both the state and physical reasons remain inspectable.

### 19.3 Lengths, stopping markers and held storage

Route distance is an arc-length bracket, not longitudinal projection. Timing uses the upper bound with outward integer-millisecond rounding. The first fan uses a rear-at-entry-marker arrival stop and reverses from that marker. Its boarding interval, storage edge and useful train length are separate.

The storage edge's geometric exclusions and berth occupation persist through any departure wait. The current whole-leg reservation remains deliberately conservative; sectional release and physical stopping trajectories are future requirements, not hidden deductions from the generated curve.

### 19.4 Bounded fitting and explicit outcomes

The implemented crossover fitter checks a finite parameter grid under immutable spacing/footprint constraints. It retains fitting candidates, non-certification reasons and budget exits. `no_candidate_in_enumerated_set` is not a global infeasibility certificate. A failed sufficient curvature bound is not necessarily an exact-radius violation.

General topology search, continuous optimisation and whole-station automatic repair remain specified but unimplemented. The finite fitter is the first executable local fitting loop, not completion of the full optimiser.

### 19.5 Exit gate

Current acceptance is a synthetic crossover plus a one-approach four-road bank whose compiled routes feed complete-visit scheduling. It is not a four-approach eight-platform station, full UK component profile, gauging approval or game construction plan. The next implementation gate preserves that original larger brief while composing its required arrival/departure interfaces.

## Version 0.4 refinement: numerical profiles and sectional operation

The 75 main requirement IDs remain unchanged. The new implementation advances GEO-001–GEO-004, OPS-001–OPS-006, OPS-010–OPS-012, OBS-006 and EVD-001–EVD-005 in a restricted proof, not their complete production scope.

Numerical values SHALL retain kind, source issue, clause, units and applicability. Nominal references SHALL not return a general compatibility pass; guidance calculations SHALL not become universal requirements. Strict input admission SHALL reject a synthetic component catalogue or unresolved mandatory input rather than silently downgrade the selected mode. [17](17_uk_numerical_profiles.md)

A station-access contract SHALL distinguish physical direction permissions, independent external leads and genuine downstream independence. The implemented two-lead bank retains a shared component and fan. No all-to-all routing is inferred from the graph's geometry.

The motion/resource interface SHALL preserve front and tail positions, stopping convention, setup and release separately. The current implementation acquires all route locks at activation and offers whole-route or synthetic sectional release; it does not infer a real interlocking from edge boundaries. [18](18_arrival_departure_and_sectional_occupation.md)

The production extension must accept a real train-performance profile, applicable speed limits, input/output speeds and downstream holding conditions. The current constant-acceleration experiment is a tested analytic model, not a calibrated vehicle substitute. The original full station brief remains pending.

## Version 0.5 refinement: vehicle geometry and data-driven components

The new implementation contracts are in [20](20_vehicle_envelopes_and_clearance.md) and [21](21_component_catalogue_import.md). Existing requirement IDs remain unchanged.

**GEO-006:** Separate rigid-body plan assessment, parent-curve approximation, vehicle dynamics, height/cant and real gauge-method applicability. A positive result in one domain cannot mask another domain's missing inputs. The implemented two-pivot body model solves fixed physical chord separation, not a presumed chainage difference. Between-pose bounds apply to the supplied polyline only.

**OPS-001 / GEO-007:** Store nominal vehicle dimensions separately from complete unit length and formation layout. The new runner uses published full-unit length for scalar fit/tail timing, while keeping the single-body sweep and full-formation geometry distinct. Performance values remain independently sourced or declared assumptions.

**GEO-003:** A component import declares units, datum, named ports, explicit route geometries, control states and source/limit status. A valid external record may remain quarantined. The current executable import is restricted to one three-port, two-route, level-plan contract; authentic multi-part specialwork requires an expanded representation.

**TOP-008 / OBS-002:** A geometric contact is not new connectivity or a train-collision prediction. Read-only clearance overlays preserve existing control/track/protection resources and provide pose witnesses. Removal of a proxy exclusion needs complete alternative evidence, not a favourable sampled rectangle.

**OPT-004 / EVD-002:** Pose/root/pair/import budgets have explicit failure states. Refining a pose interval is an authorised local computation; changing vehicle width, pivot spacing, a dynamic allowance or a nominal track interval is an input/design change whose origin must remain visible.

The final renderer/adapter must still reconcile actual game vehicle dimensions and track geometry with the chosen engineering profile. This release does not assume that an in-game vehicle exactly matches a real manufacturer's nominal data.

## Version 0.6 refinement: composed stations and candidate-bound evidence

The `railstation` increment now composes two four-road banks into one physical network, instantiates a selective recovery pair through the component-data importer, and recompiles every relevant cross-bank relationship. It schedules all service groups in one calendar; independently scheduling each bank and concatenating the results is not the implemented method. [23](23_two_bank_station_composition.md)

The following refinements apply to DAT-002/DAT-004, TOP-001/TOP-004/TOP-008, GEO-009/GEO-010, OPS-002/OPS-003/OPS-006 and OPT-001/OPT-006:

**Composition identity:** ports, physical edges, controllers, platform roads and source instances retain distinct canonical identities across namespaces. A component's record hash, canonical geometry hash and placement are separate dependencies. A final compile is invalidated when the combined geometry or route eligibility changes.

**Directional recovery:** one bidirectional traversal of a crossover must not be interpreted as all-to-all platform access. Each required recovery consists of an incoming route, usable berth, readiness and appropriate outgoing route. Platform-bank, fan and approach-lead failures remain different scenario inputs.

**Comparison discipline:** synthetic release-section boundaries are matched across the tested family instances, preventing a change in tessellation from silently granting a finer operating model. Production signalling sections must not be derived mechanically from every CAD edge.

**Footprint authority:** test actual ports, complete geometry enclosures, exact boundary conditions and supplied reserved volumes. A larger diagnostic alternative must not overwrite the user's original site. Failure of the fixed instance is not a proof that all possible station topologies fail.

**Evidence joining:** geometry, vehicle, component, numerical and operating results are tied through explicit hashes. Unknown strict-UK and game checks cannot be compensated by a favourable operating score. An independently checked operating candidate can remain outside the construction-admission boundary.

The implemented independent checker uses an interval sweep separate from the scheduling calendar and checks demand, stock, route state, storage occupation and horizon accounting. This verifies the model; it does not validate real signalling or exact rolling-stock dynamics. [25](25_v06_execution_report.md)

The original eight-road functional structure is now generated, but the specific family fails the original 1,200 m site and three exact approach positions. Treat it as a reference-informed larger-site study, not the completed original brief. Full station passenger circulation, buffer/overrun engineering, dynamic gauge, authentic turnout geometry and TPF3 lowering remain open.

## Version 0.7 — Fixed-plan generation and declared crossings

The new implementation described in [26](26_compact_site_and_recovery_design.md) fulfils a **subset** of BRF-001/003, TOP-001/003/004/008, GEO-002/004/009, OPT-001/002/004/006 and OBS/EVD contracts. It does not add or renumber the 75 production requirements.

The brief compiler shall distinguish immutable boundary/platform positions from adjustable authored component parameters. Source-admitted fixed geometry must not be stretched by the fitter. A successful centreline site check shall not suppress incomplete vehicle, platform, civil or game checks.

A crossing is an explicit component contract, not an intersection tolerance. Its two route identities remain disconnected; a validated conflict resource is added. This prototype admits only straight authored fixed diamonds and leaves hardware/speed applicability unassessed. Unexplained intersections still reject compilation.

The local search evaluates hard geometry before scheduling. Its return distinguishes an examined finite grid from an exhausted budget; a partial candidate is not the final optimum of even that grid. Scenario ranking requires the original scoped plan and all requested completions before applying the declared complexity preference.

Recovery capability is a typed relation between originating group, receiving berth, departing group, train class and failed asset. A pair of crossovers does not imply arbitrary bank access. The executed inner-road family supplies either bank-closure recovery, but not fan bypass or long-train access to an undersized receiving berth.

The whole production system remains larger than this proof. The next integration should replace synthetic component and platform assumptions without changing the success criteria or allowing earlier passes to survive changed data unexamined.


## Version 0.8 — Source-qualified platform interfaces

GEO-007/GEO-009 and PAX-005 now have a further implemented slice: rail-plane datums, paired-island boarding surfaces, reference dimensions, general obstacle clearance and bounded facility re-fit. [29](29_uk_platform_datums_and_interfaces.md) defines the transforms and rule status; [30](30_platform_refit_and_component_evidence.md) defines the operational consequences.

The production planner SHALL keep measurement datum, source/version, applicability and design-versus-maintenance stage with each resolved quantity. Permissible/enhanced infrastructure speed SHALL remain separate from a train's current or target speed. Neither missing scope nor an outdated source may become a current-rule pass.

A complete station candidate includes rail, platform and facility identities. Local access failures SHALL reach platform eligibility through an explicit policy and SHALL NOT be represented as observed physical track closures. The scoped gate also checks known height/offset/width failures, so a favourable furniture placement cannot hide an incompatible coping position.

The current implementation leaves accessible concourse paths, passenger demand sizing, lower-sector step/gauge compatibility, structural platform design and full current-source reconciliation unresolved. It does not complete the PAX-001–PAX-008 suite or an approved GB profile.


## Version 0.9 — Corridor engineering and game-fit contracts

The original requirement IDs remain stable; this increment supplies new implementations or proposals within those contracts rather than replacing the whole requirement set. Station-internal implementation is frozen. The current runnable path is `railcorridor`, with the exact scope in [32](32_corridors_junctions_and_game_fit.md).

**Corridor input:** two fixed two-track interfaces; authorised site; protected land; versioned terrain; speed/grade/curve preferences; train-length profile; realistic-number provenance; separate search and lowering budgets. Coordinate x, horizontal chainage, 3D travel distance and normal offset must remain distinct.

**Implemented local loop:** enumerate a bounded lateral/elevation family; construct C2 reference spans; derive both parallel tracks; evaluate analytic geometric bounds; inspect terrain/river constraints; retain rejected candidates; evaluate a unit-bearing objective vector; return a small displayed subset with the full local set accessible. A narrowed parameter family is not a global optimiser. Resizing a route or changing speed triggers recomputation, not uniform prefab scaling.

**Terrain output:** planning-level formation/structure runs and approximate earthwork volumes. The current midpoint estimator is not an exact site-volume calculation. Both tracks share one formation estimate. Actual bridge assets, portals, supports, drainage, ground stability and terrain mutations remain future adapter/civil work.

**Junction boundary:** complete flyover/diveunder ramps now support local crossing-cell comparisons. The upstream turnout pair, connecting branch curves and downstream merge are missing. Removing a named crossing conflict in this cell cannot certify a complete junction or improve an unmodelled network-capacity metric.

**Construction contract:** lower accepted corridor geometry to capability-qualified staged operations, preserve identity and expected world revision, and inspect realised state. Acknowledgement alone is not success. The implemented version is a mock contract; every actual TPF3 operation remains unknown. [34](34_v09_execution_and_handoff.md)

## v0.10 addendum — complete junction movements, not isolated crossing cells

The local implementation is in [35](35_connected_passenger_branch_junctions.md)–[37](37_v010_execution_and_handoff.md). Station internals remain frozen. This addendum refines existing TOP-001/TOP-006/TOP-008, GEO-008 and observation/execution responsibilities; it does not introduce a second production requirement numbering system.

The junction compiler SHALL retain the required boundary-to-boundary movements, physical component routes and shared exit tracks. A grade-separated crossing removes only the specifically supported crossing conflict. Merges, diverges, controller-state conflicts and downstream bottlenecks remain unless a corresponding physical/operating redesign actually changes them.

The implemented local family joins two imported authored turnouts, connecting curves and full return ramps. All four required movements are connected. The new local site's containment is not interchangeable with the separate v0.9 terrain assessment. Future corridor insertion SHALL bind actual terrain and authorised interfaces into the same candidate identity before claiming site feasibility.

The geometry-to-operation contract distinguishes physical-edge occupation, component bodies, controller states and a derived crossing footprint. The current whole-pass reservation policy books future intervals atomically in memory. It is neither a real interlocking nor a literal TPF3 path-reservation implementation. The demonstration retains identical request inputs across variants and tests crossing and merge objectives separately.

A prospective holding location SHALL report bare formation clearance separately from extra margins. The current implementation supplies that static check only. Braking, stopping, grade restart, signal placement and queue spillback remain explicit production work; an adequate length alone cannot establish an operational holding position.

Semantic construction SHALL lower unique physical assets rather than duplicate shared rails for each service route. Current object read-back, legal component movements and non-connecting crossings are required in addition to coordinate checks. All such executed behaviour currently belongs to the mock, not the real game.


## v0.11 — Terrain-bound corridor/junction composition

The new implementation refits a complete local junction against the corridor's original station interfaces, terrain and protected land. Component placement is rigid; plain-line approaches are re-solved. Both main-line routes retain the corridor profile instead of inheriting a local branch floor. Each physical edge is assessed once, with source snapshot/content, terrain, constraints and geometry joined before operation or mock construction. See [38](38_terrain_aware_junction_placement.md) and [40](40_v011_execution_and_handoff.md).

The supplied terrain is analytic synthetic data, not an acquired game grid. Civil runs and bounding reservations are planning results, not complete structures or full transverse earthwork validation. This is unbuilt-design replacement, not live demolition/splicing. The next productive scope is grade-aware motion and internal holding/restart, with station internals still frozen.
