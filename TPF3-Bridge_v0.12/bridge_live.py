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
STATION_OPERATION = 'station_lookup'
OPERATIONS = {'scissors_candidate', 'degree_four_candidate', 'inspect_degree_four', 'inspect', 'clear_obstructions', 'fit', 'build', 'readback', 'extension', 'connection', 'test_approach', 'route', 'discover', 'discover_junction', 'discover_interior', 'verify_interior', 'verify_crossover', 'remove_branch', 'crossover', 'adjacent', 'verify_adjacency', 'junction', 'interior_junction', 'selected_connection', 'corridor'}

OPERATIONS.add(STATION_OPERATION)
OPERATIONS.add('repair_crossover')
OPERATIONS.add('structured_chain')
OPERATIONS.update({'operating_inspect', 'operating_control'})

def is_mutation(operation, params):
    return operation in ('build', 'test_approach', 'remove_branch', 'clear_obstructions') or (operation in ('operating_control', 'structured_chain', 'repair_crossover', 'scissors_candidate', 'extension', 'connection', 'selected_connection', 'corridor', 'junction', 'interior_junction', 'crossover', 'adjacent', 'degree_four_candidate') and params.get('execute') is True)

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
    if not isinstance(brief, dict) or set(brief) - {'vertical','station_target'} != keys:
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
    if 'station_target' in brief and (type(brief['station_target']) is not int or brief['station_target']<=0):
        raise ValueError('station_target must be an exact positive construction identity')
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
    if not isinstance(brief, dict) or set(brief) - {'vertical','fit_radius'} != {'source_ref','target_ref','radius','region'}:
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
    if 'fit_radius' in brief:
        _validate_fit_radius(brief['fit_radius'], brief['radius'])
    vertical={'vertical':brief['vertical']} if 'vertical' in brief else {}
    validate_connection_brief({'anchor_edge':source['edge_id'],'anchor_node':source['node_id'],
        'target_edge':target['edge_id'],'target_node':target['node_id'],'radius':brief['radius'],'region':brief['region'],**vertical})
    return {'source':source,'target':target,
        'radius':brief['radius'],'region':brief['region'],'discovery_request':request_ids[0],
        'discovery_requests':request_ids,**vertical,
        **({'fit_radius':brief['fit_radius']} if 'fit_radius' in brief else {})}

def _validate_fit_radius(value, minimum):
    if type(value) not in (int,float) or not math.isfinite(value) or value<minimum:
        raise ValueError('fit_radius cannot lower the hard radius')

def prepare_junction(client, parameters, candidates):
    """Bounded native fitting/evaluation; no construction. Exact native bindings required."""
    keys={'source','target','radius','region','vertical','max_route_length'}
    if not isinstance(parameters,dict) or not keys<=parameters.keys() or parameters.keys()-keys-{'fit_radius','discovery_request','discovery_requests'}:
        raise ValueError('junction preparation requires exact bindings, hard bounds and route limit')
    validate_connection_brief({'anchor_edge':parameters['source']['edge_id'],'anchor_node':parameters['source']['node_id'],
        'target_edge':parameters['target']['edge_id'],'target_node':parameters['target']['node_id'],
        **{k:parameters[k] for k in ('radius','region','vertical')}})
    if 'fit_radius' in parameters:_validate_fit_radius(parameters['fit_radius'],parameters['radius'])
    length=parameters['max_route_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 0<length<=800:
        raise ValueError('junction route limit must be within(0,800]')
    if not isinstance(candidates,list) or not 1<=len(candidates)<=8:
        raise ValueError('junction candidates must be within1–8')
    for candidate in candidates:
        if not isinstance(candidate,dict) or set(candidate)!={'fit_radius','representation'}:
            raise ValueError('candidate requires fit_radius and representation only')
        _validate_fit_radius(candidate['fit_radius'],parameters['radius'])
        if candidate['representation'] not in ('native_parts','single_cubic_level','two_piece_level','endpoint_cubic_level'):
            raise ValueError('unsupported junction representation')
    return client.request('junction',{**parameters,'execute':False,'prepare':True,'fit_candidates':candidates})

def build_prepared_junction(client, prepared):
    """Consume one current-session native proposal; never silently refit or replay."""
    if (not isinstance(prepared,dict) or prepared.get('session')!=client.session or prepared.get('operation')!='junction'
            or prepared.get('status')!='ok' or prepared.get('result',{}).get('native_proposal_evaluated') is not True
            or prepared['result'].get('native_proposal_critical') is not False
            or prepared['result'].get('prepared_request')!=prepared.get('request_id')):
        raise ValueError('accepted current-session prepared junction required')
    return client.request('junction',{'prepared_request':prepared['request_id'],'execute':True})

def _validate_interior_shapes(parameters, candidates, minimum):
    if not isinstance(candidates,list) or not 1<=len(candidates)<=8:
        raise ValueError('interior candidates must be within1–8')
    for candidate in candidates:
        if (not isinstance(candidate,dict) or not {'branch','through'}<=candidate.keys()
                or candidate.keys()-{'branch','through','fit_radius','handle_scale','through_handle_scales'}):
            raise ValueError('invalid interior candidate fields')
        if candidate['branch'] not in ('native_parts','endpoint_cubic_level','endpoint_cubic_graded','guided_cubic_level') or candidate['through'] not in ('subdivide','subdivide_fresh','endpoint_cubic_level','extended_endpoint_cubic_level'):
            raise ValueError('unsupported interior candidate')
        if ('through_extension' in parameters)!=(candidate['through']=='extended_endpoint_cubic_level'):
            raise ValueError('adjoining replacement requires an explicit extended candidate and snapshot')
        if 'fit_radius' in candidate:_validate_fit_radius(candidate['fit_radius'],minimum)
        scales=[candidate.get('handle_scale',1)]+candidate.get('through_handle_scales',[1,1,1,1]) if isinstance(candidate.get('through_handle_scales',[]),list) else []
        if len(scales)!=5 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 or x>4 for x in scales):
            raise ValueError('bounded positive control handle scales required')
    guides=parameters.get('guides',[])
    if not isinstance(guides,list) or len(guides)>2:
        raise ValueError('at most two local shape guides')
    for guide in guides:
        if not isinstance(guide,dict) or set(guide)!={'pos','direction'}:
            raise ValueError('shape guide requires position and direction')
        for key,size in (('pos',3),('direction',2)):
            value=guide[key]
            if not isinstance(value,list) or len(value)!=size or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):
                raise ValueError('guide '+key+' requires finite native coordinates')
        if math.hypot(*guide['direction'])<1e-9:raise ValueError('guide direction must be nonzero')

def prepare_interior_junction(client, parameters, candidates):
    """Prepare through replacement and branch together from connection intent."""
    required={'source','target','location','region','vertical','max_route_length'}
    optional={'radius','guides','junction_nodes','through_extension'}
    if not isinstance(parameters,dict) or not required<=parameters.keys() or parameters.keys()-required-optional:
        raise ValueError('interior preparation requires exact attachments, location and bounds')
    source,target=parameters['source'],parameters['target']
    if (not isinstance(source,dict) or source.get('interior_eligible') is not True
            or type(source.get('parameter')) not in (int,float) or not .05<=source['parameter']<=.95
            or not isinstance(source.get('edge_snapshot'),dict) or source['edge_snapshot'].get('id')!=source.get('edge_id')):
        raise ValueError('observed exact interior source required')
    if not isinstance(target,dict) or not isinstance(target.get('edge_snapshot'),dict):
        raise ValueError('observed exact target required')
    if 'through_extension' in parameters:
        extension=parameters['through_extension'];snapshot=source['edge_snapshot']
        if (not isinstance(extension,dict) or type(extension.get('id')) is not int
                or extension['id']==source['edge_id'] or source.get('canonical_forward') is not True
                or snapshot['node1'] not in (extension.get('node0'),extension.get('node1'))
                or not {'p0','p1','t0','t1','template','style'}<=extension.keys()):
            raise ValueError('exact adjoining through snapshot and forward interior source required')
    minimum=parameters.get('radius',0)
    if type(minimum) not in (int,float) or not math.isfinite(minimum) or minimum<0:
        raise ValueError('optional hard radius must be finite and nonnegative')
    validate_connection_brief({'anchor_edge':source['edge_id'],'anchor_node':source['edge_snapshot']['node0'],
        'target_edge':target['edge_id'],'target_node':target['node_id'],'radius':minimum or 1,
        'region':parameters['region'],'vertical':parameters['vertical']})
    length=parameters['max_route_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 0<length<=800:
        raise ValueError('interior route limit must be within(0,800]')
    _validate_interior_shapes(parameters,candidates,minimum)
    return client.request('interior_junction',{**parameters,'radius':minimum,'execute':False,'prepare':True,'fit_candidates':candidates})

def build_prepared_interior_junction(client, prepared):
    """Consume the accepted current-session through/branch geometry without refit."""
    if (not isinstance(prepared,dict) or prepared.get('session')!=client.session
            or prepared.get('operation')!='interior_junction' or prepared.get('status')!='ok'
            or prepared.get('result',{}).get('native_proposal_evaluated') is not True
            or prepared['result'].get('native_proposal_critical') is not False
            or prepared['result'].get('prepared_request')!=prepared.get('request_id')):
        raise ValueError('accepted current-session prepared interior junction required')
    return client.request('interior_junction',{'prepared_request':prepared['request_id'],'execute':True})

def prepare_crossover(client, parameters, candidates):
    """Evaluate both exact interior through attachments and one connecting lead."""
    required={'source','target','location','target_location','region','vertical','max_route_length'}
    if not isinstance(parameters,dict) or not required<=parameters.keys() or parameters.keys()-required-{'radius','guides','junction_nodes'}:
        raise ValueError('crossover preparation requires two exact interior attachments and bounds')
    for key in ('source','target'):
        port=parameters[key]
        if (not isinstance(port,dict) or port.get('interior_eligible') is not True
                or type(port.get('edge_id')) is not int or port['edge_id']<=0
                or type(port.get('parameter')) not in (int,float) or not .05<=port['parameter']<=.95
                or not isinstance(port.get('edge_snapshot'),dict) or port['edge_snapshot'].get('id')!=port['edge_id']):
            raise ValueError('observed exact interior '+key+' required')
    source,target=parameters['source'],parameters['target']
    if source['edge_id']==target['edge_id']:raise ValueError('distinct through tracks required')
    minimum=parameters.get('radius',0)
    if type(minimum) not in (int,float) or not math.isfinite(minimum) or minimum<0:
        raise ValueError('optional hard radius must be finite and nonnegative')
    validate_connection_brief({'anchor_edge':source['edge_id'],'anchor_node':source['edge_snapshot']['node0'],
        'target_edge':target['edge_id'],'target_node':target['edge_snapshot']['node0'],'radius':minimum or 1,
        'region':parameters['region'],'vertical':parameters['vertical']})
    length=parameters['max_route_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 0<length<=800:
        raise ValueError('crossover route limit must be within(0,800]')
    _validate_interior_shapes(parameters,candidates,minimum)
    return client.request('crossover',{**parameters,'radius':minimum,'execute':False,'prepare':True,'fit_candidates':candidates})

def build_prepared_crossover(client, prepared):
    """Consume exact accepted current-session crossover controls without refitting."""
    if (not isinstance(prepared,dict) or prepared.get('session')!=client.session
            or prepared.get('operation')!='crossover' or prepared.get('status')!='ok'
            or prepared.get('result',{}).get('native_proposal_evaluated') is not True
            or prepared['result'].get('native_proposal_critical') is not False
            or prepared['result'].get('prepared_request')!=prepared.get('request_id')):
        raise ValueError('accepted current-session prepared crossover required')
    for attempt in prepared['result'].get('candidate_rejections', []):
        if attempt.get('status') == 'accepted' and attempt.get('evaluation', {}).get('messages'):
            raise ValueError('native crossover error messages prevent build')
    return client.request('crossover',{'prepared_request':prepared['request_id'],'execute':True})

def validate_project_brief(brief, *, corridor=False):
    keys={'source','target','radius','region','vertical','max_fit_attempts','max_route_length'}
    if not isinstance(brief,dict) or set(brief)-{'fit_radius'}!=keys:
        raise ValueError('connection project requires only '+', '.join(sorted(keys)))
    validate_connection_brief({'anchor_edge':1,'anchor_node':2,'target_edge':3,'target_node':4,
                              'radius':brief['radius'],'region':brief['region'],'vertical':brief['vertical']})
    if 'fit_radius' in brief:_validate_fit_radius(brief['fit_radius'],brief['radius'])
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
    if 'fit_radius' in brief:
        v=brief['fit_radius']
        if type(v) not in (int,float) or not math.isfinite(v) or v<brief['radius']:raise ValueError('fit_radius cannot lower the hard radius')
    validate_project_brief({k:v for k,v in brief.items() if k not in ('placement_tolerance','fit_radius')},corridor=junction_nodes is not None)
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
            if 'fit_radius' in brief:selection['fit_radius']=brief['fit_radius']
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
                if 'fit_radius' in brief:params['fit_radius']=brief['fit_radius']
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
    single=isinstance(steps,list) and len(steps)==1 and isinstance(steps[0],dict) and steps[0].get('kind')=='crossover'
    if not isinstance(roles,dict) or not (4 if single else 5)<=len(roles)<=(4 if single else 10):raise ValueError('throat requires bounded named roles')
    if any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',n) for n in roles):raise ValueError('invalid role name')
    kinds=[r.get('kind') for r in roles.values() if isinstance(r,dict)]
    if kinds.count('approach')!=2 or kinds.count('destination')<(2 if single else 3) or len(kinds)!=len(roles) or any(k not in ('approach','destination') for k in kinds):raise ValueError('two approaches and the required destinations must be explicit')
    if not isinstance(steps,list) or not (1 if single else 2)<=len(steps)<=6:raise ValueError('throat steps outside bounded domain')
    names=[]
    for step in steps:
        if not isinstance(step,dict) or set(step)-{'representation'}!={'name','kind','source','target'} or step['kind'] not in ('crossover','branch'):raise ValueError('invalid throat step')
        if 'representation' in step and (step['kind']!='crossover' or step['representation'] not in ('native_parts','single_cubic_level')):raise ValueError('invalid crossover representation')
        if not isinstance(step['name'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}',step['name']) or step['name'] in names:raise ValueError('invalid/duplicate step name')
        names.append(step['name'])
        b={k:brief[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length')}
        b.update(source=step['source'],target=step['target'])
        validate_project_brief(b,corridor=True)
    if not any(s['kind']=='crossover' for s in steps) or (not single and not any(s['kind']=='branch' for s in steps)):raise ValueError('crossover and branch required')
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
          'native_execution_supported':True,'native_runtime_demonstrated':False,
          'native_construction_direction':d,'direction_enforcement':'not_provided','train_traversal':'unprobed',
          'game_constructed':False,'limitations':['fixed level geometry/radius120/spacing5','outer branches only; no cross-track switching','native execution initially UUDD with increasing UP only']}
    # Preserve accepted UUDD DESIGN hashes/receipts. Only newly enabled domains
    # replace the historical initial-execution limitation.
    if pattern!='UP-UP-DOWN-DOWN' or ref['up']!='increasing':plan['limitations'][-1]='UD/UDUD/UUDD; explicit increasing or decreasing UP reference'
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_parallel_layout(plan,evidence):
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel plan differs from deterministic brief')
    path=Path(evidence)/(uuid.uuid4().hex+'.parallel_plan.json');path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,plan)
    return {'status':'ok','operation':'parallel-layout','stage':'plan','pattern':plan['pattern'],'plan_hash':plan['plan_hash'],
            'native_execution_supported':plan['native_execution_supported'],'native_runtime_demonstrated':False,'game_constructed':False,
            'movements':plan['movements'],'direction_enforcement':'not_provided','evidence':str(path.resolve())}


def _verify_parallel_layout(client,plan,record,*,movement_edges=None,partial=False):
    ports={};observations=[];d=plan['native_construction_direction'];ref=plan['brief']['route_reference']
    states={};record['current_steps']=states
    for name,p in plan['ports'].items():
        try:
            c,rid=_select_throat_port(client,_recipe_intent(plan,p['position'],p.get('construction_direction',d)),tolerance=.5,
                                      outward_sign=-1 if p['end']=='west' else 1,connected=True)
            ports[name]=c;observations.append(rid);states[name]='completed'
        except LiveError as exc:
            if not partial or exc.status!='no_eligible_candidates':raise
            states[name]='unavailable'
    if len({c['node_id'] for c in ports.values()})!=len(ports):raise LiveError('native_verification_failed','functional ports share current native attachment')
    nodes={}
    for b in plan['branches']:
        try:
            node,rids=_recipe_junction(client,b['source']);nodes[b['name']]=node;observations+=rids;states[b['name']+'_junction']='completed'
        except LiveError as exc:
            if not partial or exc.status not in ('no_eligible_candidates','recipe_state_unknown'):raise
            states[b['name']+'_junction']='unavailable'
    routes=[]
    for row in plan['movements']:
        if partial and (any(row[k] not in ports for k in ('from','to')) or any(name not in nodes for name in (row.get('via') or [b['name'] for b in plan['branches'] if b['name'] in (row['from'],row['to'])]))):
            routes.append(row|{'verified':False,'reason':'current attachment/junction unavailable'});record['routes']=routes;continue
        a,b=(ports[row[k]] for k in ('from','to'))
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],'target_node':b['node_id'],
               'mode':'TRAIN','required_edges':list(dict.fromkeys([a['edge_id'],b['edge_id']]+(movement_edges or {}).get((row['from'],row['to']),[]))),'max_length':2500,
           'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':120,'region':plan['brief']['region'],'max_grade':plan['brief']['max_grade']}}
        r=client.request('route',q);v=r.get('result',{});accepted=r['status']=='ok' and v.get('requested_route_verified') is True
        current_nodes={x[k]['entity'] for x in v.get('path',[]) for k in ('from','to')}
        via=row.get('via',[name for name in nodes if name in (row['from'],row['to'])])
        if any(name not in nodes or nodes[name] not in current_nodes for name in via):accepted=False
        routes.append(row|{'verified':accepted,'request_id':r['request_id'],'response':r})
        record['routes']=routes;atomic_json(Path(record['summary']['evidence']),record)
        if not accepted and not partial:raise LiveError('native_verification_failed','required intended movement not verified: '+row['from']+'->'+row['to'])
    spacing=[];normal=[-d[1],d[0]];lines=[]
    for i,t in enumerate(plan['brief']['tracks']):
        o=ref['origin'];q=[o[0]+50*d[0]+5*i*normal[0],o[1]+50*d[1]+5*i*normal[1],o[2]]
        try:c,rid=_select_throat_port(client,_recipe_intent(plan,q,d),interior=True,tolerance=.5)
        except LiveError as exc:
            if not partial or exc.status!='no_eligible_candidates':raise
            states['approach_spacing']='unavailable';lines=[];break
        observations.append(rid);e=c['edge_snapshot']
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
    verified=sum(r['verified'] for r in routes);complete=verified==len(plan['movements']) and len(lines)==len(plan['brief']['tracks'])
    return {'routes_verified':verified,'final_network_verified':complete,'retained_spacing':spacing,
            'direction_intent_compatible':complete,'direction_enforcement':'not_provided','geometry_sampled_only':True,'native_runtime_demonstrated':complete}


def inspect_parallel_layout(client,invocation):
    original=json.loads(Path(invocation).read_text(encoding='utf-8-sig'))
    if 'plan' not in original and original.get('evidence'):original=json.loads(Path(original['evidence']).read_text(encoding='utf-8-sig'))
    plan=original['plan']
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel invocation plan differs from brief')
    path=client.evidence/(uuid.uuid4().hex+'.parallel_inspection.json')
    summary={'status':'incomplete','operation':'parallel-layout-inspect','game_constructed':False,'evidence':str(path.resolve()),'plan_hash':plan['plan_hash'],'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'original_record':str(Path(invocation).resolve()),'routes':[],
            'recorded_prior_game_constructed':original.get('summary',{}).get('game_constructed','unknown')}
    try:
        summary.update(_verify_parallel_layout(client,plan,record,partial=original.get('summary',{}).get('status')!='ok'))
        summary.update(status='ok' if summary['final_network_verified'] else 'layout_incomplete',stage='verified' if summary['final_network_verified'] else 'current_partial_readback')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:
        _reciprocal_outcome(plan,record,summary)
        if summary['status']!='ok':summary.update(routes_verified=sum(bool(r.get('verified')) for r in record['routes']),final_network_verified=False)
        if summary['status']=='layout_incomplete':summary.update(current_steps=record.get('current_steps',{}),next_action='reconcile_native_operation' if original.get('unfinished_step') or _layout_uncertain_operations(client,original) else 'inspect_missing_attachments')
        atomic_json(path,record)
    return summary


def execute_parallel_layout(client,plan):
    if plan!=plan_parallel_layout(plan.get('brief')):raise ValueError('parallel plan differs from deterministic brief')
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
    finally:_reciprocal_outcome(plan,record,summary);atomic_json(path,record);lock.unlink()
    return summary


SWITCHING_LAYOUT = 'widened_uudd_switching_v1'


def plan_switching_layout(brief):
    """Two outward widened native throats; eight explicit intended movements."""
    if not isinstance(brief,dict) or brief.get('layout')!=SWITCHING_LAYOUT:
        raise LiveError('unsupported_layout','only '+SWITCHING_LAYOUT+' is supported')
    tracks=brief.get('tracks')
    if not isinstance(tracks,list) or len(tracks)!=4 or any(not isinstance(t,dict) or not isinstance(t.get('id'),str) for t in tracks):
        raise ValueError('switching layout requires four explicitly ordered tracks')
    if not isinstance(brief.get('route_reference'),dict):raise ValueError('explicit route reference required')
    if [t.get('direction') for t in tracks]!=['UP','UP','DOWN','DOWN'] or brief['route_reference'].get('up')!='increasing':
        raise LiveError('unsupported_native_pattern','switching v1 supports UUDD with increasing-reference UP only')
    names=[t['id'] for t in tracks]
    transfers=[{'from':names[1]+':west','to':names[0]+':east'}, {'from':names[3]+':east','to':names[2]+':west'}]
    rows=brief.get('movements')
    if not isinstance(rows,list) or any(not isinstance(row,dict) or set(row)!={'from','to'} for row in rows):raise ValueError('explicit directed movement matrix required')
    base=brief|{'layout':PARALLEL_LAYOUT,'movements':[row for row in rows if row not in transfers]}
    p=plan_parallel_layout(base)
    if len(rows)!=8 or any(rows.count(row)!=1 for row in transfers):raise ValueError('eight movements must include each same-direction transfer once')
    ref=brief['route_reference'];o=ref['origin'];h=math.radians(ref['heading_deg']);d=[math.cos(h),math.sin(h)]
    def pos(x,y):return [o[0]+x*d[0]-y*d[1],o[1]+x*d[1]+y*d[0],o[2]]
    def direction(a):return [math.cos(h+math.radians(a)),math.sin(h+math.radians(a))]
    ports={};pairs=[]
    # Same native reference/fanout/cross/branch controls as the demonstrated widened
    # recipe. UP reflects them outward; DOWN retains native construction orientation
    # and reverses only intended traffic, not supplied construction tangents.
    for label,offset,sign,reference,fan,branch in [('up',5,-1,names[1],names[0],'branch_up'),('down',10,1,names[2],names[3],'branch_down')]:
        def q(x,y=0):return pos(x,offset+sign*y)
        def intent(x,y=0,a=0):return _recipe_intent(p,q(x,y),direction(sign*a))
        specs=[('A1',reference,-20,0,0),('A2',fan,-20,5,0),('D1',reference,1600,180,12),('D2',fan,600,105,0),('D3',branch,1100,460,0)]
        fixtures=[]
        for name,track,x,y,a in specs:
            point=q(x,y);con=direction(sign*a)
            fixtures.append({'name':name,'position':point,'travel_direction':con,'length':20,
                'region':{'min':[max(point[k]-40,brief['region']['min'][k]) for k in range(3)],'max':[min(point[k]+40,brief['region']['max'][k]) for k in range(3)]}})
            west=name.startswith('A');port=track+(':west' if west else ':east') if track!=branch else branch
            end='west' if west else ('branch' if track==branch else 'east')
            traffic=1 if label=='up' else -1
            ports[port]={'track':track,'end':end,'position':point if west else [point[k]+20*(con[k] if k<2 else 0) for k in range(3)],
                'construction_direction':con,'running_direction':'UP' if traffic==1 else 'DOWN','travel_direction':[traffic*z for z in con],
                'function':'entry' if west==(traffic==1) else 'exit'}
        common={'radius':120,'region':brief['region'],'vertical':{'max_grade':brief['max_grade']},'max_fit_attempts':1,'max_route_length':2500}
        pairs.append({'name':label,'brief':{'origin':o},'fixtures':fixtures,
            'reference':common|{'radius':160,'source':intent(0),'target':intent(1600,180,12),
                'guides':[{'position':q(x,y),'travel_direction':direction(sign*a),'grade':0} for x,y,a in [(400,0,0),(800,30,8),(1200,180-400*math.tan(math.radians(12)),12)]]},
            'fanout':common|{'source':intent(0,5),'target':intent(600,105), 'guides':[{'position':q(100,5),'travel_direction':d,'grade':0}]},
            'cross_source':intent(250),'required_routes':[{'from':'A1','to':dest,'via':via} for dest,via in [('D1',[]),('D2',['cross']),('D3',['cross','branch'])]]+[
                {'from':'A2','to':'D2','via':[]},{'from':'A2','to':'D3','via':['branch']}],
            'transfer':transfers[0 if label=='up' else 1],'branch_port':branch})
    corners=[pos(x,y) for x,y in [(-60,-500),(1660,-500),(1660,515),(-60,515)]]
    footprint={'min':[min(q[k] for q in corners) for k in range(2)]+[o[2]-1],'max':[max(q[k] for q in corners) for k in range(2)]+[o[2]+1]}
    if any(footprint['min'][k]<brief['region']['min'][k] or footprint['max'][k]>brief['region']['max'][k] for k in range(3)):raise LiveError('unsupported_layout','authorised region excludes widened switching footprint')
    plan={k:p[k] for k in ('version','epoch','pattern','order_convention','native_construction_direction','native_execution_supported','native_runtime_demonstrated','direction_enforcement','train_traversal','game_constructed')}
    plan.update(layout=SWITCHING_LAYOUT,brief=brief,ports=ports,pairs=pairs,movements=rows,footprint=footprint,
        limitations=['fixed level UUDD increasing-UP/radius120/retained spacing5','widened outgoing ports; not constant5m switching zones','one UP transfer U2->U1 and one DOWN transfer D2->D1','no opposite-direction switching/operational enforcement'])
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_switching_layout(plan,evidence):
    if plan!=plan_switching_layout(plan.get('brief')):raise ValueError('switching plan differs from brief')
    path=Path(evidence)/(uuid.uuid4().hex+'.switching_plan.json');path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,plan)
    return {'status':'ok','operation':'switching-layout','stage':'plan','game_constructed':False,'plan_hash':plan['plan_hash'],
        'movements':plan['movements'],'native_runtime_demonstrated':False,'direction_enforcement':'not_provided','evidence':str(path.resolve())}


def _switching_fanout(pair,fixtures):
    """Represent the nominal straight guide along the actual native end tangent.

    Avoid tiny Dubins corrections from mixing float-native endpoints with an ideal
    map-frame line. Preserve the existing0.001 conversion/heading tolerances.
    """
    e=fixtures['A2'];tangent=e['t1'];length=math.hypot(*tangent[:2])
    if length<1e-6 or abs(tangent[2])>1e-6:raise LiveError('unsupported_native_result','level native fixture tangent required')
    old=pair['fanout']['guides'][0];point=[e['p1'][k]+5*tangent[k] for k in range(3)];d=[z/length for z in tangent[:2]]
    angle=math.degrees(math.acos(max(-1,min(1,sum(d[k]*old['travel_direction'][k] for k in range(2))))))
    if math.dist(point,old['position'])>.001 or angle>.001:raise LiveError('unsupported_native_result','native straight guide exceeds existing conversion tolerances')
    return pair['fanout']|{'guides':[{'position':point,'travel_direction':d,'grade':0}]}


def _switching_verification(client,plan,record):
    verify=plan|{'branches':[],'movements':[dict(row) for row in plan['movements']]};edges={};observations=[]
    runtime=record.get('pair_runtime',{})
    if set(runtime)!={'up','down'}:raise LiveError('incomplete_layout','both built native throat receipts required')
    for pair in plan['pairs']:
        saved=runtime[pair['name']];path=Path(saved['throat_record']);raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=saved['sha256']:raise ValueError('built throat receipt changed')
        built=json.loads(raw.decode('utf-8-sig'));b=built['brief'];cross,branch=b['steps']
        if (built['summary'].get('status')!='ok' or cross['source']!=pair['cross_source'] or b['region']!=plan['brief']['region']
                or b['radius']!=120 or b['vertical']!={'max_grade':plan['brief']['max_grade']}
                or math.dist(branch['target']['guide_xyz'],pair['fixtures'][-1]['position'])>.001
                or branch['target']['travel_direction']!=pair['fixtures'][-1]['travel_direction']):
            raise ValueError('throat evidence does not match approved pair intent')
        label=pair['name'];a=label+'_cross_source';z=label+'_cross_target'
        verify['branches'] += [{'name':a,'source':cross['source']},{'name':z,'source':cross['target']},{'name':pair['branch_port'],'source':branch['source']}]
        connector=built['semantic_mapping']['step_edges']['cross']
        if not isinstance(connector,list) or not connector or len(connector)>16 or any(type(i) is not int for i in connector):raise ValueError('bounded exact connector identities required')
        current=client.request('inspect',{'edge_ids':connector,'geometry_constraints':{'radius':120,'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}});observations.append(current['request_id'])
        if current['status']!='ok' or {e['id'] for e in current['result']['edges']}!=set(connector) or any(e['road_type']!='TRACK' for e in current['result']['edges']):
            raise LiveError('stale_switching_connector','exact current transfer connector no longer established')
        for row in verify['movements']:
            if {k:row[k] for k in ('from','to')}==pair['transfer']:
                row['via']=[a,z];edges[(row['from'],row['to'])]=connector
    return verify,edges,observations


def _verify_switching_layout(client,plan,record):
    verify,edges,observations=_switching_verification(client,plan,record)
    answer=_verify_parallel_layout(client,verify,record,movement_edges=edges)
    record['connector_observations']=observations
    return answer|{'transfers_verified':2,'widened_switching':True,'direct5m_crossover':False}


def _layout_uncertain_operations(client,original,_depth=0):
    if _depth>1:raise ValueError('nested base-stage records outside bounded workflow')
    if original.get('unfinished_step'):return ['unfinished_'+original['unfinished_step']]
    uncertain=[]
    for o in original.get('operations',[]):
        r=o['response'];v=r.get('result',{})
        if r.get('game_constructed',v.get('game_constructed'))!='unknown' and r.get('status')!='mutation_unverified':continue
        if o['name']=='base_build' and r.get('evidence'):
            uncertain+=_layout_uncertain_operations(client,_load_layout_record(r['evidence']),_depth+1);continue
        rid=r.get('request_id');rp=client.evidence/(str(rid)+'.reconciliation.json');reconciled=json.loads(rp.read_text()) if rp.exists() else {}
        if (reconciled.get('status')=='reconciled_failed_fixture' and reconciled.get('original_pending',{}).get('request_id')==rid
                and reconciled.get('intended_fixture_constructed') is False and reconciled.get('automatic_replay') is False):continue
        uncertain+=_recipe_uncertain_operations({'operations':[o]})
    return uncertain


def _switching_recipe_assessment(client,plan,pair,original):
    pp=pair|{'brief':plan['brief']['route_reference']|{'region':plan['brief']['region'],'max_grade':plan['brief']['max_grade']}}
    view={'plan':pp,'operations':[o|{'name':o['name'][len(pair['name'])+1:]} for o in original.get('operations',[]) if o['name'].startswith(pair['name']+'_')]}
    saved=original.get('pair_runtime',{}).get(pair['name']);throat=next((o['response'].get('evidence') for o in reversed(view['operations']) if o['name']=='throat'),None)
    if saved:throat=saved['throat_record']
    if throat:view['throat_brief']=json.loads(Path(throat).read_text(encoding='utf-8-sig'))['brief']
    state=_assess_recipe(client,view)
    # The recipe assessor returns early for missing roles. Qualify every retained
    # fixture independently before allowing creation of any other fixture.
    for f in pair['fixtures']:
        c=state['roles'].get(f['name'])
        a=f['position'];z=[a[k]+20*(f['travel_direction'][k] if k<2 else 0) for k in range(3)]
        def matches(e):return any(math.dist(p,a)<=.001 and math.dist(q,z)<=.001 for p,q in ((e['p0'],e['p1']),(e['p1'],e['p0'])))
        if not c:
            if state['steps'].get('prepare_'+f['name'],{}).get('state')!='absent':
                r=discover(client,{'region':f['region'],'max_edges':16});state['observations'].append(r['request_id'])
                if r['status']=='ok' and r['result'].get('complete') is True and not any(matches(v['edge_snapshot']) for v in r['result']['candidates']):
                    state['steps']['prepare_'+f['name']]={'state':'absent','basis':'complete bounded exact fixture observation; incidental assets not protected'}
            continue
        e=c['edge_snapshot']
        chord=[e['p1'][k]-e['p0'][k] for k in range(3)]
        old=next((o['response'].get('result',{}).get('edges',[None])[0] for o in view['operations'] if o['name']=='prepare_'+f['name'] and o['response']['status']=='ok'),None)
        if (e.get('road_type')!='TRACK' or not matches(e) or (old and any(e.get(k)!=old.get(k) for k in ('template','style')))
                or any(abs(e[t][k]-chord[k])>.001 for t in ('t0','t1') for k in range(3))):raise LiveError('layout_state_changed','current fixture differs from declared straight interface')
        state['steps']['prepare_'+f['name']]={'state':'completed','current_edge':e['id']}
    if state['steps'].get('reference',{}).get('state')=='completed':
        a,z=(state['roles'][n] for n in ('A1','D1'))
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':z['edge_id'],'target_node':z['node_id'],'mode':'TRAIN','required_edges':[a['edge_id'],z['edge_id']],'max_length':2500,
            'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':160,'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}}
        r=client.request('route',q);state['observations'].append(r['request_id'])
        if r['status']!='ok' or r['result'].get('requested_route_verified') is not True:raise LiveError('layout_state_changed','current reference no longer meets160limit')
    return state


def execute_switching_layout(client,plan,*,prepared_record=None,current_run=None):
    if plan!=plan_switching_layout(plan.get('brief')):raise ValueError('switching plan differs from brief')
    if prepared_record and current_run:raise ValueError('use prepared fixtures or a current run, not both')
    continuing=_load_layout_record(current_run) if current_run else None
    if continuing is not None and continuing.get('plan')!=plan:raise ValueError('current switching run differs from brief')
    if continuing is not None and (not isinstance(continuing.get('operations'),list) or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in continuing['operations'])):raise ValueError('current switching stage records malformed')
    prepared=None
    if prepared_record:
        prepared=json.loads(Path(prepared_record).read_text(encoding='utf-8-sig'))
        if not isinstance(prepared,dict):raise ValueError('prepared switching record must be an object')
        ops=prepared.get('operations',[]);old=prepared.get('plan',{})
        if (not isinstance(old,dict) or not isinstance(old.get('pairs'),list) or len(old['pairs'])!=2
                or not isinstance(ops,list) or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in ops)):
            raise ValueError('prepared switching operations/plan malformed')
        canonical={k:v for k,v in old.items() if k!='plan_hash'}
        if (old.get('brief')!=plan['brief'] or old.get('plan_hash')!=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                or old.get('pairs',[{}])[0].get('fixtures')!=plan['pairs'][0]['fixtures']
                or [o.get('name') for o in ops]!=['discover_asset','inspect_asset']+['up_prepare_'+f['name'] for f in plan['pairs'][0]['fixtures']]+['up_reference']
                or ops[-1]['response'].get('status')!='no_accepted_candidate' or ops[-1]['response'].get('game_constructed') is not False):
            raise ValueError('prepared switching record must prove matching fixtures and prebuild UP reference fit failure')
    path=client.evidence/(uuid.uuid4().hex+'.switching.json');lock=client.evidence/'switching.lock'
    summary={'status':'incomplete','operation':'switching-layout','stage':'asset','game_constructed':False,'plan_hash':plan['plan_hash'],
        'evidence':str(path.resolve()),'routes_verified':0,'direction_enforcement':'not_provided','train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'operations':[],'pair_runtime':{}}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one switching layout at a time') from None
    def perform(name,call,mutation=False):
        if mutation and name in completed:
            r=completed[name];record['operations'].append({'name':name,'response':r,'reused_after_fresh_assessment':True});atomic_json(path,record);return r
        summary['stage']=name;record['unfinished_step']=name;atomic_json(path,record);r=call()
        record['operations'].append({'name':name,'response':r});record.pop('unfinished_step');atomic_json(path,record)
        if mutation:
            effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
            if effect in (True,'unknown') or summary['game_constructed'] is not True:summary['game_constructed']=effect
        if r['status']!='ok':raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error','switching stage failed')))
        return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise LiveError('reconciliation_required','unfinished native request; no layout construction')
        retained={};completed={};assessments={}
        if continuing:
            if _layout_uncertain_operations(client,continuing):raise LiveError('reconciliation_required','unresolved current switching effects; no replay')
            record.update(original_record=str(Path(current_run).resolve()),operations=list(continuing.get('operations',[])),pair_runtime=dict(continuing.get('pair_runtime',{})))
            for pair in plan['pairs']:
                state=_switching_recipe_assessment(client,plan,pair,continuing);assessments[pair['name']]=state
                if any(v.get('state') not in ('completed','absent') for n,v in state['steps'].items() if n.startswith('prepare_')):raise LiveError('reconciliation_required','fixture not proven completed or absent')
                for f in pair['fixtures']:
                    if f['name'] in state['roles']:completed[pair['name']+'_prepare_'+f['name']]={'status':'ok','result':{'edges':[state['roles'][f['name']]['edge_snapshot']]},'current_state_proof':state['observations']}
                for phase in ('reference','fanout'):
                    old=next((o['response'] for o in reversed(continuing['operations']) if o['name']==pair['name']+'_'+phase and o['response']['status']=='ok'),None)
                    if old and state['steps'].get(phase,{}).get('state')!='completed':raise LiveError('layout_state_changed','previously completed '+phase+' not established')
                    if old:completed[pair['name']+'_'+phase]=old
                if pair['name'] in record['pair_runtime'] and not all(state['steps'].get(n,{}).get('state')=='completed' for n in ('cross','branch')):raise LiveError('layout_state_changed','previous throat not currently established')
                if state['steps'].get('cross',{}).get('state')=='completed' and pair['name'] not in record['pair_runtime']:raise LiveError('base_stage_reconciliation_required','partial throat requires focused semantic reconciliation; no crossover replay')
            record['current_assessment']=assessments;atomic_json(path,record)
        if prepared:
            old=[o['response']['result']['edges'][0] for o in prepared['operations'][2:7]]
            r=perform('reacquire_prepared',lambda:client.request('inspect',{'edge_ids':[e['id'] for e in old]}))
            if r['result'].get('edges')!=old:raise LiveError('stale_prepared_layout','prepared fixtures differ from exact current native state')
            retained={f['name']:e for f,e in zip(plan['pairs'][0]['fixtures'],old)}
            record['original_prepared']=str(Path(prepared_record).resolve());record['prepared_reacquisition']=r['request_id']
        found=perform('discover_asset',lambda:discover(client,{'region':plan['brief']['asset_region'],'max_edges':16}));v=found['result']
        assets={c['edge_id']:c['edge_snapshot'] for c in v['candidates']}
        if v.get('complete') is not True or not assets:raise LiveError('asset_unavailable','complete native asset observation required')
        if len({(e['template'],e['style']) for e in assets.values()})!=1:raise LiveError('asset_choice_ambiguous','mixed native track families')
        seed=min(assets);r=perform('inspect_asset',lambda:client.request('inspect',{'edge_ids':[seed],'resources':True}))
        if r['result']['edges'][0].get('resource',{}).get('track_distance')!=5:raise LiveError('unsupported_layout','native template spacing is not5')
        record['selected_asset']=r['result']['edges'][0]
        for pair in plan['pairs']:
            fixtures={};prefix=pair['name']+'_'
            for f in pair['fixtures']:
                q={'authorised':True,'length':20,'fixture':{'template_edge':seed,'position':f['position'],'travel_direction':f['travel_direction'],'grade':0,'region':f['region']}}
                reuse=pair['name']=='up' and f['name'] in retained
                r=perform(prefix+'prepare_'+f['name'],lambda q=q,f=f,reuse=reuse:({'status':'ok','result':{'game_constructed':True,'edges':[retained[f['name']]]},'reused_prepared':True,'fresh_observation':record['prepared_reacquisition']} if reuse else client.request('test_approach',q)),True)
                rows=r['result'].get('edges',[])
                if len(rows)!=1 or rows[0].get('road_type')!='TRACK':raise LiveError('native_verification_failed','fixture exact TRACK identity unavailable')
                fixtures[f['name']]=rows[0]
            if pair['name'] in record['pair_runtime']:continue
            if continuing:
                state=_switching_recipe_assessment(client,plan,pair,record)
                if any(state['steps'].get(n,{}).get('state') not in ('completed','absent') for n in ('reference','fanout')):raise LiveError('reconciliation_required','current through track not proven completed or absent')
            perform(prefix+'reference',lambda:connect_corridor(client,pair['reference'],execute=True),True)
            fan=perform(prefix+'fanout',lambda:connect_corridor(client,_switching_fanout(pair,fixtures),execute=True),True)
            read=perform(prefix+'native_guides',lambda:client.request('inspect',{'edge_ids':fan['edges']}))
            b=_recipe_throat_brief(pair,fixtures,read['result']['edges'])
            throat=perform(prefix+'throat',lambda:connect_throat(client,b,execute=True),True)
            tp=Path(throat['evidence']);record['pair_runtime'][pair['name']]={'throat_record':str(tp.resolve()),'sha256':hashlib.sha256(tp.read_bytes()).hexdigest()};atomic_json(path,record)
        summary.update(_verify_switching_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
    finally:atomic_json(path,record);lock.unlink()
    return summary


def inspect_switching_layout(client,invocation):
    original=json.loads(Path(invocation).read_text(encoding='utf-8-sig'))
    if not isinstance(original,dict):raise ValueError('switching invocation must be an object')
    if 'plan' not in original and original.get('evidence'):original=json.loads(Path(original['evidence']).read_text(encoding='utf-8-sig'))
    if not isinstance(original,dict):raise ValueError('switching evidence must be an object')
    plan=original['plan']
    if plan!=plan_switching_layout(plan.get('brief')):raise ValueError('switching invocation differs from deterministic brief')
    path=client.evidence/(uuid.uuid4().hex+'.switching_inspection.json')
    summary={'status':'incomplete','operation':'switching-layout-inspect','game_constructed':False,'plan_hash':plan['plan_hash'],
        'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'original_record':str(Path(invocation).resolve()),'pair_runtime':original.get('pair_runtime',{})}
    try:summary.update(_verify_switching_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:atomic_json(path,record)
    return summary


def continue_switching_layout(client,invocation):
    """Only the observed DOWN-fanout prebuild failure; no general stage resume."""
    original=json.loads(Path(invocation).read_text(encoding='utf-8-sig'))
    if not isinstance(original,dict):raise ValueError('switching invocation must be an object')
    if 'plan' not in original and original.get('evidence'):original=json.loads(Path(original['evidence']).read_text(encoding='utf-8-sig'))
    if not isinstance(original,dict):raise ValueError('switching evidence must be an object')
    plan=original['plan'];ops=original.get('operations',[])
    if not isinstance(ops,list) or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in ops):raise ValueError('switching operations malformed')
    if plan!=plan_switching_layout(plan.get('brief')):raise ValueError('switching continuation plan differs from brief')
    last=ops[-1] if ops else {};failed=last.get('response',{})
    if (original.get('summary',{}).get('stage')!='down_fanout' or original.get('unfinished_step')
            or last.get('name')!='down_fanout' or failed.get('status')!='no_accepted_candidate' or failed.get('game_constructed') is not False
            or set(original.get('pair_runtime',{}))!={'up'}):raise ValueError('only completed UP/reference and proven prebuild DOWN-fanout failure may continue')
    pair=plan['pairs'][1];fixtures={}
    for f in pair['fixtures']:
        matches=[o['response'] for o in ops if o['name']=='down_prepare_'+f['name']]
        if len(matches)!=1 or matches[0].get('status')!='ok' or len(matches[0].get('result',{}).get('edges',[]))!=1:raise ValueError('exact prepared DOWN fixtures unavailable')
        fixtures[f['name']]=matches[0]['result']['edges'][0]
    references=[o['response'] for o in ops if o['name']=='down_reference']
    if len(references)!=1 or references[0].get('status')!='ok' or references[0].get('game_constructed') is not True:raise ValueError('completed DOWN reference required')
    path=client.evidence/(uuid.uuid4().hex+'.switching_continuation.json');lock=client.evidence/'switching.lock'
    summary={'status':'incomplete','operation':'switching-layout-continue','stage':'fresh_preconditions','game_constructed':False,
        'plan_hash':plan['plan_hash'],'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'original_record':str(Path(invocation).resolve()),'operations':[],'pair_runtime':dict(original['pair_runtime'])}
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one switching layout at a time') from None
    def perform(name,call,mutation=False):
        summary['stage']=name;record['unfinished_step']=name;atomic_json(path,record);r=call()
        record['operations'].append({'name':name,'response':r});record.pop('unfinished_step');atomic_json(path,record)
        if mutation:
            effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
            if effect in (True,'unknown') or summary['game_constructed'] is not True:summary['game_constructed']=effect
        if r['status']!='ok':raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error','continuation stage failed')))
        return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise LiveError('reconciliation_required','unfinished native request; no continuation')
        old=list(fixtures.values());current=perform('reacquire_down_fixtures',lambda:client.request('inspect',{'edge_ids':[e['id'] for e in old]}))
        if current['result'].get('edges')!=old:raise LiveError('stale_prepared_layout','prepared DOWN fixtures changed')
        # Prove the already-built reference on current topology before completing it.
        ports=[]
        for end in ('west','east'):
            p=plan['ports'][plan['brief']['tracks'][2]['id']+':'+end]
            port,rid=_select_throat_port(client,_recipe_intent(plan,p['position'],p['construction_direction']),tolerance=.5,outward_sign=-1 if end=='west' else 1)
            ports.append(port)
        a,z=ports
        q={'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':z['edge_id'],'target_node':z['node_id'],'mode':'TRAIN','max_length':2500,
            'required_edges':[a['edge_id'],z['edge_id']],'geometry_constraints':{'all_path':True,'edge_ids':[],'radius':160,'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}}
        route=perform('current_down_reference',lambda:client.request('route',q))
        if route['result'].get('requested_route_verified') is not True:raise LiveError('stale_prepared_layout','current DOWN reference route not established')
        up=record['pair_runtime']['up'];upraw=Path(up['throat_record']).read_bytes()
        if hashlib.sha256(upraw).hexdigest()!=up['sha256']:raise ValueError('completed UP receipt changed')
        fan=perform('down_fanout',lambda:connect_corridor(client,_switching_fanout(pair,fixtures),execute=True),True)
        read=perform('down_native_guides',lambda:client.request('inspect',{'edge_ids':fan['edges']}))
        b=_recipe_throat_brief(pair,fixtures,read['result']['edges']);throat=perform('down_throat',lambda:connect_throat(client,b,execute=True),True)
        tp=Path(throat['evidence']);record['pair_runtime']['down']={'throat_record':str(tp.resolve()),'sha256':hashlib.sha256(tp.read_bytes()).hexdigest()}
        summary.update(_verify_switching_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
    finally:atomic_json(path,record);lock.unlink()
    return summary


def _select_throat_port(client,intent,*,interior=False,tolerance=None,outward_sign=1,connected=False):
    found=client.request('discover_interior',intent|{'placement_tolerance':tolerance}) if interior else discover(client,{k:intent[k] for k in ('region','max_edges')})
    if found['status']!='ok':raise LiveError(found['status'],found.get('result',{}).get('error','port_discovery_failed'),found['request_id'])
    value=found['result']
    if value.get('complete') is not True:raise LiveError('discovery_incomplete','bounded role discovery was truncated',found['request_id'])
    direction=intent['travel_direction'];size=math.hypot(*direction);ranked=[]
    for c in value['candidates']:
        eligible=(c.get('interior_eligible') if interior else c.get('eligible')) is True
        attached=connected and not interior and c.get('incident_count')==2 and c.get('incidence_complete') is True and not c.get('incident_output_truncated') and c.get('construction_owner') in (None,'none',-1,0)
        if not eligible and not attached:continue
        d=c['outward_direction'];horizontal=math.hypot(*d[:2])
        if horizontal<=0:continue
        heading=math.degrees(math.acos(max(-1,min(1,outward_sign*(d[0]*direction[0]+d[1]*direction[1])/(size*horizontal)))))
        if heading>intent['heading_tolerance_deg']:continue
        distance=math.dist(c['pos'],intent['guide_xyz'])
        if distance>(tolerance if tolerance is not None else (.5 if interior else 10)):continue
        ranked.append((distance,heading,c['edge_id'],c))
    ranked.sort(key=lambda x:x[:3])
    if not ranked:raise LiveError('no_eligible_candidates','no current native attachment for declared role',found['request_id'])
    if len(ranked)>1 and abs(ranked[0][0]-ranked[1][0])<.001:raise LiveError('ambiguous_attachment','declared role does not distinguish native attachments',found['request_id'])
    selected=ranked[0][3]
    if connected and not selected.get('eligible'):
        ids=selected.get('incident_edges',[])
        if len(ids)!=2 or len(set(ids))!=2 or selected['edge_id'] not in ids:raise LiveError('native_verification_failed','attached role incidence incomplete')
        current=client.request('inspect',{'edge_ids':ids})
        edges=current.get('result',{}).get('edges',[])
        if current['status']!='ok' or {e['id'] for e in edges}!=set(ids) or any(e['road_type']!='TRACK' or selected['node_id'] not in (e['node0'],e['node1']) for e in edges):raise LiveError('native_verification_failed','attached role requires two exact current TRACK edges')
    return selected,found['request_id']


RECIPROCAL_LAYOUT = 'reciprocal_uudd_switching_v1'


def plan_reciprocal_layout(brief):
    """Reuse the eight-movement layout, extending fans for separated return switches."""
    if not isinstance(brief,dict) or brief.get('layout')!=RECIPROCAL_LAYOUT:
        raise LiveError('unsupported_layout','only '+RECIPROCAL_LAYOUT+' is supported')
    tracks=brief.get('tracks');rows=brief.get('movements')
    if not isinstance(tracks,list) or len(tracks)!=4 or any(not isinstance(t,dict) or not isinstance(t.get('id'),str) for t in tracks):raise ValueError('four ordered tracks required')
    names=[t['id'] for t in tracks]
    returns=[{'from':names[0]+':west','to':names[1]+':east'},{'from':names[2]+':east','to':names[3]+':west'}]
    if not isinstance(rows,list) or len(rows)!=10 or any(rows.count(row)!=1 for row in returns):raise ValueError('ten explicit movements including both reciprocal transfers required')
    base=plan_switching_layout(brief|{'layout':SWITCHING_LAYOUT,'movements':[row for row in rows if row not in returns]})
    plan=json.loads(json.dumps(base));plan.pop('plan_hash');plan.update(layout=RECIPROCAL_LAYOUT,brief=brief,base_plan=base,movements=rows,returns=[])
    d=plan['native_construction_direction']
    for pair,transfer in zip(plan['pairs'],returns):
        fixture=json.loads(json.dumps(pair['fixtures'][3]));fixture['name']='extended_fan'
        fixture['position']=[fixture['position'][k]+600*(d[k] if k<2 else 0) for k in range(3)]
        p=fixture['position'];fixture['region']={'min':[max(p[k]-40,brief['region']['min'][k]) for k in range(3)],'max':[min(p[k]+40,brief['region']['max'][k]) for k in range(3)]}
        fan_id=names[0 if pair['name']=='up' else 3];ref_id=names[1 if pair['name']=='up' else 2]
        east=plan['ports'][fan_id+':east'];east['position']=[p[k]+20*(d[k] if k<2 else 0) for k in range(3)]
        source=[pair['fixtures'][3]['position'][k]+150*(d[k] if k<2 else 0) for k in range(3)]
        plan['returns'].append({'name':pair['name']+'_return','fixture':fixture,'fan':fan_id,'reference':ref_id,
            'source':_recipe_intent(plan,source,d),'target_reference_x':1000,'transfer':transfer,
            'extension_source':_recipe_intent(plan,base['ports'][fan_id+':east']['position'],d),
            'extension_target':_recipe_intent(plan,p,d)})
    plan['limitations']=['level UUDD increasing-UP/radius120/retained spacing5','longitudinally separated widened switches; no scissors/direct5m switching',
        'four intended same-direction transfers; no opposite-direction switching','sampled geometry; no signalling/reservation/traversal proof']
    plan['plan_hash']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    return plan


def publish_reciprocal_layout(plan,evidence):
    if plan!=plan_reciprocal_layout(plan.get('brief')):raise ValueError('reciprocal plan differs from brief')
    path=Path(evidence)/(uuid.uuid4().hex+'.reciprocal_plan.json');path.parent.mkdir(parents=True,exist_ok=True);atomic_json(path,plan)
    return {'status':'ok','operation':'reciprocal-layout','stage':'plan','game_constructed':False,'plan_hash':plan['plan_hash'],
        'movements':plan['movements'],'native_runtime_demonstrated':False,'direction_enforcement':'not_provided','evidence':str(path.resolve())}


def _load_layout_record(invocation):
    record=json.loads(Path(invocation).read_text(encoding='utf-8-sig'))
    if not isinstance(record,dict):raise ValueError('layout record must be an object')
    if 'plan' not in record and record.get('evidence'):record=json.loads(Path(record['evidence']).read_text(encoding='utf-8-sig'))
    if not isinstance(record,dict):raise ValueError('layout evidence must be an object')
    return record


def _return_target(client,plan,module,base_record):
    """Select a straight segment on the verified reference route, then native identity."""
    matching=[r for r in base_record['routes'] if {r['from'],r['to']}=={module['reference']+':west',module['reference']+':east'}]
    if len(matching)!=1 or not matching[0]['verified']:raise LiveError('stale_base_layout','reference through route unavailable')
    ids=sorted({x['edge']['entity'] for x in matching[0]['response']['result']['path'] if x['confirmed_TRACK']});edges=[];observations=[]
    for i in range(0,len(ids),16):
        r=client.request('inspect',{'edge_ids':ids[i:i+16]});observations.append(r['request_id'])
        if r['status']!='ok':raise LiveError('stale_base_layout','current reference geometry unavailable')
        edges+=r['result']['edges']
    d=plan['native_construction_direction'];o=plan['brief']['route_reference']['origin'];found=[]
    for e in edges:
        chord=[e['p1'][k]-e['p0'][k] for k in range(3)]
        if e.get('road_type')!='TRACK' or any(abs(e[t][k]-chord[k])>.001 for t in ('t0','t1') for k in range(3)):continue
        xs=[sum((e[p][k]-o[k])*d[k] for k in range(2)) for p in ('p0','p1')];x=module['target_reference_x']
        if not min(xs)+10<x<max(xs)-10:continue
        u=(x-xs[0])/(xs[1]-xs[0]);point=[e['p0'][k]+u*chord[k] for k in range(3)];size=math.hypot(*chord[:2]);sign=1 if xs[1]>xs[0] else -1
        if size<100 or abs(chord[2])>.001:continue
        found.append(_recipe_intent(plan,point,[sign*v/size for v in chord[:2]]))
    if len(found)!=1:raise LiveError('unsupported_native_result','unique current straight reference segment at return station required')
    return found[0],observations


def _return_throat(plan,module,target):
    ports=plan['ports'];roles={}
    for name,track,end in [('A1',module['fan'],'west'),('A2',module['reference'],'west'),('D1',module['fan'],'east'),('D2',module['reference'],'east')]:
        p=ports[track+':'+end];roles[name]={'kind':'approach' if end=='west' else 'destination','endpoint':_recipe_intent(plan,p['position'],p['construction_direction'])}
    return {'roles':roles,'steps':[{'name':'return','kind':'crossover','source':module['source'],'target':target}],
        'required_routes':[{'from':'A1','to':'D1','via':[]},{'from':'A2','to':'D2','via':[]},{'from':'A1','to':'D2','via':['return']}],
        'radius':120,'region':plan['brief']['region'],'vertical':{'max_grade':plan['brief']['max_grade']},'placement_tolerance':.5,'max_fit_attempts':1,'max_route_length':2500}


def _verify_reciprocal_layout(client,plan,record,*,partial=False):
    expected={m['name'] for m in plan['returns']};present=set(record.get('return_runtime',{}))
    if (not partial and present!=expected) or not present<=expected:raise LiveError('incomplete_layout','both reciprocal construction receipts required')
    verify,edges,observations=_switching_verification(client,plan,record)
    if partial:verify['movements']=[r for r in verify['movements'] if r not in [m['transfer'] for m in plan['returns'] if m['name'] not in present]]
    for module in plan['returns']:
        if module['name'] not in present:continue
        saved=record['return_runtime'][module['name']];raw=Path(saved['throat_record']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=saved['sha256']:raise ValueError('return receipt changed')
        built=json.loads(raw.decode('utf-8-sig'));b=built['brief'];target=b['steps'][0]['target'];d=plan['native_construction_direction'];o=plan['brief']['route_reference']['origin']
        if (b!=_return_throat(plan,module,target) or built['summary'].get('status')!='ok'
                or abs(sum((target['guide_xyz'][k]-o[k])*d[k] for k in range(2))-module['target_reference_x'])>.001):raise ValueError('return receipt differs from approved intent')
        a,z=module['name']+'_source',module['name']+'_target';verify['branches'] += [{'name':a,'source':module['source']},{'name':z,'source':target}]
        connector=built['semantic_mapping']['step_edges']['return']
        if not isinstance(connector,list) or not connector or len(connector)>16 or any(type(i) is not int for i in connector):raise ValueError('exact bounded return connector identities required')
        r=client.request('inspect',{'edge_ids':connector,'geometry_constraints':{'radius':120,'max_grade':plan['brief']['max_grade'],'region':plan['brief']['region']}});observations.append(r['request_id'])
        if r['status']!='ok' or {e['id'] for e in r['result']['edges']}!=set(connector) or any(e['road_type']!='TRACK' for e in r['result']['edges']):raise LiveError('stale_switching_connector','current return connector unavailable')
        for row in verify['movements']:
            if {k:row[k] for k in ('from','to')}==module['transfer']:row['via']=[a,z];edges[(row['from'],row['to'])]=connector
            elif {row['from'],row['to']}=={module['fan']+':west',module['fan']+':east'}:
                label=module['name'].removesuffix('_return');row['via']=[label+'_cross_target','branch_'+label,a]
            elif {row['from'],row['to']}=={module['reference']+':west',module['reference']+':east'}:
                row['via']=[module['name'].removesuffix('_return')+'_cross_source',z]
    answer=_verify_parallel_layout(client,verify,record,movement_edges=edges);record['connector_observations']=observations
    return answer|{'transfers_verified':2+len(present),'reciprocal_same_direction':len(present)==2,'direct5m_crossover':False}


def _reciprocal_outcome(plan,record,summary):
    verified={(r['from'],r['to']) for r in record.get('routes',[]) if r.get('verified')}
    summary['movement_results']=[r|{'state':'verified' if (r['from'],r['to']) in verified else 'unverified'} for r in plan['movements']]
    summary['next_action']='none' if summary['status']=='ok' else ('reconcile_native_operation' if summary.get('game_constructed')=='unknown' or record.get('unfinished_step') else 'inspect_current_run')
    summary['native_effect_history_complete']=False
    if 'recorded_prior_game_constructed' in record:summary['recorded_prior_game_constructed']=record['recorded_prior_game_constructed']


def _reciprocal_partial(client,original,record):
    """Fresh bounded evidence; a failed stage is not evidence that it is absent."""
    plan=original['plan'];ops=original.get('operations',[]);states={};record['stage_assessment']=states
    if not isinstance(ops,list) or any(not isinstance(o,dict) or not isinstance(o.get('response'),dict) for o in ops):raise ValueError('reciprocal stage records malformed')
    if set(original.get('pair_runtime',{}))!={'up','down'}:
        base=next((o['response'].get('evidence') for o in reversed(ops) if o['name']=='base_build'),None)
        if not base:raise LiveError('incomplete_layout','base-stage receipt unavailable; no construction inferred')
        child=_load_layout_record(base)
        if child.get('plan')!=plan['base_plan']:raise ValueError('base-stage receipt differs from standalone brief')
        record['base_stage_record']=str(Path(base).resolve());record['base_assessment']={}
        for pair in plan['base_plan']['pairs']:
            record['base_assessment'][pair['name']]=_switching_recipe_assessment(client,plan['base_plan'],pair,child)
        states['base']={'state':'incomplete','stage':child.get('summary',{}).get('stage'),'unfinished':child.get('unfinished_step')}
        steps={label+'_'+n:v['state'] for label,s in record['base_assessment'].items() for n,v in s['steps'].items()}
        unknown=_layout_uncertain_operations(client,original)
        partial_throat=any(s['steps'].get('cross',{}).get('state')=='completed' and label not in child.get('pair_runtime',{}) for label,s in record['base_assessment'].items())
        return {'status':'layout_incomplete','routes_verified':0,'final_network_verified':False,'current_steps':steps,'next_action':'reconcile_native_operation' if unknown else ('reconcile_partial_throat' if partial_throat else 'continue_known_missing_base_stages')}
    current=json.loads(json.dumps(plan));completed={o['name']:o['response'] for o in ops if o['response'].get('status')=='ok'}
    for module in plan['returns']:
        name=module['name'];fixture=name+'_fixture';extension=name+'_extension';cross=name+'_crossover'
        intent=_recipe_intent(plan,plan['ports'][module['fan']+':east']['position'],plan['ports'][module['fan']+':east']['construction_direction'])
        if fixture in completed:
            c,rid=_select_throat_port(client,intent,tolerance=.5);e=c['edge_snapshot'];p=module['fixture']['position'];z=plan['ports'][module['fan']+':east']['position']
            if e.get('road_type')!='TRACK' or not any(math.dist(a,p)<=.001 and math.dist(b,z)<=.001 for a,b in ((e['p0'],e['p1']),(e['p1'],e['p0']))):raise LiveError('layout_state_changed','extended fixture differs from authored interface')
            states[fixture]={'state':'completed','request_id':rid,'current_edge':e['id']}
        else:
            r=discover(client,{'region':module['fixture']['region'],'max_edges':16})
            absent=r['status']=='ok' and r['result'].get('complete') is True and r['result'].get('edge_count')==0
            states[fixture]={'state':'absent' if absent else 'unknown','request_id':r['request_id']}
        if extension in completed:
            states[extension]={'state':'awaiting_route_proof'}
        else:
            current['ports'][module['fan']+':east']=plan['base_plan']['ports'][module['fan']+':east']
            free=True
            for key,sign in [('extension_source',1),('extension_target',-1)]:
                try:_select_throat_port(client,module[key],tolerance=.5,outward_sign=sign)
                except LiveError:free=False
            states[extension]={'state':'absent' if free or states[fixture]['state']=='absent' else 'unknown'}
        states[cross]={'state':'awaiting_route_proof' if name in original.get('return_runtime',{}) else 'unknown'}
    record.update(pair_runtime=original['pair_runtime'],return_runtime=original.get('return_runtime',{}))
    result=_verify_reciprocal_layout(client,current,record,partial=True)
    for module in plan['returns']:
        name=module['name']
        if name+'_extension' in completed:states[name+'_extension']={'state':'completed','basis':'fresh end-to-end through route'}
        if name in record['return_runtime']:states[name+'_crossover']={'state':'completed','basis':'fresh connector/junction/transfer route'}
        elif states[name+'_extension']['state']=='completed':
            target=original.get('return_intents',{}).get(name)
            if target is None:target,_=_return_target(client,current,module,record)
            try:
                for intent in (module['source'],target):_select_throat_port(client,intent,interior=True,tolerance=.5)
                states[name+'_crossover']={'state':'absent','basis':'fresh unsplit native attachments','target':target}
            except LiveError:states[name+'_crossover']={'state':'unknown'}
    result.update(status='layout_incomplete',final_network_verified=False,current_steps={n:v['state'] for n,v in states.items()},next_action='continue_known_missing_stages' if all(v['state'] in ('completed','absent') for v in states.values()) else 'reconcile_unknown_stage')
    return result


def execute_reciprocal_layout(client,plan,*,base_layout_record=None,continuation_record=None):
    if plan!=plan_reciprocal_layout(plan.get('brief')):raise ValueError('reciprocal plan differs from brief')
    if base_layout_record is not None and continuation_record is not None:raise ValueError('use explicit base or current-run continuation, not both')
    original=_load_layout_record(continuation_record) if continuation_record else None
    if original and original.get('summary',{}).get('operation')=='reciprocal-layout-inspect':original=_load_layout_record(original['original_record'])
    if original is not None and original.get('plan')!=plan:raise ValueError('continuation differs from standalone brief')
    base=_load_layout_record(base_layout_record) if base_layout_record is not None else None
    if base is not None and (base.get('plan')!=plan['base_plan'] or base.get('summary',{}).get('status')!='ok' or base.get('unfinished_step')):raise ValueError('explicit base must be a completed matching switching layout')
    path=client.evidence/(uuid.uuid4().hex+'.reciprocal.json');lock=client.evidence/'reciprocal.lock'
    summary={'status':'incomplete','operation':'reciprocal-layout','stage':'base','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'operations':[],'pair_runtime':{},'return_runtime':{}}
    if original:record['recorded_prior_game_constructed']=original.get('summary',{}).get('game_constructed','unknown')
    try:
        with lock.open('x'):pass
    except FileExistsError:raise LiveError('client_busy','one reciprocal layout at a time') from None
    def perform(name,call,mutation=False):
        summary['stage']=name;record['unfinished_step']=name;atomic_json(path,record);r=call()
        record['operations'].append({'name':name,'response':r});record.pop('unfinished_step')
        if mutation:
            effect=r.get('game_constructed',r.get('result',{}).get('game_constructed','unknown'))
            if effect in (True,'unknown') or summary['game_constructed'] is not True:summary['game_constructed']=effect
        atomic_json(path,record)
        if r['status']!='ok':raise LiveError(r['status'],r.get('error',r.get('result',{}).get('error','reciprocal stage failed')))
        return r
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):raise LiveError('reconciliation_required','unfinished native request; no construction')
        completed={}
        if original:
            if original.get('unfinished_step') or _layout_uncertain_operations(client,original):raise LiveError('reconciliation_required','unfinished/uncertain current-run effects; no replay')
            record['original_record']=str(Path(continuation_record).resolve())
            assessed=inspect_reciprocal_layout(client,continuation_record);assessment=_load_layout_record(assessed['evidence']);record['continuation_inspection']=assessed
            if assessed['status']=='ok':
                record.update({k:v for k,v in assessment.items() if k not in ('plan','summary','original_record')})
                summary.update(assessed,evidence=str(path.resolve()),operation='reciprocal-layout',next_action='none');return summary
            if assessed['status']!='layout_incomplete':raise LiveError(assessed['status'],assessed.get('error','current-run inspection failed'))
            record['operations']=list(original.get('operations',[]));record['return_runtime']=dict(original.get('return_runtime',{}))
            if set(original.get('pair_runtime',{}))!={'up','down'}:
                child=assessment['base_stage_record']
                built=perform('base_build',lambda:execute_switching_layout(client,plan['base_plan'],current_run=child),True)
                base=_load_layout_record(built['evidence'])
            else:
                if any(v['state'] not in ('completed','absent') for v in assessment['stage_assessment'].values()):raise LiveError('reconciliation_required','current-run stage not proven completed or absent')
                completed={o['name']:o['response'] for o in original['operations'] if o['response']['status']=='ok' and assessment['stage_assessment'].get(o['name'],{}).get('state')=='completed'}
                proof=assessment;record['pair_runtime']=dict(original['pair_runtime'])
        if original and set(original.get('pair_runtime',{}))=={'up','down'}:
            base=None
        elif not base:
            built=perform('base_build',lambda:execute_switching_layout(client,plan['base_plan']),True);base=_load_layout_record(built['evidence'])
        if base:
            proof_path=client.evidence/(uuid.uuid4().hex+'.reciprocal_base.json');proof={'plan':plan['base_plan'],'pair_runtime':base['pair_runtime'],'summary':{'evidence':str(proof_path.resolve())}}
            _verify_switching_layout(client,plan['base_plan'],proof);atomic_json(proof_path,proof)
            record.update(base_readback=str(proof_path.resolve()),pair_runtime=base['pair_runtime'])
        targets={};record['return_intents']={}
        for module in plan['returns']:
            if module['name'] in record['return_runtime']:continue
            target,observations=_return_target(client,plan,module,proof);targets[module['name']]=target
            record['return_intents'][module['name']]=target
            record.setdefault('target_observations',[]).extend(observations)
        for module in plan['returns']:
            name=module['name'];f=module['fixture'];source=proof['current_ports'][module['fan']+':east']
            if name in record['return_runtime']:continue
            q={'authorised':True,'length':20,'fixture':{'template_edge':source['edge_id'],'position':f['position'],'travel_direction':f['travel_direction'],'grade':0,'region':f['region']}}
            if name+'_fixture' not in completed:perform(name+'_fixture',lambda q=q:client.request('test_approach',q),True)
            a,z=(module[k]['guide_xyz'] for k in ('extension_source','extension_target'));region={'min':[max(min(a[k],z[k])-40,plan['brief']['region']['min'][k]) for k in range(3)],'max':[min(max(a[k],z[k])+40,plan['brief']['region']['max'][k]) for k in range(3)]}
            b={'source':module['extension_source'],'target':module['extension_target'],'radius':120,'region':region,'vertical':{'max_grade':plan['brief']['max_grade']},'max_fit_attempts':1,'max_route_length':800}
            if name+'_extension' not in completed:perform(name+'_extension',lambda b=b:connect_brief(client,b,execute=True),True)
            b=_return_throat(plan,module,targets[name]);built=perform(name+'_crossover',lambda b=b:connect_throat(client,b,execute=True),True)
            p=Path(built['evidence']);record['return_runtime'][name]={'throat_record':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()};atomic_json(path,record)
        summary['stage']='final_readback';summary.update(_verify_reciprocal_layout(client,plan,record),status='ok',stage='verified')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:
        if getattr(exc,'status',None)=='mutation_outcome_unknown':summary['game_constructed']='unknown'
        summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:_reciprocal_outcome(plan,record,summary);atomic_json(path,record);lock.unlink(missing_ok=True)
    return summary


def inspect_reciprocal_layout(client,invocation):
    original=_load_layout_record(invocation);plan=original['plan']
    if plan!=plan_reciprocal_layout(plan.get('brief')):raise ValueError('reciprocal invocation differs from brief')
    path=client.evidence/(uuid.uuid4().hex+'.reciprocal_inspection.json')
    summary={'status':'incomplete','operation':'reciprocal-layout-inspect','game_constructed':False,'plan_hash':plan['plan_hash'],'evidence':str(path.resolve()),'routes_verified':0,'train_traversal':'unprobed'}
    record={'plan':plan,'summary':summary,'original_record':str(Path(invocation).resolve()),'pair_runtime':original.get('pair_runtime',{}),'return_runtime':original.get('return_runtime',{}),
        'recorded_prior_game_constructed':original.get('summary',{}).get('game_constructed','unknown')}
    try:
        if set(original.get('return_runtime',{}))=={m['name'] for m in plan['returns']}:summary.update(_verify_reciprocal_layout(client,plan,record),status='ok',stage='verified')
        elif original.get('operations'):summary.update(_reciprocal_partial(client,original,record))
        else:raise LiveError('incomplete_layout','construction-stage evidence unavailable')
    except (LiveError,ValueError,KeyError,TypeError,OSError) as exc:summary.update(status=getattr(exc,'status','invalid_result'),error=str(exc)[:400])
    finally:
        next_action=summary.get('next_action');_reciprocal_outcome(plan,record,summary)
        if next_action:summary['next_action']=next_action
        atomic_json(path,record)
    return summary


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
                if 'representation' in step:params['representation']=step['representation']
                if reconciled_crossover is not None and step is brief['steps'][0]:
                    saved=json.loads(Path(reconciled_crossover).read_text())
                    old=saved.get('verification_params',{})
                    if saved.get('status')!='reconciled_verified_crossover' or old.get('representation','native_parts')!=params.get('representation','native_parts') or any(old.get(k)!=params[k] for k in ('location','target_location','radius','region','vertical','max_route_length')):
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

def reconcile_rejected_extension(client, discovery):
    """Observe an unchanged free anchor after explicit rejection; never replay."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if (state.get('session')!=client.session or not pending
            or pending.get('session')!=client.session or pending.get('operation')!='extension'
            or pending.get('params',{}).get('execute') is not True):
        raise LiveError('reconciliation_required','no current-session pending native-rejected extension')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text());result=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid
            or response.get('operation')!='extension' or response.get('status')!='error'
            or result.get('native_command_success') is not False
            or result.get('error')!='native_construction_rejected' or result.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native extension rejection',rid)
    brief=validate_brief(pending['params']['brief'])
    if (not isinstance(discovery,dict) or discovery.get('operation')!='discover'
            or discovery.get('session')!=client.session or discovery.get('status')!='ok'):
        raise LiveError('reconciliation_required','current-session anchor discovery required',rid)
    def selected(record):
        value=record.get('result',{})
        matches=[c for c in value.get('candidates',[]) if
                 c.get('edge_id')==brief['anchor_edge'] and c.get('node_id')==brief['anchor_node']]
        if (value.get('complete') is not True or value.get('truncated') is not False
                or value.get('game_constructed') is not False or len(matches)!=1):
            raise LiveError('reconciliation_required','anchor discovery incomplete or ambiguous',rid)
        c=matches[0];snapshot=c.get('edge_snapshot',{})
        if (c.get('eligible') is not True or c.get('incidence_complete') is not True
                or c.get('incident_output_truncated') is not False or c.get('incident_count')!=1
                or c.get('incident_edges')!=[brief['anchor_edge']]
                or c.get('construction_owner') not in (None,'none',-1,0)
                or snapshot.get('id')!=brief['anchor_edge'] or snapshot.get('road_type')!='TRACK'
                or brief['anchor_node'] not in (snapshot.get('node0'),snapshot.get('node1'))):
            raise LiveError('reconciliation_required','exact free TRACK anchor not established',rid)
        pos=c.get('pos');endpoint=snapshot.get('p0' if snapshot.get('node0')==brief['anchor_node'] else 'p1')
        if (not isinstance(pos,list) or len(pos)!=3 or pos!=endpoint
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in pos)):
            raise LiveError('reconciliation_required','anchor position unavailable or inconsistent',rid)
        return c
    original=selected(discovery);fit=result.get('fit',{})
    if fit.get('start_node')!=brief['anchor_node'] or fit.get('start')!=original['pos']:
        raise LiveError('reconciliation_required','rejected fit does not bind the original anchor',rid)
    pos=original['pos'];region={'min':[x-1 for x in pos],'max':[x+1 for x in pos]}
    observed=discover(client,{'region':region,'max_edges':16})
    if (observed.get('status')!='ok' or observed.get('session')!=client.session
            or observed.get('operation')!='discover'):
        raise LiveError('reconciliation_required','fresh anchor observation unavailable',rid)
    current=selected(observed)
    if current['edge_snapshot']!=original['edge_snapshot'] or current['pos']!=pos:
        raise LiveError('reconciliation_required','anchor changed; extension outcome uncertain',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('session')!=client.session or latest.get('pending')!=pending:
        raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_extension','original_pending':pending,
            'original_response':str(response_path.resolve()),'anchor_discovery':discovery['request_id'],
            'observation':observed['request_id'],'anchor_edge':brief['anchor_edge'],
            'anchor_node':brief['anchor_node'],'anchor_unchanged_and_free':True,
            'completed_extension_absent':True,'other_effects':'unknown',
            'effects_history_complete':False,'automatic_replay':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_vehicle_assignment(client):
    """Reconcile an explicitly rejected assignment only while the train remains in depot.

    No replay or effect-history claim. Legacy adapters need a normal reload before
    further controls because their rejected callback retained its in-memory guard.
    """
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if (not pending or pending.get('operation')!='operating_control'
            or pending.get('params',{}).get('action')!='vehicle_assign'
            or pending['params'].get('execute') is not True):
        raise LiveError('reconciliation_required','pending vehicle assignment required')
    rid=pending['request_id'];path=client.evidence/(rid+'.response.json')
    response=json.loads(path.read_text());value=response.get('result',{})
    legacy=(response.get('status')=='mutation_unverified'
            and str(value.get('error','')).endswith('native_operating_command_rejected'))
    explicit=(response.get('status')=='error' and value.get('native_command_success') is False
              and value.get('error')=='native_operating_command_rejected')
    if (response.get('session')!=client.session or response.get('operation')!='operating_control'
            or response.get('request_id')!=rid or not (legacy or explicit)):
        raise LiveError('reconciliation_required','explicit native assignment rejection required',rid)
    vid=pending['params']['vehicle_id'];observed=client.request('operating_inspect',{'vehicle_ids':[vid],'limit':1})
    rows=observed.get('result',{}).get('vehicles',{}).get('records',[])
    if (observed.get('status')!='ok' or observed.get('session')!=client.session or len(rows)!=1
            or rows[0].get('id')!=vid or rows[0].get('line')!=-1
            or type(rows[0].get('depot')) is not int or rows[0]['depot']<=0 or rows[0].get('state')!='0'):
        raise LiveError('reconciliation_required','exact currently unassigned train in depot required',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_vehicle_assignment','original_pending':pending,
            'original_response':str(path.resolve()),'observation':observed['request_id'],
            'current_vehicle':rows[0],'assignment_present':False,'other_effects':'unknown',
            'automatic_replay':False,'legacy_adapter_reload_required':legacy}
    evidence=client.evidence/(rid+'.reconciliation.json');atomic_json(evidence,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(evidence.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(evidence.resolve())}


def reconcile_rejected_connection(client, discoveries=None):
    """Record a native-rejected connection as absent using fresh exact incidence."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation'] not in ('connection','selected_connection') or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','only a pending native-rejected connection is supported')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text());result=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid
            or response.get('status')!='error' or result.get('native_command_success') is not False
            or result.get('error')!='native_construction_rejected' or result.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native connection rejection evidence',rid)
    if pending['operation']=='selected_connection':
        p=pending['params'];observed=client.request('selected_connection',p|{'execute':False});fit=observed.get('result',{}).get('fit',{})
        if observed['status']!='ok' or observed.get('result',{}).get('game_constructed') is not False or fit.get('start_node')!=p['source']['node_id'] or fit.get('target_node')!=p['target']['node_id']:
            raise LiveError('reconciliation_required','exact unchanged free attachments not established',rid)
        latest=json.loads(client.journal.read_text())
        if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
        record={'status':'reconciled_rejected_connection','original_pending':pending,'original_response':str(response_path.resolve()),'observation':observed['request_id'],
            'completed_connection_constructed':False,'other_effects':'unknown','effects_history_complete':False,'automatic_replay':False}
        path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record);latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
        latest.pop('pending');atomic_json(client.journal,latest);return {'status':'ok','result':record,'evidence':str(path.resolve())}
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
    if brief.get('station_target'):
        # A rejected station approach can start at an already connected node.
        # A fresh exact free target proves the requested connection is absent;
        # it does not prove an exhaustive history of other native effects.
        target=selected[1]
        if (target.get('eligible') is not True or target.get('incidence_complete') is not True
                or target.get('incident_output_truncated') or target.get('incident_count')!=1
                or target.get('incident_edges')!=[brief['target_edge']]):
            raise LiveError('reconciliation_required','station target is not currently an exact free endpoint',rid)
        observed=client.request('connection',{'brief':brief,'execute':False})
        fit=observed.get('result',{}).get('fit',{})
        if (observed['status']!='ok' or observed.get('result',{}).get('game_constructed') is not False
                or fit.get('start_node')!=brief['anchor_node'] or fit.get('target_node')!=brief['target_node']):
            raise LiveError('reconciliation_required','current exact station attachments unavailable',rid)
        latest=json.loads(client.journal.read_text())
        if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
        record={'status':'reconciled_rejected_connection','original_pending':pending,
                'original_response':str(response_path.resolve()),'observation':observed['request_id'],
                'facts':{'target_currently_free':True,'completed_connection_absent':True,
                         'source_current_incident_edges':selected[0].get('incident_edges')},
                'completed_connection_constructed':False,'other_effects':'unknown',
                'effects_history_complete':False,'automatic_replay':False}
        path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
        latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
        latest.pop('pending');atomic_json(client.journal,latest)
        return {'status':'ok','result':record,'evidence':str(path.resolve())}
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

def reconcile_rejected_structured_chain(client):
    """Reconcile explicit rejected new alignment using fresh exact free ports.

    Establishes only that the requested connection is absent; other partial
    effects remain unknown. Never rebuilds or clears a different request.
    """
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending.get('operation')!='structured_chain' or pending.get('params',{}).get('execute') is not True:
        raise LiveError('reconciliation_required','no pending structured-chain execution')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text())
    if response.get('session')!=client.session or response.get('request_id')!=rid or response.get('operation')!='structured_chain' or response.get('status')!='mutation_unverified' or response.get('result',{}).get('native_command_success') is not False:
        raise LiveError('reconciliation_required','no explicit native structured-chain rejection',rid)
    handle=pending['params']['prepared_request'];prepared=json.loads((client.evidence/(handle+'.request.json')).read_text())
    if prepared.get('session')!=client.session or prepared.get('request_id')!=handle or prepared.get('operation')!='structured_chain':
        raise LiveError('reconciliation_required','current-session new-alignment preparation required',rid)
    params=prepared.get('params',{})
    groups=params.get('groups',[params])
    if (not isinstance(groups,list) or len(groups) not in (1,2,4)
            or any(not isinstance(g,dict) or g.get('new_alignment') is not True for g in groups)):
        raise LiveError('reconciliation_required','bounded new-alignment preparation required',rid)
    ports=[g[key] for g in groups for key in ('source','target')]
    observations=[]
    for port in ports:
        snapshot=port['edge_snapshot'];pos=snapshot['p0'] if snapshot['node0']==port['node_id'] else snapshot['p1']
        observed=client.request('discover',{'region':{'min':[x-10 for x in pos],'max':[x+10 for x in pos]},'max_edges':16})
        matches=[p for p in observed.get('result',{}).get('candidates',[]) if p['edge_id']==port['edge_id'] and p['node_id']==port['node_id']]
        if observed['status']!='ok' or observed.get('session')!=client.session or observed.get('operation')!='discover' or observed['result'].get('complete') is not True or observed['result'].get('truncated') is not False or len(matches)!=1:
            raise LiveError('reconciliation_required','exact attachment observation incomplete',rid)
        current=matches[0]
        if current.get('eligible') is not True or current.get('incidence_complete') is not True or current.get('incident_count')!=1 or current.get('incident_edges')!=[port['edge_id']] or current['edge_snapshot'].get('id')!=port['edge_id'] or current['edge_snapshot'].get('road_type')!='TRACK':
            raise LiveError('reconciliation_required','requested connection absence not established',rid)
        if any(current['edge_snapshot'].get(k)!=snapshot.get(k) for k in ('node0','node1','p0','p1','t0','t1','template','style')):
            raise LiveError('reconciliation_required','source attachment changed',rid)
        observations.append(observed['request_id'])
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_structured_chain','original_pending':pending,'original_response':str(response_path.resolve()),'observations':observations,'completed_connection_absent':True,'other_effects':'unknown','effects_history_complete':False,'automatic_replay':False,'native_guard':'requires normal session reload before another structure preparation'}
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
    details={}
    if 'prepared_request' in pending['params']:
        # Prepared handles are consumed before build and are execution-only.
        # Recover the original intent from correlated publication evidence, never
        # send the consumed handle or create another preparation during recovery.
        try:
            pid=pending['params']['prepared_request']
            assert isinstance(pid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pid)
            assert state['session']==client.session and pending['session']==client.session
            assert pending['params']=={'prepared_request':pid,'execute':True}
            request=json.loads((client.evidence/(rid+'.request.json')).read_text())
            prep_path=client.evidence/(pid+'.request.json');prepared_path=client.evidence/(pid+'.response.json')
            prep=json.loads(prep_path.read_text());accepted=json.loads(prepared_path.read_text())
            envelope={k:pending[k] for k in ('version','session','sequence','request_id','operation','params')}
            assert request==envelope and client._existing_bytes(client._slot(request))==client._request_body(request)
            assert prep['version']==1 and prep['session']==client.session and prep['request_id']==pid and prep['operation']=='crossover'
            assert type(prep['sequence']) is int and 0<prep['sequence']<request['sequence']
            assert client._existing_bytes(client._slot(prep))==client._request_body(prep)
            assert accepted['version']==1 and accepted['session']==client.session and accepted['request_id']==pid and accepted['operation']=='crossover' and accepted['status']=='ok'
            a=accepted['result'];assert a['prepared_request']==pid and a['native_proposal_evaluated'] is True and a['native_proposal_critical'] is False
            intent=prep['params'];assert intent['prepare'] is True and intent['execute'] is False
            snapshots=[intent[k]['edge_snapshot'] for k in ('source','target')]
            ids=[e['id'] for e in snapshots];assert len(set(ids))==2
            for k,e in zip(('source','target'),snapshots):
                assert intent[k]['edge_id']==e['id'] and type(intent[k]['canonical_forward']) is bool
                assert all(key in e for key in ('node0','node1','p0','p1','t0','t1','template','style'))
        except (OSError,ValueError,KeyError,TypeError,AssertionError) as exc:
            raise LiveError('reconciliation_required','prepared crossover evidence missing, stale or mismatched',rid) from exc
        def read(operation,params):
            answer=client.request(operation,params)
            if answer.get('status')!='ok' or answer.get('session')!=client.session or answer.get('operation')!=operation:
                raise LiveError('reconciliation_required','prepared crossover observation unavailable',rid)
            return answer
        observed=read('inspect',{'edge_ids':ids})
        if {e['id']:e for e in observed.get('result',{}).get('edges',[])}!={e['id']:e for e in snapshots}:
            raise LiveError('reconciliation_required','original prepared through edges changed',rid)
        routes=[]
        for k,e in zip(('source','target'),snapshots):
            forward=intent[k]['canonical_forward']
            answer=read('route',{'source_edge':e['id'],'source_node':e['node0'] if forward else e['node1'],
                'target_edge':e['id'],'target_node':e['node1'] if forward else e['node0'],
                'single_edge':True,'required_edges':[e['id']],'mode':'TRAIN','max_length':intent['max_route_length'],
                'junction_nodes':intent.get('junction_nodes',[])})
            if answer.get('result',{}).get('requested_route_verified') is not True:
                raise LiveError('reconciliation_required','original prepared through route unverified',rid)
            routes.append(answer['request_id'])
        local=discover(client,{'region':intent['region'],'max_edges':16})
        if local.get('status')!='ok' or local.get('session')!=client.session or local.get('operation')!='discover':
            raise LiveError('reconciliation_required','local prepared-rejection observation unavailable',rid)
        details={'prepared_request':pid,'preparation_request_sha256':hashlib.sha256(prep_path.read_bytes()).hexdigest(),
            'preparation_response_sha256':hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
            'through_observations':routes,'local_effects_observation':local['request_id'],
            'local_effects':local.get('result',{}),'native_effect_history_complete':False}
    else:
        observed=client.request('crossover',pending['params']|{'execute':False});r=observed.get('result',{})
        if observed['status']!='ok' or r.get('game_constructed') is not False or len(r.get('through_before',[]))!=2 or any(x.get('requested_route_verified') is not True for x in r['through_before']):
            raise LiveError('reconciliation_required','unchanged original through edges/routes not established',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_crossover','original_pending':pending,'observation':observed['request_id'],
            'completed_crossover_absent':True,'other_effects':'unknown','automatic_replay':False,**details}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def reconcile_rejected_scissors(client):
    """Observe unchanged original rails after rejection; never replay the proposal."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='scissors_candidate' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending native-rejected scissors')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json');response=json.loads(response_path.read_text());v=response.get('result',{})
    if (response.get('session')!=client.session or response.get('request_id')!=rid or response.get('operation')!='scissors_candidate'
            or response.get('status')!='error' or v.get('native_command_success') is not False
            or v.get('error')!='native_construction_rejected' or v.get('stage')!='build'):
        raise LiveError('reconciliation_required','no explicit native scissors rejection',rid)
    observed=client.request('scissors_candidate',pending['params']|{'execute':False})
    expected=[pending['params']['leads'][n]['source']['edge_snapshot'] for n in ('L0','L1')]
    if observed['status']!='ok' or observed.get('result',{}).get('game_constructed') is not False or observed['result'].get('originals')!=expected:
        raise LiveError('reconciliation_required','unchanged original running rails not established',rid)
    routes=[]
    for e in expected:
        route=client.request('route',{'source_edge':e['id'],'source_node':e['node0'],'target_edge':e['id'],'target_node':e['node1'],
            'single_edge':True,'mode':'TRAIN','required_edges':[e['id']],'max_length':pending['params']['max_route_length']})
        routes.append(route['request_id'])
        if route['status']!='ok' or route.get('result',{}).get('requested_route_verified') is not True:
            raise LiveError('reconciliation_required','original through route not established',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_rejected_scissors','original_pending':pending,'original_response':str(response_path.resolve()),
        'observation':observed['request_id'],'through_observations':routes,'completed_scissors_absent':True,
        'other_effects':'unknown','effects_history_complete':False,'automatic_replay':False}
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


def reconcile_constructed_crossover(client,original_client=None,*,acceptance_revision=None):
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
    revision=None
    if acceptance_revision is not None:
        q=acceptance_revision
        if (not isinstance(q,dict) or set(q)!={'original_request','radius','reason','authority'}
                or q['original_request']!=rid or type(q['radius']) not in (int,float)
                or not math.isfinite(q['radius']) or q['radius']<=0
                or any(not isinstance(q[k],str) or not q[k].strip() or len(q[k])>500 for k in ('reason','authority'))):
            raise ValueError('invalid explicit crossover acceptance revision')
        previous=pending['params'].get('radius')
        if type(previous) not in (int,float) or not math.isfinite(previous) or previous<=0:
            raise ValueError('original crossover radius unavailable')
        revision=q.copy()|{'original_criteria':{'radius':previous},'revised_criteria':{'radius':q['radius']}}
    params=pending['params']|{'execute':False,'fit':fit,'edge_ids':ids,'original_request':rid}
    if revision:params['radius']=revision['radius']
    observed=client.request('verify_crossover',params);r=observed.get('result',{})
    if (observed['status']!='ok' or r.get('reconciled_current_state') is not True or r.get('readback',{}).get('connected') is not True
            or r.get('crossover_after',{}).get('requested_route_verified') is not True or len(r.get('placements',[]))!=2
            or any(x.get('original_removed') is not True or x.get('subdivision_sampled_verified') is not True for x in r['placements'])
            or len(r.get('through_after',[]))!=2 or any(x.get('requested_route_verified') is not True for x in r['through_after'])):
        raise LiveError('reconciliation_required',r.get('error','current crossover unverified'),rid)
    if revision and (observed.get('session')!=client.session or observed.get('operation')!='verify_crossover'
            or r.get('readback',{}).get('requested_min_radius')!=revision['radius']
            or r.get('readback',{}).get('engineering_checks_verified') is not True):
        raise LiveError('reconciliation_required','revised criterion lacks fresh native engineering verification',rid)
    latest=json.loads(old.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during readback',rid)
    record={'status':'reconciled_verified_crossover','original_pending':pending,'verification_params':params,'observation':observed['request_id'],
            'current_session':client.session,'verified':r,'automatic_replay':False,'native_effect_history_complete':False}
    if revision:
        record['acceptance_revision']=revision
        original_path=old.evidence/(rid+'.response.json')
        record['original_response']=str(original_path.resolve())
        record['original_response_sha256']=hashlib.sha256(original_path.read_bytes()).hexdigest()
    path=old.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_constructions',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(old.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}


def reconcile_constructed_structured_junction(client):
    """Verify an exact structured two-junction receipt without rebuilding it."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending.get('operation')!='structured_chain' or pending['params'].get('execute') is not True:
        raise LiveError('reconciliation_required','no pending structured junction')
    rid=pending['request_id'];original=json.loads((client.evidence/(rid+'.response.json')).read_text())
    prepared=json.loads((client.evidence/(pending['params']['prepared_request']+'.request.json')).read_text())
    ready=json.loads((client.evidence/(prepared['request_id']+'.response.json')).read_text())
    params=prepared['params'];result=original.get('result',{});ids=result.get('returned_edges')
    segments=ready.get('result',{}).get('segments',[]);controls=[x['controls'] for x in segments]
    if (original.get('session')!=client.session or original.get('request_id')!=rid or original.get('operation')!='structured_chain'
            or original.get('status')!='mutation_unverified' or result.get('game_constructed') is not True
            or prepared.get('session')!=client.session or prepared.get('operation')!='structured_chain'
            or ready.get('session')!=client.session or ready.get('request_id')!=prepared['request_id'] or ready.get('status')!='ok'
            or params.get('junctions') is not True or not all(params[k].get('location') for k in ('source','target'))
            or not controls or not isinstance(ids,list) or len(ids)!=len(controls)+4 or len(ids)>12
            or len(set(ids))!=len(ids) or any(type(i) is not int or i<=0 for i in ids)):
        raise LiveError('reconciliation_required','no exact prepared structured junction receipt',rid)
    q={k:params[k] for k in ('source','target','region','radius','vertical')}
    q=json.loads(json.dumps(q));q['max_route_length']=params.get('max_route_length',8000)
    def point(e,u):
        weights=(2*u**3-3*u*u+1,u**3-2*u*u+u,-2*u**3+3*u*u,u**3-u*u)
        return [sum(w*e[k][axis] for w,k in zip(weights,('p0','t0','p1','t1'))) for axis in range(3)]
    for key,position,tangent in (('source',controls[0]['p0'],controls[0]['t0']),('target',controls[-1]['p1'],controls[-1]['t1'])):
        port=q[key];edge=port['edge_snapshot'];lo,hi=.05,.95
        for _ in range(80):
            a,b=lo+(hi-lo)/3,hi-(hi-lo)/3
            if math.dist(point(edge,a),position)<=math.dist(point(edge,b),position):hi=b
            else:lo=a
        u=(lo+hi)/2
        if math.dist(point(edge,u),position)>.001:raise LiveError('reconciliation_required','recorded attachment differs from named original curve',rid)
        weights=(6*u*u-6*u,3*u*u-4*u+1,-6*u*u+6*u,3*u*u-2*u)
        direction=[sum(w*edge[k][axis] for w,k in zip(weights,('p0','t0','p1','t1'))) for axis in range(3)]
        horizontal=math.hypot(*tangent[:2])
        port.update(parameter=u,canonical_forward=sum(a*b for a,b in zip(direction,tangent))>0,
                    outward_direction=[tangent[0]/horizontal,tangent[1]/horizontal,0],grade=tangent[2]/horizontal)
    q.update(execute=False,edge_ids=ids,original_request=rid,fit={'pieces':len(controls),'controls':controls,
             'start':controls[0]['p0'],'finish':controls[-1]['p1'],'grade':q['source']['grade'],'end_grade':q['target']['grade']})
    observed=client.request('verify_crossover',q);v=observed.get('result',{});rb=v.get('readback',{})
    if (observed.get('session')!=client.session or observed.get('operation')!='verify_crossover' or observed['status']!='ok'
            or v.get('reconciled_current_state') is not True or rb.get('connected') is not True
            or v.get('crossover_after',{}).get('requested_route_verified') is not True
            or len(v.get('through_after',[]))!=2 or any(x.get('requested_route_verified') is not True for x in v['through_after'])
            or len(v.get('placements',[]))!=2 or any(x.get('original_removed') is not True for x in v['placements'])
            or set(rb.get('ordered_edges',[])+[i for x in v['placements'] for i in x['replacement_edges']])!=set(ids)):
        raise LiveError('reconciliation_required','current structured junction not verified',rid)
    inspected=client.request('inspect',{'edge_ids':rb['ordered_edges'],'structures':True});rows={e['id']:e for e in inspected.get('result',{}).get('edges',[])}
    if inspected['status']!='ok' or inspected.get('session')!=client.session or set(rows)!=set(rb['ordered_edges']):
        raise LiveError('reconciliation_required','current branch structure observation incomplete',rid)
    for eid,item in zip(rb['ordered_edges'],segments):
        actual=rows[eid].get('structure',{});wanted=item['structure']
        if any(actual.get(k)!=wanted.get(k) for k in ('classification','resource_name')):
            raise LiveError('reconciliation_required','current branch structure differs from prepared intent',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending changed during observation',rid)
    record={'status':'reconciled_verified_structured_junction','original_pending':pending,'original_response':original,
            'verification_params':q,'verification':observed,'structures':inspected,'automatic_replay':False,'native_effect_history_complete':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_constructions',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
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
    if params.get('target') is None:
        free=result.get('free_end',{})
        if (not rb.get('ordered_nodes') or free.get('exact_native_identity') is not True
                or free.get('free') is not True or free.get('node')!=rb['ordered_nodes'][-1]
                or free.get('edge')!=rb['ordered_edges'][-1]
                or free.get('incident_edges')!=[free.get('edge')]):
            raise LiveError('reconciliation_required','exact free lead endpoint not verified',rid)
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

def place_signal(client, brief, *, execute=False):
    """Fresh native template discovery and explicit placement; no replay on failure."""
    keys = {'edge_id', 'parameter', 'forward', 'one_way'}
    if type(brief) is not dict or set(brief)-{'replace_signal_id'} != keys or type(execute) is not bool:
        raise ValueError('signal requires edge_id, parameter, forward, one_way and boolean execute')
    if type(brief['edge_id']) is not int or brief['edge_id'] <= 0:
        raise ValueError('signal edge_id must be an exact positive native ID')
    if 'replace_signal_id' in brief and (type(brief['replace_signal_id']) is not int or brief['replace_signal_id']<=0):
        raise ValueError('replacement requires exact positive signal ID')
    if (type(brief['parameter']) not in (int, float) or not math.isfinite(brief['parameter'])
            or not 0 < brief['parameter'] < 1
            or any(type(brief[k]) is not bool for k in ('forward', 'one_way'))):
        raise ValueError('signal needs an interior native parameter and explicit direction/one_way')
    observed = client.request('operating_inspect', {'track_ids': [brief['edge_id']]})
    if observed['status'] != 'ok':
        return observed
    rows = observed.get('result', {}).get('tracks', {}).get('records', [])
    if len(rows) != 1 or rows[0]['id'] != brief['edge_id']:
        raise LiveError('reconciliation_required', 'exact signal target observation unavailable')
    params = dict(brief, revision=rows[0]['revision'])
    if 'replace_signal_id' in brief:
        ident=brief['replace_signal_id']
        matching=[x for x in rows[0]['objects'] if x['id']==ident and isinstance(x.get('signal'),dict)
                  and abs(x.get('parameter',-1)-brief['parameter'])<=.0001]
        if len(matching)!=1:raise LiveError('reconciliation_required','replacement signal not at exact requested attachment')
        params['replace_signal_revision']=matching[0]['revision']
    prepared = client.request('operating_inspect', {'signal_placement': params})
    if prepared['status'] != 'ok' or not execute:
        return prepared
    seed = prepared['result']['signal_placement']['seed']
    params = dict(params, seed_id=seed['id'], seed_revision=seed['revision'], action='signal_place', execute=True)
    return client.request('operating_control', params)


def place_depot(client, brief, *, execute=False):
    """Prepare from native construction parameters; submit once only on explicit execution.

    Command preparation is not a world preview or proof of rail attachment. The
    caller must inspect the realised exit and connect/verify it separately.
    """
    keys = {'resource', 'template', 'params', 'position', 'angle', 'name'}
    if type(brief) is not dict or set(brief) != keys or type(execute) is not bool:
        raise ValueError('depot requires resource/template/params/position/angle/name and boolean execute')
    if (type(brief['resource']) is not str or '/depots/rail/' not in brief['resource']
            or type(brief['template']) is not int or brief['template'] < 0
            or type(brief['params']) is not dict or len(brief['params']) > 16
            or type(brief['name']) is not str or not 1 <= len(brief['name']) <= 80):
        raise ValueError('depot requires a rail resource, explicit template/parameters and bounded name')
    if (type(brief['position']) is not list or len(brief['position']) != 3
            or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) >= 100000 for v in brief['position'])
            or type(brief['angle']) not in (int, float) or not math.isfinite(brief['angle']) or abs(brief['angle']) >= 100):
        raise ValueError('depot requires finite native position and rotation in radians')
    prepared = client.request('operating_inspect', {'depot_preparation': brief})
    if prepared['status'] != 'ok' or not execute:
        return prepared
    record = prepared.get('result', {}).get('depot_preparation', {})
    if (record.get('command_constructed') is not True or record.get('native_command_submitted') is not False
            or record.get('resource') != brief['resource'] or record.get('template') != brief['template']):
        raise LiveError('reconciliation_required', 'matching native depot command preparation unavailable')
    return client.request('operating_control', dict(brief, action='depot_build', execute=True))


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
    if type(brief['max_length']) not in (int, float) or not math.isfinite(brief['max_length']) or not 0 < brief['max_length'] <= 8000:
        raise ValueError('route max_length must be finite and within (0,8000] native units')
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
    # Windows readers/filters can briefly deny replacement after the file closes.
    # Retry only this prepared file, never serialization or a native request.
    delays = (.01, .02, .04, .08, .16)
    for attempt in range(len(delays) + 1):
        try:
            os.replace(temp, path)
            return
        except OSError as exc:
            if getattr(exc, 'winerror', None) not in (5, 32, 33) or attempt == len(delays):
                raise  # Preserve the old destination and prepared temp on failure.
            time.sleep(delays[attempt])

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
    bounded_rejection=(data.get('status')=='no_accepted_candidate' and operation in ('junction','interior_junction','crossover')
        and isinstance(data.get('result'),dict) and data['result'].get('search_complete') is True
        and data['result'].get('game_constructed') is False)
    structure_rejection=(data.get('status')=='no_accepted_candidate' and operation=='structured_chain'
        and isinstance(data.get('result'),dict) and data['result'].get('game_constructed') is False
        and isinstance(data['result'].get('evaluation'),dict)
        and (data['result']['evaluation'].get('critical') is True
             or type(data['result']['evaluation'].get('message_count')) is int
             and data['result']['evaluation']['message_count']>0))
    if data.get('status') not in {'ok', 'error', 'mutation_unverified'} and not (bounded_rejection or structure_rejection):
        raise LiveError('protocol_error', 'invalid response status', request_id)
    return data

class LiveClient:
    def remove_exact_chain(self, edge_ids, *, allow_structures=False):
        """Remove one explicitly named observed open chain; never select by region."""
        if (type(allow_structures) is not bool or type(edge_ids) is not list or not 1 <= len(edge_ids) <= 16
                or any(type(x) is not int or x <= 0 for x in edge_ids)
                or len(set(edge_ids)) != len(edge_ids)):
            raise ValueError('exact chain requires 1..16 distinct native edge IDs')
        query = {'edge_ids': edge_ids}
        if allow_structures:
            query['structures'] = True
        observed = self.request('inspect', query)
        rows = observed.get('result', {}).get('edges', [])
        byid = {e['id']: e for e in rows}
        if observed['status'] != 'ok' or set(byid) != set(edge_ids):
            raise LiveError('reconciliation_required', 'exact chain observation unavailable')
        params = {'authorised': True, 'exact_chain': True, 'edges': [byid[x] for x in edge_ids]}
        if allow_structures:
            if any(e.get('structure', {}).get('classification') not in ('NORMAL', 'BRIDGE', 'TUNNEL') for e in rows):
                raise LiveError('reconciliation_required', 'exact structure observation unavailable')
            params['allow_structures'] = True
        return self.request('remove_branch', params)

    def compensate_crossover(self, *, connector_ids, reason, authority, original_client=None):
        """Explicit exact-receipt connector removal, never acceptance or replay."""
        old=original_client or self;state=json.loads(old.journal.read_text());pending=state.get('pending')
        if not pending or pending.get('operation')!='crossover' or pending['params'].get('execute') is not True:
            raise LiveError('reconciliation_required','no unresolved constructed crossover')
        rid=pending['request_id'];path=old.evidence/(rid+'.response.json');response=json.loads(path.read_text());r=response.get('result',{})
        envelope={k:pending[k] for k in ('version','session','sequence','request_id','operation','params')}
        if (pending.get('publication',{}).get('state') not in (None,'published')
                or old._existing_bytes(old._slot(pending))!=old._request_body(pending)
                or json.loads((old.evidence/(rid+'.request.json')).read_text())!=envelope):
            raise LiveError('reconciliation_required','original crossover publication identity unproven')
        if (response.get('session')!=pending['session'] or response.get('request_id')!=rid or response.get('operation')!='crossover'
                or response.get('status')!='mutation_unverified' or r.get('game_constructed') is not True
                or type(connector_ids) is not list or len(connector_ids)!=r.get('fit',{}).get('pieces')
                or len(set(connector_ids))!=len(connector_ids) or any(type(x) is not int for x in connector_ids)
                or any(x not in r.get('returned_edges',[]) for x in connector_ids)
                or any(not isinstance(x,str) or not x.strip() or len(x)>500 for x in (reason,authority))):
            raise ValueError('invalid explicit crossover compensation')
        observed=self.request('inspect',{'edge_ids':r['returned_edges']});snapshots=observed.get('result',{}).get('edges',[])
        byid={e['id']:e for e in snapshots}
        if observed['status']!='ok' or set(byid)!=set(r['returned_edges']):raise LiveError('reconciliation_required','fresh exact receipt missing')
        chosen=[byid[x] for x in connector_ids]
        for e,c in zip(chosen,r['fit']['controls']):
            if any(any(abs(e[k][j]-c[k][j])>.001 for j in range(3)) for k in ('p0','p1','t0','t1')):
                raise LiveError('reconciliation_required','chosen connector differs from original fit')
        params={'authorised':True,'edges':chosen,'compensation':{'original_request':rid,'original_response':response,'original_params':pending['params'],'reason':reason,'authority':authority}}
        intent={'status':'explicit_compensation_intent','original_pending':pending,'original_response_path':str(path.resolve()),
                'original_response_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'removal_params':params,'fresh_observation':observed['request_id'],'mutation_replay':False}
        intent_path=self.evidence/(rid+'.compensation_intent.json')
        if intent_path.exists():raise LiveError('reconciliation_required','compensation already recorded; reconcile its exact outcome')
        atomic_json(intent_path,intent)
        answer=self.request('remove_branch',params);v=answer.get('result',{})
        if (answer['status']!='ok' or answer.get('session')!=self.session or answer.get('operation')!='remove_branch'
                or v.get('game_constructed') is not True or v.get('compensated_request')!=rid or v.get('removed_edges')!=connector_ids
                or v.get('remaining_through_verified') is not True or len(v.get('remaining_endpoints',[]))!=2):
            raise LiveError('reconciliation_required','compensation outcome not verified',answer['request_id'])
        latest=json.loads(old.journal.read_text())
        if latest.get('pending')!=pending:raise LiveError('reconciliation_required','original pending changed during compensation')
        record=intent|{'status':'compensated_noncompliant_crossover','removal_response':answer,'original_build_accepted':False,'rollback':False}
        evidence=self.evidence/(rid+'.compensation.json');atomic_json(evidence,record)
        latest.setdefault('compensated_constructions',{})[rid]={'evidence':str(evidence.resolve()),'original_build_accepted':False}
        latest.pop('pending');atomic_json(old.journal,latest)
        return {'status':'ok','result':record,'evidence':str(evidence.resolve())}

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

    def _request_body(self, request):
        envelope={k:request[k] for k in ('version','session','sequence','request_id','operation','params')}
        return ('return '+lua_literal(envelope)+'\n').encode('ascii')

    def _slot(self, request):
        return self.mod/'content/scripts/pif_live'/self.session/f"{request['sequence']:06d}.lua"

    @staticmethod
    def _existing_bytes(path):
        # Permission/IO errors must never be mistaken for an absent publication.
        try:return path.read_bytes()
        except FileNotFoundError:return None

    @staticmethod
    def _publish_file(temporary, path):
        # Windows rename refuses occupied destinations. POSIX link provides the
        # same exclusive atomic publication without a partially readable module.
        if os.name=='nt':os.rename(temporary,path)
        else:os.link(temporary,path);temporary.unlink()

    def _publish(self, state, body):
        pending=state['pending'];path=self._slot(pending);temporary=path.with_suffix('.pending');phase='prepared'
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            if self._existing_bytes(path) is not None:raise LiveError('request_slot_conflict',str(path),pending['request_id'])
            with temporary.open('xb') as stream:stream.write(body)
            phase='temporary_written';pending['publication']['phase']=phase;atomic_json(self.journal,state)
            phase='rename_attempted';self._publish_file(temporary,path)
            pending['publication'].update(state='published',phase='published')
            state['next_sequence']=max(state['next_sequence'],pending['sequence']+1);atomic_json(self.journal,state)
        except (OSError,LiveError) as exc:
            try:actual=self._existing_bytes(path)
            except OSError:actual=None;phase='slot_inspection_failed'
            published=actual==body
            kind=('published' if published else 'conflict' if actual is not None else
                  'uncertain' if phase in ('rename_attempted','slot_inspection_failed') else 'unpublished')
            pending['publication'].update(state=kind,phase=phase,error=str(exc)[:400])
            if published:state['next_sequence']=max(state['next_sequence'],pending['sequence']+1)
            try:atomic_json(self.journal,state)
            except OSError:pass # Previously durable intent still protects this slot.
            status=('request_slot_conflict' if kind=='conflict' or isinstance(exc,FileExistsError) else
                    'request_publication_failed' if kind=='unpublished' else 'request_publication_uncertain')
            raise LiveError(status,'publication retained for explicit reconciliation; '+str(exc)[:300],pending['request_id']) from exc

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
        if unresolved and (unresolved.get('publication',{}).get('state') not in (None,'published')
                           or not is_mutation(unresolved.get('operation'),unresolved.get('params',{}))):
            raise LiveError('reconciliation_required','pending publication/read must be reconciled before allocating another slot',unresolved['request_id'])
        if unresolved and 'publication' not in unresolved:
            try:published=self._existing_bytes(self._slot(unresolved))==self._request_body(unresolved)
            except (KeyError,ValueError,OSError):published=False
            if not published:raise LiveError('reconciliation_required','legacy pending slot publication is not established',unresolved['request_id'])
        corrective=False
        if unresolved and operation=='remove_branch' and params.get('compensation',{}).get('original_request')==unresolved['request_id']:
            intent=self.evidence/(unresolved['request_id']+'.compensation_intent.json')
            if intent.exists():
                saved=json.loads(intent.read_text());corrective=saved.get('original_pending')==unresolved and saved.get('removal_params')==params
        if unresolved and not corrective and (is_mutation(operation,params) or operation not in ('operating_inspect', 'readback', 'inspect', 'route', 'discover', 'discover_junction', 'discover_interior', 'verify_interior', 'verify_crossover', 'verify_adjacency', 'adjacent', 'remove_branch', 'crossover', 'connection', 'selected_connection', 'corridor', 'junction', 'interior_junction', 'scissors_candidate')):
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
        state['pending'] = {**request, 'log_offset': offset,'operation_kind':'mutation' if is_mutation(operation,params) else 'read',
            'publication':{'state':'prepared','phase':'prepared','sha256':hashlib.sha256(body).hexdigest()}}
        if unresolved:
            state['pending']['unresolved_mutation'] = unresolved
        atomic_json(self.journal, state)
        self._publish(state,body)
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
                        # The matching response was already persisted above. An
                        # acknowledgement changes the journal, not that receipt.
                        verified_pending = (unresolved and unresolved['operation'] == 'build'
                                            and operation == 'readback' and response['status'] == 'ok'
                                            and response.get('result', {}).get('connected') is True
                                            and params.get('fit_request') == unresolved['params'].get('fit_request'))
                        if corrective and (response['status']=='mutation_unverified' or response.get('result',{}).get('game_constructed')=='unknown'):
                            state['pending']['outcome']='mutation_unverified'
                        elif unresolved and not verified_pending:
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

    def reconcile_read_publications(self, request_ids):
        """Explicitly restore <=2 proven unpublished reads; consume existing slots.

        This does not retry mutations, allocate filler calls, rewind the sequence,
        or recover a crashed host/game. A healthy current adapter is a precondition.
        """
        lock=self.evidence/'client.lock'
        try:
            with lock.open('x'):pass
        except FileExistsError:raise LiveError('client_busy','one client reconciliation at a time') from None
        try:return self._reconcile_read_publications(request_ids)
        finally:lock.unlink()

    def _reconcile_read_publications(self, request_ids):
        state=json.loads(self.journal.read_text());pending=state.get('pending');chain=[]
        if state.get('session')!=self.session or not pending:raise LiveError('reconciliation_required','no current pending read publication')
        if self.require_ack and discover_session(self.log)!=self.session:raise LiveError('session_changed','adapter load changed; do not publish')
        item=pending;mutation=None
        while item:
            if is_mutation(item.get('operation'),item.get('params',{})):
                if not chain or item.get('unresolved_read') or item.get('unresolved_mutation'):
                    raise LiveError('reconciliation_required','only a terminal unresolved mutation may be preserved')
                mutation=item;break
            if len(chain)==2:
                raise LiveError('reconciliation_required','only one or two explicit pending reads may be reconciled')
            chain.append(item)
            if item.get('unresolved_mutation') and item.get('unresolved_read'):raise LiveError('reconciliation_required','ambiguous pending chain')
            item=item.get('unresolved_read') or item.get('unresolved_mutation')
        chain.reverse()
        if not isinstance(request_ids,(list,tuple)) or list(request_ids)!=[p['request_id'] for p in chain]:
            raise LiveError('reconciliation_required','exact oldest-first pending read IDs required')
        if mutation:
            envelope={k:mutation[k] for k in ('version','session','sequence','request_id','operation','params')}
            body=self._request_body(mutation)
            if (mutation['session']!=self.session or type(mutation['sequence']) is not int
                    or not 0<mutation['sequence']<chain[0]['sequence']
                    or json.loads((self.evidence/(mutation['request_id']+'.request.json')).read_text())!=envelope
                    or mutation.get('publication',{}).get('state') not in (None,'published')
                    or mutation.get('publication',{}).get('sha256') not in (None,hashlib.sha256(body).hexdigest())
                    or self._existing_bytes(self._slot(mutation))!=body):
                raise LiveError('reconciliation_required','underlying mutation identity/publication unproven')
        prepared=[];observations=[]
        with self.log.open('rb') as stream:
            offset=min(p['log_offset'] for p in chain)
            if stream.seek(0,2)<offset:raise LiveError('log_rotated','retained read baseline no longer available')
            stream.seek(offset);baseline=stream.read().decode('utf-8','replace').splitlines()
        for i,p in enumerate(chain):
            envelope={k:p[k] for k in ('version','session','sequence','request_id','operation','params')}
            if (p['session']!=self.session or p['operation'] not in OPERATIONS or type(p['sequence']) is not int or p['sequence']<1
                    or i and p['sequence']!=chain[i-1]['sequence']+1):raise LiveError('reconciliation_required','invalid ordered read identity')
            if json.loads((self.evidence/(p['request_id']+'.request.json')).read_text())!=envelope:
                raise LiveError('reconciliation_required','saved request differs from pending identity',p['request_id'])
            body=self._request_body(p);path=self._slot(p);actual=self._existing_bytes(path);temporary=path.with_suffix('.pending');temp=self._existing_bytes(temporary)
            if p.get('publication',{}).get('sha256') not in (None,hashlib.sha256(body).hexdigest()):
                raise LiveError('reconciliation_required','saved publication hash differs from exact read',p['request_id'])
            if actual is not None and actual!=body or temp is not None and temp!=body:
                raise LiveError('request_slot_conflict','occupied slot/temporary differs from exact saved read',p['request_id'])
            if actual is None:
                if p.get('publication',{}).get('state')=='uncertain':raise LiveError('reconciliation_required','rename outcome remains uncertain; no republish',p['request_id'])
                for line in baseline:
                    if parse_response(line,p['request_id'],self.session,p['operation']) is not None:
                        raise LiveError('reconciliation_required','response already exists for missing slot; no republish',p['request_id'])
                    marker='TPF3_BRIDGE_LIVE_ACK '
                    if marker in line:
                        try:ack=json.loads(line.split(marker,1)[1])
                        except ValueError:continue
                        if isinstance(ack,dict) and ack.get('request_id')==p['request_id'] and ack.get('session')==self.session:
                            raise LiveError('reconciliation_required','ACK already exists for missing slot; no republish',p['request_id'])
            prepared.append((p,path,temporary,body,actual,temp))
            observations.append({'request_id':p['request_id'],'sequence':p['sequence'],'operation_kind':'read',
                'slot_present':actual is not None,'temporary_present':temp is not None,'sha256':hashlib.sha256(body).hexdigest()})
        if state['next_sequence'] not in (chain[-1]['sequence'],chain[-1]['sequence']+1):
            raise LiveError('reconciliation_required','sequence frontier does not match the retained reads')
        record={'status':'prepared','session':self.session,'original_pending':json.loads(json.dumps(pending)),'slots':observations,'mutation_replay':False}
        evidence=self.evidence/(pending['request_id']+'.'+uuid.uuid4().hex+'.publication_reconciliation.json');atomic_json(evidence,record)
        for p,path,temporary,body,actual,temp in prepared:
            if actual is None:
                if self.require_ack and discover_session(self.log)!=self.session:raise LiveError('session_changed','adapter changed before restoring read')
                path.parent.mkdir(parents=True,exist_ok=True)
                if temp is None:
                    with temporary.open('xb') as stream:stream.write(body)
                self._publish_file(temporary,path)
                assert self._existing_bytes(path)==body,'published read differs from saved identity'
        # Preserve the frontier, including any previously published successor.
        state['next_sequence']=max(state['next_sequence'],chain[-1]['sequence']+1)
        for p in chain:
            p['operation_kind']='read';p['publication']={'state':'published','phase':'explicit_read_reconciliation','sha256':hashlib.sha256(self._request_body(p)).hexdigest()}
            if p.get('unresolved_mutation') and p['unresolved_mutation'] is not mutation:p['unresolved_read']=p.pop('unresolved_mutation')
        atomic_json(self.journal,state)
        record['status']='published_waiting_for_existing_responses';atomic_json(evidence,record)
        deadline=time.monotonic()+self.timeout;responses={}
        while time.monotonic()<deadline:
            if self.require_ack and discover_session(self.log)!=self.session:raise LiveError('session_changed','adapter changed during read reconciliation')
            with self.log.open('rb') as stream:
                if stream.seek(0,2)<offset:raise LiveError('log_rotated','read reconciliation baseline unavailable')
                stream.seek(offset);raw=stream.read()
            lines=raw.decode('utf-8','replace').splitlines()
            for p in chain:
                received=None;acknowledged=not self.require_ack
                for line in lines:
                    marker='TPF3_BRIDGE_LIVE_ACK '
                    if marker in line:
                        try:ack=json.loads(line.split(marker,1)[1])
                        except ValueError:ack={}
                        if isinstance(ack,dict) and ack.get('request_id')==p['request_id'] and ack.get('session')==self.session:
                            if ack.get('success') is not True:raise LiveError('command_completion_failed','existing read command ACK failed',p['request_id'])
                            acknowledged=True
                    response=parse_response(line,p['request_id'],self.session,p['operation'])
                    if response is not None:received=response
                if received and acknowledged:
                    if received['status']=='mutation_unverified':raise LiveError('reconciliation_required','read response reports uncertainty',p['request_id'])
                    responses[p['request_id']]=received;atomic_json(self.evidence/(p['request_id']+'.response.json'),received)
            if len(responses)==len(chain):
                latest=json.loads(self.journal.read_text())
                if latest!=state:raise LiveError('reconciliation_required','journal changed during ordered read reconciliation')
                record.update(status='reconciled_reads',responses=[responses[p['request_id']] for p in chain],next_sequence=state['next_sequence'])
                evidence.with_suffix('.log').write_bytes(raw)
                atomic_json(evidence,record)
                state.setdefault('publication_reconciliations',{})[pending['request_id']]={'evidence':str(evidence.resolve()),'request_ids':list(request_ids),'mutation_replay':False}
                if mutation:state['pending']=mutation
                else:state.pop('pending')
                atomic_json(self.journal,state)
                return {'status':'ok','result':record,'evidence':str(evidence.resolve())}
            time.sleep(.1)
        record.update(status='incomplete',error='existing read responses/ACKs incomplete; no new slot allocated')
        atomic_json(evidence,record)
        raise LiveError('request_timeout',record['error'],pending['request_id'])

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
                    previous=pending.get('unresolved_mutation') or pending.get('unresolved_read')
                    if previous:state['pending']=previous
                    else:state.pop('pending')
                    state['next_sequence']=max(state['next_sequence'],pending['sequence']+1)
                    atomic_json(self.journal, state)
                return response
        raise LiveError('reconciliation_required', 'no matching late response; fresh readback may be requested, no automatic mutation replay', pending['request_id'])

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=sorted(OPERATIONS | {'station-survey','scissors','scissors-inspect','plain-crossing','plain-crossing-inspect','route-set-inspect','height-ladder','height-ladder-inspect','ladder-layout', 'ladder-layout-inspect', 'complete-layout', 'complete-layout-inspect', 'branching-corridor', 'branching-corridor-inspect', 'multitrack-connection', 'multitrack-connection-inspect', 'paired-connection', 'paired-connection-inspect', 'layout-network', 'layout-network-inspect', 'extend', 'connect', 'connect-selected', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent', 'junction-recipe', 'junction-recipe-inspect', 'junction-recipe-continue', 'parallel-layout', 'parallel-layout-inspect', 'switching-layout', 'switching-layout-inspect', 'switching-layout-continue', 'reciprocal-layout', 'reciprocal-layout-inspect', 'reconcile-fixture'}))
    parser.add_argument('--params', required=True, type=Path)
    parser.add_argument('--reconciled-crossover', type=Path, help='explicit verified crossover evidence for connect-throat; rechecks read-only, never rebuilds it')
    parser.add_argument('--recipe-plan',type=Path,help='optional reviewed junction-recipe plan; must match current brief exactly')
    parser.add_argument('--prepared-recipe',type=Path,help='explicit matching recipe stopped before reference; fresh stubs checked, never automatically resumed')
    parser.add_argument('--layout-record',type=Path,help='saved layout invocation for fresh inspection or explicit checked continuation')
    parser.add_argument('--base-layout-record',type=Path,help='explicit completed matching eight-movement switching layout; fresh readback before extending it')
    parser.add_argument('--prepared-switching',type=Path,help='explicit matching five-fixture prebuild reference failure; no automatic replay')
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
    if args.operation in ('junction-recipe','parallel-layout','switching-layout','reciprocal-layout','layout-network','paired-connection','multitrack-connection','branching-corridor','complete-layout','ladder-layout') and not args.execute:
        try:
            if args.base_layout_record or args.prepared_switching or args.layout_record or args.recipe_record or args.recipe_plan or args.prepared_recipe or args.discovery or args.reconciled_crossover:raise ValueError('planning accepts a brief, not native continuation records')
            brief=json.loads(args.params.read_text(encoding='utf-8-sig'))
            if args.operation=='ladder-layout':
                from bridge_ladder import plan_ladder_input,publish_ladder
                response=publish_ladder(plan_ladder_input(brief),args.evidence or Path('.local_runs/ladder_plans'))
            elif args.operation=='complete-layout':
                from bridge_complete import plan_complete_layout,publish_complete_layout
                response=publish_complete_layout(plan_complete_layout(brief),args.evidence or Path('.local_runs/complete_plans'))
            elif args.operation=='branching-corridor':
                from bridge_branching import plan_branching_corridor,publish_branching_corridor
                response=publish_branching_corridor(plan_branching_corridor(brief),args.evidence or Path('.local_runs/branching_plans'))
            elif args.operation=='multitrack-connection':
                from bridge_parallel import plan_multitrack_connection,publish_multitrack_connection
                response=publish_multitrack_connection(plan_multitrack_connection(brief),args.evidence or Path('.local_runs/multitrack_plans'))
            elif args.operation=='paired-connection':
                from bridge_parallel import plan_paired_connection,publish_paired_connection
                response=publish_paired_connection(plan_paired_connection(brief),args.evidence or Path('.local_runs/paired_plans'))
            elif args.operation=='layout-network':
                from bridge_network import plan_layout_network,publish_layout_network
                response=publish_layout_network(plan_layout_network(brief),args.evidence or Path('.local_runs/layout_networks'))
            elif args.operation=='junction-recipe':response=publish_junction_recipe(plan_junction_recipe(brief),args.evidence or Path('.local_runs/junction_recipes'))
            elif args.operation=='parallel-layout':response=publish_parallel_layout(plan_parallel_layout(brief),args.evidence or Path('.local_runs/parallel_layouts'))
            elif args.operation=='reciprocal-layout':response=publish_reciprocal_layout(plan_reciprocal_layout(brief),args.evidence or Path('.local_runs/reciprocal_layouts'))
            else:response=publish_switching_layout(plan_switching_layout(brief),args.evidence or Path('.local_runs/switching_layouts'))
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
        if args.base_layout_record and (args.operation!='reciprocal-layout' or not args.execute):raise ValueError('--base-layout-record requires reciprocal-layout --execute')
        if args.prepared_switching and (args.operation!='switching-layout' or not args.execute):raise ValueError('--prepared-switching requires switching-layout --execute')
        if args.layout_record and args.operation not in ('scissors-inspect','plain-crossing','plain-crossing-inspect','height-ladder','height-ladder-inspect','ladder-layout','ladder-layout-inspect','complete-layout','complete-layout-inspect','branching-corridor','branching-corridor-inspect','multitrack-connection','multitrack-connection-inspect','paired-connection','paired-connection-inspect','layout-network','layout-network-inspect','parallel-layout-inspect','switching-layout-inspect','switching-layout-continue','reciprocal-layout-inspect','reciprocal-layout'):raise ValueError('--layout-record requires a supported layout operation')
        if args.recipe_record and args.operation not in ('junction-recipe-inspect','junction-recipe-continue'):raise ValueError('--recipe-record requires recipe inspect/continue')
        if args.operation=='junction-recipe-continue' and not args.execute:raise ValueError('recipe continuation requires --execute')
        if args.recipe_plan and (args.operation!='junction-recipe' or not args.execute):raise ValueError('--recipe-plan requires junction-recipe --execute')
        if args.prepared_recipe and (args.operation!='junction-recipe' or not args.execute):raise ValueError('--prepared-recipe requires junction-recipe --execute')
        if args.reconciled_crossover and (args.operation!='connect-throat' or not args.execute):
            raise ValueError('--reconciled-crossover requires connect-throat --execute')
        if args.discovery and args.operation not in ('connect-selected','reconcile-fixture'):
            raise ValueError('--discovery is only for connect-selected/reconcile-fixture')
        if args.execute and args.operation not in ('scissors','plain-crossing','height-ladder','ladder-layout', 'complete-layout', 'branching-corridor', 'multitrack-connection', 'paired-connection', 'layout-network', 'extend', 'connect', 'connect-brief', 'connect-corridor', 'connect-junction', 'connect-junction-at', 'connect-throat', 'connect-adjacent', 'junction-recipe', 'junction-recipe-continue', 'parallel-layout', 'switching-layout', 'switching-layout-continue', 'reciprocal-layout'):
            raise ValueError('--execute is only for extend/connect/connect-brief/connect-corridor/connect-junction/connect-junction-at; low-level build uses explicit authorised parameter')
        if args.operation=='scissors':
            from bridge_scissors import scissors
            if args.layout_record:raise ValueError('scissors never automatically resumes a saved record')
            response=scissors(client,params,execute=args.execute)
        elif args.operation=='scissors-inspect':
            from bridge_scissors import inspect_scissors
            if not args.layout_record:raise ValueError('--layout-record is required')
            if json.loads(args.layout_record.read_text(encoding='utf-8-sig'))['brief']!=params:raise ValueError('scissors record differs from brief')
            response=inspect_scissors(client,args.layout_record)
        elif args.operation=='plain-crossing':
            from bridge_crossing import crossing
            response=crossing(client,params,execute=args.execute,prepared_record=args.layout_record)
        elif args.operation=='plain-crossing-inspect':
            from bridge_crossing import inspect_crossing
            if not args.layout_record:raise ValueError('--layout-record is required')
            if json.loads(args.layout_record.read_text(encoding='utf-8-sig'))['brief']!=params:raise ValueError('crossing record differs from brief')
            response=inspect_crossing(client,args.layout_record)
        elif args.operation=='station-survey':
            from bridge_station import inspect_station
            response=inspect_station(client,params)
        elif args.operation=='route-set-inspect':
            from bridge_route_set import inspect_route_set
            response=inspect_route_set(client,params)
        elif args.operation=='height-ladder':
            from bridge_height_ladder import plan_height_ladder,execute_height_ladder
            if not args.execute and args.layout_record:raise ValueError('observed planning accepts a brief, not a continuation record')
            response=execute_height_ladder(client,params,layout_record=args.layout_record) if args.execute else plan_height_ladder(client,params)
        elif args.operation=='height-ladder-inspect':
            from bridge_height_ladder import inspect_height_ladder
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']['brief']!=params:raise ValueError('height-ladder record differs from brief')
            response=inspect_height_ladder(client,args.layout_record)
        elif args.operation=='ladder-layout':
            from bridge_ladder import plan_ladder_input,execute_ladder
            response=execute_ladder(client,plan_ladder_input(params),layout_record=args.layout_record)
        elif args.operation=='ladder-layout-inspect':
            from bridge_ladder import plan_ladder_input,inspect_ladder
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_ladder_input(params):raise ValueError('ladder record differs from brief')
            response=inspect_ladder(client,args.layout_record)
        elif args.operation=='complete-layout':
            from bridge_complete import plan_complete_layout,execute_complete_layout
            response=execute_complete_layout(client,plan_complete_layout(params),continuation_record=args.layout_record)
        elif args.operation=='complete-layout-inspect':
            from bridge_complete import plan_complete_layout,inspect_complete_layout
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_complete_layout(params):raise ValueError('complete-layout record differs from brief')
            response=inspect_complete_layout(client,args.layout_record)
        elif args.operation=='branching-corridor':
            from bridge_branching import plan_branching_corridor,execute_branching_corridor
            response=execute_branching_corridor(client,plan_branching_corridor(params),continuation_record=args.layout_record)
        elif args.operation=='branching-corridor-inspect':
            from bridge_branching import plan_branching_corridor,inspect_branching_corridor
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_branching_corridor(params):raise ValueError('branching record differs from brief')
            response=inspect_branching_corridor(client,args.layout_record)
        elif args.operation=='multitrack-connection':
            from bridge_parallel import plan_multitrack_connection,execute_multitrack_connection
            response=execute_multitrack_connection(client,plan_multitrack_connection(params),continuation_record=args.layout_record)
        elif args.operation=='multitrack-connection-inspect':
            from bridge_parallel import plan_multitrack_connection,inspect_multitrack_connection
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_multitrack_connection(params):raise ValueError('multitrack record differs from brief')
            response=inspect_multitrack_connection(client,args.layout_record)
        elif args.operation=='paired-connection':
            from bridge_parallel import plan_paired_connection,execute_paired_connection
            response=execute_paired_connection(client,plan_paired_connection(params),reference_record=args.layout_record)
        elif args.operation=='paired-connection-inspect':
            from bridge_parallel import plan_paired_connection,inspect_paired_connection
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_paired_connection(params):raise ValueError('paired record differs from brief')
            response=inspect_paired_connection(client,args.layout_record)
        elif args.operation=='layout-network':
            if args.layout_record and not args.execute:raise ValueError('network continuation requires --execute')
            from bridge_network import plan_layout_network,execute_layout_network
            response=execute_layout_network(client,plan_layout_network(params),continuation_record=args.layout_record)
        elif args.operation=='layout-network-inspect':
            from bridge_network import plan_layout_network,inspect_layout_network
            if not args.layout_record:raise ValueError('--layout-record is required')
            if _load_layout_record(args.layout_record)['plan']!=plan_layout_network(params):raise ValueError('network record does not match brief')
            response=inspect_layout_network(client,args.layout_record)
        elif args.operation=='reciprocal-layout':
            response=execute_reciprocal_layout(client,plan_reciprocal_layout(params),base_layout_record=args.base_layout_record,continuation_record=args.layout_record)
        elif args.operation=='reciprocal-layout-inspect':
            if not args.layout_record:raise ValueError('--layout-record is required')
            saved=_load_layout_record(args.layout_record)
            if saved['plan']!=plan_reciprocal_layout(params):raise ValueError('reciprocal record does not match current brief')
            response=inspect_reciprocal_layout(client,args.layout_record)
        elif args.operation=='switching-layout':
            response=execute_switching_layout(client,plan_switching_layout(params),prepared_record=args.prepared_switching)
        elif args.operation in ('switching-layout-inspect','switching-layout-continue'):
            if not args.layout_record:raise ValueError('--layout-record is required')
            saved=json.loads(args.layout_record.read_text(encoding='utf-8-sig'))
            if 'plan' not in saved and saved.get('evidence'):saved=json.loads(Path(saved['evidence']).read_text(encoding='utf-8-sig'))
            if saved['plan']!=plan_switching_layout(params):raise ValueError('switching record does not match current brief')
            if args.operation=='switching-layout-continue' and not args.execute:raise ValueError('switching continuation requires --execute')
            response=(inspect_switching_layout if args.operation=='switching-layout-inspect' else continue_switching_layout)(client,args.layout_record)
        elif args.operation=='parallel-layout':
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
