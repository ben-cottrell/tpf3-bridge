"""Bounded corridor-family search over a declared synthetic terrain.

Terrain quantities are midpoint-grid planning estimates, NOT structural designs.
No station internals are regenerated. Required endpoint interfaces are immutable.
"""
from __future__ import annotations
from copy import deepcopy
import itertools
import json
import math
from pathlib import Path
from .geometry import Alignment, Knot, digest, integer, number, limits_check
from railops.uk_profiles import gb_track_centres

VERSION='0.9.0'


def closed(record, keys, name):
    if not isinstance(record,dict) or set(record)!=set(keys):
        raise ValueError(f'{name}: expected fields {sorted(keys)}')


def parse_json(path):
    p=Path(path)
    if p.stat().st_size>2000000:raise ValueError('fixture exceeds byte budget')
    def obj(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    def bad(v):raise ValueError('nonfinite JSON literal')
    return json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=obj,parse_constant=bad)


def validate_fixture(data):
    data=deepcopy(data)
    closed(data,{'schema_version','fidelity','corridor','profile','terrain','civil','search',
                 'junction','mock'},'fixture')
    if data['schema_version']!=VERSION or data['fidelity']!='gb_reference_inspired_synthetic_terrain':
        raise ValueError('unsupported fixture version/fidelity')
    c=data['corridor']; closed(c,{'length_m','end_height_m','track_centres_m','gate_x_m','site','forbidden'},'corridor')
    number(c['length_m'],'length',minimum=1000,maximum=100000)
    number(c['end_height_m'],'height',minimum=-1000,maximum=10000)
    number(c['track_centres_m'],'centres',minimum=2.8,maximum=10)
    if not isinstance(c['gate_x_m'],list) or len(c['gate_x_m'])!=3:raise ValueError('three interior x gates')
    xs=[0]+c['gate_x_m']+[c['length_m']]
    for x in xs:number(x,'gate',minimum=0,maximum=c['length_m'])
    if any(b-a<100 for a,b in zip(xs,xs[1:])):raise ValueError('interior gates must increase >=100m')
    def box(v):
        if not isinstance(v,list) or len(v)!=4:raise ValueError('box xmin,ymin,xmax,ymax')
        for x in v:number(x,'box',minimum=-1e6,maximum=1e6)
        if v[2]<=v[0] or v[3]<=v[1]:raise ValueError('empty/reversed box')
    box(c['site'])
    if not isinstance(c['forbidden'],list) or len(c['forbidden'])>100:raise ValueError('forbidden boxes')
    for b in c['forbidden']:box(b)
    t=data['terrain'];closed(t,{'base_height_m','ridge_x_m','ridge_half_x_m','ridge_half_y_m','ridge_height_m',
                               'river_x0_m','river_x1_m','water_level_m','river_bed_m','revision'},'terrain')
    for k,v in t.items():
        if k=='revision':
            if not isinstance(v,str) or not v or len(v)>100:raise ValueError('terrain revision')
        else:number(v,k,minimum=-1e5,maximum=1e5)
    if min(t['ridge_half_x_m'],t['ridge_half_y_m'])<=0 or t['ridge_height_m']<0:raise ValueError('ridge domain')
    if not 0<t['river_x0_m']<t['river_x1_m']<c['length_m']:raise ValueError('river bounds')
    if t['river_bed_m']>=t['water_level_m']:raise ValueError('river bed must be below water')
    ci=data['civil'];closed(ci,{'formation_width_m','rail_to_formation_m','side_slope_hv',
                             'max_open_cut_m','max_embankment_m','deck_depth_m','water_freeboard_m','grid_step_m'},'civil')
    for k,v in ci.items():number(v,k,minimum=.001,maximum=1000)
    if ci['grid_step_m']<1:raise ValueError('terrain estimate step >=1m')
    s=data['search'];closed(s,{'lateral_offsets_m','plateau_heights_m','candidate_budget','polyline_tolerance_m'},'search')
    for k in ('lateral_offsets_m','plateau_heights_m'):
        if not isinstance(s[k],list) or not 1<=len(s[k])<=20:raise ValueError('bounded search axis')
        for x in s[k]:number(x,k,minimum=-1000,maximum=1000)
        if len(set(s[k]))!=len(s[k]):raise ValueError('duplicate search value')
    integer(s['candidate_budget'],'candidate_budget',maximum=400)
    number(s['polyline_tolerance_m'],'polyline tolerance',minimum=.00001,maximum=.1)
    j=data['junction'];closed(j,{'crossing_x_m','height_m','ramp_lengths_m','plateau_m','max_grade',
                                'min_vertical_radius_m','lower_envelope_m','electrification_m',
                                'deck_depth_m','allowance_m','track_half_width_m','train_length_m'},'junction')
    for k,v in j.items():
        if k=='ramp_lengths_m':
            if not isinstance(v,list) or not 1<=len(v)<=10:raise ValueError('ramp grid')
            for r in v:number(r,'ramp',minimum=1,maximum=10000)
        else:number(v,k,minimum=.00001,maximum=100000)
    if not c['gate_x_m'][-1]<j['crossing_x_m']<c['length_m']:raise ValueError('crossing needs final straight corridor zone')
    m=data['mock'];closed(m,{'polyline_tolerance_m','realised_tolerance_m','batch_length_m'},'mock')
    for k,v in m.items():number(v,k,minimum=.001,maximum=1000)
    # Compile a zero-offset family to reuse profile domain validation.
    limits_check(make_alignment(data,0,c['end_height_m']),c['track_centres_m'],data['profile'])
    return data


def make_alignment(fixture, lateral, height):
    c=fixture['corridor']; a,b,d=c['gate_x_m'];e=c['end_height_m']
    return Alignment((Knot(0,0,e),Knot(a,lateral,height),Knot(b,lateral,height),
                      Knot(d,0,e),Knot(c['length_m'],0,e)))


def bell(t): return (1-t*t)**3 if abs(t)<1 else 0.0


def ground(t,x,y):
    if t['river_x0_m']<=x<=t['river_x1_m']: return t['river_bed_m']
    return t['base_height_m']+t['ridge_height_m']*bell((x-t['ridge_x_m'])/t['ridge_half_x_m'])*bell(y/t['ridge_half_y_m'])


def site_check(a,spacing,site,forbidden,formation_width):
    """Monotonic span boxes enclose whole reference formation and both tracks.

    Endpoint x allowance is omitted only at authorised external interfaces; for
    this family's zero-heading ends, normal offsets have exactly the same x.
    Other span enclosures are conservative, never sampling-only passes.
    """
    pad=max(spacing/2,formation_width/2)
    failures=[]; possible=[]; witnesses=[]
    for p,q in zip(a.knots,a.knots[1:]):
        xpad=spacing/2 if p.y!=q.y else 0
        xmin=p.x if p==a.knots[0] else p.x-xpad
        xmax=q.x if q==a.knots[-1] else q.x+xpad
        box=(xmin,min(p.y,q.y)-pad,xmax,max(p.y,q.y)+pad)
        if not (site[0]<=box[0] and site[1]<=box[1] and box[2]<=site[2] and box[3]<=site[3]):
            failures.append({'reason':'containment_not_certified','segment':[p.x,q.x],'box':box})
        for n,r in enumerate(forbidden):
            # Restrict the monotone y range to obstacle's longitudinal interval.
            lo=max(p.x,r[0]-xpad);hi=min(q.x,r[2]+xpad)
            if hi<lo:continue
            y0=a.state(lo)['y'];y1=a.state(hi)['y'];low=min(y0,y1)-pad;high=max(y0,y1)+pad
            if high<r[1] or low>r[3]:continue
            possible.append(n)
            for x in (lo,(lo+hi)/2,hi):
                st=a.state(x)
                if r[0]<=x<=r[2] and r[1]-pad<=st['y']<=r[3]+pad:
                    witnesses.append({'obstacle':n,'x':x,'y':st['y'],'model':'formation strip'})
    return {'status':'project_site_screen_pass' if not failures and not possible else 'site_constraint_unresolved_or_failed',
            'enclosure_failures':failures,'possible_obstacles':sorted(set(possible)),
            'actual_formation_witnesses':witnesses,'scope':'plan formation reservation; no earthwork toe or full vehicle envelope'}


def terrain_assessment(a,fixture):
    t=fixture['terrain'];c=fixture['civil'];spacing=fixture['corridor']['track_centres_m']
    step=c['grid_step_m'];breaks={k.x for k in a.knots}
    breaks.update((t['river_x0_m'],t['river_x1_m']))
    for p,q in zip(a.knots,a.knots[1:]):
        n=math.ceil((q.x-p.x)/step)
        breaks.update(p.x+(q.x-p.x)*i/n for i in range(n+1))
    xs=sorted(breaks);rows=[];lengths={k:0. for k in ('surface','cutting','embankment','river_bridge','viaduct','tunnel')}
    cut=fill=0.;bridge_failures=[]
    for x0,x1 in zip(xs,xs[1:]):
        x=(x0+x1)/2;st=a.state(x);y=st['y'];z=st['z'];g=ground(t,x,y)
        wet=t['river_x0_m']<=x<=t['river_x1_m'];h=z-c['rail_to_formation_m']-g
        if wet:kind='river_bridge'
        elif h>c['max_embankment_m']:kind='viaduct'
        elif -h>c['max_open_cut_m']:kind='tunnel'
        elif h>.5:kind='embankment'
        elif h<-.5:kind='cutting'
        else:kind='surface'
        dl=(x1-x0)*st['w'];lengths[kind]+=dl
        area=c['formation_width_m']*abs(h)+c['side_slope_hv']*h*h
        if kind in ('surface','embankment','cutting'):
            if h>=0:fill+=area*dl
            else:cut+=area*dl
        if wet:
            # z monotone on each span, so endpoint minimum bounds this interval.
            minz=min(a.state(x0)['z'],a.state(x1)['z'])
            margin=minz-c['deck_depth_m']-t['water_level_m']-c['water_freeboard_m']
            if margin<0:bridge_failures.append({'x0':x0,'x1':x1,'margin_m':margin})
        rows.append({'x0':x0,'x1':x1,'kind':kind,'midpoint_rail_z_m':z,'midpoint_ground_z_m':g,
                     'formation_difference_m':h,'length_estimate_m':dl})
    groups=[]
    for r in rows:
        if groups and groups[-1]['kind']==r['kind'] and groups[-1]['x1']==r['x0']:
            groups[-1]['x1']=r['x1'];groups[-1]['length_estimate_m']+=r['length_estimate_m']
        else:groups.append({k:r[k] for k in ('x0','x1','kind','length_estimate_m')})
    return {'terrain_hash':digest(t),'civil_profile_hash':digest(c),'alignment_hash':a.identity,
            'status':'planning_estimate' if not bridge_failures else 'river_clearance_failed',
            'grid_step_max_m':step,'lengths_m':lengths,'cut_estimate_m3':cut,'fill_estimate_m3':fill,
            'runs':groups,'samples':rows,'river_clearance_failures':bridge_failures,
            'units':'one double-track formation, not two separately summed earthwork beds',
            'unassessed':['geotechnical stability','portal and abutment detail','piers/hydraulics',
                          'earthwork toes at site boundary','excavation accuracy between terrain samples',
                          'retaining wall engineering','land ownership']}


def candidate(fixture,lateral,height):
    a=make_alignment(fixture,lateral,height);c=fixture['corridor'];sp=c['track_centres_m']
    checks=limits_check(a,sp,fixture['profile'])
    site=site_check(a,sp,c['site'],c['forbidden'],fixture['civil']['formation_width_m'])
    terrain=terrain_assessment(a,fixture)
    K=max(t['bounds']['plan_curvature_upper'] for t in checks['tracks'])
    nominal=gb_track_centres(applicable=True,straight=(K==0),radius_m=None if K==0 else 1/K)
    nominal_matches=nominal.get('status')=='reference_value' and abs(nominal['value']*.001-sp)<1e-9 if nominal.get('units')=='mm' else nominal.get('status')=='reference_value' and abs(nominal['value']-sp)<1e-9
    # Named normal profile uses the source's nominal spacing but not gauge approval.
    accepted=checks['status']=='project_bounds_pass' and site['status']=='project_site_screen_pass' and not terrain['river_clearance_failures']
    rec={'version':VERSION,'lateral_offset_m':lateral,'plateau_height_m':height,
         'alignment':a.record(),'alignment_hash':a.identity,'brief_hash':digest(fixture),
         'limits':checks,'site':site,'terrain':terrain,'nominal_centres_reference':nominal,
         'selected_spacing_matches_nominal_reference':nominal_matches,
         'accepted_for_reference_comparison':accepted,
         'assessment_status':'reference_inspired_candidate' if accepted else 'candidate_rejected_or_uncertified',
         'track_lengths_m':[a.length(-sp/2),a.length(sp/2)],
         'track_length_method':'composite Simpson estimate',
         'station_interfaces':{'west':[a.point(0,-sp/2),a.point(0,sp/2)],
                               'east':[a.point(c['length_m'],-sp/2),a.point(c['length_m'],sp/2)],
                               'heading_rad':0.,'grade':0.,'station_internal_edits':False},
         'uk_complete_assessment':'unassessed','game_constructed':False,'construction_authorised':False}
    rec['candidate_hash']=digest(rec)
    return rec


def objective(c):
    t=c['terrain']
    return (t['lengths_m']['tunnel'],t['lengths_m']['river_bridge']+t['lengths_m']['viaduct'],
            t['cut_estimate_m3']+t['fill_estimate_m3'],sum(c['track_lengths_m']))


def search(fixture,budget=None):
    f=validate_fixture(fixture);b=f['search']['candidate_budget'] if budget is None else integer(budget,maximum=400)
    grid=list(itertools.product(f['search']['lateral_offsets_m'],f['search']['plateau_heights_m']))
    out=[]
    for lateral,height in grid[:b]:out.append(candidate(f,lateral,height))
    valid=[c for c in out if c['accepted_for_reference_comparison']]
    pareto=[]
    for c in valid:
        x=objective(c)
        if not any(all(a<=bb for a,bb in zip(objective(other),x)) and any(a<bb for a,bb in zip(objective(other),x)) for other in valid):
            pareto.append(c['candidate_hash'])
    state='search_exhausted' if len(out)<len(grid) else ('grid_complete_candidates_found' if valid else 'grid_complete_no_candidate')
    return {'status':state,'brief_hash':digest(f),'grid_size':len(grid),'evaluated':len(out),
            'accepted':len(valid),'candidates':out,'pareto_candidate_hashes':pareto,
            'objective_names':['tunnel_length_m','elevated_length_m','earthwork_estimate_m3','two_track_total_length_m'],
            'global_optimum_claim':False,'model_calls_inside_search':0,'station_internal_edits':False}
