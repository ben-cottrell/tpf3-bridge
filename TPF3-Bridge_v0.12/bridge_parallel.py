"""Bounded connected native reference/normal-offset pair; no Python curve fitter."""
import hashlib
import json
import math
from pathlib import Path
import uuid

import bridge_live as live

LAYOUT = 'native_offset_connection_v1'
ROLES = ('up_source', 'up_target', 'down_source', 'down_target')


def _common(brief):
    return {k:brief[k] for k in ('radius','region','max_route_length')} | {'vertical':{'max_grade':brief['max_grade']},'max_fit_attempts':1}


def _reference(brief):
    return _common(brief) | {'source':brief['ports']['up_source']['endpoint'],'target':brief['ports']['up_target']['endpoint'],'guides':brief['guides']}


def plan_paired_connection(brief):
    keys={'layout','ports','guides','side','spacing','spacing_tolerance','radius','max_grade','region','max_route_length','min_curved_length'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=LAYOUT:
        raise ValueError('explicit native_offset_connection_v1 brief required')
    if not isinstance(brief['ports'],dict) or set(brief['ports'])!=set(ROLES):
        raise ValueError('four explicit UP/DOWN source/target roles required')
    for role in brief['ports'].values():
        if not isinstance(role,dict) or set(role)!={'id','endpoint'} or not isinstance(role['id'],str) or not role['id']:
            raise ValueError('each role requires stable project ID and endpoint intent')
    if len({r['id'] for r in brief['ports'].values()})!=4:raise ValueError('four distinct project endpoint IDs required')
    for direction in ('up','down'):
        live.validate_project_brief(_common(brief)|{k:brief['ports'][direction+'_'+k]['endpoint'] for k in ('source','target')},corridor=True)
    if brief['side'] not in ('left','right') or brief['spacing']!=5 or type(brief['spacing']) not in (int,float):
        raise live.LiveError('unsupported_pair','initial domain is native nominal5 spacing with explicit side')
    tol=brief['spacing_tolerance']
    if type(tol) not in (int,float) or not math.isfinite(tol) or not 0<tol<=.1:raise ValueError('spacing tolerance within(0,.1] required')
    length=brief['min_curved_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 0<length<=3200:raise ValueError('finite positive curved section length <=3200 required')
    # Use existing corridor input validation without opening a native client.
    guides=brief['guides']
    with_guides=_reference(brief)
    # Same guide rules as connect_corridor, reached without executing its workflow.
    if not isinstance(guides,list) or not 1<=len(guides)<=3:raise ValueError('1â€“3 ordered native guides required')
    for g in guides:
        if not isinstance(g,dict) or set(g)!={'position','travel_direction','grade'}:raise ValueError('explicit guide position/direction/grade required')
        for k,n in (('position',3),('travel_direction',2)):
            if not isinstance(g[k],list) or len(g[k])!=n or any(type(v) not in (int,float) or not math.isfinite(v) for v in g[k]):raise ValueError('finite native guide coordinates required')
        if math.hypot(*g['travel_direction'])<1e-9 or type(g['grade']) not in (int,float) or g['grade']!=0:raise live.LiveError('unsupported_pair','level guides only')
        if any(not brief['region']['min'][i]<=g['position'][i]<=brief['region']['max'][i] for i in range(3)):raise ValueError('guide outside authorised region')
    height=brief['ports']['up_source']['endpoint']['guide_xyz'][2]
    if any(abs(p['endpoint']['guide_xyz'][2]-height)>.001 for p in brief['ports'].values()) or any(abs(g['position'][2]-height)>.001 for g in guides):
        raise live.LiveError('unsupported_pair','initial native offset connection is level; actual heights retained')
    signed=5*(1 if brief['side']=='left' else -1)
    for up,down in (('up_source','down_target'),('up_target','down_source')):
        a,z=(brief['ports'][r]['endpoint'] for r in (up,down));d=a['travel_direction'];n=math.hypot(*d);d=[x/n for x in d]
        other=z['travel_direction'];m=math.hypot(*other)
        if math.hypot(d[0]+other[0]/m,d[1]+other[1]/m)>1e-6:raise live.LiveError('unsupported_pair','explicit opposing travel directions required')
        expected=[a['guide_xyz'][0]-signed*d[1],a['guide_xyz'][1]+signed*d[0],height]
        if math.dist(expected,z['guide_xyz'])>.001:raise live.LiveError('unsupported_pair','compatible normal-offset endpoint pairs required; no splayed transitions in v1')
    plan={'version':1,'layout':LAYOUT,'brief':brief,'reference':with_guides,'signed_spacing':signed,'epoch':'DESIGN','game_constructed':False,
          'shared_section':'entire connector; native reference/offset correspondence','transitions':'none; compatible fixed normal-offset anchors','native_direction':'UP source to target; DOWN traffic reverses offset chain','continuous_clearance_proof':False}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_paired_connection(plan,directory):
    Path(directory).mkdir(parents=True,exist_ok=True);path=Path(directory)/(uuid.uuid4().hex+'.paired_plan.json')
    live.atomic_json(path,{'plan':plan})
    return {'status':'ok','operation':'paired-connection','stage':'plan','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}


def _ports(client,plan,record,*,connected=False):
    ports={}
    for name in ROLES:
        sign=1 if name.endswith('source') else -1
        c,rid=live._select_throat_port(client,plan['brief']['ports'][name]['endpoint'],tolerance=.5,outward_sign=sign,connected=connected)
        old=record.get('ports',{}).get(name)
        if old:
            if (c['edge_id'],c['node_id'])!=(old['edge_id'],old['node_id']):raise live.LiveError('stale_pair_attachment','exact named attachment changed: '+name)
            a,z=old['edge_snapshot'],c['edge_snapshot']
            if any(math.dist(a[k],z[k])>.001 for k in ('p0','p1','t0','t1')) or any(a[k]!=z[k] for k in ('template','style')):raise live.LiveError('stale_pair_attachment','attachment geometry/resource changed: '+name)
        if type(c.get('grade')) not in (int,float) or not math.isfinite(c['grade']) or abs(c['grade'])>1e-6:raise live.LiveError('unsupported_pair','actual endpoint grade must be level')
        ports[name]=c;record.setdefault('observations',[]).append(rid)
    if len({c['node_id'] for c in ports.values()})!=4 or len({c['edge_id'] for c in ports.values()})!=4:raise ValueError('four distinct actual attachments required')
    if not connected:record['ports']=ports
    record['current_ports']=ports
    return ports


def _read_chain(client,plan,record,name):
    saved=record['chains'][name];ids,nodes=saved['edges'],saved['nodes']
    if not 1<=len(ids)<=16 or len(set(ids))!=len(ids) or len(nodes)!=len(ids)+1:raise ValueError('bounded complete connector receipt required')
    response=client.request('inspect',{'edge_ids':ids,'resources':True,'geometry_constraints':{k:plan['brief'][k] for k in ('radius','max_grade','region')}})
    rows={e['id']:e for e in response.get('result',{}).get('edges',[])}
    if response['status']!='ok' or set(rows)!=set(ids) or any(rows[e]['road_type']!='TRACK' or [rows[e]['node0'],rows[e]['node1']]!=nodes[i:i+2] for i,e in enumerate(ids)):
        raise live.LiveError('stale_pair_connector','exact ordered current connector unavailable')
    record.setdefault('current_chains',{})[name]={'inspection':response,'edges':ids,'nodes':nodes}
    return [{'edge':rows[e],'forward':True} for e in ids]


def _verify(client,plan,record):
    ports=_ports(client,plan,record,connected=True);chains={}
    for name in ('UP','DOWN'):
        if name not in record.get('chains',{}):continue
        refs=_read_chain(client,plan,record,name);chains[name]=refs
        ids=record['chains'][name]['edges'];nodes=record['chains'][name]['nodes']
        start,end=('up_source','up_target') if name=='UP' else ('down_target','down_source')
        a,z=ports[start],ports[end]
        if nodes[0]!=a['node_id'] or nodes[-1]!=z['node_id']:raise live.LiveError('stale_pair_attachment','connector no longer meets exact named ports')
        for c,connector in ((a,ids[0]),(z,ids[-1])):
            if set(c.get('incident_edges',[]))!={c['edge_id'],connector} or c.get('incident_count')!=2:raise live.LiveError('native_verification_failed','exact degree-two connector attachment missing')
        source,target=(a,z) if name=='UP' else (z,a)
        def outer(c):
            e=c['edge_snapshot'];return e['node1'] if c['node_id']==e['node0'] else e['node0']
        r=live.route(client,{'source_edge':source['edge_id'],'source_node':outer(source),'target_edge':target['edge_id'],'target_node':outer(target),'mode':'TRAIN','max_length':plan['brief']['max_route_length'],'required_edges':[source['edge_id']]+ids+[target['edge_id']]})
        actual=[x['edge']['entity'] for x in r.get('result',{}).get('path',[]) if x.get('confirmed_TRACK')]
        wanted=[source['edge_id']]+(ids if name=='UP' else list(reversed(ids)))+[target['edge_id']]
        ok=r['status']=='ok' and r.get('result',{}).get('requested_route_verified') is True and actual==wanted
        record.setdefault('routes',[]).append({'direction':name,'verified':ok,'response':r})
        if not ok:raise live.LiveError('native_verification_failed','complete intended '+name+' native route unverified')
    if len(chains)<2:return {'final_pair_verified':False,'routes_verified':len(chains),'spacing_verified':False}
    p={'reference':chains['UP'],'adjacent':chains['DOWN'],'spacing':plan['signed_spacing'],'tolerance':plan['brief']['spacing_tolerance'],**{k:plan['brief'][k] for k in ('radius','max_grade','region')}}
    r=client.request('verify_adjacency',p);record['spacing_readback']=r;v=r.get('result',{})
    if r['status']!='ok' or v.get('sampled_verified') is not True or not v.get('correspondence') or v.get('curved_reference_chord_length',0)<plan['brief']['min_curved_length']:
        raise live.LiveError('native_verification_failed','substantial curved normal-offset correspondence not established')
    return {'final_pair_verified':True,'routes_verified':2,'spacing_verified':True,'spacing':abs(plan['signed_spacing']),
            'min_sampled_spacing':v['min_sampled_separation'],'max_sampled_spacing':v['max_sampled_separation'],
            'curved_reference_chord_length':v['curved_reference_chord_length'],'samples':v['samples'],'continuous_clearance_proof':False,'transitions':'none; compatible offset anchors'}


def _finish(record,exc=None):
    s=record['summary']
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_pair_verified=False)
    s['routes_verified']=sum(r['verified'] for r in record.get('routes',[]));s['route_lengths']={r['direction']:r['response']['result'].get('total_path_length') for r in record.get('routes',[]) if r['verified']}
    s['completed_connectors']=list(record.get('chains',{}));s['native_effect_history_complete']=False
    if 'recorded_prior_game_constructed' in record:s['recorded_prior_game_constructed']=record['recorded_prior_game_constructed']
    s['train_traversal']='unprobed';s['direction_enforcement']='not_provided'
    s['next_action']='none' if s['status']=='ok' else 'inspect_and_reconcile_no_automatic_replay'
    live.atomic_json(Path(s['evidence']),record);return s


def _recover_reference(client,plan,record,invocation):
    """Explicit current-state qualification of one reported corridor receipt mismatch."""
    old=live._load_layout_record(invocation)
    if old['plan']!=plan or old.get('chains'):raise ValueError('only matching pre-offset reference readback failure supported')
    operation=next(o['response'] for o in old['operations'] if o['name']=='reference')
    raw=json.loads(Path(operation['evidence']).read_text(encoding='utf-8-sig'))
    rid=raw['attempts'][-1]['request_id'];response=Path(operation['evidence']).parent/(rid+'.response.json')
    original=json.loads(response.read_text(encoding='utf-8-sig'));v=original.get('result',{})
    if original.get('operation')!='corridor' or original.get('status')!='mutation_unverified' or not v.get('error','').endswith('construction_receipt_incomplete') or not v.get('returned_edges'):
        raise live.LiveError('reconciliation_required','exact reported constructed reference mismatch required; no retry')
    if raw.get('brief')!=plan['reference'] or original.get('request_id')!=rid or original.get('session')!=operation.get('session'):
        raise live.LiveError('reconciliation_required','reported reference is not linked to this approved corridor')
    record['ports']=old['ports'];ports=_ports(client,plan,record,connected=True)
    if any(ports[k].get('eligible') is not True for k in ('down_source','down_target')):raise live.LiveError('reconciliation_required','uncompleted offset anchors not freshly free')
    a,z=ports['up_source'],ports['up_target']
    def outer(c):
        e=c['edge_snapshot'];return e['node1'] if c['node_id']==e['node0'] else e['node0']
    r=live.route(client,{'source_edge':a['edge_id'],'source_node':outer(a),'target_edge':z['edge_id'],'target_node':outer(z),'mode':'TRAIN','max_length':plan['brief']['max_route_length'],'required_edges':[a['edge_id'],z['edge_id']]})
    rows=r.get('result',{}).get('path',[])
    if r['status']!='ok' or r.get('result',{}).get('requested_route_verified') is not True or not rows or any(x.get('confirmed_TRACK') is not True or x.get('forward') is not True for x in rows):raise live.LiveError('reconciliation_required','ordinary current reference route not established')
    ids=[x['edge']['entity'] for x in rows]
    if ids[0]!=a['edge_id'] or ids[-1]!=z['edge_id'] or not 1<=len(ids)-2<=16 or not set(ids[1:-1])<=set(v['returned_edges']):raise live.LiveError('reconciliation_required','route must use exact reported connector identities')
    observed=client.request('inspect',{'edge_ids':ids[1:-1]});edges=observed.get('result',{}).get('edges',[])
    if observed['status']!='ok' or [e['id'] for e in edges]!=ids[1:-1]:raise live.LiveError('reconciliation_required','reported current chain unavailable')
    nodes=[edges[0]['node0']]+[e['node1'] for e in edges];record['chains']['UP']={'edges':ids[1:-1],'nodes':nodes}
    # Fresh geometry, exact incidence and the full route must pass before new writes.
    record['summary'].update(_verify(client,plan,record));record['routes']=[]
    record['continuation_of']=str(Path(invocation).resolve());record['recorded_prior_game_constructed']='unknown'
    record['reference_reconciliation']={'original_response':str(response.resolve()),'sha256':hashlib.sha256(response.read_bytes()).hexdigest(),
        'current_route':r,'unused_returned_entities':sorted(set(v['returned_edges'])-set(ids[1:-1])),
        'other_effects':'unknown','automatic_replay':False,'reference_current_verified':True}
    record['summary']['game_constructed']=True


def execute_paired_connection(client,plan,*,reference_record=None):
    if plan!=plan_paired_connection(plan['brief']):raise ValueError('paired plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.paired.json');lock=client.evidence/'paired.lock'
    record={'plan':plan,'chains':{},'routes':[],'operations':[],'summary':{'status':'incomplete','operation':'paired-connection','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise live.LiveError('client_busy','one paired workflow at a time') from None
    def perform(name,call):
        record['unfinished_step']=name;live.atomic_json(path,record)
        try:r=call()
        except Exception:
            record['summary']['game_constructed']='unknown'
            raise
        record['operations'].append({'name':name,'response':r})
        effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
        if effect in (True,'unknown') or record['summary']['game_constructed'] is not True:record['summary']['game_constructed']=effect
        if r['status']!='ok':raise live.LiveError(r['status'],r.get('error',r.get('result',{}).get('error','paired construction failed')))
        record.pop('unfinished_step');live.atomic_json(path,record);return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending native mutation; no replay')
        if reference_record:
            _recover_reference(client,plan,record,reference_record)
            ports=record['current_ports']
        else:
            ports=_ports(client,plan,record)
            up=perform('reference',lambda:live.connect_corridor(client,plan['reference'],execute=True))
            if up.get('selected')!={k:ports['up_'+n][v] for n in ('source','target') for k,v in ((n+'_edge','edge_id'),(n+'_node','node_id'))}:raise live.LiveError('stale_pair_attachment','reference selected different exact role')
            record['chains']['UP']={'edges':up['edges'],'nodes':up['nodes']}
        live.atomic_json(path,record)
        reference=_read_chain(client,plan,record,'UP')
        if any(e['edge'].get('resource',{}).get('track_distance')!=plan['brief']['spacing'] for e in reference):raise live.LiveError('unsupported_pair','selected spacing differs from native trackDistance')
        p={'reference':reference,'spacing':plan['signed_spacing'],'tolerance':plan['brief']['spacing_tolerance'],**{k:plan['brief'][k] for k in ('radius','max_grade','region')},'execute':True,
           'attachments':{side:{'anchor_edge':ports[role]['edge_id'],'anchor_node':ports[role]['node_id']} for side,role in (('source','down_target'),('target','down_source'))}}
        r=perform('offset',lambda:client.request('adjacent',p));rb=r['result']['readback'];live._require_engineering_readback(rb,{'radius':plan['brief']['radius'],'vertical':{'max_grade':plan['brief']['max_grade']}})
        record['chains']['DOWN']={'edges':rb['ordered_edges'],'nodes':rb['ordered_nodes']};live.atomic_json(path,record)
        record['summary'].update(_verify(client,plan,record),status='ok');return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)
    finally:lock.unlink()


def inspect_paired_connection(client,invocation):
    original=live._load_layout_record(invocation);plan=original['plan']
    if plan!=plan_paired_connection(plan['brief']):raise ValueError('saved paired plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.paired_inspection.json')
    record={'plan':plan,'ports':original.get('ports',{}),'chains':original.get('chains',{}),'routes':[],
            'recorded_prior_game_constructed':original.get('summary',{}).get('game_constructed','unknown'),
            'summary':{'status':'incomplete','operation':'paired-connection-inspect','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        record['summary'].update(_verify(client,plan,record));record['summary']['status']='ok' if record['summary']['final_pair_verified'] else 'pair_incomplete'
        return _finish(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish(record,exc)


MULTITRACK = 'native_multitrack_connection_v1'


def plan_multitrack_connection(brief):
    """Ordered level corridors, using the pair contract for every neighboring boundary."""
    keys={'layout','tracks','reference_up','guides','side','spacing','spacing_tolerance','radius','max_grade','region','max_route_length','min_curved_length'}
    if not isinstance(brief,dict) or set(brief)!=keys or brief['layout']!=MULTITRACK:raise ValueError('explicit multitrack connection brief required')
    tracks=brief['tracks']
    if brief['reference_up'] not in ('increasing','decreasing'):raise ValueError('explicit UP reference orientation required')
    if not isinstance(tracks,list) or len(tracks) not in (2,4):raise ValueError('two or four ordered tracks required')
    for t in tracks:
        if not isinstance(t,dict) or set(t)!={'id','direction','source','target'} or not isinstance(t['id'],str) or not t['id'] or t['direction'] not in ('UP','DOWN'):raise ValueError('explicit track identity/direction/endpoints required')
    if len({t['id'] for t in tracks})!=len(tracks):raise ValueError('unique track IDs required')
    pattern='-'.join(t['direction'] for t in tracks)
    if pattern not in ('UP-DOWN','UP-UP-DOWN-DOWN','UP-DOWN-UP-DOWN'):raise live.LiveError('unsupported_pattern','UD/UUDD/UDUD only')
    normalized=[];ports={}
    for t in tracks:
        forward=(t['direction']=='UP')==(brief['reference_up']=='increasing')
        for end in ('source','target'):
            r=t[end]
            if not isinstance(r,dict) or set(r)!={'id','endpoint'} or not isinstance(r['id'],str) or not r['id']:raise ValueError('explicit stable endpoint ID/intent required')
        live.validate_project_brief(_common(brief)|{k:t[k]['endpoint'] for k in ('source','target')},corridor=True)
        pair={}
        for end,role in zip(('start','end'),('source','target') if forward else ('target','source')):
            r=json.loads(json.dumps(t[role],allow_nan=False));e=r['endpoint']
            if not isinstance(e,dict) or not isinstance(e.get('travel_direction'),list) or len(e['travel_direction'])!=2:raise ValueError('endpoint travel direction required')
            if not forward:e['travel_direction']=[-v for v in e['travel_direction']]
            pair[end]=r;ports[r['id']]={'endpoint':e,'sign':1 if end=='start' else -1}
        normalized.append({'id':t['id'],'direction':t['direction'],'forward':forward,'start':pair['start']['id'],'end':pair['end']['id']})
    if len(ports)!=2*len(tracks):raise ValueError('all endpoint IDs must be distinct')
    common={k:brief[k] for k in keys-{'layout','tracks','reference_up'}}
    pairs=[]
    for a,z in zip(normalized,normalized[1:]):
        def role(key,reverse=False):
            endpoint=json.loads(json.dumps(ports[key]['endpoint'],allow_nan=False))
            if reverse:endpoint['travel_direction']=[-v for v in endpoint['travel_direction']]
            return {'id':key,'endpoint':endpoint}
        b=common|{'layout':LAYOUT,'ports':{'up_source':role(a['start']),'up_target':role(a['end']),
            'down_source':role(z['end'],True),'down_target':role(z['start'],True)}}
        pairs.append(plan_paired_connection(b))
    plan={'version':1,'layout':MULTITRACK,'brief':brief,'pattern':pattern,'tracks':normalized,'ports':ports,
          'reference':pairs[0]['reference'],'signed_spacing':pairs[0]['signed_spacing'],'epoch':'DESIGN','game_constructed':False,
          'order_convention':'successive selected normal side along increasing construction reference',
          'transitions':'none; compatible fixed normal-offset anchors','continuous_clearance_proof':False}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_multitrack_connection(plan,directory):
    if plan!=plan_multitrack_connection(plan['brief']):raise ValueError('multitrack plan changed')
    Path(directory).mkdir(parents=True,exist_ok=True);path=Path(directory)/(uuid.uuid4().hex+'.multitrack_plan.json')
    live.atomic_json(path,{'plan':plan})
    return {'status':'ok','operation':'multitrack-connection','stage':'plan','pattern':plan['pattern'],'game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}


def _multitrack_ports(client,plan,record,*,connected):
    ports={}
    for name,q in plan['ports'].items():
        c,rid=live._select_throat_port(client,q['endpoint'],tolerance=.5,outward_sign=q['sign'],connected=connected)
        old=record.get('ports',{}).get(name)
        if old:
            if (c['edge_id'],c['node_id'])!=(old['edge_id'],old['node_id']):raise live.LiveError('stale_attachment','exact named endpoint changed: '+name)
            a,z=old['edge_snapshot'],c['edge_snapshot']
            if any(math.dist(a[k],z[k])>.001 for k in ('p0','p1','t0','t1')) or any(a[k]!=z[k] for k in ('template','style')):raise live.LiveError('stale_attachment','endpoint geometry/resource changed: '+name)
        if type(c.get('grade')) not in (int,float) or not math.isfinite(c['grade']) or abs(c['grade'])>1e-6:raise live.LiveError('unsupported_multitrack','actual level endpoints required')
        ports[name]=c;record.setdefault('observations',[]).append(rid)
    if len({c['node_id'] for c in ports.values()})!=len(ports) or len({c['edge_id'] for c in ports.values()})!=len(ports):raise ValueError('distinct exact attachment nodes/edges required')
    record.setdefault('ports',ports);record['current_ports']=ports
    return ports


def _verify_multitrack(client,plan,record):
    if not set(record['chains'])<={t['id'] for t in plan['tracks']}:raise ValueError('unknown saved connector identity')
    ports=_multitrack_ports(client,plan,record,connected=True);chains={};seen=set();record['routes']=[];record['spacing_checks']=[]
    for t in plan['tracks']:
        name=t['id']
        if name not in record['chains']:continue
        refs=_read_chain(client,plan,record,name);chains[name]=refs
        for first,last in zip(refs,refs[1:]):
            a,z=first['edge']['t1'],last['edge']['t0'];n=math.hypot(*a[:2])*math.hypot(*z[:2])
            if n<=1e-12 or math.degrees(math.acos(max(-1,min(1,sum(a[k]*z[k] for k in range(2))/n))))>.1:raise live.LiveError('native_verification_failed','current connector heading join failed')
        ids=record['chains'][name]['edges'];nodes=record['chains'][name]['nodes']
        if seen.intersection(nodes) or len(set(nodes))!=len(nodes):raise live.LiveError('native_verification_failed','tracks share/repeat exact nodes')
        seen.update(nodes);a,z=ports[t['start']],ports[t['end']]
        if (nodes[0],nodes[-1])!=(a['node_id'],z['node_id']):raise live.LiveError('stale_attachment','chain does not meet named endpoints')
        for c,edge in ((a,ids[0]),(z,ids[-1])):
            if c.get('incident_count')!=2 or set(c.get('incident_edges',[]))!={c['edge_id'],edge}:raise live.LiveError('native_verification_failed','exact degree-two attachment missing')
        source,target=(a,z) if t['forward'] else (z,a)
        def outer(c):
            e=c['edge_snapshot'];return e['node1'] if c['node_id']==e['node0'] else e['node0']
        wanted=[source['edge_id']]+(ids if t['forward'] else ids[::-1])+[target['edge_id']]
        r=live.route(client,{'source_edge':source['edge_id'],'source_node':outer(source),'target_edge':target['edge_id'],'target_node':outer(target),
            'mode':'TRAIN','max_length':plan['brief']['max_route_length'],'required_edges':wanted})
        path=[x for x in r.get('result',{}).get('path',[]) if x.get('confirmed_TRACK')]
        ok=r['status']=='ok' and r.get('result',{}).get('requested_route_verified') is True and [x['edge']['entity'] for x in path]==wanted and all(x.get('forward') is t['forward'] for x in path[1:-1])
        record['routes'].append({'direction':name,'traffic':t['direction'],'forward':t['forward'],'verified':ok,'response':r})
        if not ok:raise live.LiveError('native_verification_failed','complete directional native route unverified: '+name)
    pairs=[(i-1,i,1,'neighbor') for i in range(1,len(plan['tracks']))]+[(0,i,i,'shared_reference') for i in range(2,len(plan['tracks']))]
    for a,z,m,kind in pairs:
        first,last=plan['tracks'][a]['id'],plan['tracks'][z]['id']
        if first not in chains or last not in chains:continue
        p={'reference':chains[first],'adjacent':chains[last],'spacing':m*plan['signed_spacing'],'tolerance':plan['brief']['spacing_tolerance'],**{k:plan['brief'][k] for k in ('radius','max_grade','region')}}
        r=client.request('verify_adjacency',p);v=r.get('result',{})
        good=r['status']=='ok' and v.get('sampled_verified') is True and bool(v.get('correspondence')) and v.get('curved_reference_chord_length',0)>=plan['brief']['min_curved_length']
        record['spacing_checks'].append({'from':first,'to':last,'kind':kind,'verified':good,'response':r})
        if not good:raise live.LiveError('native_verification_failed','normal spacing/shared reference drift unverified: '+first+'->'+last)
    full=len(chains)==len(plan['tracks']);neighbor=[x['response']['result'] for x in record['spacing_checks'] if x['kind']=='neighbor']
    return {'final_multitrack_verified':full,'routes_verified':len(chains),'tracks_verified':len(chains),'spacing_verified':full,
        'neighbor_pairs_verified':len(neighbor),'shared_reference_checks':sum(x['kind']=='shared_reference' for x in record['spacing_checks']),
        'min_sampled_spacing':min((x['min_sampled_separation'] for x in neighbor),default=None),'max_sampled_spacing':max((x['max_sampled_separation'] for x in neighbor),default=None),
        'curved_reference_chord_length':min((x['curved_reference_chord_length'] for x in neighbor),default=None),'continuous_clearance_proof':False}


def _finish_multitrack(record,exc=None):
    s=record['summary']
    if exc:s.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400],final_multitrack_verified=False)
    s['routes_verified']=sum(r['verified'] for r in record.get('routes',[]));s['route_lengths']={r['direction']:r['response']['result'].get('total_path_length') for r in record.get('routes',[]) if r['verified']}
    s['completed_connectors']=list(record['chains']);s['native_effect_history_complete']=False
    s['recorded_prior_game_constructed']=record.get('recorded_prior_game_constructed','unknown')
    s['direction_enforcement']='not_provided';s['train_traversal']='unprobed';s['next_action']='none' if s['status']=='ok' else 'inspect_and_reconcile_no_automatic_replay'
    live.atomic_json(Path(s['evidence']),record);return s


def execute_multitrack_connection(client,plan,*,continuation_record=None):
    if plan!=plan_multitrack_connection(plan['brief']):raise ValueError('multitrack plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.multitrack.json');lock=client.evidence/'paired.lock'
    record={'plan':plan,'chains':{},'routes':[],'operations':[],'summary':{'status':'incomplete','operation':'multitrack-connection','pattern':plan['pattern'],'game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise live.LiveError('client_busy','one native corridor workflow at a time') from None
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise live.LiveError('reconciliation_required','pending native mutation; no replay')
        if continuation_record:
            old=live._load_layout_record(continuation_record)
            if old['plan']!=plan or old.get('unfinished_step') or old['summary'].get('game_constructed') is not True:raise live.LiveError('reconciliation_required','only exact acknowledged completed prefix may continue')
            names=[t['id'] for t in plan['tracks']];done=set(old['chains'])
            if done!=set(names[:len(done)]) or not done or len(done)==len(names):raise ValueError('strict incomplete ordered prefix required')
            record.update(ports=old['ports'],chains=old['chains'],continuation_of=str(Path(continuation_record).resolve()),recorded_prior_game_constructed=old['summary']['game_constructed'])
            _verify_multitrack(client,plan,record);record['summary']['game_constructed']=True
        ports=_multitrack_ports(client,plan,record,connected=bool(record['chains']))
        for i,t in enumerate(plan['tracks']):
            name=t['id']
            if name in record['chains']:continue
            if any(ports[t[k]].get('eligible') is not True for k in ('start','end')):raise live.LiveError('reconciliation_required','unbuilt endpoints not freshly free')
            if i:
                refs=_read_chain(client,plan,record,plan['tracks'][i-1]['id'])
                if any(e['edge'].get('resource',{}).get('track_distance')!=plan['brief']['spacing'] for e in refs):raise live.LiveError('unsupported_multitrack','native trackDistance mismatch')
                p={'reference':refs,'spacing':plan['signed_spacing'],'tolerance':plan['brief']['spacing_tolerance'],**{k:plan['brief'][k] for k in ('radius','max_grade','region')},'execute':True,
                   'attachments':{side:{'anchor_edge':ports[t[k]]['edge_id'],'anchor_node':ports[t[k]]['node_id']} for side,k in (('source','start'),('target','end'))}}
            record['unfinished_step']=name;live.atomic_json(path,record)
            try:r=live.connect_corridor(client,plan['reference'],execute=True) if not i else client.request('adjacent',p)
            except Exception:
                record['summary']['game_constructed']='unknown';raise
            record['operations'].append({'name':name,'response':r});effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
            if effect in (True,'unknown') or record['summary']['game_constructed'] is not True:record['summary']['game_constructed']=effect
            if r['status']!='ok':raise live.LiveError(r['status'],r.get('error',r.get('result',{}).get('error','construction failed')))
            if not i:
                selected={k:ports[t[n]][v] for n in ('start','end') for k,v in ((('source' if n=='start' else 'target')+'_edge','edge_id'),(('source' if n=='start' else 'target')+'_node','node_id'))}
                if r.get('selected')!=selected:raise live.LiveError('stale_attachment','reference selected different endpoints')
                chain={'edges':r['edges'],'nodes':r['nodes']}
            else:
                rb=r['result']['readback'];live._require_engineering_readback(rb,{'radius':plan['brief']['radius'],'vertical':{'max_grade':plan['brief']['max_grade']}})
                chain={'edges':rb['ordered_edges'],'nodes':rb['ordered_nodes']}
            record['chains'][name]=chain;record.pop('unfinished_step');live.atomic_json(path,record)
            record['summary'].update(_verify_multitrack(client,plan,record));live.atomic_json(path,record)
        record['summary'].update(status='ok');return _finish_multitrack(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish_multitrack(record,exc)
    finally:lock.unlink()


def inspect_multitrack_connection(client,invocation):
    original=live._load_layout_record(invocation);plan=original['plan']
    if plan!=plan_multitrack_connection(plan['brief']):raise ValueError('saved multitrack plan changed')
    path=client.evidence/(uuid.uuid4().hex+'.multitrack_inspection.json')
    record={'plan':plan,'ports':original.get('ports',{}),'chains':original.get('chains',{}),'routes':[],
        'recorded_prior_game_constructed':original.get('summary',{}).get('game_constructed','unknown'),
        'summary':{'status':'incomplete','operation':'multitrack-connection-inspect','pattern':plan['pattern'],'game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve())}}
    try:
        s=_verify_multitrack(client,plan,record);record['summary'].update(s,status='ok' if s['final_multitrack_verified'] else 'multitrack_incomplete')
        return _finish_multitrack(record)
    except (live.LiveError,OSError,ValueError,KeyError,TypeError) as exc:return _finish_multitrack(record,exc)
