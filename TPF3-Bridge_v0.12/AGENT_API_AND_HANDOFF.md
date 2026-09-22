# Astra-facing API and implementation handoff

**Version 0.12.0 · 21 September 2026**  
**Status:** proposed callable surface, machine-readable contracts, migration plan and acceptance workflows. No MCP server, durable worker, host connection or native game adapter is running in this release.

## 1. Design intent is the public interface

The normal instruction is “connect these station approaches using this British route profile” or “add this passenger branch while preserving the main-line movements”. A request is compiled into one typed brief, not expanded by Astra into hundreds of low-level track commands.

All expensive iterations run inside the Python application. The model receives material alternatives, a permission request or a bounded failure explanation. The implementation must not call an LLM secretly from each geometry function to compensate for missing engineering logic.

The eight proposed tool descriptors are in [agent_tools.json](contracts/agent_tools.json). Each has a closed input schema and a bounded response envelope. They are descriptors for implementation, not a server launch configuration. MCP can expose structured tools and resources; the domain payloads here remain independent of its wire messages. [S071](10_source_register.md#s071), [S072](10_source_register.md#s072), [S073](10_source_register.md#s073)

## 2. Tool catalogue

| Proposed tool | Input | Normal output | Native game writes |
|---|---|---|---|
| `rail.inspect` | Scope, categories, cursor, item limit | Compact world/capability/asset summary and data references | None |
| `rail.design` | Complete versioned brief and request key | Job/result handle, candidate decision packet or blockers | None |
| `rail.revise` | Candidate reference, complete replacement brief, request key | New candidate lineage and changed-check summary | None |
| `rail.commit` | Plan reference/hash, host approval reference, request key | Job handle then verified/partial/blocked result | Authorised plan only |
| `rail.status` | Job reference and last event sequence | Bounded progress or terminal outcome | None |
| `rail.explain` | Result reference, diagnostic category, item limit | Focused details and evidence references | None |
| `rail.observe` | Scope, observation window/cursor, item limit | Actual available telemetry summary | None |
| `rail.cancel` | Job reference and request key | Stop requested, then stopped/partial result | No new construction; in-flight effects may finish |

Descriptions must disclose whether a tool creates local retained state even when it makes no game changes. Annotations are hints, not an authorisation system. Resolve permissions on every request using trusted host/application state.

Old proposed names such as `rail.design_station_area`, `rail.commit_design` and `rail.cancel_job` may be compatibility aliases in an implementation. Do not publish duplicate aliases by default and inflate the model's tool list. Canonical requests use the eight names above and a versioned task field.

`rail.observe` never creates trains, advances time, changes routes or toggles signals implicitly. Those are mutations requiring their own approved plan. It may report that the requested observation is unavailable.

## 3. Domain records and checked examples

The [schema](contracts/bridge.schema.json) contains 38 definitions, including `DesignBrief`, `Binding`, `Snapshot`, `CapabilityManifest`, `Asset`, `ConstructionPlan`, `Authority`, `Receipt`, `DecisionPacket`, `RealisationReport` and each tool input/output. All numerical fields must also be finite, and objects reject undeclared fields.

The [example index](contracts/example_index.json) maps each example to its definition. These are **authored contract examples**, not evidence that a solver or game ran them. The illustrative plan contains two directed tracks sharing the brief’s four boundary-port records; it remains authored example data, not a solver-produced or native build. A production plan additionally requires resolved movement, asset, geometry and authorisation references; schema validity alone cannot establish those joins.

The local [contract checker](contract_checks.py) validates schema and selected cross-field invariants. It checks unit consistency, bounds, port directions, operation dependencies/hashes, shared-node coordinates, derived capabilities, unsupported authority escalation and false verified-status combinations. It does not implement the native planner, cryptographic authentication, persistent approval service or complete geometric validation.

For a deployment, an API handler must validate shape, resolve all referenced objects in the requesting principal/save namespace, verify current hashes and scope, then invoke the relevant domain service. A handle is an identifier, not permission to access whatever object has that name.

## 4. Minimal interaction for a build

A typical interaction is:

1. Inspect the user's selected region once, obtaining stable endpoint and snapshot references.
2. Submit one design brief. Python resolves profiles/assets, searches and verifies internally.
3. Return a small candidate choice only if there is a material difference requiring a decision. A pre-authorised selection policy may select within the user's rules without additional model calls.
4. Obtain host/user approval for the exact plan. Commit its reference, hash and approval reference.
5. The host receives completion or a material exception. Python keeps receipts, read-back and ordinary retries local.

These are logical stages, not a promised fixed number of billable calls. Inspection might already be cached; an unexpected native limitation may require another design decision. The important invariant is that segment count and numerical trial count do not determine the number of Astra interactions.

A useful result would say: “Both connections are topology-verified. One endpoint was snapped and re-fitted within the approved two-metre search interval. Train passage has not been observed. See result R for the asset map.” It would not export hundreds of spline vertices and ask Astra to decide whether they look connected.

## 5. Local job lifecycle

The Python application owns durable jobs. A transport request may return a stable job handle rather than remain open for the entire design. Application state must not depend on a particular MCP connection remaining alive.

Proposed state progression:

`received → validating → inspecting → resolving → planning → checking → decision_ready → awaiting_approval → preflight → executing → verifying → observing → completed`

Not every task uses every stage. An inspection stops after `inspecting`; a design-only task finishes at `decision_ready`; observation may be unavailable and reported separately. `completed` is a job state, not a blanket geometry or game-assurance level.

Separate terminal/error outcomes include `blocked`, `search_exhausted`, `cancelled_no_effect`, `stopped_with_partial_effects`, `uncertain_effect` and `failed`. A read-back failure cannot be concealed by returning the earlier acknowledgement as success. A cancellation after submission requires effect reconciliation.

Application cancellation is explicit through `rail.cancel`. Transport disconnect behaviour follows the negotiated transport; it is not assumed to rewind an application job. The application must document whether a cancelled request also requests job cancellation, and still return the retained state on a later authorised status query.

Progress notifications or durable task extensions are used only when the actual host supports them. Otherwise the local host polls `rail.status` with backoff and unchanged summaries are not repeatedly fed to Astra. This is a requirement on the future application, not a promise of unattended work by this chat.

## 6. Protocol compatibility and trust

The external protocol reference reviewed for this release is MCP **2026-07-28**. That revision uses per-request version/capability metadata and differs from earlier session-oriented revisions. The handoff deliberately does not include an old initialise-handshake example labelled as current. Pin a compatible implementation and test against the actual host before publishing connection instructions. [S071](10_source_register.md#s071), [S074](10_source_register.md#s074)

Keep the 0.12 domain schema version separate from the MCP revision, game build, mod build and asset version. Changing one must not silently re-label the others. Resource handles and result records remain application-owned across protocol adapters.

Use local stdio where the host can launch a process. Use authenticated Streamable HTTP only where the host can reach the endpoint and the required security boundary is explicitly configured. Do not assume that a browser-based or remotely executed host can connect to a desktop loopback address. The specified transports and their security requirements are in the primary references; no particular Astra product/plan transport support has been tested here. [S075](10_source_register.md#s075), [S076](10_source_register.md#s076)

There is no `rail.run_python`, `rail.eval_lua`, unrestricted shell tool or arbitrary-file-read function in this interface. Logs, asset descriptions and source records are untrusted data. Native methods are selected from the adapter mapping, not supplied as executable text by the model.

## 7. Authorisation is outside model-authored JSON

The `Authority` definition documents an internal trusted record. It is intentionally **not** a property of `CommitInput`. A client supplies only `approval_ref`; a server resolves it from trusted storage and verifies issuer, principal, plan hash, save/load epoch, region, operation kinds, removals, expiry and remaining attempt budget.

The text `issued_by: trusted_local_host` in an uploaded example does not establish trust. Likewise, an `approved: true` field is not accepted anywhere in model-authored plan data. Runtime approval may come from the user's explicit one-build confirmation or an existing scoped policy; either must be recorded by the host.

A standing sandbox policy can authorise bounded create-only edits in a selected region, avoiding repeated approval for each piece of track. It does not authorise silent demolition, enlarged terrain works or a materially different plan. The production policy resolver may automatically approve a new plan only if the plan remains within that recorded user policy; it still mints an exact plan-bound authority record.

The offline preflight checker accepts an assumed trusted context to test these selected rules. It always performs zero game writes and never returns actual live execution authority. A positive contract test means the selected data relationships are consistent, not that an unauthenticated object has gained permissions.

## 8. Summary, cache and observation policy

Store detailed outputs locally and retrieve them by bounded category. The normal decision packet contains no more than three alternatives, key check/metric summaries, all blockers and detail references. Apply the configured byte budget after serialization. Never truncate an error, outstanding effect or failed mandatory constraint out of the report to meet that limit.

Use separate hashes for geometry, terrain, topology, assets, rule profile, vehicle profile, solver policy and operation plan. Cache pure results by the inputs they actually depend on. A topology change invalidates affected routes; a changed signal configuration invalidates the relevant operating check but should not force every terrain calculation to rerun.

World-change observations need a cursor, coverage and gap detection. A skipped or expired cursor requires a bounded resnapshot, not an assertion that nothing changed. If native change events do not exist, a local diff can provide a fallback under an explicit read budget. Do not send every poll to the model.

A synthetic timetable comparison and real-game telemetry remain separate data kinds. The application should not rank builds by a large offline delay estimate when the actual game lacks the assumed scheduling semantics. Use that estimate only as a declared diagnostic.

## 9. Source-to-production migration map

The inventory below names modules actually present in the package. The target production layout is proposed in [the specification](IMPLEMENTATION_SPEC.md); no refactor is claimed in v0.12.

| Existing package / symbols | Reuse decision | Required production change |
|---|---|---|
| `railgeom.curves`: `Bezier`, `join_check`, `flatten`, `continuous_proximity` | Extract pure geometry foundations | One unit/frame convention and approximation contract |
| `railgeom.network`: `Network`, `Port`, `TrackEdge`, `Turnout`, `RailPath` | Use as topology reference | Stable native lineage, versioning and non-turnout component extensions |
| `railgeom.compiler`, `railcompact.compiler`, `railbranch.operations.compile_resources` | Reconcile, not three public compilers | One component-aware compilation API with explicit modelling policy |
| `railcompact.composition.build_compact`, `railstation.composition` | Preserve station patterns as reference fixtures | Freeze internals; adapt only requested station/game interfaces |
| `railcorridor.geometry.Alignment`, `railbranch.geometry.hermite` | Extract applicable fitting primitives | Arbitrary supported boundary fitting; no fixed-site assumptions |
| `railterrain.geometry.build_placed`, `railterrain.planning.search` | Retain terrain-aware pattern/search logic | Real world snapshot, asset limits and larger family domain |
| `railclear.catalogue.import_component`, `place_synthetic` | Reuse validation/evidence separation | Authentic/native component mappings; synthetic flag remains visible |
| `railops.uk_profiles`, `railinterface.reference` | Reuse scoped numerical evaluators | Production profile resolver with optional/mandatory scope |
| `railclear.model`, `railclear.sweep` | Keep useful geometry checks and diagnostics | No claim of full dynamic gauging; select fidelity per task |
| `railproof.engine`, `railops.operations`, `railbranch.operations` | Keep selectable lightweight analysis strategies | Do not treat any one as validated TPF3 signalling/physics |
| `railcorridor.adapter`, `railbranch.adapter`, `railterrain.adapter` | Reuse fault cases and reconciliation invariants | Native adapter, durable ledger, own-write revision handling and save/load |
| All `demo.py` runners and historic results | Keep as regression/reference material | Not the runtime public API, not mandatory stages of each job |

[Source inventory](implementation/source_inventory.json) records actual file hashes, public top-level symbols and absolute proof imports. It is an AST inventory, not a claim of code execution or dependency completeness.

For consolidation, begin by defining interfaces and extracting one pure function at a time behind the corresponding regression. Keep old fixture identities and expected limitations. If a production method expands its domain, add independent tests for that domain instead of changing an old narrow fixture until it passes silently.

## 10. Implementation work packages

[work_packages.json](implementation/work_packages.json) records dependencies and exit evidence. This is sequencing, not a time estimate.

| Package | Deliverable | Decisive exit evidence |
|---|---|---|
| WP-01 | Canonical contracts, trusted authority store and durable jobs | Round-trip models; non-model-minted approvals; restart-safe job records |
| WP-02 | Thin read-only native probe | Real build/save identity, coordinate mapping and coherent bounded topology/terrain/assets |
| WP-03 | Canonical kernel extraction and port fitting | Supported original boundary constraints preserved, selected proof fixtures pass through one core |
| WP-04 | Create-only game construction/read-back | A small real link works; snapping, stale state and uncertain responses are handled |
| WP-05 | Host-facing service and local worker | Actual host connects; one intent request invokes bounded local work; compact result returned |
| WP-06 | Structures and junction native support | Real assets and required movements survive native generation and read-back |
| WP-07 | Practical signals and observation | Direction/configuration checked; geometric waiting room; observed status accurately scoped |
| WP-08 | Whitelisted existing-layout replacement | Preserved neighbours, explicit removal list, successor snapshots and save/load reconciliation |
| WP-09 | Product acceptance and usage measurement | Same accepted tasks compared; failures and model/native work counted separately |

WP-02 and pure kernel work can proceed in parallel after their contracts are stable. WP-04 must not wait for full traction physics, passenger crowd analysis or every possible turnout family. WP-06/07 are required when a requested task needs those features, not to demonstrate the first plain-line link.

A future implementer with no live game access can complete contract and core work, prepare the read-only mod package and record an unresolved native mapping. They cannot mark WP-02 or WP-04 passed by running a mock. The evidence ledger must preserve that boundary.

## 11. First complete construction acceptance script

**WF-01: connect two pairs of existing stubs on a disposable sandbox save.** This is specified, not executed here.

Select four actual boundary ports: one input/output pair for each running direction. Record their positions, tangents, grades and native identity. Freeze all neighbouring tracks outside the authorised connection. Specify the design train, intended profile, route speed, grade/radius targets and available effect region.

Read the complete local terrain/topology/asset snapshot. Reject inconsistent or incomplete coverage. Choose a native available track asset; its geometry/parameters and mod fingerprint join the candidate identity. Generate both alignments, check spacing/joins and required movements, and produce a preview with effects on terrain and existing nodes included.

Approve exactly that plan in the host. Execute the smallest safe dependency-ordered batches. Read current objects after each batch and reconcile generated node/edge IDs. An acknowledgement timeout triggers receipt/effect resolution, not blind duplication. A deliberate test displacement must be detected and either repaired within the approved search/attempt limits or reported as a stopped partial result.

Verify each directional connection and the preserved neighbouring movement matrix. Confirm that no unlisted asset was deleted or modified beyond the approved expected effect. If observation is supported and authorised, record an actual train passage through each new connection. Otherwise return topology-verified status with observation explicitly unassessed.

Repeat the same approved request key and verify no duplicate effects. Change the relevant snapshot and confirm a stale plan cannot write. Reload a saved partial state and confirm the external ledger does not replay obsolete operations automatically.

The acceptance record includes game/mod/asset versions, input and plan hashes, actual entity lineage, checks, controlled failures, remaining effects and all model/native interactions. Passing a contract example is not a substitute for this record.

The later workflows are [WF-02 through WF-05](implementation/acceptance_workflows.json): a simple branch, a structure-bearing corridor, signal/passage observation, and whitelisted replacement. Each adds a named capability without reopening station internals or manufacturing a physics prerequisite.

## 12. Product metrics and stopping rule

Measure completed requested movements, explicit constraint violations, actual protected-neighbour preservation, native construction success, repair attempt counts, ambiguous effects and result verification level. Model involvement is measured using tool calls, bytes/context sent and actual usage when exposed by the host. Local solver runtime is a separate engineering metric.

Do not present fewer calls as an improvement if the new workflow drops required track, skips verification or leaves unexplained partial effects. Record failures as well as successful builds. Compare like-for-like starting saves, game builds, assets and user objectives.

The next development step is concrete: **implement the read-only native adapter probe and create-only track/read-back path**. The deferred physics work remains optional until a measured game-specific need makes it valuable.
