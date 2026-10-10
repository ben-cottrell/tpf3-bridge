# Native structure inspection

`client.request("inspect", {"edge_ids": [current_track_id], "structures": True})`
adds `structure` to each bounded rail record and to BaseEdges in an optional `site`
query, including roads. Omit the flag to retain the previous response shape.
The record distinguishes `NORMAL`, `BRIDGE`, `TUNNEL`, and unknown classifications,
the observed native `type_index`, the applicable resource repository/name, and a
small set of scalar resource parameters. Resolution failures remain explicit;
resource parameters are not asserted to be per-instance construction parameters.
Numeric repository handles must be reacquired in the current loaded context.

For construction and resource selection see [STRUCTURE_CONSTRUCTION.md](STRUCTURE_CONSTRUCTION.md).
Inspect current native resources and strip identities; never reuse numeric handles
from a different load or assume a resource is supported from its name alone.
Readback, prepared construction and realised connectivity are distinct checks.

## Exact collision-entity diagnostics

Optional `entity_ids` (1–8 exact current IDs) to `inspect`. It reports
existence and applicable edge/node/construction fields without treating every
entity as TRACK. Bounded generated-strip ranges (at most 16), model references
and positions (at most 4), and native bounding boxes can identify which railway
generated a collision object. Truncation is explicit. These diagnostic bounds
are observations, not a clearance proof or authority to infer attachment.
