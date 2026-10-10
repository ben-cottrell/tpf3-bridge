# TPF3-Bridge working rules

## Authority and scope
SPDD_SCOPE.md is the authoritative product boundary. Research, prototypes and tests
may inform implementation but cannot expand it. Apply current explicit user/coordinator
instructions, then SPDD_SCOPE.md, NATIVE_FIRST_ARCHITECTURE.md and CURRENT_TASK.md/STATE.md.
Read the short current state and exact assigned source pointers; do not audit the
repository or reread historical material by default.

The coordinator owns railway design and native/UI execution. Implementation workers
perform assigned offline code, tests and documentation only unless explicitly delegated
otherwise. Human standing authority covers in-scope work, disposable game maps/saves,
normal construction/demolition/terrain/simulation/save/load and coordinator communication.
Routine steps need no repeated project approval. External tool rules remain binding;
report denials without bypassing them. Local milestone commits follow standing user
authority; remote publication requires explicit user authority. This cleanup requires no
native actions or automatic continuation.

## Design and runtime
For railway planning or material layout changes, read railway-design/SKILL.md and
follow RAILWAY_DESIGN_PROCEDURE.md; use RAILWAY_DESIGN_GUIDE.md for design lessons.
Prefer native tools, exact attachment identities and finished functional requirements.
Do not weaken hard constraints or treat a failed fit as native impossibility. Investigate
proven functional problems; incidental numerical discrepancies do not create repair tasks.
Map content/terrain are redevelopable unless explicitly protected or functionally required.
Runtime requires a healthy running game/adapter; no host, permission, authentication,
process or crash recovery. Detailed station internals and train physics remain excluded.

## Efficient implementation
Use exact pointers, bounded tasks, deterministic local loops and one worker unless
explicitly justified. No routine model calls for search, polling or verification. Reuse
valid checks for unchanged code; run affected checks quietly when needed. Inspect failures,
not passing transcripts. Review the changed diff and preserve unrelated local changes.
Keep stdout compact. Record actual usage only when exposed; never infer credits.

## Living documentation and temporary data
Maintain concise current guidance and minimal functional state, not an activity journal.
Do not retain permanent agent audit histories, handoff archives, completed-run logs,
cleanup manifests or replacement archives. Diagnostics are temporary: keep only while
needed, then remove after completion. Keep reusable code/tests/fixtures/design knowledge.
Retain only context and state necessary for safe operation or reconciliation of uncertain
live mutations; never erase a pending operation to permit duplicate execution. Logging
wrappers may produce temporary diagnostics during a needed check, not permanent history.
Stop at the assigned outcome; no unsolicited task, batch, scheduler or automation.
