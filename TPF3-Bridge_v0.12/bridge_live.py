"""Development live client: data-only mod modules in, correlated game-log JSON out.

No model calls, UI automation, game launch, service, or mutation retry.
The mod must already be active in a healthy test world.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

MARKER = 'TPF3_BRIDGE_LIVE_RESPONSE '
OPERATIONS = {'inspect', 'fit', 'build', 'readback', 'extension', 'connection', 'test_approach', 'route', 'discover', 'discover_junction', 'discover_interior', 'verify_interior', 'verify_crossover', 'remove_branch', 'crossover', 'adjacent', 'verify_adjacency', 'junction', 'interior_junction', 'selected_connection', 'corridor'}

def is_mutation(operation, params):
    return operation in ('build', 'test_approach', 'remove_branch') or (operation in ('extension', 'connection', 'selected_connection', 'corridor', 'junction', 'interior_junction', 'crossover', 'adjacent') and params.get('execute') is True)

def discover_session(log_path):
    """Read transport markers locally; a later request must still prove responsiveness."""
    ready = None
    confirmed = None
    with Path(log_path).open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            for kind in ('READY', 'SESSION'):
                marker = 'TPF3_BRIDGE_LIVE_' + kind + ' '
                if marker not in line:
                    continue
                try:
                    value = json.loads(line.split(marker, 1)[1])
                except ValueError:
                    continue
                if not isinstance(value, dict):
                    continue
                if kind == 'READY':
                    ready = value
                    confirmed = None
                elif ready and value.get('session') == ready.get('session') and value.get('ready') is True:
                    confirmed = value['session']
    if not ready or not confirmed or ready.get('version') != 1:
        raise LiveError('adapter_handshake_unavailable', 'latest adapter READY has no matching SESSION handshake')
    return confirmed

def client_from_context(context_path, timeout=30):
    """Context contains installation paths, never a remembered native entity mapping."""
    context_path = Path(context_path).resolve()
    context = json.loads(context_path.read_text(encoding='utf-8-sig'))
    def location(key):
        path = Path(context[key])
        return path if path.is_absolute() else context_path.parent / path
    mod, log, root = location('mod_directory'), location('log'), location('session_evidence_root')
    session = discover_session(log)
    return LiveClient(mod, log, root / session, session, timeout, require_ack=True)

def validate_brief(brief):
    if not isinstance(brief, dict):
        raise ValueError('extension brief must be an object')
    keys = {'anchor_edge', 'anchor_node', 'end_xy', 'end_direction', 'radius', 'region'}
    if set(brief) - {'vertical'} != keys:
        raise ValueError('extension brief requires only ' + ', '.join(sorted(keys)))
    for key in ('anchor_edge', 'anchor_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    for key in ('end_xy', 'end_direction'):
        value = brief[key]
        if not isinstance(value, list) or len(value) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
            raise ValueError(key + ' must contain two finite native-coordinate values')
    if math.hypot(*brief['end_direction']) < 1e-9:
        raise ValueError('end_direction must be nonzero')
    if type(brief['radius']) not in (int, float) or not math.isfinite(brief['radius']) or brief['radius'] <= 0:
        raise ValueError('radius must be finite and positive')
    region = brief['region']
    if not isinstance(region, dict) or set(region) != {'min', 'max'}:
        raise ValueError('region requires min/max native XYZ coordinates')
    for key in ('min', 'max'):
        if not isinstance(region[key], list) or len(region[key]) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in region[key]):
            raise ValueError('region requires finite XYZ bounds')
    if any(region['min'][i] >= region['max'][i] for i in range(3)):
        raise ValueError('region bounds must be ordered')
    if 'vertical' in brief:
        validate_vertical(brief['vertical'], endpoint=True)
    return brief

def validate_vertical(value, *, endpoint=False):
    keys={'max_grade'} | ({'end_height','end_grade'} if endpoint else set())
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError('vertical requires only '+', '.join(sorted(keys)))
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in value.values()):
        raise ValueError('vertical values must be finite numbers')
    if value['max_grade']<=0:
        raise ValueError('vertical max_grade must be positive')
    if endpoint and abs(value['end_grade'])>value['max_grade']:
        raise ValueError('end_grade exceeds selected max_grade')

def extend(client, brief, *, execute=False):
    """One inspect/fit/(explicit build)/fresh-readback job; never retry a mutation."""
    validate_brief(brief)
    return _workflow(client, brief, execute, 'extension')

def validate_connection_brief(brief):
    keys = {'anchor_edge', 'anchor_node', 'target_edge', 'target_node', 'radius', 'region'}
    if not isinstance(brief, dict) or set(brief) - {'vertical'} != keys:
        raise ValueError('connection brief requires only ' + ', '.join(sorted(keys)))
    for key in ('target_edge', 'target_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    validate_brief({k:brief[k] for k in ('anchor_edge', 'anchor_node', 'radius', 'region')} |
                   {'end_xy':[0, 0], 'end_direction':[1, 0]})
    if brief['anchor_node'] == brief['target_node'] or brief['anchor_edge'] == brief['target_edge']:
        raise ValueError('connection requires distinct source and target attachments')
    if 'vertical' in brief:
        validate_vertical(brief['vertical'])
    return brief

def connect(client, brief, *, execute=False):
    """Connect two existing exact TRACK endpoint nodes; native geometry owns fitting."""
    validate_connection_brief(brief)
    return _workflow(client, brief, execute, 'connection')

def discover(client, brief, *, junction=False):
    """Bounded native TRACK discovery, with complete per-node incidence checks."""
    if not isinstance(brief, dict) or set(brief) != {'region', 'max_edges'}:
        raise ValueError('discovery requires region and max_edges')
    validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':[0,0],
                    'end_direction':[1,0],'radius':1,'region':brief['region']})
    if any(brief['region']['max'][i]-brief['region']['min'][i] > 400 for i in range(3)):
        raise ValueError('discovery region spans at most400 native units per axis')
    if type(brief['max_edges']) is not int or not 1 <= brief['max_edges'] <= 16:
        raise ValueError('discovery max_edges must be within1–16')
    return client.request('discover_junction' if junction else 'discover', brief)

def connect_selected(client, discovery, brief):
    """Select two recorded free endpoints; reacquire natively and fit only."""
    return client.request('selected_connection', _selected_parameters(client, discovery, brief))

def _selected_parameters(client, discovery, brief, *, junction=False):
    if not isinstance(brief, dict) or set(brief) - {'vertical'} != {'source_ref','target_ref','radius','region'}:
        raise ValueError('selection requires source_ref, target_ref, radius and region')
    records=discovery if isinstance(discovery,list) else [discovery]
    if not 1<=len(records)<=2:raise ValueError('selection accepts one or two local discoveries')
    candidates=[];request_ids=[]
    for record in records:
        if (not isinstance(record,dict) or record.get('status')!='ok' or record.get('operation') not in ({'discover','discover_junction'} if junction else {'discover'})
                or record.get('session')!=client.session):
            raise ValueError('selection requires successful current-session discoveries')
        rows=record.get('result',{}).get('candidates',[])
        if rows=={}:rows=[] # Empty Lua array uses existing object encoding.
        if not isinstance(rows,list) or any(not isinstance(c,dict) for c in rows):raise ValueError('invalid discovery candidates')
        candidates.extend(rows);request_ids.append(record['request_id'])
    if len(set(request_ids))!=len(request_ids):raise ValueError('duplicate discovery records')
    selected=[]
    for key in ('source_ref','target_ref'):
        matches=[c for c in candidates if c.get('ref')==brief[key]]
        if len(matches)!=1:raise ValueError('candidate reference missing or ambiguous')
        c=matches[0]
        if junction and key=='source_ref':
            if (c.get('junction_eligible') is not True or c.get('incidence_complete') is not True or c.get('incident_output_truncated') is True
                    or c.get('incident_count')!=2 or c.get('through_edge')==c.get('edge_id')
                    or set(c.get('incident_edges',[]))!={c.get('edge_id'),c.get('through_edge')}
                    or not isinstance(c.get('through_snapshot'),dict) or c['through_snapshot'].get('id')!=c.get('through_edge')):
                raise ValueError('candidate is not a fully verified through attachment')
        elif (c.get('eligible') is not True or c.get('incidence_complete') is not True
                or c.get('incident_count')!=1 or c.get('incident_edges')!=[c.get('edge_id')]):
            raise ValueError('candidate is not a fully verified free endpoint')
        if not isinstance(c.get('edge_snapshot'),dict):raise ValueError('candidate snapshot missing')
        selected.append(c)
    source,target=selected
    vertical={'vertical':brief['vertical']} if 'vertical' in brief else {}
    validate_connection_brief({'anchor_edge':source['edge_id'],'anchor_node':source['node_id'],
        'target_edge':target['edge_id'],'target_node':target['node_id'],'radius':brief['radius'],'region':brief['region'],**vertical})
    return {'source':source,'target':target,
        'radius':brief['radius'],'region':brief['region'],'discovery_request':request_ids[0],
        'discovery_requests':request_ids,**vertical}

def validate_project_brief(brief, *, corridor=False):
    keys={'source','target','radius','region','vertical','max_fit_attempts','max_route_length'}
    if not isinstance(brief,dict) or set(brief)!=keys:
        raise ValueError('connection project requires only '+', '.join(sorted(keys)))
    validate_connection_brief({'anchor_edge':1,'anchor_node':2,'target_edge':3,'target_node':4,
                              'radius':brief['radius'],'region':brief['region'],'vertical':brief['vertical']})
    bound=3000 if corridor else 1000
    if any(brief['region']['max'][i]-brief['region']['min'][i]>bound for i in range(2)):
        raise ValueError(f'connection region spans at most{bound} native XY units per axis')
    if type(brief['max_fit_attempts']) is not int or not 1<=brief['max_fit_attempts']<=16:
        raise ValueError('max_fit_attempts must be within1–16')
    route_bound=4000 if corridor else 800
    if type(brief['max_route_length']) not in (int,float) or not math.isfinite(brief['max_route_length']) or not 0<brief['max_route_length']<=route_bound:
        raise ValueError(f'max_route_length must be within(0,{route_bound}] native units')
    for name in ('source','target'):
        value=brief[name]
        if not isinstance(value,dict) or set(value)!={'region','max_edges','guide_xyz','travel_direction','heading_tolerance_deg'}:
            raise ValueError(name+' requires region/max_edges/guide_xyz/travel_direction/heading_tolerance_deg')
        # Reuse discovery bounds without sending a request.
        validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':[0,0],'end_direction':[1,0],'radius':1,'region':value['region']})
        if any(value['region']['max'][i]-value['region']['min'][i]>400 for i in range(3)):
            raise ValueError('search region spans at most400 native units per axis')
        if type(value['max_edges']) is not int or not 1<=value['max_edges']<=16:
            raise ValueError('max_edges must be within1–16')
        for key,count in (('guide_xyz',3),('travel_direction',2)):
            if not isinstance(value[key],list) or len(value[key])!=count or any(type(x) not in (int,float) or not math.isfinite(x) for x in value[key]):
                raise ValueError(key+' requires finite coordinates')
        if math.hypot(*value['travel_direction'])<1e-9:
            raise ValueError('travel_direction must be nonzero')
        tolerance=value['heading_tolerance_deg']
        if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<=tolerance<=180:
            raise ValueError('heading_tolerance_deg must be within0–180')
    return brief

def connect_brief(client, brief, *, execute=False):
    """Bounded discovery, deterministic selection, native build and route acceptance."""
    validate_project_brief(brief)
    return _connect_project(client,brief,execute)

def connect_junction(client, brief, *, execute=False):
    """Explicit two-edge through attachment to free branch target; native movement proof."""
    validate_project_brief(brief)
    return _connect_project(client,brief,execute,junction=True)

def connect_junction_at(client, brief, *, execute=False, junction_nodes=None):
    """Native interior placement and coherent through replacement/branch construction."""
    if not isinstance(brief,dict) or 'placement_tolerance' not in brief:
        raise ValueError('interior placement requires explicit placement_tolerance')
    tolerance=brief['placement_tolerance']
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<tolerance<=10:
        raise ValueError('placement_tolerance must be within(0,10] native units')
    validate_project_brief({k:v for k,v in brief.items() if k!='placement_tolerance'},corridor=junction_nodes is not None)
    return _connect_project(client,brief,execute,junction=True,interior=True,junction_nodes=junction_nodes)

def connect_corridor(client, brief, *, execute=False):
    """Native-fitted ordered guide legs, one coherent build, exact joins and route."""
    if not isinstance(brief,dict) or 'guides' not in brief:
        raise ValueError('corridor requires ordered guides')
    base={k:v for k,v in brief.items() if k!='guides'}
    validate_project_brief(base,corridor=True)
    guides=brief['guides']
    if not isinstance(guides,list) or not 1<=len(guides)<=3:
        raise ValueError('corridor requires1–3 ordered intermediate guides')
    for guide in guides:
        if not isinstance(guide,dict) or set(guide)!={'position','travel_direction','grade'}:
            raise ValueError('guide requires position, travel_direction and grade')
        for key,n in (('position',3),('travel_direction',2)):
            v=guide[key]
            if not isinstance(v,list) or len(v)!=n or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):
                raise ValueError('guide '+key+' must be finite native coordinates')
        if math.hypot(*guide['travel_direction'])<1e-9:
            raise ValueError('guide direction must be nonzero')
        g=guide['grade']
        if type(g) not in (int,float) or not math.isfinite(g) or abs(g)>brief['vertical']['max_grade']:
            raise ValueError('guide grade exceeds selected limit')
        if any(not brief['region']['min'][i]<=guide['position'][i]<=brief['region']['max'][i] for i in range(3)):
            raise ValueError('guide outside authorised region')
    return _connect_project(client,base,execute,guides)

def _connect_project(client, brief, execute, guides=None, *, junction=False, interior=False, junction_nodes=None):
    if type(execute) is not bool:raise ValueError('execute must be boolean')
    job=uuid.uuid4().hex;path=client.evidence/(job+'.workflow.json')
    summary={'status':'incomplete','job_id':job,'session':client.session,'operation':'connect-junction-at' if interior else ('connect-junction' if junction else ('connect-corridor' if guides else 'connect-brief')),
             'execute':execute,'game_constructed':False,'stage':'discover','evidence':str(path.resolve()),
             'attempt_count':0,'train_traversal':'unprobed'}
    record={'summary':summary,'brief':brief|({'guides':guides} if guides else {}),'discoveries':[],'attempts':[]}
    lock=client.evidence/'workflow.lock'
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one railway workflow at a time') from None
    try:
        if execute and client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):
            raise LiveError('reconciliation_required','unfinished current-session request; no construction permitted')
        atomic_json(path,record)
        records=[];choices=[]
        for name in ('source','target'):
            intent=brief[name]
            if interior and name=='source':
                found=client.request('discover_interior',intent|{'placement_tolerance':brief['placement_tolerance']})
            else:found=discover(client,{k:intent[k] for k in ('region','max_edges')},junction=junction and name=='source')
            record['discoveries'].append(found['request_id']);records.append(found)
            if found['status']!='ok':
                summary.update(status=found['status'],error=found.get('result',{}).get('error','discovery_failed'));return summary
            ranked=[];direction=intent['travel_direction'];size=math.hypot(*direction)
            for c in found['result']['candidates']:
                eligible=c.get('interior_eligible') if interior and name=='source' else (c.get('junction_eligible') if junction and name=='source' else c.get('eligible'))
                if eligible is not True or (not (interior and name=='source') and c.get('incidence_complete') is not True):continue
                actual=c['outward_direction'];sign=1 if name=='source' else -1
                dot=sign*(actual[0]*direction[0]+actual[1]*direction[1])/size
                heading=math.degrees(math.acos(max(-1,min(1,dot))))
                if heading>intent['heading_tolerance_deg']:continue
                distance=sum((c['pos'][i]-intent['guide_xyz'][i])**2 for i in range(3))
                ranked.append((distance,heading,c))
            choices.append(ranked)
        summary['discovery_complete']=all(r['result'].get('complete') is True for r in records)
        summary['eligible_counts']=[len(x) for x in choices]
        pairs=[(a[0]+b[0],a[1]+b[1],a[2],b[2]) for a in choices[0] for b in choices[1]
               if a[2]['edge_id']!=b[2]['edge_id'] and a[2].get('node_id')!=b[2]['node_id']]
        pairs.sort(key=lambda p:(p[0],p[1],p[2]['edge_id'],p[2].get('node_id',-1),p[3]['edge_id'],p[3]['node_id']))
        if not pairs:summary.update(status='no_eligible_candidates');return summary
        summary['stage']='select'
        for _,_,source,target in pairs[:brief['max_fit_attempts']]:
            selection={k:brief[k] for k in ('radius','region','vertical')}
            selection.update(source_ref=source['ref'],target_ref=target['ref'])
            if interior:
                if records[0].get('operation')!='discover_interior' or records[0].get('session')!=client.session:
                    raise ValueError('interior selection requires current-session native discovery')
                if source.get('interior_eligible') is not True or not .05<=source.get('parameter',-1)<=.95 or not isinstance(source.get('edge_snapshot'),dict) or source['edge_snapshot'].get('id')!=source['edge_id']:
                    raise ValueError('invalid recorded interior attachment')
                # Keep the target free-end contract; native execution reacquires both.
                if target.get('eligible') is not True or target.get('incidence_complete') is not True or target.get('incident_count')!=1 or target.get('incident_edges')!=[target['edge_id']] or not isinstance(target.get('edge_snapshot'),dict):
                    raise ValueError('candidate is not a fully verified free endpoint')
                params={k:brief[k] for k in ('radius','region','vertical')}
                params.update(source=source,target=target,location=brief['source']|{'placement_tolerance':brief['placement_tolerance']},execute=execute,junction_nodes=junction_nodes or [])
            else:
                params=_selected_parameters(client,records,selection,junction=junction);params['execute']=execute
            if junction:params['max_route_length']=brief['max_route_length']
            if guides:params['guides']=guides
            summary['stage']='native_connection'
            response=client.request('interior_junction' if interior else ('junction' if junction else ('corridor' if guides else 'selected_connection')),params)
            result=response.get('result',{})
            record['attempts'].append({'request_id':response['request_id'],'source_ref':source['ref'],
                'target_ref':target['ref'],'status':response['status'],'stage':result.get('stage'),
                'error':result.get('error'),'reason_class':result.get('reason_class')})
            summary['attempt_count']=len(record['attempts']);atomic_json(path,record)
            if response['status']!='ok':
                # Only explicit pre-build fitting rejection may try another pair.
                if response['status']=='error' and result.get('stage')=='fit' and result.get('game_constructed') is False:
                    continue
                summary.update(status=response['status'],error=result.get('error','native_operation_failed'),
                               game_constructed=result.get('game_constructed','unknown' if execute else False));return summary
            summary.update(selected={'source_edge':source['edge_id'],'source_node':source.get('node_id'),
                                     'target_edge':target['edge_id'],'target_node':target['node_id']},
                           native_request_id=response['request_id'],game_constructed=result.get('game_constructed',False),
                           fit={k:result.get('fit',{}).get(k) for k in ('pieces','total_length','radius','grade','end_grade','max_grade','max_sampled_grade','sampled_XY_error','sampled_Z_error','sampled_only','native_orientation')})
            if guides:
                summary['legs']=result.get('fit',{}).get('legs',[])
                summary['guide_nodes_realised']=False
            if junction:
                summary['fit']['requested_min_radius']=result.get('fit',{}).get('requested_min_radius')
                if result.get('through_before',{}).get('requested_route_verified') is not True:
                    summary.update(status='native_verification_failed',error='existing through movement not established');return summary
                summary['through_before_verified']=True
            if interior and not execute:
                summary['proposed_placement']={k:result.get('placement',{}).get(k) for k in ('original_edge','parameter','position','subdivision_sampled_verified')}
            if not execute:summary.update(status='ok',stage='fit');return summary
            if interior:
                placement=result.get('placement',{});incoming=placement.get('incoming',{});through=placement.get('through',{})
                if (placement.get('original_edge')!=source['edge_id'] or placement.get('original_removed') is not True
                        or placement.get('subdivision_sampled_verified') is not True or len(set(placement.get('replacement_edges',[])))!=2
                        or {incoming.get('id'),through.get('id')}!=set(placement['replacement_edges'])
                        or incoming.get('id')==source['edge_id'] or through.get('id')==source['edge_id']
                        or placement.get('original_nodes')!=[source['edge_snapshot']['node0'],source['edge_snapshot']['node1']]
                        or placement.get('junction_node') in placement['original_nodes']):
                    summary.update(status='native_verification_failed',error='native split identity/through geometry not established',game_constructed=True);return summary
                summary['placement']={k:placement.get(k) for k in ('original_edge','original_nodes','parameter','position','junction_node','replacement_edges','original_removed','subdivision_sampled_verified')}
                summary['selected']['original_source_edge']=source['edge_id']
                source=source|{'edge_id':incoming['id'],'edge_snapshot':incoming,'node_id':placement['junction_node'],'through_edge':through['id']}
                summary['selected'].update(source_edge=source['edge_id'],source_node=source['node_id'])
            rb=result.get('readback',{});nodes=rb.get('ordered_nodes',[]);edges=rb.get('ordered_edges',[])
            _require_engineering_readback(rb,brief)
            summary.update(stage='readback',game_constructed=True,edges=edges,nodes=nodes)
            if rb.get('connected') is not True or not nodes or nodes[0]!=source['node_id'] or nodes[-1]!=target['node_id'] or rb.get('attachments',{}).get('source_edge')!=source['edge_id'] or rb.get('attachments',{}).get('target_edge')!=target['edge_id']:
                summary.update(status='native_verification_failed',error='exact attachments not established');return summary
            summary.update(connected=True,max_sampled_grade=rb.get('max_sampled_grade'),
                           max_join_height_gap=rb.get('max_join_height_gap'),max_join_grade_gap=rb.get('max_join_grade_gap'))
            if junction:
                j=result.get('junction',{});incident=j.get('incident_edges',[])
                if (j.get('node')!=source['node_id'] or j.get('incoming_edge')!=source['edge_id'] or j.get('through_edge')!=source['through_edge']
                        or j.get('branch_edge')!=edges[0] or j.get('exact_native_identity') is not True or len(incident)!=3
                        or set(incident)!={source['edge_id'],source['through_edge'],edges[0]}
                        or result.get('through_after',{}).get('requested_route_verified') is not True):
                    summary.update(status='native_verification_failed',error='exact junction/through movement not established');return summary
                if j.get('branch_geometry_verified') is not True or result.get('branch_after',{}).get('requested_route_verified') is not True:
                    summary.update(status='native_verification_failed',error='branch movement/geometry not established');return summary
                summary['junction']=j
                summary['through_route_length']=result['through_after'].get('total_path_length')
            if guides:
                realised=rb.get('realised_guides',[])
                if len(realised)!=len(guides) or any(g.get('verified') is not True for g in realised):
                    summary.update(status='native_verification_failed',error='guide joins not established');return summary
                summary.update(guide_nodes_realised=True,guide_nodes=[g['node'] for g in realised])
            def other(c):
                edge=c['edge_snapshot'];return edge['node0'] if edge['node1']==c['node_id'] else edge['node1']
            summary['stage']='route'
            route_params={'source_edge':source['edge_id'],'source_node':other(source),
                'target_edge':target['edge_id'],'target_node':other(target),'mode':'TRAIN',
                'max_length':brief['max_route_length'],'required_edges':edges,
                'geometry_constraints':{'edge_ids':edges,'radius':brief['radius'],'max_grade':brief['vertical']['max_grade'],'region':brief['region']}}
            if junction:route_params['junction_nodes']=(junction_nodes or [])+[source['node_id']]
            verified=client.request('route',route_params)
            record['route_request_id']=verified['request_id']
            accepted=verified['status']=='ok' and verified.get('result',{}).get('requested_route_verified') is True
            summary.update(status='ok' if accepted else 'native_route_unverified',native_route_verified=accepted,
                           route_length=verified.get('result',{}).get('total_path_length'),stage='complete' if accepted else 'route')
            return summary
        summary.update(status='search_budget_exhausted' if len(pairs)>brief['max_fit_attempts'] else 'no_accepted_candidate')
        return summary
    except (LiveError,OSError,ValueError,KeyError,TypeError) as exc:
        summary.update(status=getattr(exc,'status','local_input_or_storage_error'),error=str(exc)[:400])
        if summary['stage']=='native_connection' and execute:summary['game_constructed']='unknown'
        return summary
    finally:
        try:atomic_json(path,record)
        finally:lock.unlink()

def _require_engineering_readback(readback,brief):
    """Fitter settings cannot substitute for current selected engineering acceptance."""
    minimum=readback.get('min_sampled_radius')
    if (readback.get('engineering_checks_verified') is not True
            or readback.get('requested_min_radius')!=brief['radius']
            or (minimum is None and readback.get('straight_only') is not True)
            or (minimum is not None and (type(minimum) not in (int,float) or not math.isfinite(minimum) or minimum<brief['radius']))):
        raise LiveError('native_verification_failed','selected realised radius not established')
    if 'vertical' in brief:
        grade=readback.get('max_sampled_grade')
        if type(grade) not in (int,float) or not math.isfinite(grade) or grade>brief['vertical']['max_grade']+1e-6:
            raise LiveError('native_verification_failed','selected realised grade not established')

def connect_adjacent(client,brief,*,execute=False):
    """Native normal-offset sampling at actual template spacing; no Python fitter."""
    if not isinstance(brief,dict) or not {'side','spacing_tolerance'}<=brief.keys():raise ValueError('adjacent side/tolerance required')
    base={k:v for k,v in brief.items() if k not in ('side','spacing_tolerance')};validate_project_brief(base,corridor=True)
    if brief['side'] not in ('left','right') or type(execute) is not bool:raise ValueError('invalid adjacent side/execution')
    tolerance=brief['spacing_tolerance']
    if type(tolerance) not in (float,int) or not math.isfinite(tolerance) or not 0<tolerance<=.1:raise ValueError('spacing_tolerance outside(0,.1]')
    path=client.evidence/(uuid.uuid4().hex+'.adjacent.json')
    summary={'status':'incomplete','operation':'connect-adjacent','game_constructed':False,'execute':execute,'stage':'reference','evidence':str(path.resolve())}
    record={'brief':brief,'summary':summary,'observations':[]}
    try:
        source,rid=_select_throat_port(client,brief['source'],outward_sign=-1);record['observations'].append(rid)
        target,rid=_select_throat_port(client,brief['target']);record['observations'].append(rid)
        p={'source_edge':source['edge_id'],'source_node':source['node_id'],'target_edge':target['edge_id'],'target_node':target['node_id'],
           'mode':'TRAIN','max_length':brief['max_route_length'],'required_edges':[source['edge_id'],target['edge_id']]}
        reference=client.request('route',p);record['observations'].append(reference['request_id'])
        if reference['status']!='ok' or reference.get('result',{}).get('requested_route_verified') is not True:raise LiveError('reference_route_unverified','current directed reference route required')
        chain=[r for r in reference['result']['path'] if r['confirmed_TRACK']]
        if not 1<=len(chain)<=16 or len(chain)!=len(reference['result']['path']):raise ValueError('ordinary bounded reference TRACK chain required')
        ids=[r['edge']['entity'] for r in chain]
        observed=client.request('inspect',{'edge_ids':ids,'resources':True});record['observations'].append(observed['request_id'])
        if observed['status']!='ok':raise LiveError(observed['status'],'reference inspection failed')
        rows={e['id']:e for e in observed['result']['edges']};spacing=rows[ids[0]]['resource']['track_distance']
        if type(spacing) not in (float,int) or not math.isfinite(spacing) or not 0<spacing<=20:raise ValueError('native trackDistance unavailable')
        spacing*=1 if brief['side']=='left' else -1
        params={'reference':[{'edge':rows[r['edge']['entity']],'forward':r['forward']} for r in chain],
                'spacing':spacing,'tolerance':tolerance,'radius':brief['radius'],'region':brief['region'],
                'max_grade':brief['vertical']['max_grade'],'execute':execute}
        record['native_params']=params;summary['stage']='native_adjacent';atomic_json(path,record)
        response=client.request('adjacent',params);record['response']=response;v=response.get('result',{})
        summary.update(status=response['status'],game_constructed=v.get('game_constructed','unknown'),native_track_distance=abs(spacing),side=brief['side'])
        if response['status']!='ok':summary['error']=v.get('error','native_adjacent_failed');return summary
        if not execute:summary.update(stage='preflight',sampled_only=True);return summary
        rb=v.get('readback',{});adj=v.get('adjacency',{})
        _require_engineering_readback(rb,brief)
        if rb.get('connected') is not True or adj.get('sampled_verified') is not True or adj.get('independent_native_nodes') is not True:
            summary.update(status='native_verification_failed',error='adjacent shape/independence unverified');return summary
        p.update(source_edge=rb['ordered_edges'][0],source_node=rb['ordered_nodes'][0],target_edge=rb['ordered_edges'][-1],target_node=rb['ordered_nodes'][-1],required_edges=rb['ordered_edges'],
                 geometry_constraints={'all_path':True,'edge_ids':[],'radius':brief['radius'],'max_grade':brief['vertical']['max_grade'],'region':brief['region']})
        route_result=client.request('route',p);record['adjacent_route']=route_result
        if route_result['status']!='ok' or route_result.get('result',{}).get('requested_route_verified') is not True:
            summary.update(status='native_verification_failed',error='adjacent directed route unverified');return summary
        summary.update(status='ok',stage='verified',edges=rb['ordered_edges'],nodes=rb['ordered_nodes'],
                       sampled_adjacency=adj,native_route_verified=True,train_traversal='unprobed')
        return summary
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if execute and summary['stage']=='native_adjacent':summary['game_constructed']='unknown'
        return summary
    finally:atomic_json(path,record)


def validate_throat_brief(brief):
    keys={'roles','steps','required_routes','radius','region','vertical','placement_tolerance','max_fit_attempts','max_route_length'}
    if not isinstance(brief,dict) or set(brief)!=keys:raise ValueError('throat brief fields mismatch')
    roles=brief['roles'];steps=brief['steps'];matrix=brief['required_routes']
    if not isinstance(roles,dict) or not 5<=len(roles)<=10:raise ValueError('throat requires bounded named roles')
    if any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',n) for n in roles):raise ValueError('invalid role name')
    kinds=[r.get('kind') for r in roles.values() if isinstance(r,dict)]
    if kinds.count('approach')!=2 or kinds.count('destination')<3 or len(kinds)!=len(roles) or any(k not in ('approach','destination') for k in kinds):raise ValueError('two approaches and at least three destinations required')
    if not isinstance(steps,list) or not 2<=len(steps)<=6:raise ValueError('throat steps outside bounded domain')
    names=[]
    for step in steps:
        if not isinstance(step,dict) or set(step)!={'name','kind','source','target'} or step['kind'] not in ('crossover','branch'):raise ValueError('invalid throat step')
        if not isinstance(step['name'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',step['name']) or step['name'] in names:raise ValueError('invalid/duplicate step name')
        names.append(step['name'])
        b={k:brief[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length')}
        b.update(source=step['source'],target=step['target'])
        validate_project_brief(b,corridor=True)
    if not any(s['kind']=='crossover' for s in steps) or not any(s['kind']=='branch' for s in steps):raise ValueError('crossover and branch required')
    for role in roles.values():
        if set(role)!={'kind','endpoint'}:raise ValueError('role requires kind and endpoint')
        b={k:brief[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length')}
        b.update(source=role['endpoint'],target=role['endpoint']);validate_project_brief(b,corridor=True)
    tolerance=brief['placement_tolerance']
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<tolerance<=10:raise ValueError('invalid placement_tolerance')
    if not isinstance(matrix,list) or not 3<=len(matrix)<=16:raise ValueError('required route matrix outside bounded domain')
    seen=set()
    for row in matrix:
        if not isinstance(row,dict) or set(row)!={'from','to','via'} or row['from'] not in roles or row['to'] not in roles:raise ValueError('invalid route row')
        if roles[row['from']]['kind']!='approach' or roles[row['to']]['kind']!='destination':raise ValueError('route must be directed approach to destination')
        pair=(row['from'],row['to'])
        if pair in seen:raise ValueError('duplicate required movement')
        seen.add(pair)
        if not isinstance(row['via'],list) or len(set(row['via']))!=len(row['via']) or any(n not in names for n in row['via']):raise ValueError('invalid route step reference')
    if set(r['from'] for r in matrix)!={n for n,r in roles.items() if r['kind']=='approach'} or set(r['to'] for r in matrix)!={n for n,r in roles.items() if r['kind']=='destination'}:raise ValueError('matrix must exercise every role')
    if set(n for r in matrix for n in r['via'])!=set(names):raise ValueError('matrix must exercise each construction step')


def _select_throat_port(client,intent,*,interior=False,tolerance=None,outward_sign=1):
    found=client.request('discover_interior',intent|{'placement_tolerance':tolerance}) if interior else discover(client,{k:intent[k] for k in ('region','max_edges')})
    if found['status']!='ok':raise LiveError(found['status'],found.get('result',{}).get('error','port_discovery_failed'),found['request_id'])
    value=found['result']
    if value.get('complete') is not True:raise LiveError('discovery_incomplete','bounded role discovery was truncated',found['request_id'])
    direction=intent['travel_direction'];size=math.hypot(*direction);ranked=[]
    for c in value['candidates']:
        if (c.get('interior_eligible') if interior else c.get('eligible')) is not True:continue
        d=c['outward_direction'];heading=math.degrees(math.acos(max(-1,min(1,outward_sign*(d[0]*direction[0]+d[1]*direction[1])/size))))
        if heading>intent['heading_tolerance_deg']:continue
        distance=math.dist(c['pos'],intent['guide_xyz'])
        if distance>(tolerance if interior else 10):continue
        ranked.append((distance,heading,c['edge_id'],c))
    ranked.sort(key=lambda x:x[:3])
    if not ranked:raise LiveError('no_eligible_candidates','no current native attachment for declared role',found['request_id'])
    if len(ranked)>1 and abs(ranked[0][0]-ranked[1][0])<.001:raise LiveError('ambiguous_attachment','declared role does not distinguish native attachments',found['request_id'])
    return ranked[0][3],found['request_id']


def connect_throat(client,brief,*,execute=False,reconciled_crossover=None):
    """Bounded composition, then fresh directed routes on the final assembled network.

    Guides select semantic roles; native observations provide identities. No replay,
    automatic fixture creation, Python geometry fitter or physical traversal claim.
    """
    validate_throat_brief(brief)
    if type(execute) is not bool:raise ValueError('execute must be boolean')
    path=client.evidence/(uuid.uuid4().hex+'.throat.json')
    summary={'status':'incomplete','operation':'connect-throat','execute':execute,'game_constructed':False,
             'stage':'roles','steps_completed':0,'routes_verified':0,'evidence':str(path.resolve()),'train_traversal':'unprobed'}
    record={'brief':brief,'summary':summary,'steps':[],'observations':[],'route_matrix':[],'semantic_mapping':{}}
    junctions=[];step_edges={}
    def roles():
        ports={}
        for name,role in brief['roles'].items():
            c,rid=_select_throat_port(client,role['endpoint'],outward_sign=-1 if role['kind']=='approach' else 1);record['observations'].append(rid);ports[name]=c
        record['semantic_mapping']['roles']=ports;return ports
    try:
        roles();atomic_json(path,record)
        for step in brief['steps']:
            summary['stage']=step['name'];atomic_json(path,record)
            if step['kind']=='branch':
                b={k:brief[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length','placement_tolerance')}
                b.update(source=step['source'],target=step['target'])
                response=connect_junction_at(client,b,execute=execute,junction_nodes=junctions)
                record['steps'].append({'name':step['name'],'summary':response})
                if response['status']!='ok':
                    summary.update(status=response['status'],error=response.get('error','branch_failed'),game_constructed=True if summary['game_constructed'] is True and response.get('game_constructed') is False else response.get('game_constructed','unknown'));return summary
                if execute:
                    junctions.append(response['junction']['node']);step_edges[step['name']]=response['edges']
            else:
                if reconciled_crossover is not None and step is brief['steps'][0]:
                    if not execute:raise ValueError('explicit reconciled continuation requires execute')
                    saved=json.loads(Path(reconciled_crossover).read_text());old=saved.get('verification_params',{})
                    source,target=old['source'],old['target']
                else:
                    source,rid=_select_throat_port(client,step['source'],interior=True,tolerance=brief['placement_tolerance']);record['observations'].append(rid)
                    target,rid=_select_throat_port(client,step['target'],interior=True,tolerance=brief['placement_tolerance']);record['observations'].append(rid)
                params={k:brief[k] for k in ('radius','region','vertical','max_route_length')}
                params.update(source=source,target=target,location=step['source']|{'placement_tolerance':brief['placement_tolerance']},
                    target_location=step['target']|{'placement_tolerance':brief['placement_tolerance']},junction_nodes=junctions,execute=execute)
                if reconciled_crossover is not None and step is brief['steps'][0]:
                    saved=json.loads(Path(reconciled_crossover).read_text())
                    old=saved.get('verification_params',{})
                    if saved.get('status')!='reconciled_verified_crossover' or any(old.get(k)!=params[k] for k in ('location','target_location','radius','region','vertical','max_route_length')):
                        raise ValueError('reconciled crossover does not match approved step/constraints')
                    response=client.request('verify_crossover',old|{'execute':False})
                else:response=client.request('crossover',params)
                v=response.get('result',{})
                record['steps'].append({'name':step['name'],'request_id':response['request_id'],'response':response})
                if response['status']!='ok':summary.update(status=response['status'],error=v.get('error','crossover_failed'),game_constructed=True if summary['game_constructed'] is True and v.get('game_constructed') is False else v.get('game_constructed','unknown'));return summary
                if execute:
                    rb=v.get('readback',{});placements=v.get('placements',[])
                    if (rb.get('connected') is not True or v.get('crossover_after',{}).get('requested_route_verified') is not True
                            or len(placements)!=2 or any(t.get('original_removed') is not True or t.get('subdivision_sampled_verified') is not True for t in placements)
                            or len(v.get('through_after',[]))!=2 or any(r.get('requested_route_verified') is not True for r in v['through_after'])):
                        summary.update(status='native_verification_failed',error='crossover attachments/movements not established',game_constructed=True);return summary
                    junctions.extend(v['junction_nodes']);step_edges[step['name']]=rb['ordered_edges']
            summary['steps_completed']+=1
            if execute:summary['game_constructed']=True;roles()
            atomic_json(path,record)
        if not execute:
            summary.update(status='ok',stage='preflight',final_network_verified=False,required_routes=len(brief['required_routes']));return summary
        summary['stage']='final_route_matrix';ports=roles()
        record['semantic_mapping'].update(junction_nodes=junctions,step_edges=step_edges)
        for row in brief['required_routes']:
            a,b=ports[row['from']],ports[row['to']]
            required=list(dict.fromkeys([a['edge_id'],b['edge_id']]+[e for name in row['via'] for e in step_edges[name]]))
            q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],'target_node':b['node_id'],
               'mode':'TRAIN','required_edges':required,'max_length':brief['max_route_length'],'junction_nodes':junctions,
               'geometry_constraints':{'all_path':True,'edge_ids':[],'region':brief['region'],'radius':brief['radius'],'max_grade':brief['vertical']['max_grade']}}
            observed=client.request('route',q);r=observed.get('result',{})
            accepted=observed['status']=='ok' and r.get('requested_route_verified') is True
            record['route_matrix'].append(row|{'request_id':observed['request_id'],'verified':accepted,'result':r})
            if not accepted:summary.update(status='native_verification_failed',error='required movement failed: '+row['from']+' -> '+row['to']);return summary
            summary['routes_verified']+=1;atomic_json(path,record)
        summary.update(status='ok',stage='verified',final_network_verified=True,required_routes=len(brief['required_routes']),
                       route_matrix=[{'from':r['from'],'to':r['to'],'verified':r['verified']} for r in record['route_matrix']],
                       junction_nodes=junctions,geometry_sampled_only=True,native_effect_history_complete=False)
        return summary
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc));return summary
    finally:atomic_json(path,record)


def reconcile_rejected_fixture(client, discovery):
    """Close a reported failed fixture using bounded current-state evidence, never replay."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='test_approach':
        raise LiveError('reconciliation_required','only a pending test_approach rejection is supported')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text())
    if (response.get('session')!=client.session or response.get('request_id')!=rid
            or response.get('status')!='mutation_unverified'
            or not response.get('result',{}).get('error','').endswith('native_test_approach_rejected')):
        raise LiveError('reconciliation_required','no explicit native fixture rejection evidence',rid)
    if (not isinstance(discovery,dict) or discovery.get('operation')!='discover'
            or discovery.get('session')!=client.session or discovery.get('status')!='ok'):
        raise ValueError('reconciliation requires original current-session discovery')
    p=pending['params'];b=p['brief'];validate_brief(b)
    matches=[c for c in discovery['result']['candidates'] if c['edge_id']==b['anchor_edge'] and c['node_id']==b['anchor_node']]
    if len(matches)!=1:raise ValueError('original fixture anchor snapshot missing')
    current=client.request('inspect',{'edge_ids':[b['anchor_edge']]})
    if current['status']!='ok' or current['result']['edges']!=[matches[0]['edge_snapshot']]:
        raise LiveError('reconciliation_required','fixture anchor changed; outcome remains uncertain',rid)
    direction=b['end_direction'];norm=math.hypot(*direction)
    end=[b['end_xy'][i]+p['length']*direction[i]/norm for i in range(2)]
    # Existing fixture fitter checks finish XY within0.001, heading within0.1degree,
    # and both proposed endpoints inside its XYZ region;2units covers those errors.
    region={'min':[min(b['end_xy'][i],end[i])-2 for i in range(2)]+[b['region']['min'][2]],
            'max':[max(b['end_xy'][i],end[i])+2 for i in range(2)]+[b['region']['max'][2]]}
    observed=discover(client,{'region':region,'max_edges':16});result=observed.get('result',{})
    if observed['status']!='ok' or result.get('complete') is not True or result.get('edge_count')!=0:
        raise LiveError('reconciliation_required','fixture footprint is incomplete or contains TRACK; retain pending outcome',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending operation changed during observation',rid)
    record={'status':'reconciled_failed_fixture','original_pending':pending,'original_response':str(response_path.resolve()),
        'observations':[current['request_id'],observed['request_id']],'region':region,
        'intended_fixture_constructed':False,'other_effects':'unknown','effects_history_complete':False,
        'automatic_replay':False,'game_constructed':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_connection(client, discoveries):
    """Record a native-rejected connection as absent using fresh exact incidence."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='connection' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','only a pending native-rejected connection is supported')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text());result=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid
            or response.get('status')!='error' or result.get('native_command_success') is not False
            or result.get('error')!='native_construction_rejected' or result.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native connection rejection evidence',rid)
    records=discoveries if isinstance(discoveries,list) else [discoveries]
    if not 1<=len(records)<=2 or any(not isinstance(r,dict) or r.get('operation')!='discover'
            or r.get('status')!='ok' or r.get('session')!=client.session for r in records):
        raise ValueError('reconciliation requires original current-session discoveries')
    candidates=[c for r in records for c in r['result']['candidates']];brief=pending['params']['brief']
    selected=[]
    for edge_key,node_key in (('anchor_edge','anchor_node'),('target_edge','target_node')):
        matches=[c for c in candidates if c['edge_id']==brief[edge_key] and c['node_id']==brief[node_key]]
        if len(matches)!=1:raise ValueError('original exact connection attachment missing or ambiguous')
        selected.append(matches[0])
    selection={'source_ref':selected[0]['ref'],'target_ref':selected[1]['ref'],
               'radius':brief['radius'],'region':brief['region']}
    if 'vertical' in brief:selection['vertical']=brief['vertical']
    # Reuse the already-loaded fit-only operation, which first checks exact
    # unchanged snapshots and full single-edge incidence at both attachments.
    observed=connect_selected(client,records,selection);fit=observed.get('result',{}).get('fit',{})
    if (observed['status']!='ok' or fit.get('start_node')!=brief['anchor_node']
            or fit.get('target_node')!=brief['target_node']):
        raise LiveError('reconciliation_required','attachment observations do not establish absence',rid)
    facts={'attachments_unchanged_and_free':True,'completed_connection_absent':True,
           'source_node':brief['anchor_node'],'target_node':brief['target_node']}
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_connection','original_pending':pending,'original_response':str(response_path.resolve()),
            'observation':observed['request_id'],'facts':facts,'completed_connection_constructed':False,
            'other_effects':'unknown','effects_history_complete':False,'automatic_replay':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_corridor(client):
    """Explicit current free-attachment/native preflight check; never rebuild."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='corridor' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending native-rejected corridor')
    rid=pending['request_id'];response=json.loads((client.evidence/(rid+'.response.json')).read_text());v=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid or response.get('operation')!='corridor'
            or response.get('status')!='error' or v.get('native_command_success') is not False
            or v.get('error')!='native_construction_rejected' or v.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native corridor rejection',rid)
    observed=client.request('corridor',pending['params']|{'execute':False})
    if observed['status']!='ok' or observed.get('result',{}).get('game_constructed') is not False:
        raise LiveError('reconciliation_required','unchanged free attachments/preflight not established',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_corridor','original_pending':pending,'observation':observed['request_id'],
            'completed_corridor_absent':True,'other_effects':'unknown','automatic_replay':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_crossover(client):
    """Read-only original through-edge/preflight check after explicit native rejection."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='crossover' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending native-rejected crossover')
    rid=pending['request_id'];response=json.loads((client.evidence/(rid+'.response.json')).read_text());v=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid or response.get('operation')!='crossover'
            or response.get('status')!='error' or v.get('error')!='native_construction_rejected' or v.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native crossover rejection',rid)
    observed=client.request('crossover',pending['params']|{'execute':False});r=observed.get('result',{})
    if observed['status']!='ok' or r.get('game_constructed') is not False or len(r.get('through_before',[]))!=2 or any(x.get('requested_route_verified') is not True for x in r['through_before']):
        raise LiveError('reconciliation_required','unchanged original through edges/routes not established',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_crossover','original_pending':pending,'observation':observed['request_id'],
            'completed_crossover_absent':True,'other_effects':'unknown','automatic_replay':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_junction(client):
    """Fresh fit-only identity/incidence checks after an explicit native rejection."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation'] not in ('junction','interior_junction') or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending native-rejected junction')
    operation=pending['operation']
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text());result=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid or response.get('operation')!=operation
            or response.get('status')!='error' or result.get('native_command_success') is not False
            or result.get('error')!='native_construction_rejected' or result.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native junction rejection',rid)
    params=pending['params']|{'execute':False};observed=client.request(operation,params)
    if (observed['status']!='ok' or observed.get('result',{}).get('game_constructed') is not False
            or observed.get('result',{}).get('through_before',{}).get('requested_route_verified') is not True):
        raise LiveError('reconciliation_required','unchanged junction source/free target not established',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_junction','original_pending':pending,'original_response':str(response_path.resolve()),
            'observation':observed['request_id'],'completed_junction_constructed':False,
            'other_effects':'unknown','effects_history_complete':False,'automatic_replay':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}


def reconcile_constructed_crossover(client,original_client=None):
    """Explicit read-only verification of returned crossover IDs; never replay."""
    old=original_client or client;state=json.loads(old.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='crossover' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending crossover')
    rid=pending['request_id'];original=json.loads((old.evidence/(rid+'.response.json')).read_text());v=original.get('result',{});fit=v.get('fit',{});ids=v.get('returned_edges')
    if (original.get('session')!=old.session or original.get('request_id')!=rid or original.get('operation')!='crossover'
            or original.get('status')!='mutation_unverified' or v.get('game_constructed') is not True
            or not isinstance(ids,list) or len(ids)!=fit.get('pieces',-5)+4 or len(set(ids))!=len(ids)
            or any(type(i) is not int or i<=0 for i in ids) or not isinstance(fit.get('controls'),list)):
        raise LiveError('reconciliation_required','no exact crossover receipt',rid)
    params=pending['params']|{'execute':False,'fit':fit,'edge_ids':ids,'original_request':rid}
    observed=client.request('verify_crossover',params);r=observed.get('result',{})
    if (observed['status']!='ok' or r.get('reconciled_current_state') is not True or r.get('readback',{}).get('connected') is not True
            or r.get('crossover_after',{}).get('requested_route_verified') is not True or len(r.get('placements',[]))!=2
            or any(x.get('original_removed') is not True or x.get('subdivision_sampled_verified') is not True for x in r['placements'])
            or len(r.get('through_after',[]))!=2 or any(x.get('requested_route_verified') is not True for x in r['through_after'])):
        raise LiveError('reconciliation_required',r.get('error','current crossover unverified'),rid)
    latest=json.loads(old.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during readback',rid)
    record={'status':'reconciled_verified_crossover','original_pending':pending,'verification_params':params,'observation':observed['request_id'],
            'current_session':client.session,'verified':r,'automatic_replay':False,'native_effect_history_complete':False}
    path=old.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_constructions',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(old.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}


def reconcile_constructed_interior(client, original_client=None):
    """Read back exact reported split/branch identities, even after a normal load.

    An old client is only an evidence/journal reference; all native reads use the
    current client. This is not automatic crash recovery or construction replay.
    """
    old=original_client or client
    state=json.loads(old.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='interior_junction' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending constructed interior junction')
    rid=pending['request_id'];original=json.loads((old.evidence/(rid+'.response.json')).read_text());v=original.get('result',{})
    ids=v.get('returned_edges');fit=v.get('fit',{});params=pending['params']
    if (original.get('session')!=old.session or original.get('request_id')!=rid or original.get('operation')!='interior_junction'
            or original.get('status')!='mutation_unverified' or v.get('game_constructed') is not True
            or not isinstance(ids,list) or len(ids)!=fit.get('pieces',-2)+2 or len(set(ids))!=len(ids)
            or any(type(i) is not int or i<=0 for i in ids) or not isinstance(fit.get('controls'),list)):
        raise LiveError('reconciliation_required','no exact reported split construction',rid)
    observed=client.request('verify_interior',params|{'execute':False,'fit':fit,'edge_ids':ids,
        'parameter':params['source']['parameter'],'through_before':None})
    result=observed.get('result',{})
    rb=result.get('readback',{});placement=result.get('placement',{});j=result.get('junction',{})
    if (observed['status']!='ok' or result.get('reconciled_current_state') is not True
            or rb.get('connected') is not True or placement.get('original_removed') is not True
            or placement.get('original_edge')!=params['source']['edge_id']
            or set(placement.get('replacement_edges',[])+rb.get('ordered_edges',[]))!=set(ids)
            or j.get('exact_native_identity') is not True or j.get('branch_geometry_verified') is not True
            or result.get('through_after',{}).get('requested_route_verified') is not True
            or result.get('branch_after',{}).get('requested_route_verified') is not True):
        raise LiveError('reconciliation_required',result.get('error','realised junction not verified'),rid)
    latest=json.loads(old.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_verified_interior','original_pending':pending,'original_response':str((old.evidence/(rid+'.response.json')).resolve()),
            'observation':observed['request_id'],'current_session':client.session,'verified':result,
            'native_effect_history_complete':False,'automatic_replay':False,'train_traversal':'unprobed'}
    path=old.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_constructions',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(old.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}


def reconcile_constructed_connection(client, discoveries, edge_ids):
    """Verify reported construction after a readback failure; no build or replay."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='connection' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending constructed connection')
    rid=pending['request_id'];original=json.loads((client.evidence/(rid+'.response.json')).read_text())
    result=original.get('result',{});fit=result.get('fit',{})
    if (original.get('session')!=client.session or original.get('request_id')!=rid
            or original.get('status')!='mutation_unverified' or result.get('game_constructed') is not True
            or result.get('stage')!='readback' or {'stage':'build','status':'ok'} not in result.get('stages',[])):
        raise LiveError('reconciliation_required','no reported successful native build/readback failure',rid)
    brief=pending['params']['brief'];validate_connection_brief(brief)
    controls=fit.get('controls')
    if (not isinstance(controls,list) or not 1<=len(controls)<=8 or not isinstance(edge_ids,list)
            or len(edge_ids)!=len(controls) or any(type(e) is not int or e<=0 for e in edge_ids)
            or len(set(edge_ids))!=len(edge_ids)):
        raise ValueError('provide distinct observed native edges matching recorded controls')
    records=discoveries if isinstance(discoveries,list) else [discoveries]
    if not 1<=len(records)<=2 or any(r.get('operation')!='discover' or r.get('session')!=client.session or r.get('status')!='ok' for r in records):
        raise ValueError('original current-session attachment records required')
    candidates=[c for r in records for c in r['result']['candidates']]
    expected=[]
    for ek,nk in (('anchor_edge','anchor_node'),('target_edge','target_node')):
        matches=[c for c in candidates if c['edge_id']==brief[ek] and c['node_id']==brief[nk]]
        if len(matches)!=1:raise ValueError('original exact attachment missing or ambiguous')
        expected.append(matches[0]['edge_snapshot'])
    maxgrade=brief.get('vertical',{}).get('max_grade',fit.get('max_grade'))
    if type(maxgrade) not in (int,float) or not math.isfinite(maxgrade) or maxgrade<0:
        raise LiveError('reconciliation_required','recorded engineering grade limit unavailable',rid)
    bounds={'radius':brief['radius'],'max_grade':maxgrade,'region':brief['region']}
    observed=client.request('inspect',{'edge_ids':[brief['anchor_edge'],*edge_ids,brief['target_edge']],
                                      'geometry_constraints':bounds})
    rows=observed.get('result',{}).get('edges',[])
    snapshot=lambda e:{k:v for k,v in e.items() if k!='engineering_checks'}
    if observed['status']!='ok' or len(rows)!=len(controls)+2 or snapshot(rows[0])!=expected[0] or snapshot(rows[-1])!=expected[1]:
        raise LiveError('reconciliation_required','attachments changed or inspection incomplete',rid)
    for e in rows:
        check=e.get('engineering_checks',{});radius=check.get('min_sampled_radius');grade=check.get('max_sampled_grade')
        # The native inspector omits radius only for an infinite sampled radius.
        # Its positive sampled_verified marker certifies the supplied hard bounds.
        if (check.get('sampled_verified') is not True or check.get('samples')!=17
                or (radius is not None and (type(radius) not in (int,float) or not math.isfinite(radius) or radius<brief['radius']))
                or type(grade) not in (int,float) or not math.isfinite(grade) or grade>maxgrade+.000001):
            raise LiveError('reconciliation_required','realised engineering bounds not established',rid)
    remaining={e['id']:e for e in rows[1:-1]};current=brief['anchor_node'];ordered=[];nodes=[current]
    for control in controls:
        matches=[e for e in remaining.values() if e['node0']==current]
        if len(matches)!=1:raise LiveError('reconciliation_required','exact directed chain missing or ambiguous',rid)
        e=matches[0]
        if (e['template']!=expected[0]['template'] or e['style']!=expected[0]['style']
                or any(len(e[k])!=3 or any(abs(e[k][i]-control[k][i])>.001 for i in range(3)) for k in ('p0','p1','t0','t1'))):
            raise LiveError('reconciliation_required','realised controls/resources differ from recorded fit',rid)
        ordered.append(e['id']);current=e['node1'];nodes.append(current);remaining.pop(e['id'])
    if remaining or current!=brief['target_node']:
        raise LiveError('reconciliation_required','requested exact target not reached',rid)
    source,target=expected
    path=route(client,{'source_edge':source['id'],'source_node':source['node0'] if brief['anchor_node']==source['node1'] else source['node1'],
                      'target_edge':target['id'],'target_node':target['node1'] if brief['target_node']==target['node0'] else target['node0'],
                      'mode':'TRAIN','max_length':800,'required_edges':ordered})
    if path['status']!='ok' or path.get('result',{}).get('requested_route_verified') is not True:
        raise LiveError('reconciliation_required','native path does not establish requested connection',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_verified_connection','original_pending':pending,'original_response':str((client.evidence/(rid+'.response.json')).resolve()),
            'observations':[observed['request_id'],path['request_id']],'ordered_edges':ordered,'ordered_nodes':nodes,
            'connected':True,'native_route_verified':True,'engineering_constraints':bounds,'engineering_sampled_only':True,
            'native_effect_history_complete':False,'automatic_replay':False,'train_traversal':'unprobed'}
    evidence=client.evidence/(rid+'.reconciliation.json');atomic_json(evidence,record)
    latest.setdefault('reconciled_constructions',{})[rid]={'evidence':str(evidence.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(evidence.resolve())}

def route(client, brief):
    """Query native transport routing; does not build or establish train traversal."""
    keys = {'source_edge', 'source_node', 'target_edge', 'target_node', 'mode', 'max_length', 'required_edges'}
    if not isinstance(brief, dict) or set(brief) != keys:
        raise ValueError('route brief requires only ' + ', '.join(sorted(keys)))
    for key in ('source_edge', 'source_node', 'target_edge', 'target_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    if brief['source_node'] == brief['target_node'] or brief['source_edge'] == brief['target_edge']:
        raise ValueError('route requires distinct attachments')
    if brief['mode'] not in ('TRAIN', 'ELECTRIC_TRAIN'):
        raise ValueError('route mode must be TRAIN or ELECTRIC_TRAIN')
    if type(brief['max_length']) not in (int, float) or not math.isfinite(brief['max_length']) or not 0 < brief['max_length'] <= 4000:
        raise ValueError('route max_length must be finite and within (0,4000] native units')
    ids = brief['required_edges']
    if not isinstance(ids, list) or not 1 <= len(ids) <= 32 or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('required_edges must contain 1–32 distinct exact native IDs')
    return client.request('route', brief)

def _workflow(client, brief, execute, operation):
    if type(execute) is not bool:
        raise ValueError('execute must be boolean')
    job_id = uuid.uuid4().hex
    record_path = client.evidence / (job_id + '.workflow.json')
    summary = {'status': 'incomplete', 'job_id': job_id, 'session': client.session,
               'game_constructed': False, 'execute': execute, 'stage': 'inspect',
               'evidence': str(record_path.resolve()), 'stages': []}
    lock = client.evidence / 'workflow.lock'
    try:
        with lock.open('x'):
            pass
    except FileExistsError:
        raise LiveError('client_busy', 'one railway workflow at a time') from None
    try:
        atomic_json(record_path, {'summary': summary, 'brief': brief})
        summary['stage'] = 'native_' + operation
        response = client.request(operation, {'brief': brief, 'execute': execute}, request_id=job_id)
        result = response.get('result', {})
        summary.update(status=response['status'], stage=result.get('stage', 'native_' + operation),
                       stages=result.get('stages', []), game_constructed=result.get('game_constructed', 'unknown' if execute else False))
        if result.get('fit'):
            summary['fit'] = result['fit']
        if response['status'] != 'ok':
            summary['error'] = result.get('error', 'native_stage_failed')
            if result.get('reason_class'):
                summary['reason_class'] = result['reason_class']
        elif execute:
            read = result.get('readback', {})
            _require_engineering_readback(read,brief)
            if (read.get('connected') is not True or not read.get('ordered_edges') or not read.get('ordered_nodes')
                    or read['ordered_nodes'][0] != brief['anchor_node']
                    or (operation == 'connection' and (read['ordered_nodes'][-1] != brief['target_node']
                        or read.get('attachments', {}).get('target_edge') != brief['target_edge']
                        or read.get('attachments', {}).get('source_edge') != brief['anchor_edge']))):
                raise LiveError('native_verification_failed', 'fresh readback did not establish the requested exact attachments')
            summary.update(connected=True, edges=read['ordered_edges'], nodes=read['ordered_nodes'],
                           sampled_XY_error=read.get('sampled_XY_error'), train_traversal=read.get('train_traversal'))
            if operation == 'connection':
                summary['attachments'] = read['attachments']
    except (LiveError, OSError, ValueError, KeyError, TypeError) as exc:
        summary['status'] = getattr(exc, 'status', 'local_input_or_storage_error')
        summary['error'] = str(exc)[:400]
        if summary['stage'] == 'native_' + operation and execute:
            summary['game_constructed'] = 'unknown'
    finally:
        try:
            atomic_json(record_path, {'summary': summary, 'brief': brief})
        finally:
            lock.unlink()
    return summary

class LiveError(RuntimeError):
    def __init__(self, status, detail, request_id=None):
        super().__init__(detail)
        self.status, self.request_id = status, request_id

def lua_literal(value):
    """Serialize only JSON data; no user-supplied executable Lua text."""
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError('nonfinite number')
        return repr(value)
    if isinstance(value, str):
        # Byte decimal escapes avoid Lua/JSON unicode escape differences.
        return '"' + ''.join(chr(b) if 32 <= b < 127 and b not in (34, 92)
                             else '\\' + f'{b:03d}' for b in value.encode('utf-8')) + '"'
    if isinstance(value, list):
        return '{' + ','.join(lua_literal(v) for v in value) + '}'
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return '{' + ','.join('[' + lua_literal(k) + ']=' + lua_literal(v)
                              for k, v in value.items()) + '}'
    raise ValueError('request must contain JSON data only')

def atomic_json(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)

def parse_response(line, request_id, session, operation):
    if MARKER not in line:
        return None
    try:
        data = json.loads(line.split(MARKER, 1)[1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get('request_id') != request_id:
        return None
    if data.get('session') != session or data.get('operation') != operation or data.get('version') != 1:
        raise LiveError('protocol_error', 'matching ID has wrong session/operation/version', request_id)
    if data.get('status') not in {'ok', 'error', 'mutation_unverified'}:
        raise LiveError('protocol_error', 'invalid response status', request_id)
    return data

class LiveClient:
    def __init__(self, mod_directory, log_path, evidence_directory, session, timeout=30, *, require_ack=False):
        self.mod = Path(mod_directory)
        self.log = Path(log_path)
        self.evidence = Path(evidence_directory)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', session):
            raise ValueError('invalid runtime session token')
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError('timeout must be finite and within (0,300] seconds')
        self.session, self.timeout = session, timeout
        self.require_ack = require_ack
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.journal = self.evidence / 'client_state.json'

    def request(self, operation, params, *, request_id=None):
        if operation not in OPERATIONS or not isinstance(params, dict):
            raise ValueError('invalid operation/parameters')
        request_id = request_id or uuid.uuid4().hex
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request_id):
            raise ValueError('invalid request ID')
        lock = self.evidence / 'client.lock'
        try:
            with lock.open('x'):
                pass
        except FileExistsError:
            raise LiveError('client_busy', 'one client request at a time') from None
        try:
            return self._request(operation, params, request_id)
        finally:
            lock.unlink()

    def _request(self, operation, params, request_id):
        state = json.loads(self.journal.read_text()) if self.journal.exists() else {'session': self.session, 'next_sequence': 1}
        if state['session'] != self.session:
            raise LiveError('session_changed', 'use a new evidence directory for a new runtime session')
        unresolved = state.get('pending')
        if unresolved and (is_mutation(operation,params) or operation not in ('readback', 'inspect', 'route', 'discover', 'discover_junction', 'discover_interior', 'verify_interior', 'verify_crossover', 'verify_adjacency', 'adjacent', 'remove_branch', 'crossover', 'selected_connection', 'corridor', 'junction', 'interior_junction')):
            raise LiveError('reconciliation_required', 'previous request is unfinished; inspect its matching response/current world before any repeat', state['pending']['request_id'])
        if (self.evidence / (request_id + '.request.json')).exists():
            raise LiveError('request_id_reused', 'request ID already recorded', request_id)
        sequence = state['next_sequence']
        request = {'version': 1, 'session': self.session, 'sequence': sequence,
                   'request_id': request_id, 'operation': operation, 'params': params}
        body = ('return ' + lua_literal(request) + '\n').encode('ascii')
        if len(body) > 32768:
            raise ValueError('request exceeds 32 KiB')
        offset = self.log.stat().st_size
        atomic_json(self.evidence / (request_id + '.request.json'), request)
        state['pending'] = {**request, 'log_offset': offset}
        if unresolved:
            state['pending']['unresolved_mutation'] = unresolved
        state['next_sequence'] += 1
        atomic_json(self.journal, state)
        directory = self.mod / 'content/scripts/pif_live' / self.session
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'{sequence:06d}.lua'
        if path.exists():
            raise LiveError('request_slot_conflict', str(path), request_id)
        temporary = path.with_suffix('.pending')
        temporary.write_bytes(body)
        os.replace(temporary, path)
        deadline = time.monotonic() + self.timeout
        partial = b''
        received = None
        acknowledged = not self.require_ack
        raw = self.evidence / (request_id + '.log')
        with raw.open('wb') as evidence:
            while time.monotonic() < deadline:
                with self.log.open('rb') as stream:
                    if stream.seek(0, 2) < offset:
                        raise LiveError('log_rotated', 'log changed during request; do not replay', request_id)
                    stream.seek(offset)
                    chunk = stream.read()
                    offset += len(chunk)
                evidence.write(chunk)
                partial += chunk
                lines = partial.split(b'\n')
                partial = lines.pop()
                for line in lines:
                    decoded = line.decode('utf-8', 'replace')
                    ack_marker = 'TPF3_BRIDGE_LIVE_ACK '
                    if ack_marker in decoded:
                        try:
                            ack = json.loads(decoded.split(ack_marker, 1)[1])
                        except ValueError:
                            ack = {}
                        if isinstance(ack, dict) and ack.get('request_id') == request_id and ack.get('session') == self.session:
                            if ack.get('success') is not True:
                                raise LiveError('command_completion_failed', 'native event command did not acknowledge completion; do not replay', request_id)
                            acknowledged = True
                    response = parse_response(decoded, request_id, self.session, operation)
                    if response is not None:
                        received = response
                        atomic_json(self.evidence / (request_id + '.response.json'), response)
                    if received is not None and acknowledged:
                        response = received
                        atomic_json(self.evidence / (request_id + '.response.json'), response)
                        verified_pending = (unresolved and unresolved['operation'] == 'build'
                                            and operation == 'readback' and response['status'] == 'ok'
                                            and response.get('result', {}).get('connected') is True
                                            and params.get('fit_request') == unresolved['params'].get('fit_request'))
                        if unresolved and not verified_pending:
                            state['pending'] = unresolved
                        elif response['status'] == 'mutation_unverified' or (
                                is_mutation(operation, params)
                                and response.get('result', {}).get('game_constructed') == 'unknown'):
                            state['pending']['outcome'] = 'mutation_unverified'
                        else:
                            state.pop('pending')
                        atomic_json(self.journal, state)
                        return response
                if len(partial) > 65536:
                    raise LiveError('protocol_error', 'unterminated oversized log line', request_id)
                time.sleep(.1)
        status = 'mutation_outcome_unknown' if is_mutation(operation, params) else 'request_timeout'
        raise LiveError(status, 'no matching response; request retained for reconciliation, never resubmitted automatically', request_id)

    def reconcile_pending(self):
        """Collect an existing late response only; never send another operation."""
        state = json.loads(self.journal.read_text())
        pending = state.get('pending')
        if not pending or state['session'] != self.session:
            raise LiveError('reconciliation_required', 'no matching current-session pending record')
        with self.log.open('rb') as stream:
            stream.seek(pending['log_offset'])
            lines = stream.read().decode('utf-8', 'replace').splitlines()
        if self.require_ack:
            ack_marker = 'TPF3_BRIDGE_LIVE_ACK '
            acknowledgements = []
            for line in lines:
                if ack_marker in line:
                    try:
                        ack = json.loads(line.split(ack_marker, 1)[1])
                    except ValueError:
                        continue
                    if isinstance(ack, dict) and ack.get('request_id') == pending['request_id'] and ack.get('session') == self.session:
                        acknowledgements.append(ack)
            if not any(ack.get('success') is True for ack in acknowledgements):
                raise LiveError('reconciliation_required', 'matching native command completion is still unobserved; do not replay', pending['request_id'])
        for line in lines:
            response = parse_response(line, pending['request_id'], self.session, pending['operation'])
            if response:
                atomic_json(self.evidence / (pending['request_id'] + '.response.json'), response)
                uncertain = response['status'] == 'mutation_unverified' or (
                    is_mutation(pending['operation'], pending['params'])
                    and response.get('result', {}).get('game_constructed') == 'unknown')
                if not uncertain:
                    state.pop('pending');atomic_json(self.journal, state)
                return response
        raise LiveError('reconciliation_required', 'no matching late response; fresh readback may be requested, no automatic mutation replay', pending['request_id'])

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=sorted(OPERATIONS | {'extend', 'connect', 'connect-selected', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent', 'reconcile-fixture'}))
    parser.add_argument('--params', required=True, type=Path)
    parser.add_argument('--reconciled-crossover', type=Path, help='explicit verified crossover evidence for connect-throat; rechecks read-only, never rebuilds it')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--discovery', type=Path, help='saved full discover response for connect-selected')
    parser.add_argument('--execute', action='store_true', help='authorise native construction for extend/connect/connect-brief/connect-corridor')
    parser.add_argument('--mod-directory', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--session')
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if args.context:
            if any((args.mod_directory, args.log, args.evidence, args.session)):
                raise ValueError('use context or explicit transport arguments, not both')
            client = client_from_context(args.context, args.timeout)
        else:
            if not all((args.mod_directory, args.log, args.evidence, args.session)):
                raise ValueError('provide --context or all explicit transport arguments')
            client = LiveClient(args.mod_directory, args.log, args.evidence, args.session, args.timeout)
        params = json.loads(args.params.read_text(encoding='utf-8-sig'))
        if args.reconciled_crossover and (args.operation!='connect-throat' or not args.execute):
            raise ValueError('--reconciled-crossover requires connect-throat --execute')
        if args.discovery and args.operation not in ('connect-selected','reconcile-fixture'):
            raise ValueError('--discovery is only for connect-selected/reconcile-fixture')
        if args.execute and args.operation not in ('extend', 'connect', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent'):
            raise ValueError('--execute is only for extend/connect/connect-brief/connect-corridor/connect-junction/connect-junction-at; low-level build uses explicit authorised parameter')
        if args.operation in ('extend', 'connect'):
            response = (extend if args.operation == 'extend' else connect)(client, params, execute=args.execute)
        elif args.operation == 'connect-brief':
            response = connect_brief(client,params,execute=args.execute)
        elif args.operation == 'connect-corridor':
            response = connect_corridor(client,params,execute=args.execute)
        elif args.operation == 'connect-junction':
            response = connect_junction(client,params,execute=args.execute)
        elif args.operation == 'connect-junction-at':
            response = connect_junction_at(client,params,execute=args.execute)
        elif args.operation == 'connect-throat':
            response = connect_throat(client,params,execute=args.execute,reconciled_crossover=args.reconciled_crossover)
        elif args.operation == 'connect-adjacent':
            response = connect_adjacent(client,params,execute=args.execute)
        elif args.operation == 'route':
            response = route(client, params)
        elif args.operation == 'discover':
            response = discover(client, params)
        elif args.operation == 'discover_junction':
            response = discover(client,params,junction=True)
        elif args.operation == 'connect-selected':
            if not args.discovery:raise ValueError('connect-selected requires --discovery')
            response = connect_selected(client,json.loads(args.discovery.read_text(encoding='utf-8-sig')),params)
        elif args.operation == 'reconcile-fixture':
            if params!={} or not args.discovery:raise ValueError('reconcile-fixture needs empty params and --discovery')
            response=reconcile_rejected_fixture(client,json.loads(args.discovery.read_text(encoding='utf-8-sig')))
        else:
            response = client.request(args.operation, params)
    except (OSError, ValueError, LiveError, KeyError, TypeError) as exc:
        response = {'status': getattr(exc, 'status', 'local_input_or_storage_error'),
                    'error': str(exc)[:400], 'request_id': getattr(exc, 'request_id', None)}
    output = json.dumps(response, separators=(',', ':'))
    if len(output.encode('utf-8')) > 4095:
        compact = {
            'status': response['status'], 'operation': args.operation,
            'session': client.session, 'request_id': response.get('request_id'),
            'response_file': response.get('evidence') or str((client.evidence / (response['request_id'] + '.response.json')).resolve()),
            'detail': 'full response retained locally',
        }
        if args.operation == 'route':
            result = response.get('result', {})
            compact.update({key:result.get(key) for key in ('native_path_found', 'requested_route_verified', 'path_count', 'truncated', 'reason', 'train_traversal')})
        elif args.operation == 'discover':
            result=response.get('result', {})
            compact.update({key:result.get(key) for key in ('edge_count','candidate_count','truncated','complete')})
            candidates=result.get('candidates', [])
            if isinstance(candidates,list):
                candidates=sorted(candidates,key=lambda c:(not c.get('eligible',False),c['ref']))
                compact['candidate_preview']=[{key:c.get(key) for key in ('ref','pos','eligible','grade')} for c in candidates[:4]]
                compact['candidate_preview_truncated']=len(candidates)>4
        output = json.dumps(compact, separators=(',', ':'))
    print(output)
    accepted = response['status'] == 'ok'
    if args.operation == 'route':
        accepted = accepted and response.get('result', {}).get('requested_route_verified') is True
    return 0 if accepted else 1

if __name__ == '__main__':
    raise SystemExit(main())
