"""Reproducible integrated station studies; standard-library-only, no game calls."""
from __future__ import annotations
from dataclasses import asdict,replace
from pathlib import Path
import argparse
import hashlib
import json
from railclear.catalogue import read_json,exact
from railclear.profiles import resolve_vehicle
from railclear.model import digest,count,positive
from railproof.model import Visit,strict_record,time_value
from railops.motion import MotionProfile
from .composition import StationSpec,FAMILIES,EVIDENCE,build_station,compile_station
from .operations import schedule_station
from .checks import check_result
from .assessment import vehicle_audit,assess_candidate,decision_packet

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('nominal','bunched','bank_a_platforms_closed','bank_b_platforms_closed','a_fan_closed',
           'a_arrival_closed','published_long_units','synthetic_300m','all_platforms_closed',
           'short_horizon','zero_budget','a_bank_closed_recovery_forbidden')
FIELDS=('schema_version','fidelity','station','vehicle_assumptions','pairs','pair_interval_ms','group_b_offset_ms',
        'planned_turnaround_offset_ms','dwell_ms','turnback_ms','dispatch_ms','horizon_ms','max_wait_ms',
        'evaluation_budget','motion','sweep_step_m','max_poses','max_pairs','scenarios')


def read_fixture(path:Path)->dict:
    f=read_json(path);exact(f,FIELDS)
    if f['schema_version']!='0.6.0' or f['fidelity']!='reference_informed_vehicle_dimensions_synthetic_station':raise ValueError('Unsupported station fixture')
    strict_record(StationSpec,f['station']);strict_record(MotionProfile,f['motion'])
    resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),f['vehicle_assumptions'])
    count(f['pairs'],'pairs',24);positive(f['sweep_step_m'],'pose step')
    count(f['max_poses'],'poses',10000);count(f['max_pairs'],'pose pairs',100000000)
    for k in ('pair_interval_ms','planned_turnaround_offset_ms','horizon_ms'):time_value(f[k],k,positive_only=True)
    for k in ('group_b_offset_ms','dwell_ms','turnback_ms','dispatch_ms','max_wait_ms','evaluation_budget'):time_value(f[k],k)
    if not isinstance(f['scenarios'],list) or not f['scenarios'] or len(set(f['scenarios']))!=len(f['scenarios']) or any(s not in SCENARIOS for s in f['scenarios']):raise ValueError('Invalid scenario IDs')
    return f


def scenario(f:dict,name:str)->tuple[list[Visit],dict]:
    if name not in SCENARIOS:raise ValueError('Unknown scenario')
    resolved=resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'))
    length=resolved['published']['unit_8car_length_m']
    if name=='published_long_units':length=resolved['published']['unit_12car_length_m']
    if name=='synthetic_300m':length=300.
    visits=[]
    for i in range(f['pairs']):
        for g in ('A','B'):
            t=i*f['pair_interval_ms']+(f['group_b_offset_ms'] if g=='B' else 0)
            if name=='bunched':t=(i//3)*(3*f['pair_interval_ms'])
            visits.append(Visit(f'{g}{i+1:02}',f'S{g}{i+1:02}',g,g,length,t,
                  t+f['planned_turnaround_offset_ms'],f['dwell_ms'],f['turnback_ms'],f['dispatch_ms'],
                  outgoing_kind='empty_stock' if i%6==5 else 'passenger'))
    kwargs={'closed':set(),'closed_edges':set(),'horizon_ms':f['horizon_ms'],'max_wait_ms':f['max_wait_ms'],
            'evaluation_budget':f['evaluation_budget'],'allow_recovery':True,'profile':strict_record(MotionProfile,f['motion'])}
    if name in ('bank_a_platforms_closed','a_bank_closed_recovery_forbidden'):kwargs['closed']={f'A{i}' for i in range(1,5)}
    if name=='bank_b_platforms_closed':kwargs['closed']={f'B{i}' for i in range(1,5)}
    if name=='a_bank_closed_recovery_forbidden':kwargs['allow_recovery']=False
    if name=='a_fan_closed':kwargs['closed_edges']={'A:F1:normal','A:F1:reverse'}
    if name=='a_arrival_closed':kwargs['closed_edges']={'A:arrival_lead'}
    if name=='all_platforms_closed':kwargs['closed']={f'{g}{i}' for g in ('A','B') for i in range(1,5)}
    if name=='short_horizon':kwargs['horizon_ms']=1200000
    if name=='zero_budget':kwargs['evaluation_budget']=0
    return visits,kwargs


def run(fixture_path:Path,output:Path)->dict:
    f=read_fixture(fixture_path);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def write(name,value):
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    results={};assessments={};rows=[];inventory=[]
    for family in FAMILIES:
        station=build_station(family,strict_record(StationSpec,f['station']))
        compiled=compile_station(station)
        write(f'{family}__compiled.json',compiled.export())
        vehicle=vehicle_audit(station,compiled,f['vehicle_assumptions'],step_m=f['sweep_step_m'],max_poses=f['max_poses'],max_pairs=f['max_pairs'])
        write(f'{family}__vehicle.json',vehicle)
        assessment=assess_candidate(station,compiled,vehicle);assessments[family]=assessment
        write(f'{family}__assessment.json',assessment)
        results[family]={}
        for name in f['scenarios']:
            visits,kwargs=scenario(f,name)
            r=schedule_station(compiled,visits,**kwargs)
            r['independent_check']=check_result(compiled,visits,r)
            if r['independent_check']['status']!='pass':raise AssertionError(r['independent_check'])
            # Carry the same candidate assessment identities into each run.
            r.update({'scenario_id':name,'family':family,'candidate_assessment_hash':digest(assessment),
                      'vehicle_record_hash':vehicle['vehicle_resolution']['record_hash'],
                      'formation_length_origin':'synthetic stress value' if name=='synthetic_300m' else 'S060 manufacturer unit length',
                      'site_status_original_brief':assessment['original_brief_site']['status'],
                      'construction_authorised':False})
            results[family][name]=r
            write(f'{family}__{name}.json',r)
            rows.append({'family':family,'scenario':name,'required':r['required_visits'],'scheduled':r['scheduled_visits'],
                         'completed':r['completed_within_horizon'],'unscheduled':r['unscheduled_visits'],
                         'residual':r['scheduled_residual_at_horizon'],'delay_s_scheduled_only':r['total_departure_delay_ms']/1000,
                         'recovery_legs':r['total_recovery_legs'],'evaluations':r['candidate_evaluations']})
        inventory.append({'family':family,'compile_hash':compiled.compile_hash,'edges':len(station.assembly.network.edges),
             'routes':len(compiled.routes),'platform_roads':len(compiled.platforms),'turnouts':len(station.assembly.network.turnouts),
             'normal_resource_pairs':assessment['normal_independence']['route_pair_count'],
             'vehicle_routes':vehicle['routes_evaluated'],'vehicle_pairs':vehicle['route_pairs_evaluated'],
             'original_site':assessment['original_brief_site']['status'],'proposed_site':assessment['proposed_larger_test_site']['status']})
    decisions={}
    groups={'a_bank_recovery':['nominal','bank_a_platforms_closed'],
            'b_bank_recovery':['nominal','bank_b_platforms_closed'],
            'both_bank_recoveries':['nominal','bank_a_platforms_closed','bank_b_platforms_closed']}
    for name,required in groups.items():
        if all(s in f['scenarios'] for s in required):decisions[name]=decision_packet(results,assessments,required)
    write('decision_packets.json',decisions)
    summary={'schema_version':'0.6.0','fixture_hash':hashlib.sha256(Path(fixture_path).read_bytes()).hexdigest(),
             'families':inventory,'scenario_count':len(f['scenarios']),'comparison_rows':rows,
             'comparison_count':len(rows),'all_independent_result_checks_passed':True,
             'full_original_brief_satisfied':False,'reason':'fixed family exceeds original site and changes three approach positions',
             'UK_components':'authentic data not acquired','full_vehicle_gauging':'unassessed','game':'not_tested',
             'model_or_game_api_calls_by_runner':0,'credit_saving_measured':False}
    write('summary.json',summary)
    lines=['# v0.6 integrated station comparisons','',
           'Executed on the same authored station boundaries, demand and matched synthetic corridor section breaks. Not real-site capacity.',
           'All three candidate geometries fail the original site brief. A larger test site is assessed separately.','',
           '| Scenario | Family | Scheduled / required | Completed | Unscheduled | Residual | Departure delay (scheduled only) | Recovery legs |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for name in f['scenarios']:
        for r in (r for r in rows if r['scenario']==name):
            lines.append(f"| {name} | {r['family']} | {r['scheduled']}/{r['required']} | {r['completed']} | {r['unscheduled']} | {r['residual']} | {r['delay_s_scheduled_only']:.3f} s | {r['recovery_legs']} |")
    lines+=['','Unscheduled work is not credited as low delay. The 300 m formation is a synthetic stress input. Other unit lengths come from the retained S060 record.',
            'The scheduler is greedy and its edge-based release is synthetic. No network construction or UK approval follows from a completed row.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',type=Path,default=ROOT/'station_fixtures/release.json')
    p.add_argument('--output',type=Path,default=ROOT/'station_results')
    a=p.parse_args();s=run(a.fixture,a.output)
    print(json.dumps({k:s[k] for k in ('schema_version','scenario_count','comparison_count','all_independent_result_checks_passed','full_original_brief_satisfied')},indent=2))
