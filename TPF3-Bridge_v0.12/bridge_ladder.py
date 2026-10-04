"""Two bounded native ladders: fixed railway interfaces, explicit traffic, fresh proof."""
import hashlib
import json
import math
import re
import uuid
from pathlib import Path
import bridge_live as live

LAYOUT='native_two_ladder_fan_v1'

def plan_ladder(brief):
    keys={'layout','roles','groups','movements','radius','turnout_radius','region','vertical','max_route_length','placement_tolerance','spacing'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=LAYOUT:raise ValueError('explicit two-ladder brief required')
    roles=brief['roles'];groups=brief['groups']
    if not isinstance(roles,dict) or len(roles)!=10 or any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',n) for n in roles):raise ValueError('ten distinct named fixed interfaces required')
    if not isinstance(groups,list) or len(groups)!=2:raise ValueError('two explicit ladder groups required')
    if type(brief['spacing']) not in (int,float) or not math.isfinite(brief['spacing']) or brief['spacing']<=0:raise ValueError('positive native minimum interface spacing required')
    if type(brief['turnout_radius']) not in (int,float) or not math.isfinite(brief['turnout_radius']) or brief['turnout_radius']<brief['radius']:raise ValueError('selected native turnout radius cannot lower the hard minimum')
    if type(brief['placement_tolerance']) not in (int,float) or not 0<brief['placement_tolerance']<=.5:raise ValueError('pointwork placement tolerance within(0,.5] required')
    common={k:brief[k] for k in ('radius','region','vertical','max_route_length')}|{'max_fit_attempts':1}
    expected=[];used=[];steps=[]
    for g in groups:
        if not isinstance(g,dict) or set(g)-{'spine_radius','junction_radii'}!={'id','inbound','outbound','destinations','spine_guides','arm_end','junctions'}:raise ValueError('explicit spine/arm/three-turnout group required')
        if not isinstance(g['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,30}',g['id']):raise ValueError('invalid group ID')
        ds=g['destinations']
        if not isinstance(ds,list) or len(ds)!=3:raise ValueError('three destinations per ladder required')
        names=[g['inbound'],g['outbound'],*ds]
        if any(n not in roles for n in names) or len(set(names))!=5:raise ValueError('explicit distinct pairing required')
        used+=names
        for n in names:
            r=roles[n]
            if not isinstance(r,dict) or set(r)!={'kind','endpoint'} or r['kind']!=('approach' if n in names[:2] else 'destination'):raise ValueError('fixed approach/destination kind mismatch')
            live.validate_project_brief(common|{'source':r['endpoint'],'target':r['endpoint']},corridor=True)
        sr=g.get('spine_radius',brief['radius'])
        if type(sr) not in (int,float) or not math.isfinite(sr) or sr<brief['radius']:raise ValueError('native spine radius cannot lower the hard minimum')
        spine=common|{'radius':sr,'source':roles[names[0]]['endpoint'],'target':roles[ds[0]]['endpoint'],'guides':g['spine_guides']}
        # Existing corridor validation is pure until its execution function is called.
        if not isinstance(g['spine_guides'],list) or not 1<=len(g['spine_guides'])<=3:raise ValueError('one to three native spine guides required')
        for q in g['spine_guides']:
            if set(q)!={'position','travel_direction','grade'} or q['grade']!=0:raise live.LiveError('unsupported_ladder','level spine guides required')
            live.validate_project_brief(common|{'source':intent(q['position'],q['travel_direction']),'target':roles[ds[0]]['endpoint']},corridor=True)
        if not isinstance(g['junctions'],list) or len(g['junctions'])!=3:raise ValueError('merge and two successive fan turnouts required')
        live.validate_project_brief(common|{'source':g['arm_end'],'target':g['arm_end']},corridor=True)
        steps.append({'name':g['id']+'_spine','kind':'spine','brief':spine})
        steps.append({'name':g['id']+'_arm','kind':'arm','source':g['outbound'],'target':g['arm_end']})
        radii=g.get('junction_radii',[brief['turnout_radius']]*3)
        if not isinstance(radii,list) or len(radii)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or v<brief['radius'] for v in radii):raise ValueError('three selected junction radii cannot lower the hard minimum')
        for i,q in enumerate(g['junctions']):
            target=g['arm_end'] if i==0 else roles[ds[3-i]]['endpoint']
            if i==0:target=target|{'travel_direction':[-v for v in target['travel_direction']]}
            b=common|{'source':q,'target':target,'radius':radii[i],'placement_tolerance':brief['placement_tolerance']}
            live.validate_project_brief({k:v for k,v in b.items() if k!='placement_tolerance'},corridor=True)
            steps.append({'name':g['id']+'_junction_'+str(i),'kind':'junction','brief':b})
        for i,n in enumerate(ds):
            via=[g['id']+'_junction_'+str(j) for j in range(3 if i!=2 else 2)]
            expected += [{'from':g['inbound'],'to':n,'via':via},{'from':n,'to':g['outbound'],'via':list(reversed(via))}]
    if len(set(g['id'] for g in groups))!=2 or len(set(used))!=10:raise ValueError('each fixed interface belongs to exactly one ladder')
    points=[r['endpoint']['guide_xyz'] for r in roles.values()]+[p for g in groups for p in [g['arm_end']['guide_xyz'],*[q['guide_xyz'] for q in g['junctions']],*[q['position'] for q in g['spine_guides']]]]
    if any(not brief['region']['min'][k]<=p[k]<=brief['region']['max'][k] for p in points for k in range(3)):raise ValueError('authorised region excludes selected interface/guide')
    if brief['movements']!=expected:raise ValueError('explicit inbound/outbound matrix must cover every destination and its successive turnouts')
    first=roles[groups[0]['inbound']]['endpoint'];d=first['travel_direction'];size=math.hypot(*d);d=[v/size for v in d];origin=first['guide_xyz']
    def coordinates(e):
        p=e['guide_xyz'];v=e['travel_direction'];length=math.hypot(*v)
        if math.dist([x/length for x in v],d)>.00001 or abs(p[2]-origin[2])>.001:raise live.LiveError('unsupported_ladder','level aligned parallel native interfaces required')
        return sum((p[k]-origin[k])*d[k] for k in range(2)), -d[1]*(p[0]-origin[0])+d[0]*(p[1]-origin[1])
    for kind in ('approach','destination'):
        points=[coordinates(r['endpoint']) for r in roles.values() if r['kind']==kind]
        if max(p[0] for p in points)-min(p[0] for p in points)>.001:raise live.LiveError('unsupported_ladder','aligned interface fan required')
        ys=sorted(p[1] for p in points)
        if any(b-a<brief['spacing']-.001 for a,b in zip(ys,ys[1:])):raise live.LiveError('unsupported_ladder','fixed interfaces violate selected minimum spacing')
    for g in groups:
        a=coordinates(roles[g['inbound']]['endpoint'])[0];z=coordinates(roles[g['destinations'][0]]['endpoint'])[0]
        js=[]
        for i,q in enumerate(g['junctions']):
            p=q['guide_xyz'];v=q['travel_direction'];length=math.hypot(*v);sign=-1 if i==0 else 1
            if abs(p[2]-origin[2])>.001 or math.dist([sign*x/length for x in v],d)>.00001:raise live.LiveError('unsupported_ladder','level merge/fan travel directions required')
            js.append(sum((p[k]-origin[k])*d[k] for k in range(2)))
        if not a<js[0]<js[1]<js[2]<z:raise live.LiveError('unsupported_ladder','successive pointwork must lie between fixed interfaces')
    plan={'version':1,'epoch':'DESIGN','brief':brief,'steps':steps,'movements':expected,'game_constructed':False}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan

COMPACT_LAYOUT='native_compact_two_ladder_v1'

def plan_compact_ladder(brief):
    """Derive bounded semantic controls from fixed banks, never native control curves."""
    keys={'layout','roles','groups','movements','radius','turnout_radii','region','vertical','max_route_length','placement_tolerance','spacing'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=COMPACT_LAYOUT:raise ValueError('explicit compact ladder brief required')
    roles=brief['roles'];groups=brief['groups'];selected=brief['turnout_radii']
    if not isinstance(selected,dict) or set(selected)!={'merge','outer_fan','inner_fan'}:raise ValueError('explicit merge/outer_fan/inner_fan radii required')
    if not isinstance(roles,dict) or len(roles)!=10 or not isinstance(groups,list) or len(groups)!=2:raise ValueError('four approaches/six destinations and two explicit groups required')
    low={k:v for k,v in brief.items() if k not in ('layout','roles','groups','movements','turnout_radii')};low.update(layout=LAYOUT,roles={},groups=[],movements=[],turnout_radius=selected['merge'])
    for n,r in roles.items():
        if not isinstance(r,dict) or set(r)!={'kind','position','travel_direction'}:raise ValueError('named fixed position/direction/kind required')
        low['roles'][n]={'kind':r['kind'],'endpoint':intent(r['position'],r['travel_direction'])}
    for g in groups:
        if not isinstance(g,dict) or set(g)!={'id','inbound','outbound','destinations'} or not isinstance(g['destinations'],list) or len(g['destinations'])!=3:raise ValueError('explicit ordered group pairing required')
        try:a,z=roles[g['inbound']],roles[g['destinations'][0]];out=roles[g['outbound']]
        except KeyError:raise ValueError('unknown role in group') from None
        d=a['travel_direction'];norm=math.hypot(*d)
        if norm<=0:raise ValueError('nonzero heading required')
        d=[x/norm for x in d];normal=[-d[1],d[0]];origin=a['position']
        def xy(p):return [sum((p[k]-origin[k])*v[k] for k in range(2)) for v in (d,normal)]
        L,y=xy(z['position']);out_y=xy(out['position'])[1];ds=[xy(roles[n]['position'])[1] for n in g['destinations']]
        if type(brief['spacing']) not in (int,float) or not math.isfinite(brief['spacing']) or brief['spacing']<=0:raise ValueError('positive native spacing required')
        if not 200<=L<=800:raise live.LiveError('unsupported_compact_ladder','compact planner supports aligned banks separated by200..800 native units')
        side=1 if out_y>0 else -1
        if side*out_y<brief['spacing']-.001 or not all(side*(ds[i+1]-ds[i])>=brief['spacing']-.001 for i in range(2)):raise live.LiveError('unsupported_compact_ladder','outbound approach and explicitly ordered fan must lie outward of inbound/inner track')
        def point(x,y):return [origin[k]+d[k]*x+normal[k]*y for k in range(2)]+[origin[2]]
        arm_y=ds[-1]+side*2*brief['spacing']
        # Short local S-transitions give native pointwork a usable angle; this is
        # a two-arc screening envelope with margin, not a replacement curve fitter.
        remaining=[1.1*math.sqrt(4*1.05*selected[k]*abs(ds[i]-ds[0])) for k,i in [('outer_fan',2),('inner_fan',1)]]
        fractions=(.42,1-remaining[0]/L,1-remaining[1]/L)
        q={'id':g['id'],'inbound':g['inbound'],'outbound':g['outbound'],'destinations':g['destinations'],'spine_guides':[{'position':point(.35*L,y),'travel_direction':d,'grade':0}],'arm_end':intent(point(.20*L,arm_y),d),'junctions':[intent(point(f*L,y),[-v for v in d] if i==0 else d) for i,f in enumerate(fractions)]}
        q['junction_radii']=[selected[k] for k in ('merge','outer_fan','inner_fan')]
        low['groups'].append(q)
        for i,n in enumerate(g['destinations']):
            via=[g['id']+'_junction_'+str(j) for j in range(3 if i!=2 else 2)]
            low['movements'] += [{'from':g['inbound'],'to':n,'via':via},{'from':n,'to':g['outbound'],'via':list(reversed(via))}]
    expected=[{k:r[k] for k in ('from','to')} for r in low['movements']]
    if brief['movements']!=expected:raise ValueError('compact brief must explicitly approve every directed group movement')
    plan=plan_ladder(low);plan['derivation']={'planner':COMPACT_LAYOUT,'input':brief,'controls':'one alignment guide; outward arm and three longitudinal turnout intents; native fitting owns curves','optimality':'not globally minimal','native_fit_required':True}
    plan['plan_hash']=hashlib.sha256(json.dumps({k:v for k,v in plan.items() if k!='plan_hash'},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan

def plan_ladder_input(brief):
    return plan_compact_ladder(brief) if isinstance(brief,dict) and brief.get('layout')==COMPACT_LAYOUT else plan_ladder(brief)

def _canonical(plan):
    return plan_compact_ladder(plan['derivation']['input']) if plan.get('derivation') else plan_ladder(plan['brief'])

def intent(position,direction):
    return {'guide_xyz':position,'travel_direction':direction,'heading_tolerance_deg':.1,'max_edges':16,'region':{'min':[v-2 for v in position],'max':[v+2 for v in position]}}

def publish_ladder(plan,directory):
    if plan!=_canonical(plan):raise ValueError('plan changed')
    path=Path(directory)/(uuid.uuid4().hex+'.ladder_plan.json');path.parent.mkdir(parents=True,exist_ok=True);live.atomic_json(path,{'plan':plan})
    return {'status':'ok','operation':'ladder-layout','stage':'plan','game_constructed':False,'movements':len(plan['movements']),'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}

def _roles(client,plan,record,connected):
    ports={}
    for n,r in plan['brief']['roles'].items():
        c,rid=live._select_throat_port(client,r['endpoint'],outward_sign=1 if r['kind']=='approach' else -1,tolerance=.001,connected=connected)
        e=c['edge_snapshot'];end=0 if c['node_id']==e['node0'] else 1
        if e['road_type']!='TRACK' or abs(e['t'+str(end)][2])>1e-6:raise live.LiveError('unsupported_ladder','exact level native TRACK attachment required')
        old=record.get('initial_ports',{}).get(n)
        if old and c['node_id']!=old['node_id']:raise live.LiveError('attachment_identity_changed','fixed native attachment node changed; explicit reconciliation required')
        ports[n]=c;record.setdefault('observations',[]).append(rid)
    record['current_ports']=ports
    return ports

def _other(c):
    e=c['edge_snapshot'];return e['node1'] if e['node0']==c['node_id'] else e['node0']

def _arm_region(brief,source,target):
    points=[source['guide_xyz'],target['guide_xyz']];region=brief['region']
    box={'min':[max(min(p[k] for p in points)-80,region['min'][k]) for k in range(3)],'max':[min(max(p[k] for p in points)+80,region['max'][k]) for k in range(3)]}
    if any(box['max'][k]-box['min'][k]>1000 for k in range(2)):raise live.LiveError('unsupported_ladder','widened arm exceeds existing native extension envelope')
    return box

def _assess(client,plan,record):
    ports=_roles(client,plan,record,True);junctions={}
    for step in plan['steps']:
        if step['kind']=='junction':
            node,ids=live._recipe_junction(client,step['brief']['source']);junctions[step['name']]=node;record.setdefault('observations',[]).extend(ids)
    record['current_junctions']=junctions;record['routes']=[]
    b=plan['brief']
    for row in plan['movements']:
        a,z=ports[row['from']],ports[row['to']]
        q={'source_edge':a['edge_id'],'source_node':_other(a),'target_edge':z['edge_id'],'target_node':_other(z),'required_edges':[a['edge_id'],z['edge_id']],'junction_nodes':list(junctions.values()),'mode':'TRAIN','max_length':b['max_route_length'],'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':b['radius'],'max_grade':b['vertical']['max_grade'],'region':b['region']}}
        response=client.request('route',q);v=response.get('result',{});path=v.get('path',[])
        nodes=[path[0]['from']['entity']]+[x['to']['entity'] for x in path] if path else []
        required=[junctions[n] for n in row['via']];indices=[nodes.index(n) if n in nodes else -1 for n in required]
        good=response['status']=='ok' and v.get('requested_route_verified') is True and not v.get('truncated') and all(i>=0 for i in indices) and indices==sorted(indices)
        record['routes'].append(row|{'verified':good,'response':response})
        if not good:raise live.LiveError('native_verification_failed','required directed ladder path/turnouts failed: '+row['from']+' -> '+row['to'])
    return {'status':'ok','routes_verified':len(record['routes']),'junctions_verified':len(junctions),'final_network_verified':True,'successive_turnouts_verified':True}

def _finish(record,path,exc=None):
    s=record['summary']
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_network_verified=False)
    ops=record.get('operations',[])
    s.update(evidence=str(path.resolve()),plan_hash=record['plan']['plan_hash'],steps_completed=sum(o['response'].get('status')=='ok' for o in ops),operations_recorded=len(ops),train_traversal='unprobed',direction_enforcement='not_provided',continuous_clearance_proof=False,native_effect_history_complete=False)
    live.atomic_json(path,record);return s

def execute_ladder(client,plan,*,layout_record=None):
    if plan!=_canonical(plan):raise ValueError('ladder plan differs from brief')
    prefix=None
    if layout_record:
        old=live._load_layout_record(layout_record)
        if not old.get('unfinished_step') and old.get('summary',{}).get('status')=='ok':
            if old.get('plan')!=plan:raise ValueError('ladder receipt differs from approved brief')
            return inspect_ladder(client,layout_record,checked=True)
        # Explicit, bounded prefix adoption only; failed/unknown stages never replay.
        ops=old.get('operations',[]);completed=len(ops)-1
        if (not 1<=completed<len(plan['steps']) or old['plan']['steps'][:completed]!=plan['steps'][:completed]
                or old['plan']['brief']['roles']!=plan['brief']['roles']
                or any(ops[i]['name']!=plan['steps'][i]['name'] or ops[i]['response'].get('status')!='ok' for i in range(completed))
                or ops[-1]['name']!=plan['steps'][completed]['name'] or old.get('unfinished_step')!=plan['steps'][completed]['name']):
            raise live.LiveError('reconciliation_required','partial prefix changed or malformed; no replay')
        failed=ops[-1]['response'];reconciliation=None
        w=live._load_layout_record(failed['evidence']) if failed.get('evidence') else {}
        rid=w.get('attempts',[{}])[-1].get('request_id') if w.get('attempts') else None
        response=json.loads((client.evidence/(rid+'.response.json')).read_text()) if rid else {}
        known_discovery_failure=(failed.get('operation')=='connect-junction-at' and failed.get('stage')=='discover' and failed.get('game_constructed') is False and failed.get('status')=='no_eligible_candidates' and w.get('attempts')==[] and failed.get('attempt_count')==0)
        known_unbuilt=known_discovery_failure or (failed.get('game_constructed') is False and failed.get('stage')=='fit') or (response.get('status')=='error' and response.get('result',{}).get('stage')=='fit' and response['result'].get('game_constructed') is False)
        if not known_unbuilt:
            rp=client.evidence/(str(rid)+'.reconciliation.json');reconciliation=json.loads(rp.read_text()) if rp.exists() else {}
            absent=(reconciliation.get('status')=='reconciled_rejected_junction' and reconciliation.get('completed_junction_constructed') is False
                    and plan['steps'][completed]['kind']=='junction') or (reconciliation.get('status')=='reconciled_rejected_corridor' and reconciliation.get('completed_corridor_absent') is True and plan['steps'][completed]['kind']=='spine')
            if not absent or reconciliation.get('original_pending',{}).get('request_id')!=rid:raise live.LiveError('reconciliation_required','failed stage not independently proven unbuilt')
        prefix=old
    path=client.evidence/(uuid.uuid4().hex+'.ladder.json');record={'plan':plan,'operations':[],'observations':[],'summary':{'status':'incomplete','operation':'ladder-layout','game_constructed':False}}
    if prefix:record['summary']['recorded_prior_game_constructed']=prefix['summary'].get('game_constructed','unknown')
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending native operation; no construction')
        junctions=[]
        if prefix:
            record['initial_ports']=prefix['initial_ports'];ports=_roles(client,plan,record,True);b=plan['brief'];proofs=[]
            active=plan['steps'][:completed]
            for step in active:
                if step['kind']=='junction':
                    node,observations=live._recipe_junction(client,step['brief']['source']);junctions.append(node);record['observations']+=observations
            def proof(a,z,target_node=None):
                q={'source_edge':a['edge_id'],'source_node':_other(a),'target_edge':z['edge_id'],'target_node':_other(z) if target_node is None else target_node,'required_edges':[a['edge_id'],z['edge_id']],'mode':'TRAIN','junction_nodes':junctions,'max_length':b['max_route_length'],'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':b['radius'],'max_grade':b['vertical']['max_grade'],'region':b['region']}}
                r=client.request('route',q);proofs.append(r)
                if r['status']!='ok' or r.get('result',{}).get('requested_route_verified') is not True:raise live.LiveError('reconciliation_required','completed prefix path not freshly proven')
            for g in b['groups']:
                names={step['name'] for step in active};base=g['id']
                if base+'_spine' in names:proof(ports[g['inbound']],ports[g['destinations'][0]])
                if base+'_arm' in names:
                    end,_=live._select_throat_port(client,g['arm_end'],tolerance=.001,connected=True);proof(ports[g['outbound']],end,end['node_id'])
                if base+'_junction_0' in names:proof(ports[g['destinations'][0]],ports[g['outbound']])
                for i in (1,2):
                    if base+'_junction_'+str(i) in names:
                        dest=g['destinations'][3-i];proof(ports[g['inbound']],ports[dest]);proof(ports[dest],ports[g['outbound']])
            record.update(operations=prefix['operations'][:completed],continuation={'record':str(Path(layout_record).resolve()),'prefix_proofs':proofs,'completed_prefix':completed,'failed_stage_reconciliation':reconciliation,'known_prebuild_failure':known_unbuilt,'automatic_replay':False});record['summary']['game_constructed']=True
        else:record['initial_ports']=_roles(client,plan,record,False)
        live.atomic_json(path,record)
        for index,step in enumerate(plan['steps']):
            if prefix and index<completed:continue
            record['unfinished_step']=step['name'];live.atomic_json(path,record)
            if step['kind']=='spine':answer=live.connect_corridor(client,step['brief'],execute=True)
            elif step['kind']=='arm':
                r=plan['brief']['roles'][step['source']];c,_=live._select_throat_port(client,r['endpoint'],tolerance=.001);end=step['target'];b=plan['brief']
                answer=live.extend(client,{'anchor_edge':c['edge_id'],'anchor_node':c['node_id'],'end_xy':end['guide_xyz'][:2],'end_direction':end['travel_direction'],'radius':b['radius'],'region':_arm_region(b,r['endpoint'],end),'vertical':b['vertical']|{'end_height':end['guide_xyz'][2],'end_grade':0}},execute=True)
            else:answer=live.connect_junction_at(client,step['brief'],execute=True,junction_nodes=junctions)
            record['operations'].append({'name':step['name'],'response':answer});effect=answer.get('game_constructed','unknown')
            if effect=='unknown':record['summary']['game_constructed']='unknown'
            elif effect is True and record['summary']['game_constructed']!='unknown':record['summary']['game_constructed']=True
            live.atomic_json(path,record)
            if answer['status']!='ok':raise live.LiveError(answer['status'],answer.get('error','ladder step failed'))
            if step['kind']=='junction':junctions.append(answer['junction']['node'])
            record.pop('unfinished_step');live.atomic_json(path,record)
        record['summary'].update(_assess(client,plan,record));return _finish(record,path)
    except (live.LiveError,ValueError,KeyError,TypeError,OSError) as exc:return _finish(record,path,exc)

def inspect_ladder(client,layout_record,*,checked=False):
    old=live._load_layout_record(layout_record);plan=old['plan']
    if plan!=_canonical(plan):raise ValueError('saved plan changed')
    if set(old.get('initial_ports',{}))!=set(plan['brief']['roles']):raise ValueError('saved native interface binding unavailable')
    path=client.evidence/(uuid.uuid4().hex+'.ladder_inspection.json');record={'plan':plan,'initial_ports':old.get('initial_ports',{}),'operations':[],'observations':[],'prior_record':str(Path(layout_record).resolve()),'summary':{'operation':'ladder-layout-inspect','status':'incomplete','game_constructed':False,'recorded_prior_game_constructed':old.get('summary',{}).get('game_constructed','unknown'),'checked_existing':checked,'prior_unfinished_step':old.get('unfinished_step')}}
    try:record['summary'].update(_assess(client,plan,record));return _finish(record,path)
    except (live.LiveError,ValueError,KeyError,TypeError,OSError) as exc:return _finish(record,path,exc)
