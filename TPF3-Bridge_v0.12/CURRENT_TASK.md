# PIF-P37 — full-reference route-set assessment

**Complete — 4 October 2026.** Controlled22-role/56-movement coverage and all1540pairs
pass; fresh P36 read-only4-path/2-batch inspection passes.285affected tests passed.
No full-terminal construction or native56-route claim. Checkpoint/evidence:
`.local_runs/live_python_interface/p37/`. Next physical design belongs to Astra.

## Approved outcome and concrete gap
Astra accepts P36 at ccf7d19e1b7df0b590169f705e397dc30b57619b. Preserve its evidence; no additional crossing construction/angle sweep.
The approved reference has6directional approach roles and16terminal roles,56directed required movements. bridge_route_set.validate currently rejects more than16endpoints or16movements. Its exact resource comparison must work across the entire route set, not just separate16movement reports.
Extend the existing reusable read-only route-set workflow to assess the full approved contract. No new planner/subsystem or construction required.

## Astra functional contract
Read .local_runs/design/terminal_16_8_12_8/DESIGN.md and route_requirements.json.
Keep UP_A,DOWN_A,UP_B,DOWN_B,UP_C,DOWN_C and T01..T16 identities.
A servesT01..T08, B T03..T14, C T09..T16, arrival/departure each:56relationships.
Do not substitute repeated aliases of four crossing endpoints and claim the terminal exists.
The sixteen-track physical embedding remains Astra's pending design work. This task makes the bridge able to assess it, not create it.

## Implementation
Extend existing inspector/CLI with explicit finite request limits sufficient for22endpoints/56movements and the reference junction hints. Keep existing per-native-call bounds and bounded observation sizes; use deterministic batching where necessary, report budget exhaustion/incomplete honestly. Select practical finite aggregate bounds, document their rationale, no unbounded world scan or generic scheduler.
Bind each semantic endpoint/junction once per observation pass; inspect each unique physical resource once where possible. Compare ALL requested movement pairs including across any batch boundary (56choose2=1540). Preserve shared physical nodes/rails, opposite traversal, known junction vs unknown incidence, opaque transport and incomplete-path semantics.
Same world/session throughout, final binding/readback checks across the overall pass. Sequential observation is not atomic. Stale/incomplete/native errors must not become disjoint/absent claims. Preserve partial evidence and precise unknowns.
Keep compact user/model summary and complete local evidence/matrix. Add a concise summary for explicitly nominated independence witnesses from DESIGN.md if useful through existing reporting, without asserting operating capacity or creating a reservation simulator.
No hardcoded16-platform layout constructor or geometry template; maintain existing consumers and version compatibility.

## Acceptance without another construction exercise
- Deterministic tests exercise the actual public inspector path with22distinct semantic endpoints and the56named movement contract using controlled native responses;1540pair assessments including shared resource and unknown cases across batching boundaries. These are mock/reference tests, never native full-terminal proof.
- Regression of current small callers and meaningful stale/session/partial/boundary cases. Reuse unchanged geometry tests; affected quiet_checks suite once final.
- One fresh read-only native inspection of P36's existing four paths through the extended workflow. Exercise cross-batch aggregation with a smaller observation batch setting if batching exists; avoid56duplicate native queries to fake scale coverage.
- Reference56route contract validates without actual endpoint bindings; if a dry validation output is provided, label it specification validation, not56native paths.
- No game mutation/save reload needed unless read-only runtime genuinely requires ordinary authorised context refresh; do not build a new fixture to satisfy counts.
- Scoped docs/STATE, cleanup and local milestone commit, no push/PR. Local evidence/HANDOFF .local_runs/live_python_interface/p37.
- Report remaining physical-design/observation limitations accurately. Astra chooses next topology.

Permanent direct human authority allows project chat and payload handoff to coordinator01a0f987-8917-7f31-84c3-838acacc9e04. Send compact completion with evidence and final response; external review remains binding. After compaction resume unfinished active task, not an authority acknowledgement. No new services/dependencies, host recovery, stations, signals or train operations.
