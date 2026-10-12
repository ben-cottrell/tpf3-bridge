"""Bounded scaffold observations with fake native identities; no game calls."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bridge_live as live
from bridge_operator import Operator, catalogue_components, main


def edge(ident,node0,node1,x0,x1):
    return {'id':ident,'node0':node0,'node1':node1,'p0':[x0,0,2],'p1':[x1,0,2],
            't0':[x1-x0,0,0],'t1':[x1-x0,0,0],'template':'track','style':'style',
            'road_type':'TRACK','structure':{'classification':'NORMAL'},'name':'unnamed',
            'endpoint_incidence':[{'node_id':node0,'incident_count':1,'free':True},
                                  {'node_id':node1,'incident_count':1,'free':True}],
            'objects':[]}


class CatalogueTests(unittest.TestCase):
    def fixture(self):
        a=edge(1,10,11,0,100);b=edge(2,12,11,200,100);c=edge(3,20,21,1000,1100)
        a['endpoint_incidence'][1].update(incident_count=2,free=False)
        b['endpoint_incidence'][1].update(incident_count=2,free=False)
        c['endpoint_incidence'][0].update(incident_count=2,free=False) # adjacent station rail excluded from catalogue
        b['structure']={'classification':'BRIDGE','resource_name':'observed.bridge'}
        b['objects']=[{'id':90,'name':'Scaffold fast terminus','parameter':.25,'position':[175,0,2],
                       'resource':'observed.signal','signal':{'lanes':[{'edge':2,'reversed':False}]}}]
        return [a,b,c]

    def native_result(self,edges,complete=True):
        return {'edges':edges,'returned_tracks':len(edges),'enumerated_edges':10,'examined_edges':10,
                'examined_TRACK':8,'external_tracks_observed':len(edges),'excluded_construction_tracks':5,
                'complete':complete,'truncated':not complete,'external_only':True,
                'native_qualification':'pending','exclusion':'all_construction_owned_TRACK'}

    def client(self,directory,result):
        class Client:
            session='catalogue_test'
            evidence=Path(directory)
            calls=[]
            def request(self,operation,params):
                self.calls.append((operation,params))
                return {'status':'ok','request_id':'catalogue','result':copy.deepcopy(result)}
        return Client()

    def test_components_follow_identity_and_keep_exact_free_endpoints(self):
        components=catalogue_components(self.fixture())
        self.assertEqual([c['edge_ids'] for c in components],[[1,2],[3]])
        endpoints=components[0]['endpoints']
        self.assertEqual([p['node_id'] for p in endpoints],[10,12])
        self.assertEqual([p['outward_direction'] for p in endpoints],[[-1,0],[1,0]])
        self.assertEqual(components[0]['structures'],{'NORMAL':1,'BRIDGE':1})
        self.assertEqual(components[0]['signals'][0]['name'],'Scaffold fast terminus')
        self.assertEqual(components[1]['endpoint_count'],2)
        self.assertEqual(components[1]['free_endpoint_count'],1)
        same_position=edge(4,30,31,0,100)
        self.assertEqual(len(catalogue_components(self.fixture()+[same_position])),3)

    def test_closed_component_has_no_endpoints_and_duplicate_edges_fail(self):
        a=edge(1,10,11,0,100);b=edge(2,11,10,100,0)
        self.assertEqual(catalogue_components([a,b])[0]['endpoints'],[])
        with self.assertRaisesRegex(ValueError,'duplicate exact'):catalogue_components([a,a])

    def test_catalogue_compact_summary_preserves_truncation_and_current_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.client(td,self.native_result(self.fixture(),complete=False));o=Operator(runs=td,client=c)
            result=o.track_catalogue(max_examined_edges=100,max_tracks=12,summary_limit=1)
            self.assertEqual(c.calls,[('track_catalogue',{'max_examined_edges':100,'max_tracks':12})])
            self.assertFalse(result['complete']);self.assertTrue(result['component_summary_truncated'])
            self.assertEqual(result['component_count'],2);self.assertEqual(len(result['components']),1)
            self.assertEqual(result['named_signals'][0]['id'],90)
            self.assertNotIn('edges',result)
            current=json.loads(Path(result['evidence']).read_text())
            self.assertEqual(len(current['catalogue']['edges']),3);self.assertEqual(len(current['components']),2)
            self.assertEqual(o.track_catalogue()['evidence'],result['evidence']) # replaces current working snapshot
            self.assertEqual(len(list(Path(td).glob('operator_track_catalogue*.json'))),1)

    def test_catalogue_bounds_and_read_only_classification(self):
        self.assertIn('track_catalogue',live.OPERATIONS)
        self.assertFalse(live.is_mutation('track_catalogue',{}))
        with tempfile.TemporaryDirectory() as td:
            c=self.client(td,self.native_result([]));o=Operator(runs=td,client=c)
            for arguments in ({'max_tracks':513},{'max_tracks':True},{'max_examined_edges':0},{'summary_limit':129}):
                with self.subTest(arguments=arguments),self.assertRaises(ValueError):o.track_catalogue(**arguments)
            self.assertFalse(c.calls)
            result=o.track_catalogue()
            self.assertEqual(result['components'],[]);self.assertTrue(result['complete'])

    def test_native_failure_and_returned_bound_mismatch_do_not_write_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.client(td,self.native_result(self.fixture()));o=Operator(runs=td,client=c)
            with patch.object(c,'request',return_value={'status':'error','request_id':'read','result':{'error':'BASE_EDGE_enumeration_unavailable'}}):
                with self.assertRaisesRegex(live.LiveError,'BASE_EDGE_enumeration_unavailable'):o.track_catalogue()
            with self.assertRaisesRegex(ValueError,'bound/count mismatch'):o.track_catalogue(max_tracks=1)
            self.assertFalse((Path(td)/'operator_track_catalogue.json').exists())

    def test_cli_exposes_catalogue_without_spatial_region(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.client(td,self.native_result(self.fixture()));o=Operator(runs=td,client=c)
            stdout=io.StringIO()
            with patch('bridge_operator.Operator',return_value=o),patch('sys.argv',['bridge_operator.py','track-catalogue']),contextlib.redirect_stdout(stdout):
                self.assertEqual(main(),0)
            self.assertEqual(json.loads(stdout.getvalue())['returned_tracks'],3)


if __name__=='__main__':unittest.main()
