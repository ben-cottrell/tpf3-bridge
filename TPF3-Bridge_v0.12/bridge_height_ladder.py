"""Observed-height compact pointwork with four native graded approach leads."""
import hashlib
import json
import math
import uuid
from pathlib import Path
import bridge_live as live
import bridge_ladder as ladder

LAYOUT='native_observed_height_ladder_v1'

def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate(brief):
    keys={'layout','roles','groups','movements','radius','turnout_radii','region','vertical','max_route_length','placement_tolerance','spacing','throat_length','endpoint_tolerance'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=LAYOUT:raise ValueError('observed-height ladder brief required')
    for name,lo,hi in [('throat_length',200,800),('endpoint_tolerance',.001,10)]:
        v=brief[name]
        if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(name+' outside supported finite bounds')
    if not isinstance(brief['roles'],dict) or len(brief['roles'])!=10:raise ValueError('ten explicit endpoint roles required')
    for r in brief['roles'].values():
        if not isinstance(r,dict) or set(r)!={'kind','position','travel_direction'} or r['kind'] not in ('approach','destination'):raise ValueError('explicit endpoint kind/position/direction required')
        e=ladder.intent(r['position'],r['travel_direction'])
        live.validate_project_brief({k:brief[k] for k in ('radius','region','vertical','max_route_length')}|{'source':e,'target':e,'max_fit_attempts':1},corridor=True)
    if sum(r['kind']=='approach' for r in brief['roles'].values())!=4:raise ValueError('four approaches and six destinations required')
    return brief

def _intent(brief,role):
    e=ladder.intent(role['position'],role['travel_direction']);t=brief['endpoint_tolerance']
    e['region']={'min':[v-t-1 for v in role['position']],'max':[v+t+1 for v in role['position']]}
    return e

def _ports(client,brief,*,old=None,connected=False):
    ports={};observations=[]
    for n,r in brief['roles'].items():
        # Hints identify a bounded area; the selected exact native node is authority.
        e=_intent(brief,r) if old is None else ladder.intent(old[n]['pos'],r['travel_direction'])
        c,rid=live._select_throat_port(client,e,tolerance=brief['endpoint_tolerance'] if old is None else .001,outward_sign=1 if r['kind']=='approach' else -1,connected=connected)
        observations.append(rid)
        edge=c['edge_snapshot'];end=0 if c['node_id']==edge['node0'] else 1;t=edge['t'+str(end)];grade=abs(t[2])/math.hypot(*t[:2])
        if edge['road_type']!='TRACK' or grade>brief['vertical']['max_grade']:raise live.LiveError('unsupported_height_ladder','current native TRACK/selected grade required')
        if old:
            before=old[n];be=before['edge_snapshot'];bi=0 if before['node_id']==be['node0'] else 1
            bt=be['t'+str(bi)];a=[v/math.dist(t,[0,0,0]) for v in t];b=[v/math.dist(bt,[0,0,0]) for v in bt]
            if c['node_id']!=before['node_id'] or math.dist(c['pos'],before['pos'])>.001 or math.dist(a,b)>1e-5:raise live.LiveError('attachment_identity_changed','fixed endpoint identity/geometry changed: '+n)
        ports[n]=c
    return ports,observations

def derive(brief,ports):
    """Only observed endpoint XYZ/tangents choose the level throat and lead controls."""
    validate(brief)
    if set(ports)!=set(brief['roles']):raise ValueError('all observed role bindings required')
    actual={}
    for n,r in brief['roles'].items():
        c=ports[n];e=c['edge_snapshot'];end=0 if c['node_id']==e['node0'] else 1;t=e['t'+str(end)];length=math.hypot(*t[:2])
        if length<=0 or e['road_type']!='TRACK':raise live.LiveError('unsupported_height_ladder','regular native TRACK tangent required')
        # Snapshot t0/t1 follow edge ordering, not necessarily construction travel.
        d=c['outward_direction'];sign=1 if r['kind']=='approach' else -1
        horizontal=math.hypot(*d[:2])
        actual[n]={'kind':r['kind'],'position':c['pos'],'travel_direction':[sign*v/horizontal for v in d[:2]]}
        if r['kind']=='destination' and abs(t[2])/length>1e-6:raise live.LiveError('unsupported_height_ladder','nonlevel destination tangent; cannot flatten native track')
    ds=[r for r in actual.values() if r['kind']=='destination'];height=ds[0]['position'][2]
    if any(abs(r['position'][2]-height)>.001 for r in ds):raise live.LiveError('unsupported_height_ladder','nonlevel destination bank; cannot flatten native track')
    direction=ds[0]['travel_direction'];length=math.hypot(*direction);direction=[x/length for x in direction];normal=[-direction[1],direction[0]]
    origin=ds[0]['position'];xbank=sum(origin[k]*direction[k] for k in range(2));xcore=xbank-brief['throat_length']
    core={k:v for k,v in brief.items() if k not in ('throat_length','endpoint_tolerance')};core.update(layout=ladder.COMPACT_LAYOUT,roles={})
    leads=[]
    for n,r in actual.items():
        p=r['position'];d=r['travel_direction'];norm=math.hypot(*d)
        if math.dist([x/norm for x in d],direction)>1e-5:raise live.LiveError('unsupported_height_ladder','parallel aligned destination/approach headings required')
        if r['kind']=='destination':
            if abs(sum(p[k]*direction[k] for k in range(2))-xbank)>.001:raise live.LiveError('unsupported_height_ladder','nonaligned destination bank')
            core['roles'][n]=r
        else:
            y=sum(p[k]*normal[k] for k in range(2));target=[direction[k]*xcore+normal[k]*y for k in range(2)]+[height]
            length=xcore-sum(p[k]*direction[k] for k in range(2))
            if not 20<=length<=800:raise live.LiveError('unsupported_height_ladder','native external lead must span20..800 units before pointwork')
            c=ports[n];e=c['edge_snapshot'];i=0 if c['node_id']==e['node0'] else 1;t=e['t'+str(i)];source_grade=t[2]/math.hypot(*t[:2])*(1 if i==1 else -1)
            if abs(source_grade)>brief['vertical']['max_grade']:raise live.LiveError('unsupported_height_ladder','external grade exceeds selected limit')
            q={'anchor_edge':c['edge_id'],'anchor_node':c['node_id'],'end_xy':target[:2],'end_direction':direction,'radius':brief['radius'],'region':ladder._arm_region(brief,ladder.intent(p,d),ladder.intent(target,direction)),'vertical':brief['vertical']|{'end_height':height,'end_grade':0}}
            live.validate_brief(q)
            leads.append({'role':n,'source':p,'source_grade':source_grade,'target':target,'brief':q})
            core['roles'][n]={'kind':'approach','position':target,'travel_direction':direction}
    controls=ladder.plan_compact_ladder(core)
    # Fitting controls are not additional hard acceptance requirements on every
    # existing through edge. Keep the user-selected project minimum unchanged.
    low=json.loads(json.dumps(controls['brief']))
    for g in low['groups']:
        g['fit_radii']=[1.05*v for v in g['junction_radii']]
        g['junction_radii']=[brief['radius']]*3
    coreplan=ladder.plan_ladder(low)
    plan={'version':1,'epoch':'DESIGN','brief':brief,'observed_roles':actual,'initial_ports':ports,'core_plan':coreplan,'leads':leads,'destination_height':height,'game_constructed':False,'limits':{'native_fitting_required':True,'terrain_optimised':False,'continuous_clearance_proof':False}}
    plan['plan_hash']=_hash(plan);return plan

def plan_height_ladder(client,brief):
    validate(brief);ports,observations=_ports(client,brief);p=derive(brief,ports)
    path=client.evidence/(uuid.uuid4().hex+'.height_ladder_plan.json');live.atomic_json(path,{'plan':p,'observations':observations})
    return {'status':'ok','operation':'height-ladder','stage':'observed_plan','game_constructed':False,'destination_height':p['destination_height'],'graded_leads':4,'movements':12,'plan_hash':p['plan_hash'],'evidence':str(path.resolve())}

def _canonical(plan):
    if plan!=derive(plan['brief'],plan['initial_ports']):raise ValueError('observed-height plan/binding changed')

def _finish(record,path,exc=None):
    s=record['summary']
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_network_verified=False)
    s.update(evidence=str(path.resolve()),plan_hash=record['plan']['plan_hash'],destination_height=record['plan']['destination_height'],operations_recorded=len(record['operations']),train_traversal='unprobed',continuous_clearance_proof=False,native_effect_history_complete=False)
    live.atomic_json(path,record);return s

def _assess(client,record):
    p=record['plan'];ports,ids=_ports(client,p['brief'],old=p['initial_ports'],connected=True);record['current_ports']=ports;record['observations']+=ids
    core=live._load_layout_record(record['core_record'])
    if core['plan']!=p['core_plan']:raise ValueError('core receipt differs from observed-height plan')
    checked=ladder.inspect_ladder(client,record['core_record']);record['core_inspection']=checked
    if checked['status']!='ok':raise live.LiveError(checked['status'],checked.get('error','level pointwork not verified'))
    # Reuse the same exact ordered-junction proof, with external fixed ports.
    result=ladder._assess(client,core['plan'],record,ports=ports)
    count=_level_pointwork(client,record)
    result.update(level_pointwork_verified=True,pointwork_edges_verified=count,native_movement_height=record['native_movement_height']);return result

def _level_pointwork(client,record):
    # A permitted graded route is not sufficient proof that pointwork is level.
    p=record['plan'];excluded=set(record['lead_edges'])|{c['edge_id'] for c in p['initial_ports'].values()}
    ports=record.get('current_ports',p['initial_ports'])
    destination_ids=sorted({ports[n]['edge_id'] for n,r in p['brief']['roles'].items() if r['kind']=='destination'})
    baseline=client.request('inspect',{'edge_ids':destination_ids,'geometry':True})
    if baseline['status']!='ok' or {e['id'] for e in baseline['result']['edges']}!=set(destination_ids):raise live.LiveError('native_verification_failed','destination movement-height read incomplete')
    heights=[q['pos'][2] for e in baseline['result']['edges'] for q in e['movement_geometry']['samples']]
    if not heights or max(heights)-min(heights)>.001 or any(abs(q['direction'][2])>1e-6 for e in baseline['result']['edges'] for q in e['movement_geometry']['samples']):raise live.LiveError('native_verification_failed','native destination movement bank is not level')
    movement_height=heights[0];record['destination_movement_geometry']=baseline;record['native_movement_height']=movement_height
    ids=sorted({q['edge']['entity'] for row in record['routes'] for q in row['response']['result']['path'] if q['confirmed_TRACK']}-excluded)
    if not ids:raise live.LiveError('native_verification_failed','level pointwork geometry unavailable')
    observations=[]
    for i in range(0,len(ids),16):
        response=client.request('inspect',{'edge_ids':ids[i:i+16],'geometry':True});observations.append(response)
        if response['status']!='ok' or {e['id'] for e in response['result']['edges']}!=set(ids[i:i+16]):raise live.LiveError('native_verification_failed','current pointwork edge read incomplete')
        for e in response['result']['edges']:
            if any(abs(e[k][2]-p['destination_height'])>.001 for k in ('p0','p1')) or any(abs(e[k][2])>1e-6 for k in ('t0','t1')) or any(abs(q['pos'][2]-movement_height)>.001 or abs(q['direction'][2])>1e-6 for q in e['movement_geometry']['samples']):raise live.LiveError('native_verification_failed','pointwork no longer level at observed destination height')
    record['pointwork_geometry']=observations
    return len(ids)

def execute_height_ladder(client,brief,*,layout_record=None):
    validate(brief)
    prior=None;core_prior=None
    if layout_record:
        old=live._load_layout_record(layout_record)
        if old['plan']['brief']!=brief:raise ValueError('saved brief differs')
        _canonical(old['plan'])
        if not old.get('unfinished_step') and old.get('summary',{}).get('status')=='ok':return inspect_height_ladder(client,layout_record,checked=True)
        ops=old.get('operations',[])
        if old.get('unfinished_step')!='level_throat' or len(ops)!=5 or any(ops[i]['name']!='lead_'+old['plan']['leads'][i]['role'] or ops[i]['response'].get('status')!='ok' for i in range(4)) or ops[4]['name']!='level_throat':raise live.LiveError('reconciliation_required','only explicit four-completed-lead prefix is supported; no replay')
        core=live._load_layout_record(old['core_record']);core_ops=core.get('operations',[])
        if len(core_ops)==1 and core_ops[0]['name']==core['plan']['steps'][0]['name']:
            failed=live._load_layout_record(core_ops[0]['response']['evidence']);attempts=failed.get('attempts',[])
            rid=attempts[-1]['request_id'] if attempts else None
            rp=client.evidence/(str(rid)+'.reconciliation.json');proof=json.loads(rp.read_text()) if rp.exists() else {}
            if proof.get('status')!='reconciled_rejected_corridor' or proof.get('completed_corridor_absent') is not True or proof.get('original_pending',{}).get('request_id')!=rid:raise live.LiveError('reconciliation_required','first core corridor absence not independently reconciled')
        else:core_prior=old['core_record'] # Existing ladder prefix checks remain binding.
        prior=old
    if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending native operation; no construction')
    if prior:
        plan=prior['plan'];ports,observations=_ports(client,brief,old=plan['initial_ports'],connected=True);proofs=[]
        for lead,op in zip(plan['leads'],prior['operations'][:4]):
            answer=op['response'];ids=answer.get('edges',[]);nodes=answer.get('nodes',[])
            if not ids or not nodes or nodes[0]!=ports[lead['role']]['node_id']:raise live.LiveError('reconciliation_required','exact saved graded lead binding missing')
            tip,_=live._select_throat_port(client,ladder.intent(lead['target'],lead['brief']['end_direction']),tolerance=.001,connected=True)
            if tip['node_id']!=nodes[-1]:raise live.LiveError('attachment_identity_changed','graded lead tip changed')
            a=ports[lead['role']];q={'source_edge':a['edge_id'],'source_node':ladder._other(a),'target_edge':ids[-1],'target_node':nodes[-1],'required_edges':[a['edge_id'],*ids],'mode':'TRAIN','max_length':brief['max_route_length'],'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':brief['radius'],'max_grade':brief['vertical']['max_grade'],'region':brief['region']}}
            check=client.request('route',q);proofs.append(check)
            if check['status']!='ok' or check.get('result',{}).get('requested_route_verified') is not True or check['result'].get('truncated'):raise live.LiveError('reconciliation_required','completed graded lead not freshly proven')
    else:ports,observations=_ports(client,brief);plan=derive(brief,ports)
    path=client.evidence/(uuid.uuid4().hex+'.height_ladder.json');record={'plan':plan,'operations':[],'observations':observations,'summary':{'status':'incomplete','operation':'height-ladder','game_constructed':False}}
    try:
        record['lead_edges']=[]
        if prior:
            record.update(operations=prior['operations'][:4],lead_edges=[edge for op in prior['operations'][:4] for edge in op['response']['edges']],continuation={'record':str(Path(layout_record).resolve()),'lead_proofs':proofs,'automatic_replay':False});record['summary'].update(game_constructed=True,recorded_prior_game_constructed=prior['summary'].get('game_constructed','unknown'))
        live.atomic_json(path,record)
        for lead in plan['leads']:
            if prior:continue
            # Fresh exact role identity and geometry before every mutation.
            current,ids=_ports(client,brief,old=ports,connected=True);record['observations']+=ids
            c=current[lead['role']]
            if c.get('eligible') is not True:raise live.LiveError('reconciliation_required','external lead already attached; no replay')
            q=lead['brief']|{'anchor_edge':c['edge_id'],'anchor_node':c['node_id']}
            record['unfinished_step']='lead_'+lead['role'];live.atomic_json(path,record)
            answer=live.extend(client,q,execute=True);record['operations'].append({'name':record['unfinished_step'],'response':answer})
            if answer.get('game_constructed') is True:record['summary']['game_constructed']=True
            elif answer.get('game_constructed','unknown')=='unknown':record['summary']['game_constructed']='unknown'
            live.atomic_json(path,record)
            if answer['status']!='ok':raise live.LiveError(answer['status'],answer.get('error','graded lead failed'))
            record['lead_edges']+=answer['edges']
            record.pop('unfinished_step');live.atomic_json(path,record)
        record['unfinished_step']='level_throat';live.atomic_json(path,record)
        answer=ladder.execute_ladder(client,plan['core_plan'],layout_record=core_prior);record['operations'].append({'name':'level_throat','response':answer});record['core_record']=answer['evidence']
        if answer.get('game_constructed')=='unknown':record['summary']['game_constructed']='unknown'
        live.atomic_json(path,record)
        if answer['status']!='ok':raise live.LiveError(answer['status'],answer.get('error','pointwork failed'))
        record.pop('unfinished_step');record['summary'].update(_assess(client,record));return _finish(record,path)
    except (live.LiveError,ValueError,KeyError,TypeError,OSError) as exc:return _finish(record,path,exc)

def inspect_height_ladder(client,layout_record,*,checked=False):
    old=live._load_layout_record(layout_record);_canonical(old['plan'])
    if not old.get('core_record'):raise live.LiveError('incomplete_record','level throat receipt unavailable; no construction')
    path=client.evidence/(uuid.uuid4().hex+'.height_ladder_inspection.json')
    record={'plan':old['plan'],'core_record':old['core_record'],'lead_edges':old['lead_edges'],'prior_record':str(Path(layout_record).resolve()),'operations':[],'observations':[],'summary':{'status':'incomplete','operation':'height-ladder-inspect','game_constructed':False,'recorded_prior_game_constructed':old.get('summary',{}).get('game_constructed','unknown'),'checked_existing':checked,'prior_unfinished_step':old.get('unfinished_step')}}
    try:record['summary'].update(_assess(client,record));return _finish(record,path)
    except (live.LiveError,ValueError,KeyError,TypeError,OSError) as exc:return _finish(record,path,exc)
