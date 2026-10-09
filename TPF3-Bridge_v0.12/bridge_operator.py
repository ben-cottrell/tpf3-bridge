"""Named, plan-driven live operations. CLI and MCP share this implementation.

Plans are design data, never executable Python/Lua. Native operations and their
durable request receipts remain owned by bridge_live. A failed step is not replayed.
"""
from __future__ import annotations
import argparse
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


def validate_plan(p):
    if p.get('version') != 1 or not isinstance(p.get('revision'), str):
        raise ValueError('version1 and design revision required')
    vector(p['origin'], 3)
    if not isinstance(p['ports'], dict) or not p['ports']:
        raise ValueError('named ports required')
    for port in p['ports'].values():
        vector(port['position'], 3); unit(port['direction'])
    region = p['region']
    vector(region['min'],3); vector(region['max'],3)
    if any(a >= b for a,b in zip(region['min'], region['max'])):
        raise ValueError('ordered region required')
    for port in p['ports'].values():
        if any(not region['min'][i] <= port['position'][i]+p['origin'][i] <= region['max'][i] for i in range(3)):
            raise ValueError('port outside construction region')
    if not isinstance(p['steps'],list) or not p['steps']:
        raise ValueError('construction steps required')
    names=set()
    def ref(r):
        if isinstance(r,str):
            if r not in p['ports']:raise ValueError('unknown port '+r)
        elif isinstance(r,dict) and set(r)=={'curve','u'}:
            if r['curve'] not in names or type(r['u']) not in (int,float) or not .05<=r['u']<=.95:
                raise ValueError('curve reference must refer to an earlier step at an interior parameter')
        else:raise ValueError('named port or earlier curve reference required')
    for s in p['steps']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s['name']) or s['name'] in names:
            raise ValueError('unique simple step names required')
        kind=s['kind']
        if kind not in ('stub','extend','connect','branch','crossover'):raise ValueError('unsupported construction step')
        if kind=='stub':
            ref(s['port'])
            if not isinstance(s['port'],str):raise ValueError('stub requires a named port')
            if 'direction' in s:unit(s['direction'])
            if not 5<=s['length']<=60:raise ValueError('native fixture length5..60 required')
        else:
            ref(s['source']);ref(s['target'])
        names.add(s['name'])
        for g in s.get('guides',[]):
            vector(g['position'],3);unit(g['travel_direction'])
            if type(g.get('grade')) not in (int,float) or not math.isfinite(g['grade']):raise ValueError('finite guide grade required')
    if len(p['steps'])>32:raise ValueError('at most32 steps per plan')
    if any(region['max'][i]-region['min'][i]>400 for i in range(2)):
        raise ValueError('operator region limited to400 per horizontal axis')
    if type(p.get('max_grade')) not in (int,float) or not 0 < p['max_grade'] <= 1:raise ValueError('explicit positive grade bound required')
    if not 0 < p.get('max_route_length',800) <= 800:raise ValueError('route length bound within(0,800] required')
    if not isinstance(p.get('track'),dict) or any(not isinstance(p['track'].get(k),str) or not p['track'][k] for k in ('template','style')):
        raise ValueError('named native track template and style required')
    for r in p['routes']:
        ref(r['source']);ref(r['target'])
        if not all(isinstance(r[k],str) for k in ('name','source','target')):raise ValueError('route endpoints must be named ports')
    for c in p.get('curves',{}).values():
        for k in ('p0','p1','t0','t1'):vector(c[k],3)
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
        return {'status':r['status'],'session':c.session,'capabilities':r.get('result'),
                'evidence':str(c.evidence/(r['request_id']+'.response.json'))}

    def survey(self, region, terrain_points=None):
        c=self.client();r=c.request('discover',{'region':region,'max_edges':16})
        z=r.get('result',{})
        out={'status':r['status'],'session':c.session,'complete':z.get('complete'),
             'edges':len(z.get('edges',[])),'evidence':str(c.evidence/(r['request_id']+'.response.json'))}
        if terrain_points:
            t=c.request('inspect',{'edge_ids':[],'site':{'region':region,'positions':terrain_points}})
            out['terrain']=t.get('result');out['terrain_status']=t['status']
        return out

    def plan(self, plan):
        p=validate_plan(plan);run=uuid.uuid4().hex[:16];folder=self.path(run);folder.mkdir()
        live.atomic_json(folder/'plan.json',p)
        live.atomic_json(folder/'state.json',{'status':'planned','plan_hash':digest(p),'steps':{},'calls':0,'native_seconds':0})
        render(p,[],folder/'plan.svg')
        return {'status':'planned','run':run,'revision':p['revision'],'steps':len(p['steps']),
                'plan':str(folder/'plan.json'),'view':str(folder/'plan.svg')}

    def execute(self, run):
        folder=self.path(run);lock=self.runs/'execution.lock'
        try:
            with lock.open('x'):pass
        except FileExistsError:raise ValueError('operator run is already executing; inspect its state')
        try:
            return self._execute(run)
        finally:lock.unlink()

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
            def request(_,op,params,**kwargs):
                start=time.monotonic();r=c.request(op,params,**kwargs)
                state['calls']+=1;state['native_seconds']+=time.monotonic()-start
                state['last_request']=r['request_id'];persist()
                if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r),r['request_id'])
                return r
        rc=Recorded()
        def world(port):return [port['position'][i]+p['origin'][i] for i in range(3)]
        def intent(ref):
            if isinstance(ref,str):
                port=p['ports'][ref];pos=world(port);direction=unit(port['direction'])
            else:
                rows=state['steps'][ref['curve']]['edges']
                if len(rows)!=1:raise ValueError('parameter reference needs a single native curve; use a named spatial port for a chain')
                pos,direction=cubic(rows[0],ref['u'])
            tolerance=p.get('placement_tolerance',.15)
            return {'region':box([pos],max(1,tolerance)),'max_edges':16,'guide_xyz':pos,
                    'travel_direction':direction,'heading_tolerance_deg':p.get('heading_tolerance_deg',2),
                    'placement_tolerance':tolerance}
        def resolve(ref,interior=False):
            loc=intent(ref)
            a,_=live._select_throat_port(rc,loc,interior=interior,tolerance=loc['placement_tolerance'])
            return a,loc
        try:
            for s in p['steps']:
                state['current_step']=s['name'];persist();kind=s['kind']
                if kind=='stub':
                    port=p['ports'][s['port']];pos=world(port);d=unit(s.get('direction',port['direction']));length=s['length']
                    end=[pos[i]+length*(d[i] if i<2 else 0) for i in range(3)]
                    local_region=box([pos,end])
                    for i in range(3):
                        local_region['min'][i]=max(local_region['min'][i],p['region']['min'][i])
                        local_region['max'][i]=min(local_region['max'][i],p['region']['max'][i])
                    q={'authorised':True,'length':length,'fixture':{'position':pos,'travel_direction':d,'grade':0,
                       'region':local_region,'template':p['track']['template'],'style':p['track']['style']}}
                    if any(not p['region']['min'][i]<=end[i]<=p['region']['max'][i] for i in range(3)):
                        raise ValueError('stub end outside authorised plan region')
                    r=rc.request('test_approach',q)
                else:
                    a,al=resolve(s['source'],kind in ('branch','crossover'))
                    if kind=='extend':
                        target=p['ports'][s['target']]
                        q={'anchor_edge':a['edge_id'],'anchor_node':a['node_id'],'end_xy':world(target)[:2],
                           'end_direction':unit(target['direction']),'radius':s.get('radius',1),'region':p['region'],
                           'vertical':{'end_height':world(target)[2],'end_grade':0,'max_grade':p['max_grade']}}
                        r=live.extend(rc,q,execute=True)
                    else:
                        b,bl=resolve(s['target'],kind=='crossover')
                        q={'source':a,'target':b,'region':p['region'],'vertical':{'max_grade':p['max_grade']}}
                        if kind=='connect':
                            guides=[g|{'position':[g['position'][i]+p['origin'][i] for i in range(3)]} for g in s.get('guides',[])]
                            q.update(new_alignment=True,guides=guides,structures=s.get('structures',[{'classification':'NORMAL'}]*(len(guides)+1)),
                                     representation='endpoint_cubic',radius=0,fit_radius=100,handle_scale=s.get('handle_scale',1),prepare=True)
                            prepared=rc.request('structured_chain',q)
                            r=rc.request('structured_chain',{'execute':True,'prepared_request':prepared['request_id']})
                        else:
                            q.update(location=al,max_route_length=p.get('max_route_length',800))
                            shapes=s.get('candidates',[{'branch':'endpoint_cubic_level','through':'subdivide'}])
                            if kind=='crossover':
                                q['target_location']=bl
                                prepared=live.prepare_crossover(rc,q,shapes)
                                r=live.build_prepared_crossover(rc,prepared)
                            else:
                                prepared=live.prepare_interior_junction(rc,q,shapes)
                                r=live.build_prepared_interior_junction(rc,prepared)
                value=r.get('result',r)
                if r['status']!='ok':raise live.LiveError(r['status'],native_failure(r))
                edge_ids=value.get('readback',{}).get('ordered_edges',[])
                edges=value.get('edges',[])
                if edges and isinstance(edges[0],int):edge_ids=edges;edges=[]
                if edge_ids:
                    edges=rc.request('inspect',{'edge_ids':edge_ids})['result']['edges']
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
        if state['status']!='built':raise ValueError('construction incomplete; inspect run status first')
        rows=[];ports={}
        # Route endpoints are the free outer boundaries, so their direction is outward.
        for route in p['routes']:
            for name in (route['source'],route['target']):
                if name in ports:continue
                port=p['ports'][name];pos=[port['position'][i]+p['origin'][i] for i in range(3)]
                loc={'region':box([pos],1),'max_edges':16,'guide_xyz':pos,'travel_direction':unit(port['direction']),'heading_tolerance_deg':2}
                ports[name],_=live._select_throat_port(c,loc,tolerance=.15)
            a,b=ports[route['source']],ports[route['target']]
            r=c.request('route',{'source_edge':a['edge_id'],'source_node':a['node_id'],'target_edge':b['edge_id'],
                                'target_node':b['node_id'],'mode':'TRAIN','max_length':p.get('max_route_length',800),
                                'required_edges':[a['edge_id'],b['edge_id']]})
            z=r.get('result',{});rows.append({'name':route['name'],'verified':r['status']=='ok' and z.get('requested_route_verified') is True,
                                            'length':z.get('total_path_length'),'request_id':r['request_id']})
        edges={};region=p['region'];x=region['min'][0]
        while x<region['max'][0]:
            r=c.request('discover',{'region':{'min':[x,*region['min'][1:]],'max':[min(x+100,region['max'][0]),*region['max'][1:]]},'max_edges':16})
            if r['status']!='ok' or not r['result'].get('complete'):raise ValueError('geometry survey incomplete; narrow report region')
            for e in r['result']['edges']:edges[e['id']]=e
            x+=100
        report={'session':c.session,'routes':rows,'edges':list(edges.values()),'all_routes_verified':bool(rows) and all(r['verified'] for r in rows),
                'physical_operation':'not tested','design_quality':'requires visual review'}
        live.atomic_json(folder/'review.json',report);render(p,list(edges.values()),folder/'overlay.svg')
        return {'status':'reviewed' if report['all_routes_verified'] else 'needs_attention','verified_routes':sum(r['verified'] for r in rows),'required_routes':len(rows),
                'view':str(folder/'overlay.svg'),'evidence':str(folder/'review.json')}

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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','survey','plan','execute','summary','review','camera','capture','save'])
    parser.add_argument('--input',type=Path);parser.add_argument('--run');parser.add_argument('--context',type=Path,default=CONTEXT)
    a=parser.parse_args()
    try:
        op=Operator(context=a.context)
        data=json.loads(a.input.read_text(encoding='utf-8-sig')) if a.input else {}
        if a.action in ('execute','summary','review'):r=getattr(op,a.action)(a.run)
        elif a.action=='plan':r=op.plan(data)
        elif a.action=='status':r=op.status()
        elif a.action=='survey':r=op.survey(**data)
        else:r=op.gui(a.action,**data)
    except Exception as exc:r={'status':'error','error':str(exc)[:500]}
    print(json.dumps(r,separators=(',',':')))
    return 0 if r['status'] in ('ok','planned','built','reviewed') else 1


if __name__=='__main__':raise SystemExit(main())
