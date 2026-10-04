# Exact observed chain cleanup

`client.remove_exact_chain([native_edge_id, ...])` freshly inspects 1–16 distinct
TRACK identities and submits the explicit `remove_branch` / `exact_chain:true`
option. Select identities from the actual construction receipts and current world;
do not select demolition by proximity or region. Snapshot orientation/order need
not follow chain traversal, which supports reverse-built native connections.

Native checks require one connected open chain, no branch/cycle, no removed-edge
objects or construction ownership. Internal nodes must belong exclusively to the
chain; endpoints may have bounded incidence1–16 with exactly one selected edge.
Remove exclusive internal/free endpoint nodes. Retain attached endpoint nodes and
all exact nonremoved TRACK snapshots, including mixed junction/ordinary endpoints.
After native removal, verify the requested edges/nodes are gone, retained snapshots
are unchanged and every retained endpoint's complete incidence equals its original
unselected identity set. Shared internal nodes still reject before mutation.

This mode cannot combine with compensation, isolated-fixture or free-ends modes.
Their defaults and behaviour remain unchanged. Existing mutation guards still
apply. Rejected/unknown removal remains unresolved for observation/reconciliation;
there is no automatic replay, rollback or host/crash recovery.

P48 exercised four connected chains attached at both ends and six multi-edge
isolated entrance chains, removing24 exact superseded edges before building the
entrance-first layout. Native readback established retained original attachments.
The bridge exposes bounded cleanup; Astra supplies the layout/removal intent.

P51 exercised a five-edge branch between a degree3 through junction and degree2
station lead. Exact retained incidence became2 and1; all three retained TRACK
snapshots were unchanged and four directional native TRAIN route checks passed.
A selected chain sharing its internal junction with that branch rejected before
mutation, with the eight inspected TRACK snapshots unchanged. Build40408 only;
physical train traversal was not tested. Detailed native evidence stays local.
