# State: lean handoff for v0.12

## Decisions already made
GPT usage efficiency is critical. Use one small task with precise source paths; the archive is a reference library, not a compulsory reading list. Preserve correctness, hard constraints, source qualifications and failure reporting. Detailed station internals are frozen; detailed train physics and certification remain optional. Do not reopen these decisions during L01.

## Current implementation boundary
The package contains offline engineering proofs and mock adapters, not a deployed service or live TPF3 integration. L01 wraps the existing corridor search and optional mock construction. The historical `railcorridor` fixture/API still uses version `0.9.0`; the archive being version `0.12` does not change that contract.

The three startup notes are prepared; `bridge_cli.py` and its tests are NOT implemented by this handoff. Durable jobs, packaging migration, actual game probes and MCP are outside L01. Its restricted geometry must not be presented as arbitrary map construction.

## Evidence
`handoff_validation.json` records the checks actually performed while preparing this overlay, including source-path validation and a targeted corridor test run on the preparation machine. It is not evidence of success on your PC or a new full-suite run. The original v0.12 results remain historical records.

The next agent runs one local baseline using `tools/quiet_checks.py`, which stores complete logs locally and prints one small JSON record. Zero discovered tests, failures, timeouts and skipped/incomplete runs are not reported as a clean pass.

## Next action and session close
Implement only `CURRENT_TASK.md`; no project-wide audit. At task end replace this section with completion state, changed files, precise tested commands/result paths and specific blockers. Keep this file short rather than appending a transcript. Record host-reported usage when available; otherwise say unavailable. Do not infer credit savings from word counts or test duration.
