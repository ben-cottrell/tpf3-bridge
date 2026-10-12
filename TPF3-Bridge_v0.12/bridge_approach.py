"""Bounded authored family composition over existing operator/corridor jobs."""
import copy
import json
import math
import uuid
from contextlib import contextmanager
from pathlib import Path

import bridge_live as live
from bridge_interfaces import simple_name


def load(path):return json.loads(path.read_text())


def guard(operator,state):
    client=operator.client()
    if client.session!=state['session']:raise ValueError('approach session changed; fresh inspection/design required')
    journal=getattr(client,'journal',None)
    if journal and journal.exists() and load(journal).get('pending'):raise ValueError('unresolved native request requires reconciliation')
    return client


def bounded_box(region):
    from bridge_operator import vector
    if set(region)!={'min','max'}:raise ValueError('explicit effect box required')
    vector(region['min'],3);vector(region['max'],3)
    if any(a>=b for a,b in zip(region['min'],region['max'])):raise ValueError('ordered effect envelope required')


def contained(region,envelopes):
    # Require one authorised box to contain each existing operation window.
    return any(all(e['min'][i]<=region['min'][i]<=region['max'][i]<=e['max'][i] for i in range(3)) for e in envelopes)


def compile_brief(brief):
    from bridge_operator import validate_plan,digest
    from bridge_corridor import compile_corridor
    required={'version','revision','session','station','interfaces','families','checks'}
    if set(brief)!=required or brief['version']!=1:raise ValueError('explicit version1 approach fields required')
    for k in ('revision','session'):
        if not isinstance(brief[k],str) or not 1<=len(brief[k])<=160:raise ValueError('bounded revision/session required')
    selector=brief['station']
    if set(selector)!={'name','construction'} or set(selector['construction'])!={'resource','position'}:raise ValueError('exact authored station selector required')
    if set(brief['interfaces'])-{'station','ordinary'}:raise ValueError('station/ordinary interface phases required')
    for phase,registry in brief['interfaces'].items():
        if set(registry)!={'name','revision','roles'}:raise ValueError('explicit registry fields required')
        simple_name(registry['name'])
        for role in registry['roles'].values():
            if (role['mode']=='station_exit')!=(phase=='station'):raise ValueError('station exits qualify before ordinary interfaces')
            if role.get('station',{}).get('name')!=selector['name'] or role.get('station',{}).get('construction')!=selector['construction']:raise ValueError('interface station differs from exact selector')
    families=brief['families'];available=set();names=set();rank=-1
    if not isinstance(families,list) or not 1<=len(families)<=8:raise ValueError('approach requires1..8 ordered families')
    for f in families:
        if set(f)!={'name','kind','phase','envelopes','payload','imports','exports','shared_effects'}:raise ValueError('explicit family fields required')
        simple_name(f['name'])
        if f['name'] in names:raise ValueError('unique family names required')
        names.add(f['name'])
        r={'station':0,'leads':1,'ordinary':2}.get(f['phase'],-1)
        if r<0 or r<rank:raise ValueError('station then leads then ordinary family order required')
        rank=r
        if not isinstance(f['envelopes'],list) or not 1<=len(f['envelopes'])<=16:raise ValueError('bounded family envelopes required')
        for e in f['envelopes']:bounded_box(e)
        for name,ref in f['imports'].items():
            simple_name(name)
            if ref not in available:raise ValueError('imports require earlier exact exported bindings')
        for name in f['exports']:simple_name(name)
        if len(f['imports'])>64 or len(f['exports'])>64 or not isinstance(f['shared_effects'],list) or len(f['shared_effects'])>16:raise ValueError('bounded family bindings/effects required')
        for effect in f['shared_effects']:simple_name(effect)
        p=copy.deepcopy(f['payload']);p.setdefault('bindings',{})
        if set(p['bindings'])&set(f['imports']):raise ValueError('import conflicts with authored binding')
        p['bindings'].update({n:{'edges':[{'unresolved_receipt':True}]} for n in f['imports']})
        if f['kind']=='operator':
            if not contained(p['region'],f['envelopes']):raise ValueError('operator region exceeds family envelope')
            if f['phase']=='station' and any(s['kind']!='station' for s in p['steps']):raise ValueError('station phase only creates the selected station')
            if f['phase']=='station':
                if len(p['steps'])!=1 or any(s['brief']['name']!=selector['name'] or s['brief']['resource']!=selector['construction']['resource'] or s['brief']['position']!=selector['construction']['position'] for s in p['steps']):raise ValueError('station creation must match exact authored selector')
            if f['phase']=='leads' and any(s['kind']!='extend' for s in p['steps']):raise ValueError('lead phase only extends qualified station exits')
            if f['phase']=='leads' and 'station' not in brief['interfaces']:raise ValueError('lead station-exit registry required')
            if p.get('role_refs'):
                reg=brief['interfaces'].get('station' if f['phase']=='leads' else 'ordinary')
                if not reg or (p['interface_registry'],p['interface_revision'])!=(reg['name'],reg['revision']):raise ValueError('family uses wrong interface phase/revision')
                for port,name in p['role_refs'].items():
                    role=reg['roles'][name];intent=role['intent']
                    p['ports'].setdefault(port,{'position':[intent['guide_xyz'][i]-p['origin'][i] for i in range(3)],'direction':intent['travel_direction'],'grade':role.get('grade',0)})
            validate_plan(p)
            possible=set(p['bindings'])|{s['name'] for s in p['steps']}
            if any(not isinstance(v,str) or v not in possible for v in f['exports'].values()):raise ValueError('export requires exact child step/binding name')
        elif f['kind']=='corridor':
            if f['phase']!='ordinary' or p.get('session')!=brief['session']:raise ValueError('ordinary same-session corridor required')
            compiled=compile_corridor(p)
            if any(not contained(s['region'],f['envelopes']) for s in p['sections']):raise ValueError('corridor section exceeds family envelope')
            possible=set(compiled['initial_bindings'])|{n for s in compiled['sections'] for n in s['created_bindings']}
            for value in f['exports'].values():
                if isinstance(value,str) and value in possible:continue
                if isinstance(value,dict) and set(value)=={'road'}:
                    road=value['road']
                    if set(road)=={'track','sections'} and road['sections'] and all(n in {s['name'] for s in p['sections']} for n in road['sections']):continue
                raise ValueError('corridor export requires waypoint binding or authored exact road sections')
        else:raise ValueError('family delegates operator or corridor only')
        # Station operating receipts may be exported for context, but never used
        # as geometric imports/check chains.
        if f['phase']!='station':available.update(f['name']+'.'+n for n in f['exports'])
    checks=brief['checks'];seen=set()
    if not isinstance(checks,list) or len(checks)>32:raise ValueError('at most32 explicit approach checks')
    for c in checks:
        simple_name(c['name'])
        if c['name'] in seen or not c['families'] or set(c['families'])-names:raise ValueError('unique checks with exact family dependencies required')
        seen.add(c['name'])
        if c['kind'] not in ('route','station_routes','geometry','crossing'):raise ValueError('unsupported approach check')
        if set(c)-{'name','kind','families','shared_effects','bindings','payload'}:raise ValueError('explicit check fields required')
        if not c['bindings'] or set(c['bindings'].values())-available:raise ValueError('check requires exact exported bindings')
        if any(ref.split('.')[0] not in c['families'] for ref in c['bindings'].values()):raise ValueError('every check binding needs family dependency')
        for effect in c['shared_effects']:simple_name(effect)
        if len(c['bindings'])>16 or len(c['shared_effects'])>16:raise ValueError('bounded check bindings/effects required')
        q=c['payload']
        if c['kind']=='geometry':
            if not q or set(q)-{'region','max_grade','classifications'}:raise ValueError('explicit sampled geometry bounds only')
            if 'region' in q:bounded_box(q['region'])
            if 'max_grade' in q and (type(q['max_grade']) not in (int,float) or not math.isfinite(q['max_grade']) or q['max_grade']<0):raise ValueError('explicit finite selected grade bound required')
        elif c['kind']=='route':
            if not {'source','target','required_bindings','mode','max_length'}<=set(q) or set(q)-{'source','target','required_bindings','mode','max_length','max_path_entries','expected'}:raise ValueError('explicit directed route payload required')
            if type(q.get('expected',True)) is not bool or q['mode']!='TRAIN' or type(q['max_length']) not in (int,float) or not 0<q['max_length']<=8000:raise ValueError('bounded native directed route required')
            if type(q.get('max_path_entries',256)) is not int or not 1<=q.get('max_path_entries',256)<=512:raise ValueError('bounded route path entries required')
            if not isinstance(q['required_bindings'],list) or set(q['required_bindings'])-set(c['bindings']):raise ValueError('named exact required route bindings required')
            for spec in (q['source'],q['target']):
                if not isinstance(spec,dict) or spec.get('binding') not in c['bindings'] or set(spec) not in ({'binding','end'},{'binding','edge_id','node_id'}):raise ValueError('exact route attachment selector required')
        elif c['kind']=='station_routes':
            if set(q)-{'max_path_entries'}!={'name','revision','routes'} or not isinstance(q['routes'],list) or not 1<=len(q['routes'])<=8:raise ValueError('existing bounded station route brief required')
            for route in q['routes']:
                if set(route.get('required_bindings',[]))-set(c['bindings']):raise ValueError('station route required bindings must be declared')
        elif not {'origin','region','crossings'}<=set(q) or not q['crossings']:raise ValueError('explicit crossing observation payload required')
    digest(brief) # Reject non-finite/non-JSON design data before creating a job.
    return copy.deepcopy(brief)


def plan(operator,brief):
    from bridge_operator import digest
    b=compile_brief(brief);run=uuid.uuid4().hex[:16];folder=operator.path(run);folder.mkdir()
    live.atomic_json(folder/'approach.json',b)
    live.atomic_json(folder/'state.json',{'kind':'approach','status':'planned','plan_hash':digest(b),'session':b['session'],
        'family_index':0,'families':{},'bindings':{},'checks':{},'interfaces':[]})
    return {'status':'planned','run':run,'families':len(b['families']),'checks':len(b['checks'])}


def record(operator,run):
    from bridge_operator import digest
    folder=operator.path(run);b=load(folder/'approach.json');s=load(folder/'state.json')
    if s.get('kind')!='approach' or s['plan_hash']!=digest(b):raise ValueError('approach brief changed; new revision/job required')
    return folder,b,s


@contextmanager
def locked(folder):
    lock=folder/'approach.lock'
    with lock.open('x'):pass
    try:yield
    finally:lock.unlink()


def summary(run,b,s):
    affected=[c['name'] for c in b['checks'] if not s['checks'].get(c['name'],{}).get('valid')]
    return {'status':s['status'],'run':run,'session':s['session'],'completed_families':s['family_index'],
        'families':[{'name':f['name'],**{k:s['families'].get(f['name'],{}).get(k) for k in ('status','run','calls','native_seconds')},'fit':s['families'].get(f['name'],{}).get('fit',[])[:1]} for f in b['families'][:4]],
        'family_count':len(b['families']),'family_summary_truncated':len(b['families'])>4,
        'affected_checks':affected[:8],'affected_check_count':len(affected),'affected_checks_truncated':len(affected)>8,
        'failure':s.get('error'),'current_family':s.get('current_family')}


GEOMETRY_KEYS=('id','node0','node1','p0','p1','t0','t1','template','style','road_type','structure','node_positions')


def geometry_dependency(row):return {k:copy.deepcopy(row[k]) for k in GEOMETRY_KEYS if k in row}


class Dependencies:
    """One bounded observation cache per review; no graph reconstruction."""
    def __init__(self,client):self.client=client;self.edges={};self.tracks={};self.nodes={};self.stations={}

    def observe_edges(self,ids):
        missing=sorted(set(ids)-self.edges.keys())
        if len(set(ids)|self.edges.keys())>256:raise ValueError('review dependency bound256 exact edges exceeded')
        for i in range(0,len(missing),16):
            selected=missing[i:i+16];r=self.client.request('inspect',{'edge_ids':selected,'structures':True});rows=r.get('result',{}).get('edges',[])
            if r['status']!='ok' or len(rows)!=len(selected) or {e['id'] for e in rows}!=set(selected) or any(e.get('road_type')!='TRACK' for e in rows):raise ValueError('exact review dependency geometry unavailable')
            self.edges.update({e['id']:e for e in rows})

    def observe_semantics(self,ids):
        self.observe_edges(ids);missing=sorted(set(ids)-self.tracks.keys())
        for i in range(0,len(missing),16):
            selected=missing[i:i+16];r=self.client.request('operating_inspect',{'track_ids':selected,'limit':16});value=r.get('result',{}).get('tracks',{});rows=value.get('records',[])
            if r['status']!='ok' or value.get('truncated') is not False or len(rows)!=len(selected) or {e['id'] for e in rows}!=set(selected):raise ValueError('exact review track-object dependencies incomplete')
            for row in rows:
                objects=row.get('objects');objects=[] if objects=={} else objects
                if not isinstance(objects,list) or len(objects)>16 or not isinstance(row.get('revision'),list) or len(row['revision'])!=3 or any(row.get(k)!=self.edges[row['id']][k] for k in ('node0','node1')):raise ValueError('bounded track revision/object identity unavailable')
                self.tracks[row['id']]={'revision':row['revision'],'objects':sorted(objects,key=lambda o:o['id'])}
        for ident in sorted(set(ids)):
            e=self.edges[ident]
            for end in (0,1):
                node=e['node'+str(end)]
                if node in self.nodes:continue
                pos=e.get('node_positions',[e['p0'],e['p1']])[end]
                r=self.client.request('discover',{'region':{'min':[x-.5 for x in pos],'max':[x+.5 for x in pos]},'max_edges':16});value=r.get('result',{})
                # The octree locates a witness. Exact native node identity and
                # getNodeSegments incidence establish attachment, not the edge
                # whose bounding volume happened to be returned by the octree.
                witnesses=[c for c in value.get('candidates',[]) if c.get('node_id')==node and ident in c.get('incident_edges',[])]
                if r['status']!='ok' or value.get('complete') is not True or not witnesses:raise ValueError(f'exact review endpoint incidence unavailable (edge {ident}, node {node})')
                observations=[]
                for c in witnesses:
                    incident=c.get('incident_edges',[])
                    if c.get('incidence_complete') is not True or c.get('incident_output_truncated') is not False or c.get('incident_count')!=len(incident) or len(set(incident))!=len(incident) or len(incident)>16:raise ValueError('bounded complete endpoint incidence unavailable')
                    observations.append({'incident_edges':sorted(incident),'construction_owner':c.get('construction_owner','unknown')})
                if any(v!=observations[0] for v in observations):raise ValueError('conflicting exact-node incidence witnesses')
                self.nodes[node]=observations[0]

    def station_identity(self,selector):
        import bridge_station as station
        name=selector['name']
        if name not in self.stations:
            if len(self.stations)>=8:raise ValueError('review station dependency bound8 exceeded')
            r=self.client.request('station_lookup',station.parameters({'name':name,'lookup_scope':'identity_frozen'}));v=station.normalized_station(r.get('result',{}))
            if r['status']!='ok' or v.get('identity_complete') is not True or v.get('frozen_complete') is not True:raise ValueError('complete scoped station dependency unavailable')
            self.stations[name]=v
        v=self.stations[name];cs=[x for x in v.get('constructions',[]) if x.get('resource')==selector['construction']['resource'] and x.get('position')==selector['construction']['position']]
        if len(cs)!=1:raise ValueError('exact selected station dependency changed/unavailable')
        return copy.deepcopy(v)

    def fingerprint(self,check,ids,selectors):
        self.observe_edges(ids)
        value={'geometry':{str(i):geometry_dependency(self.edges[i]) for i in sorted(set(ids))}}
        if check['kind'] in ('route','station_routes'):
            self.observe_semantics(ids)
            value['objects']={str(i):copy.deepcopy(self.tracks[i]) for i in sorted(set(ids))}
            value['incidence']={str(n):copy.deepcopy(self.nodes[n]) for i in ids for n in (self.edges[i]['node0'],self.edges[i]['node1'])}
        if check['kind']=='station_routes':value['stations']={s['name']:self.station_identity(s) for s in selectors}
        return value


def invalidate(b,s,families,effects,*,geometry_preserved=False):
    affected=[]
    for c in b['checks']:
        if set(c['families'])&set(families) or set(c['shared_effects'])&set(effects):
            if geometry_preserved and c['kind']=='geometry':continue
            s['checks'].setdefault(c['name'],{})['valid']=False;affected.append(c['name'])
    return affected


def propagate(b,s,child,signal_only,receipt=None):
    """Apply chronological native generations, not a graph of recyclable IDs."""
    from bridge_operator import digest
    lineage=child.get('lineage',[]);key=receipt or digest(lineage)
    progress=s.get('propagated_receipts',{}).get(key,{'count':0,'prefix_hash':digest([])})
    count=progress['count']
    if count>len(lineage) or digest(lineage[:count])!=progress['prefix_hash']:raise ValueError('applied replacement receipt prefix changed')
    if count==len(lineage):return
    if count and lineage[count].get('request_id') and lineage[count].get('request_id')==lineage[count-1].get('request_id'):raise ValueError('partial atomic replacement receipt requires reconciliation')
    snapshots={}
    for binding in list(child.get('bindings',{}).values())+list(child.get('steps',{}).values()):
        for e in binding.get('edges',[]):
            if e['id'] in snapshots and geometry_dependency(snapshots[e['id']])!=geometry_dependency(e):raise ValueError('conflicting final native generation snapshots')
            snapshots[e['id']]=e
    # Each root is an exact input generation. Replacements from one native
    # command are simultaneous; later commands can legitimately recycle IDs.
    inputs={}
    for v in s['bindings'].values():
        for e in v.get('edges',[]):
            if e['id'] in inputs and geometry_dependency(inputs[e['id']])!=geometry_dependency(e):raise ValueError('mixed input native generations require reconciliation')
            inputs[e['id']]=e
    roots={i:[i] for i in inputs};touched=set();groups=[]
    for i,mapping in enumerate(lineage[count:],count):
        event=mapping.get('request_id') or ('entry',i)
        if not groups or groups[-1][0]!=event:groups.append((event,{}))
        links=groups[-1][1];old=mapping['original_edge'];ids=mapping['replacement_edges']
        if old in links or not ids or len(set(ids))!=len(ids):raise ValueError('ambiguous exact replacement command receipt')
        links[old]=ids
    for _,links in groups:
        for root,ids in roots.items():
            if any(i in links for i in ids):touched.add(root)
            roots[root]=[new for i in ids for new in links.get(i,[i])]
    if any(len(ids)!=len(set(ids)) or any(i not in snapshots for i in ids) for root,ids in roots.items() if root in touched):raise ValueError('ambiguous/incomplete final native generation mapping')
    pending=copy.deepcopy(s);affected=set();preserved=True;changes={}
    for name,v in pending['bindings'].items():
        rows=v.get('edges',[]);changed_roots={e['id'] for e in rows}&touched
        # Refresh auxiliary observations on unchanged exact geometry from the
        # current child (e.g. native parallel-strip IDs), without inferring effects.
        current=lambda e:copy.deepcopy(snapshots[e['id']]) if e['id'] in snapshots and geometry_dependency(e)==geometry_dependency(snapshots[e['id']]) else e
        if rows:v['edges']=[current(e) for e in rows]
        if not changed_roots:continue
        aliases=pending.setdefault('attachment_aliases',{}).setdefault(name,[])
        for alias in aliases:
            old=alias.get('current_edge')
            if old not in changed_roots:continue
            matches=[snapshots[i] for i in roots[old] if alias['node_id'] in (snapshots[i]['node0'],snapshots[i]['node1'])]
            alias['current_edge']=matches[0]['id'] if len(matches)==1 else None
        for e in rows:
            if e['id'] not in changed_roots:continue
            changed=[snapshots[i] for i in roots[e['id']]];changes[e['id']]=changed
            preserved &= len(changed)==1 and all(e.get(k)==changed[0].get(k) for k in GEOMETRY_KEYS if k!='id' and k in e)
            generation=digest(geometry_dependency(e))
            for node in (e['node0'],e['node1']):
                matches=[r for r in changed if node in (r['node0'],r['node1'])]
                alias={'edge_id':e['id'],'node_id':node,'generation':generation,'current_edge':matches[0]['id'] if len(matches)==1 else None}
                if not any(a['edge_id']==alias['edge_id'] and a['node_id']==node and a['generation']==generation for a in aliases):aliases.append(alias)
        v['edges']=[new for e in rows for new in ([snapshots[i] for i in roots[e['id']]] if e['id'] in changed_roots else [current(e)])]
        affected.add(name.split('.')[0])
    if signal_only and preserved:
        for check in b['checks']:
            if check['kind']!='geometry':continue
            dep=pending['checks'].get(check['name'],{}).get('dependencies',{}).get('geometry',{})
            before=copy.deepcopy(dep)
            for old in changes:dep.pop(str(old),None)
            for old,changed in changes.items():
                if str(old) in before:
                    new=geometry_dependency(changed[0]);dep[str(changed[0]['id'])]={k:new[k] for k in before[str(old)] if k in new}
    invalidate(b,pending,affected,[],geometry_preserved=signal_only and preserved)
    pending.setdefault('propagated_receipts',{})[key]={'count':len(lineage),'prefix_hash':digest(lineage)}
    s.clear();s.update(pending) # No partial alias/binding update on validation failure.


def imported_endpoint(s,ref,spec,rows):
    aliases=[a for a in s.get('attachment_aliases',{}).get(ref,[]) if (a['edge_id'],a['node_id'])==(spec['edge_id'],spec['node_id'])]
    ids={a['current_edge'] for a in aliases} if aliases else {spec['edge_id']}
    if None in ids:raise ValueError('authored endpoint generation no longer survives')
    selected=[e for e in rows if e['id'] in ids and spec['node_id'] in (e['node0'],e['node1'])]
    if len(selected)!=1:raise ValueError('imported qualified endpoint generation unavailable/ambiguous')
    return selected[0]


def qualify_station(operator,b,s):
    import bridge_station as station
    r=operator.client().request('station_lookup',station.parameters({'name':b['station']['name'],'lookup_scope':'identity_frozen'}))
    value=station.normalized_station(r.get('result',{}));selector=b['station']['construction']
    exact=[c for c in value.get('constructions',[]) if c.get('resource')==selector['resource'] and c.get('position')==selector['position']]
    if r['status']!='ok' or value.get('identity_complete') is not True or value.get('frozen_complete') is not True or len(exact)!=1:raise ValueError('exact selected station identity unavailable/ambiguous')
    s['station_identity']=exact[0]


def qualify_interfaces(operator,b,s,phase):
    if phase in s['interfaces'] or phase not in b['interfaces']:return
    reg=b['interfaces'][phase];registry=operator.interfaces();path=registry.path(reg['name'])
    if path.exists():
        old=registry.load(reg['name'])
        if old['revision']!=reg['revision'] or old['roles']!=reg['roles'] or old.get('session')!=s['session']:raise ValueError('interface registry conflicts with approach brief/session')
        registry.resolve(operator.client(),reg['name'],reg['revision'])
    else:operator.register_interfaces(**reg)
    s['interfaces'].append(phase)


def exported_binding(operator,child,state,name):
    """Unused completed prefix receipts need not be refreshed during continuation.

    Reacquire them only when the parent approach actually exports their proof.
    """
    from bridge_operator import digest
    for _ in range(16):
        if name in state.get('invalidated_bindings',[]):raise ValueError('family export was removed/invalidated')
        value=state.get('steps',{}).get(name) or state.get('bindings',{}).get(name)
        if value:return value
        p=load(operator.path(child)/'plan.json');continuation=p.get('continuation')
        if not continuation or name not in continuation['skipped_steps']:return None
        child=continuation['run'];state=load(operator.path(child)/'state.json')
        if digest(state)!=continuation['state_hash']:raise ValueError('completed export parent changed')
    raise ValueError('bounded continuation receipt depth exceeded')


def station_leads(operator,selector,*,outward_direction,ordered_roles,lead_length,registry_name,revision,track,max_grade,region,exit_evidence=None):
    """Author an existing extend plan from exact, selected-side station exits.

    No construction occurs. Terminal ordering is observed lateral order, never
    guessed native terminal-index order. The caller retains layout authority.
    """
    from bridge_operator import unit,validate_plan
    import bridge_station as station
    d=unit(outward_direction);side=[-d[1],d[0]]
    if not isinstance(ordered_roles,list) or not 1<=len(ordered_roles)<=8 or len(set(ordered_roles))!=len(ordered_roles):raise ValueError('1..8 unique authored station lead roles required')
    for name in ordered_roles:simple_name(name)
    if type(lead_length) not in (int,float) or not math.isfinite(lead_length) or not 5<=lead_length<=60:raise ValueError('native lead length5..60 required')
    if exit_evidence is None:
        result=station.inspect_exits(operator.client(),{'name':selector['name'],'lookup_scope':'identity_frozen'});evidence=load(Path(result['evidence']))
    else:
        evidence=load(Path(exit_evidence))
        if evidence.get('session')!=operator.client().session:raise ValueError('station exit evidence belongs to a different session')
    # Evidence prepares intent only; register/plan/build reacquire native identity.
    value=evidence['station'];exact=[c for c in value['constructions'] if c['resource']==selector['construction']['resource'] and c['position']==selector['construction']['position']]
    if len(exact)!=1:raise ValueError('exact selected station is ambiguous/unavailable')
    cid=exact[0]['construction_id'];exits=[];terminals=set()
    for c in evidence['exits']:
        assoc=c['association'];out=unit(c['outward_direction'][:2])
        if assoc['construction_id']!=cid or sum(a*b for a,b in zip(d,out))<math.cos(math.radians(2)):continue
        matches=assoc['terminal_identity_matches']
        if len(matches)!=1 or matches[0]['terminal_index'] in terminals:raise ValueError('selected station side has ambiguous terminal components')
        terminals.add(matches[0]['terminal_index']);exits.append(c)
    if len(exits)!=len(ordered_roles):raise ValueError('selected station side does not match authored lead count')
    exits.sort(key=lambda c:sum(c['pos'][i]*side[i] for i in range(2)))
    if any(abs(sum((a['pos'][i]-z['pos'][i])*side[i] for i in range(2)))<.001 for a,z in zip(exits,exits[1:])):raise ValueError('station lateral ordering is ambiguous')
    mouth=[sum(c['pos'][i] for c in exits)/len(exits) for i in range(3)];roles={};ports={};refs={};steps=[]
    for name,c in zip(ordered_roles,exits):
        direction=unit(c['outward_direction'][:2]);pos=c['pos'];grade=c['grade'];source=name+'_exit';target=name+'_end'
        roles[name]={'station':copy.deepcopy(selector)|{'terminal_index':c['association']['terminal_identity_matches'][0]['terminal_index']},'mode':'station_exit','grade':grade,
            'intent':{'region':{'min':[x-1 for x in pos],'max':[x+1 for x in pos]},'max_edges':16,'guide_xyz':pos,'travel_direction':direction}}
        refs[source]=name;end=[pos[i]+lead_length*(direction[i] if i<2 else grade) for i in range(3)]
        ports[target]={'position':[end[i]-mouth[i] for i in range(3)],'direction':direction,'grade':grade}
        steps.append({'name':name+'_lead','kind':'extend','source':source,'target':target})
    payload={'version':2,'revision':revision,'origin':mouth,'region':copy.deepcopy(region),'ports':ports,'track':copy.deepcopy(track),'max_grade':max_grade,
        'steps':steps,'routes':[],'curves':{},'interface_registry':registry_name,'interface_revision':revision,'role_refs':refs}
    shape=copy.deepcopy(payload)
    for name,c in zip(ordered_roles,exits):shape['ports'][name+'_exit']={'position':[c['pos'][i]-mouth[i] for i in range(3)],'direction':unit(c['outward_direction'][:2]),'grade':c['grade']}
    validate_plan(shape)
    return {'station':copy.deepcopy(selector),'mouth_datum':mouth,'station_interfaces':{'name':registry_name,'revision':revision,'roles':roles},'payload':payload,
        'exports':{name+'_lead':name+'_lead' for name in ordered_roles},'session':operator.client().session,'game_constructed':False}


def build(operator,run,*,continuing=False,family_run=None):
    from bridge_operator import fresh_binding
    from bridge_corridor import recover_road
    folder,b,s=record(operator,run);guard(operator,s)
    if s['status']!='planned' and not(continuing and s['status'] in ('running','needs_attention')):raise ValueError('approach already attempted; explicit continuation required')
    if family_run and not continuing:raise ValueError('replacement child requires explicit continuation')
    def persist():live.atomic_json(folder/'state.json',s)
    with locked(folder):
        try:
            s.update(status='running');s.pop('error',None);persist()
            while s['family_index']<len(b['families']):
                client=guard(operator,s);f=b['families'][s['family_index']];name=f['name'];s['current_family']=name;persist()
                if f['phase']!='station':
                    qualify_station(operator,b,s);qualify_interfaces(operator,b,s,'station')
                    if f['phase']=='ordinary':qualify_interfaces(operator,b,s,'ordinary')
                    persist()
                entry=s['families'].setdefault(name,{'status':'pending'});child=entry.get('run')
                if family_run:
                    if f['kind']!='operator' or not child:raise ValueError('replacement requires stopped operator family')
                    p=load(operator.path(family_run)/'plan.json')
                    if p.get('continuation',{}).get('run')!=child:raise ValueError('family_run must be existing reconciled child continuation')
                    if not contained(p['region'],f['envelopes']):raise ValueError('continued child exceeds authored family envelope')
                    entry['run']=child=family_run;family_run=None;persist()
                if child is None:
                    p=copy.deepcopy(f['payload']);p.setdefault('bindings',{})
                    # Refresh current dependencies once at phase entry. Child still
                    # performs its own mutation-time freshness checks.
                    cache={}
                    for local,ref in f['imports'].items():
                        if ref not in cache:cache[ref]={'edges':fresh_binding(client,s['bindings'][ref])}
                        p['bindings'][local]=copy.deepcopy(cache[ref])
                    if f['kind']=='operator':
                        # Imported exact endpoint controls are materialised from
                        # current receipt geometry, not a stale preliminary sketch.
                        for port,spec in p.get('port_refs',{}).items():
                            if spec['chain'] not in f['imports']:continue
                            rows=p['bindings'][spec['chain']]['edges']
                            if 'end' in spec:
                                if len(rows)!=1:raise ValueError('single-edge imported endpoint required')
                                row=rows[0];at0=spec['end']=='node0'
                            else:
                                row=imported_endpoint(s,f['imports'][spec['chain']],spec,rows);at0=spec['node_id']==row['node0']
                                spec['edge_id']=row['id']
                            pos=row['p0' if at0 else 'p1'];t=row['t0' if at0 else 't1'];sign=-1 if at0 else 1;length=math.hypot(*t[:2])
                            if not length:raise ValueError('imported endpoint tangent unavailable')
                            p['ports'][port]={'position':[pos[i]-p['origin'][i] for i in range(3)],'direction':[sign*t[i]/length for i in range(2)],'grade':sign*t[2]/length}
                    child=(operator.plan(p) if f['kind']=='operator' else operator.plan_corridor(p))['run']
                    entry.update(status='running',run=child);persist()
                child_state=load(operator.path(child)/'state.json')
                if child_state['status']=='planned':
                    guard(operator,s)
                    (operator.execute if f['kind']=='operator' else operator.build_corridor)(child)
                    child_state=load(operator.path(child)/'state.json')
                elif f['kind']=='corridor' and continuing and child_state['status'] in ('running','needs_attention'):
                    guard(operator,s)
                    operator.continue_corridor(child);child_state=load(operator.path(child)/'state.json')
                guard(operator,s)
                children=[child_state];child_runs=[child]
                if f['kind']=='corridor':
                    child_runs=[r['run'] for r in child_state['section_runs']]
                    if child_state.get('current_run') and child_state['current_run'] not in child_runs:child_runs.append(child_state['current_run'])
                    children=[load(operator.path(r)/'state.json') for r in child_runs]
                signal_only=f['kind']=='operator' and all(step['kind'] in ('signal','signal_chain') for step in f['payload']['steps'])
                for child_id,cs in zip(child_runs,children):propagate(b,s,cs,signal_only,receipt=child_id)
                # Propagation atomically replaces state dictionaries; reacquire
                # the live family entry before recording completion/counters.
                entry=s['families'][name]
                invalidate(b,s,[name],f['shared_effects'],geometry_preserved=signal_only)
                persist() # Keep partial identity changes visible before stopping.
                if child_state['status']!='built':raise ValueError('family requires existing child reconciliation/continuation: '+child_state.get('error',child_state['status']))
                qualified={}
                for public,local in f['exports'].items():
                    if isinstance(local,dict):
                        compiled=load(operator.path(child)/'corridor.json');rows,_=recover_road(operator,compiled,child_state,local['road']);value={'edges':rows}
                    else:
                        value=exported_binding(operator,child,child_state,local) if f['kind']=='operator' else child_state.get('bindings',{}).get(local)
                    if not value:raise ValueError('exact family export unavailable')
                    # Station creation exports its native result, never fake rails.
                    qualified[name+'.'+public]={'edges':fresh_binding(client,value)} if value.get('edges') else copy.deepcopy(value)
                s['bindings'].update(qualified)
                entry.update(status='built',calls=sum(c.get('calls',0) for c in children),native_seconds=sum(c.get('native_seconds',0) for c in children))
                fits=[v for cs in children for v in cs.get('fit_variations',{}).values()]
                entry['fit']=[{k:v.get(k) for k in ('attempt_count','requests_used','selected_actual_shift_m')} for v in fits][:4]
                persist() # Completed proof precedes index advancement.
                s['family_index']+=1;s.pop('current_family',None);persist()
            s['status']='built';persist()
        except Exception as exc:s.update(status='needs_attention',error=str(exc)[:350]);persist()
    return summary(run,b,s)


def review(operator,run,checks=None):
    from bridge_operator import fresh_binding,cubic,in_region,crossing_observations,digest
    folder,b,s=record(operator,run);client=guard(operator,s)
    if s['status'] not in ('built','reviewed'):raise ValueError('complete approach required before acceptance')
    if checks is not None and (not isinstance(checks,list) or len(checks)>32 or len(set(checks))!=len(checks)):raise ValueError('bounded distinct explicit check names required')
    selected={c['name'] for c in b['checks'] if not s['checks'].get(c['name'],{}).get('valid')} if checks is None else set(checks)
    if selected-{c['name'] for c in b['checks']}:raise ValueError('unknown approach checks')
    cache={};results=[];dependencies=Dependencies(client)
    def selectors(c):
        out=[b['station']]
        if c['kind']=='station_routes':
            q=c['payload']
            for route in q['routes']:
                for endpoint in (route['source'],route['target']):
                    if 'role' not in endpoint:continue
                    registry=operator.interfaces().load(endpoint.get('registry_name',q['name']))
                    if registry['revision']!=endpoint.get('registry_revision',q['revision']):raise ValueError('station dependency registry revision changed')
                    out.append(registry['roles'][endpoint['role']]['station'])
        return out
    def ids_for(c):
        ids={e['id'] for ref in c['bindings'].values() for e in s['bindings'][ref]['edges']}
        if c['kind'] in ('route','station_routes'):
            # Explicit family scope includes shared fan/path interiors and
            # authored alternatives for negative checks, without graph discovery.
            ids.update(e['id'] for ref,value in s['bindings'].items() if ref.split('.')[0] in c['families'] for e in value.get('edges',[]))
        ids.update(int(i) for i in s['checks'].get(c['name'],{}).get('dependencies',{}).get('geometry',{}))
        return sorted(ids)
    with locked(folder):
        candidates=[c for c in b['checks'] if c['name'] in selected or s['checks'].get(c['name'],{}).get('valid')]
        changed=[];fingerprints={}
        try:
            dependencies.observe_edges([i for c in candidates for i in ids_for(c)])
            semantic_ids=[i for c in candidates if c['kind'] in ('route','station_routes') for i in ids_for(c)]
            if semantic_ids:dependencies.observe_semantics(semantic_ids)
            for c in candidates:
                rows={}
                for local,ref in c['bindings'].items():
                    expected=s['bindings'][ref]['edges'];current=[dependencies.edges[e['id']] for e in expected]
                    if any(any(e.get(k)!=r.get(k) for k in GEOMETRY_KEYS if k in e) for e,r in zip(expected,current)):
                        changed.append(c['name'])
                    rows[local]=current;cache[ref]=current
                fingerprints[c['name']]=dependencies.fingerprint(c,ids_for(c),selectors(c))
                proof=s['checks'].get(c['name'],{})
                if proof.get('valid') and (proof.get('criteria_hash')!=digest(c) or proof.get('session')!=s['session'] or proof.get('dependencies')!=fingerprints[c['name']]):changed.append(c['name'])
            guard(operator,s)
        except Exception as exc:
            changed=[c['name'] for c in candidates];s['error']='review dependencies unavailable: '+str(exc)[:250]
        if changed:
            for name in changed:s['checks'].setdefault(name,{})['valid']=False
            s['status']='needs_attention';s.setdefault('error','review dependencies changed; reconcile exact bindings/current state before fresh checks')
            live.atomic_json(folder/'state.json',s)
            return summary(run,b,s)|{'checks_run':0,'changed_dependencies':list(dict.fromkeys(changed))[:8]}
        for c in b['checks']:
            if c['name'] not in selected:continue
            guard(operator,s)
            rows={}
            for local,ref in c['bindings'].items():
                if ref not in cache:cache[ref]=fresh_binding(client,s['bindings'][ref])
                rows[local]=cache[ref]
            q=copy.deepcopy(c['payload']);kind=c['kind'];passed=False
            if kind=='station_routes':
                q['bindings']={n:{'edges':r} for n,r in rows.items()};result=operator.review_station_routes(q);passed=result['status']=='ok'
            elif kind=='route':
                def endpoint(spec):
                    chain=rows[spec['binding']]
                    if set(spec)=={'binding','end'} and len(chain)==1 and spec['end'] in ('node0','node1'):return chain[0]['id'],chain[0][spec['end']]
                    if set(spec)=={'binding','edge_id','node_id'} and any(e['id']==spec['edge_id'] and spec['node_id'] in (e['node0'],e['node1']) for e in chain):return spec['edge_id'],spec['node_id']
                    raise ValueError('exact route attachment required')
                a,an=endpoint(q.pop('source'));z,zn=endpoint(q.pop('target'));required=q.pop('required_bindings');expect=q.pop('expected',True)
                request=q|{'source_edge':a,'source_node':an,'target_edge':z,'target_node':zn,'required_edges':list(dict.fromkeys([a,z]+[e['id'] for n in required for e in rows[n]]))}
                result=live.route(client,request);value=result.get('result',{});verified=value.get('requested_route_verified')
                passed=result['status']=='ok' and (verified is True and value.get('truncated') is False and type(value.get('path_count')) is int and 0<value['path_count']<=request.get('max_path_entries',256) if expect else
                    value.get('native_path_found') is False and value.get('reason')=='no_native_path_returned')
            elif kind=='geometry':
                if set(q)-{'region','max_grade','classifications'}:raise ValueError('only explicit sampled geometry bounds supported')
                if 'region' in q:bounded_box(q['region'])
                if 'max_grade' in q and (type(q['max_grade']) not in (int,float) or not math.isfinite(q['max_grade']) or q['max_grade']<0):raise ValueError('explicit finite selected grade bound required')
                passed=True
                for chain in rows.values():
                    for e in chain:
                        if 'classifications' in q:passed &= e.get('structure',{}).get('classification') in q['classifications']
                        for j in range(65):
                            pos,tangent=cubic(e,j/64)
                            if 'region' in q:passed &= in_region(pos,q['region'])
                            if 'max_grade' in q:
                                u=j/64;dh=[6*u*u-6*u,3*u*u-4*u+1,-6*u*u+6*u,3*u*u-2*u]
                                d=[sum(dh[n]*e[k][axis] for n,k in enumerate(('p0','t0','p1','t1'))) for axis in range(3)]
                                passed &= math.hypot(*d[:2])>0 and abs(d[2])/math.hypot(*d[:2])<=q['max_grade']
                result={'sampled_only':True,'continuous_clearance_certified':False,'native_geometry_reproduced':False}
            else:
                paths={n:[{'edge':{'entity':e['id']},'confirmed_TRACK':True} for e in r] for n,r in rows.items()}
                result=crossing_observations(q,[e for r in rows.values() for e in r],paths)
                passed=bool(result) and all(v['separate_endpoint_identities_observed'] and v['required_structure_observed'] for v in result)
            guard(operator,s)
            ids=ids_for(c)
            if kind=='station_routes':
                complete=load(Path(result['evidence']))['routes'] if result.get('evidence') else result.get('routes',[])
                ids=sorted(set(ids)|{v[k]['edge'] for v in complete for k in ('source','target')})
            proof_dependencies=dependencies.fingerprint(c,ids,selectors(c))
            s['checks'][c['name']]={'valid':passed,'passed':passed,'criteria_hash':digest(c),'session':s['session'],'dependencies':proof_dependencies,'result':result}
            results.append({'name':c['name'],'passed':passed});live.atomic_json(folder/'state.json',s)
        s['status']='reviewed' if all(s['checks'].get(c['name'],{}).get('valid') for c in b['checks']) else 'built'
        live.atomic_json(folder/'state.json',s)
    return summary(run,b,s)|{'checks_run':len(results),'check_results':results[:8],'check_results_truncated':len(results)>8,
        'proof_scope':'recorded same-session checks and declared effects; not an atomic world snapshot','train_traversal':'unprobed'}
