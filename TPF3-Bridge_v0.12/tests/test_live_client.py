import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import contextlib
import io
from bridge_live import LiveClient, LiveError, MARKER, lua_literal, parse_response, main, extend, connect, route, discover, connect_selected, reconcile_rejected_fixture, discover_session, client_from_context

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

    def test_route_invalid_input_never_sends(self):
        for key,value in [('mode','CAR'),('max_length',float('inf')),('max_length',801),
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
                readback={'connected':True,'ordered_edges':[30,31],'ordered_nodes':[11,40,21],
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
            'readback': {'connected': True, 'ordered_edges': [4, 5], 'ordered_nodes': [2, 6, 7]}})

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

if __name__ == '__main__':
    unittest.main()
