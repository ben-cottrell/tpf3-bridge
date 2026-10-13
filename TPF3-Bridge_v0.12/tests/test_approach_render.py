"""Offline coupled-family diagrams, independent of native execution."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from bridge_approach_render import render_approach
from bridge_operator import Operator, digest
import bridge_operator


def brief():
    return {'revision':'diagram_R1','families':[
        {'name':'merge','kind':'operator','payload':{'origin':[100,200,10],
         'ports':{'landing':{'position':[0,0,0]}},'steps':[{'name':'approach','kind':'connect'}]}},
        {'name':'flyover','kind':'operator','payload':{'origin':[100,200,10],
         'ports':{'deck_end':{'position':[600,15,5]}},'steps':[]}}]}


def packet():
    return {'version':1,'curves':[
        {'family':'merge','name':'approach','frame':'local','epoch':'authored','role':'ramp',
         'p0':[0,25,0],'p1':[450,15,5],'t0':[450,80,0],'t1':[450,0,0]},
        {'family':'flyover','name':'deck','frame':'local','epoch':'preview','role':'deck',
         'p0':[450,15,5],'p1':[600,15,5],'t0':[150,0,0],'t1':[150,0,0]}],
        'markers':[{'family':'merge','kind':'signal','name':'decision','frame':'local','position':[10,26,0]},
                   {'family':'merge','kind':'merge','name':'join','frame':'local','position':[0,25,0]}]}


class ApproachRenderTests(unittest.TestCase):
    def test_combines_boundaries_shared_scale_epochs_and_roles_without_mutation(self):
        b=brief();c=packet();before=copy.deepcopy((b,c))
        with tempfile.TemporaryDirectory() as td,patch('bridge_operator.Operator.client',side_effect=AssertionError('native call')):
            r=render_approach(b,Path(td)/'diagram',controls=c)
            self.assertEqual((b,c),before);self.assertEqual(r['curve_count'],2)
            self.assertEqual(r['missing_control_count'],0);self.assertFalse(r['native_fit_verified'])
            a=ET.parse(r['plan']).getroot();p=ET.parse(r['profile']).getroot()
            self.assertEqual(a.attrib['data-horizontal-scale'],p.attrib['data-horizontal-scale'])
            for filename in ('plan','profile'):
                s=Path(r[filename]).read_text();self.assertIn('merge/approach [authored; ramp]',s)
                self.assertIn('flyover/deck [preview; deck]',s);self.assertIn('stroke-dasharray="6 3"',s)
                self.assertIn('merge/signal/decision',s);self.assertIn('merge/merge/join',s)
            self.assertLess(len(json.dumps(r).encode()),4096)

    def test_full_controls_expose_interior_bow_and_do_not_clip_control_hull(self):
        with tempfile.TemporaryDirectory() as td:
            r=render_approach(brief(),Path(td)/'diagram',controls=packet())
            data=json.loads(Path(r['controls']).read_text());c=data['curves']['merge/authored/approach']
            # Independent Hermite midpoint lies outside the endpoint lateral range.
            y=.5*c['p0'][1]+.125*c['t0'][1]+.5*c['p1'][1]-.125*c['t1'][1]
            self.assertGreater(y,max(c['p0'][1],c['p1'][1]))
            self.assertEqual(c['p0'],[100,225,10]);self.assertEqual(c['t0'],[450,80,0])

    def test_saved_job_receipts_recorded_not_fresh_no_client_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            op=Operator(runs=td);folder=op.path('1234567890abcdef');folder.mkdir();b=brief()
            state={'kind':'approach','plan_hash':digest(b),'bindings':{'merge.road':{'edges':[
                {'id':42,'p0':[1,2,3],'p1':[10,2,3],'t0':[9,0,0],'t1':[9,0,0],
                 'structure':{'classification':'BRIDGE'}}]}}}
            (folder/'approach.json').write_text(json.dumps(b));(folder/'state.json').write_text(json.dumps(state))
            before={f.name:f.read_bytes() for f in folder.iterdir()}
            with patch.object(op,'client',side_effect=AssertionError('native call')):
                r=op.render_approach('1234567890abcdef',Path(td)/'diagram',families=['merge'])
            self.assertEqual(before,{f.name:f.read_bytes() for f in folder.iterdir()})
            self.assertFalse(r['fresh_readback']);self.assertEqual(r['curve_count'],1)
            self.assertIn('merge/native_42 [committed; deck]',Path(r['plan']).read_text())

    def test_missing_controls_remain_unavailable_and_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'diagram';r=render_approach(brief(),target)
            self.assertEqual(r['curve_count'],0);self.assertEqual(r['missing_controls'],['merge/approach'])
            before=(target/'plan.svg').read_bytes()
            with self.assertRaises(FileExistsError):render_approach(brief(),target)
            self.assertEqual(before,(target/'plan.svg').read_bytes())

    def test_rotated_profile_axis_world_packet_and_selected_families(self):
        with tempfile.TemporaryDirectory() as td:
            c=packet();c['curves'][1]['frame']='world'
            r=render_approach(brief(),Path(td)/'diagram',controls=c,families=['flyover'],profile_axis=[0,1])
            data=json.loads(Path(r['controls']).read_text());self.assertEqual(data['profile_axis'],[0,1])
            self.assertEqual(r['curve_count'],1);self.assertEqual(data['curves']['flyover/preview/deck']['p0'],[450,15,5])

    def test_invalid_nonfinite_overbudget_and_unknown_selections_rejected_before_output(self):
        for fault in ('finite','epoch','frame','budget','family'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as td:
                c=packet();kwargs={}
                if fault=='finite':c['curves'][0]['t0'][1]=float('nan')
                if fault=='epoch':c['curves'][0]['epoch']='native_fitted'
                if fault=='frame':c['curves'][0]['frame']='pixels'
                if fault=='budget':c['curves']*=129
                if fault=='family':kwargs['families']=['unknown']
                with self.assertRaises(ValueError):render_approach(brief(),Path(td)/'diagram',controls=c,**kwargs)
                self.assertFalse((Path(td)/'diagram').exists())

    def test_file_input_and_payload_curves_use_family_origin(self):
        with tempfile.TemporaryDirectory() as td:
            b=brief();c=packet()['curves'][0];b['families'][0]['payload']['curves']={'approach':{k:c[k] for k in ('p0','p1','t0','t1')}}
            f=Path(td)/'approach.json';f.write_text(json.dumps(b))
            r=render_approach(f,Path(td)/'diagram',families=['merge'])
            self.assertEqual(r['missing_control_count'],0);self.assertEqual(r['curve_count'],1)

    def test_cli_dispatch_compact_json_and_deterministic_output(self):
        with tempfile.TemporaryDirectory() as td:
            op=Operator(runs=td);input_file=Path(td)/'input.json';target=Path(td)/'diagram'
            input_file.write_text(json.dumps({'source':brief(),'output':str(target),'controls':packet()}))
            stdout=io.StringIO()
            with patch.object(bridge_operator,'Operator',return_value=op),patch('sys.argv',['bridge_operator.py','approach-render','--input',str(input_file)]),patch('sys.stdout',stdout),patch.object(op,'client',side_effect=AssertionError('native call')):
                self.assertEqual(bridge_operator.main(),0)
            r=json.loads(stdout.getvalue());self.assertEqual(r['curve_count'],2)
            second=render_approach(brief(),Path(td)/'repeat',controls=packet())
            for key in ('plan','profile','controls'):
                self.assertEqual(Path(r[key]).read_bytes(),Path(second[key]).read_bytes())


if __name__=='__main__':unittest.main()
