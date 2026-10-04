# Explicit crossover acceptance revision

`reconcile_constructed_crossover(client, original_client=None,
acceptance_revision=None)` defaults to the original criteria. An explicitly
authorised radius change may be supplied as exactly:

```python
{"original_request": "<exact failed request ID>", "radius": 70,
 "reason": "<material design decision>", "authority": "<decision authority>"}
```

Only radius can change. It must be finite and positive; the exact request ID,
nonempty reason and authority are mandatory. Unknown fields are rejected.
The original pending request, receipt, fit controls and failed response remain
unchanged. Fresh native verification must establish exact current identities,
connections, subdivision and engineering checks under the revised criterion.
The reconciliation record preserves old/new criteria, authority, original response
path/hash and fresh observation. Pending clears only through successful verified
reconciliation; no construction replay or manual guard clearing.

Crossover requests optionally separate `fit_radius` from the binding realised
minimum `radius`. Default native fitting remains `radius * 1.25`; supplied fit
radius must pass the existing finite/at-least-minimum validation. This is an
explicit design option, not automatic relaxation after failure.

P45's first existing Wickham connection still rejects the original150 minimum.
Its native movement radius74.2073 passes Astra's explicit local70 revision,
without rebuilding. The matching connection retained native fit187.5 but was
constructed with sampled movement radius37.4341 and rejected70. No further
criterion change or retry followed. BaseEdge/control radii and native movement
radii differ; report both, never substitute the former for native acceptance.

Tests use a native-verifier stub; real-game readback is separate local evidence.
Neither sampled geometry nor verified pathfinding proves physical train traversal,
train speed suitability or continuous geometric bounds.
