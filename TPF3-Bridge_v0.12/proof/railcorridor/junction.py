"""Full-ramp crossing cells for later branch-junction composition.

The perpendicular crossing cell has explicit open branch ports. It does not
invent the missing connection turnouts, a merging route, or complete junction.
"""
from __future__ import annotations
from .geometry import Alignment, Knot, digest, number


def crossing_cell(fixture, mode, ramp_m, *, height_m=None, plateau_m=None):
    if mode not in ('flat','flyover','diveunder'):raise ValueError('unknown crossing mode')
    j=fixture['junction'];sp=fixture['corridor']['track_centres_m'];base=fixture['corridor']['end_height_m']
    h=j['height_m'] if height_m is None else number(height_m,'height',minimum=0,maximum=50)
    plateau=j['plateau_m'] if plateau_m is None else number(plateau_m,'plateau',minimum=1,maximum=1000)
    number(ramp_m,'ramp',minimum=1,maximum=10000)
    z=0 if mode=='flat' else h*(1 if mode=='flyover' else -1)
    # Local x becomes world y; local y is identically zero. World x is fixed.
    ext=ramp_m+plateau/2
    a=Alignment((Knot(-ext,0,base),Knot(-plateau/2,0,base+z),
                 Knot(plateau/2,0,base+z),Knot(ext,0,base)))
    bounds=a.bounds(); footprint=sp/2+j['track_half_width_m']
    if footprint>ext:raise ValueError('crossing footprint extends beyond provided approach')
    # Monotone ramp/plateau means these locations include every clearance minimum.
    sample=[-footprint,0,footprint]
    separation=min(abs(a.state(u)['z']-base) for u in sample)
    required=j['lower_envelope_m']+j['electrification_m']+j['deck_depth_m']+j['allowance_m']
    gradient_ok=bounds['grade_upper']<=j['max_grade']
    vertical_ok=bounds['vertical_curvature_upper']<=1/j['min_vertical_radius_m']
    separated=mode!='flat' and separation>=required
    geometry_ok=gradient_ok and vertical_ok and (mode=='flat' or separated)
    main_east={'main_east_track'};main_west={'main_west_track'};branch={'branch_track'}
    # Retain conflict if the grade-separated cell has not passed its full-ramp gate.
    if not (geometry_ok and separated):
        main_east.add('crossing_east');main_west.add('crossing_west')
        branch.update(('crossing_east','crossing_west'))
    paths={'main_east':main_east,'main_west':main_west,'branch':branch}
    pairs=[]
    names=list(paths)
    for i,n in enumerate(names):
        for other in names[i+1:]:
            pairs.append({'a':n,'b':other,'shared_exclusive_resources':sorted(paths[n]&paths[other])})
    line=a.polyline(max_step=25,tolerance=.02)
    pts=[(j['crossing_x_m'],p[0],p[2]) for p in line['points']]
    site=fixture['corridor']['site'];half=j['track_half_width_m'];cx=j['crossing_x_m']
    site_ok=(site[0]<=cx-half and cx+half<=site[2] and site[1]<=-ext and ext<=site[3])
    data={'version':'0.9.0','brief_hash':digest(fixture),'site_reservation_pass':site_ok,'mode':mode,'ramp_length_m':ramp_m,'height_m':abs(z),
          'plateau_length_m':plateau,'total_approach_span_m':2*ext,
          'main_rail_z_m':base,'branch_ports':[pts[0],pts[-1]],
          'crossing_x_m':j['crossing_x_m'],'branch_polyline':pts,
          'bounds':bounds,'max_grade_pass':gradient_ok,'vertical_radius_pass':vertical_ok,
          'crossing_footprint_interval_m':[-footprint,footprint],
          'minimum_rail_separation_m':separation,'required_project_separation_m':required,
          'clearance_margin_m':separation-required if mode!='flat' else None,
          'envelope_budget_origin':'project study allowances, not a universal UK bridge clearance',
          'crossing_separated_within_model':separated and geometry_ok,
          'project_cell_geometry_pass':geometry_ok,'accepted_for_cell_comparison':geometry_ok and site_ok,
          'resource_sets':{k:sorted(v) for k,v in paths.items()},'pair_checks':pairs,
          'turning_connections_at_crossing':[],
          'crossing_conflicts_with_main':sum(bool(p['shared_exclusive_resources']) for p in pairs if p['b']=='branch'),
          'full_branch_junction_connected':False,
          'missing_connection_interfaces':['upstream turnout and connecting alignment','downstream branch continuation/merge'],
          'unassessed':['actual vehicle/structure gauge','bridge/tunnel asset fit','terrain and piers at crossing',
                        'drainage/groundwater for diveunder','real signal protection and section boundaries'],
          'game_constructed':False,'construction_authorised':False}
    data['cell_hash']=digest(data)
    return data


def holding_check(available_m,train_length_m,entry_margin_m,exit_margin_m):
    for k,v in locals().copy().items():number(v,k,minimum=0,maximum=100000)
    if train_length_m<=0:raise ValueError('train length must be positive')
    required=train_length_m+entry_margin_m+exit_margin_m
    return {'available_m':available_m,'required_m':required,'fits_clear':available_m>=required,
            'shortfall_m':max(0,required-available_m),
            'scope':'static train length plus declared margins; not a signal-spacing approval'}


def braking_screen(speed_mph,brake_mps2,reaction_s,available_m):
    number(speed_mph,'speed',minimum=0,maximum=250)
    number(brake_mps2,'brake',minimum=.01,maximum=5)
    number(reaction_s,'reaction',minimum=0,maximum=100)
    number(available_m,'available',minimum=0,maximum=100000)
    v=speed_mph*.44704;d=v*reaction_s+v*v/(2*brake_mps2)
    return {'required_m':d,'available_m':available_m,'sufficient_within_model':available_m>=d,
            'scope':'level-track constant-deceleration project screen; not a UK braking/signalling standard'}
