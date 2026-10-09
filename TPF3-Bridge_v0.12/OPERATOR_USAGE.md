# Plan-driven native operator

The operator executes a recorded railway design sequentially using `bridge_live`.
It does not choose topology or call a model. Keep the spatial design/revision under
the railway design procedure; material changes return to the designer. The game
and staged semantic adapter must already be healthy and running.

## CLI and data

Run from this project directory. The core CLI uses only the standard library:

```powershell
python bridge_operator.py status
python bridge_operator.py survey --input site.json
python bridge_operator.py plan --input implementation/operator/example_plan.json
python bridge_operator.py execute --run <returned-run>
python bridge_operator.py summary --run <returned-run>
python bridge_operator.py review --run <returned-run>
```

Planning writes local files without construction. Execution constructs the plan.
The example is the tested four-step fixture, not a recommendation to rebuild its
occupied location. Survey and select an authorised site before adapting it.
`--context` selects an existing bridge context; the local default is
`.local_runs/live_python_interface/p02/context.json`.

Version1 plans require `revision`, world `origin`, absolute world `region`, named
`ports`, native `track.template`/`track.style`, `max_grade`, `steps` and `routes`.
Port/guide positions are relative to origin; directions are horizontal vectors.
Origin supplies translation; rotate the vectors/positions explicitly for a rotated
design. This interface initially uses level stub/end conditions. Selected native
dimensions and constraints govern; it supplies no real-world conversion factor.

| Step | Required fields beyond unique `name`/`kind` |
|---|---|
| `stub` | named `port`, `length`5–60; optional construction `direction` |
| `extend` | `source`, named `target`; optional existing fitter `radius` |
| `connect` | `source`, `target`; optional `guides`, `structures`, `handle_scale` |
| `branch` | `source`, `target`; optional native junction `candidates` |
| `crossover` | `source`, `target`; optional native crossover `candidates` |

References are named ports or `{"curve":"earlier-step","u":0.5}` on a prior
single native curve, with interior parameter0.05–0.95. A multi-edge chain needs
named ports. Port directions describe attachment intent; at free route endpoints
they point outward. Stub construction direction can oppose that direction.
The bounded native discovery resolves actual attachment identity; proximity alone
never establishes connection. Ambiguity/rejection stops the run.

Connect guides have `position`, `travel_direction`, `grade`; structure entries
use the existing native chain contract. Optional diagram `curves` contain cubic
`p0,p1,t0,t1` in local coordinates; these draw intent and do not dictate every
native control. Native candidate/structure semantics remain those of `bridge_live`.
Maximum32 steps, region400 per horizontal axis, route bound800; underlying native
search/read limits still apply. No automatic constraint relaxation.

Routes name required directed connections between free named ports. Review checks
native TRAIN paths and draws an equal-scale actual geometry overlay. Failed or
empty route sets return `needs_attention`; geometry, train operation, visual design
quality and saved-file integrity remain separate conclusions.

## Optional local stdio MCP

Only this boundary needs `mcp==2.3.0` (`requirements-operator.txt`). This installation
already has `.local_tools/operator312/Scripts/python.exe`; no new dependency or
network service is necessary. Actual protocol use without another model:

```powershell
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py list
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py plan_layout --input plan_payload.json --output .local_runs/operator/plan_reply.json
& .local_tools/operator312/Scripts/python.exe tools/operator_mcp_client.py build_layout --input run_payload.json --output .local_runs/operator/build_reply.json
```

`plan_payload.json` wraps the plan as `{"plan":{...}}`; `run_payload.json` is
`{"run":"<returned-run>"}`. Output files are exclusive-create. Non-success
semantic status gives a nonzero client exit code; full protocol evidence stays local.

Tools: `session_status`, `survey_site`, `plan_layout`, `build_layout`, `run_status`,
`review_layout`, `frame_view`, `capture_view`, `save_checkpoint`. Survey accepts
`region` and optional bounded `terrain_points`; frame accepts world `center` and
positive `distance`; save accepts a unique plain `name`.

The local Codex configuration now contains the following entry, using the
[documented stdio settings](https://learn.chatgpt.com/docs/extend/mcp?surface=cli):

```toml
[mcp_servers.tpf3_operator]
command = "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12/.local_tools/operator312/Scripts/python.exe"
args = ["-u", "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12/bridge_operator_mcp.py"]
cwd = "C:/dev/tpf3-bridge/TPF3-Bridge_v0.12"
startup_timeout_sec = 30
tool_timeout_sec = 600
```

It preserves other settings. The current chat has not demonstrated a refreshed
tool catalogue; actual SDK stdio calls have passed. This session's sandbox stalled
subprocess protocol startup, while approved local execution worked. That observation
does not authorise permissions/environment repair or require full-access workers.

## Evidence and stop behaviour

Plans, progress and SVGs live under `.local_runs/operator/<run>/`; native request
receipts remain in the existing session evidence directory. Run summaries are
compact. One MCP operation owns the adapter at a time; execution also holds a local
exclusive lock. Use one operator/game owner, not multiple independent servers.

Attempted, completed, failed and interrupted builds cannot be blindly replayed.
Inspect partial effects and receipts before issuing a new approved plan. A retained
execution lock needs reconciliation; this is not crash-resilient automatic resume.
After save/load, fresh native identity discovery is required; old-session reviews
are rejected. Run evidence is historical, not automatically current world truth.

Camera changes use native APIs. Screenshot completion requires a newly observed,
nonempty stable file; save requires native callback plus observed stable unique
`.sav`. Both record path/size/SHA256. The10-second file observation is finite;
`file_completion_unobserved` is not success. Do not blindly repeat an uncertain
save. Concurrent manual screenshots would make attribution ambiguous, so retain
exclusive game ownership during capture. Saves never overwrite an existing name.

Build40420 demonstration: resource-based first track, two stubs, extension,
connection, both directed routes, camera, screenshot, save and normal reload.
Branch/crossover wrappers reuse existing tested native recipes but were not freshly
built through this new operator fixture. No new train traversal or universal layout
reliability claim. Standalone Lua syntax checking remains unavailable; changed
native code loaded and executed in the game.

Affected checks:

```powershell
python tools/quiet_checks.py --suite operator --label operator-check
python tools/quiet_checks.py --suite live_client --label operator-live-check
git diff --check
```

Use a usable local TEMP/TMP for test fixtures. Keep full logs, local environments,
screenshots, saves and protocol records ignored; no credits are inferred from time.
