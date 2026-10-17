"""Carry component, vehicle, numerical and site evidence onto whole candidates."""
from __future__ import annotations
from dataclasses import asdict
import copy
from railclear.catalogue import read_json
from railclear.profiles import resolve_vehicle
from railclear.demo import extended_route
from railclear.model import bounds, bounds_gap, digest
from railclear.sweep import sweep, pair_screen
from railops.uk_profiles import admission, new_line_radius
from railproof.rules import platform_cant,platform_radius,gb_platform_interface
from .composition import Station, EVIDENCE
from .checks import independence,site_check


def vehicle_audit(station:Station,compiled,assumptions:dict,*,step_m:float=3.,max_poses:int=3000,
                  max_pairs:int=2000000)->dict:
    resolved=resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),assumptions)
    body=resolved.pop('body');a=station.assembly;ext=35.;sweeps={};rows=[]
    before=a.network.digest()
    for rid in sorted(a.routes):
        path=extended_route(a,rid,ext)
        end=path.length_m-ext+(body.length_m+body.bogie_centres_m)/2
        sw=sweep(path,body,ext,end,step_m,max_poses)
        sweeps[rid]=sw
        pts=[point for pose in sw.poses for point in pose.corners]
        raw=bounds(pts);pad=sw.between_pose_padding_m
        rows.append({'route_id':rid,**sw.export(False),
                     'static_polyline_swept_box_m':[raw[0]-pad,raw[1]-pad,raw[2]+pad,raw[3]+pad]})
    # All 4x4 normal arrival pairs, plus representative departure and recovery
    # interactions. Other pair types explicitly remain outside this audit.
    requests=[(f'A:A{i}:in',f'B:B{j}:in') for i in range(1,5) for j in range(1,5)]
    requests += [('A:A4:out','B:B1:out'),('A:A4:in','B:B1:out')]
    if station.family=='a_to_b':requests += [('A:B1:in','B:B1:in'),('A:B1:out','A:A1:out')]
    if station.family=='b_to_a':requests += [('B:A1:in','A:A1:in'),('B:A1:out','B:B1:out')]
    pairs=[]
    for x,y in requests:
        sa,sb=sweeps[x],sweeps[y]
        # AABB of all poses minus both between-pose paddings is a conservative
        # lower bound. Use it only when positive; otherwise retain exact-pair
        # screening with its explicit budget and uncertainty status.
        ba=bounds([p for pose in sa.poses for p in pose.corners]);bb=bounds([p for pose in sb.poses for p in pose.corners])
        lower=bounds_gap(ba,bb)-sa.between_pose_padding_m-sb.between_pose_padding_m
        if lower>0:
            row={'status':'clear_within_polyline_static_model','continuous_gap_lower_bound_m':lower,
                 'method':'global_pose_box_lower_bound_minus_between_pose_padding',
                 'may_remove_existing_resource':False,'full_UK_gauging':'unassessed'}
        else:row=pair_screen(sa,sb,max_pairs)
        row.update({'route_a':x,'route_b':y});pairs.append(row)
    return {'schema_version':'0.6.0','family':station.family,'compile_hash':compiled.compile_hash,
            'vehicle_resolution':{**resolved,'body':asdict(body)},'routes':rows,'pairs':pairs,
            'routes_evaluated':len(rows),'route_pairs_evaluated':len(pairs),
            'unchanged_network_hash':before==a.network.digest(),'resource_mutations':[],
            'support_assumption':{'length_each_m':ext,'kind':'authored_tangent_continuation; not checked external railway'},
            'coverage':'single representative rigid body on every selected route; listed route pairs only',
            'full_formation_positions':'unassessed','parent_Bezier_body_error_bound':'unassessed',
            'full_dynamic_3D_gauge':'unassessed'}


def assess_candidate(station:Station,compiled,vehicle:dict)->dict:
    expected={'A:ARRIVAL':[0.,-18.],'A:DEPARTURE':[0.,-6.],
              'B:ARRIVAL':[0.,6.],'B:DEPARTURE':[0.,18.]}
    original=site_check(station,[0.,-90.,1200.,90.],expected_ports=expected)
    reservation=[{'id':'concourse_reservation','box_m':[2020.,-75.,2180.,75.]}]
    proposed=site_check(station,[-5.,-90.,2200.,90.],padding_m=1.75,reservations=reservation)
    ports=station.assembly.network.ports.values()
    span=max(p.position[0] for p in ports)-min(p.position[0] for p in ports)
    original['fixed_orientation_translation_certificate']={
        'actual_port_x_span_m':span,'available_x_span_m':1200.,'fits_under_translation_only':span<=1200.,
        'scope':'this fixed candidate cannot be translated into the box; other shapes/families/rotation not ruled out'}
    records=compiled.provenance['curves'];k=max(r['curvature_upper_per_m'] for r in records.values())
    radius=1/k if k>0 else None
    checks={'whole_candidate_base_radius_floor':new_line_radius(radius,applicable=True,new_line=True,straight=k==0)}
    # The current platform edges are straight and level; retain individual,
    # condition-scoped results instead of a blanket UK compliance label.
    for pid,p in compiled.platforms.items():
        storage_k=records[p['storage_edge']]['curvature_upper_per_m']
        straight=storage_k==0
        cant=station.assembly.network.metadata.get('cant_mm')
        checks[pid]={'usable_length_m':p['usable_length_m'],'interval_m':p['boarding_interval_x_m'],
                     'straight':straight,'cant_mm':cant,
                     'platform_cant':platform_cant(cant,applicable=True,normal_service_stop=True),
                     'platform_radius':platform_radius(None if straight else 1/storage_k,applicable=True,new_line=True,straight=straight),
                     'GB_interface':gb_platform_interface(),
                     'applicability_origin':'explicit new-line study assumption; not automatic national profile resolution'}
    input_gate=admission('gb_rules_strict',synthetic_components=True,
         mandatory_unknowns=['exact_vehicle_geometry','dynamic_gauge_method','pointwork_speed_applicability',
                             'platform_height_offset','real_release_profile'],game_tested=False)
    return {'schema_version':'0.6.0','family':station.family,'compile_hash':compiled.compile_hash,
            'original_brief_site':original,'proposed_larger_test_site':proposed,
            'normal_independence':independence(compiled),'component_admission':station.component_report,
            'selected_numerical_checks':checks,'strict_UK_input_gate':input_gate,
            'vehicle_summary':{'record_hash':vehicle['vehicle_resolution']['record_hash'],
               'routes_evaluated':vehicle['routes_evaluated'],'pairs_evaluated':vehicle['route_pairs_evaluated'],
               'full_gauge':'unassessed','parent_curve_body_error':'unassessed'},
            'changed_brief_fields':['site longitudinal extent','three of four exact approach ordinates',
                                   'absolute platform and concourse locations'],
            'retained_brief_fields':['four directional approach roles','eight platform roads',
                 'two service groups','four 260 m and four 320 m boarding intervals','platform-road y positions'],
            'construction_authorised':False,'game_status':'not_tested'}


def decision_packet(results:dict[str,dict[str,dict]],assessments:dict[str,dict],required_scenarios:list[str])->dict:
    if not required_scenarios or len(required_scenarios)!=len(set(required_scenarios)):raise ValueError('Distinct required scenarios needed')
    families=sorted(results)
    if set(assessments)!=set(families):raise ValueError('Missing candidate assessment')
    for sc in required_scenarios:
        if any(sc not in results[f] for f in families):raise ValueError('Missing comparison scenario')
        if len({results[f][sc]['scenario_hash'] for f in families})!=1:raise ValueError('Incomparable scenario inputs')
    rows=[]
    for f in families:
        rs=[results[f][sc] for sc in required_scenarios]
        for r in rs:
            if r['compile_hash']!=assessments[f]['compile_hash']:raise ValueError('Stale result/assessment join')
            if r.get('independent_check',{}).get('status')!='pass':raise ValueError('Unverified operating result')
        feasible=all(r['all_required_completed_within_horizon'] for r in rs)
        rows.append({'candidate':f,'operating_scenarios_satisfied':feasible,
             'required':sum(r['required_visits'] for r in rs),'completed':sum(r['completed_within_horizon'] for r in rs),
             'unscheduled':sum(r['unscheduled_visits'] for r in rs),'residual':sum(r['scheduled_residual_at_horizon'] for r in rs),
             'delay_ms_scheduled_only':sum(r['total_departure_delay_ms'] for r in rs),
             'original_site_status':assessments[f]['original_brief_site']['status'],
             'strict_UK_status':assessments[f]['strict_UK_input_gate']['UK_profile_gate'],
             'compile_hash':assessments[f]['compile_hash']})
    eligible=[r for r in rows if r['operating_scenarios_satisfied']]
    # Operating-only ordering: never convert the selected row into build approval.
    preferred=min(eligible,key=lambda r:(r['delay_ms_scheduled_only'],r['candidate']))['candidate'] if eligible else None
    return {'schema_version':'0.6.0','required_scenarios':required_scenarios,'candidates':rows,
         'status':'operating_option_identified_site_and_engineering_gates_open' if eligible else 'no_tested_candidate_meets_required_recovery_set',
         'operating_only_candidate':preferred,'construction_authorised':False,
         'open_decisions':['retain original footprint and search a different geometry/topology, or explicitly adopt a larger study boundary'],
         'mandatory_unknowns':['authentic UK pointwork','full vehicle gauging','platform interfaces','game capability'],
         'scope':'three tested family instances under a greedy scheduler; not exhaustive feasibility or an optimum proof'}
