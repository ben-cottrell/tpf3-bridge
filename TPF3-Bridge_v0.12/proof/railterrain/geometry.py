"""Refit the connected junction between the corridor's immutable interfaces.

Only plain-line connections are re-fitted. Imported turnout geometry is rigidly
translated. The original corridor is a design baseline, NOT already built track
onto which another railway is silently overlaid. All old modules stay frozen.
"""
from __future__ import annotations
from dataclasses import asdict
import math
from railbranch.geometry import (Junction, JunctionSpec, build as build_local,
    hermite, state, ordered_curves_lower_gap)
from railcorridor.geometry import Alignment, Knot, digest, number
from railgeom.curves import Bezier, line
from railgeom.network import Network, Turnout

EXTERNAL = ('W_E', 'W_W', 'E_E', 'E_W', 'B_OUT', 'B_IN')
PAIRS = (('main_east','W_E','E_E'), ('main_west','E_W','W_W'),
         ('branch_out','W_E','B_OUT'), ('branch_in','B_IN','W_W'))


def route_records(j):
    records = {}
    for rid, path in j.routes.items():
        total = 0.; steps = []
        for s in path.steps:
            e = j.network.edges[s.edge_id]; length = j.length(e.id)
            steps.append(dict(edge_id=e.id,forward=s.forward,s0_m=total,
                s1_m=total+length,length_m=length,controller=e.controller,
                state=e.state,component=e.component))
            total += length
        records[rid] = dict(start=path.start,end=path.end,steps=steps,length_m=total)
    return records


def build_placed(spec: JunctionSpec, mode: str, lateral_m: float,
                 main_restore_x_m: float) -> Junction:
    """Construct a new physical network; retain six absolute external ports.

    `lateral_m` shifts all internal bank/branch geometry. Plain-line approaches
    return to the original external coordinates with zero slope/curvature.
    This is intentionally restricted to x-monotone, level external interfaces.
    """
    number(lateral_m,'lateral placement',minimum=-600,maximum=600)
    number(main_restore_x_m,'main restore',minimum=spec.diverge_x_m+100,
           maximum=spec.branch_parallel_x_m)
    old = build_local(spec,mode)
    n = Network('TERRAIN_BRANCH',metadata={
        'fidelity':'gb_reference_inspired_authored_components', 'cant_mm':0,
        'replacement_scope':'unbuilt corridor design between fixed external ports'})
    for pid,p in old.network.ports.items():
        n.port(pid, (p.position[0],p.position[1]+(0 if pid in EXTERNAL else lateral_m)),p.role)
    # Reuse immutable controller identities and exact local point geometry.
    for cid,t in old.network.turnouts.items():
        n.turnouts[cid] = Turnout(t.id,t.toe,t.normal,t.reverse,t.controller,t.normal_state,t.reverse_state)
    restore='EAST_RESTORE';n.port(restore,(main_restore_x_m,spec.track_centres_m/2+lateral_m),'internal')
    spread='EAST_SPREAD';n.port(spread,(spec.spread_finish_x_m,spec.track_centres_m/2+lateral_m),'internal')
    replacements = {'east_approach','west_exit','west_restore','out_boundary','return_boundary'}
    for eid,e in old.network.edges.items():
        u,v=e.u,e.v
        if eid=='east_approach':
            v=spread;curve=hermite(n.ports[u].position,n.ports[v].position)
        elif eid=='east_continuation':
            v=restore;curve=line(n.ports[u].position,n.ports[v].position)
        elif eid in replacements:
            curve=hermite(n.ports[u].position,n.ports[v].position)
        else:
            curve=Bezier(tuple((x,y+lateral_m) for x,y in e.curve.controls))
        n.edge(eid,u,v,curve,component=e.component,controller=e.controller,state=e.state,kind=e.kind)
    d=next(t for k,t in n.turnouts.items() if k.startswith('D:'))
    n.edge('east_sorted_approach',spread,d.toe,line(n.ports[spread].position,n.ports[d.toe].position))
    n.edge('east_restore',restore,'E_E',hermite(n.ports[restore].position,n.ports['E_E'].position))
    n.validate()
    heights={}
    for eid,e in n.edges.items():
        if eid=='return_connector': heights[eid]=old.height[eid]
        else: heights[eid]=Alignment((Knot(e.curve.at(0)[0],0,spec.rail_height_m),
                                      Knot(e.curve.at(1)[0],0,spec.rail_height_m)))
    routes={rid:n.one_path(a,b,rid) for rid,a,b in PAIRS}
    j=Junction(spec,mode,n,routes,heights,{})
    checks=[];failed=[]
    for eid,e in n.edges.items():
        L=e.curve.at(1)[0]-e.curve.at(0)[0]
        yy=max(abs(p[1]) for p in e.curve.derivative_controls(2))/L**2
        yp=max(abs(p[1]) for p in e.curve.derivative_controls())/L
        vb=heights[eid].bounds();ku=e.curve.curvature_upper(7)
        row=dict(edge_id=eid,curvature_upper_per_m=ku,
                 radius_lower_bound_m=None if ku==0 else 1/ku,
                 grade_upper=vb['grade_upper'],
                 vertical_curvature_upper_per_m=vb['vertical_curvature_upper']+vb['grade_upper']*yp*yy)
        row.update(radius_pass=ku<=1/spec.minimum_radius_m,
                   grade_pass=row['grade_upper']<=spec.maximum_grade,
                   vertical_pass=row['vertical_curvature_upper_per_m']<=1/spec.minimum_vertical_radius_m)
        failed.extend(eid+':'+key for key in ('radius_pass','grade_pass','vertical_pass') if not row[key])
        checks.append(row)
    cross=dict(old.assessment['crossing'])
    cross['y_m'] += lateral_m
    if main_restore_x_m<=cross['footprint_x_m'][1]:
        raise ValueError('restored main curve intersects the declared crossing window')
    # Explicit ordering proofs for the supported corridor families. These compare
    # centrelines, not rolling-stock outlines or perpendicular dynamic gaps.
    gaps=[]
    def group_gap(upper_id,lower_id):
        a,b=n.edges[upper_id].curve,n.edges[lower_id].curve
        lo=max(a.at(0)[0],b.at(0)[0]);hi=min(a.at(1)[0],b.at(1)[0])
        if hi-lo<=1e-8:return
        # Elevate any straight's degree to match the quintic before Bernstein comparison.
        def quintic(c):
            if len(c.controls)==2:return hermite(c.at(0),c.at(1),state(c,c.at(0)[0])[1],state(c,c.at(1)[0])[1])
            return c
        gap=ordered_curves_lower_gap(quintic(a),quintic(b),lo,hi,depth=9)
        gaps.append(dict(upper=upper_id,lower=lower_id,x_interval_m=[lo,hi],y_order_lower_bound_m=gap))
        if gap<=0:failed.append('unresolved_track_order:'+upper_id+':'+lower_id)
    east_edges=[s.edge_id for s in routes['main_east'].steps]
    west_edges=[s.edge_id for s in routes['main_west'].steps]
    for a in east_edges:
        for b in west_edges:group_gap(a,b)
    group_gap('out_connector','return_connector');group_gap('out_boundary','return_boundary')
    # Branch connections must remain above the eastern main after their one
    # declared crossing / divergence. Ordering was constant in the source family;
    # the refitted exits require fresh checks.
    group_gap('out_boundary','east_restore');group_gap('return_boundary','east_restore')
    ports3={}
    for eid,e in n.edges.items():
        for pid,x in ((e.u,e.curve.at(0)[0]),(e.v,e.curve.at(1)[0])):
            pos=j.point(eid,x)
            if pid in ports3 and math.dist(pos,ports3[pid])>1e-7:raise ValueError('3D join mismatch')
            ports3[pid]=pos
    hull=[min(p[0] for e in n.edges.values() for p in e.curve.controls),
          min(p[1] for e in n.edges.values() for p in e.curve.controls),
          max(p[0] for e in n.edges.values() for p in e.curve.controls),
          max(p[1] for e in n.edges.values() for p in e.curve.controls)]
    a=dict(version='0.11.0',mode=mode,spec=asdict(spec),network=n.canonical(),
        height_profiles={k:v.record() for k,v in heights.items()},ports_xyz_m=ports3,
        component_record_hash=old.assessment['component_record_hash'],
        component_geometry_hash=old.assessment['component_geometry_hash'],
        component_authenticity='authored_synthetic_import_rigid_translation_only',
        source_local_candidate_hash=old.assessment['candidate_hash'],
        placement=dict(lateral_m=lateral_m,main_restore_x_m=main_restore_x_m),
        curve_checks=checks,failed_checks=failed,plan_control_hull_m=hull,
        crossing=cross,plan_order_checks=gaps,routes=route_records(j),
        accepted_for_reference_comparison=not failed,
        complete_required_routes_connected=True,internal_open_connection_ports=[],
        external_boundary_positions_preserved=True,
        terrain_assessment='pending_terrain_binding',station_internal_edits=False,
        construction_authorised=False,game_constructed=False,
        unassessed=['authentic pointwork','3D/dynamic gauging','grade-sensitive performance','game adapter'])
    a['candidate_hash']=digest(a);j.assessment=a
    return j


def mainline_profile_check(j,profile):
    """Reapply the original corridor targets to BOTH actual main-line routes.

    Curvature/gradient use the per-edge conservative bounds. The curvature-rate
    bound |y'''|+3|y'||y''|^2 is valid for x-affine graphs with ds/dx >= 1.
    A failed sufficient bound is not an exact violation or speed certification.
    """
    from railcorridor.geometry import number
    speed=profile['speed_mph']*.44704;rows=[]
    ids=sorted({s.edge_id for name in ('main_east','main_west') for s in j.routes[name].steps})
    for eid in ids:
        e=j.network.edges[eid];L=e.curve.at(1)[0]-e.curve.at(0)[0]
        def local_rate(c,depth=5):
            if depth:
                a,b=c.split();return max(local_rate(a,depth-1),local_rate(b,depth-1))
            length=c.at(1)[0]-c.at(0)[0]
            d=[max(abs(v[1]) for v in c.derivative_controls(k))/length**k for k in (1,2,3)]
            return d[2]+3*d[0]*d[1]**2
        rate=local_rate(e.curve)
        bound=next(r for r in j.assessment['curve_checks'] if r['edge_id']==eid)
        ku=bound['curvature_upper_per_m']
        reasons=[]
        if ku>1/profile['min_radius_m']:reasons.append('main_radius_bound')
        if bound['grade_upper']>profile['max_grade']:reasons.append('main_grade_bound')
        if bound['vertical_curvature_upper_per_m']>1/profile['min_vertical_radius_m']:reasons.append('main_vertical_bound')
        if speed**2*ku>profile['max_lateral_accel_mps2']:reasons.append('main_lateral_accel_bound')
        if speed**3*rate>profile['max_lateral_jerk_mps3']:reasons.append('main_jerk_bound')
        rows.append(dict(edge_id=eid,radius_lower_bound_m=bound['radius_lower_bound_m'],
            zero_cant_lateral_accel_upper_mps2=speed**2*ku,
            constant_speed_lateral_jerk_upper_mps3=speed**3*rate,reasons=reasons,passed=not reasons))
    return dict(status='project_mainline_bounds_pass' if all(r['passed'] for r in rows) else 'not_certified_by_mainline_bounds',
                profile=dict(profile),edges=rows,turnout_speed_rating='unassessed',
                unchanged_mainline_targets=True,scope='zero-cant project screens, not actual train dynamics')
