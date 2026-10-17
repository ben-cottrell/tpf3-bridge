"""Offline combined family diagrams; controls are evidence, never a native fit."""
import copy
import json
import math
from pathlib import Path

from bridge_operator import render, render_profile, unit, vector

COLORS={'authored':'#d97706','preview':'#7c3aed','committed':'#193950'}
ROLES={'rail','signal','merge','deck','ramp','interface','guide'}


def render_approach(source,output,*,operator=None,families=None,controls=None,
                    profile_axis=(1,0),profile_exaggeration=4):
    """Read an approach file/job and optional world/local full-controls packet.

    No client access or state writes. Recorded committed rows are not fresh readback.
    Missing controls stay missing rather than being inferred from attachment hints.
    """
    state={}
    if isinstance(source,dict):brief=copy.deepcopy(source)
    elif Path(source).is_file():brief=json.loads(Path(source).read_text(encoding='utf-8-sig'))
    elif operator is not None:
        from bridge_approach import record
        _,brief,state=record(operator,source)
    else:raise ValueError('existing approach file or job required')
    if not isinstance(brief.get('families'),list) or not 1<=len(brief['families'])<=8:raise ValueError('bounded approach families required')
    names=[f['name'] for f in brief['families']]
    selected=names if families is None else families
    if not isinstance(selected,list) or not selected or len(selected)!=len(set(selected)) or set(selected)-set(names):raise ValueError('select distinct existing families')
    axis=unit(list(profile_axis))
    if type(profile_exaggeration) not in (int,float) or not math.isfinite(profile_exaggeration) or not .1<=profile_exaggeration<=20:raise ValueError('bounded profile exaggeration required')
    plan={'title':'Combined approach','revision':brief['revision'],'origin':[0,0,0],
          'ports':{},'curves':{},'profile_axis':axis,'profile_exaggeration':profile_exaggeration,
          'diagram_compact':True,
          'diagram_legend':'orange authored · purple preview · navy recorded committed; thick deck, dashed ramp; shared scale'}
    origins={f['name']:f['payload'].get('origin',[0,0,0]) for f in brief['families']}
    for origin in origins.values():vector(origin,3)
    missing=[];covered=set();seen=set()
    def position(p,family,frame):
        vector(p,3)
        if frame not in ('world','local'):raise ValueError('explicit world/local coordinate frame required')
        return [p[i]+(origins[family][i] if frame=='local' else 0) for i in range(3)]
    def curve(row):
        family=row['family'];epoch=row['epoch'];role=row.get('role','rail');name=row['name']
        if family not in names or epoch not in COLORS or role not in ROLES:raise ValueError('known family, evidence epoch and role required')
        if family not in selected:return
        if not isinstance(name,str) or not 1<=len(name)<=160:raise ValueError('bounded curve name required')
        c={k:position(row[k],family,row['frame']) if k in ('p0','p1') else list(row[k]) for k in ('p0','p1','t0','t1')}
        for v in c.values():vector(v,3)
        key=(family,epoch,name)
        if key in seen:raise ValueError('duplicate family/evidence curve name')
        seen.add(key);covered.add((family,name))
        c.update(diagram_color=COLORS[epoch],diagram_role=role,diagram_label=f'{family}/{name} [{epoch}; {role}]')
        plan['curves']['/'.join(key)]=c
        if len(plan['curves'])>256:raise ValueError('diagram bound256 curves exceeded')
    def marker(row):
        family=row['family'];kind=row['kind'];name=row['name']
        if family not in names or kind not in ROLES:raise ValueError('known marker family/kind required')
        if family not in selected:return
        if not isinstance(name,str) or not 1<=len(name)<=160:raise ValueError('bounded marker name required')
        key=f'{family}/{kind}/{name}'
        if key in plan['ports']:raise ValueError('duplicate marker name')
        plan['ports'][key]={'position':position(row['position'],family,row['frame']),'label':True,'diagram_marker':True,'diagram_kind':kind}
        if len(plan['ports'])>256:raise ValueError('diagram bound256 markers exceeded')
    for f in brief['families']:
        if f['name'] not in selected:continue
        family=f['name'];p=f['payload']
        for name,c in p.get('curves',{}).items():curve(c|{'family':family,'name':name,'epoch':'authored','frame':'local'})
        for name,v in p.get('ports',{}).items():marker({'family':family,'kind':'interface','name':name,'position':v['position'],'frame':'local'})
        for waypoint,roads in p.get('waypoints',{}).items():
            for road,v in roads.items():
                if 'position' in v:marker({'family':family,'kind':'guide','name':waypoint+'/'+road,'position':v['position'],'frame':'world'})
    if controls is not None:
        if isinstance(controls,(str,Path)):controls=json.loads(Path(controls).read_text(encoding='utf-8-sig'))
        if set(controls)-{'version','curves','markers'} or controls.get('version')!=1:raise ValueError('version1 controls packet required')
        for key in ('curves','markers'):
            if not isinstance(controls.get(key,[]),list) or len(controls.get(key,[]))>256:raise ValueError('bounded controls packet required')
        for row in controls.get('curves',[]):curve(row)
        for row in controls.get('markers',[]):marker(row)
    observed=set()
    for ref,value in state.get('bindings',{}).items():
        family=ref.split('.')[0]
        if family not in selected:continue
        for e in value.get('edges',[]):
            key=(family,e['id'])
            if key in observed:continue
            observed.add(key)
            curve(e|{'family':family,'name':'native_'+str(e['id']),'frame':'world','epoch':'committed',
                     'role':'deck' if (e.get('structure') or {}).get('classification')=='BRIDGE' else 'rail'})
    for f in brief['families']:
        if f['name'] not in selected:continue
        for step in f['payload'].get('steps',[]):
            if step['kind'] not in ('signal_chain','signal_batch') and (f['name'],step['name']) not in covered:
                missing.append(f['name']+'/'+step['name'])
        if f['kind']=='corridor' and not any(f['name']==k[0] for k in seen):missing.append(f['name']+'/section_controls')
    points=[v['position'] for v in plan['ports'].values()]
    for c in plan['curves'].values():
        points.extend((c['p0'],c['p1'],[c['p0'][i]+c['t0'][i]/3 for i in range(3)],[c['p1'][i]-c['t1'][i]/3 for i in range(3)]))
    if not points:raise ValueError('no full controls or interface positions to render')
    spans=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
    projected=[sum(p[i]*axis[i] for i in range(2)) for p in points]
    scale=min(1080/max(spans[0],1),410/max(spans[1],1),
              1060/max(max(projected)-min(projected),1),300/max(spans[2]*profile_exaggeration,1))
    folder=Path(output);folder.mkdir(parents=True,exist_ok=False)
    render(plan,[],folder/'plan.svg',horizontal_scale=scale)
    render_profile(plan,[],folder/'profile.svg',horizontal_scale=scale)
    # A current rendering packet, not acceptance or a permanent execution history.
    (folder/'controls.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    return {'status':'ok','plan':str(folder/'plan.svg'),'profile':str(folder/'profile.svg'),
            'controls':str(folder/'controls.json'),'families':selected,'curve_count':len(plan['curves']),
            'marker_count':len(plan['ports']),'horizontal_scale':scale,'missing_control_count':len(missing),
            'missing_controls':missing[:8],'missing_controls_truncated':len(missing)>8,
            'native_fit_verified':False,'fresh_readback':False}
