"""Run corridor search, crossing envelopes and mock execution; no game connection."""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
from .planning import parse_json,validate_fixture,search,objective
from .geometry import digest, Alignment, Knot
from .junction import crossing_cell,holding_check,braking_screen
from .adapter import compile_plan,manifest,MockAdapter,execute

ROOT=Path(__file__).resolve().parents[1]


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def run(fixture,output):
    f=validate_fixture(fixture);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    s=search(f);write(out/'corridor_search.json',s)
    accepted=[c for c in s['candidates'] if c['accepted_for_reference_comparison']]
    if not accepted:raise ValueError('demo requires at least one accepted candidate')
    # The displayed choice is a declared policy, NOT global geometric optimality.
    chosen=min(accepted,key=lambda c:(objective(c)[2],objective(c)[3],c['candidate_hash']))
    write(out/'selected_corridor.json',chosen)
    a=Alignment(tuple(Knot(**k) for k in chosen['alignment']['knots']))
    pairs={n:a.polyline(d,max_step=25,tolerance=f['search']['polyline_tolerance_m'])
           for n,d in (('eastbound',-f['corridor']['track_centres_m']/2),('westbound',f['corridor']['track_centres_m']/2))}
    write(out/'selected_track_polylines.json',pairs)
    restricted=deepcopy(f);restricted['profile']['speed_mph']=100
    compression=deepcopy(f)
    compression['corridor']['length_m']=3600;compression['corridor']['gate_x_m']=[900,1500,2700]
    compression['junction']['crossing_x_m']=3300
    # Holding train lengths and local dimensions are NOT rescaled.
    restricted_s=search(restricted)
    comp_s=search(compression)
    experiments={'zero_budget':{k:v for k,v in search(f,budget=0).items() if k!='candidates'},
                 'limited_budget':{k:v for k,v in search(f,budget=2).items() if k!='candidates'},
                 'higher_speed':{'speed_mph':100,'accepted':restricted_s['accepted'],
                      'candidates':[{'offset_m':c['lateral_offset_m'],'height_m':c['plateau_height_m'],
                                     'accepted':c['accepted_for_reference_comparison'],'failures':c['limits']['failures']} for c in restricted_s['candidates']]},
                 'shorter_corridor':{'length_m':3600,'train_lengths_rescaled':False,'accepted':comp_s['accepted'],
                      'candidates':[{'offset_m':c['lateral_offset_m'],'height_m':c['plateau_height_m'],
                                     'accepted':c['accepted_for_reference_comparison'],'failures':c['limits']['failures']} for c in comp_s['candidates']]}}
    write(out/'bounded_and_changed_brief_trials.json',experiments)
    cells=[crossing_cell(f,mode,r) for mode in ('flat','flyover','diveunder') for r in f['junction']['ramp_lengths_m']]
    write(out/'crossing_cells.json',cells)
    write(out/'corridor_crossing_join.json',{'corridor_candidate_hash':chosen['candidate_hash'],
        'brief_hash':digest(f),'crossing_x_m':f['junction']['crossing_x_m'],
        'actual_main_reference_point':a.point(f['junction']['crossing_x_m']),
        'cell_hashes':[c['cell_hash'] for c in cells],
        'common_interface_consistency':all(c['main_rail_z_m']==a.point(c['crossing_x_m'])[2] for c in cells),
        'physical_branch_connections_generated':False,'turnout_and_merge_interfaces':'reserved, not connected'})
    holding=[holding_check(L,f['junction']['train_length_m'],10,10) for L in (250,275,300)]
    write(out/'holding_and_braking.json',{'holding':holding,'braking':[braking_screen(60,.7,2,L) for L in (300,600)],
                'signal_positions_generated':False,'world_speed_calibrated':False})
    plan=compile_plan(chosen,f);write(out/'mock_construction_plan.json',plan)
    ad=MockAdapter();first=execute(plan,ad);second=execute(plan,ad)
    cases={'clean':first,'idempotent_repeat':second,
           'lost_acknowledgement':execute(plan,MockAdapter(drop_ack_at=1)),
           'snapped_geometry':execute(plan,MockAdapter(snap_at=1)),
           'rejected_construction':execute(plan,MockAdapter(fail_at=1)),
           'unknown_capability':execute(plan,MockAdapter(manifest(demonstrated=False))),
           'stale_world':execute(plan,MockAdapter(revision=1)),
           'stale_terrain':execute(plan,MockAdapter(terrain_revision='changed')),
           'unconnected_game':execute(plan,MockAdapter(manifest('tpf3_unprobed')))}
    write(out/'mock_execution_cases.json',cases)
    write(out/'tpf3_unprobed_capabilities.json',manifest('tpf3_unprobed'))
    rows=[]
    for c in s['candidates']:
        rows.append({'offset_m':c['lateral_offset_m'],'rail_plateau_m':c['plateau_height_m'],
                     'accepted':c['accepted_for_reference_comparison'],
                     'per_track_mean_length_m':sum(c['track_lengths_m'])/2,
                     'tunnel_length_m':c['terrain']['lengths_m']['tunnel'],
                     'elevated_length_m':c['terrain']['lengths_m']['river_bridge']+c['terrain']['lengths_m']['viaduct'],
                     'earthwork_estimate_m3':c['terrain']['cut_estimate_m3']+c['terrain']['fill_estimate_m3'],
                     'pareto':c['candidate_hash'] in s['pareto_candidate_hashes'],'candidate_hash':c['candidate_hash']})
    summary={'release':'0.9.0','fixture_hash':digest(f),'evaluated':s['evaluated'],'accepted':s['accepted'],
             'pareto_count':len(s['pareto_candidate_hashes']),'selected_candidate_hash':chosen['candidate_hash'],
             'selection_policy':'lowest midpoint-estimated earthwork, then length; example lowering choice only',
             'corridor_rows':rows,'crossing_cell_trials':len(cells),
             'crossing_cell_passes':sum(c['project_cell_geometry_pass'] for c in cells),
             'mock_operation_count':len(plan['operations']),
             'mock_case_statuses':{k:v['status'] for k,v in cases.items()},
             'station_internal_edits':False,'complete_branch_junction':False,
             'actual_game_calls':0,'actual_model_calls_inside_runner':0,
             'real_network_constructed':False,'full_uk_certification_claim':False}
    write(out/'summary.json',summary)
    direct=min((r for r in rows if r['accepted']),key=lambda r:(r['per_track_mean_length_m'],r['earthwork_estimate_m3']))
    bypass=min((r for r in rows if r['accepted']),key=lambda r:(r['tunnel_length_m'],r['earthwork_estimate_m3']))
    displayed=list({r['candidate_hash']:r for r in (direct,bypass)}.values())
    packet={'status':'reference_design_alternatives_ready','brief_hash':digest(f),
            'alternatives':displayed,
            'display_policy':'show shortest accepted and least-tunnel/earthwork accepted; all Pareto results retained locally',
            'all_pareto_count':len(s['pareto_candidate_hashes']),
            'selection_for_demo':summary['selection_policy'],'selected_candidate_hash':chosen['candidate_hash'],
            'material_tradeoff':'shorter direct route with tunnel versus longer ridge bypass; civil quantities are planning estimates',
            'crossing_note':'750m and 900m grade-separated ramps pass this project profile; connection turnouts are not generated',
            'game_execution_status':'unprobed; mock tests are not game evidence',
            'detailed_results':['corridor_search.json','crossing_cells.json','mock_execution_cases.json'],
            'construction_authorised':False}
    write(out/'decision_packet.json',packet)
    text=['# v0.9 corridor comparison','',
          'Executed on a declared synthetic terrain. Amounts are planning estimates, not construction bills or capacity measurements.','',
          '| Offset m | Rail plateau m | Accepted | Mean track length m | Tunnel m | Elevated m | Earthwork m³ | Pareto |',
          '|---:|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        text.append(f"| {r['offset_m']} | {r['rail_plateau_m']} | {r['accepted']} | {r['per_track_mean_length_m']:.3f} | {r['tunnel_length_m']:.3f} | {r['elevated_length_m']:.3f} | {r['earthwork_estimate_m3']:.3f} | {r['pareto']} |")
    text+=['','## Crossing cells','',
           '| Mode | Ramp m | Whole span m | Project geometry | Crossing separation m | Shared main conflicts |',
           '|---|---:|---:|---|---:|---:|']
    for c in cells:text.append(f"| {c['mode']} | {c['ramp_length_m']} | {c['total_approach_span_m']} | {c['project_cell_geometry_pass']} | {c['minimum_rail_separation_m']} | {c['crossing_conflicts_with_main']} |")
    text+=['','The crossing cell has open connection ports. It is not a complete diverging junction.','',
           '## Mock adapter cases','', '| Case | Result | Writes |','|---|---|---:|']
    for k,v in cases.items():text.append(f"| {k} | {v['status']} | {v['writes']} |")
    (out/'comparison.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',type=Path,default=ROOT/'corridor_fixtures/release.json')
    p.add_argument('--output',type=Path,default=Path('corridor_results'))
    args=p.parse_args()
    result=run(parse_json(args.fixture),args.output)
    print(json.dumps({k:result[k] for k in ('evaluated','accepted','pareto_count','crossing_cell_trials','mock_operation_count')},indent=2))

if __name__=='__main__':main()
