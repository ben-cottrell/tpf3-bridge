"""Strict explicit two-track input; authored metadata is not game evidence."""
from __future__ import annotations

import json
import copy
import hashlib
import math
from pathlib import Path

from bridge_connection import (
    UnsupportedConnection, _fields, _id, _number, validate_connection,
)


class UnsupportedPair(UnsupportedConnection):
    """A pair requests an arrangement outside the supported local model."""


def validate_pair(record):
    """Return the input unchanged, preserving explicit pairing and travel tangents.

    Shared single-connection validation supplies Port, frame, region, provenance
    and numerical limits. All four elevations must match exactly. Compatibility
    of endpoint directions and spacing belongs to the later geometry stage.
    """
    _fields(record, 'schema_version kind coordinate_frame ports connections region constraints provenance', 'pair')
    if record['schema_version'] != '0.12.0' or record['kind'] != 'double_track_connection':
        raise ValueError('pair: unsupported schema_version or kind')
    ports = record['ports']
    connections = record['connections']
    if not isinstance(ports, list) or len(ports) != 4:
        raise ValueError('ports: expected exactly four ports')
    if not isinstance(connections, list) or len(connections) != 2:
        raise ValueError('connections: expected exactly two connections')
    by_id = {}
    for port in ports:
        _fields(port, 'port_id position_m forward_unit grade role native_entity_ref native_port_ref', 'port')
        _id(port['port_id'], 'port.port_id')
        if port['port_id'] in by_id:
            raise ValueError('ports: duplicate port_id')
        by_id[port['port_id']] = port
    tracks, used = set(), set()
    for connection in connections:
        _fields(connection, 'track_id start_port end_port', 'connection')
        for key in ('track_id', 'start_port', 'end_port'):
            _id(connection[key], 'connection.' + key)
        if connection['track_id'] in tracks:
            raise ValueError('connections: duplicate track_id')
        tracks.add(connection['track_id'])
        for key in ('start_port', 'end_port'):
            port_id = connection[key]
            if port_id not in by_id or port_id in used:
                raise ValueError('connections: unknown or reused port')
            used.add(port_id)

    constraints = record['constraints']
    single_limits = 'min_radius_m max_length_m cant_mm max_candidates curvature_depth'
    pair_limits = 'spacing_m min_separation_m lowering_tolerance_m realised_tolerance_m'
    _fields(constraints, single_limits + ' ' + pair_limits, 'constraints')
    for key in pair_limits.split():
        _number(constraints[key], 'constraints.' + key)
        if constraints[key] <= 0:
            raise ValueError(f'constraints.{key}: must be positive')

    for connection in connections:
        single = {key: record[key] for key in ('schema_version', 'coordinate_frame', 'region', 'provenance')}
        single.update(kind='plain_track_connection',
                      start=by_id[connection['start_port']],
                      end=by_id[connection['end_port']],
                      constraints={key: constraints[key] for key in single_limits.split()})
        try:
            validate_connection(single)
        except UnsupportedConnection as exc:
            raise UnsupportedPair(str(exc)) from exc
    if any(port['position_m'][2] != ports[0]['position_m'][2] for port in ports[1:]):
        raise UnsupportedPair('pair: all four endpoint elevations must be equal')
    return record


def load_pair(path):
    """Read strict UTF-8 JSON, rejecting duplicate keys at every object level."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'nonfinite JSON constant: {value}')

    record = json.loads(Path(path).read_text(encoding='utf-8'),
                        object_pairs_hook=unique, parse_constant=invalid_constant)
    return validate_pair(record)


def _bezier(controls):
    # Same local proof kernel used by L07; no optional dependency or service.
    import sys
    proof = str(Path(__file__).resolve().parent / 'proof')
    if proof not in sys.path:
        sys.path.insert(0, proof)
    from railgeom.curves import Bezier
    return Bezier(tuple(tuple(p) for p in controls))


def _evaluation(candidate, track_id, t):
    _number(t, 't')
    if not 0 <= t <= 1:
        raise ValueError('t outside [0,1]')
    tracks = [track for track in candidate['tracks'] if track['track_id'] == track_id]
    if len(tracks) != 1:
        raise ValueError('unknown track_id')
    track = tracks[0]
    u = 1-t if track['reversed'] else t
    pieces = candidate['centreline']['curves']
    index = min(int(u*len(pieces)), len(pieces)-1)
    curve = _bezier(pieces[index]['controls'])
    return curve, u*len(pieces)-index, track


def point_at(candidate, track_id, t):
    """Analytic normal offset, parameterised in the referenced travel direction."""
    curve, u, track = _evaluation(candidate, track_id, t)
    x, y = curve.at(u)
    tx, ty = curve.tangent(u)
    d = track['offset_m']
    return [x-d*ty, y+d*tx, candidate['centreline']['elevation_m']]


def tangent_at(candidate, track_id, t):
    """Unit travel tangent; positive offset regularity is certified by fit_pair."""
    curve, u, track = _evaluation(candidate, track_id, t)
    sign = -1 if track['reversed'] else 1
    tx, ty = curve.tangent(u)
    return [sign*tx, sign*ty, 0.0]


class _PairBudget(ValueError):
    pass


def _offset_enclosures(curves, offset, tolerance, max_leaves=2048):
    """Enclose entire offsets in chord capsules using derivative convex cones.

    A positive derivative projection confines all unit tangents to the cone of
    the derivative controls. Their maximum distance from the initial tangent
    bounds normal variation. Twice this variation covers both the curve's
    displacement and the shifted chord. These are proof leaves, not lowering.
    """
    from railgeom.curves import Leaf, point_segment
    leaves = []
    stack = [(c, i/len(curves), (i+1)/len(curves), 0)
             for i, c in reversed(list(enumerate(curves)))]
    while stack:
        c, t0, t1, depth = stack.pop()
        u = c.tangent(0)
        derivatives = c.derivative_controls()
        positive = all(v[0]*u[0]+v[1]*u[1] > 1e-12 for v in derivatives)
        variation = (max(math.dist(u, (v[0]/math.hypot(*v), v[1]/math.hypot(*v)))
                         for v in derivatives) if positive else 2.0)
        radius = max(point_segment(p, c.controls[0], c.controls[-1]) for p in c.controls)
        radius += 2*abs(offset)*variation + 1e-8
        if positive and radius <= tolerance:
            points = []
            for t in (0, 1):
                x, y = c.at(t); tx, ty = c.tangent(t)
                points.append((x-offset*ty, y+offset*tx))
            leaves.append(Leaf(t0, t1, *points, radius, 0.0, 0.0))
        else:
            if depth >= 20 or len(leaves)+len(stack)+2 > max_leaves:
                raise _PairBudget('offset enclosure subdivision budget exhausted')
            a, b = c.split(); mid = (t0+t1)/2
            stack.extend(((b, mid, t1, depth+1), (a, t0, mid, depth+1)))
    return tuple(leaves)


def _pair_certificate(curves, row, tracks, record):
    from railgeom.curves import continuous_proximity
    limits = record['constraints']
    h = limits['spacing_m']/2
    k = max(row['checks']['curvature']['upper_per_m'])
    factor = 1-h*k
    checks = {'regularity': {'pass': factor > 0, 'factor_lower': factor},
              'ordering': {'pass': factor > 0, 'signed_offsets_m': [t['offset_m'] for t in tracks],
                           'method': 'fixed normal offsets; positive forward derivative and offset metric'},
              'radius': {'pass': factor > 0 and k <= factor/limits['min_radius_m'],
                         'centre_curvature_upper_per_m': k,
                         'offset_curvature_upper_per_m': k/factor if factor > 0 else None}}
    if not all(c['pass'] for c in checks.values()):
        return checks
    joins = []
    for track in tracks:
        d = track['offset_m']
        for a, b in zip(curves, curves[1:]):
            ua, ub = a.tangent(1), b.tangent(0)
            pa, pb = a.at(1), b.at(0)
            position = math.dist((pa[0]-d*ua[1], pa[1]+d*ua[0]),
                                 (pb[0]-d*ub[1], pb[1]+d*ub[0]))
            ka, kb = a.curvature(1), b.curvature(0)
            curvature = abs(ka/(1-d*ka)-kb/(1-d*kb))
            tangent = math.dist(ua, ub)
            joins.append({'track_id': track['track_id'], 'position_error_m': position,
                          'unit_tangent_error': tangent, 'curvature_error_per_m': curvature,
                          'pass': position <= 1e-6 and tangent <= 1e-7 and curvature <= 1e-7})
    checks['joins'] = {'pass': all(j['pass'] for j in joins), 'joins': joins}
    lengths = row['checks']['length']
    # For regular planar offsets ds_d=(1-d*k)ds, integral k ds is
    # the endpoint heading change. L07's positive fixed-axis projection rules
    # out winding; summing signed piece angles is therefore unambiguous.
    turn = sum(math.atan2(c.tangent(0)[0]*c.tangent(1)[1]-c.tangent(0)[1]*c.tangent(1)[0],
                          sum(a*b for a, b in zip(c.tangent(0), c.tangent(1)))) for c in curves)
    track_lengths = [{'track_id': t['track_id'],
                      'lower_m': max(0, lengths['lower_m']-t['offset_m']*turn-1e-8),
                      'upper_m': lengths['upper_m']-t['offset_m']*turn+1e-8} for t in tracks]
    checks['length'] = {'pass': all(t['upper_m'] <= limits['max_length_m'] for t in track_lengths),
                        'tracks': track_lengths, 'signed_heading_change_rad': turn}
    gap = limits['spacing_m']-limits['min_separation_m']
    straight = all(len(c.controls) == 2 for c in curves)
    if gap < 0 or (gap == 0 and not straight):
        checks['separation'] = {'pass': False, 'reason': 'no positive enclosure clearance allowance'}
        return checks
    tolerance = min(.05, gap/8) if gap > 0 else .05
    leaves = [_offset_enclosures(curves, t['offset_m'], tolerance) for t in tracks]
    contact = (None if straight else continuous_proximity(*leaves, limits['min_separation_m']))
    checks['separation'] = {'pass': contact is None,
                            'method': 'exact parallel line distance' if straight else 'all offset chord capsule pairs',
                            'min_separation_m': limits['min_separation_m'], 'possible_contact': contact,
                            'leaf_counts': list(map(len, leaves)),
                            'max_enclosure_radius_m': max(l.hull_radius_m for group in leaves for l in group)}
    low, high = record['region']['min_m'], record['region']['max_m']
    # Straight offsets have exact line hulls, including boundary endpoints.
    if straight:
        region_pass = all(low[i] <= p[i] <= high[i] for group in leaves for l in group
                          for p in (l.a, l.b) for i in range(2))
    else:
        region_pass = all(low[i] <= min(l.a[i], l.b[i])-l.hull_radius_m and
                          max(l.a[i], l.b[i])+l.hull_radius_m <= high[i]
                          for group in leaves for l in group for i in range(2))
    checks['region'] = {'pass': region_pass, 'method': 'continuous offset capsule hulls (exact straight hulls)'}
    return checks


def fit_pair(record):
    """Exhaust L07's finite centreline family, checking BOTH analytic offsets.

    Bounds use floating arithmetic with kernel allowances, not formal interval
    arithmetic. Unresolved hard checks fail; a partial search never selects.
    """
    from bridge_connection import fit_connection
    result = {'status': None, 'candidate': None, 'evaluated': 0, 'grid': [],
              'candidate_checks': [], 'checks': [], 'search_status': 'not_started',
              'game_constructed': False, 'scope': 'finite normal-offset family only; no global impossibility claim'}

    def finish(status, reason=None):
        result['status'] = status
        if reason:
            result['checks'].append({'pass': False, 'reason': reason})
        return result

    try:
        validate_pair(record)
    except UnsupportedConnection as exc:
        return finish('unsupported_input', str(exc))
    except (ValueError, TypeError, OverflowError) as exc:
        return finish('invalid_input', str(exc))
    ports = {p['port_id']: p for p in record['ports']}
    first, second = record['connections']
    a = [ports[first[key]] for key in ('start_port', 'end_port')]
    limits = record['constraints']
    spacing = limits['spacing_m']
    compatible = None
    for reverse in (False, True):
        keys = ('end_port', 'start_port') if reverse else ('start_port', 'end_port')
        b = [ports[second[key]] for key in keys]
        offsets = []
        for pa, pb in zip(a, b):
            u = pa['forward_unit'][:2]; mag = math.hypot(*u); u = [v/mag for v in u]
            v = [( -1 if reverse else 1)*x for x in pb['forward_unit'][:2]]
            delta = [pb['position_m'][i]-pa['position_m'][i] for i in range(2)]
            signed = -u[1]*delta[0]+u[0]*delta[1]
            if (math.dist(u, v) > 1e-7 or abs(sum(x*y for x, y in zip(u, delta))) > 1e-6
                    or abs(abs(signed)-spacing) > 1e-6):
                break
            offsets.append(signed)
        if len(offsets) == 2 and offsets[0]*offsets[1] > 0:
            compatible = (reverse, b, math.copysign(spacing/2, offsets[0]))
            break
    if compatible is None:
        return finish('unsupported_input', 'requires equal normal spacing, parallel endpoint tangents and uncrossed explicit pairing')
    reverse, b, half = compatible
    low, high = record['region']['min_m'], record['region']['max_m']
    if not all(low[i] <= p['position_m'][i] <= high[i] for p in ports.values() for i in range(3)):
        return finish('failed_checks', 'pair endpoint outside region')
    single = {key: copy.deepcopy(record[key]) for key in ('schema_version', 'coordinate_frame', 'region', 'provenance')}
    single.update(kind='plain_track_connection', constraints={key: limits[key] for key in
                  ('min_radius_m', 'max_length_m', 'cant_mm', 'max_candidates', 'curvature_depth')})
    for name, pa, pb in zip(('start', 'end'), a, b):
        single[name] = copy.deepcopy(pa)
        single[name]['position_m'] = [(x+y)/2 for x, y in zip(pa['position_m'], pb['position_m'])]
    centre = fit_connection(single)
    for key in ('evaluated', 'grid', 'search_status', 'required_candidates', 'max_candidates'):
        if key in centre:
            result[key] = centre[key]
    # Keep all L07 evidence, but its centre-only winner is not a pair selection.
    result['centreline_search'] = {key: value for key, value in centre.items()
                                   if key not in ('candidate', 'selected_index')}
    tracks = [dict(first, offset_m=-half, reversed=False), dict(second, offset_m=half, reversed=reverse)]
    accepted = []
    exhausted = False
    for row in centre['candidate_checks']:
        pair_row = {'index': row['index'], 'pass': False, 'centreline_pass': row['pass'], 'checks': {}}
        result['candidate_checks'].append(pair_row)
        if 'subdivision_budget_exhausted' in row['checks'].get('kernel', {}).get('reason', ''):
            exhausted = True
            pair_row['checks']['budget'] = row['checks']['kernel']
        if not row['pass']:
            continue
        try:
            curves = [_bezier(c['controls']) for c in row['curves']]
            checks = _pair_certificate(curves, row, tracks, record)
            geometry = {'centreline': {'curves': row['curves'], 'elevation_m': a[0]['position_m'][2]},
                        'tracks': tracks}
            ends = []
            for track in tracks:
                for t, key in ((0, 'start_port'), (1, 'end_port')):
                    port = ports[track[key]]
                    position_error = math.dist(point_at(geometry, track['track_id'], t), port['position_m'])
                    tangent_error = math.dist(tangent_at(geometry, track['track_id'], t), port['forward_unit'])
                    curve, u, _ = _evaluation(geometry, track['track_id'], t)
                    curvature = curve.curvature(u)
                    metric = 1-track['offset_m']*curvature
                    offset_curvature = abs(curvature/metric) if metric > 0 else None
                    ends.append({'position_error_m': position_error, 'unit_tangent_error': tangent_error,
                                 'offset_curvature_per_m': offset_curvature,
                                 'pass': position_error <= 1e-6 and tangent_error <= 1e-7 and
                                         offset_curvature is not None and offset_curvature <= 1e-7})
            checks['endpoints'] = {'pass': all(e['pass'] for e in ends), 'ends': ends,
                                   'zero_curvature': row['checks']['endpoints']}
            pair_row['checks'] = checks
            pair_row['pass'] = all(c['pass'] for c in checks.values())
            if pair_row['pass']:
                accepted.append((max(t['upper_m'] for t in checks['length']['tracks']), row['index'], row))
        except _PairBudget as exc:
            exhausted = True
            pair_row['checks']['budget'] = {'pass': False, 'reason': str(exc)}
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            pair_row['checks']['kernel'] = {'pass': False, 'reason': str(exc)}
    if centre['status'] == 'incomplete_search' or exhausted:
        result['search_status'] = 'budget_exhausted'
        return finish('incomplete_search')
    if centre['status'] not in ('connection_ready', 'no_accepted_candidate'):
        return finish(centre['status'])
    if not accepted:
        return finish('no_accepted_candidate')
    _, selected, row = min(accepted, key=lambda item: item[:2])
    result['selected_index'] = selected
    candidate = {'model': 'analytic_bezier_normal_offsets',
                 'centreline': {'curves': row['curves'], 'elevation_m': a[0]['position_m'][2]},
                 'tracks': tracks, 'pair_certificates': result['candidate_checks'][selected]['checks'],
                 'input': copy.deepcopy(record), 'provenance': copy.deepcopy(record['provenance']),
                 'search': {'status': 'complete', 'evaluated': result['evaluated'], 'grid': result['grid'],
                            'selected_index': selected},
                 'numerics': {'arithmetic': 'floating analytical bounds; not interval arithmetic',
                              'position_allowance_m': 1e-6, 'tangent_allowance': 1e-7,
                              'endpoint_curvature_allowance_per_m': 1e-7,
                              'enclosure_allowance_m': 1e-8, 'offset_leaf_budget': 2048,
                              'offset_depth_budget': 20}}
    candidate['candidate_hash'] = hashlib.sha256(json.dumps(candidate, sort_keys=True,
                                            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    result['candidate'] = candidate
    return finish('pair_ready')
