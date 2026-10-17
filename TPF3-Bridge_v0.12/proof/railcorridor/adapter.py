"""Transport-neutral plan contract and fault-injectable IN-MEMORY mock adapter.

No TPF3 API names, sockets, Lua calls or real game/desktop actions are used here.
Read-back verifies ordered vertices and explicit endpoint-node identity in this
mock representation only. No guarantee about actual game's snapping is implied.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
import math
from .geometry import Alignment, Knot, digest, number, integer

CAPS=('construct.track_polyline3','construct.bridge_reservation','construct.tunnel_reservation',
      'query.realised_geometry','query.operation_receipt')


def manifest(environment='mock', *, demonstrated=True):
    if environment not in ('mock','tpf3_unprobed'):raise ValueError('unknown adapter environment')
    state='demonstrated' if demonstrated and environment=='mock' else 'unknown'
    return {'schema_version':'0.9.0','environment':environment,'build':'memory-adapter-v09' if environment=='mock' else None,
            'capabilities':{k:{'state':state,'evidence':'local mock tests' if state=='demonstrated' else None} for k in CAPS},
            'real_game_probed':False,'atomic_rollback':False}


def operation(kind,payload,dependencies):
    rec={'kind':kind,'payload':deepcopy(payload),'dependencies':list(dependencies)}
    rec['operation_id']=digest(rec)
    return rec


def verify_operation(op):
    if not isinstance(op,dict) or set(op)!={'kind','payload','dependencies','operation_id'}:raise ValueError('operation schema')
    if op['kind'] not in CAPS[:3]:raise ValueError('operation kind not allowed')
    if op['operation_id']!=digest({k:v for k,v in op.items() if k!='operation_id'}):raise ValueError('operation content hash mismatch')
    if not isinstance(op['dependencies'],list) or len(set(op['dependencies']))!=len(op['dependencies']):raise ValueError('dependencies')
    p=op['payload']
    if set(p)!={'asset_key','points','start_node','end_node','mode'}:raise ValueError('payload schema')
    if not all(isinstance(p[k],str) and p[k] for k in ('asset_key','start_node','end_node','mode')):raise ValueError('asset identity')
    if not isinstance(p['points'],list) or not 2<=len(p['points'])<=20000:raise ValueError('polyline points')
    for point in p['points']:
        if not isinstance(point,(list,tuple)) or len(point)!=3:raise ValueError('3D point required')
        for n in point:number(n,'position',minimum=-1e6,maximum=1e6)
    if any(math.dist(a,b)<1e-8 for a,b in zip(p['points'],p['points'][1:])):raise ValueError('degenerate polyline')


def compile_plan(candidate,fixture,*,world_revision=0):
    integer(world_revision,'world revision')
    if not candidate.get('accepted_for_reference_comparison'):raise ValueError('uncertified candidate cannot reach mock lowering')
    if candidate.get('brief_hash')!=digest(fixture):raise ValueError('candidate/brief mismatch')
    if candidate.get('candidate_hash')!=digest({k:v for k,v in candidate.items() if k!='candidate_hash'}):raise ValueError('candidate identity mismatch')
    a=Alignment(tuple(Knot(**k) for k in candidate['alignment']['knots']))
    m=fixture['mock'];sp=fixture['corridor']['track_centres_m'];ops=[];cert=[]
    for track,offset in (('eastbound',-sp/2),('westbound',sp/2)):
        last=None
        # Split by terrain run, then by batch length, without changing parent alignment.
        for run_index,r in enumerate(candidate['terrain']['runs']):
            n=max(1,math.ceil((r['x1']-r['x0'])/m['batch_length_m']))
            for j in range(n):
                x0=r['x0']+(r['x1']-r['x0'])*j/n;x1=r['x0']+(r['x1']-r['x0'])*(j+1)/n
                # Global derivative bound covers every included subspan.
                bound=max(b['position_second_derivative_upper'] for b in a.bounds(offset)['segments'])
                step=25.0 if bound==0 else min(25.0,math.sqrt(8*m['polyline_tolerance_m']/bound))
                npts=max(1,math.ceil((x1-x0)/step))
                points=[list(a.point(x0+(x1-x0)*k/npts,offset)) for k in range(npts+1)]
                # Stable nodes are parametric boundaries, never raw coordinate-coincidence joins.
                node=lambda x:f'{track}:x:{x:.9f}'
                payload={'asset_key':f'{track}:{run_index}:{j}','points':points,
                         'start_node':node(x0),'end_node':node(x1),'mode':r['kind']}
                deps=[] if last is None else [last]
                structure=None
                if r['kind'] in ('river_bridge','viaduct','tunnel'):
                    kind='construct.tunnel_reservation' if r['kind']=='tunnel' else 'construct.bridge_reservation'
                    structure=operation(kind,payload,deps);ops.append(structure);deps=[structure['operation_id']]
                op=operation('construct.track_polyline3',payload,deps);ops.append(op);last=op['operation_id']
                cert.append({'asset_key':payload['asset_key'],'parent_geometry_hash':a.identity,
                             'parameter_interval':[x0,x1],'error_bound_m':bound*((x1-x0)/npts)**2/8+1e-9})
    required=sorted(set(o['kind'] for o in ops)|{'query.realised_geometry','query.operation_receipt'})
    plan={'schema_version':'0.9.0','candidate_hash':candidate['candidate_hash'],
          'brief_hash':digest(fixture),'expected_world_revision':world_revision,
          'terrain_revision':fixture['terrain']['revision'],'edit_region':fixture['corridor']['site'],
          'operations':ops,'required_capabilities':required,'lowering_certificates':cert,
          'realised_tolerance_m':m['realised_tolerance_m'],
          'scope':'two corridor tracks and civil reservation objects only; no branch connection or station edit',
          'real_game_execution_authorised':False}
    plan['plan_hash']=digest(plan)
    return plan


class LostAcknowledgement(RuntimeError):pass


@dataclass
class MockAdapter:
    capabilities: dict=field(default_factory=manifest)
    revision: int=0
    terrain_revision: str='synthetic_terrain_01'
    drop_ack_at: int|None=None
    snap_at: int|None=None
    snap_distance_m: float=.2
    fail_at: int|None=None
    ledger: dict=field(default_factory=dict)
    nodes: dict=field(default_factory=dict)
    writes: int=0
    dropped: bool=False

    def receipt(self,opid):return deepcopy(self.ledger.get(opid))
    def apply(self,op):
        verify_operation(op)
        if self.capabilities.get('environment')!='mock':raise ValueError('memory adapter cannot impersonate a game')
        oid=op['operation_id']
        if oid in self.ledger:
            if self.ledger[oid]['submitted_hash']!=digest(op):raise ValueError('idempotency collision')
            return self.receipt(oid)
        if any(d not in self.ledger for d in op['dependencies']):raise ValueError('unsatisfied dependency')
        if self.fail_at is not None and self.writes==self.fail_at:raise RuntimeError('injected construction rejection')
        realised=deepcopy(op['payload'])
        if self.snap_at is not None and self.writes==self.snap_at:
            realised['points'][-1][1]+=self.snap_distance_m
        if op['kind']=='construct.track_polyline3':
            for key,p in ((realised['start_node'],realised['points'][0]),(realised['end_node'],realised['points'][-1])):
                if key in self.nodes and math.dist(self.nodes[key],p)>1e-7:
                    raise RuntimeError('mock topology node position mismatch')
            for key,p in ((realised['start_node'],realised['points'][0]),(realised['end_node'],realised['points'][-1])):
                self.nodes[key]=list(p)
        self.writes+=1;self.revision+=1
        r={'operation_id':oid,'kind':op['kind'],'submitted_hash':digest(op),'realised':realised,'revision':self.revision}
        self.ledger[oid]=r
        if self.drop_ack_at is not None and self.writes-1==self.drop_ack_at and not self.dropped:
            self.dropped=True;raise LostAcknowledgement('effect applied, acknowledgement lost')
        return self.receipt(oid)


def preflight(plan,adapter):
    if plan.get('plan_hash')!=digest({k:v for k,v in plan.items() if k!='plan_hash'}):return ['plan_hash_mismatch']
    if plan.get('real_game_execution_authorised') is not False:return ['forged_game_authority']
    if adapter.capabilities.get('environment')!='mock':return ['real_game_adapter_not_connected']
    actual_required=sorted(set(o.get('kind') for o in plan.get('operations',[]))|{'query.realised_geometry','query.operation_receipt'})
    if actual_required!=plan.get('required_capabilities'):return ['capability_requirement_mismatch']
    missing=[k for k in actual_required if adapter.capabilities.get('capabilities',{}).get(k,{}).get('state')!='demonstrated']
    if missing:return ['capability_not_demonstrated:'+k for k in missing]
    if adapter.terrain_revision!=plan['terrain_revision']:return ['stale_terrain_revision']
    # Resume may include exactly this plan's already-applied operations, no others.
    ids={o['operation_id'] for o in plan['operations']}
    if set(adapter.ledger)-ids:return ['unrelated_world_edit']
    own=len(set(adapter.ledger)&ids)
    if adapter.revision!=plan['expected_world_revision']+own:return ['stale_world_revision']
    known=set();region=plan['edit_region'];errors=[]
    for op in plan['operations']:
        try:verify_operation(op)
        except (ValueError,TypeError,KeyError) as exc:return ['invalid_operation:'+str(exc)]
        if op['operation_id'] in known:return ['duplicate_operation_id']
        if any(d not in known for d in op['dependencies']):return ['dependency_order_invalid']
        known.add(op['operation_id'])
        if any(not(region[0]<=p[0]<=region[2] and region[1]<=p[1]<=region[3]) for p in op['payload']['points']):
            errors.append('outside_authorised_plan_region')
    return errors


def execute(plan,adapter):
    errors=preflight(plan,adapter)
    out={'plan_hash':plan.get('plan_hash'),'environment':'mock','trace':[],
         'real_game_constructed':False,'rollback_attempted':False}
    if errors:
        out.update(status='preflight_blocked',reasons=errors,writes=adapter.writes);return out
    recovered=0
    for op in plan['operations']:
        try:
            r=adapter.apply(op)
        except LostAcknowledgement:
            recovered+=1;r=adapter.receipt(op['operation_id'])
            if r is None:
                out.update(status='uncertain_effect_stop',writes=adapter.writes);return out
        except (RuntimeError,ValueError) as exc:
            out.update(status='partial_failure',reason=str(exc),writes=adapter.writes,
                       recovery='retain ledger; no automatic compensation');return out
        if r['submitted_hash']!=digest(op) or r['operation_id']!=op['operation_id']:
            out.update(status='receipt_identity_mismatch',writes=adapter.writes);return out
        pts=op['payload']['points'];actual=r['realised']['points']
        if len(pts)!=len(actual):deviation=None;ok=False
        else:
            deviation=max(math.dist(p,q) for p,q in zip(pts,actual))
            ok=deviation<=plan['realised_tolerance_m']
        ok=ok and all(r['realised'][k]==op['payload'][k] for k in ('asset_key','start_node','end_node','mode'))
        out['trace'].append({'operation_id':op['operation_id'],'kind':op['kind'],
                             'readback_matches':ok,'maximum_vertex_deviation_m':deviation})
        if not ok:
            out.update(status='realised_geometry_mismatch',writes=adapter.writes,
                       recovery='halt and retain effect; no implicit rollback');return out
    out.update(status='mock_verified',writes=adapter.writes,acknowledgements_reconciled=recovered,
               effect_count=len(adapter.ledger),node_count=len(adapter.nodes),
               verification_scope='ordered mock vertices, payload and explicit node identities; not real game topology')
    return out
