"""Caller-paired native level crossings and fitted leads; no routing planner."""
import itertools
import json
import math
import uuid
from pathlib import Path
import bridge_live as live
from bridge_route_set import _hint, _name, inspect_route_set

ARMS=('W','E','S','N')
STRAIGHT={('W','E'),('E','W'),('S','N'),('N','S')}

def validate(brief):
    if isinstance(brief,dict) and brief.get('version')==2:return _validate_v2(brief)
    if not isinstance(brief,dict) or set(brief)!={'version','center','region','endpoints'} or brief['version']!=1:
        raise ValueError('version1 orthogonal crossing brief required')
    c=brief['center']
    if not isinstance(c,list) or len(c)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in c):
        raise ValueError('finite center XYZ required')
    live.validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':c[:2],'end_direction':[1,0],'radius':1,'region':brief['region']})
    if any(not brief['region']['min'][i]<=c[i]<=brief['region']['max'][i] or brief['region']['max'][i]-brief['region']['min'][i]>400 for i in range(3)):
        raise ValueError('center must be inside bounded authorised region')
    if not isinstance(brief['endpoints'],dict) or set(brief['endpoints'])!=set(ARMS):
        raise ValueError('explicit W E S N endpoint hints required')
    for h in brief['endpoints'].values():_hint(h,True)
    return brief

def classify(readback):
    """Four proved straight paths plus eight observed no-path results; no global claim."""
    rows=readback.get('routes',[])
    pairing=readback.get('pairs',[['W','E'],['S','N']])
    names=[n for p in pairing for n in p]
    if len(pairing)!=2 or any(len(p)!=2 for p in pairing) or len(set(names))!=4:
        return {'qualified':False,'outcome':'invalid_pairing'}
    straight_pairs={tuple(p) for p in pairing}|{tuple(reversed(p)) for p in pairing}
    expected=set(itertools.permutations(names,2))
    if len(rows)!=12 or {(x.get('from'),x.get('to')) for x in rows}!=expected:
        return {'qualified':False,'outcome':'incomplete_movement_observation'}
    turns=[];unknown=[];straight=[]
    for x in rows:
        key=(x['from'],x['to']);r=x.get('result',{})
        if x.get('status')!='ok' or r.get('truncated') is not False:
            unknown.append(key);continue
        if key in straight_pairs:
            if r.get('requested_route_verified') is True and r.get('native_path_found') is True and r.get('transport_continuous') is True and r.get('path_count')==len(r.get('path',[])) and r.get('path_count',0)>0:
                straight.append(key)
            else:unknown.append(key)
        elif r.get('native_path_found') is True:turns.append(key)
        elif r.get('native_path_found') is not False or r.get('reason')!='no_native_path_returned' or r.get('path_count')!=0 or r.get('path') not in ([],{}):unknown.append(key)
    physical=(len(readback.get('arms',[]))==4 and len({a.get('id') for a in readback.get('arms',[])})==4 and type(readback.get('center_node')) is int and readback.get('transport_truncated') is False)
    qualified=physical and len(straight)==4 and not turns and not unknown
    return {'qualified':qualified,'outcome':('level_orthogonal_plain_crossing_observed' if names==list(ARMS) else 'caller_paired_plain_crossing_observed') if qualified else 'native_turn_movements_observed' if turns else 'crossing_unqualified',
            'straight_verified':len(straight),'turn_paths_returned':turns,'unknown_movements':unknown,
            'absent_turns':'no_native_path_returned_in_these_queries','global_no_route_proof':False,
            'shared_physical_crossing_node':readback.get('center_node'),'capacity':'not_assessed','train_traversal':'unprobed','reservation_availability':'unprobed'}

def _finish(client,record):
    path=client.evidence/(uuid.uuid4().hex+'.plain_crossing.json')
    native=record['response'];v=native.get('result',{})
    readback=v.get('readback',v if record['operation']=='plain-crossing-inspect' else None)
    assessment=classify(readback) if readback is not None else {'qualified':False,'outcome':'preflight_only' if native['status']=='ok' else 'native_operation_failed'}
    record['assessment']=assessment
    status=native['status']
    if readback is not None and status=='ok' and not assessment['qualified']:status='crossing_not_qualified'
    summary={'status':status,'operation':record['operation'],'session':client.session,'game_constructed':v.get('game_constructed',False),
             'qualification':assessment,'center_node':v.get('center_node'),'evidence':str(path.resolve()),'native_snapshot_atomic':False}
    record['summary']=summary;live.atomic_json(path,record);return summary

def crossing(client,brief,*,execute=False,prepared_record=None):
    validate(brief)
    if brief['version']==2:return _composed(client,brief,execute,prepared_record)
    if prepared_record:raise ValueError('prepared record applies only to version2 composition')
    ports={};observations=[]
    for name,h in brief['endpoints'].items():
        q={k:v for k,v in h.items() if k!='position_tolerance'}
        c,rid=live._select_throat_port(client,q,tolerance=h['position_tolerance'])
        ports[name]={'edge_snapshot':c['edge_snapshot'],'node_id':c['node_id']};observations.append(rid)
    params={'center':brief['center'],'region':brief['region'],'ports':ports,'execute':execute,'authorised':execute}
    response=client.request('degree_four_candidate',params)
    return _finish(client,{'version':1,'operation':'plain-crossing','session':client.session,'brief':brief,'params':params,'observations':observations,'response':response})

def inspect_crossing(client,record_path):
    record=json.loads(Path(record_path).read_text(encoding='utf-8-sig'))
    if record.get('brief',{}).get('version')==2:return _inspect_composed(client,record,record_path)
    if record.get('version')!=1 or record.get('session')!=client.session:raise live.LiveError('stale_session','fresh current-session crossing record required')
    validate(record['brief']);v=record['response']['result']
    if v.get('game_constructed') is not True or not v.get('arm_edges') or not v.get('center_node'):raise ValueError('completed native crossing record required')
    p={'ports':record['params']['ports'],'center':record['brief']['center'],'center_node':v['center_node'],'arm_edges':v['arm_edges']}
    response=client.request('inspect_degree_four',p)
    # Preserve the construction identity for another fresh read-only inspection.
    r=response.get('result',{})
    r['arm_edges']=v['arm_edges']
    return _finish(client,{'version':1,'operation':'plain-crossing-inspect','session':client.session,'brief':record['brief'],'params':record['params'],'construction':str(record_path),'response':response})

def _validate_v2(b):
    if set(b)!={'version','center','region','endpoints','pairs','axes','half_arm_length','radius','max_route_length'}:raise ValueError('version2 caller-paired composition brief required')
    if not isinstance(b['pairs'],list) or len(b['pairs'])!=2 or any(not isinstance(p,list) or len(p)!=2 for p in b['pairs']):raise ValueError('two explicit disjoint directed role pairs required')
    names=[n for p in b['pairs'] for n in p]
    if any(not _name(n) for n in names) or len(set(names))!=4 or not isinstance(b['endpoints'],dict) or set(b['endpoints'])!=set(names):raise ValueError('two explicit disjoint directed role pairs required')
    if any(not _name(a+'_to_'+z) for pair in b['pairs'] for a,z in (pair,list(reversed(pair)))):raise ValueError('paired movement names exceed existing observation limits')
    c=b['center']
    if not isinstance(c,list) or len(c)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in c):raise ValueError('finite native center XYZ required')
    live.validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':c[:2],'end_direction':[1,0],'radius':b['radius'],'region':b['region']})
    if any(b['region']['max'][i]-b['region']['min'][i]>1000 for i in range(3)):raise ValueError('bounded1000-unit composition region required')
    for k,lo,hi in [('half_arm_length',20,300),('radius',1,1000),('max_route_length',1,3000)]:
        if type(b[k]) not in (int,float) or not math.isfinite(b[k]) or not lo<=b[k]<=hi:raise ValueError(k+' outside bounded domain')
    if not isinstance(b['axes'],list) or len(b['axes'])!=2:raise ValueError('two explicit crossing travel axes required')
    ds=[]
    for d in b['axes']:
        if not isinstance(d,list) or len(d)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in d) or math.hypot(*d)<1e-9:raise ValueError('finite nonzero crossing axis required')
        ds.append([v/math.hypot(*d) for v in d])
    if abs(sum(x*y for x,y in zip(*ds)))>=.999:raise ValueError('nondegenerate crossing axes required')
    for h in b['endpoints'].values():
        _hint(h,True)
        if abs(h['guide_xyz'][2]-c[2])>.001:raise ValueError('initial composition is level; do not flatten endpoints')
    for q in [c,*[h['guide_xyz'] for h in b['endpoints'].values()],*[x['position'] for x in _tips(b).values()]]:
        if any(not b['region']['min'][i]<=q[i]<=b['region']['max'][i] for i in range(3)):raise ValueError('fixed endpoint/arm tip outside authorised region')
    return b

def _tips(b):
    out={}
    for pair,axis in zip(b['pairs'],b['axes']):
        d=[v/math.hypot(*axis) for v in axis]
        for name,sign in zip(pair,(-1,1)):
            out[name]={'position':[b['center'][i]+sign*b['half_arm_length']*d[i] for i in range(2)]+[b['center'][2]],'toward_center':[-sign*v for v in d],'binding_sign':-sign}
    return out

def _bindings(client,b,*,old=None,connected=False):
    result={}
    for name,t in _tips(b).items():
        h=b['endpoints'][name]
        c,_=live._select_throat_port(client,{k:v for k,v in h.items() if k!='position_tolerance'},tolerance=h['position_tolerance'],outward_sign=t['binding_sign'],connected=connected)
        e=c['edge_snapshot']
        if abs(c['pos'][2]-b['center'][2])>.001 or abs(c['grade'])>1e-6:raise live.LiveError('unsupported_crossing_height','actual boundary must be level at selected height')
        if old and (c['node_id']!=old[name]['node_id'] or e!=old[name]['edge_snapshot']):raise live.LiveError('stale_crossing_attachment','exact current external attachment changed')
        result[name]=c
    return result

def _composed_summary(client,record,path,status,stage,error=None):
    summary={'status':status,'operation':record.get('operation','plain-crossing'),'session':client.session,'stage':stage,'game_constructed':record.get('game_constructed',False),'evidence':str(path.resolve()),'native_snapshot_atomic':False}
    if error:summary['error']=str(error)[:400]
    if 'assessment' in record:summary['qualification']=record['assessment']
    if 'engineering' in record:summary['engineering']=record['engineering']
    if 'conflicts' in record:summary['route_set']=record['conflicts']
    record['summary']=summary;live.atomic_json(path,record);return summary

def _composed(client,b,execute,prepared):
    if type(execute) is not bool:raise ValueError('explicit boolean execute required')
    path=client.evidence/(uuid.uuid4().hex+'.composed_crossing.json')
    record={'version':2,'brief':b,'session':client.session,'operations':[],'leads':{},'game_constructed':False}
    stage='bind'
    try:
        if prepared:
            if not execute:raise ValueError('prepared record requires explicit execute')
            record=json.loads(Path(prepared).read_text(encoding='utf-8-sig'))
            if record.get('brief')!=b or record.get('session')!=client.session or record.get('summary',{}).get('stage')!='prepared' or record.get('game_constructed') is not False:raise ValueError('matching unbuilt current-session preparation required')
            record['ports']=_bindings(client,b,old=record['ports']);record['preparation']=str(prepared)
        else:
            record['ports']=_bindings(client,b)
            stage='fit'
            for name,t in _tips(b).items():
                c=record['ports'][name]
                q={'anchor_edge':c['edge_id'],'anchor_node':c['node_id'],'end_xy':t['position'][:2],'end_direction':t['toward_center'],'radius':b['radius'],'region':b['region']}
                r=client.request('fit',q);record['leads'][name]={'fit':r,'brief':q};live.atomic_json(path,record)
                if r['status']!='ok':raise live.LiveError(r['status'],r.get('result',{}).get('error','native_lead_fit_failed'))
        if not execute:return _composed_summary(client,record,path,'ok','prepared')
        for name,t in _tips(b).items():
            # Preparation is evidence, not a native handle lease. The existing
            # extension operation retains its fit within one fit/build invocation.
            stage='lead_build';lead=record['leads'][name];c=record['ports'][name]
            q={'anchor_edge':c['edge_id'],'anchor_node':c['node_id'],'end_xy':t['position'][:2],'end_direction':t['toward_center'],'radius':b['radius'],'region':b['region']}
            r=client.request('extension',{'brief':q,'execute':True});lead['build']=r;record['operations'].append({'stage':stage,'role':name,'response':r})
            if r['status']=='ok':record['game_constructed']=True
            elif r.get('result',{}).get('game_constructed') is not False:record['game_constructed']='unknown'
            live.atomic_json(path,record)
            if r['status']!='ok':raise live.LiveError(r['status'],r.get('result',{}).get('error','native_lead_build_failed'))
            v=r['result']['readback'];lead['edges']=v['ordered_edges'];lead['nodes']=v['ordered_nodes']
            _lead_observation(client,b,name,lead,record['ports'][name])
        stage='crossing_build'
        ports={name:{'edge_snapshot':lead['inspection']['result']['edges'][-1],'node_id':lead['nodes'][-1]} for name,lead in record['leads'].items()}
        q={'center':b['center'],'region':b['region'],'ports':ports,'pairs':b['pairs'],'execute':True,'authorised':True}
        r=client.request('degree_four_candidate',q);record['crossing']={'params':q,'response':r};record['operations'].append({'stage':stage,'response':r});live.atomic_json(path,record)
        if r['status']!='ok':
            record['game_constructed']='unknown';raise live.LiveError(r['status'],r.get('result',{}).get('error','native_crossing_build_failed'))
        record['complete_receipts']=True;stage='inspect';live.atomic_json(path,record)
        summary=_inspect_composed(client,record,path)
        summary.update(operation='plain-crossing',game_constructed=record['game_constructed'],construction_record=str(path.resolve()))
        record['summary']=summary;live.atomic_json(path,record);return summary
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:
        return _composed_summary(client,record,path,getattr(exc,'status','invalid_crossing_record'),stage,exc)

def _lead_observation(client,b,name,lead,port):
    ids,nodes=lead['edges'],lead['nodes'];t=_tips(b)[name]
    if not 1<=len(ids)<=16 or len(nodes)!=len(ids)+1 or nodes[0]!=port['node_id']:raise ValueError('complete exact lead receipt required')
    r=client.request('inspect',{'edge_ids':ids,'geometry':True,'geometry_constraints':{'radius':b['radius'],'max_grade':0,'region':b['region']}});lead['inspection']=r
    if r['status']!='ok':raise live.LiveError(r['status'],r.get('result',{}).get('error','lead_geometry_unavailable'))
    by_id={e['id']:e for e in r['result']['edges']};rows=[by_id[i] for i in ids];r['result']['edges']=rows
    if any([e['node0'],e['node1']]!=nodes[i:i+2] for i,e in enumerate(rows)) or math.dist(rows[0]['p0'],port['pos'])>.001 or math.dist(rows[-1]['p1'],t['position'])>.001:raise live.LiveError('stale_crossing_lead','exact realised lead boundaries changed')
    def heading(v):return [x/math.hypot(*v[:2]) for x in v[:2]]
    if math.dist(heading(rows[0]['t0']),port['outward_direction'][:2])>1e-5 or math.dist(heading(rows[-1]['t1']),t['toward_center'])>1e-5:raise live.LiveError('native_verification_failed','lead endpoint tangent changed')
    for a,z in zip(rows,rows[1:]):
        if math.dist(a['p1'],z['p0'])>.001 or math.dist(heading(a['t1']),heading(z['t0']))>1e-5:raise live.LiveError('native_verification_failed','realised lead join differs')
    return rows

def _edge_extrema(e):
    """BaseEdge Hermite extrema, rather than an endpoint-only footprint."""
    points=[e['p0'],e['p1']]
    for i in range(3):
        p,q,t,v=(e[k][i] for k in ('p0','p1','t0','t1'))
        a=2*p-2*q+t+v;z=-3*p+3*q-2*t-v
        if abs(a)<1e-12:roots=[-t/(2*z)] if abs(z)>1e-12 else []
        else:
            d=4*z*z-12*a*t
            roots=[(-2*z+s*math.sqrt(d))/(6*a) for s in (-1,1)] if d>=0 else []
        for u in roots:
            if 0<u<1:
                points.append([(2*u**3-3*u*u+1)*e['p0'][j]+(u**3-2*u*u+u)*e['t0'][j]+(-2*u**3+3*u*u)*e['p1'][j]+(u**3-u*u)*e['t1'][j] for j in range(3)])
    return points

def _cross_pair_conflicts(report,b,center):
    groups={a+'_to_'+z:i for i,pair in enumerate(b['pairs']) for a,z in (pair,list(reversed(pair)))}
    rows=[r for r in report['pairs'] if groups[r['a']]!=groups[r['b']]]
    return len(rows)==4 and all(r['both_paths_complete'] and not r['shared_TRACK_edges'] and center in r['shared_junction_nodes'] for r in rows)

def _check_arms(b,inner):
    lengths=[]
    for name,tip in _tips(b).items():
        port=inner['ports'][name];a=port['arm'];sign=1 if a['node0']==port['node'] else -1
        start=a['p0'] if sign==1 else a['p1'];end=a['p1'] if sign==1 else a['p0']
        if math.dist(start,tip['position'])>.001 or math.dist(end,b['center'])>.001:raise live.LiveError('native_verification_failed','actual arm boundaries changed')
        lengths.append(math.dist(start,end))
        for t in (a['t0'],a['t1']):
            speed=math.hypot(*t[:2])
            if speed<1e-9 or abs(t[2])>1e-9 or math.dist([sign*v/speed for v in t[:2]],tip['toward_center'])>1e-5:raise live.LiveError('native_verification_failed','actual straight arm tangent differs')
    return lengths

def _inspect_composed(client,source,record_path):
    b=validate(source['brief'])
    if source.get('session')!=client.session or source.get('complete_receipts') is not True:raise live.LiveError('stale_or_incomplete_crossing','completed current-session record required')
    record=json.loads(json.dumps(source));record['operations']=[];record['game_constructed']=False;record['construction']=str(record_path);record['operation']='plain-crossing-inspect'
    path=client.evidence/(uuid.uuid4().hex+'.composed_crossing_inspection.json')
    try:
        ports=_bindings(client,b,old=record['ports'],connected=True);all_edges=[]
        for name,lead in record['leads'].items():all_edges.extend(_lead_observation(client,b,name,lead,ports[name]))
        built=record['crossing']['response']['result'];q=record['crossing']['params']
        r=client.request('inspect_degree_four',{'ports':q['ports'],'pairs':b['pairs'],'center':b['center'],'center_node':built['center_node'],'arm_edges':built['arm_edges']});record['crossing_readback']=r
        if r['status']!='ok':raise live.LiveError(r['status'],r.get('result',{}).get('error','crossing_readback_failed'))
        inner=r['result'];outer=[];arm_lengths=_check_arms(b,inner)
        arm_observation=client.request('inspect',{'edge_ids':built['arm_edges'],'geometry':True,'geometry_constraints':{'radius':b['radius'],'max_grade':0,'region':b['region']}});record['arm_geometry']=arm_observation
        if arm_observation['status']!='ok':raise live.LiveError(arm_observation['status'],'actual crossing arm geometry failed checks')
        all_edges.extend(arm_observation['result']['edges'])
        for a,z in itertools.permutations(ports,2):
            x,y=ports[a],ports[z];other=lambda c:c['edge_snapshot']['node1'] if c['node_id']==c['edge_snapshot']['node0'] else c['edge_snapshot']['node0']
            p={'source_edge':x['edge_id'],'source_node':other(x),'target_edge':y['edge_id'],'target_node':other(y),'required_edges':[x['edge_id'],y['edge_id']],'mode':'TRAIN','max_length':b['max_route_length'],'junction_nodes':[built['center_node']]}
            response=client.request('route',p);outer.append({'from':a,'to':z,'status':response['status'],'result':response.get('result',{})})
        record['external_routes']=outer;record['assessment']=classify(inner|{'routes':outer})
        if record['assessment']['qualified']:record['assessment']['outcome']='caller_paired_plain_crossing_observed'
        ds=[]
        for pair in b['pairs']:
            port=inner['ports'][pair[0]];a=port['arm'];pos=a['p0'] if a['node0']==port['node'] else a['p1'];ds.append([inner['center_position'][i]-pos[i] for i in range(2)])
        cos=abs(sum(x*y for x,y in zip(*ds))/(math.hypot(*ds[0])*math.hypot(*ds[1])))
        points=[p for e in all_edges+[x['edge_snapshot'] for x in ports.values()] for p in _edge_extrema(e)]
        if any(not b['region']['min'][i]-.001<=p[i]<=b['region']['max'][i]+.001 for p in points for i in range(3)):raise live.LiveError('native_verification_failed','actual cubic extrema outside authorised region')
        samples=[s['pos'] for e in all_edges if 'movement_geometry' in e for s in e['movement_geometry']['samples']]
        radii=[e['engineering_checks']['min_sampled_radius'] for e in all_edges if e.get('engineering_checks',{}).get('min_sampled_radius') is not None]
        record['engineering']={'crossing_angle_deg':math.degrees(math.acos(min(1,cos))),'half_arm_length':b['half_arm_length'],'min_sampled_radius':min(radii) if radii else None,'selected_min_radius':b['radius'],'max_sampled_grade':max(e.get('engineering_checks',{}).get('max_sampled_grade',0) for e in all_edges),'base_height':b['center'][2],'movement_height_range':[min(p[2] for p in samples),max(p[2] for p in samples)] if samples else None,'footprint_including_stubs':[max(p[i] for p in points)-min(p[i] for p in points) for i in range(2)],'endpoint_spacings':[math.dist(ports[b['pairs'][0][j]]['pos'],ports[b['pairs'][1][j]]['pos']) for j in (0,1)],'continuous_clearance_proof':False}
        record['engineering']['actual_half_arm_length_range']=[min(arm_lengths),max(arm_lengths)]
        hints={name:b['endpoints'][name]|{'travel_direction':ports[name]['outward_direction'][:2]} for name in ports}
        # Search the known arm envelope; native movement bounds need not contain
        # the exact BaseNode in a two-unit box. Identity tolerance stays unchanged.
        pos=b['center'];tips=[t['position'] for t in _tips(b).values()]
        junction={'region':{'min':[min(t[i] for t in tips)-2 for i in range(3)],'max':[max(t[i] for t in tips)+2 for i in range(3)]},'max_edges':16,'guide_xyz':pos,'position_tolerance':.001}
        movements=[{'id':a+'_to_'+z,'from':a,'to':z,'via':['crossing']} for pair in b['pairs'] for a,z in (pair,list(reversed(pair)))]
        record['conflicts']=inspect_route_set(client,{'version':1,'endpoints':hints,'junctions':{'crossing':junction},'movements':movements,'mode':'TRAIN','max_length':b['max_route_length']})
        report=json.loads(Path(record['conflicts']['evidence']).read_text(encoding='utf-8-sig'))
        conflict_ok=_cross_pair_conflicts(report,b,built['center_node'])
        record['assessment']['cross_pair_shared_node_without_shared_TRACK']=conflict_ok
        return _composed_summary(client,record,path,'ok' if record['assessment']['qualified'] and record['conflicts'].get('complete_paths')==4 and conflict_ok else 'crossing_not_qualified','verified')
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _composed_summary(client,record,path,getattr(exc,'status','native_verification_failed'),'inspect',exc)
