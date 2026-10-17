"""Candidate-scoped plan, vehicle and numerical checks; no blanket UK pass."""
from dataclasses import asdict
import copy
import math
from railclear.catalogue import read_json
from railclear.profiles import resolve_vehicle
from railclear.demo import extended_route
from railclear.model import bounds,bounds_gap,digest
from railclear.sweep import sweep,pair_screen
from railops.uk_profiles import admission,new_line_radius
from railproof.rules import platform_cant,platform_radius,gb_platform_interface
from railstation.checks import site_check,independence
from .composition import EVIDENCE,EXPECTED_PORTS


def audit_vehicle(station,compiled,assumptions,*,step_m=3.,max_poses=3000,max_pairs=2000000):
    resolved=resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),assumptions)
    body=resolved.pop('body');a=station.assembly;supports=35.;sweeps={};rows=[]
    for rid in sorted(a.routes):
        path=extended_route(a,rid,supports)
        end=path.length_m-supports+(body.length_m+body.bogie_centres_m)/2
        sw=sweep(path,body,supports,end,step_m,max_poses);sweeps[rid]=sw
        rows.append({'route_id':rid,**sw.export(False)})
    requests=[(f'A:A{i}:in',f'B:B{j}:in') for i in range(1,5) for j in range(1,5)]
    requests += [('A:A4:out','B:B1:out'),('A:A4:in','B:B1:out')]
    if 'A:B1:in' in sweeps:requests += [('A:B1:in','B:B1:in'),('A:B1:out','A:A4:out')]
    if 'B:A4:in' in sweeps:requests += [('B:A4:in','A:A4:in'),('B:A4:out','B:B1:out')]
    if 'A:B1:in' in sweeps and 'B:A4:in' in sweeps:requests += [('A:B1:in','B:A4:in')]
    pairs=[]
    for x,y in requests:
        sa,sb=sweeps[x],sweeps[y]
        ba=bounds([p for pose in sa.poses for p in pose.corners]);bb=bounds([p for pose in sb.poses for p in pose.corners])
        lower=bounds_gap(ba,bb)-sa.between_pose_padding_m-sb.between_pose_padding_m
        if lower>0:
            row={'status':'clear_within_polyline_static_model','continuous_gap_lower_bound_m':lower,
                 'method':'global_pose_box_bound_minus_pose_padding','may_remove_existing_resource':False}
        else:row=pair_screen(sa,sb,max_pairs)
        pairs.append({**row,'route_a':x,'route_b':y})
    return {'schema_version':'0.7.0','family':station.family,'compile_hash':compiled.compile_hash,
            'vehicle_resolution':{**resolved,'body':asdict(body)},'routes':rows,'pairs':pairs,
            'routes_evaluated':len(rows),'route_pairs_evaluated':len(pairs),
            'resource_mutations':[],'full_UK_dynamic_gauging':'unassessed','parent_curve_body_error':'unassessed',
            'support_assumption':{'each_end_m':supports,'kind':'authored_tangent_continuation_not_checked_external_railway'},
            'scope':'one representative body on all selected routes; only listed route pairs, not full formations'}


def assess(station,compiled,vehicle):
    n=station.assembly.network
    reservation=[{'id':'original_concourse','box_m':[1020.,-75.,1180.,75.]}]
    site=site_check(station,[0.,-90.,1200.,90.],expected_ports=EXPECTED_PORTS,reservations=reservation)
    geometry_errors=[];platforms=[]
    for g in ('A','B'):
        for i in range(1,5):
            p=compiled.platforms[f'{g}{i}']; y=(-42.+12*(i-1)) if g=='A' else (6.+12*(i-1))
            start=710. if i<=2 else 650.
            m=n.ports[p['marker_port']]; e=n.edges[p['storage_edge']];limit=n.ports[e.v]
            checks={'road_y':abs(m.position[1]-y)<1e-6,
                    'boarding_interval':p['boarding_interval_x_m']==[start,970.],
                    'rear_marker':abs(m.position[0]-(start+5.))<1e-6,
                    'terminal_position':math.dist(limit.position,(1000.,y))<1e-6}
            if not all(checks.values()):geometry_errors.append(p['id'])
            platforms.append({'platform':p['id'],'checks':checks,'usable_m':p['usable_length_m']})
    special=[e for e in n.edges.values() if e.component]
    lo=min(e.curve.bounds()[0] for e in special);hi=max(e.curve.bounds()[2] for e in special)
    throat_ok=lo>=150.-1e-6 and hi<=650.+1e-6
    if not throat_ok:geometry_errors.append('specialwork_outside_throat_region')
    k=max(v['curvature_upper_per_m'] for v in compiled.provenance['curves'].values())
    numerical={'base_radius_floor':new_line_radius(1/k,applicable=True,new_line=True,straight=False)}
    for pid,p in compiled.platforms.items():
        straight=compiled.provenance['curves'][p['storage_edge']]['curvature_upper_per_m']==0.
        numerical[pid]={'platform_radius':platform_radius(None,applicable=True,new_line=True,straight=straight),
                        'platform_cant':platform_cant(n.metadata['cant_mm'],applicable=True,normal_service_stop=True),
                        'GB_interface':gb_platform_interface()}
    admission_result=admission('gb_rules_strict',synthetic_components=True,
        mandatory_unknowns=['authentic_pointwork','diamond_hardware','dynamic_vehicle_gauge','platform_height_offset','signal_protection'],game_tested=False)
    component_report=copy.deepcopy(station.component_report)
    gates={'centreline_site_and_concourse':site['status']=='pass_within_scope',
           'original_platform_and_buffer_positions':not geometry_errors,
           'specialwork_throat_region':throat_ok,
           'exact_approach_positions':not site['required_port_mismatches']}
    return {'schema_version':'0.7.0','family':station.family,'compile_hash':compiled.compile_hash,
            'original_brief_site':site,'plan_contract_gates':gates,'plan_contract_passed':all(gates.values()),
            'platform_checks':platforms,'plan_errors':geometry_errors,'changed_brief_fields':[],
            'specialwork_extent_m':[lo,hi],'radius_lower_bound_m':1/k,
            'normal_independence':independence(compiled),'component_admission':component_report,
            'selected_numerical_checks':numerical,'strict_UK_input_gate':admission_result,
            'vehicle_summary':{'record_hash':vehicle['vehicle_resolution']['record_hash'],
                 'routes_evaluated':vehicle['routes_evaluated'],'pairs_evaluated':vehicle['route_pairs_evaluated'],
                 'full_gauge':'unassessed','parent_curve_body_error':'unassessed'},
            'plan_scope':'un-padded centreline control hull, exact ports, platform intervals, terminal markers and supplied planar concourse reservation',
            'unassessed':['whole-vehicle site boundary incl. external continuations','platform islands and access','buffer stopping/overrun engineering',
                          'authentic turnout and diamond','full dynamic gauge','speed suitability','game representation'],
            'construction_authorised':False,'full_original_brief_satisfied':False}


def decisions(results,assessments,required):
    if not isinstance(required,list) or not required or len(set(required))!=len(required):raise ValueError('distinct_required_scenarios_needed')
    if not results or set(results)!=set(assessments):raise ValueError('missing_candidate_assessment')
    for sc in required:
        if any(sc not in results[f] for f in results):raise ValueError('missing_required_scenario')
        if len({results[f][sc]['scenario_hash'] for f in results})!=1:raise ValueError('incomparable_scenarios')
    rows=[]
    for f in sorted(results):
        a=assessments[f];rs=[results[f][sc] for sc in required]
        for r in rs:
            if r['compile_hash']!=a['compile_hash'] or r['candidate_assessment_hash']!=digest(a):raise ValueError('stale_assessment_join')
            if r.get('independent_check',{}).get('status')!='pass':raise ValueError('unverified_operating_result')
        op=all(r['all_required_completed_within_horizon'] for r in rs)
        row={'candidate':f,'plan_contract_passed':a['plan_contract_passed'],'operating_scenarios_passed':op,
             'eligible_for_offline_comparison':op and a['plan_contract_passed'],
             'completed':sum(r['completed_within_horizon'] for r in rs),'required':sum(r['required_visits'] for r in rs),
             'unscheduled':sum(r['unscheduled_visits'] for r in rs),'delay_ms_scheduled_only':sum(r['total_departure_delay_ms'] for r in rs),
             'specialwork_count':len(a['component_admission']['imported_instances'])+6,
             'diamond_count':1 if f=='scissors' else 0,'compile_hash':a['compile_hash']}
        rows.append(row)
    eligible=[r for r in rows if r['eligible_for_offline_comparison']]
    chosen=min(eligible,key=lambda r:(r['specialwork_count'],r['diamond_count'],r['delay_ms_scheduled_only'],r['candidate'])) if eligible else None
    return {'schema_version':'0.7.0','required_scenarios':required,'candidates':rows,
            'offline_candidate':chosen['candidate'] if chosen else None,
            'status':'offline_option_identified' if chosen else 'no_tested_candidate_meets_requested_set',
            'ranking_policy':'plan and completion first; then fewer switches, fewer diamonds, delay; a project preference, not a universal railway verdict',
            'construction_authorised':False,'scope':'fixed candidates, greedy scheduling, explicit unresolved engineering/game gates'}
