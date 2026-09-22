# Worked corridor, crossing cells and mock construction results

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.9.0 · **Date:** 21 September 2026  
**Executed scope:** twelve corridor candidates, nine crossing-cell trials, changed-brief/budget experiments, and nine mock execution cases. No real game construction.

## 1. The fictional railway brief

Connect two existing station-side double-track interfaces 6 km apart. Both sets of rails are at height 20 m, on level, x-parallel tangents, with the source-qualified 3.4 m nominal centre interval. Preserve those boundary conditions and leave the station interiors untouched.

The authored study site is x = −5 to 6,005 m and y = −1,200 to 1,200 m. It contains a river crossing between x = 1,400 and 1,650 m, a ridge centred at x = 2,700 m and a protected southern rectangle. All terrain, demand-independent civil dimensions and world coordinates are synthetic.

The main route target is 60 mph with maximum grade 1 in 100, minimum horizontal radius 1,500 m, minimum vertical radius 5,000 m and zero cant. These are project settings, not a claimed generic British standard. The origin/type distinction is in [32](32_corridors_junctions_and_game_fit.md).

The three interior longitudinal gates are 1,800, 3,000 and 4,800 m. The first two can move laterally together and share a rail height; the third returns to the fixed final tangent. The search tests lateral displacements 0, +180, +280 and −280 m, and plateau rail heights 20, 24 and 28 m.

## 2. What the corridor search found

Nine of the twelve candidates pass the selected project-bound and site screens. All three southern alternatives encounter the protected area and retain explicit formation-contact witnesses. They are not included among acceptable alternatives, even though their geometric lengths resemble the corresponding northern routes.

Selected executed rows are below. Tunnel/elevated lengths and earthworks are terrain-grid planning estimates. Track length is a 3D integration estimate. Neither establishes a completed civil design.

| Candidate | Mean length per track | Estimated tunnel | Estimated elevated section | Estimated cut + fill |
|---|---:|---:|---:|---:|
| Direct, rail plateau 20 m | 6,000.000 m | 600.000 m | 250.000 m | 53,763.412 m³ |
| +180 m offset, rail plateau 24 m | 6,025.563 m | 160.000 m | 250.385 m | 113,718.425 m³ |
| +280 m bypass, rail plateau 20 m | 6,061.280 m | 0.000 m | 250.929 m | 50,421.792 m³ |

The useful decision is concrete: the direct route is shortest but passes through the ridge; the larger northern bypass adds approximately **61.28 m per track** and avoids the tunnel under this terrain model. Elevating an intermediate route can reduce tunnel need but increase earthworks or viaduct length. There is no hidden financial valuation.

The full grid and all failure evidence are in [corridor_search.json](proof/corridor_results/corridor_search.json); the [comparison](proof/corridor_results/comparison.md) lists every row. Seven candidates are nondominated across the four raw estimated objectives. The default [decision packet](proof/corridor_results/decision_packet.json) displays two clear alternatives rather than sending every candidate or grid iteration to Astra.

The lowest-estimated-earthwork bypass is used for the mock lowering demonstration only. It is not a global optimality result or a user-approved construction choice.

## 3. Geometry and station-boundary preservation

The two tracks are genuine normal offsets of the reference alignment, not y-shifted copies. The shared normal cross-section remains 3.4 m across the curve, and each track's curvature, grade and vertical curvature are checked independently.

Both external station interfaces retain their exact x/y/z positions and zero heading/grade. There are no platform edits. The current kernel's waypoint headings and grades are restricted, so this fixture does not demonstrate arbitrary incoming station directions.

The exported track polylines retain the parent geometry identity, offset, parameter positions and a positional interpolation bound. The mock batches' maximum bound is about **0.018805 m**, below the selected 0.02 m lowering target. That is a centreline geometry bound, not a vehicle swept-envelope result. [Track polylines](proof/corridor_results/selected_track_polylines.json) · [Mock plan and lowering certificates](proof/corridor_results/mock_construction_plan.json)

## 4. Increasing speed or compressing the map is a new design problem

The changed-speed test raises the target to 100 mph without silently reducing it later. Some previously acceptable curved alternatives fail the zero-cant acceleration/curvature-rate screens under that target.

The shorter-route experiment changes the longitudinal corridor to 3.6 km and refits within its new gates. Track spacing and formation-length inputs are not rescaled. Its result is recorded as a different brief rather than substituted for the 6 km study.

The zero-candidate budget returns `search_exhausted`; a two-candidate budget also remains incomplete. Each result reports explored scope. This is not evidence that an unsearched route family is impossible. [Changed-brief and bounded-search trials](proof/corridor_results/bounded_and_changed_brief_trials.json)

## 5. Full approaches matter at a grade-separated crossing

A separate crossing cell is positioned at x = 5,400 m in the corridor's final straight zone. Its local branch direction crosses both main tracks. The model evaluates flat, raised and depressed paths, including their complete rise/fall approaches and central plateau.

The project rail-separation budget is **6.8 m**: 4.5 m lower envelope, 0.8 m electrification reservation, 1.2 m structural depth and 0.3 m allowance. These are declared study assumptions, not an imported universal UK clearance. The chosen level difference is 7.5 m.

| Raised/depressed cell | Total approach span | Maximum gradient bound | Crossing separation | Outcome |
|---|---:|---:|---:|---|
| 600 m ramps + 100 m plateau | 1,300 m | 2.34375% | 7.5 m | Gradient exceeds the 2% project target |
| 750 m ramps + 100 m plateau | 1,600 m | 1.875% | 7.5 m | Project ramp and crossing screens pass |
| 900 m ramps + 100 m plateau | 1,900 m | 1.5625% | 7.5 m | Project ramp and crossing screens pass |

The shortest cell has enough separation at the crossing but unacceptable approaches under the chosen target. It retains the model's two crossing conflicts rather than claiming grade-separated independence from a centre-point height check.

The valid raised/depressed cells remove those two named crossing conflicts within their own simplified resource model. Flat cells retain them. None creates a turning connection at a geometric intersection. [Crossing-cell records](proof/corridor_results/crossing_cells.json)

**This is not yet a connected passenger branch junction.** The upstream turnout, connecting alignment, branch continuation and merge remain open interfaces. The [corridor/cell join record](proof/corridor_results/corridor_crossing_join.json) verifies the common crossing datum and hashes while explicitly recording the missing physical connections. No full-junction throughput or construction claim follows from the cell result.

## 6. A holding length is not a braking distance

For the retained 242.6 m formation-length reference and two 10 m project margins, the static holding requirement is **262.6 m**. A 250 m interval is short by 12.6 m; 275 m and 300 m intervals meet that simple geometric requirement.

The separate 60 mph, 0.7 m/s² braking and two-second reaction example needs approximately **567.531 m** under its level constant-deceleration assumptions. Thus a 300 m interval can fit the train yet fail this approach-braking screen. No actual signal is placed and none of those margins or performance settings is a national signalling value. [Holding and braking](proof/corridor_results/holding_and_braking.json)

## 7. The 52-operation mock plan

The selected bypass produces **52 ordered operations**: explicit corridor track batches and bridge reservation batches. It does not include the disconnected branch cell or alterations to station internals. Structure dependencies precede associated track batches. Every operation has an immutable content-derived ID and stable endpoint-node IDs.

| Mock case | Actual result | Effect retained |
|---|---|---|
| Clean run | `mock_verified` | 52 applied operations |
| Repeat the same plan | `mock_verified` | Still 52; no duplicate effects |
| Lose one acknowledgement after applying the effect | `mock_verified` after receipt reconciliation | 52; no blind retry duplication |
| Snap a realised vertex by 0.2 m | `realised_geometry_mismatch` | Stops after two operations |
| Reject the second operation | `partial_failure` | First effect remains in the ledger |
| Unknown capability | `preflight_blocked` | Zero writes |
| Stale world revision | `preflight_blocked` | Zero writes |
| Changed terrain revision | `preflight_blocked` | Zero writes |
| Use the unprobed TPF3 manifest | `preflight_blocked` | Zero writes |

The comparison tolerance is 0.05 m in this mock's ordered-vertex representation. Acknowledgement alone does not establish success. Stopping after a mismatch does not remove the already applied effect, and no atomic rollback is claimed. [Mock execution cases](proof/corridor_results/mock_execution_cases.json)

The mock validates its own ordered vertices, payloads and node identities. Actual TPF3 snapping, route connectivity, structures and train passage still need a real adapter and observations. A `mock_verified` status must never be relabelled `game_verified`.

## 8. What Astra receives

The packet contains the brief identity, two displayed alternatives, relevant dimensions/estimates, the demonstration choice, the principal missing junction connection and the unprobed game status. The large grid, geometry, classifications and receipts stay local.

No model calls occur inside these runners. That verifies local orchestration structure, not an actual percentage reduction in plan credits. The eventual measurement must compare equivalent accepted in-game tasks with failures and omitted requirements counted.

## 9. Next implementation gate

The next useful work is a **real adapter capability/terrain probe and the missing branch-turnout/continuation composition**. Keep station internals frozen. Before a real build, resolve the live engine construction and read-back contract; before a full junction claim, connect its actual route geometry and check the resulting merges and holding positions.

This release deliberately does not substitute a large abstract operating simulation for those missing physical connections.
