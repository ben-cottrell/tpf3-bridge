"""Reproducible offline clearance and component-import study. No model/game calls."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from .model import (Body, Polyline, parallel_gap, concentric_gap, circular_band,
                    from_curves, positive, count, digest)
from .profiles import resolve_vehicle
from .catalogue import read_json, import_component, place_synthetic, exact, identifier
from .sweep import sweep, pair_screen, obstacle_screen, audit_pair_requests
from railgeom.curves import line, mul, norm, sub, add
from railgeom.patterns import build_crossover, Assembly, GeometryProfile
from railgeom.compiler import compile_assembly
from railops.access import build_dual_access
from railops.sectional import compile_leg

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT.parent/'evidence'


def read_fixture(path):
    d=read_json(path)
    exact(d,('schema_version','scenario_id','fidelity','assumptions','spacing_m','curve_radii_m',
             'bogie_sensitivity_m','sweep_step_m','refined_step_m','support_extension_m','max_poses','max_pairs'))
    if d['schema_version']!='0.5.0' or d['fidelity']!='reference_informed_assumptions':raise ValueError('Wrong study scope')
    identifier(d['scenario_id'])
    for k in ('spacing_m','sweep_step_m','refined_step_m','support_extension_m'):positive(d[k],k)
    for k in ('curve_radii_m','bogie_sensitivity_m'):
        if not isinstance(d[k],list) or not 1<=len(d[k])<=50:raise ValueError('Sensitivity budget')
        for x in d[k]:positive(x,k)
    count(d['max_poses'],'max poses',100000);count(d['max_pairs'],'max pairs',100000000)
    resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),d['assumptions'])
    return d


def extended_route(assembly,route_id,extension_m):
    """Explicit authored tangent supports: not evidence of outside infrastructure."""
    extension_m=positive(extension_m,'support extension')
    path=assembly.routes[route_id]
    curves=tuple(assembly.network.oriented_curve(s) for s in path.steps)
    first,last=curves[0],curves[-1]
    u=first.tangent(0);u=mul(u,1/norm(u));v=last.tangent(1);v=mul(v,1/norm(v))
    support=(line(sub(first.at(0),mul(u,extension_m)),first.at(0)),
             line(last.at(1),add(last.at(1),mul(v,extension_m))))
    return from_curves((support[0],)+curves+(support[1],),assembly.network.digest())


def run(fixture_path:Path,output:Path):
    f=read_fixture(fixture_path);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def write(name,value):
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    resolved=resolve_vehicle(read_json(EVIDENCE/'vehicle_reference.json'),f['assumptions']);body=resolved.pop('body')
    write('vehicle_resolution.json',{**resolved,'body':asdict(body)})
    rows=[]
    for B in f['bogie_sensitivity_m']:
        b=Body(body.length_m,body.width_m,B,0.,body.fidelity,body.profile_id)
        straight=parallel_gap(f['spacing_m'],b,b)
        rows.append({'radius_m':None,'bogie_centres_m':B,'gap_m':straight['gap_m'],'status':straight['status'],'allowance_each_m':0.})
        for R in f['curve_radii_m']:
            result=concentric_gap(R,f['spacing_m'],b,b)
            rows.append({'radius_m':R,'bogie_centres_m':B,'gap_m':result['gap_m'],'status':result['status'],
                         'centre_inthrow_m':result['inner']['centre_inthrow_m'],'allowance_each_m':0.})
    long=Body(26.,2.8,19.,.1)
    long_result=concentric_gap(150.,f['spacing_m'],long,long)
    write('spacing_sensitivity.json',{'rows':rows,'origin':'20 m and 2.8 m catalogue-informed body; bogie spacing assumed',
          'long_body_counterexample':{'body':asdict(long),'result':long_result,'origin':'wholly synthetic 26 m body, 19 m pivots, 0.1 m allowance each'},
          'full_UK_gauging':'unassessed','nominal_spacing_applicability':'3.4 m source reference only for straight/R>=400m; smaller radii are deliberate stress cases, not authorised GB defaults'})
    cross=build_crossover();before=cross.network.digest();cc=compile_assembly(cross)
    ext=f['support_extension_m'];sw={}
    for id in cross.routes:
        p=extended_route(cross,id,ext)
        sw[id]=sweep(p,body,ext,p.length_m-ext+(body.length_m+body.bogie_centres_m)/2,
                     f['sweep_step_m'],f['max_poses'])
    overlay=audit_pair_requests(sw,[('lower_through','upper_through'),('lower_through','cross_forward'),('upper_through','cross_forward')],f['max_pairs'])
    overlay['support_assumption']={'before_each_route_m':ext,'after_each_route_m':ext,'kind':'authored_tangent_continuation_not_observed_world'}
    overlay['existing_compile_hash']=cc.compile_hash
    overlay['unchanged_network_hash']=before==cross.network.digest()
    write('crossover_clearance_overlay.json',overlay)
    write('crossover_forward_sweep.json',sw['cross_forward'].export())
    # Refine the all-pose bound on the separated straight routes without changing
    # geometry or body dimensions until something passes.
    a=Polyline(((0.,0.),(100.,0.)));b=Polyline(((0.,f['spacing_m']),(100.,f['spacing_m'])))
    refinement=[]
    for step in (f['sweep_step_m'],f['refined_step_m']):
        sa=sweep(a,body,25.,75.,step,f['max_poses']);sb=sweep(b,body,25.,75.,step,f['max_poses'])
        row=pair_screen(sa,sb,f['max_pairs']);row['requested_step_m']=step;refinement.append(row)
    write('straight_refinement.json',{'runs':refinement,'dimensions_changed':False,'resource_mutations':[]})
    # Circular inward overhang against a small planar obstruction.
    R=400.;pts=tuple((R*math.cos(math.pi/2-.12+.24*i/400),R*math.sin(math.pi/2-.12+.24*i/400)) for i in range(401))
    arc=Polyline(pts,'authored circular polyline; not a georeferenced railway')
    arc_sweep=sweep(arc,body,20.,arc.length_m-10.,f['refined_step_m'],f['max_poses'])
    inner=circular_band(R,body)['inner_radius_m']
    obstacle=((-0.25,inner+.003),(.25,inner+.003),(.25,inner+.013),(-.25,inner+.013))
    ob=obstacle_screen(arc_sweep,obstacle)
    ob['purpose']='Small obstruction reaches body inthrow despite positive track-centreline distance'
    ob['centreline_at_x0_y_m']=R;ob['analytic_body_inner_y_m']=inner
    write('curve_overhang_obstacle.json',ob)
    # Apply published full-unit length only to the scalar fit/motion interface;
    # it never becomes the length of a single rigid swept body.
    bank=build_dual_access();compiled=compile_assembly(bank);formation=[]
    for name,key in (('8-car','unit_8car_length_m'),('12-car','unit_12car_length_m')):
        length=resolved['published'][key];p=bank.platforms['P4']
        leg=compile_leg(compiled,'P4:in',length,'in')
        row={'formation':name,'published_unit_length_m':length,'source_id':'S060',
             'boarding_length_m':p['usable_length_m'],'end_margin_each_m':p['margin_each_end_m'],
             'spare_after_margins_m':p['usable_length_m']-2*p['margin_each_end_m']-length,
             'scalar_fit':length+2*p['margin_each_end_m']<=p['usable_length_m'],
             'arrival_stop_ms':leg.motion_end_ms,'last_release_ms':leg.release_end_ms,
             'source_geometry_compile_hash':compiled.compile_hash,'motion_profile':asdict(leg.profile),
             'motion_origin':'unchanged v0.4 project profile, not a calibrated Desiro performance curve',
             'full_formation_sweep':'unassessed'}
        formation.append(row)
    write('published_formation_length_trial.json',{'rows':formation,'status':'scoped_scalar_and_motion_experiment','UK_platform_interface':'unassessed'})
    route=extended_route(bank,'P4:in',ext)
    bank_sweep=sweep(route,body,ext,route.length_m-ext+(body.length_m+body.bogie_centres_m)/2,
                     f['sweep_step_m'],f['max_poses'])
    write('bank_route_sweep.json',{'sweep':bank_sweep.export(),'support_extension_each_m':ext,
         'scope':'single representative body along generated P4 arrival plus assumed supports; not a complete train sweep'})
    synthetic=import_component(read_json(EVIDENCE/'component_import_synthetic.json'))
    pending=import_component(read_json(EVIDENCE/'component_import_pending.json'))
    placed=place_synthetic(synthetic,10.,20.,.2,True)
    imported_assembly=Assembly(placed,{name:placed.one_path('T',end,name) for name,end in (('normal','N'),('reverse','R'))},{},GeometryProfile())
    imported_compile=compile_assembly(imported_assembly)
    write('component_import_results.json',{'synthetic':synthetic.report,'pending_external':pending.report,
          'normalized_synthetic_geometry':synthetic.normalized_geometry,
          'placed_synthetic_network':placed.canonical(),'compiled_imported_geometry':imported_compile.export(),'authentic_component_imported':False,
          'note':'No product page has been substituted for an actual dimensional drawing.'})
    summary={'schema_version':'0.5.0','fixture_hash':hashlib.sha256(Path(fixture_path).read_bytes()).hexdigest(),
             'vehicle_record_hash':resolved['record_hash'],'spacing_rows':len(rows),'crossover_pair_studies':len(overlay['results']),
             'source_compile_hashes':[cc.compile_hash,compiled.compile_hash],
             'crossover_statuses':[r['status'] for r in overlay['results']],
             'refinement_statuses':[r['status'] for r in refinement],'obstacle_status':ob['status'],
             'formation_length_trials':len(formation),'resource_mutations':[],
             'assessments':{'planar_rigid_body_model':'executed','polyline_between_pose_bound':'executed',
                 'authentic_vehicle_gauge':'unassessed','actual_bogie_spacing':'unresolved',
                 'component_geometry_import_path':'restricted_synthetic_three_port_contract_executed',
                 'authentic_UK_turnout_import':'not_acquired','3D_dynamics_and_cant':'not_implemented','game':'not_tested'}}
    write('summary.json',summary)
    write('decision_packet.json',{'status':'offline_evidence_ready_not_build_authorised',
          'result_ref':'clearance_results/summary.json','material_findings':[
              'Published width replaces an arbitrary width only in a separate declared study.',
              'Bogie spacing and exact body outline remain explicit assumptions.',
              'Body sweep reports do not delete existing conflict resources.',
              'Published unit lengths now drive scalar fit and tail-clear calculations.'],
          'next_gate':'Verified bogie/outline data and an authorised component drawing; then multi-bank composition.',
          'full_UK_gauging':'unassessed','construction_authorised':False})
    lines=['# v0.5 clearance studies','',
           'Executed mathematical studies, not real-site capacity or approved vehicle gauging. All bogie spacings below are assumptions.',
           '', '| Inner radius | Bogie centres | Raw static gap at 3.4 m centres |', '|---|---:|---:|']
    for row in rows:lines.append(f"| {'Straight' if row['radius_m'] is None else str(row['radius_m'])+' m'} | {row['bogie_centres_m']:.1f} m | {row['gap_m']:.6f} m |")
    lines+=['','Smaller-radius cases do not inherit the source nominal-spacing applicability. See JSON for assumed allowances and the long-body counterexample.',
            '', '| Crossover route pair | Result |','|---|---|']
    lines += [f"| {r['route_a']} / {r['route_b']} | {r['status']} |" for r in overlay['results']]
    lines += ['','The crossover paths include explicitly assumed tangent supports. No legacy resource was removed.',
              '', '| Formation | Published length | Spare after stated margins | Stop after activation |', '|---|---:|---:|---:|']
    lines += [f"| {r['formation']} | {r['published_unit_length_m']} m | {r['spare_after_margins_m']:.3f} m | {r['arrival_stop_ms']/1000:.3f} s |" for r in formation]
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=ROOT/'clearance_fixtures/release.json')
    p.add_argument('--output',type=Path,default=ROOT/'clearance_results');args=p.parse_args()
    print(json.dumps(run(args.fixture,args.output),indent=2))
