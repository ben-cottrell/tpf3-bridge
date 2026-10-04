# Exact observed chain cleanup

`client.remove_exact_chain([native_edge_id, ...])` freshly inspects 1–16 distinct
TRACK identities and submits the explicit `remove_branch` / `exact_chain:true`
option. Select identities from the actual construction receipts and current world;
do not select demolition by proximity or region. Snapshot orientation/order need
not follow chain traversal, which supports reverse-built native connections.

Native checks require one connected open chain, no branch/cycle, no removed-edge
objects or construction ownership. Internal nodes must belong exclusively to the
chain; endpoints must have degree1 or2. Remove exclusive internal/free endpoint
nodes. Retain attached endpoint nodes and their exact nonremoved TRACK snapshots.
After native removal, verify the requested edges/nodes are gone and retained
attachments are unchanged with the expected incidence.

This mode cannot combine with compensation, isolated-fixture or free-ends modes.
Their defaults and behaviour remain unchanged. Existing mutation guards still
apply. Rejected/unknown removal remains unresolved for observation/reconciliation;
there is no automatic replay, rollback or host/crash recovery.

P48 exercised four connected chains attached at both ends and six multi-edge
isolated entrance chains, removing24 exact superseded edges before building the
entrance-first layout. Native readback established retained original attachments.
The bridge exposes bounded cleanup; Astra supplies the layout/removal intent.
