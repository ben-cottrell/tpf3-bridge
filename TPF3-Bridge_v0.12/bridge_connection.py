"""Validate local, level plain-track connection inputs; no game observations."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re


class UnsupportedConnection(ValueError):
    """A well-formed input requests a condition outside the local model."""


def _fields(value, names, path):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ValueError(f'{path}: missing or unknown fields, or not an object')


def _number(value, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{path}: expected a finite number')
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f'{path}: expected a finite number')


def _id(value, path, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}', value) is None:
        raise ValueError(f'{path}: expected a contract identifier')


def _vec3(value, path):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{path}: expected three numeric components')
    for component in value:
        _number(component, path)
        if not -1e9 <= component <= 1e9:
            raise ValueError(f'{path}: component outside Vec3 bounds')


def validate_connection(record):
    """Return the equal input record without mutation, normalization or inference.

    Unit tangent length allows 1e-9 absolute roundoff. Elevation equality,
    horizontal tangents, zero grade and zero cant are exact requirements.
    Region containment is a later geometric check, not input validation.
    Provenance is caller-supplied metadata, never verified game evidence.
    """
    _fields(record, 'schema_version kind coordinate_frame start end region constraints provenance', 'connection')
    if record['schema_version'] != '0.12.0' or record['kind'] != 'plain_track_connection':
        raise ValueError('connection: unsupported schema_version or kind')

    frame = record['coordinate_frame']
    _fields(frame, 'length_unit up_axis handedness transform_ref transform_probe_ref', 'coordinate_frame')
    if (frame['length_unit'], frame['up_axis'], frame['handedness']) != ('m', 'z', 'right'):
        raise UnsupportedConnection('coordinate_frame: requires metres, z-up and right-handed coordinates')
    _id(frame['transform_ref'], 'coordinate_frame.transform_ref')
    _id(frame['transform_probe_ref'], 'coordinate_frame.transform_probe_ref', nullable=True)

    for name in ('start', 'end'):
        port = record[name]
        _fields(port, 'port_id position_m forward_unit grade role native_entity_ref native_port_ref', name)
        _id(port['port_id'], name + '.port_id')
        for key in ('native_entity_ref', 'native_port_ref'):
            _id(port[key], name + '.' + key, nullable=True)
        if port['role'] not in ('entry', 'exit', 'bidirectional'):
            raise ValueError(f'{name}.role: invalid Port role')
        _vec3(port['position_m'], name + '.position_m')
        _vec3(port['forward_unit'], name + '.forward_unit')
        tangent = port['forward_unit']
        if not math.isclose(math.hypot(*tangent), 1.0, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f'{name}.forward_unit: expected a unit tangent')
        _number(port['grade'], name + '.grade')
        if tangent[2] != 0 or port['grade'] != 0:
            raise UnsupportedConnection(f'{name}: only horizontal tangents and zero grade are supported')
    if record['start']['position_m'][2] != record['end']['position_m'][2]:
        raise UnsupportedConnection('connection: endpoint elevations must be equal')

    region = record['region']
    _fields(region, 'min_m max_m', 'region')
    for key in ('min_m', 'max_m'):
        _vec3(region[key], 'region.' + key)
    if any(low > high for low, high in zip(region['min_m'], region['max_m'])):
        raise ValueError('region: min_m must not exceed max_m on any axis')

    constraints = record['constraints']
    _fields(constraints, 'min_radius_m max_length_m cant_mm max_candidates curvature_depth', 'constraints')
    for key in ('min_radius_m', 'max_length_m', 'cant_mm'):
        _number(constraints[key], 'constraints.' + key)
    for key in ('min_radius_m', 'max_length_m'):
        if constraints[key] <= 0:
            raise ValueError(f'constraints.{key}: must be positive')
    if constraints['cant_mm'] != 0:
        raise UnsupportedConnection('constraints.cant_mm: only zero cant is supported')
    for key, maximum in (('max_candidates', 400), ('curvature_depth', 10)):
        value = constraints[key]
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f'constraints.{key}: expected an integer in 0..{maximum}')

    provenance = record['provenance']
    _fields(provenance, 'source_refs project_choices assumptions', 'provenance')
    for key, values in provenance.items():
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f'provenance.{key}: expected a list of nonempty strings')
    return record


def load_connection(path):
    """Read strict UTF-8 JSON from a path and validate it without modifying it."""
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
    return validate_connection(record)


def _connection_region_bound(curve, low, high, depth=10):
    """Closed control hull proof; unresolved subdivision leaves fail."""
    bounds = curve.bounds()
    if all(low[i] <= bounds[i] and bounds[i+2] <= high[i] for i in range(2)):
        return {'pass': True, 'bounds_m': list(bounds)}
    if depth == 0 or any(not low[i] <= curve.controls[j][i] <= high[i]
                         for j in (0, -1) for i in range(2)):
        return {'pass': False, 'unresolved_bounds_m': list(bounds)}
    children = [_connection_region_bound(c, low, high, depth-1) for c in curve.split()]
    return {'pass': all(c['pass'] for c in children), 'children': children}


def fit_connection(record):
    """Complete finite search using floating-point kernel bounds, not game evidence.

    Failure describes only this finite family, never global impossibility.
    """
    import sys
    proof = str(Path(__file__).resolve().parent / 'proof')
    if proof not in sys.path:
        sys.path.insert(0, proof)
    from railgeom.curves import Bezier, line, flatten, join_check
    from railbranch.geometry import hermite

    result = {'status': None, 'candidate': None, 'evaluated': 0,
              'search_status': 'not_started', 'grid': [], 'checks': [],
              'candidate_checks': [], 'game_constructed': False,
              'scope': 'finite family only; no global impossibility claim'}

    def finish(status, reason=None):
        result['status'] = status
        if reason is not None:
            result['checks'].append({'pass': False, 'reason': reason})
        return result

    try:
        validate_connection(record)
    except UnsupportedConnection as exc:
        return finish('unsupported_input', str(exc))
    except (ValueError, TypeError, OverflowError) as exc:
        return finish('invalid_input', str(exc))
    start, end = record['start'], record['end']
    a, b = start['position_m'][:2], end['position_m'][:2]
    ux, uy = start['forward_unit'][:2]
    magnitude = math.hypot(ux, uy)
    ux, uy = ux/magnitude, uy/magnitude
    dx, dy = b[0]-a[0], b[1]-a[1]
    span, lateral = dx*ux+dy*uy, -dx*uy+dy*ux
    ex, ey = end['forward_unit'][:2]
    forward, side = ex*ux+ey*uy, -ex*uy+ey*ux
    heading = math.atan2(side, forward)
    result['frame'] = {'origin_m': a, 'forward_unit': [ux, uy],
                       'end_local_m': [span, lateral], 'end_heading_rad': heading}
    if span <= 0 or abs(heading) > math.pi/4 + 1e-15:
        return finish('unsupported_input', 'requires positive forward span and heading within +/-45 degrees')
    if max(map(abs, [*a, *b])) > 1e7 or span <= 1e-7:
        return finish('unsupported_input', 'outside kernel coordinate or nondegeneracy bounds')
    low, high = record['region']['min_m'], record['region']['max_m']
    inside = all(low[i] <= p[i] <= high[i]
                 for p in (start['position_m'], end['position_m']) for i in range(3))
    result['checks'].append({'name': 'endpoint_region', 'pass': inside})
    if not inside:
        return finish('failed_checks')
    slope = side/forward
    grid = [{'kind': 'line'}, {'kind': 'quintic'}]
    for fraction in (0.4, 0.5, 0.6):
        for offset in (-0.1, 0.0, 0.1):
            for adjustment in (-0.25, 0.0, 0.25):
                grid.append({'kind': 'two_quintics',
                             'midpoint_m': [span*fraction, lateral*fraction+offset*span],
                             'midpoint_slope': lateral/span+adjustment})
    result['grid'] = grid
    limits = record['constraints']
    result['required_candidates'] = len(grid)
    result['max_candidates'] = limits['max_candidates']
    accepted = []
    # Scale construction coordinates only; map geometry and constraints stay in metres.
    scale = max(1., span/1e6, abs(lateral)/1e6)
    local_end = (span/scale, lateral/scale)

    def map_curve(curve, first, last):
        controls = [(a[0]+scale*(ux*x-uy*y), a[1]+scale*(uy*x+ux*y)) for x, y in curve.controls]
        if first:
            controls[0] = tuple(a)
        if last:
            controls[-1] = tuple(b)
        return Bezier(tuple(controls))

    for index, entry in enumerate(grid[:limits['max_candidates']]):
        row = {'index': index, 'pass': False, 'checks': {}}
        result['candidate_checks'].append(row)
        result['evaluated'] += 1
        checks = row['checks']
        try:
            if entry['kind'] == 'line':
                local = [line((0., 0.), local_end)]
            elif entry['kind'] == 'quintic':
                local = [hermite((0., 0.), local_end, 0., slope)]
            else:
                midpoint = tuple(v/scale for v in entry['midpoint_m'])
                mid_slope = entry['midpoint_slope']
                local = [hermite((0., 0.), midpoint, 0., mid_slope),
                         hermite(midpoint, local_end, mid_slope, slope)]
            curves = [map_curve(c, i == 0, i == len(local)-1) for i, c in enumerate(local)]
            row['curves'] = [{'controls': [list(p) for p in c.controls]} for c in curves]
            projections = [min(v[0]*ux+v[1]*uy for v in c.derivative_controls()) for c in curves]
            checks['regularity'] = {'pass': min(projections) > 1e-8,
                                    'forward_derivative_lower_m': projections}
            ends = []
            for curve, t, port in ((curves[0], 0, start), (curves[-1], 1, end)):
                position = math.dist(curve.at(t), port['position_m'][:2])
                tangent = math.dist(curve.tangent(t), port['forward_unit'][:2])
                curvature = abs(curve.curvature(t))
                ends.append({'position_error_m': position, 'unit_tangent_error': tangent,
                             'curvature_per_m': curvature,
                             'pass': position <= 1e-6 and tangent <= 1e-7 and curvature <= 1e-7})
            checks['endpoints'] = {'pass': all(c['pass'] for c in ends), 'ends': ends}
            joins = [join_check(c, d) for c, d in zip(curves, curves[1:])]
            checks['joins'] = {'pass': all(j['pass'] for j in joins), 'joins': joins}
            regions = [_connection_region_bound(c, low, high) for c in curves]
            checks['region'] = {'pass': all(r['pass'] for r in regions), 'pieces': regions}
            upper = [c.curvature_upper(limits['curvature_depth']) for c in curves]
            checks['curvature'] = {'pass': max(upper) <= 1/limits['min_radius_m'],
                                   'upper_per_m': upper, 'limit_per_m': 1/limits['min_radius_m']}
            leaves = [leaf for c in curves for leaf in flatten(c)]
            lower_length = sum(leaf.lower_length_m for leaf in leaves)
            upper_length = sum(leaf.upper_length_m for leaf in leaves)
            checks['length'] = {'pass': upper_length <= limits['max_length_m'],
                                'lower_m': lower_length, 'upper_m': upper_length,
                                'limit_m': limits['max_length_m'], 'leaf_count': len(leaves)}
            row['pass'] = all(check['pass'] for check in checks.values())
            if row['pass']:
                accepted.append((upper_length, index, row['curves']))
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            checks['kernel'] = {'pass': False, 'reason': str(exc)}
    if result['evaluated'] != len(grid):
        result['search_status'] = 'budget_exhausted'
        return finish('incomplete_search')
    result['search_status'] = 'complete'
    if not accepted:
        return finish('no_accepted_candidate')
    _, selected, curves = min(accepted, key=lambda item: item[:2])
    result['selected_index'] = selected
    result['candidate'] = {'curves': curves, 'elevation_m': start['position_m'][2]}
    return finish('connection_ready')
