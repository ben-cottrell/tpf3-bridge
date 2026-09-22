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
| 0 | `design_ready`, `mock_verified`, `connection_ready` | Design, explicit mock or complete checked connection fit succeeded; also returned by `status` for an intact successful record. |
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
