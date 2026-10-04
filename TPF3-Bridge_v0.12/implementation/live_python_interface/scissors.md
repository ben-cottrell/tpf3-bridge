# Compact scissors on existing running tracks

`bridge_scissors.scissors(client, brief, execute=False)` and `bridge_live.py scissors`
prepare four native interior-turnout fits on existing running rails. `--execute`
explicitly builds the fitted leads, reacquiring native attachment identity after each
split, then submits one caller-paired ordinary crossing. No automatic retry/resume.
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

**Native construction is unqualified:** build40408 rejected the first L0 turnout
proposal (`native_construction_rejected`). Execution stopped; no rejected proposal
was repeated and the centre/remaining turnouts were not built. Fresh readback found
all six original running-rail TRACKs and four complete through routes; different
running rails remained graph-disjoint. This does not prove all possible side effects
absent, transactionality or rollback. Full evidence is local in
`.local_runs/live_python_interface/p38/`.

Completed-state acceptance (prepared, not natively demonstrated for this scissors)
requires eight complete directed cross-end paths, four explicit same-end no-returned
path observations, exact receipt-bound turnout/crossing identities/degrees, realised
branch/arm geometry within the selected envelope and two independent straight-route
witnesses with no shared TRACK or junction node. Existing route-set inspection
records the full conflict matrix. No-path observations are bounded, geometry checks
sampled, and graph separation is not capacity, signalling, clearance or train proof.

The concrete compact-turnout rejection is an Astra design decision boundary. Do not
substitute a spread-out crossing, lower radius or silently change the selected topology.
