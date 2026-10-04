# Current directed movement-set inspection

```
python bridge_live.py route-set-inspect --context CONTEXT.json --params MOVEMENTS.json
```

Callable: `bridge_route_set.inspect_route_set(client, brief)`. This is read-only:
current discovery, native pathfinding and exact TRACK/incidence observation only.
No layout template, historical receipt or fixed railway track count is required.
See `route_set_example.json` for a diagnostic on the existing P33 world; positions
are that example's observation hints, not a proposed design or historical handles.

Version1 brief names2..16 endpoints and1..16 explicit directed movements. Each
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

Optional `junctions` names bounded XYZ observation hints with region/max_edges/
guide_xyz/position_tolerance. Movement `via` lists these names in required order;
it checks the returned native path, and does not force/reimplement native routing.
The operation reports one returned path per movement, not all alternative paths
or a globally impossible route when no path is returned. TRAIN/ELECTRIC_TRAIN and
max_length(0,8000] reuse native routing; length is an acceptance bound, not an
engine search-budget guarantee. Existing native path observation bound is64 entries.
Aggregate observation is bounded to256 physical TRACK edges and256 physical nodes.

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
geometry is reacquired at the end; observation is bounded sequential readback,
not an atomic world snapshot or cross-save identity guarantee.

Graph separation is **not** simultaneous operational capacity. Crossing/interlocking,
clearance, signalling, reservations and train traversal outside shared graph
resources remain unknown/unprobed. The inspector does not choose topology, rank
designs or remove bottlenecks. Astra/design orchestration owns those decisions.
