# Live Python interface

bridge_live.py provides callable/CLI access to the reusable development mod in a
healthy running TPF3 world. bridge_operator.py adds named plans and operating tasks;
see [operator usage](../../OPERATOR_USAGE.md) for schemas. Offline bridge_cli.py retains design/mock
semantics. Native command success, realised-state acceptance and train operation
are separate results. Current limits/status are in [STATE.md](../../STATE.md).

## Mod and context
Copy the contents of ../n01_probe/prepared_mod/ into the normal user staging folder
`tpf3_bridge_n01_c04_20261001`, with mod.json, _metadata/ and content/ directly under
that folder. Enable TPF3 Bridge N01 Activation through normal save/load UI. Use actual
user-data paths; do not edit base-game files or assume hot reload. The adapter supports
explicit construction, not just read-only probing. The bridge does not launch/restart
TPF3, Steam or the host, or repair environmental failures.

Use an explicit local context file rather than an old demonstration path:

```json
{
  "mod_directory": "<actual staging folder>/tpf3_bridge_n01_c04_20261001",
  "log": "<actual user-data folder>/crash_dump/stdout.txt",
  "session_evidence_root": "<temporary shared operating-state folder>"
}
```

Relative paths resolve beside the context file. The field name session_evidence_root
is retained for compatibility; its folder contains temporary request data and minimal
functional reconciliation state, not a permanent audit archive. One active adapter
uses one shared journal root/client. READY/SESSION identify the adapter handshake,
not a guaranteed save GUID; freshly inspect identities after normal load changes.

```powershell
python bridge_live.py inspect --context context.json --params inspect.json
python bridge_live.py extend --context context.json --params extension.json
python bridge_live.py extend --context context.json --params extension.json --execute
python bridge_operator.py station-survey --context context.json --input station.json
python bridge_operator.py plan --context context.json --input plan.json
python bridge_operator.py execute --context context.json --run CURRENT_RUN
```

Briefs must name current native identities, authorised regions and selected constraints;
these commands are invocation shapes, not instructions to execute a previous result.
Extension defaults to fit-only; --execute performs the authorised build/readback workflow.
Callable entry points include client_from_context(path), extend(client, brief, execute=False),
place_signal and the station/depot interfaces. Use --help and source-specific usage for
other connection/layout operations; there is no unrestricted routing guarantee.

## Current behaviour
Native inspection/discovery, exact attachment, bounded fitting, graded connections,
junctions, bridge/tunnel construction and exact replacement/removal are supported.
Basic passenger stations, signals, depots, native lines/vehicles and bounded observation
reuse native APIs. Station role and connected-terminal review qualify exact frozen TRACK
identity; geometry is a filter, not correspondence. Reacquire changed bindings and use
current revisions before mutation. Sampled geometry is not a continuous clearance proof.

Public signal forward=true requests node0-to-node1 travel. Native placement maps
left=not forward and verifies the returned reversed bit equals forward. Attachment/type/
orientation readback does not prove the chosen running corridor: require its exact edges
and directions in a native path check. Physical traversal remains a separate observation.

Line creation/update configures the native passenger cargo identity at passenger stations,
using stopConfig vectors indexed at cargo ID+1, full capacity and load-if-available.
Readback verifies masks and exposes passenger_loading plus cargo_configuration_verified.
No hardcoded passenger ID, custom routing/signalling simulator or vehicle cargo rewrite.
Existing lines require explicit updates; source changes alone do not modify world state.

## Failures and data lifetime
Use finite timeouts and compact summaries. Full temporary diagnostic data stays local
only while useful. No permanent agent journals, activity histories, completed-run logs,
handoff archives or cleanup manifests. This documentation does not remove the minimal
journal/context state needed to reconcile an uncertain live operation safely.

Never rerun --execute to recover a missing response. Keep pending-operation intent,
correlation/session and reconciliation state until exact matching evidence or fresh
semantic readback resolves the effect. Partial effects remain visible; no assumed rollback,
automatic resume, crash recovery or duplicate-operation guarantee across new journals.
Read-only reconciliation does not automatically clear native mutation guards. Follow the
applicable reconciliation contract before further construction; ordinary healthy save/load
requires fresh inspection. Remove completed temporary request/response/diagnostic data once
no functional dependency remains, rather than retaining it as project history.

Saved-file integrity is separate from semantic acceptance. Unknown save identity,
reservations, demand/capacity and general-version behaviour remain unknown. Below the
semantic game boundary, report the precise external blocker and stop; do not repair OS,
permissions, authentication or processes. Native/UI execution remains coordinator-owned.
