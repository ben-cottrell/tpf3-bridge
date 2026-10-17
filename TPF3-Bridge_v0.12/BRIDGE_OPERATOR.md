# Bridge operator

See [OPERATOR_USAGE.md](OPERATOR_USAGE.md) for CLI/MCP commands and plan schemas.
The designer owns layout decisions; implementation workers own assigned code changes.
Construction, route availability, observed service operation and design quality are
separate conclusions.

## Current capabilities

- Named data plans for track, graded/structured connections, grouped construction,
  junctions, replacement/removal, native path review, camera/capture/save.
- Semantic station/interface roles, reacquired from exact current construction,
  frozen TRACK and terminal identities. Geometry filters qualified identities;
  proximity is not correspondence. Station-survey selectors are one-based; native
  line station/terminal indices are zero-based. Save identity remains unknown.
- Cross-registry station routes, scoped terminal-path reads and operating tasks for
  signals, stations, depots, lines and vehicles. Observe performs one bounded read.
- Explicit plain-track coalescing, accepted-proposal construction and reconciliation
  of already-built replacements without replay. Keep minimal unresolved request
  state until fresh native observations establish the outcome.

## Construction limits

Build junctions before dependent signals: current splitting rejects edge objects.
An identity-qualified station exit is not a promise of clearance. Check actual
station orientation, modules and open approach side. Basic placement is supported;
advanced station module assembly and numeric terrain editing remain deferred.

One failed candidate does not prove native impossibility. Bounded attachment/shape
alternatives or deliberate coalescing may help; do not infer a universal spacing,
handle scale or radius rule from a single result. Native path review returns bounded
observations, not an exhaustive continuous-clearance or capacity guarantee.

## Signal direction and service checks

Public `forward=true` means node0-to-node1 travel; false means the reverse. The
adapter translates `EdgeObject.left = not forward` and expects the native reversed
bit to equal `forward`. Do not reuse the older inverted convention. Functional
signal readback confirms attachment/type/orientation; it does not prove the intended
route. Require intended corridor edges and inspect travel directions when reviewing
running policy. Station-route checks qualify endpoints, not the entire corridor.

Passenger line create/update sets and checks the native passenger loading mask at
each stop. Existing lines require explicit update. Also inspect service warnings
and observe movement when operation is in scope. Alternative-platform reachability
is distinct from seeing a train choose another platform under contention.

## Working files

Temporary plans, receipts and pending mutation state support current operations.
Delete completed-run data after use; keep configuration, current unresolved state,
reusable examples and tests. Do not retain permanent run journals, audit reports,
activity histories or handoff archives. No host recovery, automatic replay or
universal cross-save identity guarantee is provided.
