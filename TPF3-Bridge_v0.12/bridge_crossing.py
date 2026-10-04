"""Native level orthogonal plain-crossing qualification, not a routing planner."""
import itertools
import json
import math
import uuid
from pathlib import Path
import bridge_live as live
from bridge_route_set import _hint

ARMS=('W','E','S','N')
STRAIGHT={('W','E'),('E','W'),('S','N'),('N','S')}

def validate(brief):
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
    expected=set(itertools.permutations(ARMS,2))
    if len(rows)!=12 or {(x.get('from'),x.get('to')) for x in rows}!=expected:
        return {'qualified':False,'outcome':'incomplete_movement_observation'}
    turns=[];unknown=[];straight=[]
    for x in rows:
        key=(x['from'],x['to']);r=x.get('result',{})
        if x.get('status')!='ok' or r.get('truncated') is not False:
            unknown.append(key);continue
        if key in STRAIGHT:
            if r.get('requested_route_verified') is True and r.get('native_path_found') is True and r.get('transport_continuous') is True and r.get('path_count')==len(r.get('path',[])) and r.get('path_count',0)>0:
                straight.append(key)
            else:unknown.append(key)
        elif r.get('native_path_found') is True:turns.append(key)
        elif r.get('native_path_found') is not False or r.get('reason')!='no_native_path_returned' or r.get('path_count')!=0 or r.get('path') not in ([],{}):unknown.append(key)
    physical=(len(readback.get('arms',[]))==4 and len({a.get('id') for a in readback.get('arms',[])})==4 and type(readback.get('center_node')) is int and readback.get('transport_truncated') is False)
    qualified=physical and len(straight)==4 and not turns and not unknown
    return {'qualified':qualified,'outcome':'level_orthogonal_plain_crossing_observed' if qualified else 'native_turn_movements_observed' if turns else 'crossing_unqualified',
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

def crossing(client,brief,*,execute=False):
    validate(brief)
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
    if record.get('version')!=1 or record.get('session')!=client.session:raise live.LiveError('stale_session','fresh current-session crossing record required')
    validate(record['brief']);v=record['response']['result']
    if v.get('game_constructed') is not True or not v.get('arm_edges') or not v.get('center_node'):raise ValueError('completed native crossing record required')
    p={'ports':record['params']['ports'],'center':record['brief']['center'],'center_node':v['center_node'],'arm_edges':v['arm_edges']}
    response=client.request('inspect_degree_four',p)
    # Preserve the construction identity for another fresh read-only inspection.
    r=response.get('result',{})
    r['arm_edges']=v['arm_edges']
    return _finish(client,{'version':1,'operation':'plain-crossing-inspect','session':client.session,'brief':record['brief'],'params':record['params'],'construction':str(record_path),'response':response})
