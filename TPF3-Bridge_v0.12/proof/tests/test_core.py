from dataclasses import replace
import unittest
from railproof.model import Platform, Visit, Claim, conflict, legal_traversal, strict_record, validate_stock
from railproof.engine import Calendar, Budget, BudgetExhausted, clearance_ms, route_resources, fit_visit, schedule


def visit(**kwargs):
    defaults = dict(id='v1',stock_id='s1',inbound_group='A',outbound_group='A',length_m=160,
                    requested_entry_ms=0,planned_departure_ms=308000,dwell_ms=60000,
                    turnback_ms=180000,dispatch_ms=20000)
    defaults.update(kwargs)
    return Visit(**defaults)


def platforms():
    return [Platform('pa','0','A',260),Platform('pb','17','B',320)]


class ModelTests(unittest.TestCase):
    def test_labels_do_not_determine_count(self):
        p=platforms()
        self.assertEqual(len(p),2)
        r=schedule(p,[visit()],'banked')
        r2=schedule([replace(p[0],label='1000'),p[1]],[visit()],'banked')
        self.assertEqual(r,r2)

    def test_duplicate_physical_ids_rejected(self):
        with self.assertRaises(ValueError): schedule([platforms()[0]]*2,[visit()],'banked')

    def test_train_fit_includes_both_margins(self):
        p=Platform('p','1','A',260)
        self.assertTrue(p.fits(250))
        self.assertFalse(p.fits(250.001))

    def test_overlength_has_no_opportunity(self):
        r=schedule(platforms(),[visit(length_m=500)],'common')
        self.assertEqual(r['rejected'][0]['reason'],'no_legal_complete_opportunity')

    def test_diamond_has_no_turning_connection(self):
        pairs={('west','east'),('north','south')}
        self.assertTrue(legal_traversal('west','east',pairs))
        self.assertFalse(legal_traversal('west','north',pairs))
        self.assertFalse(legal_traversal('east','west',pairs))

    def test_pedestrian_link_does_not_create_train_route(self):
        rail={('low_in','low_out'),('high_in','high_out')}
        pedestrian={('low_platform','high_platform')}
        self.assertTrue(legal_traversal('low_platform','high_platform',pedestrian))
        self.assertFalse(legal_traversal('low_in','high_out',rail))

    def test_strict_record_rejects_unknown(self):
        with self.assertRaises(ValueError): strict_record(Platform,dict(id='p',label='1',bank='A',usable_length_m=200,magic=True))

    def test_nan_rejected(self):
        with self.assertRaises(ValueError): visit(length_m=float('nan'))

    def test_boolean_length_rejected(self):
        with self.assertRaises(ValueError): visit(length_m=True)

    def test_fractional_millisecond_rejected(self):
        with self.assertRaises(ValueError): visit(requested_entry_ms=0.5)

    def test_negative_readiness_rejected(self):
        with self.assertRaises(ValueError): visit(turnback_ms=-1)

    def test_invalid_group_rejected(self):
        with self.assertRaises(ValueError): visit(inbound_group='C')

    def test_empty_identity_rejected(self):
        with self.assertRaises(ValueError): visit(id=' ')

    def test_stock_duplicate_root_rejected(self):
        with self.assertRaises(ValueError): validate_stock([visit(),visit(id='v2')])

    def test_stock_fork_rejected(self):
        root=visit()
        a=visit(id='a',predecessor='v1',external_cycle_ms=1)
        b=visit(id='b',predecessor='v1',external_cycle_ms=1)
        with self.assertRaises(ValueError): validate_stock([root,a,b])

    def test_stock_missing_predecessor_rejected(self):
        with self.assertRaises(ValueError): validate_stock([visit(predecessor='missing',external_cycle_ms=1)])

    def test_stock_cycle_rejected(self):
        a=visit(predecessor='v2',external_cycle_ms=1)
        b=visit(id='v2',predecessor='v1',external_cycle_ms=1)
        with self.assertRaises(ValueError): validate_stock([a,b])

    def test_stock_length_cannot_change_without_activity(self):
        with self.assertRaises(ValueError): validate_stock([visit(),visit(id='v2',length_m=200,predecessor='v1',external_cycle_ms=1)])

    def test_external_cycle_must_be_explicit(self):
        with self.assertRaises(ValueError): visit(predecessor='v0')


class ResourceTests(unittest.TestCase):
    def test_touching_intervals_compatible(self):
        self.assertFalse(conflict(Claim('r',0,100,'a'),Claim('r',100,200,'b')))

    def test_one_millisecond_overlap_conflicts(self):
        self.assertTrue(conflict(Claim('r',0,101,'a'),Claim('r',100,200,'b')))

    def test_same_point_state_can_overlap(self):
        self.assertFalse(conflict(Claim('point:1524',0,100,'a','N'),Claim('point:1524',0,100,'b','N')))

    def test_different_point_state_conflicts(self):
        self.assertTrue(conflict(Claim('point:1524',0,100,'a','N'),Claim('point:1524',0,100,'b','R')))

    def test_same_points_do_not_remove_track_conflict(self):
        self.assertTrue(conflict(Claim('running_track',0,100,'a'),Claim('running_track',0,100,'b')))

    def test_linked_ends_use_one_logical_lock(self):
        end_to_group={'1524A':'1524','1524B':'1524','1524C':'1524'}
        self.assertTrue(conflict(Claim(end_to_group['1524A'],0,10,'a','N'),Claim(end_to_group['1524C'],0,10,'b','R')))

    def test_tail_not_front_controls_surrogate(self):
        self.assertEqual(clearance_ms(160,160,8,0,0),40000)
        self.assertGreater(clearance_ms(160,160,8,0,0),20000)

    def test_clearance_rounds_up(self):
        self.assertEqual(clearance_ms(1,1,3,0,0),667)

    def test_invalid_speed_rejected(self):
        with self.assertRaises(ValueError): clearance_ms(100,100,0)

    def test_calendar_reserve_is_atomic_in_memory(self):
        c=Calendar();c.reserve([Claim('a',0,10,'one')])
        with self.assertRaises(ValueError):c.reserve([Claim('a',5,20,'two'),Claim('b',1,3,'two')])
        self.assertNotIn('b',c.claims)

    def test_self_conflict_rejected(self):
        c=Calendar()
        with self.assertRaises(ValueError):c.reserve([Claim('a',0,10,'one'),Claim('a',9,20,'one')])

    def test_earliest_finds_event_end(self):
        c=Calendar();c.reserve([Claim('a',0,100,'one')])
        t,w=c.earliest(('a',),50,20,'two',Budget(10))
        self.assertEqual(t,100);self.assertEqual(w[0]['owner'],'one')

    def test_earliest_matches_bruteforce_integer_time(self):
        c=Calendar();c.reserve([Claim('a',3,7,'one'),Claim('a',12,17,'two'),Claim('b',18,21,'three')])
        for start in range(25):
            for duration in (1,4,8):
                actual,_=c.earliest(('a','b'),start,duration,'new',Budget(100))
                expected=next(t for t in range(start,60) if not c.conflicts([Claim(r,t,t+duration,'new') for r in ('a','b')]))
                self.assertEqual(actual,expected)

    def test_budget_raises(self):
        with self.assertRaises(BudgetExhausted): Calendar().earliest(('a',),0,1,'v',Budget(0))


class CompleteVisitTests(unittest.TestCase):
    def test_single_visit_exact_times(self):
        r=schedule(platforms(),[visit()],'banked');a=r['assignments'][0]
        self.assertEqual((a['entry_ms'],a['berthed_ms'],a['departure_ms'],a['exit_clear_ms']),(0,48000,308000,356000))

    def test_arrival_without_exit_rejected(self):
        r=schedule(platforms(),[visit(outbound_group='B')],'banked')
        self.assertEqual(r['scheduled_visits'],0)
        self.assertEqual(r['rejected'][0]['reason'],'no_legal_complete_opportunity')

    def test_linked_family_can_supply_exit(self):
        r=schedule(platforms(),[visit(outbound_group='B')],'linked')
        self.assertEqual(r['scheduled_visits'],1)
        self.assertEqual(r['cross_bank_legs'],1)

    def test_turnback_not_replaced_by_dwell(self):
        r=schedule(platforms(),[visit(planned_departure_ms=0)],'banked')
        a=r['assignments'][0]
        self.assertEqual(a['departure_ms']-a['berthed_ms'],260000)

    def test_blocked_departure_holds_berth(self):
        c=Calendar();c.reserve([Claim('portal:A:out',300000,500000,'other')])
        a=fit_visit(visit(),platforms()[0],'banked',c,Budget(100),0,1000000)
        self.assertEqual(a.departure_ms,500000)
        berth=next(x for x in a.claims if x.resource.startswith('berth:'))
        self.assertEqual((berth.start_ms,berth.end_ms),(0,548000))

    def test_berth_conflict_reconsiders_arrival(self):
        c=Calendar();c.reserve([Claim('berth:pa',200000,600000,'other')])
        a=fit_visit(visit(),platforms()[0],'banked',c,Budget(100),0,1000000)
        self.assertEqual(a.entry_ms,600000)
        self.assertGreaterEqual(a.departure_ms,a.berthed_ms+260000)

    def test_zero_budget_not_infeasibility_proof(self):
        r=schedule(platforms(),[visit()],'banked',evaluation_budget=0)
        self.assertEqual(r['rejected'][0]['reason'],'search_exhausted')

    def test_wait_budget_distinguished(self):
        vs=[visit(),visit(id='v2',stock_id='s2')]
        r=schedule([platforms()[0]],vs,'banked',max_wait_ms=0)
        self.assertEqual(r['rejected'][0]['reason'],'not_scheduled_within_entry_wait_budget')

    def test_independent_banks_simultaneous(self):
        v2=visit(id='v2',stock_id='s2',inbound_group='B',outbound_group='B')
        r=schedule(platforms(),[visit(),v2],'banked')
        self.assertEqual([a['entry_ms'] for a in r['assignments']],[0,0])

    def test_common_resource_serializes_entries(self):
        v2=visit(id='v2',stock_id='s2',inbound_group='B',outbound_group='B')
        r=schedule(platforms(),[visit(),v2],'common')
        self.assertGreaterEqual(r['assignments'][1]['entry_ms'],48000)

    def test_replay_deterministic(self):
        vs=[visit(),visit(id='v2',stock_id='s2')]
        self.assertEqual(schedule(platforms(),vs,'common'),schedule(platforms(),vs,'common'))

    def test_horizon_does_not_drop_work(self):
        r=schedule(platforms(),[visit()],'banked',horizon_ms=100000)
        self.assertEqual((r['required_visits'],r['scheduled_visits'],r['completed_within_horizon'],r['scheduled_residual_at_horizon']),(1,1,0,1))
        self.assertFalse(r['all_required_completed_within_horizon'])

    def test_closure_never_drops_required_count(self):
        r=schedule(platforms(),[visit()],'banked',closed={'pa'})
        self.assertEqual(r['required_visits'],1);self.assertEqual(r['unscheduled_visits'],1)

    def test_stock_readiness_propagates(self):
        v2=visit(id='v2',predecessor='v1',external_cycle_ms=600000,planned_departure_ms=400000)
        r=schedule(platforms(),[visit(),v2],'banked')
        a,b=r['assignments']
        self.assertGreaterEqual(b['entry_ms'],a['exit_clear_ms']+600000)

    def test_failed_predecessor_blocks_successor(self):
        vs=[visit(),visit(id='v2',predecessor='v1',external_cycle_ms=10000)]
        r=schedule(platforms(),vs,'banked',closed={'pa'})
        self.assertEqual(r['rejected'][1]['reason'],'predecessor_not_scheduled')

    def test_empty_stock_still_occupies_resources(self):
        r=schedule(platforms(),[visit(outgoing_kind='empty_stock')],'banked')
        self.assertEqual(r['assignments'][0]['outgoing_kind'],'empty_stock')
        self.assertTrue(any(c['resource']=='portal:A:out' for c in r['assignments'][0]['claims']))

    def test_unknown_closure_rejected(self):
        with self.assertRaises(ValueError):schedule(platforms(),[visit()],'banked',closed={'missing'})

    def test_invalid_family_rejected(self):
        with self.assertRaises(ValueError):route_resources('magic','A','A','in')
