"""Semantic junction lowering and a fault-injectable in-memory adapter.

Unlike a list of route polylines, this plan retains shared physical edges,
turnout traversal/state relationships and non-connecting crossing semantics.
All capability identifiers are PROPOSED BRIDGE names, never TPF3 API names.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass,field,asdict
import math
from railcorridor.geometry import digest,integer
from .operations import verify_candidate

CAPS=('construct.junction_track3','construct.junction_turnout3','declare.junction_crossing',
      'reserve.junction_crossing_envelope','query.junction_geometry_topology','query.operation_receipt')


def manifest(environment='mock'):
    if environment not in ('mock','tpf3_unprobed'):raise ValueError('environment')
    return {'environment':environment,'build':'memory-junction-v010' if environment=='mock' else None,
            'capabilities':{k:{'state':'demonstrated' if environment=='mock' else 'unknown','evidence':'local synthetic tests' if environment=='mock' else None} for k in CAPS},
            'game_probed':False,'rollback':False}


def operation(kind,payload,deps):
    v={'kind':kind,'payload':deepcopy(payload),'dependencies':list(deps)};v['operation_id']=digest(v);return v


def compile_plan(j):
    verify_candidate(j);ops=[];edges={};certs=[]
    for eid,e in j.network.edges.items():
        pl=j.polyline(eid)
        edges[eid]={'id':eid,'u':e.u,'v':e.v,'component':e.component,'controller':e.controller,'state':e.state,'points':pl['points']}
        certs.append({'edge_id':eid,'positional_error_bound_m':pl['position_error_bound_m']})
    x=j.assessment['crossing'];deps=[]
    if j.mode!='flat':
        payload={'mode':j.mode,'crossing_x_m':x['x_m'],'footprint_x_m':x['footprint_x_m'],
                 'required_rail_separation_m':x['required_project_separation_m'],'status':'reservation_not_finished_structure'}
        op=operation(CAPS[3],payload,[]);ops.append(op);deps=[op['operation_id']]
    for cid,t in sorted(j.network.turnouts.items()):
        payload={'id':cid,'controller':t.controller,'toe':t.toe,'normal':t.normal,'reverse':t.reverse,
                 'normal_state':t.normal_state,'reverse_state':t.reverse_state,
                 'edges':[edges[eid] for eid,e in sorted(j.network.edges.items()) if e.component==cid],
                 'source_geometry_hash':j.assessment['component_geometry_hash'],'authentic_uk_component':False}
        op=operation(CAPS[1],payload,deps);ops.append(op);deps=[op['operation_id']]
    for eid,e in sorted(j.network.edges.items()):
        if e.component:continue
        op=operation(CAPS[0],edges[eid],deps);ops.append(op);deps=[op['operation_id']]
    op=operation(CAPS[2],{'edge_ids':x['edge_ids'],'x_m':x['x_m'],'footprint_x_m':x['footprint_x_m'],
                         'relation':'exclusive_flat_crossing' if j.mode=='flat' else 'grade_separated',
                         'required_separation_m':x['required_project_separation_m'],
                         'expected_separation_m':x['minimum_rail_separation_m'],'connect_at_intersection':False},deps)
    ops.append(op)
    p={'version':'0.10.0','candidate_hash':j.assessment['candidate_hash'],'operations':ops,
       'required_capabilities':sorted({o['kind'] for o in ops}|set(CAPS[4:])),
       'expected_world_revision':0,'terrain_revision':'junction_terrain_unassessed',
       'edit_region':[0,j.spec.site_y_min_m,j.spec.span_m,j.spec.site_y_max_m],
       'lowering_certificates':certs,'expected_routes':{k:{'start':v.start,'end':v.end,'steps':[asdict(s) for s in v.steps]} for k,v in j.routes.items()},
       'expected_physical_edge_ids':sorted(edges),'expected_turnout_ids':sorted(j.network.turnouts),
       'realised_tolerance_m':.05,'real_game_execution_authorised':False,
       'scope':'new junction geometry/semantics and crossing reservation, not v0.9 terrain construction or actual game'}
    p['plan_hash']=digest(p);return p


class LostAcknowledgement(RuntimeError):pass

@dataclass
class MockJunctionAdapter:
    capabilities:dict=field(default_factory=manifest)
    revision:int=0
    terrain_revision:str='junction_terrain_unassessed'
    fail_at:int|None=None
    drop_ack_at:int|None=None
    snap_at:int|None=None
    corrupt_state_at:int|None=None
    ledger:dict=field(default_factory=dict)
    edges:dict=field(default_factory=dict)
    turnouts:dict=field(default_factory=dict)
    crossings:list=field(default_factory=list)
    reservations:list=field(default_factory=list)
    writes:int=0
    dropped:bool=False
    def receipt(self,oid):return deepcopy(self.ledger.get(oid))
    def apply(self,op):
        if op['operation_id']!=digest({k:v for k,v in op.items() if k!='operation_id'}):raise ValueError('operation content mismatch')
        if self.capabilities['environment']!='mock':raise ValueError('not a real game adapter')
        oid=op['operation_id']
        if oid in self.ledger:
            if self.ledger[oid]['submitted_hash']!=digest(op):raise ValueError('operation identity collision')
            return self.receipt(oid)
        if any(d not in self.ledger for d in op['dependencies']):raise ValueError('dependency not satisfied')
        if self.fail_at==self.writes:raise RuntimeError('injected failure')
        p=deepcopy(op['payload']);kind=op['kind'];add=[]
        if kind==CAPS[0]:add=[p]
        elif kind==CAPS[1]:add=p['edges']
        elif kind not in CAPS[2:4]:raise ValueError('unknown write')
        if self.snap_at==self.writes and add:add[0]['points'][len(add[0]['points'])//2][2]+=.2
        if self.corrupt_state_at==self.writes and kind==CAPS[1]:add[1]['state']=add[0]['state']
        # Node checks are transactional within this MEMORY operation only.
        nodes={}
        for e in [*self.edges.values(),*add]:
            for node,pos in ((e['u'],e['points'][0]),(e['v'],e['points'][-1])):
                if node in nodes and math.dist(nodes[node],pos)>1e-7:raise RuntimeError('node position mismatch')
                nodes[node]=pos
        if any(e['id'] in self.edges for e in add):raise RuntimeError('duplicate physical edge')
        for e in add:self.edges[e['id']]=deepcopy(e)
        if kind==CAPS[1]:self.turnouts[p['id']]=deepcopy(p)
        elif kind==CAPS[2]:self.crossings.append(deepcopy(p))
        elif kind==CAPS[3]:self.reservations.append(deepcopy(p))
        self.writes+=1;self.revision+=1
        r={'operation_id':oid,'submitted_hash':digest(op),'realised':p,'revision':self.revision}
        self.ledger[oid]=r
        if self.drop_ack_at==self.writes-1 and not self.dropped:
            self.dropped=True;raise LostAcknowledgement('effect applied; acknowledgement lost')
        return self.receipt(oid)


def current_payload(op,adapter):
    """Read the current realised objects, not just a historical receipt echo."""
    kind=op['kind'];p=op['payload']
    if kind==CAPS[0]:return deepcopy(adapter.edges.get(p['id']))
    if kind==CAPS[1]:
        r=deepcopy(adapter.turnouts.get(p['id']))
        if r is None:return None
        r['edges']=[deepcopy(adapter.edges.get(e['id'])) for e in p['edges']]
        return r
    if kind==CAPS[2]:return deepcopy(adapter.crossings[0]) if len(adapter.crossings)==1 else None
    if kind==CAPS[3]:return deepcopy(adapter.reservations[0]) if len(adapter.reservations)==1 else None
    return None


def payload_equal(expected,realised,tolerance):
    """Only geometric vertices receive a tolerance. Every semantic field is exact."""
    if type(expected)!=type(realised):return False
    if isinstance(expected,dict):
        if set(expected)!=set(realised):return False
        for k,v in expected.items():
            if k=='points':
                if len(v)!=len(realised[k]) or any(len(p)!=3 or len(q)!=3 or not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in q) or math.dist(p,q)>tolerance for p,q in zip(v,realised[k])):return False
            elif not payload_equal(v,realised[k],tolerance):return False
        return True
    if isinstance(expected,list):return len(expected)==len(realised) and all(payload_equal(a,b,tolerance) for a,b in zip(expected,realised))
    return expected==realised


def verify_topology(plan,adapter):
    errors=[]
    if sorted(adapter.edges)!=plan['expected_physical_edge_ids']:errors.append('physical_edge_set_mismatch')
    if sorted(adapter.turnouts)!=plan['expected_turnout_ids']:errors.append('turnout_set_mismatch')
    for t in adapter.turnouts.values():
        es=[e for e in adapter.edges.values() if e['component']==t['id']]
        actual={(e['u'],e['v'],e['controller'],e['state']) for e in es}
        expected={(t['toe'],t['normal'],t['controller'],t['normal_state']),(t['toe'],t['reverse'],t['controller'],t['reverse_state'])}
        if actual!=expected or len(es)!=2:errors.append('turnout_traversal_mismatch')
    for rid,r in plan['expected_routes'].items():
        here=r['start'];used=set()
        for s in r['steps']:
            e=adapter.edges.get(s['edge_id'])
            if e is None:errors.append('route_edge_missing:'+rid);break
            a,b=(e['u'],e['v']) if s['forward'] else (e['v'],e['u'])
            if a!=here:errors.append('disconnected_route:'+rid)
            if e['component']:
                if e['component'] in used:errors.append('illegal_branch_to_branch_turn:'+rid)
                used.add(e['component'])
            here=b
        if here!=r['end']:errors.append('wrong_route_end:'+rid)
    if len(adapter.crossings)!=1:errors.append('crossing_record_missing_or_duplicated')
    else:
        c=adapter.crossings[0]
        if c['connect_at_intersection'] is not False:errors.append('invented_crossing_connection')
        if all(e in adapter.edges for e in c['edge_ids']):
            def at_x(e,x):
                ps=adapter.edges[e]['points']
                for a,b in zip(ps,ps[1:]):
                    if a[0]<=x<=b[0]:return [a[k]+(b[k]-a[k])*(x-a[0])/(b[0]-a[0]) for k in range(3)]
                raise ValueError('crossing outside realised edge')
            a,b=(at_x(e,c['x_m']) for e in c['edge_ids']);sep=abs(a[2]-b[2])
            if abs(a[1]-b[1])>.05:errors.append('realised_plan_crossing_mismatch')
            if c['relation']=='grade_separated' and sep<c['required_separation_m']:errors.append('realised_separation_failure')
            if c['relation']=='exclusive_flat_crossing' and sep>.05:errors.append('flat_crossing_height_mismatch')
        else:errors.append('crossing_edges_missing')
    return {'passed':not errors,'errors':sorted(set(errors)),
            'scope':'mock shared-edge topology, legal traversal, and declared crossing geometry; no actual train has run'}


def execute(plan,adapter):
    out={'plan_hash':plan.get('plan_hash'),'environment':'mock','trace':[],'game_constructed':False,'rollback_attempted':False}
    errors=[]
    if plan.get('plan_hash')!=digest({k:v for k,v in plan.items() if k!='plan_hash'}):errors.append('plan_hash_mismatch')
    if plan.get('real_game_execution_authorised') is not False:errors.append('forged_game_authority')
    required=sorted({o['kind'] for o in plan['operations']}|set(CAPS[4:]))
    if required!=plan['required_capabilities']:errors.append('capability_declaration_mismatch')
    if adapter.capabilities['environment']!='mock':errors.append('real_game_not_connected')
    errors += ['capability_unknown:'+k for k in required if adapter.capabilities['capabilities'].get(k,{}).get('state')!='demonstrated']
    ids={o['operation_id'] for o in plan['operations']}
    if adapter.terrain_revision!=plan['terrain_revision']:errors.append('stale_terrain')
    if set(adapter.ledger)-ids or adapter.revision!=plan['expected_world_revision']+len(set(adapter.ledger)&ids):errors.append('stale_world')
    known=set();region=plan['edit_region']
    for op in plan['operations']:
        if op['operation_id']!=digest({k:v for k,v in op.items() if k!='operation_id'}):errors.append('operation_hash_mismatch')
        if op['operation_id'] in known or any(d not in known for d in op['dependencies']):errors.append('invalid_dependency_order')
        known.add(op['operation_id']);p=op['payload']
        es=[p] if op['kind']==CAPS[0] else p.get('edges',[]) if op['kind']==CAPS[1] else []
        for e in es:
            if any(not region[0]<=v[0]<=region[2] or not region[1]<=v[1]<=region[3] for v in e['points']):errors.append('outside_edit_region')
    if errors:return dict(out,status='preflight_blocked',reasons=sorted(set(errors)),writes=adapter.writes)
    recovered=0
    for op in plan['operations']:
        try:r=adapter.apply(op)
        except LostAcknowledgement:recovered+=1;r=adapter.receipt(op['operation_id'])
        except (ValueError,RuntimeError,KeyError) as exc:return dict(out,status='partial_failure',reason=str(exc),writes=adapter.writes)
        if not r or r.get('submitted_hash')!=digest(op) or not payload_equal(op['payload'],current_payload(op,adapter),plan['realised_tolerance_m']):
            return dict(out,status='realised_geometry_or_semantics_mismatch',operation_id=op['operation_id'],writes=adapter.writes)
        out['trace'].append({'operation_id':op['operation_id'],'verified':True})
    audit=verify_topology(plan,adapter)
    return dict(out,status='mock_junction_verified' if audit['passed'] else 'realised_topology_mismatch',
                topology_check=audit,writes=adapter.writes,recovered_acknowledgements=recovered)
