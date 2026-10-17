# Basic native passenger stations

`bridge_station.place_station(client, brief, execute=False)` prepares native modules.
Use `execute=True` for one guarded construction submission; uncertain results are
not replayed. This uses the live interface in an already-running healthy game.

```python
from bridge_station import place_station
brief = {
    'resource': '::/stations/rail/modular_station/modular_station.con',
    'template': 5,
    'params': {'tracks': 2, 'length': 3, 'trackType': 2, 'catenary': 2, 'year': 2021},
    'position': [100, 200, 16.25], 'angle': 0.0, 'name': 'Test terminal',
}
prepared = place_station(client, brief)  # no game write
```

Coordinates and angle are native values/radians; choose them from the current site.
The supported resource has passenger templates 0–5, track controls 1–8 and length
controls 1–5. On build40408, template5 is a terminal; length3 produced 160-unit
tracks (4:240, 5:320). These are native control values, not metres or a universal
scale conversion. Query `operating_inspect` with `station_catalogue: true` for
bounded current assets/templates and groups before selecting them.

Preparation uses `getConstructionResult(...).params`, including native modules.
It is command preparation, not world preview or guaranteed collision acceptance.
Committed readback resolves the exact construction, owned station, station group,
zero-based station/terminal indices, vehicle nodes and frozen TRACK free endpoints.
Read again with `station_readback` containing the original brief plus
`construction_id`; never substitute coordinate proximity for native identity.

A free degree-one frozen endpoint does not prove it is a buildable entrance.
P73 connected the approach ends of two terminal stations. Attempting to connect
their buffer-side endpoints was rejected with native Collision. Use topology,
native proposal acceptance and final attachment/path readback together.

For an explicit station resource transition, `bridge_live.connect` accepts
`station_target: <exact construction ID>` in its normal brief. Native preparation
requires that the target edge belongs to that station construction. Ordinary
connections retain the same-resource rule. Reacquire fresh edges after replacement.
Line stops use the exact station group and zero-based station/terminal indices.
The older `station_lookup` terminal record's `index` is one-based; do not copy it
directly into a line stop.

P73 built separate fast A/B terminals, four leads and ordinary turnback crossovers;
the local slow service uses existing A/C platforms and retains C's fast bypass.
Station construction, line configuration, native path evidence and physical train
travel/stops are separate evidence. A truncated path is not a complete route proof.
Rejected station connections can be reconciled only from current exact attachment
evidence; rejected assignments only from explicit native rejection and a currently
unassigned train in depot. Both preserve original evidence, unknown other effects
and no automatic replay. No station architecture/crowd modelling, capacity analysis,
reservation emulation, process recovery or arbitrary-build guarantee is added.
