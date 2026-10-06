# Prepared structure-bearing chain replacement

`structured_chain` prepares and builds one connected simple chain of 1–16 existing
TRACK edges. Each segment explicitly selects `NORMAL`, `BRIDGE`, or `TUNNEL`.
Bridge/tunnel resource **names** are resolved through the current native repository
at preparation and again before construction. This constructs new edges; it does
not merely swap the resource of an existing strip.

Use fresh `inspect` output with `structures:true` and `geometry:true`. Prepare:

```json
{
  "prepare": true,
  "region": {"min": [0, 0, -30], "max": [300, 300, 100]},
  "segments": [{
    "edge_snapshot": "replace this placeholder with the complete fresh edge record",
    "controls": {"p0": [0, 0, 0], "p1": [100, 0, 0], "t0": [100, 0, 0], "t1": [100, 0, 0]},
    "structure": {"classification": "BRIDGE", "resource_name": "use an inspected current resource name"}
  }]
}
```

The example is a payload outline, not a runnable railway proposal. `NORMAL` has no
resource name. Omitted controls reuse the source controls. Boundary and internal
node identities/positions remain fixed in this slice; internal nodes may not have
external attachments. Construction-owned nodes and edge objects are unsupported.
The authored region is screened at five curve samples; this is not a continuous
containment or clearance proof. Native proposal evaluation owns native validity.

An accepted preparation returns a session-local `prepared_request`. Build using
only `{"prepared_request":"<returned handle>","execute":true}`. The adapter checks
source geometry/structure freshness and reevaluates the proposal, then consumes
the handle before sending the native command. It uses stored accepted controls
without refitting. Handles do not survive an adapter session change. Failed or
unknown mutation outcomes must not be replayed; use the existing client journal
and fresh inspection to reconcile effects. No rollback is assumed.

CLI (write payloads locally first):

```text
python bridge_live.py structured_chain --context .local_runs/live_python_interface/p02/context.json --params prepare.json
python bridge_live.py structured_chain --context .local_runs/live_python_interface/p02/context.json --params execute.json
```

Build receipt/readback distinguishes native command success, new identities,
structure resource, retained node identities and realised controls. Native TRAIN
route checks are separate from receipt acceptance and physical train traversal.
Python journal mutation guards apply when `execute:true`.

P62 on build40408 reconstructed a complete ten-edge graded flyover and a complete
seven-edge tunnel span. Fresh checks verified both routes in both directions,
tunnel approach attachments, and named companion/four-trunk functions. Deck and
portal renderings were observed. This does not prove arbitrary new alignments,
new-node structure generation, capacity, reservation, vehicle traversal or universal
clearance. Exact reference geometry is a demonstration requirement, not a general
production rule for native geometry.

Local evidence: `.local_runs/live_python_interface/p62/`. Offline evidence check:
`python tests/native/check_structured_chain.py .local_runs/live_python_interface/p62`.
