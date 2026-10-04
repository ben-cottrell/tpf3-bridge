"""Bounded read-only native movement-set resources; no capacity or design inference."""
import itertools
import math
import re
import uuid
from pathlib import Path
import bridge_live as live


def _name(s):
    return isinstance(s,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',s)


def _hint(h,endpoint):
    keys={'region','max_edges','guide_xyz','position_tolerance'}
    if endpoint:keys|={'travel_direction','heading_tolerance_deg'}
    if not isinstance(h,dict) or set(h)!=keys:raise ValueError('bounded named observation hint required')
    live.validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':[0,0],'end_direction':[1,0],'radius':1,'region':h['region']})
    if any(h['region']['max'][k]-h['region']['min'][k]>400 for k in range(3)):raise ValueError('observation region exceeds400')
    if type(h['max_edges']) is not int or not 1<=h['max_edges']<=16:raise ValueError('max_edges must be1..16')
    p=h['guide_xyz'];t=h['position_tolerance']
    if not isinstance(p,list) or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):raise ValueError('finite XYZ hint required')
    if type(t) not in (int,float) or not math.isfinite(t) or not 0<t<=10:raise ValueError('position_tolerance must be within(0,10]')
    if endpoint:
        d=h['travel_direction'];a=h['heading_tolerance_deg']
        if not isinstance(d,list) or len(d)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in d) or math.hypot(*d)<1e-9:raise ValueError('nonzero finite XY heading required')
        if type(a) not in (int,float) or not math.isfinite(a) or not 0<=a<=180:raise ValueError('heading_tolerance_deg must be0..180')


def validate(brief):
    if not isinstance(brief,dict) or set(brief)!={'version','endpoints','junctions','movements','mode','max_length'} or brief['version']!=1:raise ValueError('version1 route-set brief required')
    if brief['mode'] not in ('TRAIN','ELECTRIC_TRAIN'):raise ValueError('supported native rail mode required')
    v=brief['max_length']
    if type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=8000:raise ValueError('max_length must be within(0,8000]')
    es,js,ms=brief['endpoints'],brief['junctions'],brief['movements']
    if not isinstance(es,dict) or not 2<=len(es)<=16 or not isinstance(js,dict) or len(js)>16 or set(es)&set(js):raise ValueError('2..16 endpoints and up to16 distinct junction hints required')
    for names,endpoint in ((es,True),(js,False)):
        for n,h in names.items():
            if not _name(n):raise ValueError('invalid semantic name')
            _hint(h,endpoint)
    if not isinstance(ms,list) or not 1<=len(ms)<=16:raise ValueError('1..16 explicit movements required')
    names=set()
    for m in ms:
        if not isinstance(m,dict) or set(m)-{'via'}!={'id','from','to'} or not _name(m['id']) or m['id'] in names or m['from'] not in es or m['to'] not in es or m['from']==m['to']:raise ValueError('unique named directed movement required')
        names.add(m['id']);via=m.get('via',[])
        if not isinstance(via,list) or any(not isinstance(n,str) or n not in js for n in via) or len(via)!=len(set(via)):raise ValueError('via requires distinct named junctions in intended order')
    return brief


def _endpoint(client,h):
    return live._select_throat_port(client,{k:v for k,v in h.items() if k!='position_tolerance'},tolerance=h['position_tolerance'],connected=True)


def _junction(client,h):
    r=live.discover(client,{k:h[k] for k in ('region','max_edges')});v=r.get('result',{})
    if r['status']!='ok' or v.get('complete') is not True:raise live.LiveError('discovery_incomplete','junction discovery incomplete')
    choices={c['node_id']:c for c in v['candidates'] if c.get('incident_count',0)>=3 and c.get('incidence_complete') is True and not c.get('incident_output_truncated') and math.dist(c['pos'],h['guide_xyz'])<=h['position_tolerance']}
    if len(choices)!=1:raise live.LiveError('ambiguous_junction' if choices else 'junction_unavailable','one current junction identity required')
    c=next(iter(choices.values()));return c,r['request_id']


def _transport_ref(v):
    if not isinstance(v,dict) or type(v.get('entity')) is not int or v['entity']<=0 or type(v.get('index')) is not int or v['index']<0:raise ValueError('exact transport identity missing')
    return v['entity'],v['index']


def _normalise(row,edges,incidence):
    """Never promote incomplete transport output to a complete physical path."""
    row.update(physical_tracks=[],non_TRACK_transport=[],junction_transitions=[],physical_nodes=[],complete=False,unknowns=[])
    r=row.get('response',{});v=r.get('result',{});path=v.get('path',[])
    if row.get('binding_error'):
        row['outcome']='endpoint_or_via_unavailable';return
    if r.get('status')!='ok':row['outcome']='native_route_error';row['unknowns'].append(r.get('error',v.get('error','native route failed')));return
    if v.get('native_path_found') is False:row['outcome']='no_native_path_returned';return
    row['outcome']='incomplete_or_unverified'
    try:
        previous=None;nodes=set();native_nodes=[]
        for item in path:
            ref=_transport_ref(item['edge']);a=_transport_ref(item['from']);z=_transport_ref(item['to'])
            if type(item.get('forward')) is not bool or type(item.get('confirmed_TRACK')) is not bool:raise ValueError('direction/TRACK qualification missing')
            if previous is not None and previous!=a:row['unknowns'].append('transport discontinuity')
            previous=z;native_nodes.extend([a[0],z[0]])
            if item['confirmed_TRACK']:
                e=edges.get(ref[0]);expected=([e['node0'],e['node1']] if item['forward'] else [e['node1'],e['node0']]) if e else None
                if not e or e.get('road_type')!='TRACK' or [a[0],z[0]]!=expected:raise ValueError('current physical TRACK correspondence unavailable')
                row['physical_tracks'].append({'edge_id':ref[0],'transport_index':ref[1],'forward':item['forward'],'from_node':a[0],'to_node':z[0]})
                nodes.update((a[0],z[0]))
            else:row['non_TRACK_transport'].append({'edge':item['edge'],'from':item['from'],'to':item['to'],'forward':item['forward']})
        row['physical_nodes']=sorted(nodes)
        # The engine exports turnout internal transport resources on the exact
        # BaseNode entity. Other entities remain opaque, even if two paths differ.
        for x in row['non_TRACK_transport']:
            owner=x['edge']['entity'];info=incidence.get(owner,{})
            x['classification']='junction_internal' if info.get('complete') and info.get('degree',0)>=3 else 'unresolved_transport_internal'
            if x['classification']!='junction_internal':row['unknowns'].append('unresolved non-TRACK transport entity '+str(owner))
        for left,right in zip(row['physical_tracks'],row['physical_tracks'][1:]):
            n=left['to_node']
            if n!=right['from_node']:row['unknowns'].append('physical TRACK sequence discontinuity');continue
            info=incidence.get(n,{})
            if info.get('complete') and info.get('degree',0)>=3:row['junction_transitions'].append({'node_id':n,'from_edge':left['edge_id'],'to_edge':right['edge_id'],'incident_edges':info['edges']})
            elif not info.get('complete'):row['unknowns'].append('junction incidence unavailable '+str(n))
        needed=row.get('via_nodes',[]);at=-1
        for n in needed:
            try:at=native_nodes.index(n,at+1)
            except ValueError:row['unknowns'].append('intended via missing/out of order '+str(n))
        bindings=row.get('bindings',{})
        if len(bindings)!=2 or any(c['node_id'] not in nodes for c in bindings.values()):row['unknowns'].append('named endpoint not in physical path')
        if row.get('stale_binding'):row['unknowns'].append('endpoint/via binding changed during observation')
        complete=v.get('requested_route_verified') is True and v.get('transport_continuous') is True and v.get('truncated') is False and v.get('path_count')==len(path) and len(path)>0 and not row['unknowns']
        row['complete']=complete;row['outcome']='verified_complete' if complete else row['outcome']
    except (KeyError,TypeError,ValueError) as exc:row['unknowns'].append(str(exc))


def assess_route_set(rows,edges,incidence):
    """Pure comparison of observed identities; no routing or signalling model."""
    for row in rows:_normalise(row,edges,incidence)
    pairs=[]
    for a,b in itertools.combinations(rows,2):
        ta,tb=a['physical_tracks'],b['physical_tracks'];ea={q['edge_id'] for q in ta};eb={q['edge_id'] for q in tb}
        shared=sorted(ea&eb);reverse=sorted({q['edge_id'] for q in ta for z in tb if q['edge_id']==z['edge_id'] and q['forward']!=z['forward']})
        nodes=set(a['physical_nodes'])&set(b['physical_nodes']);endsa={c['node_id'] for c in a.get('bindings',{}).values()};endsb={c['node_id'] for c in b.get('bindings',{}).values()}
        endpoints=sorted(endsa&endsb);junctions=sorted(n for n in nodes if incidence.get(n,{}).get('complete') and incidence[n].get('degree',0)>=3)
        internal_a={_transport_ref(x['edge']) for x in a['non_TRACK_transport']};internal_b={_transport_ref(x['edge']) for x in b['non_TRACK_transport']}
        internals=[{'entity':e,'index':i} for e,i in sorted(internal_a&internal_b)]
        shared_nodes=sorted(nodes)
        positive=bool(shared or shared_nodes or internals) and not (a.get('stale_binding') or b.get('stale_binding'))
        outcome='topology_overlap' if positive else 'topology_disjoint' if a['complete'] and b['complete'] else 'unknown'
        pairs.append({'a':a['id'],'b':b['id'],'result':outcome,'both_paths_complete':a['complete'] and b['complete'],'shared_TRACK_edges':shared,'opposite_traversal_edges':reverse,'shared_junction_nodes':junctions,'junction_classification_unknown_nodes':sorted(n for n in nodes if not incidence.get(n,{}).get('complete')),'shared_endpoint_nodes':endpoints,'shared_physical_nodes':shared_nodes,'shared_non_TRACK_transport':internals,'conflicts_outside_shared_graph':'unknown','simultaneous_operation':'unprobed'})
    return pairs


def _incidence(client,edges,record):
    nodes={}
    for e in edges.values():
        for k in (0,1):nodes[e['node'+str(k)]]=e['p'+str(k)]
    if len(nodes)>256:raise live.LiveError('observation_bound','route-set exceeds256 observed physical nodes')
    out={}
    for n,p in sorted(nodes.items()):
        q=live.discover(client,{'region':{'min':[v-.1 for v in p],'max':[v+.1 for v in p]},'max_edges':16});record['node_observations'].append(q)
        v=q.get('result',{});cs=[c for c in v.get('candidates',[]) if c.get('node_id')==n]
        sets={tuple(sorted(c['incident_edges'])) for c in cs if c.get('incidence_complete') is True and not c.get('incident_output_truncated')}
        complete=q['status']=='ok' and v.get('complete') is True and len(sets)==1 and len(cs)>0 and all(c.get('incidence_complete') is True and not c.get('incident_output_truncated') for c in cs)
        ids=list(next(iter(sets))) if complete else []
        out[n]={'complete':complete,'edges':ids,'degree':len(ids) if complete else None,'evidence_request':q.get('request_id')}
    extra=sorted({i for v in out.values() for i in v['edges']}-set(edges))
    if len(extra)+len(edges)>256:raise live.LiveError('observation_bound','route-set incidence exceeds256 TRACK observations')
    for i in range(0,len(extra),16):
        r=client.request('inspect',{'edge_ids':extra[i:i+16]});record['edge_observations'].append(r)
        if r['status']=='ok':edges.update({e['id']:e for e in r['result']['edges']})
    for n,v in out.items():
        if v['complete'] and any(i not in edges or edges[i].get('road_type')!='TRACK' or n not in (edges[i]['node0'],edges[i]['node1']) for i in v['edges']):v['complete']=False;v['degree']=None
    return out


def _matrix(rows,pairs):
    labels=[r['id'] for r in rows];lookup={(p['a'],p['b']):p for p in pairs}
    lines=['# Current movement-set topology','', 'O = observed shared graph resource; D = complete graph-disjoint paths; ? = unknown.', 'No simultaneous-operation, signalling, clearance or capacity claim.','', '| Movement | '+' | '.join(labels)+' |','| --- | '+' | '.join('---' for _ in labels)+' |']
    for a in labels:
        cells=[]
        for b in labels:
            p=lookup.get((a,b),lookup.get((b,a)));cells.append('—' if a==b else {'topology_overlap':'O','topology_disjoint':'D','unknown':'?'}[p['result']])
        lines.append('| '+a+' | '+' | '.join(cells)+' |')
    lines+=['','Exact current shared resources (full ordered paths and incidence evidence in JSON):','']
    for p in pairs:
        lines.append(f"- {p['a']} / {p['b']}: {p['result']}; TRACK {p['shared_TRACK_edges']}; reverse {p['opposite_traversal_edges']}; junctions {p['shared_junction_nodes']}; junction classification unknown {p['junction_classification_unknown_nodes']}; endpoints {p['shared_endpoint_nodes']}; physical nodes {p['shared_physical_nodes']}; non-TRACK {p['shared_non_TRACK_transport']}.")
    return '\n'.join(lines)+'\n'


def inspect_route_set(client,brief):
    validate(brief)
    path=client.evidence/(uuid.uuid4().hex+'.route_set.json');matrix=path.with_suffix('.md')
    record={'version':1,'epoch':'COMMITTED','session':client.session,'brief':brief,'bindings':{},'binding_errors':{},'junctions':{},'movements':[],'observations':[],'edge_observations':[],'node_observations':[],'operations':[]}
    try:
        for n,h in brief['endpoints'].items():
            try:c,rid=_endpoint(client,h);record['bindings'][n]=c;record['observations'].append(rid)
            except live.LiveError as exc:
                if exc.status not in ('no_eligible_candidates','ambiguous_attachment','discovery_incomplete','native_verification_failed'):raise
                record['binding_errors'][n]={'status':exc.status,'error':str(exc)}
        for n,h in brief['junctions'].items():
            try:c,rid=_junction(client,h);record['junctions'][n]=c;record['observations'].append(rid)
            except live.LiveError as exc:
                if exc.status not in ('discovery_incomplete','ambiguous_junction','junction_unavailable'):raise
                record['binding_errors'][n]={'status':exc.status,'error':str(exc)}
        for m in brief['movements']:
            row=m|{'bindings':{n:record['bindings'][n] for n in (m['from'],m['to']) if n in record['bindings']}}
            names=[m['from'],m['to'],*m.get('via',[])]
            if any(n in record['binding_errors'] for n in names):row['binding_error']={n:record['binding_errors'][n] for n in names if n in record['binding_errors']}
            else:
                a,z=(record['bindings'][m[k]] for k in ('from','to'));other=lambda c:c['edge_snapshot']['node1'] if c['node_id']==c['edge_snapshot']['node0'] else c['edge_snapshot']['node0']
                row['via_nodes']=[record['junctions'][n]['node_id'] for n in m.get('via',[])]
                q={'source_edge':a['edge_id'],'source_node':other(a),'target_edge':z['edge_id'],'target_node':other(z),'mode':brief['mode'],'max_length':brief['max_length'],'required_edges':sorted({a['edge_id'],z['edge_id']})}
                if a['edge_id']==z['edge_id']:q['single_edge']=True
                row['query']=q;row['response']=client.request('route',q)
            record['movements'].append(row);live.atomic_json(path,record)
        ids=sorted({x['edge']['entity'] for r in record['movements'] for x in r.get('response',{}).get('result',{}).get('path',[]) if x.get('confirmed_TRACK') is True})
        if len(ids)>256:raise live.LiveError('observation_bound','route-set exceeds256 TRACK observations')
        edges={}
        for i in range(0,len(ids),16):
            r=client.request('inspect',{'edge_ids':ids[i:i+16]});record['edge_observations'].append(r)
            if r['status']=='ok':edges.update({e['id']:e for e in r['result']['edges']})
        incidence=_incidence(client,edges,record);record['incidence']=incidence
        # Fresh binding recheck detects stale observations; no construction/replay.
        for n,h in {**brief['endpoints'],**brief['junctions']}.items():
            old=record['bindings'].get(n,record['junctions'].get(n))
            if old is None:continue
            try:
                c,rid=(_endpoint if n in brief['endpoints'] else _junction)(client,h);record['observations'].append(rid)
                if any(c.get(k)!=old.get(k) for k in ('node_id','edge_id','pos','edge_snapshot','incident_edges')):raise live.LiveError('stale_binding','native endpoint/via identity or geometry changed')
            except live.LiveError as exc:
                if exc.status not in ('no_eligible_candidates','ambiguous_attachment','discovery_incomplete','native_verification_failed','ambiguous_junction','junction_unavailable','stale_binding'):raise
                record.setdefault('stale_bindings',{})[n]={'status':exc.status,'error':str(exc)}
                for row in record['movements']:
                    if n in (row['from'],row['to'],*row.get('via',[])):row['stale_binding']=True
        pairs=assess_route_set(record['movements'],edges,incidence);record['pairs']=pairs
        matrix.write_text(_matrix(record['movements'],pairs),encoding='utf-8')
        counts={k:sum(p['result']==k for p in pairs) for k in ('topology_overlap','topology_disjoint','unknown')}
        summary={'status':'ok','operation':'route-set-inspect','game_constructed':False,'movements':len(record['movements']),'complete_paths':sum(r['complete'] for r in record['movements']),'pair_counts':counts,'evidence':str(path.resolve()),'matrix':str(matrix.resolve()),'reservation_availability':'unprobed','train_traversal':'unprobed','conflicts_outside_shared_graph':'unknown','capacity':'not_assessed','native_snapshot_atomic':False}
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:summary={'status':getattr(exc,'status','invalid_result'),'operation':'route-set-inspect','game_constructed':False,'error':str(exc)[:400],'evidence':str(path.resolve())}
    record['summary']=summary;live.atomic_json(path,record);return summary
