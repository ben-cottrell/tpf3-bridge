# Native-first architecture

Current scope is in [SPDD_SCOPE.md](SPDD_SCOPE.md). The bridge uses game capabilities
to realise railway intent; real-world references do not impose automatic geometry limits.

## Responsibilities

| Layer | Owns |
| --- | --- |
| Designer | Topology, route priorities, whole-layout corridors/profiles and material trade-offs |
| Python | Reusable operations, bounded candidate fitting, orchestration and outcome checks |
| Lua adapter | Native identities, proposals, construction, queries, error translation and readback |
| TPF3 | Validity/collision, terrain handling, structures, pathfinding, signals and train motion |

The adapter is not a second planner. Keep models out of deterministic fitting and
polling loops. Prefer compact semantic summaries, bounded geometry for a calculation,
and raw diagnostics only for a concrete defect.

## Capability decisions

Prefer exposed native preview/construction/readback over recreating mechanics. Add
a Python approximation only for a demonstrated gap with a useful outcome. Do not
infer APIs from another game or the manual tool's appearance. Current commands and
limitations are documented in [BRIDGE_OPERATOR.md](BRIDGE_OPERATOR.md).

Fit connections, directions, corridors and neighbouring curves. Radius/gradient are
feedback or preferences unless explicitly required or demonstrated native constraints.
Evaluate the full junction, including through-track replacements, and build accepted
prepared geometry without silently refitting. Native segmentation may differ while
the actual brief still passes. Use native units/resources, not an invented universal
compression factor. Resource and turnout limits may differ.

## Identity and working state

Keep DESIGN, PREVIEW and COMMITTED state distinct. Mock tests do not demonstrate
native construction. Preview IDs are not persistent world identities; refresh native
attachments after relevant rebuilding or save/load. A callback alone does not prove
finished function. Keep just enough request/sequence and unresolved-mutation state
to avoid duplicate writes during active work; inspect uncertain effects before retry.

Completed journals, raw logs, audit trails and handoff archives are not permanent
assets. Remove them when no longer needed. Retain current configuration, working
plans, reusable tests and distilled guidance. Do not create cleanup manifests or
replacement archives. Existing code may require temporary request receipts for
reconciliation; these are functional state only while work remains active.

## Terrain and redevelopment

Ordinary content inside an authorised disposable region is redevelopable. Inspection
confers no protection. Explicit protected assets/functions and boundaries remain
binding. Do not invent penalties or approval gates for demolition, earthworks or
rebuilding. Choose native cut/fill, bridges, tunnels or rerouting as appropriate.
Respect explicit absolute terrain floors and inspect the resulting surface. Do not
reimplement terrain physics or require civil-engineering analysis without a real need.

## Outcome checks and repair

Verify intended attachments, directed routes on intended roads, requested structures
and explicit constraints. Check services and observed train movement separately when
operation is in scope. Judge overall design independently of native build success.
Do not reconstruct every internal engine mutation. An unexplained diagnostic alone
does not warrant investigation; focus on actual failures and task-critical unknowns.

Native feedback can guide bounded repair within the spatial plan. Material changes
return to whole-layout design before dependent construction. No rollback is assumed
or required for user-authorised disposable maps. Source-qualified offline geometry
and contract fixtures remain development inputs, not universal native rules.

## Runtime boundary

The game, intended save, adapter and Python environment must already be usable.
The bridge does not restart the game/Steam/OS, repair permissions/authentication,
install unrelated services or supervise crashes. Report unavailable prerequisites.
Normal save/load in a healthy game is supported and requires fresh world identity.
External tool approval review remains binding.
