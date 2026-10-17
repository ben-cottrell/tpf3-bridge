"""Check saved native P62 evidence without issuing game commands."""
import argparse
import json
from pathlib import Path


def check(root):
    read=lambda p:json.loads((root/p).read_text(encoding='utf-8'))
    cases={}
    for name,count in [('flyover',10),('tunnel',7)]:
        proposed=read(f'{name}/prepared.params.json')['segments']
        prepared=read(f'{name}/prepared.json')
        built=read(f'{name}/built.json')
        current=read(f'{name}/fresh_committed.json')
        assert prepared['status']==built['status']==current['status']=='ok'
        assert prepared['session']==built['session']==current['session']
        assert prepared['result']['native_proposal_critical'] is False
        assert built['result']['prepared_geometry_reused'] is True
        assert built['result']['geometry_refitted'] is False
        assert built['result']['effects']==dict(added_segments=count,removed_segments=count,added_nodes=0,removed_nodes=0)
        edges=current['result']['edges'];assert len(edges)==count
        original={x['edge_snapshot']['id'] for x in proposed}
        assert original.isdisjoint(e['id'] for e in edges)
        keyed={(e['node0'],e['node1']):e for e in edges};assert len(keyed)==count
        for segment in proposed:
            before=segment['edge_snapshot'];after=keyed[before['node0'],before['node1']]
            assert after['structure']['classification']==segment['structure']['classification']
            assert after['structure'].get('resource_name')==segment['structure'].get('resource_name')
            assert after['template']==before['template'] and after['style']==before['style']
            for key in ('p0','p1','t0','t1'):
                assert max(abs(a-b) for a,b in zip(after[key],segment['controls'][key]))<=.001
        cases[name]={'new_edges':[e['id'] for e in edges],'structure_classes':sorted({e['structure']['classification'] for e in edges})}
    summaries=read('after_tunnel_routes/summary.json');assert len(summaries)==14
    for item in summaries:
        route=read('after_tunnel_routes/'+item['case']+'.json')
        assert item['verified'] and route['status']=='ok'
        result=route['result'];assert result['requested_route_verified'] and result['transport_continuous']
        assert not result['missing_required_edges']
    assert all(x['game_constructed'] is False and x['status']=='error' for x in read('negative_checks.json'))
    return {'status':'pass','cases':cases,'verified_native_paths':len(summaries),'train_traversal':'unprobed'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('evidence',type=Path)
    print(json.dumps(check(parser.parse_args().evidence)))
