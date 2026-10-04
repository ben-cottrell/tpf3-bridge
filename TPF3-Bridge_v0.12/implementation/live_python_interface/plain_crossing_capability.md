# Native plain crossing — P35

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
No acute-angle, curved, graded, slip or unrestricted diamond domain is claimed.

Default command is read-only native preflight, not native preview or construction.
`--execute` submits once. Every accepted build is inspected for four exact arms and
one current centre, then all12ordered distinct-arm TRAIN queries run. Qualification
requires four complete straight paths and eight explicit no-native-path responses;
errors/truncation/missing evidence do not qualify. Returned turns are reported as a
different junction result. Native rejection/uncertain effects retain the existing
pending journal and cannot be blindly replayed. A completed current-session record
supports fresh-process read-only inspection; it is not a cross-load identity promise.
File integrity and native semantic acceptance remain separate.

Demonstration: centre(-1800,-4700,2.25), native node103501, four added TRACKs
103502/103705/103707/103708, zero removed nodes/segments. Local observed terrain
selected height; native ordinary cut/fill was allowed. Four current straight TRAIN
paths each contain four physical TRACKs and two internal transport rows on103501.
Eight turn queries returned no path, an observed result rather than global no-route
proof. BaseNodeConfig was unavailable; double-slip identity remains unknown, not false.
The generated central transport has four bidirectional TRAIN rows/five transport
node indices. No named engine subtype or internal scheduler reconstruction is claimed.

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

Raw original source qualification and empirical receipts/checks/CLI records/matrix:
`.local_runs/live_python_interface/p35/` and its `empirical/` child. Existing unrelated
engineering tests are reused; affected live-client/route-set regressions use the
quiet runner. Larger topology, footprint, bottlenecks and acute crossings remain
Astra/design decisions; this primitive chooses no replacement railway layout.
