# Live Python development interface

`bridge_live.py` supplies a standard-library callable/CLI boundary to an active
TPF3 development mod. Offline `bridge_cli.py` commands retain their original
design/mock meanings. No service, model call or UI action is needed per operation
once the mod and world are loaded.

## Activation

Copy the **contents** of `implementation/n01_probe/prepared_mod/` into the normal
TPF3 user staging directory under `tpf3_bridge_n01_c04_20261001`; `mod.json`,
`_metadata/` and `content/` must be directly beneath that mod folder. Enable
**TPF3 Bridge N01 Activation** when loading an authorised disposable test save
through the normal game UI. Do not edit base-game files. Normal save-load activation
is demonstrated; hot callback reload is not assumed.

The adapter can **construct railway** when explicitly requested. Its historical
N01 identity remains stable. The game must already be healthy and running;
the bridge does not launch/restart it or repair the environment. Staging location
and game `stdout.txt` vary: use actual user-data locations, not another account's path.

## Context and brief

Create local JSON files outside tracked source. Example `context.json`:

```json
{
  "mod_directory": "<actual staging directory>/tpf3_bridge_n01_c04_20261001",
  "log": "<actual user-data directory>/crash_dump/stdout.txt",
  "session_evidence_root": "<one shared local evidence root>"
}
```

Relative paths resolve beside the context file. Python discovers the latest READY
and matching SESSION handshake. This ephemeral token is transport identity, not a
save GUID/load epoch; a fresh operation establishes responsiveness. Use **one shared
journal root and one client** for the active adapter session.

```powershell
python bridge_live.py inspect --context context.json --params inspect.json
```

`inspect.json` contains `{"edge_ids":[<exact current TRACK edge ID>]}` from a
source-backed native observation. Proximity does not establish attachment identity.
Never reuse another world's recorded IDs.

An extension brief contains exactly:

```json
{
  "anchor_edge": 123,
  "anchor_node": 456,
  "end_xy": [100, 200],
  "end_direction": [1, 0],
  "radius": 100,
  "region": {"min": [0, 0, -20], "max": [300, 300, 20]}
}
```

These numbers illustrate the schema, not a valid construction target. Use freshly
inspected exact IDs, native coordinates and a deliberately selected brief. There
is no pixel conversion or universal real-world scale factor.

```powershell
python bridge_live.py extend --context context.json --params extension.json
python bridge_live.py extend --context context.json --params extension.json --execute
```

First command fits only. Second performs fresh inspection → native fit → explicit
build → fresh readback. Callable equivalents: `client_from_context(path)` and
`extend(client, brief, execute=False)`.

Native `findDubinsPath` supplies forward ARC/STRAIGHT pieces. Bounds: 400×400 XY
region, length≤800 and ≤8pieces; inherited constant anchor grade, selected minimum
radius and sampled geometry/region checks. TPF3 owns native construction/validity.
This is a local extension, not general routing or a station connection guarantee.

## Completion and failures

The workflow sends one correlated `extension` request. Dependent fit/build data
stays within that invocation: separate callback state proved unreliable. After
construction's initial verification, a second fresh native component/geometry query
checks actual TRACK IDs, exact nodes, resources, region and sampled shape. It is
independent of the receipt, but not another Python request. Low-level operations
remain available; cached fit persistence across callbacks/loads is not guaranteed.

Stdout targets≤4096bytes; full requests/responses/new log output/workflow records
stay locally. Files publish atomically. Finite timeout defaults30seconds, maximum300.
Native command ACK is distinct from semantic railway acceptance.

Failed inspect/fit never builds. Uncertain construction retains its journal and
blocks new mutations. **Never rerun `--execute` to collect a missing result.**
Read-only inspection remains possible but does not automatically clear uncertain
effects. `reconcile_pending()` collects a matching late response without sending
another operation. This is in-session reconciliation, not crash recovery, automatic
resume or general idempotency across new journals/loads. No rollback guarantee;
proposal placeholders/counts are not realised entities/effects.

## Demonstration and checks

Build40408, disposable world: P01 demonstrated separate calls; P02 demonstrated
the complete command, building three TRACK pieces, length296.165783native units,
selected radius100, exact connected endpoints and sampled XY error0.00048828125.
A later independent inspection confirmed actual IDs/node chain. Native fit-only,
invalid attachment and region rejection produced no further construction. A collision
was rejected; its effects remain unknown in preserved local history.

18client/fake-worker tests passed;14unchanged quiet-runner tests reused. Run:

```powershell
python tools/quiet_checks.py --suite live_client --label live-client
```

Raw acceptance logs are intentionally local, not required to use the source.
`STATE.md` identifies reports. Unprobed: train traversal, continuous geometry proof,
native save/load identity, arbitrary-version compatibility and production transport.
Detailed station modelling and train physics remain outside this milestone.
Usage unavailable; no invented credit savings.
