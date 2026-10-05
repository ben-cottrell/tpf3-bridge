# Bounded junction preparation

Use the already-running adapter through `bridge_live.py`. The designer chooses
attachments, corridor, hard constraints and a short ordered candidate list. Python
orchestrates; Lua uses native fitting and evaluates complete native proposals.
See the project design guide `RAILWAY_DESIGN_GUIDE.md` for layout decisions.

```python
from bridge_live import client_from_context, prepare_junction, build_prepared_junction

client = client_from_context(context_file, timeout=30)
# parameters contains freshly observed source/target candidates, radius, region,
# vertical={"max_grade": ...}, max_route_length, and optional fit_radius.
prepared = prepare_junction(client, parameters, [
    {"fit_radius": 735, "representation": "native_parts"},
    {"fit_radius": 735, "representation": "endpoint_cubic_level"},
])
# Save the full response locally. Inspection alone never constructs anything.
if prepared["status"] == "ok":
    built = build_prepared_junction(client, prepared)
    # Inspect status/readback/through_after/branch_after before further mutation.
```

These numeric values illustrate the P54 experiment, not global defaults. `radius`
is the mandatory minimum; `fit_radius` is a shaping preference. Each explicit
candidate fit radius must be finite and at least the mandatory minimum. Hard
corridor/grade/radius constraints remain unchanged across candidates. The source
must be an exact two-edge compatible through attachment; target an exact free end.
Native checks reacquire both snapshots and current incidence.

Candidate list: 1–8 entries, each only `fit_radius` and `representation`. Available
representations:

- `native_parts`: existing native Dubins parts converted under existing checks.
- `single_cubic_level`: existing single-piece approximation; its conversion
  tolerance remains binding and may reject a candidate.
- `two_piece_level`: existing two-piece approximation with its existing checks.
- `endpoint_cubic_level`: a distinct level candidate guided by exact endpoints,
  travel tangents and native fitted length as the two handle lengths. It is not an
  equality claim against the preliminary Dubins shape. Native cubic regularity,
  selected radius/grade, authorised region and native proposal acceptance apply.

The last candidate is opt-in: it does not globally relax approximation tolerances
or make every native result acceptable. No mandatory sketch vertices/intermediate
Dubins part boundaries are introduced. Bound checks are sampled, not continuous
clearance/curvature proofs. Non-level endpoints cannot use the level alternatives.

Preparation stops at the first noncritical evaluated proposal. Response includes
the accepted geometry, selected candidate and compact failed-candidate evidence.
`no_accepted_candidate` means this finite list found none, not global impossibility.
Preparation never submits a construction command.

Execution sends only `{prepared_request: <handle>, execute: true}` using the same
`junction` operation. Prepared numeric geometry/intent live in GameScript state;
there is no native userdata cache or persisted external mock world. The native
proposal is reconstituted from these stored controls, evaluated against fresh state
and submitted as that exact evaluated object. No native fit is repeated. Changed
source/target/through snapshots, incidence or native acceptance cause explicit
rejection. Replacement inputs/constraints on the consume request are forbidden.
Handles are consumed once; at most16 outstanding handles per adapter session.

Old sessions/save-load changes cannot use a prepared record. Missing/consumed
handles fail rather than refit. A successful preview is not a construction guarantee;
the engine may still reject, and partial/unknown effects remain explicit. Use the
existing reconciliation workflow after uncertain mutations; do not automatically
replay. Returned exact attachments and native TRAIN paths establish connectivity,
not physical train traversal, reservation availability or whole-throat capacity.

Ordinary `connect_junction` fit-only/execute behaviour is preserved, with optional
explicit `fit_radius` now propagated independently. The new prepare/consume API is
the route for building an evaluated geometry without silently fitting again.

## Interior connection preparation

`prepare_interior_junction(client, parameters, candidates)` prepares the complete
through-track replacement and branch. `build_prepared_interior_junction(client,
prepared)` consumes that accepted record without fitting again. Parameters contain
fresh `source` from interior discovery, fresh free-end `target`, the discovery
`location`, `region`, `vertical` and `max_route_length` (at most800 native units).
`radius` is optional here: omitted/zero means no hard minimum, while measured
radius remains feedback. Existing endpoint APIs retain their contracts.

Each of1–8 candidates specifies `branch` (`endpoint_cubic_level`,
`guided_cubic_level`, or existing `native_parts`) and `through` (`subdivide`,
`subdivide_fresh`, or `endpoint_cubic_level`). Level cubics use exact endpoints
and travel directions; optional positive `handle_scale` and four
`through_handle_scales` control shaping. Up to two `guides` contain native XYZ
`pos` and XY `direction`; they are candidate controls, not new hard project anchors.
`native_parts` requires explicit positive hard radius and `fit_radius`.

For a forward interior attachment requiring local resegmentation, supply the exact
adjoining `through_extension` snapshot and choose `extended_endpoint_cubic_level`.
Only a compatible normal TRACK edge at an unowned exclusive two-edge join is
supported. The proposal replaces both edges and removes that redundant join node;
it retains the exact outer nodes/directions. This option must be explicit for every
candidate. It does not authorise arbitrary topology reconstruction.

Preparation reports separate through-only and complete native evaluations and
bounded failure stages. Complete native acceptance governs selection. Failed lists
are completed bounded searches, not global railway impossibility. Stored numeric
through and branch controls live in the current GameScript session. Fresh native
acceptance precedes single-use submission; changed inputs, stale attachments and
consumed handles reject. After construction, exact realised identities, controls
and native TRAIN routes verify the through and branch movements. Bounds are sampled;
route verification does not demonstrate physical train traversal or reservation.
