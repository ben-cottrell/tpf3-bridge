# Native near-straight lowering

P43 fixes a demonstrated rotated continuation failure on build 40408. Native
Dubins fitting returned a 29.99371-unit straight between two 0.003154-unit arcs
of radius 157.5. At the observed map coordinates, native float endpoints lost
the arcs' transverse displacement. Converting each fragment separately produced
an invalid cubic radius of 0.004629; rejecting that cubic was correct.

The adapter retains the native parts and original converted controls. A path
with more than one retained piece, exactly one STRAIGHT and cumulative ARC sweep
at most 0.1 degrees is lowered as one cubic with the native overall endpoints,
directions and total length. Every original part is compared at 17 samples.
The existing 0.1 XY conversion bound, endpoint/heading checks, vertical profile,
hard radius, grade and region checks still apply. The existing collectively
0.001 tiny-part filter is unchanged. Single-piece straights and materially
curved paths retain their existing handling. No design constraint is relaxed.

Native failure diagnostics stay in local response evidence; normal CLI output
remains compact. The regression fixture records the actual failed fragments and
accepted controls. Independent Python Bezier checks sample those controls more
finely; they do not execute Lua. The staged Lua was exercised in the real game.
All geometry comparisons remain sampled evidence, not continuous proofs.

Acceptance: `python tools/quiet_checks.py --suite live_client --label pif-p43-pre-native`
passed 323 tests. Native acceptance built only the specified Wickham leads
8, 9, 12, 13 (30-unit grade transitions, level extensions to 150) and crossovers
8@50 to 9@120 and 13@50 to 12@120. Fresh readback verified 12 directional TRAIN
routes, all 16 original user leads and station-owned snapshots unchanged.

Full local evidence: `.local_runs/live_python_interface/p43/native/`;
`final_result_verified.json` contains exact current attachments, connector and
junction IDs, sampled geometry and ground-relative observations. BaseEdge datum
and native movement geometry heights are recorded separately; their observed
difference is not a universal asset conversion. Platform associations, physical
train traversal and native save GUID remain unknown/unprobed.

P44 fixes the filtering/lowering interaction exposed by an actual 130-unit
continuation: two individually tiny arcs totalled 0.00165224, exceeding the
collective discard budget before near-straight lowering could run. Such paths
now retain ALL native parts, discard nothing and undergo the same lowering and
hard checks. The discard budget is still 0.001. The recorded case passes native
read-only fitting and independent finer-sampled regression checks.

P44's fixed 100-unit/10-unit native-parts crossover passed preflight but was
constructed with an unacceptable realised movement radius (74.2073 < 150).
Fresh native re-verification retained that failure. Its partial effects and
unfinished-mutation guard remain visible; a second crossover was not attempted.
This result does not invalidate the repaired continuation, and does not establish
general native-parts crossover acceptance. See P44's local handoff for exact IDs
and the coordinator decision required before further mutation.
