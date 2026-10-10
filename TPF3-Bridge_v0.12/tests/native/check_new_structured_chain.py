"""Offline acceptance of saved committed new-chain evidence; never calls the game."""
import json
import math
from pathlib import Path
import sys


def check(root, attempt=4):
    root=Path(root)
    def read(path):return json.loads((root/path).read_text(encoding='utf-8'))
    routes=read('after_routes/summary.json')
    assert len(routes)==12 and all(row['verified'] is True for row in routes)
    pair=read(f'prepared_pair_analysis_{attempt}.json')['summary']
    assert pair['crossing_observed'] is False and pair['continuous_proof'] is False
    nodes=[];summaries=[]
    bindings={'D_US_to_E_DS':(67203,63080),'E_US_to_D_DS':(67231,63456)}
    for name,boundaries in bindings.items():
        prepared=read(f'{name}/prepare_{attempt}.json')
        built=read(f'{name}/build_{attempt}.json')
        fresh=read(f'{name}/fresh_committed.json')
        params=read(f'{name}/prepare_{attempt}.params.json')
        assert prepared['status']==built['status']==fresh['status']=='ok'
        assert prepared['session']==built['session']==fresh['session']
        assert built['result']['game_constructed'] is True
        assert prepared['result']['evaluation']['message_count']==0
        ordered=built['result']['ordered_edges'];chain=built['result']['ordered_nodes']
        assert (chain[0],chain[-1])==boundaries and len(chain)==len(ordered)+1
        edges={e['id']:e for e in fresh['result']['edges']}
        bridge_count=0;grades=[];movement_z=[]
        for index,eid in enumerate(ordered):
            edge=edges[eid]
            assert edge['road_type']=='TRACK'
            assert {edge['node0'],edge['node1']}=={chain[index],chain[index+1]}
            kind=edge['structure']['classification']
            assert kind in ('NORMAL','BRIDGE')
            if kind=='BRIDGE':
                bridge_count+=1
                assert edge['structure']['resource_name']=='::/infrastructure/bridge/stone.bridge'
            for sample in edge['movement_geometry']['samples']:
                d=sample['direction'];h=math.hypot(*d[:2]);assert h>0
                grades.append(abs(d[2])/h);movement_z.append(sample['pos'][2])
        assert bridge_count>0
        for index,key in ((0,'source'),(-1,'target')):
            port=params[key];edge=edges[ordered[index]]
            assert chain[index]==port['node_id']
            point=edge['p0'] if edge['node0']==port['node_id'] else edge['p1']
            assert max(abs(a-b) for a,b in zip(point,port['pos']))<.001
        # Connectivity uses exact node IDs; proximity never establishes attachment.
        nodes.append(set(chain))
        summaries.append({'name':name,'edges':ordered,'nodes':chain,'bridge_edges':bridge_count,
                          'max_observed_sampled_grade':max(grades),'max_observed_movement_z':max(movement_z)})
    assert nodes[0].isdisjoint(nodes[1]),'direct links share an unintended neck'
    trunk_nodes={n for e in read('capture.json')['trunk_edges'] for n in (e['node0'],e['node1'])}
    assert not (nodes[0]|nodes[1])&trunk_nodes,'unintended trunk attachment'
    return {'status':'pass','links':summaries,'native_route_checks':len(routes),
            'shared_neck':False,'trunk_attachment':False,'continuous_clearance_proof':False,
            'train_traversal':'unprobed','sampled_pair':pair}


if __name__=='__main__':
    print(json.dumps(check(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 4),allow_nan=False))
