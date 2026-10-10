# Railway design procedure

Version 0.4 — 10 October 2026. Shefford and accepted Challenge01/02 inform the
procedure. Challenge03 adds a shallow flying-junction case awaiting user review.

Purpose: produce coherent game-scale railways without repeatedly turning local
construction difficulties into unplanned layout changes. The handbook explains
lessons; this procedure determines when to apply them. Native acceptance,
connectivity, operation and design quality are separate outcomes.

## 1. Establish the brief and actual site

Use one [design record](railway-design/DESIGN_RECORD_TEMPLATE.md) per challenge.
Keep transient snapshots and full fitting logs under an ignored local run folder;
keep transferable patterns and concise evaluation results in versioned documents.

- Express required directed movements, track roles and exclusions. Include station
  arrival AND departure, turnarounds, intended alternate platforms and depot access
  when these belong to the task. Do not silently introduce extra services.
- Distinguish user requirements, observed native requirements, design preferences
  and hypotheses. Record preservation requirements explicitly; disposable existing
  geometry does not acquire protection merely because it has been built.
- Survey current station interfaces, track order/direction, terrain and structures.
  Give every interface a stable role label and map it to fresh native handles.
  Record coordinate orientation, game units, world identity and survey coverage.
- Explain the receiving cross-section: track spacing may include platform space.
  Shefford's 10/15-unit offsets represent a platform allowance; its proposed
  track-only 5/10 variant keeps the turnout pattern but changes that requirement.
- Agree the design priorities from the brief: for example, coherent principal
  routes first, useful shared corridors, then compact secondary connections.
  Compactness is not the shortest possible line at the expense of required functions.

Read only the relevant [pattern cases](railway-design/PATTERNS.md). A manual success
demonstrates a local possibility, not a universal minimum or a transferable guarantee.

## 2. Plan the whole arrangement

For a complex layout, produce a scaled overhead plan and profiles of the crossings
that determine feasibility. Show the complete intended arrangement at corridor
level before detailing individual curves. Label proposed, existing and built items.

The plan must make these decisions visible:

| Decision | What to show |
| --- | --- |
| Topology | Directed routes, shared sections, forks and merges in travel order |
| Spatial arrangement | Track order, paired corridors, attachment regions, reserved space for unfinished routes |
| Vertical arrangement | Over/under relationships, ramps and landing space, terrain treatment |
| Operation in scope | Station choices and return access, signal intent, depot entry/exit |
| Scale and shape | Game-coordinate footprint, useful sweeps, compact crossing/turnout groups |

Reservation means visible space in the plan; it is not a claim of native clearance.
Exact control points can remain provisional. State which attachment regions or
profiles are uncertain and which native observation would resolve each one.

Compare materially different arrangements where the choice controls the result:
for example, branch before versus after a crossing, or a paired corridor versus
independent arms. A sketch and a short trade-off explanation are enough; do not
enumerate permutations or require arbitrary numbers of alternatives.

Inspect the whole plan yourself. Check that every required route has a place,
every approach can reach its required choices, and ramps do not consume the space
reserved for neighbours. In disposable areas, compare replacement with retaining
awkward existing geometry. Do not keep it solely to preserve prior effort.

**Ready to construct:** the designer has selected a revision, all required routes
are represented, and the layout-defining uncertainties have a practical trial or
an explicit provisional treatment. This is an internal design decision, not a new
permission request. Do not demand certainty about every future native detail.

## 3. Resolve defining uncertainties and choose the sequence

Try the geometry on which the arrangement depends before filling in easy tracks.
Examples: an extreme fan connection, a shared multi-track bridge, a constrained
receiving junction or a station return across intervening fast tracks.

For each material uncertainty record the question, a useful native trial, the
observed result and its implication for the plan. Use existing evidence when it
answers the question. An arbitrary parameter sweep is not a design strategy.

Choose the construction sequence by remaining spatial freedom and native staging:

- Establish controlling fan boundaries before constrained intermediate branches.
  A three-exit fan may use two staggered ordinary turnouts. Shefford's preferred
  middle route branches early from the outer sweep; select the parent and junction
  region as part of that family rather than requiring a single three-way switch.
- Account for through-track replacement, turnout eligibility and usable approach
  length; do not infer these from endpoint distance alone.
- Where a demonstrated native structure sequence requires it, clear/prepare the
  corridor, construct the grouped upper tracks, then the lower connection. Other
  sites may require a different order. Design final and intermediate states.
- For a flying junction, compare crossing angle, lateral width and deck extent
  together with both ramps. A shallow level span can be longer but much narrower.
  Where appropriate, establish it unconnected before fitting earth-supported
  approaches. Treat example margins as preferences until the native fit is observed.
- Use observed elevations and terrain floors for the actual site. The Complex
  Junction z=1 floor is a user constraint there, not a universal world water level.

## 4. Fit and build within the selected revision

An implementation assignment identifies the design revision, route family, intended
attachments and directions, corridor/profile, neighbours still to be built, allowed
local adjustments, and expected functional outcome. Include the relevant plan view.

Fitting may adjust attachment position, curvature, segment representation or local
profile while retaining the arrangement. Numerical changes can be small yet change
which traffic can reach a turnout; classify by consequences, not a distance quota.

| Ordinary fitting | Material redesign: return to the spatial plan |
| --- | --- |
| Shift a turnout within its intended region with route order and neighbouring space retained | Move a turnout before a required merge, or past a required divergence |
| Adjust a sweep/tangent or native segment representation | Add a compensating loop or a new longitudinal reversal |
| Adjust ramp shape within the reserved crossing and landing region | Add a height level or reverse the planned over/under order |
| Change build order or a structure asset without changing the arrangement | Separate a paired corridor, consume another route's reservation or materially grow the footprint |

On material change, suspend dependent construction, observe actual state, and
revise the affected family in the whole-layout context. Compare moving/rebuilding
the original junction with adding a workaround. Record the reason and consequences;
update the plan and sequence before dispatching construction against that revision.
Unaffected authorised work may continue. The designer resolves in-scope trade-offs
autonomously; ask the user only for genuinely missing intent or scope decisions.

Repeated small adjustments can cumulatively change the arrangement. Compare with
the selected revision, not just with the immediately preceding candidate.

After an uncertain mutation, read actual state before repeating. A new local fit
requires appropriate native evaluation; never silently refit a prepared build.
Native feedback can be incomplete. Distinguish an unsuitable design, rejected
proposal, fitter limitation and demonstrated bridge defect.

## 5. Review at useful construction boundaries

Review after a controlling route or coupled family is built, and after material
native-driven revisions. Do not review every click. Use a comparable overhead view
and the relevant profile; overlay actual geometry on the plan where available.

Ask whether paired routes remain coherent, remaining routes retain their space,
required junction order holds, and any extra bow, crossing or structure is justified.
If the complete footprint is unattractive or inefficient, native acceptance does
not justify extending it with the next family. Revise the cause first.

Confirm intended attachments and directed native paths proportionately. Diagnose
signal direction and binding before adding track for a service failure. Observe
trains when operation is part of the brief. Ordinary queues are not a new capacity
audit. Keep nonblocking diagnostic discrepancies as observations.

## 6. Close and learn without declaring premature success

Report four separate conclusions: built, connected, observed operating, and design
quality reviewed. Record shortcomings even if the capability challenge is complete.
Retain comparable plan/profile views and distinguish user acceptance from the
designer's judgement. Do not present a merely working layout as an aesthetic baseline.

Compare the result with its selected plan using a few relevant measures, with the
same boundaries and coordinate system: footprint, route length between matched
interfaces, avoidable reversals, independently routed portions of an intended pair,
crossing levels, or major rebuilds. Explain trade-offs; no weighted magic score or
universal numeric pass threshold. Separate useful exploratory trials from rework
caused by omitted requirements or unplanned workarounds.

Update a pattern only from a demonstrated result or explicit design judgement,
with its applicability and uncertainty. Preserve the previous case and why it
changed. For procedure changes, run affected [regression cases](railway-design/REGRESSION_CASES.md).
Historical replay detects missed lessons; it does not prove transfer to a new site.

## Initial evaluation sequence

1. Retrospective P75 review: identify where this procedure would have intervened.
   Recorded in [the first review](railway-design/P75_REVIEW.md); no reconstruction.
2. Inspect a small manually built fan pattern and document its actual geometry.
   Completed for [Shefford's two mirrored fans](railway-design/examples/SHEFFORD_FANS.md):
   29 tracks captured and all six intended native directional paths verified.
3. The user also supplied mirrored 5/10 versions; these are reference data, not
   successful transfer by the agent. First prospective test:
   [an oblique two-track/four-lead throat](railway-design/CHALLENGE_01.md), including
   all arrivals and returns, planned before fitting. Built on the unchanged fixture:
   eight directed paths pass, with no rejected proposals or rebuilds. See its
   [plan comparison and limits](railway-design/examples/challenge01/DESIGN.md).
   User accepted its visual result; this single composition does not prove reliability.
4. A separate [six-lead transfer case](railway-design/examples/challenge02/DESIGN.md)
   now combines30-degree receiving alignment, larger lateral offset and nested
   three-exit fans. All12 paths pass; original topology retained through local
   crossover fitting. Designer reviewed, user visual feedback pending. This remains
   a related family, not proof across arbitrary junctions.
5. Exercise an unfamiliar combination after these small examples succeed. Broaden
   the library when a real failure reveals a missing principle.

Do not start another full-junction rebuild just to evaluate these instructions.
