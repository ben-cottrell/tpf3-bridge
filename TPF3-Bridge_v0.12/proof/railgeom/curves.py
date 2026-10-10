"""Planar Bezier kernel with subdivision bounds, not a UK turnout catalogue.

Lengths are bounded by chord and control-polygon lengths. Each flattened leaf
retains a convex-hull distance bound: proximity checks do not rely on samples
alone. Numerical guards are practical floating-point allowances, not interval
arithmetic certification. Coordinates are limited to a local engineering frame.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from railproof.model import positive

Point = tuple[float, float]
EPS = 1e-8


def finite(x: float, name: str) -> None:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f"{name} must be a finite number")


def add(a: Point, b: Point) -> Point: return a[0]+b[0], a[1]+b[1]
def sub(a: Point, b: Point) -> Point: return a[0]-b[0], a[1]-b[1]
def mul(a: Point, k: float) -> Point: return a[0]*k, a[1]*k
def dot(a: Point, b: Point) -> float: return a[0]*b[0]+a[1]*b[1]
def cross(a: Point, b: Point) -> float: return a[0]*b[1]-a[1]*b[0]
def norm(a: Point) -> float: return math.hypot(*a)
def distance(a: Point, b: Point) -> float: return norm(sub(a, b))


def point_segment(p: Point, a: Point, b: Point) -> float:
    v = sub(b, a); q = dot(v, v)
    if q == 0: return distance(p, a)
    t = max(0.0, min(1.0, dot(sub(p, a), v)/q))
    return distance(p, add(a, mul(v, t)))


def segment_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    """Distance of closed line segments, including crossing and collinearity."""
    v, w = sub(b, a), sub(d, c)
    den = cross(v, w)
    if den != 0:
        t = cross(sub(c, a), w)/den
        u = cross(sub(c, a), v)/den
        if 0 <= t <= 1 and 0 <= u <= 1: return 0.0
    return min(point_segment(a,c,d), point_segment(b,c,d),
               point_segment(c,a,b), point_segment(d,a,b))


def evaluate(points: tuple[Point, ...], t: float) -> Point:
    work = list(points)
    while len(work) > 1:
        work = [add(mul(a,1-t),mul(b,t)) for a,b in zip(work,work[1:])]
    return work[0]


@dataclass(frozen=True)
class Bezier:
    controls: tuple[Point, ...]

    def __post_init__(self):
        if not isinstance(self.controls, tuple) or not 2 <= len(self.controls) <= 6:
            raise ValueError("Bezier requires 2..6 immutable control points")
        for p in self.controls:
            if not isinstance(p, tuple) or len(p) != 2: raise ValueError("Expected 2D tuple")
            for x in p:
                finite(x, "coordinate")
                if abs(x) > 1e7: raise ValueError("Use a local coordinate frame (|coordinate| <= 1e7 m)")
        if distance(self.controls[0],self.controls[-1]) <= EPS:
            raise ValueError("Zero-chord or closed curves are outside this kernel's scope")
        if distance(self.controls[0],self.controls[1]) <= EPS or distance(self.controls[-2],self.controls[-1]) <= EPS:
            raise ValueError("Degenerate endpoint tangent")

    def at(self, t: float) -> Point:
        finite(t,"parameter")
        if not 0 <= t <= 1: raise ValueError("Parameter outside [0,1]")
        return evaluate(self.controls,t)

    def derivative_controls(self, order: int = 1) -> tuple[Point,...]:
        p=self.controls
        for _ in range(order):
            if len(p) == 1: return ((0.0,0.0),)
            p=tuple(mul(sub(b,a),len(p)-1) for a,b in zip(p,p[1:]))
        return p

    def tangent(self,t:float) -> Point:
        v=evaluate(self.derivative_controls(),t); n=norm(v)
        if n <= EPS: raise ValueError("Stationary parameter point")
        return mul(v,1/n)

    def curvature(self,t:float) -> float:
        a=evaluate(self.derivative_controls(),t)
        b=evaluate(self.derivative_controls(2),t)
        if norm(a)<=EPS: raise ValueError("Stationary parameter point")
        return cross(a,b)/norm(a)**3

    def split(self) -> tuple[Bezier,Bezier]:
        rows=[list(self.controls)]
        while len(rows[-1])>1:
            rows.append([mul(add(a,b),0.5) for a,b in zip(rows[-1],rows[-1][1:])])
        return Bezier(tuple(r[0] for r in rows)), Bezier(tuple(r[-1] for r in reversed(rows)))

    def reversed(self) -> Bezier: return Bezier(tuple(reversed(self.controls)))

    def transformed(self,dx:float=0,dy:float=0,angle:float=0,mirror:bool=False) -> Bezier:
        for x in (dx,dy,angle): finite(x,"transform")
        if not isinstance(mirror,bool): raise ValueError("mirror must be bool")
        c,s=math.cos(angle),math.sin(angle)
        p=[]
        for x,y in self.controls:
            if mirror: y=-y
            p.append((dx+c*x-s*y,dy+s*x+c*y))
        return Bezier(tuple(p))

    def bounds(self) -> tuple[float,float,float,float]:
        return min(x for x,y in self.controls),min(y for x,y in self.controls),max(x for x,y in self.controls),max(y for x,y in self.controls)

    def curvature_upper(self,depth:int=6) -> float:
        """Conservative derivative-convex-hull bound on absolute curvature.

        v_min is a positive projection of every derivative control point on the
        chord direction; v_max and a_max bound their norms. Subdivision tightens
        max(v_max*a_max/v_min**3). Unknown regularity raises rather than passes.
        """
        if isinstance(depth,bool) or not isinstance(depth,int) or not 0<=depth<=10:
            raise ValueError("curvature depth outside 0..10")
        def visit(c:Bezier,n:int)->float:
            d1=c.derivative_controls(); d2=c.derivative_controls(2)
            if len(c.controls)==2: return 0.0
            if n:
                a,b=c.split(); return max(visit(a,n-1),visit(b,n-1))
            axis=sub(c.controls[-1],c.controls[0]); axis=mul(axis,1/norm(axis))
            vmin=min(dot(v,axis) for v in d1)
            if vmin<=1e-12: raise ValueError("Curve regularity not certified by projection")
            upper=max(norm(v) for v in d1)*max(norm(v) for v in d2)/vmin**3
            return upper*(1+1e-9)+1e-12
        return visit(self,depth)


@dataclass(frozen=True)
class Leaf:
    t0:float
    t1:float
    a:Point
    b:Point
    hull_radius_m:float
    lower_length_m:float
    upper_length_m:float


def flatten(curve:Bezier,*,flatness_m:float=0.01,length_gap_m:float=0.0001,
            max_leaves:int=8192) -> tuple[Leaf,...]:
    positive(flatness_m,"flatness"); positive(length_gap_m,"length gap")
    if isinstance(max_leaves,bool) or not isinstance(max_leaves,int) or max_leaves<1:
        raise ValueError("Invalid subdivision budget")
    leaves=[]; stack=[(curve,0.0,1.0,length_gap_m)]
    while stack:
        c,t0,t1,gap=stack.pop()
        p=c.controls; chord=distance(p[0],p[-1]); upper=sum(distance(a,b) for a,b in zip(p,p[1:]))
        radius=max(point_segment(x,p[0],p[-1]) for x in p)
        if radius<=flatness_m and upper-chord<=gap:
            leaves.append(Leaf(t0,t1,p[0],p[-1],radius+EPS,max(0,chord-EPS),upper+EPS))
        else:
            if len(leaves)+len(stack)+2>max_leaves or t1-t0<2**-30:
                raise ValueError("subdivision_budget_exhausted")
            a,b=c.split(); mid=(t0+t1)*0.5
            stack.extend(((b,mid,t1,gap/2),(a,t0,mid,gap/2)))
    return tuple(leaves)


def continuous_proximity(a:tuple[Leaf,...],b:tuple[Leaf,...],threshold_m:float)->dict|None:
    """Conservative contact witness. A possible contact is NEVER a rail link.

    If chord distance - both hull radii exceeds the requested separation, all
    curve points in these leaves are separated. Otherwise conservatively retain
    a shared exclusion resource. May over-conflict; does not certify UK gauging.
    """
    positive(threshold_m,"separation",zero=True)
    best=None
    for x in a:
        for y in b:
            inflate=threshold_m+x.hull_radius_m+y.hull_radius_m
            if (max(x.a[0],x.b[0])+inflate<min(y.a[0],y.b[0]) or
                max(y.a[0],y.b[0])+inflate<min(x.a[0],x.b[0]) or
                max(x.a[1],x.b[1])+inflate<min(y.a[1],y.b[1]) or
                max(y.a[1],y.b[1])+inflate<min(x.a[1],x.b[1])): continue
            d=segment_distance(x.a,x.b,y.a,y.b)
            lower=max(0.0,d-x.hull_radius_m-y.hull_radius_m)
            if lower<=threshold_m:
                w={"a_parameter_interval":[x.t0,x.t1],"b_parameter_interval":[y.t0,y.t1],
                   "chord_distance_m":d,"distance_lower_bound_m":lower,
                   "enclosure_allowance_m":x.hull_radius_m+y.hull_radius_m,
                   "status":"possible_contact_conservative"}
                if best is None or lower<best["distance_lower_bound_m"]: best=w
    return best


def line(a:Point,b:Point)->Bezier: return Bezier((a,b))


def eased_branch(length_m:float,slope:float)->Bezier:
    positive(length_m,"branch x span"); positive(abs(slope),"nonzero branch slope")
    finite(slope,"slope")
    L,m=length_m,slope
    # x=L*u; y=m*L*(u^3-u^4/2). Zero curvature at both boundaries.
    return Bezier(((0.,0.),(L/4,0.),(L/2,0.),(3*L/4,m*L/4),(L,m*L/2)))


def join_check(a:Bezier,b:Bezier,position_tol:float=1e-6,tangent_tol:float=1e-7,
               curvature_tol:float=1e-7)->dict:
    p=distance(a.at(1),b.at(0)); t=distance(a.tangent(1),b.tangent(0))
    k=abs(a.curvature(1)-b.curvature(0))
    return {"position_error_m":p,"unit_tangent_error":t,"curvature_error_per_m":k,
            "pass":p<=position_tol and t<=tangent_tol and k<=curvature_tol}
