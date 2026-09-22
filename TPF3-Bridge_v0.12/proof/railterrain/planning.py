"""Bounded placement search and candidate-bound terrain / interface assessments."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import itertools
import math
from railclear.catalogue import read_json, exact
from railcorridor.geometry import digest, integer, number
from railcorridor.planning import validate_fixture as validate_corridor, candidate as corridor_candidate
from railbranch.demo import validate_fixture as validate_branch
from railbranch.geometry import JunctionSpec, state
from railbranch.operations import verify_candidate
from .geometry import build_placed, mainline_profile_check, EXTERNAL
from .terrain import assess

ROOT=Path(__file__).resolve().parents[1]


def validate_fixture(f):
    exact(f,{'schema_version','fidelity','source_corridor','source_branch','lateral_offsets_m','layouts','modes','candidate_budget','civil_policy','operation_scenarios','selected_mode_for_mock'})
    if f['schema_version']!='0.11.0' or f['fidelity']!='gb_reference_inspired_terrain_junction_study':raise ValueError('version/fidelity')
    if f['source_corridor']!='corridor_fixtures/release.json' or f['source_branch']!='branch_fixtures/release.json':raise ValueError('only frozen built-in source fixtures supported')
    if not isinstance(f['lateral_offsets_m'],list) or not 1<=len(f['lateral_offsets_m'])<=8:raise ValueError('bounded offset grid')
    for x in f['lateral_offsets_m']:number(x,'offset',minimum=-600,maximum=600)
    if len(set(f['lateral_offsets_m']))!=len(f['lateral_offsets_m']):raise ValueError('duplicate offsets')
    if not isinstance(f['layouts'],list) or not 1<=len(f['layouts'])<=8:raise ValueError('bounded layout grid')
    ids=[]
    for row in f['layouts']:
        exact(row,{'id','merge_x_m','diverge_x_m','spread_finish_x_m','main_restore_x_m'})
        name=row['id']
        if not isinstance(name,str) or not name or len(name)>40 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in name):raise ValueError('layout identifier')
        ids.append(name)
        for key in set(row)-{'id'}:number(row[key],key,minimum=1,maximum=6000)
        if not row['spread_finish_x_m']<row['merge_x_m']<row['diverge_x_m']<row['main_restore_x_m']<=4500:raise ValueError('layout ordering')
    if len(set(ids))!=len(ids):raise ValueError('duplicate layouts')
    if not isinstance(f['modes'],list) or not f['modes'] or any(m not in ('flat','flyover','diveunder') for m in f['modes']) or len(set(f['modes']))!=len(f['modes']):raise ValueError('mode set')
    integer(f['candidate_budget'],'candidate budget',maximum=192)
    if f['selected_mode_for_mock'] not in f['modes']:raise ValueError('mock mode outside grid')
    allowed={'nominal','crossing_pulse','merge_pulse','downstream_blocked'}
    if not isinstance(f['operation_scenarios'],list) or not f['operation_scenarios'] or any(s not in allowed for s in f['operation_scenarios']) or len(set(f['operation_scenarios']))!=len(f['operation_scenarios']):raise ValueError('scenario subset')
    exact(f['civil_policy'],{'single_track_half_formation_m','construction_margin_m','structure_half_reservation_m','grid_step_m','specialwork_on_structures'})
    for k in set(f['civil_policy'])-{'specialwork_on_structures'}:number(f['civil_policy'][k],k,minimum=.01,maximum=100 if k=='grid_step_m' else 30)
    if f['civil_policy']['specialwork_on_structures']!='unsupported_in_this_study':raise ValueError('unsupported component-on-structure admission')
    return deepcopy(f)


def load_inputs(f):
    f=validate_fixture(f)
    return validate_corridor(read_json(ROOT/f['source_corridor'])),validate_branch(read_json(ROOT/f['source_branch']))


def boundary_check(j,corridor):
    c=corridor['corridor'];east=c['track_centres_m']/2;z=c['end_height_m'];L=c['length_m']
    expected={'W_E':(0,east,z),'W_W':(0,-east,z),'E_E':(L,east,z),'E_W':(L,-east,z),
              'B_OUT':(L,j.spec.branch_centre_y_m+east,z),'B_IN':(L,j.spec.branch_centre_y_m-east,z)}
    rows=[]
    for pid,xyz in expected.items():
        actual=j.assessment['ports_xyz_m'][pid];errors=[]
        if math.dist(actual,xyz)>1e-7:errors.append('position_mismatch')
        for eid,e in j.network.edges.items():
            if pid not in (e.u,e.v):continue
            x=e.curve.at(0 if e.u==pid else 1)[0]
            if abs(state(e.curve,x)[1])>1e-8:errors.append('nonzero_boundary_slope')
            if abs(j.height[eid].state(x)['zp'])>1e-8:errors.append('nonzero_boundary_grade')
        rows.append(dict(port_id=pid,expected_xyz_m=list(xyz),actual_xyz_m=list(actual),reasons=errors,passed=not errors))
    return dict(passed=all(r['passed'] for r in rows),ports=rows,
        main_interface_source='unchanged v0.9 corridor boundary contract',
        branch_interface_source='v0.10 absolute branch boundary, not a constructed destination',station_internal_edits=False)


def bind(j,corridor,fixture):
    f=validate_fixture(fixture);c=validate_corridor(corridor)
    main=mainline_profile_check(j,c['profile']);land=assess(j,c,f['civil_policy']);ports=boundary_check(j,c)
    failures=[]
    if not j.assessment['accepted_for_reference_comparison']:failures+=j.assessment['failed_checks']
    if main['status']!='project_mainline_bounds_pass':failures+=sorted({reason for r in main['edges'] for reason in r['reasons']})
    if land['hard_failures']:failures+=sorted({v['reason'] for v in land['hard_failures']})
    if not ports['passed']:failures.append('boundary_contract_failed')
    out=dict(version='0.11.0',geometry_hash=j.assessment['candidate_hash'],source_corridor_hash=digest(c),
        fixture_hash=digest(f),terrain_hash=digest(c['terrain']),terrain_revision=c['terrain']['revision'],
        site_constraints_hash=digest(c['corridor']),mainline_profile=main,boundary_check=ports,terrain=land,
        accepted_for_reference_design=not failures,failures=sorted(set(failures)),
        same_terrain_as_corridor=True,previous_alignment_approval_inherited=False,
        corridor_integration='refitted design replacement between frozen ports; not insertion into built assets',
        full_network_movement_check='four required local movements connected; branch destination external',
        specialist_gauge_status='unassessed_not_a_game_design_blocker_by_itself',
        actual_structure_assets='unassessed',station_internal_edits=False,
        construction_authorised=False,game_constructed=False)
    out['design_hash']=digest(out);return out


def verify_binding(j,corridor,fixture,binding):
    if binding.get('design_hash')!=digest({k:v for k,v in binding.items() if k!='design_hash'}):raise ValueError('design hash mismatch')
    fresh=bind(j,corridor,fixture)
    if fresh!=binding:raise ValueError('stale or forged terrain/design evidence')
    if not fresh['accepted_for_reference_design']:raise ValueError('terrain-bound design not accepted')
    verify_candidate(j)
    return True


def spec_for(branch,corridor,layout):
    return replace(JunctionSpec(**branch['junction']),
        merge_x_m=layout['merge_x_m'],diverge_x_m=layout['diverge_x_m'],
        spread_finish_x_m=layout['spread_finish_x_m'],
        site_y_min_m=corridor['corridor']['site'][1],site_y_max_m=corridor['corridor']['site'][3])


def search(fixture,corridor=None,branch=None,budget=None):
    f=validate_fixture(fixture)
    if corridor is None or branch is None:
        c,b=load_inputs(f);corridor=c if corridor is None else corridor;branch=b if branch is None else branch
    c=validate_corridor(corridor);b=validate_branch(branch)
    grid=list(itertools.product(f['layouts'],f['lateral_offsets_m'],f['modes']))
    work=f['candidate_budget'] if budget is None else integer(budget,'budget',maximum=192)
    records=[];objects={}
    for layout,offset,mode in grid[:work]:
        row=dict(layout=layout['id'],lateral_m=offset,mode=mode,accepted=False)
        try:
            j=build_placed(spec_for(b,c,layout),mode,offset,layout['main_restore_x_m'])
            a=bind(j,c,f);t=a['terrain']
            row.update(accepted=a['accepted_for_reference_design'],design_hash=a['design_hash'],
                geometry_hash=a['geometry_hash'],reasons=a['failures'],
                estimated_tunnel_track_m=t['track_length_by_kind_m']['tunnel'],
                estimated_elevated_track_m=t['track_length_by_kind_m']['river_bridge']+t['track_length_by_kind_m']['viaduct'],
                reservation_union_area_m2=t['plan_reservation_union_area_m2'],
                total_physical_track_length_m=sum(j.length(eid) for eid in j.network.edges),
                first_land_witnesses=t['hard_failures'][:5],
                mainline_bound_status=a['mainline_profile']['status'])
            objects[a['design_hash']] = (j,a)
        except ValueError as exc:row['reasons']=[str(exc)]
        records.append(row)
    passed=[r for r in records if r['accepted']]
    # Choose a clear demonstration policy within each required crossing form.
    # Terrain and construction difficulty remain a vector, not a hidden score.
    selected={}
    for mode in f['modes']:
        eligible=[r for r in passed if r['mode']==mode]
        if eligible:selected[mode]=min(eligible,key=lambda r:(r['estimated_tunnel_track_m'],r['reservation_union_area_m2'],r['total_physical_track_length_m'],r['design_hash']))['design_hash']
    pareto=[]
    def obj(r):return r['estimated_tunnel_track_m'],r['estimated_elevated_track_m'],r['reservation_union_area_m2'],r['total_physical_track_length_m']
    # Compare within mode: flat versus separated crossing provides different function.
    for r in passed:
        if not any(o['mode']==r['mode'] and all(x<=y for x,y in zip(obj(o),obj(r))) and any(x<y for x,y in zip(obj(o),obj(r))) for o in passed):pareto.append(r['design_hash'])
    out=dict(version='0.11.0',fixture_hash=digest(f),source_corridor_hash=digest(c),source_branch_hash=digest(b),
        grid_size=len(grid),evaluated=len(records),accepted_count=len(passed),candidates=records,
        selected_by_mode=selected,pareto_by_crossing_function=pareto,
        selection_policy='within each mode: least tunnel track metres, then reservation union area, then physical track length',
        status='search_exhausted' if len(records)<len(grid) else 'grid_complete_candidates_found' if passed else 'grid_complete_no_candidate',
        global_optimum_claim=False,model_calls_inside_search=0,game_constructed=False,
        construction_authorised=False)
    return out,objects
