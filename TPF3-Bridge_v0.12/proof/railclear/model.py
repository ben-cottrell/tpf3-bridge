"""Explicit planar geometry with fixed *chord* separation of bogie pivots.

Bogie pivots follow the supplied track centreline. Actual axle geometry, bogie
rotation limits, suspension, roll and lower-sector equipment are not modelled.
Polyline poses are exact for the polyline (within floating arithmetic), not for
its Bezier parent. Unsampled motion is not automatically certified clear.
"""
from __future__ import annotations
from bisect import bisect_right
from dataclasses import dataclass, asdict
import hashlib
import json
import math
from railgeom.curves import (Bezier, Point, finite as _validate_finite, distance, sub, add, mul, dot,
                             norm, segment_distance, flatten)

TOL = 1e-8  # arithmetic tolerance, NOT an engineering clearance allowance


def finite(x, name):
    _validate_finite(x, name)
    return float(x)


def positive(x, name, zero=False):
    x=finite(x,name)
    if x < 0 or (not zero and x == 0): raise ValueError(name+' outside positive domain')
    return float(x)


def count(x, name, maximum):
    if isinstance(x,bool) or not isinstance(x,int) or not 1<=x<=maximum:
        raise ValueError(name+' outside integer work budget')
    return x


def digest(value)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Body:
    length_m: float
    width_m: float
    bogie_centres_m: float
    lateral_allowance_m: float = 0.0
    fidelity: str = 'synthetic'
    profile_id: str = 'synthetic_body'
    def __post_init__(self):
        for name in ('length_m','width_m','bogie_centres_m'):
            positive(getattr(self,name),name)
        positive(self.lateral_allowance_m,'lateral allowance',True)
        if not self.bogie_centres_m < self.length_m: raise ValueError('Bogie pivots must lie inside this symmetric body')
        if max(self.length_m,self.width_m,self.bogie_centres_m,self.lateral_allowance_m)>100:
            raise ValueError('Single-body research model dimensions exceeded; not a rigid whole train')
        if self.fidelity not in ('synthetic','reference_informed_assumptions'):
            raise ValueError('No verified dynamic gauge profile supported by this model')
        if not isinstance(self.profile_id,str) or not self.profile_id: raise ValueError('Missing profile identity')
    @property
    def half_width_m(self): return self.width_m/2+self.lateral_allowance_m
    def digest(self): return digest(asdict(self))


@dataclass(frozen=True)
class Pose:
    front_bogie_s_m: float
    rear_bogie_s_m: float
    front_bogie: Point
    rear_bogie: Point
    centre: Point
    corners: tuple[Point,...]


def pose_from_pivots(front:Point,rear:Point,body:Body,front_s:float,rear_s:float)->Pose:
    chord=distance(front,rear)
    if abs(chord-body.bogie_centres_m)>1e-6: raise ValueError('Fixed bogie chord constraint failed')
    axis=mul(sub(front,rear),1/chord); normal=(-axis[1],axis[0]); centre=mul(add(front,rear),.5)
    h=body.length_m/2; w=body.half_width_m
    corners=tuple(add(centre,add(mul(axis,x),mul(normal,y))) for x,y in ((-h,-w),(h,-w),(h,w),(-h,w)))
    return Pose(front_s,rear_s,front,rear,centre,corners)


@dataclass(frozen=True)
class Polyline:
    points: tuple[Point,...]
    # Provenance applies to this approximation only.
    origin: str = 'authored_polyline'
    parent_hash: str = ''
    maximum_curve_hull_error_m: float = 0.0
    def __post_init__(self):
        if not isinstance(self.points,tuple) or not 2<=len(self.points)<=20000:
            raise ValueError('Polyline requires 2..20000 immutable points')
        for p in self.points:
            if not isinstance(p,tuple) or len(p)!=2: raise ValueError('Only explicit 2D points supported')
            for v in p:
                if abs(finite(v,'coordinate'))>1e7: raise ValueError('Coordinate out of local-model range')
        positive(self.maximum_curve_hull_error_m,'curve error',True)
        total=0.; ss=[0.]; units=[]
        for a,b in zip(self.points,self.points[1:]):
            length=distance(a,b)
            if length<=TOL: raise ValueError('Zero/degenerate polyline segment')
            total+=length; ss.append(total); units.append(mul(sub(b,a),1/length))
        chord=sub(self.points[-1],self.points[0]); n=norm(chord)
        if n<=TOL: raise ValueError('Closed/non-progressive path unsupported')
        axis=mul(chord,1/n)
        # All headings lie in +/-40 degrees of a common axis. Pairwise heading
        # differences <80 degrees make distance to the fixed leading pivot
        # strictly monotone while stepping backward; the rear root is unique.
        if min(dot(axis,u) for u in units)<math.cos(math.radians(40)):
            raise ValueError('Path outside monotone heading cone; split into supported local windows')
        object.__setattr__(self,'chainages',tuple(ss));object.__setattr__(self,'length_m',total)
    def at(self,s:float)->Point:
        s=finite(s,'path position')
        if not 0<=s<=self.length_m: raise ValueError('Path continuation missing; extrapolation forbidden')
        i=min(bisect_right(self.chainages,s)-1,len(self.points)-2)
        t=(s-self.chainages[i])/(self.chainages[i+1]-self.chainages[i])
        return add(self.points[i],mul(sub(self.points[i+1],self.points[i]),t))
    def pose(self,front_s:float,body:Body,max_segments:int=20000)->Pose:
        count(max_segments,'root segment budget',20000)
        front=self.at(front_s); i=min(bisect_right(self.chainages,front_s)-1,len(self.points)-2)
        work=0; B=body.bogie_centres_m
        for j in range(i,-1,-1):
            work+=1
            if work>max_segments: raise RuntimeError('rear_pivot_search_exhausted')
            a=self.points[j]; b=front if j==i else self.points[j+1]
            v=sub(b,a); length=norm(v)
            if length<=TOL: continue
            # Search exact segment-circle intersection. The monotone cone
            # guarantees at most one crossing on the backward path.
            if distance(a,front) < B-TOL: continue
            unit=mul(v,1/length); rel=sub(a,front)
            proj=dot(rel,unit); disc=proj*proj-(dot(rel,rel)-B*B)
            if disc < -TOL: continue
            roots=(-proj-math.sqrt(max(0.,disc)),-proj+math.sqrt(max(0.,disc)))
            legal=[r for r in roots if -TOL<=r<=length+TOL]
            if not legal: continue
            r=max(0.,min(length,max(legal)))
            if r<TOL:r=0.
            elif length-r<TOL:r=length
            rear=add(a,mul(unit,r)); rear_s=self.chainages[j]+r
            return pose_from_pivots(front,rear,body,front_s,rear_s)
        raise ValueError('Insufficient known rear-bogie continuation')
    def digest(self): return digest(asdict(self))


def from_curves(curves:tuple[Bezier,...],parent_hash:str='',flatness_m:float=.002,
                length_gap_m:float=.001)->Polyline:
    if not curves: raise ValueError('Empty route')
    points=[]; error=0.
    for c in curves:
        leaves=flatten(c,flatness_m=flatness_m,length_gap_m=length_gap_m)
        if points and distance(points[-1],leaves[0].a)>1e-6: raise ValueError('Disconnected geometry')
        if not points: points.append(leaves[0].a)
        points.extend(x.b for x in leaves)
        error=max(error,max(x.hull_radius_m for x in leaves))
    return Polyline(tuple(points),'Bezier chord subdivision; not a certified body envelope',parent_hash,error)


def circular_pose(radius_m:float,angle_rad:float,body:Body)->Pose:
    R=positive(radius_m,'radius'); angle=finite(angle_rad,'angle')
    if R>1e7: raise ValueError('Circle outside supported local numerical range')
    if body.bogie_centres_m>=2*R: raise ValueError('No supported bogie chord on circle')
    half=math.asin(body.bogie_centres_m/(2*R))
    rear=(R*math.cos(angle-half),R*math.sin(angle-half))
    front=(R*math.cos(angle+half),R*math.sin(angle+half))
    return pose_from_pivots(front,rear,body,R*(angle+half),R*(angle-half))


def circular_band(radius_m:float,body:Body)->dict:
    """Exact radial range of the symmetric rectangular body over a full circle.

    Bounds describe all possible relative phases on concentric tracks. They are
    not a simultaneous train-motion result or a dynamic swept-gauge standard.
    """
    R=positive(radius_m,'radius'); B=body.bogie_centres_m
    if R>1e7: raise ValueError('Circle outside supported local numerical range')
    if B>=2*R: raise ValueError('Bogie chord exceeds circle diameter')
    rho=math.sqrt(R*R-B*B/4); w=body.half_width_m
    if rho<=w: raise ValueError('Body contains circle centre; outside research scope')
    # stable small-difference expression rather than subtracting close radii
    centre_throw=(B*B/4)/(R+rho)
    outer=math.hypot(rho+w,body.length_m/2)
    return {'radius_m':R,'inner_radius_m':rho-w,'outer_radius_m':outer,
            'centre_inthrow_m':centre_throw,'outer_excursion_m':outer-R,
            'bogie_arc_separation_m':2*R*math.asin(B/(2*R)),
            'origin':'analytic rigid rectangular body; fixed bogie chord; zero roll',
            'profile_hash':body.digest(),'full_UK_gauging':'unassessed'}


def parallel_gap(spacing_m:float,left:Body,right:Body)->dict:
    s=positive(spacing_m,'spacing')
    gap=s-left.half_width_m-right.half_width_m
    return {'gap_m':gap,'status':'geometric_gap' if gap>0 else 'geometric_contact_or_overlap',
            'scope':'infinite straight paths; symmetric rigid plan rectangles including declared allowances',
            'profile_hashes':[left.digest(),right.digest()],'full_UK_gauging':'unassessed',
            'may_remove_existing_resource':False}


def concentric_gap(inner_radius_m:float,spacing_m:float,inner:Body,outer:Body)->dict:
    spacing_m=positive(spacing_m,'spacing')
    a=circular_band(inner_radius_m,inner);b=circular_band(inner_radius_m+spacing_m,outer)
    gap=b['inner_radius_m']-a['outer_radius_m']
    return {'gap_m':gap,'status':'geometric_gap' if gap>0 else 'geometric_contact_or_overlap',
            'inner':a,'outer':b,'scope':'full concentric circular sweeps; arbitrary relative phase',
            'full_UK_gauging':'unassessed','may_remove_existing_resource':False}


def bounds(poly:tuple[Point,...]):
    return min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)


def bounds_gap(a,b):
    return math.hypot(max(0.,a[0]-b[2],b[0]-a[2]),max(0.,a[1]-b[3],b[1]-a[3]))


def polygon_gap(a:tuple[Point,...],b:tuple[Point,...])->float:
    """Nonnegative separation of convex polygons (zero includes containment).

    Internal polygons are rectangles; caller-supplied arbitrary polygons must
    use validate_polygon() first. Uses SAT and closed-segment distances.
    """
    separated=False
    for poly in (a,b):
        for p,q in zip(poly,poly[1:]+poly[:1]):
            v=sub(q,p);axis=(-v[1],v[0]);aa=[dot(x,axis) for x in a];bb=[dot(x,axis) for x in b]
            if max(aa)<min(bb) or max(bb)<min(aa): separated=True
    if not separated: return 0.
    return min(segment_distance(p,q,r,s) for p,q in zip(a,a[1:]+a[:1]) for r,s in zip(b,b[1:]+b[:1]))


def validate_polygon(points)->tuple[Point,...]:
    if not isinstance(points,(list,tuple)) or not 3<=len(points)<=64: raise ValueError('Expected bounded convex obstacle polygon')
    poly=[]
    for p in points:
        if not isinstance(p,(list,tuple)) or len(p)!=2: raise ValueError('Obstacle must be planar')
        q=tuple(finite(x,'obstacle coordinate') for x in p)
        if any(abs(x)>1e7 for x in q):raise ValueError('Obstacle outside local coordinate range')
        poly.append(q)
    from railgeom.curves import cross
    signs=[]
    for a,b,c in zip(poly,poly[1:]+poly[:1],poly[2:]+poly[:2]):
        if distance(a,b)<=TOL: raise ValueError('Duplicate obstacle corner')
        z=cross(sub(b,a),sub(c,b))
        if abs(z)<=TOL: raise ValueError('Degenerate obstacle corner')
        signs.append(z>0)
    if len(set(signs))!=1: raise ValueError('Obstacle polygon must be strictly convex and ordered')
    # Reject winding stars despite consistent local cross signs.
    for i in range(len(poly)):
        for j in range(i+1,len(poly)):
            if j==i+1 or (i==0 and j==len(poly)-1): continue
            if segment_distance(poly[i],poly[(i+1)%len(poly)],poly[j],poly[(j+1)%len(poly)])<=TOL:
                raise ValueError('Self-intersecting obstacle')
    return tuple(poly)
