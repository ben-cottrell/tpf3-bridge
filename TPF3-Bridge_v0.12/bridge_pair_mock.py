"""Offline pair lowering and in-memory execution; no game evidence.

A new process means a new mock world. No persistence or automatic resume.
"""
from copy import deepcopy
from pathlib import Path
import sys

from bridge_connection import _fields, _id
from bridge_pair import validate_pair, fit_pair, tangent_at, _bezier, _offset_enclosures

_PROOF = str(Path(__file__).resolve().parent / 'proof')
if _PROOF not in sys.path:
    sys.path.insert(0, _PROOF)
from railcorridor.adapter import operation, verify_operation, manifest, LostAcknowledgement
from railbranch.adapter import payload_equal
from railcorridor.geometry import digest, integer, number
from railgeom.curves import continuous_proximity

POINT_BUDGET = 10000


def _snapshot(record, snapshot):
    _fields(snapshot, 'schema_version environment snapshot_id revision ports neighbours', 'snapshot')
    if snapshot['schema_version'] != '0.12.0' or snapshot['environment'] != 'mock':
        raise ValueError('unsupported snapshot')
    _id(snapshot['snapshot_id'], 'snapshot_id')
    integer(snapshot['revision'], 'snapshot revision')
    if digest(snapshot['ports']) != digest(record['ports']):
        raise ValueError('snapshot ports mismatch (identity, position, tangent or metadata)')
    if not isinstance(snapshot['neighbours'], dict):
        raise ValueError('snapshot neighbours must be an object')
    for key, neighbour in snapshot['neighbours'].items():
        _id(key, 'neighbour id')
        _fields(neighbour, 'asset_key start_node end_node points mode direction', 'neighbour')
        if neighbour['asset_key'] != key or neighbour['direction'] not in ('forward', 'reverse', 'both'):
            raise ValueError('unsupported neighbour identity or direction')
        payload = {k: v for k, v in neighbour.items() if k != 'direction'}
        verify_operation(operation('construct.track_polyline3', payload, []))
        if payload['mode'] != 'plain' or payload['start_node'] == payload['end_node']:
            raise ValueError('unsupported neighbour topology')
    return digest(snapshot)


def compile_pair_plan(candidate, record, snapshot, *, adapter=None):
    """Bind authored state and explicit physical edges to a deterministic plan.

    Revalidation is intentional: an unkeyed hash alone cannot authenticate a
    caller's forged acceptance certificate. No world object is changed here.
    Endpoint tangents are semantic metadata, not claims about chord curvature.
    Supplying a live mock adapter also checks snapshot freshness and capabilities;
    offline compilation only binds them, and execution always checks them.
    """
    validate_pair(record)
    snapshot_hash = _snapshot(record, snapshot)
    if not isinstance(candidate, dict) or candidate.get('candidate_hash') != digest(
            {k: v for k, v in candidate.items() if k != 'candidate_hash'}):
        raise ValueError('candidate content hash mismatch')
    if digest(candidate.get('input')) != digest(record):
        raise ValueError('candidate input mismatch')
    accepted = fit_pair(record)
    if accepted['status'] != 'pair_ready' or digest(accepted['candidate']) != digest(candidate):
        raise ValueError('candidate is not the accepted pair for this input')
    limits = record['constraints']
    readback = limits['realised_tolerance_m']
    gap = limits['spacing_m'] - limits['min_separation_m']
    tolerance = min(limits['lowering_tolerance_m'], readback, gap/2-readback)
    if tolerance <= 1e-8:
        raise ValueError('insufficient spacing/read-back lowering allowance')
    integer(POINT_BUDGET, 'lowering point budget', minimum=2, maximum=20000)
    curves = [_bezier(c['controls']) for c in candidate['centreline']['curves']]
    low, high = record['region']['min_m'], record['region']['max_m']
    elevation = candidate['centreline']['elevation_m']
    ops, certificates, directions, groups = [], [], {}, []
    input_hash = digest(record)
    for track in candidate['tracks']:
        leaves = _offset_enclosures(curves, track['offset_m'], tolerance, max_leaves=POINT_BUDGET-1)
        if len(leaves)+1 > POINT_BUDGET:
            raise ValueError('lowering point budget exhausted')
        error = max(leaf.hull_radius_m for leaf in leaves)
        # Capsule bounds cover the complete smooth offset and its chord. Expand
        # by read-back tolerance so vertex perturbations also stay in the box.
        if error > tolerance or 2*(error+readback) > gap:
            raise ValueError('lowering error exceeds spacing/read-back allowance')
        for leaf in leaves:
            if any(min(leaf.a[i], leaf.b[i])-error-readback < low[i] or
                   max(leaf.a[i], leaf.b[i])+error+readback > high[i] for i in range(2)):
                raise ValueError('lowering error exceeds region allowance')
        if not low[2]+readback <= elevation <= high[2]-readback:
            raise ValueError('read-back exceeds vertical region allowance')
        points = [[*leaves[0].a, elevation]] + [[*leaf.b, elevation] for leaf in leaves]
        parameters = [leaves[0].t0] + [leaf.t1 for leaf in leaves]
        if track['reversed']:
            points.reverse()
            parameters = [1-t for t in reversed(parameters)]
        asset = 'pair:' + digest({'input_hash': input_hash, 'track_id': track['track_id']})
        if asset in snapshot['neighbours']:
            raise ValueError('physical edge collides with protected neighbour')
        payload = dict(asset_key=asset, points=points, start_node=track['start_port'],
                       end_node=track['end_port'], mode='plain')
        op = operation('construct.track_polyline3', payload, [])
        verify_operation(op)
        ops.append(op)
        directions[asset] = dict(track_id=track['track_id'], direction='forward',
                                 reversed_from_centreline=track['reversed'],
                                 start_tangent=tangent_at(candidate, track['track_id'], 0),
                                 end_tangent=tangent_at(candidate, track['track_id'], 1))
        certificates.append(dict(asset_key=asset, error_bound_m=error,
                                 method='analytic offset chord capsules; floating bounds',
                                 parameters=parameters, point_count=len(points), point_budget=POINT_BUDGET,
                                 parent_candidate_hash=candidate['candidate_hash'],
                                 exact_smooth_curvature=False))
        # Coarser enclosures prove clearance of the analytic parents without
        # a quadratic comparison of thousands of rendering vertices.
        groups.append(_offset_enclosures(curves, track['offset_m'], min(.05, gap/8)))
    total_error = max(c['error_bound_m'] for c in certificates) + readback
    if continuous_proximity(*groups, limits['min_separation_m']+2*total_error) is not None:
        raise ValueError('lowered pair separation allowance unresolved')
    edges = [o['payload']['asset_key'] for o in ops]
    nodes = [o['payload'][k] for o in ops for k in ('start_node', 'end_node')]
    if len(ops) != 2 or len(set(edges)) != 2 or len(set(nodes)) != 4:
        raise ValueError('duplicate physical edge or attachment')
    plan = dict(schema_version='0.12.0', environment='mock', input_hash=input_hash,
                candidate_hash=candidate['candidate_hash'], snapshot_id=snapshot['snapshot_id'],
                snapshot_hash=snapshot_hash, expected_world_revision=snapshot['revision'],
                operations=ops, required_capabilities=['construct.track_polyline3',
                    'query.operation_receipt', 'query.realised_geometry'],
                expected_physical_edge_ids=sorted(edges), direction_metadata=directions,
                protected_neighbours=deepcopy(snapshot['neighbours']),
                attachment_ports=deepcopy(snapshot['ports']), edit_region=deepcopy(record['region']),
                lowering_certificates=certificates, realised_tolerance_m=readback,
                real_game_execution_authorised=False,
                scope='two physical mock tracks; protected neighbours outside edit set; no execution')
    plan['plan_hash'] = digest(plan)
    if adapter is not None:
        errors = _preflight_pair(plan, adapter)
        if errors:
            raise ValueError('; '.join(errors))
    return plan


class PairMock:
    """Mutable mock world with independent historical receipts and live tracks.

    Retry means another explicit execute_pair call on this instance. Constructing
    another instance (including in a new process) creates a new mock world.
    """

    def __init__(self, snapshot):
        self._snapshot_hash = _snapshot({'ports': snapshot['ports']}, snapshot)
        self.snapshot = deepcopy(snapshot)
        self.revision = snapshot['revision']
        self.capabilities = manifest()
        self.tracks = deepcopy(snapshot['neighbours'])
        self.nodes = {p['port_id']: deepcopy(p['position_m']) for p in snapshot['ports']}
        for track in self.tracks.values():
            for side, index in (('start_node', 0), ('end_node', -1)):
                key, position = track[side], track['points'][index]
                if key in self.nodes and self.nodes[key] != position:
                    raise ValueError('snapshot node position conflict')
                self.nodes[key] = deepcopy(position)
        self._initial_nodes = deepcopy(self.nodes)
        self._effects = {}
        self.ledger = {}
        self.writes = 0
        self.drop_ack_at = self.fail_at = self.snap_at = None
        self.snap_distance_m = .2
        self.dropped = False

    def receipt(self, operation_id):
        return deepcopy(self.ledger.get(operation_id))

    def apply(self, op, direction, plan_hash):
        verify_operation(op)
        oid = op['operation_id']
        if self.capabilities.get('environment') != 'mock':
            raise ValueError('not a game adapter')
        if oid in self._effects:
            if self._effects[oid] != (plan_hash, digest(op)):
                raise ValueError('effect belongs to a different plan')
            return self.receipt(oid)
        if self.fail_at == self.writes:
            raise RuntimeError('injected construction rejection')
        realised = deepcopy(op['payload'])
        if realised['asset_key'] in self.tracks:
            raise ValueError('physical edge already exists')
        realised.update(deepcopy(direction))
        if self.snap_at == self.writes:
            realised['points'][len(realised['points'])//2][2] += self.snap_distance_m
        self.tracks[realised['asset_key']] = realised
        self.writes += 1
        self.revision += 1
        self._effects[oid] = (plan_hash, digest(op))
        self.ledger[oid] = dict(operation_id=oid, submitted_hash=digest(op),
                                realised=deepcopy(realised), revision=self.revision)
        if self.drop_ack_at == self.writes-1 and not self.dropped:
            self.dropped = True
            raise LostAcknowledgement('effect applied; acknowledgement lost')
        return self.receipt(oid)


def _current_errors(plan, adapter, *, complete=False):
    """Receipts never substitute for current physical and semantic read-back."""
    errors = []
    if adapter.nodes != adapter._initial_nodes:
        errors.append('stable_attachment_or_neighbour_node_changed')
    if any(adapter.nodes.get(p['port_id']) != p['position_m'] for p in plan['attachment_ports']):
        errors.append('authored_attachment_position_mismatch')
    for key, expected in plan['protected_neighbours'].items():
        if adapter.tracks.get(key) != expected:
            errors.append('protected_neighbour_changed:'+key)
    expected_keys = set(plan['protected_neighbours'])
    for op in plan['operations']:
        oid, payload = op['operation_id'], op['payload']
        if oid not in adapter._effects and not complete:
            continue
        key = payload['asset_key']
        expected_keys.add(key)
        expected = dict(deepcopy(payload), **plan['direction_metadata'][key])
        actual = adapter.tracks.get(key)
        if not payload_equal(expected, actual, plan['realised_tolerance_m']):
            errors.append('realised_geometry_or_semantics_mismatch:'+key)
        receipt = adapter.receipt(oid)
        if not receipt or receipt.get('operation_id') != oid or receipt.get('submitted_hash') != digest(op):
            errors.append('receipt_identity_mismatch:'+oid)
    if set(adapter.tracks) != expected_keys:
        errors.append('unexpected_physical_edge_set')
    return errors


def _preflight_pair(plan, adapter):
    if plan.get('plan_hash') != digest({k: v for k, v in plan.items() if k != 'plan_hash'}):
        return ['plan_hash_mismatch']
    if (plan.get('environment') != 'mock' or plan.get('schema_version') != '0.12.0'
            or plan.get('real_game_execution_authorised') is not False):
        return ['unsupported_plan_authority']
    required = ['construct.track_polyline3', 'query.operation_receipt', 'query.realised_geometry']
    if plan['required_capabilities'] != required:
        return ['capability_requirement_mismatch']
    if adapter.capabilities.get('environment') != 'mock' or any(
            adapter.capabilities.get('capabilities', {}).get(k, {}).get('state') != 'demonstrated'
            for k in required):
        return ['capability_not_demonstrated']
    if (digest(adapter.snapshot) != adapter._snapshot_hash
            or adapter._snapshot_hash != plan['snapshot_hash']
            or adapter.snapshot['snapshot_id'] != plan['snapshot_id']
            or adapter.snapshot['revision'] != plan['expected_world_revision']
            or adapter.snapshot['ports'] != plan['attachment_ports']
            or adapter.snapshot['neighbours'] != plan['protected_neighbours']):
        return ['stale_snapshot']
    ops = plan['operations']
    number(plan['realised_tolerance_m'], 'realised tolerance', minimum=0)
    if len(ops) != 2:
        return ['expected_two_tracks']
    ids, keys, nodes = set(), set(), set()
    ports = {p['port_id']: p for p in plan['attachment_ports']}
    for op in ops:
        verify_operation(op)
        p = op['payload']
        if op['kind'] != required[0] or op['dependencies'] or p['mode'] != 'plain':
            return ['unsupported_pair_operation']
        ids.add(op['operation_id'])
        keys.add(p['asset_key'])
        for side, index in (('start', 0), ('end', -1)):
            node = p[side+'_node']
            nodes.add(node)
            if node not in ports or not payload_equal(
                    {'points': [ports[node]['position_m']]}, {'points': [p['points'][index]]}, 1e-7):
                return ['attachment_mismatch']
            if plan['direction_metadata'][p['asset_key']][side+'_tangent'] != ports[node]['forward_unit']:
                # Tangents from analytic evaluation can differ by roundoff.
                if not payload_equal({'points': [ports[node]['forward_unit']]},
                        {'points': [plan['direction_metadata'][p['asset_key']][side+'_tangent']]}, 1e-7):
                    return ['attachment_direction_mismatch']
        if any(not all(plan['edit_region']['min_m'][i] <= point[i] <=
                       plan['edit_region']['max_m'][i] for i in range(3)) for point in p['points']):
            return ['outside_edit_region']
    if (len(ids) != 2 or len(keys) != 2 or len(nodes) != 4 or nodes != set(ports)
            or sorted(keys) != plan['expected_physical_edge_ids']
            or keys != set(plan['direction_metadata']) or keys & set(plan['protected_neighbours'])):
        return ['pair_identity_mismatch']
    own = {op['operation_id']: (plan['plan_hash'], digest(op)) for op in ops}
    if (set(adapter._effects)-ids or set(adapter.ledger) != set(adapter._effects)
            or any(effect != own[oid] for oid, effect in adapter._effects.items())
            or adapter.revision != plan['expected_world_revision']+len(adapter._effects)):
        return ['stale_world_revision_or_unrelated_effect']
    return _current_errors(plan, adapter)


def execute_pair(plan, adapter):
    """Explicit execution/retry with reconciliation, never compensation or rollback."""
    out = dict(plan_hash=plan.get('plan_hash'), environment='mock', trace=[],
               game_constructed=False, real_game_constructed=False, rollback_attempted=False,
               recovery='retain visible effects; no automatic resume or rollback',
               world_scope='in memory only; new process means new mock world')
    recovered = 0

    def result(status, **details):
        return dict(out, status=status, writes=adapter.writes,
                    acknowledgements_reconciled=recovered, **details)

    try:
        errors = _preflight_pair(plan, adapter)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        errors = ['invalid_plan_or_world:'+str(exc)]
    if errors:
        return result('preflight_blocked', reasons=errors)
    for op in plan['operations']:
        try:
            try:
                receipt = adapter.apply(op, plan['direction_metadata'][op['payload']['asset_key']], plan['plan_hash'])
            except LostAcknowledgement:
                recovered += 1
                receipt = adapter.receipt(op['operation_id'])
                if receipt is None:
                    return result('uncertain_effect_stop')
            if (not isinstance(receipt, dict) or receipt.get('operation_id') != op['operation_id']
                    or receipt.get('submitted_hash') != digest(op)):
                return result('receipt_identity_mismatch')
            errors = _current_errors(plan, adapter)
            if errors:
                return result('realised_geometry_or_semantics_mismatch', reasons=errors)
        except (RuntimeError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
            return result('partial_failure', reason=str(exc))
        out['trace'].append(dict(operation_id=op['operation_id'], verified=True))
    errors = _current_errors(plan, adapter, complete=True)
    return result('realised_geometry_or_semantics_mismatch' if errors else 'mock_verified', reasons=errors)
