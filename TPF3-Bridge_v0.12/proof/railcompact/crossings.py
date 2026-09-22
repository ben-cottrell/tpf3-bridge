"""Strict admission for two explicit straight, interior crossing paths.

An at-grade crossing is not automatically an all-directions junction. This
limited model admits no slips and no connection between its two path identities.
"""
import math
from railgeom.curves import sub, cross, distance


def validate_crossings(network):
    records=network.metadata.get('diamond_crossings',[])
    if not isinstance(records,list):raise ValueError('crossings_must_be_list')
    result={}; ids=set()
    for r in records:
        if not isinstance(r,dict) or set(r)!={'id','edges','position_m','kind','source_kind','hardware_and_flange_clearance'}:
            raise ValueError('unsupported_crossing_record')
        if not isinstance(r['id'],str) or not r['id'] or r['id'] in ids:raise ValueError('duplicate_or_invalid_crossing_id')
        ids.add(r['id'])
        if r['kind']!='synthetic_fixed_crossing_two_nonconnecting_routes' or r['source_kind']!='authored_synthetic':
            raise ValueError('unsupported_crossing_admission')
        if r['hardware_and_flange_clearance']!='unassessed':raise ValueError('no_hardware_approval_supported')
        ed=r['edges'];xy=r['position_m']
        if not isinstance(ed,list) or len(ed)!=2 or len(set(ed))!=2 or any(x not in network.edges for x in ed):
            raise ValueError('crossing_needs_two_existing_edges')
        if not isinstance(xy,list) or len(xy)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xy):
            raise ValueError('invalid_crossing_position')
        a,b=(network.edges[x] for x in ed)
        if a.component or b.component or len(a.curve.controls)!=2 or len(b.curve.controls)!=2:
            raise ValueError('crossing_supports_straight_noncomponent_edges_only')
        if {a.u,a.v}&{b.u,b.v}:raise ValueError('diamond_must_not_create_shared_port')
        p,q=a.curve.at(0),b.curve.at(0);v=sub(a.curve.at(1),p);w=sub(b.curve.at(1),q)
        den=cross(v,w)
        if abs(den)<=1e-10:raise ValueError('parallel_or_degenerate_crossing')
        u=cross(sub(q,p),w)/den;t=cross(sub(q,p),v)/den
        if not 1e-6<u<1-1e-6 or not 1e-6<t<1-1e-6:raise ValueError('crossing_not_strictly_interior')
        point=(p[0]+u*v[0],p[1]+u*v[1])
        if distance(point,tuple(xy))>1e-6:raise ValueError('crossing_location_mismatch')
        key=frozenset(ed)
        if key in result:raise ValueError('duplicate_crossing_pair')
        result[key]=r
    return result
