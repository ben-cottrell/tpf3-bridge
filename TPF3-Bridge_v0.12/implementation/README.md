# Implementation handoff metadata — v0.12

This directory makes the current scope and handoff machine-readable; it does not claim that the production services exist.

| Record | Purpose |
|---|---|
| [feature_matrix.json](feature_matrix.json) | Sixteen product capabilities, current evidence, core/conditional/deferred scope and next action |
| [requirement_disposition.json](requirement_disposition.json) | All 75 original IDs preserved; each receives a current scope interpretation |
| [source_inventory.json](source_inventory.json) | Actual Python source hashes, top-level symbols and absolute proof imports, extracted by AST inspection |
| [work_packages.json](work_packages.json) | Nine dependency-ordered implementation packages and explicit exit evidence |
| [acceptance_workflows.json](acceptance_workflows.json) | Five specified live-game acceptance workflows; none executed in this release |

Current product scope is in [IMPLEMENTATION_SPEC.md](../IMPLEMENTATION_SPEC.md). Use [AGENT_API_AND_HANDOFF.md](../AGENT_API_AND_HANDOFF.md) for the extraction map and [GAME_ADAPTER_CONTRACT.md](../GAME_ADAPTER_CONTRACT.md) for native probes.

The source inventory records presence, not code execution or production readiness. Historical pure components, restricted pattern families and mocks are not all mandatory stages in a construction request. Detailed train physics and further crowd/platform-internal simulation remain optional deferred features.
