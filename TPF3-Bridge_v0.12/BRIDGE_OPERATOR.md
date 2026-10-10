# Bridge operator — current capabilities and lessons

Updated 10 October 2026. This is a compact consolidation of operator additions
since Challenge03, not a district completion record. Commands and schemas remain
in [OPERATOR_USAGE.md](OPERATOR_USAGE.md). The coordinator owns native execution,
layout decisions and current district acceptance; the implementation worker owns
assigned offline changes. Construction, path availability, observed service operation
and visual design acceptance remain separate results.

## Reusable additions

- `bridge_interfaces.py` and `bridge_station.py` register semantic station roles and
  reacquire exact construction/terminal/frozen TRACK identities in the current
  session. Geometry filters that identity-qualified set; proximity never creates
  correspondence. An exposed `station_exit` supports deliberate lead extension,
  not a guarantee of native clearance or an operational route. Reacquire ordinary
  external roles after extension. Native line terminal indices are zero-based;
  station-survey terminal selectors are one-based. Save identity remains unknown.
- `bridge_station_routes.py` reviews connected terminal paths without demanding
  obsolete free construction ports. Each endpoint may select its own registry and
  exact revision; repeated registry loads and station surveys are reused within
  one review. `identity_frozen` reads avoid traversing the external district while
  retaining completeness checks. External role qualification still needs its
  separate complete external observation. Returned path entries default to256 for
  station review, with an explicit maximum512; these are observation/acceptance
  bounds, not native pathfinder search limits.
- `bridge_operator_tasks.py` reuses existing signal, station, depot, line and vehicle
  operations through named tasks. Exact prior receipts and freshly resolved roles
  provide identities. `observe` performs one bounded read; no automatic simulation
  loop or polling framework is introduced. Eight offline operating templates passed
  static/fake-client checks; that preparation is not six demonstrated services.
- `bridge_operator.py` supports explicit plain-track coalescing of a named exact
  chain, with complete retained boundary incidence and fresh geometry checks.
  It preserves declared outside edges and does not silently remove branches.
  Coalescing is a specific native fitting option, not a universal prerequisite.
- `bridge_live.reconcile_constructed_replacement` independently checks an already
  built replacement without replay. It requires exact saved request correlation,
  realised chain/control/structure checks, original edge absence, declared outside
  geometry/incidence and a directed route through every replacement edge. Any
  changed route-length acceptance needs explicit authority/reason. It clears only
  the Python pending journal after proof; native guard clearance and fresh-session
  reacquisition remain separate. Ordinary authorised save/load is not crash recovery.

## Construction and direction lessons

Build junctions before dependent signals where possible: the current split producer
rejects `split_edge_objects_present`. A specific bounded candidate change can solve
a rejected proposal; failure of one fit does not establish native impossibility.
Check a selected station template's actual open approach side before treating an
identity-qualified endpoint as buildable. The built-in template5 terminus example
is a template-specific observation, not a rule for every station.

Keep construction endpoint conventions distinct from signal travel. RN's original
35-unit crossovers built after correcting only the target departure tangents; its
prepared merge alternative was unused. North crossovers instead built after plain
approach coalescing, without moving their alignment. These are different diagnosed
cases, not grounds for a global tolerance or spacing change.

Public signal `forward=true` means node0→node1 travel, and `false` the reverse.
The native translation is `EdgeObject.left = not forward`; functional readback
requires `SignalList.edgePr`'s reversed bit to equal `forward`. Commit279da44 corrects
the previous inversion. On build40420, after normal reload, an isolated required-edge
TRAIN test allowed northbound travel and rejected southbound travel. Evidence:
`.local_runs/operator/district04/signal-direction-corrected-proof.json`.
The24 explicit replacements in `signals-R6-results.json` all returned successful
functional readback; none of those placement receipts claims a directed route proof.

`functional_signal_verified` verifies attachment/type/orientation. Corrected receipts
also expose `travel_forward`, `native_left` and `directed_route_verified:false`.
An available route can use an unintended running track or crossover. Require the
intended exact corridor edges and inspect path directions before asserting running
policy. The station-route helper requires endpoint edges only; its successful result
does not by itself prove the whole intended corridor. Physical train traversal and
stop/service behaviour require their own native observation.

## Efficiency evidence and limits

Recorded native crossover runs each used14 calls: north run`e4dc7001cf0b4e63`
used7.812 seconds native-call time, and RN run`9288f7b2af0d4790` used7.031 seconds.
Their local `state.json` records supply these measurements. They are individual
successful-case costs, not a comparative speedup or a general fitting guarantee.
Scoped reads address an observed incomplete external read involving768 frozen
TRACK records/786 processed station nodes. Avoiding unrelated graph traversal and
reusing surveys are implemented mechanisms; no before/after token-saving percentage
or credit saving has been measured. Actual GPT usage is unavailable here.

Latest affected checks are434 live-client tests at
`.local_checks/district04-signal-direction-fix__md9d8xo/report.json` and64 operator
tests at `.local_checks/district04-signal-direction-operator_vmt76p3x/report.json`.
They validate Python behaviour, not Lua execution. Native signal qualification
above is separate. No unchanged suites were rerun for this documentation update.
Detailed compact implementation records remain under `.local_runs/operator/district04/`.

District04 whole-route, six-service and design-quality completion remain pending
the coordinator's current acceptance. No universal connectivity, capacity,
reservation, cross-save identity or host-recovery guarantee is added.
