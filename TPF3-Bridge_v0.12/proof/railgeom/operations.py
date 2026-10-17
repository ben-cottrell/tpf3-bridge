"""Geometry-backed whole-leg scheduling, reusing the v0.2 calendar invariants.

No route distances or conflict matrices are hand-entered here. Timing still uses
an explicit constant-speed, whole-leg tail-clear surrogate (not microscopic
acceleration/braking or real signal positioning). Berth storage is held across
the complete visit, including any departure wait.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from railproof.model import Claim, Platform, Visit, positive, time_value, validate_stock
from railproof.engine import Calendar, Budget, BudgetExhausted, clearance_ms
from .compiler import CompiledAssembly, CompiledRoute, Requirement


@dataclass(frozen=True)
class TimingProfile:
    speed_mps:float=8.0
    setup_ms:int=5000
    release_ms:int=3000
    def __post_init__(self):
        positive(self.speed_mps,"speed")
        time_value(self.setup_ms,"setup"); time_value(self.release_ms,"release")


def duration(route:CompiledRoute,length_m:float,timing:TimingProfile)->int:
    return clearance_ms(route.length_upper_m,length_m,timing.speed_mps,timing.setup_ms,timing.release_ms)


def make_claims(reqs:tuple[Requirement,...],start:int,end:int,owner:str)->list[Claim]:
    return [Claim(r.resource,start,end,owner,r.state) for r in reqs]


def coalesce(claims:list[Claim])->list[Claim]:
    groups={}
    for c in claims: groups.setdefault((c.resource,c.owner,c.state),[]).append(c)
    result=[]
    for key,items in sorted(groups.items(),key=lambda x:(x[0][0],x[0][1],x[0][2] or "")):
        items.sort(key=lambda c:(c.start_ms,c.end_ms)); current=items[0]
        for c in items[1:]:
            if c.start_ms<=current.end_ms:
                current=Claim(current.resource,current.start_ms,max(current.end_ms,c.end_ms),current.owner,current.state)
            else: result.append(current); current=c
        result.append(current)
    return result


def earliest(calendar:Calendar,route:CompiledRoute,start:int,period:int,owner:str,budget:Budget)->tuple[int,list[dict]]:
    witnesses=[]
    while True:
        budget.use()
        hits=calendar.conflicts(make_claims(route.requirements,start,start+period,owner))
        if not hits: return start,witnesses
        witnesses.extend(asdict(c) for c in hits)
        start=max(c.end_ms for c in hits)


def schedule_routes(compiled:CompiledAssembly,requests:list[dict],timing:TimingProfile=TimingProfile())->dict:
    """Small route-only demonstration; order is declared, not an optimal scheduler."""
    calendar=Calendar(); rows=[]; ids=set(); budget=Budget(100000)
    for r in requests:
        if set(r)!={"id","route","requested_ms","train_length_m"}: raise ValueError("Unexpected route request fields")
        if not isinstance(r["id"],str) or not r["id"] or r["id"] in ids: raise ValueError("Duplicate/invalid request ID")
        ids.add(r["id"]); time_value(r["requested_ms"],"request time"); positive(r["train_length_m"],"train length")
        if r["route"] not in compiled.routes: raise ValueError("Unknown route")
        route=compiled.routes[r["route"]]; d=duration(route,r["train_length_m"],timing)
        t,w=earliest(calendar,route,r["requested_ms"],d,r["id"],budget)
        claims=make_claims(route.requirements,t,t+d,r["id"]); calendar.reserve(claims)
        rows.append({**r,"start_ms":t,"clear_ms":t+d,"wait_ms":t-r["requested_ms"],
                     "claims":[asdict(c) for c in claims],"witnesses":w})
    calendar.verify()
    return {"compile_hash":compiled.compile_hash,"requests":rows,"calendar_invariants":"pass",
            "policy":"declared_request_order","time_model":"whole_leg_constant_speed_tail_clear_surrogate"}


def fit(v:Visit,p:Platform,compiled:CompiledAssembly,calendar:Calendar,budget:Budget,
        earliest_entry:int,max_wait:int,timing:TimingProfile)->dict|None:
    if not p.fits(v.length_m) or v.inbound_group!="A" or v.outbound_group!="A": return None
    rin=compiled.routes.get(f"{p.id}:in"); rout=compiled.routes.get(f"{p.id}:out")
    if rin is None or rout is None: return None
    di,do=duration(rin,v.length_m,timing),duration(rout,v.length_m,timing)
    storage=compiled.platforms[p.id]["storage_edge"]
    holding=compiled.edge_requirements[storage]+(Requirement(f"berth:{p.id}"),)
    t=earliest_entry; witnesses=[]
    while t<=v.requested_entry_ms+max_wait:
        budget.use(); t,w=earliest(calendar,rin,t,di,v.id,budget); witnesses.extend(w)
        if t>v.requested_entry_ms+max_wait: return None
        berthed=t+di; dep=max(v.planned_departure_ms,berthed+v.readiness_ms)
        dep,w=earliest(calendar,rout,dep,do,v.id,budget); witnesses.extend(w)
        hold=make_claims(holding,t,dep+do,v.id)
        hits=calendar.conflicts(hold)
        if hits:
            witnesses.extend(asdict(c) for c in hits); t=max(c.end_ms for c in hits); continue
        claims=coalesce(make_claims(rin.requirements,t,berthed,v.id)+hold+make_claims(rout.requirements,dep,dep+do,v.id))
        # Independent check includes holding/route interactions and state maps.
        check=Calendar(); check.reserve(claims)
        return {"visit_id":v.id,"stock_id":v.stock_id,"platform_id":p.id,"entry_ms":t,"berthed_ms":berthed,
                "departure_ms":dep,"exit_clear_ms":dep+do,"departure_delay_ms":dep-v.planned_departure_ms,
                "train_length_m":v.length_m,"incoming_route":rin.id,"outgoing_route":rout.id,
                "incoming_distance_upper_m":rin.length_upper_m,"outgoing_distance_upper_m":rout.length_upper_m,
                "outgoing_kind":v.outgoing_kind,"claims":claims,"witnesses":witnesses}
    return None


def schedule_bank(compiled:CompiledAssembly,visits:list[Visit],*,closed:set[str]|None=None,
                  horizon_ms:int=7200000,max_wait_ms:int=7200000,evaluation_budget:int=100000,
                  timing:TimingProfile=TimingProfile())->dict:
    time_value(horizon_ms,"horizon",positive_only=True); time_value(max_wait_ms,"max wait")
    if not compiled.platforms: raise ValueError("No platform-bank contract")
    closed=set() if closed is None else set(closed)
    if not closed.issubset(compiled.platforms): raise ValueError("Unknown platform closure")
    ordered=validate_stock(visits); budget=Budget(evaluation_budget); calendar=Calendar()
    platforms=[Platform(**{k:p[k] for k in ("id","label","bank","usable_length_m","margin_each_end_m")})
               for p in compiled.platforms.values()]
    assigned={}; rejected=[]; exhausted=False
    for v in ordered:
        if exhausted: rejected.append({"visit_id":v.id,"reason":"search_exhausted"}); continue
        if v.predecessor and v.predecessor not in assigned:
            rejected.append({"visit_id":v.id,"reason":"predecessor_not_scheduled"}); continue
        ready=v.requested_entry_ms
        if v.predecessor: ready=max(ready,assigned[v.predecessor]["exit_clear_ms"]+v.external_cycle_ms)
        legal=[p for p in platforms if p.id not in closed and p.fits(v.length_m)
               and v.inbound_group=="A" and v.outbound_group=="A"
               and f"{p.id}:in" in compiled.routes and f"{p.id}:out" in compiled.routes]
        if not legal:
            rejected.append({"visit_id":v.id,"reason":"no_legal_complete_opportunity"}); continue
        alternatives=[]
        try:
            for p in sorted(legal,key=lambda x:x.id):
                a=fit(v,p,compiled,calendar,budget,ready,max_wait_ms,timing)
                if a is not None: alternatives.append(a)
        except BudgetExhausted:
            exhausted=True; rejected.append({"visit_id":v.id,"reason":"search_exhausted"}); continue
        if not alternatives:
            rejected.append({"visit_id":v.id,"reason":"not_scheduled_within_entry_wait_budget"}); continue
        best=min(alternatives,key=lambda a:(a["departure_delay_ms"],a["entry_ms"],a["platform_id"]))
        calendar.reserve(best["claims"]); assigned[v.id]=best
    calendar.verify(); values=list(assigned.values())
    completed=sum(a["exit_clear_ms"]<=horizon_ms for a in values)
    trace=[]
    for a in values:
        for kind,key in (("entry","entry_ms"),("berthed","berthed_ms"),("departure","departure_ms"),("exit_clear","exit_clear_ms")):
            trace.append({"at_ms":a[key],"kind":kind,"visit_id":a["visit_id"],"platform_id":a["platform_id"]})
    trace.sort(key=lambda x:(x["at_ms"],x["visit_id"],x["kind"]))
    output=[]
    for a in values: output.append({**a,"claims":[asdict(c) for c in a["claims"]]})
    return {"model_version":"0.3.0","fidelity":"synthetic_geometry_derived_whole_leg_resources",
       "compile_hash":compiled.compile_hash,"source_hash":compiled.source_hash,
       "time_profile":asdict(timing),"required_visits":len(visits),"scheduled_visits":len(values),
       "unscheduled_visits":len(rejected),"completed_within_horizon":completed,
       "scheduled_residual_at_horizon":len(values)-completed,"horizon_ms":horizon_ms,
       "total_departure_delay_ms":sum(a["departure_delay_ms"] for a in values),
       "all_required_scheduled":not rejected,"candidate_evaluations":budget.evaluations,
       "assignments":output,"rejected":rejected,"trace":trace,
       "assessments":{"calendar_invariants":"pass","pattern_geometry":"synthetic_planar_compiled",
           "four_approach_eight_platform_station":"not_implemented","microscopic_train_motion":"unassessed",
           "UK_turnout_and_clearance_compliance":"unassessed","real_interlocking":"unassessed",
           "sectional_resource_release":"not_implemented","passenger_circulation":"unassessed",
           "spatial_queue_spillback":"unassessed","game_construction":"not_tested","game_observation":"not_tested"}}
