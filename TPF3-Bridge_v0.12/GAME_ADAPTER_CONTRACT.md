# Game adapter contract and probe plan

**Version 0.12.0 · 21 September 2026**  
**Status:** proposed native boundary and acceptance plan. No native symbols, game transport, construction calls or live probes were implemented in this release. Mock evidence stays separate.

## 1. Two interfaces, not one

The host-facing interface exposes railway intent. The game-facing interface exposes bounded native reads and authorised edits. Neither requires the game mod to implement MCP. Neither gives Astra an unrestricted native command console.

The mod is expected to be small: receive a validated request, queue it into a supported execution context, call a documented native facility, and publish a result or bounded error. Geometry search, fitting, history, optimisation and reporting remain in Python.

Urban Games describes editable scripts and richer modding tools, but the reviewed announcement is not a native function reference. The promised modding wiki and any later API must be inspected separately. No Transport Fever 2 symbol is admitted by assumption. [S001](10_source_register.md#s001)

## 2. Capability state and evidence

The proposed identifiers below are **bridge capability identifiers**, not names of TPF3 functions. Every real-game record delivered in [the manifest](contracts/tpf3_unprobed_capabilities.json) is `unknown`.

| Evidence level | Meaning | Eligible for live mutation? |
|---|---|---|
| `unknown` | No verified native contract | No |
| `published_feature` | Official description of a player-visible feature | No |
| `api_documented` | Exact callable mapping, parameters and lifecycle reviewed | Not on this evidence alone |
| `demonstrated` | Relevant probe succeeded on a named build and scenario | Only inside tested limits and user authority |
| `unsupported` | Specific negative evidence for the tested build/scope | No; use an explicit alternative |

An unsuccessful search is not evidence that a capability is unsupported. A mock demonstration is not a game demonstration. A build upgrade, mod reload or installed-asset change can invalidate a demonstrated mapping or its limits. Store evidence by capability and operating range, not a single global `game_supported=true` flag.

Each mapping needs the native symbol or mechanism, parameter/result contract, execution context, synchronous/asynchronous semantics, tested limits, error behaviour, input/output artefacts and build fingerprint. A protocol example with `native_symbols=[]` is not an integration implementation.

## 3. Required and conditional capabilities

| Identifier | Native question to resolve | Minimum proof / fallback |
|---|---|---|
| `game.identity.read` | What save, load and game/mod build are active? | New load epoch on reload; stop on identity change |
| `game.coordinates.map` | What units, axis order, handedness and tangent convention are used? | Asymmetric coordinate/heading/grade round-trip |
| `game.topology.read` | Can local physical edges, nodes, terminal mappings and legal connections be read? | Trace a turnout and crossing; no coordinate-only inference |
| `game.terrain.read` | Can height/water/terrain modifications and obstacles be queried? | Bounded grid plus uncertainty and content identity |
| `game.assets.enumerate` | Can installed track, signal and structure IDs and parameters be discovered? | Manifest tied to loaded mod set; absent asset stays absent |
| `game.track.construct` | What native request builds track and joins nodes? | Straight, curved and existing-node attachment cases |
| `game.structure.construct` | Is a bridge/tunnel a separate construction or a track parameter? | Asset-specific approaches and realised structure; conditional |
| `game.signal.construct` | How are signals anchored and directed? | Stable edge/position mapping; conditional for signal tasks |
| `game.geometry.read` | Can actual post-snap curves and generated entities be read? | Deliberate snapping changes detected |
| `game.routes.verify` | Can intended movement eligibility be checked from native topology? | Valid traversal and invalid crossing-turn controls |
| `game.operation.receipt` | Can an uncertain submission be recovered without duplicate effects? | Receipt/effect identity survives the supported failure class |
| `game.change.observe` | Are changed regions or revision/cursor queries available? | Gap detection and bounded resnapshot; optional optimisation |
| `game.vehicle.observe` | Can passage, direction and stopped state be observed? | Named train/route evidence; optional for basic geometry-only gate |
| `game.asset.remove` | Can an exact asset be removed without unintended neighbouring effects? | Whitelisted disposal test; not in first create-only gate |
| `game.station.modify` | Can a station module be changed while retaining connected assets? | Separate station-specific gate; station internals remain frozen |
| `game.preview.validate` | Is native proposal validation available without applying it? | Proven no-write test; otherwise Python preview only |
| `game.world.pause` | Can a stable snapshot/edit be taken while paused? | Probe pause/control lifecycle; not silently assumed |
| `game.signal.configure` | Can direction, behaviour and native supported parameters be set/read? | Read-back of actual configuration, not decorative model alone |
| `game.line.configure` | Can priorities, paths or terminal alternatives be changed? | Explicitly authorised line-edit scenario; not a read operation |

The minimal plain-track build depends on identity, coordinate mapping, topology and geometry reads, track construction, route verification, safe submission/effect reconciliation, and a usable asset identity. Terrain/assets may be supplied from an authorised complete snapshot in an offline fixture; a real build still needs sufficiently current verified input. The small executable plan checker models the operation-capability subset, not all production readiness dependencies.

The native game may build track, junctions and structure spans in one proposal. Preserve that mechanism instead of forcing it through a fictional one-object-per-native-call API. Conversely, a successful native batch does not certify all intended routes.

## 4. Read contract

### 4.1 Identity and lifecycle

At attachment, produce the game/save identity, adapter version, load epoch and asset-catalogue fingerprint. Load/unload invalidates transient native handles and in-flight jobs. A file path is not a stable save identity. A restored save can rewind objects while Python's external ledger remains newer; therefore old operation receipts cannot be replayed solely because their IDs exist in Python storage.

The first operation on a changed epoch is reconciliation or a new inspection, never automatic continuation of old writes. Keep a user-readable explanation of the invalidated plan and known partial effects.

### 4.2 Bounded world snapshot

Read a region defined by an authorised scope handle. Include requested ports and dependency halo, selected physical tracks/components, related station terminals, nearby terrain/water/obstacles and relevant assets. Pagination cursors must be bound to the snapshot, not silently move across revisions.

A snapshot is complete only for its stated coverage. The final page of one category does not establish complete capture of all categories. Return `missing_refs`, capture ticks and consistency status. A single-tick claim requires equal start/end ticks; a stable multi-read claim must show that no relevant content changed between reads.

Use three independent change classes: static topology/terrain, asset catalogue, and dynamic vehicle observations. A paused game may provide stable capture if the native API permits it; otherwise use a bounded stable-read procedure. Reject mixed-state snapshots rather than filling holes with empty arrays.

### 4.3 Coordinates and ports

Normalize native coordinates to metres with z up. Preserve the tested transform record and numerical tolerances. Normalise native tangents without discarding their orientation or derivative magnitude where the spline API needs it.

Each boundary includes position, full unit travel tangent, grade, permitted direction, native entity/port reference and protection status. Opposite-direction tracks require their own boundary records. A port on a bridge or tunnel may require a structure/context attribute; an unsupported context blocks that connection.

### 4.4 Terrain and asset records

Terrain samples retain grid origin, spacing, bounds, heights, water semantics, missing cells and interpolation method. Store observed revision plus a content hash of the relevant data. An imported raster with holes is not a smooth flat world.

Asset references use actual native ID, owning mod ID/version and content fingerprint. Keep install availability separate from game-year availability and selected sandbox policy. “Everything unlocked” is a design assumption to verify; it does not authorise arbitrary installation or bypassing native dependencies.

A supported-parameter schema belongs to the selected asset/build. Reject unknown parameter names rather than passing untrusted arbitrary content to a native constructor. Do not fabricate a UK signal, bridge or track asset from a desired display label.

## 5. Native construction representation

The delivered [domain schema](contracts/bridge.schema.json) defines four minimal operation payloads: `build_track`, `build_structure`, `place_signal` and `remove_assets`. These are proposed logical operations. The native adapter may lower several into one atomic native proposal when demonstrated, or split them into smaller writes with explicit recovery boundaries.

Turnouts are **logical topology obligations** of the candidate. They need not be a dedicated game asset or function. A native track-proposal system may produce them automatically; the adapter must then identify the generated component and verify its usable traversals. The same rule applies to diamonds and slips: a planar intersection is not evidence that the game created the required railway.

The first schema's track representation is a bounded 3D polyline for a contract example. Production can add typed spline representations with versioned approximation contracts. Supplying control points to an API with different derivative conventions requires an explicit conversion and read-back. The schema does not claim that TPF3 accepts polylines.

Structures need real available assets and parameter values. A civil reservation is planning data, not a built bridge. The candidate's deck/tunnel envelope and approaches must be reconciled with the native asset after placement. If the engine owns terrain shaping, include that terrain effect in the authorised envelope and recapture it afterwards.

Signal placement is a separate authorised change unless explicitly included in the approved construction plan. Its native anchor may change after track subdivision; place or rebind it against final edge mappings. Signal appearance does not prove direction or reservation behaviour.

## 6. Operation identity, durability and failure classes

A plan has a stable opaque reference and a content hash. An operation has a stable reference, a canonical payload hash and ordered dependencies. Reusing a reference with different content is an error. Content hashes establish identity, not permission or supplier authenticity.

Persist the following states separately:

| State | Meaning | Restart action |
|---|---|---|
| `prepared` | Payload recorded; not submitted | Submit only after current preflight |
| `submitted` | Native call issued; outcome not yet confirmed | Resolve receipt/effect first |
| `accepted` | Native request accepted; effect may still be pending | Await bounded completion or inspect |
| `applied` | Native effect identified | Read current geometry/topology; receipt alone is insufficient |
| `rejected` | Native evidence establishes no requested application | Report/repair within budget |
| `uncertain` | Available evidence cannot distinguish application from failure | Stop dependent writes; do not duplicate |

A process-local dictionary proves only in-process deduplication. Durable recovery needs a receipt stored inside the save, a supported native transaction identity, or unambiguous effect identification tied to save/load state. Probe which is possible. Do not advertise exactly-once effects when the acknowledgement-loss case cannot be resolved.

A write can split existing edges and replace their native IDs. Record old-to-new lineage, reused nodes, generated components and collateral modifications. Reconcile by topology and expected effects, not nearest coordinate alone. Ambiguous association is an error requiring inspection, not permission to choose a convenient match.

If native rollback is absent, compensation is a separately authorised plan. Removing newly created infrastructure may not restore shaped terrain or neighbouring node identities. The application must report that distinction and preserve remaining effects.

## 7. Revision handling across the application's own writes

The v0.11 mock checks a static source snapshot against operations that do not actually reshape that source. A real bridge cannot apply the same strategy blindly: its own track/terrain writes may legitimately alter revisions.

Production preflight captures an expected baseline and effect model. After each stage, read back the effect and relevant dependency region, establish a successor binding, and revalidate remaining stages. The successor can be accepted only if all observed changes are within the approved expected effect and preserved invariants still hold. External or unexplained changes stop the job.

Prefer a native atomic proposal/version check if available. Otherwise use a single local writer plus immediate re-read at the game callback boundary. A Python-side lock does not prevent the player or another mod from modifying the world; those changes require native observation or consistency checks. No snapshot protocol can claim freedom from races without a demonstrated native mechanism.

## 8. Proposed private transport

Select the game-facing transport after a capability probe, not from habit.

Preferred first option, **conditional on native permission**, is a loopback byte stream with bounded UTF-8 message framing and a session token supplied through a controlled local bootstrap. A request contains bridge protocol version, request ID, save/load identity, scope, method, payload and payload hash. Secrets stay out of persisted model-facing artefacts.

A file mailbox is an alternative only if the native script environment supports the necessary reads/writes safely. Use a dedicated application directory, atomic publication if supported, file-size/depth limits, request IDs, acknowledgements, content checks and quarantine for malformed files. A repeated filename is not an execution identity. Never poll arbitrary user directories or evaluate file contents as code.

The mod must not block the simulation callback while Python performs a long solve. Drain only a measured bounded queue on the approved execution context. Python workers operate on immutable snapshots; native mutations return to that context. Actual callback/thread and filesystem/network behaviour remain unresolved until probed.

The host-facing MCP transport is independent. The reviewed MCP revision documents stdio and Streamable HTTP; actual client support must be pinned and tested rather than assumed from the word MCP. For HTTP, bind privately and implement the transport's origin/authentication requirements. No automatic public endpoint or tunnel is part of this release. [S074](10_source_register.md#s074), [S075](10_source_register.md#s075), [S076](10_source_register.md#s076), [S077](10_source_register.md#s077)

## 9. Probe sequence and exact acceptance evidence

All probes are **specified, not executed**. Start on a disposable, user-authorised save. Each record must identify build, loaded mods, script hook/method, input, expected result, observed result, native artefact mappings and failure limits. Keep screenshots or logs as evidence only where available and useful; do not invent native telemetry.

| Probe | Procedure | Pass condition / negative control |
|---|---|---|
| GP-01 Identity and lifecycle | Attach, read identity, reload a copy, reconnect | Load epoch changes; stale job cannot write |
| GP-02 Coordinate mapping | Read asymmetric points, nonzero heights and differently directed tangents | Round-trip within stated tolerance; reflected-axis control fails |
| GP-03 Local topology | Inspect straight, turnout and non-connecting crossing examples | Actual permitted movements match; no invented branch-to-branch turn |
| GP-04 Terrain snapshot | Sample ground/water, make an authorised small terrain change, resample | Content changes detected even if a coarse revision is reused |
| GP-05 Asset discovery | Enumerate available track/structure/signal records; remove a test dependency | Missing asset invalidates dependent plan; no label substitution |
| GP-06 Straight create/read | Build a short straight on empty ground; inspect geometry and endpoints | Correct native objects and effects; repeat does not duplicate |
| GP-07 Curve and existing-node join | Build a curved connection to fixed stubs | Tangents, topology and preserved neighbours verified after snapping |
| GP-08 Junction generation | Submit supported topology for a simple diverging route | Required normal/branch routes exist; no extra unintended route |
| GP-09 Structure selection | Build a short bridge or tunnel with available asset and full approaches | Actual asset/context/geometry read back; reservation-only is not pass |
| GP-10 Signals and reservations | Authorise a signal and two representative routes | Direction and demonstrated reservation behaviour recorded |
| GP-11 Receipt ambiguity | Interrupt response after an effect has been submitted | Receipt/current state reconciled or explicitly uncertain; no blind retry |
| GP-12 Change during build | Modify a relevant dependency between stages | Subsequent write blocked or correctly revalidated |
| GP-13 Save/load after partial work | Save/load at an intermediate stage; reconnect the external ledger | No replay of effects missing from/restored differently in the save |
| GP-14 Bounded traversal observation | Observe a named train through each required movement | Actual entry/exit evidence or accurately lower verification status |
| GP-15 Whitelisted replacement | On a copy, split/remove/rebuild an approved small asset set | Kept assets/routes preserved; unexpected collateral effects block promotion |

Do not require all fifteen probes for the first useful plain-track build. GP-01–07 plus ambiguity/change handling cover the basic foundation; junctions, structures, signals, observed traffic and replacement are separate promotion gates. Match the demanded task to the capabilities actually demonstrated.

## 10. Realisation verification levels

`geometry_verified` means the authoritative native geometry meets the selected constraints within recorded approximation and read-back limits. `topology_verified` additionally establishes the required connections and protected neighbour invariants. `game_traversal_observed` additionally requires actual per-movement observation on that build. Each level is scoped to the candidate, not the whole map.

A source-informed check, game-native validity check and user brief are separate authorities. A game-valid tight curve may fail the user's UK-inspired target. A beautiful reference curve may be unrepresentable by the selected game asset. Both failures matter.

When the engine changes tessellation, verify curve shape and connections independently of segment count. When it changes a junction automatically, verify every required and forbidden movement. When observation times out, retain `observation_unavailable` or a bounded non-completion result rather than marking passage successful.

## 11. First live end-to-end build

The first workflow is detailed in [the handoff](AGENT_API_AND_HANDOFF.md). It constructs a small double-track link between existing stubs, preserves the endpoint contract and neighbouring infrastructure, and returns one concise result. It does not install mods, alter station interiors, create traffic or change time settings without separate authority.

The delivered JSON examples show record shapes and checks. They are **not a generated native plan for a real save**. The production adapter must resolve referenced assets, routes, snapshots, policies and approvals in trusted storage and reject stale or foreign references.

**Next implementation dependency:** a thin read-only identity/topology/terrain/asset probe, followed by the smallest authorised native track build/read-back. No additional traction simulator is required for this step.
