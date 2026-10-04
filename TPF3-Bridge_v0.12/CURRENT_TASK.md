# PIF-P43 — COMPLETE

Specified four Wickham leads and two crossovers built and freshly verified.
323 application tests passed; new distinct game checkpoint saved. See STATE.md
and .local_runs/live_python_interface/p43/HANDOFF.md. Hand back to Astra; no
additional topology work under this task. Original coordinator card follows.

# PIF-P43 — rotated station-lead continuation fit failure

P42 3b1de6256491da91b604f7d1be36cebf3ecadfad accepted. Astra directly resumed station connection operation03 and encountered a reproducible fit-stage gap. Implement only the needed general bridge correction and specified first two connections; Astra retains topology ownership. Prefer6.1SolMedium again after temporary6Solcapacityfallback.

## Actual state and failure
Current Wickham Station sessionpif_1791129181_128730030, build40408.16userexternalleads observed freshly by operation03/prepare.py. Four selectedzero-basedports8,9,12,13 share grade-0.002819963,height1.099998474. Headingd=[0.9936118122274933,-0.11285196764787335]. Native site150m ahead is empty of reported infrastructure; sampledground0.6416..2.3969,ordinarycut/fillappropriate. No arbitrary elevateddatum.
Astra invoked existing live.extend onport8:30m straight continuation at observed heading, exact source104586/node104585, sameendheight1.099998474,endgrade0,maxgrade.01,radius150. Native fit rejected before build with realised_sampled_radius_below_limit:0.0046294592151691<150 at pif_native.lua geometry_bounds line82. jobcb4d04fca67b4bca81515b2c21fbb05c,game_constructedfalse,stagefit. No extensions/crossovers built byoperation03. Evidence operation03/extend_8_30.json and referenced workflow,response/rawrecords. No same-proposal mutation retry required.
Hypothesis only: rotated nearlystraight fit yields short degenerate native fragment / conversion precision artefact. Establish actual native controls/geometry and failure before choosing correction; could be another cause. Existing tiny-part filtering atnativefit around730 is relevant,not proven diagnosis.

## Exact intended physical design
All geometry/evidence/scripts in .local_runs/design/terminal_16_8_12_8/operation03.
plan.json contains16freshport snapshots,direction/height, selectedrails8,9,12,13 and firsttwo crossovers neareststation in full30crossover/9stage candidate. Indices are physical lead order, NOT claimed stationplatformnumbers (native Terminal.vehicleEdges empty).
For eachselectedrail: nativecontinuation t0->30 transitions observedgrade to0 atsameheight; thenstraightlevel t30->150. Position(t)=observedportXY+d*t. Hardradius150,maxgrade.01 for transition,levelpointworkmaxgrade1e-6. Existingstationanduserleads preserved,functionalattachments exact.
Firstcrossover outward: rail8 at t50 ->rail9 at t120. Second:rail13 at t50 ->rail12 at t120. Both5mspacing,70mlongitudinal,hardradius150/nativefit187.5,existingexplicit single_cubic_level representation only if current0.1combinederrorbound and nativeengineering pass. This reverses the inward graph's finalstageedges[9,8]and[12,13], preserving fulltopology. Do not change stage,spacing,heights,radius or footprint to obtain success; report concretegeometrylimitation if laternativebuildfails. No parameter sweep/rebuild ofoldtestcell.

## Repair and acceptance
Inspect actualnativefit and lowering diagnostics read-only first; add useful failure evidence if missing. Fix reusable straight/nearstraight rotated fitting/representation handling without hard-radius bypass,globaltolerancerelaxation,Pythonreplacementfitter or acceptinginvalidcubic. Preserve nativeoriginalgeometry, exactendpoints/headings, gradeconstraints and honest sampledlimits. Tests should target actualfailure and retain rejection of materiallycurved out-of-boundgeometry, rotatedheading, gradecontinuation, unchangedaxes behaviour as affected. ReuseP42tests/evidence whenunchanged.
Freshbindstation/currentjournal beforecontinuing. Complete specifiedfourleadextensions andtwo crossovers throughpublicbridge if valid. Scriptbuild_rails.py uses no-replay outputguards; do NOT blindlyrerun it or deletefailurehistory. Use new namedattemptrecords, reusealreadycompletedactions ifany, stopuncertainmutation and observe/reconcile. Nativefitfailure game_constructedfalse is not a tool denial.
Freshreadback exactfourstation-leadattachments; eachpair'sthroughroutes and crossconnectionbothdirections; engineering and ground-relativeheight. No16terminal/fullthroat/trainproofclaim. Nativeplatformassociation staysunknown; do not letthat block externalleadwork.

Normal adapterstaging/save-load ofCURRENTWickham checkpoint permitted if needed, nooldP38load orhostrestart. Newchangesnonebuilt so current savedWickham is valid; confirmactualstate beforeload. Existingstation/ownedtracks must remainfunctionallyintact. No stationexpansion,trains,signalling,services/deps. Directhuman disposablemapconstruction/terrain and permanentcompletionpayload authority apply;externalreviewbinding.
Affectedtests/docs/STATE,localmilestonecommit,no push. Evidence/HANDOFFp43. Send compactcompletion to coordinator01a0f987-8917-7f31-84c3-838acacc9e04 and return controltoAstra. If70mcrossovervalidityfails afterextensionrepair, preserve exactoutcome/reconciliation ratherthan inventalternativegeometry.
