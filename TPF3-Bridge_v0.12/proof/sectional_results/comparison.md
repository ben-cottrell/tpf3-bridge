# Executed v0.4 two-approach bank comparisons

Same geometry, demand, kinematics and setup/release assumptions within each paired scenario. Only the resource-release policy changes. These are synthetic schedules, not actual station capacity estimates.

| Scenario | Release policy | Scheduled / required | Completed | Unscheduled | Residual | Scheduled departure delay (s) |
|---|---|---:|---:|---:|---:|---:|
| nominal | whole_route | 12/12 | 12 | 0 | 0 | 16779.354 |
| nominal | sectional_release | 12/12 | 12 | 0 | 0 | 10568.224 |
| bunched | whole_route | 12/12 | 12 | 0 | 0 | 22719.354 |
| bunched | sectional_release | 12/12 | 12 | 0 | 0 | 16507.522 |
| p1_closed | whole_route | 12/12 | 12 | 0 | 0 | 16787.529 |
| p1_closed | sectional_release | 12/12 | 12 | 0 | 0 | 10572.545 |
| all_platforms_closed | whole_route | 0/12 | 0 | 12 | 0 | 0.000 |
| all_platforms_closed | sectional_release | 0/12 | 0 | 12 | 0 | 0.000 |
| long_trains | whole_route | 12/12 | 12 | 0 | 0 | 17924.675 |
| long_trains | sectional_release | 12/12 | 12 | 0 | 0 | 16780.590 |
| overlength | whole_route | 0/12 | 0 | 12 | 0 | 0.000 |
| overlength | sectional_release | 0/12 | 0 | 12 | 0 | 0.000 |
| short_horizon | whole_route | 12/12 | 0 | 0 | 12 | 16779.354 |
| short_horizon | sectional_release | 12/12 | 0 | 0 | 12 | 10568.224 |
| zero_budget | whole_route | 0/12 | 0 | 12 | 0 | 0.000 |
| zero_budget | sectional_release | 0/12 | 0 | 12 | 0 | 0.000 |
| late_stock_cycle | whole_route | 12/12 | 12 | 0 | 0 | 18579.354 |
| late_stock_cycle | sectional_release | 12/12 | 12 | 0 | 0 | 12367.522 |

Do not rank zero-delay rows with missing demand as successful. A less restrictive release model does not guarantee a globally better result under a greedy scheduler. Geometry and UK-rule gates are separate.
