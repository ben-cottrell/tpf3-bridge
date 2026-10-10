# Level free-lead turnout readback

The supported target-less `interior_junction` constructs a native turnout ending at
an explicit level free endpoint. It requires `vertical.max_grade:0`, compatible source
grade/height, `end_xyz` and `end_direction`; this does not add graded free-lead support.

The free-lead fitter uses the existing constant-grade path. The junction now explicitly
carries the declared grade limit into both the saved fit and realised readback, including
zero. Previously the optional positive-limit vertical fit was omitted for this case and
the junction geometry check attempted arithmetic on a nil `maxgrade` after construction.
No permissive grade default, changed fit controls or relaxed engineering limit was added.

`verify_interior` and `reconcile_constructed_interior(current_client, original_client)`
support this target-less receipt. They reconstruct the original subdivision and branch
controls, reacquire exact returned TRACK identities, verify original-edge removal, exact
three-edge junction incidence, branch geometry and through/branch routes. The free finish
must match its requested position/direction and have one exact incident branch edge and
no construction owner. Python also requires the returned free-end identity to match the
branch's last edge/node. Changed, missing, occupied or unverified results retain pending.

A separately authorised normal save/load may activate fixed code. All reads then use
the new session; the old client references only original failure/journal evidence.
Construction is never replayed. Success records current-state verification, not complete
effect history, physical train traversal or general crash recovery.

P50 recovered existing requeste05ba4b4cb57438b825474de0d2d0ba9 on build40408:
through104886/104887, branch104888/104889/104890, junction104882, free endpoint104885.
Both native routes passed, sampled branch radius179.46583 and grade0. Full local records
and fresh current-session bindings are `.local_runs/live_python_interface/p50/`.
