"""Authored corridor sections over existing operator primitives; no route designer."""
import copy
import json
import math
import re
import uuid

import bridge_live as live


def compile_corridor(brief):
    from bridge_operator import validate_plan, validate_structures, validate_group_offsets, validate_seed_track, vector, unit, in_region
    required={'version','revision','session','track','max_grade','stub_length','waypoints','sections'}
    if not required<=brief.keys() or brief.keys()-required-{'bindings','roads','track_by_road'}:raise ValueError('explicit corridor brief fields required')
    if brief['version']!=1 or not isinstance(brief['revision'],str) or not brief['revision'] or not isinstance(brief['session'],str) or not brief['session']:raise ValueError('corridor version1, revision and surveyed session required')
    length=brief['stub_length']
    if type(length) not in (int,float) or not math.isfinite(length) or not 5<=length<=60:raise ValueError('corridor stub_length must be5..60')
    waypoints=brief['waypoints'];sections=brief['sections'];bindings=copy.deepcopy(brief.get('bindings',{}))
    if not isinstance(waypoints,dict) or not 2<=len(waypoints)<=129 or not isinstance(sections,list) or not 1<=len(sections)<=128:raise ValueError('bounded corridor requires2..129 waypoints and1..128 sections')
    known_roads={road for roads in waypoints.values() for road in roads}
    overrides=brief.get('track_by_road',{})
    if not isinstance(overrides,dict) or set(overrides)-known_roads:raise ValueError('track_by_road requires known authored road names')
    for value in overrides.values():validate_seed_track(value)
    selected_tracks={road:overrides.get(road,brief['track']) for road in known_roads}
    def simple(name):
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise ValueError('simple corridor names required')
    for name,roads in waypoints.items():
        simple(name)
        if not isinstance(roads,dict) or not 1<=len(roads)<=4:raise ValueError('waypoint requires1..4 authored track profiles')
        for road,profile in roads.items():
            simple(road)
            if {'position','direction','grade'}<=profile.keys() and not profile.keys()-{'position','direction','grade','seed_structure'}:
                vector(profile['position'],3);unit(profile['direction'])
                if type(profile['grade']) not in (int,float) or not math.isfinite(profile['grade']) or abs(profile['grade'])>min(brief['max_grade'],.04):raise ValueError('waypoint stub grade exceeds existing native/selected bound')
                if 'seed_structure' in profile:
                    seed=profile['seed_structure']
                    if not isinstance(seed,dict) or set(seed)!={'classification','resource_name'} or seed['classification']!='TUNNEL' or not isinstance(seed['resource_name'],str) or not seed['resource_name']:
                        raise ValueError('waypoint seed_structure requires explicit TUNNEL resource')
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
        validate_group_offsets(members)
        for member in members:
            if 'normal_offset_from' in member:
                reference=members[member['normal_offset_from']['group_index']-1]['track']
                if selected_tracks[member['track']]!=selected_tracks[reference]:raise ValueError('derived family requires matching selected track resources')
        boundaries=[]
        for member in members:
            if 'normal_offset_from' in member:
                selector=member['normal_offset_from'];ends=boundaries[selector['group_index']-1]
                boundaries.append(tuple(reversed(ends)) if selector['reverse'] else ends)
            else:
                validate_structures(member)
                spans=member.get('structures',[{'classification':'NORMAL'}]*(len(member.get('guides',[]))+1))
                first=spans[0].get('spans',[spans[0]])[0]
                last=spans[-1].get('spans',[spans[-1]])[-1]
                boundaries.append(tuple({k:v[k] for k in ('classification','resource_name') if k in v} for v in (first,last)))
        boundary_by_road=dict(zip(roads,boundaries))
        p={'version':2,'revision':f"{brief['revision']}_{section['name']}",'origin':[0,0,0],
           'region':copy.deepcopy(section['region']),'ports':{},'track':copy.deepcopy(brief['track']),
           'max_grade':brief['max_grade'],'max_route_length':8000,'steps':[],'routes':[],'curves':{},'port_refs':{}}
        needed=set();created=[];groups=[]
        def endpoint(waypoint,road,side):
            if road not in waypoints[waypoint]:raise ValueError('section track missing from waypoint')
            profile=waypoints[waypoint][road];port=f'{side}_{len(p["port_refs"])}'
            if 'position' in profile:
                seed_structure=profile.get('seed_structure')
                if seed_structure is not None and boundary_by_road[road][0 if waypoint==source else 1]!=seed_structure:
                    raise ValueError('waypoint TUNNEL seed must match every adjoining section boundary structure/resource')
                key=(waypoint,road);binding=f'corr_seed_{list(waypoints).index(waypoint)}_{road}'
                direction=unit(profile['direction']);grade=profile['grade'];half=length/2
                back=[profile['position'][i]-half*(direction[i] if i<2 else grade) for i in range(3)]
                front=[profile['position'][i]+half*(direction[i] if i<2 else grade) for i in range(3)]
                if not all(in_region(pos,p['region']) for pos in (back,front)):raise ValueError('entire waypoint stub must lie inside section region')
                if key not in seeded:
                    seed_port=f'seed_origin_{len(created)}';p['ports'][seed_port]={'position':back,'direction':[-x for x in direction],'grade':-grade}
                    if seed_structure is None:
                        p['steps'].append({'name':binding,'kind':'stub','port':seed_port,'direction':direction,'grade':grade,'length':length})
                    else:
                        end_port=f'seed_end_{len(created)}';p['ports'][end_port]={'position':front,'direction':direction,'grade':grade}
                        p['steps'].append({'name':binding,'kind':'structure_seed','source':seed_port,'target':end_port,'structure':copy.deepcopy(seed_structure)})
                    if selected_tracks[road]!=brief['track']:p['steps'][-1]['track']=copy.deepcopy(selected_tracks[road])
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
                if any(rows[0].get(k)!=selected_tracks[road].get(k) for k in ('template','style')):
                    raise ValueError('imported waypoint track resources differ from selected road resources')
                e=rows[0];at_end=ref['node_id']==e['node1'];tangent=e['t1' if at_end else 't0'];sign=1 if at_end else -1
                horizontal=math.hypot(*tangent[:2])
                if not horizontal:raise ValueError('existing endpoint tangent unavailable')
                p['ports'][port]={'position':e['p1' if at_end else 'p0'],'direction':[sign*x/horizontal for x in tangent[:2]],'grade':sign*tangent[2]/horizontal}
                p['port_refs'][port]=copy.deepcopy(ref);needed.add(ref['chain'])
            return port
        for member in members:
            allowed={'track','guides','structures','representation','leg_representations','radius','fit_radius','handle_scale','normal_offset_from'}
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
        member_minimum=[]
        for group in groups:
            points=[p['ports'][group['source']]['position']]+[g['position'] for g in group.get('guides',[])]+[p['ports'][group['target']]['position']]
            if any(not 0<math.dist(a,b)<=800 for a,b in zip(points,points[1:])):raise ValueError('authored corridor leg must be nonzero and within native800 bound')
            count=(member_minimum[group['normal_offset_from']['group_index']-1] if 'normal_offset_from' in group
                   else sum(len(s.get('spans',[s])) for s in group.get('structures',[{}]*(len(points)-1))))
            member_minimum.append(count);minimum_segments+=count
        if minimum_segments>20:raise ValueError('authored corridor requires more than native20 grouped segments')
        templates.append({'name':section['name'],'plan':p,'required_bindings':sorted(needed),'created_bindings':created})
    if 'roads' in brief:validate_roads(brief,brief['roads'])
    return {'brief':copy.deepcopy(brief),'sections':templates,'initial_bindings':bindings}


def validate_roads(brief,roads):
    if not isinstance(roads,list) or not 1<=len(roads)<=4:raise ValueError('completion requires1..4 authored roads')
    names=set();tracks=set();sections={s['name']:s for s in brief['sections']}
    for road in roads:
        required={'name','track','sections','forward','spacing','start_offset','end_clearance','max_count','seed_id','max_route_length','checks'}
        if not isinstance(road,dict) or set(road)!=required:raise ValueError('explicit completion road fields required')
        if not isinstance(road['name'],str) or not re.fullmatch(r'[A-Za-z0-9_-]+',road['name']) or road['name'] in names or road['track'] in tracks:raise ValueError('distinct road names and physical tracks required')
        names.add(road['name']);tracks.add(road['track'])
        selected=road['sections']
        if not isinstance(selected,list) or not selected or len(selected)!=len(set(selected)) or any(n not in sections for n in selected):raise ValueError('exact ordered road sections required')
        indices=[list(sections).index(n) for n in selected]
        if indices!=list(range(indices[0],indices[0]+len(indices))):raise ValueError('road sections must be contiguous and ordered')
        if any(road['track'] not in [m['track'] for m in sections[n]['members']] for n in selected):raise ValueError('road track missing from section')
        if type(road['forward']) is not bool:raise ValueError('explicit road travel direction required')
        for key in ('spacing','start_offset','end_clearance','max_route_length'):
            v=road[key]
            if type(v) not in (int,float) or not math.isfinite(v) or v<0 or (key!='end_clearance' and v==0):raise ValueError('invalid road '+key)
        if road['max_route_length']>8000 or type(road['max_count']) is not int or not 1<=road['max_count']<=64 or type(road['seed_id']) is not int or road['seed_id']<=0:raise ValueError('existing road observation/placement bounds required')
        if not isinstance(road['checks'],list) or not road['checks'] or len(set(road['checks']))!=len(road['checks']) or any(c not in ('forward','reverse_blocked') for c in road['checks']):raise ValueError('explicit directed road checks required')


def ordered_path(rows,start,end):
    """Recover exact receipt topology independently of position and receipt order."""
    bynode={};seen=set();out=[];current=start
    for row in rows:
        for node in (row['node0'],row['node1']):bynode.setdefault(node,[]).append(row)
    while current!=end:
        choices=[r for r in bynode.get(current,[]) if r['id'] not in seen]
        if len(choices)!=1:raise ValueError('exact receipt chain is disconnected or ambiguous')
        row=choices[0];seen.add(row['id']);out.append(row)
        current=row['node1'] if current==row['node0'] else row['node0']
        if len(out)>64:raise ValueError('receipt chain bound exceeded')
    if not out:raise ValueError('empty receipt chain')
    return out


def recover_road(operator,compiled,state,road):
    brief=compiled['brief'];sections={s['name']:s for s in brief['sections']};runs={r['name']:r['run'] for r in state['section_runs']}
    def stub(waypoint,side):
        profile=brief['waypoints'][waypoint][road['track']]
        if 'position' in profile:
            rows=state['bindings'][f"corr_seed_{list(brief['waypoints']).index(waypoint)}_{road['track']}"]['edges']
            if len(rows)!=1:raise ValueError('exact single waypoint receipt required')
            row=rows[0];return row,row['node1' if side=='front' else 'node0']
        ref=profile[side];rows=[e for e in state['bindings'][ref['chain']]['edges'] if e['id']==ref['edge_id']]
        if len(rows)!=1:raise ValueError('exact authored waypoint receipt missing')
        return rows[0],ref['node_id']
    rows=[];envelopes=[]
    for name in road['sections']:
        section=sections[name];a,start=stub(section['source'],'front');b,end=stub(section['target'],'back')
        child=json.loads((operator.path(runs[name])/'state.json').read_text())
        if child['status']!='built':raise ValueError('completed section receipt required')
        if not rows:rows.append(a)
        elif rows[-1]['id']!=a['id']:raise ValueError('authored road changes attachment track')
        rows.extend(ordered_path(child['steps']['section_connect']['edges'],start,end));rows.append(b)
        envelopes.append(copy.deepcopy(section['region']))
    return rows,envelopes


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
    result={k:state[k] for k in ('status','session','section_index','current_run','error') if k in state}|{
        'run':run,'completed_sections':state['section_index'],'sections':len(compiled['sections']),
        'evidence':str(operator.path(run)/'state.json')}
    if 'completion' in state:
        c=state['completion'];result['completion']={'status':c['status'],'phase':c.get('phase'),'road':c.get('road'),
            'signals':sum(len(v.get('placements',[])) for v in c['roads'].values()),
            'checks':sum(len(v.get('checks',{})) for v in c['roads'].values()),'error':c.get('error')}
        if c['status']=='needs_attention':result['status']='needs_attention'
    return result


def attach_completion(operator,run,roads):
    """Author completion on an existing built corridor without reconstructing it."""
    from bridge_operator import digest
    folder=operator.path(run);compiled=json.loads((folder/'corridor.json').read_text());state=json.loads((folder/'state.json').read_text())
    if state.get('kind')!='corridor' or state['plan_hash']!=digest(compiled) or state['status']!='built':raise ValueError('unchanged built corridor required')
    validate_roads(compiled['brief'],roads)
    if (operator.runs/'execution.lock').exists():raise ValueError('operator run is already executing')
    path=folder/'completion.json';plan={'corridor_hash':state['plan_hash'],'roads':copy.deepcopy(roads)}
    if path.exists():
        if json.loads(path.read_text())!=plan:raise ValueError('authored completion scope changed')
    else:live.atomic_json(path,plan)
    if 'completion' not in state:
        state['completion']={'status':'planned','plan_hash':digest(plan),'roads':{r['name']:{'status':'planned','chunk_index':0,'placements':[],'checks':{}} for r in roads}}
        live.atomic_json(folder/'state.json',state)
    return corridor_status(operator,run)


def complete_corridor(operator,run,*,phase='all',continuing=False,road=None):
    from bridge_operator import digest, fresh_binding, signal_chain_locations, signal_batch_chunks, cubic, in_region
    if phase not in ('all','signal','qualify'):raise ValueError('unknown completion phase')
    folder=operator.path(run);compiled=json.loads((folder/'corridor.json').read_text());state=json.loads((folder/'state.json').read_text());plan=json.loads((folder/'completion.json').read_text())
    c=state.get('completion')
    if state.get('kind')!='corridor' or state['status']!='built' or state['plan_hash']!=digest(compiled) or not c or c['plan_hash']!=digest(plan) or plan['corridor_hash']!=state['plan_hash']:raise ValueError('completion/corridor scope changed or construction incomplete')
    if road is not None and road not in c['roads']:raise ValueError('unknown authored completion road')
    if c['status'] in ('running','needs_attention') and not continuing:raise ValueError('completion already attempted; explicit reconciliation/continuation required')
    lock=operator.runs/'execution.lock'
    with lock.open('x'):pass
    def persist():live.atomic_json(folder/'state.json',state)
    try:
        client=operator.client()
        def require_reconciled():
            journal=getattr(client,'journal',None)
            if journal and journal.exists() and json.loads(journal.read_text()).get('pending'):raise ValueError('unresolved native request requires reconciliation')
        require_reconciled()
        if client.session!=state['session']:raise ValueError('session changed; reacquire exact corridor identities')
        selected=[r for r in plan['roads'] if road is None or r['name']==road]
        if c.get('current_child'):
            pending=json.loads((operator.path(c['current_child'])/'state.json').read_text());owner=pending.get('road')
            if pending.get('parent')!=run or owner not in c['roads'] or pending.get('chunk')!=c['roads'][owner]['chunk_index']:raise ValueError('pending child ownership does not match completion')
            if phase=='qualify' or owner not in [r['name'] for r in selected]:raise ValueError('current chunk must be reconciled/consumed before changing completion phase or road')
            selected.sort(key=lambda r:r['name']!=owner)
        c['status']='running';c.pop('error',None);persist()
        for spec in selected:
            name=spec['name'];progress=c['roads'][name];c['road']=name
            if phase in ('all','signal') and progress['status'] not in ('signalled','verified'):
                c['phase']='signal';persist()
                if progress['status']=='planned':
                    rows,envelopes=recover_road(operator,compiled,state,spec)
                    rows=fresh_binding(client,{'edges':rows})
                    locations,length=signal_chain_locations(rows,spec['forward'],spec['spacing'],spec['start_offset'],spec['end_clearance'],spec['max_count'])
                    for loc in locations:
                        pos=cubic(rows[loc['edge_index']],loc['parameter'])[0]
                        if not any(in_region(pos,envelope) for envelope in envelopes):raise ValueError('signal outside authorised section-envelope union')
                    chunks=signal_batch_chunks(rows,locations,spec['seed_id'])
                    progress.update(status='signalling',edges=rows,envelopes=envelopes,locations=locations,chunks=chunks,sampled_length=length,chain_checked=False);persist()
                if not progress['chain_checked']:
                    rows=progress['edges'];current=rows[0]['node0']
                    if len(rows)>1:
                        shared={rows[0]['node0'],rows[0]['node1']}&{rows[1]['node0'],rows[1]['node1']}
                        current=next(n for n in (rows[0]['node0'],rows[0]['node1']) if n not in shared)
                    for first in range(0,len(rows),16):
                        subset=rows[first:first+16];q={'edges':subset,'start_node':current}
                        if first:q['before_edge']=rows[first-1]['id']
                        if first+16<len(rows):q['after_edge']=rows[first+16]['id']
                        r=client.request('operating_inspect',{'signal_chain_check':live._signal_batch_input(q)})
                        if r['status']!='ok' or r.get('result',{}).get('signal_chain_check',{}).get('checked') is not True:raise live.LiveError(r['status'],'road is not a confirmed ordinary chain',r.get('request_id'))
                        for row in subset:current=row['node1'] if current==row['node0'] else row['node0']
                    progress['chain_checked']=True;persist()
                while progress['chunk_index']<len(progress['chunks']):
                    if client.session!=state['session']:raise ValueError('session changed during completion')
                    chunk=progress['chunks'][progress['chunk_index']];rows=progress['edges'];child=c.get('current_child')
                    brief=copy.deepcopy(chunk['brief']);brief['edges']=rows[chunk['first']:chunk['last']+1]
                    brief['placements']=[q|{'edge_id':rows[loc['edge_index']]['id']} for q,loc in zip(brief['placements'],chunk['locations'])]
                    if chunk['first']:brief['before_edge']=rows[chunk['first']-1]['id']
                    if chunk['last']+1<len(rows):brief['after_edge']=rows[chunk['last']+1]['id']
                    if child is None:
                        child=uuid.uuid4().hex[:16];operator.path(child).mkdir()
                        live.atomic_json(operator.path(child)/'state.json',{'kind':'corridor_signal_chunk','parent':run,'road':name,'chunk':progress['chunk_index'],'status':'planned','brief':brief})
                        c['current_child']=child;persist()
                    child_path=operator.path(child)/'state.json';record=json.loads(child_path.read_text())
                    if record.get('parent')!=run or record.get('road')!=name or record.get('chunk')!=progress['chunk_index'] or record.get('brief')!=brief:raise ValueError('completion child does not match current road/chunk/scope')
                    if record['status']=='planned':
                        record['status']='attempted';live.atomic_json(child_path,record)
                        r=live.place_signal_batch(client,record['brief'],execute=True)
                        record.update(status='built' if r['status']=='ok' else 'needs_attention',response=r);live.atomic_json(child_path,record)
                    if record['status']!='built':raise ValueError('unknown/failed chunk requires reconciliation; never replay')
                    r=record['response'];value=r['result'];changed=live.signal_batch_replacements(record['brief'],value)
                    require_reconciled()
                    progress['placements'].extend(loc|q|{'request_id':r['request_id']} for loc,q in zip(chunk['locations'],value['placements']))
                    progress['edges']=[changed.get(e['id'],e) for e in rows]
                    for binding in state['bindings'].values():binding['edges']=[changed.get(e['id'],e) for e in binding['edges']]
                    progress['chunk_index']+=1;progress.setdefault('children',[]).append(child);c.pop('current_child',None);persist()
                progress['status']='signalled';persist()
            if phase in ('all','qualify'):
                require_reconciled()
                if progress['status'] not in ('signalled','verified'):raise ValueError('road completion must precede directed qualification')
                c['phase']='qualify';persist();rows=progress['edges'];first,last=rows[0],rows[-1]
                start={'edge':first['id'],'node':first['node0']};end={'edge':last['id'],'node':last['node1']}
                # Recover travel endpoints from exact ordered chain, not base-edge orientation.
                if len(rows)>1:
                    start['node']=next(n for n in (first['node0'],first['node1']) if n not in (rows[1]['node0'],rows[1]['node1']))
                    end['node']=next(n for n in (last['node0'],last['node1']) if n not in (rows[-2]['node0'],rows[-2]['node1']))
                if not spec['forward']:start,end=end,start
                for check in spec['checks']:
                    if check in progress['checks']:continue
                    require_reconciled()
                    a,b=(end,start) if check=='reverse_blocked' else (start,end)
                    r=client.request('route',{'source_edge':a['edge'],'source_node':a['node'],'target_edge':b['edge'],'target_node':b['node'],'mode':'TRAIN','max_length':spec['max_route_length'],'required_edges':[a['edge'],b['edge']]})
                    value=r.get('result',{});good=(value.get('native_path_found') is False and value.get('reason')=='no_native_path_returned') if check=='reverse_blocked' else value.get('requested_route_verified') is True
                    if r['status']!='ok' or not good:raise ValueError('explicit directed road acceptance failed: '+name+' '+check)
                    require_reconciled()
                    progress['checks'][check]={'request_id':r.get('request_id'),'verified':True};persist()
                progress['status']='verified';persist()
        c['status']='completed' if all(v['status']=='verified' for v in c['roads'].values()) else 'ready';persist()
    except Exception as exc:
        c.update(status='needs_attention',error=str(exc)[:400]);persist()
    finally:lock.unlink()
    return corridor_status(operator,run)


def build_corridor(operator,run,*,continuing=False,section_run=None):
    from bridge_operator import digest
    folder=operator.path(run);compiled=json.loads((folder/'corridor.json').read_text());state=json.loads((folder/'state.json').read_text())
    if state.get('kind')!='corridor' or state['plan_hash']!=digest(compiled):raise ValueError('corridor plan changed or wrong run')
    if continuing and state['status']=='built' and 'completion' in state:
        if section_run:raise ValueError('construction is complete; no replacement section permitted')
        return complete_corridor(operator,run,continuing=True)
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
    if state['status']=='built' and compiled['brief'].get('roads'):
        attach_completion(operator,run,compiled['brief']['roads'])
        return complete_corridor(operator,run,continuing=continuing)
    return corridor_status(operator,run)
