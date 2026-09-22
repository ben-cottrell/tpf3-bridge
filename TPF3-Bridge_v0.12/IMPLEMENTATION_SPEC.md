# TPF3-Bridge — current implementation specification

**Version 0.12.0 · 21 September 2026**  
**Authority:** current product scope and implementation priorities. Earlier numbered chapters are evidence, algorithm notes and historical experiments; this document overrides their next-step recommendations where they conflict.  
**Delivery status:** implementation contract, source-to-module handoff and checked message examples. Not a production orchestrator, MCP server, Lua mod or verified TPF3 integration.

## 1. Product decision

Build a practical British-railway construction assistant for Transport Fever 3 in a sandbox world. Astra chooses the railway's purpose, character, constraints and significant alternatives. Python resolves dimensions, searches layouts, fits geometry, checks connections, selects supported game representations, coordinates construction, verifies the result and repairs routine failures within authority.

The product is not a separately calibrated national railway simulator. Further platform furniture/access simulation, detailed traction and adhesion, gradient-sensitive braking/restart, microscopic crowd movement and full real-world certification are **deferred optional modules**. They are not hidden prerequisites for a normal build. Grade limits, smooth vertical profiles, train fit and sufficient waiting length remain core geometric checks.

A model upgrade is justified only when a named construction decision depends on it and a test demonstrates useful discrimination or fewer failed game attempts. Do not add complexity merely because a historical chapter listed an unresolved physical effect.

**Primary release outcome:** one authorised construction task completed and verified in the game, with its explicit constraints intact and without Astra managing a segment-by-segment retry loop. Unit-test counts support this outcome; they do not substitute for it.

## 2. Reading and precedence

Read this document first, then [the game adapter contract](GAME_ADAPTER_CONTRACT.md), then [agent API and implementation handoff](AGENT_API_AND_HANDOFF.md). The [release record](V012_RELEASE_NOTES.md) states what was actually checked. Machine-readable counterparts are under [contracts](contracts/README.md) and [implementation](implementation/README.md).

An earlier statement that construction authority is always false describes that particular offline proof. It is not a permanent prohibition on the intended application. Production construction becomes possible through a trusted user-authorisation path and demonstrated adapter capabilities. Conversely, a past successful mock does not grant that authority.

An old `SHALL` concerning a detailed passenger model remains a requirement **when that optional feature is selected**, not automatically a requirement of the first construction release. The original 75 requirement IDs are preserved and classified in [the requirement disposition](implementation/requirement_disposition.json). No historical result is relabelled as a production result.

## 3. First supported product boundary

The first live delivery is **create-only plain railway between existing boundary ports on a disposable sandbox save**, followed by a simple junction and then a structure-bearing route. It does not begin with a large-scale remake of an operating city or with a fully automated demolition/rebuild.

| Feature | First production treatment | Existing material / actual gap |
|---|---|---|
| Brief and authority | Immutable typed brief, explicit edit region, preserved assets and material-change rules | Proposed contracts; no running domain service yet |
| Existing railway input | Read a bounded snapshot; preserve save identity, ports and legal connections | Live topology/terrain import not demonstrated |
| Plain-line connection | Supported tangent/curve joins, both directional tracks and actual endpoint read-back | Curve kernels exist; arbitrary boundary fitting remains incomplete |
| British appearance | Reference-inspired profiles with sourced numbers and visible approximations | Existing numerical/evidence records; authentic pointwork still partial |
| Passenger stations | Reuse platform length/roles, usable connections and game access | Freeze internals at v0.8; game station mapping unresolved |
| Junctions | Select a functional pattern, preserve route semantics and remaining merges | Restricted offline branch/scissors families exist |
| Structures | Select available asset and solve complete approaches | Reservations exist; actual native asset selection unimplemented |
| Operation checks | Connectivity, train length, waiting room, obvious reservation conflicts | Lightweight models retained; in-game behaviour uncalibrated |
| Build execution | Staged writes, effect ledger, read-back and bounded local repair | Fault-injected mock controllers exist; live binding absent |
| Astra interaction | Small intent-oriented surface; detailed data retained locally | Eight proposed descriptors; no server or host connection |
| Existing-world replacement | Separately authorised asset whitelist and staged cutover | Deferred until create-only path and save/load handling pass |

Nothing in this table claims that the game exposes a particular native method. The public game description establishes path-based signalling, configurable alternative terminals and expanded scripting, not a tested construction API. [S001](10_source_register.md#s001)

## 4. Decisions owned by each layer

### Astra

Astra selects the service role, endpoints, preferred railway era/character, target speeds, maximum acceptable gradients, major junction family when alternatives are material, land-use priorities and approved compromises. It may authorise a bounded design search and a later build through the user's chosen approval policy.

Astra does not choose every control point, repeatedly fetch full terrain, calculate successive turnout coordinates, poll every optimisation iteration, infer success from an acknowledgement, or silently lower speed to make an invalid curve pass.

### Python domain engine

Python owns canonical asset identity, evidence resolution, profile selection, local geometry, pattern instantiation, search budgets, structure matching, ordinary movement checks, candidate comparison, operation dependency planning, result verification and compact explanations. It also owns the persistent job and effect ledgers.

Python cannot override user protection boundaries, invent missing native abilities, grant its own build approval, or promote approximate geometry into a certified UK design.

### In-game mod

The mod is the authoritative native-data adapter. It obtains data and submits supported operations in the correct game execution context, returning native receipts, actual entities, errors and state. It performs payload validation and enforces the authorised edit envelope again at the game boundary.

The mod should not contain a duplicate of the full geometry optimiser. Some local validation, command queuing and safe native batching are necessary. The exact scripting language, callback/thread model, file/network permissions and native function signatures remain probe decisions, not assumed Lua capabilities.

### Game engine

The game determines its actual construction acceptance, generated junction topology, pathfinding, train motion and passenger network behaviour. Python may predict or detect problems; it must inspect the authoritative result rather than assert that the intended design was realised.

## 5. Minimal deployed architecture

Use three replaceable boundaries:

`Astra-capable host ↔ intent/tool adapter ↔ persistent Python application ↔ native game adapter/mod ↔ TPF3`

The first arrow may use MCP when the actual host supports the chosen transport/version. The second game-facing arrow is a separate private bridge protocol. **MCP is not the game mod protocol.** A local host can launch a stdio MCP process; an HTTP-capable host needs an explicitly reachable, authenticated endpoint. A remote service does not gain access to the user's localhost merely because a server exists there. The host/transport combination must be demonstrated. [S074](10_source_register.md#s074), [S075](10_source_register.md#s075), [S076](10_source_register.md#s076)

Proposed production tree, not a claim that these directories are already implemented:

```text
tpf3_bridge/
  contracts/        # versioned models, request validation, errors
  domain/           # world, ports, components, routes, candidates
  profiles/         # UK/game profiles, rule origins, asset compatibility
  geometry/         # one canonical alignment/component kernel
  planning/         # patterns, corridor search, repair policy
  checking/         # geometry, connectivity, fit, site, lightweight operation
  execution/        # state machine, authorisation, effect ledger, reconciliation
  storage/          # snapshots, results, jobs, caches and retention
  adapters/
    mcp/            # optional host-facing transport only
    mock/           # test backend
    tpf3/           # native mapping and real read-back
  observation/      # bounded changes, bottlenecks, completion evidence
  tests/            # contracts, migrated regressions, adapter acceptance
mod/                # thin native game package, language determined by probes
```

Keep engineering functions callable from a local CLI or test harness without an LLM. A running MCP host should not be required for geometry tests. Conversely, importing a Python module is not sufficient to expose a secure game-control endpoint.

Choose a small persistent store for jobs, authorisations, effect receipts and snapshot indices. Geometry blobs and full traces may remain content-addressed files beneath a controlled application directory. Start with one game-writer process per loaded save; introduce distributed jobs only after a demonstrated need.

## 6. One canonical intermediate representation

Different historical proofs use different geometry and resource representations. Production needs **one** typed intermediate representation with explicit capabilities, not ten independent representations promoted into a public API.

### World identity

A binding identifies environment (`offline`, `mock`, `game`), save, load epoch, spatial scope, topology revision, terrain revision, snapshot content hash, installed asset catalogue hash, game build and adapter build. A load epoch is assigned by the adapter on attachment/load and changes on reload even if the save filename is unchanged.

A snapshot records its coverage, capture interval, consistency method and missing inputs. A snapshot spanning changing state is not coherent merely because all responses came from the same save. The adapter must provide a single-tick capture, a supported pause, or a stable double-read/diff mechanism; otherwise the build remains blocked for stale/incomplete evidence.

Static topology/terrain revisions are distinct from moving-train ticks. An unrelated train advancing does not invalidate every geometric cache entry. A train occupying an edit region still matters at write time.

### Physical railway

Maintain stable canonical IDs for ports, physical edges, components, platform roads, structures and signal anchors. Keep native entity and slot mappings separately with their generation/load epoch. Display names do not supply identity; coincident coordinates do not supply connectivity.

An edge contains its canonical centreline, vertical profile, track/profile identity, structure association and component membership. Components define explicit legal traversals. A crossing does not become an unrestricted four-way node. A station terminal and its adjacent platform road may be distinct native objects.

For the first exposed contract, positions use metres, right-handed coordinates with z up, angles use radians, gradients use m/m and internal speeds use m/s. A port direction is the full 3D unit travel tangent; its grade must agree with z divided by horizontal magnitude. The native transform is separate and tested with asymmetric examples, not inferred from an attractive screenshot.

### Design and assessment

A candidate binds its brief, snapshot, profile, chosen assets, topology, geometry, checks and diagnostic references. The construction plan binds **that exact candidate** plus a native lowering certificate. Operation results from another candidate cannot be attached by matching a display name.

A check carries a domain, scope, source/assumption references, result and whether it is required for the selected task. The state `unassessed` remains available. Its effect depends on the task: unresolved detailed crowd simulation does not block a plain railway connection; an unknown game construction capability does.

## 7. UK realism without endless certification dependencies

The normal profile is `gb_reference_inspired`. It resolves source-qualified values where available, uses explicit project targets for the requested railway, and maps them to demonstrated native track/assets. A source-backed nominal interval is not proof of moving-vehicle clearance, and a particular field-study radius is not a universal turnout speed rating. Preserve the existing distinctions in [17](17_uk_numerical_profiles.md) and [21](21_component_catalogue_import.md).

Each parameter belongs to one of five operational categories: applicable requirement, nominal/reference geometry, project choice, measured game property or unresolved value. Historical or draft source material remains dated and scoped. A caller cannot label a numerical choice “UK standard” without its evidence record.

For normal game design, unresolved specialist evidence can be accepted as a **declared approximation** when the product profile allows it and neither a user constraint nor an engine constraint is violated. The packet should say “reference-inspired, assumed component geometry”, not present a blanket green UK-compliance badge. Strict research is opt-in and may block for fuller evidence.

Three precedence rules are fixed:

* A hard user design constraint is not relaxed by a softer preference score.
* Engine representation limits are not relaxed by a historical example or a successful offline fit.
* A newer source cannot silently change a saved historical profile or an already approved plan.

Map compression changes corridor routing and vertical/horizontal fitting. It does not scale gauge, train lengths, platform fit or structure clearances indiscriminately. Realistic numerics remain relevant even when the bridge is not a certification system.

## 8. Standard construction workflow

### 8.1 Inspect and resolve

Read the authorised region plus an explicitly allowed read halo for adjoining dependencies. A read halo is not an enlarged write boundary. Resolve external ports, actual terrain, water, protected objects, asset availability and game build. Match required inputs to the task and return a specific missing-input condition rather than a stream of uncertain retries.

Asset selection happens **before expensive detailed fitting** where native dimensions or construction options constrain the design. Reassess after selection changes. A bridge reservation does not stand in for an available bridge model.

### 8.2 Generate and check locally

Enumerate relevant pattern families, use cheap bounds to reject candidates, fit the full assembly and check both parent and branch interfaces. Preserve shared physical edges instead of drawing every service route independently. Run only the operational checks relevant to the brief; expensive reference simulations are optional diagnostics.

Use one stage-budget ledger. Evaluate failures into typed causes: unsupported component, insufficient corridor, endpoint mismatch, train-fit shortfall, protected-land contact, unsupported structure, reservation conflict, incomplete data or search exhaustion. A complete bounded search with no result does not prove global impossibility.

A repair may adjust only parameters explicitly authorised in the brief. It may refine numerical sampling, choose another permitted asset, try another insertion chainage or re-fit within the region. It cannot widen the region, delete an unlisted asset, shorten the train, remove a mandatory movement or lower the speed target to achieve a pass.

### 8.3 Present a compact decision

Expose at most three materially different candidates by default, with required checks, important trade-offs and blockers. Full traces stay local. Keep context-rich names for the user while IDs remain stable.

A candidate can be `design_ready` but not authorised for live execution. A target is not an achieved in-game speed. A passed topology check is not observed train passage. These statuses must appear in data, not only in caveat prose.

### 8.4 Lower and authorise

The native compiler chooses supported geometry, junction-generation and structure mechanisms. It returns an operation graph and a certificate of endpoint/curve approximation and intended legal connections. It must not invent `declare_crossing()` or `create_turnout()` native calls because an offline mock had a similarly named operation.

The host obtains or resolves user approval for the immutable plan and effect envelope. Approval binds to principal, save/load epoch, plan hash, allowed operation kinds, exact permitted removals, a write-attempt ceiling and expiry. The model receives an opaque approval reference, not the ability to mint an authority record.

First live deployment uses `create_only`. Planned splicing or removal is a later permission class. Even attaching to a native node can cause the engine to split neighbouring edges; that expected collateral effect must be within the authorised envelope and rechecked.

### 8.5 Execute and reconcile

Persist `prepared` before submission, then record `submitted`, native acknowledgement and measured effect separately. A timeout after submission has an **uncertain effect**, not an automatic failed operation. Query a persistent native receipt or inspect a uniquely identifiable current effect before any retry.

Each stage rechecks the relevant world binding. After an intentional terrain change, read a new snapshot and validate remaining operations against the approved effect plan. Do not repeatedly compare an unchanged pre-build hash against intentional writes and call every own effect external interference. Unexpected changes stop further writes and retain the partial-effect ledger.

Exactly-once effects cannot be claimed from a Python request key alone. Without reliable native deduplication or recoverable effect identity, the ambiguous case stops for reconciliation rather than blindly creating duplicate track.

### 8.6 Verify and observe

Read actual native assets after each bounded stage. Check identity mapping, endpoint alignment, topology and retained required movements; check structures and signals against their selected options. Compare curves by an appropriate continuous or bounded geometric measure when the engine changes segmentation. Ordered vertex equality remains useful only for adapters that preserve that representation.

Then validate the complete railway, including preserved neighbours. Where permitted telemetry exists, run or observe representative passage for each required movement and report which were actually observed. Observation is bounded and authorised; creating test trains, lines, signals or time changes is not hidden inside a supposedly read-only query.

If observation is unavailable, report `topology_verified` with operational observation unassessed. Do not relabel it as `game_traversal_observed`. A user may accept a declared lower-assurance task outcome, but the status remains accurate.

## 9. Useful lightweight operating checks

The default planner checks legal routes; full train length and selected margins at intended waiting locations; whether a waiting tail fouls a crossing; direction and connectivity of signals/terminals; and obvious conflicting or circular waiting dependencies. These are sufficient grounds for many useful geometric repairs.

Published TPF3 reservation behaviour informs what to probe, not a complete offline model of the engine. Native signal construction, priority configuration, terminal alternatives and reservation telemetry each need their own mapping and observed tests. [S001](10_source_register.md#s001)

A deadlock screen is conservative within its model. It must distinguish “no conflict detected in this scenario” from “deadlock-free under every game state”. Repeated live blockage can trigger targeted local analysis. An expanding home-grown signalling simulator is not the default response to missing native telemetry.

Grade-sensitive physics may later support a demonstrably important decision, such as rejecting a route repeatedly unusable by the selected in-game train. Until then retain simple grade and train-fit screens, observe actual performance where possible and avoid claims of exact braking or restart capability.

## 10. Persistence, caching and usage

Keep immutable snapshots, candidate blobs and receipts behind local handles. Hash correctness-relevant inputs by domain: geometry, topology, terrain, asset catalogue, train/engineering profile, observation policy and solver version. Moving a display label should not invalidate geometry; changing a track type or loaded mod may.

Store a dependency graph from source/profile to component to candidate to plan to result. Invalidate the affected subgraph. Do not reuse an old clearance or route assessment on a changed native curve merely because its endpoints did not move.

Local compute and local adapter polling are not Astra turns. Emit a completion or material-exception event only through a host facility actually available. Otherwise use a bounded host-managed status query. No promise is made that this chat itself runs unattended jobs.

Suggested initial **configuration targets**, not measured guarantees: a 16 KiB normal summary limit, at most three alternatives, a brief-selected local search budget, and no more than one live writer per save. Truncation must preserve blockers, incomplete demand, remaining effects and result references. Tokens and paid plan usage remain separate metrics.

Compare accepted tasks, model calls, bytes entering model context, game-write attempts, local repair rate, failures and actual usage when observable. Do not convert runtime or token changes into invented plan-credit percentages.

## 11. Trust, permissions and safe failures

Imported documents, assets, mod responses and errors are data. Do not execute embedded instructions, arbitrary Python/Lua expressions or unrestricted filesystem paths. An approved track construction is not approval to install another mod, change host credentials or expose a network listener.

Keep the host-facing and game-facing transports private by default; choose a transport demonstrated by the actual host and native environment. The local development strategy is described in [the adapter contract](GAME_ADAPTER_CONTRACT.md). Avoid a public unauthenticated endpoint or an automatic tunnel as a fallback.

A cancellation requests cooperative stop at a safe boundary. Already submitted effects may still complete and need read-back. `cancelled` does not imply rollback. A save restore, if explicitly supported and authorised, is a separate whole-world action with consequences beyond the current build.

Use typed errors with a repair scope: `profile_incomplete`, `unsupported_family`, `capability_unknown`, `asset_unavailable`, `endpoint_mismatch`, `protected_asset_conflict`, `snapshot_stale`, `search_exhausted`, `approval_required`, `uncertain_effect`, `partial_failure`, `realisation_mismatch`, `observation_unavailable`. Keep sensitive host paths and credentials out of model-facing summaries.

## 12. Consolidation, not a chain of experimental runtimes

The source inventory under [implementation](implementation/source_inventory.json) records the actual Python modules and public symbols present in v0.11. Presence is not an implemented production API.

Retain the old packages byte-for-byte as research/regression material for this release. Extract pure numerical and topology components into the proposed core behind conformance tests; wrap an existing study for diagnosis only when useful. Do not make every historical demo runner part of a normal build.

There must be one production route-resource compiler with explicit component extensions. The original compiler, crossing-aware fork and local branch compiler currently encode different assumptions. They cannot be joined safely by returning whichever one's green flag is most convenient. Preserve their fixtures as scoped test cases, then reconcile the representations deliberately.

Similarly, the whole-route, sectional-release and whole-pass calendars are different **analysis strategies**. They should be selectable diagnostics behind a common result contract, not competing definitions of real TPF3 behaviour.

The production handoff includes dependency-ordered work packages and feature-level acceptance rather than another proposed numerical simulator. See [AGENT_API_AND_HANDOFF.md](AGENT_API_AND_HANDOFF.md).

## 13. First end-to-end acceptance

On a disposable save, identify two pairs of disconnected track boundaries. Read their real positions, headings, grades and native identity; find an available track asset; generate two connections under the fixed brief; preview; obtain approval; construct; read back; verify both requested directions and preserved neighbours; and observe passage if the native interface supports it.

A valid first build is allowed to be small. A large mock junction is not a substitute. Include at least one controlled snapped geometry case, stale-snapshot rejection and ambiguous acknowledgement recovery on the same implementation before calling the workflow reliable.

The first production gate does not require flyover asset support, full dynamic gauging, detailed platform access or an exact traction law. A later requested flyover does require an actual supported structure and verified clearance/connection evidence for that task. Conditional requirements remain conditional rather than disappearing.

**Exit criterion:** useful authorised game construction, explicit verification level and bounded Astra involvement. **Not an exit criterion:** another historical study, a schema that parses, or a larger accumulated test count.
