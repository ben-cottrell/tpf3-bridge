# Version 0.8 execution evidence and release acceptance

> **Historical/reference chapter.** The [v0.12 implementation specification](IMPLEMENTATION_SPEC.md) governs current scope and supersedes earlier next-step priorities. Detailed physics and further station-internal simulation are optional deferred work; the findings below retain their original scope.

**Version:** 0.8.0 · **Date:** 21 September 2026  
**Executed:** **710 test methods**, including 118 new platform-interface methods. No failures, errors or skipped tests in the acceptance run. Three interface cases and three rail scenarios produce **nine operating comparisons**.

## 1. Delivered scope

The new `railinterface` package adds source-qualified platform dimensions, explicit rail-plane datum conversion, actual boarding-edge and island reservations, general-obstacle checks, bounded facility positioning and a joined platform-to-operation eligibility gate. It also records typed numerical references for a real studied UK switch and a research switch beam without pretending to have obtained their complete component geometry.

The full suite and all seven demo runners were executed in this conversation's Linux runtime. Runtime dependencies are Python standard-library modules. The exact environment and single-run elapsed test time are in [test_report.json](proof/results/test_report.json); they are not Windows/game validation, a production latency target or a measured plan-credit saving.

```sh
cd proof
python run_tests.py
python -m railproof.demo --output results
python -m railgeom.demo --output geometry_results
python -m railops.demo --output sectional_results
python -m railclear.demo --output clearance_results
python -m railstation.demo --output station_results
python -m railcompact.demo --output compact_results
python -m railinterface.demo --output interface_results
```

Keep `evidence/` next to `proof/`. No external PDF, online model, game connection or extra Python package is needed to rerun the supplied authored experiments. Source records contain the interpreted facts and limitations; the third-party documents are linked, not redistributed.

## 2. New tests and interpretation

| Test module | Methods | Principal behaviours |
|---|---:|---|
| `test_interface_reference.py` | 41 | Rail-plane transforms, correct offset datum, design versus build tolerance, reference applicability, speed thresholds, draft-curve branch, taper calculations and invalid inputs |
| `test_interface_platforms.py` | 39 | Actual four-island geometry, all boarding edges, centreline-hull/site screening, obstacle positioning, exact fixed-section interval search, authority/budget limits and joint admission |
| `test_interface_components.py` | 14 | Closed evidence schemas, source/quantity semantics, missing geometry, incomparable lengths/ratios, rejection of self-declared approval and input-copy integrity |
| `test_interface_demo.py` | 24 | Strict fixtures, reproducible output, complete-visit eligibility consequences, source/hash joins, retained unscheduled work, diagnostic mode and absence of fabricated repair |

The 592 preceding methods remain unchanged. Counts describe test methods, not assertions, national standards, complete production requirements or certified components. The existing 75 requirements, 32 pattern families and 41 broad benchmarks still describe more than this proof implements.

Independent checks include inverse coordinate transforms, explicit distance calculations, a separately structured rectangular-facility checker and the earlier independent route/interval result checker. These verify authored model behaviour. They do not establish the adequacy of a source interpretation, complete gauging, crowd capacity or real-world station operation.

## 3. Evidence to inspect

| Artifact | What it records |
|---|---|
| [Current test report](proof/results/test_report.json) | Exact 710 test IDs, outcomes, environment and tested code/fixture/evidence hashes |
| [Current test log](proof/results/test_log.txt) | Individual method results |
| [Historical v0.7 report](proof/results/v07_test_report.json) | Preserved 592-test acceptance record |
| [New fixture](proof/interface_fixtures/release.json) | Fixed compact station, source-qualified profile, infrastructure speeds, facility, authority and scenarios |
| [Platform reference record](evidence/platform_reference.json) | Reviewed values, locators, source-copy/draft/current distinctions and incomplete admission |
| [Component field references](evidence/component_field_references.json) | Typed study-specific quantities with null complete geometry and no universal speed rating |
| [Generated platform geometry](proof/interface_results/platform_geometry.json) | Four islands, eight faces, actual boarding intervals, dimensions, source checks and geometry identities |
| [Site including platforms](proof/interface_results/site_with_platforms.json) | Original boundary, exact approaches, concourse and boarding-slab reservations |
| [Facility search](proof/interface_results/facility_search.json) | Initial failure, fixed-width local repair and narrowly infeasible wider facility |
| [Speed/space sensitivity](proof/interface_results/speed_and_space_sensitivity.json) | Explicit infrastructure-speed and scope changes, not a new train-speed rating |
| [Datum and clause examples](proof/interface_results/datum_and_clause_examples.json) | Correct/wrong datum results, reference branches and draft-derived examples |
| [Component evidence audit](proof/interface_results/component_evidence_audit.json) | Real studied quantities versus synthetic metadata; no false component import |
| [Comparison](proof/interface_results/comparison.md) | All nine rows with required, completed, unscheduled, residual and scheduled-only delay |
| [Recovered A-bank-closure result](proof/interface_results/locally_refitted__bank_a_platforms_closed.json) | Full assignments, claims, effective boarding exclusions and independent verification |
| [Summary](proof/interface_results/summary.json) | Counts, provenance, candidate identity and remaining assessments |
| [Decision packet](proof/interface_results/decision_packet.json) | Local repair outcome, material fixed-section shortfall and no construction authority |
| [Release validation](release_validation.json) | Local links/JSON, source hashes and prior-release comparisons |
| [Manifest](manifest.json) | File-by-file SHA-256 inventory with declared self-exclusions |

## 4. Executed findings

The existing compact track plan now carries four actual **9.09 m** island reservations and eight source-qualified edge positions. Boarding lengths remain 260 m or 320 m, track-end locations remain separate, and the original limited planar site check still passes with those reservations. These values do not complete platform access or train/step compatibility.

A displaced four-metre-wide facility fails the selected general-obstacle reference check at B1. Under the explicitly enabled design-screen policy, B1 is removed from the candidate's boarding opportunities. Normal service can still use other roads, but A-to-B recovery loses its only receiving berth. With A-bank platforms unavailable, only twelve of the twenty-four required visits complete.

The local interval solve moves the same facility **0.955 m** within the authorised island interval. It changes neither the track nor the facility dimensions. The rechecked case restores the missing recovery opportunity, and all twenty-four visits complete in that scenario. This is a synthetic operating result under source-qualified reference checks, not a real station safety decision.

The 4.2 m-wide stress variant needs **110 mm more island width** under the same fixed-section assumptions. Lateral repositioning alone cannot solve it. The result is a narrowly scoped dimensional certificate, not proof that no alternative station or building design could work. A changed footprint, smaller facility or different longitudinal arrangement requires a separate brief or authorised search.

The nine new outputs preserve required demand. A low delay total over twelve surviving visits cannot outrank a complete twenty-four-visit result by silently discarding the missing trains. Completion within the four-hour horizon is also not a punctuality or capacity certificate.

## 5. Hashes and local authority

The rail compile, platform assessment, facility check, vehicle reference and combined design case are explicitly joined. The interface gate recomputes supplied checks and rejects stale/tampered identities rather than trusting a pass flag. Existing railway resources remain unchanged; their identity does not certify the new platform surfaces against vehicle gauges.

The study policy excludes failed boarding faces only when explicitly enabled. That is a planner's candidate filter, not an external instruction to close a real platform. Diagnostic mode retains failed checks without calling the design approved. Missing scoped inputs remain unassessed; no implicit current-UK or game authority is granted.

The new integration suite reruns a smaller two-pair experiment twice and compares all produced files byte-for-byte. The delivered full fixture uses twelve pairs. Determinism here does not guarantee identical floating-point bytes on every Python/platform combination.

## 6. Source progress and remaining acquisition

Five new records bring the source register to **68**. The platform reference copy, current-issue briefing, explicitly draft gauging document and two primary research papers have different evidential roles. The catalogue/current briefing was checked, but the current full platform standard was not read. Draft formulae are not promoted to current rules. [Source register](10_source_register.md#v08-source-acquisition)

The real switch study now supplies meaningful typed radius/crossing information, while the research beam example prevents confusion between part length and whole-turnout length. Neither gives the complete geometry required by the existing importer. `authentic_complete_turnout_imported` remains false. Exact vehicle interfaces and permissible component-speed applicability are still acquisition tasks.

## 7. Regression and packaging

All **64 prior model/test source files** and **207 prior deterministic JSON/Markdown output files** compared with the v0.7 ZIP are byte-identical. Historical model code and test files were not adjusted to accommodate the new interface logic. The expanded runner, updated documentation, release-maintenance tools and current test reports are deliberately outside that frozen comparison.

Local Markdown targets/fragments, finite JSON, exact tested-input hashes, test-count consistency, the package manifest and ZIP integrity are checked. `python verify_release.py --baseline ../TPF3-Bridge_Passenger_Rail_v0.7.zip` repeats the local/baseline checks when the preceding archive is available. Manifest checking excludes its own file and the separate validation record to avoid a recursive hash dependency.

## 8. Acceptance boundary and next step

**Accepted for continued offline development:** explicit dimension datums; source-qualified platform checks attached to generated geometry; actual island/edge reservations; exact bounded facility positioning; boarding-interface restrictions carried into complete train movements; retained demand and reproducible joined evidence.

**Not accepted:** a complete current UK profile, authentic turnout/diamond geometry, complete platform-to-concourse access, dynamic/3D platform gauging, boarding step/door compatibility, passenger-capacity or emergency certification, physical approach queues, a production MCP server, TPF3 construction or measured model-plan savings.

The next geometric/functional step is **platform-to-concourse access**, including continuous accessible paths and the space those paths consume. Keep current-standard reconciliation and exact component acquisition active alongside that implementation.
