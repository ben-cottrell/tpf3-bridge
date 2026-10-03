# TPF3-Bridge milestone state — 3 October 2026

## Current checkpoint
PIF-P03/P04 accepted; GIT-G02 publishes this source/tests/docs checkpoint on
codex/initial-implementation, origin https://github.com/ben-cottrell/tpf3-bridge.git.
Prior published revision1080dd457b8564faa52a5f4e20d46afed26f4b89. Git history and
.local_runs/milestone_git/g02/publication.json identify the resulting commit and
verified remote SHA. Evidence/logs/ledgers stay local and ignored; no deletions.
29client/14runner acceptance reused after unchanged-file checks; no game operations.

## P04 native route verification
Callable route(client,brief); CLI bridge_live.py route --context CONTEXT --params ROUTE.
Fresh exact BaseEdge/transport NodeIds feed native findPathNodeToNode; no Python graph.
Build40408 TRAIN path131229→131239→131240→131241→131235, nodes/index0
131225→131226→131237→131238→131215→131234, length88.659898native units.
Exact continuity, selected mode, approach lanes/directions and required edges pass.
Native excessive-length, invalid-endpoint, missing-required-edge and wrong-entry-direction
cases rejected without build; CLI exit1 even when query status is ok but unverified.
max_length is acceptance-only; API exposes no engine search bound or initial direction
parameter. ≤64observations; truncation fails. No traversal/reservation availability claim.
python tools/quiet_checks.py --suite live_client --label pif-p04-client:29passed,
.local_checks/pif-p04-client_6av4bjeg/report.json; reused after tested-file hash checks.
python .local_runs/live_python_interface/p04/run_acceptance.py:5expected native outcomes.
python .local_runs/live_python_interface/p04/check_evidence.py:passed; receipts/hashes,
py_compile and git diff --check. Checks/result/HANDOFF local in p04 directory.
8read-only requests total;4normal loads;0build/save/simulation diagnostics. Paused,
non-maximised disposable world. Earlier constructor nil/findPath error300 retained;
no broad survey/unknown mutation replay. Historical P03 code snapshot preserved at
p04/before; prior acceptance not rerun against changed source. Usage unavailable.
Accepted by coordinator; no automatic next engineering task.

## P03 two-ended native connection
Live callable connect(client,brief,execute=False), CLI bridge_live.py connect
--context CONTEXT --params CONNECTION [--execute]. Exact source/target edge/node
IDs; native fit with outward-source/incoming-target orientation, matching assets,
constant grade compatible at both ends (grade1e-6,height0.001 numerical tolerance).
No general vertical solver; unsupported native families/directions are explicit.
Final proposal reuses both existing positive node IDs; fresh readback checks both
known incident edges/resources. Unknown late mutation responses remain blocked.
Build40408: edges131239/131240/131241, nodes131226→131237→131238→131215,
source131229/target131235; length60.001331,radius100,sampledXYerror0.000503309.
Independent later inspection confirmed both attachments, tangents, Z and assets.
Nearby test approach131235 supplied the target. Fit-only, invalid target and reversed
target ran without build. Two earlier stub collisions retain unknown effects/blocked
journals; a straight candidate returned unsupported reverse geometry before mutation.
P03:12requests,4world submissions(2successful,2collision rejections),3normal loads,
1normal save,0simulation diagnostics. Disposable world saved; paused/non-maximised.
python tools/quiet_checks.py --suite live_client --label pif-p03-accepted:24passed,
.local_checks/pif-p03-accepted__v7dp768/report.json. py_compile/diff checks passed.
python .local_runs/live_python_interface/p03/check_evidence.py:passed; checks.json,
result.json,workflow_history.json,HANDOFF.md in that directory;12native receipts
validated,8prepared/staged hashes match. Unchanged14quiet-runner tests reused below.
P03 alone proves no pathfinder/traversal; P04 adds native route evidence above.
No continuous proof, saveGUID, rollback or transport guarantees; no L01–L14/runner changes.
Latest human steering: whole test map disposable; prefer open land or clear incidental
obstructions. Earlier collisions do not prove an API defect; accepted work not repeated.

## Implemented interface
Offline commands: bridge_cli.py design [--mock-execute], connect, connect-pair
[--mock-execute --snapshot], status --run, verify --run. bridge_app exposes callable
equivalents. L01–L14 and exhausted batch ledgers are preserved; no game construction
claims arise from offline/mock evidence. Supported offline connection domain is
level/zero-cant, bounded existing relative-heading/curve families; paired tracks use
explicit directed endpoint IDs, compatible parallel pairs/equal end spacing.

Live: bridge_live.py inspect/fit/build/readback, extend/connect/route --context CONTEXT
--params BRIEF [--execute]; callable client_from_context and extend. Fit-only default;
explicit construction performs fresh inspect→native fit→build→fresh readback in one
compound native invocation. Current session handshake and one shared durable journal;
no automatic mutation replay. Reusable mod is implementation/n01_probe/prepared_mod/.
Usage: implementation/live_python_interface/README.md.

## Native evidence and limits
Actual TPF3 build40408, disposable context: GameScript, native event/log transport,
native forward ARC/STRAIGHT fit, explicit construction and exact TRACK/node readback
demonstrated. Constant inherited anchor grade; selected radius/region; local bounds
400×400XY, length≤800, ≤8pieces. Final P02 edges131227/131228/131229 connect exact
nodes131218→131207→131225→131226; length296.165783native units, selected radius100,
sampledXYerror0.00048828125. Later independent inspection confirmed identities.
Fit-only, invalid attachment and region failure ran without further construction.
Owned disposable save saved normally; game left paused/non-maximised.

P02 history:11workflow attempts,3world submissions(2demonstrated builds,1collision
rejection),5normal loads,3saves,1simulation diagnostic. Collision effects remain
unknown in its historical blocked journal. Proposal placeholders are not realised
effects. Cross-callback cached state proved unreliable; dependent stages use local
invocation data. Development resource/log transport, sampled geometry only; native
save/load identity, train traversal, arbitrary-version support and production
idempotency remain unestablished. No crash resume/rollback/OS recovery guarantees.
Standalone Lua syntax check unperformed; changed scripts executed natively.
Detailed station modelling frozen; train-physics expansion deferred. Usage unavailable.

## Acceptance and local evidence
P02: python tools/quiet_checks.py --suite live_client --label pif-p02-final-reconciliation
18passed: .local_checks/pif-p02-final-reconciliation_1k1ppid8/report.json.
P01 unchanged runner: python tools/quiet_checks.py --suite quiet_runner --label pif-p01-runner
14passed: .local_checks/pif-p01-runner_8qsssvzu/report.json; relevant dependencies unchanged.
P02 evidence check passed: .local_runs/live_python_interface/p02/checks.json;
result.json and workflow_history.json in the same directory. Raw correlated requests/
responses remain under .local_runs/live_python_interface/p01/<session>/.

L14 recorded reports (unchanged engineering code; no closeout rerun):
- pair53: .local_checks/batch_l14_pair_e3di3_kv/report.json
- application73: .local_checks/batch_l14_cli_h2tulk1d/report.json
- single input9: .local_checks/batch_l14_single_input_1_86u3iy/report.json
- single geometry9: .local_checks/batch_l14_single_geom_prc_8har/report.json
- single application12: .local_checks/batch_l14_single_app_3qss9ypy/report.json
- geometry118: .local_checks/batch_l14_kernel_psl1_5no/report.json
- corridor100: .local_checks/batch_l14_corridor_ncgfreg9/report.json
- branch107: .local_checks/batch_l14_branch_v5nma0qr/report.json
Independent acceptance: .local_runs/batch_pair_5ef4682fd126404ea379936e33ca3643/result.json.
Batch ledger .task_batch/pair-l09-l14/state.json:6invocations/0repairs, exhausted.
Historical L01–L14/N01/N02/NCD/PIF detail and prior STATE/AGENTS are preserved locally;
pre-cleanup documents: .local_runs/milestone_git/g01/before/. No old evidence overwritten.

## Git hygiene
Publish reusable Python/mod source/tests, quiet-suite integration, architecture,
capability-planning template and concise docs. Imported research pack, local handoffs,
continuation records, generated request modules, old candidates and detailed P01/P02
handoffs stay ignored in place so canonical local paths continue working. No deletions,
game/save edits, worker launches or task-runner redesign. Metadata now honestly states
that explicit construction is supported. Cleanup inventory/checks and push receipt
are local beneath .local_runs/milestone_git/g01/.
