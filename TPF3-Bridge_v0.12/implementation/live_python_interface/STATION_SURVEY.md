# Named station and free-end survey

With the development mod active in the current loaded world, save a local brief such
as `{"name":"Wickham Station"}` and run:

```powershell
python bridge_live.py station-survey --context context.json --params station.json
```

Callable equivalent: `bridge_station.inspect_station(client, brief)`. This read-only
operation resolves an exact station-group name, station/construction identities and
bounded external TRACK incidence from frozen station tracks. It reports exact free
node/edge IDs, coordinates, observed direction/grade and a local mouth frame; full
geometry and site tiles stay in the local evidence file. The native catalogue is
bounded to 256 groups, 32 member stations, 64 terminals/station, 512 frozen edges/
construction, 64 external edges and 800 native-unit lead distance. A truncated or
ambiguous result is not treated as a complete survey. The same native station lookup
is repeated after site reads; this is a sequential, not atomic, world snapshot.

On build 40408, the saved Wickham example has one station with 16 terminals and 16
free TRACK ends. Native terminal vehicle-edge lists were empty, so no individual
platform-to-end association is claimed. This operation does not design or construct
a throat, verify platform routes or supply a native save GUID. Never reuse its entity
IDs after another save/load without fresh inspection. Evidence is under
`.local_runs/live_python_interface/p42/native/`.
