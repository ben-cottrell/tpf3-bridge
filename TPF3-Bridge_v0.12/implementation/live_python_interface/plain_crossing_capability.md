# Native plain crossing

## Caller-paired connection with native fitted leads

Version2 adds explicit `pairs` (two disjoint input/output role pairs), two native XY
travel `axes`, `half_arm_length`, selected minimum `radius` and `max_route_length`.
It retains `center`, authorised XYZ `region` and four bounded endpoint hints. Current
free TRACK interfaces must be level at centre height. Pair order determines arm
direction; pairing is never inferred from coordinates. Role/generated movement names
use the existing bounded semantic-name domain. Translation/rotation is supported.
Nondegenerate axes and half-arms20..300 are validated; native acceptance still governs
each layout. This is not arbitrary-angle or unrestricted routing certification.

`crossing(..., prepared_record=<path>, execute=True)` and the CLI compose four existing
native extensions and the ordinary four-arm proposal. Default preparation binds exact
ports and fits the leads read-only. Native fit handles are transient: execution uses
each extension's invocation-local fit/build/readback, reusing the engineering brief.
Durable receipts retain every stage/partial effect. Free-port rebinding prevents an
unchanged preparation replaying already-connected or partial builds. There is no
automatic partial/cross-load resume or transaction guarantee.

```powershell
python bridge_live.py plain-crossing --context <context.json> --params <version2.json>
python bridge_live.py plain-crossing --context <context.json> --params <version2.json> --layout-record <prepared.composed_crossing.json> --execute
python bridge_live.py plain-crossing-inspect --context <context.json> --params <version2.json> --layout-record <completed.composed_crossing.json>
```

Use the execution summary's `construction_record` for fresh-process inspection.
Readback checks exact attachments, lead joins/tangents/resources, actual arms, selected
sampled radius/grade and region. BaseEdge Hermite extrema determine footprint including
caller attachment stubs; native movement height is separate. All12external directed
queries must establish four complete through paths and eight explicit untruncated
no-path turn responses. Existing route-set inspection must observe the shared crossing
node and no cross-corridor shared TRACK stem. Its bounded junction search covers the
known arm envelope; exact node-position tolerance remains unchanged.

Demonstrated build40408: boundary300x30, parallel X interfaces with reversed transverse
ordering; centre(-1450,-4385,10.75), actual angle29.999345degrees,40-unit half-arms,
four fitted leads (three TRACKs each), centre node94033, arms94036/94037/94038/94039.
Including20-unit stubs:340x30, spacing30 at both boundaries. Minimum sampled realised
radius61.484422>=60, sampled grade0. Movement height11.279999733 differs from BaseEdge
height10.75. Same-XY terrain readback records native cutting/fill. No arm/longitudinal
enlargement needed. Four through routes and eight no-returned-turn queries passed;
four cross-corridor path pairs share94033 but no TRACK/transport row. This is a deliberate
physical conflict, not an independent-route witness or complete16-track embedding.
Sampling is not continuous radius/clearance proof. Train traversal, signalling,
reservations, simultaneous operation and capacity remain unprobed.

## Version1 orthogonal crossing

**Qualified observation: level orthogonal straight-only crossing on build40408.**
The native engine accepted one documented generic proposal: four ordinary NORMAL
TRACK arms incident on one new BaseNode. No CROSSING enum, prescribed transport,
slip conversion, alternative topology or Python curve fitter was supplied.

Callable interface: `bridge_crossing.crossing(client, brief, execute=False)` and
`bridge_crossing.inspect_crossing(client, completed_record_path)`. CLI:

```powershell
python bridge_live.py plain-crossing --context <context.json> --params <brief.json>
python bridge_live.py plain-crossing --context <context.json> --params <brief.json> --execute
python bridge_live.py plain-crossing-inspect --context <context.json> --params <brief.json> --layout-record <completed.plain_crossing.json>
```

A version1 brief contains `center` (native XYZ), authorised XYZ `region` and exactly
four named `endpoints`: W,E,S,N. Each endpoint uses the existing bounded native hint
fields: region,max_edges,guide_xyz,position_tolerance,travel_direction,
heading_tolerance_deg. Names specify opposed W/E and S/N tracks; the whole arrangement
may be translated/rotated. Current free TRACK endpoints, exact identities, inherited
compatible resource/style, level height and tangents toward the centre are checked.
Arms must be orthogonal and20..300native units long.120-unit arms were demonstrated;
other lengths/rotations remain subject to native legality, not blanket certification.
Version1 claims no acute-angle, curved, graded, slip or unrestricted diamond domain.

Default command is read-only native preflight, not native preview or construction.
`--execute` submits once. Every accepted build is inspected for four exact arms and
one current centre, then all12ordered distinct-arm TRAIN queries run. Qualification
requires four complete straight paths and eight explicit no-native-path responses;
errors/truncation/missing evidence do not qualify. Returned turns are reported as a
different junction result. Native rejection/uncertain effects retain the existing
pending journal and cannot be blindly replayed. A completed current-session record
supports fresh-process read-only inspection; it is not a cross-load identity promise.
File integrity and native semantic acceptance remain separate.

P34 route-set inspection reacquires a caller-named junction when a tiny spatial box
omits native movement bounds. Exact fresh node identity/incidence and current TRACK
qualification remain required; generic tolerances are unchanged. All four paths are
complete and all six pairs share physical junction103501. Perpendicular paths share
no TRACK segment or transport-row index but still have a physical crossing conflict.
Graph-disjoint does not mean collision-free. No reservation, signalling, simultaneous
operation, capacity, physical train traversal or continuous clearance proof.

The initial documentation-only finding at415f6a3 is preserved locally. It found no
dedicated plain-diamond producer; the coordinator then authorised empirical generic
formation without claiming semantics in advance. Documented slip conversion false is
single slip, not plain diamond. RailroadCrossing resources refer to road–rail crossings.
[Proposal API](https://wiki.transportfever3.com/script-doc/api/engine/util.html#UtilProposal.createDoubleSlipSwitchProposal)
and [road–rail resources](https://wiki.transportfever3.com/doku.php?id=modding:infrastructure:railroadcrossings).
