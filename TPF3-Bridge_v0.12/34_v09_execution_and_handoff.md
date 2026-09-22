# v0.9 execution evidence and implementation handoff

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.9.0 · **Date:** 21 September 2026  
**Executed:** 810 test methods, including 100 new corridor methods; no failures, errors or skipped tests. These verify the declared offline model and mock contract, not a real railway or a TPF3 build.

## 1. Product-level delivery

The release freezes further station-internal development and adds a coherent first corridor-design workflow. It compares reference-inspired routes across synthetic terrain, derives parallel 3D alignments, estimates structure/earthwork runs, checks full-ramp crossing cells and emits a capability-qualified mock construction plan.

A complete passenger branch junction is **not** delivered. The crossing cell has real ramp geometry but still-open connection ports. This distinction is present in JSON and the decision packet, not only in prose. The mock plan constructs only the two corridor paths and their civil reservation objects.

## 2. Reproduce the current increment

From `proof/`:

```sh
python run_tests.py
python -m railcorridor.demo --output corridor_results
```

The seven older runners and their outputs remain available as historical regression references. The v0.9 release reruns the full unit suite, including integration tests, and the new full corridor demonstration. Preserved old full-study output bytes are compared with v0.8; they are not presented as newly executed full demonstrations in this increment.

The recorded environment is Python 3.13.5 on Linux. Runtime dependencies are standard-library modules. Keep the root `evidence/` directory alongside `proof/`. Neither the tests nor the corridor runner calls a model, desktop or game API. No Windows/TPF3 compatibility, production latency or billing saving is claimed.

## 3. New verification coverage

| Test module | Methods | Principal checks |
|---|---:|---|
| `test_corridor_geometry.py` | 26 | Fixed interfaces, C2 conditions, true normal offsets, derivative/curvature/grade bounds, dense independent comparisons, integration and lowering error |
| `test_corridor_planning.py` | 38 | Retained grid failures, forbidden-land witnesses, river checks, terrain/version changes, input rejection, ramp/site/clearance limits, holding and braking |
| `test_corridor_adapter.py` | 24 | Read-back, idempotency, lost acknowledgements, partial failure, stale state, capability gates, tampering, dependency order and edit boundaries |
| `test_corridor_demo.py` | 12 | Byte-identical replay, full-study accounting, candidate binding, unprobed-game status, changed briefs and no complete-junction claim |

Independent checks include finite-difference derivatives, dense samples against analytic bounds, 3D chord sums against integrated length, direct normal-spacing identities and intermediate-point interpolation errors. The mock tests corrupt state and geometry rather than testing only successful construction.

Passing methods are not separately certified railway standards, authentic components or complete production features. The retained 75 high-level requirements and 41 broad benchmarks still cover a larger future bridge.

## 4. Executed evidence

| Artifact | What it establishes |
|---|---|
| [Test report](proof/results/test_report.json) | Actual method IDs, counts, environment and tested code/input hashes |
| [Test log](proof/results/test_log.txt) | Per-method results |
| [Historical v0.8 report](proof/results/v08_test_report.json) | Preserved prior acceptance record |
| [Fixture](proof/corridor_fixtures/release.json) | The exact authored site, terrain, profiles and budgets |
| [Corridor search](proof/corridor_results/corridor_search.json) | All twelve candidates, nine accepted screens, failures and local Pareto set |
| [Selected corridor](proof/corridor_results/selected_corridor.json) | Boundary preservation, source-qualified nominal reference and candidate identity |
| [Track polylines](proof/corridor_results/selected_track_polylines.json) | Normal offsets, 3D lowering and positional error bounds |
| [Changed-brief trials](proof/corridor_results/bounded_and_changed_brief_trials.json) | Higher speed, shorter corridor, zero budget and limited search |
| [Crossing cells](proof/corridor_results/crossing_cells.json) | Nine flat/raised/depressed parameter trials with complete ramps |
| [Corridor/cell join](proof/corridor_results/corridor_crossing_join.json) | Common datum and identities, with missing branch connections explicit |
| [Holding/braking](proof/corridor_results/holding_and_braking.json) | Train fit versus a separately declared braking screen |
| [Mock plan](proof/corridor_results/mock_construction_plan.json) | 52 ordered operations and their lowering certificates |
| [Mock cases](proof/corridor_results/mock_execution_cases.json) | Clean/repeat/lost-ack success and bounded fault handling |
| [Unprobed game manifest](proof/corridor_results/tpf3_unprobed_capabilities.json) | No fabricated tested game API |
| [Comparison](proof/corridor_results/comparison.md) | All corridor, crossing and mock-case rows |
| [Decision packet](proof/corridor_results/decision_packet.json) | Two displayed alternatives, local detail references and no construction authority |
| [Release validation](release_validation.json) | Local links/JSON, tested bytes, preceding-release comparison and manifest checks |

## 5. What changed materially

A 6 km direct route and approximately 6.061 km bypass now represent an actual geometric/civil trade-off under one brief. The longer route avoids the modelled ridge tunnel rather than merely receiving an artificially favourable operating resource template.

The crossing study rejects 600 m ramps under the selected 2% grade target despite adequate centre separation. It accepts longer ramps within the declared geometry model, retains whole-crossing checks and still records missing connections/civil evidence.

The construction controller refuses unknown capabilities and stale snapshots before writing. An acknowledgement loss is reconciled without duplicate effects; a 0.2 m geometry change stops execution after read-back. These are actual mock results, not assertions about TPF3 error behaviour.

## 6. Regression and release maintenance

All prior engineering packages and earlier test files remain unchanged. Documentation, the test runner, release verifier and current acceptance records are intentionally revised. The verifier compares previous source/test files and deterministic JSON/Markdown output files against the v0.8 ZIP; exact counts and paths are in `release_validation.json`.

Historical manifests and acceptance records are preserved without relabelling them as current. The current test runner hashes all eight implementation packages, fixtures and evidence records. A changed source value or fixture therefore invalidates its tested-byte record.

The new integration tests run the full new demonstration twice and compare every produced file byte-for-byte on this runtime. That is not a guarantee of identical floating-point bytes on every Python/platform combination.

From the package root, run `python verify_release.py`. With the prior archive available, use `python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.8.zip`. The release-maintainer `--refresh` option validates first and then refreshes the manifest; it does not run tests or fabricate results.

## 7. Research and game fit

The source register has one additional official release record and scoped rechecks of the existing signalling/modding and Infrastructure NTSN sources. No new complete turnout catalogue, dynamic gauge or current full platform standard is claimed.

The public game descriptions help specify the intended adapter probes, not an API implementation. Keep [game_capability_research.json](evidence/game_capability_research.json) separate from a future demonstrated capability manifest. The latter needs a named real game/mod build and reproducible observations.

## 8. Handoff: implemented versus next

**Implemented:** bounded x-monotone corridor generation; source-qualified nominal track spacing; zero-cant project speed/grade screens; analytic 3D normal offsets; terrain planning estimates; full-ramp crossing cells; static holding/braking screens; typed mock plans; read-back and failure recovery; compact local results.

**Next:** real terrain/adapter probes and the missing branch-connection geometry. Then add arbitrary boundary fitting, circular/clothoid/canted alignment families, actual structure-asset selection, grade-sensitive train performance and practical game-calibrated junction/signalling behaviour.

**Not a prerequisite for ordinary game-oriented design:** further station furniture/crowd simulation or full real-world certification. Those remain optional specialist modes, not the default workstream.
