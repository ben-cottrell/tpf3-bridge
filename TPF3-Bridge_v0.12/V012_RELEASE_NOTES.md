# v0.12 — scope consolidation and production handoff

**Version 0.12.0 · 21 September 2026**  
**Release type:** documentation/contracts consolidation, not a new railway simulation or game integration.

## 1. What this release changes

The previous next-step recommendation was detailed grade-sensitive performance and internal holding/restart. Following the user's scope correction, that work is deferred. The next objective is a small, verifiable native railway build using the existing engineering material.

A current [implementation specification](IMPLEMENTATION_SPEC.md) now governs product scope. The [adapter contract](GAME_ADAPTER_CONTRACT.md) and [agent handoff](AGENT_API_AND_HANDOFF.md) turn that scope into exact responsibilities, message definitions, native capability probes, source extraction targets and acceptance workflows. Earlier next-step recommendations are marked historical; their experimental findings are not rewritten.

The practical profile retains British geometry and evidence origins, terrain/site/connection constraints and train-length checks. It no longer demands detailed crowd simulation, certified dynamic gauging or a separate traction model before an ordinary create-only track task can be attempted.

## 2. Deliverables

| Deliverable | Actual state |
|---|---|
| Current product specification | Authored and linked to historical evidence |
| Game-adapter boundary | Nineteen capability records, all unprobed for the real game; fifteen specified native probes |
| Agent API | Eight proposed tool descriptors; no running server |
| Domain records | 38 JSON Schema definitions and selected semantic checks |
| Examples | Seventeen indexed authored examples/records; not runtime construction output |
| Requirement disposition | All 75 original IDs classified by current scope |
| Feature support | Sixteen current feature records with limitations and next action |
| Source handoff | AST inventory of 63 Python module files, with actual hashes and public symbols |
| Implementation sequence | Nine dependency-ordered work packages and five specified live workflows |
| Runtime implementation | No new simulation core, native adapter, server or job service |

The schema intentionally describes a minimal operation set. It is not a full production intermediate representation or a claim that TPF3 accepts those payloads. Asset/reference resolution, genuine native lowering, full validation, durable authority and current native observations remain implementation work.

## 3. What was executed

`python contract_checks.py` validated all seventeen indexed examples/records. `python run_contract_tests.py` ran **34 methods**, with zero failures, errors and skips in the completed acceptance run. The exact environment, elapsed time, test identities and checked input hashes are in [contract_test_report.json](validation/contract_test_report.json).

Tests cover closed schemas, duplicate/nonfinite JSON, size/depth limits, physical units, port vectors/grades, preservation conflicts, incomplete snapshots, capability provenance, payload/plan hashes, dependencies, shared-node identity, stale/expired/wrong-principal authority and false game-verification claims. Metadata tests check the original requirement set, work-package dependency graph, actual source hashes and explicit physics deferral.

The local policy checker performs **no native writes** and grants **no live execution authority**, even when its assumed trusted inputs satisfy the selected checks. Its test context is authored, not an authenticated host or real game session.

One development test initially matched the substring “traction” in “extraction”; its guard was corrected to match whole words and the complete contract suite rerun. The final report records the completed passing run, not a claim that every development invocation succeeded.

## 4. Preserved engineering evidence

The existing ten proof packages, their tests, fixtures, historical outputs and original evidence records remain byte-preserved against v0.11. The exact counts, paths and comparison result are in [release_validation.json](release_validation.json).

The **985-method engineering report under `proof/results/` is the preserved v0.11 execution**, not a fresh v0.12 run. The old full engineering suite and full-study demonstrations were not rerun. A new contract-check count must not be added to 985 and advertised as one combined completed execution.

Historical documents receive only a scope/precedence banner where needed; their source bodies and results remain reference material. The preceding full ZIP remains unchanged outside this release. The production code extraction/refactor is specified but not performed.

## 5. Research and compatibility

Eight primary protocol/schema references were reviewed, bringing the source register to 78 entries. The reviewed MCP revision is 2026-07-28. The schema dialect is JSON Schema Draft 2020-12. Host/version/transport compatibility must be tested in the deployment; none is implied by these source checks. See [the protocol source section](10_source_register.md#v012-protocol-research).

The official TPF3 feature description was rechecked for context. No exact native construction symbols, game callback/thread guarantees, filesystem/network permissions, new UK engineering clauses or authentic turnout drawings were acquired. The native manifest remains unknown rather than “unsupported”. No authentication barrier was bypassed.

The new contract tests use the `jsonschema` version pinned in [requirements-contracts.txt](requirements-contracts.txt), also recorded in their report. This is a development dependency; existing engineering runners retain their prior dependencies. No third-party source PDF, image or font is packaged.

## 6. Validation and reproducibility

From the root:

```sh
python contract_checks.py
python run_contract_tests.py
python verify_release.py
python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.11.zip
```

The verifier checks local Markdown targets/fragments, strict finite JSON, current contract input/source hashes, preserved engineering report hashes, handoff references, manifest membership and, when supplied, the preceding archive. A manifest checks bytes; it does not execute a simulator or validate a railway source interpretation.

The release verifier's `--refresh` is a maintainer operation which validates first and then records the manifest. Rerunning tests legitimately changes timing/report bytes; rerun validation with refresh before treating those new files as a sealed release. ZIP integrity is recorded separately during packaging.

## 7. Handoff decision

The next concrete development target is **WP-02 / WP-04: read-only identity/topology/terrain/asset inspection followed by create-only native track construction and read-back**, supported by WP-01 contracts/store and WP-03 kernel extraction. Work packages are not time estimates.

The first acceptance workflow uses a disposable save and a small double-track connection. It tests fixed external ports, actual assets, protected neighbours, snapping, stale state and ambiguous receipts. Actual traversal is a separate observed level, not inferred from a successful native call.

Detailed train physics and further station-internal simulation are no longer the default next workstream. They return only when a specific measured game problem justifies them.
