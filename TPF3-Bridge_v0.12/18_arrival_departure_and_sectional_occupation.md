# Two-approach platform bank, train stopping and sectional occupation

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.4.0 · **Date:** 20 September 2026  
**Status:** Generated synthetic geometry with an executed longitudinal-motion and reservation experiment. Two directional external leads feed a shared four-platform bank. This is not the full eight-platform station, real signalling design or a game-constructed asset.

## 1. What changed from v0.3

The previous platform-bank proof used one bidirectional boundary and whole-leg constant-speed reservations. The new `railops` package adds separate arrival and departure boundaries, an analytic stopping trajectory, geometry-linked resource footprints, sectional release and a directly comparable whole-route baseline.

The implementation does not infer signalling authority from geometry. Edge IDs define **synthetic sections** for the experiment. Control-state semantics remain explicit component data. Every selected route acquires its resource set at activation; only its release times change between policies.

The reference UK numbers and the numerical-profile admission work are in [17](17_uk_numerical_profiles.md). They do not silently reclassify the synthetic specialwork or motion parameters.

## 2. Module contracts

| Module | Inputs | Output / responsibility |
|---|---|---|
| `railops.access` | Existing fan, bounded access parameters, geometry profile | A checked two-lead assembly with explicit permitted arrival/departure routes |
| `railops.motion` | Path distance, acceleration/brake bounds, speed cap and endpoint condition | Analytic distance/speed/time functions and phase records |
| `railops.sectional` | Compiled route, train length, motion profile and release mode | Spatial resource footprints, approximate occupation times and reservation intervals |
| `railops.operations` | Complete visits, closures, budgets and horizon | Greedy whole-visit assignments, conflicts, conservation and residual states |
| `railops.uk_profiles` | Scoped numerical input and reviewed parameter register | Specific rule results, reference values, guidance calculations and admission status |
| `railops.demo` | Versioned local JSON fixture | Reproducible comparisons, full evidence and compact decision packet |

The v0.2 `railproof` and v0.3 `railgeom` packages remain regression baselines. The new package composes their established geometry/calendar contracts rather than rewriting their historical assumptions in place.

## 3. Explicit arrival and departure access

The generated bank has four platform roads and eight directed service routes: each platform has an arrival from `ARRIVAL` and a departure to `DEPARTURE`. There are **30 physical edges and 79 resource records** in the compiled default example. [Compiled model](proof/sectional_results/dual_access_compiled.json)

The access pattern places a facing/tailing synthetic turnout arrangement before the existing fan. Its selected normal state admits the arrival lead; its reverse state serves the departure lead. The return alignment brings the departure track back to a parallel external boundary.

| Synthetic boundary / parameter | Value |
|---|---:|
| Arrival boundary | (-400 m, 0 m) |
| Departure boundary | (-400 m, -12 m) |
| Access toe | (-20 m, 0 m) |
| Access component longitudinal span | 60 m |
| Authored branch slope | 0.08 |
| Common link to original fan boundary | 20 m |
| Existing platform road positions | y = 0, 12, 24, 36 m |
| Boarding intervals | x = 650–910 m |
| Rear stopping marker | x = 655 m |

These are new synthetic subassembly boundary conditions. The negative approach coordinates extend outside the original document-12 illustrative rectangle. No claim is made that this assembly fits that original brief without a boundary transformation and a complete authorised redesign.

The new connection checks include the return curve, common link and each route through the fan. A too-short approach corridor is rejected; the software does not introduce an unseen kink or reverse the connector to make it fit.

### 3.1 Separate leads do not remove the common conflict

All platform routes still traverse `component_body:ACCESS`. Arrival and departure request different control states. The fan and some proximity exclusions are also shared. Therefore this is **directional access to a common bank**, not independent arrival and departure distribution all the way to every platform.

The physical graph cannot turn from the arrival lead straight onto the departure lead through the two exits of the same turnout. A modelled reversal would be a separate activity; it is not created by an undirected Y-shaped graph.

This distinction should survive into the eventual topology generator. To obtain genuinely independent movements it must change the component arrangement and demonstrate the resource independence, not rename a boundary.

## 4. Train-position convention

For an arrival, let `D` be the measured route length from the external boundary to the platform's rear marker and `L` the train length. The train front starts at the boundary and follows a distance of `D + L`. It stops with its rear at the marker and its front inside the storage road.

Reversal changes which end is the front. The outgoing front begins at the marker; it travels the outgoing route plus one train length so that the tail clears the exit boundary. That final train-length continuation is an explicit assumption of a clear external line, not generated or checked downstream infrastructure.

Scalar fit still requires the train plus both stopping margins to fit the boarding interval. The platform edge, storage track and marker remain distinct records. Buffer energy absorption, overrun provision, train doors and full passenger access are not inferred from the scalar fit.

The starting boundary assumes a train ready at rest. This is not a moving mainline entry-speed model. A future trajectory interface should accept verified entry/exit speeds and an upstream/downstream continuation rather than treating every station-area boundary as a stop.

## 5. Analytic level-track motion

The model has one route-wide speed cap `v`, acceleration magnitude `a` and braking magnitude `b`. It starts at rest. For an arrival distance `S`, the peak speed is:

\[
v_p = \min\left(v,\sqrt{\frac{2S}{1/a+1/b}}\right).
\]

The acceleration and braking distances are `v_p²/(2a)` and `v_p²/(2b)`. Any remaining distance is traversed at the peak speed. A short arrival has a triangular speed profile; a longer arrival has acceleration, cruise and braking phases.

For a departure that need not stop at the model boundary, the peak is `min(v, sqrt(2aS))`; there is no invented braking phase after the boundary. Each phase has the ordinary constant-acceleration relationship:

\[
x(t)=x_0+v_0t+\tfrac12at^2.
\]

The implementation returns an analytic inverse `t(x)` using a numerically stable quadratic expression. It rejects requests outside the motion's distance/time interval rather than extrapolating. Tests check phase continuity, monotonic distance, speed limits, endpoint conditions, inverse consistency and an independently written speed integral.

This is not a calibrated British multiple-unit performance model. Gradients, resistance, power curves, adhesion and jerk limits remain outside the current scope. The project-selected numbers are recorded in the fixture and are not labelled standards.

## 6. Geometry-derived spatial resource footprints

A compiled route already has ordered physical edges, upper/lower length brackets and control/proximity requirements. The new compiler uses cumulative upper-length values as its operational path metric. It does not mistake the Bezier parameter for distance.

Each resource obtains the union of the implicated edge extents along that route. If the same resource occurs more than once, the current compiler conservatively retains a continuous footprint from its first entry to its last exit. It does not release and reacquire that resource between occurrences.

Physical edge occupation uses the edge identity. Component bodies and control groups use their declared component relationships. A proximity resource covers the relevant complete edge extents, even when the detailed contact occupies less of them. This can over-reserve space but preserves the existing conservative proxy.

The numerical path length is a geometry-derived surrogate using upper bounds. It is not a formal interval-certified train-motion calculation: differences in acceleration and stopping profiles also affect the time mapping. The current error scale and provenance stay in the geometry export; a production timing tolerance must be specified separately.

## 7. Sectional release without invented moving-block authority

For a resource ending at path position `s_end`, its physical tail-clear time is approximated by `t(s_end + L)`. Setup time and the declared release delay are applied separately.

The two implemented policies are:

**Whole route:** acquire all locks at activation and release them after the entire leg's tail-clear motion plus release delay.

**Sectional release:** acquire the same locks at the same activation, then release each one after the train tail has cleared that resource's final footprint plus release delay.

All times are integer milliseconds. Tail-clear/release calculations round outwards with `ceil`; the illustrative front-entry observation rounds down. The fixed release delay is a project input, not an authentic signal-timer value.

A later route may use a released upstream resource while the first train continues elsewhere, only if all other required resources are compatible. This is not just-in-time acquisition, a signal-aspect model or a reconstruction of a British interlocking. Actual overlaps, flank protection, track circuits and release dependencies still require an admitted operating profile.

### 7.1 A directly inspectable timing example

For a 160 m train on the P4 arrival, the generated route is about **1,056.732 m**. The stop is reached **196.828 seconds** after activation, including setup. The final release is **199.828 seconds**.

Under whole-route release, the access component remains reserved until that final time. Under the synthetic sectional policy, its reservation ends at **94.118 seconds**. The train has not vanished or completed its visit: it continues to the platform and holds its required downstream resources. [Example leg records](proof/sectional_results/example_legs.json)

The timing difference follows from this explicitly authored section model. It is not evidence of the release timing at Waterloo, New Street or another real location.

## 8. Complete-visit scheduling and persistent platform occupation

For each visit, Python considers fitting platforms with both legal routes. It searches for an incoming activation, computes actual stopping time, applies the declared dwell/turnround/dispatch activities, waits for release of incompatible incoming state locks, then searches for an outgoing activation.

The berth and its storage-edge exclusions remain held continuously from the incoming activation to the outgoing tail-clear/release. This deliberately conservative storage reservation prevents a second train being assigned to the same platform merely because the first has finished its arrival route.

When the whole holding interval conflicts, the arrival is shifted and the complete opportunity is reconsidered. The selected alternative minimises departure delay, then entry time and platform ID. Earlier visits are not backtracked. Budget exhaustion, no legal opportunity and an entry-wait limit remain different outcomes.

A successor working cannot depart using stock that has not completed its predecessor and explicit external cycle. Empty-stock departures consume railway resources even without passengers.

This is still a greedy offline reservation scheduler, not a dispatching agent observing live signals. A shorter resource lock can enlarge the feasible set, but a greedy policy is not guaranteed to discover the globally best schedule within it.

## 9. Executed paired-policy comparisons

Nine scenarios run against both policies, producing **18 comparisons**. The geometry, traffic, stock, motion parameters and reporting horizon are identical within each pair; only the release policy changes. Scenario hashes are exported to enforce that comparison.

| Scenario | Whole-route scheduled | Sectional scheduled | Whole-route total departure delay | Sectional total departure delay |
|---|---:|---:|---:|---:|
| Nominal | 12/12 | 12/12 | 16,779.354 s | 10,568.224 s |
| Bunched arrivals | 12/12 | 12/12 | 22,719.354 s | 16,507.522 s |
| P1 closed | 12/12 | 12/12 | 16,787.529 s | 10,572.545 s |
| Longer trains | 12/12 | 12/12 | 17,924.675 s | 16,780.590 s |
| Delayed stock cycle | 12/12 | 12/12 | 18,579.354 s | 12,367.522 s |

The results are intentionally not presented as a useful real timetable or a capacity target. The single shared distribution area remains highly restrictive under the supplied demand. Releasing upstream resources earlier improves these particular schedules but does not supply an independent second fan.

All-platform closure, overlength trains and zero computation budget retain twelve unscheduled required visits under both policies. Their zero delay sums are not successful service. [Complete comparison](proof/sectional_results/comparison.md)

## 10. Reporting horizon: residual work is now classified

The report splits scheduled visits at the horizon into not-yet-due, waiting outside the model, arrival setup, arriving, berthed, departure setup, departing, release hold and completed. The categories sum to all scheduled visits; unscheduled demand is retained separately.

“Waiting outside the model” is a temporal scheduling category, not a spatial queue of trains with proven holding room. Approach storage, braking to a signal and queue spillback remain a later physical model.

The short-horizon fixture has no completed visits by its cutoff but retains all twelve scheduled residuals. It does not discard them or reinterpret future work as a physically observed queue.

## 11. Compact feedback and the next decision

The [decision packet](proof/sectional_results/decision_packet.json) summarises the mode comparison, numerical-profile status and remaining gates. The detailed geometry, per-resource footprints and reservations stay in local files. No model calls are made for the individual fit, phase or calendar steps.

The next geometric choice is whether to retain a compact shared fan or compose separate banks and selected cross-access. Before using dense realistic track spacing, vehicle-envelope and authentic component admission must become stronger. It would be misleading to assemble a huge synthetic network and only then discover that its basic component widths, speeds or interfaces cannot represent the intended railway.

## 12. Acceptance boundary

Accepted: a generated two-directional-lead subassembly; complete platform movements; stopping trajectories; scoped spatial footprints; conservative and sectional release policies; retained storage occupation; controlled comparison; independent interval checks and replay.

Not accepted: the full four-approach/eight-platform brief; independent arrival/departure distributions through the entire throat; authentic pointwork; complete vehicle clearance; real signalling release; calibrated train performance; spatial queues; complete passenger platforms; TPF3 construction or measured plan-credit savings.

The separate limits are intentional model interfaces. The final implementation must replace or refine each one explicitly rather than inherit a blanket “passed” label from this proof.
