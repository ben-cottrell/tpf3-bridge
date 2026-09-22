# v0.7 compact station comparisons

Original plan boundary, exact approaches, platform intervals and buffer-marker positions.
Components are authored synthetic. The four-hour horizon is not a capacity or punctuality approval.

| Scenario | Family | Scheduled / required | Completed | Unscheduled | Residual | Departure delay (scheduled only) | Recovery legs |
|---|---|---:|---:|---:|---:|---:|---:|
| nominal | isolated | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| nominal | a_to_b | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| nominal | b_to_a | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| nominal | scissors | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| bunched | isolated | 24/24 | 24 | 0 | 0 | 3435.344 s | 0 |
| bunched | a_to_b | 24/24 | 24 | 0 | 0 | 3435.344 s | 0 |
| bunched | b_to_a | 24/24 | 24 | 0 | 0 | 3435.344 s | 0 |
| bunched | scissors | 24/24 | 24 | 0 | 0 | 3435.344 s | 0 |
| bank_a_platforms_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| bank_a_platforms_closed | a_to_b | 24/24 | 24 | 0 | 0 | 16547.982 s | 24 |
| bank_a_platforms_closed | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| bank_a_platforms_closed | scissors | 24/24 | 24 | 0 | 0 | 16547.982 s | 24 |
| bank_b_platforms_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| bank_b_platforms_closed | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| bank_b_platforms_closed | b_to_a | 24/24 | 24 | 0 | 0 | 15366.846 s | 24 |
| bank_b_platforms_closed | scissors | 24/24 | 24 | 0 | 0 | 15366.846 s | 24 |
| a_fan_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_fan_closed | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_fan_closed | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_fan_closed | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_arrival_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_arrival_closed | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_arrival_closed | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_arrival_closed | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| published_long_units | isolated | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| published_long_units | a_to_b | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| published_long_units | b_to_a | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| published_long_units | scissors | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| synthetic_300m | isolated | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| synthetic_300m | a_to_b | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| synthetic_300m | b_to_a | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| synthetic_300m | scissors | 24/24 | 24 | 0 | 0 | 0.000 s | 0 |
| all_platforms_closed | isolated | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| all_platforms_closed | a_to_b | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| all_platforms_closed | b_to_a | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| all_platforms_closed | scissors | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| short_horizon | isolated | 24/24 | 3 | 0 | 21 | 0.000 s | 0 |
| short_horizon | a_to_b | 24/24 | 3 | 0 | 21 | 0.000 s | 0 |
| short_horizon | b_to_a | 24/24 | 3 | 0 | 21 | 0.000 s | 0 |
| short_horizon | scissors | 24/24 | 3 | 0 | 21 | 0.000 s | 0 |
| zero_budget | isolated | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| zero_budget | a_to_b | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| zero_budget | b_to_a | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| zero_budget | scissors | 0/24 | 0 | 24 | 0 | 0.000 s | 0 |
| a_bank_closed_recovery_forbidden | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_recovery_forbidden | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_recovery_forbidden | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_recovery_forbidden | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_inner_b1_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_inner_b1_closed | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_inner_b1_closed | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_inner_b1_closed | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_300m | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_300m | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_300m | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| a_bank_closed_300m | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_bank_closed_300m | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_bank_closed_300m | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_bank_closed_300m | b_to_a | 24/24 | 24 | 0 | 0 | 36172.224 s | 24 |
| b_bank_closed_300m | scissors | 24/24 | 24 | 0 | 0 | 36172.224 s | 24 |
| b_fan_closed | isolated | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_fan_closed | a_to_b | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_fan_closed | b_to_a | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |
| b_fan_closed | scissors | 12/24 | 12 | 12 | 0 | 0.000 s | 0 |

Recovery reaches B1 from A and A4 from B—not the whole opposite bank.
Bank closures are separate scenarios. The links are after both fans; a failed fan cannot be bypassed.
Zero delay excludes unscheduled work and must never be ranked without its completion count.
