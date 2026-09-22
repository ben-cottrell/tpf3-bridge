# Terrain-bound junction results and mock construction contract

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.11.0 · **Date:** 21 September 2026  
**Executed scope:** 24 placement trials, three selected crossing forms, 12 operating comparisons, changed-constraint/refinement trials and 12 mock execution cases. No game construction or empirical railway-capacity validation.

## 1. Reproduce the experiment

From `proof/`:

```sh
python -m railterrain.demo --output terrain_results
```

The runner reads the frozen corridor and branch fixtures plus the new bounded placement policy. It builds complete physical networks, screens main-line geometry and terrain, retains the common external ports, applies the existing operating model and emits a new terrain-bound construction plan.

Inspect [placement_search.json](proof/terrain_results/placement_search.json), [input_provenance.json](proof/terrain_results/input_provenance.json) and [comparison.md](proof/terrain_results/comparison.md). The older corridor/junction outputs retain their historical identities; they have not been relabelled as new successful terrain builds.

## 2. What the search found

Six of 24 candidates pass the implemented geometry, boundary and terrain checks. The selected instance within each form uses the east-shifted toe arrangement and a 280 m internal lateral relocation.

| Item | Selected location or result |
|---|---|
| Merge toe | x=2,000 m; y=160 m |
| Divergence toe | x=2,300 m; y=281.7 m |
| Eastern main restored towards its fixed end | From x=4,200 m |
| Return crossing centre | Approximately x=2,900.715 m; y=281.7 m |
| Crossing footprint in x | Approximately 2,882.494–2,918.731 m |
| Raised/lowered rail difference | 7.5 m under the retained project envelope |
| Raised/lowered ramps | 750 m each, plus a 100 m plateau |
| Physical network | 16 edges, two turnouts, four required movements |
| Exact preserved external ports | Four main-line ports and two branch ports |

The external station coordinates, heights and tangents remain unchanged. The 280 m relocation is an internal layout decision, not a shift of either station. Component geometry is rigidly placed; only allowed plain-line connections are re-fitted.

The selected main-line curvature lower-bound values range down to approximately **1,814.873 m**, above the unchanged 1,500 m project minimum. The intended 60 mph zero-cant project screens also pass. This does not supply an authentic turnout rating or calibrated vehicle dynamics. [Flyover geometry](proof/terrain_results/flyover__geometry.json) · [Terrain-bound assessment](proof/terrain_results/flyover__terrain_binding.json)

### 2.1 Why other placements fail

The original merge lies over the river and needs an unsupported pointwork/structure integration. Unshifted layouts put the westbound approach inside the protected southern rectangle. A 360 m lateral relocation in the east-shifted family avoids the protected land and much of the ridge, but fails the retained main-line radius-bound screen.

Consequently Python cannot choose the widest detour merely because it has a favourable tunnel estimate. A failed required geometry check is applied before terrain preference scoring. Conversely, a conservative geometry bound that does not certify a curve is not an impossibility proof for every other family.

## 3. Terrain now distinguishes the civil alternatives

Selected planning quantities from the 40 m maximum study grid are:

| Form | Estimated tunnel track metres | Estimated river/viaduct track metres | Reservation-box union area |
|---|---:|---:|---:|
| Flat | 436.452 m | 500.499 m | 265,131.8 m² |
| Flyover | 436.452 m | 704.188 m | 268,249.9 m² |
| Diveunder | 1,083.258 m | 500.499 m | 281,684.9 m² |

These are **track metres counted once per physical edge** and a union of authored planning rectangles. They are not individual bridge lengths, structure counts, surveyed land or construction cost. Two tracks crossing the same river contribute two track lengths even if a future asset spans both; shared service routes do not multiply those lengths.

The widened junction still meets part of the ridge even when the older two-track bypass did not require a tunnel in its own model. Terrain evidence belongs to the actual candidate, not the place name or span.

The flyover reserves additional elevated track, whereas the diveunder increases the modelled tunnel exposure. No automatic real-world winner follows: portals, supports, drainage, groundwater, actual game assets and grade-sensitive traction remain unassessed. The flat form has a different operating capability because it retains the crossing conflict.

### 3.1 Refinement exposes quantity uncertainty

The same flyover geometry and terrain are re-evaluated with a 20 m maximum study grid. Its estimated tunnel exposure becomes **480 m**, and its planning rectangle-union area becomes approximately **236,440 m²**. The railway and ground have not changed. Smaller curve boxes and different midpoint classification near a threshold change these planning quantities.

This is precisely why the output does not call 436.452 m an exact tunnel design or the rectangle union a measured land footprint. Further refinement and actual portal/structure selection are needed before treating the quantities as construction commitments. The coarse and refined cases both pass the current scoped land/water screen. [Changed constraints and refinement](proof/terrain_results/changed_constraints_and_refinement.json)

The same file records two genuine brief changes. A narrower site rejects the northern design instead of moving the boundary. Raising the water level to 18 m fails the retained river-deck-clearance screen. Zero and two-candidate budgets remain explicit incomplete searches.

## 4. Complete movement results on the placed geometry

The operating scenarios are generated once from the selected flat instance and reused unchanged across all three forms. They include normal mixed movements, a deliberately timed crossing conflict, a timed merge conflict, and a blocked common downstream exit.

| Scenario | Required passes | Flat total entry delay | Flyover / diveunder total entry delay |
|---|---:|---:|---:|
| Nominal | 24 | 9,826.094 s | 9,826.494 s |
| Crossing pulse | 2 | 49.714 s | 0.000 s |
| Merge pulse | 2 | 337.362 s | 337.378 s |
| Downstream blocked | 2 | 2,735.418 s | 2,735.404 s |

Every required pass in these rows completes within the declared four-hour horizon. The large nominal delays are not evidence of an attractive service. This remains a greedy whole-pass resource planner with simple resources and route-wide speed caps. Its results should not be converted into a real trains-per-hour estimate.

Two conclusions are supported within the model. First, the crossing-pulse conflict disappears when the connected return line passes above or below the eastern main. Second, the shared merge and exit still impose delay. The terrain refit does not erase those resources or permit a train to turn at the geometric crossing.

The nominal separated result is very slightly worse than the flat result in this particular greedy schedule. That does not overturn the removed crossing conflict: a local feasible-set improvement need not improve every outcome of a fixed greedy ordering, and tiny timing differences are not civil-design rankings.

Gradient-dependent traction and braking are still absent. Flyover/diveunder equality follows from the existing motion model, not evidence that their real performance would be identical. Internal stops and spatial queues are also absent; requests wait outside the simulated boundary.

Each operating result retains its original submodel hash and adds a terrain-design hash, terrain-assessment hash and joined-result hash. The decision function rejects mismatched scenarios or stale joins. [Decision packets](proof/terrain_results/decision_packets.json)

A zero-delay crossing objective leaves the two separated forms as alternatives. A zero-delay merge or blocked-exit objective leaves no qualifying design in this tested set. Required completion precedes delay preferences; no train is removed to make the comparison look better.

## 5. One physical construction plan, with land reserved first

The selected flyover emits **17 mock operations**: one terrain/land reservation, one crossing civil reservation, two turnout objects, twelve other physical track objects and one non-connecting crossing relation.

The terrain reservation contains all selected interval boxes and the associated structure requirements. It precedes track work in the dependency chain. It is not itself excavation, ground levelling, bridge construction or a tunnel portal asset. The controller builds the replacement physical network once; it does not additionally emit the superseded two-track corridor or duplicate a shared approach per service route.

The record is [selected_mock_plan.json](proof/terrain_results/selected_mock_plan.json). Its source snapshot, terrain contents/revision, site constraints, geometry and design assessment are bound together. All new operation names are proposed bridge capabilities, not real TPF3 API identifiers.

### 5.1 Content changes matter even when a label does not

A revision string is useful but insufficient. The mock compares both the revision and actual snapshot content. Changing ridge height while retaining the same revision label blocks execution before any write. Adding a protected rectangle also blocks the old plan.

The controller checks the snapshot before every operation and after receipt/read-back. A fault-injection case changes the test terrain after the first reservation. Execution returns `environment_changed`, retains that one effect and performs no next write. No rollback is assumed.

This is important for the eventual game bridge: a cached plan must not outlive a terrain edit or changed protected asset simply because a coarse version label or earlier receipt still looks familiar.

### 5.2 Executed cases

| Case | Observed mock result |
|---|---|
| Clean run | All 17 operations and final route semantics verified |
| Repeat the same plan | Still 17 effects; no duplicates |
| Lost acknowledgement for the land reservation | Reconciled from receipt and current state |
| Lost acknowledgement for track work | Reconciled without duplicate construction |
| Changed terrain bytes, same revision label | Preflight blocked; zero writes |
| Changed protected land | Preflight blocked; zero writes |
| Terrain changes after the first write | Execution stops; one reservation remains |
| Deliberately displaced track coordinate | Read-back mismatch; execution stops |
| Corrupted turnout state | Semantic mismatch; execution stops |
| Injected construction rejection | Partial-effect ledger retained |
| Stale world revision | Preflight blocked |
| Unprobed game manifest | Preflight blocked; no fabricated game access |

Detailed receipts and outcomes are in [mock_execution_cases.json](proof/terrain_results/mock_execution_cases.json). The underlying topology checker verifies legal shared-edge routes and the absence of an invented crossing turn. No train has actually traversed a game asset.

The adapter's current snapshot is an in-memory copy of the analytic test field. It is not a live terrain query, and this test does not demonstrate that TPF3 exposes the required data. [Unprobed capabilities](proof/terrain_results/tpf3_unprobed_capabilities.json)

## 6. What Astra receives

A normal result reports the fixed brief, accepted alternatives, a few principal terrain/movement differences, the remaining merge constraint and the unresolved game/structure gate. The 24 trial records, 515-cell selected terrain assessment, resource claims and operation receipts remain in local artifacts for inspection.

This preserves the intended division of responsibility: Astra chooses among material design alternatives; Python owns the geometry trials, constraint checks, routine repair and reconciliation. The local runner makes no model or game calls. That verifies its execution structure, not any particular saving in billed plan usage.

## 7. Next engineering task

The terrain-qualified crossing forms should now be tested with **grade-sensitive train motion, braking to a defined internal holding point, and restart after waiting**. The same formation, geometry, resource footprints and terrain identity should drive those calculations. The expected result is not another detached physics demonstration: it should determine whether an actual proposed holding arrangement is useful, or still fouls the crossing/merge.

Actual structure-asset selection and a live capability probe remain separate integration tasks. Detailed station internals, crowd circulation and specialist real-world certification are not prerequisites for this ordinary game-oriented workflow.
