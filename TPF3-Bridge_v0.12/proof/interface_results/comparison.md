# v0.8 platform-interface operating comparisons

Reference-source design-screen exclusions, not physical track closures or real station safety decisions.

| Interface case | Rail scenario | Excluded boarding faces | Completed / required | Unscheduled | Residual | Departure delay, scheduled only |
|---|---|---|---:|---:|---:|---:|
| initial | nominal | B1 | 24/24 | 0 | 0 | 0.000 s |
| initial | bank_a_platforms_closed | B1 | 12/24 | 12 | 0 | 0.000 s |
| initial | bank_b_platforms_closed | B1 | 24/24 | 0 | 0 | 15366.846 s |
| oversize | nominal | B1, B2 | 24/24 | 0 | 0 | 0.000 s |
| oversize | bank_a_platforms_closed | B1, B2 | 12/24 | 12 | 0 | 0.000 s |
| oversize | bank_b_platforms_closed | B1, B2 | 24/24 | 0 | 0 | 15366.846 s |
| locally_refitted | nominal | none | 24/24 | 0 | 0 | 0.000 s |
| locally_refitted | bank_a_platforms_closed | none | 24/24 | 0 | 0 | 16547.982 s |
| locally_refitted | bank_b_platforms_closed | none | 24/24 | 0 | 0 | 15366.846 s |

Same track, source vehicle-unit lengths and operating assumptions; only explicitly gated boarding eligibility changes.
The unreviewed current standard, full access, dynamic gauging, authentic specialwork and game interfaces remain unassessed.
