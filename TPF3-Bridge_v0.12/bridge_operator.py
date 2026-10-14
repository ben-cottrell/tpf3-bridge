"""Named, plan-driven live operations. CLI and MCP share this implementation.

Plans are design data, never executable Python/Lua. Native operations and their
durable request receipts remain owned by bridge_live. A failed step is not replayed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import heapq
import html
import json
import math
from pathlib import Path
import re
import time
import uuid

import bridge_live as live
from bridge_interfaces import InterfaceRegistry, diagnose
import bridge_operator_tasks as tasks

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / '.local_runs/operator'
CONTEXT = ROOT / '.local_runs/live_python_interface/p02/context.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

def no_step_effects(state):
    signal=state.get('signal_chains',{}).get(state.get('current_step'),{})
    if signal.get('placements') or signal.get('batches'):return False
    mutation=state.get('step_mutation')
    if 'step_mutation' in state and mutation is None:return True
    return bool(mutation and mutation.get('game_constructed') is False and not mutation.get('native_operating_state_changed') and mutation.get('operating_effects')!='unknown')

def native_failure(response):
    """Keep distinct native rejection messages bounded; receipts retain details."""
    value=response.get('result',{});messages=[]
    def retain(message):
        if isinstance(message,str) and message:
            message=message[:120]
            if message not in messages and len(messages)<3:messages.append(message)
    retain(value.get('error'))
    evaluations=[value.get('evaluation',{})]
    rejections=value.get('candidate_rejections',[])
    for rejection in (rejections[:16] if isinstance(rejections,list) else []):
        evaluations.append(rejection.get('evaluation',{}))
        through=rejection.get('through_evaluation',[])
        if isinstance(through,list):evaluations.extend(through[:8])
    for evaluation in evaluations:
        raw=evaluation.get('messages',[])
        if isinstance(raw,list):
            for message in raw[:16]:retain(message)
    return (response['status']+': '+('; '.join(messages) or 'native operation rejected'))[:400]


def vector(v, n):
    if not isinstance(v, list) or len(v) != n or any(type(x) not in (int, float) or not math.isfinite(x) for x in v):
        raise ValueError(f'finite {n}-vector required')
    return v


def unit(v):
    vector(v, 2)
    length = math.hypot(*v)
    if length < 1e-9:
        raise ValueError('nonzero direction required')
    return [x / length for x in v]


def cubic(c, u):
    h = [2*u**3-3*u*u+1, u**3-2*u*u+u, -2*u**3+3*u*u, u**3-u*u]
    dh = [6*u*u-6*u, 3*u*u-4*u+1, -6*u*u+6*u, 3*u*u-2*u]
    keys = ('p0', 't0', 'p1', 't1')
    p = [sum(h[j]*c[k][i] for j,k in enumerate(keys)) for i in range(3)]
    d = [sum(dh[j]*c[k][i] for j,k in enumerate(keys)) for i in range(2)]
    return p, unit(d)


def box(points, margin=3):
    return {'min': [min(p[i] for p in points)-margin for i in range(3)],
            'max': [max(p[i] for p in points)+margin for i in range(3)]}

def in_region(pos,region):
    return all(region['min'][i]<=pos[i]<=region['max'][i] for i in range(3))

def inspect_edges(client,ids):
    rows=[]
    for start in range(0,len(ids),16):
        response=client.request('inspect',{'edge_ids':ids[start:start+16],'structures':True,'parallel_strips':True})
        if response['status']!='ok':raise live.LiveError(response['status'],native_failure(response),response['request_id'])
        found={e['id']:e for e in response['result']['edges']}
        if set(found)!=set(ids[start:start+16]):raise ValueError('exact edge readback incomplete')
        rows.extend(found[i] for i in ids[start:start+16])
    return rows

def fresh_binding(client,binding):
    expected=binding['edges'];ids=[e['id'] for e in expected]
    if not ids or len(ids)>64 or len(set(ids))!=len(ids):raise ValueError('binding needs1..64 distinct exact edges')
    rows=inspect_edges(client,ids)
    keys=('id','node0','node1','p0','p1','t0','t1','template','style','road_type','structure')
    if any(any(e.get(k)!=r.get(k) for k in keys if k in e) for e,r in zip(expected,rows)):
        raise ValueError('native binding changed; inspect current state before revising')
    if any(r.get('road_type')!='TRACK' for r in rows):raise ValueError('binding must confirm native TRACK identity')
    return rows

def replacement_boundary(client,intent,chain,spec):
    """Opt-in exact outside edges at a degree2/3 replacement boundary."""
    if not 1<=len(chain)<=16 or len({e['id'] for e in chain})!=len(chain):raise ValueError('replacement requires1..16 distinct exact chain edges')
    outside=fresh_binding(client,{'edges':spec['edges']});ids={e['id'] for e in chain};out_ids={e['id'] for e in outside}
    if ids&out_ids:raise ValueError('replacement outside edge belongs to removed chain')
    primary=[e for e in outside if e['id']==spec['anchor_edge']]
    if len(primary)!=1:raise ValueError('exact primary outside edge required')
    primary=primary[0]
    adj={}
    for edge in chain:
        for node in (edge['node0'],edge['node1']):adj.setdefault(node,set()).add(edge['id'])
    response=client.request('discover',intent);value=response.get('result',{})
    if response['status']!='ok' or value.get('complete') is not True:raise live.LiveError('discovery_incomplete','complete exact replacement boundary read required')
    matches={}
    for c in value.get('candidates',[]):
        node=c.get('node_id')
        if len(adj.get(node,[]))!=1:continue
        expected=adj[node]|out_ids
        if c.get('edge_id') not in expected or c.get('incidence_complete') is not True or c.get('incident_output_truncated') or c.get('incident_count')!=len(expected) or set(c.get('incident_edges',[]))!=expected or c.get('construction_owner') not in (None,'none',-1,0):continue
        if any(node not in (e['node0'],e['node1']) for e in outside):continue
        # Octree edge coverage need not include every incident edge. Complete
        # node incidence establishes identity; the exact fresh named primary
        # supplies the anchor geometry, using the native anchor convention.
        end=node==primary['node1'];pos=primary['p1'] if end else primary['p0']
        tangent=primary['t1'] if end else [-x for x in primary['t0']]
        size=math.hypot(*tangent[:2]);wanted=intent['travel_direction'];norm=size*math.hypot(*wanted)
        if not size or any(abs(c['pos'][i]-pos[i])>.001 for i in range(3)):continue
        d=[tangent[0]/size,tangent[1]/size,0]
        if norm and math.dist(pos,intent['guide_xyz'])<=intent['placement_tolerance'] and sum(tangent[i]*wanted[i] for i in (0,1))/norm>=math.cos(math.radians(intent['heading_tolerance_deg'])):
            matches[node]=c|{'ref':response.get('request_id','discover')+f":E{primary['id']}:N{node}",'edge_id':primary['id'],'edge_snapshot':primary,
                             'pos':pos,'outward_direction':d,'grade':tangent[2]/size,'template':primary['template'],'style':primary['style']}
    if len(matches)!=1:raise live.LiveError('ambiguous_attachment' if matches else 'no_eligible_candidates','named replacement boundary identity/incidence is not unique/current')
    return next(iter(matches.values()))

def check_plain_coalescing(chain,source,target,*,require_structure=True):
    start,end=source['pos'],target['pos'];delta=[b-a for a,b in zip(start,end)];sq=sum(x*x for x in delta)
    if not sq:raise ValueError('degenerate coalescing alignment')
    for e in chain:
        classification=e.get('structure',{}).get('classification')
        if (classification!='NORMAL' and (require_structure or classification is not None)) or e['template']!=source['edge_snapshot']['template'] or e['style']!=source['edge_snapshot']['style']:raise ValueError('coalescing requires unchanged plain track resources')
        controls=[e['p0'],[e['p0'][i]+e['t0'][i]/3 for i in range(3)],
                  [e['p1'][i]-e['t1'][i]/3 for i in range(3)],e['p1']];us=[]
        for point in controls:
            u=sum((point[i]-start[i])*delta[i] for i in range(3))/sq;at=[start[i]+u*delta[i] for i in range(3)]
            if not -.000001<=u<=1.000001 or any(abs(point[i]-at[i])>.001 for i in range(3)):raise ValueError('coalescing changes alignment')
            us.append(u)
        sign=1 if us[-1]>us[0] else -1
        if any(sign*(b-a)<-.000001 for a,b in zip(us,us[1:])):raise ValueError('coalescing nonmonotone cubic')

def chain_point(rows,u,segment=None):
    if segment is not None:
        if not 1<=segment<=len(rows):raise ValueError('native chain segment unavailable')
        return cubic(rows[segment-1],u)
    if len(rows)==1:return cubic(rows[0],u)
    if any(a['node1']!=b['node0'] for a,b in zip(rows,rows[1:])):raise ValueError('reference spans distinct chains; choose an explicit segment')
    lengths=[];total=0
    for row in rows:
        previous=cubic(row,0)[0]
        for j in range(1,65):
            point=cubic(row,j/64)[0];length=math.dist(previous,point)
            lengths.append((row,(j-1)/64,j/64,length));total+=length;previous=point
    target=total*u;current=0
    for row,a,b,length in lengths:
        if target<=current+length and length>0:return cubic(row,a+(b-a)*(target-current)/length)
        current+=length
    raise ValueError('native chain has no regular sampled length')


def fit_variation_config(step):
    value=step.get('fit_variation')
    if value is None:return None
    if not isinstance(value,dict) or set(value)-{'source','target','max_attempts','max_requests','intent'} or not {'source','target'}&value.keys():raise ValueError('fit_variation requires declared source/target windows')
    if step['kind'] not in ('branch','crossover') or step.get('attachments'):raise ValueError('fit_variation supports branch/crossover without manual alternatives')
    for end in ('source','target'):
        if end not in value:continue
        spec=value[end];ref=step[end]
        if not isinstance(ref,dict) or end=='target' and step['kind']!='crossover':raise ValueError('fit_variation slides interior named chain references only; free endpoints stay exact')
        if not isinstance(spec,dict) or set(spec)-{'max_shift','step','direction'} or not {'max_shift','step'}<=spec.keys():raise ValueError('fit_variation requires max_shift and step metres')
        for key in ('max_shift','step'):
            if type(spec[key]) not in (int,float) or not math.isfinite(spec[key]) or spec[key]<=0:raise ValueError('fit_variation finite positive window/resolution required')
        ratio=spec['max_shift']/spec['step']
        if not math.isfinite(ratio) or spec['step']>spec['max_shift'] or math.ceil(ratio)>512:raise ValueError('fit_variation window requires1..512 resolution intervals')
        if spec.get('direction','both') not in ('both','forward','backward'):raise ValueError('fit_variation direction is canonical forward/backward/both')
    for key,default,upper in [('max_attempts',32,256),('max_requests',256,4096)]:
        if type(value.get(key,default)) is not int or not 1<=value.get(key,default)<=upper:raise ValueError('fit_variation bounded '+key+' required')
    intent=value.get('intent',{})
    if not isinstance(intent,dict) or set(intent)-{'envelope','longitudinal_axis','max_extra_inflections'}:raise ValueError('unsupported fit_variation intent check')
    if 'envelope' in intent:
        region=intent['envelope'];vector(region['min'],3);vector(region['max'],3)
        if any(a>=b for a,b in zip(region['min'],region['max'])):raise ValueError('ordered fit_variation envelope required')
    if 'longitudinal_axis' in intent:unit(intent['longitudinal_axis'])
    if type(intent.get('max_extra_inflections',0)) is not int or not 0<=intent.get('max_extra_inflections',0)<=16:raise ValueError('bounded extra inflection allowance required')
    return value


def chain_distance_table(rows,ref):
    """Match chain_point's64-interval arc estimate; segment-local u stays local."""
    selected=rows if 'segment' not in ref else rows[ref['segment']-1:ref['segment']]
    if not selected or len(selected)>64 or len(selected)>1 and any(a['node1']!=b['node0'] for a,b in zip(selected,selected[1:])):raise ValueError('fit_variation requires one directed continuous named chain')
    points=[];distance=0
    for row in selected:
        previous=cubic(row,0)[0]
        points.append((distance,row['id'],0))
        for j in range(1,65):
            point=cubic(row,j/64)[0];distance+=math.dist(previous,point);points.append((distance,row['id'],j/64));previous=point
    if distance<=0:raise ValueError('fit_variation chain length unavailable')
    def at_parameter(eid,u):
        part=[x for x in points if x[1]==eid]
        if not part:raise ValueError('fit attachment escaped named chain')
        for a,b in zip(part,part[1:]):
            if a[2]<=u<=b[2]:return a[0]+(b[0]-a[0])*(u-a[2])/(b[2]-a[2])
        raise ValueError('fit attachment parameter outside named chain')
    nominal=at_parameter(selected[0]['id'],ref['u']) if len(selected)==1 else ref['u']*distance
    return points,distance,nominal,at_parameter


def fit_variation_positions(step,chains):
    cfg=fit_variation_config(step);options=[];tables={}
    for end in ('source','target'):
        ref=step[end]
        if end not in cfg:options.append([(0,ref)]);continue
        table,total,nominal,measure=chain_distance_table(chains[ref['curve']],ref);tables[end]=(nominal,measure)
        spec=cfg[end];shifts=[0];count=math.ceil(spec['max_shift']/spec['step'])
        for i in range(1,count+1):
            amount=min(i*spec['step'],spec['max_shift'])
            if spec.get('direction','both')!='backward':shifts.append(amount)
            if spec.get('direction','both')!='forward':shifts.append(-amount)
        choices=[]
        for shift in shifts:
            at=nominal+shift
            if not 0<at<total:continue
            if len(chains[ref['curve']])==1 or 'segment' in ref:
                for a,b in zip(table,table[1:]):
                    if a[0]<=at<=b[0] and b[0]>a[0]:u=a[2]+(b[2]-a[2])*(at-a[0])/(b[0]-a[0]);break
            else:u=at/total
            choices.append((shift,ref|{'u':u}))
        options.append(choices)
    if any(not choices for choices in options):return [],tables
    heap=[(0,0,0,0)];seen={(0,0)};result=[]
    while heap and len(result)<cfg.get('max_attempts',32):
        _,_,i,j=heapq.heappop(heap);a,b=options[0][i],options[1][j]
        result.append(({'source':a[1],'target':b[1]},{'source':a[0],'target':b[0]}))
        for x,y in ((i+1,j),(i,j+1)):
            if x<len(options[0]) and y<len(options[1]) and (x,y) not in seen:
                seen.add((x,y));sa,sb=options[0][x][0],options[1][y][0];heapq.heappush(heap,(sa*sa+sb*sb,abs(sb),x,y))
    return result,tables


def fit_geometry_check(controls,nominal,intent,region):
    """Sample declared intent, never substitute a radius/physics qualification."""
    def sample(rows):
        if not isinstance(rows,list) or not rows:return None
        points=[];signs=[]
        try:
            for c in rows:
                for key in ('p0','p1','t0','t1'):vector(c[key],3)
                for j in range(65):
                    u=j/64;points.append(cubic(c,u)[0])
                    d=[(6*u*u-6*u)*c['p0'][i]+(3*u*u-4*u+1)*c['t0'][i]+(-6*u*u+6*u)*c['p1'][i]+(3*u*u-2*u)*c['t1'][i] for i in range(2)]
                    dd=[(12*u-6)*c['p0'][i]+(6*u-4)*c['t0'][i]+(-12*u+6)*c['p1'][i]+(6*u-2)*c['t1'][i] for i in range(2)]
                    k=(d[0]*dd[1]-d[1]*dd[0])/math.hypot(*d)**3
                    if abs(k)>1e-7:signs.append(1 if k>0 else -1)
        except (KeyError,TypeError,ValueError,ZeroDivisionError):return None
        return points,sum(a!=b for a,b in zip(signs,signs[1:]))
    actual=sample(controls);baseline=sample(nominal)
    if actual is None:return {'available':False,'sampled_only':True,'passed':None,'reason':'prepared branch controls unavailable'}
    points,reversals=actual;axis=intent.get('longitudinal_axis')
    if axis is None:
        reference=baseline[0] if baseline else points;delta=[reference[-1][i]-reference[0][i] for i in range(2)];axis=unit(delta) if math.hypot(*delta)>1e-9 else None
    else:axis=unit(axis)
    reasons=[]
    if any(not in_region(point,intent.get('envelope',region)) for point in points):reasons.append('sampled envelope exceeded')
    if axis and any(sum((b[i]-a[i])*axis[i] for i in range(2))<-.001 for a,b in zip(points,points[1:])):reasons.append('sampled longitudinal backtracking')
    if baseline and reversals>baseline[1]+intent.get('max_extra_inflections',0):reasons.append('extra sampled curvature reversals')
    return {'available':True,'sampled_only':True,'passed':not reasons,'reasons':reasons,'inflections':reversals,
            'nominal_inflections':baseline[1] if baseline else None,'inflection_comparison':'checked' if baseline else 'unavailable','backtracking_check':'checked' if axis else 'unavailable'}

def signal_chain_locations(rows,forward,spacing,start_offset,end_clearance,max_count):
    """Sample native cubics by travelled distance, retaining canonical edge direction."""
    if not rows or len(rows)>64 or len({r['id'] for r in rows})!=len(rows):raise ValueError('signal chain requires1..64 distinct exact edges')
    if len(rows)>1:
        shared={rows[0]['node0'],rows[0]['node1']} & {rows[1]['node0'],rows[1]['node1']}
        if len(shared)!=1:raise ValueError('signal chain requires a simple ordered chain')
        current=rows[0]['node1'] if rows[0]['node0'] in shared else rows[0]['node0']
    else:current=rows[0]['node0']
    oriented=[];visited={current}
    for index,row in enumerate(rows):
        if current not in (row['node0'],row['node1']):raise ValueError('signal chain ordered edges are disconnected')
        direction=current==row['node0'];current=row['node1' if direction else 'node0']
        if current in visited:raise ValueError('signal chain must not loop')
        visited.add(current);oriented.append((index,row,direction))
    if not forward:oriented=[(index,row,not direction) for index,row,direction in reversed(oriented)]
    samples=[];total=0
    for index,row,direction in oriented:
        previous=cubic(row,0 if direction else 1)[0]
        for j in range(1,129):
            a=(j-1)/128 if direction else 1-(j-1)/128;b=j/128 if direction else 1-j/128
            point=cubic(row,b)[0];length=math.dist(previous,point)
            if length>0:samples.append((total,total+length,index,a,b,direction))
            total+=length;previous=point
    count=max(0,math.floor((total-end_clearance-start_offset)/spacing+1e-9)+1)
    if count>max_count:raise ValueError('signal chain placement count exceeds explicit max_count')
    placements=[];cursor=0
    for j in range(count):
        distance=start_offset+j*spacing
        while cursor<len(samples)-1 and distance>samples[cursor][1]:cursor+=1
        lo,hi,index,a,b,direction=samples[cursor];parameter=a+(b-a)*(distance-lo)/(hi-lo)
        if not 0<parameter<1:raise ValueError('signal distance falls on native node; adjust start_offset')
        placements.append({'edge_index':index,'parameter':parameter,'forward':direction,'distance':distance})
    return placements,total


def signal_batch_chunks(rows,locations,seed_id,excluded_intervals=()):
    """Keep sampled global phase; split exclusions and bound each contiguous chunk."""
    nodes=[]
    start=rows[0]['node0']
    if len(rows)>1:
        shared={rows[0]['node0'],rows[0]['node1']} & {rows[1]['node0'],rows[1]['node1']}
        if len(shared)!=1:raise ValueError('signal batch simple ordered chain required')
        start=next(n for n in (rows[0]['node0'],rows[0]['node1']) if n not in shared)
    nodes.append(start)
    for row in rows:
        if nodes[-1] not in (row['node0'],row['node1']):raise ValueError('signal batch disconnected chain')
        nodes.append(row['node1'] if nodes[-1]==row['node0'] else row['node0'])
    runs={}
    for q in locations:
        if any(a<=q['distance']<=b for a,b in excluded_intervals):continue
        interval=sum(q['distance']>b for a,b in excluded_intervals)
        runs.setdefault(interval,[]).append(q)
    chunks=[]
    for interval,locations_in_run in runs.items():
        remaining=sorted(locations_in_run,key=lambda q:q['edge_index'])
        while remaining:
            first=remaining[0]['edge_index'];selected=[q for q in remaining if q['edge_index']<first+16][:64]
            last=max(q['edge_index'] for q in selected)
            brief={'edges':rows[first:last+1],'placements':[{'edge_id':rows[q['edge_index']]['id'],
                'parameter':q['parameter'],'forward':q['forward'],'one_way':True,'distance':q['distance']} for q in selected],
                'seed_id':seed_id,'start_node':nodes[first],'excluded_intervals':[list(v) for v in excluded_intervals]}
            # Budget-only boundaries remain ordinary through nodes. Exclusion boundaries
            # are deliberate breaks, not an assertion of through-chain connectivity.
            chunks.append({'brief':brief,'locations':selected,'first':first,'last':last,'interval':interval})
            remaining=remaining[len(selected):]
    return chunks


def catalogue_components(edges):
    """Summarise the returned native graph only; incidence identifies actual free ends."""
    by_id={e['id']:e for e in edges}
    if len(by_id)!=len(edges):raise ValueError('catalogue contains duplicate exact edge identities')
    nodes={}
    for e in edges:
        for node in (e['node0'],e['node1']):nodes.setdefault(node,[]).append(e['id'])
    unseen=set(by_id);components=[]
    while unseen:
        pending=[min(unseen)];ids=set()
        while pending:
            ident=pending.pop()
            if ident in ids:continue
            ids.add(ident);unseen.discard(ident);edge=by_id[ident]
            for node in (edge['node0'],edge['node1']):pending.extend(i for i in nodes[node] if i not in ids)
        rows=[by_id[i] for i in sorted(ids)];endpoints=[];signals=[];controls=[];structures={}
        for e in rows:
            controls.extend([e['p0'],e['p1'],[e['p0'][i]+e['t0'][i]/3 for i in range(3)],[e['p1'][i]-e['t1'][i]/3 for i in range(3)]])
            kind=e['structure']['classification'];structures[kind]=structures.get(kind,0)+1
            for index,node in enumerate((e['node0'],e['node1'])):
                if len(nodes[node])!=1:continue
                incidence=next(r for r in e['endpoint_incidence'] if r['node_id']==node)
                tangent=e['t0' if index==0 else 't1'];sign=-1 if index==0 else 1
                magnitude=math.hypot(*tangent[:2])
                endpoints.append({'node_id':node,'edge_id':e['id'],'position':e['p0' if index==0 else 'p1'],
                                  'outward_direction':[sign*x/magnitude for x in tangent[:2]] if magnitude else None,
                                  'grade':sign*tangent[2]/magnitude if magnitude else None,
                                  'free':incidence['free'],'incident_count':incidence['incident_count']})
            for obj in e.get('objects',[]):
                if obj.get('signal'):signals.append({'id':obj['id'],'name':obj['name'],'edge_id':e['id'],
                                                    'parameter':obj['parameter'],'position':obj['position'],'resource':obj['resource'],
                                                    'lanes':obj['signal']['lanes']})
        components.append({'edge_ids':sorted(ids),'edge_count':len(ids),'control_bounds':box(controls,0),
                           'endpoints':endpoints,'endpoint_count':len(endpoints),'free_endpoint_count':sum(r['free'] for r in endpoints),
                           'structures':structures,'names':[{'edge_id':e['id'],'name':e['name']} for e in rows if e['name']!='unnamed'],
                           'signals':signals,'signal_count':len(signals)})
    return components


def terrain_samples(client,region,positions):
    if not 1<=len(positions)<=128:raise ValueError('1..128 selected terrain samples required')
    for pos in positions:
        vector(pos,2)
        if not in_region([*pos,(region['min'][2]+region['max'][2])/2],region):raise ValueError('terrain sample outside authorised region')
    r=client.request('terrain_samples',{'positions':positions})
    if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r['request_id'])
    found=r['result'].get('terrain',[])
    if len(found)!=len(positions) or any(row.get('xy')!=pos for row,pos in zip(found,positions)):raise ValueError('terrain sample identity/coverage incomplete')
    return found

def crossing_observations(plan,edges,route_paths):
    observations=[]
    for crossing in plan.get('crossings',[]):
        window=crossing.get('window')
        if not window:
            position=[crossing['position'][i]+plan['origin'][i] for i in range(2)]
            window={'min':[position[0]-10,position[1]-10,plan['region']['min'][2]],
                    'max':[position[0]+10,position[1]+10,plan['region']['max'][2]]}
        roles={}
        for role,names in (('upper',[crossing.get('upper_route')]),('lower',crossing.get('lower_routes',[]))):
            ids={item['edge']['entity'] for name in names for item in route_paths.get(name,[]) if item.get('confirmed_TRACK') is True}
            selected=[];heights=[]
            for edge in edges:
                if edge['id'] not in ids:continue
                samples=[cubic(edge,j/64)[0] for j in range(65)]
                inside=[point for point in samples if in_region(point,window)]
                if inside:selected.append(edge);heights.extend(point[2] for point in inside)
            roles[role]={'edge_ids':[e['id'] for e in selected],
                         'endpoint_nodes':sorted({e[k] for e in selected for k in ('node0','node1')}),
                         'classifications':sorted({e.get('structure',{}).get('classification','unknown') for e in selected}),
                         'sampled_height_range':[min(heights),max(heights)] if heights else None}
        shared=sorted(set(roles['upper']['endpoint_nodes']) & set(roles['lower']['endpoint_nodes']))
        observed=bool(roles['upper']['edge_ids'] and roles['lower']['edge_ids'])
        observations.append({'name':crossing['name'],'window':window,**roles,'shared_endpoint_nodes':shared,
                             'separate_endpoint_identities_observed':observed and not shared,
                             'required_structure_observed':crossing.get('required_structure','BRIDGE') in roles['upper']['classifications'],
                             'sampled_only':True,'clearance_certified':False})
    return observations

def discover_region(client,region,max_queries=64):
    """Subdivide only bounded/truncated queries; never claim incomplete coverage."""
    todo=[region];edges={};calls=0
    while todo:
        area=todo.pop();spans=[area['max'][i]-area['min'][i] for i in range(2)]
        split=max(spans)>400
        if not split:
            if calls>=max_queries:raise ValueError('geometry query budget exhausted; no complete coverage')
            r=client.request('discover',{'region':area,'max_edges':16});calls+=1
            if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r['request_id'])
            split=r['result'].get('complete') is not True
            if not split:
                for e in r['result']['edges']:edges[e['id']]=e
                continue
        axis=0 if spans[0]>=spans[1] else 1
        if spans[axis]<=1:raise ValueError('dense geometry query remains incomplete; narrower semantic read required')
        mid=(area['min'][axis]+area['max'][axis])/2
        left,right=copy.deepcopy(area),copy.deepcopy(area);left['max'][axis]=mid;right['min'][axis]=mid
        todo.extend([right,left])
    return list(edges.values()),calls

def validate_group_offsets(groups):
    """One fitted reference plus ordered local derivatives; native spacing is queried."""
    family=any('normal_offset_from' in g for g in groups)
    if not family:return
    offsets=[0];reversed_flags=[False]
    for index,group in enumerate(groups):
        if index==0:
            if 'normal_offset_from' in group:raise ValueError('family first member must fit the reference')
            continue
        selector=group.get('normal_offset_from')
        if not isinstance(selector,dict) or set(selector)!={'group_index','spacing','reverse'}:
            raise ValueError('family derivative needs group_index, spacing, reverse')
        ref=selector['group_index'];spacing=selector['spacing']
        if type(ref) is not int or not 1<=ref<=index:raise ValueError('family reference must be an earlier member (1-based)')
        if type(spacing) not in (int,float) or not math.isfinite(spacing) or not 0<abs(spacing)<=60 or type(selector['reverse']) is not bool:
            raise ValueError('finite nonzero bounded family spacing and explicit reverse required')
        if group.get('guides') or any(k in group for k in ('structures','leg_representations','representation','handle_scale','fit_radius')):
            raise ValueError('derived family geometry and structures are inherited; specify on reference')
        total=offsets[ref-1]+(-spacing if reversed_flags[ref-1] else spacing)
        if any(abs(total-old)<=.001 for old in offsets):raise ValueError('family offset repeats an existing member')
        offsets.append(total);reversed_flags.append(reversed_flags[ref-1]!=selector['reverse'])


def validate_structures(step):
    guides=step.get('guides',[])
    if len(guides)>6:raise ValueError('at most6 native structure guides')
    for guide in guides:
        vector(guide['position'],3);unit(guide['travel_direction'])
        if type(guide.get('grade')) not in (int,float) or not math.isfinite(guide['grade']):raise ValueError('finite guide grade required')
    structures=step.get('structures',[{'classification':'NORMAL'}]*(len(guides)+1))
    if len(structures)!=len(guides)+1:raise ValueError('one structure specification per guide leg')
    for item in structures:
        spans=item.get('spans',[item]);previous=0
        if not 1<=len(spans)<=3:raise ValueError('at most3 spans per leg')
        for span in spans:
            if span.get('classification') not in ('NORMAL','BRIDGE','TUNNEL'):raise ValueError('explicit supported structure classification required')
            if span['classification']!='NORMAL' and not isinstance(span.get('resource_name'),str):raise ValueError('observed native structure resource_name required')
            if 'spans' in item:
                value=span.get('until_u')
                if type(value) not in (int,float) or not previous<value<=1:raise ValueError('ordered covering structure spans required')
                previous=value
        if 'spans' in item and previous!=1:raise ValueError('structure spans must cover the leg')


def validate_seed_track(value):
    if not isinstance(value,dict) or set(value)!={'template','style'} or any(not isinstance(value[k],str) or not value[k] for k in ('template','style')):
        raise ValueError('seed track requires explicit template/style resources')
    return value


def validate_plan(p):
    if p.get('version') not in (1,2) or not isinstance(p.get('revision'), str):
        raise ValueError('version1/2 and design revision required')
    vector(p['origin'], 3)
    if not isinstance(p['ports'], dict) or not p['ports']:
        raise ValueError('named ports required')
    for port in p['ports'].values():
        vector(port['position'], 3); unit(port['direction'])
        if type(port.get('grade',0)) not in (int,float) or not math.isfinite(port.get('grade',0)) or abs(port.get('grade',0))>p['max_grade']:
            raise ValueError('port grade exceeds explicit design bound')
    region = p['region']
    vector(region['min'],3); vector(region['max'],3)
    if any(a >= b for a,b in zip(region['min'], region['max'])):
        raise ValueError('ordered region required')
    for port in p['ports'].values():
        if any(not region['min'][i] <= port['position'][i]+p['origin'][i] <= region['max'][i] for i in range(3)):
            raise ValueError('port outside construction region')
    if not isinstance(p['steps'],list) or not p['steps']:
        raise ValueError('construction steps required')
    names=set(p.get('bindings',{}))|set(p.get('result_bindings',{}))
    port_refs=p.get('port_refs',{})
    if not isinstance(port_refs,dict) or any(name not in p['ports'] for name in port_refs):raise ValueError('exact port_refs require named ports')
    for spec in port_refs.values():
        if not isinstance(spec,dict) or set(spec) not in ({'chain','end'},{'chain','edge_id','node_id'}) or not isinstance(spec['chain'],str):raise ValueError('exact port reference requires a named chain and endpoint selector')
        if 'end' in spec and spec['end'] not in ('node0','node1'):raise ValueError('single-edge port end must be node0 or node1')
        if 'edge_id' in spec and any(type(spec[k]) is not int or spec[k]<=0 for k in ('edge_id','node_id')):raise ValueError('exact positive edge/node port identities required')
    for binding in p.get('bindings',{}).values():
        if not isinstance(binding,dict) or not binding.get('edges'):raise ValueError('binding requires observed exact edges')
    def ref(r):
        if isinstance(r,str):
            if r not in p['ports']:raise ValueError('unknown port '+r)
            if r in port_refs and port_refs[r]['chain'] not in names:raise ValueError('exact port requires an earlier chain receipt')
        elif isinstance(r,dict) and set(r) in ({'curve','u'},{'curve','segment','u'}):
            if r['curve'] not in names or type(r['u']) not in (int,float) or not 0<r['u']<1:
                raise ValueError('curve reference must refer to an earlier step at an interior parameter')
            if 'segment' in r and (type(r['segment']) is not int or r['segment']<1):raise ValueError('one-based explicit segment required')
        else:raise ValueError('named port or earlier curve reference required')
    for s in p['steps']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']) or s['name'] in names:
            raise ValueError('unique simple step names required')
        kind=s['kind']
        if 'track' in s:
            if kind not in ('stub','structure_seed'):raise ValueError('track override supports seed steps only')
            validate_seed_track(s['track'])
        if kind not in ('stub','extend','connect','branch','crossover','group','structure_seed','remove','terrain_check','signal_chain') and kind not in tasks.KINDS:raise ValueError('unsupported construction step')
        if p['version']==1 and kind in {'group','structure_seed','remove','terrain_check','signal_chain'}|tasks.KINDS:raise ValueError('new operation requires version2')
        if kind=='stub':
            ref(s['port'])
            if not isinstance(s['port'],str):raise ValueError('stub requires a named port')
            if 'direction' in s:unit(s['direction'])
            if not 5<=s['length']<=60:raise ValueError('native fixture length5..60 required')
            if type(s.get('grade',0)) not in (int,float) or not math.isfinite(s.get('grade',0)) or abs(s.get('grade',0))>min(p['max_grade'],.04):raise ValueError('stub grade within native .04 and selected bound required')
        elif kind=='signal_chain':
            if set(s)-{'seed_id','placement_mode','excluded_intervals','one_way'}!={'name','kind','chains','forward','spacing','start_offset','end_clearance','max_count'}:raise ValueError('explicit signal_chain fields required')
            if s.get('placement_mode','individual') not in ('individual','batch'):raise ValueError('signal_chain placement_mode must be individual or batch')
            if type(s.get('one_way',True)) is not bool:raise ValueError('signal_chain one_way must be boolean')
            if s.get('placement_mode')=='batch' and not s.get('one_way',True):raise ValueError('batch signal_chain supports one_way:true only')
            if s.get('placement_mode')=='batch' and 'seed_id' not in s:raise ValueError('signal batch requires explicit seed_id')
            excluded=s.get('excluded_intervals',[])
            if not isinstance(excluded,list) or len(excluded)>64 or any(not isinstance(v,list) or len(v)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v) or not 0<=v[0]<=v[1] for v in excluded) or any(a[1]>=b[0] for a,b in zip(excluded,excluded[1:])):raise ValueError('signal_chain requires ordered disjoint exclusion intervals')
            if 'seed_id' in s and (type(s['seed_id']) is not int or s['seed_id']<=0):raise ValueError('signal_chain seed_id requires an exact positive native signal ID')
            if not isinstance(s['chains'],list) or not 1<=len(s['chains'])<=32 or any(not isinstance(n,str) or n not in names for n in s['chains']):raise ValueError('signal_chain requires earlier named chains')
            if type(s['forward']) is not bool:raise ValueError('signal_chain requires explicit forward direction')
            for key in ('spacing','start_offset','end_clearance'):
                if type(s[key]) not in (int,float) or not math.isfinite(s[key]) or s[key]<0 or (key!='end_clearance' and s[key]==0):raise ValueError('signal_chain requires positive spacing/start_offset and nonnegative end_clearance')
            if type(s['max_count']) is not int or not 1<=s['max_count']<=64:raise ValueError('signal_chain max_count must be1..64')
        elif kind in tasks.KINDS:
            if not isinstance(s.get('brief'),dict):raise ValueError('explicit operating brief required')
            tasks.validate(kind,s['brief'],names)
        elif kind=='structure_seed':
            ref(s['source']);ref(s['target'])
            if not all(isinstance(s[k],str) for k in ('source','target')) or s['source']==s['target']:raise ValueError('structure seed requires two distinct named ports')
            for name in (s['source'],s['target']):
                if 'grade' not in p['ports'][name]:raise ValueError('structure seed requires explicit outward endpoint grades')
            structure=s.get('structure',{})
            if set(structure)!={'classification','resource_name'} or structure.get('classification') not in ('BRIDGE','TUNNEL') or not isinstance(structure.get('resource_name'),str) or not structure['resource_name']:
                raise ValueError('structure seed requires an explicit observed BRIDGE/TUNNEL resource')
            if any(k in s for k in ('guides','structures','source_interior','target_interior','replace_chain','attachments','candidates')):raise ValueError('standalone structure seed is one unconnected span')
            if not 0<math.dist(p['ports'][s['source']]['position'],p['ports'][s['target']]['position'])<=800:raise ValueError('structure seed length must be within800')
            for key,default,lower,upper in [('radius',0,0,800),('handle_scale',1,0,4)]:
                value=s.get(key,default)
                if type(value) not in (int,float) or not math.isfinite(value) or value<lower or value>upper or (key=='handle_scale' and value==0):raise ValueError('invalid structure seed '+key)
        elif kind=='group':
            if len(s.get('groups',[])) not in (2,4):raise ValueError('native group requires2 or4 members')
            validate_group_offsets(s['groups'])
            for group in s['groups']:
                ref(group['source']);ref(group['target']);validate_structures(group)
                if group.get('source_interior') or group.get('target_interior') or group.get('replace_chain'):raise ValueError('group requires free distinct attachments')
        elif kind=='remove':
            if s.get('chain') not in names:raise ValueError('removal requires named exact earlier chain')
        elif kind=='terrain_check':
            if type(s.get('absolute_floor')) not in (int,float) or not math.isfinite(s['absolute_floor']):raise ValueError('absolute terrain floor required')
            if not 1<=len(s.get('positions',[]))<=128:raise ValueError('terrain check requires1..128 declared samples')
            for pos in s['positions']:vector(pos,2)
        else:
            ref(s['source']);ref(s['target'])
            if kind=='extend':
                radius=s.get('radius',1)
                if type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0:raise ValueError('extend radius must be finite and positive')
            if kind=='connect':validate_structures(s)
            if 'replace_chain' in s and (kind!='connect' or s['replace_chain'] not in names):raise ValueError('replacement requires an earlier exact chain')
            if 'replacement_boundaries' in s or 'coalesce_plain' in s:
                if kind!='connect' or not s.get('replace_chain') or s.get('coalesce_plain') is not True or s.get('source_interior') or s.get('target_interior') or s.get('guides') or s.get('representation','endpoint_cubic')!='endpoint_cubic' or s.get('handle_scale',1)!=1 or s.get('structures',[{'classification':'NORMAL'}])!=[{'classification':'NORMAL'}]:raise ValueError('explicit plain straight coalescing contract required')
                boundaries=s.get('replacement_boundaries')
                if not isinstance(boundaries,dict) or set(boundaries)!={'source','target'}:raise ValueError('both exact replacement boundaries required')
                for spec in boundaries.values():
                    if not isinstance(spec,dict) or set(spec)!={'anchor_edge','edges'} or not isinstance(spec['edges'],list) or not 1<=len(spec['edges'])<=2:raise ValueError('one or two exact outside edge snapshots required')
                    ids=[e.get('id') for e in spec['edges']]
                    if any(type(i) is not int or i<=0 for i in ids) or len(set(ids))!=len(ids) or spec['anchor_edge'] not in ids:raise ValueError('explicit primary outside identity required')
                    for e in spec['edges']:
                        if not all(k in e for k in ('node0','node1','p0','p1','t0','t1','template','style')):raise ValueError('complete outside geometry snapshot required')
            alternatives=s.get('attachments',[])
            if alternatives:
                if kind not in ('branch','crossover','connect') or not 1<=len(alternatives)<=8:raise ValueError('bounded explicit attachment alternatives required')
                if len(alternatives)*len(s.get('candidates',[{}]))>8:raise ValueError('at most8 explicit attachment/shape evaluations')
                if not {'source','target'}<=s.get('attachment_windows',{}).keys():raise ValueError('designer source/target windows required')
                for window in s['attachment_windows'].values():
                    vector(window['min'],3);vector(window['max'],3)
                    if any(a>=b for a,b in zip(window['min'],window['max'])):raise ValueError('ordered attachment windows required')
                for alternative in alternatives:ref(alternative['source']);ref(alternative['target'])
        names.add(s['name'])
        if kind=='branch' and isinstance(s['source'],str) and s['source'] in port_refs:
            raise ValueError('branch requires an interior source, not an exact endpoint port; use structured connect for a free source and interior target')
        if kind in ('branch','crossover'):
            local_limit=s.get('max_route_length',p.get('max_route_length',800))
            if type(local_limit) not in (int,float) or not math.isfinite(local_limit) or not 0<local_limit<=800:
                raise ValueError('branch/crossover effective local route limit must be within(0,800]')
        if 'fit_variation' in s:fit_variation_config(s)
        if kind in ('branch','crossover') and len(s.get('guides',[]))>2:
            raise ValueError('branch/crossover support at most two local shape guides')
        for g in s.get('guides',[]):
            vector(g['position'],3);unit(g['travel_direction'])
            if type(g.get('grade')) not in (int,float) or not math.isfinite(g['grade']):raise ValueError('finite guide grade required')
            if abs(g['grade'])>p['max_grade'] or not in_region([g['position'][i]+p['origin'][i] for i in range(3)],p['region']):raise ValueError('guide violates selected grade/region')
            if kind in ('branch','crossover') and g['grade']!=0:raise ValueError('graded guides require structured connect')
    if len(p['steps'])>32:raise ValueError('at most32 steps per plan')
    bound=400 if p['version']==1 else 1000
    if any(region['max'][i]-region['min'][i]>bound for i in range(2)) or region['max'][2]-region['min'][2]>400:
        raise ValueError(f'operator region limited to{bound} per horizontal axis,400 vertical')
    if type(p.get('max_grade')) not in (int,float) or not 0 < p['max_grade'] <= 1:raise ValueError('explicit positive grade bound required')
    if not 0 < p.get('max_route_length',800) <= (800 if p['version']==1 else 8000):raise ValueError('route length exceeds native bound')
    if not isinstance(p.get('track'),dict) or any(not isinstance(p['track'].get(k),str) or not p['track'][k] for k in ('template','style')):
        raise ValueError('named native track template and style required')
    for r in p['routes']:
        ref(r['source']);ref(r['target'])
        if not all(isinstance(r[k],str) for k in ('name','source','target')):raise ValueError('route endpoints must be named ports')
    for c in p.get('curves',{}).values():
        for k in ('p0','p1','t0','t1'):vector(c[k],3)
    if 'profile_axis' in p:unit(p['profile_axis'])
    if type(p.get('profile_exaggeration',4)) not in (int,float) or not .1<=p.get('profile_exaggeration',4)<=20:raise ValueError('bounded profile exaggeration required')
    if len(p.get('crossings',[]))>8:raise ValueError('at most8 named crossing observations')
    for crossing in p.get('crossings',[]):
        vector(crossing['position'],2)
        for key in ('upper_height','lower_height'):
            if type(crossing.get(key)) not in (int,float) or not math.isfinite(crossing[key]):raise ValueError('explicit relative crossing heights required')
        if crossing.get('upper_route') not in {r['name'] for r in p['routes']} or any(name not in {r['name'] for r in p['routes']} for name in crossing.get('lower_routes',[])) or not crossing.get('lower_routes'):raise ValueError('crossing must bind declared upper/lower native routes')
    digest(p)
    return p


class Operator:
    def __init__(self, context=CONTEXT, runs=RUNS, client=None):
        self.context=Path(context);self.runs=Path(runs);self._client=client
        self.runs.mkdir(parents=True,exist_ok=True)

    def client(self):
        # Re-discover session per public operation; never reuse aliases across loads.
        client=self._client or live.client_from_context(self.context,30)
        collector=getattr(self,'_phase_collector',None)
        return collector.wrap(client) if collector is not None else client

    def path(self, run):
        if not re.fullmatch(r'[a-f0-9]{16}',run):raise ValueError('operator run id required')
        return self.runs/run

    def status(self):
        c=self.client()
        r=c.request('operator_gui',{'action':'status'})
        return {'status':r['status'],'session':c.session,'capabilities':r.get('result'),'numeric_local_terrain_edit':'unsupported',
                'evidence':str(c.evidence/(r['request_id']+'.response.json'))}

    def survey(self, region, terrain_points=None):
        c=self.client();edges,calls=discover_region(c,region)
        rid=uuid.uuid4().hex;path=c.evidence/(rid+'.operator_survey.json')
        record={'session':c.session,'region':region,'edges':edges,'complete':True,'queries':calls}
        out={'status':'ok','session':c.session,'complete':True,'edges':len(edges),'queries':calls,'evidence':str(path)}
        if terrain_points:
            record['terrain']=terrain_samples(c,region,terrain_points);out['terrain_samples']=len(record['terrain'])
        live.atomic_json(path,record)
        return out

    def track_catalogue(self,max_examined_edges=65536,max_tracks=512,summary_limit=32,region=None):
        for key,value,upper in [('max_examined_edges',max_examined_edges,65536),('max_tracks',max_tracks,512),('summary_limit',summary_limit,128)]:
            if type(value) is not int or not 1<=value<=upper:raise ValueError(f'{key} requires an integer within1..{upper}')
        query={'max_examined_edges':max_examined_edges,'max_tracks':max_tracks}
        if region is not None:
            if not isinstance(region,dict) or set(region)!={'min','max'}:raise ValueError('catalogue region requires min/max XYZ')
            vector(region['min'],3);vector(region['max'],3)
            if any(a>=b for a,b in zip(region['min'],region['max'])):raise ValueError('catalogue region requires finite ordered XYZ bounds')
            query['region']=copy.deepcopy(region)
        c=self.client();response=c.request('track_catalogue',query)
        if response['status']!='ok':raise live.LiveError(response['status'],native_failure(response),response['request_id'])
        result=response['result'];edges=result['edges']
        if len(edges)>max_tracks or result['returned_tracks']!=len(edges):raise ValueError('catalogue returned-track bound/count mismatch')
        components=catalogue_components(edges)
        path=c.evidence/'operator_track_catalogue.json'
        live.atomic_json(path,{'session':c.session,'catalogue':result,'components':components})
        compact=[]
        for component in components[:summary_limit]:
            compact.append(component|{'endpoints':component['endpoints'][:16],'names':component['names'][:16],'signals':component['signals'][:16],
                                      'details_truncated':max(len(component['endpoints']),len(component['names']),len(component['signals']))>16})
        named=[signal for component in components for signal in component['signals'] if signal['name']!='unnamed']
        return {k:v for k,v in result.items() if k!='edges'}|{'status':'ok','session':c.session,'component_count':len(components),
            'components':compact,'component_summary_truncated':len(components)>summary_limit,
            'named_signals':named[:64],'named_signal_count':len(named),'named_signals_truncated':len(named)>64,
            'graph_scope':'returned_external_tracks_only','evidence':str(path)}

    def plan(self, plan):
        plan=copy.deepcopy(plan)
        used_roles=set(plan.get('role_refs',{}).values())|tasks.role_names(plan['steps'])
        if used_roles:
            resolved=self.interfaces().resolve(self.client(),plan['interface_registry'],plan['interface_revision'],sorted(used_roles))['resolved']
            plan.setdefault('ports',{});selected={}
            for port,role in plan.get('role_refs',{}).items():
                observed=resolved[role];c=observed['candidate'];selected[port]=observed
                value={'position':[c['pos'][i]-plan['origin'][i] for i in range(3)],'direction':unit(c['outward_direction'][:2]),'grade':c['grade']}
                if port in plan['ports'] and plan['ports'][port]!=value:raise ValueError('role port conflicts with explicit port')
                plan['ports'][port]=value
            plan['interface_bindings']=selected
            plan['role_bindings']=resolved
        p=validate_plan(plan);run=uuid.uuid4().hex[:16];folder=self.path(run);folder.mkdir()
        live.atomic_json(folder/'plan.json',p)
        live.atomic_json(folder/'state.json',{'status':'planned','plan_hash':digest(p),'steps':{},'calls':0,'native_seconds':0})
        render(p,[],folder/'plan.svg')
        render_profile(p,[],folder/'profile.svg')
        return {'status':'planned','run':run,'revision':p['revision'],'steps':len(p['steps']),
                'plan':str(folder/'plan.json'),'view':str(folder/'plan.svg'),'profile':str(folder/'profile.svg')}

    def interfaces(self):return InterfaceRegistry(self.runs/'interfaces')
    def register_interfaces(self,name,revision,roles):return self.interfaces().register(self.client(),name,revision,roles)
    def resolve_interfaces(self,name,revision,names=None):
        c=self.client();result=self.interfaces().resolve(c,name,revision,names)
        rows=[{'name':n,'edge':v['candidate']['edge_id'],'node':v['candidate'].get('node_id'),'xyz':v['candidate']['pos'],
               'direction':v['candidate']['outward_direction'],'grade':v['candidate']['grade'],'terminal':v.get('operating_terminal','unqualified')} for n,v in result['resolved'].items()]
        return {k:v for k,v in result.items() if k!='resolved'}|{'roles':len(rows),'session':c.session,'interfaces':rows[:8],'summary_truncated':len(rows)>8}
    def survey_station(self,brief):
        from bridge_station import inspect_station
        return inspect_station(self.client(),brief)
    def survey_station_exits(self,brief):
        from bridge_station import inspect_exits
        return inspect_exits(self.client(),brief)
    def review_station_routes(self,brief):
        from bridge_station_routes import review
        return review(self.client(),self.interfaces(),brief)
    def attachment_diagnostics(self,intent,mode='free'):
        c=self.client();result=diagnose(c,intent,mode);path=self.runs/(uuid.uuid4().hex+'.attachment_diagnostics.json')
        live.atomic_json(path,result)
        return {k:v for k,v in result.items() if k not in ('candidates','rejections')}|{'candidates':len(result['candidates']),
            'eligible':sum(r['eligible'] for r in result['candidates']),'reasons':sorted({reason for r in result['candidates'] for reason in r['reasons']})[:8],
            'rejections':result['rejections'][:4],'evidence':str(path)}

    def execute(self, run):
        folder=self.path(run);lock=self.runs/'execution.lock'
        try:
            with lock.open('x'):pass
        except FileExistsError:raise ValueError('operator run is already executing; inspect its state')
        try:
            return self._execute(run)
        finally:lock.unlink()

    def plan_corridor(self,brief):
        from bridge_corridor import plan_corridor
        return plan_corridor(self,brief)

    def build_corridor(self,run):
        from bridge_corridor import build_corridor
        return self._measure_phase(run,'corridor_build',lambda:build_corridor(self,run))

    def corridor_status(self,run):
        from bridge_corridor import corridor_status
        return corridor_status(self,run)

    def continue_corridor(self,run,section_run=None):
        from bridge_corridor import build_corridor
        return self._measure_phase(run,'corridor_build',lambda:build_corridor(self,run,continuing=True,section_run=section_run),continuing=True)

    def attach_corridor_completion(self,run,roads):
        from bridge_corridor import attach_completion
        return attach_completion(self,run,roads)

    def complete_corridor(self,run,*,phase='all',continuing=False,road=None):
        from bridge_corridor import complete_corridor
        return self._measure_phase(run,'corridor_complete',lambda:complete_corridor(self,run,phase=phase,continuing=continuing,road=road),continuing=continuing)

    def plan_approach(self,brief):
        from bridge_approach import plan
        return plan(self,brief)

    def build_approach(self,run):
        from bridge_approach import build
        return self._measure_phase(run,'approach_build',lambda:build(self,run))

    def continue_approach(self,run,family_run=None,remaining_families=None):
        from bridge_approach import build
        return self._measure_phase(run,'approach_build',lambda:build(self,run,continuing=True,family_run=family_run,remaining_families=remaining_families),continuing=True)

    def review_approach(self,run,checks=None):
        from bridge_approach import review
        return self._measure_phase(run,'approach_review',lambda:review(self,run,checks))

    def _measure_phase(self,run,phase,callback,*,continuing=False):
        from bridge_phase_metrics import invoke
        return invoke(self,run,phase,callback,continuing=continuing)

    def render_approach(self,source,output,**options):
        from bridge_approach_render import render_approach
        return render_approach(source,output,operator=self,**options)

    def continue_plan(self,run,revision,steps=None,updates=None,bindings=None,reconciled_step=None):
        """Fresh, auditable remaining work; never replay successful native steps."""
        folder=self.path(run);parent=json.loads((folder/'state.json').read_text());old=json.loads((folder/'plan.json').read_text())
        if parent['status'] not in ('built','needs_attention'):raise ValueError('unfinished execution requires reconciliation, not continuation')
        if parent['plan_hash']!=digest(old):raise ValueError('parent plan changed')
        c=self.client()
        if c.session!=parent.get('session'):raise ValueError('session changed; create a new inspected design')
        journal=getattr(c,'journal',None)
        if journal and journal.exists() and json.loads(journal.read_text()).get('pending'):raise ValueError('unresolved native request requires reconciliation')
        carried=copy.deepcopy(parent['steps']);failed=parent.get('current_step') if parent['status']=='needs_attention' else None
        if failed:
            response=parent.get('last_response',{})
            harmless=no_step_effects(parent)
            if reconciled_step:
                if reconciled_step.get('name')!=failed:raise ValueError('reconciliation must name the unfinished step')
                rows=fresh_binding(c,reconciled_step)
                carried[failed]={'status':'reconciled','edges':rows,'request_id':response.get('request_id')}
            elif not harmless:raise ValueError('uncertain/partial effects must be reconciled before remaining-work plan')
        remaining=steps if steps is not None else [s for s in old['steps'] if s['name'] not in carried]
        if not remaining or any(s['name'] in carried for s in remaining):raise ValueError('remaining work cannot replay successful steps')
        def strings(value):
            if isinstance(value,str):return {value}
            if isinstance(value,list):return set().union(*(strings(v) for v in value))
            if isinstance(value,dict):return set().union(*(strings(v) for v in value.values()))
            return set()
        references=strings(remaining)
        selected={**old.get('bindings',{}),**parent.get('bindings',{}),**{name:value for name,value in carried.items() if value.get('edges')}}
        selected={name:value for name,value in selected.items() if name not in parent.get('invalidated_bindings',[])}
        selected.update(bindings or {})
        needed=(set(selected)&references)|{v['chain'] for k,v in old.get('port_refs',{}).items() if k in references}
        selected={name:value for name,value in selected.items() if name in needed}
        observed={name:{'edges':fresh_binding(c,value)} for name,value in selected.items()}
        p=copy.deepcopy(old)
        p['port_refs']={name:value for name,value in p.get('port_refs',{}).items() if name in references}
        p['role_refs']={name:value for name,value in p.get('role_refs',{}).items() if name in references}
        needed_roles=set(p['role_refs'].values())|tasks.role_names(remaining)
        p['interface_bindings']={name:value for name,value in p.get('interface_bindings',{}).items() if name in p['role_refs']}
        p['role_bindings']={name:value for name,value in p.get('role_bindings',{}).items() if name in needed_roles}
        if updates:
            allowed={'ports','curves','region','profile_axis','profile_exaggeration','crossings','max_grade','max_route_length'}
            if set(updates)-allowed:raise ValueError('unsupported continuation update')
            p.update(copy.deepcopy(updates))
        if not revision or revision==old['revision']:raise ValueError('new explicit design revision required')
        p.update(version=2,revision=revision,steps=copy.deepcopy(remaining),bindings=observed,
                 continuation={'run':run,'state_hash':digest(parent),'session':c.session,'skipped_steps':list(carried)})
        p['result_bindings']={name:{'result':value['result']} for name,value in carried.items() if 'result' in value}
        result=self.plan(p)
        live.atomic_json(self.path(result['run'])/'continuation_readback.json',{'parent':p['continuation'],'bindings':observed})
        return result|{'parent_run':run,'skipped_steps':len(carried)}

    def _execute(self, run):
        folder=self.path(run);p=validate_plan(json.loads((folder/'plan.json').read_text()))
        state=json.loads((folder/'state.json').read_text())
        if state['plan_hash']!=digest(p):raise ValueError('plan changed; publish a new design revision')
        if state['status']!='planned':
            raise ValueError('run already attempted; inspect outcome, never replay construction automatically')
        c=self.client();state.update(status='running',session=c.session,started=time.time())
        def persist():live.atomic_json(folder/'state.json',state)
        persist()
        class Recorded:
            session=c.session
            evidence=c.evidence
            allow_rejection=False
            fit_budget=None
            def request(_,op,params,**kwargs):
                mutating=live.is_mutation(op,params)
                if _.fit_budget is not None and not mutating:
                    if _.fit_budget['used']>=_.fit_budget['limit']:raise live.LiveError('fit_variation_budget','declared fit request budget exhausted')
                    _.fit_budget['used']+=1
                if mutating:state['step_mutation']={'operation':op,'game_constructed':'unknown'};persist()
                start=time.monotonic();r=c.request(op,params,**kwargs)
                state['calls']+=1;state['native_seconds']+=time.monotonic()-start
                state['last_request']=r['request_id'];persist()
                state['last_response']={k:r.get(k) for k in ('request_id','status')};state['last_response']['operation']=op
                state['last_response']['game_constructed']=r.get('result',{}).get('game_constructed','unknown');persist()
                state['last_response'].update({k:r['result'][k] for k in ('native_operating_state_changed','operating_effects') if k in r.get('result',{})})
                if mutating:state['step_mutation']=state['last_response'].copy();persist()
                harmless=_.allow_rejection and r['status']=='no_accepted_candidate' and r.get('result',{}).get('game_constructed') is False
                if r['status']!='ok' and not harmless:raise live.LiveError(r['status'],native_failure(r),r['request_id'])
                return r
        rc=Recorded()
        prior={}
        fit_chain_cache=None
        def world(port):return [port['position'][i]+p['origin'][i] for i in range(3)]
        def intent(ref):
            if isinstance(ref,str):
                port=p['ports'][ref];pos=world(port);direction=unit(port['direction'])
            else:
                rows=chain(ref['curve'])
                pos,direction=chain_point(rows,ref['u'],ref.get('segment'))
            tolerance=p.get('placement_tolerance',.15)
            return {'region':box([pos],max(1,tolerance)),'max_edges':16,'guide_xyz':pos,
                    'travel_direction':direction,'heading_tolerance_deg':p.get('heading_tolerance_deg',2),
                    'placement_tolerance':tolerance}
        def resolve(ref,interior=False,connected=False):
            exact=p.get('port_refs',{}).get(ref) if isinstance(ref,str) else None
            if exact and interior:
                raise ValueError('exact endpoint port cannot resolve as an interior attachment')
            loc=intent(ref)
            role=roles.get(p.get('role_refs',{}).get(ref)) if isinstance(ref,str) else None
            if role and role['mode']=='station_exit':
                if kind!='extend' or interior or connected:raise ValueError('qualified station_exit supports deliberate lead extension only')
                a=role['candidate']
            else:a,_=live._select_throat_port(rc,loc,interior=interior,tolerance=loc['placement_tolerance'],connected=connected)
            if exact:
                binding=state['steps'].get(exact['chain']) or prior.get(exact['chain']);rows=binding['edges']
                if 'end' in exact:
                    if len(rows)!=1:raise ValueError('exact named end requires one native edge')
                    expected_edge,expected_node=rows[0]['id'],rows[0][exact['end']]
                else:expected_edge,expected_node=exact['edge_id'],exact['node_id']
                if not any(e['id']==expected_edge and expected_node in (e['node0'],e['node1']) for e in rows) or (a['edge_id'],a['node_id'])!=(expected_edge,expected_node):raise ValueError('discovered port differs from exact authored chain endpoint')
            if fit_chain_cache is not None and isinstance(ref,dict) and a['edge_id'] not in {e['id'] for e in chain(ref['curve'])}:
                raise ValueError('fit attachment escaped the same named chain')
            if isinstance(ref,str) and 'grade' in p['ports'][ref]:
                expected=p['ports'][ref]['grade']
                if type(a.get('grade')) not in (int,float) or abs(a['grade']-expected)>p.get('grade_tolerance',.001):raise ValueError('attachment grade does not meet declared port')
            return a,loc
        def chain(name):
            binding=state['steps'].get(name) or prior.get(name)
            if not binding:raise ValueError('named earlier result unavailable')
            if fit_chain_cache is None:return fresh_binding(rc,binding)
            if name not in fit_chain_cache:fit_chain_cache[name]=fresh_binding(rc,binding)
            return fit_chain_cache[name]
        def follow_replacement(original,replacement,changed,request_id):
            for binding in list(state['steps'].values())+list(prior.values()):
                old=binding.get('edges',[])
                if any(e['id']==original for e in old):
                    binding.setdefault('original_edges',copy.deepcopy(old))
                    binding['edges']=[new for e in old for new in (changed if e['id']==original else [e])]
            state.setdefault('lineage',[]).append({'request_id':request_id,'original_edge':original,'replacement_edges':replacement})
            if prior:state['bindings']=prior
        def follow_batch(changed,request_id):
            for binding in list(state['steps'].values())+list(prior.values()):
                old=binding.get('edges',[])
                if any(e['id'] in changed for e in old):
                    binding.setdefault('original_edges',copy.deepcopy(old))
                    binding['edges']=[changed.get(e['id'],e) for e in old]
            state.setdefault('lineage',[]).extend({'request_id':request_id,'original_edge':old,
                'replacement_edges':[new['id']]} for old,new in changed.items())
            if prior:state['bindings']=prior
        def structure_query(spec):
            replacement=chain(spec['replace_chain']) if spec.get('replacement_boundaries') else None
            if replacement is not None:
                al,bl=intent(spec['source']),intent(spec['target'])
                a=replacement_boundary(rc,al,replacement,spec['replacement_boundaries']['source'])
                b=replacement_boundary(rc,bl,replacement,spec['replacement_boundaries']['target'])
                check_plain_coalescing(replacement,a,b)
            else:
                a,al=resolve(spec['source'],spec.get('source_interior',False),bool(spec.get('replace_chain')))
                b,bl=resolve(spec['target'],spec.get('target_interior',False),bool(spec.get('replace_chain')))
            q={'source':a,'target':b,'region':p['region'],'vertical':{'max_grade':p['max_grade']},'new_alignment':True,
               'guides':[g|{'position':world(g)} for g in spec.get('guides',[])],
               'structures':spec.get('structures',[{'classification':'NORMAL'}]*(len(spec.get('guides',[]))+1)),
               'representation':spec.get('representation','endpoint_cubic'),'radius':spec.get('radius',0),
               'fit_radius':spec.get('fit_radius',100),'handle_scale':spec.get('handle_scale',1)}
            if 'normal_offset_from' in spec:
                q['normal_offset_from']=copy.deepcopy(spec['normal_offset_from'])
                if 'group_index' in spec['normal_offset_from']:
                    for key in ('structures','representation','fit_radius','handle_scale'):q.pop(key,None)
            if 'leg_representations' in spec:q['leg_representations']=spec['leg_representations']
            if spec.get('source_interior') or spec.get('target_interior'):
                q.update(junctions=True,max_route_length=spec.get('max_route_length',p.get('max_route_length',800)))
                if spec.get('source_interior'):q['source']=a|{'location':al}
                if spec.get('target_interior'):q['target']=b|{'location':bl}
            if 'replace_chain' in spec:q.update(replace_chain=replacement if replacement is not None else chain(spec['replace_chain']),max_route_length=spec.get('max_route_length',p.get('max_route_length',800)))
            if replacement is not None:q.update(replacement_boundaries=spec['replacement_boundaries'],coalesce_plain=True)
            return q
        def fit_step(s):
            nonlocal fit_chain_cache
            cfg=fit_variation_config(s);tables={};nominal_controls=None;summary=None;fixed={}
            if cfg:
                fit_chain_cache={};rc.fit_budget={'used':0,'limit':cfg.get('max_requests',256)}
                for end in ('source','target'):
                    if isinstance(s[end],dict):chain(s[end]['curve'])
                variations,tables=fit_variation_positions(s,fit_chain_cache)
                if any(not in_region(intent(s[end])['guide_xyz'],p['region']) for end in ('source','target')):raise ValueError('nominal fit attachment outside authorised region')
                variations=[(a,d) for a,d in variations if all(in_region(intent(a[end])['guide_xyz'],p['region']) for end in ('source','target'))]
                summary={'attempt_count':0,'selected_requested_shift_m':None,'selected_actual_shift_m':None,'sampled_rejection_range_m':{},'boundary_proven':False,'nominal_geometry':'unavailable'}
                state.setdefault('fit_variations',{})[s['name']]=summary
                shape=s.get('candidates',[{'branch':'endpoint_cubic_graded'}])[0]
                if shape['branch'] in ('endpoint_cubic_level','endpoint_cubic_graded','guided_cubic_level'):
                    start,end=intent(s['source']),intent(s['target'])
                    points=[(start['guide_xyz'],start['travel_direction'])]
                    if shape['branch']=='guided_cubic_level':points.extend((world(g),g['travel_direction']) for g in s.get('guides',[]))
                    points.append((end['guide_xyz'],[-x for x in end['travel_direction']] if s['kind']=='branch' else end['travel_direction']))
                    nominal_controls=[]
                    for (a,da),(b,db) in zip(points,points[1:]):
                        length=math.dist(a,b)*shape.get('handle_scale',1);da=unit(da[:2]);db=unit(db[:2])
                        nominal_controls.append({'p0':a,'p1':b,'t0':[length*x for x in da]+[0],'t1':[length*x for x in db]+[0]})
                    summary['nominal_geometry']='endpoint_control_model'
            else:variations=[(a,{}) for a in s.get('attachments',[{'source':s['source'],'target':s['target']}])]
            attempts=[]
            state.setdefault('candidates',{})[s['name']]=attempts
            for number,(alternative,shifts) in enumerate(variations,1):
                spec=s|alternative
                if summary:summary['attempt_count']=number;summary['requests_used']=rc.fit_budget['used']
                for end,window in s.get('attachment_windows',{}).items():
                    if end in ('source','target') and not in_region(intent(spec[end])['guide_xyz'],window):raise ValueError('attachment outside designer window')
                rc.allow_rejection=True
                try:
                    if s['kind']=='connect':prepared=rc.request('structured_chain',structure_query(spec)|{'prepare':True})
                    else:
                        if cfg and isinstance(spec['source'],str):
                            if 'source' not in fixed:fixed['source']=resolve(spec['source'],True)
                            a,al=fixed['source']
                        else:a,al=resolve(spec['source'],True)
                        if cfg and isinstance(spec['target'],str):
                            if 'target' not in fixed:fixed['target']=resolve(spec['target'],False)
                            b,bl=fixed['target']
                        else:b,bl=resolve(spec['target'],s['kind']=='crossover')
                        q={'source':a,'target':b,'location':al,'region':p['region'],'vertical':{'max_grade':p['max_grade']},
                           'max_route_length':s.get('max_route_length',p.get('max_route_length',800)),'radius':s.get('radius',0)}
                        if 'guides' in s:q['guides']=[{'pos':world(g),'direction':g['travel_direction']} for g in s['guides']]
                        shapes=s.get('candidates',[{'branch':'endpoint_cubic_graded' if p['version']==2 else 'endpoint_cubic_level','through':'subdivide'}])
                        if s['kind']=='crossover':q['target_location']=bl;prepared=live.prepare_crossover(rc,q,shapes)
                        else:prepared=live.prepare_interior_junction(rc,q,shapes)
                except live.LiveError as exc:
                    if getattr(exc,'status',None)!='no_eligible_candidates':raise
                    attempts.append({'index':number,'attachments':alternative,'shift_m':shifts,'status':exc.status,'reason':str(exc)[:300]})
                    if summary:
                        summary['requests_used']=rc.fit_budget['used']
                        for end,shift in shifts.items():
                            limits=summary['sampled_rejection_range_m'].setdefault(end,[shift,shift]);limits[0]=min(limits[0],shift);limits[1]=max(limits[1],shift)
                    persist();continue
                finally:rc.allow_rejection=False
                attempt={'index':number,'attachments':alternative,'status':prepared['status'],'request_id':prepared['request_id'],
                         'reason':native_failure(prepared) if prepared['status']!='ok' else None}
                if cfg:
                    attempt['shift_m']=shifts;summary['requests_used']=rc.fit_budget['used']
                    if prepared.get('result',{}).get('game_constructed') is not False:
                        state['step_mutation']=state['last_response'].copy();persist();raise live.LiveError('fit_variation_uncertain','preparation effects are not confirmed absent',prepared['request_id'])
                    if prepared['status']=='ok':
                        fit=prepared.get('result',{}).get('fit');controls=fit.get('controls') if isinstance(fit,dict) else None
                        check=fit_geometry_check(controls,nominal_controls,cfg.get('intent',{}),p['region']);attempt['geometry_checks']=check
                        if cfg.get('intent') and (not check['available'] or ('max_extra_inflections' in cfg['intent'] and check.get('inflection_comparison')!='checked')):
                            attempts.append(attempt);summary['geometry_checks']=check;persist();raise live.LiveError('fit_geometry_unavailable','explicit geometry intent cannot be checked before construction',prepared['request_id'])
                        if check['passed'] is False:attempt.update(status='intent_rejected',reason='; '.join(check['reasons']))
                    if attempt['status']!='ok':
                        for end,shift in shifts.items():
                            limits=summary['sampled_rejection_range_m'].setdefault(end,[shift,shift]);limits[0]=min(limits[0],shift);limits[1]=max(limits[1],shift)
                attempts.append(attempt);persist()
                if attempt['status']=='ok':
                    if cfg:
                        geometry=fit.get('candidate_geometry',{}) if isinstance(fit,dict) else {}
                        summary.update(selected_requested_shift_m=shifts,selected_actual_shift_m={end:measure((a if end=='source' else b)['edge_id'],(a if end=='source' else b)['parameter'])-nominal for end,(nominal,measure) in tables.items()},geometry_checks=attempt['geometry_checks'],
                                       native_proposal_evaluated=prepared['result'].get('native_proposal_evaluated'),native_shape_fit_invoked=geometry.get('native_fit_invoked') if isinstance(geometry,dict) else None)
                        persist();rc.fit_budget=None;fit_chain_cache=None
                    if s['kind']=='connect':return rc.request('structured_chain',{'execute':True,'prepared_request':prepared['request_id']})
                    if s['kind']=='crossover':return live.build_prepared_crossover(rc,prepared)
                    return live.build_prepared_interior_junction(rc,prepared)
            rc.fit_budget=None;fit_chain_cache=None
            if attempts:raise live.LiveError('no_accepted_candidate',attempts[-1]['reason'] or 'no accepted attachment in configured alternatives')
            raise ValueError('no attachment alternatives supplied')
        try:
            roles={}
            if p.get('continuation'):
                parent=p['continuation'];parent_path=self.path(parent['run'])
                if c.session!=parent['session'] or digest(json.loads((parent_path/'state.json').read_text()))!=parent['state_hash']:raise ValueError('continuation parent/session changed')
            if p.get('role_bindings'):
                roles=self.interfaces().resolve(c,p['interface_registry'],p['interface_revision'],list(p['role_bindings']))['resolved']
                if roles!=p['role_bindings']:raise ValueError('named interface changed; resolve and publish a fresh plan')
            prior.update(p.get('result_bindings',{}))
            for name,binding in p.get('bindings',{}).items():prior.setdefault(name,{}).update(edges=fresh_binding(rc,binding))
            for s in p['steps']:
                state['current_step']=s['name'];state['current_step_start_calls']=state['calls'];state['step_mutation']=None;persist();kind=s['kind']
                if kind=='signal_chain':
                    rows=[edge for name in s['chains'] for edge in chain(name)]
                    locations,total=signal_chain_locations(rows,s['forward'],s['spacing'],s['start_offset'],s['end_clearance'],s['max_count'])
                    progress={'placements':[],'sampled_length':total,'sampled_only':True}
                    state.setdefault('signal_chains',{})[s['name']]=progress;persist()
                    if s.get('placement_mode')=='batch':
                        chunks=signal_batch_chunks(rows,locations,s['seed_id'],s.get('excluded_intervals',[]))
                        # Qualify every ordinary through node before the first mutation,
                        # including unsignalled edges between budget chunks.
                        current=chunks[0]['brief']['start_node'] if chunks and chunks[0]['first']==0 else rows[0]['node0']
                        if len(rows)>1:
                            shared={rows[0]['node0'],rows[0]['node1']} & {rows[1]['node0'],rows[1]['node1']}
                            current=next(n for n in (rows[0]['node0'],rows[0]['node1']) if n not in shared)
                        for first in range(0,len(rows),16):
                            selected=rows[first:first+16];q={'edges':selected,'start_node':current}
                            if first:q['before_edge']=rows[first-1]['id']
                            if first+16<len(rows):q['after_edge']=rows[first+16]['id']
                            checked=rc.request('operating_inspect',{'signal_chain_check':live._signal_batch_input(q)})
                            if checked['status']!='ok' or checked.get('result',{}).get('signal_chain_check',{}).get('checked') is not True:
                                raise live.LiveError('signal_chain_not_ordinary',native_failure(checked),checked.get('request_id'))
                            for row in selected:current=row['node1'] if current==row['node0'] else row['node0']
                        for chunk in chunks:
                            brief=chunk['brief']|{'edges':rows[chunk['first']:chunk['last']+1]}
                            # Earlier native replacement receipts change identities, not phase.
                            brief['placements']=[q|{'edge_id':rows[loc['edge_index']]['id']} for q,loc in zip(brief['placements'],chunk['locations'])]
                            if chunk['first']:brief['before_edge']=rows[chunk['first']-1]['id']
                            if chunk['last']+1<len(rows):brief['after_edge']=rows[chunk['last']+1]['id']
                            r=live.place_signal_batch(rc,brief,execute=True)
                            if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r.get('request_id'))
                            value=r['result']
                            progress.setdefault('batches',[]).append({'request_id':r['request_id'],'receipt':value});persist()
                            # Preserve exact receipt before any qualification can fail.
                            changed=live.signal_batch_replacements(brief,value)
                            progress['placements'].extend(loc|q|{'request_id':r['request_id']} for loc,q in zip(chunk['locations'],value['placements']))
                            follow_batch(changed,r['request_id'])
                            rows=[changed.get(row['id'],row) for row in rows];persist()
                        state['steps'][s['name']]={'status':'built','edges':[],'result':progress};persist()
                        continue
                    for location in locations:
                        if any(a<=location['distance']<=b for a,b in s.get('excluded_intervals',[])):continue
                        index=location['edge_index'];original=rows[index]['id']
                        brief={'edge_id':original,'parameter':location['parameter'],'forward':location['forward'],'one_way':s.get('one_way',True)}
                        if 'seed_id' in s:brief['seed_id']=s['seed_id']
                        r=live.place_signal(rc,brief,execute=True)
                        if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r.get('request_id'))
                        value=r['result']
                        replacement=value['replacement_edge']
                        # Persist the successful effect before any fallible readback.
                        progress['placements'].append(location|{'one_way':brief['one_way'],'request_id':r['request_id'],'replaced_edge':original,'replacement_edge':replacement,'signal':value.get('signal')});persist()
                        if value['replaced_edge']!=original:raise ValueError('signal receipt replaced a different edge; inspect partial effects')
                        changed=inspect_edges(rc,[replacement])
                        if any(changed[0][k]!=rows[index][k] for k in ('node0','node1')) or any(abs(a-b)>.001 for k in ('p0','p1','t0','t1') for a,b in zip(changed[0][k],rows[index][k])):raise ValueError('signal replacement changed chain geometry; inspect partial effects')
                        rows[index]=changed[0]
                        follow_replacement(original,[replacement],changed,r['request_id']);persist()
                    state['steps'][s['name']]={'status':'built','edges':[],'result':progress};persist()
                    continue
                elif kind in tasks.KINDS:
                    brief=tasks.references(s['brief'],state['steps']|prior,roles)
                    r=tasks.perform(rc,kind,brief)
                elif kind=='stub':
                    port=p['ports'][s['port']];pos=world(port);d=unit(s.get('direction',port['direction']));length=s['length']
                    grade=s.get('grade',0)
                    end=[pos[i]+length*(d[i] if i<2 else grade) for i in range(3)]
                    local_region=box([pos,end])
                    for i in range(3):
                        local_region['min'][i]=max(local_region['min'][i],p['region']['min'][i])
                        local_region['max'][i]=min(local_region['max'][i],p['region']['max'][i])
                    seed_track=s.get('track',p['track'])
                    q={'authorised':True,'length':length,'fixture':{'position':pos,'travel_direction':d,'grade':grade,
                       'region':local_region,'template':seed_track['template'],'style':seed_track['style']}}
                    if any(not p['region']['min'][i]<=end[i]<=p['region']['max'][i] for i in range(3)):
                        raise ValueError('stub end outside authorised plan region')
                    r=rc.request('test_approach',q)
                elif kind=='remove':
                    rows=chain(s['chain'])
                    if any(not in_region(e[k],p['region']) for e in rows for k in ('p0','p1')):raise ValueError('removal outside authorised region')
                    r=live.LiveClient.remove_exact_chain(rc,[e['id'] for e in rows],allow_structures=s.get('allow_structures',False))
                elif kind=='terrain_check':
                    positions=[[pos[i]+p['origin'][i] for i in range(2)] for pos in s['positions']]
                    samples=terrain_samples(rc,p['region'],positions)
                    state.setdefault('terrain',{})[s['name']]={'absolute_floor':s['absolute_floor'],'samples':samples,'sampled_only':True};persist()
                    if any(sample.get('valid') is not True or type(sample.get('height')) not in (int,float) or sample['height']<s['absolute_floor'] for sample in samples):raise ValueError('sampled terrain below explicit absolute floor or unavailable')
                    r={'status':'ok','request_id':state['last_request'],'result':{'edges':[]}}
                elif kind=='structure_seed':
                    source,target=p['ports'][s['source']],p['ports'][s['target']]
                    start={'position':world(source),'travel_direction':[-x for x in unit(source['direction'])],'grade':-source['grade']}
                    end={'position':world(target),'travel_direction':unit(target['direction']),'grade':target['grade']}
                    q={'prepare':True,'new_alignment':True,'freestanding':True,'source':start,'target':end,
                       'track':s.get('track',p['track']),'region':p['region'],'vertical':{'max_grade':p['max_grade']},
                       'guides':[],'structures':[s['structure']],'representation':'endpoint_cubic',
                       'radius':s.get('radius',0),'handle_scale':s.get('handle_scale',1)}
                    prepared=rc.request('structured_chain',q)
                    r=rc.request('structured_chain',{'execute':True,'prepared_request':prepared['request_id']})
                elif kind=='group':
                    prepared=rc.request('structured_chain',{'prepare':True,'groups':[structure_query(g) for g in s['groups']]})
                    r=rc.request('structured_chain',{'execute':True,'prepared_request':prepared['request_id']})
                elif kind in ('connect','branch','crossover'):
                    r=fit_step(s)
                else:
                    a,al=resolve(s['source'],kind in ('branch','crossover'))
                    if kind=='extend':
                        target=p['ports'][s['target']]
                        q={'anchor_edge':a['edge_id'],'anchor_node':a['node_id'],'end_xy':world(target)[:2],
                           'end_direction':unit(target['direction']),'radius':s.get('radius',1),'region':p['region'],
                           'vertical':{'end_height':world(target)[2],'end_grade':target.get('grade',0),'max_grade':p['max_grade']}}
                        r=live.extend(rc,q,execute=True)
                value=r.get('result',r)
                if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r))
                edge_ids=value.get('readback',{}).get('ordered_edges',value.get('ordered_edges',[]))
                if kind=='signal':edge_ids=[value['replacement_edge']]
                edges=value.get('edges',[])
                if value.get('groups'):
                    edge_ids=[i for group in value['groups'] for i in group['readback']['ordered_edges']]
                if edges and isinstance(edges[0],int):edge_ids=edges;edges=[]
                if edge_ids:
                    edges=inspect_edges(rc,edge_ids)
                # Follow the exact native replacement receipt, never proximity.
                placements=value.get('placements',[])
                placements=(placements if isinstance(placements,list) else [])+([value['placement']] if 'placement' in value else [])
                if kind=='signal':placements.append({'original_edge':value['replaced_edge'],'replacement_edges':edge_ids})
                for placement in placements:
                    original=placement.get('original_edge');replacement=placement.get('replacement_edges',[])
                    if original and replacement:
                        changed=edges if kind=='signal' else inspect_edges(rc,replacement)
                        follow_replacement(original,replacement,changed,r.get('request_id'))
                if prior:state['bindings']=prior
                invalidated=s.get('replace_chain') or (s.get('chain') if kind=='remove' else None)
                if invalidated:state.setdefault('invalidated_bindings',[]).append(invalidated)
                state['steps'][s['name']]={'status':'built','request_id':r.get('request_id',r.get('job_id')),
                                          'edges':edges}
                if kind in tasks.KINDS:state['steps'][s['name']]['result']=value
                persist()
            state['status']='built';state['elapsed_seconds']=time.time()-state['started'];persist()
        except Exception as exc:
            state.update(status='needs_attention',error=str(exc)[:450],error_type=type(exc).__name__,elapsed_seconds=time.time()-state['started'])
            status=getattr(exc,'status',None)
            state['failure_class']=('native_proposal_rejection' if status=='no_accepted_candidate' else
                'adapter_attachment_exclusion' if status in ('no_eligible_candidates','ambiguous_attachment','discovery_incomplete','role_unavailable','ambiguous_role') else 'operation_or_adapter_check')
            persist()
        return self.summary(run)

    def summary(self,run):
        state=json.loads((self.path(run)/'state.json').read_text())
        return {k:state[k] for k in ('status','session','current_step','error','calls','native_seconds','elapsed_seconds') if k in state} | {
            'run':run,'completed_steps':len(state['steps']),'failure_class':state.get('failure_class'),'evidence':str(self.path(run)/'state.json')}

    def review(self,run):
        folder=self.path(run);p=json.loads((folder/'plan.json').read_text());state=json.loads((folder/'state.json').read_text())
        if state['plan_hash']!=digest(p):raise ValueError('plan changed')
        c=self.client()
        if c.session!=state.get('session'):raise ValueError('session changed; new survey and rebind required')
        if state['status'] not in ('built','needs_attention'):raise ValueError('unfinished execution requires reconciliation before review')
        if (self.runs/'execution.lock').exists():raise ValueError('operator run is already executing')
        journal=getattr(c,'journal',None)
        if journal and journal.exists() and json.loads(journal.read_text()).get('pending'):raise ValueError('unresolved native request requires reconciliation')
        construction_complete=state['status']=='built'
        if not construction_complete:
            harmless=no_step_effects(state)
            if not harmless:raise ValueError('uncertain/partial effects require reconciliation before review')
        rows=[];ports={};port_errors={};route_paths={}
        # Route endpoints are the free outer boundaries, so their direction is outward.
        for route in p['routes']:
            for name in (route['source'],route['target']):
                if name in ports or name in port_errors:continue
                port=p['ports'][name];pos=[port['position'][i]+p['origin'][i] for i in range(3)]
                loc={'region':box([pos],1),'max_edges':16,'guide_xyz':pos,'travel_direction':unit(port['direction']),'heading_tolerance_deg':2}
                try:ports[name],_=live._select_throat_port(c,loc,tolerance=.15)
                except live.LiveError as exc:
                    if construction_complete or exc.status not in ('no_eligible_candidates','ambiguous_attachment'):raise
                    port_errors[name]={'status':exc.status,'error':str(exc),'request_id':exc.request_id}
            missing={name:port_errors[name] for name in (route['source'],route['target']) if name in port_errors}
            if missing:
                route_paths[route['name']]=[]
                rows.append({'name':route['name'],'verified':False,'status':'attachment_unavailable','ports':missing})
                continue
            a,b=ports[route['source']],ports[route['target']]
            r=c.request('route',{'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],
                                'target_node':b['node_id'],'mode':'TRAIN','max_length':p.get('max_route_length',800),
                                'required_edges':[a['edge_id'],b['edge_id']]})
            z=r.get('result',{});route_paths[route['name']]=z.get('path',[]);rows.append({'name':route['name'],'verified':r['status']=='ok' and z.get('requested_route_verified') is True,
                                            'length':z.get('total_path_length'),'request_id':r['request_id']})
        edges,queries=discover_region(c,p['region'])
        edges=inspect_edges(c,[e['id'] for e in edges])
        report={'session':c.session,'construction_complete':construction_complete,'construction_status':state['status'],
                'completed_steps':len(state['steps']),'planned_steps':len(p['steps']),
                'routes':rows,'edges':edges,'geometry_queries':queries,'all_routes_verified':bool(rows) and all(r['verified'] for r in rows),
                'physical_operation':'not tested','design_quality':'requires visual review'}
        report['crossings']=crossing_observations(p,edges,route_paths)
        report['crossing_requirements_observed']=all(x['separate_endpoint_identities_observed'] and x['required_structure_observed'] for x in report['crossings'])
        live.atomic_json(folder/'review.json',report);render(p,edges,folder/'overlay.svg');render_profile(p,edges,folder/'profile-overlay.svg')
        return {'status':'reviewed' if construction_complete and report['all_routes_verified'] and report['crossing_requirements_observed'] else 'needs_attention',
                'construction_complete':construction_complete,'completed_steps':len(state['steps']),'planned_steps':len(p['steps']),
                'verified_routes':sum(r['verified'] for r in rows),'required_routes':len(rows),
                'crossing_requirements_observed':report['crossing_requirements_observed'],
                'view':str(folder/'overlay.svg'),'profile':str(folder/'profile-overlay.svg'),'evidence':str(folder/'review.json')}

    def gui(self, action, **params):
        c=self.client();local=c.log.parent.parent
        if action=='capture':
            folder=local/'screenshots';before={str(f):f.stat().st_mtime_ns for f in folder.glob('*') if f.is_file()}
        elif action=='save':
            if not isinstance(params.get('name'),str) or not re.fullmatch(r'[A-Za-z0-9 _-]{1,100}',params['name']):raise ValueError('plain checkpoint name required')
            folder=local/'save';target=folder/(params['name']+'.sav')
            if target.exists():raise ValueError('checkpoint already exists; choose a unique name')
        r=c.request('operator_gui',{'action':action,**params})
        result={'status':r['status'],**r.get('result',{}),'evidence':str(c.evidence/(r['request_id']+'.response.json'))}
        if r['status']!='ok' or action not in ('capture','save'):return result
        deadline=time.monotonic()+10;previous=None
        while time.monotonic()<deadline:
            candidates=([target] if action=='save' else sorted((f for f in folder.glob('*') if f.is_file() and before.get(str(f))!=f.stat().st_mtime_ns),key=lambda f:f.stat().st_mtime_ns,reverse=True))
            if candidates and candidates[0].exists():
                f=candidates[0];signature=(str(f),f.stat().st_size,f.stat().st_mtime_ns)
                if signature==previous and signature[1]>0:
                    result.update(file_completed=True,file=str(f),bytes=signature[1],sha256=hashlib.sha256(f.read_bytes()).hexdigest());break
                previous=signature
            time.sleep(.2)
        else:result.update(status='file_completion_unobserved',file_completed=False)
        live.atomic_json(c.evidence/(r['request_id']+'.operator_file.json'),result)
        return result


def render(plan,edges,path,*,horizontal_scale=None):
    """Equal-scale SVG of designer controls and observed native BaseEdge curves."""
    origin=plan['origin'];curves=list(plan.get('curves',{}).values())
    actual=[{k:[e[k][i]-(origin[i] if k in ('p0','p1') else 0) for i in range(3)] for k in ('p0','p1','t0','t1')} for e in edges]
    points=[p for c in curves+actual for p in (c['p0'],c['p1'],[c['p0'][i]+c['t0'][i]/3 for i in range(3)],[c['p1'][i]-c['t1'][i]/3 for i in range(3)])]+[v['position'] for v in plan['ports'].values()]
    if not points:points=[[0,0,0],[1,1,0]]
    lo=[min(p[i] for p in points) for i in range(2)];hi=[max(p[i] for p in points) for i in range(2)]
    scale=min(1100/max(hi[0]-lo[0],1),430/max(hi[1]-lo[1],1))
    if horizontal_scale is not None:scale=min(scale,horizontal_scale)
    compact=plan.get('diagram_compact',False);height=max(320,math.ceil((hi[1]-lo[1])*scale+270)) if compact else 650
    baseline=height-150 if compact else 540
    def xy(p):return [80+(p[0]-lo[0])*scale,baseline-(p[1]-lo[1])*scale]
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" data-horizontal-scale="{scale}"><rect width="1280" height="{height}" fill="#f8fafc"/>',
         f'<text x="50" y="40" font-family="Arial" font-size="25">{html.escape(plan.get("title","Railway plan"))} — {html.escape(plan["revision"])}</text>',
         f'<text x="50" y="72" font-family="Arial" font-size="16">{html.escape(plan.get("diagram_legend","Orange: recorded plan · navy: native geometry · equal scale"))}</text>']
    for group,color,width in ((curves,'#f5a524',5),(actual,'#193950',2.2)):
        for c in group:
            stroke=c.get('diagram_color',color);label=c.get('diagram_label','')
            line_width=6 if c.get('diagram_role')=='deck' else (2 if compact else width)
            dash=' stroke-dasharray="6 3"' if c.get('diagram_role')=='ramp' else ''
            ps=[c['p0'],[c['p0'][i]+c['t0'][i]/3 for i in range(3)],[c['p1'][i]-c['t1'][i]/3 for i in range(3)],c['p1']]
            a,b,d,e=[xy(v) for v in ps]
            svg.append(f'<path d="M {a[0]} {a[1]} C {b[0]} {b[1]} {d[0]} {d[1]} {e[0]} {e[1]}" fill="none" stroke="{html.escape(stroke)}" stroke-width="{line_width}"{dash}><title>{html.escape(label)}</title></path>')
    for index,(name,p) in enumerate(plan['ports'].items()):
        if not p.get('label'):continue
        x,y=xy(p['position']);label=str(index+1) if compact else name
        svg.append(f'<text x="{x+6}" y="{y-7}" font-family="Arial" font-size="{10 if compact else 14}">{html.escape(label)}<title>{html.escape(name)}</title></text>')
        if p.get('diagram_marker'):svg.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#9d174d"><title>{html.escape(name)}</title></circle>')
    if compact:
        for index,name in enumerate(list(plan['ports'])[:8]):
            x=50+600*(index//4);y=height-110+17*(index%4)
            label=f'{index+1}: {name}';visible=label if len(label)<=75 else label[:72]+'...'
            svg.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="11">{html.escape(visible)}<title>{html.escape(label)}</title></text>')
    note='Numbered controls: hover for family/kind/identity; full labels in controls.json.' if compact else 'Centreline reconstruction; internal native turnout movement geometry and train operation are separate.'
    svg.append(f'<text x="50" y="{height-30 if compact else 610}" font-family="Arial" font-size="15">{note}</text></svg>')
    Path(path).write_text(''.join(svg),encoding='utf-8')

def render_profile(plan,edges,path,*,horizontal_scale=None):
    """Projected local longitudinal coordinate, with explicitly exaggerated height."""
    axis=unit(plan.get('profile_axis',[1,0]));origin=plan['origin'];exaggeration=plan.get('profile_exaggeration',4)
    curves=list(plan.get('curves',{}).items())
    actual=[('native '+str(e['id']),{k:[e[k][i]-(origin[i] if k in ('p0','p1') else 0) for i in range(3)] for k in ('p0','p1','t0','t1')}) for e in edges]
    def sampled(curve):
        points=[]
        for j in range(65):
            u=j/64;h=[2*u**3-3*u*u+1,u**3-2*u*u+u,-2*u**3+3*u*u,u**3-u*u]
            p=[sum(h[n]*curve[k][i] for n,k in enumerate(('p0','t0','p1','t1'))) for i in range(3)]
            points.append((sum(p[i]*axis[i] for i in range(2)),p[2]+origin[2]))
        return points
    rows=[(c.get('diagram_label',name),sampled(c),c.get('diagram_color',color),c.get('diagram_role')) for group,color in ((curves,'#f5a524'),(actual,'#193950')) for name,c in group]
    points=[p for _,ps,_,_ in rows for p in ps]
    points.extend((sum(v['position'][i]*axis[i] for i in range(2)),v['position'][2]+origin[2]) for v in plan['ports'].values())
    if not points:points=[(0,origin[2]),(1,origin[2])]
    xmin,xmax=min(p[0] for p in points),max(p[0] for p in points);zmin,zmax=min(p[1] for p in points),max(p[1] for p in points)
    plot_height=330-18*len(plan.get('crossings',[]))
    scale=min(1080/max(xmax-xmin,1),plot_height/max((zmax-zmin)*exaggeration,1))
    if horizontal_scale is not None:scale=min(scale,horizontal_scale)
    compact=plan.get('diagram_compact',False);height=max(300,math.ceil((zmax-zmin)*scale*exaggeration+240)) if compact else 560
    baseline=height-100 if compact else 440
    def xy(x,z):return 100+(x-xmin)*scale,baseline-(z-zmin)*scale*exaggeration
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" data-horizontal-scale="{scale}"><rect width="1280" height="{height}" fill="#f8fafc"/>',
         f'<text x="50" y="35" font-family="Arial" font-size="24">{html.escape(plan.get("title","Railway"))} — elevation profile</text>',
         f'<text x="50" y="65" font-family="Arial" font-size="16">Projected local axis {axis}; vertical exaggeration {exaggeration}×; orange intended, navy native</text>']
    if plan.get('diagram_legend'):
        svg.append(f'<text x="50" y="88" font-family="Arial" font-size="14">{html.escape(plan["diagram_legend"])}</text>')
    for j in range(5):
        z=zmin+(zmax-zmin)*j/4;x,y=xy(xmin,z)
        svg.append(f'<path d="M 90 {y} L 1190 {y}" stroke="#d3dce4"/><text x="30" y="{y+5}" font-family="Arial" font-size="13">z {z:.2f}</text>')
    for name,ps,color,role in rows:
        coords=[xy(x,z) for x,z in ps];d=' '.join(('M' if i==0 else 'L')+f' {x:.3f} {y:.3f}' for i,(x,y) in enumerate(coords))
        width=6 if role=='deck' else 2;dash=' stroke-dasharray="6 3"' if role=='ramp' else ''
        svg.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash}><title>{html.escape(name)}</title></path>')
    for index,(name,v) in enumerate(plan['ports'].items()):
        if not v.get('diagram_marker'):continue
        x,y=xy(sum(v['position'][i]*axis[i] for i in range(2)),v['position'][2]+origin[2])
        label=str(index+1) if compact else name
        svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#9d174d"/><text x="{x+5}" y="{y-5}" font-family="Arial" font-size="11">{html.escape(label)}<title>{html.escape(name)}</title></text>')
    for index,crossing in enumerate(plan.get('crossings',[])):
        distance=sum(crossing['position'][i]*axis[i] for i in range(2))
        x,_=xy(distance,zmin)
        label=f'{crossing["name"]} at projected {distance:.2f}: planned upper z={crossing["upper_height"]+origin[2]:.2f}, lower z={crossing["lower_height"]+origin[2]:.2f}'
        svg.append(f'<path d="M {x} {140+18*index} L {x} 440" stroke="#ad8090" stroke-dasharray="4 4"/><text x="50" y="{92+18*index}" font-family="Arial" font-size="12">{html.escape(label)}</text>')
    svg.append(f'<text x="90" y="{height-65 if compact else 475}" font-family="Arial" font-size="14">Projected distance {xmin:.2f}–{xmax:.2f}, native coordinate units; absolute z axis</text>')
    svg.append(f'<text x="50" y="{height-25 if compact else 520}" font-family="Arial" font-size="14">Centreline profiles only; projected height difference is not structure/clearance certification.</text></svg>')
    Path(path).write_text(''.join(svg),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','survey','track-catalogue','station-survey','station-exits','station-routes','diagnose','register-interfaces','resolve-interfaces','plan','execute','summary','review','continue','corridor-plan','corridor-build','corridor-status','corridor-continue','corridor-attach-completion','corridor-complete','approach-plan','approach-build','approach-continue','approach-review','approach-render','camera','capture','save'])
    parser.add_argument('--input',type=Path);parser.add_argument('--run');parser.add_argument('--context',type=Path,default=CONTEXT)
    a=parser.parse_args()
    try:
        op=Operator(context=a.context)
        data=json.loads(a.input.read_text(encoding='utf-8-sig')) if a.input else {}
        if a.action in ('execute','summary','review'):r=getattr(op,a.action)(a.run)
        elif a.action=='continue':r=op.continue_plan(a.run,**data)
        elif a.action=='plan':r=op.plan(data)
        elif a.action=='status':r=op.status()
        elif a.action=='survey':r=op.survey(**data)
        elif a.action=='track-catalogue':r=op.track_catalogue(**data)
        elif a.action=='corridor-plan':r=op.plan_corridor(data)
        elif a.action=='corridor-build':r=op.build_corridor(a.run)
        elif a.action=='corridor-status':r=op.corridor_status(a.run)
        elif a.action=='corridor-continue':r=op.continue_corridor(a.run,**data)
        elif a.action=='corridor-attach-completion':r=op.attach_corridor_completion(a.run,**data)
        elif a.action=='corridor-complete':r=op.complete_corridor(a.run,**data)
        elif a.action=='approach-plan':r=op.plan_approach(data)
        elif a.action=='approach-build':r=op.build_approach(a.run)
        elif a.action=='approach-continue':r=op.continue_approach(a.run,**data)
        elif a.action=='approach-review':r=op.review_approach(a.run,**data)
        elif a.action=='approach-render':r=op.render_approach(data.pop('source',a.run),**data)
        elif a.action=='station-survey':r=op.survey_station(data)
        elif a.action=='station-exits':r=op.survey_station_exits(data)
        elif a.action=='station-routes':r=op.review_station_routes(data)
        elif a.action=='diagnose':r=op.attachment_diagnostics(**data)
        elif a.action=='register-interfaces':r=op.register_interfaces(**data)
        elif a.action=='resolve-interfaces':r=op.resolve_interfaces(**data)
        else:r=op.gui(a.action,**data)
    except Exception as exc:r={'status':'error','error':str(exc)[:500]}
    print(json.dumps(r,separators=(',',':')))
    return 0 if r['status'] in ('ok','planned','built','reviewed') else 1


if __name__=='__main__':raise SystemExit(main())
