"""Frozen host checks for the approved L06-L08 batch; no workers or game calls."""
import argparse
import copy
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'proof')]


def fixture():
    def port(name, position, forward, role):
        return dict(port_id=name, position_m=position, forward_unit=forward,
                    grade=0, role=role, native_entity_ref=None, native_port_ref=None)
    return dict(schema_version='0.12.0', kind='plain_track_connection',
                coordinate_frame=dict(length_unit='m', up_axis='z', handedness='right',
                                      transform_ref='local-offline', transform_probe_ref=None),
                start=port('start', [0, 0, 0], [1, 0, 0], 'entry'),
                end=port('end', [500, 0, 0], [1, 0, 0], 'exit'),
                region=dict(min_m=[-2000, -2000, -1], max_m=[2000, 2000, 1]),
                constraints=dict(min_radius_m=80, max_length_m=2000, cant_mm=0,
                                 max_candidates=100, curvature_depth=6),
                provenance=dict(source_refs=[], project_choices=['offline design constraints'],
                                assumptions=['level plain track; no terrain or game evidence']))


def expect_invalid(module, record):
    try:
        module.validate_connection(record)
    except ValueError:
        return
    raise AssertionError('invalid or unsupported input was accepted')


def input_checks(module):
    record = fixture()
    before = copy.deepcopy(record)
    assert module.validate_connection(record) == record and record == before
    mutations = [('start', 'forward_unit', [0, 0, 0]), ('end', 'position_m', [500, 0, 1]),
                 ('end', 'grade', 0.01), ('constraints', 'cant_mm', 1),
                 ('constraints', 'min_radius_m', -1), ('constraints', 'min_radius_m', True),
                 ('constraints', 'max_candidates', 401), ('constraints', 'curvature_depth', 11),
                 ('coordinate_frame', 'length_unit', 'ft'), ('start', 'position_m', [float('nan'), 0, 0]),
                 ('end', 'forward_unit', [2, 0, 0]), ('region', 'max_m', [-3000, 0, 0])]
    for group, key, value in mutations:
        bad = copy.deepcopy(record)
        bad[group][key] = value
        expect_invalid(module, bad)
    bad = copy.deepcopy(record)
    bad['unrecognised'] = True
    expect_invalid(module, bad)


def independent_geometry(record, result):
    from railgeom.curves import Bezier, distance, flatten, join_check
    assert result['status'] == 'connection_ready', result
    candidate = result['candidate']
    assert candidate['elevation_m'] == record['start']['position_m'][2]
    curves = [Bezier(tuple(tuple(p) for p in c['controls'])) for c in candidate['curves']]
    assert 1 <= len(curves) <= 2
    assert distance(curves[0].at(0), tuple(record['start']['position_m'][:2])) < 1e-6
    assert distance(curves[-1].at(1), tuple(record['end']['position_m'][:2])) < 1e-6
    for curve, t, endpoint in [(curves[0], 0, 'start'), (curves[-1], 1, 'end')]:
        assert distance(curve.tangent(t), tuple(record[endpoint]['forward_unit'][:2])) < 1e-7
    for a, b in zip(curves, curves[1:]):
        assert distance(a.at(1), b.at(0)) < 1e-6
        assert distance(a.tangent(1), b.tangent(0)) < 1e-7
        assert abs(a.curvature(1) - b.curvature(0)) < 1e-7
    upper_length = 0
    for curve in curves:
        assert curve.curvature_upper(record['constraints']['curvature_depth']) <= 1 / record['constraints']['min_radius_m']
        upper_length += sum(leaf.upper_length_m for leaf in flatten(curve))
        # Independent dense witnesses supplement the required continuous worker bounds.
        for i in range(201):
            point = curve.at(i / 200)
            for axis in range(2):
                assert record['region']['min_m'][axis] - 1e-7 <= point[axis] <= record['region']['max_m'][axis] + 1e-7
    assert upper_length <= record['constraints']['max_length_m']


def geometry_checks(module):
    record = fixture()
    independent_geometry(record, module.fit_connection(record))
    record['end']['position_m'][1] = 100
    record['end']['forward_unit'] = [math.cos(math.pi / 6), 0.5, 0]
    independent_geometry(record, module.fit_connection(record))
    angle = 1.1
    c, s = math.cos(angle), math.sin(angle)
    for end in ('start', 'end'):
        x, y, z = record[end]['position_m']
        record[end]['position_m'] = [100 + c*x - s*y, -200 + s*x + c*y, z]
        x, y, z = record[end]['forward_unit']
        record[end]['forward_unit'] = [c*x - s*y, s*x + c*y, z]
    independent_geometry(record, module.fit_connection(record))
    tight = fixture()
    tight['end']['position_m'] = [10, 10, 0]
    tight['end']['forward_unit'] = [math.cos(math.pi / 6), 0.5, 0]
    tight['constraints']['min_radius_m'] = 10000
    assert module.fit_connection(tight)['status'] == 'no_accepted_candidate'
    outside = fixture()
    outside['region']['max_m'][0] = 100
    assert module.fit_connection(outside)['status'] == 'failed_checks'
    exhausted = fixture()
    exhausted['constraints']['max_candidates'] = 0
    result = module.fit_connection(exhausted)
    assert result['status'] == 'incomplete_search' and result.get('candidate') is None
    unsupported = fixture()
    unsupported['end']['forward_unit'] = [0, 1, 0]
    assert module.fit_connection(unsupported)['status'] == 'unsupported_input'


def application_checks(folder):
    import bridge_app
    source = folder / 'input.json'
    source.write_text(json.dumps(fixture()), encoding='utf-8')
    def cli(*args, ok=True):
        p = subprocess.run([sys.executable, str(ROOT / 'bridge_cli.py'), *map(str, args)],
                           cwd=ROOT, capture_output=True, timeout=60)
        assert (p.returncode == 0) == ok, p.stderr.decode(errors='replace')
        assert len(p.stdout) <= 4096
        value = json.loads(p.stdout)
        assert value['game_constructed'] is False
        return value
    out = folder / 'cli'
    assert cli('connect', '--input', source, '--output', out)['status'] == 'connection_ready'
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
    assert cli('status', '--run', out)['status'] == 'connection_ready'
    assert cli('verify', '--run', out)['status'] == 'integrity_verified'
    cli('connect', '--input', source, '--output', out, ok=False)
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
    (out / 'candidate.json').write_text('{}', encoding='utf-8')
    assert 'candidate.json' in cli('verify', '--run', out, ok=False)['changed_files']
    assert bridge_app.connect(source, folder / 'api')['status'] == 'connection_ready'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True, choices=['L06', 'L07', 'L08'])
    task = parser.parse_args().task
    folder = ROOT / '.local_runs' / ('batch_connection_' + uuid.uuid4().hex)
    folder.mkdir(parents=True)
    try:
        module = importlib.import_module('bridge_connection')
        input_checks(module)
        if task in ('L07', 'L08'):
            geometry_checks(module)
        if task == 'L08':
            application_checks(folder)
        result = dict(status='passed', task=task, evidence=str(folder))
    except Exception:
        (folder / 'failure.log').write_text(traceback.format_exc(), encoding='utf-8')
        result = dict(status='failed', task=task, evidence=str(folder))
    (folder / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
