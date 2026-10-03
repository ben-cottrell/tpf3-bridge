# Native-first production architecture

## Authority and status
Use TPF3 as the authority for game-native behaviour, Python as the authority for
UK railway engineering and orchestration, the mod as the semantic boundary between
them, and Astra only for intent and material design decisions. Verify the finished
railway state that matters rather than reconstructing the game's internal causal
history.

This is the production architectural authority: native-first, state-based, bounded,
evidence-driven and final-state-oriented. It takes precedence over conflicting
production guidance in IMPLEMENTATION_SPEC.md, GAME_ADAPTER_CONTRACT.md and older
research, especially blanket preservation and internal-write reconstruction.
Reuse their applicable contracts, evidence and authority controls. This document
does not change executable schemas, algorithms, test-specific briefs or acceptance
history, grant mutation authority, or assert any released native capability.

## Hard runtime and environment scope
The bridge is a railway construction system, not a computer-management system.
It drives TPF3 only while a healthy game session is already running and the
semantic adapter is available. These are external preconditions:
- TPF3 is running with the intended world/save already loaded.
- The mod/semantic adapter is loaded and reachable.
- Python and required local files are usable.
- OS permissions, authentication, machine and network environment are functioning.

The bridge does not launch/restart TPF3, recover a game crash, start/restart Steam
or another launcher, kill/supervise OS processes, repair/reinstall the game/mod/
Python environment, change filesystem permissions, configure antivirus/firewalls,
recover failed storage/disks, repair authentication/accounts, reboot/recover the OS,
restore jobs after machine/process crashes, or perform unrelated desktop automation.
Do not create requirements, retry loops, diagnostics, watchdogs or recovery
workflows for those cases. Never cross the semantic adapter boundary for OS or
process recovery.

If a precondition is absent, stop the current job with a concise terminal blocker:
`game_session_unavailable`, `adapter_unavailable`,
`external_environment_unavailable` or `local_storage_unavailable`, as appropriate.
These production status meanings require user/environment intervention; they are
not instructions for the bridge or Astra to repair anything. No availability
polling or automatic retry follows the blocker. This policy does not claim that
these statuses or native checks are already implemented in the offline application.

Retain finite engineering-focused recovery only while the environment stays
healthy: preview/construction rejection, realised geometry mismatch, missing
required routes, bounded candidate failure, explicitly reported partial game
mutation, stale in-session identity, or other semantic adapter results resolvable
by a permitted railway-design retry. Below the game-semantic boundary, report and stop.

Ordinary save/load changes while TPF3 stays running may establish a new world/load
identity and require fresh inspection. A crashed or terminated game process is an
external-environment failure; never relaunch it or automatically recover its jobs.
Persistence supports engineering evidence, result history, in-session operation
reconciliation and avoiding duplicate semantic game operations where appropriate.
It does not require workflow continuation across game crashes, process/machine
crashes, OS restarts or broken host environments.

This hard rule supersedes any older generic requirement for automatic game restart,
process recovery, filesystem/permission repair, host watchdogs or OS remediation.
It governs production runtime scope; existing development tooling is unchanged.

## Responsibilities
| Layer | Owns |
|---|---|
| Astra decides intent | Intent, material trade-offs, unusual design choices, ambiguous policy and genuinely novel native semantics needing human/model interpretation. |
| Python engineers and supervises | UK knowledge and source-qualified profiles; briefs/hard constraints; topology/pattern choice; intended geometry and corridor/junction alternatives; candidate generation, bounded search/repair/ranking; train/platform fit and geometric holding; site/protection constraints; engineering acceptance, orchestration and compact evidence/decision packets. |
| The mod translates native reality | Native identities/capabilities/queries, preview/construction calls, asset semantics, topology/path queries, committed read-back, save/load reconciliation, error normalisation and canonical-to-native mapping. Technically capable, strategically dumb: no second railway planner. |
| TPF3 owns native mechanics | Where exposed adequately: construction/snapping, terrain modification, bridge/tunnel implementation, entity lifecycle, pathfinding, reservation/signalling, train motion, passengers, native validity/collision, save/load reconstruction and preview behaviour. |

Astra stays above routine loops: no model calls for geometry retries, parameter
sweeps, routine ranking, polling, repeated world interpretation, bounded repair or
normal verification. Use deterministic local work and compact decisions.

## Capability decisions, in order
1. Does TPF3 already own the behaviour?
2. Can the semantic mod query or command it adequately?
3. Can Python use native preview/read-back instead of reproducing it?
4. If an answer is needed before preview, is a cheap engineering approximation enough?
5. Build a deeper Python fallback only if native support is absent/insufficient and
   the fallback demonstrably improves construction quality, safety or GPT usage.

An unknown internal game mechanism is not a reason to implement a substitute.
Classify relevant requirements/state as ENGINE_NATIVE, MOD_SEMANTIC,
PYTHON_ENGINEERING, PYTHON_CACHE, FALLBACK_ONLY or UNSUPPORTED. Preferred ownership
is provisional until the survey; UNSUPPORTED needs scoped evidence, not failed
discovery. Unknown native implementation details need not block a project; unknown
required engineering or final-state facts block acceptance.

## Semantic information and geometry
Prefer bounded queries for ports, required movements, route availability, corridor
observations, preview results, asset capabilities, realised geometry, construction
effects and verification results. Do not normally serialise native component graphs.

| Tier | Use |
|---|---|
| 1: semantic summaries | Default production exchange and model-visible output. |
| 2: bounded engineering geometry/state | Only what a specific Python calculation needs. |
| 3: raw native diagnostics | Local adapter debugging for a specific question; Astra should almost never see it. |

Keep intended engineering geometry, native preview geometry/state and committed
realised geometry/state distinct. Python owns intent, engineering requirements,
relevant layout choices and acceptance; it need not precompute every track's exact
shape. TPF3 realises the intent. Do not reproduce native control points/entities unless the
API requires that representation. Assess the realised railway against engineering
intent, not equality of segmentation or internal construction history.

## Native construction tools before custom geometry
Before promoting custom fitting or geometry lowering into the native construction
path, survey actual TPF3 workflows: modes, control points, attachments, snapping,
parallel tracks, elevation, structures and junction formation. Begin with ordinary
connection and parallel-track workflows; expand only when a project need requires it.
Keep player-visible behaviour, documented callable APIs and demonstrated mod
behaviour as separate evidence. Do not infer CS2 modes, TF2 APIs, automatic parallel
rails or scripted preview access from appearance or another game's behaviour.

Prefer supported native construction/proposal mechanisms, supplying the fewest
controls needed for engineering intent. Add production Python fitting/lowering only
for a demonstrated native gap. Distinguish exact fixed anchors/attachment identities,
approximate guide locations and native-generated geometry. A control point takes
its meaning from the chosen native tool; it is not automatically a mandatory point
on the finished railway. Preserve exact attachment identity where available.

A Python sketch, ordered vertex list or subdivision pattern is not the default
expected native result. Accept native geometric differences when actual connections,
required movements, selected engineering limits and the authorised corridor pass.
Do not fix mismatches by globally relaxing tolerances or weakening genuine hard
requirements. Saved-file integrity remains separate from semantic native-build
acceptance. Existing geometry stays as regression/fallback material until evidence
shows what to use, bypass or demote; do not rewrite or delete it now.

Record findings once in the compact local capability table, with build/scope and
evidence references for each evidence type, control semantics, limits and decision.
Keep raw details local instead of repeating model transcripts. This is preparation,
not permission to run a survey, mutate the game or launch an implementation batch;
all existing authority, runtime, preservation, station and physics exclusions apply.

## Game scale and representation
Default to a credible British railway at TPF3's native scale, not metre-for-metre
real-world reconstruction. Keep verified coordinate/unit conversion separate from
geographic/gameplay compression; assume neither a universal scale factor nor equal
compression of every asset dimension.

Use actual native vehicle, track, platform and structure dimensions where available.
UK measurements remain source-qualified reference evidence, not automatically
mandatory construction values. Use UK research primarily for functional topology,
railway character, appropriate design families and explicitly selected dimensional
targets. In the task's profile, distinguish binding user constraints, project-selected
defaults and optional real-world references; adoption must be explicit.

Preserve working relationships: selected native trains fit their platforms/holding
sections; required routes and exact attachments exist; native structures/clearances
are suitable; realised curves and gradients satisfy the selected game-oriented brief.
Compress layout through routing, placement and native design choices, not uniform
shrinking of assets, clearances or a reference plan. Reassess geometry after changes:
shortening a ramp or curve changes its gradient/curvature and may invalidate acceptance.

Prefer native tools to realise that intent. Do not reject an otherwise acceptable
native result solely for differing from an unscaled UK reference or preliminary
Python sketch. Explicit hard user constraints remain binding.

Add only task-relevant units/transforms, observed dimensions/behaviour, fit/clearance
evidence and selected-value origins to the existing profile/capability survey record.
Retain unknowns and build/scope references; do not invent conversion factors, build
a global scale model or add a simulator. Existing geometry, code and historical
fixtures remain unchanged; this policy is not authorisation for an implementation batch.

## Evidence epochs and identity
| Epoch | Evidence concerns |
|---|---|
| DESIGN | Python's proposed railway and engineering checks. |
| PREVIEW | A native proposed action, its proposed geometry and effects. |
| COMMITTED | Freshly observed resulting persistent-world state. |

Qualify evidence by epoch, relevant game/mod build, save/load identity, scope,
coverage, provenance and uncertainty. Mock evidence never demonstrates a native
epoch. Reacquire committed identities/state; never promote temporary preview
entities or preview IDs into committed truth. File integrity is a separate fact.

Maintain canonical Python identity ↔ semantic-adapter mapping ↔ exact native entity
identity plus load epoch. Use exact identity when exposed. Geometry may verify
correspondence; nearest/proximity matching must not invent authoritative identity.
After in-session reload/restore, invalidate transient mappings and inspect/reconcile
before acting; a process crash instead triggers the terminal environment blocker.
Caches are derived and bounded, not a second authority for native state.

## Preservation and redevelopment
Mere existence in a map, inspection or snapshot confers no preservation requirement.
Inside the authorised construction/effect region, ordinary content defaults to
REDEVELOPABLE unless the brief explicitly says otherwise. Outside that region,
there is no implied authority to change anything.

| Policy | Required outcome |
|---|---|
| PROTECTED | The named physical asset remains within its stated tolerance. |
| FUNCTION_ONLY | Objects may change or be replaced; the named function/connectivity survives. |
| REPLACEABLE | May be removed and rebuilt as part of the design. |
| REDEVELOPABLE | May be modified/destroyed without preservation penalty. |
| ENGINE_DELEGATED | Native consequences are accepted without object-by-object verification, within authorised scope and named constraints. |

Construction may legitimately change/remove terrain, vegetation, buildings,
development, roads, landscaping, existing railway and other objects. Do not assign
implicit demolition, terrain, vegetation, road or development-loss penalties;
only explicit brief/profile preferences introduce those costs. Prefer rebuilding
when it produces a better railway and redevelopment is authorised; existing
infrastructure alone does not oblige Python to route around it.

Ordinary native preview side effects, including generated-object changes, are
acceptable unless they breach an explicit protection/function policy or effect
boundary. Verify requested infrastructure, required movements/functions, named
protected assets, authorised boundaries and other hard constraints. Do not verify
incidental map-content preservation by default. This supersedes generic earlier
requirements to preserve all neighbours or unlisted assets. Narrow protections
declared in an existing test/brief remain valid for that test/brief only.

## Hard terrain policy
Existing terrain is not implicitly protected, and steep ground is not automatically
a design failure. The primary responsibility is a valid railway alignment. Ground
may normally be modified as necessary inside the authorised construction/effect
region, subject to explicit protection and other hard constraints.

Ordinary treatments include native terrain deformation, cutting, embankment,
bridge/viaduct, tunnel, routing around the area, or combinations. Railway gradient,
curvature, required clearances and explicit protected areas remain engineering
constraints. Ground slope informs treatment selection; it does not require the
railway to follow the original ground.

Do not impose implicit optimisation penalties for terrain deformation, cutting/fill,
tunnels, bridges or landscape change. Terrain-treatment costs/preferences exist
only when explicitly requested by the brief, including a profile deliberately
selected for that purpose; a generic default profile must not introduce them.

Prefer this native-first sequence:

1. Python proposes an engineering-valid alignment/corridor.
2. The semantic mod asks TPF3 native preview, or separately authorised native
   construction, whether ordinary terrain handling can realise it.
3. If the native result is unsuitable, Python tries a finite, authorised alternative:
   another elevation/profile, bridge/viaduct, tunnel or nearby corridor.
4. Verify the realised railway and explicit constraints, including effect boundaries.

Do not reproduce TPF3's terrain solver in Python when native handling can perform
the required modification. Detailed terrain-volume, slope-stability, drainage or
civil-engineering analysis is not mandatory for ordinary game construction unless
TPF3 exposes a relevant construction limitation, the user explicitly requests that
realism, or a demonstrated failure shows that the extra model is needed. Lightweight
terrain/civil estimates may remain planning diagnostics rather than acceptance gates.

A steep hill normally calls for choosing cut/tunnel/bridge/reroute, not declaring
"terrain infeasible". A bounded search or native rejection establishes only its
actual supported failure scope, not global impossibility. This rule supersedes
generic earlier requirements to preserve existing terrain, minimise terrain change
or enforce detailed ground conformity. Explicit brief constraints and scoped
historical test evidence remain intact; this policy does not authorise new native
calls, game writes or algorithm changes before the existing capability/authority gates.

## Final-state acceptance and recovery
Ask whether intended endpoints connect, required movements exist, forbidden
movements remain absent, realised radius/gradient meet limits, requested structures
exist, named protected assets/functions survive, terrain effects stay in scope,
and the native pathfinder recognises required routes. Where supported and separately
authorised, traversal observation can establish additional facts; do not label
topology checks as observed train traversal or hide mutations inside read-only probes.

Use independent final-state facts rather than reconstructing every transient engine
write. Retain enough submission/effect identity to avoid duplicate ambiguous writes;
an acknowledgement or receipt alone does not prove the finished railway is correct.

Within the healthy running session, the target loop is: intent → deterministic Python design → native preview → Python
engineering assessment → authority/checkpoint gate → native build → fresh committed
semantic read-back → Python acceptance → accept / bounded repair / restore-or-escalate.

Do not assume transactions, undo or rollback. A checkpoint is the safest recovery
mechanism demonstrated on the released build/API: possibly save duplication,
save/load, undo or native transactions. Until tested, rollback is a capability
question. Restoration/compensation needs appropriate authority, fresh identity
reconciliation and honest reporting of remaining effects; never assume rollback.
Here restore-or-escalate covers authorised railway-operation recovery through the
semantic adapter while TPF3 remains healthy, not game/process/host crash recovery.
Unavailable runtime preconditions terminate the job instead of entering this loop.

## Existing Python work
- Keep for production: UK evidence/profiles, topology/pattern knowledge, engineering
  geometry, corridor/junction design, bounded search, site/protection constraints,
  train/platform fit, decision packets, saved-run integrity and task orchestration.
- Keep for screening/diagnostics: lightweight conflicts, terrain/civil estimates,
  clearance approximations and synthetic operating comparisons.
- Consider demotion/removal only after an API survey demonstrates a native
  replacement: recreated snapping, broad terrain serialisation, duplicated topology
  reconstruction, synthetic native-object lifecycle, detailed reservation/signalling
  emulation and lowering that TPF3 can perform better. Do not delete/refactor now.

## Production survey gate and efficient development
Initial post-release prerequisites were installed/runnable TPF3, current modding/API
documentation and explicit probe authority. Focused development experiments now
demonstrate a limited native path on build40408; see STATE.md and live interface
usage. This does not certify a complete production capability survey. Begin each
new native capability with evidence, not an assumed port of the mock adapter.
Prefer finding what Python can bypass/demote before implementing native code.
Use the existing adapter contract and the planning-only capability matrix; no
native names, TF2 compatibility or live capability are assumed.

Production mutation needs relevant read-only capability/identity/coordinate/terrain/
topology/asset evidence, explicit authority and a demonstrated recovery assessment.
Separately authorised disposable-world development experiments have already built
track; they do not establish production rollback or universal native support.
Detailed station modelling is frozen; train-physics expansion deferred.

Keep small cards, exact pointers, a short STATE, full local logs and compact model
summaries; deterministic loops, one worker unless justified, no repeated broad
audits or historical preload. No new batch, polling, scheduler, MCP, dependencies
or speculative binding is authorised by this document alone.
