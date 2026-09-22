# Executed v0.3 geometry-derived examples

Synthetic components and service data; whole-leg scheduling; no real-station capacity or game-performance claim.

## Crossover route reservations

| Route | Requested (s) | Start (s) | Clear (s) | Wait (s) |
|---|---:|---:|---:|---:|
| lower_through | 0.000 | 0.000 | 40.501 | 0.000 |
| upper_through | 0.000 | 0.000 | 40.501 | 0.000 |
| cross_forward | 0.000 | 40.501 | 81.019 | 40.501 |

## Four-platform bank scenarios

| Scenario | Scheduled / required | Completed | Unscheduled | Residual | Departure delay, scheduled only (s) |
|---|---:|---:|---:|---:|---:|
| nominal | 12/12 | 12 | 0 | 0 | 1078.842 |
| p1_closed | 12/12 | 12 | 0 | 0 | 1079.849 |
| three_platforms_closed | 12/12 | 12 | 0 | 0 | 11893.248 |
| all_platforms_closed | 0/12 | 0 | 12 | 0 | 0.000 |
| long_trains | 12/12 | 12 | 0 | 0 | 1909.494 |
| overlength | 0/12 | 0 | 12 | 0 | 0.000 |
| short_horizon | 12/12 | 3 | 0 | 9 | 1078.842 |
| zero_search_budget | 0/12 | 0 | 12 | 0 | 0.000 |

## Bounded crossover fitting

| Request | Evaluations | Fitted candidates | Status |
|---|---:|---:|---|
| within_100m | 35 | 3 | candidate_found_in_enumerated_set |
| within_70m | 35 | 0 | no_candidate_in_enumerated_set |
| one_evaluation | 1 | 0 | search_exhausted |

A low-delay row with missing required visits is not a successful design. No candidate here authorises game construction.
The bank has ONE bidirectional approach; do not present it as the four-approach v0.2 station.
