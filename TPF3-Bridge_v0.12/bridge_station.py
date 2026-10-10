"""Basic native station placement and bounded exact-identity survey."""
import math
import copy
import uuid
import bridge_live as live

def normalized_station(value):
    """Lua's empty table is {} on the wire; normalize only declared list fields."""
    lists={'ports','external_edges','matches','constructions','stations','terminals','vehicle_edges','frozen_tracks','incident_edges','edge_ids','terminal_identity_matches'}
    def walk(v):
        if isinstance(v,dict):
            out={}
            for k,x in v.items():
                if k in lists:
                    if x=={}:x=[]
                    if not isinstance(x,list):raise ValueError('malformed station list '+k)
                out[k]=walk(x)
            return out
        if isinstance(v,list):return [walk(x) for x in v]
        return v
    return walk(copy.deepcopy(value))

def frozen_components(value,cid):
    rows=[c for c in value['constructions'] if c['construction_id']==cid]
    if len(rows)!=1:raise ValueError('exact station construction required')
    tracks=rows[0]['frozen_tracks'];edges={};nodes={}
    if len(tracks)>2048:raise ValueError('frozen TRACK observation bound')
    for e in tracks:
        eid=e['edge_id'];ends=[e['node0'],e['node1']]
        if eid in edges or any(type(x) is not int or x<=0 for x in [eid]+ends) or ends[0]==ends[1]:raise ValueError('exact distinct frozen TRACK identities required')
        edges[eid]=e
        for node in ends:nodes.setdefault(node,set()).add(eid)
    components={};remaining=set(edges)
    while remaining:
        stack=[min(remaining)];group=set()
        while stack:
            eid=stack.pop()
            if eid in group:continue
            group.add(eid);remaining.discard(eid)
            for node in (edges[eid]['node0'],edges[eid]['node1']):stack.extend(nodes[node]-group)
        for eid in group:components[eid]=group
    return edges,nodes,components

def associate_station_exit(value,candidate,cid):
    edges,nodes,components=frozen_components(value,cid);eid=candidate['edge_id'];nid=candidate['node_id']
    if eid not in edges or nid not in (edges[eid]['node0'],edges[eid]['node1']) or nodes[nid]!={eid}:return None
    if candidate.get('incident_count')!=1 or candidate.get('incident_edges')!=[eid] or candidate.get('incidence_complete') is not True or candidate.get('incident_output_truncated'):return None
    owner=candidate.get('construction_owner')
    if type(owner) in (int,float) and owner>0 and owner!=cid:return None
    snapshot=candidate.get('edge_snapshot',{})
    if snapshot.get('id')!=eid or snapshot.get('road_type')!='TRACK' or {snapshot.get('node0'),snapshot.get('node1')}!={edges[eid]['node0'],edges[eid]['node1']}:return None
    matches=[{'station_id':s['station_id'],'terminal_index':t['index'],'vehicle_edge':track}
             for s in value['stations'] if s['construction_id']==cid for t in s['terminals']
             for track in t['vehicle_edges'] if track in components[eid]]
    matches=list({(m['station_id'],m['terminal_index']):m for m in matches}.values())
    return {'kind':'exact_station_frozen_TRACK_incidence_component','construction_id':cid,'frozen_edge':eid,
            'edge_ids':sorted(components[eid]),'terminal_identity_matches':matches,'native_TRAIN_route':'unprobed'}

def inspect_exits(client,brief):
    """Discover exposed exact frozen rail nodes; no user-supplied internal IDs."""
    p=parameters(brief);session=client.session;first=client.request('station_lookup',p);v=normalized_station(first.get('result',{}))
    if first['status']!='ok' or v.get('complete') is not True or v.get('outcome')!='resolved':raise live.LiveError('station_exit_survey_incomplete',v.get('outcome',first['status']))
    endpoints=[]
    for construction in v['constructions']:
        cid=construction['construction_id'];edges,nodes,_=frozen_components(v,cid)
        endpoints.extend((cid,nid,next(iter(ids))) for nid,ids in sorted(nodes.items()) if len(ids)==1)
    if len(endpoints)>64:raise live.LiveError('station_exit_survey_incomplete','more than64 candidate frozen endpoints; no silent truncation')
    snapshots={};ids=sorted({eid for _,_,eid in endpoints})
    for start in range(0,len(ids),16):
        r=client.request('inspect',{'edge_ids':ids[start:start+16]})
        if r['status']!='ok':raise live.LiveError(r['status'],'exact frozen edge geometry unavailable')
        for e in r['result']['edges']:snapshots[e['id']]=e
    exits=[];rejected=[]
    for cid,nid,eid in endpoints:
        e=snapshots[eid];pos=e['p0'] if nid==e['node0'] else e['p1'];t=e['t0'] if nid==e['node0'] else e['t1']
        length=math.hypot(*t[:2])
        if not length:raise ValueError('station exit tangent unavailable')
        q={'region':{'min':[x-1 for x in pos],'max':[x+1 for x in pos]},'max_edges':16}
        r=client.request('discover',q);raw=r.get('result',{})
        if r['status']!='ok' or raw.get('complete') is not True:raise live.LiveError('station_exit_survey_incomplete','bounded exact-node discovery incomplete')
        matches=[c for c in raw.get('candidates',[]) if c['edge_id']==eid and c['node_id']==nid]
        if len(matches)!=1:raise live.LiveError('station_exit_survey_incomplete','exact candidate identity unavailable')
        c=matches[0];association=associate_station_exit(v,c,cid)
        if association:exits.append(c|{'association':association,'mode':'station_exit','native_buildability':'unprobed'})
        else:rejected.append({'edge':eid,'node':nid,'reason':'frozen_endpoint_has_external_or_changed_incidence'})
    final=client.request('station_lookup',p)
    if client.session!=session or final['status']!='ok' or normalized_station(final['result'])!=v:raise live.LiveError('stale_station','station changed during frozen-exit survey')
    path=client.evidence/(uuid.uuid4().hex+'.station_exits.json');live.atomic_json(path,{'session':client.session,'station':v,'exits':exits,'rejections':rejected,'game_constructed':False})
    summary=[{'edge':c['edge_id'],'node':c['node_id'],'xyz':c['pos'],'direction':c['outward_direction'],'grade':c['grade'],
              'construction':c['association']['construction_id'],'terminal_matches':len(c['association']['terminal_identity_matches'])} for c in exits[:8]]
    return {'status':'ok','name':p['name'],'session':client.session,'candidate_count':len(endpoints),'exits':len(exits),'rejected':len(rejected),
            'interfaces':summary,'summary_truncated':len(exits)>8,'native_buildability':'unprobed','game_constructed':False,'evidence':str(path)}


def place_station(client, brief, *, execute=False):
    """Prepare native modules; optionally submit once. Connections remain separate."""
    keys={'resource','template','params','position','angle','name'}
    if type(brief) is not dict or set(brief)!=keys or type(execute) is not bool:
        raise ValueError('station requires resource/template/params/position/angle/name')
    if brief['resource']!='::/stations/rail/modular_station/modular_station.con':
        raise ValueError('supported native modular passenger station required')
    if type(brief['template']) is not int or not 0<=brief['template']<=5:
        raise ValueError('explicit native passenger template required')
    p=brief['params']
    if (type(p) is not dict or set(p)-{'tracks','length','trackType','catenary','year'}
            or type(p.get('tracks')) is not int or not 1<=p['tracks']<=8
            or type(p.get('length')) is not int or not 1<=p['length']<=5):
        raise ValueError('bounded native station tracks/length controls required')
    for key in ('trackType','catenary','year'):
        if key in p and (type(p[key]) is not int or p[key]<0):
            raise ValueError('integer native station parameter required')
    if (type(brief['position']) is not list or len(brief['position'])!=3
            or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>=100000 for v in brief['position'])
            or type(brief['angle']) not in (int,float) or not math.isfinite(brief['angle']) or abs(brief['angle'])>=100
            or type(brief['name']) is not str or not 1<=len(brief['name'])<=80):
        raise ValueError('finite native position/angle and bounded station name required')
    prepared=client.request('operating_inspect',{'station_preparation':brief})
    if prepared['status']!='ok' or not execute:return prepared
    r=prepared.get('result',{}).get('station_preparation',{})
    if (r.get('resource')!=brief['resource'] or r.get('template')!=brief['template']
            or r.get('command_constructed') is not True or r.get('native_command_submitted') is not False):
        raise live.LiveError('reconciliation_required','matching native station preparation unavailable')
    return client.request('operating_control',dict(brief,action='station_build',execute=True))


def parameters(brief):
    if not isinstance(brief,dict) or set(brief)-{'name','max_groups','max_external_edges','max_lead_distance','survey_depth','max_frozen_entities','max_frozen_tracks'}:raise ValueError('bounded station survey brief required')
    if not isinstance(brief.get('name'),str) or not 1<=len(brief['name'].encode('utf-8'))<=120:raise ValueError('exact station name required')
    p={'name':brief['name'],'max_groups':brief.get('max_groups',256),'max_external_edges':brief.get('max_external_edges',64),'max_lead_distance':brief.get('max_lead_distance',800)}
    for k,limit in (('max_groups',256),('max_external_edges',64)):
        if type(p[k]) is not int or not 1<=p[k]<=limit:raise ValueError(k+' outside bounded domain')
    for k,limit in (('max_frozen_entities',16384),('max_frozen_tracks',2048)):
        if k in brief:
            if type(brief[k]) is not int or not 1<=brief[k]<=limit:raise ValueError(k+' outside bounded domain')
            p[k]=brief[k]
    for value,limit in ((p['max_lead_distance'],800),(brief.get('survey_depth',100),200)):
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=limit:raise ValueError('distance/depth outside bounded domain')
    return p


def mouth_groups(ports):
    groups=[]
    for p in ports:
        e=p['edge_snapshot'];n=p['node_id'];ids=p['incident_edges']
        if (type(n) is not int or n<=0 or e['id']!=p['edge_id'] or e['road_type']!='TRACK' or n not in (e['node0'],e['node1'])
                or p.get('eligible') is not True or p.get('incidence_complete') is not True or p.get('incident_output_truncated')
                or p['incident_count']!=1 or ids!=[p['edge_id']] or p.get('construction_owner') not in (None,'none',-1,0)):
            raise ValueError('free endpoint lacks exact TRACK/node/incidence identity')
        pos=e['p0'] if n==e['node0'] else e['p1']
        if p['pos']!=pos:raise ValueError('endpoint position does not match exact native node')
        d=p['outward_direction'];size=math.hypot(*d[:2])
        if size<1e-9 or any(not math.isfinite(x) for x in (*p['pos'],*d,p['grade'])):raise ValueError('invalid observed geometry')
        direction=[d[0]/size,d[1]/size]
        g=next((g for g in groups if sum(a*b for a,b in zip(g['direction'],direction))>=math.cos(math.radians(5))),None)
        if g is None:g={'direction':direction,'ports':[]};groups.append(g)
        g['ports'].append(p)
    for g in groups:
        ps=g['ports'];d=[sum(p['outward_direction'][k] for p in ps) for k in (0,1)];size=math.hypot(*d);d=[x/size for x in d];right=[-d[1],d[0]]
        origin=[sum(p['pos'][k] for p in ps)/len(ps) for k in range(3)]
        def projection(p,axis):return sum((p['pos'][k]-origin[k])*axis[k] for k in (0,1))
        ps.sort(key=lambda p:(projection(p,right),p['node_id']))
        across=[projection(p,right) for p in ps];along=[projection(p,d) for p in ps]
        g.update(direction=d,right=right,origin=origin,ordered_nodes=[p['node_id'] for p in ps],
            spacings=[b-a for a,b in zip(across,across[1:])],span=across[-1]-across[0],
            mouth_depth_spread=max(along)-min(along),elevation_spread=max(p['pos'][2] for p in ps)-min(p['pos'][2] for p in ps),
            max_heading_deviation_deg=max(math.degrees(math.acos(max(-1,min(1,sum(d[k]*p['outward_direction'][k]/math.hypot(*p['outward_direction'][:2]) for k in (0,1)))))) for p in ps))
    return groups


def inspect_station(client,brief):
    p=parameters(brief);session=client.session;path=client.evidence/(uuid.uuid4().hex+'.station_survey.json')
    record={'brief':brief,'session':session,'observations':[],'sites':[],'game_constructed':False}
    summary={'status':'incomplete','operation':'station-survey','name':p['name'],'game_constructed':False,'evidence':str(path.resolve()),'platform_routes':'unprobed','native_save_identity':'unknown','snapshot_atomic':False}
    try:
        r=client.request('station_lookup',p);record['observations'].append(r)
        if r['status']!='ok':raise live.LiveError(r['status'],r['result'].get('error','station lookup failed'))
        v=normalized_station(r['result']);record['station']=v
        if v.get('outcome')!='resolved' or v.get('complete') is not True:
            matches=v.get('matches',[]);summary.update(status=v.get('outcome','lookup_unavailable'),matches=matches[:8] if matches else [],match_count=len(matches))
            summary.update({k:v[k] for k in ('blocker','observation_limits','frozen_entity_count','processed_frozen_entities','frozen_TRACK_count','processed_station_nodes') if k in v});return summary
        ports=v['ports']
        if len(ports)>64 or len({q['node_id'] for q in ports})!=len(ports):raise ValueError('external port observation bound/duplicate identity')
        groups=mouth_groups(ports);record['mouth_groups']=groups
        for g in groups:
            # Small local tiles in front of observed mouths, at most8 total.
            for start in range(0,len(g['ports']),8):
                if len(record['sites'])>=8:raise live.LiveError('site_observation_bound','at most8 station-mouth site tiles')
                selected=g['ports'][start:start+8];depth=brief.get('survey_depth',100);d=g['direction']
                points=[[q['pos'][0]+d[0]*depth*f,q['pos'][1]+d[1]*depth*f] for q in (selected[0],selected[-1]) for f in (.1,.5,1)]
                region={'min':[min(x[k] for x in points)-5 for k in (0,1)]+[min(q['pos'][2] for q in selected)-100],
                        'max':[max(x[k] for x in points)+5 for k in (0,1)]+[max(q['pos'][2] for q in selected)+100]}
                if any(region['max'][k]-region['min'][k]>400 for k in range(3)):raise live.LiveError('site_observation_bound','observed mouth tile exceeds native400 bound')
                s=client.request('inspect',{'edge_ids':[q['edge_id'] for q in selected],'site':{'region':region,'positions':points}})
                record['sites'].append(s)
                if s['status']!='ok':raise live.LiveError(s['status'],s['result'].get('error','site read failed'))
        final=client.request('station_lookup',p);record['observations'].append(final)
        if client.session!=session or final.get('session',session)!=session or final['status']!='ok' or normalized_station(final['result'])!=v:raise live.LiveError('stale_station','station/external identities changed during survey')
        record['station_identity_rechecked']=True
        summary.update(status='ok',group_id=v['group_id'],constructions=[{'id':c['construction_id'],'position':c['position']} for c in v['constructions']],
            station_count=len(v['stations']),terminal_count=sum(s['terminal_count'] for s in v['stations']),free_connection_count=len(ports),
            ports=[{'node':q['node_id'],'edge':q['edge_id'],'xyz':q['pos']} for q in ports[:16]],port_summary_truncated=len(ports)>16,mouth_groups=len(groups),
            site_tiles=len(record['sites']),site_complete=bool(record['sites']) and all(s['result']['site']['truncated'] is False for s in record['sites']))
    except (live.LiveError,ValueError,KeyError,TypeError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:350])
    finally:record['summary']=summary;live.atomic_json(path,record)
    return summary
