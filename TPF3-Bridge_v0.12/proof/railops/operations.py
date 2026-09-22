"""Complete visits with stopping motion and sectional release; greedy, not optimal."""
from dataclasses import asdict
from railproof.model import Claim, Platform, Visit, time_value, validate_stock
from railproof.engine import Calendar, Budget, BudgetExhausted
from railgeom.compiler import CompiledAssembly, Requirement
from railgeom.operations import coalesce, make_claims
from .motion import MotionProfile
from .sectional import Leg, compile_leg, earliest_leg, MODES


def schedule(compiled: CompiledAssembly, visits: list[Visit], *, mode: str='sectional_release',
             profile: MotionProfile=MotionProfile(), closed: set[str]|None=None,
             horizon_ms: int=7200000, max_wait_ms: int=7200000,
             evaluation_budget: int=100000) -> dict:
    if mode not in MODES:
        raise ValueError('Unknown release mode')
    time_value(horizon_ms,'horizon',positive_only=True); time_value(max_wait_ms,'max wait')
    if not compiled.platforms:
        raise ValueError('No platform inventory')
    permissions=compiled.provenance['network']['metadata'].get('route_permissions')
    if not permissions:
        raise ValueError('Explicit arrival/departure permissions required')
    for pid in compiled.platforms:
        rin=compiled.routes.get(f'{pid}:in'); rout=compiled.routes.get(f'{pid}:out')
        if rin is None or rout is None:
            continue
        if rin.start!=permissions['arrival_boundary'] or rout.end!=permissions['departure_boundary']:
            raise ValueError('Compiled route violates arrival/departure boundary permission')
    closed=set() if closed is None else set(closed)
    if not closed.issubset(compiled.platforms):
        raise ValueError('Unknown closed platform')
    platforms=[Platform(**{k:p[k] for k in ('id','label','bank','usable_length_m','margin_each_end_m')})
               for p in compiled.platforms.values()]
    ordered=validate_stock(visits); budget=Budget(evaluation_budget); calendar=Calendar()
    assigned={}; rejected=[]; exhausted=False; legs={}
    def leg(pid,length,direction):
        key=(pid,length,direction)
        if key not in legs:
            legs[key]=compile_leg(compiled,f'{pid}:{direction}',length,direction,profile,mode)
        return legs[key]
    for v in ordered:
        if exhausted:
            rejected.append({'visit_id':v.id,'reason':'search_exhausted'}); continue
        if v.predecessor and v.predecessor not in assigned:
            rejected.append({'visit_id':v.id,'reason':'predecessor_not_scheduled'}); continue
        ready=v.requested_entry_ms
        if v.predecessor:
            ready=max(ready,assigned[v.predecessor]['exit_clear_ms']+v.external_cycle_ms)
        eligible=[p for p in platforms if p.id not in closed and p.fits(v.length_m)
                  and v.inbound_group=='A' and v.outbound_group=='A'
                  and f'{p.id}:in' in compiled.routes and f'{p.id}:out' in compiled.routes]
        if not eligible:
            rejected.append({'visit_id':v.id,'reason':'no_legal_complete_opportunity'}); continue
        alternatives=[]
        try:
            for p in sorted(eligible,key=lambda p:p.id):
                lin=leg(p.id,v.length_m,'in'); lout=leg(p.id,v.length_m,'out')
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
                         'arrival_motion':lin.motion.export(),'departure_motion':lout.motion.export(),
                         'incoming_release_end_ms':t+lin.release_end_ms,
                         'incoming_distance_m':lin.route_length_m,'outgoing_distance_m':lout.route_length_m,
                         'outgoing_kind':v.outgoing_kind,'claims':claims,'witnesses':witnesses})
                    break
        except BudgetExhausted:
            exhausted=True; rejected.append({'visit_id':v.id,'reason':'search_exhausted'}); continue
        if not alternatives:
            rejected.append({'visit_id':v.id,'reason':'not_scheduled_within_entry_wait_budget'}); continue
        best=min(alternatives,key=lambda a:(a['departure_delay_ms'],a['entry_ms'],a['platform_id']))
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
    return {'model_version':'0.4.0','fidelity':'synthetic_geometry_and_release; selected_UK_values_separate',
       'mode':mode,'compile_hash':compiled.compile_hash,'profile':asdict(profile),
       'required_visits':len(visits),'scheduled_visits':len(values),'unscheduled_visits':len(rejected),
       'completed_within_horizon':counts['completed'],'scheduled_residual_at_horizon':len(values)-counts['completed'],
       'horizon_ms':horizon_ms,'scheduled_states_at_horizon':counts,
       'all_required_scheduled':not rejected,
       'all_required_completed_within_horizon':not rejected and counts['completed']==len(visits),
       'total_departure_delay_ms':sum(a['departure_delay_ms'] for a in values),
       'candidate_evaluations':budget.evaluations,
       'assignments':[{**a,'claims':[asdict(c) for c in a['claims']]} for a in values],
       'rejected':rejected,
       'assessments':{'reservation_invariants':'pass','explicit_two_approach_geometry':'compiled_synthetic',
         'shared_throat':'retained; separate external leads do not prove independence',
         'kinematics':'analytic_constant_acceleration_level_track_only',
         'sectional_release':'synthetic_edge_sections' if mode=='sectional_release' else 'conservative_whole_route',
         'real_interlocking':'unassessed','UK_component_and_vehicle_gauging':'unassessed',
         'eight_platform_station':'not_implemented','braking_curve_validation':'uncalibrated',
         'spatial_queues':'unassessed; waiting_outside_model is a temporal count',
         'passenger_circulation':'unassessed','game_construction':'not_tested',
         'full_UK_engineering_profile':'incomplete; selected rule checks do not promote this assembly'}}
