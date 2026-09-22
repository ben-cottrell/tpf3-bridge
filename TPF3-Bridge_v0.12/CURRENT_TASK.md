# Next milestone: read-only native TPF3 probe

**BLOCKED / NOT AUTHORISED TO RUN YET**

The offline L01-L14 milestone is closed and paused. Leave all approved queues
exhausted. Do not launch workers, poll, schedule checks, install dependencies,
generate a mod or begin another implementation batch.

Prerequisites: a runnable local Transport Fever 3 game and verified native API
mapping for the actual installed build. Neither is established by mock evidence.
Resume only after prerequisites are available and explicit user authorisation
for the bounded read-only probe is given. Do not invent native functions or assume
Transport Fever 2 API compatibility.

Future authorised scope: reuse the existing adapter/capability and snapshot
contracts (`contracts/bridge.schema.json`, `contracts/tpf3_unprobed_capabilities.json`;
existing adapter manifests in `proof/railcorridor/adapter.py`). Establish actual
game/mod build, loaded save identity, coordinate mapping, and a small explicitly
bounded snapshot of terrain, track and available assets. Report inaccessible or
unverified fields and incomplete coverage honestly; retain source/probe provenance.

Keep raw observations/results local in a new evidence location, never overwrite
older results. Normal response contains identities, coverage, counts and blockers
only. Read-only: no construction, game/save edits or automatic resume. No MCP,
physics, station detail, new dependencies or task-runner feature. No second world
schema or large specification. Preserve source, ledgers, counts and acceptance
records. Refer to STATE.md and USAGE.md; do not re-audit or rerun unchanged tests.
