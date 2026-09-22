# Connected passenger branch junctions

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.10.0 · **Date:** 21 September 2026  
**Status:** Executed local junction geometry, route/resource compilation and mock construction. Four required movements are connected in flat, flyover and diveunder variants. Actual terrain insertion, complete vehicle/civil clearance and game behaviour remain unassessed. Station internals stay frozen at v0.8.

## 1. The gap this release closes

The v0.9 crossing cells contained complete vertical ramps, but their branch connection ports were open. A passing crossing-height check could not establish a usable branch railway. The new `railbranch` package adds both real-in-the-model turnout components, connecting curves, the return merge and complete boundary-to-boundary routes.

The acceptance question is now: **does the same connected railway carry the required movements, and exactly which conflicts change when one movement passes above or below another?** It is not enough to delete a crossing resource from an abstract graph.

This is a **new synthetic local junction window**, not a terrain-checked alteration to v0.9's river/ridge corridor. Its main tracks spread to provide room for the return alignment and ramps. The resulting land requirement has not been fitted to that previous landscape. The previous corridor and station examples remain unchanged and retain their own identities. A future corridor insertion must preserve their interfaces or obtain an authorised change.

### 1.1 Reference lesson, not a replica

Network Rail's 26 June 2013 Hitchin announcement describes selective separation of Cambridge-bound trains that previously crossed other lines; the southbound route remained on its existing arrangement. This is a useful reference for separating a named movement rather than raising every track. No Hitchin coordinates, component dimensions or capacity claim are imported into this fixture. [S070](10_source_register.md#s070)

## 2. Functional contract and route inventory

The local brief has six external directional rail ports and four mandatory movements. An outbound branch train leaves the eastbound main line; the returning branch train crosses the eastbound main line and joins the westbound main line.

| Movement ID | Required path | Principal infrastructure |
|---|---|---|
| `main_east` | W_E → E_E | East approach, normal route through divergence D, east continuation |
| `main_west` | E_W → W_W | Spread westbound track, normal route through merge M, common west exit |
| `branch_out` | W_E → B_OUT | Shared east approach, reverse route through D, outward branch connection |
| `branch_in` | B_IN → W_W | Return branch, declared crossing, reverse route through M, common west exit |

This inventory does not promise every possible connection between the six ports. Directional permission and legal component traversal remain explicit. In particular, the geometric crossing does not create a turn from the return branch onto the eastbound main track.

Each variant contains **16 ports, 14 physical edges and two turnout components**. Every degree-one boundary is a declared external interface; there is no dangling internal connection. Route enumeration uses the component port relationships and the existing legal traversal machinery. Shared physical edges are represented once, even when two service routes traverse them.

A route can be topologically complete while terrain, speed applicability or construction representation remains unassessed. The result fields deliberately separate `complete_required_routes_connected`, geometric-screen acceptance, operational outcomes and construction authority.

## 3. Fixed local geometry and evidence types

The runnable fixture is [branch_fixtures/release.json](proof/branch_fixtures/release.json). Coordinates are local metres, not a geographic survey.

| Quantity | Selected value | Origin / interpretation |
|---|---:|---|
| Local longitudinal extent | 0–6,000 m | Authored junction-study boundary |
| Site lateral interval | −150 to +270 m | Authored unpadded plan boundary; not terrain permission |
| Main external rail ordinates | +1.7 m eastbound; −1.7 m westbound | Uses the retained 3.4 m nominal straight-track reference |
| Main rail height at interfaces | 20 m | Project datum |
| Spread westbound rail ordinate | −120 m | Deliberate space for a descending/rising return connection |
| Branch external rail ordinates | +241.7 m outbound; +238.3 m inbound | Parallel interface with 3.4 m nominal separation |
| Merge / divergence toes | x = 1,500 / 1,800 m | Authored insertion locations |
| Branch parallel boundary begins | x = 4,500 m | Authored connector boundary |
| Selected level change | ±7.5 m | Project crossing solution; zero in flat mode |
| Selected ramps / level plateau | 750 / 100 m | Search-selected dimensions |
| Radius / grade / vertical-radius screens | 300 m / 2% / 5,000 m | Project targets, not a universal UK design table |
| Formation length | 242.6 m | Retained manufacturer complete-unit reference, S060 |
| Main / branch motion caps | 60 / 15 mph | Uncalibrated, route-wide project motion inputs |

The local 300 m geometry screen is not a replacement for v0.9's 1,500 m corridor target. This is a different, explicitly declared junction profile; insertion into that corridor must re-evaluate the applicable per-route limits. The main/branch motion caps below are not validated speed ratings.

The nominal track-centre helper is called with its straight-track applicability. Its result is `reference_value`, not an adjacent-vehicle clearance pass. The curved transition geometry is assessed separately; this release does not claim that a 3.4 m y separation proves acceptable spacing everywhere along the branch curves. [S058](10_source_register.md#s058), [numerical profile](17_uk_numerical_profiles.md)

Published full-unit length is used for tail clearance and holding. It is not converted into one long rigid body, and it does not supply traction, suspension or exact bogie data. The existing vehicle evidence and assumptions remain unchanged. [S060](10_source_register.md#s060), [vehicle model](20_vehicle_envelopes_and_clearance.md)

### 3.1 Component geometry is immutable but still authored

Both D and M pass through the existing JSON component importer using `component_import_synthetic.json`. The supported bounded family requires its unmodified 40 m longitudinal span, 1.5 m branch offset and 0.075 branch-exit slope. The record hash, normalised geometry and rigid placement are preserved. An incompatible supplied geometry is rejected rather than stretched until it fits.

These values do **not** identify an approved UK turnout series. The component remains an authored synthetic centreline model with unresolved hardware, vehicle compatibility and speed rating. Source-qualified reference design can proceed with that explicit limitation; strict UK component approval cannot.

## 4. Horizontal connections with actual tangent conditions

The earlier corridor primitive forced horizontal tangents at every gate. This local junction adds a restricted arbitrary-slope connector useful at a turnout exit. It is not a general free-heading alignment solver.

For an x-monotone span of length L, end ordinates y0/y1 and end slopes m0/m1, the quintic Bezier control ordinates are:

`[y0, y0 + m0 L/5, y0 + 2 m0 L/5, y1 − 2 m1 L/5, y1 − m1 L/5, y1]`.

The x controls are equally spaced between the endpoints. This gives the requested positions and first derivatives, with zero second derivative at each end. The imported specialwork and adjoining curves are checked together for compatible endpoint, tangent and curvature conditions. A component's curve is not altered by a generic smoothing pass.

The two branch connectors also receive a Bernstein-polynomial lower-bound check on their relative y ordering over the shared x interval. This prevents an unintended extra plan intersection within this restricted family. It is an ordering test, **not perpendicular clearance, dynamic gauging or a full all-obstacle test**.

The selected control hull is x = 0–6,000 m and y = −120–241.7 m. Its conservative whole-candidate horizontal-radius lower bound is approximately **355.987 m**. The bound passes the declared 300 m project target. It is not a turnout speed certificate or proof of compatibility with every train.

## 5. Deriving the crossing and fitting its vertical profile

The crossing point is computed from the actual monotone return connector, rather than assumed to remain at a hand-written coordinate. In the selected fit it is approximately **(2,534.849 m, 1.7 m)** in plan.

The project crossing band extends four metres to either side of the eastbound track in y. Intersecting that band with the return curve gives an x interval of approximately **2,512.414–2,557.036 m**. This interval is used both for the geometric separation screen and for the crossing resource footprint.

The raised and lowered profiles reuse the v0.9 complete quintic ramp function `H(u)=10u³−15u⁴+6u⁵`. They contain a complete rise/fall, a level plateau and a complete return to the main rail datum before the merge or branch interface. Both height and its first two x derivatives match at the flat/ramp joins. No turnout is tilted to absorb a missing length of ramp.

The available connector interval is checked before accepting a proposed ramp. Thus a ramp can fail because it is too steep, because the full approaches do not fit, or because the crossing separation is inadequate. Those are distinct failures.

For the chosen 7.5 m change, the conservative maximum grade on 750 m ramps is **1.875%**. The chosen crossing has 7.5 m rail-level separation over its complete declared band against a **6.8 m project budget**: 4.5 m lower envelope, 0.8 m electrification reservation, 1.2 m structural depth and 0.3 m allowance. None is presented as a universal UK clearance.

The vertical-curvature calculation includes the horizontal metric of the return curve. Its upper bound in the selected case is approximately `8.2173e-5 1/m`, passing the 5,000 m project vertical-radius target. Lengths use numerical integration of the full three-dimensional metric, with the method recorded rather than an exact-chainage claim.

**Civil design remains incomplete.** The vertical budget does not produce a bridge deck, abutments, tunnel portals, drainage system, retaining walls, foundation solution or full vehicle/structure envelope. The diveunder's groundwater and drainage implications are not hidden by a successful level profile.

## 6. Bounded design search

The demonstration tests one flat candidate, plus two separated forms × four ramp lengths × two level changes. That is **17 candidate trials**. The ramp set is 600, 750, 900 and 1,050 m; changes are 6.5 and 7.5 m.

Five candidates pass the implemented screens: the flat layout and the 7.5 m raised/lowered layouts with either 750 m or 900 m ramps. The 600 m ramps exceed the chosen grade; 6.5 m does not meet the chosen crossing budget; 1,050 m ramps do not fit within the selected connector's complete approach interval.

Each mode retains its shortest accepted ramp, with stable parameter tie-breaking. This is not global optimisation or a cost ranking between flyover and diveunder. Limited work budgets return `search_exhausted`; a completed grid with no candidate would be a different outcome. A failed bounded family does not prove no other junction could fit. [Search record](proof/branch_results/geometry_search.json)

## 7. Geometry-to-resource compilation

The compiler derives physical-edge intervals, exclusive component bodies and compatible-state controller locks from the connected routes. A component's normal and reverse paths may require incompatible states even before their running-space conflicts are considered.

The flat crossing adds one exclusive named resource over the derived crossing footprint. Raised/depressed layouts omit that resource only after their ramp, profile and crossing-envelope screens pass. They do not delete the merge, divergence, shared running-track resources or any input requirement.

| Movement pair | Flat form | Separated forms |
|---|---|---|
| Main east / branch return | Shared crossing footprint | No shared crossing in this declared model |
| Main west / branch return | Shared merge and downstream west exit | Same shared merge and downstream west exit |
| Main east / branch outbound | Shared approach and divergence | Same shared approach and divergence |
| Main east / main west | Separate paths | Separate paths |

This is the central regression requirement: **a separated crossing cannot become an unqualified claim of an independent branch route**. The complete incoming branch still needs a compatible opportunity at its merge.

The general v0.5/v0.7 swept-body and proximity machinery is not silently treated as a completed 3D gauge here. This new local resource compiler covers the explicitly checked route/ordering/crossing family. It does not establish every possible adjacent-body or structure conflict. Such physical checks remain a separate admission stage before game construction.

## 8. Holding and operation are different contracts

The geometric holding check measures actual return-route length between the near crossing boundary and a proposed train-front stopping position. It checks both whether the physical tail clears the crossing and whether the selected entry/exit margins also fit.

No signal or stopping action is constructed. The current operating experiment schedules complete passes from the external boundary, with waiting outside the model. It does not yet simulate braking to this internal stop, holding on the gradient, restarting, or a spatial queue. The holding result cannot therefore claim a new operational headway or a verified signal location.

The operating and semantic-construction details, measured counterexamples and compact decisions are in [36](36_branch_junction_results_and_game_contract.md). The source/test evidence is in [37](37_v010_execution_and_handoff.md).

## 9. Production extension points

A production junction task should resolve required movements and boundaries, select a permitted topological family, fit its components and complete ramps, compile crossing **and merge** resources, evaluate representative train classes, and return the consequential alternatives. Most trial failures should stay local.

Before lowering to a real game adapter, add the actual terrain/obstacle snapshot and account for the spread tracks and structures within the authorised region. Engine representation may require different geometry primitives or supported junction assets. Read-back must then verify the legal movements and realised separation, not merely accept an acknowledgement.

The next integration step is terrain-aware placement into the corridor, followed by grade-aware practical performance and holding validation. It does not require reopening platform-furniture, crowd or specialist certification work for ordinary game-oriented design.
