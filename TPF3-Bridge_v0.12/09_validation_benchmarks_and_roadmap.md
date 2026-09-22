# Validation benchmarks, traceability and implementation roadmap

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Current integration:** v0.6 addendum at the end of this document; earlier sections retain their version-specific status. Current execution evidence is in [25](25_v06_execution_report.md).

Version **0.3.0** · 20 September 2026 · **41 project benchmark definitions; partial offline proof coverage**

These are full-project test definitions. Version 0.2 includes a small, executed offline proof, not the complete engineering engine or game integration. Its unit tests must not be confused with acceptance of the 41 project benchmarks; see section 9 and [13](13_offline_proof_and_results.md). Passing a synthetic fixture proves only the stated model behaviour, not the capacity or compliance of a real station.

## 1. Fixture conventions

Use names such as `synthetic_birmingham_inspired_v1`, never `birmingham_as_built`, unless the stronger evidence gate has actually been met. A fixture freezes the brief, topology, geometry, profiles, service/stock activities, passenger demand, rule/capability versions and random seed.

Numerical inputs in synthetic fixtures must be labelled synthetic. Do not borrow real station names to imply that an invented train length, turnout speed, gradient, headway or demand level is an authentic local value.

Maintain three suites: pure model/geometry tests, mock-adapter protocol tests, and real-game integration/calibration tests. The first two can progress before TPF3 API access is resolved. The third must name the actual tested game and mod versions.

## 2. Benchmark catalogue

<a id="b001"></a>
### B001 — Labels are not independent resources

**Fixture:** A physical platform road has several labels and two alternative berth configurations.

**Required oracle:** Count physical roads and permitted simultaneous berths separately. Renumbering must not create or delete track.

**Requirements:** DAT-001, DAT-002, DAT-003, EVD-004. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b002"></a>
### B002 — Platform zero and non-contiguous numbering

**Fixture:** An existing station receives an added road labelled 0; another fixture skips a number.

**Required oracle:** Do not use maximum label or array index as platform count/identity. Preserve previous snapshot aliases.

**Requirements:** DAT-002, EVD-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b003"></a>
### B003 — Multi-level and pedestrian-only interchange

**Fixture:** Two crossing rail layers share a station complex and a pedestrian bridge.

**Required oracle:** Passengers can use a permitted interchange path, but trains have no cross-layer route without an explicit rail connection.

**Requirements:** DAT-001, DAT-004, PAX-001. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b004"></a>
### B004 — Diamond with no turning connection

**Fixture:** Two tracks cross through a diamond with two defined traversal routes.

**Required oracle:** Reject all invented turning routes. An explicit slip variant may add only its documented route pairs.

**Requirements:** DAT-004, GEO-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b005"></a>
### B005 — Free platform with unusable onward route

**Fixture:** A berth is empty and reachable, but its required departure route is absent or time-blocked.

**Required oracle:** Reject the complete assignment or reschedule within the brief; do not report success after arrival feasibility alone.

**Requirements:** TOP-001, TOP-002, TOP-004, OPS-002. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b006"></a>
### B006 — Non-overlapping drawn routes with incompatible resources

**Fixture:** Two geometric paths require incompatible point states or modelled protection.

**Required oracle:** Reject simultaneous use and return the resource/state witness. Geometry alone must not prove independence.

**Requirements:** TOP-008, OPS-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b007"></a>
### B007 — Tail-clear release

**Fixture:** A long train front clears a crossing while its tail remains inside the relevant resource.

**Required oracle:** Keep the conflicting resource unavailable until the configured release condition holds.

**Requirements:** OPS-004. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b008"></a>
### B008 — Split berth permission and overlap

**Fixture:** Two short trains fit geometrically, but simultaneous occupation is disabled or conflicts with a long-train configuration.

**Required oracle:** Reject unauthorised split occupation and overlapping configurations. Enable it only in a separately declared compatible fixture.

**Requirements:** DAT-003, OPS-007. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b009"></a>
### B009 — Delayed stock cycle and empty-stock movement

**Fixture:** An incoming train supplies a later departure; a servicing/stabling move uses the throat.

**Required oracle:** Respect readiness, movement time and stock identity. No duplicate vehicle, teleportation or instant turnround.

**Requirements:** TOP-005, OPS-005, OPS-006. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b010"></a>
### B010 — Invalid crossover connection

**Fixture:** Individually valid turnouts are joined by an invalid connecting alignment or boundary discontinuity.

**Required oracle:** Reject the assembly and locate the failing geometry; alternative fitting must preserve the complete movement contract.

**Requirements:** GEO-001, GEO-002, GEO-004. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b011"></a>
### B011 — Combined geometry and compressed prefab

**Fixture:** A scaled candidate passes isolated plan checks but fails a declared combined curvature/grade/cant constraint.

**Required oracle:** Revalidation detects the combined failure. Parent-pattern success must not carry through automatically.

**Requirements:** GEO-005, GEO-010. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b012"></a>
### B012 — Swept-envelope collision

**Fixture:** Track centrelines clear an obstacle while the selected vehicle envelope does not; include a coordinate-transform variant.

**Required oracle:** Reject the infringement and identify the geometric region. Transform round-trip error must meet the fixture tolerance.

**Requirements:** GEO-006, DAT-006. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b013"></a>
### B013 — Incomplete grade-separation footprint

**Fixture:** The crossing centre has sufficient separation, but a ramp, transition, structure or reserved passenger volume does not fit.

**Required oracle:** Reject the assembly or return a scoped alternative. A centre-point clearance check is insufficient.

**Requirements:** GEO-008, GEO-009. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b014"></a>
### B014 — Bottleneck shifted to downstream merge

**Fixture:** A crossing is separated but the next merge remains binding under the same service scenario.

**Required oracle:** Report the residual conflict/queue. Do not label the corridor solved from crossing independence alone.

**Requirements:** TOP-006. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b015"></a>
### B015 — Overlength approach holding train

**Fixture:** A train is longer than the usable holding interval and still fouls an upstream resource.

**Required oracle:** Reject the claimed clear holding opportunity and propagate the blocking effect.

**Requirements:** OPS-008. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b016"></a>
### B016 — Queue reaches assessment boundary

**Fixture:** A downstream station disturbance creates a queue beyond the initially modelled station area.

**Required oracle:** Expand the boundary or flag incomplete assessment; report residual queues and externalised delay.

**Requirements:** TOP-007, OPS-009, OPS-011. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b017"></a>
### B017 — Incompatible spare platform group

**Fixture:** A through or system-specific service is offered a spare but incompatible terminal/group berth.

**Required oracle:** Reject the reassignment; separately compare legitimate grouped-throat alternatives against the movement matrix.

**Requirements:** DAT-005, TOP-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b018"></a>
### B018 — Simultaneous passenger arrival pulses

**Fixture:** Several services generate transfers through a constrained bridge/deck/subway.

**Required oracle:** Conserve passenger cohorts and represent walking/queuing time; identify the bottleneck without adding train connectivity.

**Requirements:** PAX-002, PAX-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b019"></a>
### B019 — Accessible route loses a lift

**Fixture:** An accessible transfer depends on a lift that becomes unavailable.

**Required oracle:** Return an accessible alternative or an explicit unavailable transfer; stairs are not silently substituted. Keep the disturbed scenario distinct.

**Requirements:** PAX-004, PAX-008. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b020"></a>
### B020 — Late platform reassignment

**Fixture:** A service changes to a distant platform group shortly before departure in the passenger-enabled model.

**Required oracle:** Apply declared announcement/redirection and boarding effects, or flag them unassessed; no instantaneous passenger relocation.

**Requirements:** PAX-006, PAX-007. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b021"></a>
### B021 — Gross area hides a pinch point

**Fixture:** A large platform contains structures/furniture and a narrow access location.

**Required oracle:** Exclude unusable/reserved space and detect the local constraint. Rail optimisation must preserve required passenger structures.

**Requirements:** PAX-005, GEO-009. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b022"></a>
### B022 — Mixed infrastructure and standard versions

**Fixture:** An importer attempts to combine assets from incompatible stages or rules with missing applicability/issue data.

**Required oracle:** Reject or explicitly resolve the version mix. The resulting snapshot and rule evaluations retain complete lineage.

**Requirements:** DAT-007, EVD-001. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b023"></a>
### B023 — Conflicting platform inventory claims

**Fixture:** Two genuine sources disagree on totals or contain an anomalous label.

**Required oracle:** Create an evidence discrepancy; do not average totals or build extra physical assets from an uncertain label.

**Requirements:** EVD-003, EVD-004. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b024"></a>
### B024 — Unknown UK numerical rule

**Fixture:** The applicable rule has only a verified catalogue record, with no extracted clause/value.

**Required oracle:** Mark the UK check unassessed. A synthetic/game check may still pass under its own explicit profile, without relabelling the result.

**Requirements:** BRF-002, EVD-001, EVD-002. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b025"></a>
### B025 — Unsupported or unprobed engine capability

**Fixture:** A design requires specialwork, route inspection or control that the adapter has not demonstrated.

**Required oracle:** Return not-representable/unknown as appropriate, or a declared alternative. No invented engine function or silent topological change.

**Requirements:** EXE-001, EXE-002. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b026"></a>
### B026 — Stale world or out-of-region edit

**Fixture:** Topology/terrain revisions differ from the approved plan, or a proposed edit escapes its authority boundary.

**Required oracle:** Stop and revalidate/escalate before mutation. A moving-train timestamp alone should not masquerade as a static topology change.

**Requirements:** EXE-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b027"></a>
### B027 — Lost acknowledgement and partial execution

**Fixture:** The game may have performed an operation before the connection times out; rollback support is absent.

**Required oracle:** Reconcile by operation ID and observed state before retry. Preserve a staged recovery/compensation record and avoid duplicate construction.

**Requirements:** EXE-004, EXE-005, EXE-008. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b028"></a>
### B028 — Engine snapping changes realised geometry

**Fixture:** The engine accepts a command but alters segmentation, alignment or connectivity.

**Required oracle:** Map realised entities to canonical IDs, recheck relevant invariants, and reject or repair the changed result locally.

**Requirements:** EXE-006, EXE-007, GEO-010. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b029"></a>
### B029 — Budget exhaustion versus infeasibility

**Fixture:** The local search reaches its configured limit without finding an acceptable candidate.

**Required oracle:** Return search_exhausted with explored scope and useful alternatives, not a global impossibility proof or an unapproved relaxed constraint.

**Requirements:** OPT-004, BRF-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b030"></a>
### B030 — Cache invalidation

**Fixture:** Change one correctness-relevant train, rule, topology, terrain, capability or solver-version input.

**Required oracle:** Invalidate affected results and retain unaffected cached artifacts only when dependency coverage is complete.

**Requirements:** OPT-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b031"></a>
### B031 — Deterministic replay and finite horizon

**Fixture:** Repeat an immutable synthetic run with the same seed; end another run with trains still queued.

**Required oracle:** Reproduce the deterministic trace and disclose unfinished work, warm-up and observation horizon. No artificial success by truncation.

**Requirements:** OPS-010, OPS-011. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b032"></a>
### B032 — High-level versus primitive workflow usage

**Fixture:** Run matched accepted-design tasks through primitive commands and the high-level planner.

**Required oracle:** Measure model interactions and available usage data while retaining full local traces. Do not infer plan credits from wall-clock time or token counts alone.

**Requirements:** OBS-001, OBS-004, OBS-005. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b033"></a>
### B033 — Construction-stage service continuity

**Fixture:** A baseline-to-target remodelling has several temporary infrastructure states.

**Required oracle:** Validate each required stage and its passenger/rail operation; do not mix stages or assume an atomic world rebuild.

**Requirements:** DAT-007, EXE-004, EXE-008. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b034"></a>
### B034 — Missing passenger/operation telemetry

**Fixture:** Boarding parameters or observed game-flow data are incomplete.

**Required oracle:** Preserve coverage/uncertainty. Calibrated claims are blocked; explicitly synthetic assumptions remain usable for synthetic evaluation.

**Requirements:** DAT-008, PAX-007, OBS-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b035"></a>
### B035 — Nominal success but disturbed failure

**Fixture:** A candidate runs the regular timetable but fails a delay, bunching or access-loss scenario.

**Required oracle:** Report scenario-specific performance and sensitivity instead of calling the nominal pass robust.

**Requirements:** OPT-005, PAX-008. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b036"></a>
### B036 — Controlled or system-specific passenger zone

**Fixture:** A proposed transfer or platform reassignment crosses an ineligible access/operating group.

**Required oracle:** Enforce declared eligibility and passenger-zone constraints without inventing rail connections or instant processing.

**Requirements:** DAT-005, PAX-001. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b037"></a>
### B037 — Track length versus usable boarding length

**Fixture:** A train fits the track but not its boarding interval or stopping envelope.

**Required oracle:** Reject the stopping configuration unless an explicitly supported, permitted alternative exists. Use the correct train class.

**Requirements:** GEO-007, OPS-001. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b038"></a>
### B038 — Civil feasibility is not certification

**Fixture:** Geometry appears feasible but structural, drainage or other applicable detailed evidence is absent.

**Required oracle:** Return the scoped geometry result alongside unassessed civil checks; distinguish proposed, simulated, built and observed status.

**Requirements:** EVD-002, OBS-006. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b039"></a>
### B039 — Game and railway model disagree

**Fixture:** A tested game reservation/routing behaviour differs from the UK-inspired shadow model.

**Required oracle:** Preserve separate assessments, identify the mismatch and calibrate only the appropriate model using measured evidence.

**Requirements:** OPS-012, OBS-003. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b040"></a>
### B040 — Feasibility, family diversity and decision packet

**Fixture:** Search several allowed topology families; include attractive infeasible and feasible trade-off candidates.

**Required oracle:** Reject hard failures before scoring and return a small meaningful alternative set with bottleneck witnesses and trace references.

**Requirements:** OPT-001, OPT-002, OPT-006, OBS-002. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

<a id="b041"></a>
### B041 — Brief round-trip and fidelity labels

**Fixture:** Serialise/restore explicit site, service, authority and mode fields; export a synthetic reference-inspired result.

**Required oracle:** Preserve the brief exactly and label every result/fixture with its actual synthetic or reconstruction fidelity.

**Requirements:** BRF-001, BRF-004, EVD-005. **Status:** full-project acceptance pending; see section 9 for any narrower executed coverage.

## 3. Requirement-to-benchmark traceability

This table establishes planned coverage, not passing results. The test implementation must preserve each requirement's full acceptance scope.

| Requirement | Planned benchmarks |
|---|---|
| BRF-001 | [B041](#b041) |
| BRF-002 | [B024](#b024) |
| BRF-003 | [B029](#b029) |
| BRF-004 | [B041](#b041) |
| DAT-001 | [B001](#b001), [B003](#b003) |
| DAT-002 | [B001](#b001), [B002](#b002) |
| DAT-003 | [B001](#b001), [B008](#b008) |
| DAT-004 | [B003](#b003), [B004](#b004) |
| DAT-005 | [B017](#b017), [B036](#b036) |
| DAT-006 | [B012](#b012) |
| DAT-007 | [B022](#b022), [B033](#b033) |
| DAT-008 | [B034](#b034) |
| TOP-001 | [B005](#b005) |
| TOP-002 | [B005](#b005) |
| TOP-003 | [B017](#b017) |
| TOP-004 | [B005](#b005) |
| TOP-005 | [B009](#b009) |
| TOP-006 | [B014](#b014) |
| TOP-007 | [B016](#b016) |
| TOP-008 | [B006](#b006) |
| GEO-001 | [B010](#b010) |
| GEO-002 | [B010](#b010) |
| GEO-003 | [B004](#b004) |
| GEO-004 | [B010](#b010) |
| GEO-005 | [B011](#b011) |
| GEO-006 | [B012](#b012) |
| GEO-007 | [B037](#b037) |
| GEO-008 | [B013](#b013) |
| GEO-009 | [B013](#b013), [B021](#b021) |
| GEO-010 | [B011](#b011), [B028](#b028) |
| OPS-001 | [B037](#b037) |
| OPS-002 | [B005](#b005) |
| OPS-003 | [B006](#b006) |
| OPS-004 | [B007](#b007) |
| OPS-005 | [B009](#b009) |
| OPS-006 | [B009](#b009) |
| OPS-007 | [B008](#b008) |
| OPS-008 | [B015](#b015) |
| OPS-009 | [B016](#b016) |
| OPS-010 | [B031](#b031) |
| OPS-011 | [B016](#b016), [B031](#b031) |
| OPS-012 | [B039](#b039) |
| PAX-001 | [B003](#b003), [B036](#b036) |
| PAX-002 | [B018](#b018) |
| PAX-003 | [B018](#b018) |
| PAX-004 | [B019](#b019) |
| PAX-005 | [B021](#b021) |
| PAX-006 | [B020](#b020) |
| PAX-007 | [B020](#b020), [B034](#b034) |
| PAX-008 | [B019](#b019), [B035](#b035) |
| OPT-001 | [B040](#b040) |
| OPT-002 | [B040](#b040) |
| OPT-003 | [B030](#b030) |
| OPT-004 | [B029](#b029) |
| OPT-005 | [B035](#b035) |
| OPT-006 | [B040](#b040) |
| EXE-001 | [B025](#b025) |
| EXE-002 | [B025](#b025) |
| EXE-003 | [B026](#b026) |
| EXE-004 | [B027](#b027), [B033](#b033) |
| EXE-005 | [B027](#b027) |
| EXE-006 | [B028](#b028) |
| EXE-007 | [B028](#b028) |
| EXE-008 | [B027](#b027), [B033](#b033) |
| OBS-001 | [B032](#b032) |
| OBS-002 | [B040](#b040) |
| OBS-003 | [B034](#b034), [B039](#b039) |
| OBS-004 | [B032](#b032) |
| OBS-005 | [B032](#b032) |
| OBS-006 | [B038](#b038) |
| EVD-001 | [B022](#b022), [B024](#b024) |
| EVD-002 | [B024](#b024), [B038](#b038) |
| EVD-003 | [B002](#b002), [B023](#b023) |
| EVD-004 | [B001](#b001), [B023](#b023) |
| EVD-005 | [B041](#b041) |

## 4. Scenario design and comparison discipline

Compare candidates under the same boundary, demand, train profiles and observation horizon. When a design changes passenger routing, regenerate the relevant passenger paths rather than reusing the old distribution blindly.

Include regular service, late arrivals, dwell variation, bunched trains, long-train substitution, unavailable platform/throat resources, empty-stock moves, passenger surges and lost accessible links where applicable. Perturbations must have declared origins and seeds. Do not tune every candidate to a different favourable scenario.

Report completed required activities, cancelled/rejected activities, train and passenger delay, missed transfers, residual queues, key resource occupation, recovery behaviour, footprint and unassessed checks. High occupation is neither automatically failure nor proof of spare capacity; interpretation depends on resource structure and service mix.

Use a warm-up and observation/flush policy appropriate to the fixture. A finite-horizon test must disclose unresolved queues rather than make them disappear. For periodic tests, distinguish steady-state evidence from a single short sequence that happened to fit.

## 5. Model validation versus model verification

Verification checks whether the code follows its defined model: conservation, legal routes, release logic, deterministic replay and correct geometry. Validation checks whether the model usefully represents the observed game or reference behaviour within a declared scope.

The passenger-capacity guidance's model-assessment approach is a useful reference, but this bridge has not implemented its complete requirements or demonstrated an equivalent validated model. [S040](10_source_register.md#s040)

For game calibration, compare route traversal, dwell, reservation/release and queue behaviour where observable. Use error distributions and coverage, not a single “accurate” label. Unobservable behaviours remain assumptions. A fit on one small station is not validation for a dense multi-junction passenger complex.

## 6. Implementation roadmap

| Milestone | Deliverable | Exit gate |
|---|---|---|
| M0 — Contracts and evidence | Typed records, stable IDs, source/claim ledger, versioning, synthetic fixtures | B001–B003, B022–B024 and B041 implemented with explicit fidelity labels |
| M1 — Railway operating core | Legal routes, temporal resources, berths, train/stock activities, queues and replay | B004–B009, B015–B017, B031 and nominal portions of B035 pass |
| M2 — Geometry and pattern composition | Alignment kernel, component contracts, crossover/throat fitting, swept envelopes and civil reservations | B010–B014 and B037–B038 pass under declared synthetic profiles |
| M3 — Passenger station model | Entry/exit/transfer demand, queue graph, accessible routing, platform-change effects | B018–B021, B034 and B036 pass; assumptions clearly marked |
| M4 — Local design orchestration | Family search, bounded repair, caches, decision packets and usage instrumentation | B029–B030, B032 and B040 pass; no routine Astra-per-segment loops |
| M5 — TPF3 adapter probe and integration | Versioned capability manifest, staged operations, reconciliation, realised checks | B025–B028 and B039 on a real named game/mod build; unsupported capabilities remain explicit |
| M6 — Technical reference promotion | Dated detailed topology/geometry for selected cases, lawful evidence imports and calibrated fixtures | Selected features reach R3/R4; no package-wide replica claim |
| M7 — Large-complex robustness | Integrated station areas, construction stages and disturbed passenger/rail ensembles | B016, B033, B035 and relevant composed-pattern tests pass at the chosen scale |

Milestones are dependency-oriented, not calendar estimates. Evidence acquisition and adapter probing should begin in parallel with the pure Python model rather than block all development. Do not require advanced coupling, detailed pedestrian telemetry or atomic rollback to deliver a useful initial bridge; declare reduced support where necessary.

## 7. Performance/usage measurement plan

For each fixture, record candidate families considered, geometric evaluations, local repair attempts, simulated events, memory, local runtime, game calls, model calls and observation volume. Record p50/p95 runtime only after repeated measured runs on a named machine/configuration.

Set local runtime and game-attempt budgets in the brief. A timeout is an explicit outcome. No universal interactive-time or percentage-credit-saving claim is made before measurement.

The principal product metric is accepted required functionality per unit of Astra involvement, with failure/repair rates and engineering validity held visible. A workflow that saves model calls by silently dropping constraints fails the product objective.

## 8. Release acceptance record

Every release should publish: implemented requirement IDs; tests run and results; rule/source versions; synthetic versus reference-calibrated coverage; game/mod versions; capability probes; known unsupported behaviours; and usage measurements with their method.

The v0.1 baseline contained **75 requirements, 32 proposed pattern families and 41 project benchmarks**. Version 0.2 retains those stable IDs and adds the separately scoped proof and acceptance record below. No full-engine or game-integration milestone is declared complete.

## 9. Version 0.2 executed coverage

The standalone proof has an actual test log and machine-readable [test report](proof/results/test_report.json). Its test-method count is not the number of project requirements or full benchmarks completed.

### 9.1 Traceability to the existing benchmark intentions

| Project benchmarks | Narrow behaviours exercised | Important remaining gap |
|---|---|---|
| B001–B002 | Relabelling does not change physical IDs or platform count; duplicate IDs rejected | No production alias/history store or split-configuration model |
| B003–B004 | Explicit rail traversal allowlists; no connection inferred from pedestrian links or a crossing | No imported station graph, full crossing geometry or general route enumerator |
| B005–B007 | Complete entry/exit eligibility, state/resource conflicts, constant-speed tail-clear surrogate and delayed-departure berth retention | No actual interlocking, geometry-derived resource compiler or microscopic motion |
| B009 | Stock predecessor continuity, fork/cycle rejection, explicit external cycle and empty-stock occupation | External movement geometry, formation changes and substitution unsupported |
| B011 | Compression rechecks one analytic plain-line primitive | Combined cant/grade/curvature and full component assemblies unimplemented |
| B017 | Bank eligibility and closure retain rejected demand explicitly | Operating-system and detailed train compatibility incomplete |
| B024 | Missing applicability/input and unresolved national interface remain unassessed | Full UK rule profile and exception workflow incomplete |
| B029 | Computation and entry-wait budgets have distinct non-proof outcomes | Full geometry/authority/repair controller incomplete |
| B031 | Deterministic scheduling, reproducible trace and finite-horizon residual reporting | Spatial queues, steady-state assessment and warm-up/flush calibration absent |
| B035 | Normal, bunched, long-train, late-stock and closure scenarios compared separately | No calibrated disturbances or passenger model |
| B037 | Boarding length plus explicit margins governs train fit | Detailed stopping envelopes, doors and selective-door policy absent |
| B040–B041 | Three predefined families, strict synthetic fixture schema, compact result reference | No general topology search, full DesignBrief round-trip or Pareto decision generator |

No complete M0/M1/M2 milestone is asserted by this table. The proof deliberately covers a thin portion of several milestones rather than implementing one full production subsystem.

### 9.2 Executed scenarios

Seven JSON fixtures are retained in [proof/fixtures](proof/README.md): nominal, bunched arrivals, one platform closed, all A-bank platforms closed, long-train substitutions, a delayed stock cycle and a shortened reporting horizon. Each is run against the same three family definitions. All preserve 24 required visits; the closure scenario changes availability, not demand.

The generated [comparison table](proof/results/comparison.md) separates scheduled, completed, unscheduled and residual counts. Its delay totals are not comparable without those counts. No cancelled visit is silently removed to improve a result.

### 9.3 Independent checks and regression limits

The test suite independently inspects resulting claims, train/platform fit, readiness, closure eligibility, predecessor timing and demand accounting. Small event-calendar searches are compared with a brute-force integer-time oracle. Geometry tests check analytic endpoints and sample the independently derived curvature bound.

These checks establish properties of the authored model. They do not validate the resource-template assumptions against an observed station or game. Exact scenario numbers are reproducible regression outputs, not externally calibrated passenger-rail capacity estimates.

### 9.4 Release gates still outstanding

Full component geometry, split berths, swept vehicle envelopes, physical approach queues, passenger circulation, rule-profile completion, persistent cache invalidation, autonomous repair and all game integration remain open. S055 supplies a historical component relationship, not permission to mark the whole Waterloo case R3/R4.

The next implementation gate should generate and validate a complete crossover from actual or explicitly synthetic component geometry, then compile its route resources and replace one hand-authored proof template. Keep existing operation tests running while making that substitution.

## 10. Version 0.3 executed coverage and remaining benchmark scope

The current suite runs 176 test methods: 83 legacy and 93 new. The 41 benchmark IDs above remain broad project acceptance definitions, not 41 completed integration tests. [16](16_v03_execution_report.md) records the actual test evidence.

| Existing benchmark family | Behaviour now exercised | Still outside acceptance |
|---|---|---|
| B004 — Illegal crossing connectivity | Explicit component traversals; no invented diagonal or coordinate-based rail connection | Complete generated diamond/slip catalogue and real route permissions |
| B005–B007 — Complete movement, conflict and tail clearance | Geometry-derived routes/resources, missing exits, state/space distinction, conservative length-aware whole-leg clearance | Real control tables, signal protection, sectional release and microscopic motion |
| B010–B011 — Complete assembly and compression | Full synthetic crossover joins, eased fan paths, curvature-bound checking and changed-geometry revalidation | UK turnout dimensions, cant/vertical interaction and complete station envelopes |
| B012 — Envelope collision | Continuous planar corridor-proxy conflicts, including interior curved proximity | Full kinematic swept envelopes and complete 3D structures |
| B017 — Incompatible spare berth | Group eligibility, closures, train length, both routes and held storage | Multi-system large-station recovery with measured route eligibility |
| B024 — Unknown numerical rule | Legacy missing-evidence behaviour retained; new corridor/component values explicitly synthetic | Complete numerical UK engineering profile |
| B029–B030 — Bounded work/provenance | Finite fitting budgets and geometry/profile-dependent hashes | General repair authority controller and persistent dependency-aware cache |
| B031–B032 — Replay/compact evidence | Repeatable compiled scenario results, local claims and compact packet | Production event delivery and measured Astra usage experiment |
| B037–B038 — Fit and status integrity | Scalar platform fit, rear-marker stop semantics and explicit assessment domains | Full platform/vehicle interface and all engineering checks |

The unchanged legacy runner is re-executed separately. Release validation compares its scenario outputs with the v0.2 archive. A change in test count is not permitted to hide a regression in the earlier resource-template results.

### Revised immediate gate

M2 now has executed synthetic planar crossover/fan subassemblies and a geometry-to-resource compiler. M1 has additional compiled-route scenarios, but neither milestone is wholly complete. The next integration target is an explicit arrival/departure bank, followed by sectional occupation with validated stopping semantics. M5 remains an untested game adapter; no offline pass changes that status.

## Version 0.4 implementation coverage

The 41 broad project benchmarks remain unchanged. The current suite contains 284 executed methods, including 108 new methods; these do not equal 284 certified railway requirements. [Current execution report](19_v04_execution_report.md)

The new tests exercise scoped behaviours related to B004–B009 (legal/complete movements, state compatibility, tail release, berths and stock), B017 (eligibility), B022–B024 (versioned evidence and unknown numerical rules), B031/B041 (replay and fidelity), and selected geometry checks. Passenger crowding, full civil/gauging and real-game benchmark gates are not completed by those tests.

New regression oracles include an independent speed integral, analytic motion identities, physical footprint/resource-set equality, pairwise reservation inspection, finite-horizon state conservation, immutable baseline geometry metadata and strict numerical-profile admission. The sourced nominal-spacing versus generic-corridor case must remain as a negative promotion test.

Next dependency gate: authentic component admission and a representative vehicle envelope, followed by multi-bank composition and actual independent/recovery movement checks. The two external leads still feed one common fan. Continue numerical source acquisition in parallel, rather than treating the synthetic catalogue as the final UK library.

## Version 0.5 implementation coverage

The recorded suite now has **414 passing methods**, including 130 new methods; see [22](22_v05_execution_report.md). This is narrower than completion of the original broad benchmark contracts.

| Existing benchmark | New exercised behaviour | Remaining full scope |
|---|---|---|
| B010 — Invalid crossover connection | Imported route endpoints, common-toe tangent and synthetic placement/compiler path | Authentic component families and complete crossover compatibility |
| B012 — Swept-envelope collision | Rigid two-pivot body, curved inthrow, polygon contact, continuous-polyline pose bound and geometry-linked route audit | Full dynamic/3D gauging and certified parent-curve/body approximation |
| B022 — Mixed versions | Exact reviewed-record hashes; origin/issue retention; changed records lose prior admission | Full historic validity and standards applicability resolution |
| B024 — Unknown UK rule | Missing bogie/outline/method fields remain unresolved; source speed record does not invent executable applicability | Complete imported national gauge/profile rules |
| B037 — Train compatibility | Published full-unit length enters platform fit and longitudinal tail-clear calculation | Exact formation/door/coupler geometry and calibrated performance |
| B038 — Honest geometry status | Analytic, sampled, bounded-polyline and whole-UK outcomes remain distinct | Engine construction and measured observation |

The new suite also checks millimetre/metre round trips, all-relative-phase route pairs, duplicate JSON keys, unsupported 3D fields, bounded pose/search work, arbitrary-path rejection and deterministic replay. Tests of the review gate use authored records; they are not claims of newly verified external drawings.

New release comparisons include eighteen base analytic spacing cases, a separate synthetic long-body counterexample, three crossover route pairs, two refinement runs, a curved-obstacle case, one representative-body bank scan, two full-unit-length trials and two component import outcomes. These are different kinds of evidence and are not summed into an inflated trains-per-hour or railway-capacity metric.

The next composition gate is still required: a full bank arrangement must meet its site, service and movement contracts. An individually clear component or a source-backed width does not complete a station.

## Version 0.6 implementation coverage

The suite now executes **500 test methods**, including 86 new station methods. Three family instances and twelve scenarios produce 36 operating comparisons with independent checks. These counts are not equivalent to completing all 75 requirements or 41 broad benchmark contracts. [25](25_v06_execution_report.md)

| Existing benchmark area | Additional executed evidence | Remaining boundary |
|---|---|---|
| B005/B017: complete opportunity and eligibility | Both recovery legs, bank-specific routes, missing-exit rejection, heterogeneous train fit | General route optimisation and actual local permissions |
| B006/B007: resources and release | Combined-network compilation, 64 normal route-pair checks, matched sections, state/tail/storage tests | Real interlocking protection, track circuits and calibrated release |
| B009: stock | Multi-group scheduler retains predecessor, formation and external-cycle constraints | Detailed external stock path, coupling/splitting |
| B012/B013/B021: fit and reserved space | Whole-candidate planar footprint and reserved-concourse checks; per-route static body audit | Full 3D vehicle/structure/platform and passenger-capacity assessment |
| B016: finite boundary | Required, completed, rejected and residual visits retained; original physical site failure exposed | Spatial approach queues and downstream spillback |
| B024/B025: unknown rules/capabilities | Candidate-bound partial numerical checks and blocked strict/game gates | Authentic component, full gauge and live TPF3 evidence |
| B040/B041: comparison and fidelity | Completion-first packets, scenario-hash guard, explicit changed brief fields and larger-site study label | Full multiobjective topology/geometry optimisation |

The important next gate is now the failed site/recovery contract: search a more compact approach/fan arrangement without dropping required movements, renaming unsupported components or silently enlarging the boundary. Evidence acquisition remains parallel, especially authentic pointwork and complete vehicle/platform interfaces.

## Version 0.7 — Additional exercised behaviours

The current suite has **592 executed test methods**, including 92 new ones, and 64 full-study comparisons. [28](28_v07_execution_report.md) distinguishes implementation verification from physical validation. The original 41 broad benchmarks retain their identifiers and wider scope.

| Existing benchmark | Additional evidence | Remaining scope |
|---|---|---|
| B004: diamond topology | Two explicit crossing paths; no turning connection; missing declarations rejected | Authentic crossing/slip hardware and game representation |
| B005/B017: complete opportunities | Inner-road recovery, no all-to-all inference, receiving-berth and long-train failures | General alternative-route allocation and local operating permission |
| B006/B007: resource compatibility | Named diamond exclusion plus preserved track/control/proximity locks and tail release | Actual protection and detection/release boundaries |
| B010/B011: fitting | Immutable imported component; new authored fan fit; original radius target retained | Authentic component and full dynamic combined-geometry rules |
| B013/B021: footprint/reservations | Exact original approaches, platform intervals, terminal markers and concourse reservation | Full padded vehicle/civil/interface site and passenger capacity |
| B029/B040: search and decision | Budget/grid distinction; six passing fits of 27; original-plan/completion-first ranking | Global geometry/topology optimisation and real data calibration |
| B038/B041: fidelity | Plan subset pass alongside blocked strict UK/full-design/game gates | Constructed and observed engine behaviour |

The previous original-plan failure is resolved for the new family only. Fan-failure recovery and 300 m A-to-B recovery still fail. Do not close those broader requirements based on the normal and short-unit bank-closure results.


## Version 0.8 — Additional executed coverage

The suite now has **710 methods**, including 118 new platform-interface tests. These deepen portions of B012/B021/B024/B029/B037/B038 and the evidence/identity checks; they do not complete those broad benchmark contracts in their entirety.

New positive/negative cases distinguish a rail-running-edge datum from the track centre; design height from a linked build/maintenance allowance; permissible speed from simulated speed; gross platform width from a local obstruction; and a scalar component reference from a complete dimensional import.

The integrated regression removes B1 from a declared planning scenario because of a failed local interface check, retains all required train demand, then restores the same recovery cycle through a same-size authorised facility move. A 4.2 m footprint cannot be made feasible by moving it laterally within the fixed 9.09 m island. Unknown rules and zero work budgets remain separate outcomes. Full suite/fixture evidence is in [31](31_v08_execution_report.md).


## Version 0.9 — Corridor and adapter validation; revised priorities

**810 methods ran successfully**, including 100 new tests. Counts verify software behaviour, not 810 engineering rules or completion of the broader 41 benchmark definitions. Full detail is in [34](34_v09_execution_and_handoff.md).

| Existing benchmark area | New executed evidence | Remaining boundary |
|---|---|---|
| B010/B011 geometry | C2 spans, normal-offset derivatives, both-track geometric bounds, changed-speed/shorter-route rejection | General headings, clothoids/cant, authentic switches and game snapping |
| B012/B013 fit | Source-scoped spacing, protected-land witnesses, full-ramp grade/crossing-budget checks | Full 3D vehicle/structure gauging, exact terrain/support fit |
| B014 downstream consequence | Open branch and absent merge explicitly prevent a complete-junction claim | Connected branch and corridor operating scenario |
| B015 holding | Formation length plus named margins, explicit shortfall, separate braking-distance screen | Signal overlap, braking profile, physical queue and usable game holding section |
| B025–B028 execution | Unknown/unsupported capability refusal, stale revisions, content identity, lost acknowledgement, geometry read-back and partial failure | Actual named game/mod build; engine rollback not assumed |
| B029/B040 search | Fixed 12-candidate scope, budget status, rejected candidates retained, seven local nondominated options and two displayed alternatives | Global optimisation, robust game capacity and automatic user preference resolution |
| B038/B041 fidelity | Synthetic terrain, published nominal reference, open-port crossing cell and mock-only construction statuses | Real game construction and observation |

**Revised sequence:** freeze station internals; develop corridor fitting and practical game contracts; complete branch/merge connectivity; probe actual terrain/assets/construction/routing; calibrate local operating screens; then broaden structures and network design. Crowd/facility detail is no longer the default next milestone.

Historical full-study outputs are preserved and compared with v0.8, while the full unit/integration suite and the new corridor demonstration were executed for this release. Do not describe every old full runner as freshly rerun merely because its output files remain in the package.

## v0.10 coverage addendum — connected branch and semantic construction

The current execution record is [37](37_v010_execution_and_handoff.md). **917 methods passed; 107 are new.** This does not complete the 41 broad benchmark contracts.

The connected-junction tests exercise a narrower form of B014: an acceptable separated crossing still has a binding downstream merge/blocked exit. B013 receives complete-ramp fit and crossing-band checks, but full civil/vehicle envelopes remain unassessed. B004's no-invented-turn principle is checked at a declared flat crossing without claiming authentic diamond hardware.

Holding tests distinguish an overlength tail fouling the crossing from a train that clears physically but lacks the specified margins. This supports B015's intended failure detection only at a static geometric level; the train is not yet simulated stopping there.

Capability, uncertain-acknowledgement and realised-result tests strengthen the mock portions of B025–B028. They include corrupted component state and changed current geometry, not only displaced vertices. The real-game portions remain unexecuted.

All comparisons use common scenario identities and preserve required/scheduled/completed/unscheduled/residual counts. The new interval checker uses a separate event sweep but shares declared physical timing assumptions. Those assumptions require empirical validation before capacity or game-performance claims.


## v0.11 — Terrain-placement acceptance evidence

The completed suite contains 985 methods, including 68 new methods. New coverage checks immutable external ports and components, inherited main-line targets, river boundaries, protected-land witnesses, conservative planning reservations, quantity accounting/refinement, stale evidence and snapshot changes during semantic mock execution. See [40](40_v011_execution_and_handoff.md) for actual test IDs and scope.

This supplies narrower implementation evidence for corridor composition, full-assessment boundaries, version binding, constraint-preserving search and partial failure. It does not complete every original requirement or benchmark. Grade-sensitive braking/restart, internal holding, spatial queues, actual structure assets and live engine probes remain open.
