"""Signal-only envelope scope and existing replacement/continuation guards."""
import copy
import json
import tempfile
import unittest
from unittest.mock import patch

from bridge_operator import Operator,validate_plan,signal_envelope,no_step_effects
from test_signal_batch import Fake,plan,edge


def wide():
    p=plan();p['ports']={};p['region']={'min':[-10,-10,-10],'max':[10000,10000,1000]}
    return p


class WideSignalTests(unittest.TestCase):
    def test_wide_empty_ports_native_batch_replacements_keep_aliases(self):
        with tempfile.TemporaryDirectory() as td:
            c=Fake();op=Operator(runs=td,client=c);p=wide();run=op.plan(p)['run']
            r=op.execute(run);self.assertEqual(r['status'],'built',r)
            s=json.loads((op.path(run)/'state.json').read_text())
            self.assertEqual([s['bindings'][n]['edges'][0]['id'] for n in ('road','alias')],[101,101])
            self.assertEqual(sum(o=='operating_control' for o,q in c.calls),1)
            self.assertEqual(len(s['signal_chains']['blocks']['placements']),3)

    def test_mixed_construction_and_port_routes_retain_old_limits(self):
        p=wide();p['ports']={'a':{'position':[0,0,0],'direction':[1,0]}}
        p['steps'].append({'name':'seed','kind':'stub','port':'a','length':10})
        with self.assertRaisesRegex(ValueError,'region limited'):validate_plan(p)
        p=wide();p['routes']=[{'name':'route','source':'a','target':'b'}]
        with self.assertRaisesRegex(ValueError,'named ports'):validate_plan(p)
        p=wide();p['steps']=[]
        with self.assertRaises(ValueError):validate_plan(p)

    def test_outside_or_missing_snapshot_rejects_before_calls(self):
        for problem in ('endpoint','bowed_control','missing','nonfinite','unknown_chain'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as td:
                c=Fake();op=Operator(runs=td,client=c);p=wide();row=p['bindings']['road']['edges'][0]
                if problem=='endpoint':row['p1'][0]=10001
                elif problem=='bowed_control':row['t0'][1]=40000
                elif problem=='missing':row.pop('t1')
                elif problem=='nonfinite':row['t0'][0]=float('inf')
                else:p['steps'][0]['chains']=['absent']
                with self.assertRaises(ValueError):op.plan(p)
                self.assertEqual(c.calls,[])

    def test_fresh_bound_preflight_checks_all_steps_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            c=Fake();op=Operator(runs=td,client=c);p=wide()
            p['bindings']['later']={'edges':[edge(2)]}
            p['steps'].append(p['steps'][0]|{'name':'later_blocks','chains':['later']})
            run=op.plan(p)['run']
            def refreshed(client,binding):
                rows=copy.deepcopy(binding['edges'])
                if rows[0]['id']==2:rows[0]['t0'][1]=40000
                return rows
            with patch('bridge_operator.fresh_binding',side_effect=refreshed):r=op.execute(run)
            self.assertEqual(r['status'],'needs_attention');self.assertIn('outside authorised envelope',r['error'])
            self.assertFalse(any(o=='operating_control' for o,q in c.calls))

    def test_placement_check_independent_of_control_guard(self):
        p=wide();row=p['bindings']['road']['edges'][0]
        # Inject a contradictory sampler observation to verify placement checking
        # independently of the conservative control-hull check.
        with patch('bridge_operator.cubic',return_value=([10001,0,2],[1,0,0])),patch('bridge_operator.signal_chain_locations',return_value=([{'edge_index':0,'parameter':.5}],700)):
            with self.assertRaisesRegex(ValueError,'sampled signal placement outside'):signal_envelope([row],p['steps'][0],p['region'])

    def test_declared_step_edge_placement_and_region_bounds_preserved(self):
        p=wide();p['steps']=[p['steps'][0]|{'name':'s'+str(i)} for i in range(33)]
        with self.assertRaisesRegex(ValueError,'at most32'):validate_plan(p)
        p=wide();p['steps'][0]['max_count']=65
        with self.assertRaises(ValueError):validate_plan(p)
        p=wide();p['region']['max'][1]=p['region']['min'][1]
        with self.assertRaisesRegex(ValueError,'ordered region'):validate_plan(p)
        p=wide();p['bindings']['road']['edges']=[edge(i+1) for i in range(65)]
        with self.assertRaisesRegex(ValueError,'1..64'):validate_plan(p)

    def test_stopped_remaining_continuation_does_not_replay_successful_chain(self):
        with tempfile.TemporaryDirectory() as td:
            c=Fake();op=Operator(runs=td,client=c);p=wide();p['steps'].append(p['steps'][0]|{'name':'second'})
            original=c.request;preparations=0
            def reject_second(o,q,**kw):
                nonlocal preparations
                if 'signal_batch' in q:
                    preparations+=1;c.accepted=preparations==1
                return original(o,q,**kw)
            run=op.plan(p)['run']
            with patch.object(c,'request',side_effect=reject_second):r=op.execute(run)
            self.assertEqual(r['status'],'needs_attention');s=json.loads((op.path(run)/'state.json').read_text())
            self.assertEqual(list(s['steps']),['blocks']);self.assertTrue(no_step_effects(s))
            c.accepted=True;child=op.continue_plan(run,'remaining')['run']
            before=sum(o=='operating_control' for o,q in c.calls)
            self.assertEqual(op.execute(child)['status'],'built')
            self.assertEqual(sum(o=='operating_control' for o,q in c.calls)-before,1)
            self.assertEqual([x['name'] for x in json.loads((op.path(child)/'plan.json').read_text())['steps']],['second'])


if __name__=='__main__':unittest.main()
