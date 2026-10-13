# Development scope

## Current position
The offline application, native bridge and integrated operator are implemented.
Challenge04 and the Giganto1 corridor rehearsal are user-accepted; no layout repair is
requested. Giganto1's final save includes254 signals and line233671, with58 station/
junction and24 corridor/handoff directed checks passed; configuration is not traversal.
Current acceptance/limits are in STATE.md. The baseline is published. The reviewed
efficiency slices1–3 are qualified: prepared bulk signals, one-reference native
parallel families and whole-road completion. Plain curved/graded2/4-road fixtures,
20 signals in4 batches and8/8 directed/reverse-blocked checks passed. The measured
~6x improvement concerns that signal phase only. Standalone Lua fixtures and native
parallel bridge/tunnel qualification remain unclaimed.

## Reusable capabilities
Native-first connections, graded junctions and structures, basic passenger stations,
fresh interface/terminal qualification, directed routes, signals, depots and representative
services are available. The operator integrates named plans, bounded fitting, exact
replacement/removal, explicit remaining-work continuation and read-only reconciliation.
bridge_corridor.py compiles bounded authored sections over those same primitives;
sparse catalogue/point terrain queries, deterministic nearby fitting and signal-chain
placement are reusable. It does not select a new railway layout or promise exact geometry.
See [operator usage](OPERATOR_USAGE.md) and [capabilities](BRIDGE_OPERATOR.md) for
current behaviour and usage.

## Design priorities
Use the [handbook](RAILWAY_DESIGN_GUIDE.md) and
[procedure](RAILWAY_DESIGN_PROCEDURE.md) for whole-layout planning and current
lessons: reserve urban space, establish main corridors/pointwork before dependent
fixtures, keep coherent approaches, preserve explicit running direction across station
sides and treat curve/speed relationships at native scale. Lead lengths and signal
spacing are contextual guidance, not universal fixed gates. No unmeasured speed or
GPT-efficiency claim follows from a successful design. Native nearby fitting need not
reconstruct an exact sketch. Assess a flyover's whole approach/deck/exit curve and lateral
terrain clearance. Roughly80m compact crossovers and55–60mph fans are contextual user
preferences/observations, not universal limits or an inferred length-to-speed formula.

## Completed approach milestone
The approved thin approach composition layer reuses existing Operator/corridor children:
at most8 ordered families, station exits/leads before ordinary interfaces, exact receipts,
bounded local fitting and affected-only named checks. The seven-family station/fan/
crossover/flyover example passed13 native check records,12 positive platform movements
and3 wrong-way probes on build40420. No traversal or speed claim follows.

The corrected R2 flyover is user-accepted:12 positive platform movements
and3 explicit wrong-way absences passed; independent combined actual-geometry/game-
visual review passed the continuous merge/ramp/deck/exit sweep. Prebuild combined
controls and a different designer/reviewer prevented treating shallow deck acceptance
as whole-alignment approval. The offline approach renderer and exact one-track signal
removal are reusable; the latter also passed a partial-selection retained-signal case.
Native component absence uses entityExists before getComponent; recycled IDs still
require component qualification. No generic recovery system or train-traversal claim.

Current fans and the user-reported approximately80mph crossovers remain unchanged.
Fan shape alone was insufficient review: the fans are too long/fast, now recorded as
future-design feedback only. Choose a compact envelope before local fitting, retain
30m leads and compare length/native speed with the throat crossovers; roughly55mph
Challenge04/05 is a contextual reference, not a fixed numeric gate. No repair or new
workload is authorised by this guidance.

Route caches fingerprint all exported rail bindings in declared check families and actual
endpoints. Stale dependencies stop for reconciliation; unchanged review makes no route
calls. Native IDs can recycle, so chronological replacement generations and qualified
handles are required. Complete exact-node incidence may be witnessed by a sibling edge;
coordinate resemblance is not identity. Remaining dependency observation cost is measured
in STATE.md; a bounded Lua batch observation would be future work, not implemented.
No new worker task or native operation is implied by milestone completion.

## Boundaries for any future brief
Choose a concrete authorised construction/operation outcome before adding capabilities.
Reuse native mechanics and the existing interface; investigate demonstrated gaps.
Native paths, configuration, observed passage and visual quality remain separate.
Numeric terrain editing is unavailable; ordinary native track terrain treatment exists.
Detailed station internals, train physics, capacity/reservation simulation, host recovery
and unsolicited autonomous map improvement remain outside scope. No follow-on work is
implied by this document.

Maintain living guidance rather than dated milestone narratives. Remove temporary
completed diagnostics and activity histories; retain only reusable knowledge and minimal
functional context/state needed to operate or reconcile uncertain effects.
