"""Run v0.4: python -m railops.demo --output sectional_results."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import re
from railproof.model import Visit, strict_record, time_value, positive
from railgeom.patterns import FanSpec, GeometryProfile, Assembly
from railgeom.network import Network
from railgeom.curves import line
from railgeom.compiler import compile_assembly
from .access import AccessSpec, build_dual_access
from .motion import MotionProfile
from .sectional import compile_leg, MODES
from .operations import schedule
from .uk_profiles import (REGISTER, nominal_gauge, gb_track_centres, new_line_radius,
    vertical_radius, coupling_platform_gradient, platform_cant, platform_radius,
    gb_platform_interface, platform_zone_widths, admission)


def read_fixture(path: Path) -> dict:
    o=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(o,dict) or set(o)!={'schema_version','fidelity','description','geometry_profile','fan','access','motion','visits','scenarios'}:
        raise ValueError('Unexpected fixture fields')
    if o['schema_version']!='0.4.0' or o['fidelity']!='synthetic_geometry_with_separate_UK_reference_checks':
        raise ValueError('Unsupported fixture version/fidelity')
    for cls,key in ((GeometryProfile,'geometry_profile'),(FanSpec,'fan'),(AccessSpec,'access'),(MotionProfile,'motion')):
        strict_record(cls,o[key])
    if not isinstance(o['visits'],list) or not o['visits']:raise ValueError('Missing visits')
    for x in o['visits']:strict_record(Visit,x)
    if not isinstance(o['scenarios'],list) or not o['scenarios']:raise ValueError('Missing scenarios')
    seen=set()
    for s in o['scenarios']:
        if not isinstance(s,dict) or set(s)!={'id','closed_platform_ids','length_override_m','entry_spacing_override_ms','horizon_ms','evaluation_budget','late_stock_cycle'}:
            raise ValueError('Unexpected scenario fields')
        if not isinstance(s['id'],str) or not re.fullmatch('[a-z0-9_-]+',s['id']) or s['id'] in seen:
            raise ValueError('Invalid or duplicate scenario ID')
        seen.add(s['id'])
        ids=s['closed_platform_ids']
        if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
            raise ValueError('Invalid closures')
        if s['length_override_m'] is not None:positive(s['length_override_m'],'length override')
        if s['entry_spacing_override_ms'] is not None:time_value(s['entry_spacing_override_ms'],'spacing')
        time_value(s['horizon_ms'],'horizon',positive_only=True);time_value(s['evaluation_budget'],'budget')
        if type(s['late_stock_cycle']) is not bool:raise ValueError('Cycle flag must be boolean')
    return o


def write(path: Path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def numerical_examples() -> dict:
    return {'gauge':nominal_gauge(applicable=True),
       'centres_straight':gb_track_centres(applicable=True,straight=True),
       'centres_radius_below_scope':gb_track_centres(applicable=True,straight=False,radius_m=399),
       'new_line_radius_at_floor':new_line_radius(150,applicable=True,new_line=True),
       'same_radius_at_platform':platform_radius(150,applicable=True,new_line=True),
       'platform_radius_at_floor':platform_radius(300,applicable=True,new_line=True),
       'platform_cant_boundary':platform_cant(110,applicable=True,normal_service_stop=True),
       'crest_boundary':vertical_radius(500,kind='crest',applicable=True),
       'sag_same_radius':vertical_radius(500,kind='sag',applicable=True),
       'sag_boundary':vertical_radius(900,kind='sag',applicable=True),
       'coupling_gradient_boundary':coupling_platform_gradient(.0025,applicable=True,new_line=True,regular_attach_detach=True),
       'ordinary_platform_gradient_not_this_clause':coupling_platform_gradient(.01,applicable=True,new_line=True,regular_attach_detach=False),
       'platform_interface':gb_platform_interface(),
       'passenger_width_partial':platform_zone_widths(applicable=True,method='platform_waiting_method_two',block_passengers=80,block_length_m=20,circulation_peak_5min=200),
       'strict_admission':admission('gb_rules_strict',synthetic_components=True,mandatory_unknowns=['vehicle_gauging','real_release_rules']),
       'reference_inspired_admission':admission('gb_reference_inspired',synthetic_components=True,mandatory_unknowns=['vehicle_gauging','real_release_rules'])}


def generated_bank_rule_checks(compiled) -> dict:
    """Apply selected scalar clauses to the actually compiled synthetic bank.

    A sufficient curvature bound failing to certify is not an exact violation.
    This explicit new-line analysis scope does not promote the component catalogue.
    """
    records=compiled.provenance['curves']; metadata=compiled.provenance['network']['metadata']
    kmax=max(r['curvature_upper_per_m'] for r in records.values())
    lower_radius=None if kmax==0 else 1/kmax
    floor=new_line_radius(lower_radius,applicable=True,new_line=True,straight=kmax==0)
    if floor['status']=='fail':
        floor['status']='not_certified_by_bound'
        floor['reason']='A conservative curvature bound is not an exact-radius failure proof'
    platforms={}
    for pid,p in compiled.platforms.items():
        ks=[records[e]['curvature_upper_per_m'] for e in ('lead_'+pid,p['storage_edge'])]
        straight=all(k==0 for k in ks)
        platforms[pid]={'new_line_radius':platform_radius(None,applicable=True,new_line=True,straight=straight),
                       'stopping_cant':platform_cant(metadata.get('cant_mm'),applicable=True,normal_service_stop=True)}
    return {'scope':'explicit new-line scalar checks on synthetic generated geometry, not engineering approval',
            'compile_hash':compiled.compile_hash,'global_radius_lower_bound_m':lower_radius,
            'horizontal_floor_check':floor,'platform_checks':platforms,
            'platform_height_offset':gb_platform_interface(),
            'whole_UK_geometry_status':'unassessed; components, dynamics and national interfaces incomplete'}


def export_geometry_for_operations(compiled) -> dict:
    # Deep copy: do not mutate the established geometry compiler's regression payload.
    exported=json.loads(json.dumps(compiled.export()))
    exported['schema_version']='0.4.0'
    exported['geometry_compiler_version']='0.3.0'
    exported['provenance']['time_model']='not_assessed_by_geometry_compiler; see v0.4 leg and schedule records'
    exported['provenance']['assessments']['sectional_release']='separate railops assessment, not a geometry check'
    return exported


def spacing_proxy_trial() -> dict:
    resolved=gb_track_centres(applicable=True,straight=True);spacing=resolved['value']
    n=Network('gb_nominal_spacing_proxy_limit_test');routes={}
    for name,y in (('lower',0),('upper',spacing)):
        u=n.port(name+'_start',(0,y));v=n.port(name+'_end',(100,y))
        n.edge(name,u,v,line((0,y),(100,y)))
        routes[name]=n.one_path(u,v,name)
    c=compile_assembly(Assembly(n,routes,{},GeometryProfile()))
    return {'reference_lookup':resolved,'nominal_gauge':nominal_gauge(applicable=True),
       'track_centres_m':spacing,'synthetic_proxy_required_separation_m':GeometryProfile().separation_m,
       'proximity_resources':c.provenance['proximity_contacts'],
       'proxy_independence_established':not c.provenance['proximity_contacts'],
       'actual_vehicle_clearance':'unassessed',
       'interpretation':'The 4m generic proxy is not an authentic GB gauge. Do not alter it merely to make a 3.4m reference pass.',
       'compiled_model':c.export()}


def run(fixture: Path, output: Path) -> dict:
    o=read_fixture(fixture);output.mkdir(exist_ok=True,parents=True)
    gp=strict_record(GeometryProfile,o['geometry_profile']);fan=strict_record(FanSpec,o['fan'])
    ap=strict_record(AccessSpec,o['access']);mp=strict_record(MotionProfile,o['motion'])
    assembled=build_dual_access(fan,ap,gp);compiled=compile_assembly(assembled)
    write(output/'dual_access_compiled.json',export_geometry_for_operations(compiled))
    write(output/'generated_bank_uk_checks.json',generated_bank_rule_checks(compiled))
    rows=[];visits=[strict_record(Visit,x) for x in o['visits']]
    for s in o['scenarios']:
        current=list(visits)
        if s['length_override_m'] is not None:current=[replace(v,length_m=s['length_override_m']) for v in current]
        if s['entry_spacing_override_ms'] is not None:
            current=[replace(v,requested_entry_ms=i*s['entry_spacing_override_ms'],planned_departure_ms=i*s['entry_spacing_override_ms']+480000) for i,v in enumerate(current)]
        if s['late_stock_cycle']:
            current[0]=replace(current[0],requested_entry_ms=180000)
            current[6]=replace(current[6],stock_id=current[0].stock_id,predecessor=current[0].id,external_cycle_ms=600000)
        sh=hashlib.sha256(json.dumps({'visits':[asdict(v) for v in current],'scenario':s},sort_keys=True).encode()).hexdigest()
        for mode in MODES:
            r=schedule(compiled,current,mode=mode,profile=mp,closed=set(s['closed_platform_ids']),
                       horizon_ms=s['horizon_ms'],evaluation_budget=s['evaluation_budget'])
            r.update(scenario_id=s['id'],scenario_sha256=sh)
            write(output/f"{s['id']}__{mode}.json",r)
            keys=('required_visits','scheduled_visits','unscheduled_visits','completed_within_horizon',
                  'scheduled_residual_at_horizon','total_departure_delay_ms','candidate_evaluations')
            rows.append({'scenario_id':s['id'],'mode':mode,'scenario_sha256':sh,**{k:r[k] for k in keys}})
    legs={mode:{direction:compile_leg(compiled,'P4:'+direction,160,direction,mp,mode).export()
                for direction in ('in','out')} for mode in MODES}
    write(output/'example_legs.json',legs)
    examples=numerical_examples();write(output/'uk_numerical_checks.json',examples)
    spacing=spacing_proxy_trial();write(output/'gb_spacing_proxy_trial.json',spacing)
    summary={'release_version':'0.4.0','python':platform.python_version(),
        'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
        'numerical_register_sha256':hashlib.sha256(REGISTER.read_bytes()).hexdigest(),
        'compile_hash':compiled.compile_hash,'physical_platform_roads':len(compiled.platforms),
        'external_approach_tracks':2,'required_directed_routes':len(compiled.routes),
        'track_edges':len(compiled.edge_requirements),'resource_count':len(compiled.provenance['resources']),
        'route_lengths_upper_m':{k:r.length_upper_m for k,r in compiled.routes.items()},
        'motion_profile':asdict(mp),'operating_comparisons':rows,
        'nominal_spacing_reference_m':spacing['track_centres_m'],
        'nominal_spacing_proxy_independence_established':spacing['proxy_independence_established'],
        'external_model_or_game_calls_in_runner':0,'measured_plan_credit_savings':None,
        'construction_authorised':False,'whole_UK_profile':'not_approved; selected sourced checks only',
        'scope':['two external approaches feeding shared synthetic fan','all locks acquired at activation',
                 'sectional release after tail under authored edge sections','level-track uncalibrated acceleration/braking',
                 'storage held conservatively for complete visit','departure needs unmodelled clear continuation',
                 'not a complete eight-platform station or real signalling design']}
    write(output/'summary.json',summary)
    packet={'packet_kind':'executed_v04_proof','construction_authorised':False,
       'summary':'Two directional approaches, stopping motion and sectional release executed against the same whole-route baseline.',
       'nominal_rows':[r for r in rows if r['scenario_id']=='nominal'],
       'UK_profile_status':'selected values now executable; authentic turnouts and vehicle gauging still unresolved',
       'spacing_proxy_warning':'A sourced nominal track interval does not establish independent clearance under the current proxy.',
       'evidence_refs':['summary.json','comparison.md','uk_numerical_checks.json','example_legs.json','gb_spacing_proxy_trial.json'],
       'next_gate':'vehicle envelope and authentic component admission; then compose multiple banks with explicit recovery movements'}
    write(output/'decision_packet.json',packet)
    lines=['# Executed v0.4 two-approach bank comparisons','',
      'Same geometry, demand, kinematics and setup/release assumptions within each paired scenario. Only the resource-release policy changes. These are synthetic schedules, not actual station capacity estimates.','',
      '| Scenario | Release policy | Scheduled / required | Completed | Unscheduled | Residual | Scheduled departure delay (s) |',
      '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['scenario_id']} | {r['mode']} | {r['scheduled_visits']}/{r['required_visits']} | {r['completed_within_horizon']} | {r['unscheduled_visits']} | {r['scheduled_residual_at_horizon']} | {r['total_departure_delay_ms']/1000:.3f} |")
    lines +=['','Do not rank zero-delay rows with missing demand as successful. A less restrictive release model does not guarantee a globally better result under a greedy scheduler. Geometry and UK-rule gates are separate.','']
    (output/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',type=Path,default=Path(__file__).resolve().parents[1]/'sectional_fixtures'/'release.json')
    p.add_argument('--output',type=Path,default=Path('sectional_results'))
    args=p.parse_args()
    try:r=run(args.fixture,args.output)
    except (ValueError,TypeError,KeyError,OSError) as e:p.exit(2,f'Invalid input or output: {e}\n')
    print(f"Executed {len(r['operating_comparisons'])} paired-policy comparisons; outputs in {args.output}")

if __name__=='__main__':main()
