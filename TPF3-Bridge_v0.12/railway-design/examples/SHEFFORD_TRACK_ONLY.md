# Shefford track-only fans and comparison

Read-only capture, 9 October 2026; build40420/sessionpif_1791572697_48431435.
The user supplied two additional mirrored 5/10-unit fans near the original 10/15
station-spacing pair. The new examples are C/D in the comparison below; A/B retain
the original reference labels. All four are user-built reference designs.

![Four fans at equal scale](shefford-fans-comparison.png)

| Reference | Middle / outer offsets, magnitudes | Junction-node distance |
| --- | --- | --- |
| A, station spacing | 10.00 / 15.00 | 27.88 |
| B, mirrored station spacing | 10.00 / 15.00 | 26.88 |
| C, track-only | 5.00 / 10.00 | 27.47 |
| D, mirrored track-only | 5.00 / 10.00 | 27.44 |

Distances are native game units. The original first gap allows a 5-unit-wide
platform; the new first gap contains no platform allowance. Both cross-sections
retain the same directed arrangement: through straight, outer sweep from J1,
middle route branching early from that sweep at J2.

The narrower examples settle into their parallel leads earlier in the scaled view,
while J1-J2 spacing remains similar. This supports transferring the branching
relationship while refitting the downstream curves. It does not prove a fixed
turnout spacing, engine minimum, universal radius or ideal span for other sites.

Native capture includes four complete components,56TRACK controls,8degree-three
junction nodes and4one-way signals. Some older track handles changed; they were
rediscovered rather than treated as constraints. All12 current approach-to-exit
TRAIN paths pass, including all6 in the new pair. No train movement, capacity or
smooth-running proof is claimed. No game mutation was performed by this inspection.

[Self-contained geometry and route summary](shefford-fans-comparison.json),
[vector comparison](shefford-fans-comparison.svg). Raw receipts and analysis are in
`.local_runs/design/shefford_track_only/`; the earlier reference is retained separately.
The plot is a BaseEdge control reconstruction, omitting internal turnout geometry.

These examples expand the pattern library but do not count as a blind or prospective
test of the agent's design process: the solutions were supplied by the user. The next
test should combine functional and spatial constraints, as specified in
[the oblique four-lead throat challenge](../CHALLENGE_01.md).
