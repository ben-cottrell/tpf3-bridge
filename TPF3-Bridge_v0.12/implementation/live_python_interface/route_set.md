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
The heading selects the native reference track's **outward direction at the named node**;
it stays the same when a movement is reversed. Hints disambiguate exact current
node/edge identities; proximity never establishes attachment. Supported endpoints
are free or unowned two-edge TRACK attachments under the existing discovery
contract. Construction-owned/ambiguous/truncated observations stay unavailable.

The native route query includes each endpoint's selected reference TRACK segment.
Exact complete incidence determines its boundary semantics: a free endpoint (one
incident TRACK) uses the selected node directly. A connected boundary (two incident
TRACKs) retains the existing opposite-end query on the selected reference edge,
passing through the named boundary. Optional endpoint `boundary_kind` is
`free_endpoint` or `connected_boundary`; a mismatch with current incidence fails
without routing. Omitted kind is resolved from exact current incidence, never
coordinates. The binding records both `boundary_kind` and `query_node`. Reverse
movements swap bindings; the selected native outward heading remains the same.
Every named freshly bound junction ID is forwarded for native turnout orientation.
Unavailable named junctions prevent the query; any changed forwarded junction
invalidates affected paths, including when not listed as a movement's `via`.
Required endpoint-edge traversal, named-node completeness and final freshness
remain acceptance gates; no global node reversal or tolerance weakening.

P41 build40408 verified the same live staggered two-crossover assembly with all eight
external directed movements complete. Twenty-eight pairs:24overlap,4graph-disjoint,
0unknown. W0_E0 / E1_W1 share no TRACK, junction, endpoint or internal transport
resources. Other overlaps remain explicit in the local physical resource matrix.
Evidence `.local_runs/live_python_interface/p41/native/`; 311affected tests pass.
No construction, world reload or native code change was needed. This is current
topology/readback evidence, not train traversal, reservations or capacity proof.

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
