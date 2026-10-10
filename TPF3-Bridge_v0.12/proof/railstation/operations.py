"""Multi-group complete visits on one recompiled station calendar.

Adapted from the frozen v0.4 scheduler; no per-bank scheduling followed by an
unchecked merge. Both route legs, storage exclusions and closures are checked.
"""
from dataclasses import asdict
from railproof.model import Claim, Platform, Visit, time_value, validate_stock
from railproof.engine import Calendar, Budget, BudgetExhausted
from railgeom.compiler import CompiledAssembly, Requirement
from railgeom.operations import coalesce, make_claims
from railops.motion import MotionProfile
from railops.sectional import Leg, compile_leg, earliest_leg, MODES
from railclear.model import digest


def schedule_station(compiled: CompiledAssembly, visits: list[Visit], *, mode: str='sectional_release',
             profile: MotionProfile=MotionProfile(), closed: set[str]|None=None,
             horizon_ms: int=7200000, max_wait_ms: int=7200000,
             evaluation_budget: int=100000, closed_edges: set[str]|None=None,
             allow_recovery: bool=True) -> dict:
    if mode not in MODES:
        raise ValueError('Unknown release mode')
    time_value(horizon_ms,'horizon',positive_only=True); time_value(max_wait_ms,'max wait')
    if not compiled.platforms:
        raise ValueError('No platform inventory')
    if type(allow_recovery) is not bool:
        raise ValueError('allow_recovery must be boolean')
    permissions=compiled.provenance['network']['metadata'].get('station_permissions')
    if not permissions or set(permissions)!={'A','B'}:
        raise ValueError('Explicit station corridor permissions required')
    for group,ports in permissions.items():
        for pid,p in compiled.platforms.items():
            for direction,start,end in (('in',ports['arrival'],p['marker_port']),
                                        ('out',p['marker_port'],ports['departure'])):
                r=compiled.routes.get(f'{group}:{pid}:{direction}')
                if r is not None and (r.start!=start or r.end!=end):
                    raise ValueError('Route violates station boundary or berth permission')
    closed_edges=set() if closed_edges is None else set(closed_edges)
    if not closed_edges.issubset(compiled.edge_requirements):
        raise ValueError('Unknown closed physical edge')
    closed=set() if closed is None else set(closed)
    if not closed.issubset(compiled.platforms):
        raise ValueError('Unknown closed platform')
    platforms=[Platform(**{k:p[k] for k in ('id','label','bank','usable_length_m','margin_each_end_m')})
               for p in compiled.platforms.values()]
    ordered=validate_stock(visits); budget=Budget(evaluation_budget); calendar=Calendar()
    assigned={}; rejected=[]; exhausted=False; legs={}
    def leg(group,pid,length,direction):
        key=(group,pid,length,direction)
        if key not in legs:
            legs[key]=compile_leg(compiled,f'{group}:{pid}:{direction}',length,direction,profile,mode)
        return legs[key]
    for v in ordered:
        if exhausted:
            rejected.append({'visit_id':v.id,'reason':'search_exhausted'}); continue
        if v.predecessor and v.predecessor not in assigned:
            rejected.append({'visit_id':v.id,'reason':'predecessor_not_scheduled'}); continue
        ready=v.requested_entry_ms
        if v.predecessor:
            ready=max(ready,assigned[v.predecessor]['exit_clear_ms']+v.external_cycle_ms)
        eligible=[]
        for p in platforms:
            rin=compiled.routes.get(f'{v.inbound_group}:{p.id}:in')
            rout=compiled.routes.get(f'{v.outbound_group}:{p.id}:out')
            if p.id in closed or not p.fits(v.length_m) or rin is None or rout is None:
                continue
            if not allow_recovery and (p.bank!=v.inbound_group or p.bank!=v.outbound_group):
                continue
            used=set(rin.edge_ids)|set(rout.edge_ids)|{compiled.platforms[p.id]['storage_edge']}
            if used & closed_edges:
                continue
            eligible.append(p)
        if not eligible:
            rejected.append({'visit_id':v.id,'reason':'no_legal_complete_opportunity'}); continue
        alternatives=[]
        try:
            for p in sorted(eligible,key=lambda p:p.id):
                lin=leg(v.inbound_group,p.id,v.length_m,'in'); lout=leg(v.outbound_group,p.id,v.length_m,'out')
                t=ready; witnesses=[]
                holding=compiled.edge_requirements[compiled.platforms[p.id]['storage_edge']]+(Requirement(f'berth:{p.id}'),)
                while t<=v.requested_entry_ms+max_wait_ms:
                    budget.use()
                    t,w=earliest_leg(calendar,lin,t,v.id,budget); witnesses.extend(w)
                    if t>v.requested_entry_ms+max_wait_ms:
                        break
                    berthed=t+lin.motion_end_ms
                    # Stop readiness and last incoming-lock release are separate.
                    dep=max(v.planned_departure_ms,berthed+v.readiness_ms,t+lin.release_end_ms)
                    dep,w=earliest_leg(calendar,lout,dep,v.id,budget); witnesses.extend(w)
                    clear=dep+lout.release_end_ms
                    held=make_claims(holding,t,clear,v.id)
                    hits=calendar.conflicts(held)
                    if hits:
                        witnesses.extend(asdict(c) for c in hits)
                        t=max(c.end_ms for c in hits); continue
                    claims=coalesce(lin.claims_at(t,v.id)+held+lout.claims_at(dep,v.id))
                    check=Calendar(); check.reserve(claims)
                    if calendar.conflicts(claims):
                        raise AssertionError('Complete-opportunity checker found an unhandled conflict')
                    alternatives.append({'visit_id':v.id,'stock_id':v.stock_id,'platform_id':p.id,
                         'requested_entry_ms':v.requested_entry_ms,'planned_departure_ms':v.planned_departure_ms,
                         'entry_ms':t,'entry_motion_ms':t+profile.setup_ms,'berthed_ms':berthed,
                         'departure_ms':dep,'departure_motion_ms':dep+profile.setup_ms,
                         'tail_exits_ms':dep+lout.motion_end_ms,'exit_clear_ms':clear,
                         'departure_delay_ms':dep-v.planned_departure_ms,'train_length_m':v.length_m,
                         'incoming_route':lin.route_id,'outgoing_route':lout.route_id,
                         'recovery_legs':int(p.bank!=v.inbound_group)+int(p.bank!=v.outbound_group),
                         'arrival_motion':lin.motion.export(),'departure_motion':lout.motion.export(),
                         'incoming_release_end_ms':t+lin.release_end_ms,
                         'incoming_distance_m':lin.route_length_m,'outgoing_distance_m':lout.route_length_m,
                         'outgoing_kind':v.outgoing_kind,'claims':claims,'witnesses':witnesses})
                    break
        except BudgetExhausted:
            exhausted=True; rejected.append({'visit_id':v.id,'reason':'search_exhausted'}); continue
        if not alternatives:
            rejected.append({'visit_id':v.id,'reason':'not_scheduled_within_entry_wait_budget'}); continue
        best=min(alternatives,key=lambda a:(a['departure_delay_ms'],a['recovery_legs'],a['entry_ms'],a['platform_id']))
        calendar.reserve(best['claims']); assigned[v.id]=best
    calendar.verify()
    counts={k:0 for k in ('not_yet_due','waiting_outside_model','arrival_setup','arriving','berthed',
                         'departure_setup','departing','release_hold','completed')}
    values=list(assigned.values())
    for a in values:
        h=horizon_ms
        if h<a['requested_entry_ms']: key='not_yet_due'
        elif h<a['entry_ms']: key='waiting_outside_model'
        elif h<a['entry_motion_ms']: key='arrival_setup'
        elif h<a['berthed_ms']: key='arriving'
        elif h<a['departure_ms']: key='berthed'
        elif h<a['departure_motion_ms']: key='departure_setup'
        elif h<a['tail_exits_ms']: key='departing'
        elif h<a['exit_clear_ms']: key='release_hold'
        else: key='completed'
        counts[key]+=1
    return {'model_version':'0.6.0','fidelity':'synthetic_geometry_and_release; selected_UK_values_separate',
       'mode':mode,'compile_hash':compiled.compile_hash,'profile':asdict(profile),
       'scenario_hash':digest({'visits':[asdict(v) for v in visits], 'closed_platforms':sorted(closed),
            'closed_edges':sorted(closed_edges),'horizon_ms':horizon_ms,'max_wait_ms':max_wait_ms,
            'evaluation_budget':evaluation_budget,'allow_recovery':allow_recovery,'profile':asdict(profile),'mode':mode}),
       'closed_platforms':sorted(closed),'closed_edges':sorted(closed_edges),'allow_recovery':allow_recovery,
       'total_recovery_legs':sum(a['recovery_legs'] for a in values),
       'required_visits':len(visits),'scheduled_visits':len(values),'unscheduled_visits':len(rejected),
       'completed_within_horizon':counts['completed'],'scheduled_residual_at_horizon':len(values)-counts['completed'],
       'horizon_ms':horizon_ms,'scheduled_states_at_horizon':counts,
       'all_required_scheduled':not rejected,
       'all_required_completed_within_horizon':not rejected and counts['completed']==len(visits),
       'total_departure_delay_ms':sum(a['departure_delay_ms'] for a in values),
       'candidate_evaluations':budget.evaluations,
       'assignments':[{**a,'claims':[asdict(c) for c in a['claims']]} for a in values],
       'rejected':rejected,
       'assessments':{'reservation_invariants':'pass','explicit_four_approach_geometry':'compiled_synthetic',
         'shared_throat':'per-bank fan plus any used recovery-link resources; combined compiler',
         'kinematics':'analytic_constant_acceleration_level_track_only',
         'sectional_release':'synthetic_edge_sections' if mode=='sectional_release' else 'conservative_whole_route',
         'real_interlocking':'unassessed','UK_component_and_vehicle_gauging':'unassessed',
         'eight_platform_station':'composed_synthetic; original_site_conformance_checked_separately','braking_curve_validation':'uncalibrated',
         'spatial_queues':'unassessed; waiting_outside_model is a temporal count',
         'passenger_circulation':'unassessed','game_construction':'not_tested',
         'full_UK_engineering_profile':'incomplete; selected rule checks do not promote this assembly'}}
