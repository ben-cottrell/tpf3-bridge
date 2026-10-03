import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import contextlib
import io
from bridge_live import connect_adjacent, reconcile_constructed_crossover, connect_throat, validate_throat_brief, _select_throat_port, is_mutation, LiveClient, LiveError, MARKER, lua_literal, parse_response, main, extend, connect, route, discover, connect_selected, connect_brief, connect_corridor, connect_junction, connect_junction_at, reconcile_rejected_junction, reconcile_rejected_fixture, reconcile_rejected_connection, reconcile_constructed_connection, reconcile_constructed_interior, discover_session, client_from_context

class LiveClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'stdout.txt'
        self.log.write_bytes(b'old output\n')
        self.client = LiveClient(self.root / 'mod', self.log, self.root / 'evidence', 'test_session', .5)

    def response(self, request_id='r1', operation='inspect', **changes):
        return dict(version=1, session='test_session', request_id=request_id,
                    operation=operation, status='ok', **changes)

    def engineering_readback(self,radius=100):
        return {'engineering_checks_verified':True,'requested_min_radius':radius,'min_sampled_radius':radius+1,'max_sampled_grade':0}

    def test_data_literals_cannot_escape_strings(self):
        data = lua_literal({'x': '";os.execute("evil")--\n£', 'a': [True, 3.5]})
        self.assertIn('\\034;os.execute(\\034evil\\034)', data)
        self.assertIn('\\010\\194\\163', data)
        self.assertNotIn('\n', data)
        with self.assertRaises(ValueError):
            lua_literal(float('nan'))

    def test_correlation_and_bad_framing(self):
        self.assertIsNone(parse_response('not a response', 'r1', 'test_session', 'inspect'))
        self.assertIsNone(parse_response(MARKER + '{bad}', 'r1', 'test_session', 'inspect'))
        self.assertIsNone(parse_response(MARKER + json.dumps(self.response('other')), 'r1', 'test_session', 'inspect'))
        response = self.response(); response['session'] = 'other'
        with self.assertRaises(LiveError) as ctx:
            parse_response(MARKER + json.dumps(response), 'r1', 'test_session', 'inspect')
        self.assertEqual(ctx.exception.status, 'protocol_error')

    def test_partial_log_response(self):
        def worker():
            slot = self.root / 'mod/content/scripts/pif_live/test_session/000001.lua'
            deadline = time.monotonic() + 1
            while not slot.exists() and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertTrue(slot.read_text().startswith('return {'))
            line = (MARKER + json.dumps(self.response()) + '\n').encode()
            with self.log.open('ab') as stream:
                stream.write(b'unrelated\n' + line[:30]);stream.flush()
                time.sleep(.025)
                stream.write(line[30:]);stream.flush()
        thread = threading.Thread(target=worker);thread.start()
        result = self.client.request('inspect', {'edge_ids': [1]}, request_id='r1')
        thread.join()
        self.assertEqual(result['status'], 'ok')
        self.assertNotIn('pending', json.loads(self.client.journal.read_text()))
        self.assertTrue((self.root / 'evidence/r1.response.json').exists())

    def test_timed_out_build_is_not_replayed_on_restart(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError) as ctx:
            self.client.request('build', {'fit_request': 'fit1'}, request_id='build1')
        self.assertEqual(ctx.exception.status, 'mutation_outcome_unknown')
        restarted = LiveClient(self.client.mod, self.log, self.client.evidence, 'test_session', .02)
        with self.assertRaises(LiveError) as ctx:
            restarted.request('build', {'fit_request': 'fit1'}, request_id='build2')
        self.assertEqual(ctx.exception.status, 'reconciliation_required')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_late_rejection_with_unknown_effects_still_blocks_mutation(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError):
            self.client.request('connection', {'execute': True, 'brief': {}}, request_id='late')
        response = self.response('late', 'connection', result={'game_constructed': 'unknown'})
        response['status'] = 'error'
        with self.log.open('a') as stream:
            stream.write(MARKER + json.dumps(response) + '\n')
        self.assertEqual(self.client.reconcile_pending()['status'], 'error')
        self.assertIn('pending', json.loads(self.client.journal.read_text()))
        with self.assertRaises(LiveError) as ctx:
            self.client.request('connection', {'execute': True, 'brief': {}}, request_id='again')
        self.assertEqual(ctx.exception.status, 'reconciliation_required')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_finite_timeout_and_single_worker(self):
        with self.assertRaises(ValueError):
            LiveClient(self.client.mod, self.log, self.client.evidence, 'test_session', float('inf'))
        (self.client.evidence / 'client.lock').touch()
        with self.assertRaises(LiveError) as ctx:
            self.client.request('inspect', {})
        self.assertEqual(ctx.exception.status, 'client_busy')

    def test_uncertain_compound_extension_cannot_replay_after_restart(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError) as ctx:
            self.client.request('extension', {'execute': True, 'brief': {}}, request_id='extension1')
        self.assertEqual(ctx.exception.status, 'mutation_outcome_unknown')
        restarted = LiveClient(self.client.mod, self.log, self.client.evidence, 'test_session', .02)
        with self.assertRaises(LiveError) as ctx:
            restarted.request('extension', {'execute': True, 'brief': {}}, request_id='extension2')
        self.assertEqual(ctx.exception.status, 'reconciliation_required')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_rejection_unknown_effects_allows_inspection_but_not_mutation(self):
        def worker():
            for sequence, rid, op, result in [(1, 'reject', 'extension', {'game_constructed': 'unknown'}),
                                              (2, 'observe', 'inspect', {'edges': [1]})]:
                slot = self.client.mod / f'content/scripts/pif_live/test_session/{sequence:06d}.lua'
                deadline = time.monotonic() + 1
                while not slot.exists() and time.monotonic() < deadline:
                    time.sleep(.005)
                response = self.response(rid, op, result=result)
                if rid == 'reject':
                    response['status'] = 'error'
                with self.log.open('a') as stream:
                    stream.write(MARKER + json.dumps(response) + '\n')
        thread = threading.Thread(target=worker); thread.start()
        self.client.request('extension', {'execute': True}, request_id='reject')
        self.client.request('inspect', {'edge_ids': [1]}, request_id='observe')
        thread.join()
        self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'], 'reject')
        with self.assertRaises(LiveError):
            self.client.request('extension', {'execute': True}, request_id='repeat')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 2)

    def route_brief(self):
        return {'source_edge':10,'source_node':11,'target_edge':20,'target_node':21,
                'mode':'TRAIN','max_length':300,'required_edges':[30,31]}

    def discovery_record(self):
        def candidate(edge,node,ref):
            return dict(ref=ref,edge_id=edge,node_id=node,eligible=True,incidence_complete=True,
                        incident_count=1,incident_edges=[edge],edge_snapshot={'id':edge})
        return self.response('discovery','discover',result={'candidates':[candidate(10,11,'source'),candidate(20,21,'target')]})

    def selected_brief(self):
        return {'source_ref':'source','target_ref':'target','radius':100,
                'region':{'min':[0,0,-10],'max':[300,300,10]}}

    def project_brief(self):
        region={'min':[-10,-10,-10],'max':[100,100,10]}
        intent={'region':region,'max_edges':8,'guide_xyz':[0,0,0],
                'travel_direction':[1,0],'heading_tolerance_deg':5}
        return {'source':intent,'target':intent|{'guide_xyz':[20,0,0]},'radius':100,
                'region':region,'vertical':{'max_grade':.04},'max_fit_attempts':2,'max_route_length':300}

    def project_query(self, *, failure=None, extra=False, truncated=False):
        counter={'discover':0,'native':0};calls=[]
        def candidate(edge,node,ref,pos,direction):
            return dict(ref=ref,edge_id=edge,node_id=node,pos=pos,outward_direction=direction,
                        eligible=True,incidence_complete=True,incident_count=1,incident_edges=[edge],
                        edge_snapshot={'id':edge,'node0':node if edge==20 else node-1,'node1':node+1 if edge==20 else node})
        def query(op,params):
            calls.append((op,params))
            if op=='discover':
                counter['discover']+=1;source=counter['discover']==1
                cs=[candidate(10,11,'src',[0,0,0],[1,0,0])] if source else [candidate(20,21,'dst',[20,0,0],[-1,0,0])]
                if source and extra:cs.append(candidate(12,13,'alt',[1,0,0],[1,0,0]))
                # A closer opposite-direction endpoint must never be silently reversed.
                cs.append(candidate(50,51,'wrong_src' if source else 'wrong_dst',[0,0,0],[-1,0,0] if source else [1,0,0]))
                return self.response('ds' if source else 'dt',op,result={'candidates':cs,'complete':not truncated})
            if op=='selected_connection':
                counter['native']+=1
                if failure in ('fit','budget') and (failure=='budget' or counter['native']==1):
                    return self.response('fit'+str(counter['native']),op,result={'stage':'fit','game_constructed':False,'error':'unsupported_reverse_geometry'})|{'status':'error'}
                if failure=='build':
                    return self.response('rejected',op,result={'stage':'build','game_constructed':'unknown','error':'native_construction_rejected'})|{'status':'error'}
                a=params['source'];b=params['target']
                return self.response('native',op,result={'game_constructed':params['execute'],'fit':{'pieces':1},
                    'readback':self.engineering_readback(params['radius'])|{'connected':True,'ordered_edges':[30],'ordered_nodes':[a['node_id'],b['node_id']],
                        'attachments':{'source_edge':a['edge_id'],'target_edge':b['edge_id']}}})
            self.assertEqual(op,'route')
            return self.response('route',op,result={'requested_route_verified':failure!='route','total_path_length':40})
        return query,calls

    def test_project_default_and_execute_select_directions_and_exact_attachments(self):
        for execute in (False,True):
            query,calls=self.project_query(truncated=True)
            with patch.object(self.client,'request',side_effect=query):value=connect_brief(self.client,self.project_brief(),execute=execute)
            self.assertEqual(value['status'],'ok');self.assertIs(value['discovery_complete'],False)
            self.assertEqual(value['selected'],{'source_edge':10,'source_node':11,'target_edge':20,'target_node':21})
            self.assertEqual([c[0] for c in calls],['discover','discover','selected_connection']+(['route'] if execute else []))
            self.assertIs(calls[2][1]['execute'],execute)
            if execute:self.assertEqual(calls[-1][1]['required_edges'],[30]);self.assertTrue(value['native_route_verified'])
            self.assertLessEqual(len(json.dumps(value).encode()),4096)
            self.assertTrue(Path(value['evidence']).exists())

    def test_project_fit_alternative_is_bounded_and_does_not_retry_build(self):
        for failure,status,attempts in [('fit','ok',2),('build','error',1),('budget','no_accepted_candidate',2),('route','native_route_unverified',1)]:
            query,calls=self.project_query(failure=failure,extra=True)
            with patch.object(self.client,'request',side_effect=query):value=connect_brief(self.client,self.project_brief(),execute=True)
            self.assertEqual(value['status'],status);self.assertEqual(value['attempt_count'],attempts)
            if failure=='route':self.assertIs(value['game_constructed'],True)
        query,calls=self.project_query(failure='budget',extra=True);brief=self.project_brief()|{'max_fit_attempts':1}
        with patch.object(self.client,'request',side_effect=query):value=connect_brief(self.client,brief)
        self.assertEqual(value['status'],'search_budget_exhausted')

    def test_project_no_candidates_and_bad_briefs_never_build(self):
        b=self.project_brief();b['source']=b['source']|{'travel_direction':[0,1]}
        query,calls=self.project_query()
        with patch.object(self.client,'request',side_effect=query):value=connect_brief(self.client,b,execute=True)
        self.assertEqual(value['status'],'no_eligible_candidates');self.assertEqual(len(calls),2)
        for brief in (self.project_brief()|{'max_fit_attempts':17},self.project_brief()|{'max_route_length':float('nan')},
                      self.project_brief()|{'region':{'min':[0,0,-10],'max':[1001,300,10]}},
                      self.project_brief()|{'source':b['source']|{'travel_direction':[0,0]}},
                      self.project_brief()|{'target':b['target']|{'heading_tolerance_deg':True}}):
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):connect_brief(self.client,brief)
                calls.assert_not_called()

    def test_project_pending_blocks_execute_and_selected_execution_is_a_mutation(self):
        self.client.journal.write_text(json.dumps({'session':'test_session','pending':{'request_id':'old'},'next_sequence':1}))
        with patch.object(self.client,'request') as calls:
            value=connect_brief(self.client,self.project_brief(),execute=True)
            self.assertEqual(value['status'],'reconciliation_required');calls.assert_not_called()
        with self.assertRaises(LiveError) as error:self.client.request('selected_connection',{'execute':True})
        self.assertEqual(error.exception.status,'reconciliation_required')
        self.client.journal.unlink();self.client.timeout=.01
        with self.assertRaises(LiveError) as error:self.client.request('selected_connection',{'execute':True})
        self.assertEqual(error.exception.status,'mutation_outcome_unknown')

    def test_project_cli_routes_new_brief_to_one_callable(self):
        params=self.root/'project.json';params.write_text(json.dumps(self.project_brief()))
        args=['connect-brief','--params',str(params),'--mod-directory',str(self.client.mod),'--log',str(self.log),'--evidence',str(self.client.evidence),'--session','test_session','--execute']
        with patch('bridge_live.connect_brief',return_value={'status':'ok','native_route_verified':True}) as call,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),0);self.assertTrue(call.call_args.kwargs['execute'])

    def corridor_brief(self):
        return self.project_brief()|{'guides':[{'position':[10,1,1],'travel_direction':[1,0],'grade':.01}],
            'region':{'min':[-50,-50,-10],'max':[1500,300,20]},'max_route_length':2000}

    def test_corridor_fit_only_has_no_realised_guide_identity(self):
        query,calls=self.project_query()
        def worker(op,p):
            if op=='corridor':
                self.assertEqual(p['guides'],self.corridor_brief()['guides'])
                return self.response('cf',op,result={'game_constructed':False,'fit':{'legs':[{'index':1},{'index':2}]}})
            return query(op,p)
        with patch.object(self.client,'request',side_effect=worker):v=connect_corridor(self.client,self.corridor_brief())
        self.assertEqual(v['status'],'ok');self.assertFalse(v['guide_nodes_realised']);self.assertFalse(v['game_constructed'])
        self.assertNotIn('guide_nodes',v);self.assertEqual(len(v['legs']),2)

    def test_corridor_build_requires_exact_guide_readback_then_overall_route(self):
        for verified in (True,False):
            query,calls=self.project_query()
            def worker(op,p):
                if op=='corridor':
                    return self.response('cb',op,result={'game_constructed':True,'fit':{'legs':[{'index':1},{'index':2}]},
                        'readback':self.engineering_readback(p['radius'])|{'connected':True,'ordered_edges':[30,31],'ordered_nodes':[11,40,21],
                            'attachments':{'source_edge':10,'target_edge':20},'realised_guides':[{'node':40,'verified':verified}]}})
                if op=='route':self.assertEqual(p['required_edges'],[30,31]);self.assertEqual(p['max_length'],2000)
                return query(op,p)
            with patch.object(self.client,'request',side_effect=worker):v=connect_corridor(self.client,self.corridor_brief(),execute=True)
            self.assertEqual(v['status'],'ok' if verified else 'native_verification_failed');self.assertTrue(v['game_constructed'])
            if verified:self.assertEqual(v['guide_nodes'],[40]);self.assertTrue(v['native_route_verified'])
            else:self.assertNotIn('native_route_verified',v)
            self.assertLessEqual(len(json.dumps(v).encode()),4096)

    def test_corridor_partial_and_uncertain_mutation_never_replayed(self):
        for status,constructed in [('mutation_unverified','unknown'),('mutation_unverified',True),('error','unknown')]:
            query,calls=self.project_query();native_calls=[]
            def worker(op,p):
                if op=='corridor':
                    native_calls.append(p)
                    return self.response('partial',op,result={'stage':'build','game_constructed':constructed,'error':'partial_native_effects'})|{'status':status}
                return query(op,p)
            with patch.object(self.client,'request',side_effect=worker):v=connect_corridor(self.client,self.corridor_brief(),execute=True)
            self.assertEqual(v['status'],status);self.assertEqual(v['game_constructed'],constructed);self.assertEqual(len(native_calls),1)
            self.assertEqual(len(calls),2)
        self.client.timeout=.01
        with self.assertRaises(LiveError) as error:self.client.request('corridor',{'execute':True})
        self.assertEqual(error.exception.status,'mutation_outcome_unknown')

    def test_corridor_invalid_guides_fail_before_discovery(self):
        valid=self.corridor_brief()
        for guides in ([], valid['guides']*4,[valid['guides'][0]|{'grade':.05}],
                       [valid['guides'][0]|{'position':[10,1,float('nan')]}],
                       [valid['guides'][0]|{'travel_direction':[0,0]}],
                       [valid['guides'][0]|{'position':[10,1,30]}]):
            with patch.object(self.client,'request') as request:
                with self.assertRaises(ValueError):connect_corridor(self.client,valid|{'guides':guides})
                request.assert_not_called()
        with patch.object(self.client,'request') as request:
            with self.assertRaises(ValueError):connect_corridor(self.client,valid|{'max_route_length':4001})
            request.assert_not_called()

    def test_corridor_cli_and_no_direction_candidate(self):
        params=self.root/'corridor.json';params.write_text(json.dumps(self.corridor_brief()))
        args=['connect-corridor','--params',str(params),'--mod-directory',str(self.client.mod),'--log',str(self.log),'--evidence',str(self.client.evidence),'--session','test_session']
        with patch('bridge_live.connect_corridor',return_value={'status':'ok'}) as call,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),0);self.assertFalse(call.call_args.kwargs['execute'])
        b=self.corridor_brief();b['source']=b['source']|{'travel_direction':[0,1]}
        query,calls=self.project_query()
        with patch.object(self.client,'request',side_effect=query):v=connect_corridor(self.client,b,execute=True)
        self.assertEqual(v['status'],'no_eligible_candidates');self.assertEqual(len(calls),2)

    def test_native_orientation_counts_are_evidence_not_direction_rewrites(self):
        query,calls=self.project_query();orientation={'forward_parts':2,'backward_parametrised_parts':1}
        def worker(op,p):
            response=query(op,p)
            if op=='selected_connection':response['result']['fit']['native_orientation']=orientation
            return response
        with patch.object(self.client,'request',side_effect=worker):v=connect_brief(self.client,self.project_brief())
        self.assertEqual(v['fit']['native_orientation'],orientation)
        self.assertEqual(calls[2][1]['source']['outward_direction'],[1,0,0])
        self.assertEqual(calls[2][1]['target']['outward_direction'],[-1,0,0])
        self.assertFalse(v['game_constructed']);self.assertLessEqual(len(json.dumps(v).encode()),4096)

    def junction_query(self, *, failure=None):
        base,_=self.project_query();calls=[]
        def query(op,p):
            calls.append((op,p))
            if op=='discover_junction':
                r=base('discover',p);r['operation']=op
                c=r['result']['candidates'][0]
                c.update(eligible=False,junction_eligible=True,incident_count=2,incident_edges=[10,12],
                         through_edge=12,through_snapshot={'id':12,'node0':11,'node1':13})
                if failure=='eligibility':c['junction_eligible']=False
                if failure=='incidence':c['incident_edges']=[10,99]
                return r
            if op=='junction':
                r=base('selected_connection',p);r['operation']=op
                r['result'].update(through_before={'requested_route_verified':True},
                    through_after={'requested_route_verified':failure!='through','total_path_length':30},
                    branch_after={'requested_route_verified':failure!='native_branch'},
                    junction={'node':11,'incoming_edge':10,'through_edge':12,'branch_edge':30,
                              'incident_edges':[10,12,30],'exact_native_identity':True,'through_route_verified':True,
                              'branch_geometry_verified':failure!='geometry'})
                if failure=='identity':r['result']['junction']['node']=999
                if failure=='unknown':r.update(status='mutation_unverified');r['result'].update(stage='build',game_constructed='unknown')
                return r
            if op=='route' and failure=='branch':return self.response('route',op,result={'requested_route_verified':False})
            return base(op,p)
        return query,calls

    def test_junction_fit_only_and_execute_require_both_movements(self):
        for execute in (False,True):
            query,calls=self.junction_query()
            with patch.object(self.client,'request',side_effect=query):v=connect_junction(self.client,self.project_brief(),execute=execute)
            self.assertEqual(v['status'],'ok');self.assertEqual(v['operation'],'connect-junction')
            self.assertEqual([x[0] for x in calls],['discover_junction','discover','junction']+(['route'] if execute else []))
            self.assertTrue(v['through_before_verified']);self.assertEqual(v['game_constructed'],execute)
            if execute:self.assertEqual(v['junction']['incident_edges'],[10,12,30]);self.assertTrue(v['native_route_verified'])
            else:self.assertNotIn('junction',v)
            self.assertLessEqual(len(json.dumps(v).encode()),4096)

    def test_junction_degree_three_or_through_failure_is_not_success(self):
        for failure in ('identity','through','branch','native_branch','geometry'):
            query,calls=self.junction_query(failure=failure)
            with patch.object(self.client,'request',side_effect=query):v=connect_junction(self.client,self.project_brief(),execute=True)
            self.assertEqual(v['status'],'native_route_unverified' if failure=='branch' else 'native_verification_failed')
            self.assertTrue(v['game_constructed']);self.assertEqual(sum(x[0]=='junction' for x in calls),1)

    def test_junction_wrong_attachment_never_executes(self):
        for failure,status in [('eligibility','no_eligible_candidates'),('incidence','local_input_or_storage_error')]:
            query,calls=self.junction_query(failure=failure)
            with patch.object(self.client,'request',side_effect=query):v=connect_junction(self.client,self.project_brief(),execute=True)
            self.assertEqual(v['status'],status);self.assertFalse(v['game_constructed'])
            self.assertEqual(len(calls),2)

    def test_junction_unknown_mutation_never_replayed(self):
        query,calls=self.junction_query(failure='unknown')
        with patch.object(self.client,'request',side_effect=query):v=connect_junction(self.client,self.project_brief(),execute=True)
        self.assertEqual(v['status'],'mutation_unverified');self.assertEqual(v['game_constructed'],'unknown');self.assertEqual(len(calls),3)
        self.client.timeout=.01
        with self.assertRaises(LiveError) as error:self.client.request('junction',{'execute':True})
        self.assertEqual(error.exception.status,'mutation_outcome_unknown')

    def test_junction_keeps_free_endpoint_and_constraint_checks(self):
        query,calls=self.junction_query()
        b=self.project_brief();b['source']=b['source']|{'travel_direction':[0,1]}
        with patch.object(self.client,'request',side_effect=query):v=connect_junction(self.client,b,execute=True)
        self.assertEqual(v['status'],'no_eligible_candidates');self.assertEqual(len(calls),2)
        with patch.object(self.client,'request') as call:
            with self.assertRaises(ValueError):connect_junction(self.client,self.project_brief()|{'radius':0})
            call.assert_not_called()

    def test_junction_cli_explicit_execution(self):
        params=self.root/'junction.json';params.write_text(json.dumps(self.project_brief()))
        args=['connect-junction','--params',str(params),'--mod-directory',str(self.client.mod),'--log',str(self.log),'--evidence',str(self.client.evidence),'--session','test_session','--execute']
        with patch('bridge_live.connect_junction',return_value={'status':'ok'}) as call,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),0);self.assertTrue(call.call_args.kwargs['execute'])

    def interior_query(self, defect=None):
        base,_=self.project_query();calls=[]
        def query(op,p):
            calls.append((op,p))
            if op=='discover_interior':
                v=base('discover',p);v['operation']=op;c=v['result']['candidates'][0]
                c.pop('node_id');c.update(interior_eligible=True,parameter=.5)
                if defect=='location':c['parameter']=0
                return v
            if op=='interior_junction':
                v=base('selected_connection',p|{'source':p['source']|{'node_id':99}});v['operation']=op
                incoming={'id':40,'node0':10,'node1':99};through={'id':41,'node0':99,'node1':11}
                v['result']['readback']['attachments']['source_edge']=40
                v['result'].update(through_before={'requested_route_verified':True},through_after={'requested_route_verified':defect!='through','total_path_length':20},
                    branch_after={'requested_route_verified':True},placement={'original_edge':10,'original_nodes':[10,11],'parameter':.5,'position':[0,0,0],
                    'junction_node':99,'replacement_edges':[40,41],'incoming':incoming,'through':through,'original_removed':defect!='removed','subdivision_sampled_verified':True},
                    junction={'node':99,'incoming_edge':40,'through_edge':41,'branch_edge':30,'incident_edges':[40,41,30],
                    'exact_native_identity':True,'branch_geometry_verified':True})
                if defect=='unknown':v['status']='mutation_unverified';v['result'].update(game_constructed='unknown',stage='build')
                return v
            return base(op,p)
        return query,calls

    def test_interior_fit_only_and_exact_replacement_execution(self):
        for execute in (False,True):
            query,calls=self.interior_query()
            with patch.object(self.client,'request',side_effect=query):v=connect_junction_at(self.client,self.project_brief()|{'placement_tolerance':1},execute=execute)
            self.assertEqual(v['status'],'ok');self.assertEqual(v['game_constructed'],execute)
            self.assertEqual([x[0] for x in calls],['discover_interior','discover','interior_junction']+(['route'] if execute else []))
            if execute:
                self.assertEqual(v['selected']['original_source_edge'],10);self.assertEqual(v['selected']['source_edge'],40)
                self.assertEqual(calls[-1][1]['source_edge'],40);self.assertEqual(v['placement']['replacement_edges'],[40,41])
            else:self.assertNotIn('placement',v);self.assertNotIn('junction',v)
            self.assertLessEqual(len(json.dumps(v).encode()),4096)

    def test_interior_bad_location_and_replacement_evidence_are_not_success(self):
        for defect,status in [('location','local_input_or_storage_error'),('removed','native_verification_failed'),('through','native_verification_failed')]:
            query,calls=self.interior_query(defect)
            with patch.object(self.client,'request',side_effect=query):v=connect_junction_at(self.client,self.project_brief()|{'placement_tolerance':1},execute=True)
            self.assertEqual(v['status'],status);self.assertEqual(v['game_constructed'],defect!='location')
            self.assertNotIn('route',[x[0] for x in calls])

    def test_interior_unknown_mutation_is_not_replayed(self):
        query,calls=self.interior_query('unknown')
        with patch.object(self.client,'request',side_effect=query):v=connect_junction_at(self.client,self.project_brief()|{'placement_tolerance':1},execute=True)
        self.assertEqual(v['status'],'mutation_unverified');self.assertEqual(v['game_constructed'],'unknown');self.assertEqual(len(calls),3)

    def test_interior_invalid_tolerance_stops_before_native_commands(self):
        for tol in (0,11,True,float('nan')):
            with patch.object(self.client,'request') as call:
                with self.assertRaises(ValueError):connect_junction_at(self.client,self.project_brief()|{'placement_tolerance':tol},execute=True)
                call.assert_not_called()

    def test_interior_cli_defaults_to_fit_only(self):
        params=self.root/'interior.json';params.write_text(json.dumps(self.project_brief()|{'placement_tolerance':1}))
        args=['connect-junction-at','--params',str(params),'--mod-directory',str(self.client.mod),'--log',str(self.log),'--evidence',str(self.client.evidence),'--session','test_session']
        with patch('bridge_live.connect_junction_at',return_value={'status':'ok'}) as call,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args),0);self.assertFalse(call.call_args.kwargs['execute'])

    def test_interior_reconciliation_reads_exact_receipt_without_replay(self):
        for defect in (None,'incomplete','unverified','unknown'):
            params={'execute':True,'source':{'edge_id':10,'parameter':.5},'target':{}}
            pending={'operation':'interior_junction','request_id':'built','params':params}
            self.client.journal.write_text(json.dumps({'pending':pending}))
            response=self.response('built','interior_junction',result={'game_constructed':True,'returned_edges':[40,41,30],'fit':{'pieces':1,'controls':[{}]}})
            response['status']='mutation_unverified'
            if defect=='unknown':response['result']['game_constructed']='unknown'
            (self.client.evidence/'built.response.json').write_text(json.dumps(response))
            result={'reconciled_current_state':True,'readback':{'connected':True,'ordered_edges':[30]},
                'placement':{'original_removed':True,'original_edge':10,'replacement_edges':[40,41]},
                'junction':{'exact_native_identity':True,'branch_geometry_verified':True},
                'through_after':{'requested_route_verified':True},'branch_after':{'requested_route_verified':True}}
            if defect=='incomplete':result['placement']['replacement_edges']=[40]
            if defect=='unverified':result['branch_after']['requested_route_verified']=False
            with patch.object(self.client,'request',return_value={'status':'ok','request_id':'verify','result':result}) as call:
                if defect:
                    with self.assertRaises(LiveError):reconcile_constructed_interior(self.client)
                    self.assertIn('pending',json.loads(self.client.journal.read_text()))
                    if defect=='unknown':call.assert_not_called()
                else:
                    v=reconcile_constructed_interior(self.client);self.assertEqual(v['status'],'ok')
                    self.assertNotIn('pending',json.loads(self.client.journal.read_text()));self.assertFalse(v['result']['automatic_replay'])
                if defect!='unknown':self.assertEqual(call.call_count,1);self.assertEqual(call.call_args.args[0],'verify_interior');self.assertFalse(call.call_args.args[1]['execute'])

    def test_discovery_invalid_bounds_never_query(self):
        for params in ({'region':{'min':[0,0,0],'max':[401,1,1]},'max_edges':1},
                       {'region':{'min':[0,0,0],'max':[1,1,1]},'max_edges':True}):
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):discover(self.client,params)
                calls.assert_not_called()

    def test_discovery_preserves_truncation_and_exact_candidates(self):
        response=self.discovery_record();response['result']['truncated']=True
        brief={'region':self.selected_brief()['region'],'max_edges':1}
        with patch.object(self.client,'request',return_value=response) as calls:
            self.assertIs(discover(self.client,brief),response)
            calls.assert_called_once_with('discover',brief)

    def test_selected_candidates_one_fit_only_native_request(self):
        record=self.discovery_record();brief=self.selected_brief()
        with patch.object(self.client,'request',return_value=self.response(operation='selected_connection')) as calls:
            connect_selected(self.client,record,brief)
        args=calls.call_args.args
        self.assertEqual(args[0],'selected_connection');self.assertNotIn('execute',args[1])
        self.assertEqual(args[1]['source']['node_id'],11);self.assertEqual(args[1]['discovery_request'],'discovery')
        self.assertEqual(calls.call_count,1)

    def test_ineligible_stale_missing_or_ambiguous_selection_never_sends(self):
        for defect in ('nonfree','incomplete','stale','missing','ambiguous'):
            record=self.discovery_record();brief=self.selected_brief()
            if defect=='nonfree':record['result']['candidates'][0]['incident_count']=2
            elif defect=='incomplete':record['result']['candidates'][0]['incidence_complete']=False
            elif defect=='stale':record['session']='old_session'
            elif defect=='missing':brief['source_ref']='missing'
            else:record['result']['candidates'].append(record['result']['candidates'][0])
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):connect_selected(self.client,record,brief)
                calls.assert_not_called()

    def test_selected_cli_default_fit_only_and_forbids_execute(self):
        params=self.root/'selection.json';params.write_text(json.dumps(self.selected_brief()))
        record=self.root/'discovery.json';record.write_text(json.dumps(self.discovery_record()))
        output=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request',return_value=self.response(operation='selected_connection')) as calls,contextlib.redirect_stdout(output):
            self.assertEqual(main(['connect-selected','--context','context.json','--params',str(params),'--discovery',str(record)]),0)
            self.assertEqual(main(['connect-selected','--context','context.json','--params',str(params),'--discovery',str(record),'--execute']),1)
        self.assertEqual(calls.call_count,1)

    def test_discovery_cli_compact_preview_keeps_selection_references(self):
        record=self.discovery_record();record['result']['edges']=['x'*10000]
        params=self.root/'area.json';params.write_text(json.dumps({'region':self.selected_brief()['region'],'max_edges':16}))
        output=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request',return_value=record),contextlib.redirect_stdout(output):
            self.assertEqual(main(['discover','--context','context.json','--params',str(params)]),0)
        data=json.loads(output.getvalue())
        self.assertEqual(data['candidate_preview'][0]['ref'],'source');self.assertIn('response_file',data)
        self.assertLessEqual(len(output.getvalue().encode()),4096)

    def test_selected_fit_only_does_not_clear_uncertain_build(self):
        self.client.timeout=.02
        with self.assertRaises(LiveError):self.client.request('build',{'fit_request':'f'},request_id='unknown')
        def worker():
            slot=self.client.mod/'content/scripts/pif_live/test_session/000002.lua'
            deadline=time.monotonic()+1
            while not slot.exists() and time.monotonic()<deadline:time.sleep(.005)
            with self.log.open('a') as f:f.write(MARKER+json.dumps(self.response('selection','selected_connection',result={'game_constructed':False}))+'\n')
        self.client.timeout=.5;thread=threading.Thread(target=worker);thread.start()
        self.client.request('selected_connection',{},request_id='selection');thread.join()
        self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'],'unknown')
        with self.assertRaises(LiveError):self.client.request('build',{},request_id='repeat')

    def test_selection_combines_two_current_discoveries_without_identity_guessing(self):
        a=self.discovery_record();b=self.discovery_record();b['request_id']='second'
        a['result']['candidates']=a['result']['candidates'][:1];b['result']['candidates']=b['result']['candidates'][1:]
        with patch.object(self.client,'request',return_value=self.response()) as calls:
            connect_selected(self.client,[a,b],self.selected_brief())
        self.assertEqual(calls.call_args.args[1]['discovery_requests'],['discovery','second'])
        for bad in ([a,a],[a,b|{'session':'old'}]):
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):connect_selected(self.client,bad,self.selected_brief())
                calls.assert_not_called()

    def test_vertical_briefs_reject_bad_limits_and_endpoint_values_before_request(self):
        for vertical in ({'max_grade':0},{'max_grade':True},{'max_grade':float('nan')},
                         {'max_grade':.04,'end_height':3}):
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):connect(self.client,self.connection_brief()|{'vertical':vertical})
                calls.assert_not_called()
        base=self.connection_brief();base.pop('target_edge');base.pop('target_node')
        base.update(end_xy=[100,100],end_direction=[1,0])
        for vertical in ({'max_grade':.04},{'max_grade':.04,'end_height':float('inf'),'end_grade':.01},
                         {'max_grade':.04,'end_height':3,'end_grade':.05}):
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):extend(self.client,base|{'vertical':vertical})
                calls.assert_not_called()

    def test_explicit_native_vertical_constraints_reach_one_compound_workflow(self):
        for execute in (False,True):
            brief=self.connection_brief()|{'vertical':{'max_grade':.04}}
            with patch.object(self.client,'request',return_value=self.response(operation='connection')) as calls:
                connect(self.client,brief,execute=execute)
            self.assertEqual(calls.call_count,1)
            self.assertEqual(calls.call_args.args[1]['brief'],brief)
            self.assertIs(calls.call_args.args[1]['execute'],execute)
        base=self.connection_brief();base.pop('target_edge');base.pop('target_node')
        base.update(end_xy=[100,100],end_direction=[1,0],vertical={'max_grade':.04,'end_height':3,'end_grade':.01})
        with patch.object(self.client,'request',return_value=self.response()) as calls:extend(self.client,base)
        self.assertEqual(calls.call_args.args[1]['brief']['vertical'],base['vertical'])

    def test_selected_vertical_keeps_native_endpoint_identity_and_fit_only(self):
        brief=self.selected_brief()|{'vertical':{'max_grade':.04}}
        with patch.object(self.client,'request',return_value=self.response()) as calls:
            connect_selected(self.client,self.discovery_record(),brief)
        self.assertEqual(calls.call_args.args[1]['vertical'],{'max_grade':.04})
        self.assertNotIn('execute',calls.call_args.args[1])
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(ValueError):
                connect_selected(self.client,self.discovery_record(),brief|{'vertical':{'max_grade':.04,'end_height':3}})
            calls.assert_not_called()

    def fixture_pending(self):
        brief=self.connection_brief();brief.pop('target_edge');brief.pop('target_node')
        brief.update(end_xy=[100,100],end_direction=[1,0])
        pending=dict(request_id='failed_fixture',operation='test_approach',params={'brief':brief,'length':20,'authorised':True})
        self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}))
        response=self.response('failed_fixture','test_approach',result={'error':'source: native_test_approach_rejected','game_constructed':'unknown'})
        response['status']='mutation_unverified'
        (self.client.evidence/'failed_fixture.response.json').write_text(json.dumps(response))
        return pending

    def test_fixture_reconciliation_requires_complete_absence_and_unchanged_anchor(self):
        for defect in ('none','truncated','track','changed'):
            pending=self.fixture_pending();record=self.discovery_record()
            def query(operation,params):
                if operation=='inspect':return self.response('fresh_anchor',operation,result={'edges':[{'id':10 if defect!='changed' else 99}]})
                self.assertEqual(operation,'discover')
                return self.response('footprint',operation,result={'complete':defect!='truncated','edge_count':1 if defect=='track' else 0})
            with patch.object(self.client,'request',side_effect=query) as calls:
                if defect=='none':
                    value=reconcile_rejected_fixture(self.client,record)
                    self.assertIs(value['result']['automatic_replay'],False)
                    self.assertEqual(value['result']['other_effects'],'unknown')
                    final=json.loads(self.client.journal.read_text());self.assertNotIn('pending',final)
                    evidence=Path(final['reconciled_rejections']['failed_fixture']['evidence'])
                    self.assertEqual(json.loads(evidence.read_text())['original_pending'],pending)
                else:
                    with self.assertRaises(LiveError):reconcile_rejected_fixture(self.client,record)
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)
            self.assertTrue(all(c.args[0] in ('inspect','discover') for c in calls.call_args_list))

    def test_fixture_reconciliation_rejects_missing_native_failure_evidence(self):
        self.fixture_pending();record=self.discovery_record()
        path=self.client.evidence/'failed_fixture.response.json';response=json.loads(path.read_text());response['result']['error']='unknown response';path.write_text(json.dumps(response))
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(LiveError):reconcile_rejected_fixture(self.client,record)
            calls.assert_not_called()

    def test_seeded_fixture_reconciliation_is_read_only_and_requires_exact_absence(self):
        for defect in ('none','truncated','track','changed'):
            pending=self.fixture_pending();pending['params']={'authorised':True,'length':20,'fixture':{'template_edge':10,'position':[100,100,0],'travel_direction':[1,0],'grade':0,'region':{'min':[60,60,-10],'max':[140,140,10]}}}
            self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}));record=self.discovery_record()
            record['result']['candidates'].append(dict(record['result']['candidates'][0],node_id=99))
            def query(op,p):
                if op=='inspect':return self.response('fresh',op,result={'edges':[{'id':99 if defect=='changed' else 10}]})
                self.assertEqual(op,'discover');return self.response('region',op,result={'complete':defect!='truncated','edge_count':1 if defect=='track' else 0})
            with patch.object(self.client,'request',side_effect=query):
                if defect=='none':self.assertEqual(reconcile_rejected_fixture(self.client,record)['status'],'ok')
                else:
                    with self.assertRaises(LiveError):reconcile_rejected_fixture(self.client,record)
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)

    def rejected_connection_pending(self):
        pending={'request_id':'rejected_connection','operation':'connection',
                 'params':{'execute':True,'brief':self.connection_brief()}}
        self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}))
        response=self.response('rejected_connection','connection',result={'stage':'build',
                 'native_command_success':False,'error':'native_construction_rejected','game_constructed':'unknown'})
        response['status']='error'
        (self.client.evidence/'rejected_connection.response.json').write_text(json.dumps(response))
        return pending

    def test_rejected_connection_reconciliation_requires_fresh_free_exact_attachments(self):
        for defect in ('none','failed_query','wrong_node'):
            pending=self.rejected_connection_pending()
            response=self.response('fresh','selected_connection',result={'fit':{'start_node':11,'target_node':21 if defect!='wrong_node' else 22}})
            if defect=='failed_query':response['status']='error'
            with patch.object(self.client,'request',return_value=response) as calls:
                if defect=='none':
                    result=reconcile_rejected_connection(self.client,self.discovery_record())
                    self.assertEqual(result['result']['other_effects'],'unknown')
                    self.assertEqual(result['result']['original_pending'],pending)
                    self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
                else:
                    with self.assertRaises(LiveError):reconcile_rejected_connection(self.client,self.discovery_record())
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)
            self.assertEqual(calls.call_count,1)
            self.assertEqual(calls.call_args.args[0],'selected_connection')
            self.assertNotIn('execute',calls.call_args.args[1])

    def test_rejected_junction_reconciliation_is_read_only_and_preserves_unknowns(self):
        for operation,defect in [(op,d) for op in ('junction','interior_junction') for d in ('none','failed_query','through','constructed')]:
            pending=self.rejected_connection_pending();pending['operation']=operation
            pending['params']={'execute':True,'source':{'node_id':11},'target':{'node_id':21}}
            self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}))
            original=self.client.evidence/'rejected_connection.response.json';r=json.loads(original.read_text());r['operation']=operation;original.write_text(json.dumps(r))
            response=self.response('fresh',operation,result={'game_constructed':defect=='constructed','through_before':{'requested_route_verified':defect!='through'}})
            if defect=='failed_query':response['status']='error'
            with patch.object(self.client,'request',return_value=response) as calls:
                if defect=='none':
                    r=reconcile_rejected_junction(self.client)
                    self.assertFalse(r['result']['completed_junction_constructed']);self.assertEqual(r['result']['other_effects'],'unknown')
                    self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
                else:
                    with self.assertRaises(LiveError):reconcile_rejected_junction(self.client)
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)
            self.assertEqual(calls.call_args.args[0],operation);self.assertIs(calls.call_args.args[1]['execute'],False)

    def test_junction_reconciliation_requires_explicit_native_failure(self):
        pending=self.rejected_connection_pending();pending['operation']='junction'
        self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}))
        path=self.client.evidence/'rejected_connection.response.json';r=json.loads(path.read_text());r['result'].pop('native_command_success');path.write_text(json.dumps(r))
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(LiveError):reconcile_rejected_junction(self.client)
            calls.assert_not_called()

    def test_rejected_connection_without_explicit_rejection_cannot_be_cleared(self):
        self.rejected_connection_pending()
        path=self.client.evidence/'rejected_connection.response.json';r=json.loads(path.read_text())
        r['result'].pop('native_command_success');path.write_text(json.dumps(r))
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(LiveError):reconcile_rejected_connection(self.client,self.discovery_record())
            calls.assert_not_called()

    def constructed_pending(self):
        pending={'request_id':'built','operation':'connection','params':{'execute':True,'brief':self.connection_brief()}}
        control={'p0':[0,0,0],'p1':[2,0,.01],'t0':[2,0,0],'t1':[2,0,.02]}
        source={'id':10,'node0':12,'node1':11,'template':'track','style':'style'}
        target={'id':20,'node0':21,'node1':22,'template':'track','style':'style'}
        record=self.discovery_record()
        for c,e in zip(record['result']['candidates'],[source,target]):c['edge_snapshot']=e
        edge={'id':30,'node0':11,'node1':21,'template':'track','style':'style',**control}
        response=self.response('built','connection',result={'stage':'readback','game_constructed':True,
            'stages':[{'stage':'build','status':'ok'}],'fit':{'controls':[control],'max_grade':.04}});response['status']='mutation_unverified'
        self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}))
        (self.client.evidence/'built.response.json').write_text(json.dumps(response))
        rows=[dict(e,engineering_checks={'sampled_verified':True,'samples':17,'min_sampled_radius':101,'max_sampled_grade':.01}) for e in (source,edge,target)]
        return pending,record,rows

    def test_constructed_reconciliation_requires_exact_controls_chain_and_native_route(self):
        for defect in ('none','controls','node','route','radius','grade','missing_checks','nonfinite'):
            pending,record,rows=self.constructed_pending()
            if defect=='controls':rows[1]['p1']=[2,0,1]
            if defect=='node':rows[1]['node1']=99
            if defect=='radius':rows[1]['engineering_checks']['min_sampled_radius']=99
            if defect=='grade':rows[1]['engineering_checks']['max_sampled_grade']=.041
            if defect=='missing_checks':rows[1].pop('engineering_checks')
            if defect=='nonfinite':rows[1]['engineering_checks']['min_sampled_radius']=float('nan')
            def query(op,params):
                self.assertIn(op,('inspect','route'))
                if op=='inspect':self.assertEqual(params['geometry_constraints'],{'radius':100,'max_grade':.04,'region':self.connection_brief()['region']})
                return self.response('observed_'+op,op,result={'edges':rows} if op=='inspect' else {'requested_route_verified':defect!='route'})
            with patch.object(self.client,'request',side_effect=query):
                if defect=='none':
                    value=reconcile_constructed_connection(self.client,record,[30])
                    self.assertEqual(value['result']['ordered_nodes'],[11,21]);self.assertEqual(value['result']['original_pending'],pending)
                    self.assertIs(value['result']['automatic_replay'],False)
                    self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
                else:
                    with self.assertRaises(LiveError):reconcile_constructed_connection(self.client,record,[30])
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)

    def test_constructed_reconciliation_without_reported_native_success_never_queries(self):
        _,record,_=self.constructed_pending();p=self.client.evidence/'built.response.json';r=json.loads(p.read_text())
        r['result']['game_constructed']='unknown';p.write_text(json.dumps(r))
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(LiveError):reconcile_constructed_connection(self.client,record,[30])
            calls.assert_not_called()

    def test_route_invalid_input_never_sends(self):
        for key,value in [('mode','CAR'),('max_length',float('inf')),('max_length',4001),
                          ('source_node',True),('required_edges',[30,30]),('target_node',11)]:
            bad={**self.route_brief(),key:value}
            with patch.object(self.client,'request') as calls:
                with self.assertRaises(ValueError):route(self.client,bad)
                calls.assert_not_called()

    def test_route_uses_one_native_query_and_preserves_negative_result(self):
        for verified in (True,False):
            response=self.response(operation='route',result={'native_path_found':verified,
                'requested_route_verified':verified,'game_constructed':False,'train_traversal':'unprobed'})
            with patch.object(self.client,'request',return_value=response) as calls:
                result=route(self.client,self.route_brief())
            self.assertIs(result['result']['requested_route_verified'],verified)
            self.assertEqual(result['result']['train_traversal'],'unprobed')
            calls.assert_called_once_with('route',self.route_brief())

    def test_route_inspection_preserves_unresolved_mutation(self):
        self.client.timeout=.02
        with self.assertRaises(LiveError):self.client.request('build',{'fit_request':'f'},request_id='unknown')
        def worker():
            slot=self.client.mod/'content/scripts/pif_live/test_session/000002.lua'
            deadline=time.monotonic()+1
            while not slot.exists() and time.monotonic()<deadline:time.sleep(.005)
            with self.log.open('a') as f:f.write(MARKER+json.dumps(self.response('query','route',result={'game_constructed':False}))+'\n')
        self.client.timeout=.5
        thread=threading.Thread(target=worker);thread.start()
        self.client.request('route',self.route_brief(),request_id='query');thread.join()
        self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'],'unknown')
        with self.assertRaises(LiveError):self.client.request('build',{'fit_request':'f'},request_id='replay')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))),2)

    def test_junction_observations_keep_pending_and_never_allow_replay(self):
        self.client.timeout=.02
        with self.assertRaises(LiveError):self.client.request('junction',{'execute':True},request_id='unknown')
        self.client.timeout=.5
        for sequence,op in enumerate(('discover_junction','junction'),start=2):
            def worker():
                slot=self.client.mod/f'content/scripts/pif_live/test_session/{sequence:06d}.lua'
                deadline=time.monotonic()+1
                while not slot.exists() and time.monotonic()<deadline:time.sleep(.005)
                with self.log.open('a') as f:f.write(MARKER+json.dumps(self.response(op,op,result={'game_constructed':False}))+'\n')
            thread=threading.Thread(target=worker);thread.start()
            self.client.request(op,{'execute':False},request_id=op);thread.join()
            self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'],'unknown')
        with self.assertRaises(LiveError):self.client.request('junction',{'execute':True},request_id='replay')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))),3)

    def test_route_cli_keeps_large_native_path_local(self):
        params=self.root/'route.json';params.write_text(json.dumps(self.route_brief()))
        response=self.response(operation='route',result={'requested_route_verified':True,'path':['x'*10000]})
        output=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request',return_value=response),contextlib.redirect_stdout(output):
            code=main(['route','--context','context.json','--params',str(params)])
        self.assertEqual(code,0);self.assertIn('response_file',json.loads(output.getvalue()))
        self.assertIs(json.loads(output.getvalue())['requested_route_verified'],True)
        self.assertLessEqual(len(output.getvalue().encode()),4096)

    def test_route_cli_negative_is_not_a_success_exit(self):
        params=self.root/'route.json';params.write_text(json.dumps(self.route_brief()))
        response=self.response(operation='route',result={'native_path_found':False,'requested_route_verified':False,'game_constructed':False})
        output=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request',return_value=response),contextlib.redirect_stdout(output):
            code=main(['route','--context','context.json','--params',str(params)])
        self.assertEqual(code,1);self.assertIs(json.loads(output.getvalue())['result']['requested_route_verified'],False)

    def connection_brief(self):
        return {'anchor_edge':10,'anchor_node':11,'target_edge':20,'target_node':21,
                'radius':100,'region':{'min':[0,0,-10],'max':[300,300,10]}}

    def connection_worker(self, operation, params, *, request_id):
        self.assertEqual(operation, 'connection')
        self.assertEqual(params['brief'], self.connection_brief())
        result={'stage':'fit','stages':[{'stage':'inspect','status':'ok'},{'stage':'fit','status':'ok'}],
                'fit':{'target_node':21},'game_constructed':False}
        if params['execute']:
            result.update(stage='readback',game_constructed=True,
                readback=self.engineering_readback(params['brief']['radius'])|{'connected':True,'ordered_edges':[30,31],'ordered_nodes':[11,40,21],
                          'attachments':{'source_edge':10,'source_node':11,'target_edge':20,'target_node':21}})
        return self.response(request_id, operation, result=result)

    def test_two_ended_fit_only_and_execute_preserve_both_identities(self):
        with patch.object(self.client,'request',side_effect=self.connection_worker) as calls:
            fit=connect(self.client,self.connection_brief())
            built=connect(self.client,self.connection_brief(),execute=True)
        self.assertIs(fit['game_constructed'],False)
        self.assertTrue(built['connected']);self.assertEqual(built['nodes'],[11,40,21])
        self.assertEqual(built['attachments']['target_edge'],20)
        self.assertEqual(len(calls.call_args_list),2)

    def test_wrong_target_node_or_edge_never_claims_connection(self):
        for changed in ('node','edge'):
            def worker(operation,params,*,request_id):
                response=self.connection_worker(operation,params,request_id=request_id)
                if changed=='node':response['result']['readback']['ordered_nodes'][-1]=999
                else:response['result']['readback']['attachments']['target_edge']=999
                return response
            with patch.object(self.client,'request',side_effect=worker) as calls:
                result=connect(self.client,self.connection_brief(),execute=True)
            self.assertEqual(result['status'],'native_verification_failed')
            self.assertIs(result['game_constructed'],True);self.assertEqual(len(calls.call_args_list),1)

    def test_two_ended_invalid_brief_or_native_grade_failure_never_builds(self):
        bad=self.connection_brief();bad['target_node']=11
        with patch.object(self.client,'request') as calls:
            with self.assertRaises(ValueError):connect(self.client,bad,execute=True)
            calls.assert_not_called()
        def worker(operation,params,*,request_id):
            return dict(version=1,session='test_session',request_id=request_id,operation=operation,status='error',
                        result={'stage':'fit','error':'unsupported_endpoint_grades','game_constructed':False})
        with patch.object(self.client,'request',side_effect=worker) as calls:
            result=connect(self.client,self.connection_brief(),execute=True)
        self.assertEqual(result['status'],'error');self.assertIs(result['game_constructed'],False)
        self.assertEqual(len(calls.call_args_list),1)

    def test_two_ended_timeout_keeps_pending_and_cannot_replay(self):
        self.client.timeout=.02
        with self.assertRaises(LiveError) as ctx:
            self.client.request('connection',{'brief':self.connection_brief(),'execute':True},request_id='connect1')
        self.assertEqual(ctx.exception.status,'mutation_outcome_unknown')
        with self.assertRaises(LiveError):
            self.client.request('connection',{'brief':self.connection_brief(),'execute':True},request_id='connect2')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))),1)

    def test_connect_cli_routes_one_bounded_workflow(self):
        params=self.root/'connection.json';params.write_text(json.dumps(self.connection_brief()))
        output=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request',side_effect=self.connection_worker) as calls,contextlib.redirect_stdout(output):
            code=main(['connect','--context','context.json','--params',str(params),'--execute'])
        self.assertEqual(code,0);self.assertTrue(json.loads(output.getvalue())['connected'])
        self.assertEqual(len(calls.call_args_list),1);self.assertLessEqual(len(output.getvalue().encode()),4096)

    def test_late_response_reconciles_without_new_module(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError):
            self.client.request('build', {'fit_request': 'fit1'}, request_id='r1')
        with self.log.open('a') as stream:
            stream.write(MARKER + json.dumps(self.response('r1', 'build')) + '\n')
        self.assertEqual(self.client.reconcile_pending()['status'], 'ok')
        self.assertNotIn('pending', json.loads(self.client.journal.read_text()))
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_fresh_readback_clears_only_matching_uncertain_build(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError):
            self.client.request('build', {'fit_request': 'fit1'}, request_id='build1')
        def worker():
            slot = self.client.mod / 'content/scripts/pif_live/test_session/000002.lua'
            deadline = time.monotonic() + 1
            while not slot.exists() and time.monotonic() < deadline:
                time.sleep(.005)
            with self.log.open('a') as stream:
                stream.write(MARKER + json.dumps(self.response('verify1', 'readback', result={'connected': True})) + '\n')
        self.client.timeout = .5
        thread = threading.Thread(target=worker);thread.start()
        self.client.request('readback', {'fit_request': 'fit1'}, request_id='verify1')
        thread.join()
        self.assertNotIn('pending', json.loads(self.client.journal.read_text()))
        modules = list(self.client.mod.rglob('*.lua'))
        self.assertEqual(len(modules), 2)
        self.assertEqual(sum('["operation"]="build"' in p.read_text() for p in modules), 1)

    def test_cli_keeps_large_response_local_and_stdout_compact(self):
        params = self.root / 'params.json';params.write_text('{}')
        response = self.response(result={'geometry': 'x' * 10000})
        output = io.StringIO()
        with patch.object(LiveClient, 'request', return_value=response), contextlib.redirect_stdout(output):
            code = main(['inspect', '--params', str(params), '--mod-directory', str(self.client.mod),
                         '--log', str(self.log), '--evidence', str(self.client.evidence), '--session', 'test_session'])
        self.assertEqual(code, 0)
        self.assertLessEqual(len(output.getvalue().encode()), 4096)
        self.assertEqual(json.loads(output.getvalue())['response_file'], str((self.client.evidence / 'r1.response.json').resolve()))

    def brief(self):
        return {'anchor_edge': 1, 'anchor_node': 2, 'end_xy': [20, 30],
                'end_direction': [0, 1], 'radius': 10,
                'region': {'min': [-100, -100, -10], 'max': [100, 100, 10]}}

    def workflow_worker(self, operation, params, *, request_id):
        self.assertEqual(operation, 'extension')
        self.assertEqual(params['brief'], self.brief())
        stages=[{'stage': s, 'status': 'ok'} for s in (['inspect', 'fit', 'build', 'readback'] if params['execute'] else ['inspect', 'fit'])]
        return self.response(request_id, operation, result={'stage': stages[-1]['stage'], 'stages': stages,
            'fit': {'fit_request': request_id+'_fit', 'pieces': 3, 'sampled_only': True},
            'game_constructed': params['execute'],
            'readback': self.engineering_readback(params['brief']['radius'])|{'connected': True, 'ordered_edges': [4, 5], 'ordered_nodes': [2, 6, 7]}})

    def test_workflow_fit_only_and_explicit_execution(self):
        with patch.object(self.client, 'request', side_effect=self.workflow_worker) as calls:
            design = extend(self.client, self.brief())
            self.assertEqual([c.args[0] for c in calls.call_args_list], ['extension'])
            self.assertIs(calls.call_args.args[1]['execute'], False)
            self.assertEqual([s['stage'] for s in design['stages']], ['inspect','fit'])
            self.assertEqual(design['status'], 'ok');self.assertIs(design['game_constructed'], False)
        with patch.object(self.client, 'request', side_effect=self.workflow_worker) as calls:
            built = extend(self.client, self.brief(), execute=True)
            self.assertEqual([c.args[0] for c in calls.call_args_list], ['extension'])
            self.assertIs(calls.call_args.args[1]['execute'], True)
            self.assertEqual([s['stage'] for s in built['stages']], ['inspect','fit','build','readback'])
            self.assertEqual(built['nodes'], [2, 6, 7]);self.assertTrue(built['connected'])
            self.assertEqual(json.loads(Path(built['evidence']).read_text())['summary'], built)

    def test_failed_inspection_or_fit_never_builds(self):
        for failed_stage in ('inspect', 'fit'):
            def worker(operation, params, *, request_id):
                return {**self.response(request_id, operation), 'status':'error',
                        'result': {'stage':failed_stage,'error':'rejected','game_constructed':False,
                                   'stages':[{'stage':failed_stage,'status':'error'}]}}
            with patch.object(self.client, 'request', side_effect=worker) as calls:
                result = extend(self.client, self.brief(), execute=True)
                self.assertEqual(result['stage'], failed_stage);self.assertEqual(result['status'], 'error')
                self.assertNotIn('build', [c.args[0] for c in calls.call_args_list])
                self.assertEqual(len(calls.call_args_list),1)

    def test_uncertain_build_stops_without_replay(self):
        def worker(operation, params, *, request_id):
            raise LiveError('mutation_outcome_unknown', 'timeout', request_id)
        with patch.object(self.client, 'request', side_effect=worker) as calls:
            result = extend(self.client, self.brief(), execute=True)
            self.assertEqual([c.args[0] for c in calls.call_args_list], ['extension'])
            self.assertEqual(result['status'], 'mutation_outcome_unknown')
            self.assertEqual(result['game_constructed'], 'unknown')

    def test_readback_failure_does_not_rebuild_or_claim_acceptance(self):
        def worker(operation, params, *, request_id):
            response = self.workflow_worker(operation, params, request_id=request_id)
            response['result']['readback']['connected'] = False
            return response
        with patch.object(self.client, 'request', side_effect=worker) as calls:
            result = extend(self.client, self.brief(), execute=True)
            self.assertEqual(result['status'], 'native_verification_failed')
            self.assertIs(result['game_constructed'], True)
            self.assertEqual(len(calls.call_args_list), 1)

    def test_context_discovers_latest_handshake_and_reuses_journal(self):
        def marker(kind, value):return 'TPF3_BRIDGE_LIVE_' + kind + ' ' + json.dumps(value) + '\n'
        self.log.write_text(marker('READY', {'version': 1, 'session': 'old'}) +
                            marker('SESSION', {'ready': True, 'session': 'old'}) +
                            marker('READY', {'version': 1, 'session': 'test_session'}))
        with self.assertRaises(LiveError):discover_session(self.log)
        with self.log.open('a') as f:f.write(marker('SESSION', {'ready': True, 'session': 'test_session'}))
        context = self.root / 'context.json'
        context.write_text(json.dumps({'mod_directory': 'mod', 'log': 'stdout.txt', 'session_evidence_root': 'sessions'}))
        directory = self.root / 'sessions/test_session';directory.mkdir(parents=True)
        (directory/'client_state.json').write_text(json.dumps({'session': 'test_session', 'next_sequence': 7}))
        client = client_from_context(context)
        self.assertEqual(client.session, 'test_session')
        self.assertEqual(json.loads(client.journal.read_text())['next_sequence'], 7)

    def test_invalid_brief_never_sends_and_cli_routes_one_workflow(self):
        bad = self.brief();bad['end_direction'] = [0, 0]
        with patch.object(self.client, 'request') as calls:
            with self.assertRaises(ValueError):extend(self.client, bad, execute=True)
            calls.assert_not_called()
        params = self.root/'brief.json';params.write_text(json.dumps(self.brief()))
        output = io.StringIO()
        with patch('bridge_live.client_from_context', return_value=self.client), patch.object(self.client, 'request', side_effect=self.workflow_worker) as calls, contextlib.redirect_stdout(output):
            code = main(['extend', '--context', 'context.json', '--params', str(params), '--execute'])
        self.assertEqual(code, 0);self.assertTrue(json.loads(output.getvalue())['connected'])
        self.assertEqual(len(calls.call_args_list), 1)
        self.assertLessEqual(len(output.getvalue().encode()), 4096)

    def test_request_waits_for_native_completion_after_response(self):
        self.client.require_ack = True
        def worker():
            slot = self.client.mod/'content/scripts/pif_live/test_session/000001.lua'
            deadline = time.monotonic()+1
            while not slot.exists() and time.monotonic()<deadline:time.sleep(.005)
            with self.log.open('a') as f:f.write(MARKER+json.dumps(self.response())+'\n')
            time.sleep(.12)
            self.assertIn('pending', json.loads(self.client.journal.read_text()))
            ack={'session':'test_session','request_id':'r1','success':True}
            with self.log.open('a') as f:f.write('TPF3_BRIDGE_LIVE_ACK '+json.dumps(ack)+'\n')
        thread=threading.Thread(target=worker);thread.start()
        response=self.client.request('inspect',{},request_id='r1');thread.join()
        self.assertEqual(response['status'],'ok')
        self.assertNotIn('pending',json.loads(self.client.journal.read_text()))

    def test_response_without_completion_remains_pending(self):
        self.client.require_ack=True;self.client.timeout=.05
        def worker():
            slot=self.client.mod/'content/scripts/pif_live/test_session/000001.lua'
            deadline=time.monotonic()+1
            while not slot.exists() and time.monotonic()<deadline:time.sleep(.005)
            with self.log.open('a') as f:f.write(MARKER+json.dumps(self.response('r1','build'))+'\n')
        thread=threading.Thread(target=worker);thread.start()
        with self.assertRaises(LiveError):self.client.request('build',{'fit_request':'f'},request_id='r1')
        thread.join()
        with self.assertRaises(LiveError):self.client.reconcile_pending()
        self.assertIn('pending',json.loads(self.client.journal.read_text()))
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))),1)

    def throat_brief(self):
        def endpoint(x):return {'region':{'min':[x-5,-5,-5],'max':[x+5,5,5]},'guide_xyz':[x,0,0],'travel_direction':[1,0],'max_edges':4,'heading_tolerance_deg':5}
        roles={n:{'kind':'approach' if n[0]=='A' else 'destination','endpoint':endpoint(i*20)} for i,n in enumerate(['A1','A2','D1','D2','D3'])}
        return {'roles':roles,'steps':[{'name':'cross','kind':'crossover','source':endpoint(100),'target':endpoint(200)},
                                      {'name':'ladder','kind':'branch','source':endpoint(300),'target':endpoint(400)}],
                'required_routes':[{'from':'A1','to':'D1','via':[]},{'from':'A1','to':'D2','via':['cross']},{'from':'A2','to':'D3','via':['ladder']}],
                'radius':120,'region':{'min':[-50,-50,-10],'max':[500,500,50]},'vertical':{'max_grade':.04},
                'placement_tolerance':1,'max_fit_attempts':2,'max_route_length':2000}

    def throat_worker(self,operation,params):
        self.throat_calls.append((operation,params))
        if operation=='crossover':
            if params['execute']:self.throat_epoch+=1
            result={'game_constructed':params['execute']}
            if params['execute']:result.update(readback={'connected':True,'ordered_edges':[81]},placements=[{'original_removed':True,'subdivision_sampled_verified':True}]*2,
                through_after=[{'requested_route_verified':True}]*2,crossover_after={'requested_route_verified':True},junction_nodes=[91,92])
        else:
            self.assertEqual(operation,'route');self.assertEqual(self.throat_epoch,2)
            self.assertGreaterEqual(params['source_edge'],2000);self.assertEqual(params['junction_nodes'],[91,92,93])
            self.assertTrue(params['geometry_constraints']['all_path']);result={'requested_route_verified':not self.throat_fail_route}
        return self.response('r'+str(len(self.throat_calls)),operation,result=result)

    def throat_port(self,client,intent,**kw):
        x=intent['guide_xyz'][0];eid=self.throat_epoch*1000+int(x)+1
        return {'edge_id':eid,'node_id':eid+100,'edge_snapshot':{'id':eid},'parameter':.5},'d'+str(eid)

    def throat_branch(self,client,brief,*,execute,junction_nodes):
        self.assertEqual(junction_nodes,[91,92] if execute else [])
        if execute:self.throat_epoch+=1
        return {'status':'ok','game_constructed':execute,'junction':{'node':93},'edges':[82]}

    def test_throat_composes_then_reacquires_final_roles_and_matrix(self):
        self.throat_calls=[];self.throat_epoch=0;self.throat_fail_route=False
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at',side_effect=self.throat_branch),patch.object(self.client,'request',side_effect=self.throat_worker):
            r=connect_throat(self.client,self.throat_brief(),execute=True)
        self.assertEqual(r['status'],'ok');self.assertTrue(r['final_network_verified']);self.assertEqual(r['routes_verified'],3)
        self.assertEqual([x[0] for x in self.throat_calls],['crossover','route','route','route'])
        q=self.throat_calls[2][1];self.assertIn(81,q['required_edges']);self.assertTrue(r['game_constructed'])
        self.assertLessEqual(len(json.dumps(r).encode()),4096)
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved['summary'],r)
        self.assertEqual(saved['semantic_mapping']['roles']['A1']['edge_id'],2001)

    def test_throat_fit_only_does_not_claim_final_network_or_mutate(self):
        self.throat_calls=[];self.throat_epoch=0;self.throat_fail_route=False
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at',side_effect=self.throat_branch),patch.object(self.client,'request',side_effect=self.throat_worker):
            r=connect_throat(self.client,self.throat_brief())
        self.assertEqual(r['status'],'ok');self.assertFalse(r['final_network_verified']);self.assertFalse(r['game_constructed'])
        self.assertEqual(len(self.throat_calls),1);self.assertFalse(is_mutation(*self.throat_calls[0]))

    def throat_reconciliation(self,brief):
        step=brief['steps'][0]
        params={k:brief[k] for k in ('radius','region','vertical','max_route_length')}
        params.update(source={},target={},location=step['source']|{'placement_tolerance':brief['placement_tolerance']},
                      target_location=step['target']|{'placement_tolerance':brief['placement_tolerance']})
        path=self.client.evidence/'explicit_crossover.json'
        path.write_text(json.dumps({'status':'reconciled_verified_crossover','verification_params':params}))
        return path

    def test_throat_explicit_reconciled_step_rechecks_without_rebuilding(self):
        self.throat_calls=[];self.throat_epoch=1;self.throat_fail_route=False
        brief=self.throat_brief();path=self.throat_reconciliation(brief)
        def worker(op,params):
            if op=='verify_crossover':
                self.assertFalse(params['execute'])
                result=self.throat_worker('crossover',{'execute':True})
                self.throat_epoch=1
                self.throat_calls[-1]=(op,params)
                return result|{'operation':op}
            return self.throat_worker(op,params)
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at',side_effect=self.throat_branch),patch.object(self.client,'request',side_effect=worker):
            r=connect_throat(self.client,brief,execute=True,reconciled_crossover=path)
        self.assertEqual(r['status'],'ok');self.assertEqual(self.throat_calls[0][0],'verify_crossover')
        self.assertNotIn('crossover',[x[0] for x in self.throat_calls])

    def test_throat_reconciled_constraints_cannot_change(self):
        self.throat_epoch=0;brief=self.throat_brief();path=self.throat_reconciliation(brief)
        brief['radius']=130
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at') as branch,patch.object(self.client,'request') as worker:
            r=connect_throat(self.client,brief,execute=True,reconciled_crossover=path)
        self.assertEqual(r['status'],'invalid_result');self.assertIn('does not match',r['error'])
        worker.assert_not_called();branch.assert_not_called();self.assertFalse(r['game_constructed'])

    def test_throat_final_route_failure_preserves_built_effects(self):
        self.throat_calls=[];self.throat_epoch=0;self.throat_fail_route=True
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at',side_effect=self.throat_branch),patch.object(self.client,'request',side_effect=self.throat_worker):
            r=connect_throat(self.client,self.throat_brief(),execute=True)
        self.assertEqual(r['status'],'native_verification_failed');self.assertTrue(r['game_constructed']);self.assertEqual(r['routes_verified'],0)
        self.assertEqual(len(self.throat_calls),2)

    def test_throat_uncertain_crossover_stops_without_branch_or_replay(self):
        self.throat_epoch=0
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at') as branch,patch.object(self.client,'request',side_effect=LiveError('mutation_outcome_unknown','timeout')) as worker:
            r=connect_throat(self.client,self.throat_brief(),execute=True)
        self.assertEqual(r['status'],'mutation_outcome_unknown');self.assertEqual(r['game_constructed'],'unknown');branch.assert_not_called();self.assertEqual(worker.call_count,1)

    def test_throat_invalid_matrix_rejected_before_commands(self):
        import copy
        b=self.throat_brief();validate_throat_brief(b)
        cases=[]
        for change in ('duplicate','unknown','missing','reverse'):
            bad=copy.deepcopy(b)
            if change=='duplicate':bad['required_routes'].append(bad['required_routes'][0])
            elif change=='unknown':bad['required_routes'][0]['via']=['missing']
            elif change=='missing':bad['required_routes'][1]['via']=[]
            else:bad['required_routes'][0].update({'from':'D1','to':'A1'})
            cases.append(bad)
        with patch.object(self.client,'request') as worker:
            for bad in cases:
                with self.assertRaises(ValueError):connect_throat(self.client,bad,execute=True)
            worker.assert_not_called()

    def test_throat_role_discovery_rejects_truncated_and_ambiguous_identity(self):
        intent=self.throat_brief()['roles']['A1']['endpoint']
        candidate={'edge_id':11,'node_id':12,'eligible':True,'pos':[0,0,0],'outward_direction':[-1,0]}
        for complete,candidates in [(False,[candidate]),(True,[candidate,candidate|{'edge_id':13}])]:
            with patch.object(self.client,'request',return_value=self.response(result={'complete':complete,'candidates':candidates})):
                with self.assertRaises(LiveError):_select_throat_port(self.client,intent,outward_sign=-1)

    def test_crossover_reconciliation_is_read_only_and_keeps_original_failure(self):
        rid='cross';params={'execute':True,'source':{},'target':{}}
        pending={'operation':'crossover','request_id':rid,'params':params}
        self.client.journal.write_text(json.dumps({'session':self.client.session,'pending':pending}))
        original=self.response(rid,'crossover',result={'game_constructed':True,'returned_edges':[1,2,3,4,5],'fit':{'pieces':1,'controls':[{}]}})
        original['status']='mutation_unverified'
        original_path=self.client.evidence/(rid+'.response.json');original_path.write_text(json.dumps(original));before=original_path.read_bytes()
        verified={'reconciled_current_state':True,'readback':{'connected':True},'crossover_after':{'requested_route_verified':True},
            'placements':[{'original_removed':True,'subdivision_sampled_verified':True}]*2,'through_after':[{'requested_route_verified':True}]*2}
        with patch.object(self.client,'request',return_value=self.response('verify','verify_crossover',result=verified)) as request:
            r=reconcile_constructed_crossover(self.client)
        op,p=request.call_args.args;self.assertEqual(op,'verify_crossover');self.assertFalse(p['execute']);self.assertFalse(is_mutation(op,p))
        self.assertEqual(r['result']['status'],'reconciled_verified_crossover');self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
        self.assertEqual(before,original_path.read_bytes());self.assertFalse(r['result']['automatic_replay'])

    def adjacent_brief(self):
        b=self.throat_brief()
        return {k:b[k] for k in ('radius','region','vertical','max_fit_attempts','max_route_length')}|{
            'source':b['steps'][0]['source'],'target':b['steps'][0]['target'],'side':'left','spacing_tolerance':.1}

    def adjacent_port(self,client,intent,**kwargs):
        source=kwargs.get('outward_sign')==-1
        return {'edge_id':11 if source else 12,'node_id':101 if source else 103},'discovery'

    def adjacent_worker(self,op,params):
        self.adjacent_calls.append((op,params))
        if op=='inspect':
            self.assertTrue(params['resources'])
            result={'edges':[{'id':eid,'resource':{'track_distance':self.template_spacing}} for eid in (11,12)]}
        elif op=='adjacent':
            self.assertEqual(abs(params['spacing']),5);self.assertEqual(params['tolerance'],.1)
            result={'game_constructed':params['execute'],'readback':self.engineering_readback(params['radius'])|{'connected':True,'ordered_edges':[21,22],'ordered_nodes':[201,202,203]},
                    'adjacency':{'sampled_verified':True,'independent_native_nodes':True}}
            if self.adjacent_failure:return self.response('a'+str(len(self.adjacent_calls)),op,result={'game_constructed':'unknown','error':'readback_failed'})|{'status':'mutation_unverified'}
        else:
            self.assertEqual(op,'route')
            if params['source_edge']==21:
                self.assertEqual(params['required_edges'],[21,22]);self.assertTrue(params['geometry_constraints']['all_path'])
            result={'requested_route_verified':True,'path':[{'edge':{'entity':eid},'forward':True,'confirmed_TRACK':True} for eid in (11,12)]}
        return self.response('a'+str(len(self.adjacent_calls)),op,result=result)

    def test_adjacent_native_resource_spacing_then_route_and_compact_summary(self):
        self.adjacent_calls=[];self.template_spacing=5;self.adjacent_failure=False
        with patch('bridge_live._select_throat_port',side_effect=self.adjacent_port),patch.object(self.client,'request',side_effect=self.adjacent_worker):
            r=connect_adjacent(self.client,self.adjacent_brief(),execute=True)
        self.assertEqual(r['status'],'ok');self.assertEqual(r['native_track_distance'],5);self.assertTrue(r['native_route_verified'])
        self.assertEqual([x[0] for x in self.adjacent_calls],['route','inspect','adjacent','route'])
        self.assertLessEqual(len(json.dumps(r).encode()),4096)
        self.assertEqual(json.loads(Path(r['evidence']).read_text())['summary'],r)

    def test_adjacent_fit_only_right_side_never_constructs(self):
        self.adjacent_calls=[];self.template_spacing=5;self.adjacent_failure=False
        b=self.adjacent_brief();b['side']='right'
        with patch('bridge_live._select_throat_port',side_effect=self.adjacent_port),patch.object(self.client,'request',side_effect=self.adjacent_worker):
            r=connect_adjacent(self.client,b)
        self.assertEqual(r['status'],'ok');self.assertFalse(r['game_constructed']);self.assertEqual(len(self.adjacent_calls),3)
        op,p=self.adjacent_calls[-1];self.assertEqual(p['spacing'],-5);self.assertFalse(is_mutation(op,p))

    def test_adjacent_failed_readback_stops_without_route_or_replay(self):
        self.adjacent_calls=[];self.template_spacing=5;self.adjacent_failure=True
        with patch('bridge_live._select_throat_port',side_effect=self.adjacent_port),patch.object(self.client,'request',side_effect=self.adjacent_worker):
            r=connect_adjacent(self.client,self.adjacent_brief(),execute=True)
        self.assertEqual(r['status'],'mutation_unverified');self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(len(self.adjacent_calls),3)

    def test_adjacent_unknown_native_spacing_is_not_a_default(self):
        self.adjacent_calls=[];self.template_spacing=None;self.adjacent_failure=False
        with patch('bridge_live._select_throat_port',side_effect=self.adjacent_port),patch.object(self.client,'request',side_effect=self.adjacent_worker):
            r=connect_adjacent(self.client,self.adjacent_brief(),execute=True)
        self.assertEqual(r['status'],'invalid_result');self.assertFalse(r['game_constructed']);self.assertEqual(len(self.adjacent_calls),2)

    def test_adjacent_invalid_side_or_tolerance_rejected_before_reads(self):
        for k,v in [('side','nearest'),('spacing_tolerance',1),('spacing_tolerance',float('nan'))]:
            b=self.adjacent_brief();b[k]=v
            with patch.object(self.client,'request') as worker:
                with self.assertRaises(ValueError):connect_adjacent(self.client,b,execute=True)
                worker.assert_not_called()

    def test_corridor_realised_radius_shortfall_rejects_without_retry_or_route(self):
        for hard,accepted in [(160,False),(120,True)]:
            b=self.corridor_brief()|{'radius':hard};query,calls=self.project_query();native=[]
            def worker(op,p):
                if op=='corridor':
                    native.append(p)
                    return self.response('current',op,result={'game_constructed':True,'fit':{'radius':hard,'native_fit_radius':168},
                        'readback':self.engineering_readback(hard)|{'min_sampled_radius':157.37422991553754,
                            'connected':True,'ordered_edges':[30,31],'ordered_nodes':[11,40,21],
                            'attachments':{'source_edge':10,'target_edge':20},'realised_guides':[{'node':40,'verified':True}]}})
                if op=='route':
                    self.assertEqual(p['geometry_constraints']['radius'],hard)
                    self.assertEqual(p['geometry_constraints']['edge_ids'],[30,31])
                return query(op,p)
            with patch.object(self.client,'request',side_effect=worker):r=connect_corridor(self.client,b,execute=True)
            self.assertEqual(r['status'],'ok' if accepted else 'native_verification_failed');self.assertTrue(r['game_constructed'])
            self.assertEqual(len(native),1)
            self.assertEqual(any(op=='route' for op,p in calls),accepted)

    def test_engineering_readback_missing_nonfinite_or_grade_failure_is_not_success(self):
        from bridge_live import _require_engineering_readback
        b=self.project_brief();good=self.engineering_readback(b['radius'])
        for defect in [{'engineering_checks_verified':False},{'requested_min_radius':1},{'min_sampled_radius':None},
                       {'min_sampled_radius':float('nan')},{'max_sampled_grade':.5}]:
            with self.assertRaises(LiveError):_require_engineering_readback(good|defect,b)
        _require_engineering_readback(good|{'min_sampled_radius':None,'straight_only':True},b)

    def recipe_brief(self):
        from bridge_live import JUNCTION_RECIPE
        return {'recipe':JUNCTION_RECIPE,'origin':[0,0,33],'heading_deg':0,'radius':120,'max_grade':.04,'spacing':5,
                'region':{'min':[-100,-100,0],'max':[1700,550,80]},'asset_region':{'min':[0,0,0],'max':[10,10,80]}}

    def recipe_worker(self,*,failure=None,spacing=5):
        calls=[];count=0
        def query(op,p):
            nonlocal count
            calls.append((op,p));count+=1
            if op=='discover':v={'complete':True,'candidates':[{'edge_id':900,'edge_snapshot':{'id':900,'template':'template','style':'style'}}]}
            elif op=='test_approach':
                if failure=='fixture':return self.response('failed',op,result={'game_constructed':True,'error':'readback_failed'})|{'status':'mutation_unverified'}
                q=p['fixture'];self.assertTrue(all(0<q['region']['max'][i]-q['region']['min'][i]<=100 for i in range(3)))
                pos=q['position'];d=q['travel_direction'];end=[pos[i]+p['length']*(d[i] if i<2 else 0) for i in range(3)]
                v={'game_constructed':True,'edges':[{'id':count,'node0':100+count,'node1':200+count,'p0':pos,'p1':end,'road_type':'TRACK'}]}
            elif op=='inspect' and p.get('resources'):
                v={'edges':[{'id':900,'resource':{'track_distance':spacing}}]}
            elif op=='inspect':v={'edges':[{'id':80,'p0':[126,8,33],'p1':[574,102,33],'t0':[448,94,0],'t1':[448,94,0]}]}
            else:raise AssertionError(op)
            return self.response('r'+str(count),op,result=v)
        ports=[({'edge_id':1,'node_id':11},'a'),({'edge_id':2,'node_id':12},'b'),
               ({'edge_id':3,'pos':[50,0,33]},'c'),({'edge_id':4,'pos':[50,5,33]},'d')]
        return query,calls,ports

    def test_recipe_plan_offline_and_frame_transform(self):
        from bridge_live import plan_junction_recipe
        b=self.recipe_brief();p=plan_junction_recipe(b)
        self.assertFalse(p['game_constructed']);self.assertFalse(p['native_fit_verified']);self.assertEqual(len(p['required_routes']),5)
        self.assertEqual([f['name'] for f in p['fixtures']],['A1','A2','D1','D2','D3'])
        self.assertEqual(p,plan_junction_recipe(b));self.assertEqual(p['selected_final_min_radius'],120);self.assertEqual(p['reference_design_min_radius'],160)
        rotated=plan_junction_recipe(b|{'heading_deg':90,'region':{'min':[-600,-100,0],'max':[100,1700,80]}})
        for x,y in zip(rotated['fixtures'][1]['position'],[-5,-20,33]):self.assertAlmostEqual(x,y)
        self.assertNotEqual(p['plan_hash'],rotated['plan_hash']);self.assertNotIn('template_edge',json.dumps(p))

    def test_recipe_invalid_or_unsupported_intent_never_executes(self):
        from bridge_live import plan_junction_recipe,execute_junction_recipe
        b=self.recipe_brief()
        for patch_value in ({'radius':160},{'spacing':7},{'recipe':'general_router'},{'origin':[0,0,float('nan')]},
                            {'heading_deg':181},{'max_grade':.05},{'region':{'min':[0,0,0],'max':[1,1,1]}},
                            {'asset_region':{'min':[0,0,0],'max':[401,10,80]}}):
            with patch.object(self.client,'request') as worker:
                with self.assertRaises((ValueError,LiveError)):plan_junction_recipe(b|patch_value)
                worker.assert_not_called()
        p=plan_junction_recipe(b);p['fixtures'][0]['position'][0]+=1
        with patch.object(self.client,'request') as worker:
            with self.assertRaises(ValueError):execute_junction_recipe(self.client,p)
            worker.assert_not_called()

    def test_recipe_cli_planning_needs_no_game_or_context_and_rejects_changed_plan(self):
        from bridge_live import plan_junction_recipe
        brief=self.root/'brief.json';brief.write_text(json.dumps(self.recipe_brief()));out=io.StringIO()
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(out):
            code=main(['junction-recipe','--params',str(brief),'--evidence',str(self.root/'plans')])
            native.assert_not_called()
        result=json.loads(out.getvalue());self.assertEqual(code,0);self.assertLess(len(out.getvalue().encode()),4096)
        saved=Path(result['evidence']);p=json.loads(saved.read_text());self.assertEqual(p,plan_junction_recipe(self.recipe_brief()))
        p['required_routes'].pop();saved.write_text(json.dumps(p));out=io.StringIO()
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request') as native,contextlib.redirect_stdout(out):
            code=main(['junction-recipe','--context','context.json','--params',str(brief),'--recipe-plan',str(saved),'--execute'])
            native.assert_not_called()
        self.assertEqual(code,1);self.assertIn('does not match',out.getvalue())

    def test_recipe_sequences_preparation_native_geometry_and_final_matrix(self):
        from bridge_live import plan_junction_recipe,execute_junction_recipe
        query,calls,ports=self.recipe_worker();corridors=[]
        def corridor(c,b,execute):
            self.assertTrue(execute);corridors.append(b)
            return {'status':'ok','game_constructed':True,'edges':[80]}
        def throat(c,b,execute):
            self.assertTrue(execute);self.assertEqual(b['required_routes'],plan_junction_recipe(self.recipe_brief())['required_routes'])
            self.assertEqual(set(b['roles']),{'A1','A2','D1','D2','D3'});self.assertEqual(b['radius'],120)
            self.assertEqual(b['steps'][1]['target']['guide_xyz'],[1100,460,33])
            return {'status':'ok','game_constructed':True,'routes_verified':5,'final_network_verified':True,'route_matrix':b['required_routes']}
        with patch.object(self.client,'request',side_effect=query),patch('bridge_live.connect_corridor',side_effect=corridor),patch('bridge_live.connect_throat',side_effect=throat),patch('bridge_live._select_throat_port',side_effect=ports):
            result=execute_junction_recipe(self.client,plan_junction_recipe(self.recipe_brief()))
        self.assertEqual(result['status'],'ok');self.assertEqual(result['routes_verified'],5);self.assertEqual(result['retained_approach_spacing'],5)
        self.assertEqual([op for op,p in calls],['discover','inspect']+['test_approach']*5+['inspect'])
        self.assertEqual([b['radius'] for b in corridors],[160,120]);self.assertFalse((self.client.evidence/'recipe.lock').exists())
        r=json.loads(Path(result['evidence']).read_text());self.assertEqual([o['name'] for o in r['operations']],r['plan']['operations'])

    def test_recipe_stops_on_partial_or_uncertain_effects_without_replay(self):
        from bridge_live import plan_junction_recipe,execute_junction_recipe
        for failure in ('fixture','corridor','throat'):
            query,calls,ports=self.recipe_worker(failure=failure)
            def corridor(c,b,execute):return {'status':'mutation_unverified','game_constructed':'unknown','error':'construction uncertain'} if failure=='corridor' else {'status':'ok','game_constructed':True,'edges':[80]}
            with patch.object(self.client,'request',side_effect=query),patch('bridge_live.connect_corridor',side_effect=corridor) as native,patch('bridge_live.connect_throat',return_value={'status':'native_verification_failed','game_constructed':True,'error':'missing route'}) as throat:
                result=execute_junction_recipe(self.client,plan_junction_recipe(self.recipe_brief()))
            self.assertNotEqual(result['status'],'ok');self.assertEqual(result['routes_verified'],0)
            self.assertEqual(result['game_constructed'],'unknown' if failure=='corridor' else True)
            self.assertEqual(sum(op=='test_approach' for op,p in calls),1 if failure=='fixture' else 5)
            self.assertEqual(native.call_count,0 if failure=='fixture' else 1 if failure=='corridor' else 2)
            self.assertEqual(throat.call_count,1 if failure=='throat' else 0);self.assertFalse((self.client.evidence/'recipe.lock').exists())

    def test_recipe_resource_gap_and_busy_execution_stop_before_mutation(self):
        from bridge_live import plan_junction_recipe,execute_junction_recipe
        query,calls,ports=self.recipe_worker(spacing=7)
        with patch.object(self.client,'request',side_effect=query):result=execute_junction_recipe(self.client,plan_junction_recipe(self.recipe_brief()))
        self.assertEqual(result['status'],'unsupported_recipe');self.assertFalse(result['game_constructed']);self.assertEqual(len(calls),2)
        lock=self.client.evidence/'recipe.lock';lock.write_text('busy')
        with patch.object(self.client,'request') as worker:
            with self.assertRaises(LiveError):execute_junction_recipe(self.client,plan_junction_recipe(self.recipe_brief()))
            worker.assert_not_called()

    def test_recipe_explicit_prepared_continuation_reacquires_stubs_without_rebuilding(self):
        from bridge_live import plan_junction_recipe,execute_junction_recipe
        plan=plan_junction_recipe(self.recipe_brief());worker,calls,ports=self.recipe_worker()
        with patch.object(self.client,'request',side_effect=worker),patch('bridge_live.connect_corridor',return_value={'status':'no_accepted_candidate','game_constructed':False}):
            stopped=execute_junction_recipe(self.client,plan)
        source=Path(stopped['evidence']);old=json.loads(source.read_text());rows=[o['response']['result']['edges'][0] for o in old['operations'][2:7]]
        for malformed in ({},{'operations':[]},{'operations':[None]}):
            source.write_text(json.dumps(malformed))
            with patch.object(self.client,'request') as native:
                with self.assertRaises(ValueError):execute_junction_recipe(self.client,plan,prepared_record=source)
                native.assert_not_called()
        for defect in ('none','stale','reconciled','unreconciled'):
            candidate=json.loads(json.dumps(old))
            if defect in ('reconciled','unreconciled'):
                workflow=self.client.evidence/'rejected_recipe.workflow.json'
                workflow.write_text(json.dumps({'attempts':[{'request_id':'rejected_recipe'}]}))
                candidate['summary']['status']='error'
                candidate['operations'][-1]['response']={'status':'error','error':'native_construction_rejected','game_constructed':'unknown','evidence':str(workflow)}
                rp=self.client.evidence/'rejected_recipe.reconciliation.json'
                if defect=='reconciled':rp.write_text(json.dumps({'status':'reconciled_rejected_corridor','completed_corridor_absent':True,'automatic_replay':False,'original_pending':{'request_id':'rejected_recipe'}}))
                elif rp.exists():rp.unlink()
            source.write_text(json.dumps(candidate))
            query,calls,ports=self.recipe_worker()
            def observe(op,p):
                if op=='inspect' and len(p['edge_ids'])==5:
                    return self.response('fresh_stubs',op,result={'edges':[] if defect=='stale' else rows})
                return query(op,p)
            with patch.object(self.client,'request',side_effect=observe),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True,'edges':[80]}) as fit,patch('bridge_live.connect_throat',return_value={'status':'ok','game_constructed':True,'routes_verified':5,'final_network_verified':True,'route_matrix':plan['required_routes']}),patch('bridge_live._select_throat_port',side_effect=ports):
                if defect=='unreconciled':
                    with self.assertRaises(ValueError):execute_junction_recipe(self.client,plan,prepared_record=source)
                    self.assertEqual(calls,[]);continue
                result=execute_junction_recipe(self.client,plan,prepared_record=source)
            self.assertEqual(result['status'],'stale_prepared_recipe' if defect=='stale' else 'ok')
            self.assertFalse(any(op=='test_approach' for op,p in calls));self.assertEqual(fit.call_count,0 if defect=='stale' else 2)

    def recipe_current_world(self,*,defect=None,missing_branch=False,missing_cross=False):
        from bridge_live import plan_junction_recipe,_recipe_throat_brief,_recipe_intent
        plan=plan_junction_recipe(self.recipe_brief());calls=[];built={'branch':not missing_branch,'cross':not missing_cross};fixtures={};roles={}
        for i,f in enumerate(plan['fixtures']):
            end=[f['position'][k]+20*(f['travel_direction'][k] if k<2 else 0) for k in range(3)]
            fixtures[f['name']]={'id':i+1,'node0':10+i,'node1':20+i,'p0':f['position'],'p1':end,'road_type':'TRACK','template':'t','style':'s','t0':[end[k]-f['position'][k] for k in range(3)],'t1':[end[k]-f['position'][k] for k in range(3)]}
            q=f['position'] if i<2 else end
            roles[tuple(q)]=(f['name'],{'edge_id':i+101,'node_id':i+201,'edge_snapshot':fixtures[f['name']]|{'id':i+101}})
        guide={'id':80,'p0':[126,8,33],'p1':[574,102,33],'t0':[448,94,0],'t1':[448,94,0]}
        b=_recipe_throat_brief(plan,fixtures,[guide]);nodes={tuple(b['steps'][0]['source']['guide_xyz']):501,tuple(b['steps'][0]['target']['guide_xyz']):502,tuple(b['steps'][1]['source']['guide_xyz']):503}
        record={'plan':plan,'operations':[{'name':'prepare_'+n,'response':{'status':'ok','result':{'edges':[e]}}} for n,e in fixtures.items()]+[{'name':'native_guides','response':{'status':'ok','result':{'edges':[guide]}}}],
                'throat_brief':b,'summary':{'status':'error','stage':'throat','game_constructed':'unknown'}}
        source=self.root/'recipe_failed.json';source.write_text(json.dumps(record))
        def select(client,intent,**options):
            calls.append(('select',intent))
            if tuple(intent['guide_xyz']) in roles:
                name,c=roles[tuple(intent['guide_xyz'])];c=json.loads(json.dumps(c))
                if defect=='geometry':c['edge_snapshot']['p0'][0]+=1
                if defect=='asset':c['edge_snapshot']['template']='changed'
                return c,'selected_'+name
            q=intent['guide_xyz'];e={'p0':[q[0]-50,q[1],q[2]],'p1':[q[0]+50,q[1],q[2]],'t0':[100,0,0],'t1':[100,0,0]}
            return {'edge_id':700 if q[1]<3 else 701,'node_id':800,'pos':q,'edge_snapshot':e},'interior'
        def request(op,p):
            calls.append((op,p))
            if op=='route':
                target=next(n for n,c in roles.values() if c['node_id']==p['target_node']);source_name=next(n for n,c in roles.values() if c['node_id']==p['source_node']);ok=(built['branch'] or target!='D3') and (built['cross'] or source_name!='A1' or target=='D1')
                path=[{'from':{'entity':n},'to':{'entity':n}} for n in (501,502,503)]
                if defect=='bypass':path=[]
                r=self.response('route'+str(len(calls)),op,result={'requested_route_verified':ok,'path':path,'game_constructed':False})
                if defect=='route_error':r['status']='error';r['result']['error']='radius_below_limit'
                return r
            if op=='discover':
                q=[sum(p['region'][k][i] for k in ('min','max'))/2 for i in range(3)];node=nodes[tuple(q)]
                return self.response('junction',op,result={'complete':defect!='truncated','candidates':[{'node_id':node,'pos':q,'incident_count':3,'incidence_complete':True,'incident_edges':[900,901,902]}]})
            if op=='inspect':
                node=nodes[tuple([sum(calls[-2][1]['region'][k][i] for k in ('min','max'))/2 for i in range(3)])]
                return self.response('incident',op,result={'edges':[{'id':eid,'node0':node,'node1':1000+eid,'road_type':'TRACK'} for eid in p['edge_ids']]})
            raise AssertionError('unexpected native operation '+op)
        return source,plan,select,request,built,calls

    def test_recipe_inspect_and_continue_completed_network_reacquire_changed_ids_no_build(self):
        from bridge_live import inspect_junction_recipe,continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world();before=source.read_bytes()
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor') as corridor,patch('bridge_live.connect_throat') as throat,patch('bridge_live.connect_junction_at') as branch:
            inspected=inspect_junction_recipe(self.client,source);result=continue_junction_recipe(self.client,source)
            self.assertEqual(inspected['status'],'ok');self.assertEqual(result['status'],'ok');self.assertEqual(result['new_mutations'],0)
            self.assertFalse(result['game_constructed']);self.assertEqual(result['routes_verified'],5)
            # The new successful receipt can itself be inspected/continued without duplication.
            again=continue_junction_recipe(self.client,result['evidence']);self.assertEqual(again['status'],'ok');self.assertEqual(again['new_mutations'],0)
            corridor.assert_not_called();throat.assert_not_called();branch.assert_not_called()
        self.assertEqual(source.read_bytes(),before);self.assertLess(len(json.dumps(result).encode()),4096)
        rows=json.loads(Path(inspected['evidence']).read_text())['assessment']['roles'];self.assertEqual(rows['A1']['edge_id'],101)
        self.assertFalse(any(is_mutation(op,p) for op,p in calls if op!='select'))

    def test_recipe_current_state_geometry_assets_junctions_and_route_errors_block_replay(self):
        from bridge_live import inspect_junction_recipe,continue_junction_recipe
        for defect in ('geometry','asset','bypass','truncated','route_error'):
            source,plan,select,request,built,calls=self.recipe_current_world(defect=defect)
            with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor') as corridor,patch('bridge_live.connect_throat') as throat,patch('bridge_live.connect_junction_at') as branch:
                inspected=inspect_junction_recipe(self.client,source);result=continue_junction_recipe(self.client,source)
                self.assertNotEqual(inspected['status'],'ok',defect);self.assertNotEqual(result['status'],'ok',defect)
                self.assertEqual(result['new_mutations'],0);corridor.assert_not_called();throat.assert_not_called();branch.assert_not_called()
            self.assertFalse((self.client.evidence/'recipe.lock').exists())

    def test_recipe_continue_only_missing_branch_after_current_exact_crossover(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True);before=source.read_bytes()
        def build(client,brief,**kwargs):
            self.assertTrue(kwargs['execute']);self.assertEqual(kwargs['junction_nodes'],[501,502]);built['branch']=True
            return {'status':'ok','game_constructed':True}
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor') as corridor,patch('bridge_live.connect_throat') as throat,patch('bridge_live.connect_junction_at',side_effect=build) as branch:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'ok');self.assertEqual(r['new_mutations'],1)
            self.assertTrue(r['game_constructed']);branch.assert_called_once();corridor.assert_not_called();throat.assert_not_called()
        self.assertEqual(source.read_bytes(),before)

    def test_recipe_unknown_pending_state_stops_continuation_and_keeps_failed_receipt(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True)
        self.client.journal.write_text(json.dumps({'pending':{'operation':'interior_junction','request_id':'uncertain'}}))
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at') as build:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'reconciliation_required');build.assert_not_called()
        self.assertEqual(json.loads(self.client.journal.read_text())['pending']['request_id'],'uncertain')
        self.assertEqual(json.loads(source.read_text())['summary']['status'],'error')

    def test_recipe_cli_inspect_is_read_only_continue_requires_explicit_authority_and_matching_brief(self):
        from bridge_live import inspect_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world();brief=self.root/'recipe_brief.json';brief.write_text(json.dumps(plan['brief']))
        with patch('bridge_live.client_from_context',return_value=self.client),patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['junction-recipe-inspect','--params',str(brief),'--context','unused','--recipe-record',str(source)])
        self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue())['mutations'],0)
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request') as native,contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['junction-recipe-continue','--params',str(brief),'--context','unused','--recipe-record',str(source)])
            self.assertEqual(code,1);native.assert_not_called()
            brief.write_text(json.dumps(plan['brief']|{'heading_deg':1}))
            code=main(['junction-recipe-continue','--params',str(brief),'--context','unused','--recipe-record',str(source),'--execute'])
            self.assertEqual(code,1);native.assert_not_called()

    def test_recipe_cross_session_uncertain_effects_still_require_reconciliation(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True)
        record=json.loads(source.read_text());record['operations'].append({'name':'throat','response':{'status':'mutation_unverified','game_constructed':'unknown'}});source.write_text(json.dumps(record))
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at') as build:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'reconciliation_required');build.assert_not_called()
        self.assertEqual(r['new_mutations'],0)

    def test_recipe_inspection_receipt_can_be_used_but_changed_original_is_rejected(self):
        from bridge_live import inspect_junction_recipe,continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world()
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request):
            inspected=inspect_junction_recipe(self.client,source);r=continue_junction_recipe(self.client,inspected['evidence']);self.assertEqual(r['status'],'ok')
        source.write_text(source.read_text()+' ')
        with patch.object(self.client,'request') as native:
            with self.assertRaises(ValueError):continue_junction_recipe(self.client,inspected['evidence'])
            native.assert_not_called()

    def test_recipe_changed_interface_tangent_and_edited_native_guide_fail_without_writes(self):
        from bridge_live import inspect_junction_recipe,continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world()
        def changed(client,intent,**options):
            c,rid=select(client,intent,**options)
            if c.get('edge_snapshot'):c['edge_snapshot']['t0'][2]=1
            return c,rid
        with patch('bridge_live._select_throat_port',side_effect=changed),patch.object(self.client,'request',side_effect=request):
            r=inspect_junction_recipe(self.client,source);self.assertEqual(r['status'],'recipe_state_changed')
        record=json.loads(source.read_text());record['throat_brief']['steps'][1]['source']['guide_xyz'][0]+=10;source.write_text(json.dumps(record))
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at') as build:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'recipe_state_unknown');build.assert_not_called()

    def test_recipe_failed_missing_branch_stops_once_and_keeps_unknown_effects(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True)
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at',return_value={'status':'mutation_unverified','game_constructed':'unknown','error':'lost acknowledgement'}) as build:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'mutation_unverified');build.assert_called_once()
        self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(r['new_mutations'],1);self.assertEqual(r['routes_verified'],0)
        self.assertEqual(json.loads(source.read_text())['summary']['status'],'error')

    def test_recipe_checked_throat_continuation_needs_no_extracted_brief(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True,missing_cross=True)
        def build(client,brief,**kwargs):
            self.assertTrue(kwargs['execute']);self.assertEqual(brief['required_routes'],plan['required_routes']);built.update(cross=True,branch=True)
            return {'status':'ok','game_constructed':True}
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor') as corridor,patch('bridge_live.connect_throat',side_effect=build) as throat:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'ok');self.assertEqual(r['new_mutations'],1);throat.assert_called_once();corridor.assert_not_called()
            again=continue_junction_recipe(self.client,r['evidence']);self.assertEqual(again['status'],'ok');self.assertEqual(again['new_mutations'],0);throat.assert_called_once()

    def test_recipe_absent_interface_is_reported_without_automatic_fixture_recreation(self):
        from bridge_live import inspect_junction_recipe,continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world()
        def missing(client,intent,**options):
            if intent['guide_xyz']==plan['fixtures'][0]['position']:raise LiveError('no_eligible_candidates','attachment absent')
            return select(client,intent,**options)
        def query(op,p):
            self.assertEqual(op,'discover');return self.response('empty',op,result={'complete':True,'edge_count':0,'candidates':[]})
        with patch('bridge_live._select_throat_port',side_effect=missing),patch.object(self.client,'request',side_effect=query),patch('bridge_live.connect_corridor') as construction:
            r=inspect_junction_recipe(self.client,source);self.assertEqual(r['status'],'recipe_incomplete');self.assertEqual(r['current_steps']['prepare_A1'],'absent')
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'recipe_state_unknown');self.assertEqual(r['new_mutations'],0);construction.assert_not_called()

    def test_recipe_interrupted_step_is_durable_and_not_repeated_in_a_new_session(self):
        from bridge_live import continue_junction_recipe
        source,plan,select,request,built,calls=self.recipe_current_world(missing_branch=True)
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at',side_effect=LiveError('mutation_outcome_unknown','no acknowledgement')) as build:
            r=continue_junction_recipe(self.client,source);self.assertEqual(r['status'],'mutation_outcome_unknown');self.assertEqual(r['new_mutations'],1);self.assertEqual(r['game_constructed'],'unknown');build.assert_called_once()
        saved=Path(r['evidence']);self.assertEqual(json.loads(saved.read_text())['pending_recipe_step'],'branch')
        with patch('bridge_live._select_throat_port',side_effect=select),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at') as build:
            r=continue_junction_recipe(self.client,saved);self.assertEqual(r['status'],'reconciliation_required');self.assertEqual(r['new_mutations'],0);build.assert_not_called()

    def test_recipe_spacing_requires_full_length_and_samples_beyond_midpoint(self):
        from bridge_live import inspect_junction_recipe
        for defect in ('short','diverging'):
            source,plan,select,request,built,calls=self.recipe_current_world()
            def altered(client,intent,**options):
                c,rid=select(client,intent,**options)
                if options.get('interior') and intent['guide_xyz']==[50,5,33]:
                    e=c['edge_snapshot'];e['p1']=[60,5,33] if defect=='short' else [100,6,33]
                    e['t0']=e['t1']=[e['p1'][i]-e['p0'][i] for i in range(3)]
                return c,rid
            with patch('bridge_live._select_throat_port',side_effect=altered),patch.object(self.client,'request',side_effect=request):
                r=inspect_junction_recipe(self.client,source);self.assertEqual(r['status'],'native_verification_failed',defect)

    def test_rejected_corridor_and_crossover_reconcile_without_replay(self):
        from bridge_live import reconcile_rejected_corridor,reconcile_rejected_crossover
        for op,fn in [('corridor',reconcile_rejected_corridor),('crossover',reconcile_rejected_crossover)]:
            pending={'operation':op,'request_id':'reject_'+op,'params':{'execute':True}}
            self.client.journal.write_text(json.dumps({'session':self.client.session,'pending':pending}))
            original=self.response(pending['request_id'],op,result={'error':'native_construction_rejected','native_command_success':False,'stage':'build','game_constructed':'unknown'})|{'status':'error'}
            path=self.client.evidence/(pending['request_id']+'.response.json');path.write_text(json.dumps(original));before=path.read_bytes()
            observed=self.response('observe',op,result={'game_constructed':False,'through_before':[{'requested_route_verified':True}]*2})
            with patch.object(self.client,'request',return_value=observed) as worker:r=fn(self.client)
            operation,params=worker.call_args.args;self.assertEqual(operation,op);self.assertFalse(params['execute']);self.assertFalse(is_mutation(operation,params))
            self.assertEqual(worker.call_count,1);self.assertFalse(r['result']['automatic_replay']);self.assertNotIn('pending',json.loads(self.client.journal.read_text()));self.assertEqual(path.read_bytes(),before)

if __name__ == '__main__':
    unittest.main()
