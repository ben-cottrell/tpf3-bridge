# TPF3-Bridge milestone state — 3 October 2026

## Current checkpoint
PIF-P02 accepted; GIT-G01 closes repository hygiene and publication. No new railway
task/batch authorised by this closeout. Working branch codex/initial-implementation,
remote origin https://github.com/ben-cottrell/tpf3-bridge.git. Pre-publication HEAD:
f416b232844c07e76bce256fa93e55966ad8a7b8. Final commit/push receipt remains local
at .local_runs/milestone_git/g01/publication.json; Git history supplies the checkpoint.

## Implemented interface
Offline commands: bridge_cli.py design [--mock-execute], connect, connect-pair
[--mock-execute --snapshot], status --run, verify --run. bridge_app exposes callable
equivalents. L01–L14 and exhausted batch ledgers are preserved; no game construction
claims arise from offline/mock evidence. Supported offline connection domain is
level/zero-cant, bounded existing relative-heading/curve families; paired tracks use
explicit directed endpoint IDs, compatible parallel pairs/equal end spacing.

Live: bridge_live.py inspect/fit/build/readback and extend --context CONTEXT
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
