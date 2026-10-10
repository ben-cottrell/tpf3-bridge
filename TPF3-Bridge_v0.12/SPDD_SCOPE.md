# TPF3-Bridge — authoritative product boundary

## Requirements
A practical British-railway construction assistant for an already-running healthy
Transport Fever 3 sandbox session. The target is credible, functional railway at native
game scale, not metre-for-metre reconstruction. GPT usage efficiency is a core requirement.
Current scope includes track connections, junctions, graded structures, basic passenger
stations, signals, depots and representative native service operation. Additional product
outcomes require adoption; available APIs, research and old tests do not create them.

## Entities and responsibilities
Use bounded semantic entities: briefs, railway interfaces, named protections/functions,
native proposal handles, selected assets, engineering observations, committed results
and acceptance. Do not duplicate the entire game world.

- Astra/model chooses intent, material layout trade-offs and genuinely novel decisions.
- Python supplies UK/game-scale engineering, topology choices, bounded search/repair,
  orchestration and acceptance.
- The semantic mod translates capabilities, native identities, supported commands,
  bounded observations and committed readback. It is not another planner.
- TPF3 owns native detailed geometry, snapping, terrain treatment, structures, topology,
  pathfinding, reservation, simulation and entity lifecycle.

## Approach
Use native-tool-first construction and the fewest controls expressing the intent.
Detailed Python geometry is justified only by a native input requirement, an engineering
check, meaningful alternative comparison or demonstrated native gap. Accept realised
connections, required movements and selected engineering limits, rather than exact
reproduction of a sketch or internal construction history. Exact identity outranks
coordinate resemblance. Keep DESIGN, PREVIEW and COMMITTED evidence distinct;
reacquire committed identities rather than promote temporary preview entities.

Use native vehicle/track/platform/structure dimensions. UK measurements guide topology,
character and explicitly selected targets. Unit conversion differs from geographic or
play compression; no universal scale factor. Preserve train/platform fit and selected
curve/gradient requirements after compression. Radius is feedback/preference unless
an explicit brief or demonstrated requirement makes it hard.

Existing terrain is not implicitly protected. Native cutting, fill, bridges, tunnels
and rerouting are ordinary responses. Terrain slope guides treatment, not automatic
failure. No implicit penalties for demolition, landscape change or structures. Detailed
civil analysis is required only by the brief or a demonstrated construction limitation.

Inside the authorised effect region classify relevant state explicitly as PROTECTED,
FUNCTION_ONLY, REPLACEABLE, REDEVELOPABLE or ENGINE_DELEGATED. Existing or inspected
objects do not automatically become protected. Verify requested infrastructure, required
functions, explicit protections, effect boundaries and named hard constraints; incidental
map preservation is not a default acceptance gate.

## Operations and norms
The operating loop is intent → bounded design → native preview where supported →
engineering assessment → applicable authority/checkpoint gate → build → fresh semantic
readback → acceptance or finite railway-focused repair/escalation. Rollback/undo are
capabilities to establish, never guarantees. Ordinary save/load in a healthy process
requires fresh identity inspection; unknown or partial mutations must not be replayed.
The coordinator owns native/UI and design decisions; workers follow their assigned scope.

Before adding a module or gate, identify the approved outcome, why native behaviour or
a simpler check is insufficient, and the bounded success criterion. Investigate proven
functional problems. Do not weaken tests to obtain a pass or turn a modelling difference
into a new product guarantee. Native paths, physical traversal, service configuration,
saved-file integrity and visual design acceptance are separate conclusions.

Use deterministic local loops and compact decision packets. Models stay above routine
search, polling, ranking and verification. Small current instructions and precise pointers
replace repeated audits. The development runner is tooling, not game/OS supervision;
there is no active batch or automation.

Keep living documentation, reusable source/tests/fixtures and transferable design lessons.
No permanent agent journals, audit histories, handoff archives, completed-run logs or
cleanup manifests. Temporary diagnostics are removed after their purpose is complete.
Persist only minimal functional context/state needed to operate or reconcile uncertain
live effects. This policy supersedes earlier evidence/history-retention wording.

## Safeguards
Assume game, loaded world, adapter, Python/local files and external permissions/environment
already work. Below the semantic boundary, report and stop: game_session_unavailable,
adapter_unavailable, external_environment_unavailable or local_storage_unavailable.
Do not launch/restart the game/Steam, repair permissions/authentication/network/OS,
supervise processes, restore crash workflows or build watchdogs.

Detailed station crowd/furniture/access simulation, traction/braking/adhesion physics,
a second reservation/signalling simulator, general tycoon/fleet/revenue management,
regulatory certification and open-ended map improvement are outside scope. Basic native
stations and representative services do not imply those expansions. Publication remains
externally blocked; do not retry or push. Architecture details are in
NATIVE_FIRST_ARCHITECTURE.md; practical design guidance is in the handbook/procedure.
