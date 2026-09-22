# Platform re-fit, recovery eligibility and stronger component evidence

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.8.0 · **Date:** 21 September 2026  
**Executed:** Four paired-island reservations, eight boarding edges, a bounded facility re-fit, and nine interface/operation comparisons on one unchanged scissors railway.

## 1. A platform is part of the station's operating capability

The v0.7 scissors provides A-to-B recovery through B1. That railway connection is not sufficient by itself: the boarding face must remain available for the selected passenger-station brief.

This experiment introduces a twenty-metre-long, four-metre-wide **synthetic facility footprint** on island IB12. It is a reserved obstruction representing a future access/building arrangement, not an asserted dimension for a real staircase, lift or station building. Its initial centre is one metre closer to B1 than the island centre.

The selected reference-copy general-obstacle screen requires 2.5 m between an obstacle and each face for the stated low-speed case. The requirement uses permissible/enhanced infrastructure speed; the release fixture separately declares that value rather than inheriting it from the motion solver. Exceptions and passenger-demand sufficiency are not assumed. [S064, 2.3.4](10_source_register.md#s064)

The project explicitly enables a **planning policy** that excludes boarding faces failing the selected reference dimension/obstacle checks. This is not a report of a real physical track closure or a real station safety decision. The diagnostic-only mode retains the failed check without applying an operational exclusion.

## 2. The initial problem and the local repair

IB12 has faces at y=7.455 m and y=16.545 m. Its centre is y=12 m, and its derived width is 9.09 m. The initial facility centre is y=11 m.

| Facility arrangement | B1-side gap | B2-side gap | Reference-obstacle result |
|---|---:|---:|---|
| Four metres wide, initial offset | 1.545 m | 3.545 m | B1 face fails |
| Same facility, nearest authorised fit | 2.500 m | 2.590 m | Both pass the selected reference screen |
| Same facility, centred for comparison | 2.545 m | 2.545 m | Both pass; 45 mm above each selected minimum |
| 4.2 m wide, centred | 2.445 m | 2.445 m | Both fail |

The local solver moves the four-metre facility **0.955 m laterally**, from y=11 m to y=11.955 m. It does not resize the facility, move track, alter train length, change a standard value or enlarge the site.

The selected objective is the smallest authorised lateral change. The centred comparison is also exported because it gives more balanced spare width. Neither arrangement includes construction tolerances, detailed demand sizing or a guarantee that a real access facility can be built inside the reserved footprint. A mathematically exact minimum is not automatically a desirable finished design target.

Full inputs and results are in [facility_search.json](proof/interface_results/facility_search.json).

## 3. Exact local feasibility, not trial-and-error drawing

For island face ordinates `y0,y1`, facility width `w` and required clear distances `d0,d1`, the permissible facility-centre interval is:

\[
[y_0+d_0+w/2,\;y_1-d_1-w/2].
\]

Python intersects this with the authorised movement interval. A feasible original location is retained. Otherwise it chooses the nearest point of the intersection and runs a separately structured distance check.

This is a small exact interval problem under the declared rectangular model; it does not require repeated model calls or game construction. The implementation records a tiny floating-arithmetic comparison guard separately from physical dimensions. That numerical guard is not an engineering allowance.

If the physical interval is empty, the required width lower bound is:

\[
W_{required}=w+d_0+d_1.
\]

For the 4.2 m facility, this is 9.2 m, **110 mm more** than the present island. Keeping the same face-offset interpretation would require track centres of **12.11 m** in this fixed-section model. Moving those tracks is outside the frozen brief, so the solver does not do it automatically.

This is a certificate for the fixed face locations, facility dimensions and longitudinal location. It does not prove that a different building shape, access arrangement, platform pairing or wider authorised site cannot work.

The other outcomes remain distinct: `outside_authorised_moves` when the physical fit exists but permission does not; `search_exhausted` when no fit evaluation is allowed; and `unassessed` when required reference applicability or permissible speed is missing.

## 4. Speed and space are different design inputs

A comparison changes the two adjacent infrastructure speed fields to 125 mph but leaves the same railway and facility geometry for the width study. The selected reference-copy general-obstacle distances then require three metres at both faces. The four-metre facility needs a ten-metre island, exceeding this island by 0.91 m. [S064, 2.3.4](10_source_register.md#s064)

That calculation does **not** rate the station's pointwork or permit trains to approach it at 125 mph. It tests that the rule resolver uses the correct speed concept. A train presently moving slowly is not evidence that the adjacent line has a low permissible speed.

See [speed_and_space_sensitivity.json](proof/interface_results/speed_and_space_sensitivity.json). The original speed values are explicit synthetic project infrastructure settings, and the 15 mph motion target remains an independent, uncalibrated operating input.

## 5. Actual integrated operating results

Each case uses the same track, the same twelve service pairs, the retained published full-unit length and the same motion/stock/readiness assumptions as the compact fixture. The only policy change is which boarding faces the selected interface checks make unavailable.

| Interface case | Normal completed / required | A-bank platform closure | B-bank platform closure |
|---|---:|---:|---:|
| Initial displaced facility; B1 excluded | 24 / 24 | 12 / 24 | 24 / 24 |
| Locally re-fitted facility; no new exclusion | 24 / 24 | 24 / 24 | 24 / 24 |
| Wider fixed facility; B1/B2 excluded | 24 / 24 | 12 / 24 | 24 / 24 |

All counts use the existing four-hour reporting horizon. Completion within that window is not punctuality or a realistic station-capacity approval. The [full comparison](proof/interface_results/comparison.md) preserves delay, unscheduled demand and residual work.

For A-bank closure, the initial low delay total excludes twelve trains that have lost their complete recovery opportunity. After the local re-fit, all required trains are scheduled and completed, with 16,547.982 seconds of aggregate departure delay in this synthetic scenario. It would be misleading to prefer the initial layout because its scheduled-only delay is lower.

The B-bank closure results are unaffected by this particular B1/B2 facility screen: that recovery uses A4. The test therefore checks the **location** of an interface restriction, not a blanket reduction in station capacity.

The scheduler and the independent checker still enforce complete arrival–berth–departure routes, train fit, stock readiness, track/control claims and sustained platform occupation. The new interface layer cannot repair an operating failure by dropping trains from the input.

## 6. The joined design assessment

Every new operating output includes the rail compile hash, platform-assessment hash, facility-check hash, vehicle-reference hash and a combined design-case hash. It also retains the effective planning exclusion and independently checked operating result.

The gate recalculates the supplied facility check rather than trusting its stated pass flag. It also considers failures in the selected height, offset and minimum-width checks. Thus an obstacle fit cannot hide a failed platform-height input. Missing scoped inputs leave the gate unassessed.

Railway geometry and compiled resources are compared before and after interface work. They are unchanged in the accepted repair. Existing vehicle audits therefore remain evidence about those railway paths, **not** evidence that the new platform surfaces have passed dynamic gauging. Infrastructure-level clearance must be assessed against the new platform/facility identities separately.

The [site result](proof/interface_results/site_with_platforms.json) tests the original rectangle, exact approaches and concourse together with the four boarding-slab reservations. It passes the limited planar/hull check. Accessible paths from the slabs to the concourse, structural details and track-end protection are still missing.

## 7. Stronger real UK component references

The research also obtained usable numerical facts about a real studied UK switch, rather than only a generic supplier product page. A primary West Coast Main Line study identifies a CEN56 113A shallow-depth G-type installation, a reported 1,650 m switch radius, a 1-in-28 crossing and 1,435 mm gauge. The reported local through and diverging line speeds have their own directions and site scope. [S067, section 2](10_source_register.md#s067)

These become a **dated field-reference record** in [component_field_references.json](evidence/component_field_references.json). They do not define every route curve, toe datum, crossing location, end port, bearer or hardware envelope. In particular, a reported line speed at one installation is not a universal rating for any component with the same crossing ratio.

A second primary study describes a REPOINT stub-switch model based on an NR60 inclined C-switch drawing and gives a 7.8 m movable beam length. That length describes the movable research beam, not the length of a conventional complete turnout. The drawing identifier is an acquisition lead; the drawing itself was not obtained. [S068, section 2.2](10_source_register.md#s068)

The resulting component audit demonstrates two intentional `not_comparable` results:

1. A real crossing ratio is not automatically comparable to the reciprocal of the synthetic model's branch-exit tangent slope. The locations and definitions must first be reconciled.
2. A movable beam length is not a whole-turnout longitudinal envelope. Relabelling the forty-metre synthetic object as the source's C-switch would be false.

These are useful numerical/semantic constraints on the eventual importer. They prevent a superficially plausible standard designation from laundering synthetic geometry into the authentic catalogue.

## 8. What is still required for a physical component replacement

A complete dimensional definition must resolve the local reference system, both route curves, switch and crossing relationship, installation/handedness limits, physical envelope and source validity. Piecewise straight/arc/transition geometry may require a richer importer than the current single-Bezier route contract.

The present compact fan is not re-fitted against a fabricated “G28 turnout”. Such a re-fit would merely exchange one unverified shape for another. The newly sourced scalar references are retained for future matching and independent dimension checks, while `authentic_complete_turnout_imported` remains false.

The useful change in v0.8 is that realistic platform dimensions have actually challenged the built candidate and affected complete recovery movements. Component acquisition has also moved from a supplier category to specific primary-study quantities, without pretending those quantities constitute a full catalogue drawing.

## 9. Production continuation

Next, connect each usable boarding face to the concourse through explicitly sized and accessible passenger paths, while preserving platform-end and vehicle-interface reservations. The current general-obstacle screen is one necessary local check, not that complete access model.

Continue current-standard reconciliation and exact pointwork acquisition in parallel. The eventual network generator needs both the functional algorithms demonstrated here and suitably sourced component/vehicle profiles. Neither is a substitute for the other.
