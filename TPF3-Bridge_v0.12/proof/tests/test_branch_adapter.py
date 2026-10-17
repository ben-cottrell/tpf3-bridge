import unittest
from copy import deepcopy
from railbranch.geometry import build
from railbranch.adapter import *

class BranchAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plans={m:compile_plan(build(mode=m)) for m in ('flat','flyover','diveunder')}
    def test_all_modes_construct_mock(self):
        for p in self.plans.values():self.assertEqual(execute(p,MockJunctionAdapter())['status'],'mock_junction_verified')
    def test_physical_edges_written_once_not_per_route(self):
        a=MockJunctionAdapter();p=self.plans['flyover'];execute(p,a)
        self.assertEqual(len(a.edges),14);self.assertEqual(len(a.turnouts),2)
    def test_real_components_are_explicit_operations(self):
        p=self.plans['flat'];self.assertEqual(sum(x['kind']==CAPS[1] for x in p['operations']),2)
        self.assertEqual(sum(x['kind']==CAPS[2] for x in p['operations']),1)
    def test_structure_reservation_precedes_geometry(self):self.assertEqual(self.plans['flyover']['operations'][0]['kind'],CAPS[3])
    def test_flat_has_no_invented_bridge(self):self.assertFalse(any(x['kind']==CAPS[3] for x in self.plans['flat']['operations']))
    def test_repeat_is_idempotent(self):
        a=MockJunctionAdapter();p=self.plans['flyover'];execute(p,a);n=a.writes
        self.assertEqual(execute(p,a)['status'],'mock_junction_verified');self.assertEqual(a.writes,n)
    def test_lost_ack_reconciled(self):
        a=MockJunctionAdapter(drop_ack_at=1);r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'mock_junction_verified');self.assertEqual(r['recovered_acknowledgements'],1);self.assertEqual(a.writes,14)
    def test_geometry_mismatch_stops(self):
        a=MockJunctionAdapter(snap_at=1);r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'realised_geometry_or_semantics_mismatch');self.assertEqual(a.writes,2)
    def test_point_state_mismatch_stops(self):
        a=MockJunctionAdapter(corrupt_state_at=1);r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'realised_geometry_or_semantics_mismatch');self.assertEqual(a.writes,2)
    def test_partial_failure_preserves_effects(self):
        a=MockJunctionAdapter(fail_at=2);r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'partial_failure');self.assertEqual(a.writes,2);self.assertFalse(r['rollback_attempted'])
    def test_resume_after_partial_failure(self):
        a=MockJunctionAdapter(fail_at=2);p=self.plans['flyover'];execute(p,a);a.fail_at=None
        self.assertEqual(execute(p,a)['status'],'mock_junction_verified');self.assertEqual(a.writes,14)
    def test_unknown_capability_rejects_before_write(self):
        a=MockJunctionAdapter();a.capabilities['capabilities'][CAPS[1]]['state']='unknown';r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'preflight_blocked');self.assertEqual(a.writes,0)
    def test_unprobed_real_game_blocked(self):
        a=MockJunctionAdapter(capabilities=manifest('tpf3_unprobed'));r=execute(self.plans['flyover'],a)
        self.assertEqual(r['status'],'preflight_blocked');self.assertEqual(a.writes,0)
    def test_stale_world_blocked(self):
        a=MockJunctionAdapter(revision=1);self.assertEqual(execute(self.plans['flyover'],a)['status'],'preflight_blocked')
    def test_stale_terrain_blocked(self):
        a=MockJunctionAdapter(terrain_revision='other');self.assertEqual(execute(self.plans['flyover'],a)['status'],'preflight_blocked')
    def test_forged_game_authority_blocked(self):
        p=deepcopy(self.plans['flat']);p['real_game_execution_authorised']=True;p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        self.assertEqual(execute(p,MockJunctionAdapter())['status'],'preflight_blocked')
    def test_plan_tamper_blocked(self):
        p=deepcopy(self.plans['flat']);p['operations'][0]['payload']['normal_state']='wrong'
        self.assertEqual(execute(p,MockJunctionAdapter())['status'],'preflight_blocked')
    def test_dependency_order_checked(self):
        p=deepcopy(self.plans['flat']);p['operations'].reverse();p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        self.assertEqual(execute(p,MockJunctionAdapter())['status'],'preflight_blocked')
    def test_region_is_not_silently_enlarged(self):
        p=deepcopy(self.plans['flat']);p['edit_region'][2]=100;p['plan_hash']=digest({k:v for k,v in p.items() if k!='plan_hash'})
        a=MockJunctionAdapter();self.assertEqual(execute(p,a)['status'],'preflight_blocked');self.assertEqual(a.writes,0)
    def test_actual_edge_readback_not_receipt_only(self):
        a=MockJunctionAdapter();p=self.plans['flat'];execute(p,a)
        a.edges['east_approach']['points'][1][2]+=.2
        self.assertEqual(execute(p,a)['status'],'realised_geometry_or_semantics_mismatch')
    def test_actual_topology_tamper_detected(self):
        a=MockJunctionAdapter();p=self.plans['flat'];execute(p,a);a.edges['west_exit']['v']='wrong_node'
        self.assertFalse(verify_topology(p,a)['passed'])
    def test_crossing_cannot_become_turn(self):
        a=MockJunctionAdapter();p=self.plans['flat'];execute(p,a);a.crossings[0]['connect_at_intersection']=True
        self.assertIn('invented_crossing_connection',verify_topology(p,a)['errors'])
    def test_geometry_tolerance_not_applied_to_semantics(self):
        self.assertFalse(payload_equal({'state':'N'},{'state':'R'},1000.))
    def test_nonfinite_readback_rejected(self):
        self.assertFalse(payload_equal({'points':[[0.,0.,0.],[1.,0.,0.]]},{'points':[[0.,0.,0.],[1.,float('nan'),0.]]},.05))
    def test_real_capabilities_stay_unknown(self):
        m=manifest('tpf3_unprobed');self.assertEqual({v['state'] for v in m['capabilities'].values()},{'unknown'});self.assertFalse(m['game_probed'])
