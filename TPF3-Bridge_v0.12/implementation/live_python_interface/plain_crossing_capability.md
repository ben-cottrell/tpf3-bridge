# Plain rail crossing — P35 qualification boundary

**Status: plain_crossing_construction_contract_unestablished.** No reusable plain
diamond operation or native demonstration is claimed. Existing `M.crossover`
constructs a connecting link with two turnouts; it is not a plain crossing.

Relevant installed build40408 bindings expose:

- `BaseEdgeType`: NORMAL, BRIDGE, TUNNEL. A plain crossing is not a documented
  additional edge-type enum; absence of an enum does not prove impossibility.
- `SimpleProposal`/`SimpleStreetProposal`: adding/removing native TRACK edges and
  nodes, node configurations and generic world-build command. The inspected contract
  does not specify a straight-only four-arm rail diamond or its automatic formation.
- `LaneConnection`: road/tram connection flags, not a demonstrated rail movement
  selector. No fabricated rail flag or hand-written fake crossing is supplied.
- `createDoubleSlipSwitchProposal`: converts an existing node to double or single
  slip; false selects single slip, not a documented plain/no-turn diamond.
- `RailroadCrossingType`, `node2rcType` and crossing-system records: road–rail level
  crossing types/animations. Their names do not establish rail–rail diamond support.

Official references: [proposal API](https://wiki.transportfever3.com/script-doc/api/engine/util.html#UtilProposal.createDoubleSlipSwitchProposal)
and [road–rail crossing resources](https://wiki.transportfever3.com/doku.php?id=modding:infrastructure:railroadcrossings).
Bundled track menu/metadata provide descriptive resource registration, not a rail
crossing proposal producer. The inspected street helpers are explicitly obsolete;
they are not adopted as a new construction API.

Minimal missing fact: a supported native proposal-generation/formation contract
for two independent level intersecting TRACKs, with exact native crossing identity
and straight-through movement representation. Generic node/edge insertion is real;
its plain-diamond semantics remain unestablished here. This is a bounded accessible
API qualification result, not a claim that the game/UI cannot build crossings.

The specified level orthogonal four-endpoint experiment remains unperformed.
No endpoints/site/height were chosen, no track/terrain/mod/save was changed, and no
flyover/slip/collector or other topology was substituted. No API/CLI stub claims
unsupported native behaviour. Acute crossings and unwanted-turn connectivity remain
unqualified. Preserve existing P34 route-set interpretation: graph-disjoint paths
can still have unresolved physical crossing/interlocking/clearance conflict; no
collision-free, signalling, capacity or concurrent-operation guarantee follows.

Exact installed source ranges/hashes, bounded archive resource observations and
checks are retained locally in `.local_runs/live_python_interface/p35/`. Existing
261-test evidence is reused for unchanged implementation; no broad regression rerun.
Design/orchestration owns the next decision; this finding chooses no alternative.
