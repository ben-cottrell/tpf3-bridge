"""Explicit arrival/departure access, retaining a shared fan (not independence)."""
from dataclasses import dataclass, asdict, replace
import math
from railproof.model import positive
from railgeom.curves import line, eased_branch
from railgeom.patterns import (Assembly, FanSpec, GeometryProfile, build_fan,
                               add_turnout, connector_dimensions)

@dataclass(frozen=True)
class AccessSpec:
    lead_length_m: float = 400.0
    departure_offset_m: float = 12.0
    turnout_span_m: float = 60.0
    branch_slope: float = 0.08
    common_link_m: float = 20.0

    def __post_init__(self):
        for key, value in asdict(self).items():
            positive(value, key)
        if self.branch_slope > 0.25:
            raise ValueError('Unsupported synthetic branch slope')


def build_dual_access(fan: FanSpec = FanSpec(), access: AccessSpec = AccessSpec(),
                      profile: GeometryProfile = GeometryProfile()) -> Assembly:
    a = build_fan(fan, profile)
    n = a.network
    if access.departure_offset_m < profile.separation_m:
        raise ValueError('Independent external leads fail the declared corridor proxy')
    X, _ = connector_dimensions(access.departure_offset_m, access.turnout_span_m,
                                 access.branch_slope)
    if access.lead_length_m <= access.common_link_m + X:
        raise ValueError('access_does_not_fit_declared_lead_length')
    origin = (-access.common_link_m, 0.0)
    t = add_turnout(n, 'ACCESS', origin, access.turnout_span_m,
                    access.branch_slope, math.pi)
    arrival = n.port('ARRIVAL', (-access.lead_length_m, 0.0), 'arrival_only_boundary')
    departure = n.port('DEPARTURE', (-access.lead_length_m, -access.departure_offset_m),
                       'departure_only_boundary')
    n.ports['APPROACH'] = replace(n.ports['APPROACH'], role='internal_common_spine')
    n.edge('arrival_lead', arrival, t.normal,
           line(n.ports[arrival].position, n.ports[t.normal].position))
    n.edge('access_common', t.toe, 'APPROACH', line(origin, (0.0, 0.0)))
    # Build the return in the positive local frame, then rotate the whole shape.
    returning = eased_branch(access.turnout_span_m, access.branch_slope).transformed(
        X, access.departure_offset_m, math.pi).reversed().transformed(*origin, math.pi)
    q = n.port('ACCESS_RETURN_START', returning.at(0))
    r = n.port('ACCESS_RETURN_END', returning.at(1))
    n.edge('access_diagonal', t.reverse, q, line(n.ports[t.reverse].position, n.ports[q].position))
    n.edge('access_return', q, r, returning, kind='plain_line_eased_return')
    n.edge('departure_lead', r, departure, line(n.ports[r].position, n.ports[departure].position))
    routes = {}
    for pid, p in sorted(a.platforms.items()):
        routes[f'{pid}:in'] = n.one_path(arrival, p['marker_port'], f'{pid}:in')
        routes[f'{pid}:out'] = n.one_path(p['marker_port'], departure, f'{pid}:out')
    n.id = 'synthetic_dual_access_shared_bank'
    n.metadata.update({'access_spec': asdict(access),
                       'route_permissions': {'arrival_boundary': arrival, 'departure_boundary': departure},
                       'scope': 'two directional external leads; shared access turnout and platform fan',
                       'construction_authorised': False})
    n.validate()
    return Assembly(n, routes, a.platforms, profile)
