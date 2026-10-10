"""Read-only directed route review against freshly qualified station terminals."""
import math
import uuid
import bridge_live as live
import bridge_station as station

def review(client,registry,brief):
    if set(brief)-{'max_path_entries'}!={'name','revision','routes'} or not isinstance(brief['routes'],list) or not 1<=len(brief['routes'])<=8:
        raise ValueError('registry name/revision and1..8 directed station routes required')
    path_limit=brief.get('max_path_entries',256)
    if type(path_limit) is not int or not 1<=path_limit<=512:raise ValueError('explicit route path observation bound1..512 required')
    records={}
    def registered_record(name,revision):
        if name not in records:records[name]=registry.load(name)
        record=records[name]
        if record['revision']!=revision:raise ValueError('registry revision changed')
        return record
    registered_record(brief['name'],brief['revision'])
    session=client.session;surveys={};observations=[];rows=[];names=set()
    def endpoint(spec,source):
        if set(spec)-{'role','registry_name','registry_revision','guide_xyz','travel_direction','placement_tolerance','heading_tolerance_deg'}:raise ValueError('bounded explicit route endpoint required')
        pos=spec['guide_xyz'];direction=spec['travel_direction'];tol=spec.get('placement_tolerance',.15);heading=spec.get('heading_tolerance_deg',2)
        for vector,n in ((pos,3),(direction,2)):
            if not isinstance(vector,list) or len(vector)!=n or any(type(x) not in (int,float) or not math.isfinite(x) for x in vector):raise ValueError('finite explicit route vectors required')
        if math.hypot(*direction)==0 or type(tol) not in (int,float) or not 0<tol<=10 or type(heading) not in (int,float) or not 0<heading<=180:raise ValueError('bounded direction/location tolerances required')
        if 'role' not in spec:
            if 'registry_name' in spec or 'registry_revision' in spec:raise ValueError('endpoint registry requires a terminal role')
            outward=[(-1 if source else 1)*x for x in direction]
            intent={'region':{'min':[x-max(1,tol) for x in pos],'max':[x+max(1,tol) for x in pos]},'max_edges':16,
                    'guide_xyz':pos,'travel_direction':outward,'heading_tolerance_deg':heading,'placement_tolerance':tol}
            candidate,_=live._select_throat_port(client,intent,tolerance=tol)
            return {'edge':candidate['edge_id'],'node':candidate['node_id'],'travel_direction':direction,'qualification':'fresh_free_boundary'}
        registry_name=spec.get('registry_name',brief['name']);registry_revision=spec.get('registry_revision',brief['revision'])
        role=registered_record(registry_name,registry_revision)['roles'][spec['role']];selector=role['station'];terminal=selector.get('terminal_index')
        if type(terminal) is not int or not 1<=terminal<=64:raise ValueError('exact registered one-based terminal required')
        name=selector['name']
        if name not in surveys:
            response=client.request('station_lookup',station.parameters({'name':name,'lookup_scope':'identity_frozen'}));observations.append(response)
            v=station.normalized_station(response.get('result',{}))
            if response['status']!='ok' or v.get('complete') is not True or v.get('outcome')!='resolved' or v.get('lookup_scope')!='identity_frozen' or v.get('identity_complete') is not True or v.get('frozen_complete') is not True:raise live.LiveError('station_route_incomplete','complete scoped station identity/frozen observation required')
            surveys[name]=v
        v=surveys[name];cs=[c for c in v['constructions'] if c['resource']==selector['construction']['resource'] and c['position']==selector['construction']['position']]
        if len(cs)!=1:raise live.LiveError('ambiguous_station_route','registered construction not unique/current')
        cid=cs[0]['construction_id'];edges,nodes,components=station.frozen_components(v,cid)
        groups=[]
        for group in {tuple(sorted(group)) for group in components.values()}:
            matched=[m for m in station.terminal_component_matches(v,cid,group[0]) if m['terminal_index']==terminal]
            if matched:groups.append((group,matched))
        if len(groups)!=1 or len(groups[0][1])!=1:raise live.LiveError('ambiguous_station_route','terminal does not qualify exactly one station/frozen TRACK component')
        group=set(groups[0][0]);ends=[(nid,next(iter(ids))) for nid,ids in nodes.items() if len(ids)==1 and next(iter(ids)) in group]
        if not 1<=len(ends)<=16:raise live.LiveError('station_route_incomplete','bounded frozen-chain ends unavailable')
        response=client.request('inspect',{'edge_ids':sorted({eid for _,eid in ends})});observations.append(response)
        if response['status']!='ok':raise live.LiveError('station_route_incomplete','current exact frozen geometry unavailable')
        snapshots=response['result']['edges'];matches=[]
        for nid,eid in ends:
            current=[e for e in snapshots if e['id']==eid]
            if len(current)!=1 or current[0].get('road_type')!='TRACK':raise live.LiveError('station_route_incomplete','current TRACK edge missing/ambiguous')
            e=current[0]
            if {e['node0'],e['node1']}!={edges[eid]['node0'],edges[eid]['node1']}:raise live.LiveError('stale_station','frozen endpoint identity changed')
            at0=nid==e['node0'];xyz=e['p0'] if at0 else e['p1'];t=e['t0'] if at0 else e['t1']
            sign=(1 if at0 else -1)*(1 if source else -1);travel=[sign*x for x in t[:2]]
            norm=math.hypot(*travel)*math.hypot(*direction)
            if not norm:raise live.LiveError('station_route_incomplete','endpoint direction unavailable')
            if math.dist(xyz,pos)<=tol and sum(a*b for a,b in zip(travel,direction))/norm>=math.cos(math.radians(heading)):
                matches.append({'edge':eid,'node':nid,'travel_direction':direction,'qualification':'exact_registered_terminal_frozen_TRACK_component','terminal_index':terminal,'construction_id':cid,'registry_name':registry_name,'registry_revision':registry_revision})
        if len(matches)!=1:raise live.LiveError('ambiguous_station_route' if matches else 'station_route_endpoint_unavailable','qualified terminal endpoint/direction is not unique')
        return matches[0]
    for route in brief['routes']:
        if set(route)!={'name','purpose','source','target','max_length'} or route['purpose'] not in ('arrival','departure') or not isinstance(route['name'],str) or not 1<=len(route['name'])<=80 or route['name'] in names:raise ValueError('unique bounded named arrival/departure route required')
        names.add(route['name'])
        required='target' if route['purpose']=='arrival' else 'source'
        if 'role' not in route[required]:raise ValueError('arrival targets/departure starts at a registered terminal')
        a=endpoint(route['source'],True);b=endpoint(route['target'],False)
        response=live.route(client,{'source_edge':a['edge'],'source_node':a['node'],'target_edge':b['edge'],'target_node':b['node'],
                                    'mode':'TRAIN','max_length':route['max_length'],'max_path_entries':path_limit,'required_edges':list(dict.fromkeys([a['edge'],b['edge']]))})
        observations.append(response);value=response.get('result',{})
        count=value.get('path_count');complete=value.get('truncated') is False and type(count) is int and 0<count<=path_limit
        rows.append({'name':route['name'],'purpose':route['purpose'],'verified':response['status']=='ok' and value.get('requested_route_verified') is True and complete,
                     'source':a,'target':b,'status':response['status'],'reason':value.get('reason'),'length':value.get('total_path_length'),'request_id':response.get('request_id')})
        rows[-1].update(path_count=count,max_path_entries=path_limit,truncated=value.get('truncated','unknown'))
    for name,v in surveys.items():
        final=client.request('station_lookup',station.parameters({'name':name,'lookup_scope':'identity_frozen'}));observations.append(final)
        if final['status']!='ok' or station.normalized_station(final['result'])!=v or client.session!=session:raise live.LiveError('stale_station','station route review crossed changed state/session')
    path=client.evidence/(uuid.uuid4().hex+'.station_routes.json')
    live.atomic_json(path,{'brief':brief,'session':session,'routes':rows,'observations':observations,'game_constructed':False,'snapshot_atomic':False})
    return {'status':'ok' if all(r['verified'] for r in rows) else 'routes_unverified','routes':rows[:4],'route_count':len(rows),'summary_truncated':len(rows)>4,'session':session,'evidence':str(path),
            'game_constructed':False,'train_traversal':'unprobed','line_operation':'unprobed','snapshot_atomic':False}
