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
        for key,value in [('mode','CAR'),('max_length',float('inf')),('max_length',8001),
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

    def parallel_brief(self,pattern=('UP','UP','DOWN','DOWN'),up='increasing',heading=-50):
        b=json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/parallel_layout_example.json').read_text())
        b['tracks']=[{'id':'T'+str(i+1),'direction':x} for i,x in enumerate(pattern)];b['route_reference']['up']=up;b['route_reference']['heading_deg']=heading
        b['region']={'min':[-5000,-5000,0],'max':[10000,10000,80]}
        b['movements']=[]
        for t in b['tracks']:
            positive=(t['direction']=='UP')==(up=='increasing');a,z=('west','east') if positive else ('east','west')
            b['movements'].append({'from':t['id']+':'+a,'to':t['id']+':'+z})
        for t,branch in [(b['tracks'][0],'branch_up'),(b['tracks'][-1],'branch_down')]:
            positive=(t['direction']=='UP')==(up=='increasing');west=t['id']+':west'
            b['movements'].append({'from':west,'to':branch} if positive else {'from':branch,'to':west})
        return b

    def test_parallel_patterns_direction_reference_and_rotation_are_deterministic(self):
        from bridge_live import plan_parallel_layout
        for pattern in [('UP','DOWN'),('UP','DOWN','UP','DOWN'),('UP','UP','DOWN','DOWN')]:
            for up in ('increasing','decreasing'):
                b=self.parallel_brief(pattern,up,90);p=plan_parallel_layout(b)
                self.assertEqual(p,plan_parallel_layout(b));self.assertEqual(p['pattern'],'-'.join(pattern));self.assertEqual(len(p['movements']),len(pattern)+2)
                self.assertTrue(p['native_execution_supported'])
                self.assertEqual(p['direction_enforcement'],'not_provided');self.assertFalse(p['game_constructed'])
                self.assertAlmostEqual(p['native_construction_direction'][1],1)
                for t in b['tracks']:
                    port=p['ports'][t['id']+':west'];positive=(t['direction']=='UP')==(up=='increasing')
                    self.assertAlmostEqual(port['travel_direction'][1],1 if positive else -1)
                    self.assertEqual(port['function'],'entry' if positive else 'exit')
                # Track order is the reference's left normal, not map-axis ordering.
                self.assertLess(p['ports']['T2:west']['position'][0],p['ports']['T1:west']['position'][0])

    def test_parallel_against_direction_and_unsupported_cross_track_matrix_reject_before_calls(self):
        from bridge_live import plan_parallel_layout,execute_parallel_layout
        b=self.parallel_brief();cases=[]
        wrong=json.loads(json.dumps(b));wrong['movements'][0]={'from':'T1:east','to':'T1:west'};cases.append(wrong)
        cross=json.loads(json.dumps(b));cross['movements'][0]={'from':'T1:west','to':'T2:east'};cases.append(cross)
        omitted=json.loads(json.dumps(b));omitted['movements'].pop();cases.append(omitted)
        duplicate=json.loads(json.dumps(b));duplicate['tracks'][1]['id']='T1';cases.append(duplicate)
        ambiguous=json.loads(json.dumps(b));ambiguous['route_reference'].pop('up');cases.append(ambiguous)
        bad=json.loads(json.dumps(b));bad['tracks'][0]['direction']='NORTH';cases.append(bad)
        interleaved=self.parallel_brief(('UP','DOWN','UP','DOWN'));interleaved['movements'][0]={'from':'T1:west','to':'T3:east'};cases.append(interleaved)
        for brief in cases:
            with patch.object(self.client,'request') as worker:
                with self.assertRaises((ValueError,LiveError)):plan_parallel_layout(brief)
                worker.assert_not_called()

    def test_parallel_cli_plan_is_offline_compact_and_current_record_must_match(self):
        from bridge_live import plan_parallel_layout
        b=self.parallel_brief();brief=self.root/'parallel_brief.json';brief.write_text(json.dumps(b))
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['parallel-layout','--params',str(brief),'--evidence',str(self.root/'plans')]);native.assert_not_called()
        self.assertEqual(code,0);r=json.loads(out.getvalue());self.assertLess(len(out.getvalue().encode()),4096)
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved,plan_parallel_layout(b))
        saved['plan_hash']='edited';record=self.root/'parallel.json';record.write_text(json.dumps({'plan':saved}))
        with patch('bridge_live.client_from_context',return_value=self.client),patch.object(self.client,'request') as native,contextlib.redirect_stdout(io.StringIO()):
            code=main(['parallel-layout-inspect','--params',str(brief),'--context','unused','--layout-record',str(record)])
            self.assertEqual(code,1);native.assert_not_called()

    def test_parallel_execution_sequences_four_through_two_outward_branches_and_stops_partial(self):
        from bridge_live import plan_parallel_layout,execute_parallel_layout
        p=plan_parallel_layout(self.parallel_brief());calls=[]
        def request(op,params):
            calls.append(op)
            if op=='discover':v={'complete':True,'candidates':[{'edge_id':900,'edge_snapshot':{'template':'t','style':'s'}}]}
            elif op=='inspect':v={'edges':[{'resource':{'track_distance':5}}]}
            elif op=='test_approach':v={'game_constructed':True,'edges':[{'road_type':'TRACK'}]}
            else:raise AssertionError(op)
            return self.response('r'+str(len(calls)),op,result=v)
        verified={'routes_verified':6,'final_network_verified':True,'direction_intent_compatible':True,'direction_enforcement':'not_provided'}
        with patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True}) as through,patch('bridge_live.connect_junction_at',return_value={'status':'ok','game_constructed':True,'junction':{'node':500}}) as branch,patch('bridge_live._verify_parallel_layout',return_value=verified):
            r=execute_parallel_layout(self.client,p);self.assertEqual(r['status'],'ok');self.assertEqual(r['routes_verified'],6)
            self.assertEqual(through.call_count,4);self.assertEqual(branch.call_count,2);self.assertEqual(calls.count('test_approach'),10)
            self.assertEqual(branch.call_args_list[0].args[1]['source'],p['branches'][0]['source'])
            # DOWN native construction uses the same forward geometric reference;
            # traffic intent is subsequently verified in the opposite direction.
            self.assertEqual(branch.call_args_list[1].args[1]['target']['travel_direction'],p['native_construction_direction'])
        with patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'mutation_unverified','game_constructed':'unknown','error':'lost acknowledgement'}) as through,patch('bridge_live.connect_junction_at') as branch,patch('bridge_live._verify_parallel_layout') as verify:
            r=execute_parallel_layout(self.client,p);self.assertEqual(r['status'],'mutation_unverified');self.assertEqual(r['game_constructed'],'unknown');through.assert_called_once();branch.assert_not_called();verify.assert_not_called()
        self.assertFalse((self.client.evidence/'parallel.lock').exists())

    def test_parallel_fresh_movements_use_intended_down_flow_and_current_native_roles(self):
        from bridge_live import plan_parallel_layout,_verify_parallel_layout,_recipe_intent
        p=plan_parallel_layout(self.parallel_brief(heading=0));requests=[];ports={name:({'edge_id':100+i,'node_id':200+i,'pos':v['position']},v) for i,(name,v) in enumerate(p['ports'].items())}
        node_by_pos={tuple(b['source']['guide_xyz']):500+i for i,b in enumerate(p['branches'])}
        def select(client,intent,**opts):
            if opts.get('interior'):
                i=round((intent['guide_xyz'][1]-p['brief']['route_reference']['origin'][1])/5);o=p['brief']['route_reference']['origin'];y=o[1]+5*i
                e={'id':800+i,'p0':[o[0],y,o[2]],'p1':[o[0]+600,y,o[2]],'t0':[600,0,0],'t1':[600,0,0]}
                return {'edge_id':800+i,'edge_snapshot':e},'spacing'+str(i)
            for name,(c,v) in ports.items():
                if v['position']==intent['guide_xyz']:
                    self.assertEqual(opts['outward_sign'],-1 if v['end']=='west' else 1);return c,'port_'+name
            raise AssertionError(intent)
        def junction(client,intent):return node_by_pos[tuple(intent['guide_xyz'])],['junction_observation']
        def request(op,q):
            self.assertEqual(op,'route');requests.append(q)
            self.assertTrue(q['geometry_constraints']['all_path']);self.assertEqual(q['geometry_constraints']['radius'],120)
            return self.response('route'+str(len(requests)),op,result={'requested_route_verified':True,'path':[{'from':{'entity':n},'to':{'entity':n}} for n in (500,501)]})
        path=self.client.evidence/'parallel_verified.json';record={'summary':{'evidence':str(path)}}
        with patch('bridge_live._select_throat_port',side_effect=select),patch('bridge_live._recipe_junction',side_effect=junction),patch.object(self.client,'request',side_effect=request):
            r=_verify_parallel_layout(self.client,p,record)
        self.assertEqual(r['routes_verified'],6);self.assertTrue(r['direction_intent_compatible']);self.assertEqual(r['direction_enforcement'],'not_provided')
        self.assertEqual(len(r['retained_spacing']),3);self.assertTrue(all(x['min']==5 and x['max']==5 for x in r['retained_spacing']))
        down=requests[2];self.assertEqual(down['source_node'],ports['T3:east'][0]['node_id']);self.assertEqual(down['target_node'],ports['T3:west'][0]['node_id'])
        branch=requests[-1];self.assertEqual(branch['source_node'],ports['branch_down'][0]['node_id']);self.assertEqual(branch['target_node'],ports['T4:west'][0]['node_id'])
        self.assertFalse(any(is_mutation('route',q) for q in requests))
        # An unsignalled reverse route could exist, but it remains invalid design intent.
        wrong=json.loads(json.dumps(p['brief']));wrong['movements'][2]={'from':'T3:west','to':'T3:east'}
        with patch.object(self.client,'request') as worker:
            with self.assertRaises(LiveError) as exc:plan_parallel_layout(wrong)
            self.assertEqual(exc.exception.status,'against_running_direction');worker.assert_not_called()
        def bypass(op,q):return self.response('wrong',op,result={'requested_route_verified':True,'path':[]})
        with patch('bridge_live._select_throat_port',side_effect=select),patch('bridge_live._recipe_junction',side_effect=junction),patch.object(self.client,'request',side_effect=bypass):
            with self.assertRaises(LiveError):_verify_parallel_layout(self.client,p,record)

    def test_parallel_existing_pending_or_changed_plan_stops_before_mutation(self):
        from bridge_live import plan_parallel_layout,execute_parallel_layout
        p=plan_parallel_layout(self.parallel_brief());self.client.journal.write_text(json.dumps({'pending':{'request_id':'old'}}))
        with patch.object(self.client,'request') as worker:
            r=execute_parallel_layout(self.client,p);self.assertEqual(r['status'],'reconciliation_required');self.assertFalse(r['game_constructed']);worker.assert_not_called()
            p['movements'].pop()
            with self.assertRaises(ValueError):execute_parallel_layout(self.client,p)
            worker.assert_not_called()

    def test_parallel_authorised_footprint_does_not_inherit_larger_recipe_extent(self):
        from bridge_live import plan_parallel_layout,plan_junction_recipe
        b=self.parallel_brief(heading=0);b['region']={'min':[1600,6150,0],'max':[3000,6900,80]}
        p=plan_parallel_layout(b);self.assertLess(p['footprint']['max'][0],3000)
        old=json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/junction_recipe_example.json').read_text())
        self.assertEqual(plan_junction_recipe(old)['plan_hash'],'19cb06710e1ecf27a4387619450053d0f1e27b810855bfdaf93a4c516023f71f')

    def test_parallel_enabled_patterns_execute_shared_native_stages_with_fixed_construction_orientation(self):
        from bridge_live import plan_parallel_layout,execute_parallel_layout
        for pattern in [('UP','DOWN'),('UP','DOWN','UP','DOWN'),('UP','UP','DOWN','DOWN')]:
            for up in ('increasing','decreasing'):
                p=plan_parallel_layout(self.parallel_brief(pattern,up,37));calls=[]
                def request(op,q):
                    calls.append(op)
                    if op=='discover':v={'complete':True,'candidates':[{'edge_id':900,'edge_snapshot':{'template':'t','style':'s'}}]}
                    elif op=='inspect':v={'edges':[{'resource':{'track_distance':5}}]}
                    else:
                        self.assertEqual(op,'test_approach');self.assertEqual(q['fixture']['travel_direction'],p['native_construction_direction']);v={'game_constructed':True}
                    return self.response('r'+str(len(calls)),op,result=v)
                def verified(c,plan,record):
                    record['routes']=[r|{'verified':True} for r in plan['movements']]
                    return {'routes_verified':len(plan['movements']),'final_network_verified':True}
                with patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True}) as through,patch('bridge_live.connect_junction_at',return_value={'status':'ok','game_constructed':True,'junction':{'node':500}}) as branch,patch('bridge_live._verify_parallel_layout',side_effect=verified):
                    result=execute_parallel_layout(self.client,p);self.assertEqual(result['status'],'ok');self.assertEqual(through.call_count,len(pattern));self.assertEqual(branch.call_count,2)
                    self.assertEqual(calls.count('test_approach'),2*len(pattern)+2);self.assertTrue(all(r['state']=='verified' for r in result['movement_results']))
                    self.assertLess(len(json.dumps(result).encode()),4096)
                    for call in through.call_args_list:self.assertEqual(call.args[1]['source']['travel_direction'],p['native_construction_direction'])

    def test_parallel_partial_readback_preserves_current_completed_movements_and_unavailable_port(self):
        from bridge_live import plan_parallel_layout,inspect_parallel_layout
        p=plan_parallel_layout(self.parallel_brief(('UP','DOWN'),'decreasing',0));o=p['brief']['route_reference']['origin']
        ports={name:{'edge_id':100+i,'node_id':200+i,'pos':v['position']} for i,(name,v) in enumerate(p['ports'].items())}
        def select(c,intent,**opts):
            if opts.get('interior'):
                i=round((intent['guide_xyz'][1]-o[1])/5);a=[o[0],o[1]+5*i,o[2]];z=[o[0]+600,a[1],a[2]]
                return {'edge_snapshot':{'id':800+i,'p0':a,'p1':z,'t0':[600,0,0],'t1':[600,0,0]}},'approach'
            name=next(name for name,v in p['ports'].items() if v['position']==intent['guide_xyz'])
            if name=='T2:east':raise LiveError('no_eligible_candidates','not currently established')
            return ports[name],'port_'+name
        def request(op,q):
            self.assertEqual(op,'route');return self.response('route',op,result={'requested_route_verified':True,'path':[{'from':{'entity':500},'to':{'entity':501}}]})
        original=self.root/'partial_parallel.json';original.write_text(json.dumps({'plan':p,'summary':{'status':'no_accepted_candidate','game_constructed':True},'operations':[]}));before=original.read_bytes()
        with patch('bridge_live._select_throat_port',side_effect=select),patch('bridge_live._recipe_junction',return_value=(500,['junction'])),patch.object(self.client,'request',side_effect=request):
            result=inspect_parallel_layout(self.client,original)
        self.assertEqual(result['status'],'layout_incomplete');self.assertEqual(result['routes_verified'],3);self.assertFalse(result['game_constructed']);self.assertFalse(result['final_network_verified'])
        self.assertTrue(result['recorded_prior_game_constructed']);self.assertEqual([r['state'] for r in result['movement_results']],['verified','unverified','verified','verified'])
        self.assertEqual(result['current_steps']['T2:east'],'unavailable');self.assertEqual(result['next_action'],'inspect_missing_attachments');self.assertEqual(original.read_bytes(),before)
        self.assertLess(len(json.dumps(result).encode()),4096)

    def test_parallel_inspection_keeps_unknown_effects_separate_from_partial_readback(self):
        from bridge_live import plan_parallel_layout,inspect_parallel_layout
        p=plan_parallel_layout(self.parallel_brief(('UP','DOWN'),'decreasing'))
        path=self.root/'unfinished_parallel.json';path.write_text(json.dumps({'plan':p,'summary':{'game_constructed':'unknown'},'unfinished_step':'through_T1','operations':[]}))
        def partial(c,plan,record,**kw):
            self.assertTrue(kw['partial']);record['routes']=[plan['movements'][0]|{'verified':True}]
            return {'routes_verified':1,'final_network_verified':False}
        with patch('bridge_live._verify_parallel_layout',side_effect=partial),patch.object(self.client,'request') as native:
            result=inspect_parallel_layout(self.client,path);native.assert_not_called()
        self.assertEqual(result['status'],'layout_incomplete');self.assertEqual(result['next_action'],'reconcile_native_operation');self.assertEqual(result['recorded_prior_game_constructed'],'unknown')

    def test_parallel_final_spacing_failure_keeps_verified_routes_without_claiming_acceptance(self):
        from bridge_live import plan_parallel_layout,inspect_parallel_layout
        p=plan_parallel_layout(self.parallel_brief(('UP','DOWN'),'decreasing'))
        path=self.root/'spacing_failure.json';path.write_text(json.dumps({'plan':p,'summary':{'status':'ok','game_constructed':True}}))
        def fail(c,plan,record,**kw):
            record['routes']=[r|{'verified':True} for r in plan['movements']]
            raise LiveError('native_verification_failed','ordered native spacing differs from5')
        with patch('bridge_live._verify_parallel_layout',side_effect=fail),patch.object(self.client,'request') as native:
            result=inspect_parallel_layout(self.client,path);native.assert_not_called()
        self.assertEqual(result['status'],'native_verification_failed');self.assertEqual(result['routes_verified'],4);self.assertFalse(result['final_network_verified'])
        self.assertTrue(all(r['state']=='verified' for r in result['movement_results']));self.assertFalse(result['game_constructed'])

    def switching_brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/switching_layout_example.json').read_text())

    def switching_runtime(self,p):
        import hashlib
        from bridge_live import _recipe_throat_brief
        runtime={};briefs={}
        for index,pair in enumerate(p['pairs']):
            fixtures={f['name']:{'p0':f['position'],'p1':[f['position'][k]+20*(f['travel_direction'][k] if k<2 else 0) for k in range(3)]} for f in pair['fixtures']}
            a=pair['fanout']['guides'][0]['position'];z=pair['fanout']['target']['guide_xyz'];chord=[z[k]-a[k] for k in range(3)]
            b=_recipe_throat_brief(pair,fixtures,[{'p0':a,'p1':z,'t0':chord,'t1':chord}]);briefs[pair['name']]=b
            path=self.root/(pair['name']+'_throat.json');path.write_text(json.dumps({'brief':b,'summary':{'status':'ok'},'semantic_mapping':{'step_edges':{'cross':[900+index]}}}))
            runtime[pair['name']]={'throat_record':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        return runtime,briefs

    def test_switching_plan_has_explicit_directional_transfers_and_outward_widening(self):
        from bridge_live import plan_switching_layout,plan_parallel_layout
        b=self.switching_brief();p=plan_switching_layout(b);self.assertEqual(p,plan_switching_layout(b));self.assertEqual(len(p['movements']),8)
        self.assertEqual(p['pairs'][0]['transfer'],{'from':'U2:west','to':'U1:east'})
        self.assertEqual(p['pairs'][1]['transfer'],{'from':'D2:east','to':'D1:west'})
        self.assertEqual(p['ports']['D2:east']['function'],'entry');self.assertEqual(p['ports']['branch_down']['function'],'entry')
        self.assertFalse(p['native_runtime_demonstrated']);self.assertFalse(p['game_constructed'])
        # Zero-degree rotation makes outward displacement/order independently visible.
        b['route_reference']['heading_deg']=0;b['region']={'min':[-10000,-10000,0],'max':[10000,10000,80]};p=plan_switching_layout(b)
        origin=b['route_reference']['origin'];self.assertLess(p['ports']['U1:east']['position'][1],origin[1]);self.assertGreater(p['ports']['D2:east']['position'][1],origin[1]+15)
        west=[p['ports'][t['id']+':west']['position'][1] for t in b['tracks']];self.assertEqual([west[i+1]-west[i] for i in range(3)],[5,5,5])
        self.assertLess(p['ports']['U2:east']['construction_direction'][1],0);self.assertGreater(p['ports']['D1:east']['construction_direction'][1],0)
        old=json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/parallel_layout_example.json').read_text())
        self.assertEqual(plan_parallel_layout(old)['plan_hash'],'ffc95fefd91d2e821cbcc69d9075ec38cb3fe3bfe1a3ba311353cb29f2d0aec4')

    def test_switching_invalid_matrices_pattern_region_and_offline_cli(self):
        from bridge_live import plan_switching_layout
        b=self.switching_brief();cases=[]
        for movement in ({'from':'U1:west','to':'U2:east'},{'from':'U2:east','to':'U1:west'},{'from':'U2:west','to':'D1:east'}):
            bad=json.loads(json.dumps(b));bad['movements'][-2]=movement;cases.append(bad)
        bad=json.loads(json.dumps(b));bad['movements'].pop();cases.append(bad)
        bad=json.loads(json.dumps(b));bad['tracks'][1]['direction']='DOWN';cases.append(bad)
        bad=json.loads(json.dumps(b));bad['region']={'min':[3499,6499,32],'max':[3501,6501,34]};cases.append(bad)
        for bad in cases:
            with patch.object(self.client,'request') as native:
                with self.assertRaises((LiveError,ValueError)):plan_switching_layout(bad)
                native.assert_not_called()
        path=self.root/'brief.json';path.write_text(json.dumps(b))
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['switching-layout','--params',str(path),'--evidence',str(self.root/'plans')])
        self.assertEqual(code,0);native.assert_not_called();self.assertLess(len(out.getvalue().encode()),4096)

    def test_switching_build_sequences_both_pairs_and_stops_visible_partial_effects(self):
        from bridge_live import plan_switching_layout,execute_switching_layout
        p=plan_switching_layout(self.switching_brief());calls=[]
        def request(op,q):
            calls.append(op)
            if op=='discover':v={'complete':True,'candidates':[{'edge_id':800,'edge_snapshot':{'template':'t','style':'s'}}]}
            elif op=='inspect' and q.get('resources'):v={'edges':[{'resource':{'track_distance':5}}]}
            elif op=='test_approach':
                f=q['fixture'];chord=[20*x for x in f['travel_direction']]+[0];v={'game_constructed':True,'edges':[{'id':801,'road_type':'TRACK','p0':f['position'],'p1':[f['position'][k]+chord[k] for k in range(3)],'t1':chord}]}
            else:v={'edges':[{'p0':[0,0,33],'p1':[600,0,33],'t0':[600,0,0],'t1':[600,0,0]}]}
            return self.response('r'+str(len(calls)),op,result=v)
        def throat(client,b,**opts):
            path=self.root/(str(len(calls))+'_built.json');path.write_text(json.dumps({'brief':b}));return {'status':'ok','game_constructed':True,'evidence':str(path)}
        with patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True,'edges':[801]}) as corridor,patch('bridge_live.connect_throat',side_effect=throat) as cross,patch('bridge_live._verify_switching_layout',return_value={'routes_verified':8,'transfers_verified':2,'final_network_verified':True}):
            result=execute_switching_layout(self.client,p);self.assertEqual(result['status'],'ok');self.assertEqual(corridor.call_count,4);self.assertEqual(cross.call_count,2);self.assertEqual(calls.count('test_approach'),10)
        with patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'mutation_unverified','game_constructed':'unknown','error':'lost acknowledgement'}) as corridor,patch('bridge_live.connect_throat') as cross:
            result=execute_switching_layout(self.client,p);self.assertEqual(result['status'],'mutation_unverified');self.assertEqual(result['game_constructed'],'unknown');corridor.assert_called_once();cross.assert_not_called()
        self.assertFalse((self.client.evidence/'switching.lock').exists())

    def test_switching_fresh_routes_require_exact_connectors_and_both_junctions(self):
        from bridge_live import plan_switching_layout,_verify_switching_layout
        b=self.switching_brief();b['route_reference']['heading_deg']=0;b['region']={'min':[-10000,-10000,0],'max':[10000,10000,80]};p=plan_switching_layout(b)
        runtime,briefs=self.switching_runtime(p);ports={name:({'edge_id':100+i,'node_id':200+i},v) for i,(name,v) in enumerate(p['ports'].items())}
        junctions={}
        for index,label in enumerate(('up','down')):
            for i,pos in enumerate((briefs[label]['steps'][0]['source'],briefs[label]['steps'][0]['target'],briefs[label]['steps'][1]['source'])):junctions[tuple(pos['guide_xyz'])]=500+index*3+i
        def select(client,intent,**opts):
            if opts.get('interior'):
                i=round((intent['guide_xyz'][1]-b['route_reference']['origin'][1])/5);o=b['route_reference']['origin'];y=o[1]+5*i
                return {'edge_id':800+i,'edge_snapshot':{'id':800+i,'p0':[o[0],y,o[2]],'p1':[o[0]+400,y,o[2]],'t0':[400,0,0],'t1':[400,0,0]}},'spacing'
            for name,(c,v) in ports.items():
                if v['position']==intent['guide_xyz']:
                    self.assertEqual(intent['travel_direction'],v['construction_direction']);return c,'port'
            raise AssertionError(intent)
        requests=[]
        def request(op,q):
            if op=='inspect':return self.response('connector',op,result={'edges':[{'id':i,'road_type':'TRACK'} for i in q['edge_ids']]})
            requests.append(q);return self.response('route',op,result={'requested_route_verified':True,'path':[{'from':{'entity':i},'to':{'entity':i}} for i in junctions.values()]})
        record={'pair_runtime':runtime,'summary':{'evidence':str(self.root/'verified.json')}}
        with patch('bridge_live._select_throat_port',side_effect=select),patch('bridge_live._recipe_junction',side_effect=lambda c,i:(junctions[tuple(i['guide_xyz'])],['junction'])),patch.object(self.client,'request',side_effect=request):
            result=_verify_switching_layout(self.client,p,record)
            self.assertEqual(result['routes_verified'],8);self.assertEqual(result['transfers_verified'],2)
            self.assertIn(900,requests[-2]['required_edges']);self.assertIn(901,requests[-1]['required_edges'])
            self.assertEqual(requests[-1]['source_node'],ports['D2:east'][0]['node_id']);self.assertEqual(requests[-1]['target_node'],ports['D1:west'][0]['node_id'])
            def bypass(op,q):
                if op=='inspect':return request(op,q)
                return self.response('bypass',op,result={'requested_route_verified':True,'path':[{'from':{'entity':i},'to':{'entity':i}} for i in (502,505)]})
            with patch.object(self.client,'request',side_effect=bypass):
                with self.assertRaises(LiveError):_verify_switching_layout(self.client,p,record)
            with patch.object(self.client,'request',return_value=self.response('stale','inspect',result={'edges':[]})):
                with self.assertRaises(LiveError) as exc:_verify_switching_layout(self.client,p,record)
                self.assertEqual(exc.exception.status,'stale_switching_connector')
        # Changed native-receipt evidence cannot silently authorise another connection.
        Path(runtime['up']['throat_record']).write_text('{}')
        with patch.object(self.client,'request') as native:
            with self.assertRaises(ValueError):_verify_switching_layout(self.client,p,record)
            native.assert_not_called()

    def test_switching_pending_and_incomplete_inspection_do_not_construct(self):
        from bridge_live import plan_switching_layout,execute_switching_layout,inspect_switching_layout
        p=plan_switching_layout(self.switching_brief());self.client.journal.write_text(json.dumps({'pending':{'request_id':'old'}}))
        record=self.root/'incomplete.json';record.write_text(json.dumps({'plan':p,'pair_runtime':{}}))
        with patch.object(self.client,'request') as native:
            r=execute_switching_layout(self.client,p);self.assertEqual(r['status'],'reconciliation_required');self.assertFalse(r['game_constructed'])
            r=inspect_switching_layout(self.client,record);self.assertEqual(r['status'],'incomplete_layout');self.assertFalse(r['game_constructed']);native.assert_not_called()

    def test_switching_explicit_prepared_reuse_requires_fresh_exact_fixtures(self):
        from bridge_live import plan_switching_layout,execute_switching_layout
        p=plan_switching_layout(self.switching_brief());fixtures=[{'id':700+i,'road_type':'TRACK'} for i in range(5)]
        ops=[{'name':n,'response':{'status':'ok'}} for n in ('discover_asset','inspect_asset')]
        ops += [{'name':'up_prepare_'+f['name'],'response':{'status':'ok','result':{'edges':[e]}}} for f,e in zip(p['pairs'][0]['fixtures'],fixtures)]
        ops += [{'name':'up_reference','response':{'status':'no_accepted_candidate','game_constructed':False}}]
        record=self.root/'prepared.json';record.write_text(json.dumps({'plan':p,'operations':ops}))
        def request(op,q):
            if op=='inspect':return self.response('fresh',op,result={'edges':fixtures})
            if op=='discover':return self.response('asset',op,result={'complete':True,'candidates':[]})
            raise AssertionError('no fixtures/build may be repeated')
        with patch.object(self.client,'request',side_effect=request) as native:
            r=execute_switching_layout(self.client,p,prepared_record=record);self.assertEqual(r['status'],'asset_unavailable');self.assertEqual(native.call_count,2)
        with patch.object(self.client,'request',return_value=self.response('changed','inspect',result={'edges':[]})) as native:
            r=execute_switching_layout(self.client,p,prepared_record=record);self.assertEqual(r['status'],'stale_prepared_layout');self.assertFalse(r['game_constructed']);native.assert_called_once()
        ops[-1]['response']['game_constructed']='unknown';record.write_text(json.dumps({'plan':p,'operations':ops}))
        with patch.object(self.client,'request') as native:
            with self.assertRaises(ValueError):execute_switching_layout(self.client,p,prepared_record=record)
            native.assert_not_called()
        pair=p['pairs'][0];last=pair['reference']['guides'][-1];end=pair['reference']['target']['guide_xyz'];d=last['travel_direction'];delta=[end[k]-last['position'][k] for k in range(2)]
        self.assertAlmostEqual(delta[0]*d[1]-delta[1]*d[0],0,places=8);self.assertEqual(pair['reference']['radius'],160)

    def test_switching_native_straight_guide_preserves_existing_tolerances(self):
        from bridge_live import plan_switching_layout,_switching_fanout
        p=plan_switching_layout(self.switching_brief());pair=p['pairs'][1];f=pair['fixtures'][1];d=f['travel_direction']
        e={'p0':f['position'],'p1':[f['position'][k]+20*(d[k] if k<2 else 0) for k in range(3)],'t1':[20*d[0],20*d[1],0]}
        actual=_switching_fanout(pair,{'A2':e});self.assertEqual(actual['radius'],120);self.assertEqual(actual['region'],p['brief']['region'])
        self.assertLess(sum((actual['guides'][0]['position'][k]-pair['fanout']['guides'][0]['position'][k])**2 for k in range(3)),1e-6)
        e['p1'][0]+=1
        with self.assertRaises(LiveError):_switching_fanout(pair,{'A2':e})

    def test_switching_missing_down_stage_continues_only_after_exact_readback(self):
        from bridge_live import plan_switching_layout,continue_switching_layout
        p=plan_switching_layout(self.switching_brief());pair=p['pairs'][1];runtime,briefs=self.switching_runtime(p)
        fixtures=[{'id':710+i,'road_type':'TRACK','p0':f['position'],'p1':[f['position'][k]+20*(f['travel_direction'][k] if k<2 else 0) for k in range(3)],'t1':[20*f['travel_direction'][0],20*f['travel_direction'][1],0]} for i,f in enumerate(pair['fixtures'])]
        ops=[{'name':'down_prepare_'+f['name'],'response':{'status':'ok','result':{'edges':[e]}}} for f,e in zip(pair['fixtures'],fixtures)]
        ops += [{'name':'down_reference','response':{'status':'ok','game_constructed':True}},{'name':'down_fanout','response':{'status':'no_accepted_candidate','game_constructed':False}}]
        source=self.root/'partial_switching.json';record={'plan':p,'summary':{'stage':'down_fanout'},'pair_runtime':{'up':runtime['up']},'operations':ops};source.write_text(json.dumps(record))
        self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch.object(self.client,'request') as native:
            r=continue_switching_layout(self.client,source);self.assertEqual(r['status'],'reconciliation_required');native.assert_not_called()
        self.client.journal.write_text(json.dumps({'pending':None}))
        with patch.object(self.client,'request',return_value=self.response('changed','inspect',result={'edges':[]})),patch('bridge_live.connect_corridor') as build:
            r=continue_switching_layout(self.client,source);self.assertEqual(r['status'],'stale_prepared_layout');build.assert_not_called()
        count=[]
        def request(op,q):
            count.append(op)
            if op=='route':v={'requested_route_verified':True}
            elif q['edge_ids']==[e['id'] for e in fixtures]:v={'edges':fixtures}
            else:v={'edges':[{'p0':[0,0,33],'p1':[600,0,33],'t0':[600,0,0],'t1':[600,0,0]}]}
            return self.response('read',op,result=v)
        def built(client,b,**opts):
            out=self.root/'down_built.json';out.write_text(json.dumps({'brief':b}));return {'status':'ok','game_constructed':True,'evidence':str(out)}
        with patch.object(self.client,'request',side_effect=request),patch('bridge_live._select_throat_port',side_effect=[({'edge_id':1,'node_id':2},'a'),({'edge_id':3,'node_id':4},'b')]),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True,'edges':[999]}) as fan,patch('bridge_live.connect_throat',side_effect=built) as throat,patch('bridge_live._verify_switching_layout',return_value={'routes_verified':8,'transfers_verified':2}):
            r=continue_switching_layout(self.client,source);self.assertEqual(r['status'],'ok');self.assertTrue(r['game_constructed']);fan.assert_called_once();throat.assert_called_once();self.assertNotIn('test_approach',count)
        record['operations'][-1]['response']['game_constructed']='unknown';source.write_text(json.dumps(record))
        with patch.object(self.client,'request') as native:
            with self.assertRaises(ValueError):continue_switching_layout(self.client,source)
            native.assert_not_called()

    def test_switching_malformed_records_fail_before_native_calls(self):
        from bridge_live import inspect_switching_layout,continue_switching_layout
        record=self.root/'malformed.json';record.write_text('[]')
        with patch.object(self.client,'request') as native:
            for method in (inspect_switching_layout,continue_switching_layout):
                with self.assertRaises(ValueError):method(self.client,record)
            native.assert_not_called()

    def reciprocal_brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/reciprocal_layout_example.json').read_text())

    def test_reciprocal_plan_retains_base_hash_and_ten_explicit_movements(self):
        from bridge_live import plan_reciprocal_layout,plan_switching_layout
        b=self.reciprocal_brief();p=plan_reciprocal_layout(b)
        self.assertEqual(p['base_plan'],plan_switching_layout(self.switching_brief()))
        self.assertEqual(p['base_plan']['plan_hash'],'c74d45bb11c00ef720bfa0296af3e4e0025b707774f05b5c2501685dc6d896a2')
        self.assertEqual(len(p['movements']),10);self.assertEqual(p['returns'][1]['transfer'],{'from':'D1:east','to':'D2:west'})
        self.assertEqual(p,plan_reciprocal_layout(b));self.assertFalse(p['game_constructed'])
        b['route_reference']['heading_deg']=90;b['region']={'min':[-10000,-10000,0],'max':[10000,10000,80]};r=plan_reciprocal_layout(b)
        for m in r['returns']:
            self.assertAlmostEqual(m['source']['guide_xyz'][1]-b['route_reference']['origin'][1],750)
            self.assertAlmostEqual(m['fixture']['position'][1]-b['route_reference']['origin'][1],1200)
        for change in ('missing','duplicate','opposite','grade','region'):
            bad=self.reciprocal_brief()
            if change=='missing':bad['movements'].pop()
            elif change=='duplicate':bad['movements'][-1]=bad['movements'][-2]
            elif change=='opposite':bad['movements'][-1]={'from':'U1:west','to':'D1:east'}
            elif change=='grade':bad['route_reference']['origin'][2]=90
            else:bad['region']['max'][0]=4000
            with self.subTest(change=change),self.assertRaises((ValueError,LiveError)):plan_reciprocal_layout(bad)

    def test_reciprocal_offline_cli_never_creates_native_client(self):
        path=self.root/'brief.json';path.write_text(json.dumps(self.reciprocal_brief()));out=io.StringIO()
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(out):
            code=main(['reciprocal-layout','--params',str(path),'--evidence',str(self.root/'plans')])
            self.assertEqual(code,0);native.assert_not_called()
        self.assertLess(len(out.getvalue().encode()),4096);self.assertFalse(json.loads(out.getvalue())['game_constructed'])

    def test_single_crossover_reuses_throat_contract_without_adding_branch(self):
        b=self.throat_brief();b['roles'].pop('D3');b['steps']=b['steps'][:1]
        b['required_routes']=[{'from':'A1','to':'D1','via':[]},{'from':'A2','to':'D2','via':[]},{'from':'A1','to':'D2','via':['cross']}]
        validate_throat_brief(b);calls=[]
        def request(op,q):
            calls.append((op,q));v={'requested_route_verified':True}
            if op=='crossover':v={'readback':{'connected':True,'ordered_edges':[81]},'placements':[{'original_removed':True,'subdivision_sampled_verified':True}]*2,
                'through_after':[{'requested_route_verified':True}]*2,'crossover_after':{'requested_route_verified':True},'junction_nodes':[91,92]}
            return self.response('single',op,result=v)
        with patch('bridge_live._select_throat_port',return_value=({'edge_id':1,'node_id':2},'port')),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_junction_at') as branch:
            r=connect_throat(self.client,b,execute=True);self.assertEqual(r['routes_verified'],3);branch.assert_not_called()
        self.assertIn(81,calls[-1][1]['required_edges']);self.assertEqual(len(calls),4)
        b['steps'][0]['kind']='branch'
        with self.assertRaises(ValueError):validate_throat_brief(b)

    def test_return_target_is_on_exact_verified_reference_and_rejects_curved_or_missing_segment(self):
        from bridge_live import plan_reciprocal_layout,_return_target
        b=self.reciprocal_brief();b['route_reference']['heading_deg']=0;b['region']={'min':[-10000,-10000,0],'max':[10000,10000,80]};p=plan_reciprocal_layout(b);m=p['returns'][0];o=b['route_reference']['origin']
        edge={'id':71,'road_type':'TRACK','p0':[o[0]+800,o[1]-80,33],'p1':[o[0]+1200,o[1]-120,33],'t0':[400,-40,0],'t1':[400,-40,0]}
        proof={'routes':[{'from':'U2:west','to':'U2:east','verified':True,'response':{'result':{'path':[{'confirmed_TRACK':True,'edge':{'entity':71}}]}}}]}
        with patch.object(self.client,'request',return_value=self.response('current',result={'edges':[edge]})) as read:
            target,ids=_return_target(self.client,p,m,proof);self.assertEqual(read.call_args.args[1]['edge_ids'],[71]);self.assertEqual(target['guide_xyz'],[o[0]+1000,o[1]-100,33]);self.assertEqual(ids,['current'])
            edge['t1']=[400,30,0]
            with self.assertRaises(LiveError):_return_target(self.client,p,m,proof)

    def test_reciprocal_reuses_fresh_base_then_stops_partial_without_replay(self):
        import hashlib
        from bridge_live import plan_reciprocal_layout,execute_reciprocal_layout
        p=plan_reciprocal_layout(self.reciprocal_brief());base=self.root/'base.json';base.write_text(json.dumps({'plan':p['base_plan'],'summary':{'status':'ok'},'pair_runtime':{}}));calls=[]
        def verify(c,plan,record):record['current_ports']={m['fan']+':east':{'edge_id':71+i} for i,m in enumerate(p['returns'])};return {'routes_verified':8}
        def request(op,q):calls.append(op);return self.response('fixture',op,result={'game_constructed':True,'edges':[{'id':99,'road_type':'TRACK'}]})
        def throat(c,b,**kw):
            path=self.root/('return_'+str(len(calls))+'.json');path.write_text(json.dumps({'brief':b}));calls.append('cross');return {'status':'ok','game_constructed':True,'evidence':str(path)}
        with patch('bridge_live._verify_switching_layout',side_effect=verify),patch('bridge_live._return_target',return_value=(p['returns'][0]['source'],['target'])),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_brief',return_value={'status':'ok','game_constructed':True}) as extend,patch('bridge_live.connect_throat',side_effect=throat),patch('bridge_live._verify_reciprocal_layout',return_value={'routes_verified':10,'transfers_verified':4}):
            r=execute_reciprocal_layout(self.client,p,base_layout_record=base);self.assertEqual(r['status'],'ok');self.assertEqual(extend.call_count,2);self.assertEqual(calls,['test_approach','cross','test_approach','cross']);self.assertTrue(r['game_constructed'])
            calls.clear();extend.side_effect=[{'status':'ok','game_constructed':True},{'status':'no_accepted_candidate','game_constructed':False}]
            r=execute_reciprocal_layout(self.client,p,base_layout_record=base);self.assertEqual(r['status'],'no_accepted_candidate');self.assertTrue(r['game_constructed']);self.assertEqual(calls,['test_approach','cross','test_approach']);self.assertEqual(len(json.loads(Path(r['evidence']).read_text())['return_runtime']),1)
        self.assertFalse((self.client.evidence/'reciprocal.lock').exists())
        base.write_text(json.dumps({'plan':p['base_plan'],'summary':{'status':'ok'},'pair_runtime':{},'unfinished_step':'unknown'}))
        with patch.object(self.client,'request') as native,self.assertRaises(ValueError):execute_reciprocal_layout(self.client,p,base_layout_record=base)
        native.assert_not_called()
        base.write_text('{}')
        with patch('bridge_live.execute_switching_layout') as create,self.assertRaises(ValueError):execute_reciprocal_layout(self.client,p,base_layout_record=base)
        create.assert_not_called()

    def test_reciprocal_new_base_and_unknown_mutation_stop_before_later_stages(self):
        from bridge_live import plan_reciprocal_layout,execute_reciprocal_layout
        p=plan_reciprocal_layout(self.reciprocal_brief())
        with patch('bridge_live.execute_switching_layout',return_value={'status':'no_accepted_candidate','game_constructed':True}) as base,patch.object(self.client,'request') as native:
            r=execute_reciprocal_layout(self.client,p);self.assertEqual(r['stage'],'base_build');self.assertEqual(r['status'],'no_accepted_candidate');self.assertTrue(r['game_constructed']);base.assert_called_once_with(self.client,p['base_plan']);native.assert_not_called()
        saved=self.root/'base.json';saved.write_text(json.dumps({'plan':p['base_plan'],'summary':{'status':'ok'},'pair_runtime':{}}))
        def verify(c,plan,record):record['current_ports']={m['fan']+':east':{'edge_id':71+i} for i,m in enumerate(p['returns'])}
        with patch('bridge_live._verify_switching_layout',side_effect=verify),patch('bridge_live._return_target',return_value=(p['returns'][0]['source'],[])),patch.object(self.client,'request',side_effect=LiveError('mutation_outcome_unknown','lost acknowledgement')) as native,patch('bridge_live.connect_brief') as extend:
            r=execute_reciprocal_layout(self.client,p,base_layout_record=saved);self.assertEqual(r['status'],'mutation_outcome_unknown');self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(json.loads(Path(r['evidence']).read_text())['unfinished_step'],'up_return_fixture');native.assert_called_once();extend.assert_not_called()

    def test_reciprocal_pending_incomplete_inspection_and_stale_base_never_build(self):
        from bridge_live import plan_reciprocal_layout,execute_reciprocal_layout,inspect_reciprocal_layout
        p=plan_reciprocal_layout(self.reciprocal_brief());saved=self.root/'incomplete.json';saved.write_text(json.dumps({'plan':p,'summary':{'status':'incomplete'}}))
        self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch.object(self.client,'request') as native,patch('bridge_live.execute_switching_layout') as base:
            r=execute_reciprocal_layout(self.client,p);self.assertEqual(r['status'],'reconciliation_required');base.assert_not_called()
            r=inspect_reciprocal_layout(self.client,saved);self.assertEqual(r['status'],'incomplete_layout');native.assert_not_called();self.assertFalse(r['game_constructed'])
        self.client.journal.write_text('{}');saved.write_text(json.dumps({'plan':p['base_plan'],'summary':{'status':'ok'},'pair_runtime':{}}))
        with patch('bridge_live._verify_switching_layout',side_effect=LiveError('stale_switching_connector','gone')),patch.object(self.client,'request') as native:
            r=execute_reciprocal_layout(self.client,p,base_layout_record=saved);self.assertEqual(r['status'],'stale_switching_connector');self.assertFalse(r['game_constructed']);native.assert_not_called()

    def test_reciprocal_verification_requires_all_four_connector_paths_and_ten_junctions(self):
        import hashlib
        from bridge_live import plan_reciprocal_layout,_verify_reciprocal_layout,_return_throat
        p=plan_reciprocal_layout(self.reciprocal_brief());runtime,briefs=self.switching_runtime(p);record={'pair_runtime':runtime,'return_runtime':{},'summary':{'evidence':str(self.root/'verify10.json')}}
        for index,m in enumerate(p['returns']):
            d=p['native_construction_direction'];o=p['brief']['route_reference']['origin'];target=m['source']|{'guide_xyz':[o[k]+1000*(d[k] if k<2 else 0) for k in range(3)]}
            b=_return_throat(p,m,target);path=self.root/(m['name']+'.json');path.write_text(json.dumps({'brief':b,'summary':{'status':'ok'},'semantic_mapping':{'step_edges':{'return':[950+index]}}}))
            record['return_runtime'][m['name']]={'throat_record':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        def inspect(op,q):return self.response('connector',op,result={'edges':[{'id':i,'road_type':'TRACK'} for i in q['edge_ids']]})
        def verify(c,v,r,**kw):
            self.assertEqual(len(v['branches']),10);self.assertEqual(len(kw['movement_edges']),4)
            self.assertEqual(kw['movement_edges'][('U1:west','U2:east')],[950]);self.assertEqual(kw['movement_edges'][('D1:east','D2:west')],[951])
            for row in v['movements'][-4:]:self.assertEqual(len(row['via']),2)
            self.assertEqual(v['movements'][0]['via'],['up_cross_target','branch_up','up_return_source'])
            self.assertEqual(v['movements'][2]['via'],['down_cross_source','down_return_target'])
            self.assertEqual(v['ports']['D2:east']['running_direction'],'DOWN');return {'routes_verified':10}
        with patch.object(self.client,'request',side_effect=inspect),patch('bridge_live._verify_parallel_layout',side_effect=verify):
            result=_verify_reciprocal_layout(self.client,p,record);self.assertEqual(result['transfers_verified'],4)
            with patch.object(self.client,'request',return_value=self.response('stale',result={'edges':[]})),self.assertRaises(LiveError):_verify_reciprocal_layout(self.client,p,record)
        Path(record['return_runtime']['up_return']['throat_record']).write_text('{}')
        with patch.object(self.client,'request',side_effect=inspect),self.assertRaises(ValueError):_verify_reciprocal_layout(self.client,p,record)

    def test_partial_reciprocal_reports_current_verified_movements_without_fabricated_completion(self):
        from bridge_live import plan_reciprocal_layout,_reciprocal_outcome,_reciprocal_partial
        p=plan_reciprocal_layout(self.reciprocal_brief());original={'plan':p,'pair_runtime':{'up':{},'down':{}},'return_runtime':{},'operations':[]};record={'summary':{'evidence':str(self.root/'partial.json')}}
        def verified(c,current,record,**kw):
            self.assertTrue(kw['partial']);self.assertEqual(current['ports']['U1:east'],p['base_plan']['ports']['U1:east'])
            record['routes']=[r|{'verified':True} for r in current['movements'][:8]];return {'routes_verified':8,'transfers_verified':2,'final_network_verified':True}
        with patch('bridge_live.discover',return_value=self.response('empty',result={'complete':True,'edge_count':0})),patch('bridge_live._select_throat_port',side_effect=LiveError('no_eligible_candidates','missing target')),patch('bridge_live._verify_reciprocal_layout',side_effect=verified):
            result=_reciprocal_partial(self.client,original,record);self.assertEqual(result['status'],'layout_incomplete');self.assertFalse(result['final_network_verified']);self.assertEqual(result['routes_verified'],8)
            self.assertEqual(record['stage_assessment']['up_return_fixture']['state'],'absent')
        summary=result|{'game_constructed':False};_reciprocal_outcome(p,record,summary)
        self.assertEqual([r['state'] for r in summary['movement_results']],['verified']*8+['unverified']*2);self.assertLess(len(json.dumps(summary).encode()),4096)

    def test_reciprocal_explicit_continuation_skips_completed_stages_and_never_rebuilds_base(self):
        from bridge_live import plan_reciprocal_layout,execute_reciprocal_layout,_load_layout_record
        p=plan_reciprocal_layout(self.reciprocal_brief());original={'plan':p,'summary':{'status':'no_accepted_candidate'},'pair_runtime':{'up':{},'down':{}},'return_runtime':{'up_return':{'retained':True}},'operations':[{'name':'down_return_fixture','response':{'status':'ok','result':{'game_constructed':True}}},{'name':'down_return_extension','response':{'status':'no_accepted_candidate','game_constructed':False}}]}
        path=self.root/'run.json';path.write_text(json.dumps(original));assessment={'plan':p,'summary':{'status':'layout_incomplete'},'stage_assessment':{'down_return_fixture':{'state':'completed'},'down_return_extension':{'state':'absent'},'down_return_crossover':{'state':'absent'}},'current_ports':{'U1:east':{'edge_id':71},'D2:east':{'edge_id':72}},'routes':[]}
        checked=self.root/'inspection.json';checked.write_text(json.dumps(assessment));made=self.root/'return.json';made.write_text('{}')
        with patch('bridge_live.inspect_reciprocal_layout',return_value={'status':'layout_incomplete','evidence':str(checked)}),patch('bridge_live._return_target',return_value=(p['returns'][1]['source'],[])),patch('bridge_live.execute_switching_layout') as base,patch.object(self.client,'request') as native,patch('bridge_live.connect_brief',return_value={'status':'ok','game_constructed':True}) as extension,patch('bridge_live.connect_throat',return_value={'status':'ok','game_constructed':True,'evidence':str(made)}) as crossover,patch('bridge_live._verify_reciprocal_layout',return_value={'routes_verified':10,'transfers_verified':4}):
            before=path.read_bytes();result=execute_reciprocal_layout(self.client,p,continuation_record=path)
            self.assertEqual(result['status'],'ok');base.assert_not_called();native.assert_not_called();extension.assert_called_once();crossover.assert_called_once();self.assertEqual(path.read_bytes(),before)
        original['unfinished_step']='down_return_extension';path.write_text(json.dumps(original))
        with patch('bridge_live.inspect_reciprocal_layout') as inspect,patch('bridge_live.connect_brief') as build:
            r=execute_reciprocal_layout(self.client,p,continuation_record=path);self.assertEqual(r['status'],'reconciliation_required');inspect.assert_not_called();build.assert_not_called()
        path.write_text('{}')
        with patch('bridge_live.execute_switching_layout') as base,self.assertRaises(ValueError):execute_reciprocal_layout(self.client,p,continuation_record=path)
        base.assert_not_called()

    def test_reciprocal_completed_continuation_is_read_only_and_receipt_remains_inspectable(self):
        from bridge_live import plan_reciprocal_layout,execute_reciprocal_layout
        p=plan_reciprocal_layout(self.reciprocal_brief());old={'plan':p,'summary':{'status':'ok'},'operations':[],'pair_runtime':{'up':{},'down':{}},'return_runtime':{'up_return':{},'down_return':{}}};path=self.root/'done.json';path.write_text(json.dumps(old))
        checked=self.root/'inspection.json';checked.write_text(json.dumps(old|{'routes':[r|{'verified':True} for r in p['movements']]}))
        with patch('bridge_live.inspect_reciprocal_layout',return_value={'status':'ok','game_constructed':False,'routes_verified':10,'evidence':str(checked)}),patch('bridge_live.execute_switching_layout') as base,patch.object(self.client,'request') as native:
            result=execute_reciprocal_layout(self.client,p,continuation_record=path);self.assertEqual(result['status'],'ok');self.assertFalse(result['game_constructed']);self.assertEqual(result['next_action'],'none');self.assertEqual(len(json.loads(Path(result['evidence']).read_text())['return_runtime']),2);base.assert_not_called();native.assert_not_called()

    def test_reciprocal_partial_base_inspection_uses_current_recipe_observations_only(self):
        from bridge_live import plan_reciprocal_layout,_reciprocal_partial
        p=plan_reciprocal_layout(self.reciprocal_brief());child=self.root/'base.json';child.write_text(json.dumps({'plan':p['base_plan'],'summary':{'stage':'up_reference'},'operations':[]}))
        original={'plan':p,'operations':[{'name':'base_build','response':{'status':'no_accepted_candidate','game_constructed':True,'evidence':str(child)}}]};record={}
        with patch('bridge_live._switching_recipe_assessment',return_value={'roles':{},'steps':{'reference':{'state':'absent'}},'blockers':[]}) as assess,patch.object(self.client,'request') as native:
            r=_reciprocal_partial(self.client,original,record);self.assertEqual(r['status'],'layout_incomplete');self.assertEqual(r['routes_verified'],0);self.assertEqual(assess.call_count,2);self.assertIn('up',record['base_assessment']);native.assert_not_called()
        with patch('bridge_live._switching_recipe_assessment',return_value={'roles':{},'steps':{'cross':{'state':'completed'}},'blockers':[]}):
            r=_reciprocal_partial(self.client,original,{});self.assertEqual(r['next_action'],'reconcile_partial_throat')
        child.write_text('{}')
        with self.assertRaises(ValueError):_reciprocal_partial(self.client,original,record)

    def test_explicit_endpoint_tolerance_excludes_nearby_parallel_asset(self):
        intent=self.throat_brief()['roles']['A1']['endpoint']
        candidate={'eligible':True,'outward_direction':[1,0],'pos':[intent['guide_xyz'][0],5,0],'edge_id':71}
        with patch('bridge_live.discover',return_value=self.response('nearby',result={'complete':True,'candidates':[candidate]})):
            found,rid=_select_throat_port(self.client,intent);self.assertEqual(found['edge_id'],71)
            with self.assertRaises(LiveError):_select_throat_port(self.client,intent,tolerance=.5)

    def test_switching_continuation_reuses_exact_fixtures_and_blocks_unresolved_mutation(self):
        from bridge_live import plan_switching_layout,execute_switching_layout
        p=plan_switching_layout(self.switching_brief());fixtures=[]
        for i,f in enumerate(p['pairs'][0]['fixtures'][:2]):
            fixtures.append({'id':71+i,'road_type':'TRACK','p0':f['position'],'p1':[f['position'][k]+20*(f['travel_direction'][k] if k<2 else 0) for k in range(3)],'t0':[20*f['travel_direction'][0],20*f['travel_direction'][1],0],'t1':[20*f['travel_direction'][0],20*f['travel_direction'][1],0]})
        old={'plan':p,'operations':[{'name':'up_prepare_'+f['name'],'response':{'status':'ok','result':{'edges':[e]}}} for f,e in zip(p['pairs'][0]['fixtures'],fixtures)]};path=self.root/'partial_base.json';path.write_text(json.dumps(old))
        def state(c,plan,pair,record):
            roles={f['name']:{'edge_snapshot':e} for f,e in zip(pair['fixtures'],fixtures)} if pair['name']=='up' else {}
            return {'roles':roles,'observations':['current'],'steps':{'prepare_'+f['name']:{'state':'completed' if f['name'] in roles else 'absent'} for f in pair['fixtures']}}
        calls=[]
        def request(op,q):
            calls.append((op,q))
            if op=='discover':return self.response('asset',op,result={'complete':True,'candidates':[{'edge_id':99,'edge_snapshot':{'template':'same','style':'same'}}]})
            if op=='inspect':return self.response('resource',op,result={'edges':[{'resource':{'track_distance':5}}]})
            self.assertEqual(op,'test_approach');self.assertEqual(q['fixture']['position'],p['pairs'][0]['fixtures'][2]['position'])
            return self.response('rejected',op,result={'game_constructed':False,'error':'not accepted'})|{'status':'no_accepted_candidate'}
        with patch('bridge_live._switching_recipe_assessment',side_effect=state),patch.object(self.client,'request',side_effect=request):
            before=path.read_bytes();r=execute_switching_layout(self.client,p,current_run=path);self.assertEqual(r['stage'],'up_prepare_D1');self.assertEqual(r['status'],'no_accepted_candidate');self.assertFalse(r['game_constructed']);self.assertEqual(path.read_bytes(),before);self.assertEqual([op for op,q in calls].count('test_approach'),1)
        old['operations'].append({'name':'up_prepare_D1','response':{'status':'mutation_unverified','result':{'game_constructed':'unknown'}}});path.write_text(json.dumps(old))
        with patch.object(self.client,'request') as native:
            r=execute_switching_layout(self.client,p,current_run=path);self.assertEqual(r['status'],'reconciliation_required');native.assert_not_called()

    def test_fixture_reconciliation_is_linked_to_exact_failed_request_and_keeps_unknown_other_effects(self):
        from bridge_live import _layout_uncertain_operations
        original={'operations':[{'name':'up_prepare_D1','response':{'status':'mutation_unverified','request_id':'failed','result':{'game_constructed':'unknown'}}}]}
        self.assertEqual(_layout_uncertain_operations(self.client,original),['up_prepare_D1'])
        record=self.client.evidence/'failed.reconciliation.json';record.write_text(json.dumps({'status':'reconciled_failed_fixture','original_pending':{'request_id':'failed'},'intended_fixture_constructed':False,'other_effects':'unknown','automatic_replay':False}))
        self.assertEqual(_layout_uncertain_operations(self.client,original),[])
        original['unfinished_step']='up_prepare_D1';self.assertEqual(_layout_uncertain_operations(self.client,original),['unfinished_up_prepare_D1'])

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

class NetworkTests(unittest.TestCase):
    setUp = LiveClientTests.setUp
    response = LiveClientTests.response

    def brief(self):
        from bridge_live import plan_parallel_layout
        from bridge_network import LAYOUT
        base = json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/ud_layout_example.json').read_text())
        base['route_reference']['up']='increasing'
        base['movements']=[{'from':'U1:west','to':'U1:east'},{'from':'D1:east','to':'D1:west'},{'from':'U1:west','to':'branch_up'},{'from':'branch_down','to':'D1:west'}]
        records={}
        for i,name in enumerate(('first','second')):
            b=json.loads(json.dumps(base));b['route_reference']['origin']=[i*2000,0,33];b['region']={'min':[-2000,-2000,0],'max':[5000,5000,80]}
            plan=plan_parallel_layout(b);path=self.root/(name+'.json');path.write_text(json.dumps({'plan':plan,'summary':{'status':'ok'}}));records[name]=str(path)
        return {'layout':LAYOUT,'parents':records,'links':[{'direction':'UP','source':{'layout':'first','port':'branch_up'},'target':{'layout':'second','port':'U1:west'},'guides':[{'position':[1500,0,33],'travel_direction':[1,0],'grade':0}]},{'direction':'DOWN','source':{'layout':'second','port':'D1:west'},'target':{'layout':'first','port':'branch_down'},'guides':[{'position':[1500,300,33],'travel_direction':[-1,0],'grade':0}]}],'movements':[{'direction':'UP','source':{'layout':'first','port':'U1:west'},'target':{'layout':'second','port':'U1:east'}},{'direction':'DOWN','source':{'layout':'second','port':'D1:east'},'target':{'layout':'first','port':'D1:west'}}],'radius':120,'max_grade':.04,'region':{'min':[-500,-500,0],'max':[2500,1500,80]},'max_connection_length':4000,'max_route_length':6000,'min_sampled_link_separation':4}

    def test_network_plan_deterministic_explicit_directions_and_no_native_client(self):
        from bridge_network import plan_layout_network
        b=self.brief();b['movements'][1]['target']['port']='D1:west'
        p=plan_layout_network(b);self.assertEqual(p,plan_layout_network(b));self.assertFalse(p['game_constructed'])
        path=self.root/'network.json';path.write_text(json.dumps(b));out=io.StringIO()
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(out):
            self.assertEqual(main(['layout-network','--params',str(path),'--evidence',str(self.root/'plans')]),0);native.assert_not_called()
        self.assertLess(len(out.getvalue().encode()),4096)
        for mutation in ('direction','bound','guide','parent'):
            bad=json.loads(json.dumps(b))
            if mutation=='direction':bad['links'][0]['target']['port']='D1:west'
            elif mutation=='bound':bad['max_route_length']=8001
            elif mutation=='guide':bad['links'][0]['guides'][0]['grade']=.1
            else:bad['parents']['second']=bad['parents']['first']
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,LiveError,KeyError)):plan_layout_network(bad)

    def test_attached_role_is_read_only_exact_two_track_incidence(self):
        intent={'region':{'min':[0,0,0],'max':[2,2,2]},'max_edges':8,'guide_xyz':[1,1,1],'travel_direction':[1,0],'heading_tolerance_deg':2}
        c={'eligible':False,'incident_count':2,'incidence_complete':True,'incident_output_truncated':False,'incident_edges':[10,11],'construction_owner':'none','outward_direction':[1,0],'pos':[1,1,1],'edge_id':10,'node_id':20}
        found=self.response(result={'complete':True,'candidates':[c]})
        exact=self.response(result={'edges':[{'id':i,'node0':20,'node1':i+30,'road_type':'TRACK'} for i in (10,11)]})
        with patch('bridge_live.discover',return_value=found),patch.object(self.client,'request',return_value=exact) as read:
            with self.assertRaises(LiveError):_select_throat_port(self.client,intent)
            read.assert_not_called()
            self.assertEqual(_select_throat_port(self.client,intent,connected=True)[0],c)
            exact['result']['edges'][1]['node0']=99
            with self.assertRaises(LiveError):_select_throat_port(self.client,intent,connected=True)
            c['incidence_complete']=False
            with self.assertRaises(LiveError):_select_throat_port(self.client,intent,connected=True)

    def test_network_pending_partial_unknown_and_no_second_build_or_replay(self):
        from bridge_network import plan_layout_network,execute_layout_network
        p=plan_layout_network(self.brief());parents={name:{'current_ports':{port:{'eligible':True} for port in saved['plan']['ports']}} for name,saved in p['parents'].items()}
        self.client.journal.write_text(json.dumps({'pending':{'request_id':'uncertain'}}))
        with patch('bridge_network._parents') as inspect,patch('bridge_live.connect_corridor') as build:
            r=execute_layout_network(self.client,p);self.assertEqual(r['status'],'reconciliation_required');inspect.assert_not_called();build.assert_not_called()
        self.client.journal.write_text('{}')
        with patch('bridge_network._parents',return_value=parents),patch('bridge_live.connect_corridor',return_value={'status':'mutation_outcome_unknown','game_constructed':'unknown'}) as build:
            r=execute_layout_network(self.client,p);self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(build.call_count,1)
            saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved['unfinished_step'],'UP');self.assertEqual(r['routes_verified'],0)
        self.assertFalse((self.client.evidence/'network.lock').exists())
        parents['first']['current_ports']['branch_up']['eligible']=False
        with patch('bridge_network._parents',return_value=parents),patch('bridge_live.connect_corridor') as build:
            r=execute_layout_network(self.client,p);self.assertEqual(r['status'],'attachment_not_free');build.assert_not_called()

    def test_network_inspection_preserves_receipt_and_never_builds(self):
        from bridge_network import plan_layout_network,inspect_layout_network
        p=plan_layout_network(self.brief());path=self.root/'receipt.json';path.write_text(json.dumps({'plan':p,'summary':{'game_constructed':'unknown'},'links':{}}));before=path.read_bytes()
        with patch('bridge_network._parents',return_value={}),patch('bridge_live.connect_corridor') as build,patch.object(self.client,'request') as native:
            r=inspect_layout_network(self.client,path);self.assertEqual(r['status'],'network_incomplete');self.assertFalse(r['game_constructed']);build.assert_not_called();native.assert_not_called()
        self.assertEqual(path.read_bytes(),before)
        parent=Path(p['parents']['first']['record']);parent.write_text(parent.read_text()+' ')
        # Harmless JSON whitespace preserves canonical record identity.
        with patch('bridge_network._verify',return_value={'final_network_verified':True}),patch('bridge_live.connect_corridor') as build:
            self.assertEqual(inspect_layout_network(self.client,path)['status'],'ok');build.assert_not_called()
        data=json.loads(parent.read_text());data['summary']['status']='failed';parent.write_text(json.dumps(data))
        with self.assertRaises(ValueError):inspect_layout_network(self.client,path)

    def test_network_full_path_requires_connectors_and_each_local_movement(self):
        from bridge_network import plan_layout_network,_corridor,_verify
        import hashlib
        p=plan_layout_network(self.brief());record={'summary':{'evidence':str(self.root/'verify.json')},'links':{},'routes':[]};parents={};connector={}
        for i,name in enumerate(p['parents']):
            ports={port:{'edge_id':100+i*20+j,'node_id':200+i*20+j} for j,port in enumerate(p['parents'][name]['plan']['ports'])}
            parents[name]={'current_ports':ports,'routes':[]}
        def path_response(ids):
            return self.response(result={'requested_route_verified':True,'path':[{'confirmed_TRACK':True,'edge':{'entity':e}} for e in ids]})
        for i,link in enumerate(p['brief']['links']):
            a=parents[link['source']['layout']]['current_ports'][link['source']['port']]['node_id'];z=parents[link['target']['layout']]['current_ports'][link['target']['port']]['node_id'];edge=300+i
            y=i*20;connector[edge]={'id':edge,'node0':a,'node1':z,'road_type':'TRACK','p0':[0,y,0],'p1':[100,y,0],'t0':[100,0,0],'t1':[100,0,0]}
            receipt={'brief':_corridor(p,link),'summary':{'status':'ok','edges':[edge],'nodes':[a,z]}};f=self.root/(link['direction']+'.json');f.write_text(json.dumps(receipt));record['links'][link['direction']]={'record':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
            m=next(r for r in p['brief']['movements'] if r['direction']==link['direction'])
            for side in ('source','target'):
                x,y=(m[side]['port'],link[side]['port']) if side=='source' else (link[side]['port'],m[side]['port'])
                local=[parents[m[side]['layout']]['current_ports'][x]['edge_id'],parents[m[side]['layout']]['current_ports'][y]['edge_id']]
                parents[m[side]['layout']]['routes'].append({'from':x,'to':y,'response':path_response(local)})
        def request(op,q):
            if op=='inspect':return self.response(result={'edges':[connector[e] for e in q['edge_ids']]})
            self.assertEqual(q['max_length'],6000)
            m=next(m for m in p['brief']['movements'] if parents[m['source']['layout']]['current_ports'][m['source']['port']]['edge_id']==q['source_edge'])
            link=next(l for l in p['brief']['links'] if l['direction']==m['direction']);ids=[]
            for side in ('source','target'):
                x,y=(m[side]['port'],link[side]['port']) if side=='source' else (link[side]['port'],m[side]['port'])
                row=next(r for r in parents[m[side]['layout']]['routes'] if r['from']==x and r['to']==y)
                if side=='target':ids += [300 if m['direction']=='UP' else 301]
                ids += [e['edge']['entity'] for e in row['response']['result']['path']]
            return path_response(ids)
        with patch('bridge_network._parents',return_value=parents),patch.object(self.client,'request',side_effect=request):
            result=_verify(self.client,p,record);self.assertTrue(result['final_network_verified']);self.assertEqual(len(record['routes']),2);self.assertFalse(result['constant_parallel_spacing'])
        record['routes']=[]
        def shortcut(op,q):
            if op=='inspect':return self.response(result={'edges':[connector[e] for e in q['edge_ids']]})
            return path_response(q['required_edges'])
        with patch('bridge_network._parents',return_value=parents),patch.object(self.client,'request',side_effect=shortcut),self.assertRaises(LiveError):_verify(self.client,p,record)
        self.assertFalse(record['routes'][0]['verified'])
        connector[300]['node1']=999
        with patch('bridge_network._parents',return_value=parents),patch.object(self.client,'request',side_effect=shortcut),self.assertRaises(LiveError):_verify(self.client,p,record)

    def test_explicit_network_continuation_rechecks_and_skips_completed_link(self):
        from bridge_network import plan_layout_network,execute_layout_network
        import hashlib
        p=plan_layout_network(self.brief());original=self.root/'partial_network.json';original.write_text(json.dumps({'plan':p,'links':{'UP':{'record':'kept','sha256':'kept'}},'summary':{'status':'error','game_constructed':'unknown'}}))
        checked=self.root/'partial_readback.json';checked.write_text(json.dumps({'current_links':{'UP':{}},'summary':{'status':'network_incomplete'}}))
        parents={name:{'current_ports':{port:{'eligible':True} for port in saved['plan']['ports']}} for name,saved in p['parents'].items()};parents['first']['current_ports']['branch_up']['eligible']=False
        made=self.root/'down.json';made.write_text('{}')
        with patch('bridge_network.inspect_layout_network',return_value={'status':'network_incomplete','evidence':str(checked)}) as inspect,patch('bridge_network._parents',return_value=parents),patch('bridge_live.connect_corridor',return_value={'status':'ok','game_constructed':True,'evidence':str(made)}) as build,patch('bridge_network._verify',return_value={'final_network_verified':True}):
            r=execute_layout_network(self.client,p,continuation_record=original);self.assertEqual(r['status'],'ok');self.assertEqual(build.call_count,1);self.assertEqual(build.call_args.args[1]['source']['guide_xyz'],p['parents']['second']['plan']['ports']['D1:west']['position']);inspect.assert_called_once()
            current=json.loads(Path(r['evidence']).read_text());self.assertEqual(current['links']['UP']['sha256'],'kept');self.assertEqual(current['recorded_prior_game_constructed'],'unknown')
        bad=self.brief();bad['max_route_length']=7000;changed=plan_layout_network(bad)
        with patch('bridge_network.inspect_layout_network') as inspect,patch('bridge_live.connect_corridor') as build:
            r=execute_layout_network(self.client,changed,continuation_record=original);self.assertEqual(r['status'],'invalid_result');inspect.assert_not_called();build.assert_not_called()

    def test_combined_route_finite_longer_bound(self):
        b={'source_edge':1,'source_node':2,'target_edge':3,'target_node':4,'mode':'TRAIN','required_edges':[1,3],'max_length':6000}
        with patch.object(self.client,'request',return_value=self.response()) as read:
            route(self.client,b);self.assertEqual(read.call_args.args[1]['max_length'],6000)
            for value in (8001,float('inf'),0):
                with self.assertRaises(ValueError):route(self.client,b|{'max_length':value})

class PairedConnectionTests(unittest.TestCase):
    setUp = LiveClientTests.setUp
    response = LiveClientTests.response

    def brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/paired_connection_example.json').read_text())

    def ports(self,b):
        ports={}
        for i,(name,p) in enumerate(b['ports'].items()):
            pos=p['endpoint']['guide_xyz'];d=p['endpoint']['travel_direction'];sign=1 if name.endswith('source') else -1
            other=[pos[k]-sign*20*(d[k] if k<2 else 0) for k in range(3)]
            edge={'id':10+i,'node0':20+i,'node1':30+i,'p0':pos,'p1':other,'t0':[other[k]-pos[k] for k in range(3)],'t1':[other[k]-pos[k] for k in range(3)],'template':'track','style':'style','road_type':'TRACK'}
            ports[name]={'edge_id':10+i,'node_id':20+i,'edge_snapshot':edge,'grade':0,'eligible':True,'incident_count':1,'incident_edges':[10+i]}
        return ports

    def test_explicit_plan_direction_rotation_and_signed_offset(self):
        from bridge_parallel import plan_paired_connection
        b=self.brief();p=plan_paired_connection(b);self.assertEqual(p,plan_paired_connection(b));self.assertEqual(p['signed_spacing'],5);self.assertFalse(p['game_constructed'])
        import math
        def transform(pos):return [500-pos[1],100+pos[0],pos[2]]
        for value in b['ports'].values():
            e=value['endpoint'];e['guide_xyz']=transform(e['guide_xyz']);e['travel_direction']=[-e['travel_direction'][1],e['travel_direction'][0]];e['region']={'min':[e['guide_xyz'][0]-2,e['guide_xyz'][1]-2,31],'max':[e['guide_xyz'][0]+2,e['guide_xyz'][1]+2,35]}
        for g in b['guides']:g['position']=transform(g['position']);g['travel_direction']=[-g['travel_direction'][1],g['travel_direction'][0]]
        points=[x['endpoint']['guide_xyz'] for x in b['ports'].values()]+[g['position'] for g in b['guides']];b['region']={'min':[min(p[k] for p in points)-100 for k in range(3)],'max':[max(p[k] for p in points)+100 for k in range(3)]};self.assertEqual(plan_paired_connection(b)['signed_spacing'],5)
        b=self.brief();b['side']='right'
        for up,down in [('up_source','down_target'),('up_target','down_source')]:
            a=b['ports'][up]['endpoint'];z=b['ports'][down]['endpoint'];d=a['travel_direction'];n=math.hypot(*d);z['guide_xyz']=[a['guide_xyz'][0]+5*d[1]/n,a['guide_xyz'][1]-5*d[0]/n,a['guide_xyz'][2]]
        self.assertEqual(plan_paired_connection(b)['signed_spacing'],-5)

    def test_unsupported_and_invalid_pair_rejects_before_native(self):
        from bridge_parallel import plan_paired_connection
        for field in ('spacing','direction','height','guide_grade','duplicate','splay','tolerance','length','nan'):
            b=self.brief()
            if field=='spacing':b['spacing']=4
            elif field=='direction':b['ports']['down_target']['endpoint']['travel_direction']=[1,0]
            elif field=='height':b['ports']['down_source']['endpoint']['guide_xyz'][2]+=1
            elif field=='guide_grade':b['guides'][0]['grade']=.01
            elif field=='duplicate':b['ports']['down_target']['id']='up_source'
            elif field=='splay':b['ports']['down_target']['endpoint']['guide_xyz'][1]+=2
            elif field=='tolerance':b['spacing_tolerance']=.2
            elif field=='length':b['min_curved_length']=0
            else:b['guides'][0]['position'][0]=float('nan')
            with self.subTest(field=field),self.assertRaises((ValueError,LiveError)):plan_paired_connection(b)

    def test_cli_planning_compact_and_offline(self):
        b=self.brief();path=self.root/'brief.json';path.write_text(json.dumps(b));output=io.StringIO()
        with patch('bridge_live.client_from_context') as native,contextlib.redirect_stdout(output):
            self.assertEqual(main(['paired-connection','--params',str(path),'--evidence',str(self.root/'plans')]),0);native.assert_not_called()
        self.assertLess(len(output.getvalue().encode()),4096)

    def test_partial_and_pending_stop_without_replay(self):
        from bridge_parallel import plan_paired_connection,execute_paired_connection
        p=plan_paired_connection(self.brief());self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch('bridge_parallel._ports') as ports,patch('bridge_live.connect_corridor') as build:
            r=execute_paired_connection(self.client,p);self.assertEqual(r['status'],'reconciliation_required');ports.assert_not_called();build.assert_not_called()
        self.client.journal.write_text('{}');ports=self.ports(self.brief())
        up={'status':'ok','game_constructed':True,'selected':{k:ports['up_'+n][v] for n in ('source','target') for k,v in ((n+'_edge','edge_id'),(n+'_node','node_id'))},'edges':[100],'nodes':[20,21]}
        with patch('bridge_parallel._ports',return_value=ports),patch('bridge_live.connect_corridor',return_value=up),patch('bridge_parallel._read_chain',return_value=[{'edge':{'resource':{'track_distance':5}}}]),patch.object(self.client,'request',return_value=self.response('failed','adjacent',result={'game_constructed':'unknown','error':'partial'})|{'status':'mutation_unverified'}) as native:
            r=execute_paired_connection(self.client,p);self.assertEqual(r['status'],'mutation_unverified');self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(r['completed_connectors'],['UP']);self.assertEqual(native.call_count,1)
            record=json.loads(Path(r['evidence']).read_text());self.assertEqual(record['unfinished_step'],'offset')
        with patch('bridge_parallel._ports',return_value=ports),patch('bridge_live.connect_corridor',side_effect=LiveError('mutation_outcome_unknown','lost acknowledgement')):
            r=execute_paired_connection(self.client,p);self.assertEqual(r['game_constructed'],'unknown')

    def test_fresh_inspect_read_only_partial_receipt_and_stale_plan(self):
        from bridge_parallel import plan_paired_connection,inspect_paired_connection
        p=plan_paired_connection(self.brief());path=self.root/'partial.json';path.write_text(json.dumps({'plan':p,'summary':{'game_constructed':'unknown'},'chains':{}}));before=path.read_bytes()
        with patch('bridge_parallel._ports',return_value=self.ports(self.brief())),patch('bridge_live.connect_corridor') as build,patch.object(self.client,'request') as native:
            r=inspect_paired_connection(self.client,path);self.assertEqual(r['status'],'pair_incomplete');self.assertFalse(r['game_constructed']);self.assertEqual(r['routes_verified'],0);build.assert_not_called();native.assert_not_called()
        self.assertEqual(path.read_bytes(),before)
        record=json.loads(path.read_text());record['plan']['signed_spacing']=-5;path.write_text(json.dumps(record))
        with self.assertRaises(ValueError):inspect_paired_connection(self.client,path)

    def test_full_directional_routes_and_native_correspondence_required(self):
        from bridge_parallel import plan_paired_connection,_verify
        b=self.brief();p=plan_paired_connection(b);ports=self.ports(b);chains={'UP':{'edges':[100,101],'nodes':[20,90,21]},'DOWN':{'edges':[102,103],'nodes':[23,91,22]}}
        for name,ids in [('up_source',[10,100]),('up_target',[11,101]),('down_target',[13,102]),('down_source',[12,103])]:ports[name].update(incident_edges=ids,incident_count=2)
        record={'plan':p,'ports':ports,'chains':chains,'routes':[]}
        def request(op,q):
            if op=='route':
                self.assertEqual(q['source_node'],30 if q['source_edge']==10 else 32)
                ids=[10,100,101,11] if q['source_edge']==10 else [12,103,102,13]
                return self.response(result={'requested_route_verified':True,'path':[{'confirmed_TRACK':True,'edge':{'entity':e}} for e in ids]})
            self.assertEqual(op,'verify_adjacency');self.assertEqual(q['spacing'],5);self.assertEqual(q['reference'][0]['edge']['id'],100)
            return self.response(result={'sampled_verified':True,'correspondence':[{'reference_u':.5,'signed_normal':5}],'curved_reference_chord_length':500,'min_sampled_separation':4.99,'max_sampled_separation':5.01,'samples':34})
        def chain(c,plan,r,name):return [{'edge':{'id':e},'forward':True} for e in chains[name]['edges']]
        with patch('bridge_parallel._ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=chain),patch.object(self.client,'request',side_effect=request):
            r=_verify(self.client,p,record);self.assertTrue(r['final_pair_verified']);self.assertEqual(r['routes_verified'],2)
        record['routes']=[]
        with patch('bridge_parallel._ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=chain),patch.object(self.client,'request',return_value=self.response(result={'requested_route_verified':True,'path':[]})),self.assertRaises(LiveError):_verify(self.client,p,record)
        self.assertFalse(record['routes'][0]['verified'])
        with patch('bridge_parallel._ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=chain),patch.object(self.client,'request',side_effect=lambda op,q:request(op,q) if op=='route' else self.response(result={'sampled_verified':True,'correspondence':[],'curved_reference_chord_length':0})),self.assertRaises(LiveError):_verify(self.client,p,record)

    def test_exact_role_and_chain_changes_fail(self):
        from bridge_parallel import plan_paired_connection,_ports,_read_chain
        b=self.brief();p=plan_paired_connection(b);old=self.ports(b);record={'ports':json.loads(json.dumps(old))}
        old['up_source']['edge_snapshot']['p0'][0]+=.01
        with patch('bridge_live._select_throat_port',side_effect=lambda c,intent,**kw:(next(v for k,v in old.items() if intent==b['ports'][k]['endpoint']),'current')),self.assertRaises(LiveError):_ports(self.client,p,record,connected=True)
        record={'chains':{'UP':{'edges':[100],'nodes':[20,21]}}}
        with patch.object(self.client,'request',return_value=self.response(result={'edges':[{'id':100,'node0':20,'node1':99,'road_type':'TRACK'}]})),self.assertRaises(LiveError):_read_chain(self.client,p,record,'UP')

    def test_explicit_reference_continuation_skips_up_and_requires_precise_failure(self):
        from bridge_parallel import plan_paired_connection,execute_paired_connection,_recover_reference
        p=plan_paired_connection(self.brief());ports=self.ports(self.brief())
        def recover(c,plan,record,path):record.update(ports=ports,current_ports=ports,chains={'UP':{'edges':[100],'nodes':[20,21]}},reference_reconciliation={'reference_current_verified':True})
        def read(c,p,r,n):return [{'edge':{'resource':{'track_distance':5}}}]
        rb={'ordered_edges':[101],'ordered_nodes':[23,22],'engineering_checks_verified':True,'requested_min_radius':p['brief']['radius'],'min_sampled_radius':500,'max_sampled_grade':0}
        with patch('bridge_parallel._recover_reference',side_effect=recover),patch('bridge_parallel._read_chain',side_effect=read),patch('bridge_live.connect_corridor') as up,patch.object(self.client,'request',return_value=self.response('offset','adjacent',result={'game_constructed':True,'readback':rb})) as native,patch('bridge_parallel._verify',return_value={'final_pair_verified':True,'spacing_verified':True}):
            r=execute_paired_connection(self.client,p,reference_record='explicit');self.assertEqual(r['status'],'ok');up.assert_not_called();self.assertEqual(native.call_count,1);self.assertEqual(native.call_args.args[0],'adjacent');self.assertEqual(native.call_args.args[1]['attachments']['source']['anchor_node'],ports['down_target']['node_id'])
        raw=self.root/'workflow.json';raw.write_text(json.dumps({'attempts':[{'request_id':'wrong'}]}));response=self.root/'wrong.response.json';response.write_text(json.dumps({'operation':'corridor','status':'mutation_unverified','result':{'error':'different_failure','returned_edges':[100]}}));old=self.root/'old.json';old.write_text(json.dumps({'plan':p,'ports':ports,'operations':[{'name':'reference','response':{'evidence':str(raw)}}]}))
        with patch.object(self.client,'request') as native,self.assertRaises(LiveError):_recover_reference(self.client,p,{'chains':{}},old)
        native.assert_not_called()

if __name__ == '__main__':
    unittest.main()
