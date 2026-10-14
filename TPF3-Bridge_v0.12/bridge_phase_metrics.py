"""Bounded current phase measurements over existing jobs; no execution policy."""
import copy
import json
import time

import bridge_live as live


def read(path):
    return json.loads(path.read_text())


def fit_summary(operator, run):
    """Recompute from distinct current child records, never truncated UI summaries."""
    pending=[run];seen=set();trials=additional=requests=0;complete=True
    while pending:
        ident=pending.pop()
        if ident in seen:continue
        if len(seen)>=2048:complete=False;break
        seen.add(ident)
        try:state=read(operator.path(ident)/'state.json')
        except (OSError,ValueError):complete=False;continue
        pending.extend(v['run'] for v in state.get('families',{}).values() if v.get('run'))
        pending.extend(v['run'] for v in state.get('section_runs',[]) if v.get('run'))
        if state.get('current_run'):pending.append(state['current_run'])
        # Adoption replaces the current child pointer. Its existing immutable
        # plan link retains prior work; follow only that bounded exact lineage.
        plan_path=operator.path(ident)/'plan.json'
        if plan_path.exists():
            try:
                plan=read(plan_path)
                link=plan.get('continuation')
                if link is not None:
                    parent=link['run'];operator.path(parent) # Validate exact run ID.
                    pending.append(parent)
            except (OSError,ValueError,TypeError,KeyError):complete=False
        elif state.get('plan_hash') and state.get('kind') not in ('approach','corridor'):
            complete=False
        # Completion children are not geometry fitting jobs.
        variations=state.get('fit_variations',{})
        for name in set(variations)|set(state.get('candidates',{})):
            value=variations.get(name,{})
            count=max(value.get('attempt_count',0),len(state.get('candidates',{}).get(name,[])))
            trials+=count;additional+=max(0,count-1);requests+=value.get('requests_used',0)
    return {'attachment_trials':trials,'additional_attachment_trials':additional,
            'fit_search_requests':requests,'records_examined':len(seen),'complete':complete}


class Collector:
    def __init__(self):self.counts={}

    def wrap(self,client):
        from bridge_signal_benchmark import Counted
        collector=self
        class PhaseClient(Counted):
            def __getattr__(self,name):return getattr(self.client,name)
        if isinstance(client,Counted) and getattr(client,'_phase_collector',None) is self:return client
        wrapped=PhaseClient(client,self.counts)
        # Counted normally copies counts for benchmark persistence; production
        # wrappers for freshly discovered clients share one outermost collector.
        wrapped.counts=collector.counts;wrapped.phase='active';wrapped._phase_collector=self
        return wrapped


def invoke(operator,run,phase,callback,*,continuing=False):
    if getattr(operator,'_phase_collector',None) is not None:return callback()
    path=operator.path(run)/'state.json';state=read(path)
    measurements=state.setdefault('phase_metrics',{})
    previous=measurements.get(phase,{})
    aggregate=copy.deepcopy(previous.get('aggregate',{}))
    incomplete=aggregate.get('incomplete_invocations',0)+int(previous.get('latest_invocation',{}).get('active') is True)
    prior_complete=aggregate.get('measurement_complete',True) and incomplete==0
    aggregate.update(invocations=aggregate.get('invocations',0)+1,
                     explicit_continuations=aggregate.get('explicit_continuations',0)+int(continuing),
                     incomplete_invocations=incomplete,measurement_complete=False)
    measurements[phase]={'aggregate':aggregate,'latest_invocation':{
        'active':True,'measurement_complete':False,'outcome':'incomplete',
        'explicit_continuation':bool(continuing)}}
    live.atomic_json(path,state)
    collector=Collector();operator._phase_collector=collector
    start=time.monotonic();result=None;outcome='interrupted';complete=False
    try:
        result=callback();outcome=result.get('status','returned') if isinstance(result,dict) else 'returned'
        complete=True
        return result
    except Exception:
        outcome='raised';complete=True;raise
    finally:
        operator._phase_collector=None
        counts=collector.counts.get('active',{})
        latest={'active':False,'measurement_complete':complete,'outcome':outcome,
                'explicit_continuation':bool(continuing),
                'request_attempts':counts.get('requests',0),
                'mutation_request_attempts':counts.get('mutations',0),
                'blocking_request_wait_seconds':counts.get('native_seconds',0),
                'active_wall_seconds':time.monotonic()-start}
        # Reload instead of writing the pre-call snapshot: preserve child effects,
        # pending operation ownership, current session and continuation lineage.
        state=read(path)
        for key in ('request_attempts','mutation_request_attempts','blocking_request_wait_seconds','active_wall_seconds'):
            aggregate[key]=aggregate.get(key,0)+latest[key]
        aggregate.update(outcome=outcome,measurement_complete=prior_complete and complete,
                         incomplete_invocations=incomplete+int(not complete))
        record={'aggregate':aggregate,'latest_invocation':latest,
                'fit_summary':fit_summary(operator,run)}
        state.setdefault('phase_metrics',{})[phase]=record
        live.atomic_json(path,state)
        if isinstance(result,dict):result['measurement']={'phase':phase,**copy.deepcopy(record)}
