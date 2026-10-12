"""Authored corridor sections over existing operator primitives; no route designer."""
import copy
import json
import math
import re
import uuid

import bridge_live as live


def compile_corridor(brief):
    from bridge_operator import validate_plan, vector, unit, in_region
    required={'version','revision','session','track','max_grade','stub_length','waypoints','sections'}
    if not required<=brief.keys() or brief.keys()-required-{'bindings'}:raise ValueError('explicit corridor brief fields required')
    if brief['version']!=1 or not isinstance(brief['revision'],str) or not brief['revision'] or not isinstance(brief['session'],str) or not brief['session']:raise ValueError('corridor version1, revision and surveyed session required')
    length=brief['stub_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 5<=length<=60:raise ValueError('corridor stub_length must be5..60')
    waypoints=brief['waypoints'];sections=brief['sections'];bindings=copy.deepcopy(brief.get('bindings',{}))
    if not isinstance(waypoints,dict) or not 2<=len(waypoints)<=129 or not isinstance(sections,list) or not 1<=len(sections)<=128:raise ValueError('bounded corridor requires2..129 waypoints and1..128 sections')
    def simple(name):
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise ValueError('simple corridor names required')
    for name,roads in waypoints.items():
        simple(name)
        if not isinstance(roads,dict) or not 1<=len(roads)<=4:raise ValueError('waypoint requires1..4 authored track profiles')
        for road,profile in roads.items():
            simple(road)
            if set(profile)=={'position','direction','grade'}:
                vector(profile['position'],3);unit(profile['direction'])
                if type(profile['grade']) not in (int,float) or not math.isfinite(profile['grade']) or abs(profile['grade'])>min(brief['max_grade'],.04):raise ValueError('waypoint stub grade exceeds existing native/selected bound')
            elif not set(profile)<= {'back','front'} or not profile:raise ValueError('waypoint needs an authored profile or exact back/front endpoints')
    for name in bindings:
        simple(name)
        if name.startswith('corr_seed_'):raise ValueError('corr_seed_ binding names are reserved')
    seeded=set();templates=[];section_names=set();previous=None
    for index,section in enumerate(sections):
        if set(section)!={'name','source','target','region','members'}:raise ValueError('explicit corridor section fields required')
        simple(section['name'])
        if section['name'] in section_names:raise ValueError('unique section names required')
        section_names.add(section['name'])
        source,target=section['source'],section['target']
        if source not in waypoints or target not in waypoints or source==target or (previous is not None and source!=previous):raise ValueError('sections must follow the authored waypoint order')
        previous=target;members=section['members']
        if not isinstance(members,list) or len(members) not in (2,4):raise ValueError('corridor section requires2 or4 track members')
        roads=[member['track'] for member in members]
        if len(set(roads))!=len(roads):raise ValueError('distinct authored tracks required per section')
        p={'version':2,'revision':f"{brief['revision']}_{section['name']}",'origin':[0,0,0],
           'region':copy.deepcopy(section['region']),'ports':{},'track':copy.deepcopy(brief['track']),
           'max_grade':brief['max_grade'],'max_route_length':8000,'steps':[],'routes':[],'curves':{},'port_refs':{}}
        needed=set();created=[];groups=[]
        def endpoint(waypoint,road,side):
            if road not in waypoints[waypoint]:raise ValueError('section track missing from waypoint')
            profile=waypoints[waypoint][road];port=f'{side}_{len(p["port_refs"])}'
            if 'position' in profile:
                key=(waypoint,road);binding=f'corr_seed_{list(waypoints).index(waypoint)}_{road}'
                direction=unit(profile['direction']);grade=profile['grade'];half=length/2
                back=[profile['position'][i]-half*(direction[i] if i<2 else grade) for i in range(3)]
                front=[profile['position'][i]+half*(direction[i] if i<2 else grade) for i in range(3)]
                if not all(in_region(pos,p['region']) for pos in (back,front)):raise ValueError('entire waypoint stub must lie inside section region')
                if key not in seeded:
                    seed_port=f'seed_origin_{len(created)}';p['ports'][seed_port]={'position':back,'direction':[-x for x in direction],'grade':-grade}
                    p['steps'].append({'name':binding,'kind':'stub','port':seed_port,'direction':direction,'grade':grade,'length':length})
                    seeded.add(key);created.append(binding)
                elif binding not in created:needed.add(binding)
                sign=1 if side=='front' else -1
                p['ports'][port]={'position':front if side=='front' else back,'direction':[sign*x for x in direction],'grade':sign*grade}
                p['port_refs'][port]={'chain':binding,'end':'node1' if side=='front' else 'node0'}
            else:
                ref=profile.get(side)
                if not isinstance(ref,dict) or set(ref)!={'chain','edge_id','node_id'}:raise ValueError('existing waypoint requires exact chain/edge/node endpoint')
                if ref['chain'] not in bindings:raise ValueError('existing waypoint binding unavailable')
                rows=[e for e in bindings[ref['chain']]['edges'] if e['id']==ref['edge_id']]
                if len(rows)!=1 or ref['node_id'] not in (rows[0]['node0'],rows[0]['node1']):raise ValueError('existing waypoint endpoint identity unavailable')
                e=rows[0];at_end=ref['node_id']==e['node1'];tangent=e['t1' if at_end else 't0'];sign=1 if at_end else -1
                horizontal=math.hypot(*tangent[:2])
                if not horizontal:raise ValueError('existing endpoint tangent unavailable')
                p['ports'][port]={'position':e['p1' if at_end else 'p0'],'direction':[sign*x/horizontal for x in tangent[:2]],'grade':sign*tangent[2]/horizontal}
                p['port_refs'][port]=copy.deepcopy(ref);needed.add(ref['chain'])
            return port
        for member in members:
            allowed={'track','guides','structures','representation','leg_representations','radius','fit_radius','handle_scale'}
            if set(member)-allowed:raise ValueError('corridor member supports existing free structured-connect settings only')
            a=endpoint(source,member['track'],'front');b=endpoint(target,member['track'],'back')
            for guide in member.get('guides',[]):
                if type(guide.get('grade')) not in (int,float) or not math.isfinite(guide['grade']) or abs(guide['grade'])>brief['max_grade'] or not in_region(guide['position'],p['region']):raise ValueError('authored section guide violates selected grade/region')
            groups.append({'source':a,'target':b}|copy.deepcopy({k:v for k,v in member.items() if k!='track'}))
        p['steps'].append({'name':'section_connect','kind':'group','groups':groups})
        # Structural preflight only: reserved slots contain no invented native IDs.
        # The executable plan receives real exact bindings after prior receipts.
        shape=copy.deepcopy(p);shape['bindings']={name:bindings.get(name,{'edges':[{'unresolved_receipt':True}]}) for name in needed}
        validate_plan(shape)
        minimum_segments=0
        for group in groups:
            points=[p['ports'][group['source']]['position']]+[g['position'] for g in group.get('guides',[])]+[p['ports'][group['target']]['position']]
            if any(not 0<math.dist(a,b)<=800 for a,b in zip(points,points[1:])):raise ValueError('authored corridor leg must be nonzero and within native800 bound')
            minimum_segments+=sum(len(s.get('spans',[s])) for s in group.get('structures',[{}]*(len(points)-1)))
        if minimum_segments>20:raise ValueError('authored corridor requires more than native20 grouped segments')
        templates.append({'name':section['name'],'plan':p,'required_bindings':sorted(needed),'created_bindings':created})
    return {'brief':copy.deepcopy(brief),'sections':templates,'initial_bindings':bindings}


def plan_corridor(operator,brief):
    from bridge_operator import digest
    compiled=compile_corridor(brief);run=uuid.uuid4().hex[:16];folder=operator.path(run);folder.mkdir()
    live.atomic_json(folder/'corridor.json',compiled)
    live.atomic_json(folder/'state.json',{'kind':'corridor','status':'planned','plan_hash':digest(compiled),
        'session':brief['session'],'section_index':0,'section_runs':[],'bindings':compiled['initial_bindings']})
    return {'status':'planned','run':run,'sections':len(compiled['sections']),'evidence':str(folder/'corridor.json')}


def corridor_status(operator,run):
    state=json.loads((operator.path(run)/'state.json').read_text())
    if state.get('kind')!='corridor':raise ValueError('corridor run required')
    compiled=json.loads((operator.path(run)/'corridor.json').read_text())
    return {k:state[k] for k in ('status','session','section_index','current_run','error') if k in state}|{
        'run':run,'completed_sections':state['section_index'],'sections':len(compiled['sections']),
        'evidence':str(operator.path(run)/'state.json')}


def build_corridor(operator,run,*,continuing=False,section_run=None):
    from bridge_operator import digest
    folder=operator.path(run);compiled=json.loads((folder/'corridor.json').read_text());state=json.loads((folder/'state.json').read_text())
    if state.get('kind')!='corridor' or state['plan_hash']!=digest(compiled):raise ValueError('corridor plan changed or wrong run')
    if state['status']!='planned' and not(continuing and state['status'] in ('running','needs_attention')):raise ValueError('corridor already attempted; inspect or explicitly continue without replay')
    if section_run and not continuing:raise ValueError('section continuation requires continue_corridor')
    if operator.client().session!=state['session']:raise ValueError('session changed; survey and publish fresh corridor bindings')
    lock=operator.runs/'execution.lock'
    try:
        with lock.open('x'):pass
    except FileExistsError:raise ValueError('operator run is already executing')
    def persist():live.atomic_json(folder/'state.json',state)
    try:
        state.update(status='running');state.pop('error',None);persist()
        while state['section_index']<len(compiled['sections']):
            if operator.client().session!=state['session']:raise ValueError('session changed during corridor; reacquire native identities before further effects')
            section=compiled['sections'][state['section_index']]
            child=state.get('current_run')
            if section_run:
                if not child:raise ValueError('no stopped section to continue')
                replacement=json.loads((operator.path(section_run)/'plan.json').read_text())
                if replacement.get('continuation',{}).get('run')!=child:raise ValueError('section_run must be an existing continuation of the stopped native plan')
                child=section_run;state['current_run']=child;section_run=None;persist()
            if child is None:
                p=copy.deepcopy(section['plan']);p['bindings']={name:state['bindings'][name] for name in section['required_bindings']}
                child=operator.plan(p)['run'];state['current_run']=child;persist()
            child_state=json.loads((operator.path(child)/'state.json').read_text())
            if child_state['status']=='planned':operator._execute(child);child_state=json.loads((operator.path(child)/'state.json').read_text())
            if child_state['status']!='built':
                raise ValueError('stopped section requires native-plan inspection/continuation; '+child_state.get('error',child_state['status']))
            for name in section['required_bindings']+section['created_bindings']:
                if name in child_state.get('invalidated_bindings',[]):raise ValueError('built section invalidated exact waypoint binding '+name)
                binding=child_state['steps'].get(name) or child_state.get('bindings',{}).get(name)
                if binding and binding.get('edges'):state['bindings'][name]={'edges':binding['edges']}
                elif name in section['created_bindings']:raise ValueError('built section missing exact waypoint receipt')
            state['section_runs'].append({'name':section['name'],'run':child});state['section_index']+=1;state.pop('current_run',None);persist()
        state['status']='built';persist()
    except Exception as exc:
        state.update(status='needs_attention',error=str(exc)[:500]);persist()
    finally:lock.unlink()
    return corridor_status(operator,run)
