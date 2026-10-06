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

## New alignment between existing free ports

P63 adds `new_alignment:true` to the same `structured_chain` prepare operation.
Supply `source` and `target` from fresh exact-port discovery, including current
`edge_snapshot`, `edge_id` and `node_id`. Supply at most four `guides`, each with
`position:[x,y,z]`, `travel_direction:[dx,dy]` and `grade`, plus one `structures`
entry per leg (guides plus final target). Reuse the same region, resource names,
session-local handle and two-step build contract above. Maximum sixteen fitted
segments. Existing replacement payloads remain supported.

`radius:0` is permitted with an explicit positive `fit_radius`: no hard engineering
minimum is imposed, while the native fitter has a finite shape parameter. `vertical`
uses existing bounded grade fitting. These are task choices, not universal UK gates.
Guides express this selected method; exact source/target native identity remains
binding. Build uses stored controls, creates internal nodes, and reacquires its
receipt by exact incidence. Native resegmentation is not required to preserve
temporary node IDs. Separate readback/route checks assess realised results.

Native proposal error messages reject a preparation/build even when `critical`
is false. The bounded evaluation includes error messages and exact collision
entities; warnings alone do not reject. A rejected native execution remains
`mutation_unverified`. `reconcile_rejected_structured_chain(client)` can establish
the requested connection is absent using fresh exact free-port incidence, leaving
other partial effects unknown. It never replays. Save the current world and reload
normally before a changed structure proposal; the native session guard is retained.

P63 build40408 demonstrated two separate D/E links, nine new edges each, seven
stone bridge edges per link and level station-side reserves. Both links and all
four trunk routes passed bidirectional native TRAIN checks. No physical vehicle
traversal, capacity/reservation or continuous clearance proof is claimed.
Evidence: `.local_runs/live_python_interface/p63/`. Offline check:
`python tests/native/check_new_structured_chain.py .local_runs/live_python_interface/p63 4`.
