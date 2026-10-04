# Current directed movement-set inspection

```
python bridge_live.py route-set-inspect --context CONTEXT.json --params MOVEMENTS.json
```

Callable: `bridge_route_set.inspect_route_set(client, brief)`. This is read-only:
current discovery, native pathfinding and exact TRACK/incidence observation only.
No layout template, historical receipt or fixed railway track count is required.
See `route_set_example.json` for a diagnostic on the existing P33 world; positions
are that example's observation hints, not a proposed design or historical handles.

Version1 brief names2..32 endpoints and1..64 explicit directed movements. Each
endpoint has a bounded region (at most400 units per axis), max_edges1..16, native
XYZ guide, XY travel_direction, heading_tolerance_deg and position_tolerance(0,10].
The heading is the reference track's **outward direction toward the network**;
it stays the same when a movement is reversed. Hints disambiguate exact current
node/edge identities; proximity never establishes attachment. Supported endpoints
are free or unowned two-edge TRACK attachments under the existing discovery
contract. Construction-owned/ambiguous/truncated observations stay unavailable.

The native route query includes each endpoint's selected reference track segment:
it runs from the outer end of the source reference to the outer end of the target
reference, passing through the named attachment nodes. These reference rails are
explicitly part of the reported resource footprint. Reverse movements swap the
query bindings; they do not manufacture a new rail identity.

Optional `junctions` names up to32 bounded XYZ observation hints with region/max_edges/
guide_xyz/position_tolerance. Movement `via` lists these names in required order;
it checks the returned native path, and does not force/reimplement native routing.
The operation reports one returned path per movement, not all alternative paths
or a globally impossible route when no path is returned. TRAIN/ELECTRIC_TRAIN and
max_length(0,8000] reuse native routing; length is an acceptance bound, not an
engine search-budget guarantee. Existing native path observation bound is64 entries.
Aggregate observation is bounded to512 physical TRACK edges and1024 physical nodes.
These allow the approved22-role/56-movement contract with room for ordinary pointwork;
they do not guarantee every physical embedding fits. Overflow remains unavailable.
Optional `batch_size`1..16 defaults16. Routes are grouped deterministically; unique
resource reads use batches of at most that size, never exceeding native16-edge calls.
Bindings are acquired once per initial/final pass, not once per route batch. All
requested pairs are compared together, including across batch boundaries:56movements
produce1540pairs. Native query observation remains64rows and discovery16edges.

A pass permits2304native reads with a600second deadline checked between calls;
the existing individual request timeout remains unchanged. One already-started call
may finish after the deadline; this is not a hard realtime guarantee. No concurrency,
retry, new scheduler or game mutation. Exhaustion/error preserves observed partial
records and all requested pair slots as unknown rather than claiming separation.

JSON preserves current bindings, raw native route outcomes, ordered physical rails,
transport internals, exact incidence and junction transitions, pairwise resources
and explicit unknowns. A companion Markdown matrix contains O(overlap), D(complete
topology-disjoint), ?(unknown), with exact supporting current resource IDs below.
Normal stdout is a compact summary plus JSON/matrix paths; detailed evidence is local.

Pair comparisons distinguish shared physical TRACK segments, reverse traversal,
shared junctions, shared endpoint nodes and other physical nodes. Non-TRACK native
transport connectors remain explicit; exact observed junction-owned connectors
can be classified, while opaque internals prevent a disjoint conclusion. Known
overlap can remain visible in an incomplete path; stale bindings yield unknown.
Only complete, qualified paths can establish graph separation. Binding identity/
geometry is reacquired at the end. Each unique TRACK snapshot and relevant incidence
is also checked in a final readback pass; changed/missing resources invalidate affected
paths. Response/client session changes stop the whole pass. Observation is bounded sequential readback,
not an atomic world snapshot or cross-save identity guarantee.

Graph separation is **not** simultaneous operational capacity. Crossing/interlocking,
clearance, signalling, reservations and train traversal outside shared graph
resources remain unknown/unprobed. The inspector does not choose topology, rank
designs or remove bottlenecks. Astra/design orchestration owns those decisions.

`tests/fixtures/route_set_reference.json` preserves the approved six approach roles,
sixteen terminal roles and56directed allocations: A→T01..T08, B→T03..T14,
C→T09..T16 and their departures. Controlled native-shaped tests run the actual public
inspector on22distinct endpoint bindings and all1540pairs, including cross-batch overlap,
errors/opaque resources, stale/session/resource changes and budget stops. This is mock
contract coverage, not a native terminal or physical design. P37's native regression
reads only the existing P36 four-path crossing with batch_size2. The full terminal
embedding and nominated independence witnesses remain Astra's pending design work.
