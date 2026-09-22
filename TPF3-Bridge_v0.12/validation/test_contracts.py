from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import contract_checks as cc


def sample(name):return cc.read_json(ROOT/'contracts/examples'/f'{name}.json')
def rehash(plan):
    for op in plan['operations']:op['content_hash']=cc.digest({k:v for k,v in op.items() if k!='content_hash'})
    plan['plan_hash']=cc.digest({k:v for k,v in plan.items() if k!='plan_hash'})
    return plan

def context():
    p=sample('construction_plan');a=sample('authority_example')
    m={'schema_version':'0.12.0','manifest_id':'mock-policy-fixture','inspection_date':'2026-09-21','capabilities':[]}
    for c in p['required_capabilities']:
        m['capabilities'].append({'capability_id':c,'environment':'mock','game_build':None,'adapter_build':'contract-example-only','evidence':{'level':'demonstrated','record_refs':['synthetic-policy-fixture'],'native_symbols':[],'probe_ids':['synthetic-policy-case'],'limits_ref':None}})
    ctx={'host_resolved_authority_refs':[a['authority_ref']],'principal_ref':a['principal_ref'],'now_unix_ms':1800000000000,'current_binding':deepcopy(p['binding']),'protected_asset_refs':[]}
    return p,m,a,ctx


class Contracts(unittest.TestCase):
    def test_all_examples_validate(self):
        index=cc.read_json(ROOT/'contracts/example_index.json')['examples']
        self.assertEqual(17,len(index))
        for r in index:
            with self.subTest(r['path']):self.assertEqual([],cc.validate(r['definition'],cc.read_json(ROOT/'contracts'/r['path'])))
    def test_tool_descriptors_have_resolvable_valid_schemas(self):
        from jsonschema import Draft202012Validator
        ts=cc.read_json(ROOT/'contracts/agent_tools.json')['tools'];self.assertEqual(8,len(ts))
        self.assertEqual(len(ts),len({t['name'] for t in ts}))
        for t in ts:
            Draft202012Validator.check_schema(t['inputSchema']);Draft202012Validator.check_schema(t['outputSchema'])
            self.assertFalse(t['inputSchema']['additionalProperties'])
    def test_unknown_definition_rejected(self):
        with self.assertRaises(ValueError):cc.validate('NativeMagicBuild',{})
    def test_unknown_client_approval_field_rejected(self):
        d=sample('commitinput');d['approved']=True
        self.assertTrue(any('schema' in e for e in cc.validate('CommitInput',d)))
    def test_caller_cannot_embed_authority_in_commit(self):
        d=sample('commitinput');d['authority']=sample('authority_example')
        self.assertTrue(cc.validate('CommitInput',d))
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('{"x":1,"x":2}')
            with self.assertRaises(ValueError):cc.read_json(p)
    def test_nonfinite_and_overflow_numbers_rejected(self):
        for raw in ['{"x":NaN}','{"x":Infinity}','{"x":1e309}']:
            with self.subTest(raw),tempfile.TemporaryDirectory() as t:
                p=Path(t)/'x.json';p.write_text(raw)
                with self.assertRaises(ValueError):cc.read_json(p)
    def test_byte_and_depth_budgets(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';p.write_text('['*70+'0'+']'*70)
            with self.assertRaises(ValueError):cc.read_json(p)
            with self.assertRaises(ValueError):cc.read_json(p,max_bytes=4)
    def test_reversed_bounds_rejected(self):
        d=sample('design_brief');d['effect_region']['min_m'][0]=2000
        self.assertIn('invalid_bounds',cc.validate('DesignBrief',d))
    def test_direction_and_grade_must_agree(self):
        d=sample('design_brief');d['ports'][0]['grade']=.01
        self.assertIn('port_grade_direction_mismatch',cc.validate('DesignBrief',d))
    def test_direction_is_unit_vector(self):
        d=sample('design_brief');d['ports'][0]['forward_unit']=[2,0,0]
        self.assertIn('nonunit_port_direction',cc.validate('DesignBrief',d))
    def test_typed_units_not_interchangeable(self):
        d=sample('design_brief');d['targets']['route_speed']['unit']='m'
        self.assertIn('target_unit_mismatch',cc.validate('DesignBrief',d))
    def test_protected_delete_conflict(self):
        d=sample('design_brief');d['preservation']['permitted_delete_refs']=['existing-west']
        self.assertIn('protected_delete_conflict',cc.validate('DesignBrief',d))
    def test_snapshot_cannot_claim_missing_data_complete(self):
        d=sample('snapshot');d['capture']['missing_refs']=['missing-tile']
        self.assertIn('false_snapshot_completeness',cc.validate('Snapshot',d))
    def test_mock_cannot_be_promoted_to_game_by_label(self):
        d=cc.read_json(ROOT/'contracts/tpf3_unprobed_capabilities.json');d['capabilities'][0]['evidence']={'level':'demonstrated','record_refs':['mock-record'],'native_symbols':[],'probe_ids':[],'limits_ref':None}
        es=cc.validate('CapabilityManifest',d)
        self.assertIn('demonstration_game_binding_missing',es);self.assertIn('demonstration_probe_missing',es)
    def test_operation_payload_hash_detects_change(self):
        d=sample('construction_plan');d['operations'][0]['payload']['centreline_m'][0][0]=1
        es=cc.validate('ConstructionPlan',d)
        self.assertIn('operation_hash_mismatch',es);self.assertIn('plan_hash_mismatch',es)
    def test_dependency_cannot_reference_future_operation(self):
        d=sample('construction_plan');d['operations'][0]['depends_on']=['missing'];rehash(d)
        self.assertIn('dependency_order_invalid',cc.validate('ConstructionPlan',d))
    def test_derived_capabilities_cannot_be_removed(self):
        d=sample('construction_plan');d['required_capabilities'].remove('game.routes.verify');rehash(d)
        self.assertIn('derived_capabilities_mismatch',cc.validate('ConstructionPlan',d))
    def test_shared_nodes_are_consistent(self):
        d=sample('construction_plan');o=deepcopy(d['operations'][0]);o['operation_id']='operation-2';o['payload']['edge_ref']='edge-2';o['payload']['centreline_m'][0][1]=1
        d['operations'].append(o);rehash(d)
        self.assertIn('shared_node_position_mismatch',cc.validate('ConstructionPlan',d))
    def test_live_execution_requires_game_binding(self):
        d=sample('construction_plan');d['execution_mode']='live';rehash(d)
        self.assertIn('live_plan_has_nongame_binding',cc.validate('ConstructionPlan',d))
    def test_mock_cannot_claim_observed_game_passage(self):
        d=sample('realisation_report');d['status']='game_traversal_observed'
        self.assertIn('game_observation_not_established',cc.validate('RealisationReport',d))
    def test_failed_check_not_ready(self):
        d=sample('decision_packet');d['status']='design_ready'
        self.assertIn('design_ready_with_blocker',cc.validate('DecisionPacket',d))
    def test_passing_preflight_still_performs_no_write(self):
        r=cc.preflight_contract(*context());self.assertTrue(r['contract_preflight_passed']);self.assertFalse(r['live_execution_authorised']);self.assertEqual(0,r['writes_performed'])
    def test_unresolved_approval_blocked(self):
        p,m,a,c=context();c['host_resolved_authority_refs']=[]
        self.assertIn('authority_not_host_resolved',cc.preflight_contract(p,m,a,c)['errors'])
    def test_expired_approval_blocked(self):
        p,m,a,c=context();c['now_unix_ms']=a['expires_unix_ms']
        self.assertIn('authority_expired',cc.preflight_contract(p,m,a,c)['errors'])
    def test_wrong_principal_and_epoch_blocked(self):
        p,m,a,c=context();a['principal_ref']='other-user';a['load_epoch']='load-2'
        es=cc.preflight_contract(p,m,a,c)['errors'];self.assertIn('authority_principal_mismatch',es);self.assertIn('authority_save_epoch_mismatch',es)
    def test_unknown_capabilities_blocked(self):
        p,m,a,c=context();m['capabilities'][0]['evidence']['level']='unknown'
        self.assertTrue(any(e.startswith('capability_not_demonstrated:') for e in cc.preflight_contract(p,m,a,c)['errors']))
    def test_stale_snapshot_blocked(self):
        p,m,a,c=context();c['current_binding']['terrain_revision']='new-ground'
        self.assertIn('snapshot_binding_stale',cc.preflight_contract(p,m,a,c)['errors'])
    def test_plan_approval_hash_binding(self):
        p,m,a,c=context();a['plan_hash']='0'*64
        self.assertIn('authority_plan_mismatch',cc.preflight_contract(p,m,a,c)['errors'])
    def test_scope_cannot_be_enlarged(self):
        p,m,a,c=context();a['effect_region']['max_m'][0]=500
        self.assertIn('authority_region_too_small',cc.preflight_contract(p,m,a,c)['errors'])
    def test_requirement_dispositions_cover_original_ids(self):
        d=cc.read_json(ROOT/'implementation/requirement_disposition.json')['requirements'];self.assertEqual(75,len(d));self.assertEqual(75,len({r['requirement_id'] for r in d}))
        self.assertEqual('optional_deferred',next(r['v012_disposition'] for r in d if r['requirement_id']=='PAX-003'))
    def test_work_package_dependencies_exist_and_acyclic(self):
        ps=cc.read_json(ROOT/'implementation/work_packages.json')['work_packages'];pending={p['id']:set(p['depends_on']) for p in ps};done=set()
        while pending:
            ready={k for k,v in pending.items() if v<=done};self.assertTrue(ready)
            for k in ready:pending.pop(k)
            done|=ready
    def test_source_inventory_is_actual_bytes(self):
        inv=cc.read_json(ROOT/'implementation/source_inventory.json')
        for r in inv['modules']:
            import hashlib
            self.assertEqual(r['sha256'],hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest())
    def test_no_hidden_physics_dependency(self):
        ps=cc.read_json(ROOT/'implementation/work_packages.json')['work_packages'];self.assertNotRegex(json.dumps(ps).lower(),r'\btraction\b');self.assertNotRegex(json.dumps(ps).lower(),r'\bevacuation\b')
        features=cc.read_json(ROOT/'implementation/feature_matrix.json')['features']
        self.assertEqual('optional_deferred',next(f['scope'] for f in features if f['feature_id']=='FEAT-13'))

if __name__=='__main__':unittest.main()
