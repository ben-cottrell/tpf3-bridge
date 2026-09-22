# Task L01: expose one existing corridor workflow

**State:** ready for implementation. This is a thin local wrapper, not a new railway engine. No game installation or MCP server is required. Keep the existing v0.12 package available as code/reference, not as mandatory reading.

## Deliverable
Add a root-level `bridge_cli.py` and a small test file. These commands must work from the extracted project root:

```sh
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/l01_design
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/l01_mock --mock-execute
```

Default behaviour is design-only. The flag permits an in-memory mock run, never game writes. Preserve the existing restricted corridor domain: fixed x-parallel boundary tangents, synthetic terrain and current profile inputs. Do not claim arbitrary track-stub fitting.

## Exact entry points: read only what is needed
| Existing source | Symbols / relevant baseline lines | Use |
|---|---|---|
| `proof/railcorridor/planning.py` | `parse_json` 23–33; `validate_fixture` 36–90; `search` 216–231; `objective` 210–213 | Parse, validate and search using existing behaviour |
| `proof/railcorridor/adapter.py` | `compile_plan` 46–86; `MockAdapter` 93–130; `execute` 159–192 | Lower and execute only when mock execution is requested |
| `proof/railcorridor/demo.py` | `run` 20–39 | Selection example only; do not run all its extra experiments |
| `proof/corridor_fixtures/release.json` | Whole small record | Existing input; preserve its `0.9.0` schema and fidelity |
| `proof/tests/test_corridor_adapter.py` | `AdapterTests` | Existing mock contract and failure examples |

These line numbers were checked against the supplied archive; symbols are authoritative after edits. On demand only: `proof/railcorridor/geometry.py` for geometry/hash behaviour, `proof/tests/test_corridor_planning.py` for invalid inputs/search outcomes, and `proof/railops/uk_profiles.py` with `evidence/uk_parameters.json` for reference resolution. Do not read those dependencies just to complete a checklist.

## Behaviour contract
Use the parser and validator; do not introduce another geometry or fixture schema. For a completed search with accepted candidates, preserve the demo selection policy: minimise `(objective(candidate)[2], objective(candidate)[3], candidate_hash)`. This is a declared example policy, not a global optimum.

Save the complete search and chosen candidate locally. In mock mode also save the plan and complete execution result. Use a caller-selected output directory; refuse a nonempty destination so earlier evidence is not overwritten. Retain source hashes, assumptions, failed candidates and unresolved UK/game checks in detailed records.

Print one compact JSON object, normally no more than 4,096 UTF-8 bytes, containing status, search status, evaluated/accepted counts, candidate identity where present, result paths, blockers and `game_constructed: false`. No candidate arrays, vertices, event traces or decorative output on stdout. Capture unexpected failures to a local log when possible; never claim a missing log exists.

Report invalid input, no accepted candidate, incomplete search and mock failure distinctly. Return zero only for a completed successful design or a verified requested mock run. Budget exhaustion remains incomplete even when some candidates have passed; do not silently construct one. Use a fresh mock instance per invocation and disclose that this task does not provide persistence or cross-process replay protection.

## Tests and stop condition
Before editing, run `python tools/quiet_checks.py --suite corridor --label baseline`. Read its summary, then failing evidence only if needed. Implement in the new files; leave historical proof/evidence/results unchanged. Import the existing proof modules through a path resolved from `bridge_cli.py`, not the caller's working directory; this compatibility shim is deliberate, not a packaging refactor.

Add `tests/test_cli.py` covering design success, explicit mock mode, malformed input, zero search budget, no acceptable candidate, protected output files, compact output, honest game status and unchanged legacy results. Use temporary output directories. Run the new application suite and the corridor regression once after the final edit:

```sh
python tools/quiet_checks.py --suite application --label acceptance_cli
python tools/quiet_checks.py --suite corridor --label acceptance_corridor
```

Inspect the changed diff and update `STATE.md`. Do not add persistent jobs, native probes, MCP, broader port fitting, simulation or a full package rewrite in L01. Stop with the runnable commands, checks and remaining blockers.
