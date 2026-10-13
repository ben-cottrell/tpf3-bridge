# Parallel bridge and tunnel examples

Four authored corridor briefs reuse `bridge_corridor.compile_corridor` and the
existing operator. They are design examples, not current-world receipts or safe
replay instructions. Each uses `REFRESH_CURRENT_SESSION`; obtain a healthy current
session, survey the chosen authorised region and confirm native resources before
planning. Coordinates describe the qualification sites, not universal suitable sites.
Do not replay construction over an existing fixture.

| Brief | Roads | Representation | Structure |
| --- | --- | --- | --- |
| `bridge2.json` | 2 | One guided `native_parts` group | NORMAL / steel BRIDGE / NORMAL |
| `bridge4.json` | 4 | Three explicit corridor sections | NORMAL / steel BRIDGE / NORMAL |
| `tunnel2.json` | 2 | One guided `native_parts` group | NORMAL / tunnel_a TUNNEL / NORMAL |
| `tunnel4.json` | 4 | Three explicit corridor sections | NORMAL / tunnel_a TUNNEL / NORMAL |

All use a reference up track and genuine signed normal offsets: down +5;
four-road examples additionally fast_up -5 and fast_down +10 native units.
`reverse:false` describes construction geometry; operational down direction is
separately `forward:false`. Reference guides have explicit zero boundary grades;
the selected maximum railway grade is 0.04. These are task-selected dimensions,
not a universal UK-to-game scale conversion.

The tunnel2 brief retains the actual qualified variant: endpoints at heights
27 and 33, guides [-2280,-3276,33] and [-1900,-3245,33], with direction
[0.9966889551003809,0.08130883581082055]. Native-parts fitting supplies the cubic
approaches and straight tunnel span; this is not the different sectioned tunnel4
profile. Do not replace it with preliminary controls or a flattened profile.
Derived tracks retain shared-reference-parameter height transfer. Their signed
grade joins are checked against immutable prepared joins; ordinary zero-join
checks and all other engineering/native acceptance guards remain in force.

## Signals and qualification

Refresh the exact current signal template seed identity; no historic seed ID is
embedded here. For bridge2/bridge4/tunnel4, the demonstrated completion used roads
in authored section order, spacing 300, start_offset 150, end_clearance 150,
max_count 8 and max_route_length 1500. Up/fast_up are forward; down/fast_down are
reverse. Check forward reachability and reverse blocking independently on each
road after native readback. These values are examples, not capacity guarantees.

Tunnel2 is an explicit site-specific exception. Body and NORMAL-approach down
signal previews, including bounded nearby positions, were rejected with native
`Collision`. That rejection remains an error even with `critical:false`.
An explicitly authorised remaining-work batch placed two one-way reverse signals
at the midpoint of the existing down end seeds. Their separation is approximately
780 native units. Obtain fresh exact edge/node identities and geometry before any
such batch; do not infer seed correspondence by proximity. Preserve already-built
up signals and uncertain/failed operation records; never replay the original
failed completion. No 300-spacing or capacity qualification is claimed for this
exception, and it is not an automatic fallback recipe.

The four native fixtures collectively qualified 24 signals and 24 forward/reverse
route checks. Three original parent completions finished; tunnel2 qualified through
explicit remaining work while its original preparation failure remains honestly
`needs_attention`. This does not establish train traversal, general native asset
availability, arbitrary-site success or cross-process crash recovery.

Local static reuse check (no native calls): load each JSON and pass it to
`bridge_corridor.compile_corridor`. Compilation accepts the nonempty placeholder;
it does not prove that the placeholder identifies a usable native session.
