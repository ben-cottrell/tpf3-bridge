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

## Connection-led geometry

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
one instead of assuming an unsupported creation representation. Inspect passenger
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
  slowest relevant fan, using native speed feedback. The user's 35–40 versus
  75–80 mph impressions were estimates. Comparing 120 m fans with a 120 m throat
  is a useful experiment, not a fixed recipe.
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
