import copy
import unittest
from railstation.checks import *
from railstation.assessment import decision_packet
from station_support import station,case

class StationCheckerTests(unittest.TestCase):
    def setUp(self):
        self.c=station('a_to_b')[1];self.v,self.original=case('a_to_b');self.r=copy.deepcopy(self.original)
    def errors(self):return check_result(self.c,self.v,self.r)['errors']
    def test_valid_independent_interval_sweep(self):self.assertEqual(self.errors(),[])
    def test_wrong_compile_hash_detected(self):
        self.r['compile_hash']='wrong';self.assertIn('wrong_compile_hash',self.errors())
    def test_lost_berth_detected(self):
        a=self.r['assignments'][0];a['claims']=[c for c in a['claims'] if not c['resource'].startswith('berth:')]
        self.assertIn('unheld_storage',self.errors())
    def test_wrong_point_state_detected(self):
        a=self.r['assignments'][0]
        for c in a['claims']:
            if c['state'] is not None:c['state']='bad_state'
        self.assertIn('missing_or_wrong_route_state_at_activation',self.errors())
    def test_incompatible_overlap_detected_independently(self):
        for a in self.r['assignments'][:2]:a['claims'].append({'resource':'shared_test','start_ms':0,'end_ms':100,'owner':a['visit_id'],'state':None})
        self.assertIn('incompatible_interval_overlap',self.errors())
    def test_missing_required_work_detected(self):
        self.r['assignments'].pop();self.assertIn('demand_not_conserved',self.errors())
    def test_changed_train_length_detected(self):
        self.r['assignments'][0]['train_length_m']=1.;self.assertIn('changed_stock',self.errors())
    def test_premature_departure_detected(self):
        a=self.r['assignments'][0];a['departure_ms']=a['berthed_ms'];self.assertIn('premature_departure',self.errors())
    def test_wrong_delay_total_detected(self):
        self.r['total_departure_delay_ms']+=1;self.assertIn('wrong_delay_sum',self.errors())
    def test_false_horizon_completion_detected(self):
        self.r['completed_within_horizon']=0;self.assertIn('wrong_horizon_accounting',self.errors())
    def test_closed_edge_in_assignment_detected(self):
        self.r['closed_edges']=['A:arrival_lead'];self.assertIn('closed_route_edge',self.errors())
    def test_wrong_directional_route_detected(self):
        self.r['assignments'][0]['incoming_route']='B:B1:in';self.assertIn('invalid_complete_route',self.errors())

class StationSiteTests(unittest.TestCase):
    def test_original_site_rejected_from_actual_points(self):
        r=site_check(station()[0],[0.,-90.,1200.,90.]);self.assertEqual(r['status'],'fail');self.assertTrue(r['actual_ports_outside'])
    def test_expanded_site_is_scoped_not_authorised(self):
        r=site_check(station()[0],[-5.,-90.,2200.,90.],padding_m=1.75)
        self.assertEqual(r['status'],'pass_within_scope');self.assertFalse(r['construction_authorised'])
    def test_exact_port_mismatch_survives_large_box(self):
        r=site_check(station()[0],[-5.,-90.,2200.,90.],expected_ports={'A:ARRIVAL':[0.,-18.]})
        self.assertEqual(r['status'],'fail');self.assertEqual(len(r['required_port_mismatches']),1)
    def test_contact_with_reserved_space_is_reported(self):
        r=site_check(station()[0],[-5.,-90.,2200.,90.],reservations=[{'id':'bad','box_m':[1750.,-44.,1800.,-40.]}])
        self.assertEqual(r['status'],'fail');self.assertTrue(r['reservations'][0]['possible_rail_contacts'])
    def test_concourse_reservation_is_preserved(self):
        r=site_check(station()[0],[-5.,-90.,2200.,90.],reservations=[{'id':'concourse','box_m':[2020.,-75.,2180.,75.]}])
        self.assertEqual(r['status'],'pass_within_scope')
    def test_invalid_box_and_padding_rejected(self):
        for box,pad in (([0,0,0,1],0),([0,0,float('nan'),1],0),([False,0,1,1],0),([0,0,1,1],-1)):
            with self.subTest(box=box,pad=pad),self.assertRaises(ValueError):site_check(station()[0],box,padding_m=pad)

class StationDecisionTests(unittest.TestCase):
    def setUp(self):
        self.results={f:{s:copy.deepcopy(case(f,s)[1]) for s in ('nominal','bank_a_platforms_closed','bank_b_platforms_closed')} for f in ('isolated','a_to_b','b_to_a')}
        self.assess={f:{'compile_hash':station(f)[1].compile_hash,'original_brief_site':{'status':'fail'},'strict_UK_input_gate':{'UK_profile_gate':'not_passed'}} for f in self.results}
    def test_a_recovery_selects_complete_option_not_low_delay_shortfall(self):
        d=decision_packet(self.results,self.assess,['nominal','bank_a_platforms_closed'])
        self.assertEqual(d['operating_only_candidate'],'a_to_b');self.assertFalse(d['construction_authorised'])
    def test_b_recovery_selects_opposite_link(self):
        self.assertEqual(decision_packet(self.results,self.assess,['nominal','bank_b_platforms_closed'])['operating_only_candidate'],'b_to_a')
    def test_both_recoveries_returns_no_tested_solution(self):
        d=decision_packet(self.results,self.assess,['nominal','bank_a_platforms_closed','bank_b_platforms_closed'])
        self.assertIsNone(d['operating_only_candidate']);self.assertTrue(d['status'].startswith('no_tested'))
    def test_comparison_hash_mismatch_rejected(self):
        self.results['isolated']['nominal']['scenario_hash']='changed'
        with self.assertRaises(ValueError):decision_packet(self.results,self.assess,['nominal'])
    def test_stale_compile_result_rejected(self):
        self.assess['isolated']['compile_hash']='old'
        with self.assertRaises(ValueError):decision_packet(self.results,self.assess,['nominal'])
    def test_unverified_result_rejected(self):
        self.results['isolated']['nominal']['independent_check']['status']='fail'
        with self.assertRaises(ValueError):decision_packet(self.results,self.assess,['nominal'])
    def test_missing_or_duplicate_scenario_rejected(self):
        for names in (['absent'],['nominal','nominal'],[]):
            with self.subTest(names=names),self.assertRaises(ValueError):decision_packet(self.results,self.assess,names)
