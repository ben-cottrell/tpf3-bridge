# Terrain-aware passenger-junction placement

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.11.0 · **Date:** 21 September 2026  
**Implemented scope:** a connected branch junction refitted against the original corridor's terrain, protected land, site and main-line interface requirements. This is an offline, reference-inspired design study. It does not alter built track or construct real game assets. Station internals remain frozen at v0.8.

## 1. What changed

The local junction in [35](35_connected_passenger_branch_junctions.md) had complete movements, but its six-kilometre plan had not been tested against the river, ridge and protected land in [32](32_corridors_junctions_and_game_fit.md). A common span and matching rail height were not sufficient evidence that the two designs could be combined.

The new `railterrain` package gives each proposed junction a fresh terrain assessment. It preserves the original main-line endpoints, resolves the branch's additional interfaces explicitly, and refits the approaches while retaining the imported turnout shapes. Every physical edge is checked, including the spread westbound track and the branch's rise/fall ramps.

The design operation is **replacement of an unbuilt corridor proposal between fixed boundary ports**. It is not an overlay of two competing tracks, nor a live demolition-and-splice operation. The earlier corridor remains a historical design baseline. Its terrain pass is never inherited by the wider junction.

The product-level outcome is a useful bounded design choice: reject locations that enter protected land, place unsupported specialwork over water, or fail the original main-line targets; compare the remaining flat, raised and lowered arrangements using their actual connected geometry.

## 2. Retained inputs and authority

The new fixture is [terrain_fixtures/release.json](proof/terrain_fixtures/release.json). It names only two supported local source fixtures: the frozen corridor and local branch records. The parser rejects arbitrary replacement paths, duplicate search values, non-finite values, malformed identifiers, unbounded grids and unknown policy fields.

The corridor supplies its 6,000 m span, 20 m external rail datum, four main-line boundary positions, 3.4 m nominal straight-track centre interval, original site rectangle, river/ridge field, protected rectangle and main-line project profile. The branch supplies its two external branch positions, complete movement contract, selected ramp family and immutable authored component record. Exact hashes are in [input_provenance.json](proof/terrain_results/input_provenance.json).

The original station interiors are not regenerated. Both main-line directions must retain position, horizontal tangent and vertical gradient at each external interface. The two branch boundaries also retain their original absolute positions. Those branch ports are useful connection contracts, not evidence of an already constructed branch destination.

Internal point locations and the lateral placement of the junction are authorised search variables. The site, protected land, intended trains and main-line profile are not.

### 2.1 Realistic targets remain typed

The main line retains the earlier **60 mph project target, 1,500 m minimum-radius target, 1-in-100 gradient target, 5,000 m vertical-radius target and zero-cant acceleration/curvature-rate screens**. These are inherited project choices, not newly claimed national limits. The complete-unit formation length continues to use the retained manufacturer record. Its source and missing dynamics remain as documented in [20](20_vehicle_envelopes_and_clearance.md).

The local branch's 300 m screening floor does not replace the more restrictive main-line profile. Each physical edge used by either main-line route is checked against the original main-line requirements. An imported turnout's normal route and reverse route retain their different geometry; passing a curvature calculation still does not supply an authentic component speed rating.

No new standards clause, authentic turnout drawing or vehicle dataset was acquired in this increment. Existing numerical evidence remains source-qualified under [17](17_uk_numerical_profiles.md) and [the source register](10_source_register.md).

## 3. Refitting without deforming pointwork

The first implementation supports x-monotone tracks with level, x-parallel external interfaces. This restriction is explicit. It is not a geographically arbitrary placement engine.

For each candidate, the generator places the two authored turnout components at the selected merge and divergence locations. Lateral relocation is a **rigid translation**: every component control point moves by the same vector. Its local dimensions, source record, legal route pairs, state mapping and geometry hash are preserved. The optimiser cannot stretch the turnout to make a difficult site pass.

Plain-line approaches and exits are re-fitted using the existing quintic Hermite connector, preserving the required positions, tangents and zero endpoint second derivatives. The branch's internal connections and vertical ramp retain their component-relative geometry. Connections to the absolute external branch ports are then re-fitted separately.

Two explicit main-line nodes prevent an accidental crossing caused by moving the westbound track sideways earlier than the eastbound one:

**EAST_SPREAD** brings the eastern track to the selected internal corridor before the divergence. It uses the same longitudinal approach interval as the westbound spreading transition. The two tracks remain separately represented and their ordering is rechecked.

**EAST_RESTORE** defines where the eastern main line starts returning to its fixed eastern boundary. It keeps the declared branch crossing inside the straight central portion. The crossing cannot silently move onto an unassessed restoration curve.

The resulting network contains **16 physical edges, two turnout components and four complete required routes**. An edge shared by two routes is built and assessed once. All degree-one nodes are declared external ports; no internal connection is left open.

### 3.1 Continuous checks within the supported family

Bezier control-hull bounds, endpoint checks and the established network validator assess the refitted connections. Bernstein bounds check the ordering of the main tracks and of the outward/return branch paths over their common x intervals. These are continuous centreline-order checks in the supported family, not dynamic vehicle clearance or general three-dimensional collision detection.

The main-line speed screen uses local derivative bounds after subdivision. For an x-affine graph, a sufficient bound is:

`|dκ/ds| ≤ |y'''| + 3 |y'| |y''|²`.

Subdivision tightens those derivative bounds without moving any track or changing the requested speed. A failed sufficient bound means **not certified by this bound**. It is not automatically proof that the exact curve violates the engineering target.

The tests compare dense independently evaluated curvature and curvature-rate values against these bounds. That verifies the numerical implementation for this representation; it is not a validation of real train dynamics.

## 4. Terrain assessment follows physical infrastructure

The terrain service evaluates every physical edge, including both turnout traversals, the spread main line, branch connections and ramps. It does not repeatedly count the same main-line approach merely because both a main service and a branch service use it.

Each edge is divided at geometry/profile knots, the river boundaries and additional grid positions. River intervals therefore cannot be skipped by a long sample cell. A restricted Bezier control hull bounds the plan coordinates in each interval. The supplied quintic height profile is monotone between its knots, so its endpoint heights bound rail elevation over that interval.

The synthetic ridge is the previously authored compact polynomial field. Its extrema over a rectangular box are calculated from the separable bell-function bounds. Tests compare these bounds with dense ground samples. This method is specific to that analytic test terrain. A future game-terrain importer needs a separate interpolation and uncertainty contract; it must not claim the same guarantees for arbitrary sampled ground.

### 4.1 Classification, reservations and quantities are different

Midpoint ground and rail levels classify approximate surface, cutting, embankment, river bridge, viaduct and tunnel runs. Lengths are midpoint integration estimates. The output also retains an interval ground-height range rather than treating the midpoint as the whole interval.

Each interval receives a declared planning reservation. Its width includes a single-track formation half-width, construction margin and a bounded allowance for the selected open-cut/embankment model, or the declared structure width where larger. Longitudinal reservations stop at the explicitly open external interface; the model does not infer land or vehicle support beyond the boundary.

The resulting boxes screen the authorised site and protected land. Actual track-centre witnesses are distinguished from a conservative reservation-box intersection. Both can reject a candidate under this project's strict no-build policy, but only the former is a direct witness that the track enters the protected rectangle. No tunnel or bridge automatically obtains permission to pass above/below protected land: the current restriction applies through all elevations.

**These planning boxes are not certified full earthwork toes.** Transverse ground variation, deeper excavation, retaining walls, slope stability and structure assets remain unresolved. The calculation limits the open-earthwork allowance according to the declared civil policy; material beyond that scope requires structural/ground assessment rather than a larger invented earthwork calculation.

The package reports the union area of the supplied rectangles, avoiding double counting where reservations overlap. It does not claim that this area is a surveyed land purchase, an exact formation footprint or a construction cost. There is no fabricated earthwork-volume total for the joined multi-track geometry.

Civil run lengths are explicitly **track metres over unique physical edges**. They are not bridge counts, numbers of structures, or the single double-track-formation lengths used in the older corridor example. Those different metrics must not be compared without conversion.

## 5. Water and component/structure checks

For a river interval, the lower rail-height bound is checked against the retained deck depth, water level and freeboard assumptions. Raising the test water level can therefore invalidate an otherwise unchanged railway. The failure is attached to the actual affected edge and interval.

The initial civil/component policy does not support locating a turnout on a bridge, a high structure or a deep-cover segment. Such an arrangement returns `specialwork_structure_interface_unsupported`. This is **a limit of this study's component/structure integration**, not a claim that British railways prohibit points on structures.

That check exposes a real failure of simply reusing the prior local plan: its original merge at x=1,500 m lies within the retained river interval of x=1,400–1,650 m. The search must move the pointwork or later supply an explicit supported structural solution. It cannot call the local model complete and ignore the river.

The flyover/diveunder also carries a separate crossing reservation. It records the connected paths, crossing band and retained vertical budget. It is not a completed deck, abutment, portal, pier layout or drainage system. Groundwater and the practicality of the diveunder remain consequential open assessments.

## 6. The bounded search

The demonstration tests **two component-placement layouts × four lateral offsets × three crossing forms = 24 candidates**.

| Search axis | Values |
|---|---|
| Original toe arrangement | Merge 1,500 m; divergence 1,800 m; approach spreading complete at 1,200 m |
| East-shifted toe arrangement | Merge 2,000 m; divergence 2,300 m; approach spreading complete at 1,700 m |
| Internal lateral relocation | 0, 180, 280, 360 m |
| Crossing form | Flat, flyover, diveunder |
| Eastern main-line restoration start | Fixed at 4,200 m |

Every candidate uses the same external ports, protected rectangle and selected main-line profile. The search retains failed geometries and their reasons. Six candidates pass the scoped checks: the east-shifted layout at offsets 180 and 280 m in each crossing form.

The unshifted westbound track enters protected land. The original merge location encounters the unsupported river/pointwork interface. Wider or shorter approaches can fail the original main-line geometry screen even when the local branch's looser floor passes. These are different repairs; Python must not reduce them all to “junction does not fit”.

Within each crossing form, the demonstration selects least estimated tunnel track length, then reservation-union area, then physical track length. It retains a vector of alternatives and does not create a hidden financial score. Flat and separated forms are not ranked as interchangeable when the brief requires removal of the crossing conflict.

A zero or restricted budget returns `search_exhausted`. Completing this grid without a candidate would be `grid_complete_no_candidate`, not proof that another component family, topology or placement cannot work.

## 7. Evidence and execution binding

The geometry hash, source corridor hash, terrain bytes and revision, site constraints, main-line profile, component origin and civil-policy hash all contribute to the new design assessment. `verify_binding()` rebuilds the assessment and compares it with the supplied record rather than trusting a `passed` field.

Operation results are joined to that design identity. A timing result from the old unplaced junction cannot receive the new terrain pass merely because it has the same route names. The old component and operating modules remain frozen; their output schema versions identify the reused submodels, while the new wrapper identifies the terrain-qualified composition.

The construction demonstration checks current snapshot content in addition to revision labels, reserves the design's land/structure requirements before track operations, then performs semantic read-back. Full details and measured results are in [39](39_terrain_placement_results_and_mock_contract.md).

## 8. Production contract and remaining limits

A useful production request now has a concrete structure: preserve station/branch interfaces; choose permitted placement and crossing families; refit plain-line connections without deforming admitted pointwork; assess all terrain and protected-land interfaces; compile crossing **and merge** resources; compare fixed operating scenarios; return only the consequential alternatives to Astra.

This increment supplies that sequence for one restricted synthetic landscape. It does not supply arbitrary map headings, new station design, live existing-track replacement, complete structures, real terrain acquisition, dynamic gauging, gradient-sensitive traction, internal stopping, physical queues or a TPF3 adapter.

Those omissions remain separate from a useful GB reference-inspired game-design result. The next priority is **grade-sensitive performance and actual internal holding/restart checks** on the same terrain-bound candidate, not a return to detailed station furniture or specialist certification work.
