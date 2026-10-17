"""Compile explicit track paths + continuous enclosure proxies into resources.

This does NOT derive real interlocking control tables or vehicle kinematic gauges
from track geometry. Control mappings are explicit component metadata. Proximity
exclusions are conservative synthetic corridor resources; no rail edge is added.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from functools import lru_cache
import hashlib
import json
from .curves import Bezier, flatten, continuous_proximity, join_check
from .network import RailPath, Network
from .patterns import Assembly


@dataclass(frozen=True,order=True)
class Requirement:
    resource:str
    state:str|None=None


@dataclass(frozen=True)
class CompiledRoute:
    id:str
    start:str
    end:str
    edge_ids:tuple[str,...]
    length_lower_m:float
    length_upper_m:float
    requirements:tuple[Requirement,...]
    source_hash:str
    segments:tuple[dict,...]


@dataclass
class CompiledAssembly:
    id:str
    source_hash:str
    compile_hash:str
    routes:dict[str,CompiledRoute]
    edge_requirements:dict[str,tuple[Requirement,...]]
    platforms:dict[str,dict]
    provenance:dict

    def export(self)->dict:
        return {"schema_version":"0.3.0","source_hash":self.source_hash,"compile_hash":self.compile_hash,
                "routes":{k:asdict(v) for k,v in sorted(self.routes.items())},
                "edge_requirements":{k:[asdict(r) for r in v] for k,v in sorted(self.edge_requirements.items())},
                "platforms":self.platforms,"provenance":self.provenance}


@lru_cache(maxsize=1024)
def evaluate_curve(curve:Bezier,flatness:float,gap:float):
    leaves=flatten(curve,flatness_m=flatness,length_gap_m=gap)
    return leaves,curve.curvature_upper()


def compile_assembly(assembly:Assembly)->CompiledAssembly:
    n=assembly.network; n.validate(); p=assembly.profile
    source_hash=n.digest()
    leaves={}; curve_records={}; edge_reqs={}; provenance={}
    for id,e in sorted(n.edges.items()):
        leaf,k=evaluate_curve(e.curve,p.flatness_m,p.length_gap_m)
        if k>1/p.minimum_radius_m:
            raise ValueError(f"radius_bound_not_certified:{id}; not a proof of exact-radius violation")
        leaves[id]=leaf
        curve_records[id]={"lower_length_m":sum(x.lower_length_m for x in leaf),
                           "upper_length_m":sum(x.upper_length_m for x in leaf),
                           "curvature_upper_per_m":k,"leaf_count":len(leaf),
                           "maximum_hull_radius_m":max(x.hull_radius_m for x in leaf),
                           "bounds_origin":"Bezier subdivision + derivative hull; floating guard"}
        reqs={Requirement(f"track:{id}")}
        provenance[f"track:{id}"]={"kind":"physical_edge_occupation","edges":[id]}
        if e.component:
            reqs.add(Requirement(f"component_body:{e.component}"))
            reqs.add(Requirement(f"control:{e.controller}",e.state))
            provenance[f"component_body:{e.component}"]={"kind":"exclusive_component_traversal","component":e.component}
            provenance[f"control:{e.controller}"]={"kind":"explicit_component_state_map","controller":e.controller,
                    "not_inferred_from_geometry":True}
        edge_reqs[id]=reqs
    contacts=[]; pair_evaluations=0
    ids=sorted(n.edges)
    for i,a_id in enumerate(ids):
        a=n.edges[a_id]
        for b_id in ids[i+1:]:
            b=n.edges[b_id]; pair_evaluations+=1
            same_component=a.component is not None and a.component==b.component
            shared_port=bool({a.u,a.v}&{b.u,b.v})
            # Declared component divergence and explicit shared endpoints are
            # intentional. Other possible centreline intersections stop compilation.
            # Arbitrary looping components are outside the authored catalogue scope.
            if not same_component and not shared_port:
                near_zero=continuous_proximity(leaves[a_id],leaves[b_id],1e-7)
                if near_zero:
                    raise ValueError(f"unmodelled_or_unresolved_centreline_contact:{a_id}:{b_id}")
            if same_component: continue # component_body already protects these traversals
            w=continuous_proximity(leaves[a_id],leaves[b_id],p.separation_m)
            if w is not None:
                resource=f"proximity:{a_id}|{b_id}"
                req=Requirement(resource)
                edge_reqs[a_id].add(req); edge_reqs[b_id].add(req)
                detail={"resource":resource,"kind":"conservative_corridor_pair","edges":[a_id,b_id],
                        "required_centreline_separation_m":p.separation_m,"witness":w,
                        "rail_connection_created":False}
                contacts.append(detail); provenance[resource]=detail
    routes={}
    for route_id,path in sorted(assembly.routes.items()):
        if route_id!=path.id: raise ValueError("Route key/ID mismatch")
        # Do not accept an arbitrary edge list as a legal component route.
        legal=n.enumerate_paths(path.start,path.end)
        if path.steps not in [r.steps for r in legal]: raise ValueError("Route violates explicit traversal contract")
        current=path.start; prior=None; lower=upper=0.; reqs=set(); segments=[]
        for step in path.steps:
            e=n.edges[step.edge_id]
            u,v=(e.u,e.v) if step.forward else (e.v,e.u)
            if u!=current: raise ValueError("Disconnected route")
            curve=n.oriented_curve(step)
            if prior and not join_check(prior,curve)["pass"]: raise ValueError("Route continuity failed")
            prior=curve; current=v; c=curve_records[e.id]
            segments.append({"edge_id":e.id,"forward":step.forward,
                 "entry_chainage_interval_m":[lower,upper],
                 "exit_chainage_interval_m":[lower+c["lower_length_m"],upper+c["upper_length_m"]]})
            lower+=c["lower_length_m"]; upper+=c["upper_length_m"]; reqs.update(edge_reqs[e.id])
        if current!=path.end or not path.steps: raise ValueError("Incomplete route")
        states={}
        for r in reqs:
            if r.state is not None:
                if r.resource in states and states[r.resource]!=r.state:
                    raise ValueError("internally_incompatible_linked_control_states")
                states[r.resource]=r.state
        routes[route_id]=CompiledRoute(route_id,path.start,path.end,tuple(s.edge_id for s in path.steps),lower,upper,
             tuple(sorted(reqs,key=lambda x:(x.resource,x.state or ""))),source_hash,tuple(segments))
    # Occupied platform storage has its own edge and all its proximity exclusions.
    for pid,platform in assembly.platforms.items():
        if platform["storage_edge"] not in edge_reqs: raise ValueError("Unknown platform holding edge")
        if platform["marker_port"] not in n.ports: raise ValueError("Unknown berth marker")
    profile_payload={"compiler":"0.3.0","source_hash":source_hash,"profile":asdict(p),
          "route_requests":{k:asdict(r) for k,r in sorted(assembly.routes.items())},"platforms":assembly.platforms}
    compile_hash=hashlib.sha256(json.dumps(profile_payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    payload={"network":n.canonical(),"curves":curve_records,"resources":provenance,
       "proximity_contacts":contacts,"pair_evaluations":pair_evaluations,
       "profile":asdict(p),"time_model":"whole_leg_constant_speed_tail_clear_surrogate",
       "assessments":{"explicit_topology":"pass","selected_route_G2_continuity":"pass",
          "synthetic_radius_bound":"pass","continuous_corridor_proxy":"compiled",
          "real_UK_turnout_catalogue":"unassessed","full_vehicle_gauging":"unassessed",
          "real_interlocking_control_table":"unassessed","sectional_release":"not_implemented",
          "vertical_alignment_and_cant":"level_zero_cant_only","game_construction":"not_tested"}}
    return CompiledAssembly(n.id,source_hash,compile_hash,routes,
           {k:tuple(sorted(v,key=lambda r:(r.resource,r.state or ""))) for k,v in edge_reqs.items()},
           json.loads(json.dumps(assembly.platforms)),payload)
