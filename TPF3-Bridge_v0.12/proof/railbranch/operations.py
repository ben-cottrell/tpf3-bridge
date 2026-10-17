"""Whole-pass reservation planning over connected geometry.

All future space/time claims are booked together; this is NOT live signalling,
just-in-time authority, physical waiting queues, or a timetable capacity model.
The retained level-track motion law is deliberately uncalibrated and ignores
traction changes on the new grades. Geometry still checks those grades.
"""
from __future__ import annotations
from dataclasses import asdict
from copy import deepcopy
import math
from railcorridor.geometry import digest, number, integer
from railproof.model import Claim, conflict
from railproof.engine import Calendar, Budget, BudgetExhausted
from railops.motion import MotionProfile, make_motion
from .geometry import Junction, ROUTES


def verify_candidate(j):
    a=j.assessment
    if a.get('candidate_hash')!=digest({k:v for k,v in a.items() if k!='candidate_hash'}):raise ValueError('candidate hash mismatch')
    if digest(a['network'])!=digest(j.network.canonical()) or digest(a['height_profiles'])!=digest({k:v.record() for k,v in j.height.items()}):raise ValueError('stale physical network')
    if digest(a['spec'])!=digest(asdict(j.spec)) or a['mode']!=j.mode:raise ValueError('stale specification')
    if not a['accepted_for_reference_comparison']:raise ValueError('candidate geometry not accepted')
    for r,p in j.routes.items():
        q=j.network.one_path(p.start,p.end,r)
        if q!=p:raise ValueError('stale/illegal route')
        expected=a['routes'][r]
        if [s.edge_id for s in p.steps]!=[s['edge_id'] for s in expected['steps']]:raise ValueError('stale route identity')


def compile_resources(j):
    verify_candidate(j);result={};cross=j.assessment['crossing'];all_resources={}
    for rid,r in j.assessment['routes'].items():
        fp=[]
        def add(res,s0,s1,kind='exclusive',state=None,origin=None):
            fp.append({'resource':res,'s0_m':s0,'s1_m':s1,'kind':kind,'state':state,'origin':origin})
            all_resources[res]={'kind':kind,'origin':origin}
        for st in r['steps']:
            eid=st['edge_id'];e=j.network.edges[eid]
            add('track:'+eid,st['s0_m'],st['s1_m'],origin='physical_edge')
            if e.component:
                add('body:'+e.component,st['s0_m'],st['s1_m'],origin='complete_component')
                add('state:'+e.controller,st['s0_m'],st['s1_m'],'state',e.state,'component_control')
            if not cross['separated_within_project_envelope'] and eid in cross['edge_ids']:
                a,b=cross['footprint_x_m'];x0=e.curve.at(0)[0];x1=e.curve.at(1)[0]
                if st['forward']:
                    s0=st['s0_m']+j.length(eid,x0,a);s1=st['s0_m']+j.length(eid,x0,b)
                else:
                    s0=st['s0_m']+j.length(eid,b,x1);s1=st['s0_m']+j.length(eid,a,x1)
                add('crossing:RETURN_OVER_EAST',s0,s1,origin='derived_plan_crossing_footprint')
        result[rid]={'length_m':r['length_m'],'footprints':fp}
    pairs=[]
    for i,r in enumerate(ROUTES):
        for q in ROUTES[i+1:]:
            shared=[]
            for a in result[r]['footprints']:
                for b in result[q]['footprints']:
                    if a['resource']==b['resource'] and (a['kind']=='exclusive' or a['state']!=b['state']):shared.append(a['resource'])
            pairs.append({'a':r,'b':q,'incompatible_shared_resources':sorted(set(shared))})
    out={'version':'0.10.0','candidate_hash':j.assessment['candidate_hash'],'routes':result,'resources':all_resources,'route_pairs':pairs,
         'scope':'physical edge/component and declared crossing model; not full dynamic gauging or actual signalling'}
    out['resource_hash']=digest(out);return out


def default_performance():
    return {'main_speed_mph':60.,'branch_speed_mph':15.,'acceleration_mps2':.6,'braking_mps2':.7,'setup_ms':5000,'release_ms':3000}


def validate_performance(p):
    if set(p)!=set(default_performance()):raise ValueError('performance schema')
    for k in ('main_speed_mph','branch_speed_mph'):number(p[k],k,minimum=1,maximum=125)
    for k in ('acceleration_mps2','braking_mps2'):number(p[k],k,minimum=.01,maximum=2)
    for k in ('setup_ms','release_ms'):integer(p[k],k,maximum=120000)
    return deepcopy(p)


def leg(compiled,route,train_length_m,performance):
    if route not in ROUTES:raise ValueError('unknown movement')
    number(train_length_m,'train length',minimum=1,maximum=1000);p=validate_performance(performance)
    r=compiled['routes'][route]
    speed=p['main_speed_mph'] if route.startswith('main') else p['branch_speed_mph']
    profile=MotionProfile(speed*.44704,p['acceleration_mps2'],p['braking_mps2'],p['setup_ms'],p['release_ms'])
    motion=make_motion(r['length_m']+train_length_m,profile,stop_at_end=False)
    claims=[]
    for f in r['footprints']:
        front=motion.time_at(f['s0_m']);tail=motion.time_at(f['s1_m']+train_length_m)
        # Start is setup_ms ahead of the projected front arrival. Round outward.
        claims.append({'resource':f['resource'],'kind':f['kind'],'state':f['state'],
                       'start_ms':max(0,math.floor(front*1000)),
                       'end_ms':p['setup_ms']+math.ceil(tail*1000)+p['release_ms'],
                       'front_entry_ms':p['setup_ms']+math.floor(front*1000),
                       'tail_clear_ms':p['setup_ms']+math.ceil(tail*1000)})
    return {'route':route,'formation_length_m':train_length_m,'length_m':r['length_m'],'claims':claims,
            'motion':motion.export(),'front_exit_ms':p['setup_ms']+math.ceil(motion.time_at(r['length_m'])*1000),
            'clear_ms':p['setup_ms']+math.ceil(motion.duration_s*1000)+p['release_ms'],
            'profile_hash':digest(p),'grade_sensitive_performance':False,'entry_at_rest':True,
            'external_tail_continuation_m':train_length_m,'external_continuation_verified':False}


def make_claims(template,start,owner):
    return [Claim(c['resource'],start+c['start_ms'],start+c['end_ms'],owner,c['state']) for c in template['claims']]


def validate_scenario(s,compiled):
    fields={'id','requests','closures','blocked_intervals','horizon_ms','max_wait_ms','evaluation_budget','description'}
    if not isinstance(s,dict) or set(s)!=fields:raise ValueError('scenario schema')
    from railclear.catalogue import identifier
    identifier(s['id'])
    if not isinstance(s['description'],str) or len(s['description'])>3000:raise ValueError('scenario description')
    for k in ('horizon_ms','max_wait_ms','evaluation_budget'):integer(s[k],k,minimum=1 if k=='horizon_ms' else 0,maximum=100000000)
    if not isinstance(s['requests'],list) or len(s['requests'])>500:raise ValueError('request budget')
    ids=set()
    for r in s['requests']:
        if set(r)!={'id','route','requested_ms','train_length_m'}:raise ValueError('request schema')
        identifier(r['id'])
        if r['id'] in ids or r['id'].startswith('BLOCK_'):raise ValueError('duplicate/reserved request ID')
        ids.add(r['id'])
        if r['route'] not in compiled['routes']:raise ValueError('unknown requested route')
        integer(r['requested_ms'],'requested time',maximum=100000000)
        number(r['train_length_m'],'train length',minimum=1,maximum=1000)
    if not isinstance(s['closures'],list) or len(set(s['closures']))!=len(s['closures']):raise ValueError('closures')
    if any(r not in compiled['resources'] for r in s['closures']):raise ValueError('unknown closure resource')
    if not isinstance(s['blocked_intervals'],list) or len(s['blocked_intervals'])>100:raise ValueError('blocked interval budget')
    for b in s['blocked_intervals']:
        if set(b)!={'resource','start_ms','end_ms'} or b['resource'] not in compiled['resources']:raise ValueError('blocked resource')
        if compiled['resources'][b['resource']]['kind']!='exclusive':raise ValueError('block only exclusive resources')
        integer(b['start_ms'],'block start',maximum=100000000);integer(b['end_ms'],'block end',maximum=100000000)
        if b['end_ms']<=b['start_ms']:raise ValueError('block interval ordering')
    return deepcopy(s)


def schedule(j,s,performance=None):
    p=validate_performance(performance or default_performance());comp=compile_resources(j);s=validate_scenario(s,comp)
    cal=Calendar();blocks=[]
    for i,b in enumerate(s['blocked_intervals']):
        c=Claim(b['resource'],b['start_ms'],b['end_ms'],f'BLOCK_{i}')
        cal.reserve([c]);blocks.append(asdict(c))
    budget=Budget(s['evaluation_budget']);assign=[];miss=[];templates={};total_witness={}
    for r in sorted(s['requests'],key=lambda r:(r['requested_ms'],r['id'])):
        key=(r['route'],r['train_length_m'])
        if key not in templates:templates[key]=leg(comp,*key,p)
        t=templates[key]
        closed=sorted(set(s['closures'])&{c['resource'] for c in t['claims']})
        if closed:
            miss.append({'request_id':r['id'],'reason':'required_route_resource_closed','resources':closed});continue
        start=r['requested_ms'];witness=[];status=None
        while True:
            if start>r['requested_ms']+s['max_wait_ms']:status='entry_wait_limit';break
            try:budget.use()
            except BudgetExhausted:status='search_exhausted';break
            claims=make_claims(t,start,r['id']);hits=cal.conflicts(claims)
            if not hits:cal.reserve(claims);break
            move=start
            for c,relative in zip(claims,t['claims']):
                for h in hits:
                    if conflict(c,h):
                        shift=h.end_ms-relative['start_ms'];move=max(move,shift)
                        witness.append({'resource':c.resource,'blocking_owner':h.owner,'blocked_until_ms':h.end_ms,'requested_entry_ms':start})
                        total_witness[c.resource]=total_witness.get(c.resource,0)+1
            if move<=start:raise AssertionError('event search failed to advance')
            start=move
        if status:miss.append({'request_id':r['id'],'reason':status,'witnesses':witness});continue
        clear=start+t['clear_ms'];h=s['horizon_ms']
        phase='completed' if clear<=h else 'not_yet_due' if r['requested_ms']>h else 'waiting_outside_model' if start>h else 'running_or_tail_clearing'
        assign.append({'request_id':r['id'],'route':r['route'],'formation_length_m':r['train_length_m'],
                       'requested_ms':r['requested_ms'],'entry_ms':start,'clear_ms':clear,
                       'entry_delay_ms':start-r['requested_ms'],'state_at_horizon':phase,
                       'claims':[asdict(c) for c in claims],'witnesses':witness})
    report={'version':'0.10.0','candidate_hash':j.assessment['candidate_hash'],'resource_hash':comp['resource_hash'],
            'scenario_hash':digest(s),'performance_hash':digest(p),'scenario_id':s['id'],'mode':j.mode,
            'required':len(s['requests']),'scheduled':len(assign),'completed':sum(a['state_at_horizon']=='completed' for a in assign),
            'unscheduled':len(miss),'residual':sum(a['state_at_horizon']!='completed' for a in assign),
            'total_entry_delay_ms_scheduled_only':sum(a['entry_delay_ms'] for a in assign),'assignments':assign,'unserved':miss,
            'fixed_block_claims':blocks,'conflict_witness_counts':total_witness,'calendar_evaluations':budget.evaluations,
            'assessment_scope':'whole-pass time-space reservation proof; waits occur outside model; not microscopic queues or live signalling',
            'grade_sensitive_performance':False,'terrain_or_game_validated':False,'construction_authorised':False}
    report['independent_check']=check_result(j,s,p,report)
    report['result_hash']=digest(report);return report


def check_result(j,s,p,out):
    """Separate interval-sweep legality check; never calls Calendar.conflicts."""
    errors=[];comp=compile_resources(j);s=validate_scenario(s,comp);p=validate_performance(p)
    for k,v in [('candidate_hash',j.assessment['candidate_hash']),('resource_hash',comp['resource_hash']),('scenario_hash',digest(s)),('performance_hash',digest(p))]:
        if out.get(k)!=v:errors.append('stale_'+k)
    requests={r['id']:r for r in s['requests']};seen=[];claims=[]
    expected_blocks=[asdict(Claim(b['resource'],b['start_ms'],b['end_ms'],f'BLOCK_{i}')) for i,b in enumerate(s['blocked_intervals'])]
    if out.get('fixed_block_claims')!=expected_blocks:errors.append('altered_fixed_blocks')
    claims.extend(expected_blocks)
    for a in out.get('assignments',[]):
        rid=a.get('request_id');seen.append(rid)
        if rid not in requests:errors.append('unknown_assignment');continue
        r=requests[rid]
        if a['route']!=r['route'] or a['formation_length_m']!=r['train_length_m']:errors.append('wrong_movement_or_train')
        if type(a['entry_ms']) is not int or a['entry_ms']<r['requested_ms'] or a['entry_ms']>r['requested_ms']+s['max_wait_ms']:errors.append('invalid_entry_time')
        t=leg(comp,r['route'],r['train_length_m'],p)
        expected=[asdict(c) for c in make_claims(t,a['entry_ms'],rid)]
        if a.get('claims')!=expected:errors.append('altered_or_missing_geometry_claim')
        if any(c['resource'] in s['closures'] for c in expected):errors.append('closed_route_used')
        if a.get('clear_ms')!=a['entry_ms']+t['clear_ms']:errors.append('wrong_tail_clear')
        if a.get('entry_delay_ms')!=a['entry_ms']-r['requested_ms']:errors.append('wrong_delay')
        h=s['horizon_ms'];phase='completed' if a['clear_ms']<=h else 'not_yet_due' if r['requested_ms']>h else 'waiting_outside_model' if a['entry_ms']>h else 'running_or_tail_clearing'
        if a['state_at_horizon']!=phase:errors.append('wrong_horizon_state')
        claims.extend(a.get('claims',[]))
    seen.extend(a.get('request_id') for a in out.get('unserved',[]))
    if len(seen)!=len(set(seen)) or set(seen)!=set(requests):errors.append('demand_not_conserved')
    for k,v in [('required',len(requests)),('scheduled',len(out.get('assignments',[]))),('unscheduled',len(out.get('unserved',[]))),
                ('completed',sum(a['clear_ms']<=s['horizon_ms'] for a in out.get('assignments',[]))),
                ('residual',sum(a['clear_ms']>s['horizon_ms'] for a in out.get('assignments',[]))),
                ('total_entry_delay_ms_scheduled_only',sum(a['entry_ms']-requests[a['request_id']]['requested_ms'] for a in out.get('assignments',[]) if a['request_id'] in requests))]:
        if out.get(k)!=v:errors.append('wrong_'+k)
    byres={}
    for c in claims:byres.setdefault(c['resource'],[]).append(c)
    for res,cs in byres.items():
        active=[]
        for c in sorted(cs,key=lambda c:(c['start_ms'],c['end_ms'],c['owner'])):
            active=[x for x in active if x['end_ms']>c['start_ms']]
            for other in active:
                if other['owner']!=c['owner'] and (c.get('state') is None or other.get('state') is None or c.get('state')!=other.get('state')):
                    errors.append('overlapping_incompatible_resource:'+res)
            active.append(c)
    if out.get('construction_authorised') is not False:errors.append('unexpected_construction_authority')
    return {'passed':not errors,'errors':sorted(set(errors)),
            'scope':'independent output/resource checks; timing template reused, physical model not independently validated'}
