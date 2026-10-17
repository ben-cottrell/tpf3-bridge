"""Terrain and land reservations for every physical edge, not service-route copies.

Analytic box bounds cover the supplied synthetic ridge and each Bezier subcurve.
Lengths/classification remain midpoint planning estimates. Rectangular reservation
unions avoid counting overlapping parallel-track land twice. No terrain edits,
actual structure selection, hydraulic design, or geotechnical approval occur.
"""
from __future__ import annotations
from copy import deepcopy
import math
from railbranch.geometry import restrict
from railcorridor.geometry import digest, number
from railcorridor.planning import bell, ground

KINDS=('surface','cutting','embankment','river_bridge','viaduct','tunnel')


def bell_range(a,b,centre,half):
    """Exact extrema of the nonnegative compact bell over a closed interval."""
    if a>b or half<=0:raise ValueError('bell interval')
    near=0. if a<=centre<=b else min(abs(a-centre),abs(b-centre))
    far=max(abs(a-centre),abs(b-centre))
    return bell(far/half),bell(near/half)


def ground_range(t,box,wet=False):
    if wet:return (t['river_bed_m'],t['river_bed_m'])
    x0,y0,x1,y1=box
    a,b=bell_range(x0,x1,t['ridge_x_m'],t['ridge_half_x_m'])
    c,d=bell_range(y0,y1,0,t['ridge_half_y_m'])
    return t['base_height_m']+t['ridge_height_m']*a*c,t['base_height_m']+t['ridge_height_m']*b*d


def overlaps(a,b):return a[0]<=b[2] and a[2]>=b[0] and a[1]<=b[3] and a[3]>=b[1]
def within(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]


def rectangle_union_area(rectangles):
    """Exact union of the supplied axis-aligned boxes (ordinary floats)."""
    boxes=[r for r in rectangles if r[2]>r[0] and r[3]>r[1]]
    xs=sorted({x for r in boxes for x in (r[0],r[2])});area=0.
    for a,b in zip(xs,xs[1:]):
        mid=(a+b)/2;ys=sorted((r[1],r[3]) for r in boxes if r[0]<=mid<=r[2])
        length=0.;end=-math.inf
        for lo,hi in ys:
            if hi<=end:continue
            length+=hi-max(lo,end);end=hi
        area+=(b-a)*length
    return area


def assess(j,corridor,civil_policy):
    t=corridor['terrain'];c=corridor['civil'];site=corridor['corridor']['site'];forbidden=corridor['corridor']['forbidden']
    p=deepcopy(civil_policy)
    required={'single_track_half_formation_m','construction_margin_m','structure_half_reservation_m','grid_step_m','specialwork_on_structures'}
    if not isinstance(p,dict) or set(p)!=required:raise ValueError('terrain civil policy schema')
    for key in required-{'specialwork_on_structures'}:
        number(p[key],key,minimum=.01,maximum=100 if key=='grid_step_m' else 30)
    if p['specialwork_on_structures']!='unsupported_in_this_study':raise ValueError('unsupported structure/component policy')
    rows=[];fail=[];potential=[];structures=[];totals={k:0. for k in KINDS}
    # Every original external interface is open. Backward/forward vehicle support
    # is not inferred; land reservations at x=0 and x=L remain inside the site's
    # explicitly supplied 5m end strips where the chosen pads permit it.
    for eid,e in sorted(j.network.edges.items()):
        x0,x1=e.curve.at(0)[0],e.curve.at(1)[0]
        n=max(1,math.ceil((x1-x0)/p['grid_step_m']))
        cuts={x0+(x1-x0)*i/n for i in range(n+1)}
        cuts.update(k.x for k in j.height[eid].knots)
        cuts.update(x for x in (t['river_x0_m'],t['river_x1_m'],t['ridge_x_m']-t['ridge_half_x_m'],t['ridge_x_m'],t['ridge_x_m']+t['ridge_half_x_m']) if x0<x<x1)
        cuts=sorted(cuts)
        for a,b in zip(cuts,cuts[1:]):
            curve=restrict(e.curve,a,b);ys=[v[1] for v in curve.controls]
            ylo,yhi=min(ys),max(ys);mid=(a+b)/2;point=j.point(eid,mid)
            wet=t['river_x0_m']<mid<t['river_x1_m']
            za,zb=j.z(eid,a),j.z(eid,b);zlo,zhi=min(za,zb),max(za,zb)
            gl,gh=ground_range(t,[a,ylo,b,yhi],wet)
            diff=point[2]-c['rail_to_formation_m']-ground(t,mid,point[1])
            if wet:kind='river_bridge'
            elif diff>c['max_embankment_m']:kind='viaduct'
            elif -diff>c['max_open_cut_m']:kind='tunnel'
            elif diff>.5:kind='embankment'
            elif diff<-.5:kind='cutting'
            else:kind='surface'
            # The whole interval reserves enough room for the possible open
            # earthwork or the possible structure: midpoint classification does
            # not decide containment. Ground ranges below use the unpadded track
            # box, so full transverse slope/geotechnical earthwork remains unassessed.
            max_height=max(abs(zlo-c['rail_to_formation_m']-gh),abs(zhi-c['rail_to_formation_m']-gl))
            open_depth=min(max_height,max(c['max_open_cut_m'],c['max_embankment_m']))
            pad=max(p['single_track_half_formation_m']+p['construction_margin_m']+c['side_slope_hv']*open_depth,
                    p['structure_half_reservation_m'])
            box=[a-pad,ylo-pad,b+pad,yhi+pad]
            # End-interface ribbons stop longitudinally at the authorised open
            # boundary; only lateral pads and internal-earthwork envelopes count.
            # No support is invented beyond those interfaces.
            box[0]=max(0.,box[0]);box[2]=min(j.spec.span_m,box[2])
            length=(b-a)*j.metric(eid,mid)
            totals[kind]+=length
            errors=[]
            if not within(box,site):errors.append('reservation_outside_site')
            for i,no_build in enumerate(forbidden):
                if overlaps(box,no_build):
                    witness=no_build[0]<=mid<=no_build[2] and no_build[1]<=point[1]<=no_build[3]
                    errors.append(('track_enters_protected_land:' if witness else 'reservation_intersects_protected_land:')+str(i))
            water_margin=None
            if wet:
                water_margin=zlo-c['deck_depth_m']-t['water_level_m']-c['water_freeboard_m']
                if water_margin<0:errors.append('river_deck_clearance_failed')
            if e.component:
                # An actual turnout span over water, a high structure, or deep
                # cover requires a component/structure integration not admitted
                # by this fixture. This is a project support gate, not a UK ban.
                if wet or zhi-c['rail_to_formation_m']-gl>c['max_embankment_m'] or gh-(zlo-c['rail_to_formation_m'])>c['max_open_cut_m']:
                    errors.append('specialwork_structure_interface_unsupported')
            row=dict(edge_id=eid,component=e.component,x_interval_m=[a,b],kind=kind,
                midpoint_xyz_m=list(point),ground_height_bounds_m=[gl,gh],rail_height_bounds_m=[zlo,zhi],
                formation_difference_at_midpoint_m=diff,length_estimate_m=length,
                reservation_box_m=box,project_pad_m=pad,river_clearance_margin_m=water_margin,reasons=errors)
            rows.append(row)
            fail.extend(dict(edge_id=eid,x_interval_m=[a,b],reason=reason,midpoint_xyz_m=list(point)) for reason in errors)
    # Explicit crossing reservation in addition to terrain-based classifications.
    cross=j.assessment['crossing'];cx=cross['x_m']
    band=cross['footprint_x_m'];y=cross['y_m'];w=p['structure_half_reservation_m']
    if j.mode!='flat':
        structures.append(dict(kind=j.mode+'_crossing_reservation',edge_ids=cross['edge_ids'],
            box_m=[band[0]-w,y-w,band[1]+w,y+w],crossing_candidate_hash=j.assessment['candidate_hash'],
            rail_separation_m=cross['minimum_rail_separation_m'],
            design_status='reservation_only_no_actual_deck_portals_piers_or_drainage'))
    runs=[]
    for r in rows:
        if runs and runs[-1]['edge_id']==r['edge_id'] and runs[-1]['kind']==r['kind'] and abs(runs[-1]['x_interval_m'][1]-r['x_interval_m'][0])<1e-8:
            runs[-1]['x_interval_m'][1]=r['x_interval_m'][1];runs[-1]['track_length_estimate_m']+=r['length_estimate_m']
        else:runs.append(dict(edge_id=r['edge_id'],kind=r['kind'],x_interval_m=list(r['x_interval_m']),track_length_estimate_m=r['length_estimate_m']))
    structures.extend(dict(kind=r['kind']+'_planning_run',edge_id=r['edge_id'],x_interval_m=r['x_interval_m'],
        track_length_estimate_m=r['track_length_estimate_m'],design_status='asset_selection_and_portal_transition_unassessed')
        for r in runs if r['kind'] in ('river_bridge','viaduct','tunnel'))
    out=dict(version='0.11.0',geometry_hash=j.assessment['candidate_hash'],terrain_hash=digest(t),
        terrain_revision=t['revision'],terrain_source='same authored v0.9 river/ridge field',
        corridor_constraints_hash=digest(corridor['corridor']),civil_profile_hash=digest(dict(civil=c,policy=p)),
        status='project_terrain_screen_pass' if not fail else 'terrain_or_land_constraint_failed',
        hard_failures=fail,terrain_rows=rows,civil_runs=runs,structure_reservations=structures,
        unique_physical_edges_assessed=len(j.network.edges),track_length_by_kind_m=totals,
        plan_reservation_union_area_m2=rectangle_union_area([r['reservation_box_m'] for r in rows]),
        counted_by='unique physical edges, never service routes',
        length_units='track metres, not structure asset counts or corridor formation metres',
        quantities_method='midpoint length and classification; exact union of authored conservative boxes',
        site=deepcopy(site),protected_land=deepcopy(forbidden),policy=p,
        earthwork_volume_m3=None,land_or_terrain_edited=False,
        unassessed=['transverse terrain/slope stability and full earthwork toes','structure asset dimensions, supports and portal transitions',
            'groundwater/drainage and cover adequacy','hydraulics and water crossings','3D vehicle/gauge clearance',
            'terrain between actual game samples; current terrain is analytic synthetic data'],
        game_constructed=False,construction_authorised=False)
    out['assessment_hash']=digest(out);return out
