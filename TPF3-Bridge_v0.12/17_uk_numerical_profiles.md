# UK numerical profiles: source-backed values, design targets and admission

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.4.0 · **Research date:** 20 September 2026  
**Status:** Selected numerical lookups, clause checks and guidance calculations implemented and tested. The complete GB engineering profile is not yet populated. The generated specialwork remains synthetic.

## 1. Product requirement: numbers must eventually describe a British railway

The production bridge is intended to generate a credible UK network, not merely demonstrate a general graph planner. Therefore authentic dimensions, speed-dependent alignment design, vehicle compatibility, platform interfaces and operating parameters are product requirements. Synthetic values are useful regression inputs, but are not the final default engineering catalogue.

The architecture already separated numerical rules from model code. This release makes that separation executable and visible. The parameter register is [evidence/uk_parameters.json](evidence/uk_parameters.json); the evaluators are in [proof/railops/uk_profiles.py](proof/railops/uk_profiles.py). These values are not silently substituted into the old component generator. Doing so would disguise unresolved geometry, clearance and operating assumptions.

A generated design needs both **plausibility** and **traceability**. “A number often used on British railways” is insufficient when it might describe a maintenance intervention threshold, an exceptional historical arrangement, a nominal reference, or a limit applying only to a particular new-build case.

## 2. Numerical types are part of the contract

| Numerical kind | How the engine may use it | What it must not imply |
|---|---|---|
| Applicable requirement | Evaluate the specific condition after resolving scope | Passing one condition approves a complete design |
| Nominal reference | Initialise a candidate or describe an intended reference system | Every layout using that number has adequate clearance |
| Guidance parameter | Calculate a scoped design recommendation | The result is a mandatory universal minimum |
| Verified component geometry | Instantiate the exact admitted family/variant | Any similarly named or stretched component is equivalent |
| Measured local value | Reconstruct the dated feature within recorded accuracy | The same value is a national rule |
| Project-selected target | Express the user's intended service or aesthetic performance | The target is achieved or supported by every asset |
| Calibrated game parameter | Predict the named engine/build's observed behaviour | The real railway behaves identically |
| Synthetic test input | Exercise an algorithm and its failure boundaries | The input has acquired engineering authority by passing tests |

The runtime must retain this type alongside the value. A preference score may favour a project target; it cannot trade away a failed mandatory constraint by quietly reclassifying it as a preference.

## 3. Selected imported numerical records

The Infrastructure NTSN records below are narrowly scoped extractions from **Issue 2**, with exact locators in the register. Scope includes the explicitly selected GB case, not an automatic Northern Ireland, metro, heritage or HS2 profile. [S058](10_source_register.md#s058)

| Record | Value | Imported scope / locator |
|---|---:|---|
| Nominal track gauge | 1,435 mm | 4.2.4.1(1) |
| GB nominal track centres | 3.4 m | 7.7.17.3(1), straight or radius ≥400 m; reductions remain unresolved |
| New-line horizontal-radius floor | 150 m | 4.2.3.4(1); not a speed-selected design radius |
| New coupling-platform gradient | ≤0.0025 | 4.2.3.3(1), new-line passenger platforms with regular attachment/detachment |
| Vertical-curve floors | Crest 500 m; sag 900 m | 4.2.3.5(1), excluding marshalling humps |
| Stopping-platform cant | ≤110 mm | 4.2.4.2(2); existing v0.2 evaluator |
| New-line platform radius | ≥300 m | 4.2.9.4(1); existing v0.2 evaluator |

The register contains **eleven entries**, including the centres-radius applicability threshold and two passenger-guidance parameters. It is a small selected set, not eleven complete engineering domains.

The gradient conversion is explicit: `0.0025 m/m = 2.5 mm/m = 0.25% = 1 in 400`. The implementation receives a nonnegative gradient **magnitude** for that check. Alignment direction and signed gradient remain separate data.

### 3.1 The engine must distinguish different successful answers

`nominal_gauge()` and `gb_track_centres()` return `reference_value`, not `pass`. A passed radius check returns its own rule ID and leaves other checks unresolved. Unknown scope returns `unassessed`; excluded scope returns `not_applicable`.

The examples deliberately demonstrate that a curve can meet the general new-line floor yet fail the platform-adjacent criterion. Neither result establishes a speed rating. See [executed numerical checks](proof/sectional_results/uk_numerical_checks.json).

### 3.2 Checks also run on the generated geometry

The new runner applies selected scalar checks to the compiled bank, not only to standalone examples. Its radius-bound result, platform straightness and declared cant are linked to the actual compile hash in [generated-bank checks](proof/sectional_results/generated_bank_uk_checks.json). This assesses those narrow properties of the synthetic geometry; component authenticity, speed suitability and full national interfaces remain unresolved.

### 3.3 What is not being inferred

The release does not derive a UK turnout speed from its crossing angle, select a universal maximum platform gradient, or invent national platform-height/offset values. Full GIRT7020 issue 2.1 access was attempted through its published link and reached a registration/login page. Its current catalogue was reviewed, but the full numerical national interface was not imported. [S044](10_source_register.md#s044)

Missing values are acquisition tasks, not evidence that realistic UK modelling is unattainable. The relevant records remain explicit so the next approved import can replace an unresolved field without redesigning the whole engine.

## 4. A real number exposes the present clearance model's limit

The release creates two straight test tracks using the resolved GB nominal centre interval. It then runs the existing v0.3 corridor proxy unchanged. That proxy uses a 1.75 m half-width for each track plus a 0.5 m pair allowance, producing a 4.0 m separation requirement. Those proxy dimensions were authored for tests; they were not extracted from a GB vehicle gauge.

The result is intentional: the nominal lookup resolves, but the proxy generates a shared proximity exclusion. It does **not** establish independent passage, and actual vehicle clearance remains unassessed. [Executed spacing test](proof/sectional_results/gb_spacing_proxy_trial.json)

The correct repair is not to shrink the proxy until the desired diagram passes. The next clearance model needs vehicle width and shape, bogie centres, body overhang, curvature, cant and the applicable dynamic allowances. It must also distinguish a structure interface from an adjacent moving vehicle and from a platform edge.

This example is an important regression test for the eventual implementation: **source-backed geometry inputs and source-backed clearance methods are separate dependencies**. A realistic nominal number cannot validate an unrealistic envelope.

The test does not suggest that the nominal British reference is unusable. It shows that the current generic proxy is insufficient to establish the relevant compatibility.

## 5. Passenger-platform guidance starts becoming numerical

Network Rail's station-capacity guidance supplies method-two calculations where passengers wait on the platform. For each carriage block, the implemented Zone B helper uses `passengers × 0.93 / block_length`, while Zone C uses `peak_five_minute_circulation / (5 × 40)`. Circulation demand must exclude people already counted in B. These are scoped guidance calculations, not a complete platform-width approval. [S040, section 3.3.2, printed pp. 41–43](10_source_register.md#s040)

The executed synthetic demand example supplies eighty boarding/alighting passengers over a twenty-metre block and two hundred circulating passengers over five minutes. It yields **3.72 m for B and 1.00 m for C**. Those are calculated component widths, not a claim that a 4.72 m platform is sufficient.

Zone A, activity/obstacle space, the opposite face of an island, stairs/lifts, useful waiting area, access rules and demand validation are deliberately outside that helper's approval scope. It returns `full_platform_width_status: unassessed`.

The generator should eventually distribute demand across carriage blocks rather than assume uniform loading. A train's stopping target, a staircase and a congested transfer route can affect different blocks. The future platform solver should keep that spatial relationship intact when it moves a track or changes train formation.

## 6. Three proposed design modes, now with an admission check

### Synthetic regression

Use artificial values to test algorithms, including deliberately tight and invalid cases. The result must keep its synthetic label. Existing regression outputs remain unchanged and useful after realistic profiles are introduced.

### GB reference-inspired design

Use verified numbers where available and declared approximations elsewhere. This is appropriate for developing a game-oriented UK appearance and operating logic, provided the output identifies the approximations. It must not be labelled strict rule-compliant.

### GB rules-strict design

Required numerical fields, component evidence and compatibility checks must be resolved before the relevant strict stage is admitted. The current synthetic catalogue blocks that gate. A user requesting this mode must not silently receive a synthetic fallback.

The implemented `admission()` function checks only this input gate. Even an all-resolved input set does not authorise construction, grant real-world approval or prove that an omitted requirement does not exist. `construction_authorised` is always false in this offline interface.

The long-term product must allow the user to choose a declared realism/compression profile once, not repeatedly approve arbitrary exceptions for every track segment.

## 7. Parameter resolution and priority

For a future production request, Python should resolve the following chain locally:

**Station/route function → geographic and system profile → construction era/state → applicable rule set → component family → rolling-stock profile → design targets → engine representation.**

Resolution has to preserve conflicts. An exceptional local asset must not overwrite a national default for every future build. A later rule issue must not be applied retroactively to an explicitly historical reconstruction without a deliberate brief change. A manufacturer catalogue value must remain tied to that family and variant.

The data model should retain `source_id`, `source_issue`, `clause`, `valid_period`, `kind`, `value`, `units`, `applicability`, `exceptions`, `review_status`, `origin_accuracy` and `parameter_dependencies`. The current register implements the subset needed for the selected rules; historic validity and full exception resolution remain production tasks.

Where different units are useful for humans, display both: mph and m/s, mm/m and gradient fraction, metres and chainage. The internal quantity must have a single unambiguous unit. Do not interpret `1:20` as a gradient, crossing angle or scale factor without a typed quantity.

## 8. What realistic production defaults still need

| Workstream | Required information | Intended executable output |
|---|---|---|
| Switches and crossings | Dated, permitted dimensional families; route shapes and component applicability | Catalogue instances with validated ports, curvature, hardware envelope and supported movement ratings |
| Vehicle compatibility | Representative formations, body/bogie geometry, gauge profiles and allowances | Swept-envelope checks and train/platform interface evaluation |
| Running alignment | Speed/cant/deficiency/transition relationships for the selected profile | Speed-aware horizontal alignment and transition solver |
| Vertical alignment | Speed-dependent criteria and combined horizontal/vertical constraints | Appropriate crest/sag curves, gradients and combined checks |
| Platforms | Applicable GB height/offset/width and accessibility rules | Complete boarding and circulation geometry, not only scalar length |
| Operations | Applicable release/protection assumptions and representative train performance | Calibrated route occupation, braking and stopping behaviour |
| Timetable planning | Dated, route-specific planning margins and permitted stock activities | Service scenarios that distinguish planning rules from physical motion |
| Game calibration | Actual constructed geometry and observed running behaviour | Explicit approximation map and error/coverage report |

The order of implementation should now favour vehicle-envelope and component evidence before attempting large-scale dense throats at realistic spacing. Detailed grades, electrification, structures and passenger interfaces remain necessary for the final network, even when not required by this small flat-site proof.

## 9. Performance inputs are still project choices

The new motion experiment uses a route target of **15 mph**, converted to **6.7056 m/s**, with acceleration 0.6 m/s² and braking 0.7 m/s². These are declared project inputs, not verified specifications for a particular British train or a turnout speed approval. The speed target is not inferred from the synthetic curve's slope.

The physics model is level-track constant acceleration/braking with a single route-wide speed cap. A future performance profile must add rolling resistance, power/tractive effort, formation mass, gradient, speed-dependent limits and whatever adhesion/jerk fidelity is appropriate. It must separate comfort or project targets from hard traction capability.

The architectural requirement is that Python adjusts geometry to the intended speed and vehicle, or reports the unresolved conflict. It should not solve a tight fan by quietly lowering the speed without authority.

## 10. Acceptance of this numerical-profile step

Accepted: source-linked values, scoped evaluators, nominal versus pass semantics, unit checks, missing-input behaviour, a partial passenger-width helper and a realistic-spacing proxy mismatch test. The test suite also checks that passing a looser radius rule does not override a stricter platform rule.

Not accepted: a complete GB profile, an authentic turnout library, complete gauging, a speed-certified station design or an approved eight-platform layout. These are explicit remaining implementation gates—not permanently synthetic substitutes for the intended UK railway engine.

## Version 0.5 addition: vehicle dimensions are not a national default

The eleven national-reference/guidance records above are retained unchanged. A separate manufacturer-dimension record is added for a representative passenger-vehicle study; it is not appended as four new UK-wide engineering rules. [Vehicle model](20_vehicle_envelopes_and_clearance.md), [source record](evidence/vehicle_reference.json)

The new static calculation explains body spacing through actual width and pivot/body geometry. It does not retrofit a smaller arbitrary proxy into the old scheduler. Bogie spacing and nominal-length interpretation remain explicitly assumed, and dynamic/3D gauging remains unresolved. Source-backed total unit lengths now affect scalar platform fit and tail timing without being mistaken for single-body geometry.

The component importer likewise separates a realistic gauge number from authentic turnout geometry. Its pending external record cannot supply a UK variant, route-speed rating or permissive fallback by itself. [Import contract](21_component_catalogue_import.md)

## Version 0.6 integration status

The existing radius/cant evaluators now also attach to the composed two-bank station with its actual compile hash. Full-unit lengths from the retained manufacturer record drive station fit and tail timing. The body assumptions, synthetic component origin and strict-UK missing-input gate remain explicit in the same candidate assessment. [Assessment](proof/station_results/a_to_b__assessment.json)

This increment imports no additional numerical clauses or authentic components. It must not be read as a complete national profile simply because the earlier partial checks now run on eight platform roads.

## Version 0.7 — Realism is retained as an unresolved hard gate

The compact geometry search keeps its 300 m **project radius target**; it does not lower that target to make the original plan fit. Its approximately 312.619 m bound is a mathematical property of the authored geometry, not an authentic turnout-speed rating. The 12 m inner-road interval is part of the station brief, not a new national track-centre value.

RSSB's [S047 catalogue entry](10_source_register.md#s047) was rechecked during this increment. Its scope states that the switches-and-crossings requirements are additional to INF NTSN and GCRT5021 requirements. No full new clause or dimensional drawing was imported. The output's strict-profile admission therefore remains blocked even when selected radius/cant and plan checks pass.

The next component/diamond and full platform-interface import must participate in candidate invalidation. A source-backed hardware envelope that cannot fit the present synthetic arrangement should force redesign or an explicit failed check, not a relaxed envelope or an undocumented change to the original brief.


## Version 0.8 — More realistic values with stronger datum typing

The separate [platform reference register](evidence/platform_reference.json) adds selected height, rail-edge offset, taper and width/obstacle values from an actually reviewed publisher-hosted reference copy. Current catalogue and briefing continuity are retained separately; an explicitly draft-derived curve helper is labelled draft in every result. [29](29_uk_platform_datums_and_interfaces.md) describes the evidence levels.

These values now generate the compact station's eight boarding edges, yielding four 9.09 m islands at the original twelve-metre project track spacing. They also constrain a facility re-fit and affect declared platform eligibility. This is not just another isolated scalar example. The final GB profile still needs exact current-source reconciliation, specialwork, complete gauging and platform/door interfaces.
