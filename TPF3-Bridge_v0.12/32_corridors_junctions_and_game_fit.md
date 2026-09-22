# UK corridors, junctions and game-fit specification

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.9.0 · **Date:** 21 September 2026  
**Default purpose:** credible British passenger-network construction in a sandbox game. Station internals are frozen at v0.8; this release does not implement the previously proposed detailed platform-access stage.

## 1. The product boundary has changed deliberately

Python should engineer routes, junctions and structures which change the player's railway, not grow into an unrelated station-certification simulator. Retain platform fit, usable connections and sensible spatial reservations. Defer detailed crowd circulation, lift queues, evacuation analysis and manufacturing mechanics unless game behaviour or a specific brief requires them.

The normal mode is **GB reference-inspired**: source-backed dimensions where resolved, explicit project design targets, and visible approximations where the game or available data requires them. The strict research profile remains separate. An unresolved specialist certification does not prevent returning a useful reference-design alternative; neither does reference mode turn an unknown game capability or a failed mandatory brief into a pass.

Astra owns the purpose, site, service priorities, desired character and material compromises. Python owns corridor alternatives, geometry, terrain screening, local repair, evidence resolution, lowering and result comparison. The in-game adapter remains responsible for authoritative game state and supported operations.

The success criterion is an accepted useful construction task with limited Astra involvement, not another arbitrary number of unit tests. Test counts are supporting verification, not a measure of railway completeness.

## 2. What the new implementation supplies

| Layer | Executed v0.9 behaviour | Deliberate boundary |
|---|---|---|
| Corridor search | Bounded lateral/height family search between fixed double-track interfaces | Restricted x-monotone gates, not arbitrary continental route finding |
| Track geometry | C2 horizontal/vertical alignment and genuine normal-offset parallel tracks | Zero cant; not yet a full clothoid/cant profile library |
| Engineering screens | Curvature, gradient, vertical curvature, zero-cant acceleration and curvature-rate bounds | Project speed screens, not approved vehicle or component speed ratings |
| Terrain | River, ridge, no-build reservation, cutting/fill, tunnel and elevated-run classification | Authored synthetic terrain; quantities are sampled planning estimates |
| Junction preparation | Full-ramp flat/flyover/diveunder **crossing cells**, matched to a corridor's straight crossing zone | Open connection ports; complete branch turnouts and merge geometry are not generated |
| Holding/braking | Formation-length and level braking-distance checks | No automatically certified signal spacing or physical traffic simulation |
| Game-fit | Typed construction plan, explicit capabilities, ordered dependencies and read-back verification | In-memory mock, no TPF3 API calls |

The corridor and crossing-cell assessments share the brief and a checked crossing datum. This is not a claim that the separate branch ports have already been joined into a complete railway junction. The exported join record explicitly says otherwise.

## 3. Inputs, authority and station contracts

The first corridor brief freezes two sets of station-side track ports, nominal separation, position, heading, rail height and gradient. It does not reopen their station interiors. A later live snapshot should provide those ports, plus the corresponding stable asset IDs, permitted directions and usable routes.

The executable fixture is [release.json](proof/corridor_fixtures/release.json). Its dimensions describe a fictional 6 km study, not a British location. It contains a synthetic terrain revision, authorised site rectangle, a no-build rectangle, family search axes, a route profile, civil assumptions, a crossing envelope and mock execution tolerances.

A production `CorridorBrief` must additionally carry arbitrary boundary headings/grades, service and vehicle profiles, construction epoch, required branch movements, structure restrictions, preferred visual character, protected assets and allowed changes. These wider fields are specification requirements, not silently supported by this first fixture.

The closed fixture parser rejects extra fields, malformed ranges, non-finite values, duplicate JSON keys, duplicate search values, invalid river bounds and unbounded search domains. It has no expression evaluator or network fetch. Reading a fixture cannot authorise desktop actions or execute embedded code.

## 4. Realistic UK references versus chosen targets

The source-backed nominal centre interval is **3.4 m** in the applicable GB straight/radius-at-least-400 m case. Its lookup retains `reference_value` semantics rather than passing vehicle clearance. The source's national-rule and reduced-spacing branches remain separate. [S058, 7.7.17.3](10_source_register.md#s058)

All of these initial route settings are **project-selected game-design targets**, not asserted Network Rail defaults:

| Quantity | Main corridor setting | Meaning |
|---|---:|---|
| Intended route speed | 60 mph = 26.8224 m/s | Desired speed for geometry screening; no measured train performance claim |
| Minimum horizontal radius target | 1,500 m | Must pass on both normal-offset tracks |
| Maximum gradient magnitude | 0.01, or 1 in 100 | Desired conventional-route profile, not a universal UK maximum |
| Minimum vertical radius target | 5,000 m | Project vertical smoothness screen |
| Maximum unbalanced lateral acceleration | 0.65 m/s² | Zero-cant project screen |
| Maximum lateral jerk estimate | 0.15 m/s³ | Constant-speed curvature-rate screen |
| Cant | 0 mm | Explicit supported domain, not a claim that British curves generally have no cant |

The crossing-ramp grade target is separately 0.02, or 1 in 50. Structure depth, electrical space, freeboard, formation width and earthwork slopes are likewise explicit project inputs. The parameter register is [corridor_design_profile.json](evidence/corridor_design_profile.json); executable values are in the fixture.

The NTSN's basic horizontal/vertical floors are not replacements for speed-selected alignment. In particular, its conditional gradient provisions must not be treated as one maximum for every British railway. Selected source pages were rechecked; no new universal UK design table is claimed in this increment. [S058](10_source_register.md#s058)

## 5. Canonical geometry: a graph parameter is not chainage

On a span between knots, write `u = (x-x0)/L` and `H(u)=10u³−15u⁴+6u⁵`. Both y and z interpolate using H. First and second derivatives vanish at either end, so the joined alignment is C2. This family has an intentional limitation: every gate has an x-parallel horizontal tangent and zero grade. It is not a substitute for arbitrary boundary-value fitting.

With `p=dy/dx` and `w=sqrt(1+p²)`, horizontal chainage satisfies `ds/dx=w`. Curvature is `k=y''/w³`. A track at signed normal offset d is:

`r_d(x) = (x − d p/w, y(x) + d/w, z(x))`.

This preserves the requested normal separation. Adding a fixed y amount on a curve would not. The offset's plan curvature is `k/(1−d k)` and its horizontal metric is `w(1−d k)`. The implementation requires a positive regularity factor; singular or uncertifiable offsets are rejected.

Grade is calculated against that track's horizontal chainage, not against x or the centre alignment. Vertical curvature includes the effect of the changing horizontal metric. Travel length is a composite-Simpson estimate of the 3D metric; its method is recorded, and no exact chainage claim is attached to the estimate.

### 5.1 Bounds and speed screens

For each span, the quintic derivative bounds are `|y'| ≤ 1.875 |Δy|/L`, `|y''| ≤ (10/√3)|Δy|/L²`, and `|y'''| ≤ 60|Δy|/L³`; the vertical derivatives have corresponding bounds. These are mathematical properties of this authored primitive, not external railway rules.

The implementation propagates those bounds through both offset tracks. It checks horizontal curvature, gradient and vertical curvature, then the zero-cant constant-speed screens `v²|k|` and `v³|dk/ds|`. A failed sufficient bound returns **not certified by this bound**, not proof that an exact engineering limit is violated. No solver changes the requested speed to hide such a failure.

The bounds use ordinary floating arithmetic with declared guards, not formal interval arithmetic. Dense independent tests and derivative comparisons verify implementation consistency within this model. They do not validate dynamics of an actual vehicle.

### 5.2 Lowering to supported geometry

The mathematical alignment is separate from the adapter polyline. A second-derivative bound gives a maximum positional deviation of `B Δx²/8` for linear interpolation in x. Subdivision respects the selected positional tolerance. It is a **centreline positional bound**, not a complete vehicle-pose or dynamic-gauge bound.

The mock receives those explicit 3D vertices and stable connection-node IDs. A future game adapter may choose splines instead, but must declare its approximation, preserve the boundary contracts and recheck the actual construction. Engine tessellation must not define signal sections by accident.

## 6. Terrain decisions and civil reservations

The synthetic terrain contains a ridge, a river with explicit wet boundaries, and a protected rectangle. The search varies lateral alignment and rail height. Each candidate is screened against the same immutable interfaces, profile and site; forbidden land cannot disappear from the objective merely because its route is shorter.

The terrain helper classifies run intervals as surface, cutting, embankment, river bridge, viaduct or tunnel according to declared project thresholds. The river is inserted as an explicit grid boundary, so a long cell cannot skip it accidentally. Monotonic vertical geometry provides a lower rail-height bound over each river interval, used with water level, deck depth and freeboard.

Cut and fill volumes are midpoint-grid estimates using one double-track formation and a trapezoidal cross-section. They are not separately counted once per track. These estimates do not establish ground stability, balance transport, retaining-wall design, abutment/pier suitability, tunnel cover through portal transitions, hydraulic approval or full earthwork-toe containment.

The current bridge/tunnel outputs are reservations and interface requirements, not catalogued completed structures. No price, construction time or real structural capacity is inferred. In sandbox use, compare land disturbance, route character, structure need and service purpose rather than financial return by default.

A production terrain service must import actual engine heights and revision IDs, bound interpolation uncertainty, include obstacles/roads/water extents and re-query after terrain modification. Grid refinement should improve the estimate without covertly changing the ground or allowances.

## 7. Search, preference and compression

The first grid has four lateral offsets and three heights: twelve candidates. Cheap geometric/site checks precede comparison. Full results retain failed candidates, reasons, scope and input hashes. Exhausting a computation budget is distinct from completing the grid without a candidate. Neither establishes impossibility outside the searched family.

Candidates are compared using a vector of tunnel length, elevated length, earthwork estimate and track length—no arbitrary mixture of metres and cubic metres into a hidden score. The full nondominated set stays local. The normal packet displays the shortest accepted route and the least-tunnel/earthwork alternative as two understandable choices, with other results available by reference.

The demo's construction-plan example uses the lowest estimated earthwork candidate, then length. That is an explicit demonstration policy, not a global optimum or a requirement that Astra choose it.

The changed-speed trial keeps the higher target instead of automatically slowing trains. The shorter-corridor trial refits horizontal and vertical geometry while preserving local widths and formation-length inputs. Map compression is therefore a new solve, not a uniform scaling of trains, clearances or components.

## 8. Crossing cells: progress without invented branch connections

A crossing cell is the part of a later junction that passes a branch corridor across the two main tracks. It has actual level-change approaches and open branch boundary ports. It is intentionally not a complete diverging junction: upstream turnout fitting, approach sorting, downstream continuation and merge geometry remain required composition work.

The current cell is perpendicular to the final straight main-line zone. Flat, flyover and diveunder variants use the same rail datum, horizontal crossing location and project vertical budget. The elevated/depressed alternatives include both ramps and a central level section. The site reservation is checked separately from the local ramp geometry.

Clearance is checked over the whole declared crossing footprint rather than only its centre. Removing the model's crossing exclusions requires acceptable ramp grade, vertical curvature and separation. Failed or unresolved separation retains the exclusions. A geometric intersection never creates a turning connection.

The flat cell shares two explicit crossing resources with the main tracks. A passing grade-separated cell removes those named crossing conflicts **within the declared cell model**, but does not prove independent merges, adequate downstream holding, real signalling protection or a connected branch. Existing station-model resources are not modified.

A diveunder still needs drainage/groundwater, construction-envelope and asset checks. Their unknown status is explicit, not concealed by a successful vertical profile.

## 9. Holding and practical operating scope

The first holding helper checks full formation length plus declared entry/exit margins. The separate braking helper uses a level-track, constant-deceleration model and an explicit reaction allowance. A train can fit in a holding interval but still lack sufficient approach braking distance. These are planning screens, not source-backed signal-spacing rules.

The game's published design describes path reservations and configured alternative terminals. That motivates a future game-calibrated operating adapter rather than treating the offline timetable experiments as literal engine behaviour. Published features do not establish callable API functions. [S001](10_source_register.md#s001)

Next operating work should test train waiting positions, junction fouling, practical line priorities, deadlock and slow/fast service interactions. Detailed real interlocking reconstruction is optional unless explicitly requested. The present release generates no actual game signals and predicts no trains-per-hour capacity.

## 10. Capability-qualified construction and recovery

The adapter contract separates the mathematical candidate, a lowered plan, operation receipts and realised geometry. The delivered adapter is a fault-injectable **in-memory mock**. Its capability names are bridge-design identifiers, not TPF3 API names.

Published behaviour, documented API, demonstrated operation, unsupported operation and unknown operation must remain distinct. A demonstration in the mock cannot promote a real-game capability. The [unprobed manifest](proof/corridor_results/tpf3_unprobed_capabilities.json) keeps every relevant game operation unknown.

Preflight verifies plan content hashes, derived capability requirements, expected static world/terrain revision, dependency order and edit-region containment. Civil reservations precede associated track operations. Stable operation IDs bind to their full contents, not merely a human label.

After a lost acknowledgement, the controller queries the receipt before retrying. Repeating the plan against the same mock state does not add duplicate effects. Construction rejection leaves a partial-effect ledger. A realised geometry deviation beyond tolerance stops further execution even after acknowledgement. There is no automatic or promised atomic rollback.

Mock read-back verifies ordered vertices, payload fields and explicit node identities. Real-game read-back will also need connectivity, route eligibility, asset identity, supported structure variants and observed traversal. None has been demonstrated in the game here.

## 11. Production backlog after this increment

The next integration target is **live terrain and construction capability probing, plus genuine branch-connection composition**. Preserve the new corridor contract while adding admitted turnout interfaces, approach sorting and a downstream branch route. Reuse station ports rather than reopening station internals.

After that, add circular/clothoid/cant profiles, geographically arbitrary headings, actual terrain-grid import, useful bridge/tunnel asset selection, grade-sensitive train performance and game-calibrated signal/holding behaviour. Maintain a concise implementation matrix so proposed contracts are not confused with executed support.

The immediate specification is already useful without all those later refinements. It returns genuine reference alternatives and a tested transport-neutral execution contract while clearly identifying what remains unbuilt.

## v0.10 continuation note

The historical v0.9 cell described above remains an open-port experiment. The new [connected-junction study](35_connected_passenger_branch_junctions.md) supplies complete branch paths and a shared downstream merge in its own explicit local site. It does not overwrite this corridor's terrain result or claim the new spread-track layout fits the old river/ridge footprint. Terrain-aware insertion is the next integration gate.
