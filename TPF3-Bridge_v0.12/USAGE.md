# Local bridge usage

Run from the extracted project root with Python. Choose a new output directory
for each design; an existing empty directory is allowed, but a file or nonempty
directory returns `output_refused` and preserves its contents.

```powershell
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/my_design
python bridge_cli.py design --fixture proof/corridor_fixtures/release.json --output .local_runs/my_mock --mock-execute
python bridge_cli.py status --run .local_runs/my_design
python bridge_cli.py verify --run .local_runs/my_design
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
| 0 | `design_ready`, `mock_verified` | Design or explicit mock succeeded; also returned by `status` for an intact successful record. |
| 0 | `integrity_verified` | All recorded artifact hashes match, including when the recorded design failed. |
| 1 | `invalid_input`, `output_refused` | Invalid arguments/fixture or protected output destination. |
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
```

These functions accept strings or pathlib-compatible paths and return summary
dictionaries without printing or assigning a process exit code. Check their `status`
values using the table above. Output protection and evidence rules match the CLI.

## Scope

Geometry is restricted to fixed x-parallel boundary tangents, synthetic terrain and
existing profile inputs; arbitrary track-stub fitting is unsupported. Preserve the
saved UK evidence, assumptions and hard geometry constraints when interpreting results.
Full UK assessment, station internals, detailed train physics and specialist
certification remain outside this workflow.

Every result has `game_constructed: false`. `mock_verified` describes only the mock;
native game API, geometry and topology remain unprobed. No game installations or saves
are written. Metadata persists, but the mock world does not: each invocation starts
fresh, with no cross-process replay protection.
