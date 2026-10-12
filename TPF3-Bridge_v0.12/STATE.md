# Current state

## Current accepted rehearsal
Giganto1 is user-accepted. `Giganto1 Corridor Review Ready` completed, including
220 ordinary block signals and34 station/junction boundary signals (254 total).
All58 directed station/junction checks and24 corridor/handoff checks passed.
Native stopping line233671 is configured with verified readback; no train traversal
or contention-dependent alternate-platform use is claimed. No layout repair is requested.

## Accepted application
Challenge04 (Mid West C) is user-accepted; no rebuilding requested. Both station
approaches, station-reordering flyovers, regional branches and independent Cross
service are built, with seven destination stations, four depots and24 one-way signals.
All36 intended directed station routes cover the18 C platforms. Six representative
trains completed return sequences, including the four-stop express circuit. All14
service stops have verified passenger loading; line warnings cleared.

Accepted save: Design Challenge 04 - Mid West C Ready for Review.sav. Saved and
left paused; a final reload is not claimed. Accepted earlier design examples remain
reference material, not a task queue. Use the [handbook](RAILWAY_DESIGN_GUIDE.md) and
[procedure](RAILWAY_DESIGN_PROCEDURE.md) for current lessons.

## Implemented capabilities
Offline bridge_cli.py/bridge_app.py: design, single/pair connections, explicit mock
execution, saved-run status and integrity verification. Offline/mock results do not
claim game construction. Level/zero-cant connections and compatible parallel pairs
retain their existing bounded input/fitting domain.

Live bridge_live.py and the semantic mod: bounded native inspection/discovery,
fitting, exact attachment, graded connections, junctions, bridges/tunnels, explicit
replacement/removal, native path checks, basic stations, signals, depots and services.
bridge_operator.py provides named plans, fresh station/interface roles, scoped terminal
route review, cross-registry endpoints, coalescing, operating tasks, review/continuation,
camera/capture/save and existing local stdio integration. bridge_corridor.py adds
bounded authored multi-window corridor plans over the same operator primitives;
sparse track catalogue, point terrain reads, nearby fitting and signal-chain placement
are reusable. No route-design engine or exact native-geometry reconstruction is implied. Native signal direction and
passenger stop loading are corrected and qualified on build40420.

Working source and reusable tests are retained. Completed reports and activity logs
are not retained under the current policy.

## Limits and current decisions
Native path availability, train operation and design quality are distinct. Alternative
platforms are configured/reachable; forced occupied-platform choice was not tested for
this district. No passenger-demand, capacity, deadlock-free or general-version guarantee.
Save identity remains unestablished; sampled geometry is not continuous clearance proof.
Bounded numeric terrain editing is not implemented; native track terrain treatment is.
Detailed station internals and train-physics expansion remain deferred.

Future design guidance includes urban space reservations, coherent compact approaches,
speed/curve progression and sensible lead/signal placement. Handbook/procedure dimensions
are contextual guidance, not new universal engineering gates; speed estimates are unmeasured.

The baseline is published at7530353; approved completed-run cleanup is resolved.
Slice1 adds prepared bulk signal proposals over the existing adapter: exact seed,
session/input-bound one-use handle,16 edges/64 placements,16 objects per resulting
edge, full native functional/retention proof and one named-binding update per batch.
Sampled spacing phase survives chunks/exclusions; uncertain effects require existing
reconciliation with no replay or individual fallback. Compatibility mode is explicit
individual placement; new plans opt into batch mode. Coordinator qualified equivalent
~1.8km fixtures in session pif_1791830254_10220813, benchmark run3b326e3fa125460e:
20 functional signals each and16/16 intended/reverse-blocked route checks passed.
Individual signal phase:100 requests/20 mutations/50.767s request wait; bulk:
50 requests/10 mutations/25.609s. This is ~2x signal-phase improvement only, not
whole-map performance. Construction each49 requests/17 mutations/~25s.
The reusable bridge_signal_benchmark.py now exposes offline dry-run/plan/inspect
and one-attempt build/signal/qualify phases. It uses exact receipt topology,
independent equivalent sites, bounded1000-unit signal windows, sampled300-unit
phase and measured per-phase counters. Optional parallel_family:true fits one
reference per section and derives siblings at surveyed native spacing; default unchanged.

Slice2 offline source prepares ordered local normal_offset_from.group_index
derivatives for2/4-member families, preserves the external prepared_request contract,
inherits structures/shared vertical parameter, and uses native shared trackDistance.
Strict exact/free endpoints, spacing multiples, bounds and20 total segments remain.
Conversion is sampled XY, not continuous3D clearance proof. Native qualification of
this new branch is pending with coordinator; no standalone Lua checker is installed.
Reusable fake Lua fixtures tests/native/test_signal_batch.lua and
tests/native/test_parallel_family.lua remain prepared, unexecuted.
Affected quiet Python validation:563 tests passed,0 failures/errors across
test_parallel_family.py, test_corridor_operator.py, test_operator.py,
test_signal_batch.py, test_signal_benchmark.py and test_live_client.py.
Command: `.local_tools/operator312/Scripts/python.exe -` with unittest discovery
for those six patterns and TextTestRunner(stream=io.StringIO(),verbosity=0).
Python AST checks and git diff --check passed. Slice2 local milestone is the
current source checkpoint; baseline upstream remains7530353, with no new push.
See OPERATOR_USAGE.md for family contract and existing benchmark phase commands.
Detailed station internals and train physics remain deferred.

Keep only current context and state needed to reconcile uncertain live mutations. Temporary
diagnostics are removed after use; no permanent journals, audits, handoff archives or
completed-run logs. Do not erase pending operations to enable duplicate execution.
