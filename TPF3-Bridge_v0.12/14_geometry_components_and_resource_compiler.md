# Geometry components and the resource compiler

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.3.0 · **Date:** 20 September 2026  
**Status:** Implemented and tested for authored synthetic planar crossover and single-approach platform-bank assemblies. Not an approved UK component catalogue, full vehicle-gauging system, real interlocking model or game adapter.

## 1. The boundary this release crosses

The v0.2 operating proof accepted hand-written route distances and resource families. The new `railgeom` package instead generates explicit component geometry, validates the permitted track paths, measures those paths, identifies conservative geometric proximity exclusions, and compiles the result for the reservation scheduler. The old `railproof` experiment remains intact as a separate regression baseline.

This is not an attempt to derive every railway rule from a drawing. Three inputs remain distinct: physical geometry; explicit component connectivity and control-state metadata; and the selected operating/timing assumptions. Their origin survives in the compiled result. In particular, an interlocking control table cannot be reconstructed simply by intersecting track centrelines.

The historical Waterloo reference describes linked point ends and, separately, scheme plans and control tables that specify conditions for actions. This supports preserving control semantics as explicit data. It does not validate the synthetic controller mapping used here or establish a present-day Waterloo layout. [S055, printed pp. 13 and 19](10_source_register.md#s055)

## 2. Implemented module boundaries

| Module | Responsibility | Principal non-goal in v0.3 |
|---|---|---|
| `railgeom.curves` | Bezier evaluation, derivatives, subdivision, length bounds, curvature bound, continuous enclosure proximity and geometric joins | Dynamic vehicle envelopes, full three-dimensional geometry |
| `railgeom.network` | Named ports, physical edges, explicit turnout traversals and legal route enumeration | Inferring connections from coordinate coincidence |
| `railgeom.patterns` | Synthetic turnout instances, complete crossover and a small single-approach platform bank | A measured UK switches-and-crossings catalogue |
| `railgeom.compiler` | Geometry-derived lengths, physical/proximity resources and explicit state requirements, with provenance | Actual signal positions, flank protection or authentic route-release rules |
| `railgeom.operations` | Complete visits and route-only trials using compiled data and the existing calendar | Microscopic acceleration/braking, spatial queues and live train control |
| `railgeom.search` | Bounded search of a declared finite crossover parameter grid | Global geometry optimisation or proof that no other topology fits |
| `railgeom.demo` | Strict fixture loading, repeatable experiments and compact result packets | MCP transport or authorised game-world editing |

Source is in [proof/railgeom](proof/README.md). Implementation status is reported in [16](16_v03_execution_report.md).

## 3. Canonical geometry and coordinates

All current geometry is two-dimensional in a local metre-based coordinate frame. Every track has an explicit start and end port. A curve retains its control points, analytic derivative operations and a direction; its parameter is not confused with engineering chainage. Chainage is obtained from an arc-length bracket.

Coordinates must be finite and within the implemented local-coordinate guard. Degenerate endpoint tangents and zero chord definitions are rejected. The allowed numeric range is an implementation guard, not an engineering site limit. A production adapter will supply a separately tested game-to-engineering transform.

For a parameterised curve `r(u)`, the kernel uses:

\[
\kappa(u)=\frac{x'(u)y''(u)-y'(u)x''(u)}{(x'(u)^2+y'(u)^2)^{3/2}}.
\]

A connection check compares position, unit tangent and signed curvature. This is a geometric continuity check; it does not require matching the arbitrary speed of the two curve parameters. Reversal changes the traversal orientation correctly. Mirroring changes signed curvature and handedness, and the resulting assembly is rechecked.

The implemented patterns are level, with zero cant. That is a declared limited profile, not an assessment that every eventual station should be flat or uncanted.

## 4. A deliberately synthetic turnout component

### 4.1 Purpose and mathematical definition

The initial catalogue contains one authored eased-divergence family. It provides three named ports: toe `T`, normal exit `N` and reverse exit `R`. Its normal path is straight. For span `L > 0` and positive branch slope `m`, the divergent centreline is:

\[
x(u)=Lu,\qquad y(u)=mL(u^3-\tfrac12u^4),\qquad 0\le u\le1.
\]

Therefore:

\[
\frac{dy}{dx}=m(3u^2-2u^3),\qquad
\frac{d^2y}{dx^2}=\frac{6m}{L}u(1-u).
\]

The path begins horizontally, ends at heading `atan(m)`, has lateral displacement `mL/2`, and has zero curvature at both ends. These are mathematical properties of the authored curve, not published UK turnout dimensions.

Its Bezier control polygon is stored exactly as:

```text
(0,0), (L/4,0), (L/2,0), (3L/4,mL/4), (L,mL/2)
```

The component contains no engineered switch blades, crossing nose, check rails, bearers, fastenings or actuator geometry. It is a functional centreline prototype for testing assembly and compilation. Its branch slope must not be converted into a claimed turnout speed.

RSSB's catalogue describes RIS-7707-INS as covering new, renewed and upgraded switches and crossings, with requirements additional to the infrastructure framework. The reviewed catalogue is not a source of the synthetic dimensions above. [S047](10_source_register.md#s047)

### 4.2 Connectivity is not an undirected three-way junction

Allowed component traversals are `T <-> N` and `T <-> R`, subject to the matching state. The graph search must not go from `N` through `T` to `R` within the same component. Such a movement would require leaving the component and a separately modelled reversal, not a continuous path through a Y-shaped node.

The enumerator keeps component and port visit history. Components with unsupported movements are rejected rather than smoothed into an approximate connection. There is no implicit route at a geometric crossing and no automatic connection between coincident but differently identified ports.

The authored catalogue is intentionally small. Arbitrary looping curves, self-crossing component definitions, and unrelated contacts between edges sharing a declared endpoint are outside its admission scope. A general component importer must add those checks before accepting arbitrary third-party geometry.

## 5. Curve approximation must carry uncertainty

### 5.1 Arc-length brackets

For each Bezier subdivision, the chord gives a length lower bound and the control-polygon length gives an upper bound. Subdivision continues until both the geometric flatness and allocated length-gap criteria are satisfied. Summing the leaf bounds gives the path bracket.

The current default total length-gap target is `0.0001 m` per edge and the flatness target is `0.01 m`. Small outward floating guards are applied. These are numerical configuration values, not civil construction tolerances. The implementation is ordinary floating-point code, not formally verified interval arithmetic.

A subdivision budget is enforced. Exhaustion must return a failure to complete the bound, not a zero error estimate. Tests compare the bracket with an independently written numerical integral on representative curves.

### 5.2 Curvature certification within the synthetic profile

A derivative-control-hull bound, tightened by subdivision, produces an upper bound on absolute curvature. A positive projection bound keeps the derivative away from zero. Compilation accepts the selected synthetic minimum-radius check only when the bound satisfies that profile.

If the sufficient bound fails, the result is `radius_bound_not_certified`. This is not automatically proof that the exact curve violates the radius, because the bound can be conservative. The bounded fitter can try another candidate without asserting a physical impossibility.

No claim is made about cant deficiency, comfort, vehicle dynamics or the applicability of a UK speed-dependent rule from this radius check alone.

### 5.3 Continuous corridor proximity rather than point samples

Each subdivided curve segment lies within a convex-hull enclosure around its chord. For two leaves, the compiler evaluates chord-segment distance and accounts for both enclosure radii. A broad-phase bounding-box check avoids unnecessary detailed comparisons.

If the enclosure-based separation cannot establish that two synthetic track corridors are apart, the pair receives a conservative proximity resource. The result retains the implicated edges, parameter intervals, required separation and witness information. It can over-restrict movements, but it does not silently declare unsampled gaps clear.

The demonstration uses a `1.75 m` half-width for each centreline corridor and a `0.5 m` additional gap, giving `4.0 m` pair separation. These values are synthetic. The model is not a rolling-stock swept-envelope calculation and does not account for vehicle overhang, throw, cant, suspension, structure shape or crosswind.

Infrastructure-to-rolling-stock compatibility is the scope of the separate gauging source; its catalogue does not supply a complete envelope model for this proof. [S045](10_source_register.md#s045)

## 6. Complete crossover assembly

The crossover uses two compatible synthetic turnout instances and a tangent connecting segment. The second turnout is rotated through 180 degrees. Let parent-track spacing be `S`, span be `L`, and slope be `m`. The connecting tangent length is:

\[
K=\frac{S-mL}{\sin(\arctan m)}.
\]

The longitudinal separation of the toe positions is:

\[
X=L+\frac{S}{m}.
\]

The implemented family requires `S-mL > 0`. A zero-length connecting tangent is deliberately unsupported in this release; a negative value cannot be repaired by reversing the tangent or silently warping a component. All route joins are checked after composition.

Inputs retain parent spacing, component parameters, optional linked-control semantics and the permitted overall longitudinal span. The output contains both straight parent routes and the supported crossing traversal in both directions. It does not invent the opposite diagonal, which would require another arrangement.

The fitting procedure uses exact endpoint construction for this family rather than a general nonlinear optimisation package. It can search a finite component parameter grid under a supplied footprint bound. Full UK catalogue substitution remains a separate admission step.

## 7. Small platform-bank fan

The implemented bank has one bidirectional approach, a spine, a sequence of diverging components, tangent links and reversed eased components that return the platform routes to parallel tangents. The farthest platform branch is taken first; subsequent branches have smaller offsets. This is a restricted generation grammar, not a proof that every fan should use that ordering.

Platform roads, rear-stop markers, storage edges and boarding lengths are separate records. A storage edge is not treated as another outgoing service route. It carries occupation/proximity resources while the train is berthed.

There are explicit limits on platform count and boundary geometry. A pattern that cannot finish its return curves before the boarding region is rejected. The resulting fan is a **subassembly**: it does not satisfy the four-approach, eight-platform station brief in [12](12_worked_station_design.md).

## 8. Resource compilation

| Resource class | Derived from | Compatibility and interpretation |
|---|---|---|
| `track:<edge>` | Canonical physical edge identity | Exclusive running space |
| `component_body:<id>` | Explicit synthetic component membership | Conservative exclusion of simultaneous traversals through the same turnout body |
| `control:<id>` | Declared component/controller state map | Matching states can coexist; incompatible states cannot |
| `proximity:<edgeA>\|<edgeB>` | Continuous enclosure comparison under the synthetic corridor profile | Exclusive conservative geometric conflict, not a rail connection |
| `berth:<id>` | Declared platform occupation contract | Held continuously for a complete assigned visit |

Matching point states are not sufficient for simultaneous train movement: the same routes may still share exclusive track or proximity resources. Conversely, a linked controller in the same state does not force separate straight parent tracks to share one artificial exclusive throat region.

Every compiled route contains its ordered edges, direction on each edge, arc-length bracket, cumulative chainage brackets, resource requirements and source hash. Before accepting it, the compiler checks that the route belongs to the explicit legal path set. A supplied edge list is not trusted as evidence of legality.

If a route requests both normal and reverse from the same linked controller, compilation rejects it. A possible unmodelled centreline contact between unrelated edges also stops compilation rather than being converted to a diamond.

Geometry supplies distances and conservative proximity information. Component metadata supplies connectivity and state semantics. An eventual operating profile must supply signal locations, sectional release, route locking, overlaps and other protection where modelled. These origins must never be conflated in a result labelled “geometry-derived”.

## 9. Timing, stopping and holding contracts

The compiled route's upper arc-length bound replaces the v0.2 hand-entered distance. The current timing surrogate remains:

\[
T_{leg}=T_{setup}+\left\lceil1000(D_{upper}+L_{train})/v\right\rceil+T_{release}.
\]

Times are integer milliseconds. The whole route's required resources are held for the whole leg. This is conservative whole-leg reservation, not sectional release. A route-only clear time and an arrival berth-ready time are modelling outputs, not observed train motion.

The bank has an explicit near-entry stopping convention. At the end of an arrival, the train's rear is at the marker; the front is a train length farther along the storage road. Reversal makes the marker the departure-front location. This explains why the arrival and departure include train length without pretending that a train continues beyond a buffer.

The platform is held from incoming activation through outgoing clearance. Storage-edge exclusions are held throughout the same interval, including departure waiting. This can reserve space earlier and longer than a detailed train-motion model would. That conservatism remains visible.

A production extension needs a continuous front-position function, stop target, speed/braking profile, per-resource entry/exit intervals and release assumptions. It must model the tail at each relevant resource and include the next holding location. Simply shortening the current whole-leg locks would be an unsafe modelling shortcut.

## 10. Hashes, budgets and auditability

The physical source hash covers canonical ports, edges and component state maps. A compile hash additionally binds the geometry profile, route requests, platform records and compiler version. The JSON exports retain both.

The in-process curve-evaluation cache avoids repeated subdivision of identical immutable curves. It is not a persistent candidate cache, database or incremental world invalidation engine. Those remain future work.

Limits apply to subdivision, path enumeration, finite component search and reservation-calendar evaluation. A result must distinguish a rejected candidate, missing evidence, uncompleted search and the absence of a candidate in a particular finite grid. None is silently upgraded to global infeasibility.

## 11. Production admission gates

The current implementation is suitable as a reproducible synthetic engineering experiment. Admission to a real-reference or game construction library still requires: an appropriately licensed and reviewed component catalogue; applicable vehicle/track/structure envelopes; a complete operating model for the intended assessment; platform/civil interfaces; and demonstrated engine representation.

The next extension should first compose arrival/departure access around a bank, while retaining the typed movement contract. Sectional resource occupation and train-performance work should then be validated against the conservative baseline. Full eight-platform and multi-junction examples follow after those foundations, rather than by scaling this small fan and inheriting its pass status.

## Version 0.4 extension context

This document describes the unchanged v0.3 geometry kernel. The new `railops` layer composes explicit two-lead access, derives resource footprints from these same length/edge records, adds stopping motion and compares whole-route versus synthetic sectional release. Timing is no longer inferred from this document's historical whole-leg example; use [18](18_arrival_departure_and_sectional_occupation.md) for the new model.

The numerical-profile work in [17](17_uk_numerical_profiles.md) does not approve this synthetic catalogue or turn its corridor proxy into a vehicle gauge. The new exported wrapper separates geometry-compiler provenance from the current operation assessment.
