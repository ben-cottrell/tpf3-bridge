"""Basic native station placement and bounded exact-identity survey."""
import math
import uuid
import bridge_live as live


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
    if not isinstance(brief,dict) or set(brief)-{'name','max_groups','max_external_edges','max_lead_distance','survey_depth'}:raise ValueError('bounded station survey brief required')
    if not isinstance(brief.get('name'),str) or not 1<=len(brief['name'].encode('utf-8'))<=120:raise ValueError('exact station name required')
    p={'name':brief['name'],'max_groups':brief.get('max_groups',256),'max_external_edges':brief.get('max_external_edges',64),'max_lead_distance':brief.get('max_lead_distance',800)}
    for k,limit in (('max_groups',256),('max_external_edges',64)):
        if type(p[k]) is not int or not 1<=p[k]<=limit:raise ValueError(k+' outside bounded domain')
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
        v=r['result'];record['station']=v
        if v.get('outcome')!='resolved' or v.get('complete') is not True:
            matches=v.get('matches',[]);summary.update(status=v.get('outcome','lookup_unavailable'),matches=matches[:8] if matches else [],match_count=len(matches));return summary
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
        if client.session!=session or final.get('session',session)!=session or final['status']!='ok' or final['result']!=v:raise live.LiveError('stale_station','station/external identities changed during survey')
        record['station_identity_rechecked']=True
        summary.update(status='ok',group_id=v['group_id'],constructions=[{'id':c['construction_id'],'position':c['position']} for c in v['constructions']],
            station_count=len(v['stations']),terminal_count=sum(s['terminal_count'] for s in v['stations']),free_connection_count=len(ports),
            ports=[{'node':q['node_id'],'edge':q['edge_id'],'xyz':q['pos']} for q in ports[:16]],port_summary_truncated=len(ports)>16,mouth_groups=len(groups),
            site_tiles=len(record['sites']),site_complete=all(s['result']['site']['truncated'] is False for s in record['sites']))
    except (live.LiveError,ValueError,KeyError,TypeError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:350])
    finally:record['summary']=summary;live.atomic_json(path,record)
    return summary
