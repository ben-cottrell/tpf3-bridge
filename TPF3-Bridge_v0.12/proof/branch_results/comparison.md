# Connected passenger-branch results — v0.10

Synthetic junction and operating assumptions. Delay covers scheduled requests only. No real game or capacity validation.

| Scenario | Form | Completed / required | Unscheduled | Residual | Total entry delay (s) |
|---|---|---:|---:|---:|---:|
| nominal | flat | 24 / 24 | 0 | 0 | 11341.991 |
| crossing_pulse | flat | 2 / 2 | 0 | 0 | 50.940 |
| merge_pulse | flat | 2 / 2 | 0 | 0 | 262.403 |
| downstream_blocked | flat | 2 / 2 | 0 | 0 | 2660.461 |
| branch_return_closed | flat | 18 / 24 | 6 | 0 | 6061.450 |
| shared_west_exit_closed | flat | 12 / 24 | 12 | 0 | 6061.450 |
| synthetic_300m | flat | 24 / 24 | 0 | 0 | 11793.531 |
| short_horizon | flat | 0 / 24 | 0 | 24 | 11341.991 |
| zero_budget | flat | 0 / 24 | 24 | 0 | 0.000 |
| zero_entry_wait | flat | 1 / 2 | 1 | 0 | 0.000 |
| nominal | flyover | 24 / 24 | 0 | 0 | 10312.362 |
| crossing_pulse | flyover | 2 / 2 | 0 | 0 | 0.000 |
| merge_pulse | flyover | 2 / 2 | 0 | 0 | 262.419 |
| downstream_blocked | flyover | 2 / 2 | 0 | 0 | 2660.445 |
| branch_return_closed | flyover | 18 / 24 | 6 | 0 | 6061.450 |
| shared_west_exit_closed | flyover | 12 / 24 | 12 | 0 | 6061.450 |
| synthetic_300m | flyover | 24 / 24 | 0 | 0 | 10753.202 |
| short_horizon | flyover | 0 / 24 | 0 | 24 | 10312.362 |
| zero_budget | flyover | 0 / 24 | 24 | 0 | 0.000 |
| zero_entry_wait | flyover | 1 / 2 | 1 | 0 | 0.000 |
| nominal | diveunder | 24 / 24 | 0 | 0 | 10312.362 |
| crossing_pulse | diveunder | 2 / 2 | 0 | 0 | 0.000 |
| merge_pulse | diveunder | 2 / 2 | 0 | 0 | 262.419 |
| downstream_blocked | diveunder | 2 / 2 | 0 | 0 | 2660.445 |
| branch_return_closed | diveunder | 18 / 24 | 6 | 0 | 6061.450 |
| shared_west_exit_closed | diveunder | 12 / 24 | 12 | 0 | 6061.450 |
| synthetic_300m | diveunder | 24 / 24 | 0 | 0 | 10753.202 |
| short_horizon | diveunder | 0 / 24 | 0 | 24 | 10312.362 |
| zero_budget | diveunder | 0 / 24 | 24 | 0 | 0.000 |
| zero_entry_wait | diveunder | 1 / 2 | 1 | 0 | 0.000 |

The three forms have identical plan topology. Only the return crossing height changes. Flat and separated modes keep the same physical merge.

The motion surrogate is level-track, starts trains at rest, and keeps one speed per movement. It ignores grade-dependent performance. Identical raised/lowered timings therefore do not establish equal real-world performance.

Requests wait outside this model. Holding trials are geometric screens, not evidence of a train stopping at an in-model signal.
