"""Run the terrain-aware branch refit and retain reproducible local evidence."""
from __future__ import annotations
import argparse
from copy import deepcopy
from pathlib import Path
import json
from railcorridor.geometry import digest
from railcorridor.planning import candidate as corridor_candidate
from railclear.catalogue import read_json
from railbranch.demo import scenarios as branch_scenarios
from railbranch.operations import schedule, compile_resources
from .planning import ROOT, validate_fixture, load_inputs, search, bind
from .terrain import assess
from .adapter import compile_plan, MockTerrainAdapter, execute, manifest


def write(out,name,value):
    (out/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def decisions(bindings,results,required_scenario,delay_budget_ms=None):
    all_rows=[];scenarios=set()
    for mode,b in bindings.items():
        r=results[(mode,required_scenario)]
        if r['terrain_design_hash']!=b['design_hash'] or r['candidate_hash']!=b['geometry_hash']:raise ValueError('stale design result')
        original={k:v for k,v in r.items() if k not in ('terrain_design_hash','terrain_assessment_hash','joined_result_hash')}
        if original['result_hash']!=digest({k:v for k,v in original.items() if k!='result_hash'}):raise ValueError('altered operating result')
        if r['joined_result_hash']!=digest({k:v for k,v in r.items() if k!='joined_result_hash'}):raise ValueError('joined result hash')
        if not r['independent_check']['passed']:raise ValueError('unverified operating result')
        scenarios.add(r['scenario_hash'])
        ok=b['accepted_for_reference_design'] and r['completed']==r['required'] and r['unscheduled']==0
        if delay_budget_ms is not None:ok &= r['total_entry_delay_ms_scheduled_only']<=delay_budget_ms
        all_rows.append(dict(mode=mode,design_hash=b['design_hash'],completed=r['completed'],required=r['required'],
            unscheduled=r['unscheduled'],residual=r['residual'],delay_ms=r['total_entry_delay_ms_scheduled_only'],qualifies=bool(ok),
            tunnel_track_metres_estimate=b['terrain']['track_length_by_kind_m']['tunnel'],
            reservation_union_area_m2=b['terrain']['plan_reservation_union_area_m2']))
    if len(scenarios)!=1:raise ValueError('incomparable operation scenarios')
    alternatives=[r for r in all_rows if r['qualifies']]
    return dict(scenario=required_scenario,scenario_hash=next(iter(scenarios)),delay_budget_ms=delay_budget_ms,
        status='terrain_and_operation_alternatives' if alternatives else 'no_tested_design_meets_outcome',
        alternatives=alternatives,all_results=all_rows,construction_authorised=False,
        detail_policy='keep search, terrain cells and reservations local',
        unresolved_choice='actual structures, grade-aware performance and game representation remain unassessed')


def run(fixture,output):
    f=validate_fixture(fixture);c,b=load_inputs(f);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    grid,objects=search(f,c,b);write(out,'placement_search.json',grid)
    if not all(m in grid['selected_by_mode'] for m in ('flat','flyover','diveunder')):
        summary=dict(version='0.11.0',status=grid['status'],full_comparison_not_run=True,
            reason='one or more crossing forms lack an accepted placement',search=grid,construction_authorised=False)
        write(out,'summary.json',summary);return summary
    selected={m:objects[h] for m,h in grid['selected_by_mode'].items()};bindings={m:a for m,(j,a) in selected.items()}
    v=read_json(ROOT.parent/'evidence/vehicle_reference.json');formation=v['published'][b['formation_reference_key']]['value']
    # Freeze one request scenario set from the selected flat design. Do not tune
    # a separate crossing pulse for the grade-separated alternatives.
    scenarios=[s for s in branch_scenarios(b,selected['flat'][0],formation) if s['id'] in f['operation_scenarios']]
    write(out,'common_scenarios.json',scenarios)
    rows=[];results={}
    for mode,(j,a) in selected.items():
        write(out,mode+'__geometry.json',j.assessment);write(out,mode+'__terrain_binding.json',a)
        write(out,mode+'__resources.json',compile_resources(j))
        for s in scenarios:
            r=schedule(j,s,b['performance'])
            if not r['independent_check']['passed']:raise AssertionError(r['independent_check'])
            r.update(terrain_design_hash=a['design_hash'],terrain_assessment_hash=a['terrain']['assessment_hash'])
            r['joined_result_hash']=digest(r);results[(mode,s['id'])]=r
            write(out,mode+'__'+s['id']+'.json',r)
            rows.append(dict(mode=mode,scenario=s['id'],required=r['required'],completed=r['completed'],
                unscheduled=r['unscheduled'],residual=r['residual'],delay_s=r['total_entry_delay_ms_scheduled_only']/1000,
                design_hash=a['design_hash'],scenario_hash=r['scenario_hash']))
    # Conservative rejection must not be confused with proven physical failure.
    tight=deepcopy(c);tight['corridor']['site']=[-5,-150,6005,300]
    flood=deepcopy(c);flood['terrain']['water_level_m']=18.0
    refined=deepcopy(f);refined['civil_policy']['grid_step_m']=20
    j,a=selected[f['selected_mode_for_mock']]
    changed={'zero_budget':search(f,c,b,budget=0)[0],
             'limited_budget':search(f,c,b,budget=2)[0],
             'narrow_site_binding':bind(j,tight,f),
             'raised_water_binding':bind(j,flood,f),
             'refined_terrain':assess(j,c,refined['civil_policy'])}
    write(out,'changed_constraints_and_refinement.json',changed)
    p=compile_plan(j,c,f,a);write(out,'selected_mock_plan.json',p)
    ad=MockTerrainAdapter(snapshot=c);first=execute(p,ad,a);repeat=execute(p,ad,a)
    same_label=deepcopy(c);same_label['terrain']['ridge_height_m']+=1
    wrongland=deepcopy(c);wrongland['corridor']['forbidden'].append([2000,100,2200,600])
    changed_cases={
        'clean':first,'repeat':repeat,
        'lost_land_ack':execute(p,MockTerrainAdapter(snapshot=c,drop_ack_at=0),a),
        'lost_track_ack':execute(p,MockTerrainAdapter(snapshot=c,drop_ack_at=4),a),
        'terrain_changed_same_revision':execute(p,MockTerrainAdapter(snapshot=same_label),a),
        'protected_land_changed':execute(p,MockTerrainAdapter(snapshot=wrongland),a),
        'terrain_changes_after_first_write':execute(p,MockTerrainAdapter(snapshot=c,mutate_terrain_after_write=1),a),
        'wrong_coordinate':execute(p,MockTerrainAdapter(snapshot=c,snap_at=2),a),
        'wrong_turnout_state':execute(p,MockTerrainAdapter(snapshot=c,corrupt_state_at=2),a),
        'partial_failure':execute(p,MockTerrainAdapter(snapshot=c,fail_at=3),a),
        'stale_world':execute(p,MockTerrainAdapter(snapshot=c,revision=1),a),
        'unprobed_game':execute(p,MockTerrainAdapter(snapshot=c,capabilities=manifest('tpf3_unprobed')),a)}
    write(out,'mock_execution_cases.json',changed_cases);write(out,'tpf3_unprobed_capabilities.json',manifest('tpf3_unprobed'))
    packets=[]
    for scenario in ('crossing_pulse','merge_pulse','downstream_blocked'):
        if scenario in f['operation_scenarios']:packets.append(decisions(bindings,results,scenario,delay_budget_ms=0))
    write(out,'decision_packets.json',packets)
    base=corridor_candidate(c,0,c['corridor']['end_height_m'])
    provenance=dict(version='0.11.0',source_corridor_hash=digest(c),source_branch_hash=digest(b),
        fixture_hash=digest(f),terrain_hash=digest(c['terrain']),terrain_revision=c['terrain']['revision'],
        baseline_direct_corridor_hash=base['candidate_hash'],baseline_direct_corridor_accepted=base['accepted_for_reference_comparison'],
        unchanged_static_constraints=c['corridor'],retained_mainline_profile=c['profile'],
        local_junction_profile=b['junction'],vehicle_source_record_hash=digest(v),formation_length_m=formation,
        source_field=b['formation_reference_key'],source_reference='S060 retained manufacturer record',
        component_source='authored synthetic import',new_source_records=0,
        original_corridor_is_unbuilt_design_baseline=True,station_internal_edits=False)
    write(out,'input_provenance.json',provenance)
    placements=[dict(mode=m,layout=next(r['layout'] for r in grid['candidates'] if r.get('design_hash')==x['design_hash']),
        lateral_m=j.assessment['placement']['lateral_m'],design_hash=x['design_hash'],
        tunnel_track_m=x['terrain']['track_length_by_kind_m']['tunnel'],
        elevated_track_m=x['terrain']['track_length_by_kind_m']['river_bridge']+x['terrain']['track_length_by_kind_m']['viaduct'],
        land_reservation_union_m2=x['terrain']['plan_reservation_union_area_m2']) for m,(j,x) in selected.items()]
    summary=dict(version='0.11.0',evaluated=grid['evaluated'],accepted=grid['accepted_count'],selected_placements=placements,
        operating_comparisons=len(rows),rows=rows,mock_case_statuses={k:v['status'] for k,v in changed_cases.items()},
        selected_mock_operations=len(p['operations']),physical_edges=len(selected['flat'][0].network.edges),
        preserved_external_interfaces=6,unchanged_mainline_targets=True,station_internal_edits=False,
        source_corridor_hash=digest(c),new_external_research=False,game_calls=0,model_calls_inside_runner=0,
        actual_structures_built=False,construction_authorised=False,
        grade_sensitive_performance=False,spatial_queues_simulated=False)
    write(out,'summary.json',summary)
    md=['# Terrain-aware junction results — v0.11','',
        'Same synthetic river/ridge terrain and protected land as v0.9. New refitted physical network; no inherited terrain approval.','',
        '## Placement search','', '| Layout | Offset (m) | Form | Accepted | Principal failures |','|---|---:|---|---|---|']
    for r in grid['candidates']:md.append(f"| {r['layout']} | {r['lateral_m']:g} | {r['mode']} | {r['accepted']} | {'; '.join(r.get('reasons',[])) or 'None in assessed scope'} |")
    md+=['','## Selected terrain estimates','','Track metres are summed over unique physical edges, not railway service routes. They are not numbers of bridge/tunnel assets.','',
         '| Form | Offset (m) | Tunnel track metres | Elevated track metres | Reserved rectangle-union area (m²) |','|---|---:|---:|---:|---:|']
    for r in placements:md.append(f"| {r['mode']} | {r['lateral_m']:g} | {r['tunnel_track_m']:.3f} | {r['elevated_track_m']:.3f} | {r['land_reservation_union_m2']:.1f} |")
    md+=['','## Operations','','Delay is entry delay over scheduled trains only. Whole-pass greedy planning; grade-sensitive traction and internal waiting are unassessed.','',
         '| Scenario | Form | Completed / required | Unscheduled | Residual | Entry delay (s) |','|---|---|---:|---:|---:|---:|']
    for r in rows:md.append(f"| {r['scenario']} | {r['mode']} | {r['completed']} / {r['required']} | {r['unscheduled']} | {r['residual']} | {r['delay_s']:.3f} |")
    md+=['','No actual terrain, station, game or external service was edited. Civil outputs remain reservations, not finished structure assets.']
    (out/'comparison.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'terrain_fixtures/release.json')
    parser.add_argument('--output',type=Path,default=Path('terrain_results'))
    args=parser.parse_args()
    try:result=run(read_json(args.fixture),args.output)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','search')},indent=2,allow_nan=False))
