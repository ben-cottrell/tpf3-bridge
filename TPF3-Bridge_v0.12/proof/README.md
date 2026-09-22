# Offline railway engineering proofs — v0.9

From this directory:

```sh
python run_tests.py
python -m railcorridor.demo --output corridor_results
```

The full suite has **810 methods**, including 100 new corridor methods, executed with Python 3.13.5 on Linux. Runtime dependencies are from the standard library. The current demonstration searches synthetic terrain, computes 3D track pairs and crossing cells, and executes a proposed construction protocol against an in-memory mock. It does not run a model, desktop or game API.

See [the current execution report](../34_v09_execution_and_handoff.md), [specification](../32_corridors_junctions_and_game_fit.md) and [worked results](../33_worked_corridor_and_adapter_results.md). Keep the root `evidence/` directory alongside `proof/`.

## Seven retained experiments

```sh
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
python -m railclear.demo --output clearance_results
python -m railstation.demo --output station_results
python -m railcompact.demo --output compact_results
python -m railinterface.demo --output interface_results
```

| Package | Scope |
|---|---|
| `railproof` | v0.2 resource-template and complete-visit baseline |
| `railgeom` | v0.3 synthetic components, generated crossover/fan and compiled resources |
| `railops` | v0.4 directional access, stopping motion and sectional release |
| `railclear` | v0.5 reference-informed body envelopes and data-driven component admission |
| `railstation` | v0.6 integrated two-bank railway with an explicitly failed original footprint |
| `railcompact` | v0.7 compact original-plan geometry and selective recovery/diamond model |
| `railinterface` | v0.8 source-qualified platform surfaces, local facility repair and boarding-eligibility effects |

Keep the root `evidence/` directory beside this directory. The runners use local evidence interpretations and authored fixtures, not live document downloads. No remote code execution, model call, desktop control or game connection is required. Unknown current standards and missing authentic geometry remain explicit.


## Current module and evidence

`railcorridor` contains the geometry kernel, terrain/candidate search, crossing-cell checks, mock protocol and demonstration runner. Results are written to `corridor_results/`. `selected_corridor.json`, `crossing_cells.json`, `mock_execution_cases.json` and `decision_packet.json` identify their exact assumptions and limitations.

The seven historical full-study output directories remain unchanged. The v0.9 full unit/integration suite runs old tests, including their own smaller integration fixtures; it does not claim to have regenerated every old full-study output. The new full corridor demo is executed and its integration tests compare a repeated run byte-for-byte.

From the root, run `python verify_release.py`, optionally with `--baseline ../TPF3-Bridge_Passenger_Rail_v0.8.zip`. Re-running tests changes timing/report bytes, and the old manifest then correctly reports changes until a release maintainer validates and refreshes it.

The layered packages preserve regression history. They are not a proposal for eight separate permanent production geometry engines. Consolidate stable contracts when connecting the real adapter, without dropping tests or source/authority boundaries.

## Version 0.10 — connected passenger branch junction

Run from this directory:

```sh
python run_tests.py
python -m railbranch.demo --output branch_results
```

The standard-library `railbranch` package generates connected flat/flyover/diveunder variants, compiles crossing and merge resources, runs 30 whole-pass scenario comparisons and tests semantic mock construction. Inputs are in `branch_fixtures/`; component/vehicle/nominal-reference records remain in the root `evidence/` directory.

Start with [the current specification](../35_connected_passenger_branch_junctions.md), [results and mock semantics](../36_branch_junction_results_and_game_contract.md) and [execution evidence](../37_v010_execution_and_handoff.md). The new local site is not yet terrain-checked against the older corridor. Waiting is external, holding checks are static, performance ignores gradients, and no actual game adapter is connected. All previous packages and stored deterministic examples remain regression references.


## Current v0.11 terrain-bound design demonstration

Run `python -m railterrain.demo --output terrain_results` and `python run_tests.py` from this directory. The new package reads the frozen corridor/branch fixture references and `terrain_fixtures/release.json`. It requires only the standard library and the retained sibling `evidence/` directory.

This is the tenth proof package. It performs no game, desktop, internet or model call. Earlier runners remain reproducible historical models; the current release's preserved full-study outputs are not all relabelled fresh executions. See [the v0.11 report](../40_v011_execution_and_handoff.md) for exact scope and results.
