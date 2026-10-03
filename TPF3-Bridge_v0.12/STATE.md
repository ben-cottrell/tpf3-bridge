# TPF3-Bridge milestone state — 3 October 2026

## Current checkpoint
P12 complete: connect_junction_at / CLI connect-junction-at [--execute] adds native
interior placement with explicit placement_tolerance; ordinary unowned TRACK/no objects,
parameter0.05–0.95, either travel direction, free target. Native cubic evaluation and
one coherent remove/replace/branch proposal; no Python fitter or relaxed constraint.
Build40408: original131326 replaced by135522/135548, outer nodes131317/131318 retained,
interior node135148 at0.50390625; branch135425/8641/131653 to target11085. Native fitted
length350.125965,rise2.991768,grades0.008900871→0.015,requested radius120/margin126;
realised sampled minimum124.535004,max_grade0.015<0.04. Exact native through TRAIN
473.756048 and branch608.866104 pass, including node-owned turnout connectors.
First read used class instead of instance method; corrected before construction.
Initial build returned exact edges but failed an overstrict removal-receipt check.
Fresh final-state readback verified original removal, subdivision controls/resources,
attachments, bounds and both movements without rebuilding. Separate read-only
reconcile_constructed_interior records verification; original failure remains intact,
other transient effects unknown. Old reference, invalid guide/heading, strict grade and
excluded region fail honestly. Existing P11/free-end/corridor interfaces retained.
python tools/quiet_checks.py --suite live_client --label pif-p12-checkpoint:72passed;
.local_checks/pif-p12-checkpoint_fy2mu0id/report.json. Python/test hashes unchanged thereafter.
python .local_runs/live_python_interface/p12/check_evidence.py: retained evidence checks;
full reports, receipts, failures, source/staging hashes, HANDOFF/result/checkpoint in p12.
Disposable map saved normally; fresh load/read verified the same built state. Game left
paused/nonmaximised,no restart. P11 base56011d3; local milestone only,no push.
Geometry sampled,not continuous proof; physical traversal/reservation/all movements,
general native save identity and construction-owned/object-bearing edges unprobed.
Actual usage unavailable; no station/physics/runner change.

## P11 existing-node junction accepted
P11 complete: callable connect_junction / CLI connect-junction [--execute], explicit
junction discovery; exact compatible two-edge through node to free branch target.
Native fit/build/readback reused; normal free-end/corridor eligibility unchanged.
Build40408: junction node131316, incoming131324/through131325/branch132538;
branch TRACK132538/69391/44868 to target132441/node21454; length350.987255,rise3,
grade0.01 to0.015,max_grade0.04. Requested minimum120; native-fit margin126;
sampled realised minimum124.509571. Exact native TRAIN through27.697297 and
branch372.902615 pass, including indexed node-owned turnout connectors.
Trimmed turnout movement curves use exact native connection entity/index;
BaseEdge controls/joins and realised sampled radius/grade/region stay checked.
No global tolerance reduction, Python fitter or relaxed hard constraint.
Initial branch131338-131340 built but failed geometry; fresh through/branch routes
confirmed and sampled radius120 rejection retained. Separate near-parallel proposal
natively rejected; fresh fit-only reconciliation confirmed unchanged attachments/no
completed junction, other effects unknown. Distinct diverging layout accepted.
No blind replay/assumed rollback; original failures/evidence preserved.
python tools/quiet_checks.py --suite live_client --label pif-p11-client-checkpoint:
66passed; .local_checks/pif-p11-client-checkpoint_80yvuwmh/report.json.
python .local_runs/live_python_interface/p11/check_evidence.py: passed; 39 correlated
current-session requests,1614-byte CLI; independent sampled BaseEdge minimum124.575029.
Disposable test map saved through normal UI and left paused/nonmaximised.
Full P11 evidence/HANDOFF/result, correlated receipts/hashes, independent endpoint/
constraint checks and local checkpoint: .local_runs/live_python_interface/p11/.
P10 basee799c04; local milestone only,no push. No edge splitting, construction-owned
station access or all-movements claim. Geometry sampled; physical traversal,
reservation/native save identity unprobed; actual usage unavailable.

## P10 alternating bends accepted
P10 complete: native findDubinsPath direction flag is passed to its native sampler
for endpoints/tangents and comparisons; false pieces additionally verify canonical
endpoint/tangent reversal. Existing exact travel/join/radius/grade/region checks remain.
No supplied direction, guide or hard requirement changed; no Python replacement fitter.
Build40408: translated/rotated previously rejected+12°/−8°/+4° relative pattern,
3legs/9TRACK131319–131327,source131250/node131232→target131268/node131160,
exact guide nodes131313/131316. Length1501.283859,rise12,grades0.015→0.005→0.01→0.015,
radius120/max_grade0.04; six forward/three backward-parametrised native pieces.
Independent committed inspection/native TRAIN1541.342245 pass;sampledXYerror0.005695,
Zerror0.000003815,grade0.015000002,joinheightgap0. Legacy forward straight/curved fits
and wrong-direction/strict-grade rejection pass. Initial fixtureZ envelope120 rejected
prebuild; corrected to80 within existing100 bound, unchanged fixture geometry.
python tools/quiet_checks.py --suite live_client --label pif-p10-client:57passed;
.local_checks/pif-p10-client_uwkb_h39/report.json; unchanged tested Python hashes verified.
python .local_runs/live_python_interface/p10/check_evidence.py: local receipts/hash/
orientation/guide/TRAIN-path/compact-output checks. Native Lua executed; no standalone
checker.14unchanged runner tests reused. One fixture/one corridor; two normal loads/one save,
paused/non-maximised,no restart. Full evidence/result/checks/HANDOFF in p10; reviewed
local milestone SHA in p10/checkpoint.json,P09 base2c2f60c,no push. Geometry sampled;
physical traversal/native save identity unprobed; actual usage unavailable.
Receipt review found aliased orientation-log arrays changed by later height assignment;
fixed immutable capture, retained first receipt and native fit-only verification after
reload. Existing built TRACK chain independently reacquired; no construction replay.

## P09 coherent corridor accepted
P09 complete: connect_corridor/CLI connect-corridor reuses P08 discovery/selection and
native fit/build/readback;1–3ordered XYZ/direction/grade guides, all legs pre-fitted,
one coherent native proposal, exact shared guide nodes/final attachments and TRAIN route.
Build40408:3legs/9TRACK131295–131303, source131271/node131270→target131285/node131283,
exact guide nodes131289/131292. Length1500.004925,rise12,grades0.015→0.005→0.01→0.015,
radius120/max_grade0.04; native TRAIN1540.063845. Fresh independent inspection passes;
sampledgrade0.015000001,joinheightgap0. Fit-only leaves guide identities unrealised.
Wrong-direction/strict-grade briefs rejected prebuild. Original layout/3fit-only
alternates contained unsupported reverse pieces; distinct gradual-bend layout passed,
no hard constraint relaxed. Forward pieces only; no unrestricted-routing claim.
Finite limits:800/8pieces per leg,3200/32overall,3000XY region,4000route acceptance;
discovery unchanged. One proposal is not a transaction/rollback guarantee.
python tools/quiet_checks.py --suite live_client --label pif-p09-client:56passed;
.local_checks/pif-p09-client_7puyv84f/report.json; existing tested hashes match.
python .local_runs/live_python_interface/p09/check_evidence.py checks local receipts,
staged/source hashes, exact guide positions/directions/grades/identity and TRAIN path.
Native code executed; standalone Lua checker unavailable.14unchanged runner tests reused.
Initial automatic review denial preserved/resolved by direct user approval of exact
experiment and disposable-map ownership. Two fixtures/one corridor built; one normal
load/save,no restart; paused/non-maximised. Full failures/receipts local in p09/p01.
P08 baseeae0aca; final reviewed local milestone in p09/checkpoint.json; no push.
Geometry sampled; physical traversal/native save identity unknown; actual usage unavailable.

## P08 integrated connection accepted
P08 complete: connect_brief/CLI connect-brief integrates two bounded native discoveries,
deterministic guide/heading selection and one native compound fit/build/readback plus
TRAIN route. Default fit-only; exact candidate snapshots/incidence revalidated before
build. Only explicit pre-build fit failure allows another pair; unknown/build/route
failure stops, no replay. Partial discovery/no pair/fit exhaustion remain explicit.
Build40408: source131267/node131264→target131271/node131255; TRACK131275/131276/
131277, nodes131264→131273→131274→131255. Length600.013514,rise6,grades0.005→0.015,
radius120/max_grade0.04. Fresh readback/independent inspection and native TRAIN
route623.538651 pass. SampledXYerror0.000503309,Zerror0.000001907,joinheightgap0;
wrong-direction and out-of-region briefs rejected without construction.
Initial fixture rejected by old400-unit fit envelope before proposal; expanded finite
fit envelope to1000XY per axis, retaining800length/8pieces/5samples per piece.
Discovery400-unit/16edge limits unchanged; no continuous geometry/train traversal claim.
python tools/quiet_checks.py --suite live_client --label pif-p08-final:51passed,
.local_checks/pif-p08-final_lla66d68/report.json.14unchanged quiet-runner tests reused.
First51-test run had1test-helper error; fixed and retained. Current tested hashes match.
python .local_runs/live_python_interface/p08/check_evidence.py:passed; local receipts,
source/staged hashes and diff reviewed. Result/checks/history/HANDOFF in p08.
P07 reviewed local commitd328782601b8e08386811b512fabda3ab63acaa5. Final P08 commit
and reviewed scope recorded in p08/checkpoint.json; no push. Evidence remains ignored.
Normal save/load only; game paused/non-maximised. Actual usage unavailable.

## P07 native height/grade accepted
Native cubic height/grade support in existing extend/connect/connect-selected; Python
validates explicit vertical constraints, mod retains native XY fit/interpolation.
Build40408: isolated connection131258/131259/131260, exact nodes131248→131256→
131257→131251, rise2/grades0.005→0.015; further extension131265/131266/131267,
nodes131252→131236→131254→131264,rise1/grade0.015→0.005. Radius100,max_grade0.04.
Fresh exact readback/independent inspection and native TRAIN path pass; combined
length240.031993. Five samples/piece, no continuous proof or train traversal claim.
Native strict-grade/out-of-region/no-vertical rejection and legacy fit pass.
Station-side Collision retained/reconciled absent; built-connection callback error
retained/independently reconciled present without replay. Other incidental effects
unknown. Captured-fit callback repair runtime-verified by new extension after load.
Narrow read-only in-session connection reconciliation callables record evidence
before closing Python pending jobs; no automatic resume/rollback or identity across loads.
python tools/quiet_checks.py --suite live_client --label pif-p07-final-client:46passed,
.local_checks/pif-p07-final-client_ruox9syq/report.json.14unchanged runner tests reused.
python .local_runs/live_python_interface/p07/check_evidence.py:passed; local receipts,
tested/staged hashes and diff checked; checks/result/workflow_history/HANDOFF in p07.
Python/tests/native/usage/state/task changed; coordinator policy edits preserved.
Disposable save saved normally; game paused/non-maximised. Actual usage unavailable.
28native requests,6build submissions/5verified builds,2normal loads/2saves;
0process restarts/simulation diagnostics. No unresolved current-session pending job.

P05/P06 accepted; GIT-G03 local endpoint-discovery/selection checkpoint. Its SHA,
reviewed scope and cleanliness are recorded in .local_runs/milestone_git/g03/
checkpoint.json; no remote push.39client acceptance reused after source/environment
hash checks; evidence stays ignored. Coordinator continues native grade work next.
PIF-P03/P04 accepted; GIT-G02 published a9f6e8311c1c08ecdfb0d65b3b110fd5fa262ddf on
codex/initial-implementation, origin https://github.com/ben-cottrell/tpf3-bridge.git.
Prior published revision1080dd457b8564faa52a5f4e20d46afed26f4b89. Git history and
.local_runs/milestone_git/g02/publication.json identify the resulting commit and
verified remote SHA. Evidence/logs/ledgers stay local and ignored; no deletions.
29client/14runner acceptance reused after unchanged-file checks; no game operations.

## P06 selected fit accepted
connect_selected/CLI connect-selected accepts one or two current-session full
discovery records; native snapshots/full incidence revalidated before fitting.
Build40408: source130757/node130371 to fixture131245/node131187; about4degree
forward heading change,3pieces,length110.001569,radius100,grade0,sampledXYerror
0.000492081,endpoint heading error0. Opposite stub end rejected as reverse geometry.
Only20-unit independent fixture built on clear land; fitted connection not built.
P05 rejection f717a2f83000480d8d6bed9c668175fa explicitly reconciled in its original
session: anchor unchanged, intended footprint complete/empty of TRACK. Original
pending/receipt and unknown other effects retained; no replay/rollback claim.
reconcile_rejected_fixture/CLI reconcile-fixture requires that explicit rejection
and fresh observations; changed/truncated/occupied footprint retains block.
One normal load followed reconciliation;12native requests total,1verified fixture
submission,0connection builds/saves/simulation diagnostics. Game paused/non-maximised.
python tools/quiet_checks.py --suite live_client --label pif-p06-client-fixed:39passed,
.local_checks/pif-p06-client-fixed_s1gal9hh/report.json. Earlier39-test run had2
test-helper errors; retained and corrected. Unchanged14quiet-runner tests reused.
python .local_runs/live_python_interface/p06/check_evidence.py:passed; receipts,
tested-file/staging hashes, py_compile/task diff reviewed; checks/result/history/HANDOFF
local in p06. Python/tests/usage/state changed; P05 native source unchanged. No push.
P06 left AGENTS/SPDD EOF blank lines untouched; G03 removes those blank lines only.
Limits: session-scoped refs, compatible constant-grade ends, native forward families;
no unrestricted routing/continuous proof/train traversal. Actual usage unavailable.

## P05 endpoint discovery and fit-only selection
Native discovery demonstrated, build40408. discover(client,brief)/CLI discover accepts
bounded XYZ region/max_edges; native octree + complete getNodeSegments + construction
owner checks. One incident TRACK/unowned node is eligible, not a construction guarantee.
≤16edges,≤256component inspections; callback/incident counts and truncation explicit.
Stable recorded refs valid only in current adapter session; no world identity guarantee.
connect_selected/CLI connect-selected --discovery RESPONSE uses refs, rejects stale/
nonfree candidates natively, and invokes existing connection fitter with execute=false.
Complete query:6TRACK,11candidates,173inspections. Truncated western query found3free
zero-grade ends. Selection reached native fitting but opposing headings returned
unsupported_reverse_geometry; P06 demonstrates a compatible forward selection above.
Fixture fit rejected reverse geometry before build; adjusted fixture produced native
Collision, effects unknown, journal blocked at P05 stop; later P06 reconciliation above.
python tools/quiet_checks.py --suite live_client --label pif-p05-final:36passed,
.local_checks/pif-p05-final_4wb6mie7/report.json. Five focused native cases passed:
one-edge cap still detects two incident edges, native nonfree/stale/invalid rejection,
empty region; unknown mutation preserved. python .local_runs/live_python_interface/
p05/check_evidence.py:passed; receipts/source hashes/staging/py_compile/diff checked.
Detailed checks.json/result.json/workflow_history.json/HANDOFF.md in p05 directory.
10requests,1build submission(0verified),1normal load,0save/simulation diagnostics.
P05 stopped uncommitted; G03 checkpoints P05/P06 locally without publication. P06 adds
compatible selected-fit demonstration and explicit local reconciliation. Usage unavailable.

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
