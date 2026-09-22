# v0.5 clearance studies

Executed mathematical studies, not real-site capacity or approved vehicle gauging. All bogie spacings below are assumptions.

| Inner radius | Bogie centres | Raw static gap at 3.4 m centres |
|---|---:|---:|
| Straight | 12.0 m | 0.600000 m |
| 150.0 m | 12.0 m | 0.272510 m |
| 250.0 m | 12.0 m | 0.402102 m |
| 400.0 m | 12.0 m | 0.475821 m |
| 800.0 m | 12.0 m | 0.537705 m |
| 1500.0 m | 12.0 m | 0.566725 m |
| Straight | 14.0 m | 0.600000 m |
| 150.0 m | 14.0 m | 0.273379 m |
| 250.0 m | 14.0 m | 0.402431 m |
| 400.0 m | 14.0 m | 0.475953 m |
| 800.0 m | 14.0 m | 0.537739 m |
| 1500.0 m | 14.0 m | 0.566735 m |
| Straight | 16.0 m | 0.600000 m |
| 150.0 m | 16.0 m | 0.274382 m |
| 250.0 m | 16.0 m | 0.402810 m |
| 400.0 m | 16.0 m | 0.476105 m |
| 800.0 m | 16.0 m | 0.537778 m |
| 1500.0 m | 16.0 m | 0.566746 m |

Smaller-radius cases do not inherit the source nominal-spacing applicability. See JSON for assumed allowances and the long-body counterexample.

| Crossover route pair | Result |
|---|---|
| lower_through / upper_through | clear_within_polyline_static_model |
| lower_through / cross_forward | sampled_body_contact |
| upper_through / cross_forward | sampled_body_contact |

The crossover paths include explicitly assumed tangent supports. No legacy resource was removed.

| Formation | Published length | Spare after stated margins | Stop after activation |
|---|---:|---:|---:|
| 8-car | 162.0 m | 88.000 m | 197.127 s |
| 12-car | 242.6 m | 7.400 m | 209.146 s |
