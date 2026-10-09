# Challenge 02 — six-lead oblique throat

9 October 2026. R1 selected and visually reviewed before construction. Accepted
Challenge01, its original plan and handbook remain the baseline. This broadens
the small exercise; it does not reopen the full Complex Junction.

## Fixed brief and site

Two approach tracks, 5 units apart, provide UP arrival to all six receiving leads
and departure from every lead to DOWN: twelve directed native TRAIN paths.
Retain two continuous approach corridors. No scissors, common single-track neck,
unrequested service, train-operation or capacity claim. This is design transfer.

Origin(-1200,-5300,2.6), local axes aligned with world axes. Input mouths(0,+/-2.5),
receiving centre(220,65), heading30 degrees; normal offsets -17.5,-12.5,-2.5,+2.5,
+12.5,+17.5. Receiving gaps5/10/5/10/5 represent paired leads separated by platform
allowances. Approach stubs40 and receiving stubs30 units. Boundary geometry is fixed
before fitting. These are exercise dimensions, not universal design rules.

Survey session pif_1791583177_58911467: no track/building/construction in the region;
classified entity output not truncated. Six terrain samples0.90–2.35; level rails
at2.6 provisionally allow a modest embankment. Incidental vegetation is disposable.
Bounds[-1250,-5320,0]..[-930,-5170,7]. Challenge01 and operator fixture are elsewhere.

## Whole arrangement and why

See plan-r1.json/svg/png. The same220-unit mouth-to-receiving-centre length now
handles six outlets, larger65-unit displacement(previous35),30-degree receiving
heading(previous15), and two nested three-exit fans(previous two-exit fans).
This is materially more than mirroring the first case.

UP continues towardL3 and DOWN towardL4. Sweeps start atx100. Each fan branches early
to its outer controlling leadL1/L6, then creates middleL2/L5 from that outer curve,
retaining compatible turning direction. Complete families were drawn together and
inspected; middle leads sit within reserved envelopes. Crossovers precede the fans:
UP10 toDOWN48 for arrivals; DOWN58 toUP96 described forward-x for reverse departure.
This supplies both choices while retaining through corridors.

Middle-first construction would constrain outer connections and repeat Wickham's
error. A common six-way collector would introduce an unnecessary shared neck.
The selected nested fans preserve both families. No crossing/grade separation is
needed. Radius is feedback, not a fixed gate; no loop or longitudinal reversal.

## Sequence and local freedom

Place eight boundaries; extend paired approaches and sweeps; construct two exchanges
in reserved straight regions. Build each outer boundary before its intermediate
branch. Nominal first branch parameter0.15 along actual sweep, intermediate0.22
along actual outer branch. These locate attachment regions using native curves;
they do not claim a minimum turnout spacing.

Key trial: can the second ordinary turnout fit early on each outer branch without
obstructing its neighbour? Native acceptance and required paths decide. Local
parameter/control adjustment inside the envelope is fitting; changing parent,
outlet order, footprint or adding detours requires a new spatial revision first.
The operator stops on a concrete failure.

One reusable MCP build executes the18-step data plan. Twelve paths and a native
geometry overlay follow, then save and native screenshot. Final visual approval
remains with the user.

## Outcome

Built and saved. All12 directed native TRAIN paths pass, lengths307.40–310.56
including the declared boundary stubs.26 track edges. No train operation claimed.
Designer review of native screenshot and equal-scale overlay finds coherent curves,
intact paired approach, correctly nested fans and no detour or longitudinal reversal.
User visual review pending. Vegetation obscures part of the approach in the screenshot;
the full native centreline overlay exposes both exchanges. Not a minimum-size claim.

R1 run82e9846fa3a04ba4 completed13steps then could not locate the return's x96
attachment: it was within the bridge search's unsupported final portion of the
segment endingx100. No return proposal had been built. Fit1 moved the endpoint tox90;
the native proposal rejected the resulting32-unit span as Too Much Curvature for
both offered representations. Fit2 instead shifted the original38-unit-span exchange
upstream tox54..92. It and all four fan branches were accepted. This was local
fitting inside the same reserved region; no topology revision, demolition or
human correction. All continuation plans and failures retained; no blind replay.

The unchanged R1 plan is compared with actual geometry in original-plan-overlay.svg.
Built-overlay.svg compares with the final local fitting record. The two intermediate
branches use the intended outer parents and succeeded on their first selected fit.

18 construction steps,57 native calls across three runs,28.92seconds cumulative
native-call time. This excludes design, protocol startup, review, screenshots and
documentation; it is not total completion time or a measured percentage saving.
Zero bespoke Python operator files and zero Computer Use actions for this challenge.
Data plans and existing MCP tools handled construction/review/camera/capture/save.
Actual GPT usage unavailable. The genuine costs left are design decisions, native
fit failures and their reconciliation, not repeated bridge-plumbing scripts.

Save: Design Challenge 02 - Six Lead Throat R1.sav;36,248,820bytes. Native callback
and stable file hash verified; this checkpoint was not reloaded. See result.json
for exact save/screenshot paths, hashes, route receipts and compact geometry.

## Lessons and limits

- Plan all members of a fan before fitting; build the controlling outer route and
  branch the middle route early from it. The Shefford relationship transferred to
  this oblique, displaced six-lead arrangement without an intermediate-track trap.
- Reserve both arrival and return crossovers before either fan. Keep useful length
  around attachment regions; unsupported discovery near a segment end does not
  prove the game cannot construct a turnout there.
- Compactness requires fitting both point location and connecting span. Shortening
  a rejected endpoint's link can create a new curvature problem; shifting the whole
  exchange retained its useful shape and respected the original spatial plan.
- Small, deterministic construction batches make failures cheap to inspect. Preserve
  partial progress and continue with explicit data after observing why a step stopped.
- Two related successes are encouraging, not proof of general railway-design skill.
  Grade separation, opposing receiving directions and larger multi-family layouts
  remain outside this case. Preserve accepted Challenge01 as the aesthetic baseline.
