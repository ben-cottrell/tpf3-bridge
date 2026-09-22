import copy,json,tempfile,unittest
from pathlib import Path
from railclear.model import digest
from railcompact.demo import run,read_fixture,scenario
from railcompact.assessment import decisions
from compact_support import fixture

class CompactDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        f=fixture();f['pairs']=2;f['search_domain']={'first_fan_toe_x_m':[205.],'fan_turnout_span_m':[70.],'fan_toe_step_m':[75.]}
        f['scenarios']=['nominal','bank_a_platforms_closed','bank_b_platforms_closed','a_fan_closed','b_fan_closed']
        cls.f=f;cls.path=cls.root/'fixture.json';cls.path.write_text(json.dumps(f));cls.out=cls.root/'out'
        cls.summary=run(cls.path,cls.out)
        cls.assessments={g:json.loads((cls.out/f'{g}__assessment.json').read_text()) for g in ('isolated','a_to_b','b_to_a','scissors')}
        cls.results={g:{s:json.loads((cls.out/f'{g}__{s}.json').read_text()) for s in f['scenarios']} for g in cls.assessments}
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def invalid(self,mutation):
        f=copy.deepcopy(self.f);mutation(f);p=self.root/'invalid.json';p.write_text(json.dumps(f))
        with self.assertRaises(ValueError):read_fixture(p)
    def test_replay_byte_identical(self):
        second=self.root/'replay';run(self.path,second)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),sorted(p.name for p in second.iterdir()))
        for p in self.out.iterdir():self.assertEqual(p.read_bytes(),(second/p.name).read_bytes(),p.name)
    def test_twenty_small_fixture_comparisons(self):
        self.assertEqual(self.summary['comparison_count'],20);self.assertTrue(self.summary['all_independent_checks_passed'])
    def test_matching_scenario_hashes(self):
        for sc in self.f['scenarios']:self.assertEqual(len({self.results[f][sc]['scenario_hash'] for f in self.results}),1)
    def test_assessment_identity_matches_result(self):
        for g,a in self.assessments.items():
            for r in self.results[g].values():self.assertEqual(r['candidate_assessment_hash'],digest(a));self.assertEqual(r['compile_hash'],a['compile_hash'])
    def test_original_plan_pass_not_full_approval(self):
        self.assertTrue(self.summary['plan_contract_passed_all']);self.assertFalse(self.summary['full_original_brief_satisfied']);self.assertFalse(self.summary['construction_authorised'])
    def test_no_brief_changes_claimed(self):
        for a in self.assessments.values():self.assertEqual(a['changed_brief_fields'],[])
    def test_uk_profile_remains_blocked(self):
        for a in self.assessments.values():self.assertNotEqual(a['strict_UK_input_gate']['UK_profile_gate'],'pass');self.assertFalse(a['construction_authorised'])
    def test_both_bank_recovery_selects_scissors(self):
        p=decisions(self.results,self.assessments,['nominal','bank_a_platforms_closed','bank_b_platforms_closed']);self.assertEqual(p['offline_candidate'],'scissors');self.assertFalse(p['construction_authorised'])
    def test_normal_only_avoids_unneeded_complexity(self):self.assertEqual(decisions(self.results,self.assessments,['nominal'])['offline_candidate'],'isolated')
    def test_no_fan_recovery_candidate(self):self.assertIsNone(decisions(self.results,self.assessments,['nominal','a_fan_closed','b_fan_closed'])['offline_candidate'])
    def test_failed_plan_not_selected_despite_operations(self):
        a=copy.deepcopy(self.assessments);r=copy.deepcopy(self.results)
        for g in a:
            a[g]['plan_contract_passed']=False
            for row in r[g].values():row['candidate_assessment_hash']=digest(a[g])
        self.assertIsNone(decisions(r,a,['nominal'])['offline_candidate'])
    def test_stale_compile_hash_rejected(self):
        r=copy.deepcopy(self.results);r['scissors']['nominal']['compile_hash']='stale'
        with self.assertRaises(ValueError):decisions(r,self.assessments,['nominal'])
    def test_stale_assessment_hash_rejected(self):
        r=copy.deepcopy(self.results);r['scissors']['nominal']['candidate_assessment_hash']='stale'
        with self.assertRaises(ValueError):decisions(r,self.assessments,['nominal'])
    def test_missing_or_duplicate_scenario_rejected(self):
        for req in ([],['nominal','nominal'],['missing']):
            with self.subTest(req=req),self.assertRaises(ValueError):decisions(self.results,self.assessments,req)
    def test_unverified_result_rejected(self):
        r=copy.deepcopy(self.results);r['scissors']['nominal']['independent_check']['status']='fail'
        with self.assertRaises(ValueError):decisions(r,self.assessments,['nominal'])
    def test_different_demand_hash_rejected(self):
        r=copy.deepcopy(self.results);r['scissors']['nominal']['scenario_hash']='different'
        with self.assertRaises(ValueError):decisions(r,self.assessments,['nominal'])
    def test_unknown_fixture_field_rejected(self):self.invalid(lambda f:f.update({'execute_python':'anything'}))
    def test_wrong_fixture_version_rejected(self):self.invalid(lambda f:f.update({'schema_version':'0.6.0'}))
    def test_wrong_fidelity_rejected(self):self.invalid(lambda f:f.update({'fidelity':'certified_uk'}))
    def test_unsafe_scenario_name_rejected(self):self.invalid(lambda f:f.update({'scenarios':['../../bad']}))
    def test_duplicate_scenario_rejected(self):self.invalid(lambda f:f.update({'scenarios':['nominal','nominal']}))
    def test_boolean_budget_rejected(self):self.invalid(lambda f:f.update({'geometry_budget':True}))
    def test_empty_grid_rejected(self):self.invalid(lambda f:f.update({'search_domain':{}}))
    def test_empty_search_retains_explicit_status(self):
        f=copy.deepcopy(self.f);f['geometry_budget']=0;p=self.root/'zero.json';p.write_text(json.dumps(f))
        r=run(p,self.root/'zero');self.assertEqual(r['status'],'search_exhausted');self.assertEqual(r['comparison_count'],0)
    def test_all_selected_routes_have_vehicle_audit(self):
        for g,a in self.assessments.items():
            comp=json.loads((self.out/f'{g}__compiled.json').read_text());v=json.loads((self.out/f'{g}__vehicle.json').read_text())
            self.assertEqual({r['route_id'] for r in v['routes']},set(comp['routes']));self.assertEqual(v['resource_mutations'],[])
    def test_scissors_pair_studies_have_expected_spatial_contacts(self):
        v=json.loads((self.out/'scissors__vehicle.json').read_text());self.assertEqual(len(v['pairs']),23)
        pair=next(r for r in v['pairs'] if r['route_a']=='A:B1:in' and r['route_b']=='B:A4:in');self.assertEqual(pair['status'],'sampled_body_contact')
    def test_unknown_scenario_rejected(self):
        with self.assertRaises(ValueError):scenario(self.f,'unknown')
