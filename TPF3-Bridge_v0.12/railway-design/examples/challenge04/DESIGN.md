# Challenge04 — Mid West C district

R6 complete for user review, 10 October 2026. R1 baseline retained below, followed by revisions.
Selected for construction following the successful native interface trial; use the
whole district arrangement below. User authorises the complete challenge, bridge
improvements and iteration. Challenge01–03 remain accepted baselines.

## Actual scaffold and requirements

The native survey found one station with18 distinct terminals and768 frozen TRACK
edges. Its18 disconnected rail chains match the intended provision. There are no
external leads. Native terminal numbers below are one-based survey numbers; native
line commands use zero-based indices. They are not arbitrary nearest-track labels.

Local origin is world(549.08783,-2758.25244,1.29925). North vector is
(0.069057,0.997613), east is(0.997613,-0.069057). UP travels local north. Local
coordinates are native game units, not distances measured from artwork.

| Role | Terminals | East offsets | South/north ends |
|---|---|---|---|
| Express UP |1,2|−35,−30|−140 /260|
| Express DOWN |3,4|−20,−15|−140 /260|
| South regional bank |5,7,9,11|−5,0,10,15|−220 /20|
| North regional bank |6,8,10,12|−5,0,10,15|60 /300|
| South stopping bank |13,15|25,30|−220 /20|
| North stopping bank |14,16|25,30|60 /300|
| Independent cross bays |17,18|40,45|−180 /140|

The opposed slow-bank ends at20 and60 remain unconnected. Cross bays connect only
at their south end. Four express tracks stay through; regional/stopping access
shares the appropriate slow pair, with service-specific platform choices. No
fast/slow transfers, junction tunnels, scissors or extra slow bypass.

Survey evidence: .local_runs/operator/district04/station-role-survey.json and its
linked native station/edge receipts. Native operation and passenger interchange
are not established merely by the rail graph. Three approach/cross surveys found
no external railway in their regions. Ground samples mostly0.5–2.35, except the
far north near1700 where it rises to15.7–26.9: keep the northern operating fixture
short of that rise or adapt its approach, rather than assume unlimited flat land.

## Whole district arrangement

Keep the station's western express/eastern slow grouping. Build independent fans
at both ends, then grouped approach, F reorder, ordinary four-track section, J
regional junction and outer test terminal. The cross pair departs south and turns
east, remaining independent. Two regional destinations lie west, one per approach.

Provisional longitudinal reservations (local north coordinate):

| Family | South | North |
|---|---|---|
| Station fan and platform choices |−440 to−140|260 to520|
| Clear grouped approach |−510 to−440|520 to590|
| F: US crosses UF/DF only |−950 to−510|590 to1030|
| Ordinary order / J lead |−1030 to−950|1030 to1110|
| J: west regional fork and separated return |−1470 to−1030|1110 to1550|
| Outer operating fixture |near−1600|near1600, before terrain rise|

These reserve whole curve/landing families, not fixed mandatory span lengths.
Between F and J, west-to-east order is US–UF–DF–DS. At the station it is
UF–DF–US–DS. Normal rails converge to5-unit spacing after reordering. F carries
US above the two fast rails; DS stays outside. At JN the regional return crosses
US/UF/DF to DS. At JS the DS outbound crosses DF/UF/US; return joins US directly.
All four trunk rails continue beyond each J. West branch pairs aim to stay together
outside their necessary vertical divergence, serving two-bay regional terminals.

Choose shallow approximately12-degree level crossing spans first, with provisional
7.5-unit lateral margins beyond crossed rails, then NORMAL earth-supported ramps.
These are accepted design starting points, not universal native rules. Full ramp
and turnout profiles matter more than a radius target. Keep level turnout leads
where required by observed native fitting; no invented UK gradient restriction.
Do not lower terrain below water to manufacture clearance. Ground datum follows
the scaffold near1.3; preliminary crossing rail datum is about17, subject to native
clearance feedback. Mainline remains principal; branches do not force its rerouting.

An alternative of independent long branch arms was rejected: it repeats the wide,
disjoint geometry of Complex Junction. A combined F/J tangle was also rejected:
keeping their route order and distinct landing regions makes fitting and operation
clearer. Compact them only when the whole arrangement retains those relationships.

## Construction and operation sequence

1. Qualify one native extension from an exact exposed frozen station node. This is
   a local interface trial, not station reconstruction. Establish named station
   roles and external leads; never select the internal gap ends as departures.
2. Build controlling F/J level spans and the through corridors/receiving leads in
   their reserved regions. Fit paired ramps and review the whole family before fans.
3. Establish outer fan boundaries first. Intermediate slow tracks branch early
   from the appropriate outer same-direction sweep. Add separate single crossovers
   for arrivals and returns after the required merges, before platform selection.
4. Connect regional/cross destinations and outer operating fixtures. Add depots on
   deliberately reserved plain approach sections, not squeezed between turnouts.
5. Apply one-way running signals and final platform decision signals before the
   shared platform choices. Existing signal template is a native prerequisite;
   inspect the map and report a real missing-template blocker if necessary.
6. Verify required directed paths, then observe representative express, stopping,
   regional and cross services, including terminal return and alternate-platform
   configuration. Ordinary queues do not trigger a capacity investigation.

Local fitting may move a turnout within its family, adjust curve/profile or native
representation. Changing crossing order, eating another family's reservation,
adding a loop/reversal or materially widening the corridor requires an updated
whole plan before dependent construction. Coordinator owns these choices; no new
user approval for authorised fitting. Sol implements reusable bridge gaps.

## Progress and remaining uncertainty

Both station F flyovers and both outer regional J families are built. Each F has
four native through-path checks. All22 external station leads and20 required
express/slow fan connections are built. North fan crossovers now build after
coalescing artificial plain-track subdivisions, without changing their positions
or the fan alignment. North T6 arrival and departure paths from/to the J outer
boundary at1550 are verified. South crossovers and full terminal route coverage
remain pending. Three two-track destination stations are placed; their links,
independent cross corridor, outer operating fixtures, signals, depots and services
remain under construction. No train-operation or final design acceptance claim.

Specific bridge qualification: the small spatial query returned one endpoint
witness with complete three-edge incidence but omitted the selected retained edge.
Exact incidence plus fresh snapshots of every named edge resolved the endpoint;
no search tolerance or free-port ownership rule was relaxed. Both plain merges
and both previously rejected north crossovers then succeeded natively. This is a
local demonstration of segmentation affecting fitting, not a universal explanation
for rejected turnouts. Scoped station identity/frozen inspection also avoids walking
the growing external district while retaining exact terminal association.

Completion has four separate claims: built, connected, observed operating, and
designer-reviewed for user review. No claim is complete yet. Full evidence and
operator receipts remain in the ignored district04 run folder.

Scaled whole-district corridor plan: [PLAN_R1.svg](PLAN_R1.svg). Station detail deliberately enlarges lateral spacing; whole-district view has equal axes.

## R1a — north F native fitting, before dependent families

The first free deck built, but its generated structure collided with the lower UF
proposal. Removing that deck, building the lower rails, then rebuilding the same
span succeeded. Thus span geometry first does not imply committing it before its
lower corridor on every site. Native collision evidence identified the structure.
The200+unit ramps now use560..760 and854..1060, within the clear approach/landing
reservation. Original170-unit rise had13.77% sampled peak and native Too Much
Incline rejection. It also collided specifically with DS edge46182. DS is revised
as a controlled shallow outward sweep through x20 at735/885, returning to its
existing ends. This reserves earthwork room rather than repeatedly fitting US into
an occupied strip. No fast track moves, route order changes or additional levels.
Review the resulting complete F before propagating it to the south.

## R1b — station fan detail before construction

Both F families are built with four native paths each (north46b3635b5d5343ac,
southcb52374347a04306). North visual review shows a narrow shallow crossing and
earth ramps; no operating claim yet. All22 selected station exits now have30-unit
leads,21 in9f04543af7234ca6 and the earlier T1 north trial.

Each slow fan uses two three-platform groups: north6/8/10 and12/14/16,
south5/7/9 and11/13/15. Two longitudinally separated single crossovers permit
both approach directions to use both groups; line configuration retains the four
regional/two stopping role split. Direct outer sweeps are built first. The middle
platform joins the outer sweep early; the other extreme connects at the approach
transition. Fast UP and DOWN each split independently into their two express tracks.

North slow group straight-to-fan transitions are around y430–445. The incoming/
return crossovers occupy y440–550, including the level US landing stub; fan branches
fit toward the station leads at330. South mirrors this around y40. These short,
low-speed platform fans deliberately avoid a large radius mandate. Native fitting
may shift a branch within this family; a failure must not silently consume its
neighbour's route. The two express fans use the wider290–560 interval.

## R2 — northern regional terrain and approach fitting

South ten-platform fan reproduced successfully in one batch (e94263a5979c49e8).
North has all ten platform connections; crossover proposals still require fitting.
Changing the crossover order preserves every intended movement and uses the level
landing lengths better. Do not extend the flyover solely to work around operator
segmentation: investigate the demonstrated local representation restriction first.

The northern regional site rises to31–36 at x−200..−350,y1560. Its destination and
paired landing therefore use datum31, rather than cutting the entire hillside to
station datum1.3. JN retains ordinary-order four-track mainline at grade, with a15°
level return span from(5,1310) to(−25,1422), datum17, and its eastern merge near1110.
The west landing is(−200,1555/1560), datum31; the direct US branch startsnear1190.
The return ramp meets the higher ground after crossing, while the direct branch
climbs alongside. Both entire corridors and their two elevations are planned before
construction. Native ramp/through clearance remains the controlling local trial.
The fast operating fixture is reserved near1650 at~15, with slow fixtures farther
north near1900 at~22; observed ground there is~15/22, avoiding a large deep cut.

## R2 independent cross corridor and destination detail

The independent cross pair uses the reserved southeast corridor. From C terminals
17/18 the leads continue south to local y-365 at x40/45, then turn east as nested
quarter sweeps with common centre(195,-365), arriving on y-520/-515. Straight paired
track continues to the Cross destination's west-facing ends at x650. C-side choice
crossovers occupy y-230..-335; destination choices x525..630. The plain x300..450
section is reserved for a depot connection, separate from both crossover groups.
The paired destination stations for north/south regional services stand west of J,
with their east-facing entries at x-330 and two straight connections to x-200.
Their separate35-unit crossovers fit on that existing plain approach. The initial
regional rejection was a target travel-direction input error, corrected without
changing length or segment representation. Do not conflate it with the demonstrated
north station segmentation failure. South station coalescing and both crossovers
also succeeded. Route availability and operation are checked separately.


## R3 — outer operating fixtures and open terminal ends

The Cross pair and four choice crossovers are built in b9b80c57eeb84e6a. Its first terminal faced the wrong way: incidence-free buffer-end TRACK nodes were real but not extendable. Replacement template5 faces its positive-local-Y open side west. The paired corridor was retained, with destination crossovers at x475..580 and30-unit station leads. Native build now succeeds without geometry changes.

Outer fixtures are independent express and stopping termini, rather than a new fast/slow transfer. OUTER_R3.svg records the selected local-coordinate reservations. North express rails rise from y1550,z1.3 to1810,z21, then run level to station open ends1940 (closed ends2100). Slow roads widen to x-50/+35 by1830,z21, pass the express footprint to2140,z18, and converge to x-12.5/-7.5 at2220,z12. Their terminal opens at2340 and closes2500. Northern ground samples rise to20.6 at1800, fall to16.8 at2200 and8.5 at2400; station cut/fill is intentional. South remains at datum1.3: express open-1680/closed-1840; slow bypass x-50/+35 through-1880, converges-1960 and enters its station at-2080/closed-2240. Separate paired crossovers on each plain final approach permit both platforms and return routes.

These are operating destinations beyond J, not additional middle-hub junctions. Express depot access is reserved on the flat southern approach; slow and cross depots remain on their own networks. Selected sequence: terminals, controlling outside slow corridors, fast links, choice crossovers, then depot branches and signals. Native grade/structure outcomes may adjust profiles within these reserved corridors.


## R4 — depot reservations before placement

Four independent networks receive depots: express branches from southern UF near(-12.5,-1490) into the strip between UF and the already spreading US, with its port(-30,-1620), outward north; the building extends south. North slow branches from the outer DS bypass(35,1900) to an east-side depot port(110,2060), outward south, datum20. South slow branches west from US(-50,-1700) to(-120,-1850), outward north. Cross branches south from(350,-520) to(470,-580), outward west. The latter three lie outside their running corridors; express deliberately occupies the separated bypass strip without crossing slow tracks. Native realised port/footprint and turnout fit remain to qualify. Signals are placed after depot turnouts so edge identities and decision-point ordering reflect the final geometry.


## R5 — actual depot footprint changes the southern US reservation

Native express depot placement rejected Collision. Source-qualified template2 footprint is36.035 wide, not a small trackside hut; the37.5-centreline gap left only1.465 total room before track envelopes. The earlier plan omitted this asset footprint. Widen only the southern US bypass to x-80 between y-1620 and-1800, returning to the existing convergence at-1960. Retain fast tracks, DS, station positions and crossovers. This creates67.5 between US/UF; select express depot port x-45,y-1620, with authored lateral extent about[-63.8,-27.8], leaving room either side subject to native acceptance. South slow depot already stands outside atx-120 and connects from the revisedUSx-80. Replace the three exact plain US segments as one native proposal; no compensating crossing or new level. Future station/depot reservations must include actual asset footprints before filling adjacent corridors.


## Operating signal intent

One-way running signals establish UP/DOWN use at each end of the through and slow networks. The final incoming signals precede the complete relevant platform-choice crossover/fan, with no extra incoming signal on a platform-specific branch. Terminal platforms and depot spurs remain reversible; outgoing signals lie beyond the pointwork in their outbound direction. Cross service uses C17/outer for arrival and C18/inner for departure, with the inverse at its destination. The24 initial signal locations are recorded in local signal-intent-R5.json; each is rebound to a fresh exact native edge and parameter before placement. Depot turnouts precede this step. This is basic representative operation, not a capacity/queue study.


## R6 — operating direction qualification

All four depots and24initial signals were built. Native path review exposed a real signal API translation error: the isolated express signal requested northbound allowed only southbound. Existing native lane-orientation readback alone had not established allowed train travel. Repair the translation and replace the signals before service acceptance. North route availability initially passed by using opposite running roads, so acceptance also checks which named running roads the native path uses.

The district direction policy is now explicit globally: UP roads northbound, DOWN roads southbound, including the southern approach. The earlier mirrored C_S policy is superseded: C_S_US at local(2.5,-470) is the northbound arrival decision signal; C_S_DS at(7.5,-500) is southbound departure. OuterSS andRS retain their original R5 compass directions; the temporary four-signal reversal is superseded. Existing crossover geometry permits all six southern bays in both directions and the south depot joins inboundUS. This revises operating intent, not track geometry. The completed directed-route and operating outcomes are recorded below.


## R6 native outcome and designer review

Both F reorders, both J regional branches, both station fans, the independent Cross
pair and seven destination stations are built, with four connected depots. The
24 corrected one-way signals were replaced against fresh exact attachments. All36
station-to-station directed paths pass; a separate read of each returned path also
finds both intended running-road signal edges. This catches the earlier inversion
which simple reachability missed. All18 C platforms participate in these checks.

Six two-part passenger trains were bought and assigned through the reusable
operating plans, each in six native calls (about2.9–3.3 seconds). Ten observations
across90 seconds of accelerated simulation show no noPath flags. Regional,
stopping and Cross services each alternate their two stop indices; the express
records3→0→1→2→3, completing its four-stop circuit. Native arrival-terminal
readback and changing world positions support the observations. Primary and
alternative platform configurations are present, and alternative platform paths
pass. Occupancy-driven selection of an alternative was not deliberately forced.

Final UI review found a separate missing line cargo-loading configuration, despite
successful movement. Commit e0e890c repaired native StopConfig loading masks. After staging/reload,
all six existing lines were explicitly updated: all 14 stops read passenger loading
enabled at full fraction. Further observation finds six moving trains, no noPath
flags, and the UI line warnings cleared. Physical circulation alone was insufficient
to establish this loading configuration. There is no populated catchment
on this disposable demonstration map, so passenger demand/capacity is not a claim.

Compared with R1, the controlling fan/F/J corridors and their ordering survived.
Northern outer fixtures moved onto the surveyed rise with appropriate profiles;
the Cross terminal was replaced to expose its actual open side. The principal
avoidable geometry rework was the southern US widening after discovering the
express depot footprint. That omission belongs in up-front planning. The attempted
premature Cross departure signal was another avoidable sequencing error. Neither
required changing the central station or the four graded crossing arrangements.

The designer's screenshot review finds coherent principal corridors, short shallow
level spans and earth-supported approaches, with smooth paired regional departures.
The outer stopping loops deliberately go around the express termini and depot
footprints; they are demonstration fixtures rather than a suggested whole-map
terminal arrangement. Northern cut/fill remains visually substantial, and overall
length is driven partly by separate operating destinations. These are points for
user review, not aesthetic acceptance inferred from successful trains.

Evidence lives under `.local_runs/operator/district04/`: `intended-roads-R6.json`,
`final-routes-R6.json`, `depot-service-R6.json`, `signals-R6-results.json`, and
`operating/operation-summary-R6.json` link the detailed native receipts. Captures
are indexed in `final-overview-capture.json` and `final-detail-captures.json`.

## Procedure regression reflection

This is an author self-review, not an independent blind evaluation. The affected
constrained-fan lesson remains satisfied: controlling outer paths precede middle
branches, with platform-specific departures reserved. The graded-junction lesson
remains satisfied: all F/J crossing order and landings were selected before build;
local fitting did not reroute a branch around an accidental obstacle. The known
station/depot footprint omission is explicitly a miss corrected in R5. Procedure0.5
now requires actual asset envelopes/open sides and explicit world-frame operating
directions. Signal inversion and missing cargo settings are bridge defects with
focused native examples, not reasons to impose new geometry gates or broad audits.

## Final review checkpoint

`Design Challenge 04 - Mid West C Ready for Review.sav` is saved and paused.
Native save callback and stable 42,232,877-byte file verified; SHA256
`6db45d7d982cd4d535653f15e9eadad5d3e2a22d8b598de695fc01d27f196cba`.
The final save has not been reloaded. Native evidence: `final-save.json`,
`operating/cargo-updates-summary.json`, each service's `*.cargo-update.json`,
`operating/cargo-after-operation.json` and `final-review-capture.json` beneath the
local district evidence directory. Passenger configuration is verified; no populated
catchment or capacity claim. Latest affected suites: 67 operator and 434 shared tests.

Ready for user design review, with no unresolved functional blocker. Sol remains
idle and the heartbeat paused. Earlier accepted challenges and their evidence remain.
