"""Complete bounded incidence and unchanged dependency-fingerprint contracts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bridge_approach import Dependencies
from bridge_dependency_benchmark import LegacyDependencies,compare
from test_approach import World


def rails(c,count=2):
    rows=[]
    for i in range(count):rows.append(c.make_edge([i*20,0,2],[(i+1)*20,0,2],[20,0,0],[20,0,0],node0=10+i,node1=11+i))
    return rows


class DependencyBatchTests(unittest.TestCase):
    def test_old_new_fingerprints_equal_with_objects_owner_nontrack_and_station(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);rails(c);c.objects[1]=[{'id':90,'signal':{'one_way':True}}]
            c.node_owners[11]=42;c.extra_incidence[11]=[99]
            selector={'name':'Station','construction':{'resource':'station','position':[0,0,2]}}
            old=LegacyDependencies(c).fingerprint({'kind':'station_routes'},[1,2],[selector])
            c.calls.clear();new=Dependencies(c).fingerprint({'kind':'station_routes'},[1,2],[selector])
            self.assertEqual(old,new);self.assertEqual(new['incidence']['11'],{'incident_edges':[1,2,99],'construction_owner':42})
            self.assertEqual([op for op,q in c.calls],['inspect','operating_inspect','station_lookup'])
            self.assertEqual(c.calls[0][1]['incidence_edge_ids'],[1,2])

    def test_geometry_only_then_semantic_upgrade_checks_reread_before_merge(self):
        for changed in (False,True):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as td:
                c=World(td);rails(c,1);d=Dependencies(c);d.fingerprint({'kind':'geometry'},[1],[])
                self.assertNotIn('incidence_edge_ids',c.calls[0][1]);self.assertEqual(d.nodes,{})
                if changed:c.edges[1]['t0'][1]=1
                if changed:
                    with self.assertRaisesRegex(ValueError,'reread geometry changed'):d.fingerprint({'kind':'route'},[1],[])
                    self.assertEqual(d.nodes,{});self.assertEqual(d.tracks,{});self.assertEqual(d.edges[1]['t0'][1],0)
                else:
                    d.fingerprint({'kind':'route'},[1],[])
                    self.assertEqual([op for op,q in c.calls],['inspect','inspect','operating_inspect'])

    def test_union_prefetch_enriches_only_semantic_subset_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);rails(c);d=Dependencies(c);d.observe_edges([1,2],semantic_ids=[1])
            self.assertEqual(c.calls[0][1],{'edge_ids':[1,2],'structures':True,'incidence_edge_ids':[1]})
            d.fingerprint({'kind':'route'},[1],[]);d.fingerprint({'kind':'geometry'},[2],[])
            self.assertEqual([op for op,q in c.calls],['inspect','operating_inspect'])

    def test_malformed_or_overbound_response_never_merges_partial_batch(self):
        for fault in ('missing','wrong_subset','duplicate_subset','extra_node','missing_node','duplicate_node','node_count',
                      'owner_missing','owner_malformed','node_complete','truncated','count','duplicate_incident','bool_incident',
                      'missing_membership','overbound','duplicate_edge','extra_edge','missing_geometry','nonfinite_geometry','response_incomplete'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as td:
                c=World(td);rails(c);original=c.request
                def request(op,q,**kw):
                    r=original(op,q,**kw)
                    if op!='inspect':return r
                    result=r['result'];v=result['endpoint_incidence'];row=v['nodes'][0]
                    if fault=='missing':result.pop('endpoint_incidence')
                    elif fault=='wrong_subset':v['edge_ids']=[2]
                    elif fault=='duplicate_subset':v['edge_ids']=[1,1]
                    elif fault=='extra_node':v['nodes'].append(row|{'node_id':999});v['node_count']+=1
                    elif fault=='missing_node':v['nodes'].pop();v['node_count']-=1
                    elif fault=='duplicate_node':v['nodes'][1]=copy.deepcopy(row)
                    elif fault=='node_count':v['node_count']=99
                    elif fault=='owner_missing':row.pop('construction_owner')
                    elif fault=='owner_malformed':row['construction_owner']='unknown'
                    elif fault=='node_complete':row['incidence_complete']=False
                    elif fault=='truncated':row['incident_output_truncated']=True
                    elif fault=='count':row['incident_count']+=1
                    elif fault=='duplicate_incident':row['incident_edges']*=2;row['incident_count']=len(row['incident_edges'])
                    elif fault=='bool_incident':row['incident_edges']=[True];row['incident_count']=1
                    elif fault=='missing_membership':row['incident_edges']=[99];row['incident_count']=1
                    elif fault=='overbound':row['incident_edges']=list(range(1,18));row['incident_count']=17
                    elif fault=='duplicate_edge':result['edges'].append(copy.deepcopy(result['edges'][0]))
                    elif fault=='extra_edge':result['edges'][0]['id']=999
                    elif fault=='missing_geometry':result['edges'][0].pop('t1')
                    elif fault=='nonfinite_geometry':result['edges'][0]['t0'][1]=float('nan')
                    else:v['complete']=False
                    return r
                d=Dependencies(c)
                with patch.object(c,'request',side_effect=request),self.assertRaises(ValueError):d.observe_semantics([1])
                self.assertEqual(d.edges,{});self.assertEqual(d.nodes,{});self.assertEqual(d.incidence_edges,set())

    def test_shared_node_conflict_across_chunks_stops_before_object_reads(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td)
            for i in range(17):c.make_edge([i*20,0,2],[(i+1)*20,0,2],[20,0,0],[20,0,0],node0=100+i*2,node1=101+i*2)
            shared=c.edges[1]['node1'];c.edges[17]['node0']=shared;original=c.request
            def request(op,q,**kw):
                r=original(op,q,**kw)
                if op=='inspect' and q['edge_ids']==[17]:
                    node=next(n for n in r['result']['endpoint_incidence']['nodes'] if n['node_id']==shared)
                    node['incident_edges'].append(999);node['incident_count']+=1
                return r
            d=Dependencies(c)
            with patch.object(c,'request',side_effect=request),self.assertRaisesRegex(ValueError,'conflicting exact-node'):d.observe_semantics(list(range(1,18)))
            self.assertNotIn(17,d.edges);self.assertEqual([op for op,q in c.calls],['inspect','inspect'])

    def test_nil_owner_normalizes_to_existing_none_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);rails(c,1);c.node_owners[10]=None
            self.assertEqual(Dependencies(c).fingerprint({'kind':'route'},[1],[])['incidence']['10']['construction_owner'],'none')

    def test_benchmark_same_fixture_equality_counts_bytes_and_no_artifact_or_route(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);rails(c);before=set(Path(td).rglob('*'))
            q={'version':1,'session':'test','checks':[{'name':'route','kind':'route','edge_ids':[1,2],'selectors':[]}]}
            r=compare(c,q)
            self.assertTrue(r['fingerprints_equal']);self.assertEqual(r['legacy']['requests'],5);self.assertEqual(r['enriched']['requests'],2)
            self.assertEqual(r['legacy']['operations']['discover'],3);self.assertNotIn('discover',r['enriched']['operations'])
            self.assertGreater(r['enriched']['response_bytes'],0);self.assertFalse(r['snapshot_atomic']);self.assertEqual(r['routes_run'],0)
            self.assertLess(len(json.dumps(r).encode()),4096);self.assertEqual(before,set(Path(td).rglob('*')))
            c.journal=Path(td)/'journal.json';c.journal.write_text('{"pending":{"request_id":"unresolved"}}')
            calls=len(c.calls)
            with self.assertRaisesRegex(ValueError,'unresolved'):compare(c,q)
            self.assertEqual(len(c.calls),calls)

    def test_benchmark_changed_between_passes_reports_difference_without_retry(self):
        with tempfile.TemporaryDirectory() as td:
            c=World(td);rails(c,1);request=c.request
            def changed(op,q,**kw):
                if op=='inspect' and 'incidence_edge_ids' in q:c.edges[1]['t0'][1]=1
                return request(op,q,**kw)
            packet={'version':1,'session':'test','checks':[{'name':'route','kind':'route','edge_ids':[1],'selectors':[]}]}
            with patch.object(c,'request',side_effect=changed):r=compare(c,packet)
            self.assertEqual(r['status'],'needs_attention');self.assertFalse(r['fingerprints_equal'])
            self.assertEqual([op for op,q in c.calls].count('inspect'),2);self.assertEqual(r['routes_run'],0)


if __name__=='__main__':unittest.main()
