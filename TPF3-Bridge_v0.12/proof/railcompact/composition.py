"""Compact inner-road recovery under the original station boundary.

The fixed imported crossover component is not stretched. The fan is a separately
parameterised authored family. A declared diamond creates exclusion, NOT a rail
connection. Scissors recovery reaches the opposite INNER platform only.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import copy
import math
from railgeom.curves import Bezier, line, eased_branch
from railgeom.network import Network, Turnout, RailPath
from railgeom.patterns import Assembly, FanSpec, GeometryProfile, build_fan
from railstation.composition import Station, merge_network, _component_record, EVIDENCE
from railclear.catalogue import place_synthetic

FAMILIES = ('isolated', 'a_to_b', 'b_to_a', 'scissors')
EXPECTED_PORTS = {'A:ARRIVAL': [0., -18.], 'A:DEPARTURE': [0., -6.],
                  'B:ARRIVAL': [0., 6.], 'B:DEPARTURE': [0., 18.]}

@dataclass(frozen=True)
class CompactSpec:
    first_fan_toe_x_m: float = 215.0
    fan_turnout_span_m: float = 70.0
    fan_branch_slope: float = 0.15
    fan_toe_step_m: float = 75.0
    minimum_plain_gap_m: float = 5.0
    link_gap_after_fan_m: float = 5.0
    # Site/ports/platform intervals are immutable in this generator, not knobs.
    def __post_init__(self):
        for k, v in asdict(self).items():
            if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or v <= 0:
                raise ValueError('invalid_compact_parameter:' + k)
        if self.fan_branch_slope > 0.25:
            raise ValueError('unsupported_fan_slope')
        if self.fan_toe_step_m - self.fan_turnout_span_m < self.minimum_plain_gap_m - 1e-9:
            raise ValueError('fan_plain_gap_below_project_target')


def _mirror_y(n: Network) -> None:
    for k, e in list(n.edges.items()):
        n.edges[k] = replace(e, curve=e.curve.transformed(mirror=True))
    for k, p in list(n.ports.items()):
        n.ports[k] = replace(p, position=(p.position[0], -p.position[1]))


def build_compact(family: str = 'scissors', spec: CompactSpec = CompactSpec(),
                  profile: GeometryProfile = GeometryProfile(), component_path: Path | None = None) -> Station:
    if family not in FAMILIES:
        raise ValueError('unsupported_compact_family')
    item, roles, L, offset, slope = _component_record(component_path or EVIDENCE/'component_import_synthetic.json')
    # The parallel-return adapter is deliberately limited to this exact authored
    # geometric family; a new external drawing must not be guessed into it.
    rcurve = next(e.curve for e in item.network.edges.values() if e.state == 'R')
    expected = eased_branch(L, slope)
    if len(rcurve.controls) != len(expected.controls) or any(math.dist(a,b)>1e-8 for a,b in zip(rcurve.controls, expected.controls)):
        raise ValueError('unsupported_component_return_adapter')
    access_span = 2*L + (12. - 2*offset)/slope
    if spec.first_fan_toe_x_m - access_span < spec.minimum_plain_gap_m - 1e-7:
        raise ValueError('access_fan_gap_below_project_target')
    fan_end = spec.first_fan_toe_x_m + 2*spec.fan_toe_step_m + spec.fan_turnout_span_m
    west = fan_end + spec.link_gap_after_fan_m
    east = west + access_span
    if east >= 655. - 1e-7:
        raise ValueError('recovery_does_not_clear_inner_long_platform_marker')
    n = Network('compact_' + family, metadata={
        'composition_version':'0.7.0', 'family':family, 'spec':asdict(spec),
        'catalogue':'authored_synthetic_fan_and_immutable_imported_crossover',
        'cant_mm':0., 'vertical_profile':'level', 'construction_authorised':False,
        'scope':'original boundary and platform positions; inner-road recovery only'})
    platforms = {}; placements = []; banks = []
    T, N, R = (roles[k]['id'] for k in ('toe','normal','reverse'))
    # Fan pointing away from the middle: A negative y, B positive y.
    for bank, y, mirror in (('A',-6.,True),('B',6.,False)):
        fs = FanSpec(first_toe_x_m=spec.first_fan_toe_x_m,
                     turnout_span_m=spec.fan_turnout_span_m,
                     branch_slope=spec.fan_branch_slope,
                     toe_step_m=spec.fan_toe_step_m,
                     platform_start_x_m=650., boarding_length_m=320.,
                     site_end_x_m=1000.)
        part = build_fan(fs, profile)
        del part.network.edges['spine_0']; del part.network.ports['APPROACH']
        if mirror: _mirror_y(part.network)
        merge_network(n, part.network, bank, 0., y)
        banks.append({'bank':bank, 'source_hash':part.network.digest(), 'origin':'authored_parametric_fan',
                      'mirror_y':mirror, 'translation_m':[0.,y]})
        for j in range(1,5):
            old = part.platforms[f'P{j}']; index=5-j if bank=='A' else j
            pid=f'{bank}{index}'; p=copy.deepcopy(old)
            marker=f'{bank}:{old["marker_port"]}'; storage=f'{bank}:{old["storage_edge"]}'
            start=710. if index<=2 else 650.
            port=n.ports[marker]; n.ports[marker]=replace(port,position=(start+5.,port.position[1]))
            end_port=n.edges[storage].v
            end=n.ports[end_port]
            n.ports[end_port]=replace(end,position=(1000.,end.position[1]),role="unengineered_buffer_position")
            for eid in (f'{bank}:lead_P{j}',storage):
                e=n.edges[eid]; n.edges[eid]=replace(e,curve=line(n.ports[e.u].position,n.ports[e.v].position))
            p.update({'id':pid,'label':str(index+(4 if bank=='B' else 0)), 'bank':bank,
                      'marker_port':marker,'storage_edge':storage,'usable_length_m':970.-start,
                      'boarding_interval_x_m':[start,970.]})
            platforms[pid]=p
        # Toe faces WEST: A arrival uses reverse, B departure uses reverse.
        component_mirror = bank=='B'
        access = place_synthetic(item, access_span, y, math.pi, component_mirror)
        prefix=bank+':ACCESS'
        merge_network(n,access,prefix)
        placements.append({'instance':prefix,'record_hash':item.record_hash,'geometry_hash':item.geometry_hash,
                           'translation_m':[access_span,y],'angle_rad':math.pi,'mirror':component_mirror})
        normal_boundary=f'{bank}:'+('DEPARTURE' if bank=='A' else 'ARRIVAL')
        reverse_boundary=f'{bank}:'+('ARRIVAL' if bank=='A' else 'DEPARTURE')
        n.port(normal_boundary,tuple(EXPECTED_PORTS[normal_boundary]),
               'arrival_only_boundary' if normal_boundary.endswith('ARRIVAL') else 'departure_only_boundary')
        n.port(reverse_boundary,tuple(EXPECTED_PORTS[reverse_boundary]),
               'arrival_only_boundary' if reverse_boundary.endswith('ARRIVAL') else 'departure_only_boundary')
        normal_edge=f'{bank}:'+('departure_lead' if bank=='A' else 'arrival_lead')
        n.edge(normal_edge,normal_boundary,f'{prefix}:{N}',line(n.ports[normal_boundary].position,n.ports[f'{prefix}:{N}'].position))
        sign=-1. if bank=='A' else 1.
        # Returning curve moves back towards the trunk; its sign is opposite.
        returning=eased_branch(L,-slope*sign).transformed(0.,y+sign*12.)
        q=n.port(f'{bank}:ACCESS_RETURN',returning.at(1))
        reverse_edge=f'{bank}:'+('arrival_lead' if bank=='A' else 'departure_lead')
        n.edge(reverse_edge,reverse_boundary,q,returning,kind='plain_line_authored_return')
        n.edge(f'{bank}:access_diagonal',q,f'{prefix}:{R}',line(n.ports[q].position,n.ports[f'{prefix}:{R}'].position))
        n.edge(f'{bank}:access_common',f'{prefix}:{T}',f'{bank}:F1:T',line(n.ports[f'{prefix}:{T}'].position,n.ports[f'{bank}:F1:T'].position))
    # Four fixed switch slots. Unused slots become straight study sections.
    # Thus geometry segmentation is identical in all comparison families.
    slots={}
    active={'isolated':set(),'a_to_b':{'AW','BE'},'b_to_a':{'BW','AE'},'scissors':{'AW','BE','BW','AE'}}[family]
    for name, bank, x, angle, mirror in (('AW','A',west,0.,False),('BE','B',east,math.pi,False),
                                        ('BW','B',west,0.,True),('AE','A',east,math.pi,True)):
        y=-6. if bank=='A' else 6.
        if name in active:
            prefix='REC_'+name
            part=place_synthetic(item,x,y,angle,mirror);merge_network(n,part,prefix)
            slots[name]={'toe':f'{prefix}:{T}','normal':f'{prefix}:{N}','reverse':f'{prefix}:{R}'}
            placements.append({'instance':prefix,'record_hash':item.record_hash,'geometry_hash':item.geometry_hash,
                               'translation_m':[x,y],'angle_rad':angle,'mirror':mirror})
        else:
            p=n.port('EMPTY_'+name+'_T',(x,y));q=n.port('EMPTY_'+name+'_N',(x+L if name.endswith('W') else x-L,y))
            n.edge('EMPTY_'+name,p,q,line(n.ports[p].position,n.ports[q].position),kind='matched_study_section')
            slots[name]={'toe':p,'normal':q}
    for bank in ('A','B'):
        original=n.edges.pop(f'{bank}:lead_P1');w=slots[bank+'W'];e=slots[bank+'E']
        for suffix,u,v in (('west',original.u,w['toe']),('middle',w['normal'],e['normal']),('east',e['toe'],original.v)):
            n.edge(f'{bank}:inner_{suffix}',u,v,line(n.ports[u].position,n.ports[v].position))
    crossing_edges=[]
    for name,w,e in (('AB','AW','BE'),('BA','BW','AE')):
        if w in active and e in active:
            u,v=slots[w]['reverse'],slots[e]['reverse'];eid='recovery_'+name
            n.edge(eid,u,v,line(n.ports[u].position,n.ports[v].position),kind='declared_fixed_diamond_leg' if family=='scissors' else 'recovery_plain_connector')
            crossing_edges.append(eid)
    diamonds=[]
    if family=='scissors':
        diamonds=[{'id':'INNER_DIAMOND','edges':sorted(crossing_edges),'position_m':[(west+east)/2,0.],
                   'kind':'synthetic_fixed_crossing_two_nonconnecting_routes',
                   'source_kind':'authored_synthetic','hardware_and_flange_clearance':'unassessed'}]
    permissions={g:{'arrival':g+':ARRIVAL','departure':g+':DEPARTURE'} for g in ('A','B')}
    n.metadata.update({'station_permissions':permissions, 'imported_component_instances':placements,
                       'bank_sources':banks, 'diamond_crossings':diamonds,
                       'synthetic_section_policy':{'x_breaks_m':[west,west+L,east-L,east],
                            'matched_across_families':True,'authority':'authored_not_real_signalling'},
                       'recovery_geometry':{'west_toe_x_m':west,'east_toe_x_m':east,'span_m':access_span,
                           'trunk_spacing_m':12.,'spare_to_long_inner_marker_m':655.-east},
                       'cross_bank_scope':'A may use B1; B may use A4; not whole opposite bank'})
    n.validate()
    routes={}; eligibility={}
    for g in ('A','B'):
        eligibility[g]={}
        for pid,p in sorted(platforms.items()):
            flags={}
            for direction,start,end in (('in',permissions[g]['arrival'],p['marker_port']),
                                        ('out',p['marker_port'],permissions[g]['departure'])):
                paths=n.enumerate_paths(start,end)
                if len(paths)>1:raise ValueError('multiple_routes_need_explicit_selection')
                if paths:
                    rid=f'{g}:{pid}:{direction}';routes[rid]=RailPath(rid,start,end,paths[0].steps)
                flags[direction]=bool(paths)
            flags['complete']=flags['in'] and flags['out'];eligibility[g][pid]=flags
    report={'bank_components':banks,'imported_instances':placements,'import_report':item.report,
            'authentic_UK_components':False,'component_authenticity':'authored_synthetic_only',
            'diamond_hardware':'unassessed','geometry_transform_policy':'rigid_import_placement_only'}
    return Station(Assembly(n,routes,platforms,profile),spec,family,report,eligibility)
