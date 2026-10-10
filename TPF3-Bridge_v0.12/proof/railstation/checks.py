"""Independent result checks and scoped site/independence evidence.

The checker's interval sweep does not call Calendar.verify/conflict. It tests
stored results independently of the scheduling calendar; geometry and kinematics
still have their own lower-level tests and are not independently reimplemented.
"""
from __future__ import annotations
from dataclasses import asdict
import math
from railproof.model import Visit
from railclear.model import digest
from railgeom.compiler import CompiledAssembly
from .composition import Station


def check_result(compiled:CompiledAssembly, visits:list[Visit], result:dict)->dict:
    errors=[];seen=set();by_id={v.id:v for v in visits};assigned={}
    if result['compile_hash']!=compiled.compile_hash: errors.append('wrong_compile_hash')
    events={}
    for a in result['assignments']:
        vid=a['visit_id']
        if vid in seen or vid not in by_id:errors.append('unknown_or_duplicate_visit');continue
        seen.add(vid);assigned[vid]=a;v=by_id[vid]
        p=compiled.platforms[a['platform_id']]
        rin=f'{v.inbound_group}:{p["id"]}:in';rout=f'{v.outbound_group}:{p["id"]}:out'
        if a['incoming_route']!=rin or a['outgoing_route']!=rout or rin not in compiled.routes or rout not in compiled.routes:
            errors.append('invalid_complete_route');continue
        if p['id'] in result['closed_platforms']:errors.append('closed_platform')
        used=set(compiled.routes[rin].edge_ids)|set(compiled.routes[rout].edge_ids)|{p['storage_edge']}
        if used & set(result['closed_edges']):errors.append('closed_route_edge')
        if not result['allow_recovery'] and (v.inbound_group!=p['bank'] or v.outbound_group!=p['bank']):
            errors.append('unauthorised_recovery')
        if v.length_m+2*p['margin_each_end_m']>p['usable_length_m']:errors.append('overlength')
        if a['train_length_m']!=v.length_m or a['stock_id']!=v.stock_id:errors.append('changed_stock')
        if not (v.requested_entry_ms<=a['entry_ms']<=a['entry_motion_ms']<=a['berthed_ms']<=a['departure_ms']<=a['departure_motion_ms']<=a['tail_exits_ms']<=a['exit_clear_ms']):
            errors.append('activity_order')
        if a['departure_ms']<max(v.planned_departure_ms,a['berthed_ms']+v.readiness_ms,a['incoming_release_end_ms']):
            errors.append('premature_departure')
        if a['departure_delay_ms']!=a['departure_ms']-v.planned_departure_ms:errors.append('wrong_delay')
        must={r.resource for rid in (rin,rout) for r in compiled.routes[rid].requirements}
        must|={r.resource for r in compiled.edge_requirements[p['storage_edge']]}
        must.add('berth:'+p['id'])
        for rid,activation in ((rin,a['entry_ms']),(rout,a['departure_ms'])):
            for req in compiled.routes[rid].requirements:
                if not any(c['resource']==req.resource and c['state']==req.state and c['start_ms']<=activation<c['end_ms'] for c in a['claims']):
                    errors.append('missing_or_wrong_route_state_at_activation')
        present={c['resource'] for c in a['claims']}
        if not must.issubset(present):errors.append('missing_required_resource')
        holding={r.resource for r in compiled.edge_requirements[p['storage_edge']]}|{'berth:'+p['id']}
        for res in holding:
            if not any(c['resource']==res and c['state'] is None and c['start_ms']<=a['entry_ms'] and c['end_ms']>=a['exit_clear_ms'] for c in a['claims']):
                errors.append('unheld_storage')
        for i,c in enumerate(a['claims']):
            if c['owner']!=vid or c['end_ms']<=c['start_ms'] or c['start_ms']<0:errors.append('invalid_claim')
            token=(vid,i)
            events.setdefault(c['resource'],[]).extend([(c['start_ms'],1,token,c['state']),(c['end_ms'],0,token,c['state'])])
    rejected=[r['visit_id'] for r in result['rejected']]
    if len(rejected)!=len(set(rejected)) or set(rejected)&seen or seen|set(rejected)!=set(by_id):errors.append('demand_not_conserved')
    for vid,a in assigned.items():
        v=by_id[vid]
        if v.predecessor:
            pred=assigned.get(v.predecessor)
            if pred is None or a['entry_ms']<pred['exit_clear_ms']+v.external_cycle_ms:errors.append('stock_precedence')
    # End events precede start events at a half-open boundary. Equal state locks
    # are compatible; exclusive occupancy is not, even for the same owner.
    conflict_witnesses=[]
    for res,ev in events.items():
        active={}
        for time,kind,token,state in sorted(ev,key=lambda e:(e[0],e[1],e[2])):
            if kind==0: active.pop(token,None);continue
            for other,ostate in active.items():
                if state is None or ostate is None or state!=ostate:
                    conflict_witnesses.append({'resource':res,'at_ms':time,'claims':[token,other]})
            active[token]=state
    if conflict_witnesses:errors.append('incompatible_interval_overlap')
    complete=sum(a['exit_clear_ms']<=result['horizon_ms'] for a in assigned.values())
    if result['required_visits']!=len(visits) or result['scheduled_visits']!=len(assigned) or result['unscheduled_visits']!=len(rejected):errors.append('wrong_counts')
    if result['completed_within_horizon']!=complete or result['scheduled_residual_at_horizon']!=len(assigned)-complete:errors.append('wrong_horizon_accounting')
    if sum(result['scheduled_states_at_horizon'].values())!=len(assigned):errors.append('wrong_state_total')
    if result['total_departure_delay_ms']!=sum(a['departure_delay_ms'] for a in assigned.values()):errors.append('wrong_delay_sum')
    if result['all_required_scheduled']!=(not rejected):errors.append('wrong_scheduled_status')
    if result['all_required_completed_within_horizon']!=(not rejected and complete==len(visits)):errors.append('wrong_completion_status')
    return {'status':'pass' if not errors else 'fail','errors':sorted(set(errors)),
            'conflict_witnesses':conflict_witnesses[:20],'required_visits':len(visits),
            'compile_hash':compiled.compile_hash,'checker':'independent_interval_sweep_and_complete_visit_invariants_v06',
            'scope':'reservation verification; not real-world or game validation'}



def independence(compiled:CompiledAssembly)->dict:
    normal={g:[r for rid,r in compiled.routes.items() if rid.split(':')[0]==g and rid.split(':')[1].startswith(g)] for g in ('A','B')}
    rows=[]
    for a in normal['A']:
        for b in normal['B']:
            shared=[]
            for x in a.requirements:
                for y in b.requirements:
                    if x.resource==y.resource and (x.state is None or y.state is None or x.state!=y.state):
                        shared.append(x.resource)
            rows.append({'route_a':a.id,'route_b':b.id,'conflicts':sorted(set(shared))})
    return {'status':'independent_in_compiled_resource_model' if all(not r['conflicts'] for r in rows) else 'shared_conflicts',
            'route_pair_count':len(rows),'pairs':rows,'compile_hash':compiled.compile_hash,
            'not_established':['real interlocking independence','full dynamic gauging','game routing']}


def site_check(station:Station,box:list[float],*,padding_m:float=0.,expected_ports:dict|None=None,
               reservations:list[dict]|None=None)->dict:
    if not isinstance(box,list) or len(box)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in box):raise ValueError('Invalid site box')
    xmin,ymin,xmax,ymax=box
    if xmax<=xmin or ymax<=ymin:raise ValueError('Degenerate site')
    if isinstance(padding_m,bool) or not isinstance(padding_m,(int,float)) or not math.isfinite(padding_m) or padding_m<0:raise ValueError('Invalid padding')
    n=station.assembly.network
    b=[e.curve.bounds() for e in n.edges.values()]
    envelope=[min(x[0] for x in b)-padding_m,min(x[1] for x in b)-padding_m,max(x[2] for x in b)+padding_m,max(x[3] for x in b)+padding_m]
    outside=[p.id for p in n.ports.values() if not xmin<=p.position[0]<=xmax or not ymin<=p.position[1]<=ymax]
    fit=envelope[0]>=xmin and envelope[1]>=ymin and envelope[2]<=xmax and envelope[3]<=ymax
    discrepancies=[]
    if expected_ports:
        for pid,xy in expected_ports.items():
            if pid not in n.ports or math.dist(n.ports[pid].position,xy)>1e-6:
                discrepancies.append({'port':pid,'required_m':xy,'actual_m':list(n.ports[pid].position) if pid in n.ports else None})
    reserve_rows=[]
    for r in reservations or []:
        rect=r['box_m']
        if len(rect)!=4 or not rect[0]<rect[2] or not rect[1]<rect[3] or any(not math.isfinite(v) for v in rect):raise ValueError('Invalid reservation')
        inside=rect[0]>=xmin and rect[1]>=ymin and rect[2]<=xmax and rect[3]<=ymax
        # A box intersection with a curve hull is only a conservative candidate
        # contact, not proof that a 3D structure touches a vehicle.
        overlaps=[eid for eid,e in n.edges.items() if not (e.curve.bounds()[2]+padding_m<rect[0] or e.curve.bounds()[0]-padding_m>rect[2] or e.curve.bounds()[3]+padding_m<rect[1] or e.curve.bounds()[1]-padding_m>rect[3])]
        reserve_rows.append({'id':r['id'],'contained':inside,'possible_rail_contacts':overlaps,'kind':'planar_reserved_volume_only'})
    badres=any(not r['contained'] or r['possible_rail_contacts'] for r in reserve_rows)
    status='fail' if outside or discrepancies or badres else ('pass_within_scope' if fit else 'not_certified_by_hull')
    return {'status':status,'site_box_m':box,'rail_control_hull_envelope_m':envelope,
            'padding_m':padding_m,'actual_ports_outside':outside,'required_port_mismatches':discrepancies,
            'reservations':reserve_rows,'source_hash':n.digest(),
            'scope':'plan centreline/hull and supplied reservations, not structural or dynamic gauge approval',
            'construction_authorised':False}
