# Practical railway design through the bridge

For the active planning/build/review workflow, use
[RAILWAY_DESIGN_PROCEDURE.md](RAILWAY_DESIGN_PROCEDURE.md). Its
[pattern cases](railway-design/PATTERNS.md) and
[regression cases](railway-design/REGRESSION_CASES.md) turn the lessons below into
reusable decision examples. This handbook retains the detailed evidence and context.

Working guide, grounded in the Wickham terminal experiment. These procedures are
firm; dimensions and particular track patterns remain design choices. This is not
a claim that one template solves every layout or that native acceptance proves
operational capacity.

## Accepted Mid West C lessons — future builds

Challenge04 was accepted on 10 October 2026; leave the demonstration unchanged.
The complete [user review](railway-design/examples/challenge04/DESIGN.md#user-acceptance-and-forward-guidance--10-october-2026)
records all observations and distinguishes estimates from native measurements.

- Plan urban space and railway compactness together. On the intended 48 km map,
  reserve city growth/road crossings before locating approach flyovers (about
  1.2 km from the hub) and regional branches (about 3 km); hubs are 15–20 km apart.
  These are map-specific planning targets, not native geometry limits.
- Keep the fast pair aligned; gather slow tracks alongside it without unnecessary
  gaps. Asymmetric slow fans are acceptable. Carry the independent Cross pair
  alongside the throat as a six-track corridor, departing near the flyover zone.
- Review the entire slow alignment beside a flyover. Avoid unnecessary bowing and
  curve/straight/return sequences introduced by fitting individual pieces separately.
  Preserve useful sweeps, native clearance and paired-route relationships.
- Retain about 30 m of straight parallel platform lead before the fans. Make slow
  fans appropriately compact; aim for throat crossovers no slower than the slowest
  relevant fan. Use native speed feedback when available; do not infer verified
  speeds from appearance or impose a new radius gate. The user's suggested 120 m
  fan / 120 m throat is a comparison to try, not a fixed design requirement.
- Include ordinary one-way block signals on long open stretches, normally about
  300 m apart along track. Preserve the final decision signal before all intended
  platform choices and adjust placement around pointwork/native eligibility.
  A few working trains do not establish that sparse signalling is adequate for a
  busy network; basic block provision does not require an unsolicited capacity study.

## Construction sequence is part of the design

The intended final geometry and the intermediate construction states both matter.
When a supported-looking parallel structure fails, compare with the manual game
tool and consider terrain preparation, adjoining tracks and build order before
distorting the alignment or attributing the failure to the bridge software.

On 8 October the user also encountered rejection of a four-track parallel bridge
manually and supplied this sequence for the current crossing: clear the affected
parallel tracks, lower terrain around the corridor by15 game units, build and
reconnect all four mainline tracks on a coherent shared bridge, then construct
the diveunder. P75 has now demonstrated the clearance/excavation/overpass sequence:
native UI excavation lowered central samples by about15–16 units, then one grouped
bridge proposal built four tracks sharing native concrete strip71620. All four
directed A–B paths verified, and the overview shows a continuous deck. Excavation
was performed through the UI; programmatic terrain editing was not demonstrated
by this milestone. The subsequent DS diveunder built successfully near a roomier
ordinary-track merge (reconnection_checks.json, five of eight mainline routes).
The user later observed water pockets: future excavation must obey the absolute
z=1.0 floor below rather than repeat a relative15-unit lowering. This is site evidence,
not a universal15-unit rule. Local evidence is in
`.local_runs/live_python_interface/p75/overpass_first/group_checks.json`.
Observe the current terrain and actual shared structure; track-height arithmetic
alone does not establish that supports, abutments and construction states fit.
Preserve railway functions through reconstruction, rather than freezing temporary
track pieces that prevent the required construction sequence.

## Design the complete functional arrangement

### Wickham conclusion — user review, 5 October 2026

The user accepts the completed challenge as sufficient proof of the construction
capabilities it was intended to exercise. The platform fans remain unnecessarily
long for this slow terminal setting; do not describe their retained geometry as
compact or optimal. Further fan compression is a possible design improvement, not
unfinished acceptance work. Leave this demonstration in place and use a new useful
challenge to drive the next bridge capability.

- Choose the footprint for the actual game setting and intended movements. Slow
  platform approaches can justify tighter, shorter sweeps; attractive curves need
  not be long curves. Establish this envelope before filling in intermediate fans.
- Required access is a minimum functional contract unless exclusions are explicit.
  Incidental extra access is acceptable, but adding pointwork solely for extra access
  is not a goal. Wickham requires pairs1/2/3 to serve1–8/3–14/9–16 respectively.
- Pack compatible single crossovers alongside each other and coordinate junctions
  on shared tracks. Fixed successive full-width exchange zones waste length.
- Develop through concrete gameplay/construction challenges: define an observable
  useful outcome, attempt it with existing capabilities, add reusable bridge support
  for demonstrated gaps, and return to the challenge. Stop polishing the demonstration
  once its purpose is met; carry transferable lessons into the next challenge.

Start with game capabilities and the intended railway function. Express connections,
directions, neighbouring-track relationships and the desired visual sweep; use the
game's supported construction to realise a practical equivalent. Reference drawings
and real-world dimensions are inspiration unless explicitly required. Neither fixed
distances nor fixed radii are a substitute for designing the relationships.

Classify each constraint: user requirement, demonstrated game requirement, design
preference, or untested hypothesis. Only the first two justify a hard acceptance
gate. A failed bridge candidate does not establish a game limitation, especially
where a manual construction succeeds. Reconsider our representation and assumptions
before distorting the intended layout to suit one fitting algorithm.

1. State required approach-to-platform movements, directions and useful simultaneous
   movements before choosing curves. Keep a list of unfinished connections.
2. Establish the actual station mouths, elevations, terrain, approach alignment and
   available footprint from current game state. Use game-scale dimensions.
3. Sketch continuous approach tracks and their fan groups. Avoid accidental shared
   bottlenecks. A connection to the wrong group is not progress merely because it builds.
4. Design neighbouring tracks together. Reserve their corridors and turnout locations
   before committing an individually attractive connection.

### Establish route priority before retaining infrastructure

The first Complex Junction redesign still bent the slow mainline return around
existing branch crossings. The user rejected that priority on 7 October: establish
the A–B/C mainline split first, then fit or relocate the D/E routes around it.
Moving a few junctions while retaining the branch structures as geographic anchors
did not address the whole-layout problem.

- Rank the routes whose alignment should shape the junction before selecting
  attachment points. Give the principal routes coherent corridors and profiles;
  arrange secondary crossings and connections around those corridors.
- Separate functional order from geographic position. D/E slow connections must
  reach the common stem before the C split, but that does not fix the common stem,
  branch junctions or crossing structures at their existing locations.
- When a proposed mainline has an awkward detour, ask which retained object is
  causing it and whether that object has any genuine preservation requirement.
  Reconsider the whole affected junction before polishing the detour.
- This is a hierarchy of design priorities, not a ban on every reverse curve or
  permission to sacrifice required branch movements. Account for those movements
  in the revised arrangement and distinguish a proposed corridor from a built one.

## Shape and construction order

- Boundary-first fan pattern: establish the two controlling routes at the end of
  the straight approach, reserving the space between them for intermediate tracks.
  Choose each intermediate track's parent by compatible direction and curvature,
  avoiding unnecessary reverse bends. Wickham6/8 bound7, which joins6; mirrored,
  9/11 bound10, which should join11. Check actual surroundings before mirroring.
- Separate desired fitting radius from a mandatory minimum radius. Do not turn a
  shaping preference into an acceptance requirement the user never requested.
- Before choosing the next platform, identify which unfinished neighbour it could
  constrain. For Wickham's 10–12 group, establish 11 before 10. A rejected optional
  10 candidate is not a blocker to designing 11.
- Build the most constrained controlling route first, often an outer fan boundary or
  an inner route trapped between neighbours. Platform numbering is not build order.
- Follow a neighbouring sweep where that provides a useful corridor; diverge where
  space opens. Exact parallelism for the entire route is not compulsory.
- Choose junction position, departure tangent, curve shape and available length
  together. Do not freeze a poor junction and search radii indefinitely.
- Use a small number of purposeful curve sections: coordinated sweep, separation,
  attachment. Avoid excessive straight sections, late kinks and outward overshoot.
- Treat resulting radius as useful feedback and, optionally, a shaping preference.
  Default to attachment points, directions and corridor-led fitting. Require a minimum
  only for an explicit or demonstrated requirement. Slow terminal fans can use tighter
  curves; no universal minimum split angle or radius was established here.
- Use separated single crossovers where needed while retaining through tracks.
  Scissors are not required by the current challenge.
- If an early connection obstructs a better arrangement, redesign the affected group.
  Disposable track IDs are handles, not preservation requirements.

## Observe, fit, build, learn

The original radius-led approach was a means of seeking attractive curves, not a
user requirement for prescribed radii. Keep that intent separate from the mechanism.
The working contract is: required connections and directions, a suitable corridor,
compatible neighbouring sweeps, and native construction acceptance. Measure the
resulting curvature rather than making a guessed radius dictate the layout.

Be precise about what is native: current endpoint-cubic candidates are generated by
the bridge and evaluated by the game. They are not a reproduction of the manual
tool's internal fitter or blue/grey attachment cursor. Prefer an exposed native
capability when demonstrated; where it is missing, make the bridge approximation
explicit and learn from accepted manual examples. Do not promise unavailable feedback.

1. Read fresh endpoints, tangents and incident tracks before modifying the area.
2. Fit the controlling curve and inspect its relationship to its neighbours throughout
   its length, not just its endpoints. Check where remaining routes will go.
3. Use a bounded native preview when it resolves a concrete construction question.
   A successful geometric fit does not establish construction acceptance.
   Evaluate the complete junction, including through-track replacements. Construct
   the same prepared geometry that passed evaluation; changed state requires fresh
   evaluation, not an undisclosed refit. Native attachment eligibility, curve fitting,
   proposal acceptance, realised connectivity and visual quality are distinct checks.
4. Build a useful connection, then confirm exact attachment and the intended native
   train path. Judge visual shape separately. Native pathfinding is not a train run.
5. Record useful accepted geometry and failed attempts with the relevant world state.
   After uncertain mutation, read the result before issuing another mutation.
6. Continue the design after proportionate verification. Investigate diagnostics only
   when they block required work or reveal a demonstrated functional problem.

## Responding to rejection

For several approach pairs, design the order of exchanges as well as their geometry.
A route must meet its next crossover ahead of it in its direction of travel. Merely
connecting the undirected graph can leave a movement requiring reversal. Wickham's
completed arrangement uses separate pair-to-pair exchange sections and selected
upstream pair crossovers; all 56 requested directional paths were found natively.
The initial conservative arrangement ended at1250m. P58 rebuilt the straight
approach to650m with ten ordinary40m crossovers and retained the compact platform
fans. All56 required directional paths still pass natively. The40m spans/15m gaps
are accepted choices for this layout, not proven engine minima. No scissors or
compulsory reduction of the six through tracks was required.

P59 retained those ten functions and fans while packing the approach to550m.
Separate neighbouring-strip crossovers can overlap longitudinally. After one close
shared-rail placement rejected, the remaining junction group was repositioned
together; all56 paths pass. Actual crossover spans39.671–49.880m are successful
choices, not native minimum lengths or gaps. Do not freeze each local connection
while leaving its neighbours without room.

Classify the evidence: unsuitable layout, native construction rejection, bridge
contract/implementation failure, or transport uncertainty. Do not infer a bridge bug
from rejection alone, or dismiss a near-equivalent manual success as merely design.
Change a meaningful geometric feature, not just arbitrary radius values. Compare a
successful manual example's branch and through-track geometry when available.
Native error explanations can be incomplete; neither Lua nor Python can manufacture
missing engine feedback. A proven reproducible bridge failure belongs with the
implementation agent; railway topology and geometry choices remain with the designer.
Use structured candidate data and compact outcome records to automate practical
experimentation. Prefer changes explained by a successful reference or observed
failure over blind parameter sweeps. Do not claim the bridge reproduces the manual
tool's internal algorithm or cursor eligibility feedback without evidence.

## Evidence from Wickham

- P58 accepted all ten compact single crossovers with full native proposal checks,
  then built the prepared controls. Segmenting two approach rails allowed early
  crossover placement within the bridge's interior-parameter domain; this is an
  interface condition, not a minimum game-scale throat length. A different native
  fit preference resolved one legacy micro-arc failure without enlarging the layout.
- P59 exposed a prepared-build recovery gap: accepted preview can still reject at
  construction, and its consumed handle cannot be used for a dry run. Reconcile
  correlated preparation evidence against exact original tracks, native routes and
  bounded local observations. Never replay the handle or call unchanged originals
  a rollback guarantee; unrelated partial effects may remain unknown.
- P54 rebuilt11 successfully at the intended junction by evaluating a distinct
  one-piece endpoint candidate, then building its prepared geometry without refitting.
  Native parts rejected at the same attachments. This supports representation-aware
  fitting, not moving a good junction merely because one representation fails.
  Existing-node preparation does not yet cover interior curved-track junctions;
  the subsequent10 attempt exposed that remaining limitation (operation30).
- Platform11's two-section sweep fits and its station-side section builds, but the
  approach junction rejects (operation27). Mirroring a successful manual reference
  guides design; it does not guarantee acceptance of a different native proposal.
- Building platform 5 first restricted platform 6. The user's successful 6 route
  follows its neighbour for most of its length, then curves into the approach.
- Removing earlier 7/10 connections allowed 8/9 to establish the central envelope.
- The user's 7 route follows 8 before joining 6 near longitudinal 245 m, approximately
  55 m before the approach entrance. Its native path is confirmed. This is close to
  a rejected guided proposal; the cause of that difference is not established.
- Manual construction resegments through tracks. Changed entity IDs alone do not
  demonstrate changed geometry. Small geometric differences alone do not prove cause.

Local evidence: `.local_runs/design/terminal_16_8_12_8/manual02`, `manual03`,
`operation23` and `operation25`. Update this guide when another outcome supplies a
transferable lesson; label hypotheses rather than turning them into hard rules.


## Evidence from Complex Junction

P60-P65 completed the construction challenge with 18 required native directed
paths. These checks establish connectivity, not train operation, signalling,
capacity or continuous clearance. The final footprint is a working demonstrator,
not a proven minimum-size layout.

- Start from native reference structures and actual attachment roles. Successful
  reference heights and grades inform candidates; they are not universal limits.
- Separate fitting sections from bridge/tunnel boundaries. Portal placement needs
  appropriate terrain cover; marking an entire fitting leg as tunnel can put its
  shell above ground. Preserve accepted curves while adjusting structure spans.
- Plan the vertical crossing before fitting its approaches. Track centreline
  separation alone omits bridge supports and tunnel shells. Observe the actual
  collision entities before changing the design or blaming the bridge.
- Allow local widening of the trunk when ramps need space. Preserve the four
  ordered through functions rather than freezing their original coordinates.
- A level run-in can resolve a graded turnout attachment. It is a useful candidate,
  not a rule that every turnout must be level.
- A true normal-offset curve is useful only where endpoint and grade constraints
  permit it. Independent paired curves can retain the intended function when a
  whole-route offset fails; do not claim constant spacing for those curves.
- Reconsider an earlier structure when it obstructs a later required route. P65
  repaired a shallow tunnel span and revised the slow approach under the fast
  pair rather than preserving an unsuitable local choice.
- Native proposal error messages matter even when a critical flag is false.
  Distinguish errors from warnings, and build the exact accepted prepared controls.

Evidence: `.local_runs/live_python_interface/p65/HANDOFF.md` and referenced
P60-P65 records. Final save: `TPF3_Complex_Junction_P65_Complete_20261006.sav`.

## Absolute excavation floor — Complex Junction, 9 October 2026

The user's screenshot shows water in the P75 excavation beside the lower track.
For this map, apply the user-selected hard terrain floor of absolute z=1.0 to
all excavation, including brush falloff and blended edges. A relative instruction
such as "lower by15" is insufficient on uneven or previously excavated ground.
Use target elevations and observe the resulting surface; a UI-only terrain tool
does not imply that the bridge already implements an automatic height clamp.

On resumption, raise the existing over-deep pockets to at least z=1.0 and shape
the surrounding cutting accordingly. Current mainline rail height is about16.25;
its15.25-unit difference from the terrain floor is not a verified structural
clearance, because rail height, ground height and bridge underside differ.
Meet native construction requirements through the track/structure arrangement
rather than excavating below the floor. This is a map-specific user constraint,
not a claim of a universal game water level or guaranteed native acceptance.
The user subsequently resumed the redesign on9October; repair and floor enforcement
are part of that active work. This documentation does not imply the terrain has
already been repaired or that a programmatic clamp exists.

The user supplies a native height-reference technique: start Flatten on a railway
track to clamp the tool to its height. A temporary level track at the desired
elevation can provide that reference. Prefer this track-anchored workflow over
attempting to carry a bank's cursor height into an excavation. Treat it as direct
human operating evidence; check the actual resulting terrain and its persistence
after reference-track removal in our implementation. Reference tracks are disposable
construction aids. The technique does not itself expose a numeric terrain API.

P75 subsequently reproduced this locally: anchoring Flatten on the lower DS track
raised a former surface sample from0.3318 to1.3502; eight nearby surface samples
were1.25..1.85. Evidence: `p75/central_pair/track_flatten_test2_readback.json`
under `.local_runs/live_python_interface/`. This establishes the local track-anchor
treatment, not a whole-site floor or terrain persistence after rail removal.
Underlying base heights can differ from the track-influenced surface. A broader
measured-Raise treatment also overshot a neighbouring patch; prefer the native
track reference and small observed corrective passes instead of prolonged raising.
The eight surface samples persisted across save/load, but subsequent rail removal
exposed residual low ground; a new structure build failed with native "Place on
Land". Track-anchored treatment must therefore be checked after removing a temporary
reference when the final design does not retain its terrain alignment. A dry
track-influenced surface does not establish a repaired underlying excavation.

## Crossing order and total footprint — P75 design correction, 9 October 2026

Do not minimise crossings or simplify one proposal at the expense of the whole
junction footprint. The first central-pair layout placed the fast underpass,
UP(slow) divergence and DOWN(slow) crossing in successive zones. It verified the
required routes, but the user's overview exposed excessive spread. A concrete
alternative is to branch UP(slow) before the fast underpass and carry its branch
over the fast pair alongside the two continuing upper roads. This alternative
is selected for fitting; it is not yet native-accepted or built.

Before fixing junction locations, compare the ordering of forks and crossings
in plan AND profile. An extra bridge may replace a long approach, separation
zone or return curve. Judge the total envelope, including ramps and downstream
ties, using the same boundary anchors. Reserve room for descending tracks and
adjacent route families together. Fewer structures and the first accepted native
proposal are not sufficient evidence of a good layout. An interface limitation
is not a native design rule; test the missing capability when it demonstrably
forces poor geometry. These are comparison practices, not a universal rule to
branch before every bridge or to add more structures.

The compact candidate was subsequently built (P75 compact_build, local milestone
0583d5c). Eight directed mainline paths verify. Native construction retained the
three-upper-path crossing arrangement and earlier trunk closure, with small fork
adjustments; the DS descent realised about8.30%. The actual game view and full
as-built plan/profiles show the result. Initial US construction rejections named
old elevated rail remnants; removing those resolved those specific collisions.
This does not retrospectively explain the earlier generic diagnostic rejection.
525 affected ground-surface samples were >=1.15. Two lower underlying base values
under a1.7 surface remain recorded; no current exposed-floor failure was observed.
If later removal exposes low ground, treat that actual change rather than blindly
raising a track-influenced surface to alter an unresponsive base diagnostic.

## Fit route families together — P75 branch planning, 9 October 2026

Fit opposing tracks around a common corridor and explicit track order before
designing each curve. The first D/E access candidate crossed the opposing D-B
tracks twice in plan and resolved accumulated conflicts with49/64.25 height tiers.
That was a consequence of the candidate, not a demonstrated native requirement.
Coupled guide stations removed the paired-family plan crossings in a later fit;
the complete branch arrangement is still prospective and unbuilt at this point.

Treat a fork as a local plan-and-profile problem. Neighbouring opposing tracks
may need to separate vertically at a flying junction. Keep the lower route low
until it clears the overhead bundle, and place its rise after those crossings.
Move attachment positions, crossing positions and ramp extents together. A height
that works on a plateau does not supply the same clearance halfway along a ramp.
Use a local overpass or underpass where it resolves the movement order, instead
of lifting an entire route family above every previous route.

Compare every candidate using its current whole plan and full profiles. Regenerate
figures after edits: a chart from an earlier fit can hide newly introduced ramp
conflicts. Sampled intersections help locate a concrete problem; native proposals
decide construction acceptance. Neither a clean drawing nor a failed custom fit
establishes what the game can build.

## Completed P75 lessons — 9 October 2026

The coupled branch design and station restoration were subsequently constructed,
recorded in local milestone c64bea9 and checkpoint
`TPF3_P75_Complete_Operating_20261009.sav`. Evidence is under
`.local_runs/live_python_interface/p75/branch_coupled/turnarounds/`.
All18 infrastructure routes and16 station-terminal combinations pass. Slow and
direct train stop sequences demonstrate round trips, beyond endpoint connectivity.
These results establish this native build, not an optimal layout or a general
version-independent construction rule.

- Design receiving space as well as the source turnout. D_C's source fork passed
  when its approach matched the parent bridge's vertical profile, while its landing
  remained constrained. Moving the C slow pair inward created room to cross the
  fast roads high, then descend on the fast side of the receiving US road. Fit the
  receiving pair and its other branches together; do not squeeze the new connection
  between opposing tracks just because those coordinates were already built.
- Share compatible same-direction approaches. C_D ultimately joined B_D rather
  than forcing another turnout onto a roughly24-unit station lead. Check native
  continuity for both movements; do not require a separate physical arm for every
  entry in the movement matrix.
- Construction order can affect generated structures. An unchanged E_B split
  collided with aggregate model content from the direct bridge. Removing its
  parent TRACK spans, constructing E_C, then restoring the direct pair succeeded
  with the original bridge asset and geometry. This demonstrates one native
  reconstruction sequence; aggregate bounds did not identify a precise bad pillar.
  Never bypass collision feedback or directly delete a generated model as a rail.
- Put a shared choice after every route that must reach it has merged. The first
  A return turnout preceded the C/B merge:18 infrastructure paths passed but two
  station paths failed. Replace the wrong-source approach rather than append a
  reversing feeder to preserve it. The temporary loop was removed and a direct
  outward graded bow from the common approach restored all16 station paths.
- Include station arrival, return departure and alternative-platform reachability
  in the design brief from the start. Correcting two reversed D/E arrival signals
  restored all eight D/E platform combinations without new track. C needed ordinary
  separated crossovers; A's intervening fast roads required grade separation.
  Diagnose bindings and signal direction before assuming missing construction.
- Review plan and profile together after each material native adjustment. Keep
  paired corridors coherent while allowing local vertical separation. Evaluate
  the whole footprint before retaining an outward bow or extra structure. The
  completed result is a useful tested pattern, not a licence for endless local
  additions or a claim that every remaining bend is minimal.
- Inspect a prerequisite check's result before its dependent mutation. One C_E
  build was issued before its independent screen failure was read. The failure
  concerned two intersections with still-prospective E_C, not a demonstrated native
  collision; later E_C native acceptance resolved the practical question. Preserve
  the discrepancy honestly, and do not turn a sampled diagnostic into an invented
  universal clearance threshold.

Completion limits: platform alternatives are configured and their paths verified;
actual alternate selection under contention was not demonstrated. Final C terrain
checks cover80 sampled points (minimum1.0), with28 affected track geometries and
structures unchanged. Prior E/mainline scoped evidence remains separate. One
functioning train retains a deleted home-depot reference; no observed running
failure justified extra replacement or runtime state patching. The final save's
bytes/hash were verified, but that final checkpoint was not reloaded.

## Shallow flying junction — Challenge03, 10 October 2026

A native-accepted steep-angle flyover was visually too broad. The user's preferred
alternative was a10–15° crossing with a level deck ending roughly5–10 units laterally
beyond the outer crossed rails, followed by earth-supported approaches. These are
contextual visual preferences, not measured game minima. The whole family was
replanned before rebuilding: R5b uses12°,7.5-unit side margins and a96.2-unit deck.
All four required paths pass. Designer review is positive; user review is pending.

Plan the deck, both ramps and receiving pair together. Construct the controlling
unconnected span first when that makes its position and extent unambiguous, then
fit the ramps and direct route. Prefer a coherent NORMAL earth approach when a
bridge is needed only at the crossing; do not extend structures by default merely
because the track is elevated. Actual native cut/fill and acceptance still decide fit.

Vertical shape at the turnout matters independently of peak grade. R3's sampled7.6%
first junction segment failed Too Much Incline; R4 succeeded at11.2% after a level
lead. The resource field maxSlopeBuild0.085 was not a universal cap. Final R5b peak
sampled grade is10.20%. Do not infer all native rules from a resource field or turn
radius/grade preference into an artificial blocker. See the retained design history.

One fitting stop came from the adapter's5–95% interior-parameter restriction, not
the native engine. Report that distinction and use intentional local alternatives;
do not generalise it into a required turnout distance. Long-term eligibility feedback
should expose this cause directly. Native paths, visual acceptance and physical
train operation remain separate conclusions.
