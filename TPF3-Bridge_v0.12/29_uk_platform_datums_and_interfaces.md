# UK platform datums and source-qualified interface geometry

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.8.0 · **Research date:** 21 September 2026  
**Status:** Executed rail-plane transformations, selected reference-clause checks, four island reservations and eight boarding edges on the compact station. Current full national-standard reconciliation, complete platforms and vehicle interfaces remain unassessed.

## 1. What this increment changes

The earlier station carried boarding lengths but did not place its coping edges or platform surfaces. Python now constructs those interfaces from the actual platform-road coordinates. The important change is not replacing one constant with 915: the software must know what a dimension measures, which direction it is measured in, which condition selects it, and which source version supports it.

The implementation is `proof/railinterface/`. It does not overwrite the frozen proof modules. Its [reference record](evidence/platform_reference.json) and [executed examples](proof/interface_results/datum_and_clause_examples.json) keep numeric agreement separate from current engineering admission.

## 2. Evidence resolved, and evidence not resolved

Three evidence levels must remain distinct. The publisher-hosted GIRT7020 copy is headed Issue Two, June 2022, but was obtained from a public consultation-document endpoint. Selected platform clauses and their guidance were read. It is a usable **reference copy**, not proof that the exact current full document has been reviewed. [S064](10_source_register.md#s064)

The live catalogue identifies Issue 2.1. Its public briefing describes the 2025 changes as non-technical and explains the transfer/status of platform-width and edge-marking material. The current full-standard link still led to authentication. The briefing supports continuity but does not reconcile every line of the consultation-hosted copy with the published current text. [S044](10_source_register.md#s044), [S065](10_source_register.md#s065)

The detailed running-edge datum and curved-offset example were read in a different document explicitly marked **GIRT7073 Issue Three Draft 1l**. Its status is retained, including in every computed curved-offset result. The current GIRT7073 catalogue is not the draft. [S066](10_source_register.md#s066), [S045](10_source_register.md#s045)

Consequently a new evaluator can return `reference_clause_pass` while `current_uk_compliance` remains `unassessed`. These statements answer different questions. No external record supplies construction authority.

## 3. The coordinate mistake the engine now prevents

The reviewed platform guidance describes the commonly applicable offset range relative to the **adjacent rail**, not the track centre. The related draft defines the running-edge reference at 14 mm below the rail head. Height and offset use directions perpendicular and parallel to the rail plane respectively. [S064, 2.1–2.2](10_source_register.md#s064), [S066, C.1.1](10_source_register.md#s066)

For the declared straight, level, nominal-gauge example:

- Half the 1,435 mm gauge is 717.5 mm.
- The project selects the guidance midpoint, 737.5 mm, as its rail-edge offset.
- The resulting centreline-to-platform-face distance is **1,455 mm**, not 737.5 mm.

The gauge value is retained from the earlier INF NTSN record. The midpoint is a selected reference-informed setting, not an assertion that every platform must use it. [S058](10_source_register.md#s058), [S064](10_source_register.md#s064)

Using 737.5 mm from the centreline instead would leave only 20 mm from the modelled adjacent running edge. The executable wrong-datum fixture rejects that result. A unit conversion can be numerically correct while a datum conversion is fundamentally wrong.

## 4. Explicit mathematical transform

`RailSection` defines the gauge midpoint projected onto the rail-top plane, a world-space origin, an explicitly supplied rail-plane angle, and a signed platform side. It does not treat the gauge as the distance between rail-head centres.

Let `g` be gauge, `o` the nearest-running-edge offset, `h` the perpendicular height, and `sigma` either −1 or +1. After conversion to metres:

\[
\ell=\sigma(g/2+o),\qquad v=h.
\]

For rail-plane angle `phi` and section origin `(y0,z0)`:

\[
y=y_0+\ell\cos\phi-v\sin\phi,
\qquad
z=z_0+\ell\sin\phi+v\cos\phi.
\]

The inverse transform recovers the rail-edge offset and perpendicular height. Round-trip and distance-preservation tests cover both sides, translations and signed rotations.

This is an authored coordinate transform, **not** a complete canted-platform design method. In particular, the code does not derive a cant angle by dividing cant by nominal gauge. A production transform needs its proper rail/contact datum and cant base. The whole-station platform generator presently admits only straight, level, zero-cant boarding alignments; it rejects a canted or curved input rather than quietly treating it as level.

## 5. Selected executable reference checks

The imported reference values are intentionally scoped:

| Check | Implemented reference behaviour | Important boundary |
|---|---|---|
| Normal design height | 915 mm with the reference −15/+0 interval | A distinct legacy-stock branch uses its own lower tolerance |
| Extra height allowance | A separate build/maintenance branch | It is unavailable to the design branch; its linked lower-sector condition must be explicitly confirmed |
| Lateral offset | Compare with an explicitly resolved minimum plus the reference positive tolerance | No global hard-coded minimum for every curve or special route |
| Usable platform width | One/two faces and the permissible/enhanced speed on each adjacent line select the reference minimum | The simulated train's current speed does not select the rule |
| General obstacle spacing | Check both distances between an island's faces and the obstacle | A gross-width pass is not a pinch-point pass |
| Height/offset taper | Calculate a minimum longitudinal distance from the selected slope ratio | Coping-unit compatibility and the full transition remain separate |

The reference-copy locators are 2.1.1–2.1.4, 2.2.1–2.2.2, 2.3.1, 2.3.3 and 2.3.4. The extra height allowance is explicitly excluded from design by G2.1.13. Narrow extensions, constrained columns and other exceptional reductions are **not automatically applied**. [S064](10_source_register.md#s064)

Thus a 925 mm test height fails the normal design check. It does not pass simply because the user or software calls the extra ten millimetres a tolerance. The separately selected build/maintenance check remains unassessed without its linked adjustment confirmation. Neither branch completes lower-sector gauging.

The code distinguishes `not_applicable`, missing-input `unassessed`, reference agreement and reference disagreement. A numerical zero, `False`, and unknown are not interchangeable.

## 6. Curved-offset example: useful but explicitly draft-derived

The draft's standard-case table has a constant branch at and above 360 m radius, and a formula `658 + 26000/R` mm between 160 m and 360 m. Special-route cases and smaller radii are outside the implemented helper. [S066, C.1.1](10_source_register.md#s066)

The formula is evaluated unrounded. The nearby example table contains rounded displayed values; it is not treated as a second interpolation rule. The source's branch at 360 m is preserved. The result carries `draft_reference_value`, not a current-rule pass.

The 360 m threshold concerns this platform-offset example. It must not be confused with the 400 m applicability threshold of the separate nominal track-centre reference, or the new-line platform-radius criterion. Different numbers can legitimately describe different questions.

No curved platform is generated in this release. The helper is a source-provenance and formula-regression tool pending current-document reconciliation and a richer platform/gauge model.

## 7. Building the compact station's platform surfaces

The generator reads the actual compiled boarding intervals, marker positions and track geometry. It pairs A1/A2, A3/A4, B1/B2 and B3/B4 into four islands. Each pair already shares its boarding start/end in the frozen brief. The central A4–B1 corridor remains free of a platform island, preserving the location of the compact recovery connection.

At the twelve-metre project track spacing, the width between the two boarding faces is:

\[
W=12-2(0.7175+0.7375)=9.09\;\mathrm{m}.
\]

This width is derived from the source-qualified datum choice and the **project's** twelve-metre spacing. Twelve metres is not being promoted to a national running-track interval.

All eight edges retain their 260 m or 320 m boarding lengths. They end at x=970 m, not the track-end marker at x=1000 m. The surfaces occupy only the boarding-slab reservation; the extra thirty metres of track cannot create extra boarding length.

The code checks the incoming lead as well as the storage edge. This matters because the boarding interval begins five metres before the rear stopping marker. A fictitious straight extension of the storage road would not establish the geometry of those first five metres.

Each surface is screened against every rail centreline control hull. In the delivered candidate all surfaces are disjoint from those hulls, and the original site/approach/concourse reservation check still passes. This establishes a limited planar space relationship, **not** dynamic vehicle clearance to the coping or a platform foundation.

## 8. Source minima are not a finished passenger station

A 9.09 m island can satisfy the selected geometric minima and still have inadequate waiting space, badly placed access, no accessible route, unsuitable platform ends or an unresolved train/step interface. The current surface model does not evaluate tactile paving, coping construction, drainage, lighting, shelters, foundations or emergency evacuation.

The existing single-body width study is deliberately not converted into a claimed boarding gap. Manufacturer maximum width, a rectangular plan body and a rail-plane coping coordinate do not identify the actual door-step outline, height, suspension position or accessibility condition.

The specification retains distinct dependencies for static structure location, vehicle lower-sector outline, swept/dynamic envelope, stopping/door geometry and passenger circulation. Passing one cannot remove a failure or unknown in the others.

## 9. Production contracts strengthened by this release

The full bridge should retain typed `measurement_datum`, `measurement_direction`, `quantity_kind`, `design_or_maintenance_stage`, `source_issue` and `applicability` fields. A schema carrying only a floating value and the label “UK” is inadequate.

A permissible/enhanced line speed belongs to infrastructure. A service's target speed belongs to its operating/performance profile. Changing one must not silently change the other.

Evidence identity and geometry identity are separate. The platform assessment binds the actual compile hash, source/reference hash and profile hash. Moving furniture creates a different design-case hash even when every rail edge is unchanged. The current hashes provide reproducibility and stale-input checks, not cryptographic certification of a reviewer or a railway design.

For production use, consolidate these evaluators into the versioned engineering-profile resolver rather than maintain a permanently separate “v0.8 rules” subsystem. The frozen modules are regression evidence, not the intended final application architecture.
