import unittest
from copy import deepcopy
from terrain_support import model
from railterrain.planning import bind
from railterrain.adapter import compile_plan,MockTerrainAdapter,execute,manifest,LAND
from railcorridor.geometry import digest

class TerrainAdapterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.f,cls.c,cls.b,cls.j=model();cls.a=bind(cls.j,cls.c,cls.f);cls.p=compile_plan(cls.j,cls.c,cls.f,cls.a)
 def adapter(self,**kw):return MockTerrainAdapter(snapshot=self.c,**kw)
 def test_land_reservation_precedes_tracks(self):
  self.assertEqual(self.p['operations'][0]['kind'],LAND);self.assertEqual(len(self.p['operations']),17)
  self.assertIn(self.p['operations'][0]['operation_id'],self.p['operations'][1]['dependencies'])
 def test_clean_realises_unique_edges_and_routes(self):
  ad=self.adapter();r=execute(self.p,ad,self.a);self.assertEqual(r['status'],'mock_terrain_junction_verified')
  self.assertEqual(len(ad.edges),16);self.assertFalse(r['game_constructed']);self.assertFalse(r['actual_bridge_or_tunnel_asset_built'])
 def test_repeat_no_duplicate_effects(self):
  ad=self.adapter();a=execute(self.p,ad,self.a);b=execute(self.p,ad,self.a)
  self.assertEqual(a['writes'],17);self.assertEqual(b['writes'],17)
 def test_lost_land_receipt_reconciled(self):
  r=execute(self.p,self.adapter(drop_ack_at=0),self.a);self.assertEqual(r['status'],'mock_terrain_junction_verified');self.assertEqual(r['recovered_acknowledgements'],1)
 def test_lost_track_receipt_reconciled(self):
  r=execute(self.p,self.adapter(drop_ack_at=4),self.a);self.assertEqual(r['status'],'mock_terrain_junction_verified');self.assertEqual(r['writes'],17)
 def test_changed_height_same_revision_blocks_before_write(self):
  ad=self.adapter();ad.snapshot['terrain']['ridge_height_m']+=1;r=execute(self.p,ad,self.a)
  self.assertEqual(r['status'],'preflight_blocked');self.assertEqual(r['writes'],0);self.assertIn('terrain_content_changed',r['reasons'])
 def test_changed_protected_land_blocks_before_write(self):
  ad=self.adapter();ad.snapshot['corridor']['forbidden'].append([10,10,20,20]);r=execute(self.p,ad,self.a)
  self.assertEqual(r['writes'],0);self.assertIn('site_constraints_changed',r['reasons'])
 def test_change_after_first_write_stops_no_rollback(self):
  r=execute(self.p,self.adapter(mutate_terrain_after_write=1),self.a)
  self.assertEqual(r['status'],'environment_changed');self.assertEqual(r['writes'],1);self.assertFalse(r['rollback_attempted'])
 def test_stale_world_blocks(self):
  r=execute(self.p,self.adapter(revision=1),self.a);self.assertIn('stale_world',r['reasons']);self.assertEqual(r['writes'],0)
 def test_unprobed_game_blocks(self):
  r=execute(self.p,self.adapter(capabilities=manifest('tpf3_unprobed')),self.a);self.assertEqual(r['writes'],0);self.assertIn('real_game_not_connected',r['reasons'])
 def test_missing_land_capability_blocks(self):
  ad=self.adapter();del ad.capabilities['capabilities'][LAND];r=execute(self.p,ad,self.a);self.assertEqual(r['writes'],0)
 def test_semantic_corruption_stops(self):
  r=execute(self.p,self.adapter(corrupt_state_at=2),self.a);self.assertEqual(r['status'],'realised_geometry_or_semantics_mismatch')
 def test_positional_corruption_stops(self):
  r=execute(self.p,self.adapter(snap_at=2),self.a);self.assertEqual(r['status'],'realised_geometry_or_semantics_mismatch')
 def test_failure_retains_partial_ledger(self):
  ad=self.adapter(fail_at=3);r=execute(self.p,ad,self.a);self.assertEqual(r['status'],'partial_failure');self.assertEqual(len(ad.ledger),3)
 def test_current_state_not_old_receipt(self):
  ad=self.adapter();execute(self.p,ad,self.a);ad.edges['east_approach']['points'][1][2]+=.2
  r=execute(self.p,ad,self.a);self.assertEqual(r['status'],'realised_geometry_or_semantics_mismatch')
 def test_tampered_plan_or_binding_blocks(self):
  p=deepcopy(self.p);p['terrain_hash']='wrong';r=execute(p,self.adapter(),self.a);self.assertIn('plan_hash_mismatch',r['reasons'])
  a=deepcopy(self.a);a['geometry_hash']='wrong';r=execute(self.p,self.adapter(),a);self.assertIn('binding_hash_mismatch',r['reasons'])
 def test_unqualified_design_cannot_compile(self):
  c=deepcopy(self.c);c['terrain']['water_level_m']=18;a=bind(self.j,c,self.f)
  with self.assertRaises(ValueError):compile_plan(self.j,c,self.f,a)
 def test_snapshot_copied_on_adapter_input(self):
  c=deepcopy(self.c);ad=MockTerrainAdapter(snapshot=c);c['terrain']['water_level_m']=18
  self.assertEqual(ad.snapshot,self.c)
