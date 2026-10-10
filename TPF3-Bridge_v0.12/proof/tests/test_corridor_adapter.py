import unittest
from copy import deepcopy
from pathlib import Path
from railcorridor.planning import *
from railcorridor.adapter import *


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=validate_fixture(parse_json(Path(__file__).parents[1]/'corridor_fixtures/release.json'))
        cls.c=candidate(cls.f,280,20);cls.p=compile_plan(cls.c,cls.f)
    def test_clean_run_readback(self):self.assertEqual(execute(self.p,MockAdapter())['status'],'mock_verified')
    def test_idempotent_repeat(self):
        a=MockAdapter();execute(self.p,a);n=a.writes
        self.assertEqual(execute(self.p,a)['status'],'mock_verified');self.assertEqual(n,a.writes)
    def test_lost_ack_reconciles_without_duplicate(self):
        a=MockAdapter(drop_ack_at=1);r=execute(self.p,a)
        self.assertEqual(r['status'],'mock_verified');self.assertEqual(r['acknowledgements_reconciled'],1)
        self.assertEqual(a.writes,len(self.p['operations']))
    def test_geometry_snap_stops(self):
        r=execute(self.p,MockAdapter(snap_at=1));self.assertEqual(r['status'],'realised_geometry_mismatch');self.assertEqual(r['writes'],2)
    def test_small_snap_within_tolerance(self):
        # Snap a structure reservation, not an endpoint shared by later track nodes.
        i=next(i for i,o in enumerate(self.p['operations']) if o['kind']=='construct.bridge_reservation')
        r=execute(self.p,MockAdapter(snap_at=i,snap_distance_m=.01));self.assertEqual(r['status'],'mock_verified')
    def test_partial_failure_keeps_effects(self):
        a=MockAdapter(fail_at=2);r=execute(self.p,a)
        self.assertEqual(r['status'],'partial_failure');self.assertEqual(len(a.ledger),2);self.assertFalse(r['rollback_attempted'])
    def test_resume_after_failure(self):
        a=MockAdapter(fail_at=2);execute(self.p,a);a.fail_at=None
        self.assertEqual(execute(self.p,a)['status'],'mock_verified');self.assertEqual(a.writes,len(self.p['operations']))
    def test_unknown_capability_no_writes(self):
        a=MockAdapter(manifest(demonstrated=False));r=execute(self.p,a)
        self.assertEqual(r['status'],'preflight_blocked');self.assertEqual(a.writes,0)
    def test_documented_is_not_demonstrated(self):
        m=manifest();m['capabilities']['construct.track_polyline3']['state']='documented'
        self.assertEqual(execute(self.p,MockAdapter(m))['status'],'preflight_blocked')
    def test_unconnected_game_not_mock_success(self):
        r=execute(self.p,MockAdapter(manifest('tpf3_unprobed')))
        self.assertEqual(r['status'],'preflight_blocked');self.assertFalse(r['real_game_constructed'])
    def test_stale_world_no_effect(self):
        a=MockAdapter(revision=1);self.assertEqual(execute(self.p,a)['status'],'preflight_blocked');self.assertEqual(a.writes,0)
    def test_stale_terrain_no_effect(self):
        a=MockAdapter(terrain_revision='changed');self.assertEqual(execute(self.p,a)['status'],'preflight_blocked')
    def test_tampered_plan_hash(self):
        p=deepcopy(self.p);p['expected_world_revision']=1
        self.assertEqual(execute(p,MockAdapter())['reasons'],['plan_hash_mismatch'])
    def test_cannot_hide_required_capability(self):
        p=deepcopy(self.p);p['required_capabilities']=[];p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        self.assertEqual(execute(p,MockAdapter())['reasons'],['capability_requirement_mismatch'])
    def test_reordered_dependency_rejected(self):
        p=deepcopy(self.p);p['operations'].reverse();p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        self.assertIn('dependency_order_invalid',execute(p,MockAdapter())['reasons'])
    def test_unknown_command_rejected(self):
        op=operation('python.exec',{'code':'pass'},[])
        with self.assertRaises(ValueError):verify_operation(op)
    def test_outside_scope_no_effect(self):
        p=deepcopy(self.p);p['edit_region']=[0,0,1,1];p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        self.assertEqual(execute(p,MockAdapter())['status'],'preflight_blocked')
    def test_wrong_brief_cannot_compile(self):
        f=deepcopy(self.f);f['profile']['speed_mph']=80
        with self.assertRaises(ValueError):compile_plan(self.c,f)
    def test_rejected_geometry_cannot_compile(self):
        with self.assertRaises(ValueError):compile_plan(candidate(self.f,-280,20),self.f)
    def test_changed_candidate_cannot_compile(self):
        c=deepcopy(self.c);c['track_lengths_m'][0]=1
        with self.assertRaises(ValueError):compile_plan(c,self.f)
    def test_lowering_bound_respected(self):
        self.assertTrue(all(r['error_bound_m']<=.02000001 for r in self.p['lowering_certificates']))
    def test_structure_dependency_before_track(self):
        kinds={o['operation_id']:o['kind'] for o in self.p['operations']}
        for o in self.p['operations']:
            if o['kind']=='construct.track_polyline3' and o['payload']['mode']=='river_bridge':
                self.assertEqual(kinds[o['dependencies'][0]],'construct.bridge_reservation')
    def test_branch_not_fabricated_in_plan(self):self.assertIn('no branch connection',self.p['scope'])
    def test_geometry_payloads_independent_copies(self):
        p=deepcopy(self.p);a=MockAdapter();o=p['operations'][0];r=a.apply(o)
        r['realised']['points'][0][0]=9999
        self.assertNotEqual(a.receipt(o['operation_id'])['realised']['points'][0][0],9999)
