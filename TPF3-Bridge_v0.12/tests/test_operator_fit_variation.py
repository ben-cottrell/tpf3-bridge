import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bridge_operator import Operator,validate_plan,fit_variation_positions,fit_geometry_check


def edge(eid,a,b):
    d=[b[i]-a[i] for i in range(3)]
    return {'id':eid,'node0':eid*2,'node1':eid*2+1,'p0':a,'p1':b,'t0':d,'t1':d,'template':'track','style':'style','road_type':'TRACK'}


class Client:
    session='test';evidence=Path('.')
    def __init__(self,reject=0,geometry=None,unknown=False):
        self.source=edge(1,[0,0,2],[100,0,2]);self.target=edge(2,[100,5,2],[120,5,2]);self.calls=[];self.prepares=[];self.reject=reject;self.geometry=geometry;self.unknown=unknown
    def request(self,op,q,**kw):
        self.calls.append((op,copy.deepcopy(q)));base={'session':self.session,'operation':op,'request_id':str(len(self.calls)),'status':'ok'}
        if op=='inspect':return base|{'result':{'edges':[copy.deepcopy(self.source if eid==1 else self.target) for eid in q['edge_ids']]}}
        if q.get('execute'):
            return base|{'status':'error' if self.unknown else 'ok','result':{'game_constructed':'unknown' if self.unknown else True,'edges':[]}}
        self.prepares.append(copy.deepcopy(q))
        if len(self.prepares)<=self.reject:return base|{'status':'no_accepted_candidate','result':{'game_constructed':False,'evaluation':{'messages':['Construction Not Possible']}}}
        a,b=q['source']['pos'],q['target']['pos'];length=math.dist(a,b);control={'p0':a,'p1':b,'t0':[length,0,0],'t1':[length,0,0]}
        fit={'controls':[control]} if self.geometry is None else self.geometry(len(self.prepares),control)
        return base|{'result':{'game_constructed':False,'native_proposal_evaluated':True,'native_proposal_critical':False,'prepared_request':base['request_id'],'fit':fit}}
    def select(self,rc,loc,interior=False,**kw):
        if interior:
            p=loc['guide_xyz'];a={'edge_id':1,'edge_snapshot':self.source,'parameter':p[0]/100,'canonical_forward':True,'interior_eligible':True,'pos':p,'outward_direction':[1,0,0],'grade':0}
        else:a={'edge_id':2,'node_id':4,'edge_snapshot':self.target,'pos':[100,5,2],'outward_direction':[-1,0,0],'grade':0}
        return a,loc


def plan(c):
    return {'version':2,'revision':'fit-search','origin':[0,0,0],'region':{'min':[-2,-20,0],'max':[122,20,4]},'max_grade':.1,'track':{'template':'track','style':'style'},
            'ports':{'fixed':{'position':[100,5,2],'direction':[-1,0],'grade':0}},'port_refs':{'fixed':{'chain':'free','edge_id':2,'node_id':4}},
            'bindings':{'parent':{'edges':[c.source]},'free':{'edges':[c.target]}},'routes':[],'curves':{},
            'steps':[{'name':'fan','kind':'branch','source':{'curve':'parent','u':.3},'target':'fixed','radius':0,'candidates':[{'branch':'endpoint_cubic_level','through':'subdivide_fresh'}],
                      'fit_variation':{'source':{'max_shift':20,'step':5},'max_attempts':16,'max_requests':64}}]}


class FitVariationTest(unittest.TestCase):
    def execute(self,c,p=None):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);o=Operator(runs=directory.name,client=c)
        with patch('bridge_operator.live._select_throat_port',side_effect=c.select):
            run=o.plan(p or plan(c))['run'];result=o.execute(run)
        return o,run,result,json.loads((o.path(run)/'state.json').read_text())
    def test_nominal_first_accepts_normal_fan_s_and_builds_prepared_once(self):
        c=Client();o,run,result,state=self.execute(c);self.assertEqual(result['status'],'built');self.assertEqual(len(c.prepares),1)
        summary=state['fit_variations']['fan'];self.assertEqual(summary['selected_actual_shift_m'],{'source':0});self.assertEqual(summary['attempt_count'],1)
        self.assertEqual(summary['geometry_checks']['inflections'],1);self.assertTrue(summary['geometry_checks']['passed']);self.assertFalse(summary['boundary_proven'])
        self.assertEqual(sum(q.get('execute',False) for op,q in c.calls),1)
        with self.assertRaisesRegex(ValueError,'never replay'):o.execute(run)
    def test_reject_then_nearest_fit_keeps_exact_free_identity(self):
        c=Client(reject=2);o,run,result,state=self.execute(c);self.assertEqual(result['status'],'built')
        self.assertEqual([round(q['source']['pos'][0],6) for q in c.prepares],[30,35,25]);self.assertEqual({(q['target']['edge_id'],q['target']['node_id']) for q in c.prepares},{(2,4)})
        summary=state['fit_variations']['fan'];self.assertAlmostEqual(summary['selected_actual_shift_m']['source'],-5);self.assertEqual(summary['sampled_rejection_range_m']['source'],[0,5]);self.assertEqual(summary['attempt_count'],3)
    def test_complete_proposal_cnp_response_keeps_searching_declared_window(self):
        c=Client();original=c.request
        def request(op,q,**kw):
            response=original(op,q,**kw)
            if op=='interior_junction' and not q.get('execute'):
                response.update(status='no_accepted_candidate',result={'game_constructed':False,'search_complete':True,'stage':'prepare',
                    'candidate_rejections':[{'index':i,'branch':'endpoint_cubic_level','through':'subdivide_fresh',
                        'stage':'complete_proposal','status':'native_proposal_rejected',
                        'evaluation':{'critical':True,'messages':['Construction Not Possible']},
                        'through_evaluation':{'critical':False,'messages':{}}} for i in (1,2,3)]})
            return response
        c.request=request;o,run,result,state=self.execute(c)
        self.assertEqual(result['status'],'needs_attention');self.assertEqual(len(c.prepares),9)
        self.assertEqual(state['fit_variations']['fan']['attempt_count'],9)
        self.assertEqual(state['fit_variations']['fan']['sampled_rejection_range_m']['source'],[-20,20])
        self.assertFalse(state['steps']);self.assertIsNone(state['step_mutation'])
        self.assertFalse(any(q.get('execute') for op,q in c.calls))
    def test_resolution_order_bounds_and_more_than_eight_positions(self):
        c=Client();p=plan(c);s=p['steps'][0];s['fit_variation']['source']={'max_shift':23,'step':5};s['fit_variation']['max_attempts']=32
        validate_plan(p);positions,_=fit_variation_positions(s,{'parent':[c.source]});shifts=[d['source'] for a,d in positions]
        self.assertEqual(shifts,[0,5,-5,10,-10,15,-15,20,-20,23,-23]);self.assertTrue(all(0<a['source']['u']<1 for a,d in positions))
        for bad in [float('nan'),0,-1]:
            q=copy.deepcopy(p);q['steps'][0]['fit_variation']['source']['step']=bad
            with self.assertRaises(ValueError):validate_plan(q)
        p['steps'][0]['fit_variation']['target']={'max_shift':5,'step':1}
        with self.assertRaisesRegex(ValueError,'free endpoints'):validate_plan(p)
        boundary=copy.deepcopy(s);boundary['source']['u']=1;boundary['fit_variation'].pop('target');boundary['fit_variation']['source']['direction']='forward'
        self.assertEqual(fit_variation_positions(boundary,{'parent':[c.source]})[0],[])
    def test_request_budget_stops_before_dispatch_and_does_not_search_further(self):
        c=Client();p=plan(c);p['steps'][0]['fit_variation']['max_requests']=1
        o,run,result,state=self.execute(c,p);self.assertEqual(result['status'],'needs_attention');self.assertEqual(c.prepares,[]);self.assertIn('budget',state['error'])
    def test_unknown_build_stops_and_cannot_replay_or_continue(self):
        c=Client(unknown=True);o,run,result,state=self.execute(c);self.assertEqual(result['status'],'needs_attention');self.assertEqual(len(c.prepares),1)
        with self.assertRaisesRegex(ValueError,'never replay'):o.execute(run)
        with self.assertRaisesRegex(ValueError,'uncertain/partial'):o.continue_plan(run,'retry')
    def test_geometry_rejection_skips_build_and_unknown_controls_are_unverified(self):
        def geometry(number,control):
            if number==1:control['t0'][1]=50;control['t1'][1]=-50
            return {'controls':[control]}
        c=Client(geometry=geometry);p=plan(c);p['steps'][0]['fit_variation']['intent']={'envelope':{'min':[-2,-2,0],'max':[122,10,4]}}
        o,run,result,state=self.execute(c,p);self.assertEqual(result['status'],'built');self.assertEqual(len(c.prepares),2);self.assertEqual(state['candidates']['fan'][0]['status'],'intent_rejected');self.assertEqual(sum(q.get('execute',False) for op,q in c.calls),1)
        c=Client(geometry=lambda n,ctrl:None);o,run,result,state=self.execute(c);self.assertEqual(result['status'],'built');self.assertFalse(state['fit_variations']['fan']['geometry_checks']['available']);self.assertIsNone(state['fit_variations']['fan']['geometry_checks']['passed'])
        c=Client(geometry=lambda n,ctrl:None);p=plan(c);p['steps'][0]['fit_variation']['intent']={'max_extra_inflections':0};o,run,result,state=self.execute(c,p)
        self.assertEqual(result['status'],'needs_attention');self.assertIn('cannot be checked',state['error']);self.assertEqual(sum(q.get('execute',False) for op,q in c.calls),0)
    def test_report_uses_native_parameter_displacement_not_requested_shift(self):
        c=Client();original=c.select
        def select(rc,loc,interior=False,**kw):
            a,b=original(rc,loc,interior,**kw)
            if interior:a['parameter']+=.001;a['pos']=[a['pos'][0]+.1,*a['pos'][1:]]
            return a,b
        c.select=select;o,run,result,state=self.execute(c);summary=state['fit_variations']['fan'];self.assertEqual(summary['selected_requested_shift_m']['source'],0);self.assertAlmostEqual(summary['selected_actual_shift_m']['source'],.1)
    def test_crossover_slides_both_named_chains_in_nearest_order(self):
        c=Client(reject=3);original=c.select
        def select(rc,loc,interior=False,**kw):
            if loc['guide_xyz'][1]==5:
                point=loc['guide_xyz'];return {'edge_id':2,'edge_snapshot':c.target,'parameter':(point[0]-100)/20,'canonical_forward':True,'interior_eligible':True,'pos':point,'outward_direction':[1,0,0],'grade':0},loc
            return original(rc,loc,interior,**kw)
        c.select=select;p=plan(c);s=p['steps'][0];s.update(kind='crossover',target={'curve':'free','u':.5});s['fit_variation']['source']={'max_shift':5,'step':5};s['fit_variation']['target']={'max_shift':5,'step':5}
        o,run,result,state=self.execute(c,p);self.assertEqual(result['status'],'built');self.assertEqual([(round(q['source']['pos'][0]),round(q['target']['pos'][0])) for q in c.prepares],[(30,110),(35,110),(25,110),(30,115)])
        self.assertAlmostEqual(state['fit_variations']['fan']['selected_actual_shift_m']['target'],5)
    def test_wrong_chain_and_free_endpoint_identity_fail_without_proposal(self):
        for wrong in ('chain','free'):
            c=Client();original=c.select
            def select(rc,loc,interior=False,**kw):
                a,b=original(rc,loc,interior,**kw)
                if (wrong=='chain' and interior) or (wrong=='free' and not interior):a['edge_id']=999
                return a,b
            c.select=select;o,run,result,state=self.execute(c);self.assertEqual(result['status'],'needs_attention');self.assertEqual(c.prepares,[])
    def test_extra_reversal_and_backtracking_checks_are_sampled(self):
        region={'min':[-100,-100,-1],'max':[200,100,1]};straight={'p0':[0,0,0],'p1':[100,0,0],'t0':[100,0,0],'t1':[100,0,0]};s=straight|{'p1':[100,10,0]}
        self.assertTrue(fit_geometry_check([s],[s],{},region)['passed'])
        self.assertIn('extra sampled curvature reversals',fit_geometry_check([s],[straight],{},region)['reasons'])
        back=straight|{'t0':[-50,0,0]};self.assertIn('sampled longitudinal backtracking',fit_geometry_check([back],[straight],{},region)['reasons'])


if __name__=='__main__':unittest.main()
