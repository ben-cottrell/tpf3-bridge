"""Offline current-phase accounting; no native/UI calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bridge_operator import Operator
from bridge_phase_metrics import fit_summary
from test_approach import World,brief


class Client:
    def __init__(self,path,session='test'):
        self.session=session;self.evidence=Path(path);self.journal=Path(path)/'journal.json';self.calls=[]
    def request(self,op,q,**kw):
        self.calls.append((op,q,kw))
        if q.get('fail'):raise ValueError('native failure')
        return {'status':'ok','request_id':'1','result':{}}


class PhaseTests(unittest.TestCase):
    def setup_run(self,td,client=None):
        op=Operator(runs=td,client=client or Client(td));run='a'*16
        op.path(run).mkdir();self.save(op,run,{'status':'planned','kind':'approach'})
        return op,run
    def save(self,op,run,s):
        (op.path(run)/'state.json').write_text(json.dumps(s))
    def state(self,op,run):return json.loads((op.path(run)/'state.json').read_text())

    def test_nested_public_phases_count_once_and_preserve_latest_state(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td)
            def child(*a,**kw):
                op.client().request('inspect',{},timeout=7)
                return {'status':'built'}
            def outer(*a,**kw):
                op.client().request('inspect',{'phase':'interface'})
                op.build_corridor(run)
                op.client().request('structured_chain',{'execute':True})
                s=self.state(op,run);s.update(status='built',current_child='owned',lineage={'parent':'original'},pending={'id':'unresolved'})
                self.save(op,run,s)
                op.client().request('inspect',{'phase':'export'})
                return {'status':'built'}
            with patch('bridge_approach.build',side_effect=outer),patch('bridge_corridor.build_corridor',side_effect=child):
                r=op.build_approach(run)
            m=r['measurement'];self.assertEqual(m['latest_invocation']['request_attempts'],4)
            self.assertEqual(m['latest_invocation']['mutation_request_attempts'],1)
            s=self.state(op,run);self.assertEqual(set(s['phase_metrics']),{'approach_build'})
            self.assertEqual(s['pending'],{'id':'unresolved'});self.assertEqual(s['current_child'],'owned')
            self.assertEqual(s['lineage'],{'parent':'original'});self.assertEqual(op._client.calls[1][2],{'timeout':7})

    def test_raised_request_counted_without_exception_translation(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td);failure=RuntimeError('same exception')
            def request(*a,**kw):raise failure
            with patch.object(op._client,'request',side_effect=request),patch('bridge_approach.review',side_effect=lambda *a:op.client().request('inspect',{})):
                with self.assertRaises(RuntimeError) as caught:op.review_approach(run)
            self.assertIs(caught.exception,failure)
            m=self.state(op,run)['phase_metrics']['approach_review']['latest_invocation']
            self.assertEqual(m['request_attempts'],1);self.assertEqual(m['outcome'],'raised')
            self.assertTrue(m['measurement_complete']);self.assertGreaterEqual(m['blocking_request_wait_seconds'],0)

    def test_fresh_context_clients_not_pinned_session_and_journal_forwarded(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td);op._client=None;a=Client(td,'A');b=Client(td,'B')
            def callback(*args):
                first=op.client();first.request('inspect',{});second=op.client()
                self.assertEqual(second.session,'B');self.assertEqual(second.journal,b.journal)
                self.assertIs(second.evidence,b.evidence)
                if first.session!=second.session:raise ValueError('session changed')
            with patch('bridge_operator.live.client_from_context',side_effect=[a,b]) as discover,patch('bridge_approach.build',side_effect=callback):
                with self.assertRaisesRegex(ValueError,'session changed'):op.build_approach(run)
            self.assertEqual(discover.call_count,2);self.assertIsNone(op._client)
            self.assertIs(op.client.__self__,op)

    def test_interruption_and_stale_active_entry_remain_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td)
            with patch('bridge_approach.build',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):op.build_approach(run)
            m=self.state(op,run)['phase_metrics']['approach_build']
            self.assertFalse(m['aggregate']['measurement_complete']);self.assertEqual(m['aggregate']['incomplete_invocations'],1)
            # Represents abrupt process interruption whose finally never ran.
            s=self.state(op,run);s['phase_metrics']['approach_build']['latest_invocation']['active']=True;self.save(op,run,s)
            with patch('bridge_approach.build',return_value={'status':'needs_attention'}):r=op.continue_approach(run)
            m=r['measurement'];self.assertEqual(m['aggregate']['incomplete_invocations'],2)
            self.assertFalse(m['aggregate']['measurement_complete']);self.assertTrue(m['latest_invocation']['measurement_complete'])
            self.assertEqual(m['aggregate']['explicit_continuations'],1)

    def test_full_fit_records_distinct_recomputed_not_truncated_or_accumulated(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td);families={}
            for i in range(8):
                child=f'{i:016x}';op.path(child).mkdir()
                self.save(op,child,{'status':'built','candidates':{f's{j}':[{},{}] for j in range(5)},
                    'fit_variations':{f's{j}':{'attempt_count':2,'requests_used':3} for j in range(5)}})
                families[str(i)]={'run':child,'fit':[{'attempt_count':999}]}
            families['same']={'run':'0'*16};s=self.state(op,run);s['families']=families;self.save(op,run,s)
            expected={'attachment_trials':80,'additional_attachment_trials':40,'fit_search_requests':120,'records_examined':9,'complete':True}
            self.assertEqual(fit_summary(op,run),expected);self.assertEqual(fit_summary(op,run),expected)

    def test_adopted_continuation_retains_parent_trials_without_double_count(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td);parent='b'*16;child='c'*16
            for ident,count,requests in ((parent,3,7),(child,1,2)):
                op.path(ident).mkdir()
                self.save(op,ident,{'status':'needs_attention' if ident==parent else 'built',
                    'fit_variations':{'fit':{'attempt_count':count,'requests_used':requests}},
                    'candidates':{'fit':[{}]*count}})
            (op.path(parent)/'plan.json').write_text('{}')
            (op.path(child)/'plan.json').write_text(json.dumps({'continuation':{'run':parent,'state_hash':'unchanged_parent_proof'}}))
            before=(op.path(parent)/'state.json').read_bytes()
            s=self.state(op,run);s['families']={'adopted':{'run':child},'shared':{'run':child}}
            self.save(op,run,s)
            expected={'attachment_trials':4,'additional_attachment_trials':2,'fit_search_requests':9,'records_examined':3,'complete':True}
            self.assertEqual(fit_summary(op,run),expected);self.assertEqual(fit_summary(op,run),expected)
            self.assertEqual((op.path(parent)/'state.json').read_bytes(),before)
            (op.path(parent)/'state.json').unlink()
            self.assertFalse(fit_summary(op,run)['complete'])

    def test_real_approach_cache_freshness_and_compact_measurement(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);op=Operator(runs=td,client=c);run=op.plan_approach(brief())['run']
            before=len(c.calls);r=op.build_approach(run)
            self.assertEqual(r['measurement']['latest_invocation']['request_attempts'],len(c.calls)-before)
            op.review_approach(run);before=len(c.calls);r=op.review_approach(run)
            self.assertEqual(r['checks_run'],0);self.assertEqual(r['measurement']['latest_invocation']['request_attempts'],1)
            self.assertLess(len(json.dumps(r).encode()),4096)
            c.edges[1]['t0'][1]=1;r=op.review_approach(run)
            self.assertEqual(r['status'],'needs_attention');self.assertEqual(r['checks_run'],0)

    def test_real_corridor_completion_continuation_no_replay(self):
        from test_corridor_completion import CompletionTests
        with tempfile.TemporaryDirectory() as td:
            c,op,run,roads=CompletionTests().built(td)
            op.attach_corridor_completion(run,roads);before=len(c.calls)
            r=op.complete_corridor(run)
            self.assertEqual(r['measurement']['latest_invocation']['request_attempts'],len(c.calls)-before)
            self.assertEqual(r['measurement']['latest_invocation']['mutation_request_attempts'],4)
            before=len(c.calls);r=op.complete_corridor(run,continuing=True)
            self.assertEqual(len(c.calls),before)
            self.assertEqual(r['measurement']['latest_invocation']['request_attempts'],0)
            self.assertEqual(r['measurement']['aggregate']['invocations'],2)
            self.assertEqual(r['measurement']['aggregate']['explicit_continuations'],1)
            self.assertLess(len(json.dumps(r).encode()),4096)

    def test_returned_failure_is_complete_measurement_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            op,run=self.setup_run(td)
            with patch('bridge_corridor.build_corridor',return_value={'status':'needs_attention'}):r=op.continue_corridor(run)
            self.assertTrue(r['measurement']['latest_invocation']['measurement_complete'])
            self.assertEqual(r['measurement']['latest_invocation']['outcome'],'needs_attention')
            self.assertEqual(r['measurement']['aggregate']['explicit_continuations'],1)


if __name__=='__main__':unittest.main()
