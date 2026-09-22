# Local bridge usage

Run from the extracted project root with Python. Choose a new output directory
for each design; an existing empty directory is allowed, but a file or nonempty
directory returns `output_refused` and preserves its contents.

```powershell
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/my_design
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/my_mock --mock-execute
python bridge_cli.py status --run .local_runs/my_design
python bridge_cli.py verify --run .local_runs/my_design
python bridge_cli.py connect --input connection_example.json --output .local_runs/my_connection
python bridge_cli.py status --run .local_runs/my_connection
python bridge_cli.py verify --run .local_runs/my_connection
```

`design` validates the fixture, searches the configured grid and saves the selected
accepted candidate. Selection uses the existing objective and candidate-hash tie
break; it does not claim a global optimum. A budget-exhausted or otherwise incomplete
search never selects or executes a candidate, even if some evaluated candidates pass.
Only explicit `--mock-execute` compiles and executes a plan in a fresh in-memory mock.
Use either run directory with `status` or `verify`.

## Results and exit statuses

Normal command output is one compact JSON line (at most 4,096 bytes), with full
evidence kept locally. Inspect `status`, `blockers` and any returned evidence paths.
Long paths may be abbreviated to filenames with a `paths_relative_to` explanation.

| Exit | JSON status | Meaning |
| --- | --- | --- |
| 0 | `design_ready`, `mock_verified`, `connection_ready`, `pair_ready` | Design, explicit mock or complete checked connection fit succeeded; also returned by `status` for an intact successful record. |
| 0 | `integrity_verified` | All recorded artifact hashes match, including when the recorded design failed. |
| 1 | `invalid_input`, `output_refused` | Invalid arguments/fixture or protected output destination. |
| 1 | `unsupported_input`, `failed_checks` | Connection outside the supported domain, or failed geometric checks; inspect saved evidence. |
| 1 | `incomplete_search`, `no_accepted_candidate` | Search incomplete or completed grid has no accepted candidate. |
| 1 | `mock_failed`, `unexpected_failure` | Mock or application failed; inspect retained evidence and any error log. |
| 1 | `run_incomplete`, `status_unavailable`, `verification_unavailable`, `integrity_failed` | See record handling below. |

`--help` prints usage and exits 0. Interruptions are not normal JSON outcomes.

## Saved records and evidence

`status` reads the versioned `run.json`, validates metadata and checks saved artifact
hashes before returning the recorded outcome. `verify` reports `changed_files` and
`missing_files`; mismatches return `integrity_failed`. Neither command reruns the
engine, writes files, resumes a run or repeats an operation.

Missing, corrupt or unsupported metadata, including old folders without `run.json`,
returns `status_unavailable` or `verification_unavailable`. Nothing is repaired or
rewritten. Changed/missing artifacts make `status` unavailable; unreadable evidence
can also make verification unavailable. An unfinished manifest gives `run_incomplete`
from `status`, with current process state unknown; `verify` gives
`verification_unavailable`. This is distinct from a finalized `incomplete_search`.

Depending on how far the run reached, the output contains `fixture.json`,
`context.json` (source hashes, UK evidence provenance, assumptions and scope),
`search.json`, `candidate.json`, `summary.json`, and atomically published `run.json`.
Mock runs additionally save `plan.json` and `execution.json`; unexpected failures
may save `error.log`. The manifest records relative artifact paths and SHA-256 hashes.
Verification compares saved artifacts with that manifest; it does not authenticate
the manifest, re-evaluate geometry or compare current source files with provenance.

## Callable API

```python
from pathlib import Path
import bridge_app

result = bridge_app.design(
    Path("proof/corridor_fixtures/release.json"),
    Path(".local_runs/my_api_design"),
    mock_execute=False,  # True explicitly requests a fresh mock run.
)
saved = bridge_app.status(".local_runs/my_api_design")
integrity = bridge_app.verify(".local_runs/my_api_design")
connection = bridge_app.connect("connection_example.json", ".local_runs/my_api_connection")
```

These functions accept strings or pathlib-compatible paths and return summary
dictionaries without printing or assigning a process exit code. Check their `status`
values using the table above. Output protection and evidence rules match the CLI.

## Scope

Corridor `design` geometry is restricted to fixed x-parallel boundary tangents,
synthetic terrain and existing profile inputs. Preserve the
saved UK evidence, assumptions and hard geometry constraints when interpreting results.
Full UK assessment, station internals, detailed train physics and specialist
certification remain outside this workflow.

Every result has `game_constructed: false`. `mock_verified` describes only the mock;
native game API, geometry and topology remain unprobed. No game installations or saves
are written. Metadata persists, but the mock world does not: each invocation starts
fresh, with no cross-process replay protection.

## Offline connection fitting

`connect` consumes the strict version `0.12.0` plain-track record shown in
`connection_example.json`. It calls the existing connection validator and fitter;
it does not call corridor design/search, adapter lowering or mock execution.
The callable `bridge_app.connect(input_path, output)` returns a compact summary
dictionary without printing. API and CLI connection summaries fit within 4,096
bytes; long evidence paths become relative filenames. All connection summaries
state their offline scope and `game_constructed: false`.

The supported domain is level track with exactly equal endpoint elevations,
horizontal unit tangents, zero grade and zero cant. Coordinates use metres,
right-handed axes and z-up. The end must have positive forward span greater than
1e-7 m in the start-tangent frame, with relative heading within +/-45 degrees.
Map x/y coordinates are bounded by +/-1e7 m; arbitrary translation and rotation
within those bounds are supported. The family is one line, one quintic or two
joined quintics, with 29 deterministic candidates. Input constraints are never
relaxed or rewritten. The selected fit minimizes conservative upper length, with
grid index breaking ties; it is not a global optimum.

`connection_ready` requires a complete search and passing endpoint position,
tangent and curvature checks, G2 joins, forward derivative regularity, continuous
region containment by subdivided control hulls, curvature bounds and conservative
length bounds. These checks evaluate constructed curves separately from their
construction, using the existing floating-point geometry kernel. Tests include
independent polynomial and numerical witnesses; neither those tests nor the
runtime checks are specialist certification, interval arithmetic proof or game
evidence. Terrain, collisions, other tracks, station internals, detailed train
physics and actual native track compatibility remain outside this scope.

`search.json` retains the full fitter result, candidate geometry and checks,
including rejected candidates. `candidate.json` exists only for a complete checked
fit; `fixture.json` preserves exact input bytes, even for rejected input when
readable. `context.json` records input identity, implementation SHA-256 hashes
including loaded geometry helpers, supported domain and check limitations.
Validated input provenance keeps `source_refs`, `project_choices` and `assumptions`
separate; they are caller declarations, not independently verified UK or game
evidence. Rejected records retain their original declarations in `fixture.json`.

`unsupported_input`, `invalid_input` and `failed_checks` remain distinct.
A complete finite search without a passing candidate gives `no_accepted_candidate`;
this does not prove impossibility. Budget exhaustion gives `incomplete_search`
with `search_status: budget_exhausted`, even if some evaluated candidates pass.
No candidate is selected from an incomplete search. Interruptions leave an
unfinished record, reported as `run_incomplete` with process state unknown.
The same atomic publication, output protection and saved-artifact integrity rules
apply as for corridor records. Fresh-process `status` and `verify` load no geometry
or search modules, and never refit, execute or repair a connection.


## Pair connections

`bridge_app.connect_pair(input_path, output, mock_execute=False, snapshot_path=None)`
and `connect-pair` use the strict `0.12.0` double-track input with four ports and
explicit pairing. Default execution only fits the pair; it loads no mock adapter
or plan. Use a new or empty output directory:

```powershell
python bridge_cli.py connect-pair --input pair_example.json --output .local_runs/my_pair
python bridge_cli.py connect-pair --input pair_example.json --output .local_runs/my_pair_mock --mock-execute --snapshot pair_snapshot_example.json
python bridge_cli.py status --run .local_runs/my_pair_mock
python bridge_cli.py verify --run .local_runs/my_pair_mock
```

`--mock-execute` requires the authored mock snapshot; `--snapshot` requires that
explicit execution flag. Each invocation creates one fresh in-memory mock world.
`pair_ready` means the complete finite design search passed both tracks' geometry
checks. `mock_verified` additionally means execution checked current realised
geometry, four attachments, directions and protected neighbours in that mock.
Native game behaviour remains unprobed and `game_constructed` is always false.

Pair records reuse the existing artifacts: `search.json` keeps complete checks,
`candidate.json` keeps analytic geometry, input and provenance, and `context.json`
records source hashes and limitations. Mock runs also retain exact `snapshot.json`
bytes, the bound `plan.json`, and `execution.json` with current tracks, nodes,
revision, receipts and effects, including partial failures. No automatic resume or
rollback is claimed. Interruptions leave an unfinished run with process state
unknown. `status` and `verify` only inspect saved files; `integrity_verified`
means their hashes match, even for a failed run. It does not refit the pair,
recreate a mock world or certify current game state.

The equivalent callable workflow, from the project root, is:

```python
import bridge_app

design = bridge_app.connect_pair("pair_example.json", ".local_runs/my_api_pair")
assert design["status"] == "pair_ready"
mock = bridge_app.connect_pair(
    "pair_example.json", ".local_runs/my_api_pair_mock",
    mock_execute=True, snapshot_path="pair_snapshot_example.json",
)
assert mock["status"] == "mock_verified" and mock["game_constructed"] is False
saved = bridge_app.status(".local_runs/my_api_pair_mock")
integrity = bridge_app.verify(".local_runs/my_api_pair_mock")
```

The mock call fits and revalidates the input itself; it does not consume the
previous run directory. For the same input its candidate identity matches the
design-only run. The plan binds input, candidate, authored snapshot content and
revision, two distinct physical edges, four explicit attachments, directions and
protected neighbours. Compilation checks capabilities/freshness when supplied a
mock adapter; execution always checks them. Receipts alone cannot establish
success: current geometry, attachment nodes, directions and neighbours must agree.

For explicit same-instance retry through the lower-level API:

```python
import json
from pathlib import Path
from bridge_pair import load_pair, fit_pair
from bridge_pair_mock import PairMock, compile_pair_plan, execute_pair

record = load_pair("pair_example.json")
candidate = fit_pair(record)["candidate"]
snapshot = json.loads(Path("pair_snapshot_example.json").read_text(encoding="utf-8"))
world = PairMock(snapshot)
plan = compile_pair_plan(candidate, record, snapshot, adapter=world)
assert execute_pair(plan, world)["status"] == "mock_verified"
writes = world.writes
assert execute_pair(plan, world)["status"] == "mock_verified"
assert world.writes == writes == 2
```

Idempotency applies to this instance and its effect ledger, with current state
rechecked on retry. A new instance or process starts a fresh mock; saved receipts
provide no cross-process replay protection. Partial effects are retained without
automatic rollback. Stale state, changed neighbours or corrupted realised results
block verification, including when a historical receipt still reports success.

### Pair geometry and approximation limits

The finite family uses the connection fitter's 29 deterministic line, quintic and
joined-quintic centreline candidates. Both tracks are analytic normal offsets at
half the requested spacing, with explicit same-direction or opposing travel.
Endpoints must have compatible normal spacing, parallel tangents after accounting
for travel direction, and uncrossed pairing. The level, zero-grade, zero-cant and
local forward-span/heading limits of connection fitting still apply. Selection
minimizes the larger track's conservative upper length, then grid index. No global
optimum or impossibility claim follows from this family.

Continuous certificates cover offset regularity, ordering, radius, length,
separation, region containment and endpoint agreement, together with the underlying
centreline checks. Normal spacing at matching parameters alone does not establish
minimum separation: curved pairs also use all chord-capsule pairs. Bounds use
floating arithmetic and allowances, not formal interval arithmetic or specialist
certification. The saved numerical limits include 1e-6 m endpoint position,
1e-7 tangent and endpoint curvature allowances, 1e-8 m enclosure allowance,
2,048 offset leaves and depth 20. Unresolved subdivision or search budgets give
`incomplete_search` without a selected candidate; constraints are never relaxed.

Mock lowering approximates each analytic offset with a polyline, capped at 10,000
points per track. Saved `lowering_certificates` record chord-capsule error bounds,
parameters, point budgets and parent identity. The chosen tolerance is bounded by
the requested lowering tolerance, read-back tolerance and available separation
margin; region and separation checks reserve approximation plus read-back error.
Insufficient allowances or budgets reject compilation. Polyline certificates state
`exact_smooth_curvature: false`; endpoint tangents are semantic metadata and do not
certify smooth curvature at polyline vertices. Mock capability names describe the
offline adapter only and make no native TPF3 API or live game capability claim.
Every application/execution result retains `game_constructed: false`.

### Implementation-to-test record (L09–L14)

Case names below are unittest methods; detailed results remain in local evidence.
The host runs combined acceptance; this mapping is not a claim that pending host
checks have passed. Existing `design`, `connect`, `status` and `verify` commands
remain available with their preceding behaviour and scope.

| Task / requirement | Test file and representative cases |
| --- | --- |
| L09 strict input, explicit pairing, provenance and nonmutation | `tests/test_pair_input.py`: `test_examples_and_nonmutation`, `test_cardinality_and_explicit_unique_pairing`, `test_geometry_is_deferred_and_metadata_preserved`, `test_strict_json`, `test_unsupported_level_frame_and_cant` |
| L10 both analytic offsets, finite checks and independent witnesses | `tests/test_pair_geometry.py`: `test_curved_rotated_opposing_and_swapped`, `test_heading_boundaries`, `test_offset_capsules_enclose_independent_polynomial`, `test_radius_spacing_and_length`, `test_budgets_and_invalid_evaluation` |
| L11 bound plan, topology, capabilities and conservative approximation | `tests/test_pair_plan.py`: `test_determinism_binding_and_no_effects`, `test_explicit_pairing_capabilities_and_dependencies`, `test_forgery_and_input_mismatch`, `test_revision_and_content_staleness_binding`, `test_lowering_bound_independent_witnesses`, `test_finite_budget_and_allowance_failures` |
| L12 current read-back, same-instance retry, neighbours and stale/corrupt state | `tests/test_pair_mock.py`: `test_clean_and_same_instance_repeat`, `test_ack_lost_after_effect`, `test_partial_failure_and_explicit_retry`, `test_displaced_missing_and_malformed_geometry`, `test_bad_connection_direction_and_stable_nodes`, `test_changed_neighbour_before_and_after_execution`, `test_stale_snapshot_revision_and_unrelated_effects` |
| L13 API/CLI, explicit mock, bounded output, saved integrity and fresh inspection without construction | `tests/test_pair_app.py`: `test_design_evidence_and_cli_parity`, `test_explicit_mock_one_instance_and_readback`, `test_explicit_snapshot_requirement`, `test_fresh_design_forbids_adapter_imports`, `test_fresh_inspection_no_imports_calls_or_writes`, `test_invalid_and_failed_designs`, `test_bad_missing_and_stale_snapshot`, `test_corrupt_missing_and_wrong_mode_records`, `test_compact_dispatch` |
| L14 shipped example through checked design, bound mock plan, both connections and preserved neighbours; corrupted read-back artifact | `tests/test_pair_acceptance.py`: `test_shipped_examples_design_bound_plan_and_current_readback`; existing negative/fresh-process cases above are reused |

Focused runnable test command: `python -B -m unittest discover -s tests -p test_pair_acceptance.py -q`.
The host's combined entry points are `python tools/quiet_checks.py --suite pair_combined --label batch_l14_pair`
and `python tools/pair_acceptance.py --task L14`, followed by the queued legacy
regression suites. Saved-file integrity is distinct from geometry acceptance,
current in-memory mock verification and unprobed game state.
