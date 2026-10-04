# Observed-height compact ladder

`bridge_height_ladder` composes native graded extensions and the existing compact
ladder. Use ten named endpoint intents, explicit two-group pairing and twelve
movements. Position XYZ values are bounded discovery hints, not heights to impose
on existing track. Current exact native endpoint positions/tangents are retained.
Six destinations must form an aligned, parallel, level bank; incompatible height,
heading or bank arrangements return unsupported without flattening native track.

The selected `throat_length` is200..800 native units. Four external leads must each
span20..800 units before this throat, with parallel headings and selected grades.
Their level ends/height derive automatically from the actual destination bank.
The brief's `radius` is the hard realised minimum. `turnout_radii` select native
fitting/sizing controls; the native fit has margin and acceptance still checks the
hard project minimum. No hard constraint is lowered to accept native geometry.
Rotation/translation and compact destination spacing remain supported.

```
python bridge_live.py height-ladder --context CONTEXT.json --params BRIEF.json
python bridge_live.py height-ladder --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py height-ladder-inspect --context CONTEXT.json --params BRIEF.json --layout-record RESULT.json
python bridge_live.py height-ladder --context CONTEXT.json --params BRIEF.json --execute --layout-record RESULT.json
```

Default planning is read-only and requires native observations. Completed-record
execution performs fresh checks only. Interrupted/uncertain mutations are never
blindly replayed. Explicit partial adoption supports four freshly proven completed
leads and an independently reconciled absent first core corridor, or the existing
core prefix policy; other partial states stop for reconciliation.

Final inspection verifies12 external-to-destination native TRAIN routes, ordered
six-turnout identities, radius/grade/region and separately level native pointwork.
Full evidence stays local. Lead footprint is additional to the compact throat.
BaseEdge attachment elevation and native transport movement elevation are separate
observations. Level pointwork must match the destinations in each representation;
no assumed constant offset or relaxed tolerance is used.
Terrain samples before/after are diagnostics, not an exhaustive civil/effect proof.
Ordinary native cut/fill is allowed; no terrain optimiser, station assets, train
traversal, continuous clearance or cross-load native identity guarantee is supplied.
`height_ladder_example.json` is a concrete disposable native demo, not a height or
site default. It has no historical native IDs or intermediate elevation coordinates.

Build40408 demonstration: external attachments Z9.50, destination/core Z13.75,
observed movement Z14.28; twelve routes/six turnouts and fresh checked-existing
inspection passed. Sampled minimum radius62.6201 meets hard60; maximum grade1.8214%
meets selected4%. With stubs: graded leads370x15, core470x55, total840x55.
Eight same-XY native terrain samples show ordinary fill and cutting, including a
9.85-unit cut at a lead midpoint; these are local observations, not a full effects
inventory or proof of no structures. Native NORMAL proposals were used.
