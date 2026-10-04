"""Compact native scissors on existing running rails; no automatic replay."""
import itertools
import json
import math
from pathlib import Path
import uuid
import bridge_live as live
from bridge_crossing import _hint, _check_arms, _edge_extrema, classify
from bridge_route_set import inspect_route_set

ROLES=('W0','W1','E0','E1')
TURNS=('L0','L1','R0','R1')
PAIRS=[['L0','R1'],['L1','R0']]

def validate(b):
    if not isinstance(b,dict) or set(b)!={'version','endpoints','turnouts','center','axes','half_arm_length','region','radius','fit_radius','max_route_length'} or b['version']!=1:
        raise ValueError('version1 explicit scissors brief required')
    if set(b['endpoints'])!=set(ROLES) or set(b['turnouts'])!=set(TURNS):raise ValueError('four external roles and four explicit turnouts required')
    for h in [*b['endpoints'].values(),*b['turnouts'].values()]:_hint(h,True)
    c=b['center']
    if not isinstance(c,list) or len(c)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in c):raise ValueError('finite native center required')
    live.validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':c[:2],'end_direction':[1,0],'radius':b['radius'],'region':b['region']})
    for k,lo,hi in [('half_arm_length',0,300),('radius',0,1000),('fit_radius',0,1000),('max_route_length',0,3000)]:
        if type(b[k]) not in (int,float) or not math.isfinite(b[k]) or not lo<b[k]<=hi:raise ValueError(k+' outside bounded domain')
    if b['radius']<60 or b['fit_radius']<max(70,b['radius']):raise ValueError('hard60 radius and native fit70 minimum required')
    if any(b['region']['max'][i]-b['region']['min'][i]>1000 for i in range(3)):raise ValueError('bounded1000-unit region required')
    if not isinstance(b['axes'],list) or len(b['axes'])!=2:raise ValueError('two selected diagonal axes required')
    ds=[]
    for d in b['axes']:
        if not isinstance(d,list) or len(d)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in d) or math.hypot(*d)<1e-9:raise ValueError('finite nonzero axes required')
        ds.append([v/math.hypot(*d) for v in d])
    dot=sum(a*z for a,z in zip(*ds))
    if abs(math.degrees(math.acos(max(-1,min(1,dot))))-15)>.001:raise ValueError('selected15-degree domain required')
    ex=b['endpoints'];w0=ex['W0']['guide_xyz'];w1=ex['W1']['guide_xyz'];e0=ex['E0']['guide_xyz'];e1=ex['E1']['guide_xyz']
    axis=[(e0[i]-w0[i])/300 for i in range(2)]
    normal=[-axis[1],axis[0]]
    expected={'W0':w0,'W1':[w0[i]+5*(normal[i] if i<2 else 0) for i in range(3)],'E0':[w0[i]+300*(axis[i] if i<2 else 0) for i in range(3)],'E1':[w1[i]+300*(axis[i] if i<2 else 0) for i in range(3)]}
    if abs(math.hypot(*axis)-1)>.000001 or math.dist(c,[w0[i]+150*(axis[i] if i<2 else 0)+2.5*(normal[i] if i<2 else 0) for i in range(3)])>.001:raise ValueError('level300x5 running-rail domain required')
    for n,pos in expected.items():
        if math.dist(ex[n]['guide_xyz'],pos)>.001:raise ValueError('level equal5 spacing required')
        wanted=axis if n.startswith('W') else [-v for v in axis]
        d=ex[n]['travel_direction'];d=[v/math.hypot(*d) for v in d]
        if math.dist(d,wanted)>1e-5:raise ValueError('explicit external directions differ')
    for i,d in enumerate(ds):
        wanted=[math.cos(math.radians(7.5))*axis[j]+(1 if i==0 else -1)*math.sin(math.radians(7.5))*normal[j] for j in range(2)]
        if math.dist(d,wanted)>1e-5:raise ValueError('selected diagonal orientation differs')
    longitudinal={}
    for n,h in b['turnouts'].items():
        pos=h['guide_xyz'];delta=[pos[i]-w0[i] for i in range(2)];x=sum(delta[i]*axis[i] for i in range(2));y=sum(delta[i]*normal[i] for i in range(2))
        if not 0<x<300 or abs(y-(5 if n.endswith('1') else 0))>.001 or abs(pos[2]-c[2])>.001:raise ValueError('turnout must lie on declared running rail')
        longitudinal[n]=x
        wanted=axis if n.startswith('L') else [-v for v in axis];d=h['travel_direction'];d=[v/math.hypot(*d) for v in d]
        if math.dist(d,wanted)>1e-5:raise ValueError('explicit branch travel directions differ')
    if not (longitudinal['L0']<150<longitudinal['R0']) or abs(longitudinal['L0']+longitudinal['R0']-300)>.001 or abs(longitudinal['L0']-longitudinal['L1'])>.001 or abs(longitudinal['R0']-longitudinal['R1'])>.001:raise ValueError('symmetric ordered turnout positions required')
    for n,t in tips(b).items():
        p=t['position'];delta=[p[i]-w0[i] for i in range(2)];y=sum(delta[i]*normal[i] for i in range(2))
        if not -.001<=y<=5.001:raise ValueError('crossing arms outside running rails')
    return b

def _branch_envelope(b,controls):
    """Reuse Hermite extrema in the running-rail frame, including rotated sites."""
    if not isinstance(controls,list) or not 1<=len(controls)<=8:raise ValueError('complete native branch controls required')
    origin=b['endpoints']['W0']['guide_xyz'];finish=b['endpoints']['E0']['guide_xyz']
    axis=[(finish[i]-origin[i])/300 for i in range(2)];normal=[-axis[1],axis[0]]
    for e in controls:
        q={}
        for k in ('p0','p1','t0','t1'):
            v=[e[k][i]-(origin[i] if k.startswith('p') else 0) for i in range(3)]
            q[k]=[sum(v[i]*axis[i] for i in range(2)),sum(v[i]*normal[i] for i in range(2)),v[2]]
        if any(not -.001<=p[0]<=300.001 or not -.001<=p[1]<=5.001 or abs(p[2])>.001 for p in _edge_extrema(q)):
            raise live.LiveError('branch_outside_running_rails','native branch leaves selected level300x5 envelope')

def tips(b):
    result={}
    for pair,d in zip(PAIRS,b['axes']):
        d=[x/math.hypot(*d) for x in d]
        for name,sign in zip(pair,(1,-1)):
            result[name]={'position':[b['center'][i]-sign*b['half_arm_length']*(d[i] if i<2 else 0) for i in range(3)],'toward_center':[sign*x for x in d]}
    return result

def _movements():
    result=[]
    for a,z in itertools.permutations(ROLES,2):
        via=[]
        if a[0]!=z[0]:
            via=[('L' if a[0]=='W' else 'R')+a[1]]
            if a[1]!=z[1]:via.append('C')
            via.append(('R' if z[0]=='E' else 'L')+z[1])
        result.append({'id':a+'_to_'+z,'from':a,'to':z,'via':via})
    return result

def _source(client,b,n):
    h=b['turnouts'][n]
    c,rid=live._select_throat_port(client,{k:v for k,v in h.items() if k!='position_tolerance'},interior=True,tolerance=h['position_tolerance'])
    if abs(c['grade'])>1e-6:raise live.LiveError('unsupported_grade','level existing running rail required')
    t=tips(b)[n]
    return {'source':c,'location':{'guide_xyz':h['guide_xyz'],'travel_direction':h['travel_direction'],'placement_tolerance':h['position_tolerance'],'heading_tolerance_deg':h['heading_tolerance_deg']},
            'end_xyz':t['position'],'end_direction':t['toward_center'],'radius':b['radius'],'fit_radius':b['fit_radius'],'region':b['region'],
            'vertical':{'max_grade':0},'max_route_length':b['max_route_length']},rid

def scissors(client,b,*,execute=False):
    validate(b)
    if type(execute) is not bool:raise ValueError('execute must be boolean')
    path=client.evidence/(uuid.uuid4().hex+'.scissors.json');lock=client.evidence/'scissors.lock'
    r={'version':1,'brief':b,'session':client.session,'operations':[],'leads':{},'game_constructed':False}
    stage='preflight'
    def save():live.atomic_json(path,r)
    def call(n,op,p):
        r['unfinished_step']=n;save();response=client.request(op,p);r['operations'].append({'stage':n,'params':p,'response':response});r.pop('unfinished_step');save()
        if execute and p.get('execute'):
            effect=response.get('result',{}).get('game_constructed','unknown')
            if effect in (True,'unknown'):r['game_constructed']=effect
        if response['status']!='ok':raise live.LiveError(response['status'],response.get('result',{}).get('error','native scissors stage failed'))
        return response
    try:
        with lock.open('x'):pass
    except FileExistsError:raise live.LiveError('client_busy','one scissors workflow at a time') from None
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','unfinished native request; no replay')
        for n in ROLES:
            live._select_throat_port(client,{k:v for k,v in b['endpoints'][n].items() if k!='position_tolerance'},tolerance=b['endpoints'][n]['position_tolerance'],connected=True)
        for n in TURNS:
            p,rid=_source(client,b,n);p['execute']=False
            response=call('prepare_'+n,'interior_junction',p)
            _branch_envelope(b,response['result']['fit']['controls'])
        if not execute:
            summary={'status':'ok','operation':'scissors','stage':'prepared','game_constructed':False,'evidence':str(path.resolve())};r['summary']=summary;save();return summary
        for n in TURNS:
            stage='turnout_'+n;p,rid=_source(client,b,n);p['junction_nodes']=[v['junction']['node'] for v in r['leads'].values()];p['execute']=True
            response=call(stage,'interior_junction',p);r['leads'][n]=response['result'];save()
        stage='crossing'
        ports={}
        for n,v in r['leads'].items():
            rb=v['readback'];current=call('current_tip_'+n,'inspect',{'edge_ids':[rb['ordered_edges'][-1]]})
            ports[n]={'edge_snapshot':current['result']['edges'][0],'node_id':rb['ordered_nodes'][-1]}
        p={'center':b['center'],'region':b['region'],'ports':ports,'pairs':PAIRS,'execute':True,'authorised':True}
        response=call(stage,'degree_four_candidate',p);r['crossing']={'params':p,'response':response};r['complete_receipts']=True;save()
        stage='inspection';summary=_inspect(client,r,path);summary.update(operation='scissors',game_constructed=True,construction_record=str(path.resolve()));r['summary']=summary;save();return summary
    except (live.LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary={'status':getattr(exc,'status','invalid_scissors_record'),'operation':'scissors','stage':stage,'game_constructed':r['game_constructed'],'error':str(exc)[:400],'evidence':str(path.resolve()),'automatic_resume':False};r['summary']=summary;save();return summary
    finally:lock.unlink(missing_ok=True)

def inspect_scissors(client,record_path):
    r=json.loads(Path(record_path).read_text(encoding='utf-8-sig'));validate(r['brief'])
    if r['session']!=client.session:raise live.LiveError('stale_session','current-session scissors record required')
    if r.get('complete_receipts') is not True:raise live.LiveError('incomplete_record','fresh partial reconciliation required; no automatic construction')
    return _inspect(client,r,record_path)

def _inspect(client,r,original):
    b=r['brief'];path=client.evidence/(uuid.uuid4().hex+'.scissors_inspect.json');obs={'construction':str(original),'brief':b,'session':client.session}
    v=r['crossing']['response']['result'];p=r['crossing']['params']
    crossing=client.request('inspect_degree_four',{'ports':p['ports'],'pairs':PAIRS,'center':b['center'],'center_node':v['center_node'],'arm_edges':v['arm_edges']})
    obs['crossing']=crossing
    if crossing['status']!='ok':raise live.LiveError(crossing['status'],crossing.get('result',{}).get('error','crossing inspection failed'))
    inner=crossing['result'];assessment=classify(inner);obs['crossing_assessment']=assessment
    _check_arms({'center':b['center'],'pairs':PAIRS,'axes':b['axes'],'half_arm_length':b['half_arm_length']},inner)
    junctions={n:{k:h[k] for k in ('region','max_edges','guide_xyz','position_tolerance')} for n,h in b['turnouts'].items()}
    junctions['C']={'region':{'min':[x-1 for x in b['center']],'max':[x+1 for x in b['center']]},'max_edges':16,'guide_xyz':b['center'],'position_tolerance':.001}
    # Query all12 movements once; complete paths are assessed across the entire set.
    movements=_movements()
    summary=inspect_route_set(client,{'version':1,'endpoints':b['endpoints'],'junctions':junctions,'movements':movements,'mode':'TRAIN','max_length':b['max_route_length']})
    report=json.loads(Path(summary['evidence']).read_text());obs['movement_summary']=summary;obs['movement_evidence']=summary['evidence']
    required=[m for m in report['movements'] if m['from'][0]!=m['to'][0]];forbidden=[m for m in report['movements'] if m['from'][0]==m['to'][0]]
    absent=all(m.get('response',{}).get('status')=='ok' and m['response']['result'].get('native_path_found') is False and m['response']['result'].get('reason')=='no_native_path_returned' and m['response']['result'].get('truncated') is False for m in forbidden)
    witnesses=[]
    for a,z in [('W0_to_E0','W1_to_E1'),('E0_to_W0','E1_to_W1')]:
        pair=next((x for x in report['pairs'] if {x['a'],x['b']}=={a,z}),{})
        witnesses.append(pair)
    degrees={n:len(report.get('junctions',{}).get(n,{}).get('incident_edges',[])) for n in junctions}
    ids={n:report.get('junctions',{}).get(n,{}).get('node_id') for n in junctions}
    exact_junctions=all(ids[n]==r['leads'][n]['junction']['node'] for n in TURNS) and ids['C']==v['center_node']
    geometries=[];edgeids=set(v['arm_edges'])
    for lead in r['leads'].values():edgeids.update(lead['readback']['ordered_edges'])
    for i in range(0,len(edgeids),16):
        current=client.request('inspect',{'edge_ids':sorted(edgeids)[i:i+16],'geometry':True,'geometry_constraints':{'radius':b['radius'],'max_grade':0,'region':b['region']}});geometries.append(current)
    obs['geometry']=geometries
    for g in geometries:
        for e in g.get('result',{}).get('edges',[]):_branch_envelope(b,[e])
    points=[pt for g in geometries for e in g.get('result',{}).get('edges',[]) for pt in _edge_extrema(e)]
    qualified=(summary['status']=='ok' and exact_junctions and len(required)==8 and all(m['complete'] for m in required) and absent and assessment['qualified'] and len(set(ids.values()))==5 and all(degrees[n]==3 for n in TURNS) and degrees['C']==4 and all(w.get('both_paths_complete') and w.get('result')=='topology_disjoint' and not w.get('shared_TRACK_edges') and not w.get('shared_junction_nodes') for w in witnesses) and all(g['status']=='ok' for g in geometries))
    result={'status':'ok' if qualified else 'scissors_not_qualified','operation':'scissors-inspect','game_constructed':False,'qualified':qualified,'junction_nodes':ids,'junction_degrees':degrees,'required_paths_complete':sum(m['complete'] for m in required),'same_end_no_returned_paths':absent,'independent_straight_witnesses':all(w.get('result')=='topology_disjoint' for w in witnesses),'crossing_qualification':assessment['qualified'],'movement_evidence':summary['evidence'],'evidence':str(path.resolve()),'construction_record':str(original),'sampled_only':True,'native_snapshot_atomic':False,'train_traversal':'unprobed','capacity':'not_assessed'}
    obs.update(summary=result,independent_witnesses=witnesses,footprint={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]} if points else None);live.atomic_json(path,obs);return result
