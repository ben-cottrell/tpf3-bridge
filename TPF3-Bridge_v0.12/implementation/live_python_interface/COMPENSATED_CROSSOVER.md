# Targeted correction of a constructed crossover

`client.compensate_crossover(connector_ids=[...], reason="...", authority="...",
original_client=old_client)` binds one explicit connector removal to a published
failed crossover request and its exact receipt/fit. `original_client` is optional
when the request belongs to the current client. Fresh native TRACK snapshots must
match the receipt and original connector controls. The durable intent records the
original failure hash, chosen removal and authority before the corrective mutation.

Only this exact `remove_branch` payload can cross the client's unresolved-mutation
guard. Native checks bind it to the failed receipt, splits, attachment identities
and current native guard. Through edges cannot be selected. Removal must be
observed, with both through functions verified in both directions. The original
failure then becomes **compensated**, never successful. Unknown removal retains
the corrective pending request above the original mutation and stops further
mutation. Existing evidence/intent prohibits silent repeat. This is compensation,
not rollback or automatic restoration after crashes.

`repair_crossover` fits between the existing exact attachment nodes after verified
compensation. It requires the original request/removal IDs, fresh through-edge
snapshots, original region/radius/grade/fit target and explicit execution choice.
The explicit `two_piece_level_midpoint` representation preserves native fitting:
two halves at cumulative fitted-length midpoint, fixed native endpoint/midpoint
directions, positive handles fitted by2x2 least squares against201 samples per half.
Each half receives1001 sampled checks. Original native parts/controls remain;
combined conversion error<=0.1, unchanged radius/grade/region and final native
movement checks are mandatory. Defaults and ordinary crossover representations
are unchanged. No curve search or automatic hard-constraint relaxation.

P47 replaced only95579/95585/95602 with104628/104629 at the same junctions95547/95552.
Combined conversion error0.0691432 and native route sampled radius151.56465 passed
the selected70 criterion. These results are sampled geometry/pathfinding evidence,
not physical train traversal, train-speed suitability or continuous bounds.

The first P47 fit report recorded a zero minimum because Lua expanded the returned
grade as another argument to `math.min`. The radius assertions still executed;
independent readback/routes gave151.56984/151.56465. Source now forces only the radius
return for this report. Historical prepare/execute evidence is preserved, including
the erroneous metadata field; no acceptance threshold or geometry changed.
