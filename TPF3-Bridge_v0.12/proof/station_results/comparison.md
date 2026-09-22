# v0.6 integrated station comparisons

Executed on the same authored station boundaries, demand and matched synthetic corridor section breaks. Not real-site capacity.
All three candidate geometries fail the original site brief. A larger test site is assessed separately.

| Scenario | Family | Scheduled / required | Completed | Unscheduled | Residual | Departure delay (scheduled only) | Recovery legs |
|---|---|---:|---:|---:|---:|---:|---:|
| nominal | isolated | 24/24 | 24 | 0 | 0 | 30492.490 s | 0 |
| nominal | a_to_b | 24/24 | 24 | 0 | 0 | 30492.490 s | 0 |
| nominal | b_to_a | 24/24 | 24 | 0 | 0 | 30492.490 s | 0 |
| bunched | isolated | 24/24 | 24 | 0 | 0 | 37375.606 s | 0 |
| bunched | a_to_b | 24/24 | 24 | 0 | 0 | 40726.316 s | 2 |
| bunched | b_to_a | 24/24 | 24 | 0 | 0 | 37375.606 s | 0 |
| bank_a_platforms_closed | isolated | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| bank_a_platforms_closed | a_to_b | 24/24 | 24 | 0 | 0 | 97158.473 s | 24 |
| bank_a_platforms_closed | b_to_a | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| bank_b_platforms_closed | isolated | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| bank_b_platforms_closed | a_to_b | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| bank_b_platforms_closed | b_to_a | 24/24 | 24 | 0 | 0 | 97120.782 s | 24 |
| a_fan_closed | isolated | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_fan_closed | a_to_b | 24/24 | 24 | 0 | 0 | 97158.473 s | 24 |
| a_fan_closed | b_to_a | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_arrival_closed | isolated | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_arrival_closed | a_to_b | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_arrival_closed | b_to_a | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| published_long_units | isolated | 24/24 | 24 | 0 | 0 | 32624.072 s | 0 |
| published_long_units | a_to_b | 24/24 | 24 | 0 | 0 | 32624.072 s | 0 |
| published_long_units | b_to_a | 24/24 | 24 | 0 | 0 | 32624.072 s | 0 |
| synthetic_300m | isolated | 24/24 | 24 | 0 | 0 | 33933.828 s | 0 |
| synthetic_300m | a_to_b | 24/24 | 24 | 0 | 0 | 33933.828 s | 0 |
| synthetic_300m | b_to_a | 24/24 | 24 | 0 | 0 | 33933.828 s | 0 |
| all_platforms_closed | isolated | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| all_platforms_closed | a_to_b | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| all_platforms_closed | b_to_a | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| short_horizon | isolated | 24/24 | 2 | 0 | 22 | 30492.490 s | 0 |
| short_horizon | a_to_b | 24/24 | 2 | 0 | 22 | 30492.490 s | 0 |
| short_horizon | b_to_a | 24/24 | 2 | 0 | 22 | 30492.490 s | 0 |
| zero_budget | isolated | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| zero_budget | a_to_b | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| zero_budget | b_to_a | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| a_bank_closed_recovery_forbidden | isolated | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_bank_closed_recovery_forbidden | a_to_b | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |
| a_bank_closed_recovery_forbidden | b_to_a | 12/24 | 12 | 12 | 0 | 15246.245 s | 0 |

Unscheduled work is not credited as low delay. The 300 m formation is a synthetic stress input. Other unit lengths come from the retained S060 record.
The scheduler is greedy and its edge-based release is synthetic. No network construction or UK approval follows from a completed row.
