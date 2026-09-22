"""Local corridor design and optional in-memory mock execution; no game writes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'proof'))

MANIFEST = 'run.json'
SUCCESS = ('design_ready', 'mock_verified')
OUTCOMES = (*SUCCESS, 'invalid_input', 'incomplete_search', 'no_accepted_candidate',
            'mock_failed', 'unexpected_failure')
CONNECTION_OUTCOMES = ('connection_ready', 'unsupported_input', 'invalid_input',
                       'failed_checks', 'no_accepted_candidate', 'incomplete_search',
                       'unexpected_failure')
SUCCESS = (*SUCCESS, 'connection_ready')
CONNECTION_SCOPE = 'Offline plain-track connection fit only; no game construction or adapter execution.'
CONNECTION_DOMAIN = ('Level, zero grade/cant; positive start-tangent forward span >1e-7 m; '
                     'relative end heading within +/-45 degrees; map x/y within +/-1e7 m; '
                     'line or at most two joined quintics, arbitrary map translation/rotation.')
ARTIFACTS = {'fixture.json', 'context.json', 'search.json', 'candidate.json',
             'plan.json', 'execution.json', 'summary.json', 'error.log'}


def atomic_json(path, value):
    """Publish complete metadata from a same-directory temporary file."""
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_run(directory, *, verify=False):
    """Read recorded evidence, never import or invoke the railway engine."""
    unavailable = dict(status='status_unavailable', search_status=None, evaluated=0,
                       accepted=0, candidate_hash=None, paths={}, blockers=[],
                       game_constructed=False)
    if verify:
        unavailable = dict(status='verification_unavailable', changed_files=[],
                           missing_files=[], blockers=[], game_constructed=False)
    try:
        root = directory.resolve()
        path = root / MANIFEST
        if path.stat().st_size > 65536:
            raise ValueError('manifest exceeds metadata limit')

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate metadata key')
                result[key] = value
            return result

        record = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
        if (not isinstance(record, dict) or record.get('schema_version') != '1.0'
                or record.get('game_constructed') is not False
                or record.get('mode') not in ('design', 'mock', 'connection')
                or record.get('record_state') not in ('unfinished', 'final')):
            raise ValueError('unsupported or malformed manifest')
        if record['record_state'] == 'unfinished':
            if verify:
                raise ValueError('unfinished manifest has no finalized verification data')
            return {**unavailable, 'status': 'run_incomplete',
                    'mode': record['mode'], 'record_state': 'unfinished',
                    **({'scope': CONNECTION_SCOPE} if record['mode'] == 'connection' else {}),
                    'blockers': ['Run was not finalized; current process state is unknown.']}
        summary = record['summary']
        hashes = record['artifact_sha256']
        identity = record['input_identity']
        is_hash = lambda v: isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v)
        connection = record['mode'] == 'connection'
        outcomes = CONNECTION_OUTCOMES if connection else OUTCOMES
        search_states = ((None, 'not_started', 'complete', 'budget_exhausted') if connection else
                         (None, 'search_exhausted', 'grid_complete_candidates_found', 'grid_complete_no_candidate'))
        if (not isinstance(summary, dict) or summary.get('status') not in outcomes
                or not {'search_status', 'candidate_hash'} <= summary.keys()
                or summary.get('game_constructed') is not False
                or not isinstance(identity, dict)
                or not isinstance(identity.get('source'), str)
                or (identity.get('sha256') is not None and not is_hash(identity['sha256']))
                or not isinstance(hashes, dict) or not set(hashes) <= ARTIFACTS
                or not all(is_hash(h) for h in hashes.values())
                or summary.get('paths') != {name: name for name in hashes}
                or 'summary.json' not in hashes
                or not isinstance(summary.get('blockers'), list)
                or len(summary['blockers']) > 8
                or not all(isinstance(b, str) and len(b) <= 400 for b in summary['blockers'])
                or len(json.dumps(summary['blockers']).encode('utf-8')) > 2400
                or any(type(summary.get(k)) is not int or not 0 <= summary[k] <= 400 for k in ('evaluated', 'accepted'))
                or summary['accepted'] > summary['evaluated']
                or summary.get('search_status') not in search_states
                or (summary.get('candidate_hash') is not None and not is_hash(summary['candidate_hash']))):
            raise ValueError('malformed final metadata')
        if connection:
            if (summary.get('scope') != CONNECTION_SCOPE
                    or (summary['status'] != 'connection_ready' and summary['candidate_hash'] is not None)
                    or (summary['status'] == 'incomplete_search' and summary['search_status'] != 'budget_exhausted')
                    or (summary['status'] == 'no_accepted_candidate' and
                        (summary['search_status'] != 'complete' or summary['accepted'] != 0))):
                raise ValueError('inconsistent connection metadata')
        if summary['status'] in SUCCESS:
            required = {'fixture.json', 'context.json', 'search.json', 'candidate.json'}
            if record['mode'] == 'mock':
                required |= {'plan.json', 'execution.json'}
            if (not required <= hashes.keys() or not is_hash(identity.get('sha256'))
                    or not is_hash(summary.get('candidate_hash')) or not summary['accepted']
                    or summary['search_status'] != ('complete' if connection else 'grid_complete_candidates_found')
                    or summary['status'] != ('connection_ready' if connection else
                                            'mock_verified' if record['mode'] == 'mock' else 'design_ready')
                    or (record['mode'] == 'mock' and summary.get('mock_status') != 'mock_verified')
                    or summary['blockers']):
                raise ValueError('inconsistent success metadata')
        changed_files, missing_files = [], []
        for name, digest in sorted(hashes.items()):
            artifact = root / name
            try:
                if artifact.resolve().parent != root or not artifact.is_file():
                    # Missing paths are distinct from replacements and unsafe links.
                    artifact.lstat()
                    changed_files.append(name)
                elif file_hash(artifact) != digest:
                    changed_files.append(name)
            except FileNotFoundError:
                missing_files.append(name)
        if verify:
            return {**unavailable,
                    **({'scope': CONNECTION_SCOPE} if connection else {}),
                    'status': 'integrity_failed' if changed_files or missing_files else 'integrity_verified',
                    'changed_files': changed_files, 'missing_files': missing_files}
        if changed_files or missing_files:
            raise ValueError('missing or changed saved evidence')
        # Whitelist summary fields; do not echo arbitrary content from imported records.
        result = {key: summary[key] for key in unavailable}
        result.update(mode=record['mode'], record_state='final',
                      input_sha256=identity.get('sha256'),
                      paths={name: str(root / name) for name in (*hashes, MANIFEST)})
        if connection:
            result['scope'] = CONNECTION_SCOPE
        return compact_connection_summary(result) if connection else result
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        unavailable['blockers'] = ['Run metadata/evidence missing, malformed or unsupported; legacy folders are not rewritten.']
        return unavailable


def initial_summary():
    return dict(status='invalid_input', search_status=None, evaluated=0,
                accepted=0, candidate_hash=None, paths={}, blockers=[],
                game_constructed=False,
                mock_scope='Fresh in-memory instance; no persistence of mock world or cross-process replay protection.')


def status(run):
    """Return saved run status without writing evidence or invoking the engine."""
    return inspect_run(Path(run))


def verify(run):
    """Return saved artifact integrity without writing evidence or invoking the engine."""
    return inspect_run(Path(run), verify=True)


def compact_connection_summary(summary):
    """Bound API output as well as CLI output; full evidence stays on disk."""
    if len(json.dumps(summary, ensure_ascii=True).encode('utf-8')) >= 4095:
        return {**summary, 'paths': {name: name for name in summary['paths']},
                'paths_relative_to': 'caller-selected output directory'}
    return summary


def connect(input_path, output):
    """Fit a local connection using L06/L07 and publish read-only run evidence."""
    summary = initial_summary()
    summary.pop('mock_scope')
    summary['scope'] = CONNECTION_SCOPE
    out = manifest = None

    def save(name, value):
        path = out / name
        if path.exists():
            raise FileExistsError(path)
        atomic_json(path, value)
        summary['paths'][name] = str(path)

    try:
        source = Path(input_path)
        destination = Path(output).resolve()
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            summary.update(status='output_refused', blockers=['Output destination must be an empty directory or absent.'])
            return compact_connection_summary(summary)
        destination.mkdir(parents=True, exist_ok=True)
        out = destination
        manifest = dict(schema_version='1.0', record_state='unfinished', mode='connection',
                        input_identity={'source': str(source), 'sha256': None}, game_constructed=False)
        atomic_json(out / MANIFEST, manifest)
        from bridge_connection import load_connection, fit_connection, UnsupportedConnection
        record = None
        try:
            # Parse the exact saved bytes so identity cannot race a changing input file.
            raw = source.read_bytes()
            manifest['input_identity']['sha256'] = hashlib.sha256(raw).hexdigest()
            with (out / 'fixture.json').open('xb') as stream:
                stream.write(raw)
            summary['paths']['fixture.json'] = str(out / 'fixture.json')
            record = load_connection(out / 'fixture.json')
        except UnsupportedConnection as exc:
            result = dict(status='unsupported_input', search_status='not_started', evaluated=0,
                          candidate=None, candidate_checks=[], checks=[{'pass': False, 'reason': str(exc)}],
                          game_constructed=False)
        except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as exc:
            result = dict(status='invalid_input', search_status='not_started', evaluated=0,
                          candidate=None, candidate_checks=[], checks=[{'pass': False, 'reason': str(exc)}],
                          game_constructed=False)
        else:
            result = fit_connection(record)
        save('search.json', result)
        # Capture after fitting: includes transitive loaded geometry helpers, not just wrappers.
        sources = {ROOT / 'bridge_cli.py', ROOT / 'bridge_app.py', ROOT / 'bridge_connection.py'}
        for module in tuple(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                if path.is_relative_to(ROOT / 'proof') and path.suffix == '.py':
                    sources.add(path)
        save('context.json', {
            'source_sha256': {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(sources)},
            'input_identity': manifest['input_identity'],
            'provenance': record['provenance'] if record is not None else None,
            'provenance_scope': 'Caller-supplied source_refs, project_choices and assumptions; not verified game or UK evidence.',
            'supported_domain': CONNECTION_DOMAIN, 'scope': CONNECTION_SCOPE,
            'selection_policy': 'minimum conservative upper length, then grid index; finite family only',
            'check_scope': 'Endpoint position/tangent/curvature, G2 joins, forward regularity, continuous region hulls, curvature and length bounds; floating-point kernel guards, not interval certification.',
            'unresolved': ['No global feasibility claim', 'No terrain, collision, station or specialist certification',
                           'Native game API, geometry and topology unprobed'],
            'game_constructed': False,
        })
        accepted = sum(row['pass'] is True for row in result['candidate_checks'])
        summary.update(status=result['status'], search_status=result['search_status'],
                       evaluated=result['evaluated'], accepted=accepted)
        if result['status'] == 'connection_ready':
            selected = result['candidate_checks'][result['selected_index']]
            required = {'regularity', 'endpoints', 'joins', 'region', 'curvature', 'length'}
            if (result['search_status'] != 'complete' or result['evaluated'] != result['required_candidates']
                    or not result['candidate'] or not selected['pass']
                    or not required <= selected['checks'].keys()
                    or not all(check['pass'] is True for check in selected['checks'].values())
                    or not all(check['pass'] is True for check in result['checks'])):
                summary.update(status='failed_checks', blockers=['Fit did not supply complete passing evidence; see search.json.'])
            else:
                save('candidate.json', result['candidate'])
                summary['candidate_hash'] = file_hash(out / 'candidate.json')
        else:
            summary['blockers'] = ['Connection outcome: ' + result['status'] + '; see fixture.json and search.json.']
    except Exception:
        summary.update(status='unexpected_failure', candidate_hash=None,
                       blockers=['Unexpected failure; inspect local error log if available.'])
        log_error(out, summary)
    # KeyboardInterrupt/SystemExit deliberately leave an unfinished atomic record.
    if out is not None:
        try:
            save('summary.json', summary)
            manifest.update(record_state='final',
                            summary={**summary, 'paths': {name: name for name in summary['paths']}},
                            artifact_sha256={name: file_hash(out / name) for name in summary['paths']})
            atomic_json(out / MANIFEST, manifest)
            summary['paths'][MANIFEST] = str(out / MANIFEST)
        except Exception:
            summary.update(status='unexpected_failure', candidate_hash=None,
                           blockers=['Could not finalize run metadata; saved status may be incomplete.'])
            log_error(out, summary)
    return compact_connection_summary(summary)


def design(fixture, output, mock_execute=False):
    """Design into an empty output directory and return a summary without printing.

    Paths accept strings or os.PathLike objects. Mock execution uses a fresh
    in-memory world; no game construction or persistent mock world is claimed.
    """
    summary = initial_summary()
    out = None
    manifest = None

    def save(name, value):
        path = out / name
        if path.exists():
            raise FileExistsError(path)
        atomic_json(path, value)
        summary['paths'][name] = str(path)

    try:
        fixture_path = Path(fixture)
        from railcorridor.planning import parse_json, validate_fixture, search, objective
        destination = Path(output).resolve()
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            summary.update(status='output_refused', blockers=['Output destination must be an empty directory or absent.'])
        else:
            destination.mkdir(parents=True, exist_ok=True)
            out = destination
            manifest = dict(schema_version='1.0', record_state='unfinished',
                            mode='mock' if mock_execute else 'design',
                            input_identity={'source': str(fixture_path), 'sha256': None},
                            game_constructed=False)
            atomic_json(out / MANIFEST, manifest)
            try:
                fixture = validate_fixture(parse_json(fixture_path))
                manifest['input_identity']['sha256'] = file_hash(fixture_path)
            except (ValueError, TypeError, KeyError, OSError, OverflowError) as exc:
                summary['blockers'] = ['Invalid fixture: ' + str(exc)[:400]]
            else:
                save('fixture.json', fixture)
                # Preserve implementation and UK source provenance without changing the schema.
                sources = {ROOT / 'bridge_cli.py', ROOT / 'bridge_app.py', ROOT / 'evidence/uk_parameters.json'}
                sources.update(Path(m.__file__).resolve() for n, m in tuple(sys.modules.items())
                               if n.startswith(('railcorridor.', 'railops.')) and getattr(m, '__file__', None))
                if mock_execute:
                    from railcorridor.adapter import compile_plan, MockAdapter, execute
                    sources.add(ROOT / 'proof/railcorridor/adapter.py')
                save('context.json', {
                    'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(sources)},
                    'fixture_source_sha256': hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                    'selection_policy': 'minimise (objective[2], objective[3], candidate_hash); not a global optimum',
                    'scope': 'Fixed x-parallel boundary tangents, synthetic terrain and existing profile inputs; no arbitrary track-stub fitting.',
                    'mock_scope': summary['mock_scope'],
                    'unresolved': ['Full UK assessment and specialist certification', 'Real game API, geometry and topology unprobed'],
                    'game_constructed': False,
                })
                result = search(fixture)
                save('search.json', result)
                summary.update(search_status=result['status'], evaluated=result['evaluated'], accepted=result['accepted'])
                if result['status'] == 'search_exhausted':
                    summary.update(status='incomplete_search', blockers=['Candidate budget exhausted; no candidate selected or executed.'])
                elif not result['accepted']:
                    summary.update(status='no_accepted_candidate', blockers=['Completed grid has no accepted candidate; see search.json.'])
                elif result['status'] != 'grid_complete_candidates_found':
                    summary.update(status='incomplete_search', blockers=['Search did not report completion.'])
                else:
                    chosen = min((c for c in result['candidates'] if c['accepted_for_reference_comparison']),
                                 key=lambda c: (objective(c)[2], objective(c)[3], c['candidate_hash']))
                    save('candidate.json', chosen)
                    summary.update(status='design_ready', candidate_hash=chosen['candidate_hash'])
                    if mock_execute:
                        plan = compile_plan(chosen, fixture)
                        save('plan.json', plan)
                        execution = execute(plan, MockAdapter())
                        save('execution.json', execution)
                        summary['mock_status'] = execution['status']
                        summary['status'] = 'mock_verified' if execution['status'] == 'mock_verified' else 'mock_failed'
                        if summary['status'] == 'mock_failed':
                            summary['blockers'] = ['Mock verification failed; see execution.json for reasons and retained effects.']
    except ValueError as exc:
        # Path errors can occur before the output directory is acquired.
        if out is None:
            summary['blockers'] = [str(exc)[:400]]
        else:
            summary.update(status='unexpected_failure', blockers=['Unexpected failure; inspect local error log if available.'])
            log_error(out, summary)
    except Exception:
        summary.update(status='unexpected_failure', blockers=['Unexpected failure; inspect local error log if available.'])
        log_error(out, summary)

    if out is not None:
        try:
            save('summary.json', summary)
            manifest.update(record_state='final',
                            summary={**summary, 'paths': {name: name for name in summary['paths']}},
                            artifact_sha256={name: file_hash(out / name) for name in summary['paths']})
            atomic_json(out / MANIFEST, manifest)
            summary['paths'][MANIFEST] = str(out / MANIFEST)
        except Exception:
            summary.update(status='unexpected_failure', blockers=['Could not finalize run metadata; saved status may be incomplete.'])
            log_error(out, summary)
    return summary


def log_error(out, summary):
    if out is None:
        return
    try:
        path = out / 'error.log'
        with path.open('x', encoding='utf-8') as stream:
            stream.write(traceback.format_exc())
        summary['paths']['error.log'] = str(path)
    except OSError:
        pass
