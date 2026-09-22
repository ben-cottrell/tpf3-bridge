"""Straight, level paired-platform surfaces and bounded furniture placement.

A scoped design-screen, not a passenger-safety certificate. Rail geometry is
read-only. No source-derived scalar can erase a rail or control restriction.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import copy
import math
from .datums import RailSection
from .reference import number,reference,width_requirement,height_check,offset_check
from railclear.model import digest

PAIRS=(('IA12','A1','A2'),('IA34','A3','A4'),('IB12','B1','B2'),('IB34','B3','B4'))


@dataclass(frozen=True)
class PlatformProfile:
    gauge_mm: float=1435.
    nearest_rail_offset_mm: float=737.5
    height_mm: float=915.
    resolved_minimum_offset_mm: float=730.
    applicability_confirmed: bool=True
    offset_case: str='explicit_standard_case_reference'

    def __post_init__(self):
        for name,value in asdict(self).items():
            if name.endswith('_mm'):number(value,name,positive=True)
        if type(self.applicability_confirmed) is not bool:raise ValueError('explicit_applicability_required')
        if self.offset_case not in ('explicit_standard_case_reference','unresolved'):
            raise ValueError('unsupported_generated_offset_case')
        if abs(self.gauge_mm-reference()['nominal_gauge_mm'])>1e-8:
            raise ValueError('station_adapter_requires_declared_standard_gauge')


def _bounds(curve):
    return (min(p[0] for p in curve.controls),max(p[0] for p in curve.controls),
            min(p[1] for p in curve.controls),max(p[1] for p in curve.controls))


def rectangles_overlap(a,b):
    # Contact counts as a possible interference in this conservative hull screen.
    return a[0]<=b[1] and b[0]<=a[1] and a[2]<=b[3] and b[2]<=a[3]


def make_platforms(station,compiled, *, profile=PlatformProfile(),permissible_speeds_mph=None):
    """Create four islands from the actual compiled markers and boarding data.

    Width uses track centres minus BOTH half gauges and BOTH rail-edge offsets.
    An unspecified permissible speed leaves width checks unassessed; the motion
    solver's target speed is deliberately not used to fill that field.
    """
    if compiled.source_hash!=station.assembly.network.digest():raise ValueError('stale_compiled_network')
    n=station.assembly.network; pmap=station.assembly.platforms
    if n.metadata.get('vertical_profile')!='level' or n.metadata.get('cant_mm')!=0:
        raise ValueError('straight_level_platform_adapter_only')
    expected={x for _,a,b in PAIRS for x in (a,b)}
    if set(pmap)!=expected:raise ValueError('requires_exact_eight_road_inventory')
    speeds={pid:None for pid in expected} if permissible_speeds_mph is None else dict(permissible_speeds_mph)
    if set(speeds)!=expected:raise ValueError('permissible_speed_inventory_mismatch')
    rows=[];faces={};source_before=n.digest()
    for island_id,a,b in PAIRS:
        pa,pb=pmap[a],pmap[b]
        xa=pa['boarding_interval_x_m'];xb=pb['boarding_interval_x_m']
        if xa!=xb:raise ValueError('nonmatching_island_boarding_extents')
        ay=n.ports[pa['marker_port']].position[1];by=n.ports[pb['marker_port']].position[1]
        if not ay<by:raise ValueError('reversed_pair_ordinates')
        for pid,p,y in ((a,pa,ay),(b,pb,by)):
            if p!=compiled.platforms[pid]:raise ValueError('platform_snapshot_mismatch')
            storage=n.edges[p['storage_edge']]
            if any(abs(q[1]-y)>1e-8 for q in storage.curve.controls):raise ValueError('curved_storage_not_supported')
            if abs((xa[1]-xa[0])-p['usable_length_m'])>1e-8:raise ValueError('boarding_length_mismatch')
            marker=n.ports[p['marker_port']].position[0]
            if not xa[0]<=marker<=xa[1]:raise ValueError('marker_outside_boarding_extent')
            end=max(q[0] for q in storage.curve.controls)
            if end<xa[1]:raise ValueError('track_ends_before_boarding_extent')
            # Boarding begins upstream of the rear marker. Check the actual
            # incoming line, not just a fictitious extension of the storage.
            in_route=station.assembly.routes[f'{p["bank"]}:{pid}:in']
            lead=n.edges[in_route.steps[-1].edge_id]
            if lead is None:
                incident=[e for e in n.edges.values() if p['marker_port'] in (e.u,e.v) and e.id!=p['storage_edge']]
                if len(incident)!=1:raise ValueError('ambiguous_boarding_lead')
                lead=incident[0]
            if any(abs(q[1]-y)>1e-8 for q in lead.curve.controls) or min(q[0] for q in lead.curve.controls)>xa[0]:
                raise ValueError('unsupported_boarding_lead_geometry')
        low,z1=RailSection(profile.gauge_mm,ay).edge(nearest_rail_offset_mm=profile.nearest_rail_offset_mm,height_mm=profile.height_mm,side=1)
        high,z2=RailSection(profile.gauge_mm,by).edge(nearest_rail_offset_mm=profile.nearest_rail_offset_mm,height_mm=profile.height_mm,side=-1)
        if high<=low:raise ValueError('no_positive_island_width')
        rect=[xa[0],xa[1],low,high];width=high-low
        overlaps=[eid for eid,e in n.edges.items() if rectangles_overlap(rect,_bounds(e.curve))]
        wcheck=width_requirement([speeds[a],speeds[b]],applicable=profile.applicability_confirmed)
        if wcheck['status']=='reference_requirement_value':
            wcheck={**wcheck,'actual_width_m':width,'status':'reference_clause_pass' if width>=wcheck['minimum_width_m'] else 'reference_clause_fail'}
        hcheck=height_check(profile.height_mm,applicable=profile.applicability_confirmed)
        ocheck=offset_check(profile.nearest_rail_offset_mm,applicable=profile.applicability_confirmed,
                 resolved_minimum_mm=profile.resolved_minimum_offset_mm,minimum_origin=profile.offset_case)
        for pid,y,side,face_y,z in ((a,ay,1,low,z1),(b,by,-1,high,z2)):
            faces[pid]={'platform_id':pid,'island_id':island_id,'side':side,'track_y_m':y,
                'edge_start_xyz_m':[xa[0],face_y,z],'edge_end_xyz_m':[xa[1],face_y,z],
                'boarding_length_m':xa[1]-xa[0],'permissible_or_enhanced_speed_mph':speeds[pid],
                'nearest_rail_offset_mm':profile.nearest_rail_offset_mm,'height_mm':profile.height_mm,
                'height_check':copy.deepcopy(hcheck),'offset_check':copy.deepcopy(ocheck)}
        rows.append({'id':island_id,'platform_ids':[a,b],'boarding_x_m':list(xa),'track_y_m':[ay,by],
             'surface_bounds_xy_m':rect,'elevation_m':z1,'width_m':width,'width_check':wcheck,
             'centreline_hull_check':{'status':'disjoint_hulls' if not overlaps else 'potential_interference_unassessed',
                                      'possible_edge_ids':overlaps},
             'surface_scope':'boarding_slab_reservation_only_no_foundation_or_full_access',
             'full_platform_interface':'unassessed'})
    if n.digest()!=source_before:raise AssertionError('platform_assessment_mutated_railway')
    output={'schema_version':'0.8.0','family':station.family,'compile_hash':compiled.compile_hash,
       'source_geometry_hash':source_before,'profile':asdict(profile),'profile_hash':digest(asdict(profile)),
       'reference_hash':digest(reference()),'faces':faces,'islands':rows,
       'current_uk_compliance':'unassessed','full_platform_interface':'unassessed',
       'construction_authorised':False,'rail_geometry_mutated':False,
       'unassessed':['current_full_standard_comparison','lower_sector_and_vehicle_step','dynamic_gauging',
                     'demand_sizing','accessible_connection_to_concourse','tactile_and_edge_treatment',
                     'platform_ends_buffer_and_overrun','foundation_drainage_structures']}
    output['assessment_hash']=digest(output)
    return output


def verify_assessment(assessment,compiled):
    a=copy.deepcopy(assessment);stored=a.pop('assessment_hash',None)
    if stored!=digest(a) or a.get('compile_hash')!=compiled.compile_hash or a.get('source_geometry_hash')!=compiled.source_hash or a.get('reference_hash')!=digest(reference()):
        raise ValueError('stale_or_modified_platform_assessment')
    if a.get('construction_authorised') is not False:raise ValueError('unauthorised_platform_claim')
    return True


@dataclass(frozen=True)
class Facility:
    width_m: float
    length_m: float
    centre_x_m: float
    centre_y_m: float
    def __post_init__(self):
        number(self.width_m,'width',positive=True);number(self.length_m,'length',positive=True)
        number(self.centre_x_m,'centre_x');number(self.centre_y_m,'centre_y')
    @property
    def bounds(self):
        return [self.centre_x_m-self.length_m/2,self.centre_x_m+self.length_m/2,
                self.centre_y_m-self.width_m/2,self.centre_y_m+self.width_m/2]


def facility_check(island,facility:Facility):
    """General obstacle rule, not a narrow-column or extension exception."""
    rect=island['surface_bounds_xy_m'];b=facility.bounds;w=island['width_check']
    contained=rect[0]<=b[0] and b[1]<=rect[1] and rect[2]<=b[2] and b[3]<=rect[3]
    gaps=[b[2]-rect[2],rect[3]-b[3]];req=w.get('edge_obstacle_clearances_m')
    if req is None:status='unassessed';failed=[]
    else:
        failed=[pid for pid,g,r in zip(island['platform_ids'],gaps,req) if g+1e-12<r]
        if not contained:failed=list(island['platform_ids'])
        status='reference_clause_pass' if contained and not failed else 'reference_clause_fail'
    return {'status':status,'facility':asdict(facility),'island_id':island['id'],'island_geometry_hash':digest(island),
        'contained_on_boarding_slab':contained,'edge_gaps_m':gaps,'required_edge_gaps_m':req,
        'failed_platform_faces':failed,'scope':'general_obstacle_distance_only','floating_comparison_guard_m':1e-12,
        'minimum_demand_width':'unassessed','current_uk_compliance':'unassessed','construction_authorised':False}


def fit_facility(island,facility:Facility, *, allowed_centre_y_m, budget=1):
    """An exact one-dimensional fit within caller-authorised lateral bounds.

    It never narrows the facility or moves track. Empty feasible interval is a
    certificate only for this fixed rectangle/cross-section constraint model.
    """
    if type(budget) is not int or budget<0:raise ValueError('invalid_fit_budget')
    if not isinstance(allowed_centre_y_m,(list,tuple)) or len(allowed_centre_y_m)!=2:raise ValueError('invalid_authority_interval')
    amin=number(allowed_centre_y_m[0],'min_centre');amax=number(allowed_centre_y_m[1],'max_centre')
    if amin>amax:raise ValueError('reversed_authority_interval')
    base={'island_id':island['id'],'island_geometry_hash':digest(island),'original_facility':asdict(facility),
          'authorised_centre_y_m':[amin,amax],'construction_authorised':False,'evaluations':0,
          'track_moved':False,'facility_resized':False}
    if budget==0:return {**base,'status':'search_exhausted','selected':None}
    req=island['width_check'].get('edge_obstacle_clearances_m')
    if req is None:return {**base,'status':'unassessed','selected':None}
    x0,x1,y0,y1=island['surface_bounds_xy_m'];f=facility.bounds
    low=y0+req[0]+facility.width_m/2;high=y1-req[1]-facility.width_m/2
    needed=facility.width_m+sum(req)
    details={'required_island_width_m':needed,'actual_island_width_m':y1-y0,
             'extra_width_needed_m':max(0,needed-(y1-y0)), 'physical_centre_interval_m':[low,high]}
    if low>high+1e-12 or f[0]<x0 or f[1]>x1:
        return {**base,**details,'status':'infeasible_fixed_section','certificate_scope':'fixed_facing_edges_fixed_facility_size_and_x',
                'selected':None,'evaluations':1}
    lo=max(low,amin);hi=min(high,amax)
    if lo>hi+1e-12:return {**base,**details,'status':'outside_authorised_moves','selected':None,'evaluations':1}
    selected=Facility(facility.width_m,facility.length_m,facility.centre_x_m,min(max(facility.centre_y_m,lo),hi))
    check=facility_check(island,selected)
    if check['status']!='reference_clause_pass':raise AssertionError('analytic_fit_failed_checker')
    return {**base,**details,'status':'fitted_within_reference_model','selected':asdict(selected),'check':check,
            'lateral_move_m':selected.centre_y_m-facility.centre_y_m,'evaluations':1}
