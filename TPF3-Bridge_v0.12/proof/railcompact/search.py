"""Bounded grid fitting. Exhausting a grid is not a general infeasibility proof."""
from dataclasses import asdict
from itertools import product
from railclear.model import digest
from railgeom.patterns import GeometryProfile
from .composition import build_compact, CompactSpec, EXPECTED_PORTS
from .compiler import compile_assembly
from railstation.checks import site_check

FIELDS={'first_fan_toe_x_m','fan_turnout_span_m','fan_toe_step_m'}


def fit_grid(domain:dict, *, budget:int=100, profile:GeometryProfile=GeometryProfile(),
             maximum_specialwork_end_x_m:float=650.) -> dict:
    import math
    if not isinstance(domain,dict) or set(domain)!=FIELDS:raise ValueError('closed_search_domain_required')
    if isinstance(budget,bool) or not isinstance(budget,int) or budget<0 or budget>10000:raise ValueError('invalid_search_budget')
    if isinstance(maximum_specialwork_end_x_m,bool) or not isinstance(maximum_specialwork_end_x_m,(int,float)) or not math.isfinite(maximum_specialwork_end_x_m) or maximum_specialwork_end_x_m<=0:raise ValueError('invalid_specialwork_limit')
    keys=sorted(domain);count=1
    for key in keys:
        values=domain[key]
        if not isinstance(values,list) or not values or len(values)>20:raise ValueError('invalid_grid_axis')
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values):raise ValueError('invalid_grid_value')
        if len(set(values))!=len(values):raise ValueError('duplicate_grid_value')
        count*=len(values)
    if count>1000:raise ValueError('grid_too_large')
    rows=[];accepted=[]
    for values in product(*(sorted(domain[k]) for k in keys)):
        if len(rows)>=budget:break
        params=dict(zip(keys,values));row={'parameters':params,'index':len(rows)}
        try:
            spec=CompactSpec(**params)
            station=build_compact('scissors',spec,profile)
            end=station.assembly.network.metadata['recovery_geometry']['east_toe_x_m']
            if end>maximum_specialwork_end_x_m:raise ValueError('specialwork_exceeds_search_limit')
            compiled=compile_assembly(station.assembly)
            site=site_check(station,[0.,-90.,1200.,90.],expected_ports=EXPECTED_PORTS)
            if site['status']!='pass_within_scope':raise ValueError('original_plan_site_failed')
            row.update({'status':'fitted_in_synthetic_geometry_scope','compile_hash':compiled.compile_hash,
                         'specialwork_end_x_m':end,'spare_to_inner_marker_m':655.-end,
                         'radius_lower_bound_m':1/max(c['curvature_upper_per_m'] for c in compiled.provenance['curves'].values()),
                         'construction_authorised':False})
            accepted.append(row)
        except ValueError as exc:
            row.update({'status':'candidate_rejected','reason':str(exc)})
        rows.append(row)
    exhaustive=len(rows)==count
    preferred=min(accepted,key=lambda r:(r['specialwork_end_x_m'],tuple(r['parameters'][k] for k in keys))) if accepted else None
    return {'schema_version':'0.7.0','domain':domain,'grid_size':count,'evaluation_budget':budget,'evaluated':len(rows),
            'accepted_count':len(accepted),'grid_complete':exhaustive,
            'status':('grid_complete_candidates_found' if accepted else 'grid_complete_no_candidate') if exhaustive else 'search_exhausted',
            'selected':preferred,'selection_final_within_grid':exhaustive and preferred is not None,
            'maximum_specialwork_end_x_m':maximum_specialwork_end_x_m,'profile':asdict(profile),
            'selection_policy':'minimise last specialwork x after hard geometry/site checks; operations not ranked here',
            'rows':rows,'input_hash':digest({'domain':domain,'profile':asdict(profile),'budget':budget,'limit':maximum_specialwork_end_x_m}),
            'scope':'finite grid in one authored family; no exhaustive topology or continuous optimisation claim',
            'construction_authorised':False}
