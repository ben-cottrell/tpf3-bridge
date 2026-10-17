import copy,unittest
from railstation.checks import check_result
from railstation.operations import schedule_station
from compact_support import model,fixture,executed
from railcompact.demo import scenario

class CompactOperationsTests(unittest.TestCase):
    def test_nominal_complete_both_groups(self):
        for fam in ('isolated','a_to_b','b_to_a','scissors'):
            s,c,v,r=executed(family=fam);self.assertEqual(r['completed_within_horizon'],len(v));self.assertEqual(r['independent_check']['status'],'pass')
    def test_nominal_timing_identical_across_families(self):
        rows=[]
        for fam in ('isolated','a_to_b','b_to_a','scissors'):
            r=executed(family=fam)[3];rows.append([(a['visit_id'],a['entry_ms'],a['berthed_ms'],a['departure_ms'],a['exit_clear_ms']) for a in r['assignments']])
        for r in rows[1:]:self.assertEqual(r,rows[0])
    def test_a_closure_recovery_uses_b1_only(self):
        s,c,v,r=executed('bank_a_platforms_closed');self.assertEqual(r['scheduled_visits'],len(v))
        for a in r['assignments']:
            if a['visit_id'].startswith('A'):self.assertEqual(a['platform_id'],'B1')
    def test_b_closure_recovery_uses_a4_only(self):
        s,c,v,r=executed('bank_b_platforms_closed');self.assertEqual(r['scheduled_visits'],len(v))
        for a in r['assignments']:
            if a['visit_id'].startswith('B'):self.assertEqual(a['platform_id'],'A4')
    def test_isolated_loses_half_demand_on_bank_closure(self):
        r=executed('bank_a_platforms_closed','isolated')[3];self.assertEqual(r['unscheduled_visits'],2)
    def test_single_direction_not_promoted_to_both(self):
        self.assertEqual(executed('bank_b_platforms_closed','a_to_b')[3]['unscheduled_visits'],2)
        self.assertEqual(executed('bank_a_platforms_closed','b_to_a')[3]['unscheduled_visits'],2)
    def test_failed_a_fan_not_bypassed(self):self.assertEqual(executed('a_fan_closed')[3]['unscheduled_visits'],2)
    def test_failed_b_fan_not_bypassed(self):self.assertEqual(executed('b_fan_closed')[3]['unscheduled_visits'],2)
    def test_failed_arrival_lead_not_bypassed(self):self.assertEqual(executed('a_arrival_closed')[3]['unscheduled_visits'],2)
    def test_recovery_permission_enforced(self):self.assertEqual(executed('a_bank_closed_recovery_forbidden')[3]['unscheduled_visits'],2)
    def test_closed_recovery_platform_blocks_a(self):self.assertEqual(executed('a_bank_closed_inner_b1_closed')[3]['unscheduled_visits'],2)
    def test_long_recovery_asymmetry(self):
        self.assertEqual(executed('a_bank_closed_300m')[3]['unscheduled_visits'],2)
        self.assertEqual(executed('b_bank_closed_300m')[3]['unscheduled_visits'],0)
    def test_long_trains_only_long_boarding_intervals(self):
        s,c,v,r=executed('synthetic_300m')
        for a in r['assignments']:self.assertIn(a['platform_id'],('A3','A4','B3','B4'))
    def test_all_closed_no_fake_zero_delay_success(self):
        r=executed('all_platforms_closed')[3];self.assertEqual(r['scheduled_visits'],0);self.assertFalse(r['all_required_completed_within_horizon'])
    def test_zero_budget_retains_all_demand(self):
        r=executed('zero_budget')[3];self.assertEqual(r['unscheduled_visits'],4);self.assertFalse(r['all_required_scheduled'])
    def test_short_horizon_conserves_work(self):
        s,c,v,r=executed('short_horizon',pairs=12);self.assertEqual(r['completed_within_horizon']+r['scheduled_residual_at_horizon']+r['unscheduled_visits'],len(v))
    def test_missing_recovery_departure_not_accepted(self):
        s,c=model();c=copy.deepcopy(c);del c.routes['A:B1:out'];f=fixture();f['pairs']=2;v,kw=scenario(f,'bank_a_platforms_closed')
        self.assertEqual(schedule_station(c,v,**kw)['unscheduled_visits'],2)
    def test_closed_diamond_edges_block_recovery_only(self):
        s,c=model();f=fixture();f['pairs']=2;v,kw=scenario(f,'bank_a_platforms_closed');kw['closed_edges']={'recovery_AB','recovery_BA'}
        r=schedule_station(c,v,**kw);self.assertEqual(r['unscheduled_visits'],2);self.assertEqual(check_result(c,v,r)['status'],'pass')
    def test_tampered_diamond_lock_detected(self):
        s,c,v,r=executed('bank_a_platforms_closed');r=copy.deepcopy(r)
        for a in r['assignments']:a['claims']=[q for q in a['claims'] if q['resource']!='diamond:INNER_DIAMOND']
        self.assertEqual(check_result(c,v,r)['status'],'fail')
    def test_tampered_storage_detected(self):
        s,c,v,r=executed();r=copy.deepcopy(r);r['assignments'][0]['claims']=[q for q in r['assignments'][0]['claims'] if not q['resource'].startswith('berth:')]
        self.assertEqual(check_result(c,v,r)['status'],'fail')
    def test_actual_full_fixture_bank_closures(self):
        for name in ('bank_a_platforms_closed','bank_b_platforms_closed'):
            r=executed(name,pairs=12)[3];self.assertEqual(r['completed_within_horizon'],24);self.assertEqual(r['independent_check']['status'],'pass')
