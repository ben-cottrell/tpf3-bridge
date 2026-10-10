"""Terrain-bound semantic mock construction; no real engine API.

A current snapshot hash is checked even when a publisher reuses its revision
label. The snapshot is checked before EVERY operation and after its receipt.
Old corridor tracks are not emitted alongside their replacement. Existing built
track demolition/splicing remains unsupported and must not be inferred here.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass,field
from railcorridor.geometry import digest
from railbranch import adapter as legacy
from .planning import verify_binding

LAND='reserve.terrain_junction_land'


def manifest(environment='mock'):
    m=legacy.manifest(environment);m['build']='memory-terrain-junction-v011' if environment=='mock' else None
    m['capabilities'][LAND]={'state':'demonstrated' if environment=='mock' else 'unknown',
        'evidence':'terrain-bound memory tests' if environment=='mock' else None}
    return m


def compile_plan(j,corridor,fixture,binding):
    verify_binding(j,corridor,fixture,binding)
    p=legacy.compile_plan(j);p.pop('plan_hash')
    terrain=binding['terrain']
    payload=dict(design_hash=binding['design_hash'],terrain_hash=binding['terrain_hash'],
        source_corridor_hash=binding['source_corridor_hash'],
        reservations=[dict(edge_id=r['edge_id'],x_interval_m=r['x_interval_m'],box_m=r['reservation_box_m'],kind=r['kind']) for r in terrain['terrain_rows']],
        structure_requirements=terrain['structure_reservations'],
        status='reserved_planning_envelopes_not_constructed_structures',
        geometry_hash=binding['geometry_hash'])
    ops=[legacy.operation(LAND,payload,[])]
    for op in p['operations']:
        ops.append(legacy.operation(op['kind'],op['payload'],[ops[-1]['operation_id']]))
    p.update(version='0.11.0',operations=ops,required_capabilities=sorted({o['kind'] for o in ops}|set(legacy.CAPS[4:])),
        design_hash=binding['design_hash'],snapshot_hash=digest(corridor),
        terrain_revision=corridor['terrain']['revision'],terrain_hash=digest(corridor['terrain']),
        site_constraints_hash=digest(corridor['corridor']),edit_region=deepcopy(corridor['corridor']['site']),
        source_replacement_scope='new unbuilt design replaces corridor alignment; no existing-asset deletion',
        actual_structure_assets='unassessed',geometry_and_terrain_screen_ref=binding['design_hash'])
    p['plan_hash']=digest(p);return p


@dataclass
class MockTerrainAdapter(legacy.MockJunctionAdapter):
    capabilities:dict=field(default_factory=manifest)
    snapshot:dict=field(default_factory=dict)
    land_reservations:dict=field(default_factory=dict)
    mutate_terrain_after_write:int|None=None
    def __post_init__(self):
        self.snapshot=deepcopy(self.snapshot)
        if self.snapshot:self.terrain_revision=self.snapshot['terrain']['revision']
    def apply(self,op):
        if op['kind']!=LAND:
            result=super().apply(op)
        else:
            if op['operation_id']!=digest({k:v for k,v in op.items() if k!='operation_id'}):raise ValueError('operation hash')
            oid=op['operation_id']
            if oid in self.ledger:
                if self.ledger[oid]['submitted_hash']!=digest(op):raise ValueError('operation collision')
                return self.receipt(oid)
            if self.capabilities['environment']!='mock':raise ValueError('not a real game adapter')
            if any(dep not in self.ledger for dep in op['dependencies']):raise ValueError('missing dependency')
            if self.fail_at==self.writes:raise RuntimeError('injected failure')
            self.land_reservations[oid]=deepcopy(op['payload']);self.writes+=1;self.revision+=1
            result=dict(operation_id=oid,submitted_hash=digest(op),realised=deepcopy(op['payload']),revision=self.revision)
            self.ledger[oid]=result
            if self.drop_ack_at==self.writes-1 and not self.dropped:
                self.dropped=True;raise legacy.LostAcknowledgement('land reservation applied; receipt lost')
        if self.mutate_terrain_after_write==self.writes:
            self.snapshot['terrain']['water_level_m']+=.1
        return result


def current_payload(op,adapter):
    if op['kind']==LAND:return deepcopy(adapter.land_reservations.get(op['operation_id']))
    return legacy.current_payload(op,adapter)


def snapshot_errors(plan,adapter):
    errors=[]
    if digest(adapter.snapshot)!=plan['snapshot_hash']:errors.append('snapshot_content_changed')
    if adapter.snapshot.get('terrain',{}).get('revision')!=plan['terrain_revision'] or adapter.terrain_revision!=plan['terrain_revision']:errors.append('terrain_revision_changed')
    if digest(adapter.snapshot.get('terrain',{}))!=plan['terrain_hash']:errors.append('terrain_content_changed')
    if digest(adapter.snapshot.get('corridor',{}))!=plan['site_constraints_hash']:errors.append('site_constraints_changed')
    return errors


def execute(plan,adapter,binding):
    out=dict(plan_hash=plan.get('plan_hash'),environment='mock',trace=[],game_constructed=False,rollback_attempted=False)
    errors=[]
    if plan.get('plan_hash')!=digest({k:v for k,v in plan.items() if k!='plan_hash'}):errors.append('plan_hash_mismatch')
    if binding.get('design_hash')!=digest({k:v for k,v in binding.items() if k!='design_hash'}):errors.append('binding_hash_mismatch')
    if not binding.get('accepted_for_reference_design'):errors.append('design_not_accepted')
    if binding.get('design_hash')!=plan.get('design_hash') or binding.get('geometry_hash')!=plan.get('candidate_hash'):errors.append('design_identity_mismatch')
    if plan.get('real_game_execution_authorised') is not False:errors.append('forged_game_authority')
    if adapter.capabilities['environment']!='mock':errors.append('real_game_not_connected')
    expected=sorted({o['kind'] for o in plan['operations']}|set(legacy.CAPS[4:]))
    if expected!=plan['required_capabilities']:errors.append('capability_declaration_mismatch')
    errors += ['capability_unknown:'+k for k in expected if adapter.capabilities['capabilities'].get(k,{}).get('state')!='demonstrated']
    errors+=snapshot_errors(plan,adapter)
    ids={o['operation_id'] for o in plan['operations']}
    if set(adapter.ledger)-ids or adapter.revision!=plan['expected_world_revision']+len(set(adapter.ledger)&ids):errors.append('stale_world')
    known=set();region=plan['edit_region'];land=[o for o in plan['operations'] if o['kind']==LAND]
    if len(land)!=1 or not plan['operations'] or plan['operations'][0]['kind']!=LAND:errors.append('land_reservation_not_first')
    elif land[0]['payload']['design_hash']!=binding['design_hash']:errors.append('wrong_land_binding')
    for op in plan['operations']:
        if op['operation_id']!=digest({k:v for k,v in op.items() if k!='operation_id'}):errors.append('operation_hash_mismatch')
        if op['operation_id'] in known or any(d not in known for d in op['dependencies']):errors.append('invalid_dependency_order')
        known.add(op['operation_id']);p=op['payload']
        es=[p] if op['kind']==legacy.CAPS[0] else p.get('edges',[]) if op['kind']==legacy.CAPS[1] else []
        if any(not region[0]<=v[0]<=region[2] or not region[1]<=v[1]<=region[3] for e in es for v in e['points']):errors.append('outside_edit_region')
    if errors:return dict(out,status='preflight_blocked',reasons=sorted(set(errors)),writes=adapter.writes)
    recovered=0
    for op in plan['operations']:
        if snapshot_errors(plan,adapter):return dict(out,status='environment_changed',reasons=snapshot_errors(plan,adapter),writes=adapter.writes)
        try:r=adapter.apply(op)
        except legacy.LostAcknowledgement:recovered+=1;r=adapter.receipt(op['operation_id'])
        except (ValueError,RuntimeError,KeyError) as exc:return dict(out,status='partial_failure',reason=str(exc),writes=adapter.writes)
        if snapshot_errors(plan,adapter):return dict(out,status='environment_changed',reasons=snapshot_errors(plan,adapter),writes=adapter.writes)
        if not r or r.get('submitted_hash')!=digest(op) or not legacy.payload_equal(op['payload'],current_payload(op,adapter),plan['realised_tolerance_m']):
            return dict(out,status='realised_geometry_or_semantics_mismatch',operation_id=op['operation_id'],writes=adapter.writes)
        out['trace'].append(dict(operation_id=op['operation_id'],verified=True))
    check=legacy.verify_topology(plan,adapter)
    return dict(out,status='mock_terrain_junction_verified' if check['passed'] else 'realised_topology_mismatch',
        topology_check=check,writes=adapter.writes,recovered_acknowledgements=recovered,
        terrain_snapshot_rechecked=True,actual_bridge_or_tunnel_asset_built=False)
