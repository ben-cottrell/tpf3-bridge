"""Compose two banks; recompile the combined physical network, never union locks.

The compared isolated/A-to-B/B-to-A families have identical outer ports, platform
positions and reserved corridor. A single directional crossover supplies one
complete recovery cycle, not universal access. The source component is the
v0.5 authored data record, not an authentic UK turnout.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
import copy
import math
from railproof.model import positive
from railgeom.curves import Bezier, line
from railgeom.network import Network, Turnout, RailPath
from railgeom.patterns import Assembly, FanSpec, GeometryProfile
from railgeom.compiler import compile_assembly, CompiledAssembly
from railops.access import AccessSpec, build_dual_access
from railclear.catalogue import read_json, import_component, place_synthetic

EVIDENCE = Path(__file__).resolve().parents[2] / 'evidence'
FAMILIES = ('isolated', 'a_to_b', 'b_to_a')

@dataclass(frozen=True)
class StationSpec:
    bank_separation_m: float = 48.0
    bank_a_y_m: float = -42.0
    common_corridor_m: float = 760.0
    lead_length_m: float = 1000.0
    link_west_x_m: float = 280.0
    platform_start_local_x_m: float = 650.0
    boarding_length_m: float = 320.0
    short_boarding_length_m: float = 260.0
    platform_spacing_m: float = 12.0
    margin_m: float = 5.0
    def __post_init__(self):
        for k,v in asdict(self).items():
            if k == 'bank_a_y_m':
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
                    raise ValueError('Invalid bank ordinate')
            else: positive(v,k,zero=k=='margin_m')
        if self.short_boarding_length_m>self.boarding_length_m:
            raise ValueError('Short boarding interval exceeds the longest platform')
        if self.bank_separation_m < 3*self.platform_spacing_m+4.0:
            raise ValueError('Banks overlap or fail the declared corridor gap')
        if self.lead_length_m <= self.common_corridor_m + 210.0:
            raise ValueError('Access leads do not fit the declared corridor')

@dataclass
class Station:
    assembly: Assembly
    spec: StationSpec
    family: str
    component_report: dict
    eligibility: dict


def merge_network(target: Network, source: Network, prefix: str,
                  dx: float=0., dy: float=0.) -> None:
    """Namespace every physical and control identity; preserve explicit ports."""
    def key(s): return f'{prefix}:{s}'
    positions={}
    curves={}
    for eid,e in source.edges.items():
        c=e.curve.transformed(dx,dy); curves[eid]=c
        positions[e.u]=c.at(0);positions[e.v]=c.at(1)
    for pid,p in source.ports.items():
        target.port(key(pid),positions.get(pid,(p.position[0]+dx,p.position[1]+dy)),p.role)
    for tid,t in source.turnouts.items():
        name=key(tid)
        if name in target.turnouts: raise ValueError('Duplicate component')
        target.turnouts[name]=Turnout(name,key(t.toe),key(t.normal),key(t.reverse),key(t.controller),t.normal_state,t.reverse_state)
    for eid,e in source.edges.items():
        target.edge(key(eid),key(e.u),key(e.v),curves[eid],
                    component=key(e.component) if e.component else None,
                    controller=key(e.controller) if e.controller else None,
                    state=e.state,kind=e.kind)


def _component_record(path: Path):
    item=import_component(read_json(path))
    if item.report['status'] != 'accepted_for_synthetic_tests':
        raise ValueError('This station compiler supports authored synthetic component data only')
    g=item.normalized_geometry
    roles={p['role']:p for p in g['ports']}
    toe=roles['toe']['xy'];normal=roles['normal']['xy'];branch=roles['reverse']['xy']
    if toe != [0.,0.] or abs(normal[1])>1e-8 or normal[0]<=0:
        raise ValueError('Link component requires a canonical horizontal local datum')
    curve=next(e.curve for e in item.network.edges.values() if e.state=='R')
    tangent=curve.tangent(1)
    if tangent[0]<=0 or tangent[1]<=0:
        raise ValueError('Link needs a positive supported branch tangent')
    slope=tangent[1]/tangent[0]
    if abs(branch[0]-normal[0])>1e-7:
        raise ValueError('Asymmetric exit abscissas are outside this link adapter')
    return item,roles,normal[0],branch[1],slope


def build_station(family: str='isolated', spec: StationSpec=StationSpec(),
                  profile: GeometryProfile=GeometryProfile(), component_path: Path|None=None)->Station:
    if family not in FAMILIES: raise ValueError('Unsupported station family')
    n=Network('station_'+family,metadata={'composition_version':'0.6.0','family':family,
          'spec':asdict(spec),'catalogue':'mixed_authored_synthetic_only',
          'cant_mm':0,'vertical_profile':'level','construction_authorised':False})
    platforms={};boundaries={};bank_records=[]
    fan=FanSpec(spacing_m=spec.platform_spacing_m,platform_start_x_m=spec.platform_start_local_x_m,
                boarding_length_m=spec.boarding_length_m,margin_m=spec.margin_m,
                site_end_x_m=max(1000.,spec.platform_start_local_x_m+spec.boarding_length_m))
    access=AccessSpec(common_link_m=spec.common_corridor_m,lead_length_m=spec.lead_length_m)
    # Both use the same handed fan, with enough inter-bank space. This is not
    # mirroring a fan into itself or joining coincident display coordinates.
    for bank,dy in (('A',spec.bank_a_y_m),('B',spec.bank_a_y_m+spec.bank_separation_m)):
        part=build_dual_access(fan,access,profile)
        # Preserve the original brief's four 260 m and four 320 m boarding
        # intervals with a common terminal-end line. Move the actual markers
        # and storage geometry as well as the scalar length; labels alone do
        # not make a shorter platform.
        for short in ('P1','P2'):
            p=part.platforms[short]
            end=fan.platform_start_x_m+fan.boarding_length_m
            start=end-spec.short_boarding_length_m
            marker=p['marker_port']; old=part.network.ports[marker]
            part.network.ports[marker]=replace(old,position=(start+spec.margin_m,old.position[1]))
            for eid in (f'lead_{short}',p['storage_edge']):
                e=part.network.edges[eid]
                part.network.edges[eid]=replace(e,curve=line(part.network.ports[e.u].position,part.network.ports[e.v].position))
            p.update({'usable_length_m':spec.short_boarding_length_m,'boarding_interval_x_m':[start,end]})
        part.network.validate()
        merge_network(n,part.network,bank,spec.lead_length_m,dy)
        bank_records.append({'bank':bank,'subassembly_hash':part.network.digest(),
                             'translation_m':[spec.lead_length_m,dy],
                             'origin':'authored_v04_fan_and_access; not imported UK hardware'})
        boundaries[bank]={'arrival':f'{bank}:ARRIVAL','departure':f'{bank}:DEPARTURE'}
        for old,p in part.platforms.items():
            pid=bank+old[1:];q=copy.deepcopy(p)
            q.update({'id':pid,'label':str(int(old[1:])+(4 if bank=='B' else 0)),
                      'bank':bank,'marker_port':f'{bank}:{p["marker_port"]}',
                      'storage_edge':f'{bank}:{p["storage_edge"]}',
                      'boarding_interval_x_m':[x+spec.lead_length_m for x in p['boarding_interval_x_m']]})
            platforms[pid]=q
    partition_item,partition_roles,partition_L,partition_dy,partition_m=_component_record(component_path or EVIDENCE/'component_import_synthetic.json')
    partition_span=2*partition_L+(spec.bank_separation_m-2*partition_dy)/partition_m
    section_cuts=[spec.link_west_x_m,spec.link_west_x_m+partition_L,
                  spec.link_west_x_m+partition_span-partition_L,spec.link_west_x_m+partition_span]
    item=None;placements=[]
    if family!='isolated':
        item,roles,L,dy,m=partition_item,partition_roles,partition_L,partition_dy,partition_m
        # Two immutable imported components; only their allowed rigid placements
        # change. No stretching of the imported geometry is performed.
        gap=spec.bank_separation_m-2*dy
        if gap<=0: raise ValueError('Link has no positive connector')
        span=2*L+gap/m
        x0=spec.link_west_x_m;x1=x0+span
        common_start=spec.lead_length_m-spec.common_corridor_m
        if not common_start<x0 or not x1<spec.lead_length_m:
            raise ValueError('Recovery component pair does not fit common corridor')
        donor,receiver=('A','B') if family=='a_to_b' else ('B','A')
        ydon=spec.bank_a_y_m+(spec.bank_separation_m if donor=='B' else 0)
        yrec=spec.bank_a_y_m+(spec.bank_separation_m if receiver=='B' else 0)
        mirror=donor=='B'
        west=place_synthetic(item,x0,ydon,0.,mirror)
        east=place_synthetic(item,x1,yrec,math.pi,mirror)
        merge_network(n,west,'LINK_W');merge_network(n,east,'LINK_E')
        for bank in ('A','B'): del n.edges[f'{bank}:access_common']
        T=roles['toe']['id'];N=roles['normal']['id'];R=roles['reverse']['id']
        links=[(donor+'_common_w',f'{donor}:ACCESS:T',f'LINK_W:{T}'),
               (donor+'_common_e',f'LINK_W:{N}',f'{donor}:APPROACH'),
               (receiver+'_common_w',f'{receiver}:ACCESS:T',f'LINK_E:{N}'),
               (receiver+'_common_e',f'LINK_E:{T}',f'{receiver}:APPROACH'),
               ('recovery_diagonal',f'LINK_W:{R}',f'LINK_E:{R}')]
        for eid,u,v in links:n.edge(eid,u,v,line(n.ports[u].position,n.ports[v].position))
        placements=[{'instance':'LINK_W','record_hash':item.record_hash,'geometry_hash':item.geometry_hash,
                     'translation_m':[x0,ydon],'angle_rad':0.,'mirror':mirror},
                    {'instance':'LINK_E','record_hash':item.record_hash,'geometry_hash':item.geometry_hash,
                     'translation_m':[x1,yrec],'angle_rad':math.pi,'mirror':mirror}]
        n.metadata.update({'link_span_m':span,'recovery_direction':donor+'_to_'+receiver,
                           'imported_component_record_hash':item.record_hash})
    # Matched synthetic section boundaries prevent the extra graph vertices in
    # a link candidate from silently providing a finer release model than the
    # isolated comparison. These are explicit study sections, NOT track circuits.
    for eid,e in list(n.edges.items()):
        if e.component or not (eid.endswith(':access_common') or '_common_' in eid):
            continue
        a0,b0=e.curve.at(0),e.curve.at(1)
        if abs(a0[1]-b0[1])>1e-8 or b0[0]<=a0[0]:
            raise ValueError('Common-corridor partition expects a forward horizontal line')
        cuts=[x for x in section_cuts if a0[0]+1e-7<x<b0[0]-1e-7]
        if not cuts:continue
        del n.edges[eid]
        previous=e.u
        for index,x in enumerate(cuts+[b0[0]]):
            nxt=e.v if index==len(cuts) else n.port(f'{eid}:cut{index}',(x,a0[1]))
            n.edge(f'{eid}:s{index}',previous,nxt,line(n.ports[previous].position,n.ports[nxt].position))
            previous=nxt
    n.metadata['synthetic_section_policy']={'common_x_breaks_m':section_cuts,
        'matched_across_families':True,'authority':'authored_study_sections_not_real_signalling'}
    n.metadata['station_permissions']=boundaries
    n.metadata['bank_sources']=bank_records
    n.metadata['imported_component_instances']=placements
    n.validate()
    routes={};eligibility={}
    for group in ('A','B'):
        eligibility[group]={}
        for pid,p in sorted(platforms.items()):
            flags={}
            for direction,start,end in (('in',boundaries[group]['arrival'],p['marker_port']),
                                        ('out',p['marker_port'],boundaries[group]['departure'])):
                paths=n.enumerate_paths(start,end)
                # The selected family is a tree of legal components and should
                # have at most one route; do not choose silently from alternatives.
                if len(paths)>1: raise ValueError('Multiple alternatives require an explicit route policy')
                if paths:
                    rid=f'{group}:{pid}:{direction}'
                    routes[rid]=RailPath(rid,start,end,paths[0].steps)
                flags[direction]=bool(paths)
            flags['complete']=flags['in'] and flags['out'];eligibility[group][pid]=flags
    report={'bank_components':bank_records,'imported_instances':placements,
            'import_report':item.report if item else None,'authentic_UK_components':False,
            'component_authenticity':'unassessed; every generated or imported component is authored synthetic'}
    return Station(Assembly(n,routes,platforms,profile),spec,family,report,eligibility)


def compile_station(station:Station)->CompiledAssembly:
    c=compile_assembly(station.assembly)
    # Preserve the compiler data, but replace stale whole-leg status in this
    # versioned wrapper. No legacy package is modified.
    c.provenance=copy.deepcopy(c.provenance)
    c.provenance['station_compiler_version']='0.6.0'
    c.provenance['time_model']='external_railops_motion_and_sectional_release'
    c.provenance['assessments'].update({'sectional_release':'available_in_station_scheduler',
                                      'station_topology':'four_directional_boundaries_eight_platform_roads'})
    c.provenance['component_admission']=copy.deepcopy(station.component_report)
    c.provenance['movement_eligibility']=copy.deepcopy(station.eligibility)
    return c
