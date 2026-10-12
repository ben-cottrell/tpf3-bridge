"""Point-only terrain reads preserve ordered identities and caller effect bounds."""
import unittest
from unittest.mock import Mock

import bridge_live as live
from bridge_operator import terrain_samples


class TerrainSampleTests(unittest.TestCase):
    region={'min':[-24000,-24000,-10],'max':[24000,24000,100]}

    def response(self,positions):
        return {'status':'ok','request_id':'terrain','result':{'game_constructed':False,'sampled_only':True,
            'terrain':[{'xy':p,'height':5+i,'base_height':2+i,'valid':True} for i,p in enumerate(positions)]}}

    def test_128_distant_points_use_one_read_without_spatial_discovery(self):
        positions=[[i*180,-i*180] for i in range(128)];client=Mock()
        client.request.return_value=self.response(positions)
        samples=terrain_samples(client,self.region,positions)
        client.request.assert_called_once_with('terrain_samples',{'positions':positions})
        self.assertEqual(len(samples),128);self.assertEqual(samples[-1]['height'],132);self.assertEqual(samples[-1]['base_height'],129)
        self.assertIn('terrain_samples',live.OPERATIONS);self.assertFalse(live.is_mutation('terrain_samples',{}))

    def test_all_positions_are_validated_before_native_read(self):
        for positions in ([],[[0,0]]*129,[[0,0],[24001,0]],[[0,0],[float('nan'),0]],[[0,0],[1,2,3]]):
            client=Mock()
            with self.subTest(positions=positions),self.assertRaises(ValueError):terrain_samples(client,self.region,positions)
            client.request.assert_not_called()

    def test_order_identity_and_full_coverage_are_required(self):
        positions=[[0,0],[10000,0]]
        for rows in ([{'xy':[10000,0]},{'xy':[0,0]}],[{'xy':[0,0]}],[{'xy':[0,0]},{'xy':[9999,0]}],[{'xy':[0,0]},{}]):
            client=Mock();client.request.return_value={'status':'ok','request_id':'terrain','result':{'terrain':rows}}
            with self.subTest(rows=rows),self.assertRaisesRegex(ValueError,'identity/coverage'):terrain_samples(client,self.region,positions)

    def test_duplicate_selected_points_remain_distinct_ordered_samples(self):
        positions=[[0,0],[0,0]];client=Mock();client.request.return_value=self.response(positions)
        self.assertEqual([r['height'] for r in terrain_samples(client,self.region,positions)],[5,6])

    def test_native_outside_map_error_is_retained(self):
        client=Mock();client.request.return_value={'status':'error','request_id':'terrain','result':{'error':'terrain_position_outside_map'}}
        with self.assertRaisesRegex(live.LiveError,'terrain_position_outside_map'):terrain_samples(client,self.region,[[0,0]])


if __name__=='__main__':unittest.main()
