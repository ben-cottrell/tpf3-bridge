"""Bounded sweeps: exact poses on a polyline plus a conservative pose-step bound.

The bound covers unsampled positions ON THAT POLYLINE. It does not certify
Bezier-to-vehicle error, dynamics, cant, structures in 3D or full UK gauging.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from .model import (Body, Pose, Polyline, positive, count, finite, bounds, bounds_gap,
                    polygon_gap, validate_polygon, digest)
from railgeom.curves import sub, norm, dot, mul


@dataclass(frozen=True)
class Sweep:
    body: Body
    path: Polyline
    start_front_s_m: float
    end_front_s_m: float
    poses: tuple[Pose,...]
    actual_maximum_step_m: float
    between_pose_padding_m: float
    heading_span_rad: float
    def export(self,include_poses=True):
        result={'schema_version':'0.5.0','body':asdict(self.body),'body_hash':self.body.digest(),
                'path_hash':self.path.digest(),'parent_geometry_hash':self.path.parent_hash,
                'path_origin':self.path.origin,'parent_curve_hull_error_m':self.path.maximum_curve_hull_error_m,
                'front_bogie_interval_m':[self.start_front_s_m,self.end_front_s_m],
                'path_length_m':self.path.length_m,'pose_count':len(self.poses),
                'actual_maximum_step_m':self.actual_maximum_step_m,
                'between_pose_padding_m':self.between_pose_padding_m,'heading_span_rad':self.heading_span_rad,
                'bound_scope':'continuous rigid-body sweep of supplied polyline over reported interval',
                'parent_curve_body_error_bound':'unassessed',
                'dynamic_3D_gauging':'unassessed','whole_formation':'not_modelled'}
        if include_poses:result['poses']=[asdict(p) for p in self.poses]
        return result


def sweep(path:Polyline,body:Body,start_front_s_m:float,end_front_s_m:float,
          maximum_step_m:float=1.,max_poses:int=10000)->Sweep:
    step=positive(maximum_step_m,'step');count(max_poses,'pose budget',100000)
    start=finite(start_front_s_m,'start');end=finite(end_front_s_m,'end')
    if not 0<=start<end<=path.length_m: raise ValueError('Sweep interval outside known path')
    n=max(1,math.ceil((end-start)/step))
    if n+1>max_poses: raise RuntimeError('pose_budget_exhausted')
    axis=sub(path.points[-1],path.points[0]);axis=mul(axis,1/norm(axis));angles=[]
    for a,b in zip(path.points,path.points[1:]):
        u=sub(b,a);u=mul(u,1/norm(u))
        angles.append(math.atan2(axis[0]*u[1]-axis[1]*u[0],dot(axis,u)))
    span=max(angles)-min(angles); c=math.cos(span)
    if c<=0:raise ValueError('Cannot bound rear pivot motion on this path')
    K=math.hypot(body.length_m/2,body.half_width_m)
    # |rear'| <= 1/cos(span); centre' <= (1+1/c)/2;
    # |heading'| <= sin(span)*(1+1/c)/B. These a.e. bounds
    # also integrate across piecewise-linear tangent changes.
    speed_bound=(1+1/c)*(.5+K*math.sin(span)/body.bogie_centres_m)
    actual=(end-start)/n
    padding=speed_bound*actual/2 + 1e-8
    poses=tuple(path.pose(start+(end-start)*i/n,body) for i in range(n+1))
    return Sweep(body,path,start,end,poses,actual,padding,span)


def pair_screen(a:Sweep,b:Sweep,max_pairs:int=5000000)->dict:
    count(max_pairs,'pair budget',100000000)
    work=0; exact=0;best=math.inf;witness=None
    ba=[bounds(p.corners) for p in a.poses];bb=[bounds(p.corners) for p in b.poses]
    for i,p in enumerate(a.poses):
        for j,q in enumerate(b.poses):
            work+=1
            if work>max_pairs:
                return {'status':'search_exhausted','pairs_inspected':work-1,'sample_witness':witness,
                        'full_UK_gauging':'unassessed','may_remove_existing_resource':False}
            if bounds_gap(ba[i],bb[j])>=best:continue
            d=polygon_gap(p.corners,q.corners);exact+=1
            if d<best:
                best=d;witness={'a_pose':i,'b_pose':j,'a_front_s_m':p.front_bogie_s_m,
                               'b_front_s_m':q.front_bogie_s_m,'sample_gap_m':d}
            if d==0:break
        if best==0:break
    lower=best-a.between_pose_padding_m-b.between_pose_padding_m
    status='sampled_body_contact' if best==0 else ('clear_within_polyline_static_model' if lower>0 else 'unresolved_between_poses')
    return {'status':status,'minimum_sample_gap_m':best,'continuous_gap_lower_bound_m':lower,
            'pairs_inspected':work,'exact_polygon_checks':exact,'sample_witness':witness,
            'a_sweep':a.export(False),'b_sweep':b.export(False),
            'relative_phase':'all pose pairs, not only matching chainages',
            'full_UK_gauging':'unassessed','may_remove_existing_resource':False,
            'contact_is_not_train_collision_prediction':True}


def obstacle_screen(s:Sweep,polygon,max_checks:int=100000)->dict:
    poly=validate_polygon(polygon);count(max_checks,'obstacle budget',100000)
    if len(s.poses)>max_checks:return {'status':'search_exhausted','full_UK_gauging':'unassessed'}
    best=math.inf;idx=None
    for i,p in enumerate(s.poses):
        d=polygon_gap(p.corners,poly)
        if d<best:best=d;idx=i
    lower=best-s.between_pose_padding_m
    return {'status':'sampled_body_contact' if best==0 else ('clear_within_polyline_static_model' if lower>0 else 'unresolved_between_poses'),
            'minimum_sample_gap_m':best,'continuous_gap_lower_bound_m':lower,'pose_index':idx,
            'obstacle_polygon':poly,'sweep':s.export(False),'full_UK_gauging':'unassessed',
            'platform_interface':'not_assessed; no vertical profile or boarding gap evaluation',
            'may_remove_existing_resource':False}


def audit_pair_requests(sweeps:dict[str,Sweep],requests:list[tuple[str,str]],max_pairs=5000000):
    """Read-only overlay. Never removes legacy track/control/proximity resources."""
    result=[]
    for a,b in requests:
        if a==b or a not in sweeps or b not in sweeps:raise ValueError('Invalid distinct-route screen request')
        row=pair_screen(sweeps[a],sweeps[b],max_pairs)
        row.update({'route_a':a,'route_b':b});result.append(row)
    return {'schema_version':'0.5.0','results':result,'operation':'read_only_clearance_overlay',
            'resource_mutations':[],'full_UK_gauging':'unassessed'}
