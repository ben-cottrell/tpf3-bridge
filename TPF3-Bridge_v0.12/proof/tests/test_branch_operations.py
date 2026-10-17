from copy import deepcopy
from dataclasses import replace
import unittest
from railbranch.geometry import *
from railbranch.operations import *
from railbranch.demo import scenarios,decide
from railclear.catalogue import read_json

class BranchOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js={m:build(mode=m) for m in MODES};cls.f=read_json(ROOT/'proof/branch_fixtures/release.json');cls.f['repetitions']=1
        cls.p=default_performance();cls.ss={s['id']:s for s in scenarios(cls.f,cls.js['flat'],242.6)}
        cls.rs={(m,k):schedule(j,s,cls.p) for m,j in cls.js.items() for k,s in cls.ss.items()}
    def test_crossing_resource_only_flat(self):
        self.assertIn('crossing:RETURN_OVER_EAST',compile_resources(self.js['flat'])['resources'])
        self.assertNotIn('crossing:RETURN_OVER_EAST',compile_resources(self.js['flyover'])['resources'])
    def test_merge_resources_present_in_every_form(self):
        for j in self.js.values():
            r=next(r for r in compile_resources(j)['route_pairs'] if (r['a'],r['b'])==('main_west','branch_in'))
            self.assertIn('track:west_merge_exit',r['incompatible_shared_resources']);self.assertIn('body:M:SYNTH_IMPORT_T40',r['incompatible_shared_resources'])
    def test_normal_main_directions_do_not_conflict(self):
        for j in self.js.values():self.assertEqual(compile_resources(j)['route_pairs'][0]['incompatible_shared_resources'],[])
    def test_branch_directions_do_not_invent_crossing(self):
        for j in self.js.values():self.assertEqual(compile_resources(j)['route_pairs'][-1]['incompatible_shared_resources'],[])
    def test_footprints_inside_actual_routes(self):
        for j in self.js.values():
            for r in compile_resources(j)['routes'].values():
                for f in r['footprints']:self.assertTrue(0<=f['s0_m']<f['s1_m']<=r['length_m']+1e-7)
    def test_reverse_crossing_footprint_order(self):
        j=self.js['flat'];c=compile_resources(j);fp=next(f for f in c['routes']['branch_in']['footprints'] if f['resource'].startswith('crossing'))
        self.assertGreater(fp['s0_m'],3000);self.assertLess(fp['s1_m'],4000)
    def test_tail_not_front_releases(self):
        t=leg(compile_resources(self.js['flat']),'branch_in',242.6,self.p)
        for c in t['claims']:
            self.assertGreater(c['tail_clear_ms'],c['front_entry_ms']);self.assertGreaterEqual(c['end_ms'],c['tail_clear_ms'])
    def test_train_length_changes_end_not_identity(self):
        c=compile_resources(self.js['flat']);a=leg(c,'branch_in',162,self.p);b=leg(c,'branch_in',242.6,self.p)
        self.assertGreater(b['clear_ms'],a['clear_ms']);self.assertEqual([x['resource'] for x in a['claims']],[x['resource'] for x in b['claims']])
    def test_crossing_pulse_delay_removed_only_when_separated(self):
        self.assertGreater(self.rs[('flat','crossing_pulse')]['total_entry_delay_ms_scheduled_only'],0)
        for m in ('flyover','diveunder'):self.assertEqual(self.rs[(m,'crossing_pulse')]['total_entry_delay_ms_scheduled_only'],0)
    def test_merge_pulse_still_delayed(self):
        for m in MODES:self.assertGreater(self.rs[(m,'merge_pulse')]['total_entry_delay_ms_scheduled_only'],200000)
    def test_blocked_exit_not_hidden(self):
        for m in MODES:
            r=self.rs[(m,'downstream_blocked')];self.assertIn('track:west_merge_exit',r['conflict_witness_counts']);self.assertGreater(r['total_entry_delay_ms_scheduled_only'],1000000)
    def test_return_closure_retains_required_trip(self):
        r=self.rs[('flyover','branch_return_closed')];self.assertEqual((r['required'],r['scheduled'],r['unscheduled']),(4,3,1))
    def test_downstream_closure_affects_both_inputs(self):
        r=self.rs[('flyover','shared_west_exit_closed')];self.assertEqual(r['unscheduled'],2)
    def test_short_horizon_keeps_residuals(self):
        r=self.rs[('flyover','short_horizon')];self.assertEqual((r['completed'],r['residual'],r['unscheduled']),(0,4,0))
    def test_zero_budget_is_not_geometry_failure(self):
        r=self.rs[('flat','zero_budget')];self.assertEqual(r['unscheduled'],4);self.assertEqual({v['reason'] for v in r['unserved']},{'search_exhausted'})
    def test_zero_wait_has_distinct_reason(self):
        r=self.rs[('flyover','zero_entry_wait')];self.assertEqual(r['unserved'][0]['reason'],'entry_wait_limit')
    def test_every_generated_result_checked(self):self.assertTrue(all(r['independent_check']['passed'] for r in self.rs.values()))
    def test_same_scenario_across_modes(self):
        for k in self.ss:self.assertEqual(len({self.rs[(m,k)]['scenario_hash'] for m in MODES}),1)
    def test_grade_model_limit_not_concealed(self):
        self.assertFalse(self.rs[('flyover','nominal')]['grade_sensitive_performance'])
    def test_negative_train_and_time_rejected(self):
        for key,value in [('train_length_m',-1),('requested_ms',-1),('requested_ms',1.5),('requested_ms',True)]:
            s=deepcopy(self.ss['nominal']);s['requests'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):schedule(self.js['flat'],s)
    def test_duplicate_request_rejected(self):
        s=deepcopy(self.ss['nominal']);s['requests'].append(s['requests'][0])
        with self.assertRaises(ValueError):schedule(self.js['flat'],s)
    def test_unknown_closure_rejected(self):
        s=deepcopy(self.ss['nominal']);s['closures']=['missing']
        with self.assertRaises(ValueError):schedule(self.js['flat'],s)
    def test_unknown_requested_route_rejected(self):
        s=deepcopy(self.ss['nominal']);s['requests'][0]['route']='invented_turn'
        with self.assertRaises(ValueError):schedule(self.js['flat'],s)
    def test_input_not_mutated(self):
        s=deepcopy(self.ss['nominal']);before=deepcopy(s);schedule(self.js['flat'],s);self.assertEqual(s,before)
    def test_checker_detects_dropped_demand(self):
        r=deepcopy(self.rs[('flat','nominal')]);r['assignments'].pop()
        self.assertFalse(check_result(self.js['flat'],self.ss['nominal'],self.p,r)['passed'])
    def test_checker_detects_missing_track_claim(self):
        r=deepcopy(self.rs[('flat','nominal')]);r['assignments'][0]['claims'].pop()
        self.assertIn('altered_or_missing_geometry_claim',check_result(self.js['flat'],self.ss['nominal'],self.p,r)['errors'])
    def test_checker_detects_changed_point_state(self):
        r=deepcopy(self.rs[('flat','nominal')]);c=next(c for a in r['assignments'] for c in a['claims'] if c['state'] is not None);c['state']='wrong'
        self.assertFalse(check_result(self.js['flat'],self.ss['nominal'],self.p,r)['passed'])
    def test_checker_detects_wrong_tail_time(self):
        r=deepcopy(self.rs[('flat','nominal')]);r['assignments'][0]['clear_ms']-=100
        self.assertIn('wrong_tail_clear',check_result(self.js['flat'],self.ss['nominal'],self.p,r)['errors'])
    def test_checker_detects_stale_candidate(self):
        r=deepcopy(self.rs[('flat','nominal')]);r['candidate_hash']='wrong'
        self.assertFalse(check_result(self.js['flat'],self.ss['nominal'],self.p,r)['passed'])
    def test_checker_detects_lost_block(self):
        r=deepcopy(self.rs[('flat','downstream_blocked')]);r['fixed_block_claims']=[]
        self.assertIn('altered_fixed_blocks',check_result(self.js['flat'],self.ss['downstream_blocked'],self.p,r)['errors'])
    def test_completion_precedes_delay_choice(self):
        p=decide(self.js,self.rs,'zero_budget');self.assertEqual(p['alternatives'],[])
    def test_no_zero_delay_merge_winner(self):
        p=decide(self.js,self.rs,'merge_pulse',max_total_delay_ms=0);self.assertEqual(p['alternatives'],[])
    def test_raised_lowered_not_arbitrarily_ranked(self):
        p=decide(self.js,self.rs,'crossing_pulse',max_total_delay_ms=0)
        self.assertEqual({r['mode'] for r in p['alternatives']},{'flyover','diveunder'});self.assertFalse(p['construction_authorised'])
    def test_decision_rejects_modified_result(self):
        rs=deepcopy(self.rs);rs[('flat','nominal')]['completed']=999
        with self.assertRaises(ValueError):decide(self.js,rs,'nominal')
    def test_deterministic_replay(self):
        self.assertEqual(schedule(self.js['flat'],self.ss['nominal'],self.p),self.rs[('flat','nominal')])
