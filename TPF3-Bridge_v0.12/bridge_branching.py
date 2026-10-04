"""Compose a native curved main line and outward end-zone branches; no curve fitter."""
import hashlib
import json
import math
from pathlib import Path
import uuid

import bridge_live as live
import bridge_parallel as parallel

LAYOUT='curved_main_branches_v1'


def _parent(path):
    record=live._load_layout_record(path)
    if record['plan']!=parallel.plan_multitrack_connection(record['plan']['brief']) or record['summary'].get('status')!='ok':raise ValueError('canonical completed multitrack receipt required')
    return record,hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _intent(position,direction):
    return {'guide_xyz':position,'travel_direction':direction,'heading_tolerance_deg':.1,'max_edges':16,
        'region':{'min':[x-2 for x in position],'max':[x+2 for x in position]}}


def _outer(port):
    e=port['edge_snapshot'];end=1 if port['node_id']==e['node0'] else 0
    return e['p'+str(end)]


def _branch_brief(plan,branch):
    b=plan['brief']
    return {'source':branch['source'],'target':branch['target'],'radius':b['radius'],'region':b['region'],
        'vertical':{'max_grade':b['max_grade']},'max_fit_attempts':1,'max_route_length':b['max_route_length'],'placement_tolerance':.5}


def _lead_brief(parent,brief,branch):
    t=next(t for t in parent['plan']['tracks'] if t['id']==branch['track']);key=t['end'] if t['forward'] else t['start']
    origin=_outer(parent['ports'][key]);d=branch['source']['travel_direction'];n=math.hypot(*d)
    finish=[origin[k]+branch['lead_length']*(d[k]/n if k<2 else 0) for k in range(3)];region=brief['region']
    box={'min':[max(min(origin[k],finish[k])-40,region['min'][k]) for k in range(3)],'max':[min(max(origin[k],finish[k])+40,region['max'][k]) for k in range(3)]}
    return {'source':_intent(origin,d),'target':_intent(finish,d),'radius':brief['radius'],'region':box,'vertical':{'max_grade':brief['max_grade']},'max_fit_attempts':1,'max_route_length':min(800,branch['lead_length']+80)}


def _lead_receipt(path,expected):
    r=live._load_layout_record(path);s=r.get('summary',{})
    if r.get('brief')!=expected or s.get('status')!='ok' or s.get('game_constructed') is not True or s.get('native_route_verified') is not True or not s.get('edges'):raise ValueError('explicit acknowledged matching lead receipt required')
    digest=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return s,digest


def plan_branching_corridor(brief):
    keys={'layout','main_record','branches','movements','radius','max_grade','region','max_route_length'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=LAYOUT:raise ValueError('explicit curved main/branch brief required')
    parent,digest=_parent(brief['main_record']);main=parent['plan'];tracks=main['tracks']
    if main['pattern']!='UP-UP-DOWN-DOWN' or len(tracks)!=4:raise live.LiveError('unsupported_layout','initial branching corridor requires UUDD')
    if type(brief['radius']) not in (int,float) or not math.isfinite(brief['radius']) or brief['radius']<main['brief']['radius'] or type(brief['max_grade']) not in (int,float) or not math.isfinite(brief['max_grade']) or not 0<brief['max_grade']<=main['brief']['max_grade']:raise ValueError('main engineering limits cannot be lowered')
    if type(brief['max_route_length']) not in (int,float) or not math.isfinite(brief['max_route_length']) or not 0<brief['max_route_length']<=8000:raise ValueError('finite route bound <=8000 required')
    roles={};expected=[]
    for t in tracks:
        for end in ('start','end'):
            key=t[end];p=parent['ports'][key];direction=main['ports'][key]['endpoint']['travel_direction']
            roles[key]={'track':t['id'],'endpoint':_intent(_outer(p),direction),'sign':-1 if end=='start' else 1,
                'function':'entry' if (end=='start')==t['forward'] else 'exit'}
        source,target=(t['start'],t['end']) if t['forward'] else (t['end'],t['start'])
        expected.append({'from':source,'to':target,'track':t['id'],'kind':'through'})
    branches=brief['branches']
    if not isinstance(branches,list) or len(branches)!=2:raise ValueError('two explicit outward branches required')
    outer_tracks={tracks[0]['id']:tracks[0],tracks[-1]['id']:tracks[-1]}
    if {b.get('track') for b in branches if isinstance(b,dict)}!=set(outer_tracks):raise ValueError('one branch per outer UP/DOWN track required')
    for b in branches:
        if not isinstance(b,dict) or set(b)-{'lead_record'}!={'id','track','source','target','lead_length'} or not isinstance(b['id'],str) or not b['id'] or b['id'] in roles:raise ValueError('unique branch ID/source/target/lead_length required')
        t=outer_tracks[b['track']]
        contract=_branch_brief({'brief':brief},b);live.validate_project_brief({k:v for k,v in contract.items() if k!='placement_tolerance'},corridor=True)
        target=t['end'] if t['forward'] else t['start'];stub=parent['ports'][target]['edge_snapshot'];start=stub['p0'];end=stub['p1'];delta=[end[k]-start[k] for k in range(3)];length=math.dist(start,end)
        if any(math.dist(stub[k],delta)>.001 for k in ('t0','t1')) or length<10 or abs(delta[2])>1e-6:raise live.LiveError('unsupported_layout','straight level tangent approach required')
        expected_direction=main['ports'][target]['endpoint']['travel_direction'];expected_direction=[v*(1 if t['forward'] else -1) for v in expected_direction]
        lead=b['lead_length']
        if type(lead) not in (int,float) or not math.isfinite(lead) or not (lead==0 or 100<=lead<=600):raise ValueError('lead_length must be0 or within100-600')
        n=math.hypot(*expected_direction);unit=[v/n for v in expected_direction]+[0];origin=_outer(parent['ports'][target]);finish=[origin[k]+lead*unit[k] for k in range(3)]
        if lead==0:
            if 'lead_record' in b:raise ValueError('no lead receipt for direct tangent split')
            origin=start if t['forward'] else end;lead=length;finish=end if t['forward'] else start
        p=b['source']['guide_xyz'];u=sum((p[k]-origin[k])*unit[k] for k in range(3))/lead
        if not .25<=u<=.75 or math.dist(p,[origin[k]+u*lead*unit[k] for k in range(3)])>.001:raise live.LiveError('unsupported_branch','junction must lie inside the declared tangent lead, outside shared section')
        if b['lead_length']:
            roles[target]={'track':t['id'],'endpoint':_intent([finish[k]+20*unit[k] for k in range(3)],expected_direction),'sign':1,'function':'exit'}
        d=b['source']['travel_direction'];n=math.hypot(*d);m=math.hypot(*expected_direction)
        if math.hypot(*(d[k]/n-expected_direction[k]/m for k in range(2)))>1e-6:raise ValueError('branch source must follow declared outgoing traffic')
        # Outward means away from the neighboring track, in the construction frame.
        ref=main['ports'][target]['endpoint']['travel_direction'];n=math.hypot(*ref);q=b['target']['guide_xyz'];signed=(-ref[1]*(q[0]-p[0])+ref[0]*(q[1]-p[1]))/n
        side=1 if main['signed_spacing']>0 else -1
        if signed*side*(1 if t is tracks[-1] else -1)<=20:raise live.LiveError('unsupported_branch','outward target must clear the ordered main line')
        if abs(q[2]-p[2])>.001:raise live.LiveError('unsupported_branch','initial branch is level')
        d=b['target']['travel_direction'];n=math.hypot(*d);outer=[q[k]+20*(d[k]/n if k<2 else 0) for k in range(3)]
        roles[b['id']]={'track':t['id'],'endpoint':_intent(outer,d),'sign':1,'function':'exit'}
        entry=next(x['from'] for x in expected if x['track']==t['id'] and x['kind']=='through')
        expected.append({'from':entry,'to':b['id'],'track':t['id'],'kind':'branch'})
    if len(roles)!=10:raise ValueError('distinct ten project endpoint roles required')
    movements=brief['movements']
    if not isinstance(movements,list) or len(movements)!=6 or any(not isinstance(x,dict) or set(x)!={'from','to','track','kind'} for x in movements):raise ValueError('six explicit directed movements required')
    if {tuple(sorted(x.items())) for x in movements}!={tuple(sorted(x.items())) for x in expected}:raise ValueError('matrix must contain four through and two outgoing branch movements exactly')
    for p in list(roles.values()):
        if any(not brief['region']['min'][k]<=p['endpoint']['guide_xyz'][k]<=brief['region']['max'][k] for k in range(3)):raise ValueError('authorised region excludes a role')
    plan={'version':1,'layout':LAYOUT,'brief':brief,'main':main,'main_record':str(Path(brief['main_record']).resolve()),'main_sha256':digest,
        'roles':roles,'movements':movements,'shared_section':'P25 entire connector; end tangent approaches/junction branches excluded',
        'junction_zones':[{'branch':b['id'],'source_region':b['source']['region'],'target_region':b['target']['region']} for b in branches],
        'game_constructed':False,'continuous_clearance_proof':False}
    plan['lead_receipt_hashes']={b['id']:_lead_receipt(b['lead_record'],_lead_brief(parent,brief,b))[1] for b in branches if 'lead_record' in b}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_branching_corridor(plan,directory):
    if plan!=plan_branching_corridor(plan['brief']):raise ValueError('branching plan changed')
    Path(directory).mkdir(parents=True,exist_ok=True);path=Path(directory)/(uuid.uuid4().hex+'.branching_plan.json');live.atomic_json(path,{'plan':plan})
    return {'status':'ok','operation':'branching-corridor','stage':'plan','game_constructed':False,'plan_hash':plan['plan_hash'],'movements':6,'evidence':str(path.resolve())}


def _roles(client,plan,record,partial):
    ports={}
    for name,role in plan['roles'].items():
        try:
            c,rid=live._select_throat_port(client,role['endpoint'],outward_sign=role['sign'],tolerance=.001)
        except live.LiveError as exc:
            if not partial or exc.status!='no_eligible_candidates':raise
            record.setdefault('unavailable_roles',[]).append(name);continue
        if abs(c.get('grade',1))>1e-6:raise live.LiveError('native_verification_failed','role no longer level')
        ports[name]=c;record.setdefault('observations',[]).append(rid)
    if len({c['node_id'] for c in ports.values()})!=len(ports):raise live.LiveError('native_verification_failed','semantic roles share exact nodes')
    record['current_roles']=ports;return ports


def _assess(client,plan,record,*,partial=False):
    parent,digest=_parent(plan['main_record'])
    if digest!=plan['main_sha256']:raise ValueError('main receipt changed')
    ports=_roles(client,plan,record,partial);record['routes']=[];junctions={};incidences={};refs={}
    # The explicitly retained shared section is independently fresh, not a stale
    # standalone stage receipt. Native approach IDs may legitimately be replaced.
    core={'chains':parent['chains']}
    for t in plan['main']['tracks']:
        refs[t['id']]=parallel._read_chain(client,plan['main'],core,t['id'])
    record['current_shared_chains']=core['current_chains'];record['retained_spacing']=[]
    tracks=plan['main']['tracks']
    for a,z,m in [(i-1,i,1) for i in range(1,4)]+[(0,i,i) for i in range(2,4)]:
        r=client.request('verify_adjacency',{'reference':refs[tracks[a]['id']],'adjacent':refs[tracks[z]['id']],
            'spacing':m*plan['main']['signed_spacing'],'tolerance':plan['main']['brief']['spacing_tolerance'],**{k:plan['main']['brief'][k] for k in ('radius','max_grade','region')}})
        v=r.get('result',{});good=r['status']=='ok' and v.get('sampled_verified') is True and bool(v.get('correspondence')) and v.get('curved_reference_chord_length',0)>=plan['main']['brief']['min_curved_length']
        record['retained_spacing'].append({'from':tracks[a]['id'],'to':tracks[z]['id'],'verified':good,'response':r})
        if not good:raise live.LiveError('native_verification_failed','retained shared alignment not verified')
    for b in plan['brief']['branches']:
        try:node,rids=live._recipe_junction(client,b['source'])
        except live.LiveError as exc:
            if not partial or exc.status not in ('no_eligible_candidates','recipe_state_unknown'):raise
            continue
        record.setdefault('observations',[]).extend(rids);junctions[b['id']]=node
        found=live.discover(client,{k:b['source'][k] for k in ('region','max_edges')})
        rows=[c for c in found.get('result',{}).get('candidates',[]) if c.get('node_id')==node and c.get('incidence_complete') and c.get('incident_count')==3]
        if found['status']!='ok' or not found['result'].get('complete') or not rows:raise live.LiveError('native_verification_failed','fresh junction incidence unavailable')
        ids=rows[0]['incident_edges'];r=client.request('inspect',{'edge_ids':ids});edges=r.get('result',{}).get('edges',[])
        if r['status']!='ok' or len(edges)!=3 or any(e['road_type']!='TRACK' or node not in (e['node0'],e['node1']) for e in edges):raise live.LiveError('native_verification_failed','exact three-TRACK junction unavailable')
        incidences[b['id']]=set(ids);record.setdefault('junction_inspections',{})[b['id']]=r
    record['current_junctions']=junctions
    for row in plan['movements']:
        related=next((b for b in plan['brief']['branches'] if b['track']==row['track']),None);jid=related['id'] if related else None
        if any(k not in ports for k in (row['from'],row['to'])) or row['kind']=='branch' and jid not in junctions:
            record['routes'].append(row|{'verified':False,'reason':'current role/junction unavailable'});continue
        t=next(t for t in tracks if t['id']==row['track']);a,z=ports[row['from']],ports[row['to']];coreids=parent['chains'][t['id']]['edges'];coreids=coreids if t['forward'] else coreids[::-1]
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':z['edge_id'],'target_node':z['node_id'],'mode':'TRAIN',
            'max_length':plan['brief']['max_route_length'],'required_edges':[a['edge_id']]+coreids+[z['edge_id']],
            'junction_nodes':list(junctions.values()),
            'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':plan['brief']['radius'],'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}}
        r=client.request('route',q);v=r.get('result',{});path=v.get('path',[]);ids=[x['edge']['entity'] for x in path if x.get('confirmed_TRACK')]
        transport=all(x['edge']['entity'] in junctions.values() and x['from']['entity']==x['edge']['entity']==x['to']['entity'] for x in path if not x.get('confirmed_TRACK'))
        good=r['status']=='ok' and v.get('requested_route_verified') is True and transport and len(set(ids))==len(ids) and ids[0:1]==[a['edge_id']] and ids[-1:]==[z['edge_id']]
        positions=[ids.index(e) for e in coreids if e in ids]
        trackpath=[x for x in path if x.get('confirmed_TRACK')]
        good=good and len(positions)==len(coreids) and positions==list(range(positions[0],positions[0]+len(coreids))) and all(trackpath[i].get('forward') is t['forward'] for i in positions)
        nodes={x[k]['entity'] for x in path for k in ('from','to')}
        if jid in junctions:
            used=incidences[jid].intersection(ids)
            good=good and junctions[jid] in nodes and len(used)==2
            record.setdefault('junction_route_incidence',{}).setdefault(jid,{})[row['kind']]=sorted(used)
        record['routes'].append(row|{'verified':good,'response':r})
        if not good:raise live.LiveError('native_verification_failed','complete intended route failed: '+row['from']+'->'+row['to'])
    for b in plan['brief']['branches']:
        used=record.get('junction_route_incidence',{}).get(b['id'],{})
        if b['id'] in junctions and 'branch' in used:
            a,z=(set(used[k]) for k in ('through','branch'))
            if len(a&z)!=1 or a|z!=incidences[b['id']]:raise live.LiveError('native_verification_failed','through/branch do not establish actual fork')
    count=sum(x['verified'] for x in record['routes']);full=count==6 and len(junctions)==2
    old={k:v['edge_id'] for k,v in parent['ports'].items()};replaced={k:{'previous':old[k],'current':ports[k]['edge_id']} for k in old if k in ports and old[k]!=ports[k]['edge_id']}
    record['semantic_attachment_reconciliation']={'current_exact_role_ids':{k:{x:v[x] for x in ('edge_id','node_id')} for k,v in ports.items()},'changed_main_approach_handles':replaced,'original_stage_receipt_fresh':False,'basis':'bounded role observation plus exact current TRACK incidence and complete native paths'}
    return {'final_network_verified':full,'routes_verified':count,'junctions_verified':len(junctions),'retained_spacing_verified':True,
        'shared_section':'curved connector only; tangent splits and divergent branches excluded','continuous_clearance_proof':False}


def _finish(record,exc=None):
    s=record['summary']
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_network_verified=False)
    s['routes_verified']=sum(x['verified'] for x in record.get('routes',[]));s['route_lengths']={x['from']+'->'+x['to']:x['response']['result'].get('total_path_length') for x in record.get('routes',[]) if x['verified']}
    s.update(native_effect_history_complete=False,train_traversal='unprobed',direction_enforcement='not_provided',next_action='none' if s['status']=='ok' else 'inspect_and_reconcile_no_automatic_replay')
    live.atomic_json(Path(s['evidence']),record);return s


def _continuation(client,plan,record,path):
    """Explicitly adopt proven completed branches; never infer/replay prior writes."""
    old=live._load_layout_record(path);prior=old['plan']
    if prior!=plan_branching_corridor(prior['brief']):raise ValueError('prior branching plan changed')
    if prior['main_sha256']!=plan['main_sha256'] or {k:v for k,v in prior['brief'].items() if k!='branches'}!={k:v for k,v in plan['brief'].items() if k!='branches'}:raise ValueError('continuation main/constraints/movements changed')
    completed=old.get('completed_branches',[])
    if not isinstance(completed,list) or not 0<len(completed)<2 or len(set(completed))!=len(completed):raise ValueError('explicit partial completed-branch record required')
    for name in completed:
        before=next((b for b in prior['brief']['branches'] if b['id']==name),None)
        after=next((b for b in plan['brief']['branches'] if b['id']==name),None)
        if before is None or before!=after:raise ValueError('completed branch intent changed')
    proof={'plan':plan};s=_assess(client,plan,proof,partial=True)
    through=[r for r in proof['routes'] if r['kind']=='through']
    verified={r['to'] for r in proof['routes'] if r['kind']=='branch' and r['verified']}
    if len(through)!=4 or not all(r['verified'] for r in through) or verified!=set(completed) or set(proof['current_junctions'])!=set(completed):raise live.LiveError('reconciliation_required','prior branches/current through routes not independently proven')
    record['continuation']={'record':str(Path(path).resolve()),'sha256':hashlib.sha256(json.dumps(old,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'fresh_proof':proof,'fresh_summary':s,'automatic_replay':False,'prior_effect_history_complete':False}
    record['completed_branches']=completed[:]
    return proof['current_roles'],list(proof['current_junctions'].values()),set(completed)


def execute_branching_corridor(client,plan,*,continuation_record=None):
    if plan!=plan_branching_corridor(plan['brief']):raise ValueError('branching plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.branching.json');lock=client.evidence/'branching.lock'
    record={'plan':plan,'operations':[],'routes':[],'summary':{'status':'incomplete','operation':'branching-corridor','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise live.LiveError('client_busy','one branching composition at a time') from None
    def perform(name,call):
        record['unfinished_step']=name;live.atomic_json(path,record)
        try:r=call()
        except Exception:record['summary']['game_constructed']='unknown';raise
        record['operations'].append({'name':name,'response':r});effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
        if effect in (True,'unknown') or record['summary']['game_constructed'] is not True:record['summary']['game_constructed']=effect
        if r['status']!='ok':raise live.LiveError(r['status'],r.get('error',r.get('result',{}).get('error','native branch failed')))
        record.pop('unfinished_step');live.atomic_json(path,record);return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending mutation; no branching')
        if continuation_record:
            ports,junctions,completed=_continuation(client,plan,record,continuation_record)
        else:
            proof=parallel.inspect_multitrack_connection(client,plan['main_record']);record['initial_main_inspection']=proof
            if proof['status']!='ok':raise live.LiveError('main_state_unverified','original main must be freshly complete before new composition')
            ports=_roles(client,plan,record,True);junctions=[];completed=set()
        if any(b['id'] in ports and b['id'] not in completed for b in plan['brief']['branches']):raise live.LiveError('reconciliation_required','existing unadopted branch target; inspect prior effects, no fixture replay')
        for b in plan['brief']['branches']:
            if b['id'] in completed:continue
            t=next(t for t in plan['main']['tracks'] if t['id']==b['track'])
            present=(t['end'] if t['forward'] else t['start']) in ports
            if b['lead_length'] and present!=('lead_record' in b):raise live.LiveError('reconciliation_required','lead target/explicit acknowledged receipt mismatch; inspect prior effects')
        for b in plan['brief']['branches']:
            if b['id'] in completed:continue
            t=next(t for t in plan['main']['tracks'] if t['id']==b['track']);exit_role=t['end'] if t['forward'] else t['start']
            parent,_=_parent(plan['main_record']);origin=_outer(parent['ports'][exit_role]);d=b['source']['travel_direction'];n=math.hypot(*d);finish=[origin[k]+b['lead_length']*(d[k]/n if k<2 else 0) for k in range(3)]
            region=plan['brief']['region']
            def fixture(position,direction,template):
                box={'min':[max(position[k]-40,region['min'][k]) for k in range(3)],'max':[min(position[k]+40,region['max'][k]) for k in range(3)]}
                return client.request('test_approach',{'authorised':True,'length':20,'fixture':{'template_edge':template,'position':position,'travel_direction':direction,'grade':0,'region':box}})
            lead_brief=_lead_brief(parent,plan['brief'],b)
            if not b['lead_length']:
                lead={'edges':[ports[exit_role]['edge_id']]}
            elif 'lead_record' in b:
                lead,digest=_lead_receipt(b['lead_record'],lead_brief)
                if digest!=plan['lead_receipt_hashes'][b['id']]:raise ValueError('lead receipt changed')
                original=parent['ports'][exit_role];z=ports[exit_role]
                observed=client.request('route',{'source_edge':original['edge_id'],'source_node':original['node_id'],'target_edge':z['edge_id'],'target_node':z['node_id'],'mode':'TRAIN','max_length':lead_brief['max_route_length'],
                    'required_edges':lead['edges'],'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':plan['brief']['radius'],'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}})
                record.setdefault('reused_leads',{})[b['id']]={'receipt':b['lead_record'],'fresh_route':observed,'automatic_replay':False}
                if observed['status']!='ok' or observed.get('result',{}).get('requested_route_verified') is not True:raise live.LiveError('native_verification_failed','acknowledged lead no longer connects intended current roles')
            else:
                original,rid=live._select_throat_port(client,_intent(origin,d),outward_sign=1,tolerance=.001);record.setdefault('observations',[]).append(rid)
                perform('prepare_lead_'+b['id'],lambda:fixture(finish,d,original['edge_id']))
                lead=perform('lead_'+b['id'],lambda:live.connect_brief(client,lead_brief,execute=True))
            source,rid=live._select_throat_port(client,b['source'],interior=True,tolerance=.5)
            record.setdefault('observations',[]).append(rid)
            if source['edge_id'] not in lead.get('edges',[]):raise live.LiveError('wrong_branch_attachment','interior source is not the freshly built named tangent lead')
            perform('prepare_'+b['id'],lambda:fixture(b['target']['guide_xyz'],b['target']['travel_direction'],source['edge_id']))
            branch=perform(b['id'],lambda b=b:live.connect_junction_at(client,_branch_brief(plan,b),execute=True,junction_nodes=junctions))
            if branch.get('placement',{}).get('original_edge')!=source['edge_id']:raise live.LiveError('wrong_branch_attachment','native split did not use named approach')
            junctions.append(branch['junction']['node']);record.setdefault('completed_branches',[]).append(b['id'])
        record['summary'].update(_assess(client,plan,record),status='ok');return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)
    finally:lock.unlink()


def inspect_branching_corridor(client,invocation):
    original=live._load_layout_record(invocation);plan=original['plan']
    if plan!=plan_branching_corridor(plan['brief']):raise ValueError('saved branching plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.branching_inspection.json')
    record={'plan':plan,'original_record':str(Path(invocation).resolve()),'routes':[],'recorded_prior_game_constructed':original['summary'].get('game_constructed','unknown'),
        'summary':{'status':'incomplete','operation':'branching-corridor-inspect','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        s=_assess(client,plan,record,partial=True);record['summary'].update(s,status='ok' if s['final_network_verified'] else 'branching_incomplete');return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)
