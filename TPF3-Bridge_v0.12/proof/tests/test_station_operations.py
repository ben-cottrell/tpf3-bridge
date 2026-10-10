import copy
import unittest
from dataclasses import replace
from railproof.model import Visit
from railstation.operations import schedule_station
from railstation.checks import check_result
from station_support import station,case,fixture

class StationOperatingTests(unittest.TestCase):
    def test_normal_complete_visits_pass_independent_checker(self):
        for f in ('isolated','a_to_b','b_to_a'):
            vs,r=case(f);self.assertEqual(r['scheduled_visits'],len(vs));self.assertEqual(r['independent_check']['status'],'pass')
    def test_simultaneous_normal_arrivals_are_preserved(self):
        vs,_=case();vs=[replace(v,requested_entry_ms=0) for v in vs[:2]]
        r=schedule_station(station()[1],vs)
        self.assertEqual([a['entry_ms'] for a in r['assignments']],[0,0])
    def test_no_automatic_cross_bank_use_in_nominal(self):
        self.assertEqual(case('a_to_b')[1]['total_recovery_legs'],0)
    def test_a_closure_isolated_retains_missing_demand(self):
        vs,r=case('isolated','bank_a_platforms_closed');self.assertEqual(r['unscheduled_visits'],len(vs)//2)
        self.assertFalse(r['all_required_scheduled'])
    def test_a_link_recovers_a_closure(self):
        vs,r=case('a_to_b','bank_a_platforms_closed');self.assertTrue(r['all_required_scheduled'])
        self.assertEqual(r['total_recovery_legs'],len(vs))
    def test_a_link_does_not_recover_b_closure(self):
        self.assertEqual(case('a_to_b','bank_b_platforms_closed')[1]['unscheduled_visits'],2)
    def test_b_link_recovers_b_closure(self):
        self.assertTrue(case('b_to_a','bank_b_platforms_closed')[1]['all_required_scheduled'])
    def test_fan_loss_differs_from_entry_loss(self):
        self.assertTrue(case('a_to_b','a_fan_closed')[1]['all_required_scheduled'])
        self.assertFalse(case('a_to_b','a_arrival_closed')[1]['all_required_scheduled'])
    def test_forbidden_recovery_remains_forbidden(self):
        r=case('a_to_b','a_bank_closed_recovery_forbidden')[1]
        self.assertEqual(r['unscheduled_visits'],2);self.assertEqual(r['total_recovery_legs'],0)
    def test_300m_trains_choose_long_platforms(self):
        r=case('a_to_b','synthetic_300m')[1]
        self.assertTrue(all(a['platform_id'][-1] in '34' for a in r['assignments']))
    def test_manufacturer_full_unit_length_is_not_rounded(self):
        r=case('isolated','published_long_units')[1]
        self.assertTrue(all(a['train_length_m']==242.6 for a in r['assignments']))
    def test_all_closed_not_low_delay_success(self):
        r=case('a_to_b','all_platforms_closed')[1]
        self.assertEqual(r['total_departure_delay_ms'],0);self.assertEqual(r['unscheduled_visits'],4)
        self.assertFalse(r['all_required_completed_within_horizon'])
    def test_zero_budget_is_exhaustion_not_impossibility(self):
        r=case('a_to_b','zero_budget')[1]
        self.assertTrue(all(x['reason']=='search_exhausted' for x in r['rejected']))
    def test_short_horizon_preserves_all_states(self):
        vs,r=case('a_to_b','short_horizon',6)
        self.assertEqual(sum(r['scheduled_states_at_horizon'].values())+r['unscheduled_visits'],len(vs))
        self.assertGreater(r['scheduled_residual_at_horizon'],0)
    def test_missing_exit_invalidates_free_berth(self):
        c=copy.deepcopy(station('a_to_b')[1]);del c.routes['A:B1:out']
        vs=[case()[0][0]]
        r=schedule_station(c,vs,closed=set(c.platforms)-{'B1'})
        self.assertFalse(r['all_required_scheduled'])
    def test_storage_claim_covers_departure_wait(self):
        r=case('a_to_b','bank_a_platforms_closed',3)[1]
        for a in r['assignments']:
            h=next(c for c in a['claims'] if c['resource']=='berth:'+a['platform_id'])
            self.assertEqual(h['start_ms'],a['entry_ms']);self.assertEqual(h['end_ms'],a['exit_clear_ms'])
    def test_stock_reuse_waits_for_predecessor_and_cycle(self):
        v=case()[0][0];w=replace(v,id='later',predecessor=v.id,external_cycle_ms=600000,requested_entry_ms=1000,planned_departure_ms=701000)
        r=schedule_station(station('a_to_b')[1],[v,w]);a,b=r['assignments']
        self.assertGreaterEqual(b['entry_ms'],a['exit_clear_ms']+600000)
        self.assertEqual(check_result(station('a_to_b')[1],[v,w],r)['status'],'pass')
    def test_unknown_platform_closure_rejected(self):
        with self.assertRaises(ValueError):schedule_station(station()[1],case()[0],closed={'P999'})
    def test_unknown_edge_closure_rejected(self):
        with self.assertRaises(ValueError):schedule_station(station()[1],case()[0],closed_edges={'invisible_link'})
    def test_wrong_boundary_permission_rejected(self):
        c=copy.deepcopy(station()[1]);c.routes['A:A1:in']=replace(c.routes['A:A1:in'],start='B:ARRIVAL')
        with self.assertRaises(ValueError):schedule_station(c,case()[0])
    def test_wrong_mode_and_boolean_flags_rejected(self):
        for kw in ({'mode':'moving_block_magic'},{'allow_recovery':1},{'horizon_ms':True}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):schedule_station(station()[1],case()[0],**kw)
    def test_empty_stock_still_claims_resources(self):
        r=case('a_to_b','nominal',6)[1]
        ecs=[a for a in r['assignments'] if a['outgoing_kind']=='empty_stock']
        self.assertEqual(len(ecs),2);self.assertTrue(all(a['claims'] for a in ecs))
    def test_scenario_hash_is_family_independent(self):
        self.assertEqual(case('isolated')[1]['scenario_hash'],case('a_to_b')[1]['scenario_hash'])
    def test_matched_sections_keep_nominal_timings_equal(self):
        delay=[case(f,'nominal',6)[1]['total_departure_delay_ms'] for f in ('isolated','a_to_b','b_to_a')]
        self.assertEqual(len(set(delay)),1)
