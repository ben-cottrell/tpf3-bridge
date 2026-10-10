# Native rail depot placement

Use `bridge_live.place_depot(client, brief, execute=False)` to prepare a native
construction command without submitting it. Explicit `execute=True` prepares and
submits once through the existing operating transport. Example on build40408:

```python
from bridge_live import place_depot

brief = {
    "resource": "::/depots/rail/rail_depot.con", "template": 2,
    "params": {"streetTemplate": "::/infrastructure/track/simple/simple_catenary.street_template",
               "catenary": 2, "trackType": 1, "year": 2021},
    "position": [830, -2650, 16.25], "angle": 1.5707963267948966,
    "name": "Service depot",
}
prepared = place_depot(client, brief)  # native command preparation only
# built = place_depot(client, brief, execute=True)  # explicit authorised mutation
```

Coordinates, assets, template index and toolbar choices are installation/world
examples, not portable defaults. Position uses native coordinates; rotation uses
radians. Select a usable service attachment before choosing the depot position.
Native `getConstructionResult(resource, template, params).params` supplies the
complete processed parameters required by `SimpleProposal.ConstructionEntity`.
Raw toolbar choices alone failed command construction on build40408. The bridge
uses native Mat4f, explicit player context and normal error handling; it does not
manufacture internal generated parameter keys.

Preparation is **not** a world preview. A constructed command may still be rejected
for Collision. Successful build readback identifies the exact CONSTRUCTION,
VEHICLE_DEPOT ownership, position, frozen track and native in/out nodes. The observed
SimpleProposal receipt contains numeric entity IDs; the reader also accepts paired
entries. No acknowledgement or visual resemblance proves service access.

Connect the fresh external TRACK node through the existing junction workflow.
Full native proposal acceptance requires no critical error **and no error messages**:
build40408 can report Collision with `critical=false`. Execute the accepted
`prepared_request` in the same adapter session, rechecking that exact proposal;
do not recompute another fit for construction. Native existing junction movement
geometry may be trimmed; exact native incidence/connection identities establish
correspondence, while ordinary non-junction geometry checks remain unchanged.

Read-only service proof uses `operating_inspect` with `depot_readback`:

```python
readback = client.request("operating_inspect", {"depot_readback": dict(
    brief, construction_id=actual_construction_id,
    service_target={"edge": service_edge_id, "node": service_node_id,
                    "required_edges": [exit_edge_id, *connector_edge_ids]})})
```

Reacquire IDs after a normal load; an adapter session is not a verified native save
identity. The query starts at the actual Depot outNodes and checks native TRAIN
direction, continuity, destination and named TRACK edges. At most64 returned rows
are retained; truncation does not verify a route. Native search itself has no
demonstrated length bound. Route existence does not prove dispatch, reservations,
capacity or physical train passage. Depot carrier is explicitly unavailable in the
observed runtime. External Python/mod transport remains the existing local interface.

P72 demonstrates a DS-connected depot on build40408, retaining required67386 and
passing all8 D/E terminal routes plus both DS trunk directions and the current
D_in_near approach. Historical node65804 was stale; current edge63062 source67423
was independently reacquired before checking that approach. Earlier collision,
wrong-lead and callback/storage failures remain local evidence, never replayed.
Responses are persisted when received; an acknowledgement updates the journal
without redundantly replacing that receipt. Missing acknowledgement still retains
pending state. Filesystem permission failures are not repaired by the bridge.
