# Practical railway design through the bridge

Use the [procedure](RAILWAY_DESIGN_PROCEDURE.md), [patterns](railway-design/PATTERNS.md)
and [regression cases](railway-design/REGRESSION_CASES.md) together. This handbook
contains reusable lessons, not a build diary. Example dimensions are not game limits.

## Plan the whole arrangement

Specify required directed movements, station/platform roles, arrival and return
routes, useful independent movements and explicit exclusions. Survey actual mouths,
directions, elevations, terrain and available space. Plan route families, crossings,
landings and structure extents together before constructing the controlling route.
Include station/depot footprints and access sides, city growth and road crossings.

Give principal routes coherent corridors and profiles. Fit secondary routes around
them, replacing disposable infrastructure where useful. Required merge-before-fork
order constrains topology, not the position of an existing bridge. Do not preserve
a secondary structure at the expense of an awkward mainline detour.

Design receiving space as well as departure space. Fit both ends and neighbouring
pairs together. Share compatible same-direction approaches when useful; each required
movement need not have a separate physical arm. Small fitting adjustments can preserve
the plan. Changed crossing order, extra levels, outward loops or displaced neighbours
require whole-layout reconsideration before dependent construction.

## Terrain-led corridor alignment

For the target-map rehearsal, station/city sites belong on suitable flat land.
Treat the high-level atlas as a service/topology brief, not fixed geography or a
universal elevation datum. Use user-placed guide tracks to identify natural passes
and useful levels. Compare modest horizontal deviations and selective cuttings with
repeated climbs or long structures; keep a coherent gentle mainline profile rather
than following every terrain undulation. Short terrain tunnels and deliberate
local earthworks are legitimate options. Do not assume an available numeric terrain API.

A longer shared approach can preserve more useful city land. At Mid-West, carry the
independent Cross pair beside the main throat through the cutting, then diverge
roughly 1 km away towards the short terrain tunnel. This is a site-specific user
alignment; crossing, ramp and regional-junction positions must be planned around the
whole family and actual terrain without compromising required service separation.

## Connection-led geometry

Aim for a satisfactory native realisation of the design, not exact reproduction.
Keep track roles, route order and intended corridor fixed; allow ordinary fitting
to slide junctions and adjust curve transitions within the available space.
Automate nearby proposal trials and accept the first coherent fit. Do not spend
model turns reconstructing equivalent geometry, discovering an exact optimum or
removing harmless native deviations. A rejected coordinate is not a failed design.
For a constrained turnout, a useful first search moves back along the approach
from the preferred point until the native proposal is acceptable. Express that
direction in the route's travel frame, then map it to the chain's orientation.
The manual tool may highlight an entire conflicting section; this does not locate
the precise collision or prove the whole section unusable. Local proposal trials
can find a usable point without diagnosing the engine's exact collision boundary.

Specify attachment points/regions, directions, corridors and neighbouring sweeps.
Treat radius and gradient as feedback/preferences unless explicitly required or
established by native behaviour. Real-world measurements are not automatic TPF3 limits.
Choose junction position, tangent, curve and length together; move a poor junction
rather than searching radii indefinitely. Native resources differ. One slope field
is not a universal turnout limit. A level run-in may resolve a rejected graded split
even when an accepted alternative has a larger peak grade.

Use a few purposeful sweeping sections. Avoid unnecessary straight interruptions,
late kinks, overshoot and curve/straight/reverse-curve sequences. Follow a neighbour
where useful, then diverge where space opens. Claim constant spacing only when the
actual geometry supports it; whole-route parallelism is not compulsory.

## Fans and crossovers

Review fan shape, total length and native speed feedback together. A smooth sweep
can still be unnecessarily long/fast near platforms, where final braking and initial
acceleration make distance important. Choose a compact fan envelope before routine
local native fitting, retaining the requested30m straight parallel platform leads.
The user accepts the current fans unchanged and the current approximately80mph
crossovers unchanged, but identifies the fans as too long/fast for future designs.
The slowest relevant fan should not be faster than its throat crossovers; roughly55mph
Challenge04/05 fans are a contextual reference, not a fixed speed/radius requirement.
Independent prebuild review must assess this relationship as well as visual shape.
No current-map repair, universal numeric gate or new train-physics model follows.

With staggered platform mouths, check the projecting neighbouring platform footprint,
not just exposed rail ends. Complete a fast road's lateral shift before entering
that footprint; the justified final straight may extend beyond its 30 m platform lead.
Coordinate neighbouring fans from a packed throat so an intermediate curve does not
cross another family's platform, lead or controlling parent.
Avoid long straight bank extensions and short gathering bends merely to create
construction anchors. Use continuous whole-family sweeps and keep the shared
corridor narrow until divergence towards the station is functionally needed.
Temporary construction stubs and straight anchors are staging devices, not final
design constraints. Review curvature across the whole approach; avoid concentrating
turning at artificial section boundaries. Retain a staging straight only where it
serves the final arrangement. Check signed curvature and heading within each realised cubic,
not just at its endpoints: matching guide headings can conceal interior reversals
and sign-changing curvature jumps. Derive guide positions and tangents together
from the intended whole sweep; review residual joins after native cubic conversion.
Approximately 5 m-spaced centreline geometry does not prove native parallel-strip
membership. Inspect shared range coverage when a joined ballast/terrain strip matters.
Building a straight tail separately with native `adjacent` offset can establish that
membership while preserving its existing branch curve and platform lead.
A short parallel continuation into the curved fan is also acceptable when the
native tool fits it smoothly. Do not force divergence at the straight/curve boundary;
fit the remaining turnout to the realised paired lead and check the complete route.
Manual preview reach is evidence of a candidate, not committed geometry or proof
that the remaining junction will fit.
Check fast, slow and independent pairs as one arrangement, including their root
stubs and receiving space; an accepted first family does not qualify its neighbours.

Beside a height-changing neighbour, use fewer envelope controls and delay rejoining
until clear of its ramp. A few extra metres locally can resolve observed terrain
clipping; derive the margin from the actual site, not a universal track-gap rule.
An accepted native proposal can still leave a lower track visually clipping the
terrain of a neighbouring incline. Allow a few additional game units of lateral
clearance where needed, and inspect the rendered ramp together with the lower
route. This is a visual quality check, not evidence of failed connectivity.
For a flying branch junction, assess the approach, flat crossing deck and exit as
one continuous alignment: a shallow deck angle alone does not qualify a tight
turn into the deck or an abrupt curve-to-straight transition.

Render the complete coupled merge/ramp/deck and receiving alignment before build,
including controls across family boundaries, decision signals and staging interfaces.
Use equal horizontal scale in plan/profile; keep authored, preview and committed
geometry distinct. Independent designer/reviewer judgement is needed at material
coupled changes, not each ordinary native fit. Accepted endpoint_cubic geometry is an
accepted local representation, not a native whole-alignment fitting service.
A horizontal temporary landing roughly450 native units before a deck produced a
25 ->32.14 ->15 lateral bow: the shallow deck alone did not establish a coherent
approach. Review and remove the artificial constraint where the approved design
requires it; these observations are an example, not fixed design gates.

Build controlling, constrained routes first, often outer fan boundaries. Platform
numbering is not build order. At the end of the straight approach, establish bounding
curves and reserve space for intermediates. Join a middle lead to the parent with
compatible turning direction and curvature. Mirror relationships, not assumptions
about terrain or nearby tracks. Remove a constraining early connection when needed.

A compact three-exit fan uses two staggered ordinary turnouts: branch towards the
outermost lead first, then branch from that curve towards the middle lead as close
to the first point as the native tool permits while preserving smoothness. Do not
assume single-point three-way turnouts. Track-only 5/10 offsets differ from 10/15
offsets allowing room for a platform. Neither fixes longitudinal turnout separation.

Use single crossovers where useful; avoid unnecessary scissors. Preserve intended
through roads rather than creating an accidental collector bottleneck. Plan exchanges
as a group. Compatible neighbouring-strip crossovers may overlap longitudinally;
turnouts sharing a rail require coordinated placement. Follow each required route in
travel order to avoid unintended reversal. Omit pointwork without a required purpose.
No universal minimum split angle, radius or turnout gap has been established.

Challenge04 supplies useful continuous parent/branch shapes, but its long fast fans,
short slow crossovers and extra fast-to-slow throat gap remain unresolved. Transfer
the topology, then tighten fan extent, lengthen crossover sweeps and pack the roads
around the fast alignment. A balanced three-bay slow fan on each road can reduce
spread if coordinated crossovers retain every required arrival/departure route.
Reference acceptance does not establish the desired speed balance or dimensions.

## Grade separation and construction order

Choose crossing order before curves. Compare forks before/after the crossing and
shared corridors. Plan the level span, both ramps and receiving pair together.
Build the controlling unconnected span first when this fixes its position clearly.

For a narrow flying junction, the user's preferred starting point is a shallow
10–15 degree crossing, with a level deck ending roughly 5–10 units laterally beyond
the crossed outer rails. These are visual preferences, not measured minima. A longer
shallow span can make the overall junction narrower. Use ordinary earth-supported
approaches where a structure is needed only at the crossing.

Separate fitting sections from structure boundaries. Tunnels need suitable cover;
marking a whole fitting leg as tunnel can expose its shell. Consider supports,
abutments and shells as well as rail-centreline clearance. Aggregate collision
bounds alone do not identify an obstructing pillar.

Construction order affects feasibility. One useful grouped-overpass sequence is:
remove affected parallel rails, prepare terrain, build/reconnect the shared upper
structure, then construct the diveunder. Another site may need the lower route first.
Use supported railway proposals, not direct deletion of generated bridge models.

## Terrain elevation

Use absolute targets and a site-specific floor to avoid exposed water, including
blended edges. The earlier z=1 floor was a user constraint on that map, not a universal
water level. Relative lowering by 15 is unreliable after earlier excavation.
Rail height, ground height and bridge underside are different measurements.

Starting the native Flatten tool on railway track can use its elevation as a height
reference. A disposable level track can provide the desired reference. Check resulting
ground and persistence after removing it. Ordinary NORMAL-track cut/fill may suffice.
Neither technique establishes an available numeric terrain-edit API.

## Stations, signalling and operation

Put shared platform choices after all required arrivals have merged. Correct wrongly
ordered pointwork before appending a reversing feeder. Plan arrival, return departure,
alternative platforms and depot access from the outset. Diagnose bindings and signal
direction before assuming that missing construction causes a failed route.

Build pointwork before signals. Use one-way signals for the intended road directions.
Keep the final incoming decision signal before all intended platform choices. On
long uninterrupted stretches, approximately 300 m along-track spacing is the user's
normal guideline, adjusted around pointwork and native eligibility. Short waits and
queues are normal; they do not alone justify a bridge investigation or capacity study.

Native signal placement needs an existing signal as a technical template. Discover
one instead of assuming an unsupported creation representation. Use native proposal
preflight and finite nearby offsets on the same eligible edge when a nominal
attachment is rejected; keep the signal before its intended decision/merge and
submit only the first accepted candidate. A known unsubmitted preview needs no
mutation reconciliation. Retain accepted prefixes and ordinary block phase.
Signals can split a physical track into native transport submovements. Directed
route queries must select the unique movement at the physical endpoint and check
the complete path. Native IDs can be recycled: follow replacement lineage using
ID plus endpoint identities, then refresh the current binding.
Inspect passenger
loading configuration and native service warnings; movement alone does not prove a
useful passenger service. Alternative-platform reachability and observed choice
under contention are separate claims.

## Accepted Mid West C lessons — future builds

The demonstration is accepted; apply refinements to future builds.

- For the intended 48 km map with hubs 15–20 km apart, reserve city growth and road
  crossings first. Target approach flyovers about 1.2 km from the hub and regional
  branches about 3 km away, with a defined station datum. These are project preferences.
- Keep the fast pair aligned; gather slow tracks alongside without needless gaps.
  Carry the independent East–West Cross pair with the main throat as a six-track
  corridor and turn away near the flyover. Asymmetric slow fans are acceptable.
- Smooth the whole ground-level slow alignment beside the flyover, avoiding needless
  bowing and curve/straight/return sequences from separately fitted pieces.
- Retain approximately 30 m of straight parallel platform lead before the fans.
  Slow fans may be shorter/tighter. Aim for throat crossovers no slower than the
  slowest relevant fan, using native speed feedback. For the Mid West C reference, the user found
  its roughly55–60mph fans appropriate and preferred roughly80m crossovers
  targeting75–80mph over Challenge04's roughly40m/35–40mph examples. These are
  user-reported observations/targets, not bridge-measured speeds or a linear
  length-to-speed rule. The120m crossover revision overcompensated.
  Balance speed against the distance from the final platform-decision signal and
  clearance time for departures. Keep the crossover group close to the fan where
  native turnout geometry permits. MW's successful80m fan-to-crossover gap was
  one accepted fit, not an established minimum; try a closer whole-group layout
  before carrying that gap into another hub. Preserve opposite turnout separation
  and required arrival/departure choices while finding this balance.
- Include ordinary open-line blocks as well as station decision signals. A few
  demonstration trains do not establish adequate real-network capacity.

## Fit, inspect and learn

Read fresh endpoints and incident tracks. Evaluate the complete local proposal,
including through-track replacements, then build its accepted prepared geometry.
Changed state needs fresh evaluation. Bridge-generated curves do not reproduce the
manual tool's internal fitter or its blue/grey attachment-eligibility cursor.

Distinguish fitting, native acceptance, committed connectivity, observed operation
and design quality. Check intended running roads, not merely existence of some path.
A failed candidate alone proves neither a game limit nor a bridge bug. Learn from
successful manual geometry and change a meaningful feature. After uncertain writes,
inspect actual state before repeating a mutation. Investigate proven functional
problems, not a nonblocking validation discrepancy alone.

Use reusable plans and deterministic candidate loops. Keep only current working
state needed for the operation; discard completed logs and candidate history.
Distil lessons into this guide or a reusable pattern, without dated narrative or
handoff archives. Stop polishing accepted demonstrations once their purpose is met.
