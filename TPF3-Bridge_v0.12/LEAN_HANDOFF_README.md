# Lean Codex handoff overlay

This small overlay is used **with the full v0.12 package**. It is not another engineering release and contains no copied research archive. Earlier files need not be read merely because they are present.

## Setup
Extract the complete v0.12 archive once. Extract this overlay into the same folder that contains `IMPLEMENTATION_SPEC.md` and `proof/`. The overlay adds files; it does not replace that specification, the root README or any proof code. Review/merge an existing `AGENTS.md` or same-named helper rather than overwriting your own instructions. Create a Git baseline before implementation and keep the original ZIP outside the working tree.

Open that project folder in your chosen Codex environment. Send this message:

> Implement CURRENT_TASK.md only. GPT usage efficiency is critical: follow AGENTS.md, keep detailed outputs local, update STATE.md, and stop when this task passes its acceptance checks.

Do not attach the full historical conversation or ask for a repository-wide audit. The initial task reads the three startup notes and targeted code; references remain available for unresolved questions. Access to files is not an instruction to load every file into model context.

## Files
`AGENTS.md` contains durable scope and efficiency rules. `CURRENT_TASK.md` specifies one wrapper task and exact entry points. `STATE.md` preserves short cross-session state. `tools/quiet_checks.py` executes selected tests with local full diagnostics and compact stdout. `tools/test_quiet_checks.py` verifies that helper; it is not a new railway model. `handoff_validation.json` records preparation checks and file sizes, not model token or credit savings.

## Quiet checks
From the project root:

```sh
python tools/quiet_checks.py --suite corridor --label baseline
python tools/quiet_checks.py --suite application --label acceptance_cli
```

The application suite is expected to report unavailable before L01 creates `tests/test_cli.py`; it must not pass an empty suite. Reports live in unique `.local_checks/` subdirectories. Avoid feeding that tree or `.local_runs/` back to the agent unless a failure needs investigation. Add those two directory names to local Git excludes if appropriate; Git ignores are not an access-control boundary or a guarantee that an agent cannot read them.

`--suite legacy` runs the broad historical proof suite only when deliberately requested. Do not use it as the default after every edit. The helper records commands, environment, input hashes, summaries and full logs; it does not cache or skip executions. Failure diagnostics remain available rather than truncated away. Timeout handling kills the direct test process; it is not a general operating-system process sandbox.

## Usage discipline
The normal read set is short; expand it only when correctness needs more evidence. Read relevant sections, avoid duplicate agents and repeated architecture planning, and inspect failed tests rather than all passing test output. The task has a 4,096-byte normal CLI-output target and an approximately 200-word completion-response target. Important blockers are never omitted to meet these limits.

These are project working rules, not a hard billing cap. They cannot cap hidden reasoning or guarantee host charging. Use host-reported consumption when available and compare equally verified work. Instruction word counts measure only the authored startup notes, not total task context or plan credits.

This approach is consistent with the official guidance to keep repository instructions practical and concise and give tasks specific goals, files, constraints and completion criteria. Sources reviewed on 21 September 2026: [AGENTS.md guidance](https://developers.openai.com/codex/guides/agents-md/) and [Codex best practices](https://developers.openai.com/codex/learn/best-practices/). No specific host, transport or model configuration is configured by this overlay.
