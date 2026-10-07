# Native signal placement

`bridge_live.place_signal(client, brief, execute=False)` reads the exact target,
discovers a functional native signal template, and prepares placement without writes.
Use `execute=True` explicitly to submit one new signal. Brief fields:

```json
{"edge_id": 67408, "parameter": 0.625, "forward": true, "one_way": true}
```

IDs are examples; reacquire them in the current loaded world. Parameter is strictly
inside the native edge (0..1). `forward` binds the native `left` control; committed
readback requires `reversed == not forward`. Do not infer permitted travel from
that label alone. In P73 on build40408, `forward: false` restored the selected
node0-to-node1 fast path where `true` blocked it. Verify the intended native path
and actual operation. One-way behaviour is explicit; proximity is not identity.
The existing low-level CLI also supports `operating_inspect` with `signal_placement`
and `operating_control` with `action: signal_place`, fresh target/seed revisions and
`execute: true`. Prefer the callable workflow to obtain these revisions.

Template discovery uses the native entity iterator, validates EDGE_OBJECT,
SIGNAL_LIST and TRACK attachment, and stops inspecting at the first usable seed
or 100000 entities. The iterator itself has no demonstrated early termination;
later callback visits perform no component reads. Missing template and exhausted
discovery bound are distinct blockers. Build40408 rejects direct enumeration of
SIGNAL_LIST and EDGE_OBJECT component types.
The actual native construction-resource value is used; no visual-model conversion,
native asset guessing, Auto Signals dependency, or mod modification is involved.

The native API binding was informed by the installed **Auto Signals (Transport
Fever 3)** `auto_signals.script.lua`, submit procedure. This bridge implementation
is independently written, with explicit intent/freshness and final-state checks.
No explicit licence was found at that installed package's usual root licence paths;
no substantial source copy is included.

Acceptance requires a new exact EDGE_OBJECT + SIGNAL_LIST, requested parameter,
resource, direction/type, unchanged attachment nodes/track geometry/resources,
retained existing objects and unchanged seed. Command acknowledgement alone is
insufficient. Unknown effects stay unreconciled and must not be replayed. Native
train occupation may reject replacement. This API does not establish depot creation,
continuous signalling correctness, traffic capacity, or arbitrary-build support.

To change an existing signal's direction/type, supply `replace_signal_id` with its
exact current ID and the same attachment parameter. The callable workflow reads
its current revision and verifies that it is on the selected edge before one native
remove/add proposal. Other edge objects and track geometry/resources remain checked.
The resulting signal and edge may have new or reused IDs; use committed readback.
This is an explicit selected-object replacement, not bulk signal removal.
