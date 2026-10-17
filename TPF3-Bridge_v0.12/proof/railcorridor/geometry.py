"""C2 x-monotone 3D alignments with genuine normal-offset parallel tracks.

Quintic interpolation has zero slope and curvature at its knots. This deliberately
restricted family is not a general clothoid solver. Bounds use ordinary floating
arithmetic, not formal interval arithmetic. x is NOT engineering chainage.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from bisect import bisect_right
import hashlib
import json
import math


def number(value, name='value', *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite numeric input')
    if minimum is not None and value < minimum: raise ValueError(f'{name} below minimum')
    if maximum is not None and value > maximum: raise ValueError(f'{name} above maximum')
    return float(value)


def integer(value, name='value', *, minimum=0, maximum=1000000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} outside integer domain')
    return value


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def smooth(u):
    number(u, 'u', minimum=0, maximum=1)
    return u*u*u*(10+u*(-15+6*u))


def derivatives(u):
    number(u, 'u', minimum=0, maximum=1)
    return 30*u*u*(1-u)**2, 60*u*(1-u)*(1-2*u), 60-360*u+360*u*u


@dataclass(frozen=True)
class Knot:
    x: float
    y: float
    z: float
    def __post_init__(self):
        for key, val in asdict(self).items(): number(val, key, minimum=-1e6, maximum=1e6)


@dataclass(frozen=True)
class Alignment:
    knots: tuple[Knot, ...]
    def __post_init__(self):
        if not isinstance(self.knots, tuple) or not 2 <= len(self.knots) <= 100:
            raise ValueError('2..100 immutable knots required')
        if any(not isinstance(k, Knot) for k in self.knots): raise ValueError('Knot required')
        if any(b.x-a.x < 1.0 for a,b in zip(self.knots,self.knots[1:])):
            raise ValueError('x knots must increase by at least one metre')
    @property
    def identity(self): return digest(self.record())
    def record(self): return {'model':'c2_quintic_graph_3d_v09', 'knots':[asdict(k) for k in self.knots]}
    def segment(self, x):
        number(x,'x',minimum=self.knots[0].x,maximum=self.knots[-1].x)
        i=min(len(self.knots)-2, max(0,bisect_right([k.x for k in self.knots],x)-1))
        return self.knots[i],self.knots[i+1]
    def state(self, x):
        a,b=self.segment(x); L=b.x-a.x; u=(x-a.x)/L; d1,d2,d3=derivatives(u)
        y=a.y+(b.y-a.y)*smooth(u); z=a.z+(b.z-a.z)*smooth(u)
        yp=(b.y-a.y)*d1/L; ypp=(b.y-a.y)*d2/L**2; yppp=(b.y-a.y)*d3/L**3
        zp=(b.z-a.z)*d1/L; zpp=(b.z-a.z)*d2/L**2
        w=math.hypot(1,yp); k=ypp/w**3; kx=yppp/w**3-3*yp*ypp*ypp/w**5
        return {'x':x,'y':y,'z':z,'yp':yp,'ypp':ypp,'yppp':yppp,'zp':zp,'zpp':zpp,
                'w':w,'k':k,'kx':kx}
    def point(self,x,offset=0):
        number(offset,'offset',minimum=-100,maximum=100)
        t=self.state(x)
        if 1-offset*t['k'] <= 0: raise ValueError('offset curve is singular')
        return (x-offset*t['yp']/t['w'], t['y']+offset/t['w'], t['z'])
    def quantities(self,x,offset=0):
        t=self.state(x); f=1-offset*t['k']
        if f<=0: raise ValueError('offset curve is singular')
        a=t['w']*f
        ap=t['yp']*t['ypp']/t['w']*f-t['w']*offset*t['kx']
        q=t['zp']/a
        q_s=t['zpp']/a**2-t['zp']*ap/a**3
        return {'plan_curvature':t['k']/f,'grade':q,
                'vertical_curvature':q_s/(1+q*q)**1.5,
                'horizontal_dx_metric':a,'travel_dx_metric':math.hypot(a,t['zp'])}
    def bounds(self,offset=0):
        """Sufficient global derivative bounds for every x, including joins."""
        number(offset,'offset',minimum=-100,maximum=100)
        rows=[]
        for a,b in zip(self.knots,self.knots[1:]):
            L=b.x-a.x;dy=abs(b.y-a.y);dz=abs(b.z-a.z)
            P=1.875*dy/L; Q=10/math.sqrt(3)*dy/L**2; T=60*dy/L**3
            ZP=1.875*dz/L; ZQ=10/math.sqrt(3)*dz/L**2
            K=Q; Kx=T+3*P*Q*Q; w=math.hypot(1,P); m=1-abs(offset)*K
            if m<=0: raise ValueError('offset regularity cannot be certified')
            ap=P*Q*(1+abs(offset)*K)+w*abs(offset)*Kx
            Kv=ZQ/m**2+ZP*ap/m**3
            Bxy=Q+abs(offset)*(Kx*w+K*Q)
            rows.append({'x0':a.x,'x1':b.x,'plan_curvature_upper':K/m,
                         'grade_upper':ZP/m,'vertical_curvature_upper':Kv,
                         'curvature_rate_upper':Kx/m**3,
                         'position_second_derivative_upper':math.hypot(Bxy,ZQ),
                         'travel_dx_metric_upper':math.hypot(w*(1+abs(offset)*K),ZP)})
        keys=('plan_curvature_upper','grade_upper','vertical_curvature_upper','curvature_rate_upper')
        vals={k:max(r[k] for r in rows)*(1+1e-10) for k in keys}
        vals.update({'segments':rows,'arithmetic':'floating analytical bounds; not interval arithmetic'})
        return vals
    def polyline(self,offset=0,*,max_step=25.0,tolerance=0.02,point_budget=10000):
        """Bound positional error of the piecewise-linear lowering in metres."""
        number(max_step,'max_step',minimum=.01,maximum=1000)
        number(tolerance,'tolerance',minimum=1e-6,maximum=1)
        integer(point_budget,'point_budget',minimum=2,maximum=100000)
        bounds=self.bounds(offset); points=[]; xs=[]; error=0
        for r in bounds['segments']:
            step=max_step
            B=r['position_second_derivative_upper']
            if B>0:step=min(step,math.sqrt(8*tolerance/B))
            count=max(1,math.ceil((r['x1']-r['x0'])/step))
            if len(points)+count+1>point_budget: raise ValueError('polyline point budget exhausted')
            dx=(r['x1']-r['x0'])/count;error=max(error,B*dx*dx/8)
            for j in range(count):
                x=r['x0']+j*dx;xs.append(x);points.append(self.point(x,offset))
        xs.append(self.knots[-1].x);points.append(self.point(xs[-1],offset))
        return {'points':points,'parameters_x':xs,'positional_error_bound_m':error+1e-9,
                'parent_alignment_hash':self.identity,'offset_m':offset,
                'not_a_vehicle_pose_error_bound':True}
    def length(self,offset=0,*,steps_per_segment=100):
        """Composite Simpson estimate; reports its estimator, not exact chainage."""
        integer(steps_per_segment, minimum=2,maximum=10000)
        if steps_per_segment%2: raise ValueError('even Simpson count required')
        total=0.
        for a,b in zip(self.knots,self.knots[1:]):
            h=(b.x-a.x)/steps_per_segment
            f=lambda x:self.quantities(x,offset)['travel_dx_metric']
            s=f(a.x)+f(b.x)
            s+=sum((4 if i%2 else 2)*f(a.x+i*h) for i in range(1,steps_per_segment))
            total+=h*s/3
        return total


def limits_check(alignment, spacing_m, profile):
    """Zero-cant speed screens plus sufficient geometry bounds on BOTH tracks."""
    number(spacing_m,'spacing',minimum=2.8,maximum=10)
    needed={'speed_mph','min_radius_m','max_grade','min_vertical_radius_m',
            'max_lateral_accel_mps2','max_lateral_jerk_mps3','cant_mm'}
    if set(profile)!=needed:raise ValueError('profile fields differ from supported contract')
    for k,v in profile.items():number(v,k,minimum=0,maximum=1e6)
    if profile['cant_mm']!=0:raise ValueError('canted alignment not implemented; do not ignore cant')
    if any(profile[k]<=0 for k in needed-{'cant_mm'}):raise ValueError('positive project limits required')
    v=profile['speed_mph']*.44704; records=[]; failures=[]
    for offset in (-spacing_m/2,spacing_m/2):
        b=alignment.bounds(offset); tests={
            'radius_bound': b['plan_curvature_upper']<=1/profile['min_radius_m'],
            'gradient_bound': b['grade_upper']<=profile['max_grade'],
            'vertical_radius_bound':b['vertical_curvature_upper']<=1/profile['min_vertical_radius_m'],
            'zero_cant_lateral_accel':v*v*b['plan_curvature_upper']<=profile['max_lateral_accel_mps2'],
            'zero_cant_lateral_jerk':v**3*b['curvature_rate_upper']<=profile['max_lateral_jerk_mps3']}
        failures.extend(f'{offset}:{k}:not_certified_by_bound' for k,ok in tests.items() if not ok)
        records.append({'offset_m':offset,'bounds':b,'checks':tests,
                        'lateral_accel_upper_mps2':v*v*b['plan_curvature_upper'],
                        'lateral_jerk_upper_mps3':v**3*b['curvature_rate_upper']})
    return {'status':'project_bounds_pass' if not failures else 'project_bounds_not_certified',
            'tracks':records,'failures':failures,'speed_target_mps':v,
            'profile_hash':digest(profile),'geometry_hash':alignment.identity,
            'limits_origin':'project targets, not universal UK thresholds',
            'actual_operating_speed_achieved':False,'uk_complete_assessment':'unassessed'}
