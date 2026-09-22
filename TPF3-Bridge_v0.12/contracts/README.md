# Checked domain contracts — v0.12

These are proposed production message contracts, not native TPF3 APIs or a running MCP server.

[bridge.schema.json](bridge.schema.json) supplies the record and tool-input definitions. [agent_tools.json](agent_tools.json) supplies eight original tool descriptors with self-contained input/output schemas. [example_index.json](example_index.json) identifies the definition for each included authored example. [operation_capabilities.json](operation_capabilities.json) provides the minimal operation-to-capability mapping used by the selected offline checker.

[tpf3_unprobed_capabilities.json](tpf3_unprobed_capabilities.json) contains nineteen real-game capability records, all unknown. No demonstrated game build or native symbol is invented.

Examples are record-shape fixtures, not solved designs, approval credentials or game output. The two-track plan and brief share their four illustrative boundary ports, but no real snapshot, asset resolution or generated-candidate approval is implied. Asset/movement reference resolution and full candidate-to-plan equivalence must be performed by the production service.

Run from the package root:

```sh
python -m pip install -r requirements-contracts.txt
python contract_checks.py
python run_contract_tests.py
```

The installation is a development-environment action, not performed by these scripts. The contract checks use the pinned `jsonschema` development dependency. Existing `proof/` runners retain their earlier standard-library-only dependencies.

JSON Schema validates data shape. [contract_checks.py](../contract_checks.py) adds selected cross-field checks and an offline policy example. It does not implement authentication, a durable approval store, native geometry, a running job worker or live construction. An `Authority` record is an internal host contract; `rail.commit` accepts only a reference resolved by a trusted runtime.

Full contracts and interpretation are in [the current implementation specification](../IMPLEMENTATION_SPEC.md), [game adapter contract](../GAME_ADAPTER_CONTRACT.md) and [agent handoff](../AGENT_API_AND_HANDOFF.md).
