"""Reusable bounded individual/bulk signal benchmark over the existing operator.

Dry-run is offline. Published runs execute once; interrupted/partial runs stop for
existing operation reconciliation. Site/resources are supplied by the coordinator.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import time
import uuid

import bridge_live as live
from bridge_corridor import compile_corridor, ordered_path, recover_road
from bridge_operator import CONTEXT, Operator, box, digest, signal_chain_locations, vector


ROADS=('up','down','fast_up','fast_down')


def fixtures(config):
    required={'version','session','origins','track','track_distance','seed_id'}
    if not isinstance(config,dict) or set(config)-{'rotation_degrees','parallel_family','production_completion'}!=required or config['version']!=1:
        raise ValueError('explicit benchmark version1 fields required')
    if type(config.get('parallel_family',False)) is not bool:raise ValueError('parallel_family must be boolean')
    if type(config.get('production_completion',False)) is not bool:raise ValueError('production_completion must be boolean')
    if not isinstance(config['session'],str) or not config['session'] or type(config['seed_id']) is not int or config['seed_id']<=0:
        raise ValueError('surveyed session and exact seed required')
    d=config['track_distance']
    if type(d) not in (int,float) or not math.isfinite(d) or not 0<d<=20:raise ValueError('native trackDistance required')
    origins=config['origins']
    if not isinstance(origins,list) or len(origins)!=2:raise ValueError('two separately authorised equivalent sites required')
    for origin in origins:vector(origin,3)
    angle=config.get('rotation_degrees',0)
    if type(angle) not in (int,float) or not math.isfinite(angle):raise ValueError('finite map rotation required')
    theta=math.radians(angle);cs,sn=math.cos(theta),math.sin(theta)
    local=[(0,0,0,0),(600,0,0,0),(1197,52,0,10),(1787.885,156.189,6,10)]
    output=[]
    for mode,origin in zip(('individual','batch'),origins):
        waypoints={}
        for index,(x,y,z,heading) in enumerate(local):
            directions=[math.cos(math.radians(heading)),math.sin(math.radians(heading))]
            profiles={}
            for road,multiplier in zip(ROADS,(-.5,.5,-1.5,1.5)):
                if index==0 and road.startswith('fast'):continue
                px=x-directions[1]*d*multiplier;py=y+directions[0]*d*multiplier
                profiles[road]={'position':[origin[0]+cs*px-sn*py,origin[1]+sn*px+cs*py,origin[2]+z],
                    'direction':[cs*directions[0]-sn*directions[1],sn*directions[0]+cs*directions[1]],'grade':0}
            waypoints['ABCD'[index]]=profiles
        sections=[]
        for i in range(3):
            source,target='ABCD'[i:i+2];members=ROADS[:2] if i==0 else ROADS
            points=[p['position'] for name in (source,target) for p in waypoints[name].values()]
            group=[{'track':r} for r in members]
            if config.get('parallel_family',False):
                group[0]['representation']='native_parts'
                multipliers=dict(zip(ROADS,(-.5,.5,-1.5,1.5)))
                for member in group[1:]:
                    member['normal_offset_from']={'group_index':1,
                        'spacing':d*(multipliers[member['track']]-multipliers[group[0]['track']]),'reverse':False}
            sections.append({'name':source+target,'source':source,'target':target,'region':box(points,30),'members':group})
        brief={'version':1,'revision':'signal_benchmark_'+mode,'session':config['session'],'track':copy.deepcopy(config['track']),
               'max_grade':.025,'stub_length':10,'waypoints':waypoints,'sections':sections}
        compile_corridor(brief);output.append((mode,brief))
    # Effect envelopes, not just origins, must be separate.
    envelopes=[box([p['position'] for roads in b['waypoints'].values() for p in roads.values()],30) for _,b in output]
    if all(max(envelopes[0]['min'][i],envelopes[1]['min'][i])<=min(envelopes[0]['max'][i],envelopes[1]['max'][i]) for i in range(2)):
        raise ValueError('benchmark fixture envelopes overlap')
    return output


def completion_roads(brief,seed_id):
    return [{'name':name,'track':name,'sections':[s['name'] for s in brief['sections'] if name in [m['track'] for m in s['members']]],
             'forward':name in ('up','fast_up'),'spacing':300,'start_offset':150,'end_clearance':150,
             'max_count':64,'seed_id':seed_id,'max_route_length':3000,'checks':['forward','reverse_blocked']} for name in ROADS]


def recover_roads(operator,corridor_run):
    state=json.loads((operator.path(corridor_run)/'state.json').read_text())
    if state['status']!='built':raise ValueError('completed corridor required')
    compiled=json.loads((operator.path(corridor_run)/'corridor.json').read_text())
    roads={}
    for road in ROADS:
        spec=next(r for r in completion_roads(compiled['brief'],1) if r['name']==road)
        rows,_=recover_road(operator,compiled,state,spec)
        # This existing sampler independently checks ordering/loops and count.
        forward=road in ('up','fast_up')
        targets,length=signal_chain_locations(rows,forward,300,150,150,64)
        roads[road]={'edges':rows,'forward':forward,'target_distances':[q['distance'] for q in targets],'sampled_length':length}
    return roads


class Counted:
    def __init__(self,client,counts=None):
        self.client=client;self.session=client.session;self.evidence=client.evidence;self.phase='preflight';self.counts=copy.deepcopy(counts or {})
        self.journal=getattr(client,'journal',None)
    def request(self,operation,params,**kwargs):
        entry=self.counts.setdefault(self.phase,{'requests':0,'mutations':0,'native_seconds':0})
        entry['requests']+=1;entry['mutations']+=int(live.is_mutation(operation,params));start=time.monotonic()
        try:return self.client.request(operation,params,**kwargs)
        finally:entry['native_seconds']+=time.monotonic()-start


def signal_windows(rows,forward,distances):
    """Partition actual edges within the existing1000 plan bound; carry global phase."""
    groups=[];first=0
    while first<len(rows):
        last=first
        while last+1<len(rows):
            candidate=rows[first:last+2];region=box([r[k] for r in candidate for k in ('p0','p1')],30)
            if len(candidate)>64 or any(region['max'][i]-region['min'][i]>1000 for i in range(2)):break
            last+=1
        selected=rows[first:last+1];region=box([r[k] for r in selected for k in ('p0','p1')],30)
        if any(region['max'][i]-region['min'][i]>1000 for i in range(2)):raise ValueError('native edge exceeds benchmark signal window')
        groups.append((first,last,region));first=last+1
    if not forward:groups.reverse()
    start=0;retained=0
    for first,last,region in groups:
        selected=rows[first:last+1]
        # Same sampler, zero possible placements: this only measures realised length.
        _,length=signal_chain_locations(selected,forward,1e12,1e12,0,1)
        local=[d-start for d in distances if start<d<start+length]
        if local:
            retained+=len(local)
            yield {'first':first,'last':last,'region':region,'start_distance':start,
                   'start_offset':local[0],'end_clearance':length-local[-1],'count':len(local)}
        start+=length
    if retained!=len(distances):raise ValueError('signal target at window boundary or outside measured chain')


def prepare(operator,config):
    plans=fixtures(config);run=uuid.uuid4().hex[:16];folder=operator.path(run);folder.mkdir()
    live.atomic_json(folder/'benchmark.json',config)
    live.atomic_json(folder/'state.json',{'kind':'signal_benchmark','status':'planned','next_phase':'build','input_hash':digest(config),'fixtures':[]})
    return {'status':'planned','run':run,'modes':[m for m,_ in plans],'game_constructed':False}


def inspect(operator,run):
    state=json.loads((operator.path(run)/'state.json').read_text())
    if state.get('kind')!='signal_benchmark':raise ValueError('signal benchmark run required')
    return {k:state[k] for k in ('status','next_phase','error','counts') if k in state}|{'run':run,
        'fixtures':[{k:v for k,v in r.items() if k not in ('targets','roads')} for r in state['fixtures']],
        'comparison':'equivalent authored intent; sampled targets from each actual native realisation'}


def execute(operator,run,phase='all'):
    folder=operator.path(run);config=json.loads((folder/'benchmark.json').read_text());state=json.loads((folder/'state.json').read_text())
    if state.get('kind')!='signal_benchmark' or state['input_hash']!=digest(config):raise ValueError('benchmark input changed')
    if state['status'] not in ('planned','ready'):raise ValueError('benchmark already attempted/interrupted; reconcile without replay')
    if phase!='all' and phase!=state['next_phase']:raise ValueError('benchmark phase out of order or already completed')
    lock=folder/'execution.lock'
    with lock.open('x'):pass
    def persist():live.atomic_json(folder/'state.json',state)
    counted=None
    try:
        current=json.loads((folder/'state.json').read_text())
        if current!=state:raise ValueError('benchmark state changed before execution')
        state['status']='running';persist();counted=Counted(operator.client(),state.get('counts'));worker=Operator(runs=operator.runs,client=counted)
        if counted.session!=config['session']:raise ValueError('session changed; fresh survey required')
        seed=counted.request('operating_inspect',{'signal_seed':{'seed_id':config['seed_id']}})
        if seed['status']!='ok':raise live.LiveError(seed['status'],'exact signal seed unavailable')
        source=seed['result']['signal_seed'];resource=counted.request('inspect',{'edge_ids':[source['edge']],'resources':True})
        observed=resource.get('result',{}).get('edges',[])
        if resource['status']!='ok' or len(observed)!=1 or observed[0]['resource']['track_distance']!=config['track_distance'] or any(observed[0][k]!=config['track'][k] for k in ('template','style')):
            raise ValueError('selected native track resource/spacing differs from benchmark brief')
        while state['next_phase']!='done':
            active=state['next_phase']
            for index,(mode,brief) in enumerate(fixtures(config)):
                if active=='build':
                    counted.phase=mode+'_build';record={'mode':mode};state['fixtures'].append(record);persist()
                    corridor=worker.plan_corridor(brief)['run'];record['corridor_run']=corridor;persist()
                    result=worker.build_corridor(corridor)
                    if result['status']!='built':raise ValueError('fixture build stopped: '+result.get('error',result['status']))
                    recover_roads(worker,corridor);record['status']='built';persist();continue
                record=state['fixtures'][index]
                if mode=='batch' and config.get('production_completion',False):
                    counted.phase=mode+('_signals' if active=='signal' else '_routes')
                    if active=='signal':worker.attach_corridor_completion(record['corridor_run'],completion_roads(brief,config['seed_id']))
                    result=worker.complete_corridor(record['corridor_run'],phase='signal' if active=='signal' else 'qualify')
                    if result['status']!='built' or result['completion']['status']=='needs_attention':raise ValueError('production completion stopped: '+str(result['completion']))
                    record.update(status='signalled' if active=='signal' else 'verified',signals=result['completion']['signals'],route_checks=result['completion']['checks']);persist();continue
                if active=='signal':
                    roads=recover_roads(worker,record['corridor_run'])
                    record['targets']={name:{k:v for k,v in road.items() if k!='edges'} for name,road in roads.items()};persist()
                    record['signal_runs']=[];record['signals']=0;counted.phase=mode+'_signals'
                    for name,road in roads.items():
                        for window in list(signal_windows(road['edges'],road['forward'],road['target_distances'])):
                            selected=road['edges'][window['first']:window['last']+1]
                            plan={'version':2,'revision':'benchmark_'+mode,'origin':[0,0,0],'region':window['region'],
                                  'ports':{'origin':{'position':selected[0]['p0'],'direction':[1,0]}},
                                  'track':config['track'],'max_grade':.025,'routes':[],'curves':{},'bindings':{'road':{'edges':selected}},
                                  'steps':[{'name':'blocks','kind':'signal_chain','chains':['road'],'forward':road['forward'],
                                   'spacing':300,'start_offset':window['start_offset'],'end_clearance':window['end_clearance'],
                                   'max_count':64,'seed_id':config['seed_id'],'placement_mode':mode}]}
                            child=worker.plan(plan)['run'];record['signal_runs'].append({'road':name,'run':child});persist()
                            result=worker.execute(child)
                            if result['status']!='built':raise ValueError('signal phase stopped: '+result.get('error',result['status']))
                            native=json.loads((worker.path(child)/'state.json').read_text())
                            road['edges'][window['first']:window['last']+1]=native['bindings']['road']['edges']
                            placements=native['signal_chains']['blocks']['placements']
                            if len(placements)!=window['count']:raise ValueError('signal window changed global target count')
                            record['signals']+=len(placements);record['roads']={r:road['edges'] for r,road in roads.items()};persist()
                    record['status']='signalled';persist();continue
                counted.phase=mode+'_routes';passed=0
                for name,target in record['targets'].items():
                    rows=record['roads'][name];a,b=rows[0],rows[-1]
                    start={'edge':a['id'],'node':a['node0']};end={'edge':b['id'],'node':b['node1']}
                    if not target['forward']:start,end=end,start
                    for reverse in (False,True):
                        x,y=(end,start) if reverse else (start,end)
                        q={'source_edge':x['edge'],'source_node':x['node'],'target_edge':y['edge'],'target_node':y['node'],
                           'mode':'TRAIN','max_length':3000,'required_edges':[x['edge'],y['edge']]}
                        r=counted.request('route',q);v=r.get('result',{})
                        good=v.get('native_path_found') is False and v.get('reason')=='no_native_path_returned' if reverse else v.get('requested_route_verified') is True
                        if r['status']!='ok' or not good:raise ValueError('directed route acceptance failed/unavailable: '+name)
                        passed+=1
                record.update(status='verified',route_checks=passed);persist()
            state.update(next_phase={'build':'signal','signal':'qualify','qualify':'done'}[active],counts=counted.counts)
            state['status']='completed' if state['next_phase']=='done' else 'ready';persist()
            if phase!='all':break
            if state['next_phase']!='done':state['status']='running';persist()
    except Exception as exc:
        state.update(status='needs_attention',error=str(exc)[:350],counts=counted.counts if counted else state.get('counts',{}));persist()
    finally:lock.unlink()
    return inspect(operator,run)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['dry-run','plan','prepare','inspect','build','signal','qualify','execute'])
    parser.add_argument('--input',type=Path);parser.add_argument('--run');parser.add_argument('--context',type=Path,default=CONTEXT)
    args=parser.parse_args()
    try:
        if args.action=='inspect':result=inspect(Operator(context=args.context),args.run)
        elif args.action in ('execute','build','signal','qualify'):result=execute(Operator(context=args.context),args.run,'all' if args.action=='execute' else args.action)
        else:
            config=json.loads(args.input.read_text(encoding='utf-8-sig'))
            plans=fixtures(config)
            result=({'status':'ok','native_calls':0,'fixtures':[{'mode':m,'sections':len(b['sections']),'origin':o} for (m,b),o in zip(plans,config['origins'])],
                     'limits':{'edges_per_batch':16,'placements_per_batch':64,'spacing':300,'start_offset':150,'end_clearance':150},'game_constructed':False}
                    if args.action=='dry-run' else prepare(Operator(context=args.context),config))
    except Exception as exc:result={'status':'error','error':str(exc)[:350]}
    print(json.dumps(result,separators=(',',':')))
    return 0 if result['status'] in ('ok','planned','ready','completed') else 1


if __name__=='__main__':raise SystemExit(main())
