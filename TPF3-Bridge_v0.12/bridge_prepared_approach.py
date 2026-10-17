"""Named-input preparation and one fixed approach/corridor workflow. No planner.

prepare_approach(brief, inputs, follow_on_corridor=None) is read-only until it
publishes the local prepared record. Initial family/corridor binding names select
either an explicit edge_id guide or {edge_id, terminal_index, end} proven against
the selected station's native frozen component. {edge_id, frozen: true, end}
instead proves selected-construction membership without an operating terminal
claim (for through tracks). The catalogue region, functional
signal_seed {seed_id, resource}, and optional original removal-only bootstrap are
explicit inputs. Geometry, controls, track resources and checks stay authored.

Optional follow_on_corridor contains exactly brief, roads and whole_routes. Each
whole_routes road declares road/waypoint, root_binding, forward_root_to_main,
existing_scaffold_edge_ids and new_receipt_pool family/step selectors. An optional
extract_path names exact source/target binding endpoints for one grouped member.
Only those receipts form the final pool; fan/throat edges behind the root are not
implicitly included. Saved rows are freshly qualified before native route checks.
waypoint_side defaults to front; back is explicit. roads: [] explicitly means no
additional whole-family checks; original approach/completion checks stay intact.

A corridor selector may instead be {receipt: {approach: 'self' or an exact
completed approach run, export: 'family.public_export'}}. Its waypoint reference
is {chain, end: 'node0' or 'node1'}. Existing sources capture immutable plan/state/
session proof immediately; self exports resolve only after the approach review.
Only single-edge exports are supported. Authored reference binding geometry is
static preflight material, never a guessed executable native identity. Stage3
freezes the concrete brief/provenance before publishing its corridor child.

build_prepared_approach delegates a fixed six-stage flow to existing public APIs.
It does not retry uncertain effects. Explicit continuation adopts only owned child
continuations; completed children are reused. A resumed final check stage repeats
all current whole-road checks. Phase metrics contain one outer total; stage_metrics
are a breakdown, not additional elapsed time. No global/world-state cache exists.
"""
import copy
import json
import time
import uuid

import bridge_live as live
from bridge_approach import compile_brief,exported_binding,record as approach_record
from bridge_corridor import compile_corridor,validate_roads,ordered_path
from bridge_operator import digest,validate_plan,vector,no_step_effects,fresh_binding
from bridge_phase_metrics import Collector
from bridge_station import normalized_station,terminal_component_matches,parameters as station_parameters


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def guard(op,session=None):
    c=op.client()
    if session is not None and c.session!=session:raise ValueError('prepared approach session changed; prepare fresh inputs')
    journal=getattr(c,'journal',None)
    if journal and journal.exists() and read(journal).get('pending'):raise ValueError('unresolved native request requires reconciliation')
    return c


def same_geometry(old,new):
    for key in ('p0','p1','t0','t1','template','style','road_type','structure'):
        if key in old and old[key]!=new.get(key):raise ValueError('qualified input geometry/resources differ from accepted recipe')
    for key in ('p0','p1','t0','t1'):vector(new[key],3)
    if new.get('road_type')!='TRACK':raise ValueError('qualified TRACK snapshot required')


def public_export(brief,name):
    matches=[(f,f['exports'][name.split('.',1)[1]]) for f in brief['families']
             if '.' in name and f['name']==name.split('.',1)[0] and name.split('.',1)[1] in f['exports']]
    if len(matches)!=1 or matches[0][0]['kind']!='operator' or not isinstance(matches[0][1],str):raise ValueError('one named operator public export required')
    f,local=matches[0];p=f['payload']
    if local in p.get('bindings',{}):
        rows=p['bindings'][local]['edges']
        if len(rows)!=1:raise ValueError('single-edge public export required')
        track={k:rows[0][k] for k in ('template','style')}
    else:
        selected=[s for s in p['steps'] if s['name']==local]
        if len(selected)!=1 or selected[0]['kind']=='group':raise ValueError('single-edge public export contract required')
        step=selected[0];track=step.get('track',p['track'])
        # An extension inherits its exact attachment's resources, including
        # mixed fast/slow station leads; the seed default does not override it.
        ref=p.get('port_refs',{}).get(step.get('source')) if isinstance(step.get('source'),str) else None
        if step['kind']=='extend' and ref and ref['chain'] in p.get('bindings',{}):
            rows=p['bindings'][ref['chain']]['edges']
            if len(rows)!=1:raise ValueError('single exact extension source required')
            track={k:rows[0][k] for k in ('template','style')}
    return f,local,{k:track[k] for k in ('template','style')}


def receipt_source(op,selector,session,expected=None):
    """Read an exact completed approach, never a search or proximity selector."""
    run=selector['approach'];_,p,s=approach_record(op,run)
    if s.get('kind')!='approach' or s.get('session')!=session or p['session']!=session or s.get('plan_hash')!=digest(p):raise ValueError('receipt source scope/session changed')
    if s['status']!='reviewed' and not(s['status']=='built' and not p['checks']):raise ValueError('completed reviewed approach receipt required')
    f,local,track=public_export(p,selector['export']);entry=s['families'][f['name']]
    child=entry['run'];cs=read(op.path(child)/'state.json')
    cp=read(op.path(child)/'plan.json')
    if cs.get('status')!='built' or cs.get('session')!=session or cs.get('plan_hash')!=digest(cp):raise ValueError('completed unchanged same-session receipt child required')
    proof={'approach':run,'export':selector['export'],'plan_hash':digest(p),'state_hash':digest(s),
           'child':child,'child_plan_hash':digest(cp),'child_state_hash':digest(cs),'session':session}
    if expected is not None and proof!=expected:raise ValueError('receipt source proof changed')
    value=exported_binding(op,child,cs,local)
    if not value or len(value.get('edges',[]))!=1:raise ValueError('unavailable or ambiguous single-edge public receipt')
    return value,proof,track


def qualify_receipt(op,selector,session,ends,expected=None,client=None):
    value,proof,track=receipt_source(op,selector,session,expected)
    c=client or guard(op,session);rows=fresh_binding(c,value);e=rows[0]
    if any(e.get(k)!=track[k] for k in track):raise ValueError('public receipt resource contract differs')
    r=c.request('inspect',{'edge_ids':[e['id']],'structures':True,'incidence_edge_ids':[e['id']]})
    inc=r.get('result',{}).get('endpoint_incidence',{})
    if r.get('status')!='ok' or inc.get('complete') is not True or inc.get('truncated') is not False or inc.get('edge_ids')!=[e['id']]:raise ValueError('complete public receipt incidence required')
    nodes={n['node_id']:n for n in inc['nodes']}
    if set(nodes)!={e['node0'],e['node1']} or len(inc['nodes'])!=2 or inc.get('node_count')!=2:raise ValueError('exact public receipt endpoint incidence required')
    observed=r['result']['edges']
    if len(observed)!=1 or observed[0]['id']!=e['id']:raise ValueError('exact public receipt snapshot required')
    same_geometry(e,observed[0])
    if any(e[k]!=observed[0][k] for k in ('node0','node1')):raise ValueError('public receipt attachment changed')
    for end in ends:
        n=nodes[e[end]]
        if n.get('incidence_complete') is not True or n.get('incident_output_truncated') or n.get('incident_count')!=1 or n.get('incident_edges')!=[e['id']] or n.get('construction_owner') not in ('none',-1,0):raise ValueError('public receipt endpoint is occupied or unavailable')
    return {'edges':rows},proof


def receipt_ends(c,name):
    ends=[]
    for profiles in c['waypoints'].values():
        for profile in profiles.values():
            for side in ('back','front'):
                ref=profile.get(side,{})
                if ref.get('chain')!=name:continue
                if set(ref)!={'chain','end'} or ref['end'] not in ('node0','node1'):raise ValueError('receipt waypoint requires explicit chain and node0/node1 end')
                ends.append(ref['end'])
    if not ends:raise ValueError('receipt binding must name a corridor endpoint')
    return ends


def reference_corridor(c,receipts):
    """Compile authored reference controls only; never publish these as native IDs."""
    out=copy.deepcopy(c)
    for name in receipts:
        rows=out['bindings'][name]['edges']
        if len(rows)!=1:raise ValueError('one authored receipt reference edge required')
        row=rows[0];receipt_ends(out,name)
        for profiles in out['waypoints'].values():
            for profile in profiles.values():
                for side in ('back','front'):
                    ref=profile.get(side,{})
                    if ref.get('chain')==name:profile[side]={'chain':name,'edge_id':row['id'],'node_id':row[ref['end']]}
    return out


def prepare(op,brief,inputs,follow_on_corridor=None):
    """Only read native state; publication contains concrete qualified inputs."""
    start=time.monotonic();collector=Collector();session=guard(op).session
    def request(operation,params):
        c=collector.wrap(guard(op,session));r=c.request(operation,params)
        if r.get('status')!='ok':raise ValueError('named input unavailable: '+str(r.get('result',{}).get('error',r.get('status')))[:200])
        return r['result']
    allowed={'family_bindings','corridor_bindings','catalogue_region','signal_seed','bootstrap'}
    if not isinstance(inputs,dict) or set(inputs)-allowed:raise ValueError('explicit bounded named inputs required')
    a=copy.deepcopy(brief);compile_brief(a)
    follow=copy.deepcopy(follow_on_corridor);receipts={}
    if follow is not None:
        if set(follow)!={'brief','roads','whole_routes'}:raise ValueError('one explicit corridor, roads and whole-route recipe required')
        for name,selector in inputs.get('corridor_bindings',{}).items():
            if 'receipt' not in selector:continue
            if set(selector)!={'receipt'} or not isinstance(selector['receipt'],dict) or set(selector['receipt'])!={'approach','export'}:raise ValueError('explicit approach/public export receipt selector required')
            spec=selector['receipt'];ends=receipt_ends(follow['brief'],name)
            old=follow['brief']['bindings'][name]['edges']
            if spec['approach']=='self':
                _,_,track=public_export(a,spec['export']);proof=None
            else:
                value,proof=qualify_receipt(op,spec,session,ends,client=collector.wrap(guard(op,session)))
                _,_,track=receipt_source(op,spec,session,proof)
            if len(old)!=1 or any(old[0].get(k)!=track[k] for k in track):raise ValueError('receipt and selected corridor resources differ')
            if spec['approach']!='self':follow['brief']['bindings'][name]=value
            receipts[name]={'selector':copy.deepcopy(spec),'proof':proof}
        reference=reference_corridor(follow['brief'],receipts)
        compile_corridor(reference);validate_roads(reference,follow['roads'])
    bootstrap=copy.deepcopy(inputs.get('bootstrap'))
    if bootstrap is not None:
        validate_plan(bootstrap)
        if any(s['kind']!='remove' for s in bootstrap['steps']):raise ValueError('bootstrap supports explicitly authored removals only')
        if {s['chain'] for s in bootstrap['steps']}!=set(bootstrap.get('bindings',{})):raise ValueError('bootstrap inputs must be exactly its declared removal chains')
    region=inputs['catalogue_region'];vector(region['min'],3);vector(region['max'],3)
    if set(region)!={'min','max'} or any(a>=b for a,b in zip(region['min'],region['max'])):raise ValueError('finite ordered catalogue region required')
    station=normalized_station(request('station_lookup',station_parameters({'name':a['station']['name'],
        'lookup_scope':'identity_frozen','max_groups':256,'max_external_edges':16,'max_lead_distance':800,
        'max_frozen_entities':16384,'max_frozen_tracks':2048})))
    if station.get('outcome')!='resolved' or not station.get('identity_complete') or not station.get('frozen_complete'):raise ValueError('exact current station identity unavailable')
    selected=[c for c in station['constructions'] if c['resource']==a['station']['construction']['resource'] and c['position']==a['station']['construction']['position']]
    if len(selected)!=1:raise ValueError('ambiguous or missing exact station construction')
    cid=selected[0]['construction_id'];frozen={e['edge_id']:e for e in selected[0]['frozen_tracks']}
    catalogue=request('track_catalogue',{'region':region,'max_examined_edges':65536,'max_tracks':512})
    if catalogue.get('complete') is not True or catalogue.get('truncated') is not False:raise ValueError('complete bounded guide catalogue required')
    guides={e['id']:e for e in catalogue['edges']}
    if len(guides)!=len(catalogue['edges']) or len(guides)>512:raise ValueError('bounded distinct guide identities required')
    families={f['name']:f for f in a['families']};named=inputs['family_bindings']
    if set(named)-set(families):raise ValueError('unknown named input family')
    slots=[]
    for name,f in families.items():
        bindings=f['payload'].get('bindings',{});selectors=named.get(name,{})
        if set(bindings)!=set(selectors):raise ValueError('every initial family binding requires one named selector')
        slots.extend((bindings,key,selector,f['payload']) for key,selector in selectors.items())
    if follow is not None:
        bindings=follow['brief'].get('bindings',{});selectors=inputs.get('corridor_bindings',{})
        if set(bindings)!=set(selectors):raise ValueError('every corridor input requires one named selector')
        slots.extend((bindings,key,selector,None) for key,selector in selectors.items() if key not in receipts)
    elif inputs.get('corridor_bindings'):raise ValueError('corridor inputs without follow-on corridor')
    ids=set();removed=set()
    for _,_,selector,_ in slots:
        if not isinstance(selector,dict) or set(selector) not in ({'edge_id'},{'edge_id','terminal_index','end'},{'edge_id','frozen','end'}):raise ValueError('exact guide or station endpoint selector required')
        eid=selector['edge_id']
        if type(eid) is not int or eid<=0:raise ValueError('exact native input ID required')
        if 'terminal_index' in selector:
            if type(selector['terminal_index']) is not int or selector['terminal_index']<=0 or selector['end'] not in ('node0','node1'):raise ValueError('explicit station endpoint required')
            matches=terminal_component_matches(station,cid,eid)
            if len(matches)!=1 or matches[0]['terminal_index']!=selector['terminal_index'] or 'vehicle_node' not in matches[0]:raise ValueError('missing/ambiguous native terminal component endpoint')
        elif 'frozen' in selector:
            if selector['frozen'] is not True or selector['end'] not in ('node0','node1') or eid not in frozen:raise ValueError('exact selected-construction frozen endpoint required')
        elif eid not in guides or guides[eid].get('construction_owner')!='none':raise ValueError('exact external guide unavailable')
        ids.add(eid)
    if bootstrap:
        for binding in bootstrap['bindings'].values():
            for e in binding['edges']:
                if e['id'] not in guides:raise ValueError('bootstrap exact external input unavailable')
                ids.add(e['id']);removed.add(e['id'])
    if len(ids)>256:raise ValueError('named input snapshot bound256')
    snapshots={};nodes={}
    for offset in range(0,len(ids),16):
        chunk=sorted(ids)[offset:offset+16];r=request('inspect',{'edge_ids':chunk,'structures':True,'incidence_edge_ids':chunk})
        rows=r['edges'];inc=r['endpoint_incidence']
        if len(rows)!=len(chunk) or {e['id'] for e in rows}!=set(chunk) or inc.get('complete') is not True or inc.get('truncated') is not False or set(inc.get('edge_ids',[]))!=set(chunk):raise ValueError('complete exact input/incidence response required')
        expected={e[k] for e in rows for k in ('node0','node1')}
        if inc.get('node_count')!=len(inc['nodes']) or len(inc['nodes'])!=len(expected) or {n['node_id'] for n in inc['nodes']}!=expected:raise ValueError('complete exact input nodes required')
        for n in inc['nodes']:
            if not n.get('incidence_complete') or n.get('incident_output_truncated') or n['incident_count']!=len(n['incident_edges']) or len(n['incident_edges'])>16 or len(set(n['incident_edges']))!=len(n['incident_edges']):raise ValueError('bounded complete incidence required')
            if n['node_id'] in nodes and n!=nodes[n['node_id']]:raise ValueError('conflicting native incidence')
            nodes[n['node_id']]=n
        snapshots.update({e['id']:e for e in rows})
    edge_map={};node_map={}
    def update_binding(bindings,key,selector,payload):
        old=bindings[key]['edges']
        if len(old)!=1:raise ValueError('named endpoint input must be a single exact edge')
        old=old[0];new=snapshots[selector['edge_id']];same_geometry(old,new)
        station_endpoint='terminal_index' in selector or 'frozen' in selector
        if station_endpoint and {new['node0'],new['node1']}!={frozen[new['id']]['node0'],frozen[new['id']]['node1']}:raise ValueError('station snapshot differs from frozen identity')
        if new['id'] in removed:raise ValueError('required input selected for bootstrap removal')
        for old_id,new_id,mapping in [(old['id'],new['id'],edge_map)]+[(old[k],new[k],node_map) for k in ('node0','node1')]:
            if old_id in mapping and mapping[old_id]!=new_id:raise ValueError('ambiguous named identity mapping')
            mapping[old_id]=new_id
        if payload:
            for ref in payload.get('port_refs',{}).values():
                if ref['chain']!=key:continue
                node=new[ref['end']] if 'end' in ref else node_map[ref['node_id']]
                n=nodes[node]
                if station_endpoint and node!=new[selector['end']]:raise ValueError('station selector endpoint differs from declared binding')
                if set(n['incident_edges'])-removed!={new['id']} or n['construction_owner'] not in ('none',-1,0,cid if station_endpoint else -1):raise ValueError('required endpoint is not free after explicit bootstrap')
                if 'end' not in ref:ref.update(edge_id=new['id'],node_id=node)
        bindings[key]={'edges':[copy.deepcopy(new)]}
    for bindings,key,selector,payload in slots:update_binding(bindings,key,selector,payload)
    if bootstrap:
        for binding in bootstrap['bindings'].values():
            for i,old in enumerate(binding['edges']):
                new=snapshots[old['id']];same_geometry(old,new);binding['edges'][i]=copy.deepcopy(new)
    # Update only declared identity fields, never positions, tangents or budgets.
    for check in a['checks']:
        for side in ('source','target'):
            ref=check['payload'].get(side)
            if isinstance(ref,dict) and 'edge_id' in ref:
                if ref['edge_id'] not in edge_map or ref['node_id'] not in node_map:raise ValueError('unqualified check endpoint identity')
                ref.update(edge_id=edge_map[ref['edge_id']],node_id=node_map[ref['node_id']])
    seed_spec=inputs['signal_seed'];seed=request('operating_inspect',{'signal_seed':{'seed_id':seed_spec['seed_id']}})['signal_seed']
    if seed.get('id')!=seed_spec['seed_id'] or seed.get('resource')!=seed_spec['resource']:raise ValueError('explicit functional signal template differs')
    a['session']=session
    for f in a['families']:
        if f['kind']=='corridor':f['payload']['session']=session
    compile_brief(a)
    if follow:
        c=follow['brief'];c['session']=session
        for profiles in c['waypoints'].values():
            for profile in profiles.values():
                for side in ('back','front'):
                    if side in profile:
                        ref=profile[side]
                        if ref['chain'] in receipts:continue
                        ref.update(edge_id=edge_map[ref['edge_id']],node_id=node_map[ref['node_id']])
                        n=nodes[ref['node_id']]
                        if set(n['incident_edges'])-removed!={ref['edge_id']} or n['construction_owner'] not in ('none',-1,0):raise ValueError('corridor endpoint is not free after explicit bootstrap')
        for road in follow['roads']:road['seed_id']=seed['id']
        reference=reference_corridor(c,receipts);compile_corridor(reference);validate_roads(reference,follow['roads'])
        routes=follow['whole_routes']['roads']
        if not isinstance(routes,list) or not 0<=len(routes)<=4 or len({r['name'] for r in routes})!=len(routes):raise ValueError('explicit bounded whole-family road contracts required')
        for route in routes:
            if type(route['forward_root_to_main']) is not bool or route['road'] not in c['waypoints'].get(route['waypoint'],{}):raise ValueError('exact road, waypoint and direction required')
            if route.get('waypoint_side','front') not in ('front','back') or route.get('waypoint_side','front') not in c['waypoints'][route['waypoint']][route['road']]:raise ValueError('explicit existing whole-road waypoint side required')
            if not isinstance(route['new_receipt_pool'],list) or not 1<=len(route['new_receipt_pool'])<=64:raise ValueError('bounded explicit road receipt selectors required')
            if route['root_binding'] not in {f['name']+'.'+n for f in a['families'] for n in f['exports']}:raise ValueError('unknown whole-family root binding')
            for spec in route['new_receipt_pool']:
                if spec['family'] not in families or spec['step'] not in {s['name'] for s in families[spec['family']]['payload']['steps']}:raise ValueError('unknown whole-family step receipt')
                x=spec.get('extract_path',{})
                if 'target_exact_node' in x:
                    # Explicit scaffold identity is not inferred/remapped by proximity.
                    if x['target_exact_node'] in node_map and node_map[x['target_exact_node']]!=x['target_exact_node']:raise ValueError('whole-route scaffold identity changed; author fresh exact recipe')
            if any(i not in guides or i in removed for i in route['existing_scaffold_edge_ids']):raise ValueError('whole-family scaffold input unavailable')
        if len(ids|{i for r in routes for i in r['existing_scaffold_edge_ids']})>256:raise ValueError('prepared dependency snapshot bound256')
    guard(op,session)
    plan={'approach':a,'bootstrap':bootstrap,'follow_on':follow,'guides':catalogue['edges'],
          'signal_seed':{'id':seed['id'],'resource':seed['resource']},
          'input_hash':digest(inputs),'source_hash':digest(brief),'session':session}
    if receipts:plan['corridor_receipts']=receipts
    run=uuid.uuid4().hex[:16];folder=op.path(run);folder.mkdir()
    live.atomic_json(folder/'prepared_approach.json',plan)
    live.atomic_json(folder/'state.json',{'kind':'prepared_approach','status':'prepared','session':session,'plan_hash':digest(plan),
        'stage':0,'children':{},'whole_checks':{},'preparation':{'request_counts':collector.counts.get('active',{}),'active_wall_seconds':time.monotonic()-start}})
    return status(op,run)


def status(op,run):
    s=read(op.path(run)/'state.json')
    return {k:s[k] for k in ('status','session','stage','children','error','preparation') if k in s}|{'run':run,'whole_checks':len(s.get('whole_checks',{})),'game_constructed':s.get('game_constructed',False)}


def qualify_inputs(op,plan,*,after_bootstrap,completed_removals=frozenset()):
    """Prediction before removal never substitutes for actual surviving incidence."""
    removed={e['id'] for b in (plan['bootstrap'] or {}).get('bindings',{}).values() for e in b['edges']}
    expected={};ends=[]
    def add(row):
        old=expected.get(row['id'])
        if old is not None:
            same_geometry(old,row)
            if any(old[k]!=row[k] for k in ('node0','node1')):raise ValueError('conflicting prepared input')
        else:expected[row['id']]=row
    for f in plan['approach']['families']:
        p=f['payload']
        for b in p.get('bindings',{}).values():
            for e in b['edges']:add(e)
        for ref in p.get('port_refs',{}).values():
            if ref['chain'] not in p.get('bindings',{}):continue
            row=p['bindings'][ref['chain']]['edges'][0]
            ends.append((row['id'],row[ref['end']] if 'end' in ref else ref['node_id']))
    if plan['follow_on']:
        c=plan['follow_on']['brief']
        for name,b in c.get('bindings',{}).items():
            if name in plan.get('corridor_receipts',{}):continue
            for e in b['edges']:add(e)
        for profiles in c['waypoints'].values():
            for profile in profiles.values():
                ends.extend((profile[side]['edge_id'],profile[side]['node_id']) for side in ('back','front') if side in profile and profile[side]['chain'] not in plan.get('corridor_receipts',{}))
        guides={e['id']:e for e in plan['guides']}
        for r in plan['follow_on']['whole_routes']['roads']:
            for eid in r['existing_scaffold_edge_ids']:add(guides[eid])
    if not after_bootstrap:
        for b in (plan['bootstrap'] or {}).get('bindings',{}).values():
            for e in b['edges']:
                if e['id'] not in completed_removals:add(e)
    ids=sorted(expected)
    for offset in range(0,len(ids),16):
        chunk=ids[offset:offset+16]
        response=guard(op,plan['session']).request('inspect',{'edge_ids':chunk,'structures':True,'incidence_edge_ids':chunk})
        if response.get('status')!='ok':raise ValueError('fresh prepared inputs unavailable')
        value=response['result'];rows=value['edges'];inc=value['endpoint_incidence']
        if len(rows)!=len(chunk) or {e['id'] for e in rows}!=set(chunk) or inc.get('complete') is not True or inc.get('truncated') is not False:raise ValueError('fresh complete prepared inputs required')
        for e in rows:
            old=expected[e['id']];same_geometry(old,e)
            if any(e[k]!=old[k] for k in ('node0','node1')):raise ValueError('prepared native attachment identity changed')
        nodes={n['node_id']:n for n in inc['nodes']}
        for eid,node in ends:
            if eid not in chunk:continue
            n=nodes[node];incident=n['incident_edges']
            if n.get('incidence_complete') is not True or n.get('incident_output_truncated') or n['incident_count']!=len(incident) or len(incident)>16:raise ValueError('fresh complete attachment incidence required')
            # Before removal this is only a prediction. After it the actual
            # current incidence must stand alone; no vanished IDs are subtracted.
            if set(incident)-(set() if after_bootstrap else removed)!={eid}:raise ValueError('prepared attachment is not actually free' if after_bootstrap else 'bootstrap does not release prepared attachment')
    seed=plan['signal_seed']
    r=guard(op,plan['session']).request('operating_inspect',{'signal_seed':{'seed_id':seed['id']}})
    if r.get('status')!='ok' or any(r['result']['signal_seed'].get(k)!=seed[k] for k in ('id','resource')):raise ValueError('prepared signal seed changed')


def bootstrap_continuation(op,parent,child,session):
    """Adopt only the unchanged remaining declared removals, never a new plan."""
    old=read(op.path(parent)/'plan.json');state=read(op.path(parent)/'state.json')
    new=read(op.path(child)/'plan.json');validate_plan(new)
    child_state=read(op.path(child)/'state.json')
    if child_state.get('plan_hash')!=digest(new) or child_state.get('status') not in ('planned','built'):raise ValueError('bootstrap continuation child changed or unfinished')
    if state.get('status') not in ('needs_attention','built') or (state.get('status')=='needs_attention' and not no_step_effects(state)):raise ValueError('bootstrap uncertain effects require reconciliation')
    link=new.get('continuation',{})
    if state['plan_hash']!=digest(old) or state.get('session')!=session or link.get('run')!=parent or link.get('state_hash')!=digest(state) or link.get('session')!=session:raise ValueError('bootstrap continuation ownership/hash/session differs')
    done=set(state['steps']);steps={s['name']:s for s in old['steps']}
    if done-set(steps) or any(v.get('status')!='built' for v in state['steps'].values()) or set(link.get('skipped_steps',[]))!=done:raise ValueError('bootstrap completed removal proof unavailable')
    remaining=[s for s in old['steps'] if s['name'] not in done]
    if not remaining or new['steps']!=remaining or any(s['kind']!='remove' for s in remaining):raise ValueError('bootstrap continuation changes approved remaining removals')
    ignored={'version','revision','steps','bindings','continuation'}
    # Existing continue_plan adds these empty metadata maps when no roles apply.
    empty={'port_refs','role_refs','interface_bindings','role_bindings','result_bindings'}
    for key in (set(old)|set(new))-ignored:
        if key in empty and not old.get(key) and not new.get(key):continue
        if old.get(key)!=new.get(key):raise ValueError('bootstrap continuation changes approved contract')
    chains={s['chain'] for s in remaining}
    if set(new.get('bindings',{}))!=chains:raise ValueError('bootstrap continuation bindings differ')
    for name in chains:
        previous=old['bindings'][name]['edges'];rows=new['bindings'][name]['edges']
        if len(rows)!=len(previous):raise ValueError('bootstrap continuation edge set differs')
        for a,b in zip(previous,rows):
            same_geometry(a,b)
            if any(a[k]!=b[k] for k in ('id','node0','node1')):raise ValueError('bootstrap continuation exact identity differs')
    return {e['id'] for name in done for e in old['bindings'][steps[name]['chain']]['edges']}


def materialize_corridor(op,folder,plan,approach_run):
    """One immutable concrete child brief, after declared receipts exist."""
    path=folder/'materialized_corridor.json';checked=set()
    if path.exists():
        record=read(path)
        if record['prepared_hash']!=digest(plan):raise ValueError('materialized corridor scope changed')
        # No corridor child existed yet; requalify the frozen endpoints without
        # substituting a newer export. Once a child exists this path is not run.
        declared=plan.get('corridor_receipts',{})
        if set(record['provenance'])!=set(declared):raise ValueError('materialized receipt provenance differs')
        expected=copy.deepcopy(plan['follow_on']['brief'])
        for name,value in record['provenance'].items():
            selector=copy.deepcopy(declared[name]['selector'])
            if selector['approach']=='self':selector['approach']=approach_run
            if value['selector']!=selector or (declared[name]['proof'] is not None and value['proof']!=declared[name]['proof']):raise ValueError('materialized receipt source changed')
            binding,_,_=receipt_source(op,selector,plan['session'],value['proof'])
            rows=record['brief']['bindings'][name]['edges'];old=binding['edges'][0]
            if len(rows)!=1 or any(rows[0][k]!=old[k] for k in ('id','node0','node1')):raise ValueError('frozen receipt identity differs')
            same_geometry(old,rows[0]);expected['bindings'][name]=copy.deepcopy(record['brief']['bindings'][name])
        if reference_corridor(expected,declared)!=record['brief']:raise ValueError('frozen authored corridor controls changed')
        brief=record['brief']
    else:
        brief=copy.deepcopy(plan['follow_on']['brief']);proofs={}
        for name,value in plan.get('corridor_receipts',{}).items():
            selector=copy.deepcopy(value['selector'])
            if selector['approach']=='self':selector['approach']=approach_run
            binding,proof=qualify_receipt(op,selector,plan['session'],receipt_ends(brief,name),value['proof'])
            expected=brief['bindings'][name]['edges'][0];row=binding['edges'][0]
            if any(expected.get(k)!=row.get(k) for k in ('template','style')):raise ValueError('materialized receipt resources differ')
            brief['bindings'][name]=binding;proofs[name]={'selector':selector,'proof':proof}
            checked.add(name)
        brief=reference_corridor(brief,plan.get('corridor_receipts',{}));compile_corridor(brief);validate_roads(brief,plan['follow_on']['roads'])
        record={'prepared_hash':digest(plan),'brief':brief,'provenance':proofs}
        live.atomic_json(path,record)
    # Existing concrete inputs and receipt endpoints all need current free
    # incidence immediately before publishing the single corridor child.
    refs={}
    for profiles in brief['waypoints'].values():
        for profile in profiles.values():
            for side in ('back','front'):
                ref=profile.get(side)
                if ref:refs.setdefault(ref['chain'],set()).add(ref['node_id'])
    for name,ends in refs.items():
        if name in checked:continue
        rows=fresh_binding(guard(op,plan['session']),brief['bindings'][name]);ids=[e['id'] for e in rows]
        r=guard(op,plan['session']).request('inspect',{'edge_ids':ids,'structures':True,'incidence_edge_ids':ids})
        inc=r.get('result',{}).get('endpoint_incidence',{});nodes={n['node_id']:n for n in inc.get('nodes',[])}
        if r.get('status')!='ok' or inc.get('complete') is not True or inc.get('truncated') is not False:raise ValueError('fresh concrete corridor incidence required')
        for node in ends:
            selected=[e['id'] for e in rows if node in (e['node0'],e['node1'])];n=nodes[node]
            if len(selected)!=1 or n.get('incidence_complete') is not True or n.get('incident_output_truncated') or n.get('incident_count')!=1 or n.get('incident_edges')!=selected or n.get('construction_owner') not in ('none',-1,0):raise ValueError('concrete corridor endpoint occupied')
    return record


def whole_queries(op,approach_run,plan,corridor_run):
    """Explicit per-road known receipt pools; no world graph or proximity matching."""
    s=read(op.path(approach_run)/'state.json')
    if s['status'] not in ('built','reviewed'):raise ValueError('completed approach required for whole-family checks')
    recipe=plan['follow_on']['whole_routes'];guides={e['id']:e for e in plan['guides']};out=[];qualified={}
    link=read(op.path(corridor_run)/'state.json')
    concrete=read(op.path(corridor_run)/'corridor.json')['brief']
    def binding(family,name):
        child=s['families'][family]['run'];cs=read(op.path(child)/'state.json')
        value=exported_binding(op,child,cs,name)
        if not value or not value.get('edges'):raise ValueError('exact whole-family receipt unavailable')
        return value['edges']
    def node(family,name,end):
        rows=binding(family,name)
        if len(rows)!=1:raise ValueError('single-edge whole-family endpoint required')
        return rows[0][end]
    if not isinstance(recipe['roads'],list) or not 0<=len(recipe['roads'])<=4:raise ValueError('explicit bounded whole-family roads required')
    for road in recipe['roads']:
        roots=s['bindings'][road['root_binding']]['edges']
        if len(roots)!=1:raise ValueError('exact whole-family root required')
        root=roots[0];label=road['road'];ref=concrete['waypoints'][road['waypoint']][label][road.get('waypoint_side','front')]
        # Completion readback is authoritative after signal replacement.
        selected=[r for r in plan['follow_on']['roads'] if r['track']==label]
        if len(selected)!=1:raise ValueError('exact named completion road required')
        progress=link['completion']['roads'][selected[0]['name']];current=progress['edges']
        replacements={p['replaced_edge']:p['replacement_edge'] for p in progress['placements']}
        def latest(ident):
            seen=set()
            while ident in replacements:
                if ident in seen:raise ValueError('cyclic signal replacement identity')
                seen.add(ident);ident=replacements[ident]
            return ident
        live_rows={e['id']:e for e in current}
        main=[e for e in current if e['id']==latest(ref['edge_id']) and ref['node_id'] in (e['node0'],e['node1'])]
        if len(main)!=1:raise ValueError('follow-on interface changed; explicit reconciliation required')
        pool={}
        def add(rows):
            for e in rows:
                if latest(e['id'])!=e['id']:e=live_rows[latest(e['id'])]
                # Native IDs may be reused after demolition. Fresh owned
                # receipts define the new generation; do not blacklist integers.
                if e['id'] in pool and any(pool[e['id']][k]!=e[k] for k in ('node0','node1','p0','p1','t0','t1','template','style')):raise ValueError('conflicting receipt identity')
                pool[e['id']]=e
        for spec in road['new_receipt_pool']:
            rows=binding(spec['family'],spec['step']);x=spec.get('extract_path')
            if x:
                start=node(spec['family'],x['source_binding'],x['source_end'])
                finish=node(spec['family'],x['target_step'],x['target_end']) if 'target_step' in x else x['target_exact_node']
                rows=ordered_path(rows,start,finish)
            add(rows)
        add([guides[i] for i in road['existing_scaffold_edge_ids']])
        if len(pool)>256:raise ValueError('whole-family receipt pool bound256')
        path=ordered_path(list(pool.values()),root['node0'],ref['node_id'])
        if len(path)!=len(pool) or path[0]['id']!=root['id'] or path[-1]['id']!=main[0]['id']:raise ValueError('explicit road pool is not the exact whole-family path')
        for e in path:
            old=qualified.get(e['id'])
            if old:
                same_geometry(old,e)
                if any(old[k]!=e[k] for k in ('node0','node1')):raise ValueError('conflicting whole-road attachment')
            qualified[e['id']]=e
        a=(root['id'],root['node0']);b=(main[0]['id'],ref['node_id']);ids=[e['id'] for e in path]
        if not road['forward_root_to_main']:a,b=b,a;ids.reverse()
        out.append((road['name'],{'source_edge':a[0],'source_node':a[1],'target_edge':b[0],'target_node':b[1],
            'required_edges':ids,'mode':'TRAIN','max_length':5000,'max_path_entries':256}))
    if len(qualified)>256:raise ValueError('whole-road current snapshot bound256')
    ids=sorted(qualified)
    for offset in range(0,len(ids),16):
        chunk=ids[offset:offset+16];r=guard(op,plan['session']).request('inspect',{'edge_ids':chunk,'structures':True})
        rows=r.get('result',{}).get('edges',[])
        if r.get('status')!='ok' or len(rows)!=len(chunk) or {e['id'] for e in rows}!=set(chunk):raise ValueError('current whole-road geometry unavailable')
        for e in rows:
            old=qualified[e['id']];same_geometry(old,e)
            if any(old[k]!=e[k] for k in ('node0','node1')):raise ValueError('whole-road exact attachment changed')
    return out


def build(op,run,*,continuing=False,bootstrap_run=None,family_run=None,section_run=None):
    folder=op.path(run);plan=read(folder/'prepared_approach.json');s=read(folder/'state.json')
    if s.get('kind')!='prepared_approach' or digest(plan)!=s['plan_hash']:raise ValueError('prepared scope changed')
    guard(op,s['session'])
    for supplied,stage in ((bootstrap_run,0),(family_run,1),(section_run,3)):
        if supplied is not None and (not continuing or s['stage']!=stage):raise ValueError('explicit child continuation supplied for wrong stage')
    if bootstrap_run is not None and not plan['bootstrap']:raise ValueError('no bootstrap continuation in approved flow')
    if section_run is not None and not plan['follow_on']:raise ValueError('no corridor continuation in approved flow')
    if s['status']=='completed':return status(op,run)
    if s['status']!='prepared' and not continuing:raise ValueError('prepared workflow already attempted; explicit continuation required')
    lock=folder/'prepared.lock'
    with lock.open('x'):pass
    def persist():live.atomic_json(folder/'state.json',s)
    stage_started=None;before={}
    def counts():
        collector=getattr(op,'_phase_collector',None)
        return dict(collector.counts.get('active',{})) if collector else {}
    def measured(outcome):
        if stage_started is None:return
        current=counts();entry=s.setdefault('stage_metrics',{}).setdefault(str(stage),{})
        for key,value in {'active_wall_seconds':time.monotonic()-stage_started,
                          'request_attempts':current.get('requests',0)-before.get('requests',0),
                          'mutation_request_attempts':current.get('mutations',0)-before.get('mutations',0)}.items():entry[key]=entry.get(key,0)+value
        entry.update(attempts=entry.get('attempts',0)+1,outcome=outcome)
    try:
        s.update(status='running',game_constructed='unknown');s.pop('error',None);persist()
        while s['stage']<6:
            guard(op,s['session']);stage=s['stage'];children=s['children'];stage_started=time.monotonic();before=counts()
            if stage==0 and plan['bootstrap']:
                if 'bootstrap' not in children:children['bootstrap']=op.plan(plan['bootstrap'])['run'];persist()
                if bootstrap_run:
                    completed=bootstrap_continuation(op,children['bootstrap'],bootstrap_run,s['session'])
                    s['completed_bootstrap_removals']=sorted(set(s.get('completed_bootstrap_removals',[]))|completed)
                    children['bootstrap']=bootstrap_run;persist();bootstrap_run=None
                child=children['bootstrap'];cs=read(op.path(child)/'state.json')
                if cs['status']=='planned':
                    qualify_inputs(op,plan,after_bootstrap=False,completed_removals=set(s.get('completed_bootstrap_removals',[])))
                    op.execute(child)
                if read(op.path(child)/'state.json')['status']!='built':raise ValueError('bootstrap requires existing reconciliation/continuation')
            elif stage==1:
                if 'approach' not in children:
                    qualify_inputs(op,plan,after_bootstrap=True)
                    children['approach']=op.plan_approach(plan['approach'])['run'];persist()
                child=children['approach'];cs=read(op.path(child)/'state.json')
                if family_run is not None and cs['status'] not in ('running','needs_attention'):raise ValueError('no stopped approach child to replace')
                if cs['status']=='planned':r=op.build_approach(child)
                elif cs['status'] in ('built','reviewed'):r={'status':cs['status']}
                elif continuing:r=op.continue_approach(child,family_run=family_run);family_run=None
                else:raise ValueError('approach requires explicit continuation')
                if r['status'] not in ('built','reviewed'):raise ValueError('approach needs_attention')
                s['game_constructed']=True
            elif stage==2:
                if op.review_approach(children['approach'])['status']!='reviewed':raise ValueError('approach checks failed')
            elif stage==3 and plan['follow_on']:
                if 'corridor' not in children:
                    if plan.get('corridor_receipts'):
                        frozen=materialize_corridor(op,folder,plan,children['approach'])
                        s['materialized_corridor_hash']=digest(frozen);persist();concrete=frozen['brief']
                    else:concrete=plan['follow_on']['brief']
                    children['corridor']=op.plan_corridor(concrete)['run'];persist()
                if plan.get('corridor_receipts'):
                    frozen=read(folder/'materialized_corridor.json')
                    if digest(frozen)!=s.get('materialized_corridor_hash') or frozen['prepared_hash']!=digest(plan) or read(op.path(children['corridor'])/'corridor.json')['brief']!=frozen['brief']:raise ValueError('frozen corridor/child scope changed')
                child=children['corridor'];cs=read(op.path(child)/'state.json')
                if section_run is not None and cs['status'] not in ('running','needs_attention'):raise ValueError('no stopped corridor child to replace')
                if cs['status']=='planned':r=op.build_corridor(child)
                elif cs['status']=='built':r={'status':'built'}
                elif continuing:r=op.continue_corridor(child,section_run=section_run);section_run=None
                else:raise ValueError('corridor requires explicit continuation')
                if r['status']!='built':raise ValueError('corridor needs_attention')
            elif stage==4 and plan['follow_on']:
                child=children['corridor'];cs=read(op.path(child)/'state.json')
                if 'completion' not in cs:op.attach_corridor_completion(child,plan['follow_on']['roads'])
                if op.complete_corridor(child,continuing=continuing)['completion']['status']!='completed':raise ValueError('corridor completion needs_attention')
            elif stage==5 and plan['follow_on']:
                # A stopped run may have been manually edited/reconciled. Cached
                # pass names are historical evidence, never current acceptance.
                s['whole_checks']={};persist()
                for name,q in whole_queries(op,children['approach'],plan,children['corridor']):
                    r=guard(op,s['session']).request('route',q);v=r.get('result',{})
                    passed=r.get('status')=='ok' and v.get('native_path_found') is True and v.get('requested_route_verified') is True and v.get('truncated',False) is False
                    s['whole_checks'][name]={'passed':passed,'request_id':r.get('request_id')};persist()
                    if not passed:raise ValueError('whole-family directed query failed')
            measured('completed');stage_started=None;s['stage']+=1;persist()
        s['status']='completed';persist()
    except Exception as exc:measured('needs_attention');s.update(status='needs_attention',error=str(exc)[:350]);persist()
    finally:lock.unlink()
    return status(op,run)
