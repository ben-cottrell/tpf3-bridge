"""Generate source-qualified platform geometry and re-fit a fixed-size obstacle."""
from __future__ import annotations
from dataclasses import asdict,replace
from pathlib import Path
import argparse,copy,hashlib,json
from railclear.catalogue import read_json,exact
from railclear.model import digest
from railcompact.composition import build_compact,CompactSpec,EXPECTED_PORTS
from railcompact.compiler import compile_assembly
from railcompact.demo import read_fixture as read_operating_fixture,scenario
from railstation.operations import schedule_station
from railstation.checks import check_result,site_check
from .reference import number,reference,height_check,offset_check,width_requirement,taper_length,draft_curve_offset
from .platforms import PlatformProfile,Facility,make_platforms,verify_assessment,facility_check,fit_facility
from .datums import RailSection
from .components import load_component_references,compare_like_quantity
ROOT=Path(__file__).resolve().parents[1]
FIELDS=('schema_version','fidelity','family','compact_spec','platform_profile','permissible_speeds_mph','permissible_speed_origin','facility_island_id','facility_width_m','facility_length_m','facility_centre_x_m','initial_lateral_offset_from_island_centre_m','oversize_facility_width_m','authority_lateral_half_span_m','fit_budget','exclude_failed_boarding_faces','operating_scenarios','operating_pairs')


def read_fixture(path):
    f=read_json(Path(path));exact(f,FIELDS)
    if f['schema_version']!='0.8.0' or f['fidelity']!='reference_source_platforms_authored_compact_station':raise ValueError('unsupported_interface_fixture')
    if f['family']!='scissors':raise ValueError('fixture_requires_scissors_comparison')
    exact(f['compact_spec'],asdict(CompactSpec()).keys());CompactSpec(**f['compact_spec'])
    exact(f['platform_profile'],asdict(PlatformProfile()).keys());PlatformProfile(**f['platform_profile'])
    if f['facility_island_id'] not in ('IA12','IA34','IB12','IB34'):raise ValueError('unknown_island')
    if not isinstance(f['permissible_speed_origin'],str) or not f['permissible_speed_origin'].strip():raise ValueError('speed_origin_required')
    expected={g+str(i) for g in ('A','B') for i in range(1,5)}
    if set(f['permissible_speeds_mph'])!=expected:raise ValueError('speed_inventory_mismatch')
    for speed in f['permissible_speeds_mph'].values():number(speed,'permissible_speed',nonnegative=True)
    for key in ('facility_width_m','facility_length_m','oversize_facility_width_m','authority_lateral_half_span_m'):number(f[key],key,positive=True)
    for key in ('facility_centre_x_m','initial_lateral_offset_from_island_centre_m'):number(f[key],key)
    if type(f['fit_budget']) is not int or not 0<=f['fit_budget']<=100:raise ValueError('invalid_fit_budget')
    if type(f['exclude_failed_boarding_faces']) is not bool:raise ValueError('explicit_exclusion_policy_required')
    if type(f['operating_pairs']) is not int or not 1<=f['operating_pairs']<=24:raise ValueError('invalid_pairs')
    if not isinstance(f['operating_scenarios'],list) or not f['operating_scenarios'] or len(set(f['operating_scenarios']))!=len(f['operating_scenarios']) or any(s not in ('nominal','bank_a_platforms_closed','bank_b_platforms_closed') for s in f['operating_scenarios']):raise ValueError('unsupported_scenarios')
    return f


def gate_platforms(assessment,compiled,check,*,exclude_failed):
    verify_assessment(assessment,compiled)
    if type(exclude_failed) is not bool:raise ValueError('explicit_exclusion_policy_required')
    islands={i['id']:i for i in assessment['islands']}
    if check['island_id'] not in islands or digest(islands[check['island_id']])!=check['island_geometry_hash']:
        raise ValueError('stale_facility_geometry')
    # Recompute the check, rather than trusting supplied failure/approval flags.
    verified=facility_check(islands[check['island_id']],Facility(**check['facility']))
    if verified!=check:raise ValueError('modified_facility_result')
    failed=set(check['failed_platform_faces']); reasons=[];unknown=[]
    for pid,face in assessment['faces'].items():
        for kind in ('height_check','offset_check'):
            state=face[kind]['status']
            if state=='reference_clause_fail':failed.add(pid);reasons.append({'face':pid,'check':kind})
            elif state!='reference_clause_pass':unknown.append({'face':pid,'check':kind})
    for island in assessment['islands']:
        if island['width_check']['status']=='reference_clause_fail':
            failed.update(island['platform_ids']);reasons.append({'island':island['id'],'check':'minimum_width'})
        elif island['width_check']['status']!='reference_clause_pass':unknown.append({'island':island['id'],'check':'minimum_width'})
        if island['centreline_hull_check']['status']!='disjoint_hulls':unknown.append({'island':island['id'],'check':'rail_hull_interference'})
    if check['status']=='unassessed' or unknown:
        return {'status':'unassessed','excluded_platform_ids':[],'unknown_checks':unknown,'construction_authorised':False}
    return {'status':'planning_exclusion_applied' if failed and exclude_failed else 'no_planning_exclusion',
        'excluded_platform_ids':sorted(failed) if exclude_failed else [],'additional_dimension_failures':reasons,
        'policy':'exclude_faces_failing_selected_reference_dimensions_or_general_obstacle_distance' if exclude_failed else 'diagnostic_only_no_exclusion',
        'is_physical_track_closure':False,'is_real_station_safety_decision':False,'construction_authorised':False}


def run(fixture,output):
    f=read_fixture(fixture);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    def write(name,v):(out/name).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    s=build_compact(f['family'],CompactSpec(**f['compact_spec']));c=compile_assembly(s.assembly)
    c.provenance['component_admission']=s.component_report;c.provenance['movement_eligibility']=s.eligibility
    before=s.assembly.network.digest();compiled_before=digest(c.export())
    vehicle_reference_hash=digest(read_json(ROOT.parent/'evidence/vehicle_reference.json'))
    a=make_platforms(s,c,profile=PlatformProfile(**f['platform_profile']),permissible_speeds_mph=f['permissible_speeds_mph'])
    verify_assessment(a,c);write('platform_geometry.json',a)
    reservations=[{'id':'concourse','box_m':[1020.,-75.,1180.,75.]}]
    for island_row in a['islands']:
        x0,x1,y0,y1=island_row['surface_bounds_xy_m']
        reservations.append({'id':island_row['id'],'box_m':[x0,y0,x1,y1]})
    site=site_check(s,[0.,-90.,1200.,90.],expected_ports=EXPECTED_PORTS,reservations=reservations)
    write('site_with_platforms.json',site)
    write('compact_track_model.json',c.export())
    island=next(x for x in a['islands'] if x['id']==f['facility_island_id']);y0,y1=island['surface_bounds_xy_m'][2:];mid=(y0+y1)/2
    obj=Facility(f['facility_width_m'],f['facility_length_m'],f['facility_centre_x_m'],mid+f['initial_lateral_offset_from_island_centre_m'])
    initial=facility_check(island,obj)
    authority=[mid-f['authority_lateral_half_span_m'],mid+f['authority_lateral_half_span_m']]
    fitted=fit_facility(island,obj,allowed_centre_y_m=authority,budget=f['fit_budget'])
    centred=Facility(obj.width_m,obj.length_m,obj.centre_x_m,mid)
    centred_check=facility_check(island,centred)
    over=replace(centred,width_m=f['oversize_facility_width_m']);overcheck=facility_check(island,over)
    overfit=fit_facility(island,over,allowed_centre_y_m=authority,budget=f['fit_budget'])
    rows=[];cases={'initial':initial,'oversize':overcheck}
    if fitted['selected'] is not None:cases['locally_refitted']=fitted['check']
    write('facility_search.json',{'initial':initial,'nearest_authorised_fit':fitted,
        'centred_same_size':centred_check,'oversize':overfit,
        'zero_budget':fit_facility(island,obj,allowed_centre_y_m=authority,budget=0),
        'no_lateral_authority':fit_facility(island,obj,allowed_centre_y_m=[obj.centre_y_m,obj.centre_y_m],budget=1)})
    high=copy.deepcopy(island);req=width_requirement([125.,125.]);high['width_check']={**req,'status':'reference_clause_pass','actual_width_m':island['width_m']}
    highfit=fit_facility(high,centred,allowed_centre_y_m=authority,budget=1)
    write('speed_and_space_sensitivity.json',{'speed_is_independent_of_motion_target':True,
        'same_facility_at_100mph':width_requirement([100.,100.]),'same_facility_above_100mph':highfit,
        'fixed_track_centres_m':island['track_y_m'][1]-island['track_y_m'][0],
        'minimum_centres_for_oversize_facility_m':overfit['required_island_width_m']+2*(f['platform_profile']['gauge_mm']/2+f['platform_profile']['nearest_rail_offset_mm'])/1000 if 'required_island_width_m' in overfit else None,
        'track_movement_authorised':False})
    opf=read_operating_fixture(ROOT/'compact_fixtures/release.json');opf['pairs']=f['operating_pairs']
    operating={};gates={}
    for name,chk in cases.items():
        gate=gate_platforms(a,c,chk,exclude_failed=f['exclude_failed_boarding_faces']);gates[name]=gate
        if gate['status']=='unassessed':continue
        for sc in f['operating_scenarios']:
            visits,kw=scenario(opf,sc);kw['closed']=set(kw.get('closed',set()))|set(gate['excluded_platform_ids'])
            r=schedule_station(c,visits,**kw);independent=check_result(c,visits,r)
            if independent['status']!='pass':raise AssertionError(independent)
            r.update({'release_version':'0.8.0','scenario_id':sc,'interface_case':name,
                'platform_assessment_hash':a['assessment_hash'],'facility_check_hash':digest(chk),
                'vehicle_reference_hash':vehicle_reference_hash,
                'design_case_hash':digest({'compile':c.compile_hash,'platforms':a['assessment_hash'],'facility':digest(chk),'vehicle':vehicle_reference_hash}),
                'planning_exclusion':gate,'independent_check':independent,'construction_authorised':False})
            operating[name,sc]=r;write(f'{name}__{sc}.json',r)
            rows.append({'case':name,'scenario':sc,'required':r['required_visits'],'scheduled':r['scheduled_visits'],
                'completed':r['completed_within_horizon'],'unscheduled':r['unscheduled_visits'],'residual':r['scheduled_residual_at_horizon'],
                'excluded_faces':gate['excluded_platform_ids'],'delay_s_scheduled_only':r['total_departure_delay_ms']/1000})
    ref=reference();sec=RailSection();edge=sec.edge(nearest_rail_offset_mm=f['platform_profile']['nearest_rail_offset_mm'],height_mm=915.,side=1)
    raw_wrong=sec.measure((.7375,.915),side=1)
    write('datum_and_clause_examples.json',{'correct_centreline_offset_m':edge[0],
        'correct_edge_yz_m':edge,'roundtrip':sec.measure(edge,side=1),
        'incorrectly_using_737_5mm_from_centreline':raw_wrong,
        'wrong_datum_check':offset_check(raw_wrong['nearest_rail_offset_mm'],applicable=True,resolved_minimum_mm=730,minimum_origin='explicit_standard_case_reference'),
        'height_design_915':height_check(915,applicable=True),'height_design_925':height_check(925,applicable=True),
        'height_build_925_unconfirmed':height_check(925,applicable=True,stage='build_maintenance'),
        'height_build_925_confirmed':height_check(925,applicable=True,stage='build_maintenance',linked_lower_sector_adjustment_confirmed=True),
        'offset_taper_15mm':taper_length(15,'offset'),'height_taper_15mm':taper_length(15,'height'),
        'draft_curve_cases':[{ 'radius_m':r,**draft_curve_offset(r,standard_case_confirmed=True)} for r in (400.,360.,359.,300.,250.,160.,159.)],
        'gauge_source_id':ref['gauge_source_id'],'current_uk_compliance':'unassessed'})
    comps=load_component_references()
    write('component_evidence_audit.json',{'records':comps,
        'wrong_scope_comparisons':[
            compare_like_quantity(comps[0],'reported_crossing_ratio_denominator',1/.075,candidate_scope='synthetic_branch_exit_tangent_reciprocal'),
            compare_like_quantity(comps[1],'movable_stub_beam_length_m',40.,candidate_scope='complete_authored_turnout_longitudinal_span')],
        'authentic_complete_turnout_imported':False,'station_pointwork_unchanged':True,'construction_authorised':False})
    if before!=s.assembly.network.digest() or compiled_before!=digest(c.export()):raise AssertionError('interface_work_mutated_track_or_resources')
    summary={'schema_version':'0.8.0','fixture_sha256':hashlib.sha256(Path(fixture).read_bytes()).hexdigest(),
        'operating_fixture_hash':digest(opf),'compile_hash':c.compile_hash,'platform_assessment_hash':a['assessment_hash'],
        'islands':len(a['islands']),'boarding_faces':len(a['faces']),'island_widths_m':[i['width_m'] for i in a['islands']],
        'all_platform_centreline_hulls_disjoint':all(i['centreline_hull_check']['status']=='disjoint_hulls' for i in a['islands']),
        'comparison_count':len(rows),'comparison_rows':rows,'all_independent_checks_passed':True if rows else None,
        'original_plan_with_platform_reservations':site['status'],
        'local_fit_status':fitted['status'],'oversize_fit_status':overfit['status'],
        'track_and_resources_unchanged':True,'current_full_platform_standard_reviewed':False,
        'authentic_complete_turnout_imported':False,'current_uk_compliance':'unassessed','game':'not_tested',
        'construction_authorised':False,'model_or_game_api_calls_by_runner':0,'plan_credit_saving_measured':False}
    write('summary.json',summary)
    packet={'schema_version':'0.8.0','status':'offline_reference_profile_design_screen',
        'material_result':('Fixed-size facility fitted within the authorised platform slab; wider facility requires changed design authority.' if fitted['selected'] is not None else 'No authorised local fit has been selected; inspect the reported budget, applicability or geometry outcome.'),
        'fit_status':fitted['status'],'oversize_status':overfit['status'],
        'rail_rebuild_required_for_accepted_local_fit':False if fitted['selected'] is not None else None,'comparison_rows':rows,
        'remaining_decision':'Retain supported footprint or authorise a different facility/access arrangement; current UK source and component gates remain open.',
        'platform_assessment_hash':a['assessment_hash'],'trace_files':['facility_search.json','platform_geometry.json','component_evidence_audit.json'],
        'construction_authorised':False}
    write('decision_packet.json',packet)
    lines=['# v0.8 platform-interface operating comparisons','','Reference-source design-screen exclusions, not physical track closures or real station safety decisions.','',
        '| Interface case | Rail scenario | Excluded boarding faces | Completed / required | Unscheduled | Residual | Departure delay, scheduled only |',
        '|---|---|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['case']} | {r['scenario']} | {', '.join(r['excluded_faces']) or 'none'} | {r['completed']}/{r['required']} | {r['unscheduled']} | {r['residual']} | {r['delay_s_scheduled_only']:.3f} s |")
    lines+=['','Same track, source vehicle-unit lengths and operating assumptions; only explicitly gated boarding eligibility changes.',
        'The unreviewed current standard, full access, dynamic gauging, authentic specialwork and game interfaces remain unassessed.']
    (out/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'interface_fixtures/release.json');p.add_argument('--output',type=Path,default=ROOT/'interface_results')
    args=p.parse_args();s=run(args.fixture,args.output)
    print(json.dumps({k:s[k] for k in ('schema_version','boarding_faces','comparison_count','local_fit_status','oversize_fit_status','all_independent_checks_passed')},indent=2))
