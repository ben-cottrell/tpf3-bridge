"""Run a bounded geometry search and integrated compact-station comparisons."""
from dataclasses import asdict,replace
from pathlib import Path
import argparse,hashlib,json
from railclear.catalogue import read_json,exact
from railclear.profiles import resolve_vehicle
from railclear.model import count,positive,digest
from railproof.model import strict_record,time_value
from railops.motion import MotionProfile
from railstation.demo import SCENARIOS as BASE_SCENARIOS,scenario as base_scenario
from railstation.operations import schedule_station
from railstation.checks import check_result
from .composition import build_compact,CompactSpec,FAMILIES,EVIDENCE
from .compiler import compile_assembly
from .search import fit_grid
from .assessment import audit_vehicle,assess,decisions
ROOT=Path(__file__).resolve().parents[1]
EXTRA=('a_bank_closed_inner_b1_closed','a_bank_closed_300m','b_bank_closed_300m','b_fan_closed')
SCENARIOS=BASE_SCENARIOS+EXTRA
FIELDS=('schema_version','fidelity','search_domain','geometry_budget','vehicle_assumptions','pairs','pair_interval_ms','group_b_offset_ms','planned_turnaround_offset_ms','dwell_ms','turnback_ms','dispatch_ms','horizon_ms','max_wait_ms','evaluation_budget','motion','sweep_step_m','max_poses','max_pairs','scenarios')

def read_fixture(path):
    f=read_json(Path(path));exact(f,FIELDS)
    if f['schema_version']!='0.7.0' or f['fidelity']!='reference_informed_vehicle_dimensions_synthetic_station':raise ValueError('unsupported_compact_fixture')
    strict_record(MotionProfile,f['motion']);resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),f['vehicle_assumptions'])
    count(f['pairs'],'pairs',24);positive(f['sweep_step_m'],'pose step');count(f['max_poses'],'poses',10000);count(f['max_pairs'],'pose pairs',100000000)
    for k in ('pair_interval_ms','planned_turnaround_offset_ms','horizon_ms'):time_value(f[k],k,positive_only=True)
    for k in ('group_b_offset_ms','dwell_ms','turnback_ms','dispatch_ms','max_wait_ms','evaluation_budget','geometry_budget'):time_value(f[k],k)
    fit_grid(f['search_domain'],budget=0)
    if f['geometry_budget']>10000:raise ValueError('excessive_geometry_budget')
    if not isinstance(f['scenarios'],list) or not f['scenarios'] or len(set(f['scenarios']))!=len(f['scenarios']) or any(s not in SCENARIOS for s in f['scenarios']):raise ValueError('invalid_scenarios')
    return f

def scenario(f,name):
    if name not in SCENARIOS:raise ValueError('unknown_scenario')
    base=name
    if name in ('a_bank_closed_inner_b1_closed','a_bank_closed_300m'):base='bank_a_platforms_closed'
    if name=='b_bank_closed_300m':base='bank_b_platforms_closed'
    if name=='b_fan_closed':base='nominal'
    visits,kw=base_scenario(f,base)
    if name=='a_bank_closed_inner_b1_closed':kw['closed'].add('B1')
    if name in ('a_bank_closed_300m','b_bank_closed_300m'):visits=[replace(v,length_m=300.) for v in visits]
    if name=='b_fan_closed':kw['closed_edges']={'B:F1:normal','B:F1:reverse'}
    return visits,kw

def run(fixture,output):
    f=read_fixture(fixture);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    search=fit_grid(f['search_domain'],budget=f['geometry_budget']);write('geometry_search.json',search)
    write('restricted_search_examples.json',{'no_evaluations':fit_grid(f['search_domain'],budget=0),
        'bounded_one_evaluation':fit_grid(f['search_domain'],budget=1),
        'additional_600m_specialwork_limit':fit_grid(f['search_domain'],budget=f['geometry_budget'],maximum_specialwork_end_x_m=600.)})
    if search['selected'] is None:
        summary={'schema_version':'0.7.0','status':search['status'],'comparison_count':0,'construction_authorised':False};write('summary.json',summary);return summary
    spec=CompactSpec(**search['selected']['parameters']);results={};assessments={};rows=[];inventory=[]
    for family in FAMILIES:
        station=build_compact(family,spec);compiled=compile_assembly(station.assembly)
        compiled.provenance['component_admission']=station.component_report;compiled.provenance['movement_eligibility']=station.eligibility
        write(f'{family}__compiled.json',compiled.export())
        vehicle=audit_vehicle(station,compiled,f['vehicle_assumptions'],step_m=f['sweep_step_m'],max_poses=f['max_poses'],max_pairs=f['max_pairs']);write(f'{family}__vehicle.json',vehicle)
        assessment=assess(station,compiled,vehicle);assessments[family]=assessment;write(f'{family}__assessment.json',assessment);results[family]={}
        for name in f['scenarios']:
            visits,kw=scenario(f,name);r=schedule_station(compiled,visits,**kw);checker=check_result(compiled,visits,r)
            if checker['status']!='pass':raise AssertionError(checker)
            r.update({'release_version':'0.7.0','scenario_id':name,'family':family,'independent_check':checker,
                'candidate_assessment_hash':digest(assessment),'vehicle_record_hash':vehicle['vehicle_resolution']['record_hash'],
                'plan_contract_passed':assessment['plan_contract_passed'],'construction_authorised':False,
                'formation_origin':'synthetic_300m_stress' if '300m' in name else 'retained_S060_published_unit_length'})
            results[family][name]=r;write(f'{family}__{name}.json',r)
            rows.append({'family':family,'scenario':name,'required':r['required_visits'],'scheduled':r['scheduled_visits'],
                'completed':r['completed_within_horizon'],'unscheduled':r['unscheduled_visits'],'residual':r['scheduled_residual_at_horizon'],
                'delay_s_scheduled_only':r['total_departure_delay_ms']/1000.,'recovery_legs':r['total_recovery_legs'],'candidate_evaluations':r['candidate_evaluations']})
        inventory.append({'family':family,'compile_hash':compiled.compile_hash,'source_hash':compiled.source_hash,
            'edges':len(station.assembly.network.edges),'turnouts':len(station.assembly.network.turnouts),'diamonds':len(station.assembly.network.metadata['diamond_crossings']),
            'routes':len(compiled.routes),'platforms':len(compiled.platforms),'plan_contract_passed':assessment['plan_contract_passed'],
            'normal_independence':assessment['normal_independence']['status'],'vehicle_route_count':vehicle['routes_evaluated'],'vehicle_pair_count':vehicle['route_pairs_evaluated']})
    packets={};requirements={'normal_only':['nominal'],'a_bank_recovery':['nominal','bank_a_platforms_closed'],
        'b_bank_recovery':['nominal','bank_b_platforms_closed'],'either_bank_recovery':['nominal','bank_a_platforms_closed','bank_b_platforms_closed'],
        'either_fan_recovery':['nominal','a_fan_closed','b_fan_closed']}
    for key,required in requirements.items():
        if all(s in f['scenarios'] for s in required):packets[key]=decisions(results,assessments,required)
    write('decision_packets.json',packets)
    summary={'schema_version':'0.7.0','fixture_sha256':hashlib.sha256(Path(fixture).read_bytes()).hexdigest(),
        'selected_geometry_parameters':asdict(spec),'geometry_search_status':search['status'],'families':inventory,
        'scenario_count':len(f['scenarios']),'comparison_count':len(rows),'comparison_rows':rows,
        'all_independent_checks_passed':True,'plan_contract_passed_all':all(a['plan_contract_passed'] for a in assessments.values()),
        'full_original_brief_satisfied':False,'strict_UK_profile':'blocked_pending_authentic_components_and_gauging',
        'game':'not_tested','construction_authorised':False,'model_or_game_api_calls_by_runner':0,'plan_credit_saving_measured':False,
        'scope':'finite family/grid; centreline plan contract and synthetic operation; not full site/UK approval'}
    write('summary.json',summary)
    lines=['# v0.7 compact station comparisons','','Original plan boundary, exact approaches, platform intervals and buffer-marker positions.',
        'Components are authored synthetic. The four-hour horizon is not a capacity or punctuality approval.','',
        '| Scenario | Family | Scheduled / required | Completed | Unscheduled | Residual | Departure delay (scheduled only) | Recovery legs |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for name in f['scenarios']:
        for r in (r for r in rows if r['scenario']==name):lines.append(f"| {name} | {r['family']} | {r['scheduled']}/{r['required']} | {r['completed']} | {r['unscheduled']} | {r['residual']} | {r['delay_s_scheduled_only']:.3f} s | {r['recovery_legs']} |")
    lines+=['','Recovery reaches B1 from A and A4 from B—not the whole opposite bank.',
        'Bank closures are separate scenarios. The links are after both fans; a failed fan cannot be bypassed.',
        'Zero delay excludes unscheduled work and must never be ranked without its completion count.']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'compact_fixtures/release.json');p.add_argument('--output',type=Path,default=ROOT/'compact_results')
    a=p.parse_args();s=run(a.fixture,a.output);print(json.dumps({k:s.get(k) for k in ('schema_version','comparison_count','plan_contract_passed_all','all_independent_checks_passed')},indent=2))
