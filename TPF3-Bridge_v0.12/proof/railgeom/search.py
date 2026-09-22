"""Bounded local component fitting; no model calls and no hidden brief changes."""
from __future__ import annotations
from dataclasses import asdict
from railproof.model import positive
from .patterns import GeometryProfile, CrossoverSpec, build_crossover
from .compiler import compile_assembly


def fit_crossover(spacing_m:float,maximum_span_m:float,profile:GeometryProfile=GeometryProfile(),
                  *,evaluation_budget:int=35)->dict:
    positive(spacing_m,"spacing"); positive(maximum_span_m,"authorised span")
    if isinstance(evaluation_budget,bool) or not isinstance(evaluation_budget,int) or evaluation_budget<0:
        raise ValueError("Invalid evaluation budget")
    grid=[(m,L) for m in (0.06,0.075,0.09,0.1,0.12) for L in (30.,36.,40.,45.,50.,60.,72.)]
    trace=[]; candidates=[]
    for m,L in grid:
        if len(trace)>=evaluation_budget: break
        try:
            spec=CrossoverSpec(spacing_m,L,m,maximum_span_m)
            a=build_crossover(spec,profile); c=compile_assembly(a)
            row={"spec":asdict(spec),"status":"synthetic_candidate_fitted","span_m":a.network.metadata["span_m"],
                 "compile_hash":c.compile_hash,"curvature_upper_per_m":max(x["curvature_upper_per_m"] for x in c.provenance["curves"].values())}
            candidates.append(row)
        except ValueError as e:
            row={"spec":{"branch_slope":m,"turnout_span_m":L},"status":"rejected_or_not_certified","reason":str(e)}
        trace.append(row)
    exhausted=len(trace)<len(grid)
    best=min(candidates,key=lambda c:(c["span_m"],c["spec"]["branch_slope"],c["spec"]["turnout_span_m"])) if candidates else None
    status="search_exhausted" if exhausted else ("candidate_found_in_enumerated_set" if best else "no_candidate_in_enumerated_set")
    return {"schema_version":"0.3.0","status":status,"evaluations":len(trace),"grid_size":len(grid),
       "feasible_candidates":len(candidates),"best_in_evaluated_set":best,
       "selection_scope":"minimum centreline span in finite declared grid; not global optimum or construction approval",
       "brief":{"spacing_m":spacing_m,"maximum_span_m":maximum_span_m,"profile":asdict(profile)},
       "trace":trace,"UK_component_compliance":"unassessed","game_representability":"unknown"}
