"""Development live client: data-only mod modules in, correlated game-log JSON out.

No model calls, UI automation, game launch, service, or mutation retry.
The mod must already be active in a healthy test world.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import time
import uuid

MARKER = 'TPF3_BRIDGE_LIVE_RESPONSE '
OPERATIONS = {'inspect', 'fit', 'build', 'readback', 'extension', 'connection', 'test_approach', 'route', 'discover', 'selected_connection'}

def is_mutation(operation, params):
    return operation in ('build', 'test_approach') or (operation in ('extension', 'connection') and params.get('execute') is True)

def discover_session(log_path):
    """Read transport markers locally; a later request must still prove responsiveness."""
    ready = None
    confirmed = None
    with Path(log_path).open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            for kind in ('READY', 'SESSION'):
                marker = 'TPF3_BRIDGE_LIVE_' + kind + ' '
                if marker not in line:
                    continue
                try:
                    value = json.loads(line.split(marker, 1)[1])
                except ValueError:
                    continue
                if not isinstance(value, dict):
                    continue
                if kind == 'READY':
                    ready = value
                    confirmed = None
                elif ready and value.get('session') == ready.get('session') and value.get('ready') is True:
                    confirmed = value['session']
    if not ready or not confirmed or ready.get('version') != 1:
        raise LiveError('adapter_handshake_unavailable', 'latest adapter READY has no matching SESSION handshake')
    return confirmed

def client_from_context(context_path, timeout=30):
    """Context contains installation paths, never a remembered native entity mapping."""
    context_path = Path(context_path).resolve()
    context = json.loads(context_path.read_text(encoding='utf-8-sig'))
    def location(key):
        path = Path(context[key])
        return path if path.is_absolute() else context_path.parent / path
    mod, log, root = location('mod_directory'), location('log'), location('session_evidence_root')
    session = discover_session(log)
    return LiveClient(mod, log, root / session, session, timeout, require_ack=True)

def validate_brief(brief):
    if not isinstance(brief, dict):
        raise ValueError('extension brief must be an object')
    keys = {'anchor_edge', 'anchor_node', 'end_xy', 'end_direction', 'radius', 'region'}
    if set(brief) != keys:
        raise ValueError('extension brief requires only ' + ', '.join(sorted(keys)))
    for key in ('anchor_edge', 'anchor_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    for key in ('end_xy', 'end_direction'):
        value = brief[key]
        if not isinstance(value, list) or len(value) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
            raise ValueError(key + ' must contain two finite native-coordinate values')
    if math.hypot(*brief['end_direction']) < 1e-9:
        raise ValueError('end_direction must be nonzero')
    if type(brief['radius']) not in (int, float) or not math.isfinite(brief['radius']) or brief['radius'] <= 0:
        raise ValueError('radius must be finite and positive')
    region = brief['region']
    if not isinstance(region, dict) or set(region) != {'min', 'max'}:
        raise ValueError('region requires min/max native XYZ coordinates')
    for key in ('min', 'max'):
        if not isinstance(region[key], list) or len(region[key]) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in region[key]):
            raise ValueError('region requires finite XYZ bounds')
    if any(region['min'][i] >= region['max'][i] for i in range(3)):
        raise ValueError('region bounds must be ordered')
    return brief

def extend(client, brief, *, execute=False):
    """One inspect/fit/(explicit build)/fresh-readback job; never retry a mutation."""
    validate_brief(brief)
    return _workflow(client, brief, execute, 'extension')

def validate_connection_brief(brief):
    keys = {'anchor_edge', 'anchor_node', 'target_edge', 'target_node', 'radius', 'region'}
    if not isinstance(brief, dict) or set(brief) != keys:
        raise ValueError('connection brief requires only ' + ', '.join(sorted(keys)))
    for key in ('target_edge', 'target_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    validate_brief({k:brief[k] for k in ('anchor_edge', 'anchor_node', 'radius', 'region')} |
                   {'end_xy':[0, 0], 'end_direction':[1, 0]})
    if brief['anchor_node'] == brief['target_node'] or brief['anchor_edge'] == brief['target_edge']:
        raise ValueError('connection requires distinct source and target attachments')
    return brief

def connect(client, brief, *, execute=False):
    """Connect two existing exact TRACK endpoint nodes; native geometry owns fitting."""
    validate_connection_brief(brief)
    return _workflow(client, brief, execute, 'connection')

def discover(client, brief):
    """Bounded native TRACK discovery, with complete per-node incidence checks."""
    if not isinstance(brief, dict) or set(brief) != {'region', 'max_edges'}:
        raise ValueError('discovery requires region and max_edges')
    validate_brief({'anchor_edge':1,'anchor_node':2,'end_xy':[0,0],
                    'end_direction':[1,0],'radius':1,'region':brief['region']})
    if any(brief['region']['max'][i]-brief['region']['min'][i] > 400 for i in range(3)):
        raise ValueError('discovery region spans at most400 native units per axis')
    if type(brief['max_edges']) is not int or not 1 <= brief['max_edges'] <= 16:
        raise ValueError('discovery max_edges must be within1–16')
    return client.request('discover', brief)

def connect_selected(client, discovery, brief):
    """Select two recorded free endpoints; reacquire natively and fit only."""
    if not isinstance(brief, dict) or set(brief) != {'source_ref','target_ref','radius','region'}:
        raise ValueError('selection requires source_ref, target_ref, radius and region')
    records=discovery if isinstance(discovery,list) else [discovery]
    if not 1<=len(records)<=2:raise ValueError('selection accepts one or two local discoveries')
    candidates=[];request_ids=[]
    for record in records:
        if (not isinstance(record,dict) or record.get('status')!='ok' or record.get('operation')!='discover'
                or record.get('session')!=client.session):
            raise ValueError('selection requires successful current-session discoveries')
        rows=record.get('result',{}).get('candidates',[])
        if rows=={}:rows=[] # Empty Lua array uses existing object encoding.
        if not isinstance(rows,list) or any(not isinstance(c,dict) for c in rows):raise ValueError('invalid discovery candidates')
        candidates.extend(rows);request_ids.append(record['request_id'])
    if len(set(request_ids))!=len(request_ids):raise ValueError('duplicate discovery records')
    selected=[]
    for key in ('source_ref','target_ref'):
        matches=[c for c in candidates if c.get('ref')==brief[key]]
        if len(matches)!=1:raise ValueError('candidate reference missing or ambiguous')
        c=matches[0]
        if (c.get('eligible') is not True or c.get('incidence_complete') is not True
                or c.get('incident_count')!=1 or c.get('incident_edges')!=[c.get('edge_id')]):
            raise ValueError('candidate is not a fully verified free endpoint')
        if not isinstance(c.get('edge_snapshot'),dict):raise ValueError('candidate snapshot missing')
        selected.append(c)
    source,target=selected
    validate_connection_brief({'anchor_edge':source['edge_id'],'anchor_node':source['node_id'],
        'target_edge':target['edge_id'],'target_node':target['node_id'],'radius':brief['radius'],'region':brief['region']})
    return client.request('selected_connection',{'source':source,'target':target,
        'radius':brief['radius'],'region':brief['region'],'discovery_request':request_ids[0],
        'discovery_requests':request_ids})

def reconcile_rejected_fixture(client, discovery):
    """Close a reported failed fixture using bounded current-state evidence, never replay."""
    state=json.loads(client.journal.read_text());pending=state.get('pending')
    if not pending or pending['operation']!='test_approach':
        raise LiveError('reconciliation_required','only a pending test_approach rejection is supported')
    rid=pending['request_id'];response_path=client.evidence/(rid+'.response.json')
    response=json.loads(response_path.read_text())
    if (response.get('session')!=client.session or response.get('request_id')!=rid
            or response.get('status')!='mutation_unverified'
            or not response.get('result',{}).get('error','').endswith('native_test_approach_rejected')):
        raise LiveError('reconciliation_required','no explicit native fixture rejection evidence',rid)
    if (not isinstance(discovery,dict) or discovery.get('operation')!='discover'
            or discovery.get('session')!=client.session or discovery.get('status')!='ok'):
        raise ValueError('reconciliation requires original current-session discovery')
    p=pending['params'];b=p['brief'];validate_brief(b)
    matches=[c for c in discovery['result']['candidates'] if c['edge_id']==b['anchor_edge'] and c['node_id']==b['anchor_node']]
    if len(matches)!=1:raise ValueError('original fixture anchor snapshot missing')
    current=client.request('inspect',{'edge_ids':[b['anchor_edge']]})
    if current['status']!='ok' or current['result']['edges']!=[matches[0]['edge_snapshot']]:
        raise LiveError('reconciliation_required','fixture anchor changed; outcome remains uncertain',rid)
    direction=b['end_direction'];norm=math.hypot(*direction)
    end=[b['end_xy'][i]+p['length']*direction[i]/norm for i in range(2)]
    # Existing fixture fitter checks finish XY within0.001, heading within0.1degree,
    # and both proposed endpoints inside its XYZ region;2units covers those errors.
    region={'min':[min(b['end_xy'][i],end[i])-2 for i in range(2)]+[b['region']['min'][2]],
            'max':[max(b['end_xy'][i],end[i])+2 for i in range(2)]+[b['region']['max'][2]]}
    observed=discover(client,{'region':region,'max_edges':16});result=observed.get('result',{})
    if observed['status']!='ok' or result.get('complete') is not True or result.get('edge_count')!=0:
        raise LiveError('reconciliation_required','fixture footprint is incomplete or contains TRACK; retain pending outcome',rid)
    latest=json.loads(client.journal.read_text())
    if latest.get('pending')!=pending:raise LiveError('reconciliation_required','pending operation changed during observation',rid)
    record={'status':'reconciled_failed_fixture','original_pending':pending,'original_response':str(response_path.resolve()),
        'observations':[current['request_id'],observed['request_id']],'region':region,
        'intended_fixture_constructed':False,'other_effects':'unknown','effects_history_complete':False,
        'automatic_replay':False,'game_constructed':False}
    path=client.evidence/(rid+'.reconciliation.json');atomic_json(path,record)
    latest.setdefault('reconciled_rejections',{})[rid]={'evidence':str(path.resolve()),'automatic_replay':False}
    latest.pop('pending');atomic_json(client.journal,latest)
    return {'status':'ok','result':record,'evidence':str(path.resolve())}

def route(client, brief):
    """Query native transport routing; does not build or establish train traversal."""
    keys = {'source_edge', 'source_node', 'target_edge', 'target_node', 'mode', 'max_length', 'required_edges'}
    if not isinstance(brief, dict) or set(brief) != keys:
        raise ValueError('route brief requires only ' + ', '.join(sorted(keys)))
    for key in ('source_edge', 'source_node', 'target_edge', 'target_node'):
        if type(brief[key]) is not int or brief[key] <= 0:
            raise ValueError(key + ' must be an exact positive native ID')
    if brief['source_node'] == brief['target_node'] or brief['source_edge'] == brief['target_edge']:
        raise ValueError('route requires distinct attachments')
    if brief['mode'] not in ('TRAIN', 'ELECTRIC_TRAIN'):
        raise ValueError('route mode must be TRAIN or ELECTRIC_TRAIN')
    if type(brief['max_length']) not in (int, float) or not math.isfinite(brief['max_length']) or not 0 < brief['max_length'] <= 800:
        raise ValueError('route max_length must be finite and within (0,800] native units')
    ids = brief['required_edges']
    if not isinstance(ids, list) or not 1 <= len(ids) <= 16 or any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('required_edges must contain 1–16 distinct exact native IDs')
    return client.request('route', brief)

def _workflow(client, brief, execute, operation):
    if type(execute) is not bool:
        raise ValueError('execute must be boolean')
    job_id = uuid.uuid4().hex
    record_path = client.evidence / (job_id + '.workflow.json')
    summary = {'status': 'incomplete', 'job_id': job_id, 'session': client.session,
               'game_constructed': False, 'execute': execute, 'stage': 'inspect',
               'evidence': str(record_path.resolve()), 'stages': []}
    lock = client.evidence / 'workflow.lock'
    try:
        with lock.open('x'):
            pass
    except FileExistsError:
        raise LiveError('client_busy', 'one railway workflow at a time') from None
    try:
        atomic_json(record_path, {'summary': summary, 'brief': brief})
        summary['stage'] = 'native_' + operation
        response = client.request(operation, {'brief': brief, 'execute': execute}, request_id=job_id)
        result = response.get('result', {})
        summary.update(status=response['status'], stage=result.get('stage', 'native_' + operation),
                       stages=result.get('stages', []), game_constructed=result.get('game_constructed', 'unknown' if execute else False))
        if result.get('fit'):
            summary['fit'] = result['fit']
        if response['status'] != 'ok':
            summary['error'] = result.get('error', 'native_stage_failed')
            if result.get('reason_class'):
                summary['reason_class'] = result['reason_class']
        elif execute:
            read = result.get('readback', {})
            if (read.get('connected') is not True or not read.get('ordered_edges') or not read.get('ordered_nodes')
                    or read['ordered_nodes'][0] != brief['anchor_node']
                    or (operation == 'connection' and (read['ordered_nodes'][-1] != brief['target_node']
                        or read.get('attachments', {}).get('target_edge') != brief['target_edge']
                        or read.get('attachments', {}).get('source_edge') != brief['anchor_edge']))):
                raise LiveError('native_verification_failed', 'fresh readback did not establish the requested exact attachments')
            summary.update(connected=True, edges=read['ordered_edges'], nodes=read['ordered_nodes'],
                           sampled_XY_error=read.get('sampled_XY_error'), train_traversal=read.get('train_traversal'))
            if operation == 'connection':
                summary['attachments'] = read['attachments']
    except (LiveError, OSError, ValueError, KeyError, TypeError) as exc:
        summary['status'] = getattr(exc, 'status', 'local_input_or_storage_error')
        summary['error'] = str(exc)[:400]
        if summary['stage'] == 'native_' + operation and execute:
            summary['game_constructed'] = 'unknown'
    finally:
        try:
            atomic_json(record_path, {'summary': summary, 'brief': brief})
        finally:
            lock.unlink()
    return summary

class LiveError(RuntimeError):
    def __init__(self, status, detail, request_id=None):
        super().__init__(detail)
        self.status, self.request_id = status, request_id

def lua_literal(value):
    """Serialize only JSON data; no user-supplied executable Lua text."""
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError('nonfinite number')
        return repr(value)
    if isinstance(value, str):
        # Byte decimal escapes avoid Lua/JSON unicode escape differences.
        return '"' + ''.join(chr(b) if 32 <= b < 127 and b not in (34, 92)
                             else '\\' + f'{b:03d}' for b in value.encode('utf-8')) + '"'
    if isinstance(value, list):
        return '{' + ','.join(lua_literal(v) for v in value) + '}'
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return '{' + ','.join('[' + lua_literal(k) + ']=' + lua_literal(v)
                              for k, v in value.items()) + '}'
    raise ValueError('request must contain JSON data only')

def atomic_json(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)

def parse_response(line, request_id, session, operation):
    if MARKER not in line:
        return None
    try:
        data = json.loads(line.split(MARKER, 1)[1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get('request_id') != request_id:
        return None
    if data.get('session') != session or data.get('operation') != operation or data.get('version') != 1:
        raise LiveError('protocol_error', 'matching ID has wrong session/operation/version', request_id)
    if data.get('status') not in {'ok', 'error', 'mutation_unverified'}:
        raise LiveError('protocol_error', 'invalid response status', request_id)
    return data

class LiveClient:
    def __init__(self, mod_directory, log_path, evidence_directory, session, timeout=30, *, require_ack=False):
        self.mod = Path(mod_directory)
        self.log = Path(log_path)
        self.evidence = Path(evidence_directory)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', session):
            raise ValueError('invalid runtime session token')
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError('timeout must be finite and within (0,300] seconds')
        self.session, self.timeout = session, timeout
        self.require_ack = require_ack
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.journal = self.evidence / 'client_state.json'

    def request(self, operation, params, *, request_id=None):
        if operation not in OPERATIONS or not isinstance(params, dict):
            raise ValueError('invalid operation/parameters')
        request_id = request_id or uuid.uuid4().hex
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', request_id):
            raise ValueError('invalid request ID')
        lock = self.evidence / 'client.lock'
        try:
            with lock.open('x'):
                pass
        except FileExistsError:
            raise LiveError('client_busy', 'one client request at a time') from None
        try:
            return self._request(operation, params, request_id)
        finally:
            lock.unlink()

    def _request(self, operation, params, request_id):
        state = json.loads(self.journal.read_text()) if self.journal.exists() else {'session': self.session, 'next_sequence': 1}
        if state['session'] != self.session:
            raise LiveError('session_changed', 'use a new evidence directory for a new runtime session')
        unresolved = state.get('pending')
        if unresolved and operation not in ('readback', 'inspect', 'route', 'discover', 'selected_connection'):
            raise LiveError('reconciliation_required', 'previous request is unfinished; inspect its matching response/current world before any repeat', state['pending']['request_id'])
        if (self.evidence / (request_id + '.request.json')).exists():
            raise LiveError('request_id_reused', 'request ID already recorded', request_id)
        sequence = state['next_sequence']
        request = {'version': 1, 'session': self.session, 'sequence': sequence,
                   'request_id': request_id, 'operation': operation, 'params': params}
        body = ('return ' + lua_literal(request) + '\n').encode('ascii')
        if len(body) > 32768:
            raise ValueError('request exceeds 32 KiB')
        offset = self.log.stat().st_size
        atomic_json(self.evidence / (request_id + '.request.json'), request)
        state['pending'] = {**request, 'log_offset': offset}
        if unresolved:
            state['pending']['unresolved_mutation'] = unresolved
        state['next_sequence'] += 1
        atomic_json(self.journal, state)
        directory = self.mod / 'content/scripts/pif_live' / self.session
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'{sequence:06d}.lua'
        if path.exists():
            raise LiveError('request_slot_conflict', str(path), request_id)
        temporary = path.with_suffix('.pending')
        temporary.write_bytes(body)
        os.replace(temporary, path)
        deadline = time.monotonic() + self.timeout
        partial = b''
        received = None
        acknowledged = not self.require_ack
        raw = self.evidence / (request_id + '.log')
        with raw.open('wb') as evidence:
            while time.monotonic() < deadline:
                with self.log.open('rb') as stream:
                    if stream.seek(0, 2) < offset:
                        raise LiveError('log_rotated', 'log changed during request; do not replay', request_id)
                    stream.seek(offset)
                    chunk = stream.read()
                    offset += len(chunk)
                evidence.write(chunk)
                partial += chunk
                lines = partial.split(b'\n')
                partial = lines.pop()
                for line in lines:
                    decoded = line.decode('utf-8', 'replace')
                    ack_marker = 'TPF3_BRIDGE_LIVE_ACK '
                    if ack_marker in decoded:
                        try:
                            ack = json.loads(decoded.split(ack_marker, 1)[1])
                        except ValueError:
                            ack = {}
                        if isinstance(ack, dict) and ack.get('request_id') == request_id and ack.get('session') == self.session:
                            if ack.get('success') is not True:
                                raise LiveError('command_completion_failed', 'native event command did not acknowledge completion; do not replay', request_id)
                            acknowledged = True
                    response = parse_response(decoded, request_id, self.session, operation)
                    if response is not None:
                        received = response
                        atomic_json(self.evidence / (request_id + '.response.json'), response)
                    if received is not None and acknowledged:
                        response = received
                        atomic_json(self.evidence / (request_id + '.response.json'), response)
                        verified_pending = (unresolved and unresolved['operation'] == 'build'
                                            and operation == 'readback' and response['status'] == 'ok'
                                            and response.get('result', {}).get('connected') is True
                                            and params.get('fit_request') == unresolved['params'].get('fit_request'))
                        if unresolved and not verified_pending:
                            state['pending'] = unresolved
                        elif response['status'] == 'mutation_unverified' or (
                                is_mutation(operation, params)
                                and response.get('result', {}).get('game_constructed') == 'unknown'):
                            state['pending']['outcome'] = 'mutation_unverified'
                        else:
                            state.pop('pending')
                        atomic_json(self.journal, state)
                        return response
                if len(partial) > 65536:
                    raise LiveError('protocol_error', 'unterminated oversized log line', request_id)
                time.sleep(.1)
        status = 'mutation_outcome_unknown' if is_mutation(operation, params) else 'request_timeout'
        raise LiveError(status, 'no matching response; request retained for reconciliation, never resubmitted automatically', request_id)

    def reconcile_pending(self):
        """Collect an existing late response only; never send another operation."""
        state = json.loads(self.journal.read_text())
        pending = state.get('pending')
        if not pending or state['session'] != self.session:
            raise LiveError('reconciliation_required', 'no matching current-session pending record')
        with self.log.open('rb') as stream:
            stream.seek(pending['log_offset'])
            lines = stream.read().decode('utf-8', 'replace').splitlines()
        if self.require_ack:
            ack_marker = 'TPF3_BRIDGE_LIVE_ACK '
            acknowledgements = []
            for line in lines:
                if ack_marker in line:
                    try:
                        ack = json.loads(line.split(ack_marker, 1)[1])
                    except ValueError:
                        continue
                    if isinstance(ack, dict) and ack.get('request_id') == pending['request_id'] and ack.get('session') == self.session:
                        acknowledgements.append(ack)
            if not any(ack.get('success') is True for ack in acknowledgements):
                raise LiveError('reconciliation_required', 'matching native command completion is still unobserved; do not replay', pending['request_id'])
        for line in lines:
            response = parse_response(line, pending['request_id'], self.session, pending['operation'])
            if response:
                atomic_json(self.evidence / (pending['request_id'] + '.response.json'), response)
                uncertain = response['status'] == 'mutation_unverified' or (
                    is_mutation(pending['operation'], pending['params'])
                    and response.get('result', {}).get('game_constructed') == 'unknown')
                if not uncertain:
                    state.pop('pending');atomic_json(self.journal, state)
                return response
        raise LiveError('reconciliation_required', 'no matching late response; fresh readback may be requested, no automatic mutation replay', pending['request_id'])

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=sorted(OPERATIONS | {'extend', 'connect', 'connect-selected', 'reconcile-fixture'}))
    parser.add_argument('--params', required=True, type=Path)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--discovery', type=Path, help='saved full discover response for connect-selected')
    parser.add_argument('--execute', action='store_true', help='authorise native construction for extend/connect')
    parser.add_argument('--mod-directory', type=Path)
    parser.add_argument('--log', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--session')
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if args.context:
            if any((args.mod_directory, args.log, args.evidence, args.session)):
                raise ValueError('use context or explicit transport arguments, not both')
            client = client_from_context(args.context, args.timeout)
        else:
            if not all((args.mod_directory, args.log, args.evidence, args.session)):
                raise ValueError('provide --context or all explicit transport arguments')
            client = LiveClient(args.mod_directory, args.log, args.evidence, args.session, args.timeout)
        params = json.loads(args.params.read_text(encoding='utf-8-sig'))
        if args.discovery and args.operation not in ('connect-selected','reconcile-fixture'):
            raise ValueError('--discovery is only for connect-selected/reconcile-fixture')
        if args.execute and args.operation not in ('extend', 'connect'):
            raise ValueError('--execute is only for extend/connect; low-level build uses explicit authorised parameter')
        if args.operation in ('extend', 'connect'):
            response = (extend if args.operation == 'extend' else connect)(client, params, execute=args.execute)
        elif args.operation == 'route':
            response = route(client, params)
        elif args.operation == 'discover':
            response = discover(client, params)
        elif args.operation == 'connect-selected':
            if not args.discovery:raise ValueError('connect-selected requires --discovery')
            response = connect_selected(client,json.loads(args.discovery.read_text(encoding='utf-8-sig')),params)
        elif args.operation == 'reconcile-fixture':
            if params!={} or not args.discovery:raise ValueError('reconcile-fixture needs empty params and --discovery')
            response=reconcile_rejected_fixture(client,json.loads(args.discovery.read_text(encoding='utf-8-sig')))
        else:
            response = client.request(args.operation, params)
    except (OSError, ValueError, LiveError, KeyError, TypeError) as exc:
        response = {'status': getattr(exc, 'status', 'local_input_or_storage_error'),
                    'error': str(exc)[:400], 'request_id': getattr(exc, 'request_id', None)}
    output = json.dumps(response, separators=(',', ':'))
    if len(output.encode('utf-8')) > 4095:
        compact = {
            'status': response['status'], 'operation': args.operation,
            'session': client.session, 'request_id': response.get('request_id'),
            'response_file': response.get('evidence') or str((client.evidence / (response['request_id'] + '.response.json')).resolve()),
            'detail': 'full response retained locally',
        }
        if args.operation == 'route':
            result = response.get('result', {})
            compact.update({key:result.get(key) for key in ('native_path_found', 'requested_route_verified', 'path_count', 'truncated', 'reason', 'train_traversal')})
        elif args.operation == 'discover':
            result=response.get('result', {})
            compact.update({key:result.get(key) for key in ('edge_count','candidate_count','truncated','complete')})
            candidates=result.get('candidates', [])
            if isinstance(candidates,list):
                candidates=sorted(candidates,key=lambda c:(not c.get('eligible',False),c['ref']))
                compact['candidate_preview']=[{key:c.get(key) for key in ('ref','pos','eligible','grade')} for c in candidates[:4]]
                compact['candidate_preview_truncated']=len(candidates)>4
        output = json.dumps(compact, separators=(',', ':'))
    print(output)
    accepted = response['status'] == 'ok'
    if args.operation == 'route':
        accepted = accepted and response.get('result', {}).get('requested_route_verified') is True
    return 0 if accepted else 1

if __name__ == '__main__':
    raise SystemExit(main())
