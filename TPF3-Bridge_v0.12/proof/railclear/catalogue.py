"""Closed, transport-neutral component record import. No executable content.

Schema validation, reference recording, geometric usability and source review
are independent. JSON self-assertions cannot grant authoritative admission.
Even reviewed geometry does not constitute a complete construction approval.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from .model import digest, positive, finite
from railgeom.curves import Bezier, distance
from railgeom.network import Network, Turnout

ID=re.compile(r'^[A-Za-z][A-Za-z0-9_.:-]{0,95}$')

def identifier(x):
    if not isinstance(x,str) or not ID.fullmatch(x): raise ValueError('Invalid identifier')
    return x


def exact(d,fields):
    if not isinstance(d,dict) or set(d)!=set(fields): raise ValueError('Missing/unknown fields: '+str(fields))


def text(s,name):
    if not isinstance(s,str) or not s.strip() or len(s)>5000:raise ValueError('Invalid '+name)
    return s


def reject_constant(x):raise ValueError('Nonfinite JSON value: '+x)

def unique_object(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:raise ValueError('Duplicate JSON field: '+k)
        obj[k]=v
    return obj


def read_json(path:Path,max_bytes=2000000):
    path=Path(path)
    if path.stat().st_size>max_bytes:raise ValueError('Input size exceeds import budget')
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)


@dataclass
class Imported:
    record:dict
    normalized_geometry:dict|None
    record_hash:str
    geometry_hash:str|None
    report:dict
    network:Network|None


def normalize_geometry(g):
    exact(g,('units','coordinate_frame','gauge','ports','routes','controller','switch_type','crossing_type'))
    if g['units'] not in ('m','mm'):raise ValueError('Unsupported length unit')
    if g['coordinate_frame']!='local_plan_xy_level_zero_cant':raise ValueError('Unsupported datum/vertical domain')
    factor=1. if g['units']=='m' else .001
    gauge=positive(g['gauge'],'gauge')*factor
    if not .5<=gauge<=2.:raise ValueError('Gauge outside admitted study domain')
    text(g['switch_type'],'switch type');text(g['crossing_type'],'crossing type')
    controller=identifier(g['controller'])
    if not isinstance(g['ports'],list) or len(g['ports'])!=3:raise ValueError('Restricted importer requires exactly three ports')
    ports={}
    for p in g['ports']:
        exact(p,('id','role','xy'));id=identifier(p['id'])
        if id in ports:raise ValueError('Duplicate port ID')
        if p['role'] not in ('toe','normal','reverse'):raise ValueError('Unknown turnout port role')
        if not isinstance(p['xy'],list) or len(p['xy'])!=2:raise ValueError('Invalid planar port')
        xy=[finite(x,'port')*factor for x in p['xy']]
        if any(abs(x)>1e5 for x in xy):raise ValueError('Local component span outside scope')
        ports[id]={'id':id,'role':p['role'],'xy':xy}
    if {p['role'] for p in ports.values()}!={'toe','normal','reverse'}:raise ValueError('Duplicate/missing turnout roles')
    role={p['role']:p['id'] for p in ports.values()}
    if not isinstance(g['routes'],list) or len(g['routes'])!=2:raise ValueError('Two explicit traversals required')
    routes={}
    for r in g['routes']:
        exact(r,('id','from','to','state','bezier_controls'));id=identifier(r['id'])
        if id in routes:raise ValueError('Duplicate route ID')
        state=r['state']
        if state not in ('N','R'):raise ValueError('Unknown state')
        if r['from']!=role['toe'] or r['to']!=role['normal' if state=='N' else 'reverse']:
            raise ValueError('Illegal toe/branch traversal')
        if not isinstance(r['bezier_controls'],list):raise ValueError('Curve controls missing')
        controls=[]
        for p in r['bezier_controls']:
            if not isinstance(p,list) or len(p)!=2:raise ValueError('Only explicit 2D Bezier controls accepted')
            controls.append(tuple(finite(x,'curve coordinate')*factor for x in p))
        curve=Bezier(tuple(controls))
        if distance(curve.at(0),tuple(ports[r['from']]['xy']))>1e-6 or distance(curve.at(1),tuple(ports[r['to']]['xy']))>1e-6:
            raise ValueError('Curve/port mismatch')
        # Minimum required regularity check; does not establish operating radius/speed.
        bound=curve.curvature_upper()
        if not math.isfinite(bound):raise ValueError('Unresolved derivative regularity')
        routes[id]={'id':id,'from':r['from'],'to':r['to'],'state':state,
                    'bezier_controls':[list(p) for p in controls]}
    if {r['state'] for r in routes.values()}!={'N','R'}:raise ValueError('Both normal and reverse routes required')
    curves=[Bezier(tuple(tuple(p) for p in r['bezier_controls'])) for r in routes.values()]
    if distance(curves[0].tangent(0),curves[1].tangent(0))>1e-7:
        raise ValueError('Shared toe has incompatible approach tangents')
    return {'units':'m','coordinate_frame':g['coordinate_frame'],'gauge':gauge,
            'ports':sorted(ports.values(),key=lambda x:x['id']),'routes':sorted(routes.values(),key=lambda x:x['id']),
            'controller':controller,'switch_type':g['switch_type'],'crossing_type':g['crossing_type']}


def import_component(record:dict,reviewed_record_hashes:frozenset[str]=frozenset())->Imported:
    """reviewed_record_hashes is trusted caller policy, NOT a JSON record field.

    The demo supplies an empty registry for real sources. Hash allowlisting binds
    a locally reviewed record; it is not digital proof of engineering authority.
    """
    record=json.loads(json.dumps(record,allow_nan=False))
    if not isinstance(reviewed_record_hashes,frozenset) or any(not isinstance(h,str) or not re.fullmatch(r'[a-f0-9]{64}',h) for h in reviewed_record_hashes):
        raise ValueError('Expected a trusted caller hash registry')
    exact(record,('schema_version','component_id','display_name','origin_kind','source','geometry','limits'))
    if record['schema_version']!='0.5.0':raise ValueError('Unsupported catalogue schema')
    cid=identifier(record['component_id']);text(record['display_name'],'display name')
    if record['origin_kind'] not in ('authored_synthetic','external_reference'):raise ValueError('Unknown origin')
    src=record['source'];exact(src,('source_id','issue','locator','reuse_status','geometry_evidence'))
    identifier(src['source_id']);text(src['issue'],'source issue');text(src['locator'],'source locator')
    if src['reuse_status'] not in ('authored','permitted','unresolved'):raise ValueError('Invalid reuse status')
    if src['geometry_evidence'] not in ('authored_synthetic','metadata_only','drawing_transcription'):raise ValueError('Invalid evidence type')
    synthetic=record['origin_kind']=='authored_synthetic'
    if synthetic != (src['geometry_evidence']=='authored_synthetic'):raise ValueError('Contradictory origin/evidence')
    if synthetic and src['reuse_status']!='authored':raise ValueError('Synthetic record requires authored provenance')
    limits=record['limits'];exact(limits,('diverging_speed_mps','speed_evidence','application_profile'))
    text(limits['application_profile'],'application profile')
    if limits['diverging_speed_mps'] is None:
        if limits['speed_evidence']!='unresolved':raise ValueError('Missing value cannot have resolved speed evidence')
    else:
        positive(limits['diverging_speed_mps'],'speed')
        if limits['speed_evidence'] not in ('project_assumption','source_backed_claim'):raise ValueError('Invalid speed origin')
    rawhash=digest(record);g=None;gh=None;n=None;missing=[]
    if record['geometry'] is None:missing.append('complete_component_geometry')
    else:
        g=normalize_geometry(record['geometry']);gh=digest(g)
        n=Network(cid,metadata={'import_schema':'0.5.0','record_hash':rawhash,'geometry_hash':gh,
             'geometry_origin':record['origin_kind'],'UK_component_approval':'unassessed'})
        for p in g['ports']:n.port(p['id'],tuple(p['xy']))
        roles={p['role']:p['id'] for p in g['ports']}
        t=Turnout(cid,roles['toe'],roles['normal'],roles['reverse'],g['controller']);n.turnouts[cid]=t
        for r in g['routes']:
            n.edge(r['id'],r['from'],r['to'],Bezier(tuple(tuple(p) for p in r['bezier_controls'])),
                   component=cid,controller=g['controller'],state=r['state'],kind='imported_centreline_route')
        n.validate()
    if not synthetic:
        if src['geometry_evidence']!='drawing_transcription':missing.append('dimensional_drawing_evidence')
        if src['reuse_status']!='permitted':missing.append('reuse_permission')
        if rawhash not in reviewed_record_hashes:missing.append('trusted_local_review_of_exact_record')
    if limits['diverging_speed_mps'] is None or limits['speed_evidence']!='source_backed_claim':
        missing.append('source_backed_speed_applicability')
    # Synthetic data is usable only within labelled tests. Geometry import and
    # operating suitability are separate, not one optimistic accepted boolean.
    admitted_geometry=g is not None and (synthetic or not any(x in missing for x in
        ('dimensional_drawing_evidence','reuse_permission','trusted_local_review_of_exact_record')))
    status=('accepted_for_synthetic_tests' if synthetic and g is not None else
            'reference_only_missing_geometry' if g is None else
            'reviewed_geometry_import' if admitted_geometry else 'quarantined_pending_review')
    report={'status':status,'record_hash':rawhash,'geometry_hash':gh,'missing':missing,
            'geometry_schema_checked':g is not None,'geometry_usable_in_declared_mode':admitted_geometry,
            'authenticity':'synthetic' if synthetic else 'source_review_required' if not admitted_geometry else 'locally_reviewed_record',
            'source_speed_record_reviewed':not synthetic and admitted_geometry and 'source_backed_speed_applicability' not in missing,
            'speed_usable_for_UK_design':False,'speed_applicability':'unassessed_application_profile_label_only',
            'full_component_interface':'unassessed','construction_authorised':False,
            'network_export_note':'legacy Network.canonical() retains synthetic pipeline label; no promotion through that export'}
    return Imported(record,g,rawhash,gh,report,n)


def place_synthetic(imported:Imported,dx=0.,dy=0.,angle_rad=0.,mirror=False)->Network:
    """Demonstrate imported-data placement without inventing a UK-approved asset."""
    if imported.report['status']!='accepted_for_synthetic_tests' or imported.network is None:
        raise ValueError('Placement adapter currently admits authored synthetic records only')
    for x in (dx,dy,angle_rad):finite(x,'placement transform')
    if not isinstance(mirror,bool):raise ValueError('Mirror must be bool')
    original=imported.network;n=Network(original.id,metadata={**original.metadata,'transform':{'dx':dx,'dy':dy,'angle_rad':angle_rad,'mirror':mirror}})
    transformed={id:e.curve.transformed(dx,dy,angle_rad,mirror) for id,e in original.edges.items()}
    positions={}
    for id,e in original.edges.items():positions[e.u]=transformed[id].at(0);positions[e.v]=transformed[id].at(1)
    for id,p in original.ports.items():n.port(id,positions[id],p.role)
    n.turnouts.update(original.turnouts)
    for id,e in original.edges.items():n.edge(id,e.u,e.v,transformed[id],component=e.component,controller=e.controller,state=e.state,kind=e.kind)
    n.validate();return n
