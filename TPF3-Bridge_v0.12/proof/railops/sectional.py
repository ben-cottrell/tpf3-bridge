"""All-at-once route acquisition with declared sectional release behind the tail.

Sections correspond to authored physical edges, not observed track circuits.
State/body/proximity footprints cover the entire implicated edge(s), deliberately
conservative. A repeated resource is retained through its last use. There is no
moving-block or just-in-time lock acquisition and no inferred signalling approval.
"""
from dataclasses import dataclass, asdict
import math
from railproof.model import Claim, positive, time_value
from railproof.engine import Budget, Calendar
from railgeom.compiler import CompiledAssembly, CompiledRoute
from .motion import MotionProfile, Motion, make_motion

MODES = ('whole_route', 'sectional_release')

@dataclass(frozen=True)
class Footprint:
    resource: str
    state: str | None
    start_m: float
    end_m: float
    edges: tuple[str, ...]

@dataclass(frozen=True)
class Leg:
    route_id: str
    route_length_m: float
    train_length_m: float
    direction: str
    mode: str
    profile: MotionProfile
    motion: Motion
    footprints: tuple[Footprint, ...]
    relative_claims: tuple[Claim, ...]
    occupancy: tuple[dict, ...]

    @property
    def motion_end_ms(self):
        return self.profile.setup_ms + math.ceil(self.motion.duration_s*1000)
    @property
    def release_end_ms(self):
        return max(c.end_ms for c in self.relative_claims)
    def claims_at(self,start_ms: int, owner: str) -> list[Claim]:
        time_value(start_ms,'leg start')
        return [Claim(c.resource,start_ms+c.start_ms,start_ms+c.end_ms,owner,c.state) for c in self.relative_claims]
    def export(self):
        return {'route_id':self.route_id, 'route_length_m':self.route_length_m,
                'train_length_m':self.train_length_m,'direction':self.direction,'mode':self.mode,
                'motion':self.motion.export(),'profile':asdict(self.profile),
                'motion_end_ms':self.motion_end_ms,'release_end_ms':self.release_end_ms,
                'resource_footprints':[asdict(f) for f in self.footprints],
                'relative_claims':[asdict(c) for c in self.relative_claims],
                'physical_occupancy_approximations':list(self.occupancy),
                'path_metric':'sum_of_geometry_upper_length_bounds; operational surrogate',
                'section_authority':'synthetic_edge_release; not an interlocking design',
                'boundary_assumption':('stop with rear at platform marker; front inside storage'
                     if self.direction=='in' else 'continue one train length beyond exit on unmodelled clear line')}


def footprints(compiled: CompiledAssembly, route: CompiledRoute) -> tuple[Footprint, ...]:
    if compiled.routes.get(route.id) != route:
        raise ValueError('Route does not belong to this compiled assembly')
    mapping={}
    previous=0.0
    for seg in route.segments:
        start=seg['entry_chainage_interval_m'][1]
        end=seg['exit_chainage_interval_m'][1]
        if abs(start-previous)>1e-6 or end<=start:
            raise ValueError('Noncontiguous or degenerate route chainage')
        previous=end
        for r in compiled.edge_requirements[seg['edge_id']]:
            key=(r.resource,r.state)
            if key not in mapping:
                mapping[key]=[start,end,set()]
            mapping[key][0]=min(start,mapping[key][0]); mapping[key][1]=max(end,mapping[key][1])
            mapping[key][2].add(seg['edge_id'])
    if abs(previous-route.length_upper_m)>1e-6:
        raise ValueError('Route length/section mismatch')
    result=tuple(Footprint(k[0],k[1],v[0],v[1],tuple(sorted(v[2])))
                 for k,v in sorted(mapping.items(),key=lambda item:(item[0][0],item[0][1] or '')))
    if {(f.resource,f.state) for f in result}!={(r.resource,r.state) for r in route.requirements}:
        raise ValueError('Footprint compilation lost or invented a route resource')
    return result


def compile_leg(compiled: CompiledAssembly, route_id: str, train_length_m: float,
                direction: str, profile: MotionProfile = MotionProfile(),
                mode: str = 'sectional_release') -> Leg:
    positive(train_length_m,'train length')
    if direction not in ('in','out') or mode not in MODES:
        raise ValueError('Unknown leg direction or release mode')
    if route_id not in compiled.routes:
        raise ValueError('Unknown route')
    route=compiled.routes[route_id]
    if route_id.split(':')[-1] != direction:
        raise ValueError('Route permission/direction mismatch')
    fp=footprints(compiled,route)
    motion=make_motion(route.length_upper_m+train_length_m,profile,stop_at_end=direction=='in')
    total=profile.setup_ms+math.ceil(motion.duration_s*1000)+profile.release_ms
    claims=[]; occupancy=[]
    for f in fp:
        occupied_start=profile.setup_ms+math.floor(motion.time_at(f.start_m)*1000)
        tail_clear=profile.setup_ms+math.ceil(motion.time_at(f.end_m+train_length_m)*1000)
        release=tail_clear+profile.release_ms if mode=='sectional_release' else total
        claims.append(Claim(f.resource,0,release,'relative_leg',f.state))
        occupancy.append({'resource':f.resource,'state':f.state,
                          'front_enters_ms':occupied_start,'tail_clears_ms':tail_clear,
                          'lock_acquired_ms':0,'lock_released_ms':release})
    return Leg(route_id,route.length_upper_m,train_length_m,direction,mode,profile,motion,fp,
               tuple(claims),tuple(occupancy))


def earliest_leg(calendar: Calendar, leg: Leg, start_ms: int, owner: str,
                 budget: Budget) -> tuple[int,list[dict]]:
    time_value(start_ms,'earliest activation')
    witnesses=[]
    while True:
        budget.use()
        hits=calendar.conflicts(leg.claims_at(start_ms,owner))
        if not hits:
            return start_ms,witnesses
        witnesses.extend(asdict(c) for c in hits)
        # All locks are acquired at activation, therefore this jump cannot skip
        # an earlier feasible activation with respect to any current conflict.
        start_ms=max(c.end_ms for c in hits)
