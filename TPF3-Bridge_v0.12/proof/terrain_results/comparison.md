# Terrain-aware junction results — v0.11

Same synthetic river/ridge terrain and protected land as v0.9. New refitted physical network; no inherited terrain approval.

## Placement search

| Layout | Offset (m) | Form | Accepted | Principal failures |
|---|---:|---|---|---|
| original_toes | 0 | flat | False | reservation_intersects_protected_land:0; specialwork_structure_interface_unsupported; track_enters_protected_land:0 |
| original_toes | 0 | flyover | False | reservation_intersects_protected_land:0; specialwork_structure_interface_unsupported; track_enters_protected_land:0 |
| original_toes | 0 | diveunder | False | reservation_intersects_protected_land:0; specialwork_structure_interface_unsupported; track_enters_protected_land:0 |
| original_toes | 180 | flat | False | main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 180 | flyover | False | main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 180 | diveunder | False | main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 280 | flat | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 280 | flyover | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 280 | diveunder | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 360 | flat | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 360 | flyover | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| original_toes | 360 | diveunder | False | main_jerk_bound; main_lateral_accel_bound; main_radius_bound; specialwork_structure_interface_unsupported |
| east_shifted_toes | 0 | flat | False | reservation_intersects_protected_land:0; track_enters_protected_land:0 |
| east_shifted_toes | 0 | flyover | False | reservation_intersects_protected_land:0; track_enters_protected_land:0 |
| east_shifted_toes | 0 | diveunder | False | reservation_intersects_protected_land:0; track_enters_protected_land:0 |
| east_shifted_toes | 180 | flat | True | None in assessed scope |
| east_shifted_toes | 180 | flyover | True | None in assessed scope |
| east_shifted_toes | 180 | diveunder | True | None in assessed scope |
| east_shifted_toes | 280 | flat | True | None in assessed scope |
| east_shifted_toes | 280 | flyover | True | None in assessed scope |
| east_shifted_toes | 280 | diveunder | True | None in assessed scope |
| east_shifted_toes | 360 | flat | False | main_radius_bound |
| east_shifted_toes | 360 | flyover | False | main_radius_bound |
| east_shifted_toes | 360 | diveunder | False | main_radius_bound |

## Selected terrain estimates

Track metres are summed over unique physical edges, not railway service routes. They are not numbers of bridge/tunnel assets.

| Form | Offset (m) | Tunnel track metres | Elevated track metres | Reserved rectangle-union area (m²) |
|---|---:|---:|---:|---:|
| flat | 280 | 436.452 | 500.499 | 265131.8 |
| flyover | 280 | 436.452 | 704.188 | 268249.9 |
| diveunder | 280 | 1083.258 | 500.499 | 281684.9 |

## Operations

Delay is entry delay over scheduled trains only. Whole-pass greedy planning; grade-sensitive traction and internal waiting are unassessed.

| Scenario | Form | Completed / required | Unscheduled | Residual | Entry delay (s) |
|---|---|---:|---:|---:|---:|
| nominal | flat | 24 / 24 | 0 | 0 | 9826.094 |
| crossing_pulse | flat | 2 / 2 | 0 | 0 | 49.714 |
| merge_pulse | flat | 2 / 2 | 0 | 0 | 337.362 |
| downstream_blocked | flat | 2 / 2 | 0 | 0 | 2735.418 |
| nominal | flyover | 24 / 24 | 0 | 0 | 9826.494 |
| crossing_pulse | flyover | 2 / 2 | 0 | 0 | 0.000 |
| merge_pulse | flyover | 2 / 2 | 0 | 0 | 337.378 |
| downstream_blocked | flyover | 2 / 2 | 0 | 0 | 2735.404 |
| nominal | diveunder | 24 / 24 | 0 | 0 | 9826.494 |
| crossing_pulse | diveunder | 2 / 2 | 0 | 0 | 0.000 |
| merge_pulse | diveunder | 2 / 2 | 0 | 0 | 337.378 |
| downstream_blocked | diveunder | 2 / 2 | 0 | 0 | 2735.404 |

No actual terrain, station, game or external service was edited. Civil outputs remain reservations, not finished structure assets.
