from dataclasses import replace
from pathlib import Path
import copy
import json
import tempfile
import unittest
from railproof.model import Visit,Claim,conflict
from railproof.engine import Calendar,Budget
from railgeom.patterns import *
from railgeom.compiler import compile_assembly
from railgeom.operations import *
from railgeom.search import fit_crossover
from railgeom.demo import read_fixture,run

FIXTURE=Path(__file__).resolve().parents[1]/'geometry_fixtures'/'release.json'


def visit(id='v',**kwargs):
    return Visit(**{'id':id,'stock_id':id,'inbound_group':'A','outbound_group':'A','length_m':160.,
            'requested_entry_ms':0,'planned_departure_ms':370000,'dwell_ms':60000,'turnback_ms':180000,
            'dispatch_ms':20000,**kwargs})


class GeometryOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=compile_assembly(build_crossover());cls.f=compile_assembly(build_fan())

    def test_two_through_routes_start_together(self):
        r=schedule_routes(self.c,[{'id':x,'route':route,'requested_ms':0,'train_length_m':160.}
                                 for x,route in [('a','lower_through'),('b','upper_through')]])
        self.assertEqual([x['start_ms'] for x in r['requests']],[0,0])

    def test_crossing_waits_for_through_movement(self):
        r=schedule_routes(self.c,[{'id':x,'route':route,'requested_ms':0,'train_length_m':160.}
                                 for x,route in [('a','lower_through'),('b','cross_forward')]])
        a,b=r['requests'];self.assertEqual(b['start_ms'],a['clear_ms']);self.assertTrue(b['witnesses'])

    def test_longer_train_extends_tail_clear_time(self):
        r=self.c.routes['lower_through']
        self.assertEqual(duration(r,240,TimingProfile())-duration(r,160,TimingProfile()),10000)

    def test_time_uses_geometry_not_legacy_160m_template(self):
        r=self.f.routes['P1:in']
        self.assertGreater(r.length_lower_m,650)
        self.assertGreater(duration(r,160,TimingProfile()),100000)

    def test_zero_or_invalid_speed_rejected(self):
        for v in (0,-1,True,float('nan')):
            with self.subTest(value=v),self.assertRaises(ValueError):TimingProfile(speed_mps=v)

    def test_exact_interval_boundary_is_available(self):
        route=self.c.routes['cross_forward'];cal=Calendar();period=duration(route,160,TimingProfile())
        cal.reserve(make_claims(route.requirements,0,period,'a'))
        t,w=earliest(cal,route,period,period,'b',Budget(5));self.assertEqual(t,period);self.assertEqual(w,[])

    def test_earliest_matches_integer_bruteforce_oracle(self):
        route=self.c.routes['lower_through'];cal=Calendar()
        cal.reserve(make_claims(route.requirements,5,9,'x'));cal.reserve(make_claims(route.requirements,13,18,'y'))
        for requested in range(21):
            found,_=earliest(cal,route,requested,4,'new',Budget(100))
            brute=next(t for t in range(requested,40) if not cal.conflicts(make_claims(route.requirements,t,t+4,'new')))
            self.assertEqual(found,brute)

    def test_one_complete_visit(self):
        r=schedule_bank(self.f,[visit()]);a=r['assignments'][0]
        self.assertEqual(r['scheduled_visits'],1)
        self.assertGreaterEqual(a['departure_ms'],a['berthed_ms']+260000)
        self.assertGreater(a['exit_clear_ms'],a['departure_ms'])

    def test_platform_hold_is_present_across_whole_visit(self):
        a=schedule_bank(self.f,[visit()])['assignments'][0]
        resource='track:'+self.f.platforms[a['platform_id']]['storage_edge']
        c=next(c for c in a['claims'] if c['resource']==resource)
        self.assertEqual(c['start_ms'],a['entry_ms']);self.assertEqual(c['end_ms'],a['exit_clear_ms'])

    def test_departure_delay_does_not_release_berth(self):
        cal=Calendar();out=self.f.routes['P1:out']
        cal.reserve(make_claims(out.requirements,400000,1000000,'block'))
        p=Platform('P1','1','A',260,5)
        a=fit(visit(),p,self.f,cal,Budget(100),0,7200000,TimingProfile())
        self.assertGreaterEqual(a['departure_ms'],1000000)
        c=next(c for c in a['claims'] if c.resource=='track:storage_P1')
        self.assertEqual(c.end_ms,a['exit_clear_ms'])

    def test_missing_exit_rejects_free_platform(self):
        c=copy.deepcopy(self.f);del c.routes['P1:out']
        r=schedule_bank(c,[visit()],closed={'P2','P3','P4'})
        self.assertEqual(r['scheduled_visits'],0);self.assertEqual(r['rejected'][0]['reason'],'no_legal_complete_opportunity')

    def test_long_train_fit_boundary(self):
        self.assertEqual(schedule_bank(self.f,[visit(length_m=250)])['scheduled_visits'],1)
        self.assertEqual(schedule_bank(self.f,[visit(length_m=250.001)])['scheduled_visits'],0)

    def test_all_closed_does_not_drop_required_demand(self):
        r=schedule_bank(self.f,[visit()],closed=set(self.f.platforms))
        self.assertEqual(r['required_visits'],1);self.assertEqual(r['unscheduled_visits'],1)
        self.assertFalse(r['all_required_scheduled'])

    def test_unknown_platform_closure_rejected(self):
        with self.assertRaises(ValueError):schedule_bank(self.f,[visit()],closed={'invented'})

    def test_unsupported_corridor_not_silently_remapped(self):
        r=schedule_bank(self.f,[visit(inbound_group='B')])
        self.assertEqual(r['unscheduled_visits'],1)

    def test_zero_budget_not_physical_impossibility(self):
        r=schedule_bank(self.f,[visit()],evaluation_budget=0)
        self.assertEqual(r['rejected'][0]['reason'],'search_exhausted')

    def test_stock_dependency_propagates(self):
        a=visit('a',stock_id='stock',requested_entry_ms=200000,planned_departure_ms=570000)
        b=visit('b',stock_id='stock',requested_entry_ms=0,predecessor='a',external_cycle_ms=600000)
        r=schedule_bank(self.f,[b,a]);rows={a['visit_id']:a for a in r['assignments']}
        self.assertGreaterEqual(rows['b']['entry_ms'],rows['a']['exit_clear_ms']+600000)

    def test_failed_predecessor_does_not_create_stock(self):
        a=visit('a',stock_id='stock',length_m=280)
        b=visit('b',stock_id='stock',length_m=280,predecessor='a',external_cycle_ms=600000)
        r=schedule_bank(self.f,[a,b])
        self.assertEqual(r['rejected'][1]['reason'],'predecessor_not_scheduled')

    def test_short_horizon_retains_work(self):
        r=schedule_bank(self.f,[visit()],horizon_ms=1)
        self.assertEqual(r['scheduled_residual_at_horizon'],1);self.assertEqual(r['completed_within_horizon'],0)

    def test_empty_stock_still_occupies_resources(self):
        a=schedule_bank(self.f,[visit(outgoing_kind='empty_stock')])['assignments'][0]
        self.assertEqual(a['outgoing_kind'],'empty_stock');self.assertTrue(a['claims'])

    def test_all_visit_claims_independently_conflict_free(self):
        vs=[visit(str(i),requested_entry_ms=i*150000,planned_departure_ms=i*150000+370000) for i in range(8)]
        r=schedule_bank(self.f,vs);claims=[Claim(**c) for a in r['assignments'] for c in a['claims']]
        for i,a in enumerate(claims):self.assertFalse(any(conflict(a,b) for b in claims[i+1:]))
        self.assertEqual(r['scheduled_visits']+r['unscheduled_visits'],len(vs))

    def test_replay_deterministic(self):
        vs=[visit('a'),visit('b')]
        self.assertEqual(schedule_bank(self.f,vs),schedule_bank(self.f,vs))

    def test_coalescing_own_claims_preserves_hold_extent(self):
        c=coalesce([Claim('x',0,10,'a'),Claim('x',5,15,'a'),Claim('x',15,20,'a')])
        self.assertEqual(c,[Claim('x',0,20,'a')])

    def test_search_finds_candidate_without_relaxing_span(self):
        r=fit_crossover(4.5,100)
        self.assertEqual(r['status'],'candidate_found_in_enumerated_set')
        self.assertLessEqual(r['best_in_evaluated_set']['span_m'],100)
        self.assertEqual(r['evaluations'],35)

    def test_tight_search_no_candidate_not_universal_infeasibility(self):
        r=fit_crossover(4.5,70)
        self.assertEqual(r['status'],'no_candidate_in_enumerated_set')
        self.assertIsNone(r['best_in_evaluated_set'])

    def test_search_budget_preserves_exhaustion_status(self):
        r=fit_crossover(4.5,100,evaluation_budget=1)
        self.assertEqual(r['status'],'search_exhausted');self.assertEqual(r['evaluations'],1)

    def test_geometry_fixture_rejects_unlabelled_real_data(self):
        o=json.loads(FIXTURE.read_text());o['fidelity']='measured_waterloo'
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'x.json';f.write_text(json.dumps(o))
            with self.assertRaises(ValueError):read_fixture(f)

    def test_geometry_fixture_rejects_unknown_fields(self):
        o=json.loads(FIXTURE.read_text());o['crossover']['invented_api']=True
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'x.json';f.write_text(json.dumps(o))
            with self.assertRaises(ValueError):read_fixture(f)

    def test_geometry_fixture_rejects_path_in_scenario_name(self):
        o=json.loads(FIXTURE.read_text());o['scenarios'][0]['id']='../../escape'
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'x.json';f.write_text(json.dumps(o))
            with self.assertRaises(ValueError):read_fixture(f)

    def test_demo_writes_eight_scenarios_and_scoped_packet(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);r=run(FIXTURE,p)
            self.assertEqual(len(r['bank_scenarios']),8)
            self.assertEqual(len(list(p.glob('bank__*.json'))),8)
            packet=json.loads((p/'decision_packet.json').read_text())
            self.assertFalse(packet['construction_approval'])
            self.assertEqual(packet['game_status'],'not_tested')
            self.assertIsNone(r['measured_plan_credit_savings'])
