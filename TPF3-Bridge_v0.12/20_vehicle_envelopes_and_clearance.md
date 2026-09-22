# Passenger-vehicle envelopes and clearance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.5.0 · **Date:** 20 September 2026  
**Status:** Executed planar rigid-body geometry, continuous-between-pose bounds for the supplied polyline, source-informed dimensions and read-only route-clearance overlays. Not an approved dynamic vehicle gauge.

## 1. What this adds to the railway engineer

A fixed-width strip around a track cannot describe a long vehicle on a curve. The body follows the orientation established by its supporting pivots, not every change of direction along the centreline. The middle and the ends therefore occupy different positions relative to the track.

The new `railclear` package makes that relationship explicit. Python now derives the orientation and footprint of a single two-bogie body, checks its path against another swept body or a planar obstacle, and records where a geometric contact occurs. It can also distinguish a genuine contact at an evaluated pose from an inconclusive coarse sampling result.

This is an additional engineering assessment, not a silent replacement of the v0.4 conflict model. An output that is clear for a declared rectangle does not erase an existing track, control, protection or proximity resource. The adapter is intentionally **read-only** until the missing profile and geometric-error gates are resolved.

## 2. Representative dimensions: what is sourced and what is assumed

The selected manufacturer sheet publishes a 2.8 m width, 20 m nominal vehicle length, and full-unit lengths of 162 m and 242.6 m. It does not supply the detailed bogie/outline data required by this implementation. Its date and general-product scope remain attached to the record. [S060](10_source_register.md#s060)

The data and runtime choices are deliberately separate:

| Layer | Delivered record | Interpretation |
|---|---|---|
| Published dimensions | [vehicle_reference.json](evidence/vehicle_reference.json) | Four catalogue quantities with source/issue/locator; no invented bogie data |
| Body interpretation | [clearance fixture](proof/clearance_fixtures/release.json) | Explicit use of nominal length as a symmetric plan rectangle |
| Bogie spacing | 14 m baseline, 12/14/16 m sensitivity | Project assumptions, not attributed to the manufacturer |
| Lateral allowance | Zero in the baseline raw-body study | Exposes unallocated space; does not mean actual movement allowances are zero |
| Long-body counterexample | 26 m body, 19 m pivots, 0.1 m allowance each | Wholly synthetic stress case; no named train attribution |
| Formation operation | Published complete unit length | Used for scalar platform fit and longitudinal tail clearance, not as one rigid body |

`resolve_vehicle()` returns reference-only status when no explicit assumptions are provided. Supplying those assumptions enables a **reference-informed static study**, not strict UK admission. The unresolved exact outline, pivot positions, suspension allowances, cross-section and coupling geometry remain in the result.

The nominal body interpretation is not guaranteed conservative for every actual driving/intermediate vehicle. A rectangular outline can overstate some corners while an approximate length can understate others. Do not market it as an exact or universally conservative model of the named fleet.

## 3. Governing geometric model

Let the body have symmetric length `L`, width `W`, physical separation `B` between its two bogie pivots, and declared plan allowance `a` on each side. The model uses half-width `w = W/2 + a`. It is restricted to a single rigid body with `0 < B < L`, level track, zero cant and a common horizontal plane.

For rear and front pivot positions `r` and `f`, solve:

\[
\|f-r\|=B.
\]

The centre is `(f+r)/2`. The longitudinal unit vector is `(f-r)/B`; its perpendicular supplies the lateral axis. Four corners follow from longitudinal offsets `±L/2` and lateral offsets `±w`.

**B is a straight-line physical separation, not a distance along curved track.** Choosing a second point exactly B metres earlier in track chainage shortens the physical pivot separation on a curve. The implementation instead solves the chord constraint.

This model treats pivots as following the supplied track centreline. It does not model the individual axles inside a bogie, wheel/rail lateral movement, bogie rotational stops, suspension, roll, track tolerances, pantographs, door steps or the lower-sector equipment envelope.

## 4. Exact circular reference calculations

For a circular path of radius `R`, the body-centre radius is:

\[
\rho=\sqrt{R^2-(B/2)^2}.
\]

The central inward displacement is evaluated using a numerically stable expression:

\[
R-\rho=\frac{B^2/4}{R+\rho}.
\]

The arc interval between the two pivots is:

\[
\Delta s=2R\arcsin\left(\frac{B}{2R}\right),
\]

which exceeds B for a finite radius. These formulae are project mathematical derivations, not imported national design rules.

Over a complete circle, the symmetric rectangular body occupies radial distances between:

\[
r_{min}=\rho-w,
\qquad
r_{max}=\sqrt{(\rho+w)^2+(L/2)^2}.
\]

The closest point is at the middle of the inward side, not necessarily at a corner. The tests explicitly catch that distinction.

For concentric tracks, the outer track's inner swept radius minus the inner track's outer swept radius gives a separation for **arbitrary relative vehicle phase**. A positive result is geometric space in this idealised plan model. Zero or a negative result means the swept bands touch or overlap; it is not a prediction that two scheduled trains will collide.

The analytic routines reject degenerate chords and unsupported numerical ranges rather than returning NaN or a deceptively large clearance.

## 5. General local paths and their support boundaries

The existing Bezier centreline kernel is retained. `from_curves()` subdivides its curves into chords and records the parent geometry hash and maximum curve-hull deviation. The resulting path has its own chord-length chainage. This is not confused with a Bezier parameter or the upper-length metric used by the older operating proof.

The rear pivot is found by solving segment–circle intersections backwards from the leading pivot. The implementation restricts the local path's headings to a common cone of ±40 degrees. All segment directions then differ by less than 90 degrees, giving a unique, monotone rear-pivot solution. This is a numerical/model-support restriction, **not a railway curvature limit**. Wider changes of heading need supported overlapping windows or another solver.

The solver rejects an unknown rear continuation. It never extrapolates a route implicitly. The crossover and bank demonstrations request 35 m tangent supports at both ends and export that assumption. These supports are authored geometry for the experiment, not observed infrastructure outside the model boundary.

Each sweep reports its front-pivot interval. The worked route scan advances far enough for the entire representative body to clear the original endpoint, within the explicit support. The bank scan remains a representative **single body** along an arrival route; it is not the positions of all bodies in a real formation or a reconstruction of that formation's stopping configuration.

## 6. Covering the space between evaluated poses

A set of sampled rectangles alone can miss an obstruction between samples. This release adds a conservative displacement bound for the continuous rigid-body motion **on the supplied polyline**.

Let `phi` be the span of all segment headings in the local path, `c = cos(phi) > 0`, and:

\[
K=\sqrt{(L/2)^2+w^2}.
\]

Parameterise motion by the front pivot's path distance. Differentiating the fixed chord gives a rear-pivot speed bounded by `1/c`. The centre speed is at most `(1+1/c)/2`. The body-heading rate is bounded by `sin(phi)(1+1/c)/B`. Therefore a sufficient bound on the speed of any rectangle point is:

\[
M=(1+1/c)\left(\frac12+\frac{K\sin\phi}{B}\right).
\]

For maximum pose interval `h`, every intermediate body is within `M h/2` of its nearest sampled body, plus the declared small floating-arithmetic guard. The argument integrates across polyline vertices; it does not assume a derivative exists at every vertex.

For two sweeps with minimum sampled polygon distance `d`, a conservative lower bound is:

\[
d_{continuous}\ge d-p_A-p_B,
\]

where `p_A` and `p_B` are their between-pose paddings. A stationary obstacle needs only the moving body's padding.

This is an analytic bound implemented with ordinary floating arithmetic, not formal interval arithmetic. More importantly, the parent Bezier's centreline error is **not automatically an error bound on the solved body pose**. That amplification has not been certified in this release. A clear polyline result therefore retains `parent_curve_body_error_bound: unassessed` and cannot authorise removal of the older continuous centreline-proxy exclusions.

Independent tests compare densely evaluated intermediate corners against the bound for changing-heading and reversing-curvature examples. They verify the implementation on those fixtures; the derivation defines its intended scope.

## 7. Contact algorithms and result states

At an evaluated pose, the separating-axis test handles rectangle overlap and containment. Closed-segment distances supply positive separation. Supplied obstacles must be ordered, strictly convex, non-self-intersecting planar polygons; malformed or three-dimensional inputs are rejected.

Pairs are checked across **all relative pose combinations**, not only equal chainages or equal times. Axis-aligned bounds prune pairs that cannot improve the current minimum. A work budget remains explicit.

| Status | Meaning |
|---|---|
| `geometric_gap` | Positive analytic straight/circular model space; not complete gauge approval |
| `geometric_contact_or_overlap` | Analytic bands touch/overlap under the declared model |
| `sampled_body_contact` | At least one evaluated pair or obstacle pose touches/overlaps |
| `clear_within_polyline_static_model` | The between-pose lower bound is positive over the reported intervals |
| `unresolved_between_poses` | Samples do not touch, but the bound cannot establish continuous separation |
| `search_exhausted` | The configured computational budget stopped the check; not physical infeasibility |

An obstruction can contact a body's inward overhang while remaining away from the track centreline. The delivered curved-obstacle fixture exercises exactly that case. It is a plan obstacle, not a fully specified platform edge or pier with height and structural clearance.

## 8. Executed spacing studies

All results are in [spacing_sensitivity.json](proof/clearance_results/spacing_sensitivity.json) and the [comparison table](proof/clearance_results/comparison.md). The study has eighteen base rows: three assumed pivot separations across a straight and five circular cases.

For the 20 m by 2.8 m rectangular interpretation with 14 m assumed pivot spacing, the raw analytic gap between tracks 3.4 m apart is:

| Inner track radius | Raw plan gap |
|---|---:|
| Straight | 0.600000 m |
| 1,500 m | 0.566735 m |
| 800 m | 0.537739 m |
| 400 m | 0.475953 m |
| 250 m | 0.402431 m |
| 150 m | 0.273379 m |

The selected source nominal-centre reference applies only to straight track and curves of radius at least 400 m. The tighter cases are deliberately labelled stress tests, not permission to use that interval everywhere. [S058](10_source_register.md#s058), [UK numerical profiles](17_uk_numerical_profiles.md)

The independent synthetic 26 m body with 19 m pivot spacing and 0.1 m lateral allowance on each vehicle produces overlapping swept bands in the 150 m stress case. This counterexample prevents the engine from adopting one width-only answer for every passenger formation.

The straight-path refinement experiment is equally important: a coarse 1 m pose step is inconclusive; a 0.1 m step establishes separation within the static polyline model. **The track spacing, body dimensions and allowances are unchanged.** Python refines computation instead of changing the physical assumptions until a desired answer appears. [Refinement evidence](proof/clearance_results/straight_refinement.json)

## 9. Generated railway and operating interfaces

The existing generated crossover has two separate through routes and a crossing route. The new overlay establishes static-polyline separation of the two through paths and finds body contacts between the crossing path and each through path. These findings agree with the broad purpose of the existing conflict arrangement, but the overlay does not replace its control-state requirements. [Crossover overlay](proof/clearance_results/crossover_clearance_overlay.json)

The generated bank's P4 arrival also produces a full representative-body pose trace tied to the source geometry hash. [Bank sweep](proof/clearance_results/bank_route_sweep.json)

Published whole-unit lengths are separately passed into v0.4's scalar berth-fit and tail-clear motion interface. With the fixture's 260 m boarding length and 5 m margin at each end, the residual space is 88 m for the shorter unit and 7.4 m for the longer one. Motion still uses the existing project-selected acceleration, braking and speed cap; these have not become manufacturer performance data. [Formation trial](proof/clearance_results/published_formation_length_trial.json)

A future formation model needs each vehicle's actual outline, pivots and coupling layout. It must not place one 162 m rectangle on a curve or infer exact vehicle spacing from nominal body length.

## 10. National gauging and the production admission gate

RSSB's current catalogue identifies GMRT2173 issue 4.1 for vehicle-size/swept-envelope requirements and GERT8073 issue 5 for standard vehicle gauges and their application. The latter includes the transferred benchmark-suspension material. Both full-standard links reached registration/login; catalogue verification is not clause-level implementation. [S061](10_source_register.md#s061), [S062](10_source_register.md#s062)

The next production profile requires actual body/cab outlines, pivot and axle geometry, the selected gauge methodology, applicable suspension/track allowances, vertical sections, cant/roll transformations, vehicle-to-platform treatment and source-validity review. A body-to-body passing check and a vehicle-to-structure clearance check must not share unexplained generic allowances.

These are missing input/method gates, not a reason to stop reference-informed game design. Python can continue to compare clearly declared approximations. Strict UK design must not silently receive the same approximation with a different label.

## 11. Module and cache contracts

`model.py` supplies body/path geometry, analytic references and convex distance helpers. `sweep.py` supplies bounded pose generation, pair/obstacle studies and the read-only overlay. `profiles.py` resolves the partial published record with explicit assumptions. `demo.py` generates reproducible evidence, including the source-input hashes.

A future persistent cache key must include the vehicle record, every assumption, path approximation, support intervals, pose step, method version and relevant rule profile. An old width-only check must not survive a change in bogie spacing, body length or cant. The present implementation records those inputs/hashes; it does not claim a production persistent cache or incremental world update engine.
