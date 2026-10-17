"""Compose two accepted native layouts; evidence is local, inspection never builds."""
import hashlib
import json
import math
from pathlib import Path
import uuid

import bridge_live as live

LAYOUT = 'two_layout_network_v1'


def _bound(value, maximum, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError(label + ' must be finite and within (0,' + str(maximum) + ']')


def _parent(path):
    record = live._load_layout_record(path)
    plan = record['plan']
    planners = {live.PARALLEL_LAYOUT: live.plan_parallel_layout,
                live.RECIPROCAL_LAYOUT: live.plan_reciprocal_layout}
    if plan.get('layout') not in planners or plan != planners[plan['layout']](plan['brief']):
        raise ValueError('parent must be a canonical parallel or reciprocal layout')
    if record.get('summary', {}).get('status') != 'ok':
        raise ValueError('parent requires a completed receipt')
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return record, digest


def _port(plan, role):
    if not isinstance(role, dict) or set(role) != {'layout', 'port'}:
        raise ValueError('role requires explicit layout and port')
    return plan['parents'][role['layout']]['plan']['ports'][role['port']]


def _intent(plan, role):
    p = _port(plan, role)
    return live._recipe_intent(plan, p['position'], p['travel_direction'])


def _corridor(plan, link):
    b = plan['brief']
    return {'source': _intent(plan, link['source']), 'target': _intent(plan, link['target']),
            'guides': link['guides'], 'radius': b['radius'], 'region': b['region'],
            'vertical': {'max_grade': b['max_grade']}, 'max_fit_attempts': 1,
            'max_route_length': b['max_connection_length']}


def plan_layout_network(brief):
    keys = {'layout', 'parents', 'links', 'movements', 'radius', 'max_grade', 'region',
            'max_connection_length', 'max_route_length', 'min_sampled_link_separation'}
    if not isinstance(brief, dict) or set(brief) != keys or brief['layout'] != LAYOUT:
        raise ValueError('explicit two_layout_network_v1 brief required')
    if not isinstance(brief['parents'], dict) or len(brief['parents']) != 2:
        raise ValueError('two named existing layout records required')
    plan = {'version': 1, 'layout': LAYOUT, 'brief': brief, 'parents': {}, 'game_constructed': False}
    for name, path in brief['parents'].items():
        if not isinstance(name, str) or not name or not isinstance(path, str):
            raise ValueError('named parent record paths required')
        record, digest = _parent(path)
        plan['parents'][name] = {'record': str(Path(path).resolve()), 'sha256': digest, 'plan': record['plan']}
    if len({p['sha256'] for p in plan['parents'].values()}) != 2:
        raise ValueError('two distinct layouts required')
    _bound(brief['max_route_length'], 8000, 'combined route length')
    _bound(brief['max_connection_length'], 4000, 'connection length')
    _bound(brief['min_sampled_link_separation'], 100, 'sampled separation')
    if type(brief['radius']) not in (int,float) or not math.isfinite(brief['radius']) or brief['radius'] < 120 or type(brief['max_grade']) not in (int,float) or not math.isfinite(brief['max_grade']) or not 0 <= brief['max_grade'] <= .04:
        raise ValueError('network radius >=120 and max_grade <=.04 required')
    if len(brief['links']) != 2 or len(brief['movements']) != 2:
        raise ValueError('exactly two directed links and full movements required')
    for rows, endpoint_functions in ((brief['links'], ('exit', 'entry')), (brief['movements'], ('entry', 'exit'))):
        if {r['direction'] for r in rows} != {'UP', 'DOWN'}:
            raise ValueError('one explicit UP and DOWN required')
        for row in rows:
            required = {'direction', 'source', 'target'} | ({'guides'} if rows is brief['links'] else set())
            if set(row) != required or row['source']['layout'] == row['target']['layout']:
                raise ValueError('explicit cross-layout directed roles required')
            for key, function in zip(('source', 'target'), endpoint_functions):
                p = _port(plan, row[key])
                if p['running_direction'] != row['direction'] or p['function'] != function:
                    raise ValueError('role direction/function mismatch')
    for link in brief['links']:
        movement = next(r for r in brief['movements'] if r['direction'] == link['direction'])
        if any(link[k]['layout'] != movement[k]['layout'] for k in ('source', 'target')):
            raise ValueError('full movement must traverse its declared link')
        for side, pair in (('source', ('source', 'source')), ('target', ('target', 'target'))):
            parent = plan['parents'][link[side]['layout']]['plan']
            a, z = (movement[side]['port'], link[side]['port']) if side == 'source' else (link[side]['port'], movement[side]['port'])
            if not any(r['from'] == a and r['to'] == z for r in parent['movements']):
                raise ValueError('full movement requires an existing declared local movement')
        corridor = _corridor(plan, link)
        live.validate_project_brief({k: v for k, v in corridor.items() if k != 'guides'}, corridor=True)
        # Reuse all guide validation, without constructing a client or native call.
        class ValidateOnly:
            pass
        # connect_corridor validates before calling _connect_project; avoid calling it here.
        if not isinstance(link['guides'], list) or not 1 <= len(link['guides']) <= 3:
            raise ValueError('one to three guides required')
        for g in link['guides']:
            if set(g) != {'position', 'travel_direction', 'grade'}:
                raise ValueError('explicit guide geometry required')
            for k, n in (('position', 3), ('travel_direction', 2)):
                if not isinstance(g[k], list) or len(g[k]) != n or any(type(v) not in (int, float) or not math.isfinite(v) for v in g[k]):
                    raise ValueError('finite guide coordinates required')
            if math.hypot(*g['travel_direction']) < 1e-9 or type(g['grade']) not in (int, float) or not math.isfinite(g['grade']) or abs(g['grade']) > brief['max_grade']:
                raise ValueError('invalid guide direction/grade')
            if any(not brief['region']['min'][i] <= g['position'][i] <= brief['region']['max'][i] for i in range(3)):
                raise ValueError('guide outside authorised region')
    plan['plan_hash'] = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return plan


def publish_layout_network(plan, directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    path = Path(directory) / (uuid.uuid4().hex + '.network_plan.json')
    live.atomic_json(path, {'plan': plan})
    return {'status': 'ok', 'operation': 'layout-network', 'stage': 'plan', 'game_constructed': False,
            'plan_hash': plan['plan_hash'], 'evidence': str(path.resolve()), 'native_execution_supported': True}


def _parents(client, plan, record):
    result = {}
    for name, saved in plan['parents'].items():
        parent, digest = _parent(saved['record'])
        if digest != saved['sha256']:
            raise ValueError('parent receipt changed: ' + name)
        proof = {k: v for k, v in parent.items() if k in ('pair_runtime', 'return_runtime')}
        proof['summary'] = {'evidence': str(client.evidence / (uuid.uuid4().hex + '.network_parent.json'))}
        verifier = live._verify_reciprocal_layout if parent['plan']['layout'] == live.RECIPROCAL_LAYOUT else live._verify_parallel_layout
        assessed = verifier(client, parent['plan'], proof)
        live.atomic_json(Path(proof['summary']['evidence']), proof)
        if not assessed.get('final_network_verified'):
            raise live.LiveError('native_verification_failed', 'local layout movements failed: ' + name)
        result[name] = proof
    record['parent_observations'] = result
    return result


def _role(parents, role):
    return parents[role['layout']]['current_ports'][role['port']]


def _path_edges(response):
    return [r['edge']['entity'] for r in response['result']['path'] if r['confirmed_TRACK']]


def _verify(client, plan, record, *, partial=False):
    parents = _parents(client, plan, record)
    chains = {}
    for link in plan['brief']['links']:
        direction = link['direction']
        if direction not in record.get('links', {}):
            if partial: continue
            raise live.LiveError('network_incomplete', 'connector receipt missing: ' + direction)
        saved = record['links'][direction]
        raw = Path(saved['record']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != saved['sha256']:
            raise ValueError('connector receipt changed')
        receipt = json.loads(raw.decode('utf-8-sig'))
        if receipt['brief'] != _corridor(plan, link) or receipt['summary']['status'] != 'ok':
            raise ValueError('connector receipt differs from approved link')
        ids, nodes = receipt['summary']['edges'], receipt['summary']['nodes']
        a, z = (_role(parents, link[k]) for k in ('source', 'target'))
        if not ids or len(ids) > 16 or len(nodes) != len(ids) + 1 or nodes[0] != a['node_id'] or nodes[-1] != z['node_id']:
            raise live.LiveError('stale_network_connector', 'current named ports differ from connector endpoints')
        r = client.request('inspect', {'edge_ids': ids, 'geometry_constraints': {'radius': plan['brief']['radius'], 'max_grade': plan['brief']['max_grade'], 'region': plan['brief']['region']}})
        edges = {e['id']: e for e in r.get('result', {}).get('edges', [])}
        if r['status'] != 'ok' or set(edges) != set(ids) or any(edges[e]['road_type'] != 'TRACK' or {edges[e]['node0'], edges[e]['node1']} != {nodes[i], nodes[i + 1]} for i, e in enumerate(ids)):
            raise live.LiveError('stale_network_connector', 'exact current connector chain unavailable')
        chains[direction] = {'edges': ids, 'nodes': nodes, 'inspection': r}
        record['current_links'] = chains
    record['current_links'] = chains
    # Native readback samples a Hermite edge; this clearance screen is not a continuous proof.
    samples = {}
    for direction, chain in chains.items():
        points = []
        for e in chain['inspection']['result']['edges']:
            for j in range(65):
                u = j / 64
                h = (2*u**3-3*u*u+1, u**3-2*u*u+u, -2*u**3+3*u*u, u**3-u*u)
                points.append([sum(h[t]*e[k][i] for t, k in enumerate(('p0','t0','p1','t1'))) for i in range(3)])
        samples[direction] = points
    clearance = min(math.dist(a, b) for a in samples['UP'] for b in samples['DOWN']) if len(samples)==2 else None
    record['sampled_link_separation'] = {'minimum': clearance, 'samples_per_edge': 65, 'continuous_proof': False}
    if clearance is not None and clearance < plan['brief']['min_sampled_link_separation']:
        raise live.LiveError('native_verification_failed', 'sampled connecting alignment separation below selected minimum')
    for movement in plan['brief']['movements']:
        direction = movement['direction'];link = next(r for r in plan['brief']['links'] if r['direction'] == direction)
        if direction not in chains:
            record.setdefault('routes', []).append(movement | {'verified':False, 'reason':'connector unavailable'})
            continue
        a, z = (_role(parents, movement[k]) for k in ('source', 'target'))
        local_paths = {}
        for side in ('source', 'target'):
            x, y = (movement[side]['port'], link[side]['port']) if side == 'source' else (link[side]['port'], movement[side]['port'])
            local = next(r for r in parents[movement[side]['layout']]['routes'] if r['from'] == x and r['to'] == y)
            local_paths[side] = _path_edges(local['response'])
        intended = local_paths['source'] + chains[direction]['edges'] + local_paths['target']
        # Native request accepts 32 required edges; verify the complete intended set below.
        r = live.route(client, {'source_edge': a['edge_id'], 'source_node': a['node_id'], 'target_edge': z['edge_id'], 'target_node': z['node_id'], 'mode': 'TRAIN', 'max_length': plan['brief']['max_route_length'], 'required_edges': list(dict.fromkeys([a['edge_id'], z['edge_id']] + chains[direction]['edges']))})
        ok = r['status'] == 'ok' and r.get('result', {}).get('requested_route_verified') is True and intended == _path_edges(r)
        record.setdefault('routes', []).append(movement | {'verified': ok, 'required_complete_path_edges': intended, 'response': r})
        live.atomic_json(Path(record['summary']['evidence']), record)
        if not ok:
            raise live.LiveError('native_verification_failed', 'intended full movement failed: ' + direction)
    verified=sum(r['verified'] for r in record['routes'])
    return {'routes_verified': verified, 'final_network_verified': verified==2 and len(chains)==2, 'local_routes_verified': sum(len(p['routes']) for p in parents.values()), 'min_sampled_link_separation': clearance, 'geometry_sampled_only': True, 'constant_parallel_spacing': False}


def _finish(record, exc=None):
    summary = record['summary']
    if exc:
        summary.update(status=getattr(exc, 'status', 'invalid_result'), error=str(exc)[:400], final_network_verified=False)
    summary['routes_verified'] = sum(r['verified'] for r in record.get('routes', []))
    summary['route_lengths'] = {r['direction']: r.get('response',{}).get('result',{}).get('total_path_length') for r in record.get('routes',[]) if r['verified']}
    summary['native_effect_history_complete'] = False
    if 'recorded_prior_game_constructed' in record:
        summary['recorded_prior_game_constructed'] = record['recorded_prior_game_constructed']
    summary['local_routes_verified'] = sum(sum(bool(r.get('verified')) for r in p.get('routes', [])) for p in record.get('parent_observations', {}).values())
    summary['link_results'] = [{'direction': l['direction'], 'state': 'current_verified' if l['direction'] in record.get('current_links', {}) else ('recorded_complete_not_rechecked' if l['direction'] in record.get('links', {}) else 'unverified')} for l in record['plan']['brief']['links']]
    summary['movement_results'] = [{'direction': m['direction'], 'state': 'verified' if any(r['direction'] == m['direction'] and r['verified'] for r in record.get('routes', [])) else 'unverified'} for m in record['plan']['brief']['movements']]
    summary['next_action'] = 'none' if summary['status'] == 'ok' else 'inspect_and_reconcile_no_automatic_replay'
    live.atomic_json(Path(summary['evidence']), record)
    return summary


def execute_layout_network(client, plan, *, continuation_record=None):
    if plan != plan_layout_network(plan['brief']):
        raise ValueError('network plan changed')
    path = client.evidence / (uuid.uuid4().hex + '.network.json')
    record = {'plan': plan, 'links': {}, 'routes': [], 'summary': {'status': 'incomplete', 'operation': 'layout-network', 'game_constructed': False, 'plan_hash': plan['plan_hash'], 'evidence': str(path.resolve()), 'train_traversal': 'unprobed', 'direction_enforcement': 'not_provided'}}
    lock = client.evidence / 'network.lock'
    try:
        with lock.open('x'): pass
    except FileExistsError:
        raise live.LiveError('client_busy', 'one network operation at a time') from None
    try:
        if client.journal.exists() and json.loads(client.journal.read_text()).get('pending'):
            raise live.LiveError('reconciliation_required', 'prior native operation pending')
        parents=None
        if continuation_record:
            old=live._load_layout_record(continuation_record)
            comparable=json.loads(json.dumps(old['plan']['brief']))
            if not set(old.get('links',{})) <= {'UP','DOWN'}:raise ValueError('invalid completed link roles')
            for link in comparable['links']:
                if link['direction'] not in old.get('links',{}):
                    link['guides']=next(r['guides'] for r in plan['brief']['links'] if r['direction']==link['direction'])
            if comparable!=plan['brief']:raise ValueError('continuation may change only guides of an uncompleted link')
            checked=inspect_layout_network(client,continuation_record)
            proof=json.loads(Path(checked['evidence']).read_text())
            if checked['status'] not in ('ok','network_incomplete') or set(proof.get('current_links',{}))!=set(old.get('links',{})):
                raise live.LiveError('reconciliation_required','completed links/local movements not freshly established')
            record.update(links=old.get('links',{}),continuation_of=str(Path(continuation_record).resolve()),
                          recorded_prior_game_constructed=old.get('summary',{}).get('game_constructed','unknown'),
                          native_effect_history_complete=False)
            parents=proof.get('parent_observations')
            live.atomic_json(path,record)
        if parents is None:parents = _parents(client, plan, record)
        for link in plan['brief']['links']:
            if link['direction'] in record['links']:continue
            if any(_role(parents, link[k]).get('eligible') is not True for k in ('source', 'target')):
                raise live.LiveError('attachment_not_free', 'preflight requires free link endpoints; no replay')
        for link in plan['brief']['links']:
            if link['direction'] in record['links']:continue
            record['unfinished_step'] = link['direction'];live.atomic_json(path, record)
            result = live.connect_corridor(client, _corridor(plan, link), execute=True)
            record.setdefault('operations', []).append({'direction': link['direction'], 'response': result})
            effect = result.get('game_constructed', 'unknown')
            if effect == 'unknown' or record['summary']['game_constructed'] is not True:
                record['summary']['game_constructed'] = effect
            if result['status'] != 'ok':
                raise live.LiveError(result['status'], result.get('error', 'link failed'))
            raw = Path(result['evidence']).read_bytes()
            record['links'][link['direction']] = {'record': result['evidence'], 'sha256': hashlib.sha256(raw).hexdigest()}
            record.pop('unfinished_step');live.atomic_json(path, record)
        record['summary'].update(_verify(client, plan, record), status='ok')
        return _finish(record)
    except (live.LiveError, ValueError, KeyError, TypeError, OSError) as exc:
        return _finish(record, exc)
    finally:
        lock.unlink()


def inspect_layout_network(client, invocation):
    original = live._load_layout_record(invocation);plan = original['plan']
    if plan != plan_layout_network(plan['brief']):
        raise ValueError('network plan/parent records changed')
    path = client.evidence / (uuid.uuid4().hex + '.network_inspection.json')
    record = {'plan': plan, 'links': original.get('links', {}), 'routes': [], 'recorded_prior_game_constructed': original.get('summary', {}).get('game_constructed', 'unknown'), 'summary': {'status': 'incomplete', 'operation': 'layout-network-inspect', 'game_constructed': False, 'plan_hash': plan['plan_hash'], 'evidence': str(path.resolve()), 'train_traversal': 'unprobed', 'direction_enforcement': 'not_provided'}}
    try:
        record['summary'].update(_verify(client, plan, record, partial=original.get('summary',{}).get('status')!='ok'))
        record['summary']['status']='ok' if record['summary']['final_network_verified'] else 'network_incomplete'
        return _finish(record)
    except (live.LiveError, ValueError, KeyError, TypeError, OSError) as exc:
        return _finish(record, exc)
