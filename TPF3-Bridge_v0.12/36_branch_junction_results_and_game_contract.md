# Connected junction results and semantic game contract

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.10.0 · **Date:** 21 September 2026  
**Executed:** 17 geometry trials; three connected junction forms; ten common scenarios per form, giving 30 operating comparisons; twelve geometric holding checks; eleven mock execution cases. No live game construction or actual railway capacity measurement.

## 1. Reproduce and inspect

From `proof/`:

```sh
python -m railbranch.demo --output branch_results
```

The fixture, source-qualified nominal spacing, existing manufacturer-length record and imported authored component are hashed in [input_provenance.json](proof/branch_results/input_provenance.json). The three variants use the same plan topology and service scenarios. Only the return connector's vertical arrangement changes.

This is a new **local** six-kilometre junction site. It has not inherited a passing terrain, river or protected-land assessment from the separate v0.9 corridor merely because both examples are six kilometres long. `terrain_or_game_validated` and construction authority remain false.

Inspect the complete [comparison](proof/branch_results/comparison.md), [search](proof/branch_results/geometry_search.json), [summary](proof/branch_results/summary.json) and individual traces before interpreting a single favourable metric.

## 2. Connected geometry: what is now different

Each variant contains four required boundary-to-boundary routes. The branch return has an actual curved path from its external interface, across the eastbound main track, through turnout M and onto the shared westbound exit. The outbound branch traverses turnout D and reaches its separate branch interface.

Selected numerically integrated route lengths are:

| Route | Flat | Flyover / diveunder |
|---|---:|---:|
| Main east | 6,000.000 m | 6,000.000 m |
| Main west | 6,014.916 m | 6,014.916 m |
| Branch outward | 6,013.146 m | 6,013.146 m |
| Branch return | 6,035.025 m | 6,035.131 m |

These numbers describe the authored local alignment, including its spread-track approach. They are not a reconstruction of Hitchin or a claim that this is the shortest practical passenger branch layout. The selected radius/gradient screens and complete ramp-fit tests are described in [35](35_connected_passenger_branch_junctions.md).

## 3. Operating model and comparison discipline

The proof uses a **whole-pass reservation planner**. For each required train, it derives front-arrival and tail-clear times along the actual route and reserves all of that pass's future resource intervals together. Individual intervals start relative to the predicted arrival at their location; they are not all held from the first boundary activation.

This differs from the deliberately conservative all-at-activation station release experiments. It does not establish a live signalling authority, moving-block operation or an actual TPF3 reservation sequence. It is an offline comparison policy, preserved identically across these three forms.

Times use nonnegative integer milliseconds and half-open intervals. Setup is applied before predicted front entry, release after tail clearance, with outward rounding. Reservations include physical running tracks, component bodies, controller states and the flat crossing footprint. An independent event-sweep checker examines all committed claims and closures.

The retained motion law starts each train at rest and uses a route-wide cap: 60 mph on main movements and 15 mph on branch movements, with 0.6 m/s² acceleration and the existing declared setup/release parameters. These are project inputs, not component ratings. A clear continuation outside the exit boundary is assumed long enough for the train's tail; no downstream external railway is generated.

**Gradient-dependent performance is not modelled.** The raised and lowered alternatives have equal path lengths and produce equal motion results because the retained law ignores their different traction/braking circumstances. This is an explicit missing performance model, not a finding that real flyovers and diveunders perform identically. The geometry nevertheless checks the gradients themselves.

The scheduler is deterministic and greedy. It moves to compatible event boundaries rather than asking Astra to try another time. Earlier choices are not globally backtracked. A computation limit or entry-wait limit remains distinguishable from no legal route. Required, scheduled, completed, residual and unscheduled demand are all retained.

## 4. Scenario set

The base scenario has six requests for each of four movements: 24 required passes. Repetition spacing, request offsets and the four-hour reporting horizon are authored test inputs, not a UK timetable or an acceptable-delay specification.

| Scenario | Purpose |
|---|---|
| `nominal` | Complete mixed movement accounting under the declared greedy policy |
| `crossing_pulse` | Main-east and branch-return requests timed to conflict at the flat crossing |
| `merge_pulse` | Main-west and branch-return requests timed to compete at the shared merge |
| `downstream_blocked` | Same merge test with the west exit unavailable for a fixed interval |
| `branch_return_closed` | Close the return connector; retain the affected required demand |
| `shared_west_exit_closed` | Close a shared exit used by both westward movements |
| `synthetic_300m` | Longer formation stress without assigning manufacturer identity |
| `short_horizon` | Keep scheduled but unfinished/future work at an early cutoff |
| `zero_budget` | Stop before scheduling without inventing an infeasibility proof |
| `zero_entry_wait` | Preserve the permitted-wait constraint even when a later route would work |

Pulse request times are generated once from the same flat reference timing and reused across all modes. They are not tuned separately to favour the separated candidates. The fixed downstream closure is 1,000–2,400 seconds on the declared west-exit resource.

## 5. The crossing benefit and the remaining merge

The table shows **total entry delay over scheduled requests**, in seconds. It is not platform departure delay or an estimate of railway capacity.

| Scenario | Required | Flat delay | Flyover delay | Diveunder delay |
|---|---:|---:|---:|---:|
| Nominal | 24 | 11,341.991 | 10,312.362 | 10,312.362 |
| Crossing pulse | 2 | 50.940 | 0.000 | 0.000 |
| Merge pulse | 2 | 262.403 | 262.419 | 262.419 |
| Downstream blocked | 2 | 2,660.461 | 2,660.445 | 2,660.445 |

All required requests in these four rows finish within the stated horizon. The large nominal delays are not evidence of a satisfactory service: the deliberately simple whole-edge resources, route-wide speeds, generous horizon and greedy policy remain restrictive.

The useful engineering finding is narrower. Separating the crossing removes the crossing-pulse delay in this model. **The merge test still delays trains in every form.** Both incoming flows must use the same merge component, controller state and west-exit tracks. The downstream closure remains a bottleneck even after the crossing is separated.

Millisecond-level differences in merge rows follow the numerical path length and timing law. They are not meaningful evidence that one physical scheme has superior real-world merge performance.

The branch-return closure leaves six of 24 requests unscheduled in every form. Closing the common west exit leaves twelve unscheduled. The zero-budget row has zero scheduled delay because no request was scheduled, not because the junction worked perfectly. The short-horizon row retains 24 scheduled residuals rather than dropping them.

### 5.1 Compact decisions for Astra

The demonstration's decision function first verifies candidate/resource/scenario/result identities and the independent-check result. It then applies required completion and any explicit delay threshold. It cannot substitute a different scenario or accept a result whose merge resources were removed.

A zero-delay crossing-pulse requirement leaves the flyover and diveunder forms eligible for further study. Applying the same requirement to the merge-pulse or downstream-blocked scenario leaves **no tested candidate**. The packet names the unresolved resource rather than claiming the crossing improvement solved the whole brief.

There is no automatic winner between the two separated forms. Their terrain, structures and grade-aware performance are unassessed. Those are consequential remaining choices, not a reason to invent a tiny weighted score. [Decision packets](proof/branch_results/decision_packets.json)

## 6. Holding room: tail fouling versus margin failure

The returning train moves towards decreasing x. The holding check measures the actual curved path from the western edge of the crossing footprint to a selected train-front stop. Two ten-metre project margins are evaluated separately from the bare formation length.

The following selected rows are for the **flat** geometry; separated modes are also recorded and differ slightly in three-dimensional length.

| Train length | Front-stop x | Available path | Required with margins | Physical tail clear? | Full margin check |
|---|---:|---:|---:|---|---|
| 242.6 m | 2,200 m | 316.398 m | 262.6 m | Yes | Pass |
| 242.6 m | 2,300 m | 215.324 m | 262.6 m | No | Fail |
| 300 m, synthetic | 2,200 m | 316.398 m | 320.0 m | Yes | Fail by about 3.602 m |
| 300 m, synthetic | 2,300 m | 215.324 m | 320.0 m | No | Fail |

This avoids conflating two different problems. In the second row the train itself would extend back across the crossing footprint. In the third, the body length clears but the desired allowances do not fit. Python can explain the appropriate design shortfall without treating both as the same collision.

The 242.6 m complete-unit length comes from the retained manufacturer record; the 300 m formation and margins are explicit stress inputs. [S060](10_source_register.md#s060), [all holding trials](proof/branch_results/holding_geometry_trials.json)

These are **geometric potential-holding checks**. No internal signal, braking movement or stop is constructed or simulated. Requests in the operating comparison still wait outside the model. A later physical queue model must validate braking room, stopping on the grade, restart, protection and the downstream movement before using this interval operationally.

## 7. Construction must preserve railway semantics

A corridor-only mock can compare vertex coordinates. A junction also needs to preserve shared physical edges, component identities, permitted turnout traversals, required states and non-connecting crossings.

The new adapter therefore produces **13 operations for the flat junction and 14 for each separated junction**. The plan contains two turnout objects with both permitted route geometries, ten remaining physical-track objects and one declared crossing relation. The separated forms add a civil reservation before associated track work.

Each physical edge is built once. Lowering one entire service route at a time would duplicate shared main-line track and could disconnect the intended turnout. The plan instead carries stable common node and component identities and lowers the complete physical network.

The prototype capability identifiers include `construct.junction_track3`, `construct.junction_turnout3`, `declare.junction_crossing`, `reserve.junction_crossing_envelope`, `query.junction_geometry_topology` and `query.operation_receipt`. **These are proposed bridge identifiers, not TPF3 API names.** The real-game manifest keeps them unknown until actual probes establish support.

Polyline lowering has a 0.02 m centreline interpolation target. Read-back allows a declared 0.05 m positional tolerance, but component state, legal routes, identities and source fields must match exactly. A coordinate tolerance cannot excuse a different turnout connection.

### 7.1 Inspect current state, not only the old receipt

The execution controller queries the current stored mock object after acknowledgement or receipt recovery. An old receipt may establish that an action happened; it does not prove the object is still correct. A test mutates the realised edge after receipt and confirms that inspection detects the mismatch.

The final whole-network check verifies connectivity along each of the four required routes and the declared non-connection and separation at the crossing. This is semantic read-back of the mock, not a train actually traversing the game.

| Mock case | Outcome |
|---|---|
| Clean flyover; flat; diveunder | All operations and final route semantics verified in memory |
| Repeat an already applied plan | Same effects; no duplicate construction |
| Lost acknowledgement after application | Receipt reconciled, current object checked, no duplicate write |
| Deliberately displaced coordinate | Execution stops at realised-geometry mismatch |
| Corrupted turnout state | Execution stops at semantic mismatch even with plausible coordinates |
| Injected rejection | Partial-effect ledger retained; no assumed rollback |
| Stale world or terrain | Preflight blocks all writes |
| Unprobed TPF3 capability manifest | Preflight blocks all writes |

The full demo contains eleven cases, counting the three clean forms separately. The tests add resume, stale receipt, altered node, invented crossing-turn and malformed-data cases. [Mock execution evidence](proof/branch_results/mock_execution_cases.json)

## 8. Interpretation boundary

This release demonstrates a connected local branch, the distinct effects of crossing and merge conflicts, length-aware holding screens and a tested semantic construction contract. It does not demonstrate real terrain insertion, railway capacity, realistic traction on grades, authentic turnout/crossing hardware, dynamic vehicle clearance, drainage, constructed signals or a TPF3 mod.

The next useful product increment is to insert and refit the local junction against an actual corridor/terrain interface, with its spread-track and structural land take visible. Grade-aware timing and genuinely modelled holding should follow the same candidate rather than borrowing a favourable result from another geometry. Station interiors remain outside that next step.
