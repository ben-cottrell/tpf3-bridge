# Research backlog and evidence-to-implementation plan

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Current integration:** v0.6 addendum at the end of this document; earlier sections retain their version-specific status. Current execution evidence is in [25](25_v06_execution_report.md).

Version **0.3.0** · 20 September 2026

The next research stage should deepen technical topology and operating evidence for selected cases, not simply collect more passenger maps. The source register identifies what was actually reviewed and what remains unassessed.

## 1. Priority acquisition tasks

| Task | Priority | Required material or question | Why it changes the implementation | Completion evidence |
|---|---|---|---|---|
| RES-001 — Birmingham region | P0 | Dated track/route plan covering both station ends, Proof House and Grand Junction | Resolves exact movement eligibility and which conflicts are genuinely independent | Feature-level R3 topology with traceable route/point identities and unresolved protection fields |
| RES-002 — Birmingham berths | P0 | Physical platform roads, usable lengths, labels, permitted split occupation and stopping positions | Converts A/B/4C labels into correct physical and operating resources | Reconciled berth inventory with no inferred simultaneous-use permissions |
| RES-003 — Clapham rail corridors | P0 | Dated track plan and permitted stopping/routing by relevant service/track group | Prevents treating seventeen labels as one interchangeable platform pool | Explicit group graph and complete required movement matrix for a selected scenario |
| RES-004 — Willesden topology | P0 | Authorised accessible copy of the 2018 feasibility study plus a dated operational track plan | Distinguishes study options from the actual rail layers, bay and surrounding connections | Study reviewed with option/status labels; operational topology independently reconciled |
| RES-005 — Waterloo approaches | P0 | Current technical platform/approach plan and suitable service/stock scenario | Replaces historical enhancement intent with a coherent reference snapshot | Dated bank/route eligibility and approach boundary model |
| RES-006 — Victoria approach groups | P0 | Platform-group eligibility and signalling/topology by a chosen completed stage | Avoids mixing current and future programme phases | One internally consistent reference stage with normal and exceptional movements |
| RES-007 — UK rule extraction | P0 | Applicable full clauses from platform, track, clearance and switches/crossings sources | Provides executable numbers and applicability rather than plausible constants | Rule records with units, issue, locator, conditions, exceptions and review |
| RES-008 — TPF3 capability probe | P0 | Actual query/construction/routing/observation interfaces on a named game/mod build | Establishes which patterns can be represented and measured | Reproducible supported/unsupported/unknown manifest, with tested limits |
| RES-009 — Euston and stock | P1 | Dated approach topology, platform fit and a lawful representative stock-working scenario | Tests useful spare berths, turnround recovery and empty-stock access | Validated synthetic-to-reference mapping without future HS2 assumptions |
| RES-010 — King's Cross/Gasworks | P1 | Completed-scheme topology, portal boundary geometry and applicable route data | Turns the simplification/extra-corridor concept into a reconstructable pattern | Evidence distinguishing announcement, construction and commissioned arrangement |
| RES-011 — Leeds and Edinburgh | P1 | Physical edge/road/berth mapping, exact approach eligibility and dated labels | Validates asymmetric station and longitudinal-berth models | No false independence from labels; explicit shared-resource relationships |
| RES-012 — Reading/London Bridge corridor | P1 | Integrated station, junction, grade-separation and stock-access plans | Tests composition and displaced bottlenecks across several patterns | Coherent region model with common assessment boundaries and train profiles |
| RES-013 — Passenger model calibration | P1 | Suitable observed or synthetic-with-declared-origin demand, paths, dwell and circulation parameters | Prevents invented passenger-capacity predictions | Calibration/uncertainty report with parameter provenance and coverage |
| RES-014 — Inventory reconciliation | P1 | Authoritative dated Bristol and Lime Street platform records | Resolves EV-004/EV-005 before replica construction | Claims reconciled by source/date/scope, not arbitrary preference |
| RES-015 — Smaller London controls | P2 | Technical plans for Charing Cross, Cannon Street, Marylebone and Fenchurch Street | Tests whether simpler patterns meet the same kind of brief | Measured or explicitly abstract control fixtures with exact fidelity labels |
| RES-016 — Wider large/interchange sample | P2 | Investigate Stratford, York, Newcastle, Glasgow Queen Street and East Croydon/Windmill Bridge where suitable evidence exists | Adds other mixed-system, historical and corridor cases | New case records only after primary evidence is actually reviewed |

P0/P1/P2 are project sequencing priorities, not assessments of railway importance or engineering risk.

## 2. Evidence acquisition channels

NESA and regional Timetable Planning Rules are useful official starting points for network capability and planning constraints. Their landing pages have been reviewed, but the specific route diagrams/tables needed here have not been extracted. [S048](10_source_register.md#s048), [S049](10_source_register.md#s049)

Other possible channels include infrastructure-owner project drawings, public planning submissions, station-owner documentation, authorised technical material and first-party project engineering records. Availability, permission and suitability must be checked per document. Do not assume that a public diagram is georeferenced, measured or licensed for redistribution.

The GLA Willesden study is an identified acquisition target, not an invisible source already used in the design. The retrieval attempted for this release exceeded the available PDF tool's size limit. [S023](10_source_register.md#s023)

## 3. Site dossier completion template

A completed technical dossier should answer:

**What date and state?** Existing, proposed, temporary construction stage or commissioned layout; source validity and conflicts.

**What physical railway?** Ports, track roads, platform edges, labels, lengths, horizontal/vertical alignment, structures, electrification/system attributes and geometric accuracy.

**What movements?** Required and permitted routes, point/crossing behaviour, route resources, holding positions, release assumptions and train compatibility.

**What services and stock?** Representative timetable or explicitly synthetic demand, train classes, dwell/turnround, linked workings, empty-stock movements and recovery policies.

**What passenger station?** Entrances, access zones, vertical circulation, accessible paths, transfer demand, useful platform/waiting area and known bottlenecks.

**What game representation?** Demonstrated capabilities, approximations, unsupported components, realised geometry and observed operation.

Do not require every source to answer every question. Do require the composite dossier to show which fields remain unknown and whether that prevents its intended use.

## 4. Turning evidence into rules

For each proposed numerical rule, extract the exact condition and scope before the value. Record units, whether the value is required or recommended, its exceptions and the input information needed to evaluate it.

Reconcile older guidance references with the selected current standard profile. The public catalogue for RIS-7016-INS now identifies issue 2.2, while the passenger-space and vertical-circulation manuals are earlier editions. A citation to an older embedded standard must not silently define the current profile. [S043](10_source_register.md#s043), [S040](10_source_register.md#s040), [S041](10_source_register.md#s041)

Then implement a pure evaluator with positive, negative, boundary-value and missing-input tests. Bind the evaluator to an applicability predicate. A rule that does not apply should report `not_applicable`; a rule missing required inputs should report `unassessed`.

## 5. Turning references into patterns

Extract the operational purpose first: preserve independent through running, enable a turnback, separate a crossing, provide stock access or improve passenger transfer. Identify the minimum topology required for that purpose. Only then extract geometry and allowable variation.

A reference does not need to be copied exactly to improve the generator. It can supply a failure case, a useful boundary condition or a counterexample to a naive rule. For example, a station's label structure can test identity handling even before its throat is reconstructed.

A proposed pattern becomes implemented only after its contract and benchmark oracles are executable. It becomes a real-site reference only after the relevant topology/geometry evidence is adequate. It becomes a validated TPF3 pattern only after engine construction and observation tests pass for the stated scope.

## 6. Immediate Python work that does not need further source access

Implement stable asset/alias records, the split-berth model, explicit rail versus passenger graphs, a route-resource simulator, stock dependencies, snapshot/version handling, the evidence ledger and the result-status model. These can be tested using labelled synthetic fixtures now.

Start the geometry work with complete single-crossover and grouped-terminal assemblies before attempting a full New Street-inspired region. Start the passenger work with explicit walking/queue links and accessible-route checks before adding detailed crowd simulation.

Keep reference acquisition and TPF3 probing parallel to this work. The project should not wait for a perfect national dataset, but neither should it fill missing fields with unlabelled guesses.

## 7. Questions reserved for future design briefs

A reconstruction needs a selected epoch. A generated station needs an intended service pattern, train classes, site footprint and preferred balance between realism and game compression. A passenger simulation needs an accepted level of behavioural detail and a demand source or synthetic scenario.

These questions need not block the present research package. They should become typed brief fields and deliberate defaults, rather than repeated informal questions to Astra during low-level construction.

## 8. Version 0.2 disposition of priority tasks

| Task | Progress this release | Still needed |
|---|---|---|
| RES-001/002 Birmingham | Assessment-method scope and model boundary sharpened | Exact coherent topology, road/edge/berth inventory and permissions |
| RES-003 Clapham | More specific corridor/stock-access research context from S056 | Dated station/approach route and holding inventory |
| RES-004 Willesden | S057/S059 distinguish access-link material and report editions | S023 full report and independent operating track plan; neither acquired |
| RES-005 Waterloo | S055 provides a useful historical technical schematic and linked point group | Current selected-epoch geometry, full movement table and component data |
| RES-007 UK rules | Two scoped numerical clause checks and an unresolved national-interface guard implemented | Broader track/S&C/clearance/transition profile and applicable national rules |
| RES-008 TPF3 | No live game probe available or performed | Real named build, actual query/construction contracts and observed limits |
| Immediate Python work | Executed whole-platform resource scheduling, stock checks, a plain-line primitive and scoped rule tests | Production engine decomposition, full geometry, passenger and game layers |

## 9. Next evidence-to-code increment

The next increment should make one **geometry-to-resource** pipeline real. Select a single crossover and a small bank fan. Acquire a suitable component definition or explicitly author a synthetic component with known geometry. Fit the whole assembly, validate its boundary/clearance conditions, derive resource intervals and run the existing complete-visit tests against that output.

This is a better next step than treating a collection of independently plausible curves as a station generator. It also prevents the operating model from learning an unrealistically favourable resource graph that no track arrangement can realise.

Keep a parallel source-acquisition track for Birmingham and Waterloo, but do not wait for every national diagram. New factual fields should be admitted individually with date, scope and geometry accuracy. A historical diagram remains useful when its epoch is explicit.

For source access, the NESA and operational-rules pages were rechecked but did not yield the site-specific records needed here. The renewed S023 retrieval was unsuccessful. Those are specific acquisition gaps, not claims that the information does not exist.

## 10. Additional implementation questions now exposed

How should the production scheduler trade local greediness against limited backtracking? How will it locate a physical queue rather than an external entry delay? How should a stopped train's braking/acceleration profile affect both route timing and berth clearance? Which berth configurations does the game genuinely support? What conservative envelope is suitable before a vehicle-specific sweep is available?

These questions now have concrete fixture interfaces. Answering them should change typed profiles and tests, not create repeated informal instructions that Astra must remember during every construction operation.

## 11. Version 0.3 progress and next acquisition/implementation gate

The synthetic crossover and single-approach bank now generate geometry-derived lengths and physical/proximity resources. That closes the narrow “no geometry-to-resource link” gap from v0.2, but not the wider requirement for an authentic component catalogue, vehicle gauging, complete station approaches or a game adapter.

| Next task | Required deliverable | Gate before promotion |
|---|---|---|
| Real or explicitly game-qualified component admission | Rights-cleared dimensions, allowed traversals, profile applicability, geometric bounds and source issue | Imported component reproduces its definition and passes independent endpoint/clearance tests |
| Two-approach bank composition | Separate arrival/departure corridor interfaces with complete platform-access movements | No silent reduction of the original four-approach/eight-platform intent |
| Resource-section and stopping model | Physical train front/tail trajectory, stop target, section entries/exits and release assumptions | Independent motion/resource tests; conservative whole-leg baseline retained |
| Vehicle/structure clearance | Named rolling-stock envelope and geometry transforms, with applicability and uncertainty | Continuous three-dimensional checks rather than the synthetic corridor proxy |
| Passenger/civil reservations | Boarding edges, platform/island widths, access structures and buffer/overrun reservations | Geometric fitting cannot remove a required passenger path or boarding interval |
| Full station composition | Two banks, required approach ordering and justified recovery links | Same full brief/scenarios evaluated with all compulsory movements retained |
| Reference promotion | Dated technical station plans and movement/control evidence for selected cases | Promote features individually; no whole-station fidelity from a few fragments |
| Game capability probe | Actual construction/query/routing interfaces on a named build | Reproducible capability manifest and observed realised geometry |

Keep the reference acquisition work parallel. Do not block all Python progress waiting for a national dataset, but do not replace missing evidence with an unlabelled “British” default. The implemented synthetic profile remains a separately named testing tool.

## Version 0.4 backlog update

The selected numerical-import work now has executable records for nominal geometry, several scoped alignment/platform criteria and a partial platform-width guidance calculation. Source locators and limits are in [17](17_uk_numerical_profiles.md). This is partial progress on RES-007, not closure of the full UK-rule task.

The immediate highest-value acquisition is a lawful, dated UK switches-and-crossings dimensional family and a representative passenger vehicle envelope. The existing generic corridor proxy does not establish independent compatibility at the resolved British nominal track interval. Do not loosen that proxy solely to obtain a green result.

National platform height/offset/width, cant/deficiency and transition rules, speed-dependent vertical design, calibrated train performance, actual release/protection semantics and route-specific planning margins remain acquisition/import tasks. Catalogue verification alone is not a numerical import.

The generated two-lead bank and synthetic sectional release now exist. Full multi-bank station composition, downstream queue/holding space, passenger interfaces and the TPF3 capability probe remain open. The old station dossiers retain their dated evidence limits; no new full station topology reconstruction is claimed in this release.

## Version 0.5 backlog update

Vehicle-geometry work now has an executable fixed-pivot body model, a conservative between-pose bound for supported polylines, source-informed dimensions and real published unit lengths in the fit/motion interface. The authentic component-data path now validates and compiles a supplied synthetic record. Neither closes the complete source-data acquisition task.

| Priority task | Current evidence / progress | Next material acquisition or implementation |
|---|---|---|
| Representative passenger vehicle | S060 supplies selected dimensions; missing exact body/pivot data is explicit | A dated outline and pivot/axle/coupling record for a selected variant; authorised source use and review |
| National gauge method | S061/S062 current catalogue/edition verified; full links require registration | Applicable complete method, gauge sections and allowances; no inference from catalogue summaries |
| Authentic UK turnout | S063 is a supplier lead, not a drawing; null-geometry import remains blocked | A particular dated variant's dimensional definition and applicable limits, followed by exact-record review |
| Continuous parent-curve sweep | Exact polyline poses and between-pose bound executed | Bound or eliminate centreline-approximation amplification into body pose |
| 3D/cant envelope | Explicitly outside planar model | Height-dependent outlines, cant/roll transform, track/suspension allowances and structure interfaces |
| Formation clearance | Published unit lengths reach scalar fit/motion, not one rigid body | Individual vehicle/coupler placement and formation-wide swept geometry |
| Two-bank passenger station | Existing crossover/shared bank and route audit are usable subassemblies | Fit the selected site, preserve normal independence, add bounded recovery movements and rerun the fixed service scenarios |

These workstreams can proceed in parallel. Reference-informed game-oriented layouts may use transparent assumptions; strict UK mode must retain unresolved gates. Further station reference research remains valuable when it supplies a concrete movement constraint, component variant, source geometry or failure case rather than another unmeasured passenger map.

## Version 0.6 backlog update

Completed as an offline integration step: two-bank/eight-road composition, four directional external roles, imported synthetic recovery pair placement, combined resource compilation, candidate-bound vehicle/numerical checks, complete multi-group scheduling and guarded decision packets.

The fixed family exposes an actual 1,970 m port span against the original 1,200 m window, plus three approach-ordinate mismatches. The next geometry search should compare an earlier sorting zone, compact recovery connections and alternative fan arrangements. It must retain the original eight road positions and four-short/four-long boarding requirements unless a deliberate brief revision is authorised.

A single selective link does not survive both separate bank-closure scenarios. Investigate a second correctly oriented link or another topology and evaluate its added conflicts and footprint; do not create the absent recovery route by changing only a permission flag.

No new authentic UK component drawing, exact bogie/outline data or standards clause was acquired in this increment. RES-007 and the vehicle/component admission tasks therefore remain open. The 63-source register is retained, not represented as a fresh comprehensive source review.

Keep full formation/cant/dynamic gauging, platform-height/offset and buffer/overrun interfaces, speed-dependent geometry, actual release/protection semantics, spatial queues and game probes visible. More generated platforms are not a substitute for resolving those engineering dependencies.

## Version 0.7 — Gate update and next evidence priorities

The original unpadded **plan contract** now passes for the compact inner-road family: exact approach ports, road/boarding intervals, terminal position markers and concourse reservation. This does not close the full civil/vehicle/platform site gate. The two separate platform-bank recovery scenarios pass for the base formation; upstream fan failure and an overlength receiving train remain explicit failures.

Next priorities are evidence that can invalidate or refine the fitted geometry: an authentic, lawfully usable turnout/diamond dimensional definition with speed/applicability context; complete platform-side geometry and access reservations; exact vehicle outlines and the remaining dynamic/cant allowances. Public numerical floors alone cannot supply those component definitions.

A future component importer must distinguish fixed crossing, switched crossing and slip connectivity without guessing hardware from a schematic X. The v0.7 diamond is deliberately not an approved UK product. [S047](10_source_register.md#s047) remains a requirements-source gate, not an acquired dimensional drawing.

The next operating improvement is physical approach queues and explicitly modelled external continuations. Recovery finishing inside a four-hour test window must not become an implicit acceptable timetable. Maintain the fixed demand and report spillback, restart/holding feasibility and unmet quality targets.

The reference-station dossiers remain evidence acquisition tasks. This compact fictional station does not establish the track plan, control table or capacity of Waterloo, Birmingham or any other real reference.


## Version 0.8 update — targeted sources and next acquisition

RES-007 has progressed: selected platform reference-copy clauses and an explicit draft offset method are now read and executable with their source status. The current full GIRT7020 issue remains behind an authentication step; the public change briefing is not a full-text replacement. Exact current text and associated lower-sector diagrams remain acquisition tasks.

The component work has two stronger leads: a primary WCML field study with typed local component quantities, and an NR60 C-switch drawing identifier cited by a primary stub-switch study. Neither is a complete turnout drawing. Acquire the exact dimensional definition and its supported route/hardware profiles before substituting it for the authored compact specialwork. [S067](10_source_register.md#s067), [S068](10_source_register.md#s068)

Immediate model work should connect platform surfaces to the concourse with explicitly sized, accessible paths, then add vehicle-step/lower-sector interface geometry. Preserve the compact fixed-site and recovery fixtures while testing whether those new requirements make a face or route unusable. Do not turn the present obstacle-distance check into a complete access certificate.


## Version 0.9 — Reprioritised game-oriented backlog

This table supersedes the prior default next step of detailed platform-to-concourse access. Preserve those earlier research questions, but do not let them displace route construction.

| Priority | Next deliverable | Required evidence / acceptance |
|---|---|---|
| P0 | Actual game terrain and construction probe | A named game/mod build, documented or discovered real identifiers, raw observations, supported/unsupported/unknown states and versioned geometry read-back |
| P0 | Connected branch junction | Genuine upstream switching, the existing crossing-cell candidate, connecting branch alignment and downstream merge; no open mandatory ports and no false conflict removal |
| P0 | Reusable station interfaces | Query/define game station ports and usable train lengths; hold station internals fixed; reject direction, elevation or geometry mismatch |
| P1 | General alignment families | Arbitrary boundary tangents, circular/clothoid/canted primitives and explicit speed-profile applicability; numerical/geometry comparison tests |
| P1 | Engine structures and terrain mutation | Available bridge/tunnel assets, portals, support constraints, snapping and terrain reconstruction; staged operations plus realised checks |
| P1 | Game-oriented traffic checks | Verified reservation behaviour, holding lengths, junction priorities and alternative-terminal eligibility; comparison to observed train runs |
| P1 | Realistic component and train defaults | Lawfully available geometry or declared game-oriented approximations; body/formation dimensions and realistic performance provenance |
| P2 | Broad network design | Route hierarchy, two-/four-track transitions, overtaking and selective grade separation after the single corridor/branch path works |

Exact national certification remains an optional stricter track rather than a prerequisite for every reference-inspired game preview. Evidence gaps still remain visible, and unsupported engine behaviours cannot be approximated by silently changing the requested route topology. A source-register entry never substitutes for a successful API probe.

The v0.9 study demonstrates the missing dependency rather than hiding it: its crossing ramps are checked, but no complete branch connection or in-game edit is delivered. [Current handoff](34_v09_execution_and_handoff.md)

## v0.10 next-work update — junction insertion, not more station interiors

The previously open crossing-cell connections now exist within a new, explicit local junction. The next gap is insertion into an actual corridor/terrain context, not another abstract route count. [Implementation boundary](37_v010_execution_and_handoff.md)

| Priority | Task | Required completion evidence |
|---|---|---|
| P0 | Terrain-aware junction placement | Preserved external corridor ports; actual spread-track/civil reservations checked against terrain, protected land and edit authority; all affected resources rebuilt |
| P0 | Real game read/query/build probe when a named build is available | Actual callable functions and supported representations, plus post-build geometry/topology observation; mock manifests stay separate |
| P1 | Practical speed and grade performance | Section-specific permissible/project speeds, verified profile origins, gradient effects and boundary speeds; no silent turnout rating from radius |
| P1 | Usable holding and queue behaviour | Braking to the selected stop, tail position, grade restart, downstream availability and spillback; static length is not sufficient |
| P1 | Admitted specialwork/structure assets | Exact supported geometry and engine representations with source/approximation scope; retain existing evidence gaps |

S070 adds functional reference context only. No new national rule, full turnout drawing, suspension allowance or actual terrain dataset has been imported. Reference-inspired game design remains the normal path; unavailable specialist certification does not justify resuming platform furniture/crowd work as the main milestone.


## v0.11 handoff — terrain composition completed within a restricted study

The connected branch now has a boundary-preserving refit against the original analytic corridor terrain, with main-line targets, protected land, river clearance and explicit structural support gates rechecked. That closes the previously detached local-site experiment for this selected family; it does not import live terrain or implement arbitrary headings.

Next: extend motion with grade-sensitive traction/braking and a real internal stop/restart activity, validate tail clearance at the holding point and preserve the shared merge/exit constraints. Couple those checks to this same terrain-qualified geometry. In parallel implementation tracks, specify actual structure-asset selection and live terrain/construction probes when a named game/mod build is available. Do not resume detailed station internals, crowds or specialist certification as the default next task.

Source acquisition remains open for authentic UK pointwork, more exact representative rolling-stock performance and engine capability evidence. Existing project targets remain explicit rather than silently becoming national standards.
