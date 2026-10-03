"""Development live client: data-only mod modules in, correlated game-log JSON out.

No model calls, UI automation, game launch, service, or mutation retry.
The mod must already be active in a healthy test world.
"""
from __future__ import annotations
import argparse
import hashlib
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


JUNCTION_RECIPE = 'widened_two_approach_three_exit_v1'

def _validate_native_frame(brief,unsupported="unsupported_recipe"):
    if brief['radius']!=120 or brief['spacing']!=5:
        raise LiveError(unsupported,'v1 requires hard radius120 and native template spacing5; no scaling or mirroring')
    p=brief['origin']
    if not isinstance(p,list) or len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p):raise ValueError('origin requires finite native XYZ')
    h=brief['heading_deg'];grade=brief['max_grade']
    if type(h) not in (int,float) or not math.isfinite(h) or not -180<=h<=180:raise ValueError('heading_deg must be within [-180,180]')
    if type(grade) not in (int,float) or not math.isfinite(grade) or not 0<grade<=.04:raise ValueError('level recipe max_grade must be within (0,.04]')
    for name in ('region','asset_region'):
        r=brief[name]
        if (not isinstance(r,dict) or set(r)!={'min','max'} or any(not isinstance(r[k],list) or len(r[k])!=3
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in r[k]) for k in ('min','max'))
                or any(r['min'][i]>=r['max'][i] for i in range(3))):raise ValueError(name+' requires ordered finite native XYZ bounds')
    if any(brief['asset_region']['max'][i]-brief['asset_region']['min'][i]>400 for i in range(3)):raise ValueError('asset_region must fit the bounded400-unit native query')
    return p,h,grade


def plan_junction_recipe(brief):
    """Fixed P15 intent in a chosen map frame; no native calls or Python curve fitting."""
    keys={'recipe','origin','heading_deg','radius','max_grade','spacing','region','asset_region'}
    if not isinstance(brief,dict) or set(brief)!=keys:raise ValueError('junction recipe brief fields mismatch')
    if brief['recipe']!=JUNCTION_RECIPE:raise LiveError('unsupported_recipe','only '+JUNCTION_RECIPE+' is supported')
    p,h,grade=_validate_native_frame(brief)
    def position(x,y=0):
        a=math.radians(h);return [p[0]+x*math.cos(a)-y*math.sin(a),p[1]+x*math.sin(a)+y*math.cos(a),p[2]]
    def direction(a=0):a=math.radians(h+a);return [math.cos(a),math.sin(a)]
    def intent(q,a=0):return {'region':{'min':[q[0]-1,q[1]-1,p[2]-1],'max':[q[0]+1,q[1]+1,p[2]+1]},'guide_xyz':q,'travel_direction':direction(a),'max_edges':8,'heading_tolerance_deg':2}
    fixtures=[{'name':name,'position':position(x,y),'travel_direction':direction(a),'length':20} for name,x,y,a in
              [('A1',-20,0,0),('A2',-20,5,0),('D1',1600,180,12),('D2',600,105,0),('D3',1100,460,0)]]
    corners=[position(x,y) for x,y in [(-60,-40),(1660,-40),(1660,500),(-60,500)]]
    footprint={'min':[min(q[i] for q in corners) for i in range(2)]+[p[2]-1],
               'max':[max(q[i] for q in corners) for i in range(2)]+[p[2]+1]}
    if any(footprint['min'][i]<brief['region']['min'][i] or footprint['max'][i]>brief['region']['max'][i] for i in range(3)):
        raise LiveError('unsupported_recipe','authorised region does not contain the widened recipe footprint')
    for f in fixtures:
        f['region']={'min':[max(f['position'][i]-40,brief['region']['min'][i]) for i in range(3)],
                     'max':[min(f['position'][i]+40,brief['region']['max'][i]) for i in range(3)]}
    common={'radius':120,'region':brief['region'],'vertical':{'max_grade':grade},'max_fit_attempts':1,'max_route_length':2500}
    reference=common|{'radius':160,'source':intent(position(0)),'target':intent(position(1600,180),12),
                    'guides':[{'position':position(x,y),'travel_direction':direction(a),'grade':0} for x,y,a in [(400,0,0),(800,30,8),(1200,100,12)]]}
    fanout=common|{'source':intent(position(0,5)),'target':intent(position(600,105)),
                  'guides':[{'position':position(100,5),'travel_direction':direction(),'grade':0}]}
    matrix=[{'from':'A1','to':dest,'via':via} for dest,via in [('D1',[]),('D2',['cross']),('D3',['cross','branch'])]]
    matrix += [{'from':'A2','to':'D2','via':[]},{'from':'A2','to':'D3','via':['branch']}]
    plan={'version':1,'recipe':JUNCTION_RECIPE,'brief':brief,'epoch':'DESIGN','game_constructed':False,'native_fit_verified':False,
          'footprint':footprint,'fixtures':fixtures,'reference':reference,'fanout':fanout,
          'reference_design_min_radius':160,'selected_final_min_radius':120,'level_only':True,
          'retained_close_approach':{'length':100,'spacing':5},'direct5m_crossover':False,
          'cross_source':intent(position(250)),
          'native_fanout_guide_rule':{'source':'long native straight between fan-out arcs','cross_fraction':.70,'branch_fraction':.88},
          'required_routes':matrix,'limitations':['no scaling/mirroring','no direct5m crossover','no physical traversal or continuous geometry proof'],
          'operations':['discover_asset','inspect_asset','prepare_A1','prepare_A2','prepare_D1','prepare_D2','prepare_D3','reference','fanout','native_guides','throat','fresh_approach_spacing']}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_junction_recipe(plan,evidence):
    if plan!=plan_junction_recipe(plan.get('brief')):raise ValueError('recipe plan differs from its deterministic brief')
    path=Path(evidence)/(uuid.uuid4().hex+'.recipe_plan.json');path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,plan)
    return {'status':'ok','operation':'junction-recipe','stage':'plan','game_constructed':False,'native_fit_verified':False,
            'recipe':plan['recipe'],'plan_hash':plan['plan_hash'],'footprint':plan['footprint'],'required_routes':plan['required_routes'],
            'retained_close_approach':plan['retained_close_approach'],'direct5m_crossover':False,'evidence':str(path.resolve())}


def _recipe_throat_brief(plan,fixtures,edges):
    straight=[e for e in edges if all(abs(e[k][i]-(e['p1'][i]-e['p0'][i]))<.001 for k in ('t0','t1') for i in range(3))]
    if not straight:raise LiveError('unsupported_native_result','native fan-out has no straight guide segment')
    e=max(straight,key=lambda e:math.dist(e['p0'],e['p1']))
    if math.dist(e['p0'],e['p1'])<400:raise LiveError('unsupported_native_result','native fan-out guide segment is too short')
    direction=[e['t0'][i]/math.hypot(*e['t0'][:2]) for i in range(2)];z=plan['brief']['origin'][2]
    def intent(q,d):return {'region':{'min':[q[0]-1,q[1]-1,z-1],'max':[q[0]+1,q[1]+1,z+1]},'guide_xyz':q,'travel_direction':d,'max_edges':8,'heading_tolerance_deg':2}
    def guide(f):return intent([e['p0'][i]+f*(e['p1'][i]-e['p0'][i]) for i in range(3)],direction)
    roles={}
    for name,f in fixtures.items():
        d=next(x['travel_direction'] for x in plan['fixtures'] if x['name']==name)
        roles[name]={'kind':'approach' if name.startswith('A') else 'destination','endpoint':intent(f['p0'] if name.startswith('A') else f['p1'],d)}
    b={k:plan['fanout'][k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length')}
    b.update(roles=roles,placement_tolerance=.5,steps=[{'name':'cross','kind':'crossover','source':plan['cross_source'],'target':guide(.70)},
              {'name':'branch','kind':'branch','source':guide(.88),'target':intent(fixtures['D3']['p0'],roles['D3']['endpoint']['travel_direction'])}],required_routes=plan['required_routes'])
    return b


def execute_junction_recipe(client,plan,*,prepared_record=None):
    """One explicit execution, durable step receipts and no automatic resume/replay."""
    if plan!=plan_junction_recipe(plan.get('brief')):raise ValueError('recipe plan differs from its deterministic brief')
    prepared=None
    if prepared_record:
        prepared=json.loads(Path(prepared_record).read_text(encoding='utf-8-sig'))
        if (not isinstance(prepared,dict) or not isinstance(prepared.get('operations'),list) or not prepared['operations']
                or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in prepared['operations'])):
            raise ValueError('prepared recipe operations are missing or malformed')
        s=prepared.get('summary',{});names=[o.get('name') for o in prepared.get('operations',[])]
        if not isinstance(s,dict):raise ValueError('prepared recipe summary is malformed')
        last=prepared.get('operations',[{}])[-1].get('response',{})
        safe_fit_failure=last.get('status')=='no_accepted_candidate' and last.get('game_constructed') is False
        reconciled_rejection=False
        if last.get('status')=='error' and last.get('error')=='native_construction_rejected' and last.get('evidence'):
            workflow=json.loads(Path(last['evidence']).read_text(encoding='utf-8-sig'))
            attempts=workflow.get('attempts',[])
            if len(attempts)==1:
                rp=Path(last['evidence']).parent/(attempts[0]['request_id']+'.reconciliation.json')
                if rp.exists():
                    rr=json.loads(rp.read_text(encoding='utf-8-sig'))
                    reconciled_rejection=(rr.get('status')=='reconciled_rejected_corridor' and rr.get('completed_corridor_absent') is True
                        and rr.get('automatic_replay') is False and rr.get('original_pending',{}).get('request_id')==attempts[0]['request_id'])
        if (prepared.get('plan')!=plan or s.get('status') not in ('no_accepted_candidate','error') or s.get('stage')!='reference'
                or names!=plan['operations'][:8] or any(o.get('response',{}).get('status')!='ok' for o in prepared['operations'][:7])
                or not (safe_fit_failure or reconciled_rejection)):
            raise ValueError('prepared recipe must be this exact plan stopped before reference build')
    path=client.evidence/(uuid.uuid4().hex+'.recipe.json');lock=client.evidence/'recipe.lock'
    summary={'status':'incomplete','operation':'junction-recipe','stage':'start','game_constructed':False,
             'plan_hash':plan['plan_hash'],'completed_operations':0,'routes_verified':0,'evidence':str(path.resolve()),'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'operations':[]}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one recipe execution at a time') from None
    def perform(name,call):
        summary['stage']=name;atomic_json(path,record);r=call();record['operations'].append({'name':name,'response':r});atomic_json(path,record)
        constructed=r.get('game_constructed',r.get('result',{}).get('game_constructed'))
        if constructed in (True,'unknown'):summary['game_constructed']=constructed
        if r['status']!='ok':
            raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error',name+' failed')))
        summary['completed_operations']+=1;atomic_json(path,record);return r
    try:
        atomic_json(path,record)
        observed=perform('discover_asset',lambda:discover(client,{'region':plan['brief']['asset_region'],'max_edges':16}))
        if observed['result'].get('complete') is not True:raise LiveError('discovery_incomplete','asset query was truncated')
        assets={c['edge_id']:c['edge_snapshot'] for c in observed['result']['candidates']}
        if not assets:raise LiveError('asset_unavailable','no actual native TRACK in asset_region')
        if len({(e['template'],e['style']) for e in assets.values()})!=1:raise LiveError('asset_choice_ambiguous','asset_region contains different track resource families')
        seed=min(assets);r=perform('inspect_asset',lambda:client.request('inspect',{'edge_ids':[seed],'resources':True}))
        if r['result']['edges'][0].get('resource',{}).get('track_distance')!=5:raise LiveError('unsupported_recipe','actual native template trackDistance is not5')
        record['selected_asset']=r['result']['edges'][0];fixtures={}
        retained={}
        if prepared:
            old=[o['response']['result']['edges'][0] for o in prepared['operations'][2:7]]
            r=client.request('inspect',{'edge_ids':[e['id'] for e in old]})
            record['prepared_reacquisition']={'request_id':r['request_id'],'original_record':str(Path(prepared_record).resolve())}
            if r['status']!='ok' or r['result'].get('edges')!=old:raise LiveError('stale_prepared_recipe','prepared stubs differ from fresh exact native state')
            retained=dict(zip([f['name'] for f in plan['fixtures']],old))
        for f in plan['fixtures']:
            q={'authorised':True,'length':f['length'],'fixture':{'template_edge':seed,'position':f['position'],'travel_direction':f['travel_direction'],'grade':0,'region':f['region']}}
            r=perform('prepare_'+f['name'],lambda q=q,f=f:({'status':'ok','result':{'edges':[retained[f['name']]],'game_constructed':True},'reused_prepared':True,'fresh_observation':record['prepared_reacquisition']['request_id']} if f['name'] in retained else client.request('test_approach',q)))
            rows=r['result'].get('edges',[])
            if len(rows)!=1 or rows[0].get('road_type')!='TRACK':raise LiveError('native_verification_failed','fixture TRACK identity unavailable')
            fixtures[f['name']]=rows[0]
        perform('reference',lambda:connect_corridor(client,plan['reference'],execute=True))
        fanout=perform('fanout',lambda:connect_corridor(client,plan['fanout'],execute=True))
        observed=perform('native_guides',lambda:client.request('inspect',{'edge_ids':fanout['edges']}))
        b=_recipe_throat_brief(plan,fixtures,observed['result']['edges'])
        roles=b['roles'];z=plan['brief']['origin'][2]
        record['throat_brief']=b;result=perform('throat',lambda:connect_throat(client,b,execute=True))
        summary['routes_verified']=result['routes_verified']
        if result.get('final_network_verified') is not True or result['routes_verified']!=5:raise LiveError('native_verification_failed','five final movements not verified')
        summary['stage']='fresh_approach_spacing';atomic_json(path,record)
        # Fresh exact route/edge identities after every native split; no remembered entity mapping.
        a,_=_select_throat_port(client,roles['A1']['endpoint'],outward_sign=-1)
        a2,_=_select_throat_port(client,roles['A2']['endpoint'],outward_sign=-1)
        points=[plan['reference']['source']['guide_xyz'],plan['fanout']['source']['guide_xyz']]
        h=math.radians(plan['brief']['heading_deg']);n=[-math.sin(h),math.cos(h)];d=[math.cos(h),math.sin(h)]
        def close(q):return {'region':{'min':[q[0]-1,q[1]-1,z-1],'max':[q[0]+1,q[1]+1,z+1]},'guide_xyz':q,'travel_direction':d,'max_edges':8,'heading_tolerance_deg':2}
        q=[points[0][i]+50*(d[i] if i<2 else 0) for i in range(3)];q2=[points[1][i]+50*(d[i] if i<2 else 0) for i in range(3)]
        ref,rid=_select_throat_port(client,close(q),interior=True,tolerance=.5);adj,rid2=_select_throat_port(client,close(q2),interior=True,tolerance=.5)
        spacing=sum((adj['pos'][i]-ref['pos'][i])*n[i] for i in range(2))
        if abs(spacing-5)>.1 or ref['edge_id']==adj['edge_id'] or a['node_id']==a2['node_id']:raise LiveError('native_verification_failed','retained independent5m approach not established')
        record['approach_observations']=[rid,rid2];record['retained_approach']={'sampled_signed_spacing':spacing,'source_nodes':[a['node_id'],a2['node_id']],'continuous_proof':False}
        record['operations'].append({'name':'fresh_approach_spacing','response':{'status':'ok','observations':[rid,rid2],'spacing':spacing}});summary['completed_operations']+=1
        summary.update(status='ok',stage='verified',final_network_verified=True,route_matrix=result['route_matrix'],
                       retained_approach_spacing=spacing,direct5m_crossover=False,geometry_sampled_only=True,native_effect_history_complete=False)
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
    finally:
        atomic_json(path,record);lock.unlink()
    return summary


def _load_recipe_record(invocation):
    source=Path(invocation).resolve()
    raw=source.read_bytes();record=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(record,dict):raise ValueError('recipe invocation must be an object')
    # CLI summaries point at the full record; callers need not extract nested briefs.
    if 'plan' not in record and record.get('operation')=='junction-recipe' and record.get('evidence'):
        source=Path(record['evidence']).resolve();raw=source.read_bytes();record=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(record,dict) or not isinstance(record.get('summary',{}),dict):raise ValueError('recipe invocation/summary must be objects')
    if record.get('summary',{}).get('operation')=='junction-recipe-inspect':
        expected=record['original_sha256'];source=Path(record['original_record']).resolve();raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('original recipe changed since inspection')
        record=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(record,dict) or not isinstance(record.get('plan'),dict):raise ValueError('recipe invocation has no plan')
    plan=record['plan']
    if plan!=plan_junction_recipe(plan.get('brief')):raise ValueError('recipe invocation plan differs from deterministic brief')
    if not isinstance(record.get('operations'),list) or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in record['operations']):raise ValueError('recipe invocation operations missing or malformed')
    return record,source,hashlib.sha256(raw).hexdigest()


def _recipe_intent(plan,position,direction):
    return {'region':{'min':[q-1 for q in position],'max':[q+1 for q in position]},
            'guide_xyz':position,'travel_direction':direction,'max_edges':8,'heading_tolerance_deg':2}


def _recipe_spacing(client,plan,roles):
    h=math.radians(plan['brief']['heading_deg']);d=[math.cos(h),math.sin(h)];normal=[-d[1],d[0]]
    ports=[];observations=[]
    for name in ('reference','fanout'):
        p=plan[name]['source']['guide_xyz'];q=[p[0]+50*d[0],p[1]+50*d[1],p[2]]
        c,rid=_select_throat_port(client,_recipe_intent(plan,q,d),interior=True,tolerance=.5)
        ports.append(c);observations.append(rid)
    origins=[plan[name]['source']['guide_xyz'] for name in ('reference','fanout')]
    lines=[]
    for port,origin in zip(ports,origins):
        e=port['edge_snapshot'];chord=[e['p1'][i]-e['p0'][i] for i in range(3)]
        if any(abs(e[k][i]-chord[i])>.001 for k in ('t0','t1') for i in range(3)):
            raise LiveError('native_verification_failed','retained approach is not straight')
        x=[sum((e[k][i]-origin[i])*d[i] for i in range(2)) for k in ('p0','p1')]
        if min(x)>.001 or max(x)<99.999 or abs(x[1]-x[0])<99.999:
            raise LiveError('native_verification_failed','complete100-unit retained approach not established')
        lines.append((e,x))
    spacing=[]
    for j in range(17):
        points=[]
        for e,x in lines:
            u=(100*j/16-x[0])/(x[1]-x[0]);points.append([e['p0'][i]+u*(e['p1'][i]-e['p0'][i]) for i in range(3)])
        spacing.append(sum((points[1][i]-points[0][i])*normal[i] for i in range(2)))
    if any(abs(x-5)>.1 for x in spacing) or ports[0]['edge_id']==ports[1]['edge_id'] or roles['A1']['node_id']==roles['A2']['node_id']:
        raise LiveError('native_verification_failed','retained independent5m approach not established')
    return {'sampled_signed_spacing':spacing[8],'spacing_min':min(spacing),'spacing_max':max(spacing),'samples':17,
            'source_nodes':[roles['A1']['node_id'],roles['A2']['node_id']],
            'observations':observations,'continuous_proof':False}



def _recipe_junction(client,intent):
    """Position chooses an observation; exact incidence establishes current identity."""
    r=discover(client,{k:intent[k] for k in ('region','max_edges')})
    if r['status']!='ok' or r['result'].get('complete') is not True:
        raise LiveError('discovery_incomplete','junction observation failed or truncated')
    nodes={c['node_id']:c for c in r['result']['candidates'] if c.get('incident_count')==3
           and c.get('incidence_complete') is True and not c.get('incident_output_truncated')
           and math.dist(c['pos'],intent['guide_xyz'])<=.5}
    if len(nodes)!=1:raise LiveError('recipe_state_unknown','one current exact three-edge junction not established')
    c=next(iter(nodes.values()))
    current=client.request('inspect',{'edge_ids':c['incident_edges']})
    if current['status']!='ok' or len(current['result'].get('edges',[]))!=3 or any(
            e.get('road_type')!='TRACK' or c['node_id'] not in (e['node0'],e['node1']) for e in current['result']['edges']):
        raise LiveError('recipe_state_unknown','current junction TRACK incidence not established')
    return c['node_id'],[r['request_id'],current['request_id']]


def _assess_recipe(client,original):
    plan=original['plan'];state={'roles':{},'routes':[],'steps':{},'observations':[],'blockers':[]}
    # Reacquire all named interfaces from the fixed brief. Old numeric IDs are not authority.
    for f in plan['fixtures']:
        approach=f['name'].startswith('A');q=list(f['position']) if approach else [
            f['position'][i]+f['length']*(f['travel_direction'][i] if i<2 else 0) for i in range(3)]
        intent=_recipe_intent(plan,q,f['travel_direction'])
        try:
            c,rid=_select_throat_port(client,intent,tolerance=.5,outward_sign=-1 if approach else 1)
            state['roles'][f['name']]=c;state['observations'].append(rid)
        except LiveError as exc:
            current='unknown'
            if exc.status=='no_eligible_candidates':
                observed=discover(client,{'region':f['region'],'max_edges':16});state['observations'].append(observed['request_id'])
                if observed['status']=='ok' and observed['result'].get('complete') is True and observed['result'].get('edge_count')==0:current='absent'
            state['steps']['prepare_'+f['name']]={'state':current,'blocker':exc.status}
            state['blockers'].append('prepare_'+f['name']+':'+current+':'+exc.status)
    if len(state['roles'])!=5:return state
    if len({c['node_id'] for c in state['roles'].values()})!=5:raise LiveError('recipe_state_unknown','recipe roles share an attachment')
    # Whole current fixture geometry/resources must still match the authored interfaces,
    # even if native IDs were replaced or reused since the original invocation.
    for f in plan['fixtures']:
        c=state['roles'][f['name']];e=c['edge_snapshot'];end=[f['position'][i]+f['length']*(f['travel_direction'][i] if i<2 else 0) for i in range(3)]
        pairs=((e['p0'],e['p1']),(e['p1'],e['p0']))
        if e.get('road_type')!='TRACK' or not any(math.dist(a,f['position'])<=.001 and math.dist(b,end)<=.001 for a,b in pairs):
            raise LiveError('recipe_state_changed','current interface geometry differs from recipe')
        old=next((o['response']['result']['edges'][0] for o in original['operations'] if o.get('name')=='prepare_'+f['name'] and o.get('response',{}).get('status')=='ok'),None)
        if old and any(e.get(k)!=old.get(k) for k in ('template','style')):
            raise LiveError('recipe_state_changed','current interface native assets differ from recorded recipe')
        chord=[e['p1'][i]-e['p0'][i] for i in range(3)]
        if any(abs(e[k][i]-chord[i])>.001 for k in ('t0','t1') for i in range(3)):
            raise LiveError('recipe_state_changed','current interface is not the authored straight level fixture')
        state['steps']['prepare_'+f['name']]={'state':'completed','current_edge':e['id'],'current_node':c['node_id']}
    constraints={'all_path':True,'edge_ids':[],'region':plan['brief']['region'],'radius':120,'max_grade':plan['brief']['max_grade']}
    for row in plan['required_routes']:
        a,b=(state['roles'][row[k]] for k in ('from','to'))
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],'target_node':b['node_id'],
           'mode':'TRAIN','required_edges':[a['edge_id'],b['edge_id']],'max_length':2500,'geometry_constraints':constraints}
        r=client.request('route',q);v=r.get('result',{});accepted=r['status']=='ok' and v.get('requested_route_verified') is True
        state['routes'].append(row|{'request_id':r['request_id'],'verified':accepted,'response':r})
        if r['status']!='ok':state['blockers'].append(row['from']+'->'+row['to']+':'+v.get('error',r['status']))
    movements={(r['from'],r['to']):r['verified'] for r in state['routes']}
    for name,pair in [('reference',('A1','D1')),('fanout',('A2','D2')),('cross',('A1','D2')),('branch',('A2','D3'))]:
        row=next(r for r in state['routes'] if (r['from'],r['to'])==pair)
        state['steps'][name]={'state':'completed' if movements[pair] else ('failed' if row['response']['status']!='ok' else 'unknown')}
    # Use only the original native-produced guide geometry, never its old identities.
    b=original.get('throat_brief')
    if b:
        fixtures={o['name'][8:]:o['response']['result']['edges'][0] for o in original['operations']
                  if o.get('name','').startswith('prepare_') and o.get('response',{}).get('status')=='ok'}
        guide=next((o['response']['result']['edges'] for o in original['operations'] if o.get('name')=='native_guides' and o['response'].get('status')=='ok'),None)
        if len(fixtures)!=5 or guide is None or b!=_recipe_throat_brief(plan,fixtures,guide):raise ValueError('recorded throat intent differs from native guide receipt')
        state['throat_brief']=b
        # Completed steps must exist at intended joins with exact current incidence.
        nodes={}
        for step in b['steps']:
            if state['steps'][step['name']]['state']=='completed':
                intents=[step['source']]+([step['target']] if step['kind']=='crossover' else [])
                nodes[step['name']]=[]
                for intent in intents:
                    node,ids=_recipe_junction(client,intent);nodes[step['name']].append(node);state['observations']+=ids
        for row in state['routes']:
            if row['verified']:
                path=row['response']['result']['path'];actual={x[k]['entity'] for x in path for k in ('from','to')}
                if any(n not in actual for via in row['via'] for n in nodes.get(via,[])):
                    raise LiveError('recipe_state_changed','native route bypasses required intended junction')
    if not state['blockers']:
        for name in ('reference','fanout'):
            if state['steps'][name]['state']=='unknown':
                try:
                    for key,sign in [('source',1),('target',-1)]:
                        c,rid=_select_throat_port(client,plan[name][key],tolerance=.5,outward_sign=sign);state['observations'].append(rid)
                    state['steps'][name]={'state':'absent','basis':'fresh exact free inner attachments'}
                except LiveError as exc:state['steps'][name]['blocker']=exc.status
        if b and all(state['steps'][n]['state']=='completed' for n in ('reference','fanout')):
            for step in b['steps']:
                if state['steps'][step['name']]['state']=='unknown':
                    try:
                        c,rid=_select_throat_port(client,step['source'],interior=True,tolerance=.5);state['observations'].append(rid)
                        c,rid=_select_throat_port(client,step['target'],interior=step['kind']=='crossover',tolerance=.5);state['observations'].append(rid)
                        state['steps'][step['name']]={'state':'absent','basis':'fresh unsplit through and exact available target'}
                    except LiveError as exc:state['steps'][step['name']]['blocker']=exc.status
    if all(r['verified'] for r in state['routes']) and not b:state['blockers'].append('native throat guide receipt missing')
    if all(r['verified'] for r in state['routes']):state['retained_approach']=_recipe_spacing(client,plan,state['roles'])
    return state


def inspect_junction_recipe(client,invocation):
    """Fresh read-only recipe assessment; writes a new evidence receipt only."""
    original,source,digest=_load_recipe_record(invocation);path=client.evidence/(uuid.uuid4().hex+'.recipe_inspection.json')
    summary={'status':'incomplete','operation':'junction-recipe-inspect','game_constructed':False,'mutations':0,
             'plan_hash':original['plan']['plan_hash'],'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':original['plan'],'original_record':str(source),'original_sha256':digest,'summary':summary}
    try:
        state=_assess_recipe(client,original);record['assessment']=state
        summary['routes_verified']=sum(r['verified'] for r in state['routes'])
        complete=len(state['routes'])==5 and summary['routes_verified']==5 and not state['blockers']
        summary.update(status='ok' if complete else 'recipe_incomplete',final_network_verified=complete,
                       current_steps={k:v['state'] for k,v in state['steps'].items()},blockers=state['blockers'],geometry_sampled_only=True)
        if complete:summary['retained_approach_spacing']=state['retained_approach']['sampled_signed_spacing']
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:atomic_json(path,record)
    return summary


def _recipe_uncertain_operations(original):
    uncertain=['unfinished_'+original['pending_recipe_step']] if original.get('pending_recipe_step') else []
    for o in original['operations']:
        r=o['response'];v=r.get('result',{})
        if r.get('game_constructed',v.get('game_constructed'))!='unknown' and r.get('status')!='mutation_unverified':continue
        evidence=r.get('evidence');requests=[]
        if evidence:
            full=json.loads(Path(evidence).read_text(encoding='utf-8-sig'))
            requests=[a.get('request_id') for a in full.get('attempts',[])]
            requests += [a.get('request_id') for a in full.get('steps',[]) if a.get('response',{}).get('result',{}).get('game_constructed')=='unknown']
        reconciled=bool(requests)
        for rid in requests:
            rp=Path(evidence).parent/(str(rid)+'.reconciliation.json')
            rr=json.loads(rp.read_text()) if rp.exists() else {}
            reconciled=reconciled and rr.get('original_pending',{}).get('request_id')==rid and rr.get('automatic_replay') is False and (
                rr.get('completed_corridor_absent') is True or rr.get('completed_crossover_absent') is True)
        if not reconciled:uncertain.append(o.get('name','unnamed'))
    return uncertain


def continue_junction_recipe(client,invocation):
    """Explicit checked continuation, never trust old IDs or replay uncertain work."""
    original,source,digest=_load_recipe_record(invocation);plan=original['plan']
    path=client.evidence/(uuid.uuid4().hex+'.recipe.json');lock=client.evidence/'recipe.lock'
    record={'plan':plan,'original_record':str(source),'original_sha256':digest,'operations':list(original['operations'])}
    if original.get('throat_brief'):record['throat_brief']=original['throat_brief']
    summary={'status':'incomplete','operation':'junction-recipe','stage':'assessment','game_constructed':False,
             'plan_hash':plan['plan_hash'],'evidence':str(path.resolve()),'routes_verified':0,'new_mutations':0,
             'train_traversal':'unprobed','automatic_replay':False}
    record['summary']=summary
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one recipe execution at a time') from None
    def perform(name,call):
        summary['stage']=name;summary['new_mutations']+=1;record['pending_recipe_step']=name;atomic_json(path,record)
        r=call();record['operations'].append({'name':name,'response':r});record.pop('pending_recipe_step');atomic_json(path,record)
        if r.get('game_constructed',r.get('result',{}).get('game_constructed')) in (True,'unknown'):summary['game_constructed']=r.get('game_constructed',r.get('result',{}).get('game_constructed'))
        if r['status']!='ok':raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error','recipe step failed')))
        return r
    try:
        atomic_json(path,record)
        assessed=inspect_junction_recipe(client,source);record['inspection']=assessed
        state=json.loads(Path(assessed['evidence']).read_text()).get('assessment',{})
        if assessed['status']!='ok':
            if assessed['status']!='recipe_incomplete' or state.get('blockers') or len(state.get('roles',{}))!=5:
                raise LiveError('recipe_state_unknown',assessed.get('error','complete current interfaces/observations required'))
            if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):
                raise LiveError('reconciliation_required','unfinished native operation; explicit reconciliation required before continuation')
            uncertain=_recipe_uncertain_operations(original)
            if uncertain:raise LiveError('reconciliation_required','unresolved recipe effects: '+','.join(uncertain))
            for name in ('reference','fanout'):
                current=state['steps'][name]['state']
                if current=='absent':perform(name,lambda name=name:connect_corridor(client,plan[name],execute=True))
                elif current!='completed':raise LiveError('recipe_state_unknown',name+' not proven completed or absent')
            b=state.get('throat_brief')
            if not b:
                # Current fanout route IDs provide native geometry for the guides.
                fresh=_assess_recipe(client,record)
                row=next(r for r in fresh['routes'] if r['from']=='A2' and r['to']=='D2')
                if not row['verified']:raise LiveError('native_verification_failed','current fanout not verified')
                ids=list(dict.fromkeys(x['edge']['entity'] for x in row['response']['result']['path'] if x['confirmed_TRACK']))
                if len(ids)>16:raise LiveError('recipe_state_unknown','fanout guide observation exceeds16edges')
                r=client.request('inspect',{'edge_ids':ids});record['operations'].append({'name':'native_guides','response':r})
                if r['status']!='ok':raise LiveError('recipe_state_unknown','native fanout guide unavailable')
                fixtures={f['name']:fresh['roles'][f['name']]['edge_snapshot'] for f in plan['fixtures']}
                b=_recipe_throat_brief(plan,fixtures,r['result']['edges']);record['throat_brief']=b
                fresh=_assess_recipe(client,record);state=fresh
            else:record['throat_brief']=b
            if state['steps']['cross']['state']=='absent' and state['steps']['branch']['state']=='absent':
                perform('throat',lambda:connect_throat(client,b,execute=True))
            elif state['steps']['cross']['state']=='completed' and state['steps']['branch']['state']=='absent':
                # Reacquired exact current junctions are needed for trimmed native route rows.
                junctions=[_recipe_junction(client,x)[0] for x in (b['steps'][0]['source'],b['steps'][0]['target'])]
                q={k:b[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length','placement_tolerance')}
                q.update(source=b['steps'][1]['source'],target=b['steps'][1]['target'])
                perform('branch',lambda:connect_junction_at(client,q,execute=True,junction_nodes=junctions))
            elif not all(state['steps'][n]['state']=='completed' for n in ('cross','branch')):
                raise LiveError('recipe_state_unknown','throat step is not safely absent; no resubmission')
            atomic_json(path,record)
            assessed=inspect_junction_recipe(client,path);record['final_inspection']=assessed
            if assessed['status']!='ok':raise LiveError('native_verification_failed',assessed.get('error','current recipe requirements not met'))
        summary.update(status='ok',stage='verified',routes_verified=5,final_network_verified=True,
                       retained_approach_spacing=assessed['retained_approach_spacing'],existing_network_verified=True,
                       geometry_sampled_only=True,native_effect_history_complete=False)
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
    finally:atomic_json(path,record);lock.unlink()
    return summary


PARALLEL_LAYOUT = 'ordered_parallel_branches_v1'


def plan_parallel_layout(brief):
    """Ordered traffic intent; UP/DOWN never describe native parameter orientation."""
    keys={'layout','route_reference','tracks','movements','spacing','radius','max_grade','region','asset_region'}
    if not isinstance(brief,dict) or set(brief)!=keys:raise ValueError('parallel layout brief fields mismatch')
    if brief['layout']!=PARALLEL_LAYOUT:raise LiveError('unsupported_layout','only '+PARALLEL_LAYOUT+' is supported')
    ref=brief['route_reference']
    if not isinstance(ref,dict) or set(ref)!={'origin','heading_deg','up'} or ref['up'] not in ('increasing','decreasing'):
        raise ValueError('route_reference requires origin, heading_deg and explicit UP increasing/decreasing')
    # Reuse current frame/region/engineering validation; no new world/scale model.
    frame={'origin':ref['origin'],'heading_deg':ref['heading_deg'],'spacing':brief['spacing'],'radius':brief['radius'],
           'max_grade':brief['max_grade'],'region':brief['region'],'asset_region':brief['asset_region']}
    _validate_native_frame(frame,unsupported='unsupported_layout')
    tracks=brief['tracks']
    if not isinstance(tracks,list) or len(tracks) not in (2,4) or any(not isinstance(t,dict) or set(t)!={'id','direction'}
            or not isinstance(t['id'],str) or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,15}',t['id']) is None
            or t['direction'] not in ('UP','DOWN') for t in tracks):raise ValueError('tracks require2or4ordered unique IDs and UP/DOWN intent')
    if len({t['id'] for t in tracks})!=len(tracks):raise ValueError('track IDs must be unique')
    pattern='-'.join(t['direction'] for t in tracks)
    if pattern not in ('UP-DOWN','UP-DOWN-UP-DOWN','UP-UP-DOWN-DOWN'):raise LiveError('unsupported_pattern','approved ordered patterns are UP-DOWN, UP-DOWN-UP-DOWN, UP-UP-DOWN-DOWN')
    h=math.radians(ref['heading_deg']);d=[math.cos(h),math.sin(h)];o=ref['origin']
    def pos(x,y):return [o[0]+x*d[0]-y*d[1],o[1]+x*d[1]+y*d[0],o[2]]
    ports={};fixtures=[];corridors=[];expected=[]
    for i,t in enumerate(tracks):
        y=5*i;sign=(1 if t['direction']=='UP' else -1)*(1 if ref['up']=='increasing' else -1)
        for end,x in [('west',-20),('east',1220)]:
            name=t['id']+':'+end;q=pos(x,y);ports[name]={'track':t['id'],'end':end,'position':q,
                'running_direction':t['direction'],'travel_direction':[sign*z for z in d],
                'function':'entry' if (end=='west')==(sign==1) else 'exit'}
        for end,x in [('west',-20),('east',1200)]:
            q=pos(x,y);fixtures.append({'name':t['id']+':'+end,'position':q,'travel_direction':d,'length':20,
                'region':{'min':[max(q[k]-40,brief['region']['min'][k]) for k in range(3)],'max':[min(q[k]+40,brief['region']['max'][k]) for k in range(3)]}})
        a,b=(t['id']+':west',t['id']+':east') if sign==1 else (t['id']+':east',t['id']+':west');expected.append({'from':a,'to':b})
        corridors.append({'name':t['id'],'source':_recipe_intent(frame,pos(0,y),d),'target':_recipe_intent(frame,pos(1200,y),d),
                          'guides':[{'position':pos(600,y),'travel_direction':d,'grade':0}]})
    branches=[]
    for name,t,y,by in [('branch_up',tracks[0],0,-250),('branch_down',tracks[-1],5*(len(tracks)-1),5*(len(tracks)-1)+250)]:
        q=pos(1000,by);sign=(1 if t['direction']=='UP' else -1)*(1 if ref['up']=='increasing' else -1)
        ports[name]={'track':t['id'],'end':'branch','position':pos(1020,by),'running_direction':t['direction'],
                     'travel_direction':[sign*z for z in d],'function':'exit' if sign==1 else 'entry'}
        fixtures.append({'name':name,'position':q,'travel_direction':d,'length':20,
                         'region':{'min':[max(q[k]-40,brief['region']['min'][k]) for k in range(3)],'max':[min(q[k]+40,brief['region']['max'][k]) for k in range(3)]}})
        expected.append({'from':t['id']+':west','to':name} if sign==1 else {'from':name,'to':t['id']+':west'})
        branches.append({'name':name,'source':_recipe_intent(frame,pos(400,y),d),'target':_recipe_intent(frame,q,d)})
    movements=brief['movements']
    if not isinstance(movements,list) or not movements or any(not isinstance(row,dict) or set(row)!={'from','to'} for row in movements):raise ValueError('explicit directed movement matrix required')
    for row in movements:
        if row['from'] not in ports or row['to'] not in ports:raise ValueError('movement references unknown functional port')
        a,b=ports[row['from']],ports[row['to']]
        if a['function']!='entry' or b['function']!='exit' or a['running_direction']!=b['running_direction']:
            raise LiveError('against_running_direction','movement conflicts with declared running direction')
        if row not in expected:raise LiveError('unsupported_movement','v1 provides same-track through and outer branches; no cross-track switch/crossing')
    if len(movements)!=len(expected) or {tuple(sorted(r.items())) for r in movements}!={tuple(sorted(r.items())) for r in expected}:
        raise ValueError('matrix must explicitly include every through track and both outer branch functions once')
    corners=[pos(x,y) for x,y in [(-60,-300),(1260,-300),(1260,5*(len(tracks)-1)+300),(-60,5*(len(tracks)-1)+300)]]
    footprint={'min':[min(q[i] for q in corners) for i in range(2)]+[o[2]-1],'max':[max(q[i] for q in corners) for i in range(2)]+[o[2]+1]}
    if any(footprint['min'][i]<brief['region']['min'][i] or footprint['max'][i]>brief['region']['max'][i] for i in range(3)):raise LiveError('unsupported_layout','authorised region excludes outward branch footprint')
    plan={'version':1,'layout':PARALLEL_LAYOUT,'brief':brief,'epoch':'DESIGN','pattern':pattern,
          'order_convention':'increasing left-normal offset when looking along increasing route reference',
          'ports':ports,'fixtures':fixtures,'corridors':corridors,'branches':branches,'movements':movements,'footprint':footprint,
          'native_execution_supported':pattern=='UP-UP-DOWN-DOWN' and ref['up']=='increasing','native_runtime_demonstrated':False,
          'native_construction_direction':d,'direction_enforcement':'not_provided','train_traversal':'unprobed',
          'game_constructed':False,'limitations':['fixed level geometry/radius120/spacing5','outer branches only; no cross-track switching','native execution initially UUDD with increasing UP only']}
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_parallel_layout(plan,evidence):
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel plan differs from deterministic brief')
    path=Path(evidence)/(uuid.uuid4().hex+'.parallel_plan.json');path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,plan)
    return {'status':'ok','operation':'parallel-layout','stage':'plan','pattern':plan['pattern'],'plan_hash':plan['plan_hash'],
            'native_execution_supported':plan['native_execution_supported'],'native_runtime_demonstrated':False,'game_constructed':False,
            'movements':plan['movements'],'direction_enforcement':'not_provided','evidence':str(path.resolve())}


def _verify_parallel_layout(client,plan,record):
    ports={};observations=[];d=plan['native_construction_direction'];ref=plan['brief']['route_reference']
    for name,p in plan['ports'].items():
        c,rid=_select_throat_port(client,_recipe_intent(plan,p['position'],d),tolerance=.5,
                                  outward_sign=-1 if p['end']=='west' else 1)
        ports[name]=c;observations.append(rid)
    if len({c['node_id'] for c in ports.values()})!=len(ports):raise LiveError('native_verification_failed','functional ports share current native attachment')
    nodes={}
    for b in plan['branches']:
        node,rids=_recipe_junction(client,b['source']);nodes[b['name']]=node;observations+=rids
    routes=[]
    for row in plan['movements']:
        a,b=(ports[row[k]] for k in ('from','to'))
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],'target_node':b['node_id'],
           'mode':'TRAIN','required_edges':[a['edge_id'],b['edge_id']],'max_length':2500,
           'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':120,'region':plan['brief']['region'],'max_grade':plan['brief']['max_grade']}}
        r=client.request('route',q);v=r.get('result',{});accepted=r['status']=='ok' and v.get('requested_route_verified') is True
        current_nodes={x[k]['entity'] for x in v.get('path',[]) for k in ('from','to')}
        via=next((name for name in nodes if name in (row['from'],row['to'])),None)
        if via and nodes[via] not in current_nodes:accepted=False
        routes.append(row|{'verified':accepted,'request_id':r['request_id'],'response':r})
        record['routes']=routes;atomic_json(Path(record['summary']['evidence']),record)
        if not accepted:raise LiveError('native_verification_failed','required intended movement not verified: '+row['from']+'->'+row['to'])
    spacing=[];normal=[-d[1],d[0]];lines=[]
    for i,t in enumerate(plan['brief']['tracks']):
        o=ref['origin'];q=[o[0]+50*d[0]+5*i*normal[0],o[1]+50*d[1]+5*i*normal[1],o[2]]
        c,rid=_select_throat_port(client,_recipe_intent(plan,q,d),interior=True,tolerance=.5);observations.append(rid);e=c['edge_snapshot']
        chord=[e['p1'][k]-e['p0'][k] for k in range(3)]
        if any(abs(e[k][j]-chord[j])>.001 for k in ('t0','t1') for j in range(3)):raise LiveError('native_verification_failed','retained parallel approach is not straight')
        origin=[o[0]+5*i*normal[0],o[1]+5*i*normal[1],o[2]]
        x=[sum((e[k][j]-origin[j])*d[j] for j in range(2)) for k in ('p0','p1')]
        if min(x)>.001 or max(x)<99.999:raise LiveError('native_verification_failed','retained100-unit approach incomplete')
        lines.append((e,x))
    if len({e['id'] for e,x in lines})!=len(lines):raise LiveError('native_verification_failed','ordered tracks share an approach edge')
    for i in range(len(lines)-1):
        values=[]
        for j in range(17):
            points=[]
            for e,x in lines[i:i+2]:
                u=(j*100/16-x[0])/(x[1]-x[0]);points.append([e['p0'][k]+u*(e['p1'][k]-e['p0'][k]) for k in range(3)])
            values.append(sum((points[1][k]-points[0][k])*normal[k] for k in range(2)))
        if any(abs(x-5)>.1 for x in values):raise LiveError('native_verification_failed','ordered native spacing differs from5')
        spacing.append({'tracks':[plan['brief']['tracks'][i]['id'],plan['brief']['tracks'][i+1]['id']],'min':min(values),'max':max(values),'samples':17})
    record.update(current_ports=ports,current_junction_nodes=nodes,observations=observations,retained_spacing=spacing)
    return {'routes_verified':len(routes),'final_network_verified':True,'retained_spacing':spacing,
            'direction_intent_compatible':True,'direction_enforcement':'not_provided','geometry_sampled_only':True,'native_runtime_demonstrated':True}


def inspect_parallel_layout(client,invocation):
    original=json.loads(Path(invocation).read_text(encoding='utf-8-sig'))
    if 'plan' not in original and original.get('evidence'):original=json.loads(Path(original['evidence']).read_text(encoding='utf-8-sig'))
    plan=original['plan']
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel invocation plan differs from brief')
    path=client.evidence/(uuid.uuid4().hex+'.parallel_inspection.json')
    summary={'status':'incomplete','operation':'parallel-layout-inspect','game_constructed':False,'evidence':str(path.resolve()),'plan_hash':plan['plan_hash'],'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'original_record':str(Path(invocation).resolve()),'routes':[]}
    try:summary.update(_verify_parallel_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:atomic_json(path,record)
    return summary


def execute_parallel_layout(client,plan):
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel plan differs from deterministic brief')
    if not plan['native_execution_supported']:raise LiveError('unsupported_native_pattern','native execution is currently UUDD with increasing-reference UP; other patterns are planning evidence only')
    path=client.evidence/(uuid.uuid4().hex+'.parallel.json');lock=client.evidence/'parallel.lock'
    summary={'status':'incomplete','operation':'parallel-layout','stage':'asset','pattern':plan['pattern'],'game_constructed':False,'plan_hash':plan['plan_hash'],
             'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed','direction_enforcement':'not_provided'}
    record={'plan':plan,'summary':summary,'operations':[]}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one parallel layout at a time') from None
    def perform(name,call,mutation=False):
        summary['stage']=name;record['unfinished_step']=name;atomic_json(path,record);r=call()
        record['operations'].append({'name':name,'response':r});record.pop('unfinished_step');atomic_json(path,record)
        if mutation:
            effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
            if effect in (True,'unknown') or summary['game_constructed'] is not True:summary['game_constructed']=effect
        if r['status']!='ok':raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error','parallel stage failed')))
        return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise LiveError('reconciliation_required','unfinished native request; no layout construction')
        found=perform('discover_asset',lambda:discover(client,{'region':plan['brief']['asset_region'],'max_edges':16}))
        v=found['result'];assets={c['edge_id']:c['edge_snapshot'] for c in v['candidates']}
        if v.get('complete') is not True or not assets:raise LiveError('asset_unavailable','complete native asset observation required')
        if len({(e['template'],e['style']) for e in assets.values()})!=1:raise LiveError('asset_choice_ambiguous','mixed native track families')
        seed=min(assets);r=perform('inspect_asset',lambda:client.request('inspect',{'edge_ids':[seed],'resources':True}))
        if r['result']['edges'][0].get('resource',{}).get('track_distance')!=5:raise LiveError('unsupported_layout','native template spacing is not5')
        record['selected_asset']=r['result']['edges'][0]
        for f in plan['fixtures']:
            q={'authorised':True,'length':20,'fixture':{'template_edge':seed,'position':f['position'],'travel_direction':f['travel_direction'],'grade':0,'region':f['region']}}
            perform('prepare_'+f['name'],lambda q=q:client.request('test_approach',q),True)
        common={'radius':120,'region':plan['brief']['region'],'vertical':{'max_grade':plan['brief']['max_grade']},'max_fit_attempts':1,'max_route_length':2500}
        for b in plan['corridors']:perform('through_'+b['name'],lambda b=b:connect_corridor(client,common|{k:b[k] for k in ('source','target','guides')},execute=True),True)
        junctions=[]
        for b in plan['branches']:
            r=perform(b['name'],lambda b=b:connect_junction_at(client,common|{'placement_tolerance':.5,'source':b['source'],'target':b['target']},execute=True,junction_nodes=junctions),True)
            junctions.append(r['junction']['node'])
        summary['stage']='fresh_intended_movements';summary.update(_verify_parallel_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
    finally:atomic_json(path,record);lock.unlink()
    return summary


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
    p=pending['params']
    if 'fixture' in p:
        q=p['fixture'];pos=q['position'];direction=q['travel_direction']
        if (len(pos)!=3 or len(direction)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in pos+direction)
                or math.hypot(*direction)==0):raise ValueError('recorded native fixture seed is malformed')
        b={'anchor_edge':q['template_edge'],'end_xy':pos[:2],'end_direction':direction,'region':q['region']}
        matches=[c for c in discovery['result']['candidates'] if c['edge_id']==b['anchor_edge']]
        if matches and all(c['edge_snapshot']==matches[0]['edge_snapshot'] for c in matches):matches=matches[:1]
    else:
        b=p['brief'];validate_brief(b)
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
    parser.add_argument('operation', choices=sorted(OPERATIONS | {'extend', 'connect', 'connect-selected', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent', 'junction-recipe', 'junction-recipe-inspect', 'junction-recipe-continue', 'parallel-layout', 'parallel-layout-inspect', 'reconcile-fixture'}))
    parser.add_argument('--params', required=True, type=Path)
    parser.add_argument('--reconciled-crossover', type=Path, help='explicit verified crossover evidence for connect-throat; rechecks read-only, never rebuilds it')
    parser.add_argument('--recipe-plan',type=Path,help='optional reviewed junction-recipe plan; must match current brief exactly')
    parser.add_argument('--prepared-recipe',type=Path,help='explicit matching recipe stopped before reference; fresh stubs checked, never automatically resumed')
    parser.add_argument('--layout-record',type=Path,help='saved parallel-layout invocation for fresh read-only current-state verification')
    parser.add_argument('--recipe-record',type=Path,help='recipe invocation or compact summary for fresh inspect/explicit checked continuation')
    parser.add_argument('--context', type=Path)
    parser.add_argument('--discovery', type=Path, help='saved full discover response for connect-selected')
    parser.add_argument('--execute', action='store_true', help='authorise native construction for extend/connect/connect-brief/connect-corridor')
    parser.add_argument('--mod-directory', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--session')
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    if args.operation in ('junction-recipe','parallel-layout') and not args.execute:
        try:
            if args.layout_record or args.recipe_record or args.recipe_plan or args.prepared_recipe or args.discovery or args.reconciled_crossover:raise ValueError('planning accepts a brief, not native continuation records')
            brief=json.loads(args.params.read_text(encoding='utf-8-sig'))
            response=(publish_junction_recipe(plan_junction_recipe(brief),args.evidence or Path('.local_runs/junction_recipes')) if args.operation=='junction-recipe' else publish_parallel_layout(plan_parallel_layout(brief),args.evidence or Path('.local_runs/parallel_layouts')))
        except (OSError,ValueError,LiveError,KeyError,TypeError) as exc:
            response={'status':getattr(exc,'status','invalid_recipe'),'error':str(exc)[:400],'game_constructed':False}
        print(json.dumps(response,separators=(',',':')));return 0 if response['status']=='ok' else 1
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
        if args.layout_record and args.operation!='parallel-layout-inspect':raise ValueError('--layout-record requires parallel-layout-inspect')
        if args.recipe_record and args.operation not in ('junction-recipe-inspect','junction-recipe-continue'):raise ValueError('--recipe-record requires recipe inspect/continue')
        if args.operation=='junction-recipe-continue' and not args.execute:raise ValueError('recipe continuation requires --execute')
        if args.recipe_plan and (args.operation!='junction-recipe' or not args.execute):raise ValueError('--recipe-plan requires junction-recipe --execute')
        if args.prepared_recipe and (args.operation!='junction-recipe' or not args.execute):raise ValueError('--prepared-recipe requires junction-recipe --execute')
        if args.reconciled_crossover and (args.operation!='connect-throat' or not args.execute):
            raise ValueError('--reconciled-crossover requires connect-throat --execute')
        if args.discovery and args.operation not in ('connect-selected','reconcile-fixture'):
            raise ValueError('--discovery is only for connect-selected/reconcile-fixture')
        if args.execute and args.operation not in ('extend', 'connect', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent', 'junction-recipe', 'junction-recipe-continue', 'parallel-layout'):
            raise ValueError('--execute is only for extend/connect/connect-brief/connect-corridor/connect-junction/connect-junction-at; low-level build uses explicit authorised parameter')
        if args.operation=='parallel-layout':
            response=execute_parallel_layout(client,plan_parallel_layout(params))
        elif args.operation=='parallel-layout-inspect':
            if not args.layout_record:raise ValueError('--layout-record is required')
            saved=json.loads(args.layout_record.read_text(encoding='utf-8-sig'))
            if 'plan' not in saved and saved.get('evidence'):saved=json.loads(Path(saved['evidence']).read_text(encoding='utf-8-sig'))
            if saved['plan']!=plan_parallel_layout(params):raise ValueError('layout record does not match current brief')
            response=inspect_parallel_layout(client,args.layout_record)
        elif args.operation in ('junction-recipe-inspect','junction-recipe-continue'):
            if not args.recipe_record:raise ValueError('--recipe-record is required')
            original,_,_=_load_recipe_record(args.recipe_record)
            if original['plan']!=plan_junction_recipe(params):raise ValueError('recipe record does not match current brief')
            response=(inspect_junction_recipe if args.operation=='junction-recipe-inspect' else continue_junction_recipe)(client,args.recipe_record)
        elif args.operation=='junction-recipe':
            plan=plan_junction_recipe(params)
            if args.recipe_plan and json.loads(args.recipe_plan.read_text(encoding='utf-8-sig'))!=plan:raise ValueError('reviewed recipe plan does not match current brief')
            response=execute_junction_recipe(client,plan,prepared_record=args.prepared_recipe)
        elif args.operation in ('extend', 'connect'):
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
