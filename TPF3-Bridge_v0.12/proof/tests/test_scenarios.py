from pathlib import Path
import json
import tempfile
import unittest
from railproof.demo import read_fixture,run
from railproof.model import Platform,Visit,strict_record,Claim,conflict
from railproof.engine import schedule

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures'


def run_case(name,family):
    o=read_fixture(FIXTURES/(name+'.json'))
    return schedule([strict_record(Platform,p) for p in o['platforms']],
                    [strict_record(Visit,v) for v in o['visits']],family,
                    closed=set(o['closed_platform_ids']),horizon_ms=o['horizon_ms'],
                    max_wait_ms=o['max_wait_ms'],evaluation_budget=o['evaluation_budget'])


class ScenarioTests(unittest.TestCase):
    def test_nominal_all_demand_scheduled(self):
        for f in ('common','banked','linked'):
            r=run_case('nominal',f)
            self.assertEqual(r['scheduled_visits'],24)
            self.assertEqual(r['completed_within_horizon'],24)

    def test_recovery_connection_has_specific_benefit(self):
        a=run_case('bank_a_platforms_closed','banked')
        b=run_case('bank_a_platforms_closed','linked')
        self.assertEqual(a['unscheduled_visits'],12)
        self.assertEqual(b['unscheduled_visits'],0)
        self.assertEqual(b['cross_bank_legs'],24)

    def test_no_recovery_use_when_unneeded(self):
        self.assertEqual(run_case('nominal','linked')['cross_bank_legs'],0)

    def test_all_case_claims_and_activity_invariants(self):
        for path in sorted(FIXTURES.glob('*.json')):
            o=read_fixture(path)
            visits={v['id']:v for v in o['visits']}
            ps={p['id']:p for p in o['platforms']}
            for f in ('common','banked','linked'):
                r=run_case(o['scenario_id'],f)
                self.assertEqual(r['scheduled_visits']+r['unscheduled_visits'],r['required_visits'])
                claims=[];assigned={a['visit_id']:a for a in r['assignments']}
                for a in r['assignments']:
                    v=visits[a['visit_id']];p=ps[a['platform_id']]
                    self.assertLessEqual(v['length_m']+2*p['margin_each_end_m'],p['usable_length_m'])
                    self.assertGreaterEqual(a['departure_ms'],a['berthed_ms']+v['dwell_ms']+v['turnback_ms']+v['dispatch_ms'])
                    self.assertGreaterEqual(a['entry_ms'],v['requested_entry_ms'])
                    self.assertNotIn(a['platform_id'],o['closed_platform_ids'])
                    if v['predecessor']:
                        self.assertGreaterEqual(a['entry_ms'],assigned[v['predecessor']]['exit_clear_ms']+v['external_cycle_ms'])
                    claims += [Claim(**c) for c in a['claims']]
                for i,a in enumerate(claims):
                    self.assertFalse(any(conflict(a,b) for b in claims[i+1:]))

    def test_short_horizon_preserves_residual(self):
        r=run_case('short_horizon','common')
        self.assertEqual(r['required_visits'],24)
        self.assertGreater(r['scheduled_residual_at_horizon'],0)

    def test_fixture_requires_fidelity(self):
        o=json.loads((FIXTURES/'nominal.json').read_text());o['fidelity']='real_waterloo'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text(json.dumps(o))
            with self.assertRaises(ValueError):read_fixture(p)

    def test_demo_outputs_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            result=run(FIXTURES,Path(d))
            self.assertEqual(result['scenario_count'],7)
            self.assertEqual(result['comparison_count'],21)
            self.assertIsNone(result['measured_plan_credit_savings'])
            self.assertEqual(len(list(Path(d).glob('*__*.json'))),21)
            self.assertTrue((Path(d)/'decision_packet.json').exists())
