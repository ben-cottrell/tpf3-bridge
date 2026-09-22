# Component catalogue import and authentic-data admission

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.5.0 · **Date:** 20 September 2026  
**Status:** Executed closed-schema import, unit normalisation, topology/curve checks, reviewed-record gates and synthetic placement through the existing resource compiler. No authentic UK turnout drawing has been imported.

## 1. Why the catalogue must become data

A synthetic function that draws a smooth branch is useful for checking planning algorithms. It is not a permanent substitute for British switches and crossings. The eventual engineer needs actual families, variants, boundary conditions, limitations and evidence that can be updated without rewriting the station planner.

This release provides the first data-driven route into that architecture. A component is a bounded JSON record with explicit ports, route geometry, state mapping, source metadata, units and operating-limit status. The importer distinguishes four separate questions: is the record structurally valid; does the geometry form the declared component; has its source interpretation been reviewed; and may it be used for the requested engineering purpose?

Those questions must not collapse into a single `verified: true` supplied by the file itself.

## 2. The two delivered records

### Authored synthetic reference

[component_import_synthetic.json](evidence/component_import_synthetic.json) expresses a 40 m synthetic turnout in millimetres. It includes normal and diverging route curves, three named ports, a control identity and a declared 1,435 mm gauge. The geometric family remains authored, even though a gauge number is realistic.

The importer normalises it to metres, validates its legal traversals and places it with translation, rotation and reflection. The resulting component is then sent through the existing resource compiler. This is a functioning data-to-geometry-to-resource path, not only a proposed schema.

### External acquisition target

[component_import_pending.json](evidence/component_import_pending.json) records a supplier discovery lead. The official product page identifies turnout, crossover, slip and crossing product families, but the inspected material does not supply a selected UK variant's dimensional definition. [S063](10_source_register.md#s063)

The result is `reference_only_missing_geometry`. No dimensions, route rating or type designation are invented from the supplier's name. The demonstration exports `authentic_component_imported: false`.

This external record is an acquisition target, not a claim that the supplier page describes a particular UK turnout. Its ID and display description state that its variant remains unresolved.

## 3. Current schema

The complete executable example should be used rather than copying this abbreviated explanation into the importer. Every admitted record has these fields:

| Field | Contract |
|---|---|
| `schema_version` | Exact supported version, currently `0.5.0` |
| `component_id` | Stable restricted identifier, not a filesystem path |
| `display_name` | Human description; changes do not alter the geometry hash |
| `origin_kind` | `authored_synthetic` or `external_reference` |
| `source` | Source ID, issue, locator, reuse status and evidence kind |
| `geometry` | Complete supported geometry or explicit null |
| `limits` | Diverging speed value, its evidence type and application-profile label |

Geometry requires one local planar coordinate system, units `m` or `mm`, gauge, three ports, two route definitions, a control identity and switch/crossing descriptors. Each port has an ID, role and two-dimensional coordinate. Each route names its endpoints, required state and Bezier control points.

The importer deliberately supports only a **single three-port normal/reverse turnout contract**. A scissors, diamond, slip, tandem or moving-crossing configuration needs a richer schema. It must not be squeezed into this contract by deleting routes or pretending multiple switches are one control state.

One Bezier per route is also an explicit restriction. Exact circular, piecewise and drawing-derived alignments need additional representations and conversion-error contracts. The existing schema is a tested first import path, not a general-purpose CAD reader.

## 4. Validation sequence

The local JSON reader first enforces a byte budget, rejects duplicate keys and rejects NaN/infinite literals. The record validator rejects unknown fields, malformed IDs, incomplete source metadata, unsupported units/datums and contradictory origin declarations. There is no embedded script, expression evaluator, network fetch or arbitrary command execution.

Unit normalisation follows. Every spatial coordinate and gauge value uses the declared common length unit. The current coordinate system is explicitly level and zero-cant. Supplying a canted or three-dimensional frame is an unsupported-domain error, not a reason to ignore the extra dimensions.

Then validate component geometry: exactly one toe, one normal exit and one reverse exit; both required traversal states; matching route endpoints; bounded nondegenerate curve definitions; consistent approach tangents at the common toe; and a regularity check using the existing derivative-bound routine. The shared port is a declared connection, not a coordinate-coincidence inference.

Normal-to-reverse movement through the toe is not created as an ordinary train path. The imported network uses the established legal-traversal enumerator. A reversal would be a separate operating activity, not an unrestricted Y-junction shortcut.

The regularity check does not determine an approved radius, turnout series or speed. Those are separate component/profile requirements. An internally smooth curve can still be an inappropriate or unsupported railway component.

## 5. Evidence and use states

| Import result | Meaning |
|---|---|
| `accepted_for_synthetic_tests` | Supported authored geometry may enter labelled synthetic tests |
| `reference_only_missing_geometry` | A source/reference record exists but no complete supported geometry is available |
| `quarantined_pending_review` | Geometry parses, but external source/evidence/permission review is incomplete |
| `reviewed_geometry_import` | The exact external record is in the caller's reviewed registry and passes the supported geometry gate |

Even the last state is not full component certification. Source-backed speed-record review is tracked separately, but the application-profile label is not yet an executable applicability predicate. Therefore `speed_usable_for_UK_design` remains false even for a reviewed record. Hardware interfaces and construction authority also remain unresolved. A missing speed stays null. A crossing ratio, general product page or mathematically fitted radius cannot silently generate a rating.

`reviewed_record_hashes` is trusted caller policy outside the imported JSON. The example real-source registry is empty. Tests use explicitly authored external-like fixtures to exercise the admission logic; those are not delivered as newly verified railway products.

The local allowlist binds an exact normalised input record to a review decision. It is **not** a cryptographic attestation by a supplier or proof that a reviewer correctly interpreted a drawing. The production evidence ledger must retain that review's source, scope and decision. External source bytes should be hashed only when they have actually been lawfully obtained.

The importer copies the record before retaining it, so a caller's later mutation cannot silently change the content associated with its stored hash. Changes to an externally reviewed record invalidate its exact-record admission.

## 6. Different hashes answer different questions

`record_hash` covers the complete input record, including source and display information. `geometry_hash` covers canonical metre geometry and declared component metadata. A unit conversion from equivalent millimetre data to metre data preserves the geometry hash in the tested example; a display-name change does not change geometry but does change the reviewed record hash.

A physical component instance also has a placement transform. Translation, rotation and reflection create a placed network whose physical hash is distinct. A station planner must retain the template, normalised geometry, placement and any permitted parameter changes as separate identities.

The current importer does not permit arbitrary stretching of a reviewed external component. A parameterised authentic family will need explicit allowed ranges and boundary/crossing constraints. A fixed drawing cannot be distorted into a new variant merely because a solver needs another metre.

## 7. Placement and resource integration

`place_synthetic()` currently admits only `accepted_for_synthetic_tests`. It uses the supplied geometry; it does not reconstruct dimensions from a hard-coded turnout name. Placement preserves legal endpoints and control-state identity, then validates the resulting network.

The demo constructs normal and reverse `RailPath` objects and compiles the resulting assembly with the existing geometry/resource machinery. Its output contains actual route length bounds, curve checks, component-body occupation and separate control-state requirements. [Executed import results](proof/clearance_results/component_import_results.json)

The legacy `Network.canonical()` format still carries its synthetic pipeline label. This release does not use that older exporter to promote external geometry into an approved game asset. A production authentic-data export needs its own accurately scoped schema and post-import engineering checks.

Quarantined geometry may be inspectable for diagnosis but is not automatically authorised for placement. The eventual world-editing API must enforce admission and authority itself; possession of a parsed Python object is not a construction permission.

## 8. What an authentic UK import must contain next

The specific acquisition target is a lawfully accessible, dated dimensional definition for one UK passenger-rail turnout family—not a national collection of loosely labelled photographs. It must identify the variant, switch/crossing configuration, rail/gauge basis, datums, dimensional geometry and relevant limitations.

The next review should reconcile the drawing's dimensions with its complete route curves and ports, then document any approximation needed by the bridge representation. A manufacturer's drawing may define rail centre lines, working faces or reference datums that are not identical to the game track centreline. That conversion must be explicit.

Operating ratings require their own applicable evidence. Installation conditions, curved variants, permissible transformations, cant/gradient compatibility and interface requirements cannot be guessed from one normal turnout drawing. Hardware/clearance envelopes, maintenance reservations, detection/control groups and game representation follow as separate data domains.

The first complete external import should have positive tests, malformed/contradictory-data tests, endpoint and dimension checks, an independent geometric cross-check, and a version-change test. A claimed new source issue must invalidate the old review rather than inherit its green status.

These are admission requirements on the bridge specification, not a claim to reproduce an infrastructure owner's whole approval process.

## 9. Agent-facing workflow

The proposed high-level flow remains:

**Choose railway purpose and realism profile → resolve component evidence locally → select an admitted family → fit within authorised ranges → compile resources → evaluate services → return material alternatives.**

Astra should not select spline control points or resolve millimetres versus metres during ordinary station design. Missing source evidence should be a compact, specific exception: for example, “A dimensionally complete variant is available, but its diverging-speed applicability is unresolved.” It should not trigger repeated trial construction with guessed ratings.

The current offline runner has no MCP server or game connection. Its import and placement functions are internal engineering interfaces, not automatically exposed world-editing tools.


## Version 0.8 — Typed field quantities are now available

The new [component field references](evidence/component_field_references.json) retain primary-study UK component quantities with local/research scope. They strengthen the acquisition baseline but do not populate the missing complete route geometry. The external placement gate stays closed.

The executed semantic audit rejects a comparison between a source crossing ratio and the synthetic branch-exit tangent, and between a research movable-beam length and a complete turnout span. A scalar cannot silently change its physical meaning while crossing the import boundary. See [30](30_platform_refit_and_component_evidence.md) and [component_evidence_audit.json](proof/interface_results/component_evidence_audit.json).
