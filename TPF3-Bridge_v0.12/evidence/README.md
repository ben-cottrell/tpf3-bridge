# Evidence data — v0.2

These are original authored records linked to the [source register](../10_source_register.md). They are not copies of third-party maps or standards.

| File | Purpose |
|---|---|
| [claims.json](claims.json) | Seven feature-level research claims and their scope |
| [reference_fragments.json](reference_fragments.json) | Historical Waterloo names/point relationships and scoped Birmingham/Willesden records |
| [rules.json](rules.json) | Two numerical clause evaluators plus an unresolved national-interface guard |

`record` references containing `#id` refer to object IDs inside JSON, not browser-resolvable HTML anchors. Coordinates, full route tables, observed states and source-byte hashes remain null where not acquired. Those nulls must not become zero coordinates, normal point states or passed engineering checks.

The eight-platform worked fixture is separate and wholly synthetic. It does not silently fill the gaps in these reference records.

## Version 0.3 additions

[component_catalogue.json](component_catalogue.json) records the authored synthetic centreline component and demonstration parameters. Its values are not imported UK engineering requirements. [v03_reinspection.json](v03_reinspection.json) records the limited new review scope for existing source IDs; no additional source count or external-source hash is claimed.

The executable geometry fixture is [release.json](../proof/geometry_fixtures/release.json). Geometry/resource provenance is exported with the compiled assemblies. The main evidence ledger and prior rule records are retained, not silently upgraded by the new synthetic tests.

## v0.4 numerical evidence

[uk_parameters.json](uk_parameters.json) is the executable selected numerical register; [v04_reinspection.json](v04_reinspection.json) records actual source-review scope. Values are typed as nominal references, scoped criteria or guidance. The synthetic component catalogue remains unchanged. Missing national interfaces, vehicle envelopes and real turnout families remain explicit.

## Version 0.5 records

- [Vehicle reference](vehicle_reference.json): four manufacturer-catalogue quantities and explicit missing geometry; source S060.
- [Synthetic component input](component_import_synthetic.json): authored millimetre geometry, not a UK turnout drawing.
- [External component target](component_import_pending.json): supplier discovery evidence only; geometry and speed remain null.
- [Review log](v05_reinspection.json): four new primary-source records, actual reviewed scope and access limits.

The new vehicle and component facts are not national-rule entries. Exact-record review hashes are a caller policy; no imported `verified` flag grants authority. Remote source bytes are not included or assigned invented hashes.
