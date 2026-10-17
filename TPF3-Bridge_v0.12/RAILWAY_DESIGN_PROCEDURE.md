# Railway design procedure

Purpose: produce coherent game-scale railways without repeatedly turning local
construction difficulties into unplanned layout changes. The handbook explains
lessons; this procedure determines when to apply them. Native acceptance,
connectivity, operation and design quality are separate outcomes.

## 1. Establish the brief and actual site

Use one [design record](railway-design/DESIGN_RECORD_TEMPLATE.md) per challenge.
Keep only the current working plan and state needed to finish the operation.
Discard completed snapshots, candidate logs and run records. Preserve transferable
lessons in the handbook and reusable patterns, not an activity history.

- Express required directed movements, track roles and exclusions. Include station
  arrival AND departure, turnarounds, intended alternate platforms and depot access
  when these belong to the task. Specify travel in a common world/local frame on
  both sides of a station; mirroring geometry must not silently invert UP/DOWN.
  Do not silently introduce extra services.
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

Before constructing or materially changing a coupled approach family, render the
combined plan and profile across payload/section boundaries, at shared horizontal
scale. Include full authored controls, signal/merge order, deck/ramps and construction
interfaces. Endpoint-only sketches can conceal an interior bow. Keep authored controls,
native preview and committed readback distinct; accepted endpoint_cubic geometry is
not a native whole-alignment fit or design approval.

Use a designer and a different independent reviewer (Astra for material design
judgements) at material coupled-family changes. Give the reviewer the combined
controls/diagrams and requirements before construction; feed actual native geometry
back into that whole-family view. Resolve material design objections before dependent
construction. Routine bounded fitting, sweeps and normal verification need no extra
model/approval gate.

The plan must make these decisions visible:

| Decision | What to show |
| --- | --- |
| Topology | Directed routes, shared sections, forks and merges in travel order |
| Spatial arrangement | Track order, paired corridors, attachment regions, reserved space for unfinished routes |
| Vertical arrangement | Over/under relationships, ramps and landing space, terrain treatment |
| Operation in scope | Station choices and return access, signal intent, depot entry/exit |
| Scale and shape | Game-coordinate footprint, useful sweeps, compact crossing/turnout groups |

Reserve city growth and road-crossing corridors as well as railway space. Record
map-specific hub/flyover/regional-junction distances with a defined station datum;
do not copy compact demonstration spacing into the real network. Keep principal
fast alignment and gather slow/Cross tracks into a narrow shared approach where
required, accepting asymmetric slow fans. See the handbook
[Mid West C guidance](RAILWAY_DESIGN_GUIDE.md#accepted-mid-west-c-lessons--future-builds).

Plan the intended speed progression: slow platform fans need not be faster and
longer than throat crossovers. Retain the preferred approximately 30 m straight
parallel platform leads; compare fan/crossover lengths together using native speed
feedback when available. Approximate visual speed estimates are not measurements.
Independent prebuild review must assess fan shape, total length and native speed
feedback together. Choose the compact fan envelope before local fitting; preserve
30m straight leads and account for final braking/initial acceleration near platforms
without adding a physics model. In the current accepted layout the user-reported
approximately80mph crossovers stay unchanged; fans are accepted unchanged but judged
too long/fast. For future design the slowest relevant fan should not be faster than
those crossovers. Challenge04/05 roughly55mph is contextual guidance, not a universal
speed/radius gate or authority to repair the current map.

Balance crossover speed with final decision-signal distance and departure clearance:
longer/faster crossovers can consume useful capacity through a longer approach.
Do not propagate a successful turnout gap as a native minimum without testing a
closer arrangement. The earlier Mid West C80m crossover trial is a reference, not
a current repair instruction; native fit/speed feedback informs future choices.
For operating networks, include open-line block signals (user default about 300 m)
as well as junction/station signals, preserving final platform-decision placement.

Reserve the actual selected station/depot footprint, open approach side and turnout
space before committing neighbouring corridors. A centreline-only reservation can
miss a building collision even when the approach curve itself fits.

Reservation means visible space in the plan; it is not a claim of native clearance.
Exact control points can remain provisional. State which attachment regions or
profiles are uncertain and which native observation would resolve each one.

The plan is an intent and space allocation, not an exact curve reconstruction.
Separate fixed requirements (route roles, connection identities, crossing order,
explicit protections) from flexible preferences (turnout position, curve start,
segment lengths, control points). Provide a usable local fitting envelope rather
than making every coordinate a constraint. Choose its extent from neighbouring
routes and reserved space; do not demand an arbitrary universal tolerance.

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
  Isolated bridge supports can obstruct lower-track proposals despite a15m
  railhead height gap. At demonstrated sites, building the lower roads first
  and restoring the identical deck resolved support staging; height separation
  alone does not prove proposal clearance.
- For a flying junction, compare crossing angle, lateral width and deck extent
  together with both ramps. A shallow level span can be longer but much narrower.
  Where appropriate, establish it unconnected before fitting earth-supported
  approaches. Treat example margins as preferences until the native fit is observed.
- Complete planned depot and service turnouts before placing dependent signals
  where possible. The current split producer excludes edges carrying objects;
  discovering this after signalling creates avoidable rework.
- Use observed elevations and terrain floors for the actual site. The Complex
  Junction z=1 floor is a user constraint there, not a universal world water level.

## 4. Fit and build within the selected revision

Keep the accepted source recipe reusable: full canonical intent, named attachment
slots, resources, required bootstrap removals, every approved bounded continuation
window and acceptance criteria. A final remaining-only plan or post-build entity
IDs are not the complete recipe. Qualify named slots against the current world;
reuse completed prefixes and continue only the original outstanding scope.

An implementation assignment identifies the design revision, route family, intended
attachments and directions, corridor/profile, neighbours still to be built, allowed
local adjustments, and expected functional outcome. Include the relevant plan view.

For delegated work, keep one coordinator responsible for current state and native
mutations, with one implementation worker. Specialist designers may plan independent
families concurrently when their connecting interfaces, route roles and reserved space
are explicit. Give each a separate editing area and a compact decision package with
the applicable lessons and current observations. Review adjoining interfaces together
before construction. Escalate material topology or spatial trade-offs to the designer;
routine fitting and result checks stay with the coordinator and deterministic operator.

Fitting may adjust attachment position, curvature, segment representation or local
profile while retaining the arrangement. Numerical changes can be small yet change
which traffic can reach a turnout; classify by consequences, not a distance quota.

Review curvature distribution over the whole approach. Temporary stubs and straight
anchors support construction; they do not require long final straights joined by
short abrupt bends. Keep neighbouring roads packed until platform fan space is
needed, and compare width at several distances from the station before fitting.
Check staggered platform footprints: complete lateral shifting before a projecting
neighbour, allowing a justified straight beyond the retained 30 m lead. For required
parallel appearance, inspect native strip coverage as well as spacing; a separately
built native-offset tail may join the strip without rebuilding its fan. Beside ramps,
review one continuous sweep with few controls and delay rejoining until the neighbour's
height transition is clear. A jointly derived interior guide can move a local
 descent envelope a few metres to clear neighbouring earthworks while retaining
 both interfaces and the intended profile; review the complete smooth sweep.
 Add local margin for observed terrain clipping only. Check signed curvature and heading within each realised cubic,
not just at its endpoints: matching guide headings can conceal interior reversals
and sign-changing curvature jumps. Derive guide positions and tangents together
from the intended whole sweep; review residual joins after native cubic conversion.

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

For ordinary local rejection, the operator should automatically try nearby native
fits within the declared envelope, starting with the preferred arrangement and
then small adjustments. Use deterministic code for this loop, not repeated model
turns, scripts or design revisions for individual offsets. Accept the first suitable
native fit that preserves the intended routes, smooth sweep, neighbouring space
and overall footprint. Do not optimise harmless differences back towards the sketch.
Native segmentation and a short parallel continuation into a fan are acceptable.
Exact entity binding prevents attachment to the wrong track; it does not justify
fixing a turnout's position on the correct track to a single arbitrary coordinate.

Try proposals without construction where supported, then build the selected prepared
proposal once. Stop on uncertain effects and re-observe before further mutations.
Report the selected displacement and compact outcome. A finite search establishes
only sampled feasible/rejected positions, not a universal feasibility boundary;
refine a local boundary only when doing so serves the design. Exhausting a local
window calls for diagnosis or a wider justified window, not an automatic redesign.
Numerical shape checks catch obvious defects; whole-family visual review remains
necessary at useful boundaries, without reviewing every candidate.

Repeated small adjustments can cumulatively change the arrangement. Compare with
the selected revision, not just with the immediately preceding candidate.

After an uncertain mutation, read actual state before repeating. A new local fit
requires appropriate native evaluation; never silently refit a prepared build.
Native feedback can be incomplete. Distinguish an unsuitable design, rejected
proposal, fitter limitation and demonstrated bridge defect.

## 5. Review at useful construction boundaries

A known failure used a horizontal temporary landing about450 native units before
the deck, decoupling the branch merge from its ramp. The actual lateral sweep ran
25 ->32.14 ->15 despite an acceptable shallow deck. This is a whole-alignment bow,
not a universal clearance limit or engine defect. Review merge/ramp/deck together
before build; a staging interface must not force the final shape. Keep selected hard
constraints without imposing exact sketch equality.

The reusable R2 reference demonstrates the feedback loop: independent prebuild
combined-control review, native construction, required/forbidden route checks, then
independent realised-geometry and unobstructed visual review. Its continuous graded
sweep removed the staging plateau/bow while preserving the required functions.
Do not turn those example controls into universal dimensions or exact-sketch gates;
prebuild comparison diagrams are not final readback or train-traversal evidence.

Review after a controlling route or coupled family is built, and after material
native-driven revisions. Do not review every click. Use a comparable overhead view
and the relevant profile; overlay actual geometry on the plan where available.

Review adjacent ground-level slow sweeps as whole curves alongside flyovers,
including unnecessary outward bows or inserted straights between turns.
Ask whether paired routes remain coherent, remaining routes retain their space,
required junction order holds, and any extra bow, crossing or structure is justified.
If the complete footprint is unattractive or inefficient, native acceptance does
not justify extending it with the next family. Revise the cause first.

Confirm intended attachments and directed native paths proportionately. Diagnose
signal direction and binding before adding track for a service failure. Observe
trains when operation is part of the brief. Ordinary queues are not a new capacity
audit. Keep nonblocking diagnostic discrepancies as observations.

## 6. Close and learn without declaring premature success

For directional services, check that the native path uses the intended running
roads; route availability alone can pass on an unintended opposite road. Separate
signal attachment/orientation readback from allowed travel. In operating challenges,
also inspect actual line loading configuration and visible native service warnings;
a moving train alone does not establish a useful passenger service.

After signal mutations, refresh bindings through endpoint-qualified replacement
lineage and recheck the affected directed roads, including reverse bay arrivals.
Use native preflight for bounded nearby signal fitting; preserve decision order
and accepted placements. Signal-split transport rows are a query representation,
not evidence that the physical railway needs rebuilding. Configured line choices
and native paths can be qualified without claiming observed traversal or platform
selection under contention.

Report four separate conclusions: built, connected, observed operating, and design
quality reviewed. Record shortcomings even if the capability challenge is complete.
Use comparable plan/profile views during review and distinguish user acceptance from the
designer's judgement. Do not present a merely working layout as an aesthetic baseline.

Compare the result with its selected plan using a few relevant measures, with the
same boundaries and coordinate system: footprint, route length between matched
interfaces, avoidable reversals, independently routed portions of an intended pair,
crossing levels, or major rebuilds. Explain trade-offs; no weighted magic score or
universal numeric pass threshold. Separate useful exploratory trials from rework
caused by omitted requirements or unplanned workarounds.

Update a pattern only from a demonstrated result or explicit design judgement,
with its applicability and uncertainty. Update the current guidance in place;
do not keep superseded cases or revision archives. For procedure changes, run affected [regression cases](railway-design/REGRESSION_CASES.md).
Historical replay detects missed lessons; it does not prove transfer to a new site.
