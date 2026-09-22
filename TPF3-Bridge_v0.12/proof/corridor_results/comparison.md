# v0.9 corridor comparison

Executed on a declared synthetic terrain. Amounts are planning estimates, not construction bills or capacity measurements.

| Offset m | Rail plateau m | Accepted | Mean track length m | Tunnel m | Elevated m | Earthwork m³ | Pareto |
|---:|---:|---|---:|---:|---:|---:|---|
| 0 | 20 | True | 6000.000 | 600.000 | 250.000 | 53763.412 | True |
| 0 | 24 | True | 6000.013 | 520.000 | 250.000 | 93139.190 | True |
| 0 | 28 | True | 6000.051 | 440.000 | 1440.000 | 102936.859 | True |
| 180 | 20 | True | 6025.550 | 400.000 | 250.385 | 62917.869 | True |
| 180 | 24 | True | 6025.563 | 160.000 | 250.385 | 113718.425 | True |
| 180 | 28 | True | 6025.600 | 0.000 | 1522.199 | 114511.066 | True |
| 280 | 20 | True | 6061.280 | 0.000 | 250.929 | 50421.792 | True |
| 280 | 24 | True | 6061.292 | 0.000 | 250.929 | 104226.629 | False |
| 280 | 28 | True | 6061.329 | 0.000 | 2005.303 | 108592.083 | False |
| -280 | 20 | False | 6061.280 | 0.000 | 250.929 | 50421.792 | False |
| -280 | 24 | False | 6061.292 | 0.000 | 250.929 | 104226.629 | False |
| -280 | 28 | False | 6061.329 | 0.000 | 2005.303 | 108592.083 | False |

## Crossing cells

| Mode | Ramp m | Whole span m | Project geometry | Crossing separation m | Shared main conflicts |
|---|---:|---:|---|---:|---:|
| flat | 600 | 1300.0 | True | 0.0 | 2 |
| flat | 750 | 1600.0 | True | 0.0 | 2 |
| flat | 900 | 1900.0 | True | 0.0 | 2 |
| flyover | 600 | 1300.0 | False | 7.5 | 2 |
| flyover | 750 | 1600.0 | True | 7.5 | 0 |
| flyover | 900 | 1900.0 | True | 7.5 | 0 |
| diveunder | 600 | 1300.0 | False | 7.5 | 2 |
| diveunder | 750 | 1600.0 | True | 7.5 | 0 |
| diveunder | 900 | 1900.0 | True | 7.5 | 0 |

The crossing cell has open connection ports. It is not a complete diverging junction.

## Mock adapter cases

| Case | Result | Writes |
|---|---|---:|
| clean | mock_verified | 52 |
| idempotent_repeat | mock_verified | 52 |
| lost_acknowledgement | mock_verified | 52 |
| snapped_geometry | realised_geometry_mismatch | 2 |
| rejected_construction | partial_failure | 1 |
| unknown_capability | preflight_blocked | 0 |
| stale_world | preflight_blocked | 0 |
| stale_terrain | preflight_blocked | 0 |
| unconnected_game | preflight_blocked | 0 |
