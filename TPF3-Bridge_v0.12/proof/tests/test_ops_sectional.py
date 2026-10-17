from dataclasses import replace
import unittest
from railgeom.patterns import FanSpec, GeometryProfile, build_fan
from railgeom.compiler import compile_assembly
from railproof.model import Visit, Claim
from railproof.engine import Calendar, Budget, BudgetExhausted
from railops.access import AccessSpec, build_dual_access
from railops.motion import MotionProfile
from railops.sectional import compile_leg, footprints, earliest_leg
from railops.operations import schedule


def visit(i=1,entry=0,length=160,**changes):
    return replace(Visit(f'N{i}',f'S{i}','A','A',length,entry,entry+480000,60000,180000,20000),**changes)

class SectionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assembly=build_dual_access();cls.compiled=compile_assembly(cls.assembly)
    def test_eight_directed_routes(self):
        self.assertEqual(len(self.compiled.routes),8)
        for pid in self.compiled.platforms:
            self.assertEqual(self.compiled.routes[pid+':in'].start,'ARRIVAL')
            self.assertEqual(self.compiled.routes[pid+':out'].end,'DEPARTURE')
    def test_not_an_unrestricted_Y(self):
        self.assertEqual(self.assembly.network.enumerate_paths('ARRIVAL','DEPARTURE'),[])
    def test_shared_access_body(self):
        for r in self.compiled.routes.values():
            self.assertIn('component_body:ACCESS',[x.resource for x in r.requirements])
    def test_access_states_differ(self):
        a={x.resource:x.state for x in self.compiled.routes['P1:in'].requirements}
        b={x.resource:x.state for x in self.compiled.routes['P1:out'].requirements}
        self.assertEqual(a['control:ACCESS'],'N');self.assertEqual(b['control:ACCESS'],'R')
    def test_joins_are_valid(self):self.assembly.network.validate()
    def test_lead_does_not_fit(self):
        with self.assertRaises(ValueError):build_dual_access(access=AccessSpec(lead_length_m=100))
    def test_independent_lead_proxy(self):
        with self.assertRaises(ValueError):build_dual_access(access=AccessSpec(departure_offset_m=3.4,turnout_span_m=20))
    def test_invalid_access(self):
        with self.assertRaises(ValueError):AccessSpec(branch_slope=.3)
        with self.assertRaises(ValueError):AccessSpec(lead_length_m=float('nan'))
    def test_footprints_cover_requirements(self):
        for r in self.compiled.routes.values():
            fs=footprints(self.compiled,r)
            self.assertEqual({(f.resource,f.state) for f in fs},{(x.resource,x.state) for x in r.requirements})
            self.assertTrue(all(0<=f.start_m<f.end_m<=r.length_upper_m+1e-7 for f in fs))
    def test_wrong_route_origin_rejected(self):
        with self.assertRaises(ValueError):footprints(self.compiled,replace(self.compiled.routes['P1:in'],length_upper_m=1))
    def test_reversed_chainage_starts_at_platform(self):
        route=self.compiled.routes['P4:out']
        first=route.segments[0]
        self.assertEqual(first['entry_chainage_interval_m'],[0,0])
        self.assertNotEqual(first['edge_id'],self.compiled.routes['P4:in'].segments[0]['edge_id'])
    def test_arrival_stops_inside_storage(self):
        l=compile_leg(self.compiled,'P1:in',160,'in')
        self.assertAlmostEqual(l.motion.distance_m,l.route_length_m+160)
        self.assertAlmostEqual(l.motion.at(l.motion.duration_s)[1],0)
    def test_departure_tail_clear_continuation_is_explicit(self):
        l=compile_leg(self.compiled,'P1:out',160,'out')
        self.assertFalse(l.motion.stop_at_end)
        self.assertIn('unmodelled',l.export()['boundary_assumption'])
    def test_every_lock_acquired_at_activation(self):
        l=compile_leg(self.compiled,'P4:in',160,'in')
        self.assertTrue(all(c.start_ms==0 for c in l.relative_claims))
    def test_release_after_tail_not_front(self):
        l=compile_leg(self.compiled,'P4:in',160,'in')
        for x in l.occupancy:
            self.assertGreater(x['tail_clears_ms'],x['front_enters_ms'])
            self.assertEqual(x['lock_released_ms'],x['tail_clears_ms']+l.profile.release_ms)
    def test_sectional_never_later_than_same_whole_leg(self):
        for d in ('in','out'):
            s=compile_leg(self.compiled,'P4:'+d,160,d)
            w=compile_leg(self.compiled,'P4:'+d,160,d,mode='whole_route')
            self.assertEqual(s.motion,w.motion)
            sw={(c.resource,c.state):c.end_ms for c in w.relative_claims}
            self.assertTrue(all(c.end_ms<=sw[c.resource,c.state] for c in s.relative_claims))
            self.assertTrue(any(c.end_ms<sw[c.resource,c.state] for c in s.relative_claims))
    def test_whole_route_constant_release(self):
        l=compile_leg(self.compiled,'P1:in',160,'in',mode='whole_route')
        self.assertEqual(len({c.end_ms for c in l.relative_claims}),1)
    def test_final_resource_does_not_release_before_stop(self):
        l=compile_leg(self.compiled,'P1:in',160,'in')
        self.assertEqual(l.release_end_ms,l.motion_end_ms+l.profile.release_ms)
    def test_longer_train_releases_later(self):
        a=compile_leg(self.compiled,'P1:in',160,'in');b=compile_leg(self.compiled,'P1:in',240,'in')
        self.assertGreater(b.release_end_ms,a.release_end_ms)
    def test_zero_setup_release(self):
        l=compile_leg(self.compiled,'P1:in',160,'in',MotionProfile(setup_ms=0,release_ms=0))
        self.assertEqual(l.motion_end_ms,l.release_end_ms)
    def test_bad_leg_requests(self):
        for args in [('P1:in',160,'out'),('missing',160,'in'),('P1:in',0,'in')]:
            with self.assertRaises(ValueError):compile_leg(self.compiled,*args)
        with self.assertRaises(ValueError):compile_leg(self.compiled,'P1:in',160,'in',mode='moving_block')
    def test_exact_release_endpoint(self):
        l=compile_leg(self.compiled,'P1:in',160,'in');c=Calendar()
        c.reserve([Claim(l.relative_claims[0].resource,0,1000,'block',None)])
        t,w=earliest_leg(c,l,0,'train',Budget(100))
        self.assertEqual(t,1000);self.assertTrue(w)
    def test_no_budget(self):
        l=compile_leg(self.compiled,'P1:in',160,'in')
        with self.assertRaises(BudgetExhausted):earliest_leg(Calendar(),l,0,'train',Budget(0))
    def test_negative_activation(self):
        l=compile_leg(self.compiled,'P1:in',160,'in')
        with self.assertRaises(ValueError):l.claims_at(-1,'train')
    def test_complete_visit(self):
        r=schedule(self.compiled,[visit()]);a=r['assignments'][0]
        self.assertEqual(r['scheduled_visits'],1)
        self.assertGreaterEqual(a['departure_ms'],a['berthed_ms']+260000)
        self.assertGreaterEqual(a['departure_ms'],a['incoming_release_end_ms'])
    def test_independent_interval_check(self):
        r=schedule(self.compiled,[visit(i,i*90000) for i in range(1,7)])
        cs=[c for a in r['assignments'] for c in a['claims']]
        for i,a in enumerate(cs):
            for b in cs[i+1:]:
                if a['resource']==b['resource'] and max(a['start_ms'],b['start_ms'])<min(a['end_ms'],b['end_ms']):
                    self.assertIsNotNone(a['state']);self.assertEqual(a['state'],b['state'])
    def test_platform_held_through_waiting_departure(self):
        r=schedule(self.compiled,[visit(planned_departure_ms=1000000)])
        a=r['assignments'][0];b=next(c for c in a['claims'] if c['resource'].startswith('berth:'))
        self.assertEqual((b['start_ms'],b['end_ms']),(a['entry_ms'],a['exit_clear_ms']))
    def test_fit_boundary_and_overlength(self):
        self.assertEqual(schedule(self.compiled,[visit(length=250)])['scheduled_visits'],1)
        self.assertEqual(schedule(self.compiled,[visit(length=250.001)])['unscheduled_visits'],1)
    def test_all_closed_retains_demand(self):
        r=schedule(self.compiled,[visit()],closed=set(self.compiled.platforms))
        self.assertEqual(r['unscheduled_visits'],1);self.assertFalse(r['all_required_scheduled'])
    def test_unknown_closed_id(self):
        with self.assertRaises(ValueError):schedule(self.compiled,[visit()],closed={'bad'})
    def test_mismatch_service_group(self):
        r=schedule(self.compiled,[visit(inbound_group='B')]);self.assertEqual(r['unscheduled_visits'],1)
    def test_zero_evaluation_budget_retains_demand(self):
        r=schedule(self.compiled,[visit()],evaluation_budget=0)
        self.assertEqual(r['rejected'][0]['reason'],'search_exhausted')
    def test_horizon_conservation(self):
        r=schedule(self.compiled,[visit(i,i*100000) for i in range(1,7)],horizon_ms=600000)
        self.assertEqual(sum(r['scheduled_states_at_horizon'].values()),r['scheduled_visits'])
        self.assertEqual(r['completed_within_horizon']+r['scheduled_residual_at_horizon']+r['unscheduled_visits'],r['required_visits'])
    def test_not_yet_due_separate_from_queue(self):
        r=schedule(self.compiled,[visit(entry=2000000)],horizon_ms=1000000)
        self.assertEqual(r['scheduled_states_at_horizon']['not_yet_due'],1)
        self.assertEqual(r['scheduled_states_at_horizon']['waiting_outside_model'],0)
    def test_stock_dependency(self):
        r=schedule(self.compiled,[visit(),visit(2,stock_id='S1',predecessor='N1',external_cycle_ms=600000)])
        a,b=r['assignments'];self.assertGreaterEqual(b['entry_ms'],a['exit_clear_ms']+600000)
    def test_unsupported_one_lead_model_rejected(self):
        with self.assertRaises(ValueError):schedule(compile_assembly(build_fan()),[visit()])
    def test_deterministic(self):
        vs=[visit(i,i*100000) for i in range(1,4)]
        self.assertEqual(schedule(self.compiled,vs),schedule(self.compiled,vs))
    def test_compiler_hash_unchanged_by_operation(self):
        before=self.compiled.compile_hash;schedule(self.compiled,[visit()])
        self.assertEqual(before,compile_assembly(self.assembly).compile_hash)
    def test_invalid_mode_or_horizon(self):
        with self.assertRaises(ValueError):schedule(self.compiled,[],mode='x')
        with self.assertRaises(ValueError):schedule(self.compiled,[],horizon_ms=0)
