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
