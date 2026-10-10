"""Analytic level-track longitudinal kinematics; not calibrated traction physics.

Uses a constant acceleration/brake bound and one route-wide speed cap. Starts
at rest. Arrival stops; departure continues beyond the boundary by one train
length so its tail can clear. No jerk, adhesion, gradients or power curve.
"""
from dataclasses import dataclass, asdict
import math
from railproof.model import positive, time_value

@dataclass(frozen=True)
class MotionProfile:
    speed_mps: float = 6.7056  # 15 mph; project-selected target, not a turnout rating
    acceleration_mps2: float = 0.6
    braking_mps2: float = 0.7
    setup_ms: int = 5000
    release_ms: int = 3000
    provenance: str = 'project_selected_uncalibrated_level_track_profile'

    def __post_init__(self):
        for key in ('speed_mps', 'acceleration_mps2', 'braking_mps2'):
            positive(getattr(self, key), key)
        time_value(self.setup_ms, 'setup'); time_value(self.release_ms, 'release')
        if self.provenance != 'project_selected_uncalibrated_level_track_profile':
            raise ValueError('This motion implementation is not an approved UK vehicle profile')

@dataclass(frozen=True)
class Phase:
    start_s: float
    duration_s: float
    start_m: float
    start_speed_mps: float
    acceleration_mps2: float

    @property
    def end_m(self):
        return self.start_m + self.start_speed_mps*self.duration_s + 0.5*self.acceleration_mps2*self.duration_s**2
    @property
    def end_s(self):
        return self.start_s + self.duration_s

@dataclass(frozen=True)
class Motion:
    distance_m: float
    stop_at_end: bool
    phases: tuple[Phase, ...]

    @property
    def duration_s(self):
        return self.phases[-1].end_s

    @property
    def peak_speed_mps(self):
        return max(max(p.start_speed_mps, p.start_speed_mps+p.acceleration_mps2*p.duration_s) for p in self.phases)

    def time_at(self, distance_m: float) -> float:
        positive(distance_m, 'path distance', zero=True)
        if distance_m > self.distance_m + 1e-7:
            raise ValueError('Requested distance beyond this motion; no extrapolation')
        if distance_m >= self.distance_m:
            return self.duration_s
        for p in self.phases:
            if distance_m <= p.end_m + 1e-9:
                dx = max(0.0, distance_m-p.start_m)
                if abs(p.acceleration_mps2) < 1e-15:
                    dt = dx/p.start_speed_mps
                else:
                    v = math.sqrt(max(0.0, p.start_speed_mps**2+2*p.acceleration_mps2*dx))
                    dt = 0.0 if dx == 0 else 2*dx/(p.start_speed_mps+v)
                return p.start_s + min(p.duration_s, dt)
        return self.duration_s

    def at(self, time_s: float) -> tuple[float, float]:
        positive(time_s, 'time', zero=True)
        if time_s > self.duration_s+1e-7:
            raise ValueError('Requested time beyond motion')
        if time_s >= self.duration_s:
            p=self.phases[-1]
            return self.distance_m, max(0.0,p.start_speed_mps+p.acceleration_mps2*p.duration_s)
        for p in self.phases:
            if time_s <= p.end_s:
                dt=max(0.0,time_s-p.start_s)
                return (p.start_m+p.start_speed_mps*dt+0.5*p.acceleration_mps2*dt**2,
                        max(0.0,p.start_speed_mps+p.acceleration_mps2*dt))
        raise AssertionError('Motion phase gap')

    def export(self):
        return {'distance_m': self.distance_m, 'stop_at_end': self.stop_at_end,
                'duration_s': self.duration_s, 'peak_speed_mps': self.peak_speed_mps,
                'phases': [asdict(p) for p in self.phases]}


def make_motion(distance_m: float, profile: MotionProfile, *, stop_at_end: bool) -> Motion:
    positive(distance_m, 'motion distance')
    if not isinstance(stop_at_end, bool):
        raise ValueError('stop_at_end must be a boolean')
    a,b,v=profile.acceleration_mps2,profile.braking_mps2,profile.speed_mps
    peak=min(v, math.sqrt(2*distance_m/(1/a+1/b))) if stop_at_end else min(v, math.sqrt(2*a*distance_m))
    sa=peak**2/(2*a); sb=peak**2/(2*b) if stop_at_end else 0.0
    cruise=max(0.0, distance_m-sa-sb)
    phases=[Phase(0.0,peak/a,0.0,0.0,a)]
    if cruise > 1e-10:
        phases.append(Phase(phases[-1].end_s,cruise/peak,phases[-1].end_m,peak,0.0))
    if stop_at_end:
        phases.append(Phase(phases[-1].end_s,peak/b,phases[-1].end_m,peak,-b))
    if not all(math.isfinite(x) for p in phases for x in asdict(p).values()):
        raise ValueError('Numeric overflow in motion')
    return Motion(distance_m,stop_at_end,tuple(phases))
