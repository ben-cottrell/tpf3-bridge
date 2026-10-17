# Native TRACK observations

The native edge reader uses `BaseEdge.node0/node1` to retrieve the exact
`BaseNode` identities. Missing nodes, non-TRACK entities and nonfinite positions
still reject. Spatial closeness never establishes identity.

`p0/p1` remain the native edge's geometry endpoints. `node_positions` separately
records the native node positions. `endpoint_node_position_match` reports whether
both observations agree within .001; it is diagnostic, not a universal acceptance
gate. Their difference alone must not abort a bounded discovery of useful tracks.
No construction tolerance is enlarged. Freshness checks retain exact IDs, edge
positions/tangents/template/style and, when present in a new snapshot, node positions.
Older snapshots remain supported without inventing missing node observations.

P52/build40408 recovered both formerly blocked interior discoveries. Nearby edges
104794 and104819 differed from their exact node positions by up to .006103515625
native coordinate units. The cause is unestablished; it does not prove broken
connectivity. Selected candidates97196 and100845 had matching endpoints. Both
native discoveries and independent exact inspect reads passed. Invalid IDs still
rejected. No fitting, construction, geometry repair or train traversal was performed.
Detailed measurements and original failures remain in local P52 evidence.
