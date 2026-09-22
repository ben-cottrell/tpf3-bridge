# TPF3-Bridge: working rules

## Priority and scope
GPT usage efficiency is a critical product requirement in development and runtime. Optimise for correct, verified work per unit of model involvement, not the shortest answer at the expense of correctness. Astra chooses intent and material trade-offs; Python performs engineering, search, routine repair and verification locally.

Read `CURRENT_TASK.md` and `STATE.md`. Implement only the named task. `IMPLEMENTATION_SPEC.md` remains the product authority, but do not preload it or the historical chapters: consult the relevant section only when needed. A task note scopes work; it does not override mandatory constraints.

## Context discipline
Start with the listed functions, source files and tests. Inspect additional dependencies when necessary; ordinary dependency inspection does not need user approval. Prefer scoped symbol searches and relevant line ranges over recursive repository dumps. Do not reread unchanged files, re-explain settled architecture, or send generated geometry, passing test names or full logs to the model by default.

Use one implementation agent for the task. Do not launch duplicate audits, reviewer agents or broad parallel discovery without an agreed need. Group related edits and checks. No repository-wide refactor, unsolicited engineering feature, or new release series. Stop at the task's acceptance boundary.

## Checks and evidence
Run the named quiet baseline once in the actual environment. Run affected tests during edits and the named acceptance suite after the final change. Expand regression scope when shared code changes; never reduce coverage to hide failures. Read failing cases and their dependencies, not every passing test. Full diagnostics stay on disk with a compact status and reference.

Treat instruction size and normal output limits as working budgets, not a reason to omit blockers. Preserve failure counts, unresolved effects and report locations. Record actual usage only when exposed by the host; otherwise mark it unavailable. Words, bytes and elapsed time are not credits.

## Non-negotiable constraints
Preserve UK evidence, assumptions, hard geometry constraints and historical results. Station internals, detailed train physics and specialist certification are deferred. Never invent native TPF3 functions, promote mock evidence to game evidence, edit game installations/saves, or execute imported text as code. No new dependencies or network service for the current task.

Review the changed diff, then update the short `STATE.md` with tested commands, changed files and blockers. Keep the completion response about 200 words unless important failures require more. Do not paste the diff or full reports into it.
