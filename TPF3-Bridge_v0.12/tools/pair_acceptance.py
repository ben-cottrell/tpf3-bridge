"""Frozen host acceptance for L09-L14. Offline Python only; never runs a worker."""
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
from tools.connection_acceptance import fixture as single_fixture


def fixture(curved=False, opposing=False):
    base = single_fixture()
    angle = math.pi/6 if curved else 0
    end = [500, 100 if curved else 0, 0]
    ports = []
    for track, offset in [('a', -2), ('b', 2)]:
        for side in (0, 1):
            port = copy.deepcopy(base['start' if side == 0 else 'end'])
            phi = angle if side else 0
            centre = end if side else [0, 0, 0]
            sign = -1 if opposing and track == 'b' else 1
            port.update(port_id=track+str(side),
                        position_m=[centre[0]-offset*math.sin(phi), centre[1]+offset*math.cos(phi), 0],
                        forward_unit=[sign*math.cos(phi), sign*math.sin(phi), 0],
                        role='entry' if side == (1 if sign < 0 else 0) else 'exit')
            ports.append(port)
    base.pop('start'); base.pop('end')
    base.update(kind='double_track_connection', ports=ports,
                connections=[dict(track_id='a', start_port='a0', end_port='a1'),
                             dict(track_id='b', start_port='b1' if opposing else 'b0',
                                  end_port='b0' if opposing else 'b1')])
    base['constraints'].update(spacing_m=4, min_separation_m=3.5,
                               lowering_tolerance_m=0.01, realised_tolerance_m=0.001)
    return base


def snapshot(record):
    return dict(schema_version='0.12.0', environment='mock', snapshot_id='authored-pair-example',
                revision=0, ports=copy.deepcopy(record['ports']),
                neighbours={'protected-1': dict(asset_key='protected-1', start_node='n0', end_node='n1',
                    points=[[-30, 30, 0], [-20, 30, 0]], mode='plain', direction='forward')})


def reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('invalid or mismatched record accepted')


def input_checks(module):
    for opposing in (False, True):
        r = fixture(opposing=opposing)
        assert module.validate_pair(r) == r
    for edit in ('duplicate', 'pairing', 'grade', 'tangent', 'spacing', 'unknown'):
        r = fixture()
        if edit == 'duplicate': r['ports'][1]['port_id'] = r['ports'][0]['port_id']
        if edit == 'pairing': r['connections'][1]['start_port'] = 'a0'
        if edit == 'grade': r['ports'][0]['grade'] = 0.1
        if edit == 'tangent': r['ports'][0]['forward_unit'] = [0, 0, 0]
        if edit == 'spacing': r['constraints']['spacing_m'] = True
        if edit == 'unknown': r['unknown'] = True
        reject(lambda: module.validate_pair(r))


def geometry_checks(module):
    for curved, opposing, rotation in [(False, False, 0), (True, False, 0), (True, True, 1.1)]:
        record = fixture(curved, opposing)
        if rotation:
            c, s = math.cos(rotation), math.sin(rotation)
            for p in record['ports']:
                x, y, z = p['position_m']; p['position_m'] = [100+c*x-s*y, -100+s*x+c*y, z]
                x, y, z = p['forward_unit']; p['forward_unit'] = [c*x-s*y, s*x+c*y, z]
        result = module.fit_pair(record)
        assert result['status'] == 'pair_ready', result
        candidate = result['candidate']; ports = {p['port_id']: p for p in record['ports']}
        for connection in record['connections']:
            for t, key in [(0, 'start_port'), (1, 'end_port')]:
                assert math.dist(module.point_at(candidate, connection['track_id'], t), ports[connection[key]]['position_m']) < 1e-6
                assert math.dist(module.tangent_at(candidate, connection['track_id'], t), ports[connection[key]]['forward_unit']) < 1e-7
        for i in range(41):
            t = i/40
            a = module.point_at(candidate, 'a', t)
            b = module.point_at(candidate, 'b', 1-t if opposing else t)
            tangent = module.tangent_at(candidate, 'a', t)
            delta = [y-x for x, y in zip(a, b)]
            assert abs(math.dist(a, b)-4) < 1e-5
            assert abs(sum(x*y for x, y in zip(delta, tangent))) < 1e-5
        # These witnesses supplement, and do not replace, the required continuous certificates.
        assert candidate.get('candidate_hash')
    r = fixture(); r['constraints']['max_candidates'] = 0
    assert module.fit_pair(r)['status'] == 'incomplete_search'
    r = fixture(); r['region']['max_m'][0] = 100
    assert module.fit_pair(r)['status'] == 'failed_checks'
    r = fixture(); r['ports'][-1]['position_m'][1] += 1
    assert module.fit_pair(r)['status'] == 'unsupported_input'
    r = fixture(True); r['constraints']['min_radius_m'] = 1000000
    assert module.fit_pair(r)['status'] == 'no_accepted_candidate'


def plan_checks(pair, mock):
    record = fixture(True, True); source = snapshot(record)
    candidate = pair.fit_pair(record)['candidate']
    plan = mock.compile_pair_plan(candidate, record, source)
    assert plan['candidate_hash'] == candidate['candidate_hash']
    assert len(plan['operations']) == 2 and plan['real_game_execution_authorised'] is False
    assert len({o['payload']['asset_key'] for o in plan['operations']}) == 2
    assert {(o['payload']['start_node'], o['payload']['end_node']) for o in plan['operations']} == {('a0', 'a1'), ('b1', 'b0')}
    bad = copy.deepcopy(source); bad['ports'][0]['position_m'][0] += 1
    reject(lambda: mock.compile_pair_plan(candidate, record, bad))
    bad = copy.deepcopy(candidate); bad['candidate_hash'] = '0'*64
    reject(lambda: mock.compile_pair_plan(bad, record, source))
    return source, plan


def mock_checks(pair, mock):
    source, plan = plan_checks(pair, mock)
    world = mock.PairMock(source)
    assert mock.execute_pair(plan, world)['status'] == 'mock_verified'
    writes = world.writes
    assert mock.execute_pair(plan, world)['status'] == 'mock_verified' and world.writes == writes
    assert world.tracks['protected-1'] == source['neighbours']['protected-1']
    key = plan['operations'][0]['payload']['asset_key']
    for fault in ('geometry', 'connection', 'neighbour'):
        world = mock.PairMock(source); assert mock.execute_pair(plan, world)['status'] == 'mock_verified'
        if fault == 'geometry': world.tracks[key]['points'][1][0] += 1
        if fault == 'connection': world.tracks[key]['end_node'] = 'wrong-node'
        if fault == 'neighbour': world.tracks['protected-1']['points'][0][0] += 1
        assert mock.execute_pair(plan, world)['status'] != 'mock_verified'
    world = mock.PairMock(source); world.drop_ack_at = 0
    assert mock.execute_pair(plan, world)['status'] == 'mock_verified' and world.writes == 2
    world = mock.PairMock(source); world.fail_at = 1
    assert mock.execute_pair(plan, world)['status'] != 'mock_verified' and world.writes == 1
    world = mock.PairMock(source); world.revision += 1
    assert mock.execute_pair(plan, world)['status'] != 'mock_verified' and world.writes == 0


def app_checks(folder):
    record = fixture(True, True)
    source = folder/'pair.json'; source.write_text(json.dumps(record))
    snap = folder/'snapshot.json'; snap.write_text(json.dumps(snapshot(record)))
    def cli(*args, ok=True):
        p = subprocess.run([sys.executable, str(ROOT/'bridge_cli.py'), *map(str, args)], cwd=ROOT, capture_output=True, timeout=90)
        assert (p.returncode == 0) == ok and len(p.stdout) <= 4096
        value = json.loads(p.stdout); assert value['game_constructed'] is False
        return value
    for execute in (False, True):
        out = folder/('mock' if execute else 'design')
        args = ['connect-pair', '--input', source, '--output', out]
        if execute: args += ['--mock-execute', '--snapshot', snap]
        result = cli(*args)
        assert result['status'] == ('mock_verified' if execute else 'pair_ready')
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
        assert cli('status', '--run', out)['status'] == result['status']
        assert cli('verify', '--run', out)['status'] == 'integrity_verified'
        cli(*args, ok=False)
        assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in out.iterdir()}
        (out/'candidate.json').write_text('{}')
        assert 'candidate.json' in cli('verify', '--run', out, ok=False)['changed_files']
    record['ports'][0]['grade'] = 0.1; source.write_text(json.dumps(record))
    cli('connect-pair', '--input', source, '--output', folder/'invalid', ok=False)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--task', required=True, choices=[f'L{i:02}' for i in range(9,15)])
    task = parser.parse_args().task
    folder = ROOT/'.local_runs'/('batch_pair_'+uuid.uuid4().hex); folder.mkdir(parents=True)
    try:
        pair = importlib.import_module('bridge_pair'); input_checks(pair)
        if int(task[1:]) >= 10: geometry_checks(pair)
        if int(task[1:]) >= 11:
            mock = importlib.import_module('bridge_pair_mock'); plan_checks(pair, mock)
        if int(task[1:]) >= 12: mock_checks(pair, mock)
        if int(task[1:]) >= 13: app_checks(folder)
        status = 'passed'
    except Exception:
        (folder/'failure.log').write_text(traceback.format_exc(), encoding='utf-8'); status = 'failed'
    result = dict(status=status, task=task, evidence=str(folder))
    (folder/'result.json').write_text(json.dumps(result)); print(json.dumps(result))
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
