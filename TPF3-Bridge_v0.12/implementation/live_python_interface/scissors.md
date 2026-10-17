# Compact scissors on existing running tracks

`bridge_scissors.scissors(client, brief, execute=False)` and `bridge_live.py scissors`
prepare four native interior-turnout fits on existing running rails. `--execute`
submits one complete connected native proposal: both through-rail subdivisions,
four fitted branches and one caller-paired ordinary crossing. No automatic retry/resume.
`inspect_scissors(client, record)` / `scissors-inspect --layout-record RECORD` inspect
completed current-session receipts without construction. Partial records require
focused reconciliation; neither command invents success or guarantees rollback.

```text
python bridge_live.py scissors --context CONTEXT.json --params BRIEF.json
python bridge_live.py scissors --context CONTEXT.json --params BRIEF.json --execute
python bridge_live.py scissors-inspect --context CONTEXT.json --params BRIEF.json --layout-record RECORD.json
```

The explicit version1 brief names W0/W1/E0/E1 and L0/L1/R0/R1 using current native
observation hints. The selected domain is level300x5 native units, four distinct
degree3 turnouts and one degree4 plain crossing, with15-degree diagonal axes.
Translation/rotation are supported by the brief; no coordinate matching replaces
native identities. Radius60 is a hard sampled minimum, native fit radius70 a guide.
Finite positive crossing arms up to300 are accepted for explicit caller pairing;
the older unpaired orthogonal20-unit minimum remains unchanged.

`scissors_example.json` contains the original radius70 circular geometric guide.
That guide is not native construction proof. P38's native preflight initially failed
the existing conversion tolerance. A symmetric0.1-unit reduction in half-arm length
and0.2-unit outward shift of each turnout passed all four native fits and the
300x5 branch-envelope check, without lowering constraints.

The connected path also performs bounded branch repartitioning: exact native-fit
endpoints/headings form one native cubic per branch, compared at33 samples per
original fit part. The sum of sampled conversion errors must remain within the
existing0.1 tolerance; selected radius/grade/region checks remain binding. Original
controls and comparison results remain in evidence. This is sampled approximation,
not exact continuous equality or a claim about the engine's minimum segment size.

**Native construction is unqualified:** build40408 rejected the original isolated
L0 proposal, a complete22-segment/17-node connected proposal, and a repartitioned
14-segment/9-node connected proposal. All returned `Construction Not Possible`;
the native response provided no more specific validation reason. Repartitioning
passed four native preflights (sampled radius>=69.942, combined sampled error<0.005)
without relaxing radius60, grade0, spacing5 or15-degree crossing.
No unchanged proposal was replayed. Explicit read-only rejection reconciliation
confirmed original rail snapshots and through routes before clearing pending state.
Final fresh readback found six original TRACKs and four complete through routes;
different running rails remained graph-disjoint. Other effects remain unknown.
This establishes a persistent rejection of these tested proposals, not global
topology impossibility or an engine minimum. Evidence remains local in
`.local_runs/live_python_interface/p38/repair1/` and `repair2/`; earlier evidence
is preserved. The separate running-rail save retains the test fixture.

Completed-state acceptance (prepared, not natively demonstrated for this scissors)
requires eight complete directed cross-end paths, four explicit same-end no-returned
path observations, exact receipt-bound turnout/crossing identities/degrees, realised
branch/arm geometry within the selected envelope and two independent straight-route
witnesses with no shared TRACK or junction node. Existing route-set inspection
records the full conflict matrix. No-path observations are bounded, geometry checks
sampled, and graph separation is not capacity, signalling, clearance or train proof.

The unresolved native validation rejection is an Astra decision boundary. Do not
substitute a spread-out crossing, lower radius or silently change the selected topology.
