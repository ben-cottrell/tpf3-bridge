# PIF-P35 — native plain rail crossing capability

**STOPPED — plain_crossing_construction_contract_unestablished, 4 October 2026.**
Relevant native bindings/resources inspected; generic node/edge proposals, slips
and road–rail crossings do not establish a plain straight-only rail diamond contract.
No native trial, implementation stub or alternative topology. Source/check evidence
in `.local_runs/live_python_interface/p35/`; concise finding in
`implementation/live_python_interface/plain_crossing_capability.md`.

P34 acceptedbf5f5b958f638aa5cd5554d55cd7521419763921. Coordinator design review for approved6approach/16destination8-12-8 reference found crossing treatment unresolved. Existing M.crossover constructs a connecting link with two turnouts; that is NOT a plain diamond crossing. Current construction paths force NORMAL and no plain crossing operation is exposed. Do not assume unsupported from this absence; first inspect relevant local native docs/examples and existing actual game mechanisms.

Astra design choice: evaluate a SIMPLE AT-GRADE PLAIN CROSSING before adding grade separation or complex slips to the reference design. This is a reusable bridge primitive capability task, not a railway design delegation. Two independent continuous tracks intersect geometrically; intended movements are west<->east and south<->north, with no intended turning connection. A crossing can impose an operational conflict despite no shared rail segment; record that distinction explicitly. No capacity/signalling inference.

Specified qualification geometry: level orthogonal tracks meeting at local(0,0), endpoint stubs at(-120,0),(120,0),(0,-120),(0,120), headings along their respective axes. Use a suitable local ground height, native track type and actual endpoints; translate/rotate the whole arrangement to clear disposable land.120unit arms are a starting work envelope, not a required game minimum; adjust only lengths needed by documented native mechanics, no unrequested topology substitution. Do not turn this into a flyover, shared collector, connecting crossover or station fan. Native legal geometry remains authority.

First resolve native construction support from available documentation/current bindings. If supported, expose reusable explicit crossing construction/inspection through existing bridge patterns, with current endpoint selection, native generated crossing identity and honest receipts. Use native mechanisms, no hand-built fake crossing/unsupported enum or replacement geometry backend. If only UI support exists, document actual available API gap; no claim that visible UI means callable API. If unsupported by accessible native API, return concise evidence and the minimal missing capability; don't spend the task inventing alternate railway designs or new dependencies.

One native crossing qualification when feasible: prove both intended straight-through native directed paths (both directions), inspect crossing/physical and transport representation, enumerate whether any unintended turn connectivity is returned, and preserve read-only evidence of existing straight routes. Expose supported crossing resource semantics to route-set inspection if evidence permits; otherwise report unresolved physical conflict, never graph-disjoint => collision-free. Do not claim signalling prevents unwanted turns. Test completed-record inspection and routine uncertain-effect reconciliation proportionately. No forced multi-angle matrix; acute geometry remains unqualified until needed by a chosen design.

Include reusable API/CLI docs, affected deterministic checks, one useful native demonstration, compact handoff, ignored raw evidence and local milestone commit if meaningful implementation completed. Reuse unaffected fitting/grade tests. Existing native road/terrain clearance authorised; no need protect old disposable fixtures, no blind replay. No station buildings/signals/train operations, host recovery/restarts, dependencies/services, new chats/agents or remote push/PR. Do not rewrite existing templates.

Sol Medium for narrow native capability integration. Astra retains all larger topology/independence/footprint decisions. Completion message to coordinator01a0f987-8917-7f31-84c3-838acacc9e04 permanently human authorised plus local/final handoff; external review binding, no bypass.40minute fallback.
