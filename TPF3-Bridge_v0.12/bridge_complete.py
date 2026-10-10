"""Portable ordered tracks with native main geometry and locally level outward forks."""
import hashlib
import json
import math
from pathlib import Path
import uuid

import bridge_live as live
import bridge_parallel as parallel
import bridge_branching as branching

LAYOUT='native_complete_branching_v1'


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _unit(direction):
    if not isinstance(direction,list) or len(direction)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in direction) or math.hypot(*direction)<1e-9:raise ValueError('finite nonzero native XY direction required')
    n=math.hypot(*direction);return [x/n for x in direction]


def _position(value):
    if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):raise ValueError('finite native XYZ required')
    return value


def _move(p,d,length):return [p[0]+length*d[0],p[1]+length*d[1],p[2]]


def plan_complete_layout(brief):
    keys={'layout','seed_edge','reference','tracks','branches','side','spacing','spacing_tolerance','radius','max_grade','region','max_route_length','min_curved_length','site_policy'}
    if not isinstance(brief,dict) or set(brief)-{'vertical_mode','vertical_tolerance','reference_up'}!=keys or brief['layout']!=LAYOUT:raise ValueError('explicit portable complete-layout brief required')
    if type(brief['seed_edge']) is not int or brief['seed_edge']<=0:raise ValueError('exact current native asset seed edge required')
    if brief['site_policy'] not in ('observe','clear_roads'):raise ValueError('explicit observe/clear_roads site policy required')
    ref=brief['reference']
    if not isinstance(ref,dict) or set(ref)!={'start','finish','guides'}:raise ValueError('reference start/finish/guides required')
    ends=[]
    for key in ('start','finish'):
        row=ref[key]
        if not isinstance(row,dict) or set(row)-{'grade'}!={'position','travel_direction'}:raise ValueError('reference position/travel_direction required')
        if 'grade' in row and (type(row['grade']) not in (int,float) or not math.isfinite(row['grade']) or row['grade']!=0):raise live.LiveError('unsupported_layout','complete-layout requires zero endpoint grades for level pointwork')
        ends.append((_position(row['position']),_unit(row['travel_direction'])))
    tracks=brief['tracks']
    if not isinstance(tracks,list) or len(tracks) not in (2,4) or any(not isinstance(t,dict) or set(t)!={'id','direction'} or not isinstance(t['id'],str) or not t['id'] for t in tracks) or '-'.join(t['direction'] for t in tracks) not in ('UP-DOWN','UP-UP-DOWN-DOWN','UP-DOWN-UP-DOWN') or len({t['id'] for t in tracks})!=len(tracks):raise live.LiveError('unsupported_layout','unique ordered UD/UUDD/UDUD roles required')
    reference_up=brief.get('reference_up','increasing')
    if reference_up not in ('increasing','decreasing'):raise ValueError('explicit increasing/decreasing UP reference required')
    main={k:brief[k] for k in ('side','spacing','spacing_tolerance','radius','max_grade','region','max_route_length','min_curved_length')}
    main.update(parallel._vertical_options(brief))
    main.update(layout=parallel.MULTITRACK,reference_up=reference_up,guides=ref['guides'],tracks=[])
    signed=brief['spacing']*(1 if brief['side']=='left' else -1);fixtures=[]
    for i,t in enumerate(tracks):
        row=t|{}
        forward=(t['direction']=='UP')==(reference_up=='increasing')
        for end,(base,d) in zip(('start','end'),ends):
            pos=[base[0]-i*signed*d[1],base[1]+i*signed*d[0],base[2]]
            role=('source' if end=='start' else 'target') if forward else ('target' if end=='start' else 'source')
            name=t['id']+':'+role
            row[role]={'id':name,'endpoint':branching._intent(pos,d if forward else [-x for x in d])}
            fixtures.append({'name':name,'position':_move(pos,d,-20) if end=='start' else pos,'travel_direction':d})
        main['tracks'].append(row)
    main_plan=parallel.plan_multitrack_connection(main)
    branches=brief['branches']
    if not isinstance(branches,list) or len(branches)!=2 or {b.get('track') for b in branches if isinstance(b,dict)}!={tracks[0]['id'],tracks[-1]['id']}:raise ValueError('one explicit branch on each outer track required')
    branch_intents=[];movements=[{'from':t['id']+':source','to':t['id']+':target','track':t['id'],'kind':'through'} for t in tracks]
    for b in branches:
        if not isinstance(b,dict) or set(b)!={'id','track','lead_length','split_fraction','target'} or not isinstance(b['id'],str) or not b['id']:raise ValueError('explicit branch ID/track/lead/split/target required')
        length,fraction=b['lead_length'],b['split_fraction']
        if type(length) not in (int,float) or not math.isfinite(length) or not 100<=length<=600 or type(fraction) not in (int,float) or not math.isfinite(fraction) or not .25<=fraction<=.75:raise ValueError('lead100–600 and interior split25–75percent required')
        t=next(t for t in main_plan['tracks'] if t['id']==b['track']);p,d=ends[1 if t['forward'] else 0];i=next(i for i,x in enumerate(tracks) if x['id']==b['track'])
        pos=[p[0]-i*signed*d[1],p[1]+i*signed*d[0],p[2]];out=d if t['forward'] else [-x for x in d];origin=_move(pos,out,20);source=_move(origin,out,length*fraction)
        target=b['target']
        if not isinstance(target,dict) or set(target)!={'position','travel_direction'}:raise ValueError('explicit native branch target required')
        q=_position(target['position']);td=_unit(target['travel_direction'])
        sign=1 if brief['side']=='left' else -1
        lateral=(-d[1]*(q[0]-source[0])+d[0]*(q[1]-source[1]))*sign*(1 if i==len(tracks)-1 else -1)
        if lateral<=20 or abs(q[2]-source[2])>.001:raise live.LiveError('unsupported_branch','level outward branch target required')
        intent={'id':b['id'],'track':b['track'],'lead_length':length,'source':branching._intent(source,out),'target':branching._intent(q,td)}
        live.validate_project_brief({'source':intent['source'],'target':intent['target'],'radius':brief['radius'],'region':brief['region'],'vertical':{'max_grade':brief['max_grade']},'max_fit_attempts':1,'max_route_length':brief['max_route_length']},corridor=True)
        branch_intents.append(intent);movements.append({'from':t['id']+':source','to':b['id'],'track':t['id'],'kind':'branch'})
        fixtures.extend([{'name':b['id']+':lead','position':_move(origin,out,length),'travel_direction':out},{'name':b['id']+':target','position':q,'travel_direction':td}])
    if len({b['id'] for b in branches})!=2 or any(b['id'] in main_plan['ports'] for b in branches):raise ValueError('distinct branch/project endpoint IDs required')
    for f in fixtures:
        for p in (f['position'],_move(f['position'],f['travel_direction'],20)):
            if any(not brief['region']['min'][k]<=p[k]<=brief['region']['max'][k] for k in range(3)):raise ValueError('fixture/lead outside authorised region')
    plan={'version':1,'layout':LAYOUT,'brief':brief,'main_plan':main_plan,'branch_intents':branch_intents,'fixtures':fixtures,'movements':movements,'game_constructed':False,'continuous_clearance_proof':False}
    plan['plan_hash']=_hash(plan);return plan


def publish_complete_layout(plan,directory):
    if plan!=plan_complete_layout(plan['brief']):raise ValueError('portable plan changed')
    Path(directory).mkdir(parents=True,exist_ok=True);path=Path(directory)/(uuid.uuid4().hex+'.complete_plan.json');live.atomic_json(path,{'plan':plan})
    return {'status':'ok','operation':'complete-layout','stage':'plan','movements':len(plan['movements']),'game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}


def _fixture_params(plan,f):
    region=plan['brief']['region'];pos=f['position']
    box={'min':[max(pos[k]-40,region['min'][k]) for k in range(3)],'max':[min(pos[k]+40,region['max'][k]) for k in range(3)]}
    return {'authorised':True,'length':20,'fixture':{'template_edge':plan['brief']['seed_edge'],'position':pos,'travel_direction':f['travel_direction'],'grade':0,'region':box}}


def _boxes(plan,footprints):
    """Small cells covering intent/native-control bounds; not a terrain/clearance proof."""
    region=plan['brief']['region'];cells=set()
    for points in footprints:
        for i in range(math.floor((min(p[0] for p in points)-70)/250),math.floor((max(p[0] for p in points)+70)/250)+1):
            for j in range(math.floor((min(p[1] for p in points)-70)/250),math.floor((max(p[1] for p in points)+70)/250)+1):cells.add((i,j))
    if len(cells)>64:raise live.LiveError('site_observation_budget_exhausted','footprint needs >64 bounded cells')
    boxes=[]
    for i,j in sorted(cells):
        lo=[max(i*250,region['min'][0]),max(j*250,region['min'][1]),region['min'][2]];hi=[min((i+1)*250,region['max'][0]),min((j+1)*250,region['max'][1]),region['max'][2]]
        if all(lo[k]<hi[k] for k in range(3)):boxes.append({'min':lo,'max':hi})
    return boxes


def _site(client,plan,record,name,footprints,*,mutate):
    row={'name':name,'basis':'intent straight stubs/leads or native fitted cubic control hulls plus70unit diagnostic margin;not exhaustive effects/clearance proof','observations':[],'clearances':[],'unsupported_objects':[],'truncated':False}
    record.setdefault('site_assessments',[]).append(row);roads=set();global_region=plan['brief']['region']
    boxes=_boxes(plan,footprints);queries=0
    while boxes:
        box=boxes.pop(0);queries+=1
        if queries>256:raise live.LiveError('site_observation_budget_exhausted','bounded subdivision exceeded256 observations')
        r=client.request('inspect',{'edge_ids':[plan['brief']['seed_edge']],'site':{'region':box,'positions':[[(box['min'][0]+box['max'][0])/2,(box['min'][1]+box['max'][1])/2]]}})
        row['observations'].append(r)
        if r['status']!='ok':raise live.LiveError(r['status'],'bounded site observation failed')
        site=r['result']['site'];row['truncated']|=site['truncated']
        for e in site['entities']:
            if e.get('town_building') or e.get('construction'):row['unsupported_objects'].append(e)
        if site['truncated']:
            if max(box['max'][k]-box['min'][k] for k in (0,1))<=63:raise live.LiveError('site_observation_incomplete','bounded local subdivision remains truncated')
            mx=(box['min'][0]+box['max'][0])/2;my=(box['min'][1]+box['max'][1])/2
            boxes[:0]=[{'min':[x0,y0,box['min'][2]],'max':[x1,y1,box['max'][2]]} for x0,x1 in ((box['min'][0],mx),(mx,box['max'][0])) for y0,y1 in ((box['min'][1],my),(my,box['max'][1]))]
            continue
        if mutate and plan['brief']['site_policy']=='clear_roads':
            for e in site['entities']:
                if not e.get('base_edge') or e.get('TRACK') or e['entity'] in roads:continue
                bounds={'min':[max(min(e['p0'][k],e['p1'][k])-2,global_region['min'][k]) for k in range(3)],'max':[min(max(e['p0'][k],e['p1'][k])+2,global_region['max'][k]) for k in range(3)]}
                if any(bounds['max'][k]-bounds['min'][k]>400 or not bounds['min'][k]<=min(e['p0'][k],e['p1'][k])<=max(e['p0'][k],e['p1'][k])<=bounds['max'][k] for k in range(3)):raise live.LiveError('unsupported_site_clearance','observed road exceeds authorised bounded clearance')
                r=client.request('clear_obstructions',{'authorised':True,'edges':[e],'region':bounds});row['clearances'].append(r)
                if r.get('result',{}).get('game_constructed') in (True,'unknown'):record['summary']['game_constructed']=r['result']['game_constructed']
                if r['status']!='ok':raise live.LiveError(r['status'],r.get('result',{}).get('error','road clearance failed'))
                roads.add(e['entity'])
    return row


def _controls(client,summary):
    if summary['status']!='ok':raise live.LiveError(summary['status'],summary.get('error','native preflight failed'))
    response=json.loads((client.evidence/(summary['native_request_id']+'.response.json')).read_text())
    controls=response.get('result',{}).get('fit',{}).get('controls')
    if not isinstance(controls,list) or not 1<=len(controls)<=32:raise live.LiveError('native_fit_unavailable','bounded native control evidence unavailable')
    return [[c['p0'],_move3(c['p0'],c['t0'],1/3),_move3(c['p1'],c['t1'],-1/3),c['p1']] for c in controls]


def _move3(p,t,a):return [p[k]+a*t[k] for k in range(3)]


def _branch_plan(plan,main_path):
    brief={k:plan['brief'][k] for k in ('radius','max_grade','region','max_route_length')}
    brief.update(layout=branching.LAYOUT,main_record=str(Path(main_path).resolve()),branches=plan['branch_intents'],movements=plan['movements'])
    return branching.plan_branching_corridor(brief)


def _inspect_fixtures(client,plan,record):
    current={}
    for name,r in record.get('fixtures',{}).items():
        if r['status']!='ok':
            record.setdefault('unverified_fixtures',[]).append(name);continue
        if r.get('result',{}).get('game_constructed') is not True or len(r['result'].get('edges',[]))!=1:raise live.LiveError('reconciliation_required','fixture lacks exact acknowledged receipt')
        old=r['result']['edges'][0];q=client.request('inspect',{'edge_ids':[old['id']]})
        if q['status']!='ok' or len(q['result'].get('edges',[]))!=1:raise live.LiveError('stale_fixture','acknowledged fixture no longer readable')
        now=q['result']['edges'][0]
        if any(now[k]!=old[k] for k in ('id','node0','node1','template','style')) or any(math.dist(now[k],old[k])>.001 for k in ('p0','p1','t0','t1')):raise live.LiveError('stale_fixture','exact authored fixture changed')
        current[name]=now
    return current


def _inspect(client,plan,record):
    stages=record.get('stages',{})
    if 'branches' in stages:
        p=_branch_plan(plan,stages['main']['evidence']);r=branching.inspect_branching_corridor(client,stages['branches']['evidence'])
        if live._load_layout_record(stages['branches']['evidence'])['plan']!=p:raise ValueError('nested branching intent changed')
        record['fresh_branches']=r
        if r['status'] not in ('ok','branching_incomplete'):raise live.LiveError(r['status'],r.get('error','branches unverified'))
        return {'status':r['status'] if r['status']=='ok' else 'complete_layout_incomplete',**{k:r[k] for k in ('routes_verified','junctions_verified','final_network_verified','retained_spacing_verified')},**{k:r[k] for k in ('vertical_mode','vertical_tolerance','spacing_convention','sampled_max_grades','max_sampled_height_difference','junction_geometry') if k in r}}
    record['fresh_fixtures']=_inspect_fixtures(client,plan,record)
    if 'main' in stages:
        r=parallel.inspect_multitrack_connection(client,stages['main']['evidence']);record['fresh_main']=r
        if r['status'] not in ('ok','multitrack_incomplete'):raise live.LiveError(r['status'],r.get('error','main unverified'))
        return {'status':'complete_layout_incomplete','main_routes_verified':r['routes_verified'],'routes_verified':r['routes_verified'],'final_network_verified':False}
    return {'status':'complete_layout_incomplete','fixtures_verified':len(record['fresh_fixtures']),'unverified_fixtures':record.get('unverified_fixtures',[]),'routes_verified':0,'final_network_verified':False}


def _finish(record,exc=None):
    s=record['summary'];s.update(pattern=record['plan']['main_plan']['pattern'],reference_up=record['plan']['main_plan']['brief']['reference_up'])
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_network_verified=False)
    s.update(fixtures_acknowledged=sum(r.get('status')=='ok' for r in record.get('fixtures',{}).values()),completed_stages=[k for k,v in record.get('stages',{}).items() if v.get('status')=='ok'],native_effect_history_complete=False,continuous_clearance_proof=False,train_traversal='unprobed',direction_enforcement='not_provided',next_action='none' if s['status']=='ok' else 'inspect_and_explicitly_reconcile_no_replay')
    live.atomic_json(Path(s['evidence']),record);return s


def inspect_complete_layout(client,invocation):
    old=live._load_layout_record(invocation);plan=old['plan']
    if plan!=plan_complete_layout(plan['brief']):raise ValueError('portable saved plan changed')
    record={k:old[k] for k in ('plan','fixtures','stages')};path=client.evidence/(uuid.uuid4().hex+'.complete_inspection.json')
    record.update(original_record=str(Path(invocation).resolve()),summary={'status':'incomplete','operation':'complete-layout-inspect','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())})
    try:record['summary'].update(_inspect(client,plan,record));return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)


def execute_complete_layout(client,plan,*,continuation_record=None):
    if plan!=plan_complete_layout(plan['brief']):raise ValueError('portable plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.complete.json');lock=client.evidence/'complete.lock'
    record={'plan':plan,'fixtures':{},'stages':{},'operations':[],'summary':{'status':'incomplete','operation':'complete-layout','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise live.LiveError('client_busy','one complete layout at a time') from None
    def perform(name,call,store):
        record['unfinished_step']=name;live.atomic_json(path,record)
        try:r=call()
        except Exception:record['summary']['game_constructed']='unknown';raise
        record['operations'].append({'name':name,'response':r});store(r);live.atomic_json(path,record)
        effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
        if effect in (True,'unknown'):record['summary']['game_constructed']=effect
        if r['status']!='ok':raise live.LiveError(r['status'],r.get('error',r.get('result',{}).get('error','stage failed')))
        record.pop('unfinished_step');live.atomic_json(path,record);return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending native request;no construction')
        if continuation_record:
            old=live._load_layout_record(continuation_record)
            if old.get('summary',{}).get('operation')=='complete-layout-inspect':raise ValueError('inspection evidence is not a construction continuation receipt')
            if old['plan']!=plan:raise ValueError('continuation brief changed')
            record.update(fixtures=old['fixtures'],stages=old['stages'],continuation_of=str(Path(continuation_record).resolve()),prior_effects=old['summary'].get('game_constructed','unknown'))
            proof=_inspect(client,plan,record);record['initial_continuation_inspection']=proof
            if proof['status']=='ok':record['summary'].update(proof,checked_existing=True);return _finish(record)
            step=old.get('unfinished_step')
            if step and step not in record['stages'] and step not in record['fixtures']:raise live.LiveError('reconciliation_required','interrupted stage has no returned receipt')
            if any(r['status']!='ok' for r in record['fixtures'].values()):raise live.LiveError('reconciliation_required','failed fixture requires explicit rejection/absence reconciliation;no recreation')
        seed=client.request('inspect',{'edge_ids':[plan['brief']['seed_edge']],'resources':True});record['asset_seed']=seed
        if seed['status']!='ok' or seed['result']['edges'][0].get('resource',{}).get('track_distance')!=plan['brief']['spacing']:raise live.LiveError('unsupported_asset_seed','actual native template spacing mismatch')
        if 'main' not in record['stages']:
            footprints=[[f['position'],_move(f['position'],f['travel_direction'],20)] for f in plan['fixtures']]
            _site(client,plan,record,'approaches_and_branch_targets',footprints,mutate=True)
            for f in plan['fixtures'][:len(plan['main_plan']['ports'])]:
                if f['name'] in record['fixtures']:continue
                intent=plan['main_plan']['ports'][f['name']]
                try:live._select_throat_port(client,intent['endpoint'],outward_sign=intent['sign'],tolerance=.001)
                except live.LiveError as exc:
                    if exc.status!='no_eligible_candidates':raise
                else:raise live.LiveError('reconciliation_required','unrecorded existing approach;no duplicate fixture')
                perform(f['name'],lambda f=f:client.request('test_approach',_fixture_params(plan,f)),lambda r,f=f:record['fixtures'].__setitem__(f['name'],r))
        if record.get('stages',{}).get('main',{}).get('status')!='ok':
            previous=record['stages'].get('main');adopt=None
            if previous:
                old=live._load_layout_record(previous['evidence']);current={k:old[k] for k in ('plan','ports','chains')};parallel._verify_multitrack(client,plan['main_plan'],current)
                if not current['chains'] or len(current['chains'])==len(plan['main_plan']['tracks']):raise live.LiveError('reconciliation_required','main prefix cannot be continued')
                current['summary']={'status':'incomplete','game_constructed':True,'recorded_prior_game_constructed':old['summary'].get('game_constructed','unknown'),'native_effect_history_complete':False};adopt=client.evidence/(uuid.uuid4().hex+'.main_adopted_prefix.json');live.atomic_json(adopt,current)
            else:
                preview=live.connect_corridor(client,plan['main_plan']['reference'],execute=False);record['main_fit_screening']=preview
                _site(client,plan,record,'native_main_candidate',_controls(client,preview),mutate=True)
            perform('main',lambda:parallel.execute_multitrack_connection(client,plan['main_plan'],continuation_record=adopt),lambda r:record['stages'].__setitem__('main',r))
        branch_plan=_branch_plan(plan,record['stages']['main']['evidence']);record['generated_branch_plan']=branch_plan
        def before_build(name,fit):
            _site(client,plan,record,name,_controls(client,fit),mutate=True);live.atomic_json(path,record)
        prior=record['stages'].get('branches')
        perform('branches',lambda:branching.execute_branching_corridor(client,branch_plan,continuation_record=prior['evidence'] if prior else None,before_build=before_build),lambda r:record['stages'].__setitem__('branches',r))
        record['summary'].update(_inspect(client,plan,record));return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)
    finally:lock.unlink()
