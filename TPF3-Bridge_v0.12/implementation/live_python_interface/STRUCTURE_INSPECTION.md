# Native structure inspection

`client.request("inspect", {"edge_ids": [current_track_id], "structures": True})`
adds `structure` to each bounded rail record and to BaseEdges in an optional `site`
query, including roads. Omit the flag to retain the previous response shape.
The record distinguishes `NORMAL`, `BRIDGE`, `TUNNEL`, and unknown classifications,
the observed native `type_index`, the applicable resource repository/name, and a
small set of scalar resource parameters. Resolution failures remain explicit;
resource parameters are not asserted to be per-instance construction parameters.
Numeric repository handles must be reacquired in the current loaded context.

On build40408 the Complex Junction central flyover rails and road bridge resolve to
`::/infrastructure/bridge/stone.bridge`; Tunnel Example F resolves to
`::/infrastructure/tunnel/tunnel_b.tunnel`. Sloping flyover approaches are ordinary
edges. This is readback evidence, not successful bridge/tunnel construction.

## Supported next construction contract; not executed by P61

Installed declarations expose `api.engine.system.baseParallelStripSystem.getStrips`
for exact edge-to-strip identity and
`api.engine.util.proposal.createBridgeOrTunnelProposal(strip_id, new_type_index)`
for changing an existing strip's bridge/tunnel resource. Resolve the index with the
appropriate repository's `find(resource_name)` in the current context. Do not pass
an edge ID as a strip ID or reuse a handle from another load.

New segment proposals also carry `SegmentAndEntity.comp: BaseEdge` with `type` and
`typeIndex`; acceptance of structure-bearing new geometry remains to be demonstrated.
P61 does not call either proposal path or select a new railway layout. Native asset
generation and terrain treatment remain TPF3 responsibilities. Resource sentinels
(such as negative dimensions) and speed units retain their native values; no project
constraint or conversion is inferred from them.

## Verification

Check saved reference evidence without game calls:

```text
python tests/native/check_structure_readback.py .local_runs/live_python_interface/p61
python tools/quiet_checks.py --suite live_client --label pif-p61-structure-final
```

Full local evidence and exact source references are in P61's HANDOFF.md and
source_evidence.json. Native runtime reads exercise the Lua serializer; Python tests
exercise semantic evidence acceptance. No standalone Lua checker is claimed.
