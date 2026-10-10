"""Named, plan-driven live operations. CLI and MCP share this implementation.

Plans are design data, never executable Python/Lua. Native operations and their
durable request receipts remain owned by bridge_live. A failed step is not replayed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import html
import json
import math
from pathlib import Path
import re
import time
import uuid

import bridge_live as live

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / '.local_runs/operator'
CONTEXT = ROOT / '.local_runs/live_python_interface/p02/context.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

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

def terrain_samples(client,region,positions):
    if not 1<=len(positions)<=128:raise ValueError('1..128 selected terrain samples required')
    samples=[]
    for offset in range(0,len(positions),8):
        batch=positions[offset:offset+8]
        areas=[batch]
        area=box([[*pos,(region['min'][2]+region['max'][2])/2] for pos in batch])
        if any(area['max'][i]-area['min'][i]>400 for i in range(2)):areas=[[pos] for pos in batch]
        for selected in areas:
            area=box([[*pos,(region['min'][2]+region['max'][2])/2] for pos in selected])
            if any(not in_region([*pos,(region['min'][2]+region['max'][2])/2],region) for pos in selected):raise ValueError('terrain sample outside authorised region')
            r=client.request('inspect',{'edge_ids':[],'site':{'region':area,'positions':selected}})
            if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r['request_id'])
            found=r['result']['site']['terrain']
            if len(found)!=len(selected) or any(row['xy']!=pos for row,pos in zip(found,selected)):raise ValueError('terrain sample identity/coverage incomplete')
            samples.extend(found)
    return samples

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
    names=set(p.get('bindings',{}))
    for binding in p.get('bindings',{}).values():
        if not isinstance(binding,dict) or not binding.get('edges'):raise ValueError('binding requires observed exact edges')
    def ref(r):
        if isinstance(r,str):
            if r not in p['ports']:raise ValueError('unknown port '+r)
        elif isinstance(r,dict) and set(r) in ({'curve','u'},{'curve','segment','u'}):
            if r['curve'] not in names or type(r['u']) not in (int,float) or not .05<=r['u']<=.95:
                raise ValueError('curve reference must refer to an earlier step at an interior parameter')
            if 'segment' in r and (type(r['segment']) is not int or r['segment']<1):raise ValueError('one-based explicit segment required')
        else:raise ValueError('named port or earlier curve reference required')
    for s in p['steps']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']) or s['name'] in names:
            raise ValueError('unique simple step names required')
        kind=s['kind']
        if kind not in ('stub','extend','connect','branch','crossover','group','structure_seed','remove','terrain_check'):raise ValueError('unsupported construction step')
        if p['version']==1 and kind in ('group','structure_seed','remove','terrain_check'):raise ValueError('new operation requires version2')
        if kind=='stub':
            ref(s['port'])
            if not isinstance(s['port'],str):raise ValueError('stub requires a named port')
            if 'direction' in s:unit(s['direction'])
            if not 5<=s['length']<=60:raise ValueError('native fixture length5..60 required')
            if type(s.get('grade',0)) not in (int,float) or not math.isfinite(s.get('grade',0)) or abs(s.get('grade',0))>min(p['max_grade'],.04):raise ValueError('stub grade within native .04 and selected bound required')
        elif kind=='structure_seed':
            ref(s['source']);ref(s['target'])
            if not all(isinstance(s[k],str) for k in ('source','target')) or s['source']==s['target']:raise ValueError('structure seed requires two distinct named ports')
            for name in (s['source'],s['target']):
                if 'grade' not in p['ports'][name]:raise ValueError('structure seed requires explicit outward endpoint grades')
            structure=s.get('structure',{})
            if set(structure)!={'classification','resource_name'} or structure.get('classification')!='BRIDGE' or not isinstance(structure.get('resource_name'),str) or not structure['resource_name']:
                raise ValueError('structure seed requires an explicit observed BRIDGE resource')
            if any(k in s for k in ('guides','structures','source_interior','target_interior','replace_chain','attachments','candidates')):raise ValueError('standalone structure seed is one unconnected span')
            if not 0<math.dist(p['ports'][s['source']]['position'],p['ports'][s['target']]['position'])<=800:raise ValueError('structure seed length must be within800')
            for key,default,lower,upper in [('radius',0,0,800),('handle_scale',1,0,4)]:
                value=s.get(key,default)
                if type(value) not in (int,float) or not math.isfinite(value) or value<lower or value>upper or (key=='handle_scale' and value==0):raise ValueError('invalid structure seed '+key)
        elif kind=='group':
            if len(s.get('groups',[])) not in (2,4):raise ValueError('native group requires2 or4 members')
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
            if kind=='connect':validate_structures(s)
            if 'replace_chain' in s and (kind!='connect' or s['replace_chain'] not in names):raise ValueError('replacement requires an earlier exact chain')
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
        return self._client or live.client_from_context(self.context,30)

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

    def plan(self, plan):
        p=validate_plan(plan);run=uuid.uuid4().hex[:16];folder=self.path(run);folder.mkdir()
        live.atomic_json(folder/'plan.json',p)
        live.atomic_json(folder/'state.json',{'status':'planned','plan_hash':digest(p),'steps':{},'calls':0,'native_seconds':0})
        render(p,[],folder/'plan.svg')
        render_profile(p,[],folder/'profile.svg')
        return {'status':'planned','run':run,'revision':p['revision'],'steps':len(p['steps']),
                'plan':str(folder/'plan.json'),'view':str(folder/'plan.svg'),'profile':str(folder/'profile.svg')}

    def execute(self, run):
        folder=self.path(run);lock=self.runs/'execution.lock'
        try:
            with lock.open('x'):pass
        except FileExistsError:raise ValueError('operator run is already executing; inspect its state')
        try:
            return self._execute(run)
        finally:lock.unlink()

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
            mutation=parent.get('step_mutation')
            harmless=(mutation is not None and mutation.get('game_constructed') is False) or ('step_mutation' in parent and mutation is None)
            if reconciled_step:
                if reconciled_step.get('name')!=failed:raise ValueError('reconciliation must name the unfinished step')
                rows=fresh_binding(c,reconciled_step)
                carried[failed]={'status':'reconciled','edges':rows,'request_id':response.get('request_id')}
            elif not harmless:raise ValueError('uncertain/partial effects must be reconciled before remaining-work plan')
        remaining=steps if steps is not None else [s for s in old['steps'] if s['name'] not in carried]
        if not remaining or any(s['name'] in carried for s in remaining):raise ValueError('remaining work cannot replay successful steps')
        selected={**old.get('bindings',{}),**parent.get('bindings',{}),**{name:value for name,value in carried.items() if value.get('edges')}}
        selected={name:value for name,value in selected.items() if name not in parent.get('invalidated_bindings',[])}
        selected.update(bindings or {})
        observed={name:{'edges':fresh_binding(c,value)} for name,value in selected.items()}
        p=copy.deepcopy(old)
        if updates:
            allowed={'ports','curves','region','profile_axis','profile_exaggeration','crossings','max_grade','max_route_length'}
            if set(updates)-allowed:raise ValueError('unsupported continuation update')
            p.update(copy.deepcopy(updates))
        if not revision or revision==old['revision']:raise ValueError('new explicit design revision required')
        p.update(version=2,revision=revision,steps=copy.deepcopy(remaining),bindings=observed,
                 continuation={'run':run,'state_hash':digest(parent),'session':c.session,'skipped_steps':list(carried)})
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
            def request(_,op,params,**kwargs):
                mutating=live.is_mutation(op,params)
                if mutating:state['step_mutation']={'operation':op,'game_constructed':'unknown'};persist()
                start=time.monotonic();r=c.request(op,params,**kwargs)
                state['calls']+=1;state['native_seconds']+=time.monotonic()-start
                state['last_request']=r['request_id'];persist()
                state['last_response']={k:r.get(k) for k in ('request_id','operation','status')}
                state['last_response']['game_constructed']=r.get('result',{}).get('game_constructed','unknown');persist()
                if mutating:state['step_mutation']=state['last_response'].copy();persist()
                harmless=_.allow_rejection and r['status']=='no_accepted_candidate' and r.get('result',{}).get('game_constructed') is False
                if r['status']!='ok' and not harmless:raise live.LiveError(r['status'],native_failure(r),r['request_id'])
                return r
        rc=Recorded()
        prior={}
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
            loc=intent(ref)
            a,_=live._select_throat_port(rc,loc,interior=interior,tolerance=loc['placement_tolerance'],connected=connected)
            if isinstance(ref,str) and 'grade' in p['ports'][ref]:
                expected=p['ports'][ref]['grade']
                if type(a.get('grade')) not in (int,float) or abs(a['grade']-expected)>p.get('grade_tolerance',.001):raise ValueError('attachment grade does not meet declared port')
            return a,loc
        def chain(name):
            binding=state['steps'].get(name) or prior.get(name)
            if not binding:raise ValueError('named earlier result unavailable')
            return fresh_binding(rc,binding)
        def structure_query(spec):
            a,al=resolve(spec['source'],spec.get('source_interior',False),bool(spec.get('replace_chain')))
            b,bl=resolve(spec['target'],spec.get('target_interior',False),bool(spec.get('replace_chain')))
            q={'source':a,'target':b,'region':p['region'],'vertical':{'max_grade':p['max_grade']},'new_alignment':True,
               'guides':[g|{'position':world(g)} for g in spec.get('guides',[])],
               'structures':spec.get('structures',[{'classification':'NORMAL'}]*(len(spec.get('guides',[]))+1)),
               'representation':spec.get('representation','endpoint_cubic'),'radius':spec.get('radius',0),
               'fit_radius':spec.get('fit_radius',100),'handle_scale':spec.get('handle_scale',1)}
            if 'leg_representations' in spec:q['leg_representations']=spec['leg_representations']
            if spec.get('source_interior') or spec.get('target_interior'):
                q.update(junctions=True,max_route_length=spec.get('max_route_length',p.get('max_route_length',800)))
                if spec.get('source_interior'):q['source']=a|{'location':al}
                if spec.get('target_interior'):q['target']=b|{'location':bl}
            if 'replace_chain' in spec:q.update(replace_chain=chain(spec['replace_chain']),max_route_length=spec.get('max_route_length',p.get('max_route_length',800)))
            return q
        def fit_step(s):
            alternatives=s.get('attachments',[{'source':s['source'],'target':s['target']}]);attempts=[]
            state.setdefault('candidates',{})[s['name']]=attempts
            for number,alternative in enumerate(alternatives,1):
                spec=s|alternative
                for end,window in s.get('attachment_windows',{}).items():
                    if end in ('source','target') and not in_region(intent(spec[end])['guide_xyz'],window):raise ValueError('attachment outside designer window')
                rc.allow_rejection=True
                try:
                    if s['kind']=='connect':prepared=rc.request('structured_chain',structure_query(spec)|{'prepare':True})
                    else:
                        a,al=resolve(spec['source'],True);b,bl=resolve(spec['target'],s['kind']=='crossover')
                        q={'source':a,'target':b,'location':al,'region':p['region'],'vertical':{'max_grade':p['max_grade']},
                           'max_route_length':s.get('max_route_length',p.get('max_route_length',800)),'radius':s.get('radius',0)}
                        if 'guides' in s:q['guides']=[{'pos':world(g),'direction':g['travel_direction']} for g in s['guides']]
                        shapes=s.get('candidates',[{'branch':'endpoint_cubic_graded' if p['version']==2 else 'endpoint_cubic_level','through':'subdivide'}])
                        if s['kind']=='crossover':q['target_location']=bl;prepared=live.prepare_crossover(rc,q,shapes)
                        else:prepared=live.prepare_interior_junction(rc,q,shapes)
                except live.LiveError as exc:
                    if getattr(exc,'status',None)!='no_eligible_candidates':raise
                    attempts.append({'index':number,'attachments':alternative,'status':exc.status,'reason':str(exc)[:300]});persist();continue
                finally:rc.allow_rejection=False
                attempts.append({'index':number,'attachments':alternative,'status':prepared['status'],'request_id':prepared['request_id'],
                                 'reason':native_failure(prepared) if prepared['status']!='ok' else None});persist()
                if prepared['status']=='ok':
                    if s['kind']=='connect':return rc.request('structured_chain',{'execute':True,'prepared_request':prepared['request_id']})
                    if s['kind']=='crossover':return live.build_prepared_crossover(rc,prepared)
                    return live.build_prepared_interior_junction(rc,prepared)
            if attempts:raise live.LiveError('no_accepted_candidate',attempts[-1]['reason'] or 'no accepted attachment in configured alternatives')
            raise ValueError('no attachment alternatives supplied')
        try:
            if p.get('continuation'):
                parent=p['continuation'];parent_path=self.path(parent['run'])
                if c.session!=parent['session'] or digest(json.loads((parent_path/'state.json').read_text()))!=parent['state_hash']:raise ValueError('continuation parent/session changed')
            for name,binding in p.get('bindings',{}).items():prior[name]={'edges':fresh_binding(rc,binding)}
            for s in p['steps']:
                state['current_step']=s['name'];state['current_step_start_calls']=state['calls'];state['step_mutation']=None;persist();kind=s['kind']
                if kind=='stub':
                    port=p['ports'][s['port']];pos=world(port);d=unit(s.get('direction',port['direction']));length=s['length']
                    grade=s.get('grade',0)
                    end=[pos[i]+length*(d[i] if i<2 else grade) for i in range(3)]
                    local_region=box([pos,end])
                    for i in range(3):
                        local_region['min'][i]=max(local_region['min'][i],p['region']['min'][i])
                        local_region['max'][i]=min(local_region['max'][i],p['region']['max'][i])
                    q={'authorised':True,'length':length,'fixture':{'position':pos,'travel_direction':d,'grade':grade,
                       'region':local_region,'template':p['track']['template'],'style':p['track']['style']}}
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
                       'track':p['track'],'region':p['region'],'vertical':{'max_grade':p['max_grade']},
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
                edges=value.get('edges',[])
                if value.get('groups'):
                    edge_ids=[i for group in value['groups'] for i in group['readback']['ordered_edges']]
                if edges and isinstance(edges[0],int):edge_ids=edges;edges=[]
                if edge_ids:
                    edges=inspect_edges(rc,edge_ids)
                # Follow the exact native replacement receipt, never proximity.
                placements=value.get('placements',[])
                placements=(placements if isinstance(placements,list) else [])+([value['placement']] if 'placement' in value else [])
                for placement in placements:
                    original=placement.get('original_edge');replacement=placement.get('replacement_edges',[])
                    if original and replacement:
                        changed=inspect_edges(rc,replacement)
                        for binding in list(state['steps'].values())+list(prior.values()):
                            old=binding.get('edges',[])
                            if any(e['id']==original for e in old):
                                binding.setdefault('original_edges',copy.deepcopy(old))
                                binding['edges']=[new for e in old for new in (changed if e['id']==original else [e])]
                        state.setdefault('lineage',[]).append({'request_id':r.get('request_id'),'original_edge':original,'replacement_edges':replacement})
                if prior:state['bindings']=prior
                invalidated=s.get('replace_chain') or (s.get('chain') if kind=='remove' else None)
                if invalidated:state.setdefault('invalidated_bindings',[]).append(invalidated)
                state['steps'][s['name']]={'status':'built','request_id':r.get('request_id',r.get('job_id')),
                                          'edges':edges}
                persist()
            state['status']='built';state['elapsed_seconds']=time.time()-state['started'];persist()
        except Exception as exc:
            state.update(status='needs_attention',error=str(exc)[:450],error_type=type(exc).__name__,elapsed_seconds=time.time()-state['started'])
            persist()
        return self.summary(run)

    def summary(self,run):
        state=json.loads((self.path(run)/'state.json').read_text())
        return {k:state[k] for k in ('status','session','current_step','error','calls','native_seconds','elapsed_seconds') if k in state} | {
            'run':run,'completed_steps':len(state['steps']),'evidence':str(self.path(run)/'state.json')}

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
            mutation=state.get('step_mutation')
            harmless=(mutation is not None and mutation.get('game_constructed') is False) or ('step_mutation' in state and mutation is None)
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


def render(plan,edges,path):
    """Equal-scale SVG of designer controls and observed native BaseEdge curves."""
    origin=plan['origin'];curves=list(plan.get('curves',{}).values())
    actual=[{k:[e[k][i]-(origin[i] if k in ('p0','p1') else 0) for i in range(3)] for k in ('p0','p1','t0','t1')} for e in edges]
    points=[c[k] for c in curves+actual for k in ('p0','p1')]+[v['position'] for v in plan['ports'].values()]
    lo=[min(p[i] for p in points) for i in range(2)];hi=[max(p[i] for p in points) for i in range(2)]
    scale=min(1100/max(hi[0]-lo[0],1),430/max(hi[1]-lo[1],1))
    def xy(p):return [80+(p[0]-lo[0])*scale,540-(p[1]-lo[1])*scale]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="650"><rect width="1280" height="650" fill="#f8fafc"/>',
         f'<text x="50" y="40" font-family="Arial" font-size="25">{html.escape(plan.get("title","Railway plan"))} — {html.escape(plan["revision"])}</text>',
         '<text x="50" y="72" font-family="Arial" font-size="16">Orange: recorded plan · navy: native geometry · equal scale</text>']
    for group,color,width in ((curves,'#f5a524',5),(actual,'#193950',2.2)):
        for c in group:
            ps=[c['p0'],[c['p0'][i]+c['t0'][i]/3 for i in range(3)],[c['p1'][i]-c['t1'][i]/3 for i in range(3)],c['p1']]
            a,b,d,e=[xy(v) for v in ps]
            svg.append(f'<path d="M {a[0]} {a[1]} C {b[0]} {b[1]} {d[0]} {d[1]} {e[0]} {e[1]}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    for name,p in plan['ports'].items():
        if not p.get('label'):continue
        x,y=xy(p['position']);svg.append(f'<text x="{x+6}" y="{y-7}" font-family="Arial" font-size="14">{html.escape(name)}</text>')
    svg.append('<text x="50" y="610" font-family="Arial" font-size="15">Centreline reconstruction; internal native turnout movement geometry and train operation are separate.</text></svg>')
    Path(path).write_text(''.join(svg),encoding='utf-8')

def render_profile(plan,edges,path):
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
    rows=[(name,sampled(c),color) for group,color in ((curves,'#f5a524'),(actual,'#193950')) for name,c in group]
    points=[p for _,ps,_ in rows for p in ps]
    if not points:points=[(0,origin[2]),(1,origin[2])]
    xmin,xmax=min(p[0] for p in points),max(p[0] for p in points);zmin,zmax=min(p[1] for p in points),max(p[1] for p in points)
    plot_height=330-18*len(plan.get('crossings',[]))
    scale=min(1080/max(xmax-xmin,1),plot_height/max((zmax-zmin)*exaggeration,1))
    def xy(x,z):return 100+(x-xmin)*scale,440-(z-zmin)*scale*exaggeration
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="560"><rect width="1280" height="560" fill="#f8fafc"/>',
         f'<text x="50" y="35" font-family="Arial" font-size="24">{html.escape(plan.get("title","Railway"))} — elevation profile</text>',
         f'<text x="50" y="65" font-family="Arial" font-size="16">Projected local axis {axis}; vertical exaggeration {exaggeration}×; orange intended, navy native</text>']
    for j in range(5):
        z=zmin+(zmax-zmin)*j/4;x,y=xy(xmin,z)
        svg.append(f'<path d="M 90 {y} L 1190 {y}" stroke="#d3dce4"/><text x="30" y="{y+5}" font-family="Arial" font-size="13">z {z:.2f}</text>')
    for name,ps,color in rows:
        coords=[xy(x,z) for x,z in ps];d=' '.join(('M' if i==0 else 'L')+f' {x:.3f} {y:.3f}' for i,(x,y) in enumerate(coords))
        svg.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"><title>{html.escape(name)}</title></path>')
    for index,crossing in enumerate(plan.get('crossings',[])):
        distance=sum(crossing['position'][i]*axis[i] for i in range(2))
        x,_=xy(distance,zmin)
        label=f'{crossing["name"]} at projected {distance:.2f}: planned upper z={crossing["upper_height"]+origin[2]:.2f}, lower z={crossing["lower_height"]+origin[2]:.2f}'
        svg.append(f'<path d="M {x} {140+18*index} L {x} 440" stroke="#ad8090" stroke-dasharray="4 4"/><text x="50" y="{92+18*index}" font-family="Arial" font-size="12">{html.escape(label)}</text>')
    svg.append(f'<text x="90" y="475" font-family="Arial" font-size="14">Projected distance {xmin:.2f}–{xmax:.2f}, native coordinate units; absolute z axis</text>')
    svg.append('<text x="50" y="520" font-family="Arial" font-size="14">Centreline profiles only; projected height difference is not structure/clearance certification.</text></svg>')
    Path(path).write_text(''.join(svg),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','survey','plan','execute','summary','review','continue','camera','capture','save'])
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
        else:r=op.gui(a.action,**data)
    except Exception as exc:r={'status':'error','error':str(exc)[:500]}
    print(json.dumps(r,separators=(',',':')))
    return 0 if r['status'] in ('ok','planned','built','reviewed') else 1


if __name__=='__main__':raise SystemExit(main())
