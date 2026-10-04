# Explicit read publication recovery

With a healthy current adapter, `client.reconcile_read_publications([request_id])`
may restore the exact saved unpublished read, including one wrapping an unresolved
construction. Supply the exact oldest-first read IDs (at most two). The terminal
mutation must have the same saved envelope/session, earlier sequence and exact
published slot. It is never replayed, modified or cleared by read recovery.

Read envelope/hash, sequence frontier, current session, slot/temporary bytes and
log baseline must match. A missing slot with prior matching response/ACK or uncertain
publication cannot be republished. An already published matching read consumes its
existing response, without another publication. Timeout or denied writes retain
the pending history. Successful read recovery restores the underlying mutation as
pending, preserving its payload/outcome; only separate verified construction
reconciliation can accept that mutation. No filler requests or host/permission repair.

P46 recovered the exact P45 unpublished route, while the second crossover stayed
unaccepted at radius70. Native fitting/full BaseEdge geometry and realised movement
geometry remain separate evidence: the 187.22 full curve became a roughly0.253-unit
trimmed native movement segment whose first sampled radius is37.434. A failed
first sample is not the minimum over the entire curve. Do not replace realised
movement checks with the prefit radius or loosen the threshold to accept it.
