# TPF3-Bridge

A native-first British-railway construction assistant for a healthy, already-running
Transport Fever 3 sandbox. Python handles engineering intent, orchestration and
acceptance; the semantic mod translates native capabilities; TPF3 owns game mechanics.
The current Mid West C district is user-accepted. No new task or automation is queued.

## Current guidance

- [Product boundary](SPDD_SCOPE.md) and [standing instructions](AGENTS.md).
- [Native-first architecture](NATIVE_FIRST_ARCHITECTURE.md).
- [Current state](STATE.md), [current task](CURRENT_TASK.md) and
  [development scope](DEVELOPMENT_ROADMAP.md).
- [Railway design handbook](RAILWAY_DESIGN_GUIDE.md) and
  [design procedure](RAILWAY_DESIGN_PROCEDURE.md).
- [Operator commands](OPERATOR_USAGE.md) and [operator capabilities](BRIDGE_OPERATOR.md).
- [Live Python interface](implementation/live_python_interface/README.md) and
  [development mod](implementation/n01_probe/README.md).

## Interfaces
Offline bridge_cli.py/bridge_app.py support bounded design and mock execution,
single/pair connections, saved-run status and integrity checks. Native work uses
bridge_live.py and the reusable mod; bridge_operator.py supplies named plans and
existing local stdio tools. Native identity/readback, path availability, physical
operation and design quality are assessed separately.

```powershell
python bridge_cli.py --help
python bridge_live.py --help
python bridge_operator.py --help
```

Use explicit current context/brief files for live operations. The bridge does not
launch or repair the game/environment, assume rollback or replay uncertain writes.
Current scope includes native connections/junctions/structures, basic passenger
stations, signals, depots and representative services; detailed station internals
and train physics remain deferred.

Keep reusable source, tests, fixtures and living design guidance. Diagnostics are
temporary, not permanent activity/audit/handoff history. Retain minimal functional
context and uncertain-operation state only while needed. Publication remains
externally blocked; no push retry is authorised.
