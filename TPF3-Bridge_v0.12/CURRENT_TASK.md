# PIF-P45 — STOPPED: explicit reconciliation passes; matching native build fails70

First connector accepted under auditable local70 revision, original150 failure
preserved. Matching connector constructed but native radius37.4341<70; no replay
or further criterion revision. Later read publication stopped on WinError5 journal
replace; pending read/nested mutation retained, no host repair. Return to Astra.
See STATE.md and p45/HANDOFF.md. Original coordinator card follows.

# PIF-P45 — explicit revised throat criterion and completion of the existing stage

Astra design decision after direct human correction, 4 October 2026. The user says single crossovers are good, especially on 5 m parallel tracks; the earlier discouragement concerned scissors. The user observes the existing curves look acceptable and explicitly accepts tighter radii around low-speed throats/platform fans. This supersedes the coordinator's blanket 150 m throat minimum. It does not establish a train speed or waive native connectivity.

## Fixed design decision
Retain the already constructed rail9@160 -> rail10@260 crossover if fresh native verification passes under a revised LOCAL minimum radius of 70 m. Its measured radius was 74.2072767 m. The 70 m value is Astra's explicit design choice for these two compact throat connections, not a global bridge default or a user-supplied number. Keep the original native fit target 187.5, same endpoints, height, representation, conversion tolerances and level grade bound. Apply the same local 70 m realised minimum to the matching unbuilt rail12@160 -> rail11@260 crossover. Do not redesign or demolish the first crossover merely to recover 150 m. Do not implement the offline operation05 two-piece candidate: the requirement has changed. Other existing constraints remain unchanged.

## Actual bridge gap to implement
Baseline local commit 158cb96a43608bd41de3759f5bec46abbdba4a77; P44 repair reviewed and accepted (326 tests, exact continuation exercised). P44 original crossover remains historically failed against 150 m. The live journal/native state has pending request e3c5eae2c9cc47c39b65631dd220459e in session pif_1791132513_132062371, build40408. Seven returned TRACKs104607..104613; connector104611/104612/104613 and junctions104599/104602. Fresh bind before use; physical indices are not platform IDs.

Existing bridge_live.reconcile_constructed_crossover always reuses the original constraints. Add a narrow explicit caller-supplied acceptance revision for this reconciliation: original request/receipt/fit, old and new criteria, reason/authority and new native observations remain recorded. Default reconciliation must still use original criteria. Only allow the supported radius revision; do not allow endpoint, returned identity, topology or other unrelated parameters to change. Validate its value and reject malformed revisions. Do not rewrite the original failed response, mutate the old pending payload to pretend it always asked for70, manually clear guards, or replay construction. Clear pending only through successful native verification of exact constructed state under explicitly revised criteria, with durable evidence tying both criteria to the same original request. Native guard must retain receipt/current-state matching; adapt it narrowly only if required. If fresh verification fails other requirements, report the concrete discrepancy rather than waive them.

## Integrated native outcome
Reconcile the existing first connector without rebuilding it. Then complete the still-unbuilt matching rail12@160 -> rail11@260 connection using the P44 fixed brief with local realised radius70 and native fit187.5, all other geometry/identity requirements unchanged. Reuse all six completed extension actions; no replay. Preserve functioning station connections and previously built first-stage crossovers. Verify both new connections in both directions plus affected through routes, reusing unaffected evidence. Inspect actual realised geometry and record measured radii honestly. No arbitrary parameter sweeps, new topology, scissors, station expansion or train-operation claims.

Tests should prove default150 still rejects this recorded74 case, explicit justified70 revision succeeds only with fresh exact-state verification, and malformed/unrelated/stale revisions fail without clearing pending. Use affected suite, concise docs/STATE, local milestone commit, no push. Normal healthy-game save/load and staging authorised; preserve pending evidence through any session change. Save a useful completed-stage checkpoint. No host restarts/services/dependencies.

Evidence references: p44/HANDOFF.md, native/final_result03.json, native/partial_readback03/, native/crossovers/cross_9_10_execute02.json, operation04 fixed geometry. Write p45/HANDOFF.md and compact completion handoff to coordinator01a0f987-8917-7f31-84c3-838acacc9e04, under permanent direct human authorisation for project payloads. Return control to Astra for the next physical design stage; do not substitute a layout.
