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

class ScissorsTests(unittest.TestCase):
    def brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/scissors_example.json').read_text())

    def test_compact_scissors_validates_selected_domain(self):
        from bridge_scissors import validate,tips
        b=self.brief();validate(b)
        for t in tips(b).values():self.assertTrue(0<=t['position'][1]<=5)
        for field,value in [('radius',59),('fit_radius',69),('half_arm_length',0),('half_arm_length',float('nan'))]:
            q=self.brief();q[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):validate(q)

    def test_scissors_movements_require_selected_turnouts_and_plain_crossing(self):
        from bridge_scissors import _movements
        ms={m['id']:m for m in _movements()}
        self.assertEqual(len(ms),12)
        self.assertEqual(ms['W0_to_E0']['via'],['L0','R0'])
        self.assertEqual(ms['W0_to_E1']['via'],['L0','C','R1'])
        self.assertEqual(ms['E1_to_W0']['via'],['R1','C','L0'])
        self.assertEqual(ms['W0_to_W1']['via'],[])

    def test_compact_scissors_does_not_silently_repair_layout(self):
        from bridge_scissors import validate
        for field in ('spacing','heading','level','axis'):
            b=self.brief()
            if field=='spacing':b['endpoints']['E1']['guide_xyz'][1]=30
            if field=='heading':b['turnouts']['R0']['travel_direction']=[1,0]
            if field=='level':b['endpoints']['W1']['guide_xyz'][2]=1
            if field=='axis':b['axes'][0]=[1,1]
            with self.subTest(field=field),self.assertRaises(ValueError):validate(b)

    def test_scissors_pending_mutation_and_partial_record_stop(self):
        from bridge_scissors import scissors,inspect_scissors
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);client=LiveClient(root/'mod',root/'log',root/'evidence','test',.1)
            client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
            with patch.object(client,'request') as call:
                summary=scissors(client,self.brief(),execute=True)
                self.assertEqual(summary['status'],'reconciliation_required');call.assert_not_called()
            r=root/'partial.json';r.write_text(json.dumps({'brief':self.brief(),'session':'test','complete_receipts':False}))
            with patch.object(client,'request') as call,self.assertRaises(LiveError):inspect_scissors(client,r)
            call.assert_not_called()

    def test_scissors_rotated_envelope_checks_curve_interior(self):
        from bridge_scissors import validate,_branch_envelope
        import math
        b=self.brief();a=.4;c,s=math.cos(a),math.sin(a)
        def pos(v):return [100+c*v[0]-s*v[1],200+s*v[0]+c*v[1],9]
        for h in [*b['endpoints'].values(),*b['turnouts'].values()]:
            h['guide_xyz']=pos(h['guide_xyz']);h['region']={'min':[v-1 for v in h['guide_xyz']],'max':[v+1 for v in h['guide_xyz']]};d=h['travel_direction'];h['travel_direction']=[c*d[0]-s*d[1],s*d[0]+c*d[1]]
        b['center']=pos(b['center']);b['axes']=[[c*d[0]-s*d[1],s*d[0]+c*d[1]] for d in b['axes']];b['region']={'min':[80,180,8],'max':[410,330,10]};validate(b)
        e={'p0':pos([120,1,0]),'p1':pos([130,2,0]),'t0':[10*c,10*s,0],'t1':[10*c,10*s,0]};_branch_envelope(b,[e])
        e['t0']=[10*c-100*s,10*s+100*c,0]
        with self.assertRaises(LiveError):_branch_envelope(b,[e])

    def test_scissors_native_rejection_stops_without_replay(self):
        from bridge_scissors import scissors
        b=self.brief();calls=[]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);client=LiveClient(root/'mod',root/'log',root/'evidence','test',.1)
            def request(op,p):
                calls.append((op,p))
                if p.get('execute'):
                    return {'status':'error','result':{'error':'native_construction_rejected','game_constructed':'unknown'}}
                fits={n:{'controls':[{'p0':h['guide_xyz'],'p1':[150,2.5,0],'t0':[0,0,0],'t1':[0,0,0]}]} for n,h in b['turnouts'].items()}
                return {'status':'ok','result':{'fits':fits}}
            with patch('bridge_scissors.live._select_throat_port',return_value=({},'read')),patch('bridge_scissors._source',side_effect=lambda client,brief,n:({'location':{'guide_xyz':brief['turnouts'][n]['guide_xyz']}},'read')),patch.object(client,'request',side_effect=request):
                result=scissors(client,b,execute=True)
            self.assertEqual(len(calls),2);self.assertEqual(result['stage'],'connected_pointwork');self.assertEqual(result['game_constructed'],'unknown')
            self.assertTrue(all(op=='scissors_candidate' for op,p in calls));self.assertFalse(calls[0][1]['execute']);self.assertTrue(calls[1][1]['execute'])
            record=json.loads(Path(result['evidence']).read_text());self.assertEqual(len(record['operations']),2);self.assertFalse(record['leads']);self.assertNotIn('complete_receipts',record)

    def test_connected_scissors_execution_is_classified_as_mutation(self):
        self.assertTrue(is_mutation('scissors_candidate',{'execute':True}))
        self.assertFalse(is_mutation('scissors_candidate',{'execute':False}))

    def test_rejected_scissors_reconciliation_requires_current_rails_and_routes(self):
        from bridge_live import reconcile_rejected_scissors
        originals=[{'id':11,'node0':1,'node1':2},{'id':22,'node0':3,'node1':4}]
        for failure in (None,'ack','snapshot','route'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as d:
                root=Path(d);client=LiveClient(root/'mod',root/'log',root/'evidence','test',.1)
                pending={'request_id':'rejected','operation':'scissors_candidate','params':{'execute':True,'max_route_length':500,
                    'leads':{n:{'source':{'edge_snapshot':e}} for n,e in zip(('L0','L1'),originals)}}}
                client.journal.write_text(json.dumps({'pending':pending}))
                (client.evidence/'rejected.response.json').write_text(json.dumps({'session':'test','request_id':'rejected','operation':'scissors_candidate',
                    'status':'error','result':{'native_command_success':failure=='ack','error':'native_construction_rejected','stage':'build'}}))
                calls=[]
                def request(op,p):
                    calls.append((op,p))
                    if op=='scissors_candidate':return {'request_id':'read','status':'ok','result':{'game_constructed':False,'originals':[] if failure=='snapshot' else originals}}
                    return {'request_id':'route'+str(len(calls)),'status':'ok','result':{'requested_route_verified':failure!='route'}}
                with patch.object(client,'request',side_effect=request):
                    if failure:
                        with self.assertRaises(LiveError):reconcile_rejected_scissors(client)
                        self.assertEqual(json.loads(client.journal.read_text())['pending'],pending)
                    else:
                        result=reconcile_rejected_scissors(client)
                        self.assertFalse(result['result']['automatic_replay']);self.assertEqual(result['result']['other_effects'],'unknown')
                        self.assertNotIn('pending',json.loads(client.journal.read_text()));self.assertEqual(len(calls),3)
                self.assertTrue(all(not p.get('execute') for _,p in calls))

    def test_connected_scissors_keeps_incomplete_native_receipt(self):
        from bridge_scissors import scissors
        b=self.brief()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);client=LiveClient(root/'mod',root/'log',root/'evidence','test',.1)
            fits={n:{'controls':[{'p0':h['guide_xyz'],'p1':[150,2.5,0],'t0':[0,0,0],'t1':[0,0,0]}]} for n,h in b['turnouts'].items()}
            with patch('bridge_scissors.live._select_throat_port',return_value=({},'read')),patch('bridge_scissors._source',return_value=({},'read')),patch.object(client,'request',side_effect=[{'status':'ok','result':{'fits':fits}},{'status':'mutation_unverified','result':{'game_constructed':True,'returned_edges':[20],'error':'receipt_incomplete'}}]) as call:
                summary=scissors(client,b,execute=True)
            self.assertEqual(summary['status'],'mutation_unverified');self.assertIs(summary['game_constructed'],True);self.assertEqual(call.call_count,2)
            record=json.loads(Path(summary['evidence']).read_text());self.assertEqual(record['operations'][-1]['response']['result']['returned_edges'],[20]);self.assertNotIn('complete_receipts',record)

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.log=self.root/'stdout.txt';self.log.write_text('')
        self.client=LiveClient(self.root/'mod',self.log,self.root/'evidence','test_session',.15)

    def state(self):return json.loads(self.client.journal.read_text())

    def append(self,request,*,ack=True,status='ok'):
        response={k:request[k] for k in ('version','session','request_id','operation')};response.update(status=status,result={'game_constructed':False})
        with self.log.open('a') as stream:
            stream.write(MARKER+json.dumps(response)+'\n')
            if ack:stream.write('TPF3_BRIDGE_LIVE_ACK '+json.dumps({'session':'test_session','request_id':request['request_id'],'success':True})+'\n')

    def legacy_pair(self):
        requests=[]
        for seq in (70,71):
            r={'version':1,'session':'test_session','sequence':seq,'request_id':'read'+str(seq),'operation':'discover_interior','params':{'max_edges':16}}
            (self.client.evidence/(r['request_id']+'.request.json')).write_text(json.dumps(r));requests.append(r|{'log_offset':0})
        second=requests[1]|{'unresolved_mutation':requests[0]}
        self.client.journal.write_text(json.dumps({'session':'test_session','next_sequence':72,'pending':second}))
        slot=self.client._slot(requests[1]);slot.parent.mkdir(parents=True);slot.write_bytes(self.client._request_body(requests[1]))
        return requests

    def nested_mutation_read(self):
        mutation={'version':1,'session':'test_session','sequence':20,'request_id':'constructed','operation':'crossover','params':{'execute':True,'radius':70},'log_offset':0,'outcome':'mutation_unverified','publication':{'state':'published'}}
        read={'version':1,'session':'test_session','sequence':42,'request_id':'retained','operation':'route','params':{'mode':'TRAIN'},'log_offset':0,'operation_kind':'read'}
        read['publication']={'state':'unpublished','phase':'temporary_written','sha256':__import__('hashlib').sha256(self.client._request_body(read)).hexdigest()}
        for p in (mutation,read):
            (self.client.evidence/(p['request_id']+'.request.json')).write_text(json.dumps({k:p[k] for k in ('version','session','sequence','request_id','operation','params')}))
            slot=self.client._slot(p);slot.parent.mkdir(parents=True,exist_ok=True)
            (slot if p is mutation else slot.with_suffix('.pending')).write_bytes(self.client._request_body(p))
        read['unresolved_mutation']=mutation
        self.client.journal.write_text(json.dumps({'session':'test_session','next_sequence':42,'pending':read}))
        return mutation,read

    def test_unpublished_read_restored_without_replaying_or_clearing_nested_mutation(self):
        mutation,read=self.nested_mutation_read();old=self.client._slot(mutation).read_bytes()
        publish=self.client._publish_file
        def worker(temp,path):publish(temp,path);self.append(read)
        with patch.object(self.client,'_publish_file',side_effect=worker) as calls:
            result=self.client.reconcile_read_publications(['retained'])
        self.assertEqual(calls.call_count,1);self.assertEqual(self.state()['pending'],mutation)
        self.assertEqual(self.state()['next_sequence'],43);self.assertEqual(self.client._slot(mutation).read_bytes(),old)
        self.assertEqual(result['result']['original_pending']['unresolved_mutation'],mutation)
        self.assertFalse(result['result']['mutation_replay'])

    def test_nested_mutation_identity_hash_and_positive_publication_evidence_rejected(self):
        for defect in ('mutation_slot','mutation_envelope','mutation_hash','hash','ack','ambiguous','ids'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                old=self.client;self.client=LiveClient(Path(d)/'mod',self.log,Path(d)/'evidence','test_session',.02)
                mutation,read=self.nested_mutation_read();state=self.state()
                if defect=='mutation_slot':self.client._slot(mutation).write_bytes(b'foreign')
                if defect=='mutation_envelope':(self.client.evidence/'constructed.request.json').write_text('{}')
                if defect=='mutation_hash':state['pending']['unresolved_mutation']['publication']['sha256']='wrong'
                if defect=='hash':state['pending']['publication']['sha256']='wrong'
                if defect=='ack':self.append(read)
                if defect=='ambiguous':state['pending']['unresolved_read']=mutation
                self.client.journal.write_text(json.dumps(state))
                with patch.object(self.client,'_publish_file') as publish,self.assertRaises(LiveError):
                    self.client.reconcile_read_publications(['constructed','retained'] if defect=='ids' else ['retained'])
                publish.assert_not_called();self.assertEqual(self.state(),state);self.client=old;self.log.write_text('')

    def test_nested_mutation_retained_on_timeout_and_journal_denial_after_publication(self):
        for deny in (False,True):
            with self.subTest(deny=deny),tempfile.TemporaryDirectory() as d:
                import bridge_live as live
                old=self.client;self.client=LiveClient(Path(d)/'mod',self.log,Path(d)/'evidence','test_session',.02)
                mutation,read=self.nested_mutation_read();atomic=live.atomic_json
                def writer(path,value):
                    if deny and path==self.client.journal:raise PermissionError('fake journal replace denied')
                    atomic(path,value)
                with patch('bridge_live.atomic_json',side_effect=writer),self.assertRaises((LiveError,PermissionError)):
                    self.client.reconcile_read_publications(['retained'])
                self.assertEqual(self.state()['pending']['unresolved_mutation'],mutation)
                self.assertTrue(self.client._slot(read).exists());self.assertFalse((self.client.evidence/'client.lock').exists())
                self.client=old

    def test_nested_mutation_published_read_consumes_response_without_republication(self):
        mutation,read=self.nested_mutation_read()
        self.client._publish_file(self.client._slot(read).with_suffix('.pending'),self.client._slot(read));self.append(read)
        with patch.object(self.client,'_publish_file') as again:
            result=self.client.reconcile_read_publications(['retained'])
        again.assert_not_called();self.assertEqual(result['status'],'ok')
        self.assertEqual(self.state()['pending'],mutation);self.assertEqual(self.state()['next_sequence'],43)

    def test_permission_before_publication_preserves_identity_without_advancing(self):
        original=Path.open
        def denied(path,*args,**kwargs):
            if path.suffix=='.pending':raise PermissionError('fake staging denied')
            return original(path,*args,**kwargs)
        for operation,params,kind in [('discover_interior',{},'read'),('build',{'fit_request':'f'},'mutation')]:
            with self.subTest(operation=operation):
                if self.client.journal.exists():self.client.journal.unlink()
                with patch.object(Path,'open',denied),self.assertRaises(LiveError) as failed:self.client.request(operation,params,request_id=kind)
                self.assertEqual(failed.exception.status,'request_publication_failed');s=self.state()
                self.assertEqual(s['next_sequence'],1);self.assertEqual(s['pending']['operation_kind'],kind)
                self.assertEqual(s['pending']['publication']['state'],'unpublished')
                self.assertTrue((self.client.evidence/(kind+'.request.json')).exists())
                with self.assertRaises(LiveError):self.client.request('inspect',{},request_id='must_not_skip_'+kind)
                self.assertEqual(self.state()['next_sequence'],1);self.assertFalse(self.client._slot(s['pending']).exists())

    def test_occupied_slot_or_temporary_is_not_overwritten(self):
        for suffix in ('.lua','.pending'):
            with self.subTest(suffix=suffix),tempfile.TemporaryDirectory() as d:
                c=LiveClient(Path(d)/'mod',self.log,Path(d)/'evidence','test_session',.05)
                slot=c.mod/'content/scripts/pif_live/test_session'/('000001'+suffix);slot.parent.mkdir(parents=True);slot.write_bytes(b'foreign')
                with self.assertRaises(LiveError) as failed:c.request('inspect',{},request_id='conflict')
                self.assertEqual(failed.exception.status,'request_slot_conflict');self.assertEqual(slot.read_bytes(),b'foreign')
                self.assertEqual(json.loads(c.journal.read_text())['next_sequence'],1)

    def test_partial_temporary_write_remains_unpublished_and_is_preserved(self):
        original=Path.open
        class Partial:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def write(self,body):self.stream.write(body[:10]);raise OSError('partial write')
        def interrupted(path,*args,**kwargs):
            stream=original(path,*args,**kwargs)
            return Partial(stream) if path.suffix=='.pending' else stream
        with patch.object(Path,'open',interrupted),self.assertRaises(LiveError):self.client.request('inspect',{},request_id='partial')
        p=self.state()['pending'];slot=self.client._slot(p);temp=slot.with_suffix('.pending');partial=temp.read_bytes()
        self.assertEqual(len(partial),10);self.assertFalse(slot.exists());self.assertEqual(self.state()['next_sequence'],1)
        self.assertEqual(p['publication']['state'],'unpublished')
        with self.assertRaises(LiveError):self.client.reconcile_read_publications(['partial'])
        self.assertEqual(temp.read_bytes(),partial);self.assertFalse(slot.exists())

    def test_rename_error_without_slot_is_uncertain_and_cannot_be_restored(self):
        with patch.object(self.client,'_publish_file',side_effect=OSError('rename ambiguous')),self.assertRaises(LiveError) as failed:
            self.client.request('inspect',{},request_id='rename')
        self.assertEqual(failed.exception.status,'request_publication_uncertain');self.assertEqual(self.state()['next_sequence'],1)
        self.assertEqual(self.state()['pending']['publication']['state'],'uncertain')
        with self.assertRaises(LiveError):self.client.reconcile_read_publications(['rename'])
        self.assertFalse(self.client._slot(self.state()['pending']).exists())

    def test_error_after_actual_publication_does_not_duplicate_request(self):
        publish=self.client._publish_file
        def failed_after(temp,path):publish(temp,path);raise OSError('failure after rename')
        with patch.object(self.client,'_publish_file',side_effect=failed_after),self.assertRaises(LiveError):self.client.request('inspect',{},request_id='published')
        pending=self.state()['pending'];self.assertEqual(self.state()['next_sequence'],2);self.assertEqual(pending['publication']['state'],'published')
        before=self.client._slot(pending).read_bytes();self.append(pending)
        with patch.object(self.client,'_publish_file') as again:r=self.client.reconcile_read_publications(['published'])
        again.assert_not_called();self.assertEqual(r['status'],'ok');self.assertEqual(self.client._slot(pending).read_bytes(),before)
        self.assertEqual(self.state()['next_sequence'],2);self.assertNotIn('pending',self.state())

    def test_journal_failure_after_publication_retains_durable_intent(self):
        import bridge_live as live
        atomic=live.atomic_json;failed=[]
        def once(path,value):
            if path==self.client.journal and value.get('pending',{}).get('publication',{}).get('state')=='published' and not failed:
                failed.append(True);raise OSError('journal publication update failed')
            return atomic(path,value)
        with patch('bridge_live.atomic_json',side_effect=once),self.assertRaises(LiveError):self.client.request('inspect',{},request_id='journal')
        s=self.state();self.assertEqual(s['pending']['publication']['state'],'published');self.assertEqual(s['next_sequence'],2)
        self.assertTrue(self.client._slot(s['pending']).exists())
        with self.assertRaises(LiveError):self.client.request('inspect',{},request_id='skip')

    def test_published_mutation_with_io_error_is_never_restored_or_repeated(self):
        publish=self.client._publish_file
        def failed_after(temp,path):publish(temp,path);raise OSError('after publication')
        with patch.object(self.client,'_publish_file',side_effect=failed_after),self.assertRaises(LiveError):self.client.request('build',{},request_id='mutation')
        original=self.client._slot(self.state()['pending']).read_bytes()
        with self.assertRaises(LiveError):self.client.reconcile_read_publications(['mutation'])
        with self.assertRaises(LiveError):self.client.request('build',{},request_id='repeat')
        self.assertEqual(self.client._slot(self.state()['pending']).read_bytes(),original);self.assertEqual(self.state()['next_sequence'],2)

    def test_legacy_unpublished_mutation_cannot_allocate_a_later_read(self):
        self.client.timeout=.02
        with self.assertRaises(LiveError):self.client.request('build',{},request_id='legacy')
        s=self.state();self.client._slot(s['pending']).unlink();s['pending'].pop('publication');self.client.journal.write_text(json.dumps(s))
        with self.assertRaises(LiveError):self.client.request('inspect',{},request_id='skip')
        self.assertEqual(self.state(),s)

    def test_exact_legacy_read_gap_is_restored_and_published_successor_consumed(self):
        reqs=self.legacy_pair();self.client.require_ack=True;second=self.client._slot(reqs[1]).read_bytes()
        def worker():
            deadline=time.monotonic()+1
            while not self.client._slot(reqs[0]).exists() and time.monotonic()<deadline:time.sleep(.005)
            self.append(reqs[0]);self.append(reqs[1],status='error')
        thread=threading.Thread(target=worker);thread.start()
        with patch('bridge_live.discover_session',return_value='test_session'):result=self.client.reconcile_read_publications(['read70','read71'])
        thread.join();self.assertEqual(result['status'],'ok');self.assertEqual(result['result']['responses'][1]['status'],'error')
        self.assertEqual(self.client._slot(reqs[0]).read_bytes(),self.client._request_body(reqs[0]))
        self.assertEqual(self.client._slot(reqs[1]).read_bytes(),second);self.assertEqual(self.state()['next_sequence'],72);self.assertNotIn('pending',self.state())
        self.assertIn('unresolved_mutation',result['result']['original_pending']);self.assertFalse(result['result']['mutation_replay'])

    def test_read_reconciliation_rejects_mismatch_mutation_and_stale_session_before_writes(self):
        for defect in ('slot','saved_request','mutation','session','ids'):
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as d:
                old=self.client;self.client=LiveClient(Path(d)/'mod',self.log,Path(d)/'evidence','test_session',.05)
                reqs=self.legacy_pair();state=self.state()
                if defect=='slot':self.client._slot(reqs[1]).write_bytes(b'foreign')
                if defect=='saved_request':(self.client.evidence/'read70.request.json').write_text('{}')
                if defect=='mutation':state['pending']['unresolved_mutation'].update(operation='build',params={});self.client.journal.write_text(json.dumps(state))
                if defect=='session':self.client.require_ack=True
                ids=['wrong','read71'] if defect=='ids' else ['read70','read71']
                with patch('bridge_live.discover_session',return_value='other'),self.assertRaises(LiveError):self.client.reconcile_read_publications(ids)
                self.assertFalse(self.client._slot(reqs[0]).exists());self.assertEqual(self.state(),state);self.client=old

    def test_missing_response_or_ack_keeps_read_history_and_never_republishes(self):
        reqs=self.legacy_pair();self.client.require_ack=True;self.client.timeout=.02
        self.append(reqs[0],ack=False) # A response already present forbids restoring absent70.
        with patch('bridge_live.discover_session',return_value='test_session'),self.assertRaises(LiveError):self.client.reconcile_read_publications(['read70','read71'])
        self.assertFalse(self.client._slot(reqs[0]).exists())
        self.client._slot(reqs[0]).write_bytes(self.client._request_body(reqs[0]));self.append(reqs[1])
        with patch('bridge_live.discover_session',return_value='test_session'),patch.object(self.client,'_publish_file') as again,self.assertRaises(LiveError):self.client.reconcile_read_publications(['read70','read71'])
        again.assert_not_called();self.assertIn('pending',self.state());self.assertEqual(self.state()['next_sequence'],72)
        self.append(reqs[0])
        with patch('bridge_live.discover_session',return_value='test_session'),patch.object(self.client,'_publish_file') as again:r=self.client.reconcile_read_publications(['read70','read71'])
        again.assert_not_called();self.assertEqual(r['status'],'ok');self.assertNotIn('pending',self.state())
        attempts=[json.loads(p.read_text()) for p in self.client.evidence.glob('*.publication_reconciliation.json')]
        self.assertEqual({p['status'] for p in attempts},{'incomplete','reconciled_reads'})

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

    def test_experimental_degree_four_tracks_explicit_mutation_and_unknown_effects(self):
        self.assertFalse(is_mutation('degree_four_candidate', {'execute': False}))
        self.assertTrue(is_mutation('degree_four_candidate', {'execute': True}))
        self.assertFalse(is_mutation('inspect_degree_four', {'execute': True}))
        self.client.timeout = .02
        with self.assertRaises(LiveError) as failed:
            self.client.request('degree_four_candidate', {'execute': True}, request_id='candidate')
        self.assertEqual(failed.exception.status, 'mutation_outcome_unknown')
        restarted = LiveClient(self.client.mod, self.log, self.client.evidence, 'test_session', .02)
        with self.assertRaises(LiveError) as blocked:
            restarted.request('degree_four_candidate', {'execute': True}, request_id='repeat')
        self.assertEqual(blocked.exception.status, 'reconciliation_required')
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_rejected_interior_proposal_evaluation_is_a_read_not_a_build(self):
        params = {'execute': False, 'proposal_diagnostics': True}
        diagnostics = {'critical': True, 'build_acceptance': 'unestablished',
                       'messages': {'values': ['Construction Not Possible'], 'count': 1}}
        def worker():
            slot = self.client.mod / 'content/scripts/pif_live/test_session/000001.lua'
            deadline = time.monotonic() + 1
            while not slot.exists() and time.monotonic() < deadline:
                time.sleep(.005)
            pending = json.loads(self.client.journal.read_text())['pending']
            self.assertEqual(pending['operation_kind'], 'read')
            self.assertEqual(pending['params'], params)
            with self.log.open('a') as stream:
                stream.write(MARKER + json.dumps(self.response('diagnostic', 'interior_junction',
                    result={'game_constructed': False, 'proposal_diagnostics': diagnostics})) + '\n')
        thread = threading.Thread(target=worker); thread.start()
        result = self.client.request('interior_junction', params, request_id='diagnostic')
        thread.join()
        self.assertFalse(result['result']['game_constructed'])
        self.assertEqual(result['result']['proposal_diagnostics'], diagnostics)
        self.assertNotIn('pending', json.loads(self.client.journal.read_text()))
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_interior_diagnostic_timeout_retains_read_for_reconciliation_without_retry(self):
        self.client.timeout = .02
        with self.assertRaises(LiveError):
            self.client.request('interior_junction', {'execute': False, 'proposal_diagnostics': True}, request_id='diagnostic')
        pending = json.loads(self.client.journal.read_text())['pending']
        self.assertEqual(pending['operation_kind'], 'read')
        self.assertFalse(is_mutation(pending['operation'], pending['params']))
        self.assertEqual(len(list(self.client.mod.rglob('*.lua'))), 1)

    def test_degree_four_preflight_and_inspection_are_read_only_cli_entries(self):
        params = self.root / 'params.json'; params.write_text(json.dumps({'execute': False}))
        for operation in ('degree_four_candidate', 'inspect_degree_four'):
            with patch('bridge_live.client_from_context', return_value=self.client), patch.object(self.client, 'request', return_value={'status':'ok', 'game_constructed':False}) as request, contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main([operation, '--context', 'dummy', '--params', str(params)]), 0)
            request.assert_called_once_with(operation, {'execute':False})
            self.assertLess(len(out.getvalue().encode()),4096)

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

    def test_free_lead_reconciliation_after_normal_load_requires_exact_free_binding(self):
        for defect in (None,'missing_free','occupied','wrong_node','wrong_edge','incidence','branch','through','receipt'):
            with self.subTest(defect=defect):
                params={'execute':True,'source':{'edge_id':10,'parameter':.5},
                        'end_xyz':[50,5,1],'end_direction':[1,0],'vertical':{'max_grade':0}}
                pending={'operation':'interior_junction','request_id':'built_free','params':params}
                self.client.journal.write_text(json.dumps({'pending':pending}))
                response=self.response('built_free','interior_junction',result={
                    'game_constructed':True,'returned_edges':[40,41,30],
                    'fit':{'pieces':1,'controls':[{}],'grade':0,'end_grade':0}})
                response['status']='mutation_unverified'
                (self.client.evidence/'built_free.response.json').write_text(json.dumps(response))
                current=LiveClient(self.root/'mod',self.log,self.root/'new_evidence','new_session',.5)
                result={'reconciled_current_state':True,
                    'readback':{'connected':True,'ordered_edges':[30],'ordered_nodes':[31,32]},
                    'placement':{'original_removed':True,'original_edge':10,'replacement_edges':[40,41]},
                    'junction':{'exact_native_identity':True,'branch_geometry_verified':True},
                    'through_after':{'requested_route_verified':True},'branch_after':{'requested_route_verified':True},
                    'free_end':{'exact_native_identity':True,'free':True,'node':32,'edge':30,'incident_edges':[30]}}
                if defect=='missing_free':result.pop('free_end')
                elif defect=='occupied':result['free_end']['free']=False
                elif defect=='wrong_node':result['free_end']['node']=99
                elif defect=='wrong_edge':result['free_end']['edge']=99
                elif defect=='incidence':result['free_end']['incident_edges']=[30,99]
                elif defect=='branch':result['branch_after']['requested_route_verified']=False
                elif defect=='through':result['through_after']['requested_route_verified']=False
                elif defect=='receipt':result['placement']['replacement_edges']=[40,99]
                with patch.object(current,'request',return_value={'status':'ok','request_id':'verify_free','result':result}) as call:
                    if defect:
                        with self.assertRaises(LiveError):reconcile_constructed_interior(current,self.client)
                        self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)
                    else:
                        value=reconcile_constructed_interior(current,self.client)
                        self.assertEqual(value['result']['current_session'],'new_session')
                        self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
                        self.assertFalse(value['result']['automatic_replay'])
                call.assert_called_once();op,p=call.call_args.args
                self.assertEqual(op,'verify_interior');self.assertFalse(p['execute']);self.assertNotIn('target',p)
                self.assertEqual(p['vertical']['max_grade'],0);self.assertEqual(p['edge_ids'],[40,41,30])
                self.assertFalse(is_mutation(op,p))

    def test_native_free_lead_retains_explicit_zero_grade_and_read_only_endpoint_checks(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        junction=source[source.index('function M.interior_junction'):source.index('local function reacquire_split')]
        self.assertIn('vertical=te and p.vertical or nil',junction)
        self.assertIn('f.max_grade=p.vertical.max_grade;fit.max_grade=p.vertical.max_grade',junction)
        self.assertLess(junction.index('f.max_grade=p.vertical.max_grade'),junction.index('stage="build"'))
        verifier=source[source.index('function M.verify_interior'):source.index('function M.test_approach')]
        self.assertIn('if p.target then',verifier)
        self.assertIn('recorded_free_lead_not_level',verifier)
        self.assertIn('recorded_free_lead_endpoint_mismatch',verifier)
        self.assertIn('max_grade=p.vertical.max_grade',verifier)
        self.assertNotIn('M.build',verifier);self.assertNotIn('sendCommand',verifier)
        readback=source[source.index('local function interior_readback'):source.index('function M.interior_junction')]
        self.assertIn('realised_free_lead_not_free',readback)
        self.assertIn('realised_free_lead_endpoint_mismatch',readback)

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

    def test_rejected_selected_connection_reconciles_without_replaying_or_inventing_effects(self):
        for defect in ('none','wrong_node','constructed','query'):
            pending=self.rejected_connection_pending();pending['operation']='selected_connection';pending['params']={'execute':True,'source':{'node_id':11},'target':{'node_id':21}}
            self.client.journal.write_text(json.dumps({'session':'test_session','pending':pending}));response=self.response('rejected_connection','selected_connection',result={'stage':'build','native_command_success':False,'error':'native_construction_rejected'});response['status']='error'
            (self.client.evidence/'rejected_connection.response.json').write_text(json.dumps(response))
            observed=self.response('fresh','selected_connection',result={'game_constructed':defect=='constructed','fit':{'start_node':11,'target_node':22 if defect=='wrong_node' else 21}})
            if defect=='query':observed['status']='error'
            with patch.object(self.client,'request',return_value=observed) as native:
                if defect=='none':
                    r=reconcile_rejected_connection(self.client);self.assertFalse(r['result']['completed_connection_constructed']);self.assertEqual(r['result']['other_effects'],'unknown');self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
                else:
                    with self.assertRaises(LiveError):reconcile_rejected_connection(self.client)
                    self.assertEqual(json.loads(self.client.journal.read_text())['pending'],pending)
                self.assertEqual(native.call_count,1);self.assertFalse(native.call_args.args[1]['execute'])

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

    def test_crossover_representation_is_explicit_opt_in_and_forwarded(self):
        for representation in (None,'native_parts','single_cubic_level'):
            with self.subTest(representation=representation):
                self.throat_calls=[];self.throat_epoch=0;self.throat_fail_route=False;b=self.throat_brief()
                if representation is not None:b['steps'][0]['representation']=representation
                with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch('bridge_live.connect_junction_at',side_effect=self.throat_branch),patch.object(self.client,'request',side_effect=self.throat_worker):r=connect_throat(self.client,b)
                self.assertEqual(r['status'],'ok');self.assertFalse(r['game_constructed'])
                self.assertEqual(self.throat_calls[0][1].get('representation'),representation)
                self.assertFalse(self.throat_calls[0][1]['execute'])

    def test_crossover_representation_domain_rejects_unapproved_options(self):
        for value in (True,{},'approximate','single_cubic_graded'):
            b=self.throat_brief();b['steps'][0]['representation']=value
            with self.subTest(value=value),patch.object(self.client,'request') as calls,self.assertRaises(ValueError):connect_throat(self.client,b)
            calls.assert_not_called()
        b=self.throat_brief();b['steps'][1]['representation']='single_cubic_level'
        with self.assertRaises(ValueError):validate_throat_brief(b)

    def test_crossover_reconciliation_cannot_change_representation(self):
        self.throat_epoch=1
        b=self.throat_brief();saved=self.throat_reconciliation(b);b['steps'][0]['representation']='single_cubic_level'
        with patch('bridge_live._select_throat_port',side_effect=self.throat_port),patch.object(self.client,'request') as calls:
            result=connect_throat(self.client,b,execute=True,reconciled_crossover=saved)
        self.assertEqual(result['status'],'invalid_result');calls.assert_not_called()

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

class MultitrackConnectionTests(unittest.TestCase):
    setUp = LiveClientTests.setUp
    response = LiveClientTests.response

    def brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/multitrack_connection_example.json').read_text())

    def state(self,plan):
        ports={};chains={}
        for i,t in enumerate(plan['tracks']):
            ids=[100+i];nodes=[20+2*i,21+2*i];chains[t['id']]={'edges':ids,'nodes':nodes}
            for j,end in enumerate(('start','end')):
                key=t[end];p=plan['ports'][key]['endpoint']['guide_xyz'];d=plan['ports'][key]['endpoint']['travel_direction'];outer=[p[k]+(-1 if not j else 1)*20*(d[k] if k<2 else 0) for k in range(3)]
                ports[key]={'edge_id':10+2*i+j,'node_id':nodes[j],'grade':0,'eligible':True,'incident_count':2,'incident_edges':[10+2*i+j,ids[0]],
                    'edge_snapshot':{'p0':p,'p1':outer,'t0':[20,0,0],'t1':[20,0,0],'node0':nodes[j],'node1':200+2*i+j,'template':'track','style':'style'}}
        return ports,chains

    def chain(self,c,p,r,name):
        return [{'edge':{'id':e,'t0':[100,0,0],'t1':[100,0,0],'resource':{'track_distance':5}},'forward':True} for e in r['chains'][name]['edges']]

    def native_read(self,plan,record,op,q):
        if op=='route':
            t=next(t for t in plan['tracks'] if record['ports'][t['start'] if t['forward'] else t['end']]['edge_id']==q['source_edge'])
            ids=record['chains'][t['id']]['edges'];ids=ids if t['forward'] else ids[::-1]
            self.assertEqual(q['required_edges'],[q['source_edge']]+ids+[q['target_edge']])
            return self.response(result={'requested_route_verified':True,'total_path_length':1000,'path':[{'edge':{'entity':e},'confirmed_TRACK':True,'forward':t['forward']} for e in q['required_edges']]})
        self.assertEqual(op,'verify_adjacency')
        self.assertIn(q['spacing'],(5,10,15))
        return self.response(result={'sampled_verified':True,'correspondence':[{'signed_normal':q['spacing']}],'curved_reference_chord_length':500,'min_sampled_separation':abs(q['spacing'])-.01,'max_sampled_separation':abs(q['spacing'])+.01,'samples':17})

    def test_orderings_reversed_reference_and_ud(self):
        from bridge_parallel import plan_multitrack_connection
        for directions in (['UP','UP','DOWN','DOWN'],['UP','DOWN','UP','DOWN'],['UP','DOWN']):
            for up in ('increasing','decreasing'):
                b=self.brief();b['tracks']=b['tracks'][:len(directions)];b['reference_up']=up
                for i,t in enumerate(b['tracks']):
                    desired=(directions[i]=='UP')==(up=='increasing');old=t['direction']=='UP'
                    if desired!=old:
                        t['source'],t['target']=t['target'],t['source']
                        for k in ('source','target'):t[k]['endpoint']['travel_direction']=[-v for v in t[k]['endpoint']['travel_direction']]
                    t['direction']=directions[i]
                p=plan_multitrack_connection(b);self.assertEqual(p,plan_multitrack_connection(b));self.assertEqual([t['forward'] for t in p['tracks']],[(d=='UP')==(up=='increasing') for d in directions]);self.assertFalse(p['game_constructed'])

    def test_bad_order_identity_height_spacing_and_direction(self):
        from bridge_parallel import plan_multitrack_connection
        for kind in ('order','id','port','height','spacing','direction','splay','missing'):
            b=self.brief()
            if kind=='order':b['tracks'][0]['direction']='DOWN'
            elif kind=='id':b['tracks'][1]['id']=b['tracks'][0]['id']
            elif kind=='port':b['tracks'][1]['source']['id']=b['tracks'][0]['source']['id']
            elif kind=='height':b['tracks'][2]['target']['endpoint']['guide_xyz'][2]+=1
            elif kind=='spacing':b['spacing']=4
            elif kind=='direction':b['tracks'][1]['source']['endpoint']['travel_direction']=[-1,0]
            elif kind=='splay':b['tracks'][3]['source']['endpoint']['guide_xyz'][0]+=1
            else:b.pop('reference_up')
            with self.subTest(kind=kind),self.assertRaises((ValueError,LiveError)):plan_multitrack_connection(b)

    def test_four_routes_neighbor_and_cumulative_reference_checks(self):
        from bridge_parallel import plan_multitrack_connection,_verify_multitrack
        p=plan_multitrack_connection(self.brief());ports,chains=self.state(p);r={'ports':ports,'chains':chains}
        with patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch.object(self.client,'request',side_effect=lambda op,q:self.native_read(p,r,op,q)):
            s=_verify_multitrack(self.client,p,r)
        self.assertTrue(s['final_multitrack_verified']);self.assertEqual(s['routes_verified'],4);self.assertEqual(s['neighbor_pairs_verified'],3);self.assertEqual(s['shared_reference_checks'],2)
        self.assertEqual([q['response']['result']['correspondence'][0]['signed_normal'] for q in r['spacing_checks']],[5,5,5,10,15])

    def test_wrong_direction_cumulative_drift_and_shared_nodes_reject(self):
        from bridge_parallel import plan_multitrack_connection,_verify_multitrack
        p=plan_multitrack_connection(self.brief())
        for kind in ('direction','drift','nodes'):
            ports,chains=self.state(p);r={'ports':ports,'chains':chains}
            if kind=='nodes':chains[p['tracks'][1]['id']]['nodes'][0]=chains[p['tracks'][0]['id']]['nodes'][0]
            def request(op,q):
                v=self.native_read(p,r,op,q)
                if kind=='direction' and op=='route':v['result']['path'][1]['forward']=not v['result']['path'][1]['forward']
                if kind=='drift' and op=='verify_adjacency' and q['spacing']==15:v['result']['sampled_verified']=False
                return v
            with self.subTest(kind=kind),patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch.object(self.client,'request',side_effect=request),self.assertRaises(LiveError):_verify_multitrack(self.client,p,r)

    def test_single_reference_three_native_offsets_and_partial_stop(self):
        from bridge_parallel import plan_multitrack_connection,execute_multitrack_connection
        p=plan_multitrack_connection(self.brief());ports,chains=self.state(p);t=p['tracks'][0]
        first={'status':'ok','game_constructed':True,**chains[t['id']],'selected':{'source_edge':ports[t['start']]['edge_id'],'source_node':ports[t['start']]['node_id'],'target_edge':ports[t['end']]['edge_id'],'target_node':ports[t['end']]['node_id']}}
        for fail in (False,True):
            count=[0]
            def request(op,q):
                self.assertEqual(op,'adjacent');count[0]+=1
                if fail and count[0]==2:return self.response(result={'game_constructed':'unknown','error':'lost ack'})|{'status':'mutation_unverified'}
                chain=chains[p['tracks'][count[0]]['id']]
                return self.response(result={'game_constructed':True,'readback':{'ordered_edges':chain['edges'],'ordered_nodes':chain['nodes']}})
            with patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_live.connect_corridor',return_value=first) as build,patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_live._require_engineering_readback'),patch('bridge_parallel._verify_multitrack',return_value={'final_multitrack_verified':not fail}),patch.object(self.client,'request',side_effect=request):
                s=execute_multitrack_connection(self.client,p);self.assertEqual(build.call_count,1);self.assertEqual(count[0],2 if fail else 3)
                self.assertEqual(len(s['completed_connectors']),2 if fail else 4)
                if fail:self.assertEqual(s['game_constructed'],'unknown');self.assertEqual(json.loads(Path(s['evidence']).read_text())['unfinished_step'],p['tracks'][2]['id'])
                else:self.assertEqual(s['status'],'ok')

    def test_pending_and_unacknowledged_continuation_never_build(self):
        from bridge_parallel import plan_multitrack_connection,execute_multitrack_connection
        p=plan_multitrack_connection(self.brief());self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch('bridge_live.connect_corridor') as build,patch.object(self.client,'request') as native:
            s=execute_multitrack_connection(self.client,p);self.assertEqual(s['status'],'reconciliation_required');build.assert_not_called();native.assert_not_called()
        self.client.journal.write_text('{}');old=self.root/'old.json';old.write_text(json.dumps({'plan':p,'summary':{'game_constructed':'unknown'},'chains':{},'unfinished_step':'U1'}))
        with patch('bridge_live.connect_corridor') as build,patch.object(self.client,'request') as native:
            s=execute_multitrack_connection(self.client,p,continuation_record=old);self.assertEqual(s['status'],'reconciliation_required');build.assert_not_called();native.assert_not_called()
        old.write_text(json.dumps({'plan':p,'summary':{'game_constructed':False},'chains':{p['tracks'][0]['id']:{'edges':[100],'nodes':[20,21]}}}))
        with patch('bridge_live.connect_corridor') as build,patch.object(self.client,'request') as native:
            s=execute_multitrack_connection(self.client,p,continuation_record=old);self.assertEqual(s['status'],'reconciliation_required');build.assert_not_called();native.assert_not_called()

    def test_read_only_partial_inspection_and_offline_cli(self):
        from bridge_parallel import plan_multitrack_connection,inspect_multitrack_connection
        p=plan_multitrack_connection(self.brief());ports,chains=self.state(p);path=self.root/'partial.json';path.write_text(json.dumps({'plan':p,'ports':ports,'chains':{p['tracks'][0]['id']:chains[p['tracks'][0]['id']]},'summary':{'game_constructed':'unknown'}}));before=path.read_bytes()
        r={'ports':ports,'chains':chains}
        with patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch.object(self.client,'request',side_effect=lambda op,q:self.native_read(p,r,op,q)),patch('bridge_live.connect_corridor') as build:
            s=inspect_multitrack_connection(self.client,path);self.assertEqual(s['status'],'multitrack_incomplete');self.assertEqual(s['routes_verified'],1);self.assertFalse(s['game_constructed']);build.assert_not_called()
        self.assertEqual(path.read_bytes(),before)

    def test_stale_named_port_and_unknown_saved_chain_reject(self):
        from bridge_parallel import plan_multitrack_connection,_multitrack_ports,_verify_multitrack
        p=plan_multitrack_connection(self.brief());ports,chains=self.state(p);old=json.loads(json.dumps(ports));first=next(iter(ports));ports[first]['node_id']+=500
        with patch('bridge_live._select_throat_port',side_effect=lambda c,e,**kw:(next(v for k,v in ports.items() if e==p['ports'][k]['endpoint']),'current')),self.assertRaises(LiveError):_multitrack_ports(self.client,p,{'ports':old},connected=True)
        with patch.object(self.client,'request') as native,self.assertRaises(ValueError):_verify_multitrack(self.client,p,{'ports':old,'chains':chains|{'unapproved':chains[p['tracks'][0]['id']]}})
        native.assert_not_called()
        b=self.root/'brief.json';b.write_text(json.dumps(self.brief()));stdout=io.StringIO()
        with patch('bridge_live.client_from_context') as client,contextlib.redirect_stdout(stdout):
            self.assertEqual(main(['multitrack-connection','--params',str(b),'--evidence',str(self.root/'plans')]),0);client.assert_not_called()
        self.assertLess(len(stdout.getvalue().encode()),4096)

    def test_explicit_acknowledged_prefix_continuation_skips_reference(self):
        from bridge_parallel import plan_multitrack_connection,execute_multitrack_connection
        p=plan_multitrack_connection(self.brief());ports,chains=self.state(p);first=p['tracks'][0]['id'];path=self.root/'prefix.json'
        path.write_text(json.dumps({'plan':p,'ports':ports,'chains':{first:chains[first]},'summary':{'game_constructed':True,'status':'native_verification_failed'}}));before=path.read_bytes();count=[0]
        def offset(op,q):
            self.assertEqual(op,'adjacent');count[0]+=1;chain=chains[p['tracks'][count[0]]['id']]
            return self.response(result={'game_constructed':True,'readback':{'ordered_edges':chain['edges'],'ordered_nodes':chain['nodes']}})
        with patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_parallel._verify_multitrack',return_value={'final_multitrack_verified':False}),patch('bridge_live._require_engineering_readback'),patch.object(self.client,'request',side_effect=offset),patch('bridge_live.connect_corridor') as build:
            s=execute_multitrack_connection(self.client,p,continuation_record=path);self.assertEqual(s['status'],'ok');self.assertEqual(count[0],3);build.assert_not_called()
        self.assertEqual(path.read_bytes(),before)

class BranchingCorridorTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    response=LiveClientTests.response

    def brief(self):
        return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/branching_corridor_example.json').read_text())

    def parent(self):
        from bridge_parallel import plan_multitrack_connection
        b=json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/multitrack_connection_example.json').read_text());p=plan_multitrack_connection(b);ports={};chains={}
        for i,t in enumerate(p['tracks']):
            nodes=[20+2*i,21+2*i];chains[t['id']]={'edges':[100+i],'nodes':nodes}
            for j,end in enumerate(('start','end')):
                key=t[end];q=p['ports'][key]['endpoint'];pos=q['guide_xyz'];d=q['travel_direction'];n=sum(x*x for x in d)**.5;outside=[pos[k]+(-20 if not j else 20)*(d[k]/n if k<2 else 0) for k in range(3)];a,z=(outside,pos) if not j else (pos,outside);delta=[z[k]-a[k] for k in range(3)]
                ports[key]={'edge_id':10+2*i+j,'node_id':nodes[j],'edge_snapshot':{'id':10+2*i+j,'p0':a,'p1':z,'t0':delta,'t1':delta,'node0':200+2*i+j if not j else nodes[j],'node1':nodes[j] if not j else 200+2*i+j,'template':'track','style':'style'}}
        return {'plan':p,'ports':ports,'chains':chains,'summary':{'status':'ok','game_constructed':True}}

    def plan(self):
        from bridge_branching import plan_branching_corridor
        parent=self.parent()
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')):return plan_branching_corridor(self.brief()),parent

    def ports(self,p):
        return {name:{'edge_id':400+i,'node_id':800+i,'edge_snapshot':{'id':400+i},'grade':0,'eligible':True} for i,name in enumerate(p['roles'])}

    def native(self,p,parent,ports,op,q):
        if op=='verify_adjacency':return self.response(result={'sampled_verified':True,'correspondence':[{'signed_normal':q['spacing']}],'curved_reference_chord_length':500})
        if op=='inspect':
            index=0 if 501 in q['edge_ids'] else 1
            return self.response(result={'edges':[{'id':e,'node0':900+index,'node1':999+e,'road_type':'TRACK'} for e in q['edge_ids']]})
        self.assertEqual(op,'route');self.assertTrue(q['geometry_constraints']['all_path']);self.assertEqual(q['geometry_constraints']['radius'],400)
        row=next(row for row in p['movements'] if ports[row['from']]['edge_id']==q['source_edge'] and ports[row['to']]['edge_id']==q['target_edge'])
        t=next(t for t in p['main']['tracks'] if t['id']==row['track']);core=parent['chains'][t['id']]['edges'];related=next((b for b in p['brief']['branches'] if b['track']==t['id']),None)
        ids=[q['source_edge']]+core
        ji=None
        if related:
            index=p['brief']['branches'].index(related);ji=900+index;ids.append(501+index)
            if row['kind']=='branch':ids.append(601+index)
        ids.append(q['target_edge'])
        return self.response(result={'requested_route_verified':True,'total_path_length':1700,'path':[{'confirmed_TRACK':True,'forward':t['forward'],'edge':{'entity':e},'from':{'entity':ji or 700},'to':{'entity':ji or 701}} for e in ids]})

    def chain(self,client,p,r,name):
        r.setdefault('current_chains',{})[name]={'inspection':{'result':{'edges':[{'id':e} for e in r['chains'][name]['edges']]}}}
        return [{'edge':{'id':e},'forward':True} for e in r['chains'][name]['edges']]

    def discovery(self,p,ports,q):
        b=next(b for b in p['brief']['branches'] if b['source']['region']==q['region']);index=p['brief']['branches'].index(b);t=next(t for t in p['main']['tracks'] if t['id']==b['track']);exit=t['end'] if t['forward'] else t['start']
        return self.response(result={'complete':True,'candidates':[{'node_id':900+index,'incidence_complete':True,'incident_count':3,'incident_edges':[501+index,601+index,ports[exit]['edge_id']]}]})

    def test_six_explicit_movements_and_distinct_shared_divergence(self):
        p,parent=self.plan();self.assertEqual(len(p['movements']),6);self.assertEqual(sum(x['kind']=='through' for x in p['movements']),4);self.assertEqual(len(p['roles']),10);self.assertEqual(len(p['junction_zones']),2)
        self.assertIn('excluded',p['shared_section']);self.assertFalse(p['game_constructed']);self.assertEqual(p['main'],parent['plan'])

    def test_zero_lead_names_original_tangent_and_retains_original_outer_role(self):
        from bridge_branching import plan_branching_corridor,_outer,_intent
        parent=self.parent();b=self.brief();row=b['branches'][1];stub=parent['ports']['D4:target']['edge_snapshot'];row['lead_length']=0;row['source']=_intent([(stub['p0'][k]+stub['p1'][k])/2 for k in range(3)],[-1,0])
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')):p=plan_branching_corridor(b)
        self.assertEqual(p['roles']['D4:target']['endpoint']['guide_xyz'],_outer(parent['ports']['D4:target']));self.assertEqual(p['roles']['D4:target']['sign'],-1)

    def test_invalid_direction_matrix_region_radius_and_junction_zone(self):
        from bridge_branching import plan_branching_corridor
        parent=self.parent()
        for kind in ('direction','movement','radius','region','location','inward','duplicate','lead'):
            b=self.brief()
            if kind=='direction':b['branches'][0]['source']['travel_direction']=[-1,0]
            elif kind=='movement':b['movements'][-1]['from']='U1:source'
            elif kind=='radius':b['radius']=120
            elif kind=='region':b['region']['max'][0]=-2000
            elif kind=='location':b['branches'][0]['source']['guide_xyz'][0]-=100
            elif kind=='inward':b['branches'][0]['target']['guide_xyz']=b['branches'][0]['source']['guide_xyz'][:]
            elif kind=='lead':b['branches'][0]['lead_length']=float('inf')
            else:b['branches'][1]['id']=b['branches'][0]['id']
            with self.subTest(kind=kind),patch('bridge_branching._parent',return_value=(parent,'known_hash')),self.assertRaises((ValueError,LiveError)):plan_branching_corridor(b)

    def test_replaced_approach_ids_are_reacquired_and_six_paths_cross_actual_forks(self):
        from bridge_branching import _assess
        p,parent=self.plan();ports=self.ports(p);r={}
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._roles',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_live._recipe_junction',side_effect=lambda c,e:(900+next(i for i,b in enumerate(p['brief']['branches']) if b['source']==e),['current'])),patch('bridge_live.discover',side_effect=lambda c,q:self.discovery(p,ports,q)),patch.object(self.client,'request',side_effect=lambda op,q:self.native(p,parent,ports,op,q)):
            s=_assess(self.client,p,r)
        self.assertTrue(s['final_network_verified']);self.assertEqual(s['routes_verified'],6);self.assertEqual(s['junctions_verified'],2);self.assertEqual(len(r['retained_spacing']),5)
        self.assertEqual(len(r['semantic_attachment_reconciliation']['changed_main_approach_handles']),8);self.assertFalse(r['semantic_attachment_reconciliation']['original_stage_receipt_fresh'])

    def test_missing_core_direction_and_wrong_fork_reject(self):
        from bridge_branching import _assess
        p,parent=self.plan();ports=self.ports(p)
        for kind in ('core','direction','fork'):
            def request(op,q):
                v=self.native(p,parent,ports,op,q)
                if op=='route':
                    if kind=='core':v['result']['path']=[v['result']['path'][0],v['result']['path'][-1]]
                    elif kind=='direction':v['result']['path'][1]['forward']=not v['result']['path'][1]['forward']
                    else:
                        for x in v['result']['path']:x['from']['entity']=1;x['to']['entity']=2
                return v
            with self.subTest(kind=kind),patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._roles',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_live._recipe_junction',side_effect=lambda c,e:(900+next(i for i,b in enumerate(p['brief']['branches']) if b['source']==e),['current'])),patch('bridge_live.discover',side_effect=lambda c,q:self.discovery(p,ports,q)),patch.object(self.client,'request',side_effect=request),self.assertRaises(LiveError):_assess(self.client,p,{})

    def test_partial_fresh_inspection_keeps_four_through_and_never_builds(self):
        from bridge_branching import inspect_branching_corridor
        p,parent=self.plan();ports={k:v for k,v in self.ports(p).items() if k not in ('branch_up','branch_down')};path=self.root/'branching.json';path.write_text(json.dumps({'plan':p,'summary':{'game_constructed':'unknown'}}));before=path.read_bytes()
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._roles',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_live._recipe_junction',side_effect=LiveError('recipe_state_unknown','no junction')),patch.object(self.client,'request',side_effect=lambda op,q:self.native(p,parent,ports,op,q)),patch('bridge_live.connect_junction_at') as build:
            s=inspect_branching_corridor(self.client,path);self.assertEqual(s['status'],'branching_incomplete');self.assertEqual(s['routes_verified'],4);self.assertFalse(s['game_constructed']);build.assert_not_called()
        self.assertEqual(path.read_bytes(),before)

    def test_pending_and_existing_fixture_stop_without_replay(self):
        from bridge_branching import execute_branching_corridor
        p,parent=self.plan();self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_live.connect_junction_at') as build,patch.object(self.client,'request') as native:
            s=execute_branching_corridor(self.client,p);self.assertEqual(s['status'],'reconciliation_required');native.assert_not_called();build.assert_not_called()
        self.client.journal.write_text('{}')
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_parallel.inspect_multitrack_connection',return_value={'status':'ok'}),patch('bridge_branching._roles',return_value=self.ports(p)),patch('bridge_live.connect_junction_at') as build,patch.object(self.client,'request') as native:
            s=execute_branching_corridor(self.client,p);self.assertEqual(s['status'],'reconciliation_required');native.assert_not_called();build.assert_not_called()

    def test_integrated_build_and_second_branch_unknown_remains_visible(self):
        from bridge_branching import execute_branching_corridor
        p,parent=self.plan();ports={k:v for k,v in self.ports(p).items() if k not in ('branch_up','branch_down','U1:target','D4:target')}
        for failure in (False,True):
            count=[0]
            def fixture(op,q):
                self.assertEqual(op,'test_approach');box=q['fixture']['region'];pos=q['fixture']['position'];d=q['fixture']['travel_direction'];n=sum(x*x for x in d)**.5
                for k in range(3):
                    self.assertLessEqual(box['max'][k]-box['min'][k],100);self.assertGreaterEqual(box['min'][k],p['brief']['region']['min'][k]);self.assertLessEqual(box['max'][k],p['brief']['region']['max'][k]);self.assertTrue(box['min'][k]<=pos[k]+20*(d[k]/n if k<2 else 0)<=box['max'][k])
                return self.response(result={'game_constructed':True})
            def branch(c,b,**kw):
                count[0]+=1
                if failure and count[0]==2:return {'status':'mutation_unverified','game_constructed':'unknown','error':'partial'}
                return {'status':'ok','game_constructed':True,'placement':{'original_edge':888},'junction':{'node':900+count[0]}}
            def lead(c,b,**kw):
                self.assertTrue(kw['execute']);self.assertEqual(b['max_fit_attempts'],1);self.assertLessEqual(b['max_route_length'],800)
                self.assertEqual(b['radius'],400);return {'status':'ok','game_constructed':True,'edges':[888]}
            with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_parallel.inspect_multitrack_connection',return_value={'status':'ok'}),patch('bridge_branching._roles',return_value=ports),patch('bridge_live._select_throat_port',return_value=({'edge_id':888},'current')),patch.object(self.client,'request',side_effect=fixture),patch('bridge_live.connect_brief',side_effect=lead) as leads,patch('bridge_live.connect_junction_at',side_effect=branch),patch('bridge_branching._assess',return_value={'final_network_verified':True,'routes_verified':6}):
                s=execute_branching_corridor(self.client,p);self.assertEqual(count[0],2)
                self.assertEqual(leads.call_count,2)
                if failure:self.assertEqual(s['game_constructed'],'unknown');self.assertEqual(json.loads(Path(s['evidence']).read_text())['unfinished_step'],'branch_down')
                else:self.assertEqual(s['status'],'ok')

    def test_native_junction_internal_transport_requires_exact_verified_junction_identity(self):
        from bridge_branching import _assess
        p,parent=self.plan();ports=self.ports(p)
        for wrong in (False,True):
            def request(op,q):
                r=self.native(p,parent,ports,op,q)
                if op=='route' and q['source_edge']==ports['U1:source']['edge_id']:
                    node=77 if wrong else 900;r['result']['path'].insert(-1,{'confirmed_TRACK':False,'edge':{'entity':node,'index':1},'from':{'entity':node,'index':0},'to':{'entity':node,'index':2},'forward':True})
                return r
            with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._roles',return_value=ports),patch('bridge_parallel._read_chain',side_effect=self.chain),patch('bridge_live._recipe_junction',side_effect=lambda c,e:(900+next(i for i,b in enumerate(p['brief']['branches']) if b['source']==e),['current'])),patch('bridge_live.discover',side_effect=lambda c,q:self.discovery(p,ports,q)),patch.object(self.client,'request',side_effect=request):
                if wrong:
                    with self.assertRaises(LiveError):_assess(self.client,p,{})
                else:self.assertTrue(_assess(self.client,p,{})['final_network_verified'])

    def test_explicit_acknowledged_lead_reuse_is_hash_bound_and_rechecked_before_mutation(self):
        from bridge_branching import _lead_brief,plan_branching_corridor,execute_branching_corridor
        parent=self.parent();b=self.brief();path=self.root/'lead.json';b['branches'][0]['lead_record']=str(path)
        expected=_lead_brief(parent,b,b['branches'][0]);receipt={'brief':expected,'summary':{'status':'ok','game_constructed':True,'native_route_verified':True,'edges':[888]}}
        path.write_text(json.dumps(receipt))
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')):p=plan_branching_corridor(b)
        ports={k:v for k,v in self.ports(p).items() if k not in ('branch_up','branch_down','D4:target')};self.client.journal.write_text('{}')
        rejected=self.response(result={'requested_route_verified':False});rejected['status']='error'
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_parallel.inspect_multitrack_connection',return_value={'status':'ok'}),patch('bridge_branching._roles',return_value=ports),patch.object(self.client,'request',return_value=rejected) as native,patch('bridge_live.connect_brief') as lead,patch('bridge_live.connect_junction_at') as branch:
            s=execute_branching_corridor(self.client,p);self.assertEqual(s['status'],'native_verification_failed');self.assertFalse(s['game_constructed']);self.assertEqual(native.call_count,1);self.assertEqual(native.call_args.args[0],'route');lead.assert_not_called();branch.assert_not_called()
        receipt['summary']['game_constructed']='unknown';path.write_text(json.dumps(receipt))
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),self.assertRaises(ValueError):plan_branching_corridor(b)

    def test_partial_continuation_proves_completed_branch_and_freezes_its_intent(self):
        from bridge_branching import _continuation
        p,parent=self.plan();path=self.root/'partial.json';old={'plan':p,'completed_branches':['branch_up'],'summary':{'game_constructed':'unknown'}}
        path.write_text(json.dumps(old));ports=self.ports(p)
        def fresh(c,plan,r,**kw):
            r.update(current_roles=ports,current_junctions={'branch_up':900},routes=[x|{'verified':x['kind']=='through' or x['to']=='branch_up'} for x in p['movements']]);return {'routes_verified':5}
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._assess',side_effect=fresh),patch.object(self.client,'request') as mutation:
            r={};actual=_continuation(self.client,p,r,path);self.assertEqual(actual[2],{'branch_up'});self.assertFalse(r['continuation']['automatic_replay']);mutation.assert_not_called()
            changed=json.loads(json.dumps(p));changed['brief']['branches'][0]['target']['guide_xyz'][0]+=1
            with self.assertRaises(ValueError):_continuation(self.client,changed,{},path)

    def test_partial_continuation_rejects_stale_or_unclaimed_junctions(self):
        from bridge_branching import _continuation
        p,parent=self.plan();path=self.root/'partial.json';path.write_text(json.dumps({'plan':p,'completed_branches':['branch_up'],'summary':{}}))
        for wrong in ('through','branch','extra'):
            def fresh(c,plan,r,**kw):
                r.update(current_roles=self.ports(p),current_junctions={'branch_up':900},routes=[x|{'verified':x['kind']=='through' or x['to']=='branch_up'} for x in p['movements']])
                if wrong=='through':r['routes'][0]['verified']=False
                elif wrong=='branch':r['routes'][-2]['verified']=False
                else:r['current_junctions']['branch_down']=901
                return {}
            with self.subTest(wrong=wrong),patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._assess',side_effect=fresh),self.assertRaises(LiveError):_continuation(self.client,p,{},path)

    def test_continuation_executes_only_unfinished_branch_without_original_stage_replay(self):
        from bridge_branching import execute_branching_corridor
        p,parent=self.plan();ports={k:v for k,v in self.ports(p).items() if k not in ('branch_down','D4:target')}
        def adopt(c,plan,r,path):r['completed_branches']=['branch_up'];return ports,[900],{'branch_up'}
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._continuation',side_effect=adopt),patch('bridge_parallel.inspect_multitrack_connection') as original,patch.object(self.client,'request',return_value=self.response(result={'game_constructed':True})) as fixtures,patch('bridge_live._select_throat_port',return_value=({'edge_id':888},'current')),patch('bridge_live.connect_brief',return_value={'status':'ok','game_constructed':True,'edges':[888]}) as lead,patch('bridge_live.connect_junction_at',return_value={'status':'ok','game_constructed':True,'placement':{'original_edge':888},'junction':{'node':901}}) as branch,patch('bridge_branching._assess',return_value={'final_network_verified':True,'routes_verified':6}):
            s=execute_branching_corridor(self.client,p,continuation_record='explicit.json');self.assertEqual(s['status'],'ok');original.assert_not_called();self.assertEqual(lead.call_count,1);self.assertEqual(branch.call_count,1);self.assertEqual(branch.call_args.args[1]['source'],p['brief']['branches'][1]['source']);self.assertEqual(fixtures.call_count,2)

    def test_road_clearance_is_always_mutation_and_native_guards_exact_site(self):
        from bridge_live import is_mutation
        self.assertTrue(is_mutation('clear_obstructions',{}))
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        block=source.split('function M.clear_obstructions',1)[1].split('-- Native normal-offset',1)[0]
        for guard in ('p.authorised==true','#p.edges<=8','q.TRACK==false','e.roadType~=E.RoadType.TRACK','stale_clearance_identity','stale_clearance_geometry','in_region(q.p0,p.region)','makeSegmentsRemoveProposal(ids)','road_removal_unverified'):
            self.assertIn(guard,block)
        self.assertIn('makeWorldBuildProposalCmd(proposal,nil,false,false)',block)

class CompleteLayoutTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    response=LiveClientTests.response

    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/complete_layout_example.json').read_text())

    def plan(self):
        from bridge_complete import plan_complete_layout
        return plan_complete_layout(self.brief())

    def test_portable_offline_plan_has_no_historical_receipt_dependency(self):
        from bridge_complete import plan_complete_layout,publish_complete_layout
        with patch('bridge_live.client_from_context') as client,patch('bridge_branching._parent') as historical:
            p=self.plan();s=publish_complete_layout(p,self.root/'plans');self.assertEqual(s['status'],'ok');client.assert_not_called();historical.assert_not_called()
        self.assertEqual(len(p['fixtures']),12);self.assertEqual(len(p['movements']),6);self.assertNotIn('main_record',p['brief']);self.assertEqual([t['direction'] for t in p['main_plan']['tracks']],['UP','UP','DOWN','DOWN'])
        params=self.root/'brief.json';params.write_text(json.dumps(self.brief()));out=io.StringIO()
        with patch('bridge_live.client_from_context') as client,contextlib.redirect_stdout(out):self.assertEqual(main(['complete-layout','--params',str(params),'--evidence',str(self.root/'plans')]),0);client.assert_not_called()
        self.assertLess(len(out.getvalue().encode()),4096)

    def test_translation_rotation_and_opposing_directions_preserve_layout_relationships(self):
        import math
        from bridge_complete import plan_complete_layout
        b=self.brief();p=self.plan()
        def xyz(v):return [-v[1]+250,v[0]+500,v[2]]
        def direction(v):return [-v[1],v[0]]
        for key in ('start','finish'):
            b['reference'][key]['position']=xyz(b['reference'][key]['position']);b['reference'][key]['travel_direction']=direction(b['reference'][key]['travel_direction'])
        for g in b['reference']['guides']:g['position']=xyz(g['position']);g['travel_direction']=direction(g['travel_direction'])
        for r in b['branches']:r['target']['position']=xyz(r['target']['position']);r['target']['travel_direction']=direction(r['target']['travel_direction'])
        corners=[xyz(b['region'][key]) for key in ('min','max')];b['region']={'min':[min(v[k] for v in corners) for k in range(3)],'max':[max(v[k] for v in corners) for k in range(3)]}
        q=plan_complete_layout(b)
        for a,z in zip(p['fixtures'],q['fixtures']):self.assertLess(math.dist(xyz(a['position']),z['position']),1e-9)
        self.assertEqual([t['forward'] for t in q['main_plan']['tracks']],[True,True,False,False])

    def test_invalid_domain_and_constraints_rejected_before_native_work(self):
        from bridge_complete import plan_complete_layout
        for kind in ('vertical','direction','branch','seed','scope','policy'):
            b=self.brief()
            if kind=='vertical':b['reference']['finish']['position'][2]+=1
            elif kind=='direction':b['tracks'][-1]['direction']='UP'
            elif kind=='branch':b['branches'][0]['split_fraction']=1
            elif kind=='seed':b['seed_edge']=True
            elif kind=='scope':b['region']['min'][0]=-3500
            else:b['site_policy']='demolish_world'
            with self.subTest(kind=kind),self.assertRaises((ValueError,LiveError)):plan_complete_layout(b)

    def test_stage_failure_is_durable_and_stops_before_main_or_branches(self):
        from bridge_complete import execute_complete_layout
        p=self.plan();calls=[]
        def request(op,q):
            calls.append(op)
            if op=='inspect':return self.response(result={'edges':[{'resource':{'track_distance':5}}]})
            self.assertEqual(op,'test_approach');return self.response(result={'game_constructed':'unknown','error':'partial'})|{'status':'mutation_unverified'}
        with patch('bridge_complete._site'),patch('bridge_live._select_throat_port',side_effect=LiveError('no_eligible_candidates','empty')),patch.object(self.client,'request',side_effect=request),patch('bridge_parallel.execute_multitrack_connection') as parent,patch('bridge_branching.execute_branching_corridor') as branch:
            s=execute_complete_layout(self.client,p);self.assertEqual(s['status'],'mutation_unverified');self.assertEqual(s['game_constructed'],'unknown');parent.assert_not_called();branch.assert_not_called()
        r=json.loads(Path(s['evidence']).read_text());self.assertEqual(r['unfinished_step'],'U1:source');self.assertEqual(r['fixtures']['U1:source']['status'],'mutation_unverified');self.assertEqual(len(calls),2)

    def test_complete_reexecution_only_checks_current_state_and_changed_brief_stops(self):
        from bridge_complete import execute_complete_layout
        p=self.plan();path=self.root/'done.json';path.write_text(json.dumps({'plan':p,'fixtures':{},'stages':{'main':{'status':'ok','evidence':'current'},'branches':{'status':'ok','evidence':'current'}},'summary':{'status':'ok','game_constructed':True}}))
        with patch('bridge_complete._inspect',return_value={'status':'ok','routes_verified':6,'junctions_verified':2,'final_network_verified':True}),patch.object(self.client,'request') as native,patch('bridge_branching.execute_branching_corridor') as branch:
            s=execute_complete_layout(self.client,p,continuation_record=path);self.assertTrue(s['checked_existing']);self.assertFalse(s['game_constructed']);native.assert_not_called();branch.assert_not_called()
        changed=json.loads(json.dumps(p));changed['plan_hash']='changed'
        with patch('bridge_complete.plan_complete_layout',return_value=changed),patch.object(self.client,'request') as native:
            s=execute_complete_layout(self.client,changed,continuation_record=path);self.assertEqual(s['status'],'invalid_result');native.assert_not_called()

    def test_interrupted_and_pending_work_never_replays(self):
        from bridge_complete import execute_complete_layout
        p=self.plan();path=self.root/'interrupted.json';path.write_text(json.dumps({'plan':p,'fixtures':{},'stages':{},'unfinished_step':'main','summary':{'game_constructed':'unknown'}}))
        with patch('bridge_complete._inspect',return_value={'status':'complete_layout_incomplete'}),patch.object(self.client,'request') as native:
            s=execute_complete_layout(self.client,p,continuation_record=path);self.assertEqual(s['status'],'reconciliation_required');native.assert_not_called()
        self.client.journal.write_text(json.dumps({'pending':{'request_id':'unknown'}}))
        with patch.object(self.client,'request') as native:
            s=execute_complete_layout(self.client,p);self.assertEqual(s['status'],'reconciliation_required');native.assert_not_called()

    def test_site_bounds_nontrack_terrain_and_truncation_fail_honestly(self):
        from bridge_complete import _site,_boxes
        p=self.plan();box=_boxes(p,[[[-3200,-2900,33],[-3220,-2900,33]]]);self.assertTrue(all(max(b['max'][k]-b['min'][k] for k in range(3))<=400 for b in box))
        seen=[]
        def request(op,q):
            seen.append(q);self.assertEqual(op,'inspect');return self.response(result={'site':{'truncated':True,'entities':[],'terrain':[]}})
        with patch.object(self.client,'request',side_effect=request),self.assertRaises(LiveError):_site(self.client,p,{'summary':{}},'fixture',[[[-3200,-2900,33]]],mutate=True)
        self.assertIn('site',seen[0]);self.assertEqual(len(seen[0]['site']['positions']),1)

    def test_fresh_inspection_delegates_semantic_replacement_and_never_builds(self):
        from bridge_complete import inspect_complete_layout
        p=self.plan();path=self.root/'complete.json';path.write_text(json.dumps({'plan':p,'fixtures':{},'stages':{'main':{'evidence':'new_main'},'branches':{'evidence':'new_branches'}},'summary':{}}));before=path.read_bytes()
        current={'routes_verified':6,'junctions_verified':2,'final_network_verified':True,'retained_spacing_verified':True,'status':'ok'}
        with patch('bridge_complete._branch_plan',return_value={'current':'intent'}),patch('bridge_live._load_layout_record',side_effect=[json.loads(before),{'plan':{'current':'intent'}}]),patch('bridge_branching.inspect_branching_corridor',return_value=current) as inspect,patch('bridge_branching.execute_branching_corridor') as build:
            s=inspect_complete_layout(self.client,path);self.assertEqual(s['status'],'ok');self.assertFalse(s['game_constructed']);inspect.assert_called_once_with(self.client,'new_branches');build.assert_not_called()
        self.assertEqual(path.read_bytes(),before)

    def test_successful_composition_and_acknowledged_fixture_continuation(self):
        from bridge_complete import execute_complete_layout
        p=self.plan();prior=self.root/'fixtures.json'
        ack={f['name']:self.response(result={'game_constructed':True}) for f in p['fixtures'][:3]}
        prior.write_text(json.dumps({'plan':p,'fixtures':ack,'stages':{},'summary':{'game_constructed':True}}))
        built=[];sites=[]
        def request(op,q):
            if op=='inspect':return self.response(result={'edges':[{'resource':{'track_distance':5}}]})
            self.assertEqual(op,'test_approach');built.append(q['fixture']['position']);return self.response(result={'game_constructed':True})
        def inspect(c,plan,r):return {'status':'ok','routes_verified':6,'junctions_verified':2,'retained_spacing_verified':True,'final_network_verified':True} if 'branches' in r['stages'] else {'status':'complete_layout_incomplete'}
        def branch(c,plan,**kw):
            kw['before_build']('native_branch',{'status':'ok'})
            return {'status':'ok','evidence':'branches','game_constructed':True}
        with patch('bridge_complete._inspect',side_effect=inspect),patch('bridge_complete._site',side_effect=lambda c,p,r,n,f,**kw:sites.append(n)),patch('bridge_complete._controls',return_value=[[[0,0,33],[1,0,33]]]),patch('bridge_live._select_throat_port',side_effect=LiveError('no_eligible_candidates','empty')),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'ok'}),patch('bridge_parallel.execute_multitrack_connection',return_value={'status':'ok','evidence':'main','game_constructed':True}) as main,patch('bridge_complete._branch_plan',return_value={'generated':'current main'}),patch('bridge_branching.execute_branching_corridor',side_effect=branch):
            result=execute_complete_layout(self.client,p,continuation_record=prior)
        self.assertEqual(result['status'],'ok');self.assertEqual(result['routes_verified'],6);self.assertEqual(result['fixtures_acknowledged'],8);self.assertEqual(len(built),5)
        self.assertEqual(built,[f['position'] for f in p['fixtures'][3:8]])
        self.assertIn('native_main_candidate',sites);self.assertIn('native_branch',sites);main.assert_called_once()
        self.assertEqual(json.loads(prior.read_text())['fixtures'],ack)

    def test_prepared_branch_fixture_adoption_requires_exact_current_receipt(self):
        from bridge_branching import _adopt_prepared_fixture
        e={'id':42,'node0':7,'node1':8,'template':3,'style':0,'p0':[0,0,33],'p1':[20,0,33],'t0':[20,0,0],'t1':[20,0,0]}
        receipt=self.response(result={'game_constructed':True,'edges':[e]})
        with patch.object(self.client,'request',return_value=self.response(result={'edges':[e]})) as request:
            _adopt_prepared_fixture(self.client,receipt);request.assert_called_once_with('inspect',{'edge_ids':[42]})
        changed=e|{'node1':9}
        with patch.object(self.client,'request',return_value=self.response(result={'edges':[changed]})),self.assertRaises(LiveError):_adopt_prepared_fixture(self.client,receipt)
        with patch.object(self.client,'request') as request,self.assertRaises(LiveError):_adopt_prepared_fixture(self.client,receipt|{'status':'mutation_unverified'});request.assert_not_called()

    def test_dense_site_is_subdivided_with_finite_budget(self):
        from bridge_complete import _site
        p=self.plan();calls=[]
        def request(op,q):
            calls.append(q['site']['region']);return self.response(result={'site':{'truncated':len(calls)==1,'entities':[],'terrain':[]}})
        record={'summary':{}}
        with patch.object(self.client,'request',side_effect=request):r=_site(self.client,p,record,'dense',[[[-3200,-2900,33]]],mutate=False)
        self.assertTrue(r['truncated']);self.assertGreater(len(calls),1);self.assertLess(len(calls),256)
        self.assertTrue(any(b['max'][0]-b['min'][0]<=125 for b in calls))

    def test_inspection_receipt_cannot_discard_interruption_history_for_continuation(self):
        from bridge_complete import execute_complete_layout
        p=self.plan();path=self.root/'inspect.json';path.write_text(json.dumps({'plan':p,'fixtures':{},'stages':{},'summary':{'operation':'complete-layout-inspect','game_constructed':False}}))
        with patch.object(self.client,'request') as native:
            result=execute_complete_layout(self.client,p,continuation_record=path)
        self.assertEqual(result['status'],'invalid_result');native.assert_not_called()

    def test_native_fit_controls_are_preserved_for_site_bounds(self):
        from bridge_complete import _controls
        rid='site_fit';control={'p0':[0,0,33],'p1':[100,20,33],'t0':[90,0,0],'t1':[90,30,0]}
        (self.client.evidence/(rid+'.response.json')).write_text(json.dumps({'result':{'fit':{'controls':[control]}}}))
        self.assertEqual(_controls(self.client,{'status':'ok','native_request_id':rid}),[[[0,0,33],[30,0,33],[70,10,33],[100,20,33]]])
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        self.assertIn('fit.controls=all.controls',source)
        self.assertNotIn('controls=profile and controls or nil',source)

class GradedParallelTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    response=LiveClientTests.response

    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/graded_multitrack_connection_example.json').read_text())

    def test_explicit_shared_height_mode_composes_four_tracks_without_native_calls(self):
        from bridge_parallel import plan_multitrack_connection
        with patch('bridge_live.client_from_context') as native:p=plan_multitrack_connection(self.brief());native.assert_not_called()
        self.assertEqual(p['pattern'],'UP-UP-DOWN-DOWN');self.assertEqual([t['forward'] for t in p['tracks']],[True,True,False,False])
        self.assertEqual(p['reference']['source']['guide_xyz'][2],33);self.assertEqual(p['reference']['target']['guide_xyz'][2],39);self.assertEqual(p['reference']['guides'][0]['grade'],.012)

    def test_nonlevel_mode_cannot_relax_normal_endpoints_or_grade_limits(self):
        from bridge_parallel import plan_multitrack_connection
        for bad in ('mode','height','grade','direction','tolerance','missing_tolerance'):
            b=self.brief()
            if bad=='mode':b['vertical_mode']='anything'
            elif bad=='height':b['tracks'][1]['target']['endpoint']['guide_xyz'][2]+=.01
            elif bad=='grade':b['guides'][0]['grade']=.041
            elif bad=='tolerance':b['vertical_tolerance']=.051
            elif bad=='missing_tolerance':b.pop('vertical_tolerance')
            else:b['tracks'][2]['source']['endpoint']['travel_direction']=[1,0]
            with self.subTest(bad=bad),self.assertRaises((ValueError,LiveError)):plan_multitrack_connection(b)

    def test_pair_inherits_explicit_vertical_budget_and_default_level_stays_closed(self):
        from bridge_parallel import plan_paired_connection,plan_multitrack_connection
        b=self.brief();b['tracks']=b['tracks'][:2];b['tracks'][1]['direction']='DOWN';b['tracks'][1]['source'],b['tracks'][1]['target']=b['tracks'][1]['target'],b['tracks'][1]['source']
        for key in ('source','target'):b['tracks'][1][key]['endpoint']['travel_direction']=[-x for x in b['tracks'][1][key]['endpoint']['travel_direction']]
        p=plan_multitrack_connection(b);self.assertEqual(p['pattern'],'UP-DOWN')
        pair={k:v for k,v in b.items() if k not in ('tracks','reference_up','layout')};pair.update(layout='native_offset_connection_v1',ports={'up_source':b['tracks'][0]['source'],'up_target':b['tracks'][0]['target'],'down_source':b['tracks'][1]['source'],'down_target':b['tracks'][1]['target']})
        self.assertEqual(plan_paired_connection(pair)['brief']['vertical_tolerance'],.05)
        pair.pop('vertical_mode');pair.pop('vertical_tolerance')
        with self.assertRaises(LiveError):plan_paired_connection(pair)

    def test_nonzero_endpoint_grade_cannot_enter_level_branching_workflow(self):
        from bridge_branching import plan_branching_corridor
        parent=BranchingCorridorTests.parent(self);parent['plan']['brief'].update(vertical_mode='native_shared_height_v1',vertical_tolerance=.05)
        for port in parent['ports'].values():port['grade']=0
        next(iter(parent['ports'].values()))['grade']=.005
        b=BranchingCorridorTests.brief(self)
        with patch('bridge_branching._parent',return_value=(parent,'hash')),self.assertRaises(LiveError):plan_branching_corridor(b)

    def test_actual_endpoint_grades_are_checked_in_construction_frame(self):
        from bridge_parallel import plan_multitrack_connection,_multitrack_ports
        p=plan_multitrack_connection(self.brief())
        def observed(c,e,**kw):
            i=next(i for i,x in enumerate(p['ports'].values()) if x['endpoint']==e)
            return {'edge_id':100+i,'node_id':200+i,'grade':.005*kw['outward_sign'],'edge_snapshot':{}},'current'
        with patch('bridge_live._select_throat_port',side_effect=observed):r={};ports=_multitrack_ports(self.client,p,r,connected=False)
        self.assertEqual(len(ports),8);self.assertTrue(any(c['grade']<0 for c in ports.values()))
        with patch('bridge_live._select_throat_port',return_value=({'edge_id':1,'node_id':2,'grade':.041},'current')),self.assertRaises(LiveError):_multitrack_ports(self.client,p,{},connected=False)

    def test_native_offset_keeps_height_grade_and_joins_binding(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text();block=source.split('function M.adjacent',1)[1].split('local function region_check',1)[0]
        self.assertNotIn('adjacent_level_only',block)
        for required in ('offset_boundary_grade_incompatible','dz<=ztol','math.abs(slope(c.t0)-slope(controls[i-1].t1))<=.000001','grade=slope(controls[1].t0)','end_grade=slope(controls[#controls].t1)'):self.assertIn(required,block)
        self.assertNotIn('region=p.region,grade=0,end_grade=0',block)

    def test_current_readback_rejects_grade_join_and_real_attachment_mismatch(self):
        from bridge_parallel import plan_multitrack_connection,_vertical_readback
        p=plan_multitrack_connection(self.brief())
        a={'p0':[0,0,33],'p1':[100,0,34],'t0':[100,0,.5],'t1':[100,0,1]}
        b={'p0':[100,0,34],'p1':[200,0,35],'t0':[100,0,1],'t1':[100,0,.3]}
        start={'grade':.005,'node_id':1,'edge_snapshot':{'node0':0,'p0':[-20,0,32.9],'p1':[0,0,33]}}
        end={'grade':-.003,'node_id':2,'edge_snapshot':{'node0':2,'p0':[200,0,35],'p1':[220,0,35.06]}}
        _vertical_readback(p,[{'edge':a},{'edge':b}],start,end)
        for key in ('join','endpoint','height'):
            altered=json.loads(json.dumps(b))
            if key=='join':altered['t0'][2]+=.01
            elif key=='endpoint':altered['t1'][2]+=.01
            else:altered['p1'][2]+=.01
            with self.subTest(key=key),self.assertRaises(LiveError):_vertical_readback(p,[{'edge':a},{'edge':altered}],start,end)

    def test_graded_offset_failure_keeps_reference_and_does_not_retry(self):
        from bridge_parallel import plan_multitrack_connection,execute_multitrack_connection
        p=plan_multitrack_connection(self.brief());ports,chains=MultitrackConnectionTests.state(self,p);t=p['tracks'][0]
        first={'status':'ok','game_constructed':True,**chains[t['id']],'selected':{'source_edge':ports[t['start']]['edge_id'],'source_node':ports[t['start']]['node_id'],'target_edge':ports[t['end']]['edge_id'],'target_node':ports[t['end']]['node_id']}}
        def request(op,q):
            self.assertEqual(op,'adjacent');self.assertEqual(q['vertical_mode'],'native_shared_height_v1');self.assertEqual(q['vertical_tolerance'],.05)
            return self.response(result={'game_constructed':False,'error':'native_offset_conversion_failed'})|{'status':'error'}
        with patch('bridge_parallel._multitrack_ports',return_value=ports),patch('bridge_live.connect_corridor',return_value=first),patch('bridge_parallel._read_chain',side_effect=lambda c,p,r,n:MultitrackConnectionTests.chain(self,c,p,r,n)),patch('bridge_parallel._verify_multitrack',return_value={'final_multitrack_verified':False}),patch.object(self.client,'request',side_effect=request) as calls:
            result=execute_multitrack_connection(self.client,p)
        self.assertEqual(calls.call_count,1);self.assertTrue(result['game_constructed']);self.assertEqual(result['completed_connectors'],['U1']);self.assertFalse(result['final_multitrack_verified'])
        r=json.loads(Path(result['evidence']).read_text());self.assertEqual(r['unfinished_step'],'U2');self.assertEqual(r['operations'][-1]['response']['result']['game_constructed'],False)

class GradedCompleteLayoutTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    response=LiveClientTests.response
    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/graded_complete_layout_example.json').read_text())
    def plan(self):
        from bridge_complete import plan_complete_layout
        return plan_complete_layout(self.brief())

    def test_fresh_brief_forwards_grading_and_keeps_local_fixtures_level(self):
        from bridge_complete import _fixture_params
        with patch('bridge_live.client_from_context') as client:p=self.plan();client.assert_not_called()
        self.assertEqual(p['main_plan']['brief']['vertical_tolerance'],.05)
        self.assertEqual(p['main_plan']['reference']['guides'][0]['grade'],.012)
        self.assertEqual({f['position'][2] for f in p['fixtures']},{33,39})
        for f in p['fixtures']:self.assertEqual(_fixture_params(p,f)['fixture']['grade'],0)
        self.assertEqual([b['source']['guide_xyz'][2] for b in p['branch_intents']],[39,33])
        self.assertEqual(len(p['movements']),6)

    def test_nonzero_endpoint_grade_bad_local_height_and_missing_mode_reject(self):
        from bridge_complete import plan_complete_layout
        for kind in ('slope','nan','height','mode','budget'):
            b=self.brief()
            if kind=='slope':b['reference']['start']['grade']=.001
            elif kind=='nan':b['reference']['finish']['grade']=float('nan')
            elif kind=='height':b['branches'][0]['target']['position'][2]=33
            elif kind=='mode':b.pop('vertical_mode');b.pop('vertical_tolerance')
            else:b['vertical_tolerance']=.06
            with self.subTest(kind=kind),self.assertRaises((LiveError,ValueError)):plan_complete_layout(b)

    def test_graded_partial_composition_adopts_only_acknowledged_fixtures(self):
        CompleteLayoutTests.test_successful_composition_and_acknowledged_fixture_continuation(self)

    def test_completed_graded_record_rechecks_without_rebuild_or_changed_brief(self):
        CompleteLayoutTests.test_complete_reexecution_only_checks_current_state_and_changed_brief_stops(self)

    def test_grade_domain_retains_fresh_level_forks_and_forwards_height_checks(self):
        import bridge_branching as branching
        parent=BranchingCorridorTests.parent(self);parent['plan']['brief'].update(vertical_mode='native_shared_height_v1',vertical_tolerance=.05)
        for port in parent['ports'].values():port['grade']=0
        b=BranchingCorridorTests.brief(self)
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')):p=branching.plan_branching_corridor(b)
        ports=BranchingCorridorTests.ports(self,p);record={}
        def native(op,q):
            result=BranchingCorridorTests.native(self,p,parent,ports,op,q)
            if op=='verify_adjacency':
                self.assertEqual(q['vertical_mode'],'native_shared_height_v1');self.assertEqual(q['vertical_tolerance'],.05)
                result['result']['max_sampled_height_difference']=.002
            if op=='inspect':
                for e in result['result']['edges']:e.update(p0=[0,0,33],p1=[20,0,33],t0=[20,0,.01 if getattr(self,'bad_junction',False) else 0],t1=[20,0,0])
            return result
        with patch('bridge_branching._parent',return_value=(parent,'known_hash')),patch('bridge_branching._roles',return_value=ports),patch('bridge_parallel._read_chain',side_effect=lambda c,p,r,n:BranchingCorridorTests.chain(self,c,p,r,n)),patch('bridge_parallel._vertical_readback') as vertical,patch('bridge_live._recipe_junction',side_effect=lambda c,e:(900+next(i for i,b in enumerate(p['brief']['branches']) if b['source']==e),['current'])),patch('bridge_live.discover',side_effect=lambda c,q:BranchingCorridorTests.discovery(self,p,ports,q)),patch.object(self.client,'request',side_effect=native):
            result=branching._assess(self.client,p,record)
        self.assertEqual(vertical.call_count,4);self.assertTrue(result['final_network_verified']);self.assertEqual(result['max_sampled_height_difference'],.002)
        self.assertIn('level local',result['junction_geometry'])

    def test_nonlevel_current_fork_rejects_even_when_core_and_native_paths_pass(self):
        self.bad_junction=True
        with self.assertRaises(LiveError):self.test_grade_domain_retains_fresh_level_forks_and_forwards_height_checks()

    def test_elevation_intent_changes_hash_without_flattening_or_direction_reversal(self):
        from bridge_complete import plan_complete_layout
        p=self.plan();b=self.brief();b['reference']['finish']['position'][2]=40;b['branches'][0]['target']['position'][2]=40
        q=plan_complete_layout(b);self.assertNotEqual(p['plan_hash'],q['plan_hash']);self.assertEqual(q['main_plan']['reference']['target']['guide_xyz'][2],40)
        self.assertEqual([t['forward'] for t in q['main_plan']['tracks']],[True,True,False,False])

    def test_failed_graded_fixture_never_advances_to_main_or_branching(self):
        CompleteLayoutTests.test_stage_failure_is_durable_and_stops_before_main_or_branches(self)

    def test_changed_endpoint_tangent_rejects_parent_before_any_native_call(self):
        from bridge_branching import plan_branching_corridor
        parent=BranchingCorridorTests.parent(self);parent['plan']['brief'].update(vertical_mode='native_shared_height_v1',vertical_tolerance=.05)
        for port in parent['ports'].values():port['grade']=0
        next(iter(parent['ports'].values()))['edge_snapshot']['t0'][2]=.01
        with patch('bridge_branching._parent',return_value=(parent,'hash')),self.assertRaises(LiveError):plan_branching_corridor(BranchingCorridorTests.brief(self))

class DirectionalCompleteLayoutTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    response=LiveClientTests.response
    def brief(self,key='ud'):return json.loads((Path(__file__).resolve().parents[1]/f'implementation/live_python_interface/{key}_complete_layout_example.json').read_text())
    def plan(self):
        from bridge_complete import plan_complete_layout
        return plan_complete_layout(self.brief())
    def variants(self):
        import math
        for directions in (('UP','DOWN'),('UP','UP','DOWN','DOWN'),('UP','DOWN','UP','DOWN')):
            for up in ('increasing','decreasing'):
                for side in ('left','right'):
                    b=CompleteLayoutTests.brief(self);b['tracks']=[{'id':f'T{i+1}','direction':d} for i,d in enumerate(directions)];b['reference_up']=up;b['side']=side
                    branches=[];sign=1 if side=='left' else -1
                    for i in (0,len(directions)-1):
                        forward=(directions[i]=='UP')==(up=='increasing');end=b['reference']['finish' if forward else 'start'];d=end['travel_direction'];n=math.hypot(*d);d=[x/n for x in d];normal=[-d[1],d[0]];pos=[end['position'][k]+i*5*sign*normal[k] for k in range(2)]+[33];out=d if forward else [-v for v in d];lead=400 if forward else 200;long=450 if forward else 700;lateral=(100 if forward else 80)*sign*(1 if i==len(directions)-1 else -1)
                        q=[pos[k]+(20+lead/2+long)*out[k]+lateral*normal[k] for k in range(2)]+[33]
                        branches.append({'id':'branch_'+str(i),'track':b['tracks'][i]['id'],'lead_length':lead,'split_fraction':.5,'target':{'position':q,'travel_direction':out}})
                    b['branches']=branches;b['region']={'min':[-4400,-3300,-20],'max':[-1400,-1600,80]}
                    yield b
                    graded=json.loads(json.dumps(b));graded.update(vertical_mode='native_shared_height_v1',vertical_tolerance=.05);graded['reference']['finish']['position'][2]=39;graded['reference']['guides'][0]['position'][2]=36;graded['reference']['guides'][0]['grade']=.012
                    for branch in graded['branches']:
                        t=next(t for t in graded['tracks'] if t['id']==branch['track']);forward=(t['direction']=='UP')==(up=='increasing');branch['target']['position'][2]=39 if forward else 33
                    yield graded
    def parent(self,p):
        fixtures={f['name']:f for f in p['fixtures']};ports={};chains={};main=p['main_plan']
        for i,t in enumerate(main['tracks']):
            chains[t['id']]={'edges':[100+i],'nodes':[200+i*2,201+i*2]}
            for j,key in enumerate((t['start'],t['end'])):
                f=fixtures[key];a=f['position'];d=f['travel_direction'];z=[a[0]+20*d[0],a[1]+20*d[1],a[2]];node=200+2*i+j
                ports[key]={'edge_id':10+2*i+j,'node_id':node,'grade':0,'edge_snapshot':{'id':10+2*i+j,'node0':node if j else 500+i*2,'node1':501+i*2 if j else node,'p0':a,'p1':z,'t0':[20*d[0],20*d[1],0],'t1':[20*d[0],20*d[1],0],'template':3,'style':0}}
        return {'plan':main,'ports':ports,'chains':chains,'summary':{'status':'ok','game_constructed':True}}
    def test_full_pattern_orientation_and_side_matrix_has_exact_outgoing_roles(self):
        import bridge_complete as complete
        import bridge_branching as branching
        for b in self.variants():
            with self.subTest(pattern=[t['direction'] for t in b['tracks']],up=b['reference_up'],side=b['side']):
                p=complete.plan_complete_layout(b);n=len(b['tracks']);parent=self.parent(p)
                with patch('bridge_branching._parent',return_value=(parent,'hash')):q=complete._branch_plan(p,'current')
                self.assertEqual(len(q['roles']),2*n+2);self.assertEqual(len(q['movements']),n+2)
                self.assertEqual(len(p['fixtures']),2*n+4)
                self.assertEqual([t['forward'] for t in p['main_plan']['tracks']],[(t['direction']=='UP')==(b['reference_up']=='increasing') for t in b['tracks']])
                for row in q['movements']:self.assertEqual(q['roles'][row['from']]['function'],'entry');self.assertEqual(q['roles'][row['to']]['function'],'exit')
    def test_ud_partial_fixture_continuation_and_movement_count_are_dynamic(self):
        import bridge_complete as complete
        p=self.plan();path=self.root/'ud_partial.json';first=p['fixtures'][0]['name'];path.write_text(json.dumps({'plan':p,'fixtures':{first:self.response(result={'game_constructed':True})},'stages':{},'summary':{'game_constructed':True}}));built=[]
        def request(op,q):
            if op=='inspect':return self.response(result={'edges':[{'resource':{'track_distance':5}}]})
            built.append(q);return self.response(result={'game_constructed':True})
        def proof(c,p,r):return {'status':'ok','routes_verified':4,'junctions_verified':2,'final_network_verified':True,'retained_spacing_verified':True} if 'branches' in r['stages'] else {'status':'complete_layout_incomplete'}
        with patch('bridge_complete._inspect',side_effect=proof),patch('bridge_complete._site'),patch('bridge_complete._controls',return_value=[]),patch('bridge_live._select_throat_port',side_effect=LiveError('no_eligible_candidates','empty')),patch.object(self.client,'request',side_effect=request),patch('bridge_live.connect_corridor',return_value={'status':'ok'}),patch('bridge_parallel.execute_multitrack_connection',return_value={'status':'ok','evidence':'main','game_constructed':True}),patch('bridge_complete._branch_plan',return_value={}),patch('bridge_branching.execute_branching_corridor',return_value={'status':'ok','evidence':'branches','game_constructed':True}):
            result=complete.execute_complete_layout(self.client,p,continuation_record=path)
        self.assertEqual(result['routes_verified'],4);self.assertEqual(result['fixtures_acknowledged'],4);self.assertEqual(len(built),3)
    def test_ud_branch_continuation_proves_two_through_routes_not_four(self):
        import bridge_branching as branching
        p=self.plan();parent=self.parent(p)
        with patch('bridge_branching._parent',return_value=(parent,'hash')):q=__import__('bridge_complete')._branch_plan(p,'current')
        path=self.root/'partial_branch.json';path.write_text(json.dumps({'plan':q,'completed_branches':[q['brief']['branches'][0]['id']],'operations':[]}))
        def assess(c,p,r,**kw):
            r.update(routes=[{'kind':'through','verified':True},{'kind':'through','verified':True},{'kind':'branch','verified':True,'to':q['brief']['branches'][0]['id']}],current_junctions={q['brief']['branches'][0]['id']:5},current_roles={});return {'routes_verified':3}
        with patch('bridge_branching._parent',return_value=(parent,'hash')),patch('bridge_branching._assess',side_effect=assess):ports,junctions,done=branching._continuation(self.client,q,{},path)
        self.assertEqual(len(done),1);self.assertEqual(junctions,[5])
    def test_invalid_reference_order_branch_target_and_direction_reject_without_native_calls(self):
        from bridge_complete import plan_complete_layout
        for key in ('reference','order','branch'):
            b=self.brief()
            if key=='reference':b['reference_up']='nearest'
            elif key=='order':b['tracks'][1]['direction']='UP'
            else:b['branches'][0]['track']=b['tracks'][1]['id']
            with self.subTest(key=key),patch('bridge_live.client_from_context') as native,self.assertRaises((LiveError,ValueError)):plan_complete_layout(b)
            native.assert_not_called()
    def test_reversed_ud_record_reexecution_and_interruption_do_not_rebuild(self):
        CompleteLayoutTests.test_complete_reexecution_only_checks_current_state_and_changed_brief_stops(self)
        CompleteLayoutTests.test_interrupted_and_pending_work_never_replays(self)

class LadderLayoutTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/ladder_layout_example.json').read_text())
    def test_explicit_fixed_roles_and_bidirectional_matrix_plan_without_game(self):
        from bridge_ladder import plan_ladder,publish_ladder
        with patch('bridge_live.client_from_context') as native:
            p=plan_ladder(self.brief());r=publish_ladder(p,self.root)
        native.assert_not_called();self.assertEqual(r['movements'],12);self.assertFalse(r['game_constructed']);self.assertEqual(len(p['steps']),10)
        self.assertTrue(all(len(m['via'])>=2 for m in p['movements']))
        self.assertEqual({m['from'] for m in p['movements']} & set('A1 A2 A3 A4'.split()),{'A1','A3'})
    def test_missing_matrix_pairing_spacing_vertical_and_turnout_order_reject(self):
        from bridge_ladder import plan_ladder
        for kind in ('matrix','pair','spacing','vertical','order'):
            b=self.brief()
            if kind=='matrix':b['movements'].pop()
            elif kind=='pair':b['groups'][1]['outbound']='A2'
            elif kind=='spacing':b['spacing']=10
            elif kind=='vertical':b['roles']['S3']['endpoint']['guide_xyz'][2]+=1
            else:b['groups'][0]['junctions'].reverse()
            with self.subTest(kind=kind),self.assertRaises((ValueError,LiveError)):plan_ladder(b)
    def test_translated_rotated_fixed_endpoint_brief_is_supported(self):
        import math
        from bridge_ladder import plan_ladder
        b=self.brief();a=math.radians(20);c,z=math.cos(a),math.sin(a)
        def p(v):return [c*v[0]-z*v[1]+40,z*v[0]+c*v[1]-70,v[2]]
        def d(v):return [c*v[0]-z*v[1],z*v[0]+c*v[1]]
        def transform(e):
            e['guide_xyz']=p(e['guide_xyz']);e['travel_direction']=d(e['travel_direction']);e['region']={'min':[v-2 for v in e['guide_xyz']],'max':[v+2 for v in e['guide_xyz']]}
        for r in b['roles'].values():transform(r['endpoint'])
        for g in b['groups']:
            transform(g['arm_end'])
            for e in g['junctions']:transform(e)
            for e in g['spine_guides']:e['position']=p(e['position']);e['travel_direction']=d(e['travel_direction'])
        corners=[p([x,y,33]) for x in (-1950,650) for y in (-3400,-2800)]
        b['region']={'min':[min(q[k] for q in corners) for k in range(2)]+[30],'max':[max(q[k] for q in corners) for k in range(2)]+[36]}
        self.assertEqual(len(plan_ladder(b)['movements']),12)
    def test_build_order_and_failure_stop_keep_partial_effects(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());calls=[]
        def build(kind):
            calls.append(kind)
            return {'status':'mutation_unverified' if kind=='merge' else 'ok','game_constructed':'unknown' if kind=='merge' else True,'error':'reported partial mutation','junction':{'node':10}}
        with patch('bridge_ladder._roles',return_value={}),patch('bridge_live._select_throat_port',return_value=({'edge_id':1,'node_id':2},'r')),patch('bridge_live.connect_corridor',side_effect=lambda *a,**k:build('spine')),patch('bridge_live.extend',side_effect=lambda *a,**k:build('arm')),patch('bridge_live.connect_junction_at',side_effect=lambda *a,**k:build('merge')),patch('bridge_ladder._assess') as assess:
            r=ladder.execute_ladder(self.client,p)
        self.assertEqual(calls,['spine','arm','merge']);assess.assert_not_called();self.assertEqual(r['game_constructed'],'unknown')
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved['unfinished_step'],'north_junction_0')
        with self.assertRaises(LiveError):ladder.execute_ladder(self.client,p,layout_record=r['evidence'])
    def test_completed_execution_only_inspects_and_changed_brief_cannot_replay(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());path=self.root/'complete.json';path.write_text(json.dumps({'plan':p,'summary':{'status':'ok'}}))
        with patch('bridge_ladder.inspect_ladder',return_value={'status':'ok','game_constructed':False}) as inspect,patch('bridge_live.connect_corridor') as build:
            r=ladder.execute_ladder(self.client,p,layout_record=path)
        self.assertFalse(r['game_constructed']);build.assert_not_called();inspect.assert_called_once()
        b=self.brief();b['radius']=121
        with self.assertRaises(ValueError):ladder.execute_ladder(self.client,ladder.plan_ladder(b),layout_record=path)
    def test_final_route_requires_ordered_exact_junctions_not_nearby_geometry(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());ports={n:{'edge_id':i+100,'node_id':i+1,'edge_snapshot':{'node0':i+1,'node1':i+20}} for i,n in enumerate(p['brief']['roles'])}
        js={s['name']:i+300 for i,s in enumerate(p['steps']) if s['kind']=='junction'}
        rows=iter(p['movements'])
        def request(*a):
            row=next(rows);nodes=[ports[row['from']]['edge_snapshot']['node1'],*[js[n] for n in row['via']],ports[row['to']]['edge_snapshot']['node1']]
            if row['to']=='N3':nodes=nodes[:1]+nodes[1:-1][::-1]+nodes[-1:]
            return {'status':'ok','result':{'requested_route_verified':True,'path':[{'from':{'entity':a},'to':{'entity':b}} for a,b in zip(nodes,nodes[1:])]}}
        junctions=iter(js.values());record={}
        with patch('bridge_ladder._roles',return_value=ports),patch('bridge_live._recipe_junction',side_effect=lambda *a:(next(junctions),[])),patch.object(self.client,'request',side_effect=request),self.assertRaises(LiveError):ladder._assess(self.client,p,record)
        self.assertEqual(sum(r['verified'] for r in record['routes']),4);self.assertFalse(record['routes'][-1]['verified'])
    def test_current_role_replacement_keeps_exact_node_and_rejects_changed_identity(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());old={n:{'node_id':3} for n in p['brief']['roles']};candidate={'edge_id':200,'node_id':3,'edge_snapshot':{'road_type':'TRACK','node0':3,'node1':4,'t0':[20,0,0],'t1':[20,0,0]}}
        with patch('bridge_live._select_throat_port',return_value=(candidate,'r')):now=ladder._roles(self.client,p,{'initial_ports':old},True)
        self.assertTrue(all(c['edge_id']==200 for c in now.values()))
        candidate['node_id']=4
        with patch('bridge_live._select_throat_port',return_value=(candidate,'r')),self.assertRaises(LiveError):ladder._roles(self.client,p,{'initial_ports':old},True)

class LadderRecoveryTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    brief=LadderLayoutTests.brief
    def test_arm_region_is_bounded_subset_and_large_arm_is_unsupported(self):
        import bridge_ladder as ladder
        b=self.brief();g=b['groups'][0];box=ladder._arm_region(b,b['roles'][g['outbound']]['endpoint'],g['arm_end'])
        self.assertTrue(all(b['region']['min'][k]<=box['min'][k]<box['max'][k]<=b['region']['max'][k] for k in range(3)))
        self.assertLessEqual(box['max'][0]-box['min'][0],1000)
        end=json.loads(json.dumps(g['arm_end']));end['guide_xyz'][0]+=1000
        with self.assertRaises(LiveError):ladder._arm_region(b,b['roles'][g['outbound']]['endpoint'],end)
    def test_pending_and_unbound_records_stop_without_native_calls(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());self.client.journal.write_text(json.dumps({'pending':{'operation':'build'}}))
        with patch('bridge_live.connect_corridor') as build,patch('bridge_ladder._roles') as roles:r=ladder.execute_ladder(self.client,p)
        self.assertEqual(r['status'],'reconciliation_required');build.assert_not_called();roles.assert_not_called()
        path=self.root/'unbound.json';path.write_text(json.dumps({'plan':p,'summary':{'status':'ok'}}))
        with self.assertRaises(ValueError):ladder.inspect_ladder(self.client,path)
    def test_discovery_failure_requires_no_attempt_and_proven_prefix_before_next_stage(self):
        import bridge_ladder as ladder
        p=ladder.plan_ladder(self.brief());w=self.root/'failed_discovery.json';w.write_text(json.dumps({'attempts':[]}))
        failed={'operation':'connect-junction-at','status':'no_eligible_candidates','stage':'discover','game_constructed':False,'attempt_count':0,'evidence':str(w)}
        ops=[{'name':s['name'],'response':{'status':'ok','game_constructed':True}} for s in p['steps'][:3]]+[{'name':p['steps'][3]['name'],'response':failed}]
        ports={n:{'edge_id':i+100,'node_id':i+1,'edge_snapshot':{'node0':i+1,'node1':i+20}} for i,n in enumerate(p['brief']['roles'])}
        old={'plan':p,'initial_ports':ports,'operations':ops,'unfinished_step':p['steps'][3]['name'],'summary':{'game_constructed':True}}
        path=self.root/'prefix.json';path.write_text(json.dumps(old));q=ports['A2']
        with patch('bridge_ladder._roles',return_value=ports),patch('bridge_live._recipe_junction',return_value=(999,[])),patch('bridge_live._select_throat_port',return_value=(q,'r')),patch.object(self.client,'request',return_value={'status':'ok','result':{'requested_route_verified':True}}),patch('bridge_live.extend') as arm,patch('bridge_live.connect_corridor') as spine,patch('bridge_live.connect_junction_at',return_value={'status':'error','stage':'fit','game_constructed':False}) as junction:
            r=ladder.execute_ladder(self.client,p,layout_record=path)
        arm.assert_not_called();spine.assert_not_called();junction.assert_called_once();self.assertEqual(r['steps_completed'],3)
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(len(saved['continuation']['prefix_proofs']),3)
        old['operations'][-1]['response']['attempt_count']=1;path.write_text(json.dumps(old))
        with patch.object(self.client,'request') as native,self.assertRaises(LiveError):ladder.execute_ladder(self.client,p,layout_record=path)
        native.assert_not_called()
    def test_harder_fit_limits_and_region_are_not_silently_relaxed(self):
        import bridge_ladder as ladder
        for key in ('turnout','spine','region'):
            b=self.brief()
            if key=='turnout':b['turnout_radius']=119
            elif key=='spine':b['groups'][1]['spine_radius']=119
            else:b['region']['max'][0]=300
            with self.subTest(key=key),self.assertRaises((ValueError,LiveError)):ladder.plan_ladder(b)

class CompactLadderTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/compact_ladder_example.json').read_text())
    def test_endpoint_matrix_derives_controls_without_native_calls_or_large_spreading(self):
        import bridge_ladder as ladder
        b=self.brief()
        with patch('bridge_live.client_from_context') as native:p=ladder.plan_compact_ladder(b);summary=ladder.publish_ladder(p,self.root)
        native.assert_not_called();self.assertEqual(summary['movements'],12);self.assertFalse(summary['game_constructed'])
        self.assertEqual(p,ladder._canonical(p));self.assertEqual(p['brief']['turnout_radius'],100)
        ys=sorted(r['position'][1] for r in b['roles'].values() if r['kind']=='destination');self.assertEqual([y-ys[0] for y in ys],[0,5,15,20,30,35])
        self.assertEqual([r['endpoint']['guide_xyz'] for r in p['brief']['roles'].values()],[r['position'] for r in b['roles'].values()])
        self.assertTrue(all(len(g['spine_guides'])==1 for g in p['brief']['groups']))
        points=[g['arm_end']['guide_xyz'][1] for g in p['brief']['groups']];self.assertEqual(max(points)-min(points),55)
    def test_fan_placement_depends_on_actual_offsets_radii_not_fixed_fractions(self):
        import bridge_ladder as ladder
        b=self.brief();p=ladder.plan_compact_ladder(b);before=p['brief']['groups'][0]['junctions'][1]['guide_xyz'][0]
        for r in b['roles'].values():
            if r['kind']=='destination':r['position'][0]+=100
        b['region']['max'][0]+=100;q=ladder.plan_compact_ladder(b);after=q['brief']['groups'][0]['junctions'][1]['guide_xyz'][0]
        self.assertAlmostEqual(after-before,100);self.assertEqual(q['brief']['roles']['S3']['endpoint']['guide_xyz'],b['roles']['S3']['position'])
        b['turnout_radii']['outer_fan']=150;z=ladder.plan_compact_ladder(b)
        self.assertGreater(z['brief']['groups'][0]['junctions'][1]['guide_xyz'][0],after)
        self.assertEqual(z['steps'][3]['brief']['radius'],150)
    def test_pairing_bank_order_lengths_and_hard_limits_reject(self):
        import bridge_ladder as ladder
        for kind in ('movement','order','length','radius','unapproved'):
            b=self.brief()
            if kind=='movement':b['movements'][0]['from']='A4'
            elif kind=='order':b['groups'][0]['destinations'].reverse()
            elif kind=='length':
                for r in b['roles'].values():
                    if r['kind']=='destination':r['position'][0]=100
            elif kind=='radius':b['turnout_radii']['outer_fan']=59
            else:b['groups'][0]['arm_end']=[1,2,3]
            with self.subTest(kind=kind),self.assertRaises((ValueError,LiveError)):ladder.plan_compact_ladder(b)
    def test_rotation_translation_keep_actual_ports_and_deterministic_plan(self):
        import bridge_ladder as ladder,math
        b=self.brief();a=math.radians(17);c,z=math.cos(a),math.sin(a)
        def point(p):return [c*p[0]-z*p[1]+80,z*p[0]+c*p[1]-40,p[2]]
        for r in b['roles'].values():r['position']=point(r['position']);r['travel_direction']=[c,z]
        corners=[point([x,y,33]) for x in (-1850,-1290) for y in (-4550,-4420)];b['region']={'min':[min(q[k] for q in corners) for k in range(2)]+[30],'max':[max(q[k] for q in corners) for k in range(2)]+[36]}
        p=ladder.plan_compact_ladder(b);self.assertEqual(p,ladder.plan_compact_ladder(b));self.assertEqual(p,ladder._canonical(p));self.assertEqual(len(p['steps']),10)
    def test_derived_input_tampering_rejects_before_builder(self):
        import bridge_ladder as ladder
        p=ladder.plan_compact_ladder(self.brief());p['derivation']['input']['radius']=61
        with patch('bridge_live.connect_corridor') as native,self.assertRaises(ValueError):ladder.execute_ladder(self.client,p)
        native.assert_not_called()


class HeightLadderTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/height_ladder_example.json').read_text())
    def ports(self,b):
        out={}
        for i,(n,r) in enumerate(b['roles'].items()):
            p=list(r['position']);p[2]+=.4;d=r['travel_direction'];a=r['kind']=='approach';node=2*i+1
            out[n]={'eligible':True,'pos':p,'outward_direction':(d if a else [-x for x in d])+[0],'node_id':node,'edge_id':i+100,'edge_snapshot':{'id':i+100,'node0':node-1 if a else node,'node1':node if a else node+1,'road_type':'TRACK','t0':[20*d[0],20*d[1],0],'t1':[20*d[0],20*d[1],0],'p0':[p[0]-20*d[0],p[1]-20*d[1],p[2]] if a else p,'p1':p if a else [p[0]+20*d[0],p[1]+20*d[1],p[2]]}}
        return out
    def test_actual_destination_height_and_current_tangents_drive_plan_not_hint_z(self):
        import bridge_height_ladder as h
        b=self.brief();ports=self.ports(b);p=h.derive(b,ports)
        self.assertEqual(p['destination_height'],b['roles']['S1']['position'][2]+.4);self.assertEqual(len(p['leads']),4)
        self.assertTrue(all(q['target'][2]==b['roles']['S1']['position'][2]+.4 and q['brief']['vertical']['end_grade']==0 for q in p['leads']))
        self.assertEqual(len(p['core_plan']['movements']),12)
        self.assertEqual(p['observed_roles']['A1']['position'][2],b['roles']['A1']['position'][2]+.4)
        ports['A1']['edge_snapshot']['t1'][2]=.2
        self.assertAlmostEqual(h.derive(b,ports)['leads'][0]['source_grade'],.01)
    def test_nonlevel_nonparallel_nonaligned_destinations_rejected_without_flattening(self):
        import bridge_height_ladder as h
        for kind in ('height','grade','heading','bank'):
            b=self.brief();ports=self.ports(b);p=ports['N3']
            if kind=='height':p['pos'][2]+=.1
            elif kind=='grade':p['edge_snapshot']['t0'][2]=.1
            elif kind=='heading':p['outward_direction']=[0,-1]
            else:p['pos'][0]+=.1
            before=json.dumps(ports,sort_keys=True)
            with self.subTest(kind=kind),self.assertRaises(LiveError):h.derive(b,ports)
            self.assertEqual(json.dumps(ports,sort_keys=True),before)
    def test_rotated_translated_observed_banks_and_hard_limits_remain_supported(self):
        import bridge_height_ladder as h
        import math
        b=self.brief();a=.3;c,z=math.cos(a),math.sin(a)
        def pos(p):return [c*p[0]-z*p[1]+200,z*p[0]+c*p[1]-100,p[2]]
        for r in b['roles'].values():r['position']=pos(r['position']);r['travel_direction']=[c,z]
        points=[pos([x,y,v]) for x in (b['region']['min'][0],b['region']['max'][0]) for y in (b['region']['min'][1],b['region']['max'][1]) for v in (b['region']['min'][2],b['region']['max'][2])]
        b['region']={'min':[min(p[k] for p in points) for k in range(3)],'max':[max(p[k] for p in points) for k in range(3)]}
        p=h.derive(b,self.ports(b));self.assertEqual(p['core_plan']['brief']['radius'],60)
        b['throat_length']=790
        with self.assertRaises(LiveError):h.derive(b,self.ports(b))
    def test_observed_planning_is_read_only_and_rejects_tampered_binding(self):
        import bridge_height_ladder as h
        b=self.brief();ports=self.ports(b)
        with patch('bridge_height_ladder._ports',return_value=(ports,['read'])),patch('bridge_live.extend') as build:
            r=h.plan_height_ladder(self.client,b)
        build.assert_not_called();self.assertFalse(r['game_constructed'])
        p=json.loads(Path(r['evidence']).read_text())['plan'];h._canonical(p)
        p['initial_ports']['N3']['pos'][2]+=.1
        with self.assertRaises((ValueError,LiveError)):h._canonical(p)
    def test_four_graded_leads_before_pointwork_and_failure_stops_with_partial_effects(self):
        import bridge_height_ladder as h
        b=self.brief();ports=self.ports(b);calls=[]
        def extend(*a,**k):
            calls.append(a[1]);return {'status':'mutation_unverified' if len(calls)==2 else 'ok','game_constructed':'unknown' if len(calls)==2 else True,'edges':[1000]}
        with patch('bridge_height_ladder._ports',return_value=(ports,[])),patch('bridge_live.extend',side_effect=extend),patch('bridge_ladder.execute_ladder') as core:
            r=h.execute_height_ladder(self.client,b)
        core.assert_not_called();self.assertEqual(len(calls),2);self.assertEqual(r['game_constructed'],'unknown')
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved['unfinished_step'],'lead_A2')
        with patch('bridge_live.extend') as build,self.assertRaises(LiveError):h.execute_height_ladder(self.client,b,layout_record=r['evidence'])
        build.assert_not_called()
        calls.clear()
        with patch('bridge_height_ladder._ports',return_value=(ports,[])),patch('bridge_live.extend',side_effect=lambda *a,**k:(calls.append('lead') or {'status':'ok','game_constructed':True,'edges':[1000]})),patch('bridge_ladder.execute_ladder',side_effect=lambda *a,**k:(calls.append('core') or {'status':'ok','game_constructed':True,'evidence':'core.json'})),patch('bridge_height_ladder._assess',return_value={'status':'ok','routes_verified':12}):
            r=h.execute_height_ladder(self.client,b)
        self.assertEqual(calls,['lead']*4+['core']);self.assertEqual(r['routes_verified'],12)
    def test_completed_receipt_checks_freshly_without_construction_and_changed_brief_stops(self):
        import bridge_height_ladder as h
        b=self.brief();p=h.derive(b,self.ports(b));path=self.root/'height_complete.json'
        path.write_text(json.dumps({'plan':p,'core_record':'core.json','lead_edges':[1000],'summary':{'status':'ok','game_constructed':True}}))
        with patch('bridge_height_ladder._assess',return_value={'status':'ok','routes_verified':12}),patch('bridge_live.extend') as build,patch('bridge_ladder.execute_ladder') as core:
            r=h.execute_height_ladder(self.client,b,layout_record=path)
        build.assert_not_called();core.assert_not_called();self.assertFalse(r['game_constructed']);self.assertTrue(r['checked_existing'])
        b['radius']=61
        with self.assertRaises(ValueError):h.execute_height_ladder(self.client,b,layout_record=path)
    def test_fixed_native_identity_and_destination_tangent_change_stop_readback(self):
        import bridge_height_ladder as h
        b=self.brief();ports=self.ports(b)
        def select(client,e,**kw):
            name=min(ports,key=lambda n:__import__('math').dist(ports[n]['pos'],e['guide_xyz']))
            return ports[name],'fresh'
        old=json.loads(json.dumps(ports));ports['N3']['node_id']+=100
        with patch('bridge_live._select_throat_port',side_effect=select),self.assertRaises(LiveError):h._ports(self.client,b,old=old,connected=True)
    def test_fitting_radius_is_separate_from_unchanged_project_acceptance_radius(self):
        import bridge_height_ladder as h
        b=self.brief();p=h.derive(b,self.ports(b));steps=[s for s in p['core_plan']['steps'] if s['kind']=='junction']
        self.assertTrue(all(s['brief']['radius']==60 and s['brief']['fit_radius']>=60 for s in steps))
        q=steps[0]['brief']
        with patch('bridge_live._connect_project',return_value={'status':'ok'}) as native:
            connect_junction_at(self.client,q,junction_nodes=[])
        self.assertEqual(native.call_args.args[1]['fit_radius'],105)
        q=q|{'fit_radius':59}
        with patch('bridge_live._connect_project') as native,self.assertRaises(ValueError):connect_junction_at(self.client,q,junction_nodes=[])
        native.assert_not_called()
    def test_current_graded_port_uses_horizontal_heading_and_retains_vertical_tangent(self):
        import bridge_ladder as l
        b=self.brief();c=self.ports(b)['A1'];c.update(incidence_complete=True)
        c['outward_direction']=[.9998,0,.019996];c['edge_snapshot']['t1'][2]=.4
        with patch('bridge_live.discover',return_value={'status':'ok','request_id':'read','result':{'complete':True,'candidates':[c]}}):
            chosen,_=_select_throat_port(self.client,l.intent(c['pos'],[1,0]),tolerance=.001)
        self.assertEqual(chosen['node_id'],c['node_id']);self.assertEqual(chosen['edge_snapshot']['t1'][2],.4)
    def test_level_pointwork_requires_actual_native_height_not_merely_allowed_grade(self):
        import bridge_height_ladder as h
        b=self.brief();p=h.derive(b,self.ports(b));height=p['destination_height']
        edge={'id':900,'p0':[0,0,height],'p1':[1,0,height],'t0':[1,0,0],'t1':[1,0,0],'movement_geometry':{'samples':[{'pos':[.5,0,height],'direction':[1,0,0]}]}}
        r={'plan':p,'lead_edges':[800],'routes':[{'response':{'result':{'path':[{'edge':{'entity':800},'confirmed_TRACK':True},{'edge':{'entity':900},'confirmed_TRACK':True}]}}}]}
        def observed(op,q):
            if q['edge_ids']==[900]:return {'status':'ok','result':{'edges':[edge]}}
            return {'status':'ok','result':{'edges':[{'id':i,'movement_geometry':{'samples':[{'pos':[0,0,height+.53],'direction':[1,0,0]}]}} for i in q['edge_ids']]}}
        edge['movement_geometry']['samples'][0]['pos'][2]=height+.53
        with patch.object(self.client,'request',side_effect=observed) as read:
            self.assertEqual(h._level_pointwork(self.client,r),1)
            self.assertEqual(r['native_movement_height'],height+.53)
            self.assertEqual(read.call_args.args[1]['edge_ids'],[900])
            edge['movement_geometry']['samples'][0]['pos'][2]+=.05
            with self.assertRaises(LiveError):h._level_pointwork(self.client,r)
    def test_partial_core_without_absence_proof_does_not_replay_leads_or_throat(self):
        import bridge_height_ladder as h
        b=self.brief();p=h.derive(b,self.ports(b));failed=self.root/'failed_workflow.json';failed.write_text(json.dumps({'attempts':[{'request_id':'rejected'}]}))
        core=self.root/'failed_core.json';core.write_text(json.dumps({'plan':p['core_plan'],'operations':[{'name':p['core_plan']['steps'][0]['name'],'response':{'status':'error','evidence':str(failed)}}]}))
        old=self.root/'partial_height.json';old.write_text(json.dumps({'plan':p,'unfinished_step':'level_throat','core_record':str(core),'operations':[{'name':'lead_'+q['role'],'response':{'status':'ok','edges':[900+i]}} for i,q in enumerate(p['leads'])]+[{'name':'level_throat','response':{'status':'error'}}],'summary':{'status':'error'}}))
        with patch('bridge_live.extend') as lead,patch('bridge_ladder.execute_ladder') as throat,self.assertRaises(LiveError):h.execute_height_ladder(self.client,b,layout_record=old)
        lead.assert_not_called();throat.assert_not_called()
    def test_cli_default_observes_and_inspect_does_not_execute(self):
        b=self.brief();path=self.root/'brief.json';path.write_text(json.dumps(b))
        args=['height-ladder','--params',str(path),'--context','dummy']
        with patch('bridge_live.client_from_context',return_value=self.client),patch('bridge_height_ladder.plan_height_ladder',return_value={'status':'ok','game_constructed':False}) as plan,patch('bridge_height_ladder.execute_height_ladder') as build,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(args),0)
        plan.assert_called_once();build.assert_not_called();self.assertLess(len(out.getvalue().encode()),4096)

class RouteSetTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    def data(self):
        edges={10:{'id':10,'road_type':'TRACK','node0':1,'node1':2,'p0':[0,0,0],'p1':[10,0,0]},20:{'id':20,'road_type':'TRACK','node0':2,'node1':3,'p0':[10,0,0],'p1':[20,0,0]},30:{'id':30,'road_type':'TRACK','node0':4,'node1':5,'p0':[0,5,0],'p1':[10,5,0]}}
        incidence={n:{'complete':True,'degree':2,'edges':[]} for n in range(1,6)}
        incidence[2]={'complete':True,'degree':3,'edges':[10,20,40]}
        def row(name,ids,reverse=False):
            path=[]
            for i in ids:
                e=edges[i];a,z=(e['node1'],e['node0']) if reverse else (e['node0'],e['node1'])
                path.append({'edge':{'entity':i,'index':1 if reverse else 0},'from':{'entity':a,'index':0},'to':{'entity':z,'index':0},'forward':not reverse,'confirmed_TRACK':True})
            return {'id':name,'from':name+'a','to':name+'z','bindings':{'a':{'node_id':path[0]['from']['entity']},'z':{'node_id':path[-1]['to']['entity']}},'response':{'status':'ok','result':{'native_path_found':True,'requested_route_verified':True,'transport_continuous':True,'truncated':False,'path_count':len(path),'path':path}}}
        return edges,incidence,row
    def test_same_physical_track_reverse_and_shared_categories_are_separate(self):
        import bridge_route_set as rs
        es,ns,row=self.data();a=row('a',[10,20]);b=row('b',[20,10],True)
        p=rs.assess_route_set([a,b],es,ns)[0]
        self.assertEqual(p['result'],'topology_overlap');self.assertEqual(p['shared_TRACK_edges'],[10,20]);self.assertEqual(p['opposite_traversal_edges'],[10,20])
        self.assertEqual(p['shared_junction_nodes'],[2]);self.assertEqual(p['shared_endpoint_nodes'],[1,3]);self.assertTrue(p['both_paths_complete'])
        self.assertEqual(a['junction_transitions'][0]['from_edge'],10)
    def test_complete_disjoint_routes_not_operational_capacity(self):
        import bridge_route_set as rs
        es,ns,row=self.data();p=rs.assess_route_set([row('a',[10,20]),row('b',[30])],es,ns)[0]
        self.assertEqual(p['result'],'topology_disjoint');self.assertEqual(p['conflicts_outside_shared_graph'],'unknown');self.assertEqual(p['simultaneous_operation'],'unprobed')
    def test_unreachable_truncated_unqualified_or_missing_current_edges_are_unknown(self):
        import bridge_route_set as rs
        for kind in ('unreachable','truncated','unqualified','missing','incomplete_count','discontinuous'):
            es,ns,row=self.data();a=row('a',[10,20]);b=row('b',[30]);v=a['response']['result']
            if kind=='unreachable':v.update(native_path_found=False,path=[])
            elif kind=='truncated':v.update(truncated=True,path=[])
            elif kind=='unqualified':v['path'][0].pop('confirmed_TRACK')
            elif kind=='missing':es.pop(10)
            elif kind=='incomplete_count':v['path_count']=7
            else:v['path'][1]['from']['index']=1
            with self.subTest(kind=kind):self.assertEqual(rs.assess_route_set([a,b],es,ns)[0]['result'],'unknown');self.assertFalse(a['complete'])
    def test_known_overlap_stays_visible_in_incomplete_path(self):
        import bridge_route_set as rs
        es,ns,row=self.data();a=row('a',[10,20]);b=row('b',[10]);a['response']['result']['requested_route_verified']=False
        p=rs.assess_route_set([a,b],es,ns)[0];self.assertEqual(p['result'],'topology_overlap');self.assertFalse(p['both_paths_complete'])
    def test_shared_endpoint_and_unknown_junction_classification_remain_separate(self):
        import bridge_route_set as rs
        es,ns,row=self.data();a=row('a',[10]);b=row('b',[10]);ns[1]={'complete':False}
        p=rs.assess_route_set([a,b],es,ns)[0]
        self.assertEqual(p['result'],'topology_overlap');self.assertEqual(p['shared_endpoint_nodes'],[1,2]);self.assertIn(1,p['junction_classification_unknown_nodes'])
    def test_incidence_does_not_qualify_unobserved_branch_as_TRACK(self):
        import bridge_route_set as rs
        es,ns,row=self.data();record={'node_observations':[],'edge_observations':[]}
        def discover(c,q):
            n=min((1,2),key=lambda n:abs(q['region']['min'][0]+.1-(0 if n==1 else 10)))
            return {'status':'ok','request_id':'read','result':{'complete':True,'candidates':[{'node_id':n,'incident_edges':[10] if n==1 else [10,90,91],'incidence_complete':True,'incident_output_truncated':False}]}}
        with patch('bridge_live.discover',side_effect=discover),patch.object(self.client,'request',return_value={'status':'error','result':{'error':'not TRACK'}}):
            seen=rs._incidence(self.client,{10:es[10]},record)
        self.assertTrue(seen[1]['complete']);self.assertFalse(seen[2]['complete']);self.assertIsNone(seen[2]['degree'])
    def test_shared_junction_without_shared_rail_is_visible(self):
        import bridge_route_set as rs
        es,ns,row=self.data();es[30].update(node0=2,node1=5);ns[2]['edges']=[10,20,30]
        p=rs.assess_route_set([row('a',[10]),row('b',[30])],es,ns)[0]
        self.assertEqual(p['shared_TRACK_edges'],[]);self.assertEqual(p['shared_junction_nodes'],[2]);self.assertEqual(p['result'],'topology_overlap')
    def test_opaque_non_track_internals_block_disjoint_but_remain_explicit(self):
        import bridge_route_set as rs
        es,ns,row=self.data();a=row('a',[10,20]);b=row('b',[30])
        internal={'edge':{'entity':99,'index':0},'from':{'entity':2,'index':0},'to':{'entity':2,'index':0},'forward':True,'confirmed_TRACK':False}
        a['response']['result']['path'].insert(1,internal);a['response']['result']['path_count']=3
        p=rs.assess_route_set([a,b],es,ns)[0];self.assertEqual(p['result'],'unknown');self.assertEqual(len(a['physical_tracks']),2)
        self.assertEqual(a['non_TRACK_transport'][0]['classification'],'unresolved_transport_internal')
        internal['edge']['entity']=2
        self.assertEqual(rs.assess_route_set([a,b],es,ns)[0]['result'],'topology_disjoint')
    def test_wrong_via_order_or_stale_binding_never_proves_disjoint(self):
        import bridge_route_set as rs
        es,ns,row=self.data();a=row('a',[10,20]);b=row('b',[30]);a['via_nodes']=[3,2]
        self.assertEqual(rs.assess_route_set([a,b],es,ns)[0]['result'],'unknown')
        a.pop('via_nodes');a['stale_binding']=True;b=row('b',[10,20])
        self.assertEqual(rs.assess_route_set([a,b],es,ns)[0]['result'],'unknown')
    def brief(self):return json.loads((Path(__file__).resolve().parents[1]/'implementation/live_python_interface/route_set_example.json').read_text())
    def test_boundary_query_uses_exact_incidence_and_explicit_kind(self):
        import bridge_route_set as rs
        es,_,_=self.data()
        for node in (1,2):
            c={'node_id':node,'edge_id':10,'edge_snapshot':es[10],'incident_edges':[10],
               'incident_count':1,'incidence_complete':True,'incident_output_truncated':False}
            self.assertEqual(rs._boundary_query_node(c),('free_endpoint',node))
            with self.assertRaises(LiveError):rs._boundary_query_node(c,'connected_boundary')
            connected=c|{'incident_count':2,'incident_edges':[10,40]}
            self.assertEqual(rs._boundary_query_node(connected,'connected_boundary'),('connected_boundary',3-node))
            with self.assertRaises(LiveError):rs._boundary_query_node(connected,'free_endpoint')
            for bad in (c|{'node_id':999},c|{'edge_id':999},c|{'incidence_complete':False},c|{'incident_edges':[99]},c|{'incident_output_truncated':True}):
                with self.subTest(node=node,bad=bad),self.assertRaises(LiveError):rs._boundary_query_node(bad)
        b=self.brief();b['endpoints']['A1']['boundary_kind']='free_endpoint';rs.validate(b)
        b['endpoints']['A1']['boundary_kind']='guess'
        with self.assertRaises(ValueError):rs.validate(b)

    def test_free_trimmed_endpoint_queries_forward_fresh_junctions_and_staleness(self):
        import bridge_route_set as rs
        es,ns,row=self.data();b=self.brief();b['endpoints']={n:b['endpoints'][n] for n in ('A1','S1')}
        b['movements']=[{'id':'one','from':'A1','to':'S1'},{'id':'two','from':'S1','to':'A1'}]
        b['junctions']={'turnout':{k:v for k,v in b['endpoints']['A1'].items() if k not in ('travel_direction','heading_tolerance_deg')}}
        def endpoint(c,h):
            n=1 if h['guide_xyz']==b['endpoints']['A1']['guide_xyz'] else 3
            return {'node_id':n,'query_node':n,'boundary_kind':'free_endpoint','edge_id':10 if n==1 else 20,'edge_snapshot':es[10 if n==1 else 20],'pos':[0,0,0]},'discovery'
        def request(op,q):
            if op=='route':
                self.assertEqual(q['junction_nodes'],[2]);self.assertEqual(q['required_edges'],[10,20])
                self.assertEqual((q['source_node'],q['target_node']),(1,3) if q['source_edge']==10 else (3,1))
                return row('x',[10,20] if q['source_edge']==10 else [20,10],q['source_edge']==20)['response']
            self.assertEqual(op,'inspect');return {'status':'ok','result':{'edges':[es[i] for i in q['edge_ids']]}}
        for stale in (False,True):
            c={'node_id':2,'pos':[10,0,0],'incident_edges':[10,20,40]}
            with patch('bridge_route_set._endpoint',side_effect=endpoint),patch('bridge_route_set._junction',side_effect=[(c,'initial'),(c|{'node_id':999} if stale else c,'final')]),patch('bridge_route_set._incidence',return_value=ns),patch.object(self.client,'request',side_effect=request):r=rs.inspect_route_set(self.client,b)
            self.assertEqual(r['complete_paths'],0 if stale else 2)
            if stale:self.assertEqual(r['pair_counts']['unknown'],1)
    def test_invalid_counts_names_hints_via_and_nonfinite_limits_rejected(self):
        import bridge_route_set as rs
        for kind in ('count','name','hint','via','length','duplicate'):
            b=self.brief()
            if kind=='count':b['movements']*=4
            elif kind=='name':b['movements'][0]['from']='absent'
            elif kind=='hint':b['endpoints']['A1']['position_tolerance']=0
            elif kind=='via':b['movements'][0]['via']=['absent']
            elif kind=='length':b['max_length']=float('nan')
            else:b['movements'][1]['id']=b['movements'][0]['id']
            with self.subTest(kind=kind),self.assertRaises(ValueError):rs.validate(b)
    def test_read_only_workflow_rechecks_identity_and_captures_stale_change(self):
        import bridge_route_set as rs
        es,ns,row=self.data();b=self.brief();b['endpoints']={n:b['endpoints'][n] for n in ('A1','S1')};b['movements']=[{'id':'one','from':'A1','to':'S1'},{'id':'two','from':'S1','to':'A1'}]
        calls=[];count=0
        def endpoint(c,h):
            nonlocal count
            n=1 if h['guide_xyz']==b['endpoints']['A1']['guide_xyz'] else 3;count+=1
            return {'node_id':n+100 if count==4 else n,'query_node':n,'boundary_kind':'free_endpoint','edge_id':10 if n==1 else 20,'edge_snapshot':es[10 if n==1 else 20],'pos':[0,0,0]},'discovery'
        def request(op,q):
            calls.append(op)
            if op=='route':return row('x',[10,20])['response']
            self.assertEqual(op,'inspect');return {'status':'ok','result':{'edges':[es[i] for i in q['edge_ids']]}}
        with patch('bridge_route_set._endpoint',side_effect=endpoint),patch('bridge_route_set._incidence',return_value=ns),patch.object(self.client,'request',side_effect=request):r=rs.inspect_route_set(self.client,b)
        saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(saved['operations'],[]);self.assertEqual(saved['pairs'][0]['result'],'unknown');self.assertIn('S1',saved['stale_bindings'])
        self.assertTrue(all(op in ('route','inspect') for op in calls));self.assertEqual(count,4)
    def test_ambiguous_binding_is_unknown_without_issuing_route(self):
        import bridge_route_set as rs
        b=self.brief()
        with patch('bridge_route_set._endpoint',side_effect=LiveError('ambiguous_attachment','two current ports')),patch.object(self.client,'request') as native:
            r=rs.inspect_route_set(self.client,b)
        native.assert_not_called();self.assertEqual(r['complete_paths'],0);self.assertEqual(r['pair_counts']['unknown'],10)
    def test_external_failure_stops_instead_of_repeated_discovery(self):
        import bridge_route_set as rs
        with patch('bridge_route_set._endpoint',side_effect=LiveError('timeout','healthy adapter response unavailable')) as discovery:r=rs.inspect_route_set(self.client,self.brief())
        discovery.assert_called_once();self.assertEqual(r['status'],'timeout')
    def test_cli_compact_read_only_entry_and_matrix_exact_support(self):
        import bridge_route_set as rs
        p=self.root/'routes.json';p.write_text(json.dumps(self.brief()))
        with patch('bridge_live.client_from_context',return_value=self.client),patch('bridge_route_set.inspect_route_set',return_value={'status':'ok','game_constructed':False}) as inspect,contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main(['route-set-inspect','--context','dummy','--params',str(p)]),0)
        inspect.assert_called_once();self.assertLess(len(stdout.getvalue().encode()),4096)
        es,ns,row=self.data();rows=[row('a',[10,20]),row('b',[20,10],True)];pairs=rs.assess_route_set(rows,es,ns);s=rs._matrix(rows,pairs)
        self.assertIn('TRACK [10, 20]',s);self.assertIn('reverse [10, 20]',s);self.assertIn('| a | — | O |',s)

class PlainCrossingTests(unittest.TestCase):
    def record(self):
        import itertools
        import bridge_crossing as bc
        rows=[]
        for a,b in itertools.permutations(bc.ARMS,2):
            found=(a,b) in bc.STRAIGHT
            rows.append({'from':a,'to':b,'status':'ok','result':{'native_path_found':found,'requested_route_verified':found,'transport_continuous':found,'truncated':False,'path_count':1 if found else 0,'path':[{}] if found else [],'reason':None if found else 'no_native_path_returned'}})
        return {'arms':[{'id':i} for i in range(1,5)],'center_node':10,'transport_truncated':False,'routes':rows}

    def test_four_straights_eight_observed_absences_qualify_without_global_claim(self):
        from bridge_crossing import classify
        r=classify(self.record())
        self.assertTrue(r['qualified']);self.assertEqual(r['straight_verified'],4)
        self.assertFalse(r['global_no_route_proof']);self.assertEqual(r['shared_physical_crossing_node'],10)

    def test_native_turn_error_truncation_and_missing_observations_do_not_qualify(self):
        from bridge_crossing import classify
        r=self.record();r['routes'][1]['result']['native_path_found']=True
        self.assertEqual(classify(r)['outcome'],'native_turn_movements_observed')
        for field in ('status','truncated'):
            r=self.record()
            if field=='status':r['routes'][1]['status']='route_error'
            else:r['routes'][1]['result']['truncated']=True
            self.assertFalse(classify(r)['qualified'])
        r=self.record();r['routes'].pop();self.assertFalse(classify(r)['qualified'])
        r=self.record();r['routes'][0]['result']['transport_continuous']=False;self.assertFalse(classify(r)['qualified'])

    def test_saved_inspection_is_read_only_and_rejects_stale_or_unfinished_records(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            client=type('Client',(),{'session':'s','evidence':Path(tmp)})()
            client.request=unittest.mock.Mock(return_value={'status':'ok','result':self.record()|{'game_constructed':False}})
            h={'region':{'min':[-1,-1,-1],'max':[1,1,1]},'max_edges':2,'guide_xyz':[0,0,0],'position_tolerance':.01,'travel_direction':[1,0],'heading_tolerance_deg':.1}
            brief={'version':1,'center':[0,0,0],'region':h['region'],'endpoints':{n:h for n in bc.ARMS}}
            record={'version':1,'session':'s','brief':brief,'params':{'ports':{}},'response':{'result':{'game_constructed':True,'center_node':10,'arm_edges':[1,2,3,4]}}}
            p=Path(tmp)/'saved.json';p.write_text(json.dumps(record))
            r=bc.inspect_crossing(client,p);self.assertEqual(r['status'],'ok');self.assertFalse(r['game_constructed'])
            client.request.assert_called_once();self.assertEqual(client.request.call_args.args[0],'inspect_degree_four')
            record['session']='old';p.write_text(json.dumps(record))
            with self.assertRaises(LiveError):bc.inspect_crossing(client,p)
            record['session']='s';record['response']['result']['game_constructed']='unknown';p.write_text(json.dumps(record))
            with self.assertRaises(ValueError):bc.inspect_crossing(client,p)
            self.assertEqual(client.request.call_count,1)

    def test_named_crossing_incidence_reacquires_exact_node_without_widening_query(self):
        import bridge_route_set as rs
        edges={i:{'id':i,'node0':10,'node1':20+i,'p0':[0,0,0],'p1':[i,0,0],'road_type':'TRACK'} for i in range(1,5)}
        record={'junctions':{'crossing':{'node_id':10}},'brief':{'junctions':{'crossing':{'named_hint':True}}},'node_observations':[],'edge_observations':[]}
        c={'node_id':10,'pos':[0,0,0],'incident_edges':[1,2,3,4]}
        with patch('bridge_route_set.live.discover',return_value={'status':'ok','result':{'complete':True,'candidates':[]}}) as discovery,patch('bridge_route_set._junction',return_value=(c,'fresh')) as binding:
            result=rs._incidence(None,edges,record)
        self.assertTrue(result[10]['complete']);self.assertEqual(result[10]['degree'],4)
        binding.assert_called_once_with(None,{'named_hint':True})
        self.assertEqual(discovery.call_args_list[0].args[1]['region'],{'min':[-.1,-.1,-.1],'max':[.1,.1,.1]})
        record['node_observations']=[]
        with patch('bridge_route_set.live.discover',return_value={'status':'ok','result':{'complete':True,'candidates':[]}}),patch('bridge_route_set._junction',return_value=(c|{'node_id':999},'changed')):
            self.assertFalse(rs._incidence(None,edges,record)[10]['complete'])

    def test_construction_defaults_read_only_and_explicit_execution_is_forwarded(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            client=type('Client',(),{'session':'s','evidence':Path(tmp)})()
            client.request=unittest.mock.Mock(return_value={'status':'ok','result':{'game_constructed':False}})
            h={'region':{'min':[-1,-1,-1],'max':[1,1,1]},'max_edges':2,'guide_xyz':[0,0,0],'position_tolerance':.01,'travel_direction':[1,0],'heading_tolerance_deg':.1}
            b={'version':1,'center':[0,0,0],'region':h['region'],'endpoints':{n:h for n in bc.ARMS}}
            with patch('bridge_crossing.live._select_throat_port',return_value=({'edge_snapshot':{'id':1},'node_id':2},'discovery')):
                bc.crossing(client,b);self.assertIs(client.request.call_args.args[1]['execute'],False)
                bc.crossing(client,b,execute=True);self.assertIs(client.request.call_args.args[1]['execute'],True)
            self.assertEqual(client.request.call_count,2)

class ComposedCrossingTests(unittest.TestCase):
    def brief(self):
        import math
        d=[math.cos(math.radians(15)),math.sin(math.radians(15))]
        h=lambda p:{'region':{'min':[v-1 for v in p],'max':[v+1 for v in p]},'max_edges':4,'guide_xyz':p,'position_tolerance':.001,'travel_direction':[1,0],'heading_tolerance_deg':.1}
        return {'version':2,'center':[150,15,2],'region':{'min':[-25,-5,1],'max':[325,35,3]},'endpoints':{n:h([x,y,2]) for n,x,y in [('a_in',0,0),('a_out',300,30),('b_in',0,30),('b_out',300,0)]},'pairs':[['a_in','a_out'],['b_in','b_out']],'axes':[d,[d[0],-d[1]]],'half_arm_length':40,'radius':60,'max_route_length':1000}

    def test_explicit_pairing_tip_directions_and_nondegenerate_level_validation(self):
        import bridge_crossing as bc
        b=self.brief();bc.validate(b);tips=bc._tips(b)
        self.assertLess(tips['a_in']['position'][0],150);self.assertLess(tips['a_in']['position'][1],15)
        self.assertEqual(tips['a_in']['binding_sign'],1);self.assertEqual(tips['a_out']['binding_sign'],-1)
        b['axes'][1]=b['axes'][0]
        with self.assertRaises(ValueError):bc.validate(b)
        b=self.brief();b['pairs'][1][0]='a_in'
        with self.assertRaises(ValueError):bc.validate(b)
        b=self.brief();b['endpoints']['b_in']['guide_xyz'][2]+=1
        with self.assertRaises(ValueError):bc.validate(b)

    def test_caller_named_pairing_qualifies_only_the_explicit_four_movements(self):
        import bridge_crossing as bc
        r=PlainCrossingTests().record();rename=dict(zip(bc.ARMS,['a_in','a_out','b_in','b_out']))
        for row in r['routes']:row['from']=rename[row['from']];row['to']=rename[row['to']]
        r['pairs']=[['a_in','a_out'],['b_in','b_out']]
        self.assertTrue(bc.classify(r)['qualified'])
        r['pairs']=[['a_in','b_out'],['b_in','a_out']]
        self.assertFalse(bc.classify(r)['qualified'])

    def test_read_only_preparation_and_partial_build_stop_preserve_receipt(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            b=self.brief();client=type('Client',(),{'session':'s','evidence':Path(tmp)})();calls=[]
            def binding(client,intent,**kwargs):
                i=list(b['endpoints'].values()).index(next(h for h in b['endpoints'].values() if h['guide_xyz']==intent['guide_xyz']))
                return {'node_id':i+10,'edge_id':i+1,'edge_snapshot':{'id':i+1},'pos':intent['guide_xyz'],'grade':0,'outward_direction':[kwargs['outward_sign'],0,0]},'discovery'
            def request(op,p):
                calls.append(op)
                if op=='fit':return {'status':'ok','result':{'fit_request':str(len(calls))}}
                return {'status':'mutation_unverified','result':{'game_constructed':'unknown','error':'native partial effects'}}
            client.request=request
            with patch('bridge_crossing.live._select_throat_port',side_effect=binding):
                prepared=bc.crossing(client,b);self.assertEqual(prepared['stage'],'prepared');self.assertFalse(prepared['game_constructed']);self.assertEqual(calls,['fit']*4)
                r=bc.crossing(client,b,execute=True,prepared_record=prepared['evidence'])
                self.assertEqual(r['status'],'mutation_unverified');self.assertEqual(r['game_constructed'],'unknown');self.assertEqual(calls,['fit']*4+['extension'])
                saved=json.loads(Path(r['evidence']).read_text());self.assertEqual(len(saved['operations']),1);self.assertIn('native partial effects',saved['operations'][0]['response']['result']['error'])

    def test_execution_composes_four_native_extensions_before_exact_paired_crossing(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            b=self.brief();client=type('Client',(),{'session':'s','evidence':Path(tmp)})();calls=[]
            ports={n:{'edge_id':i+1,'node_id':i+10} for i,n in enumerate(b['endpoints'])}
            prepared={'version':2,'brief':b,'session':'s','ports':ports,'leads':{n:{} for n in ports},'game_constructed':False,'operations':[],'summary':{'stage':'prepared'}}
            p=Path(tmp)/'prepared.json';p.write_text(json.dumps(prepared))
            def request(op,q):
                calls.append((op,q))
                if op=='extension':
                    i=q['brief']['anchor_edge'];return {'status':'ok','result':{'readback':{'ordered_edges':[100+i],'ordered_nodes':[i+9,200+i]}}}
                return {'status':'ok','result':{'center_node':500,'arm_edges':[501,502,503,504]}}
            def observation(c,b,n,lead,port):lead['inspection']={'result':{'edges':[{'id':lead['edges'][-1]}]}}
            client.request=request
            with patch('bridge_crossing._bindings',return_value=ports),patch('bridge_crossing._lead_observation',side_effect=observation),patch('bridge_crossing._inspect_composed',return_value={'status':'ok','game_constructed':False}):
                r=bc.crossing(client,b,execute=True,prepared_record=p)
            self.assertEqual([op for op,q in calls],['extension']*4+['degree_four_candidate'])
            self.assertTrue(all(q['execute'] is True and q['brief']['radius']==60 for op,q in calls[:4]))
            self.assertEqual(calls[-1][1]['pairs'],b['pairs']);self.assertEqual(calls[-1][1]['center'],b['center'])
            record=json.loads(Path(r['construction_record']).read_text());self.assertTrue(record['complete_receipts']);self.assertEqual(len(record['operations']),5)

    def test_stale_or_incomplete_records_reject_without_native_operations(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            client=type('Client',(),{'session':'current','evidence':Path(tmp)})();client.request=unittest.mock.Mock()
            b=self.brief();p=Path(tmp)/'old.json';p.write_text(json.dumps({'brief':b,'session':'old','game_constructed':False,'summary':{'stage':'prepared'}}))
            r=bc.crossing(client,b,execute=True,prepared_record=p);self.assertEqual(r['status'],'invalid_crossing_record')
            with self.assertRaises(LiveError):bc.inspect_crossing(client,p)
            p.write_text(json.dumps({'brief':b,'session':'current','complete_receipts':False}))
            with self.assertRaises(LiveError):bc.inspect_crossing(client,p)
            client.request.assert_not_called()

    def test_cubic_footprint_includes_interior_extrema(self):
        import bridge_crossing as bc
        e={'p0':[0,0,2],'p1':[10,0,2],'t0':[10,20,0],'t1':[10,-20,0]}
        points=bc._edge_extrema(e);self.assertAlmostEqual(max(p[1] for p in points),5)
        self.assertEqual({p[2] for p in points},{2})

    def test_changed_arm_tangents_do_not_pass_position_only_acceptance(self):
        import bridge_crossing as bc
        b=self.brief();ports={}
        for i,(name,t) in enumerate(bc._tips(b).items()):
            v=[b['center'][j]-t['position'][j] for j in range(3)]
            ports[name]={'node':i+1,'arm':{'node0':i+1,'node1':100,'p0':t['position'],'p1':b['center'],'t0':v,'t1':v}}
        inner={'ports':ports};self.assertTrue(all(abs(n-40)<1e-8 for n in bc._check_arms(b,inner)))
        ports['a_in']['arm']['t0']=[1,0,0]
        with self.assertRaises(LiveError):bc._check_arms(b,inner)

    def test_cross_pair_shared_stem_or_unknown_incidence_does_not_pass(self):
        import bridge_crossing as bc
        b=self.brief();names=[a+'_to_'+z for pair in b['pairs'] for a,z in (pair,list(reversed(pair)))]
        rows=[{'a':a,'b':z,'both_paths_complete':True,'shared_TRACK_edges':[],'shared_junction_nodes':[500]} for a in names[:2] for z in names[2:]]
        self.assertTrue(bc._cross_pair_conflicts({'pairs':rows},b,500))
        rows[0]['shared_TRACK_edges']=[1];self.assertFalse(bc._cross_pair_conflicts({'pairs':rows},b,500))
        rows[0]['shared_TRACK_edges']=[];rows[0]['shared_junction_nodes']=[];self.assertFalse(bc._cross_pair_conflicts({'pairs':rows},b,500))

    def test_malformed_pairing_and_semantic_names_reject_before_execution(self):
        import bridge_crossing as bc
        for value in (None,{},[None,None],[[1,'a_out'],['b_in','b_out']],[['bad name','a_out'],['b_in','b_out']]):
            b=self.brief();b['pairs']=value
            with self.assertRaises(ValueError):bc.validate(b)

    def test_prepared_record_cannot_rebuild_already_connected_boundaries(self):
        import bridge_crossing as bc
        with tempfile.TemporaryDirectory() as tmp:
            b=self.brief();client=type('Client',(),{'session':'s','evidence':Path(tmp)})();client.request=unittest.mock.Mock()
            p=Path(tmp)/'prepared.json';p.write_text(json.dumps({'brief':b,'session':'s','ports':{},'game_constructed':False,'summary':{'stage':'prepared'}}))
            def selected(*args,**kwargs):
                self.assertIs(kwargs['connected'],False)
                raise LiveError('no_eligible_candidates','boundary has an existing lead')
            with patch('bridge_crossing.live._select_throat_port',side_effect=selected):r=bc.crossing(client,b,execute=True,prepared_record=p)
            self.assertEqual(r['status'],'no_eligible_candidates');self.assertFalse(r['game_constructed']);client.request.assert_not_called()

class ReferenceRouteSetTests(unittest.TestCase):
    """Controlled native-shaped binary tree: no physical terminal demonstration."""
    def run_reference(self,tmp,*,fault=None,batch_size=16,free=False):
        import bridge_route_set as rs
        reference=json.loads((Path(__file__).parent/'fixtures/route_set_reference.json').read_text())
        names=reference['endpoints'];edges={};calls=[];route_index=0;inspect_counts={}
        def edge(i,a,z):return {'id':i,'road_type':'TRACK','node0':a,'node1':z,'p0':[a,0,0],'p1':[z,0,0],'t0':[z-a,0,0],'t1':[z-a,0,0],'template':'mock_track','style':'mock_normal'}
        for n in range(2,44):edges[n-1]=edge(n-1,n//2,n)
        for i,n in enumerate(names):edges[100+i]=edge(100+i,22+i,1000+i)
        hints={n:{'region':{'min':[21+i,-1,-1],'max':[23+i,1,1]},'max_edges':16,'guide_xyz':[22+i,0,0],'position_tolerance':.001,'travel_direction':[-1,0],'heading_tolerance_deg':.1} for i,n in enumerate(names)}
        if free:
            for i,h in enumerate(hints.values()):h.update(region={'min':[999+i,-1,-1],'max':[1001+i,1,1]},guide_xyz=[1000+i,0,0],travel_direction=[1,0],boundary_kind='free_endpoint')
        brief={'version':1,'endpoints':hints,'junctions':{},'movements':reference['movements'],'mode':'TRAIN','max_length':8000,'batch_size':batch_size}
        client=type('Client',(),{'session':'reference_session','evidence':Path(tmp)})()
        def request(op,q):
            nonlocal route_index
            calls.append((op,q));out={'session':client.session,'request_id':str(len(calls)),'status':'ok'}
            if op=='inspect':
                assert len(q['edge_ids'])<=16
                rows=[]
                for i in q['edge_ids']:
                    inspect_counts[i]=inspect_counts.get(i,0)+1;e=json.loads(json.dumps(edges[i]))
                    if fault=='resource' and i==101 and inspect_counts[i]>=3:e['t0'][0]+=1
                    rows.append(e)
                out['result']={'edges':rows}
            elif op=='discover':
                pos=[sum(q['region'][v][i] for v in ('min','max'))/2 for i in range(3)];node=round(pos[0]);inc=[i for i,e in edges.items() if node in (e['node0'],e['node1'])]
                candidates=[]
                for i in inc:
                    e=edges[i];d=-1 if node==e['node0'] else 1
                    candidates.append({'node_id':node,'edge_id':i,'edge_snapshot':e,'pos':pos,'outward_direction':[d,0,0],'grade':0,'eligible':len(inc)==1,'construction_owner':-1,'incident_edges':inc,'incident_count':len(inc),'incidence_complete':True,'incident_output_truncated':False})
                out['result']={'complete':True,'candidates':candidates}
            else:
                assert op=='route';index=route_index;route_index+=1
                a=edges[q['source_edge']]['node0'];z=edges[q['target_edge']]['node0']
                up=lambda n:[n]+up(n//2) if n>1 else [1]
                aa,zz=up(a),up(z);lca=next(n for n in aa if n in zz);nodes=[q['source_node']]+aa[:aa.index(lca)+1]+list(reversed(zz[:zz.index(lca)]))+[q['target_node']]
                path=[]
                for x,y in zip(nodes,nodes[1:]):
                    i=next(i for i,e in edges.items() if {e['node0'],e['node1']}=={x,y})
                    path.append({'edge':{'entity':i,'index':0},'from':{'entity':x,'index':0},'to':{'entity':y,'index':0},'forward':edges[i]['node0']==x,'confirmed_TRACK':True})
                out['result']={'path':path,'path_count':len(path),'native_path_found':True,'requested_route_verified':True,'transport_continuous':True,'truncated':False}
                if index==20 and fault=='route_error':out.update(status='error',result={'error':'controlled native error'})
                if index==20 and fault=='opaque':
                    p=path[0]['to'];path.insert(1,{'edge':{'entity':9000,'index':0},'from':p,'to':p,'forward':True,'confirmed_TRACK':False});out['result']['path_count']+=1
                if index==16 and fault=='session':client.session='other_session'
            return out
        client.request=request
        result=rs.inspect_route_set(client,brief);saved=json.loads(Path(result['evidence']).read_text())
        return result,saved,calls,brief

    def test_full_distinct_contract_and_all_cross_batch_comparisons(self):
        with tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp)
        self.assertEqual(len(b['endpoints']),22);self.assertEqual(len({(m['from'],m['to']) for m in b['movements']}),56)
        self.assertEqual(r['complete_paths'],56);self.assertEqual(r['pairs_assessed'],1540);self.assertEqual(r['observation_batches'],4)
        a,z=b['movements'][0]['id'],b['movements'][16]['id'];p=next(p for p in s['pairs'] if (p['a'],p['b'])==(a,z))
        self.assertTrue(p['shared_TRACK_edges']);self.assertEqual(p['result'],'topology_overlap')
        self.assertTrue(all(op in ('discover','inspect','route') for op,q in c));self.assertLess(len(json.dumps(r).encode()),4096)
        self.assertEqual(sum(op=='route' for op,q in c),56)
        # Endpoint binding once at start and once for final freshness, independent of batches.
        guides={tuple(h['guide_xyz']) for h in b['endpoints'].values()}
        endpoint_reads=[q for op,q in c if op=='discover' and tuple(sum(q['region'][v][i] for v in ('min','max'))/2 for i in range(3)) in guides and q['region']['max'][1]==1]
        self.assertEqual(len(endpoint_reads),44)

    def test_free_reference_endpoints_preserve_both_directions_and_full_footprint(self):
        with tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp,free=True)
        self.assertEqual(r['complete_paths'],56);self.assertEqual(r['pairs_assessed'],1540)
        for m in s['movements']:
            a,z=(m['bindings'][m[k]] for k in ('from','to'))
            self.assertEqual(m['query']['source_node'],a['node_id']);self.assertEqual(m['query']['target_node'],z['node_id'])
            self.assertEqual(m['physical_tracks'][0]['edge_id'],a['edge_id']);self.assertEqual(m['physical_tracks'][-1]['edge_id'],z['edge_id'])
        self.assertTrue(all(op in ('discover','inspect','route') for op,q in c))

    def test_cross_batch_native_errors_and_opaque_resources_remain_unknown(self):
        for fault in ('route_error','opaque'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp,fault=fault)
            self.assertEqual(r['pairs_assessed'],1540);self.assertEqual(r['complete_paths'],55)
            p=next(p for p in s['pairs'] if p['a']==b['movements'][0]['id'] and p['b']==b['movements'][20]['id'])
            self.assertFalse(p['both_paths_complete']);self.assertNotEqual(p['result'],'topology_disjoint')

    def test_session_change_stops_and_preserves_all_requested_unknown_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp,fault='session')
        self.assertEqual(r['status'],'stale_session');self.assertEqual(r['pair_counts']['unknown'],1540);self.assertEqual(r['complete_paths'],0)
        self.assertEqual(sum(op=='route' for op,q in c),17)

    def test_final_resource_change_invalidates_affected_paths(self):
        with tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp,fault='resource')
        self.assertIn(101,s['stale_resources']['edges']);self.assertLess(r['complete_paths'],56)
        changed=[m for m in s['movements'] if m.get('stale_resources')];self.assertTrue(changed);self.assertTrue(all(not m['complete'] for m in changed))

    def test_finite_call_budget_keeps_partial_records_without_disjoint_claims(self):
        with patch('bridge_route_set.MAX_CALLS',100),tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp)
        self.assertEqual(r['status'],'observation_budget_exhausted');self.assertEqual(len(c),100);self.assertEqual(r['pair_counts']['unknown'],1540)
        self.assertTrue(s['observation_failure']);self.assertFalse(r['game_constructed'])

    def test_batch_boundary_and_request_limits(self):
        import bridge_route_set as rs
        with tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp,batch_size=3)
        self.assertEqual(r['complete_paths'],56);self.assertEqual(r['pairs_assessed'],1540);self.assertEqual(r['observation_batches'],19)
        for size in (0,17,True):
            with self.assertRaises(ValueError):rs.validate(b|{'batch_size':size})
        with self.assertRaises(ValueError):rs.validate(b|{'movements':[b['movements'][0]|{'id':'m'+str(i)} for i in range(65)]})

    def test_deadline_and_resource_budget_stop_without_success_claims(self):
        with patch('bridge_route_set.MAX_SECONDS',0),tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp)
        self.assertEqual(r['status'],'observation_budget_exhausted');self.assertEqual(len(c),0);self.assertEqual(r['pair_counts']['unknown'],1540)
        with patch('bridge_route_set.MAX_TRACKS',10),tempfile.TemporaryDirectory() as tmp:r,s,c,b=self.run_reference(tmp)
        self.assertEqual(r['status'],'observation_bound');self.assertEqual(r['pair_counts']['unknown'],1540)

class StationSurveyTests(unittest.TestCase):
    setUp=LiveClientTests.setUp
    def station(self,count=16):
        ports=[]
        for i in range(count):
            pos=[30,i*8+(i%2)*2,12+i*.01];e={'id':100+i,'node0':200+i,'node1':300+i,'p0':[0,pos[1],12],'p1':pos,'road_type':'TRACK'}
            ports.append({'node_id':300+i,'edge_id':100+i,'pos':pos,'outward_direction':[1,0,0],'grade':.001,
                'edge_snapshot':e,'incident_count':1,'incident_edges':[100+i],'incidence_complete':True,
                'incident_output_truncated':False,'construction_owner':'none','eligible':True})
        return {'outcome':'resolved','complete':True,'name':'Wickham Station','group_id':1,'group_revision':[1,2,3],
                'constructions':[{'construction_id':2,'position':[0,0,12]}],
                'stations':[{'station_id':3,'terminal_count':16}],'ports':ports,'game_constructed':False}
    def test_observed_frame_spacing_count_and_grade_are_not_invented(self):
        from bridge_station import mouth_groups
        g=mouth_groups(self.station()['ports'])[0]
        self.assertEqual(g['ordered_nodes'],list(range(300,316)));self.assertEqual(g['spacings'],[10,6]*7+[10])
        self.assertEqual(g['span'],122);self.assertAlmostEqual(g['elevation_spread'],.15)
        self.assertEqual(g['direction'],[1,0]);self.assertEqual(g['max_heading_deviation_deg'],0)
    def test_lookup_outcomes_are_unavailable_without_site_or_second_lookup(self):
        from bridge_station import inspect_station
        for outcome in ('not_found','ambiguous_station','lookup_budget_exhausted','external_observation_incomplete'):
            with self.subTest(outcome=outcome),patch.object(self.client,'request',return_value={'status':'ok','result':{'outcome':outcome,'complete':False,'matches':[{'group_id':1},{'group_id':2}]}}) as request:
                r=inspect_station(self.client,{'name':'Wickham Station'})
                self.assertEqual(r['status'],outcome);self.assertFalse(r['game_constructed']);request.assert_called_once()
    def test_bad_brief_bounds_reject_before_native_calls(self):
        from bridge_station import inspect_station
        for b in ({},{'name':''},{'name':'x','max_groups':257},{'name':'x','max_external_edges':True},{'name':'x','max_lead_distance':801},{'name':'x','survey_depth':float('nan')},{'name':'x','execute':True}):
            with self.subTest(b=b),patch.object(self.client,'request') as calls,self.assertRaises(ValueError):inspect_station(self.client,b)
            calls.assert_not_called()
    def test_exact_free_identity_rejected_without_site_reads(self):
        from bridge_station import inspect_station
        for bad in ('node','edge','incidence','position','owner'):
            v=self.station();p=v['ports'][0]
            if bad=='node':p['node_id']=999
            elif bad=='edge':p['edge_id']=999
            elif bad=='incidence':p['incident_edges']=[999]
            elif bad=='position':p['pos']=[999,0,0]
            else:p['construction_owner']=99
            with patch.object(self.client,'request',return_value={'status':'ok','result':v}) as calls:r=inspect_station(self.client,{'name':'Wickham Station'})
            self.assertEqual(r['status'],'invalid_result');calls.assert_called_once()
    def test_integrated_read_only_survey_and_stale_final_identity(self):
        from bridge_station import inspect_station
        for stale in (False,True):
            v=self.station();calls=[];lookups=0
            def request(op,p):
                nonlocal lookups
                calls.append((op,p));self.assertFalse(is_mutation(op,p))
                if op=='station_lookup':
                    lookups+=1;result=v|{'group_revision':[9,9,9]} if stale and lookups==2 else v
                else:
                    self.assertEqual(op,'inspect');self.assertLessEqual(len(p['site']['positions']),8)
                    result={'site':{'truncated':False,'terrain':[]}}
                return {'status':'ok','session':self.client.session,'result':result}
            with patch.object(self.client,'request',side_effect=request):r=inspect_station(self.client,{'name':'Wickham Station'})
            self.assertEqual(r['status'],'stale_station' if stale else 'ok');self.assertFalse(r['game_constructed']);self.assertEqual(len(calls),4)
            if not stale:self.assertEqual(r['free_connection_count'],16);self.assertLess(len(json.dumps(r).encode()),4096)
    def test_does_not_manufacture_sixteen_and_compacts_large_inventory(self):
        from bridge_station import inspect_station
        for count in (3,32):
            v=self.station(count)
            with patch.object(self.client,'request',side_effect=lambda op,p:{'status':'ok','result':v if op=='station_lookup' else {'site':{'truncated':False}}}):r=inspect_station(self.client,{'name':'Wickham Station'})
            self.assertEqual(r['status'],'ok');self.assertEqual(r['free_connection_count'],count);self.assertEqual(r['port_summary_truncated'],count>16)
            self.assertLess(len(json.dumps(r).encode()),4096)
    def test_cli_is_read_only_and_uses_public_station_survey(self):
        p=self.root/'station.json';p.write_text('{"name":"Wickham Station"}')
        with patch('bridge_live.client_from_context',return_value=self.client),patch('bridge_station.inspect_station',return_value={'status':'ok','game_constructed':False}) as inspect,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['station-survey','--context','dummy','--params',str(p)]),0)
        inspect.assert_called_once()

class NativeNearstraightEvidenceTests(unittest.TestCase):
    """Independent Bezier checks of the actual native regression record.

    These do not execute Lua; runtime acceptance also exercises the native repair.
    """
    def fixture(self):
        return json.loads((Path(__file__).parent/'fixtures/live_rotated_nearstraight.json').read_text())

    def observe(self,c,u):
        import math
        # Convert the recorded Hermite handles to Bezier control points, then use
        # de Casteljau derivatives independently of the native bound implementation.
        points=[c['p0'],[c['p0'][k]+c['t0'][k]/3 for k in range(3)],
                [c['p1'][k]-c['t1'][k]/3 for k in range(3)],c['p1']]
        def lerp(a,b):return [(1-u)*x+u*y for x,y in zip(a,b)]
        d=[[3*(b[k]-a[k]) for k in range(3)] for a,b in zip(points,points[1:])]
        dd=[[2*(b[k]-a[k]) for k in range(3)] for a,b in zip(d,d[1:])]
        speed=lerp(lerp(d[0],d[1]),lerp(d[1],d[2]));accel=lerp(dd[0],dd[1])
        horizontal=math.hypot(*speed[:2]);self.assertGreater(horizontal,1e-9)
        cross=abs(speed[0]*accel[1]-speed[1]*accel[0])
        radius=horizontal**3/cross if cross else math.inf
        return radius,abs(speed[2])/horizontal

    def test_captured_native_arc_is_valid_but_fragment_cubic_is_not(self):
        f=self.fixture();parts=f['failed_native_parts']
        self.assertEqual(len(parts),3);self.assertAlmostEqual(parts[0]['length'],.003154277801513672)
        self.assertEqual(parts[0]['radius'],157.5);self.assertEqual(parts[0]['start'][1],parts[0]['finish'][1])
        self.assertNotEqual(parts[0]['tangent_start'][1],0)
        radius=min(self.observe(f['failed_controls'][0],j/256)[0] for j in range(257))
        self.assertLess(radius,.01)  # Rejecting these fragments is still correct.

    def test_actual_repartition_meets_hard_radius_and_grade_at_finer_samples(self):
        f=self.fixture();fit=f['accepted_fit'];c=fit['controls'][0]
        self.assertEqual(fit['pieces'],1);self.assertEqual(len(fit['original_native_controls']),3)
        self.assertEqual(fit['requested_min_radius'],150);self.assertEqual(fit['max_grade'],.01)
        samples=[self.observe(c,j/256) for j in range(257)]
        self.assertGreaterEqual(min(x[0] for x in samples),150)
        self.assertLessEqual(max(x[1] for x in samples),.01)
        self.assertLessEqual(fit['nearstraight_repartition']['sampled_XY_error'],.1)
        self.assertEqual(c['p0'],f['failed_controls'][0]['p0'])
        self.assertLess(abs(c['p1'][0]-f['brief']['end_xy'][0]),.001)
        self.assertLess(abs(c['p1'][1]-f['brief']['end_xy'][1]),.001)
        self.assertEqual(c['p1'][2],f['brief']['vertical']['end_height'])
        self.assertAlmostEqual(c['t0'][2]/(c['t0'][0]**2+c['t0'][1]**2)**.5,fit['grade'],places=7)
        self.assertEqual(c['t1'][2],0)

    def test_radius_check_still_detects_material_curve_and_axes_straight(self):
        curved={'p0':[0,0,0],'p1':[10,10,0],'t0':[15,0,0],'t1':[0,15,0]}
        self.assertLess(min(self.observe(curved,j/256)[0] for j in range(257)),150)
        straight={'p0':[0,0,0],'p1':[30,0,0],'t0':[30,0,0],'t1':[30,0,0]}
        self.assertTrue(all(self.observe(straight,j/256)==(float('inf'),0) for j in range(257)))

    def test_native_domain_and_hard_checks_remain_explicit(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        fit=source.split('function M.fit(',1)[1].split('function M.readback',1)[0]
        for guard in ('#controls>1 and straight_count==1 and arc_turn<=.1',
                      'discardedlength<=.001','geometry_bounds(cg,p.region,p.radius,maxgrade or math.abs(grade))',
                      'maxerr<=.1 and maxheading<=.1','maxzerr<=.001','endpoint_grade_mismatch'):
            self.assertIn(guard,fit)

    def test_native_diagnostics_remain_local_under_cli_output_target(self):
        f=self.fixture();response={'status':'ok','session':'test_session','evidence':'local.workflow.json',
                                  'fit':f['accepted_fit']}
        with tempfile.TemporaryDirectory() as tmp:
            params=Path(tmp)/'brief.json';params.write_text(json.dumps(f['brief']))
            client=type('Client',(),{'session':'test_session'})()
            stdout=io.StringIO()
            with patch('bridge_live.client_from_context',return_value=client),patch('bridge_live.extend',return_value=response),contextlib.redirect_stdout(stdout):
                self.assertEqual(main(['extend','--context','unused','--params',str(params)]),0)
            self.assertLess(len(stdout.getvalue().encode()),4096)

class NativeAggregateTinyEvidenceTests(unittest.TestCase):
    """Actual P44 record; independent geometry checks, not a Lua interpreter."""
    def fixture(self):
        return json.loads((Path(__file__).parent/'fixtures/live_nearstraight_aggregate.json').read_text())

    def test_aggregate_over_budget_retains_every_native_part(self):
        f=self.fixture();parts=f['failed_native_parts'];fit=f['accepted_fit']
        arcs=[p for p in parts if 'radius' in p]
        self.assertEqual(len(arcs),2)
        self.assertTrue(all(p['length']<=.001 for p in arcs))
        self.assertGreater(sum(p['length'] for p in arcs),.001)
        self.assertEqual(parts,fit['native_parts'])
        self.assertFalse(parts[0]['forward'])
        self.assertEqual(fit['discarded_native_total_length'],0)
        self.assertFalse(fit['discarded_native_tiny_parts'])
        self.assertEqual(len(fit['original_native_controls']),3)
        self.assertEqual(fit['nearstraight_repartition']['original_pieces'],3)

    def test_actual_130_unit_repartition_keeps_endpoints_and_hard_bounds(self):
        f=self.fixture();c=f['accepted_fit']['controls'][0];b=f['brief']
        observer=NativeNearstraightEvidenceTests()
        samples=[observer.observe(c,j/256) for j in range(257)]
        self.assertGreaterEqual(min(x[0] for x in samples),b['radius'])
        self.assertLessEqual(max(x[1] for x in samples),b['vertical']['max_grade'])
        self.assertEqual(c['p0'][:2],f['failed_native_parts'][0]['start'][:2])
        self.assertEqual(c['p1'][:2],f['failed_native_parts'][-1]['finish'][:2])
        self.assertEqual(c['p1'][2],b['vertical']['end_height'])
        self.assertLessEqual(f['accepted_fit']['sampled_XY_error'],.1)

    def test_retention_precedes_existing_lowering_and_hard_checks(self):
        s=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        fit=s.split('function M.fit(',1)[1].split('function M.readback',1)[0]
        self.assertLess(fit.index('if discardedlength>.001 then'),fit.index('assert(discardedlength<=.001'))
        self.assertIn('filtered=result;discarded={};discardedlength=0',fit)
        self.assertLess(fit.index('assert(discardedlength<=.001'),fit.index('#controls>1 and straight_count==1 and arc_turn<=.1'))
        self.assertIn('geometry_bounds(cg,p.region,p.radius,maxgrade or math.abs(grade))',fit)

class RejectedExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.client=LiveClient(root/'mod',root/'log',root/'evidence','current',.02)
        self.pending={'session':'current','request_id':'rejected','operation':'extension',
                      'params':{'execute':True,'brief':{'anchor_edge':10,'anchor_node':11,
                       'end_xy':[100,0],'end_direction':[1,0],'radius':70,
                       'region':{'min':[-20,-20,-2],'max':[120,20,5]}}}}
        self.response={'session':'current','request_id':'rejected','operation':'extension','status':'error',
                       'result':{'native_command_success':False,'error':'native_construction_rejected',
                                 'stage':'build','game_constructed':'unknown','fit':{'start_node':11,'start':[0,0,1]}}}
        edge={'id':10,'node0':12,'node1':11,'p0':[-10,0,1],'p1':[0,0,1],
              't0':[10,0,0],'t1':[10,0,0],'road_type':'TRACK','template':'track','style':'style'}
        self.original={'session':'current','request_id':'baseline','operation':'discover','status':'ok',
                       'result':{'complete':True,'truncated':False,'game_constructed':False,'candidates':[
                           {'edge_id':10,'node_id':11,'edge_snapshot':edge,'pos':[0,0,1],
                            'eligible':True,'incidence_complete':True,'incident_output_truncated':False,
                            'incident_count':1,'incident_edges':[10],'construction_owner':-1}]}}
        self.fresh=json.loads(json.dumps(self.original));self.fresh['request_id']='fresh'
        self.save_pending()

    def save_pending(self):
        self.client.journal.write_text(json.dumps({'session':'current','pending':self.pending}))
        (self.client.evidence/'rejected.response.json').write_text(json.dumps(self.response))

    def reconcile(self):
        from bridge_live import reconcile_rejected_extension
        return reconcile_rejected_extension(self.client,self.original)

    def test_fresh_exact_free_anchor_closes_only_rejected_extension(self):
        original_bytes=(self.client.evidence/'rejected.response.json').read_bytes()
        with patch.object(self.client,'request',return_value=self.fresh) as calls:
            value=self.reconcile()
        calls.assert_called_once_with('discover',{'region':{'min':[-1,-1,0],'max':[1,1,2]},'max_edges':16})
        self.assertFalse(is_mutation(*calls.call_args.args))
        self.assertTrue(value['result']['completed_extension_absent'])
        self.assertEqual(value['result']['other_effects'],'unknown')
        self.assertFalse(value['result']['automatic_replay'])
        self.assertFalse(value['result']['effects_history_complete'])
        self.assertNotIn('game_constructed',value['result'])
        self.assertEqual((self.client.evidence/'rejected.response.json').read_bytes(),original_bytes)
        state=json.loads(self.client.journal.read_text());self.assertNotIn('pending',state)
        self.assertIn('rejected',state['reconciled_rejections'])
        self.assertEqual(json.loads(Path(value['evidence']).read_text())['original_pending'],self.pending)
        with patch.object(self.client,'request') as calls,self.assertRaises(LiveError):self.reconcile()
        calls.assert_not_called()

    def test_mismatch_or_nonexplicit_rejection_never_observes_or_clears(self):
        for defect in ('state_session','pending_session','request','operation','response_session','command',
                       'stage','error','status','fit_node','fit_position','baseline_session'):
            with self.subTest(defect=defect):
                self.setUp()
                if defect=='pending_session':self.pending['session']='old'
                elif defect=='request':self.response['request_id']='other'
                elif defect=='operation':self.response['operation']='connection'
                elif defect=='response_session':self.response['session']='old'
                elif defect=='command':self.response['result'].pop('native_command_success')
                elif defect=='stage':self.response['result']['stage']='fit'
                elif defect=='error':self.response['result']['error']='timeout'
                elif defect=='status':self.response['status']='mutation_unverified'
                elif defect=='fit_node':self.response['result']['fit']['start_node']=12
                elif defect=='fit_position':self.response['result']['fit']['start']=[1,0,1]
                elif defect=='baseline_session':self.original['session']='old'
                self.save_pending()
                if defect=='state_session':self.client.journal.write_text(json.dumps({'session':'old','pending':self.pending}))
                with patch.object(self.client,'request') as calls,self.assertRaises(LiveError):self.reconcile()
                calls.assert_not_called()
                self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)

    def test_changed_ambiguous_or_incomplete_fresh_anchor_retains_pending(self):
        for defect in ('changed','ambiguous','occupied','owner','wrong_edge','node','position','TRACK',
                       'incomplete','truncated','incidence','incident_edges','query','session'):
            with self.subTest(defect=defect):
                self.setUp();r=self.fresh['result'];c=r['candidates'][0]
                if defect=='changed':c['edge_snapshot']['t1'][0]=11
                elif defect=='ambiguous':r['candidates'].append(json.loads(json.dumps(c)))
                elif defect=='occupied':c['incident_count']=2;c['eligible']=False
                elif defect=='owner':c['construction_owner']=5
                elif defect=='wrong_edge':c['edge_snapshot']['id']=20
                elif defect=='node':c['node_id']=12
                elif defect=='position':c['pos']=[1,0,1]
                elif defect=='TRACK':c['edge_snapshot']['road_type']='STREET'
                elif defect=='incomplete':r['complete']=False
                elif defect=='truncated':r['truncated']=True
                elif defect=='incidence':c['incidence_complete']=False
                elif defect=='incident_edges':c['incident_edges']=[20]
                elif defect=='query':self.fresh['status']='error'
                elif defect=='session':self.fresh['session']='old'
                with patch.object(self.client,'request',return_value=self.fresh),self.assertRaises(LiveError):self.reconcile()
                self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)
                self.assertFalse((self.client.evidence/'rejected.reconciliation.json').exists())

    def test_pending_race_and_observation_storage_failure_do_not_clear_mutation(self):
        for defect in ('race','storage'):
            with self.subTest(defect=defect):
                self.setUp()
                def query(*args):
                    if defect=='storage':raise PermissionError('observation unavailable')
                    changed=self.pending|{'request_id':'different'}
                    self.client.journal.write_text(json.dumps({'session':'current','pending':changed}))
                    return self.fresh
                with patch.object(self.client,'request',side_effect=query),self.assertRaises((LiveError,PermissionError)):self.reconcile()
                self.assertIn('pending',json.loads(self.client.journal.read_text()))
                self.assertFalse((self.client.evidence/'rejected.reconciliation.json').exists())

class ExactChainRemovalTests(unittest.TestCase):
    def test_native_identity_read_separates_node_and_edge_positions(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        read=source[source.index('local function edge(id)'):source.index('local function anchor(p)')]
        self.assertIn('e.roadType==E.RoadType.TRACK',read)
        self.assertIn('getComponent(e.node0,api.type.ComponentType.BASE_NODE)',read)
        self.assertIn('getComponent(e.node1,api.type.ComponentType.BASE_NODE)',read)
        self.assertIn('assert(n0 and n1,"endpoint_node_unavailable")',read)
        self.assertIn('vector(np0);vector(np1)',read)
        self.assertIn('vector(ep0);vector(ep1)',read)
        self.assertIn('node_positions={np0,np1}',read)
        self.assertIn('endpoint_node_position_match=near(np0,ep0,.001) and near(np1,ep1,.001)',read)
        self.assertNotIn('endpoint_node_mismatch',read)
        fresh=source[source.index('local function assert_fresh'):source.index('local function in_region')]
        self.assertIn('current.node0==original.node0 and current.node1==original.node1',fresh)
        self.assertIn('near(current.p0,original.p0,.001)',fresh)
        self.assertIn('if original.node_positions then',fresh)
        self.assertIn('stale_attachment_node_position',fresh)

    def test_native_mixed_endpoint_retains_exact_incidence_and_rejects_shared_interior(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        block=source[source.index('function M.remove_branch'):source.index('function M.verify_crossover')]
        self.assertIn('assert(#all>=1 and #all<=16,"removal_endpoint_degree_unsupported")',block)
        self.assertIn('assert(selected_count==1,"removal_endpoint_chain_ambiguous")',block)
        self.assertIn('retained_nodes[node]=remaining',block)
        self.assertIn('snapshot=edge(id)',block)
        self.assertIn('assert(#all==#remaining and not(owner and owner>0),"retained_chain_incidence_unverified")',block)
        self.assertIn('assert(wanted[id],"retained_chain_incidence_unverified")',block)
        self.assertIn('incident_edges=retained_nodes[r.node]',block)
        self.assertIn('if #chosen==2 then assert(#all==2,"removal_node_not_exclusive")',block)
        self.assertLess(block.index('removal_node_not_exclusive'),block.index('local proposal='))
        self.assertLess(block.index('retained_chain_incidence_unverified'),block.index('s.mutationPending=nil;return {game_constructed=true,exact_chain=true'))
        # Legacy endpoint policies remain separate and unchanged.
        self.assertIn('removal_endpoint_not_two_edge_attachment',block)
        self.assertIn('#all==(p.free_ends==true and 1 or 2)',block)

    def test_named_chain_is_freshly_observed_before_exact_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            c=LiveClient(Path(d)/'mod',Path(d)/'log',Path(d)/'evidence','current',.02)
            rows=[{'id':2,'node0':3,'node1':2},{'id':1,'node0':1,'node1':2}]
            answer={'status':'ok','result':{'removed_edges':[1,2]}}
            with patch.object(c,'request',side_effect=[{'status':'ok','result':{'edges':rows}},answer]) as calls:
                self.assertEqual(c.remove_exact_chain([1,2]),answer)
            self.assertEqual(calls.call_args_list[0].args,('inspect',{'edge_ids':[1,2]}))
            self.assertEqual(calls.call_args_list[1].args,('remove_branch',{'authorised':True,'exact_chain':True,'edges':[rows[1],rows[0]]}))
            self.assertTrue(is_mutation('remove_branch',calls.call_args_list[1].args[1]))

    def test_invalid_or_missing_identity_stops_before_removal(self):
        with tempfile.TemporaryDirectory() as d:
            c=LiveClient(Path(d)/'mod',Path(d)/'log',Path(d)/'evidence','current',.02)
            for ids in ([],[1,1],[True],[-1],list(range(1,18))):
                with patch.object(c,'request') as call,self.assertRaises(ValueError):c.remove_exact_chain(ids)
                call.assert_not_called()
            for response in ({'status':'error','result':{}},{'status':'ok','result':{'edges':[{'id':3}]}}):
                with patch.object(c,'request',return_value=response) as call,self.assertRaises(LiveError):c.remove_exact_chain([1])
                self.assertEqual(call.call_count,1)

    def test_native_chain_mode_guards_and_unknown_outcome_are_preserved(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        block=source[source.index('function M.remove_branch'):source.index('function M.verify_crossover')]
        for guard in ('conflicting_chain_removal_modes','removal_chain_branched_or_disconnected','removal_chain_not_open','construction_owned_removal_node','unsupported_removal_edge','removal_endpoint_degree_unsupported','retained_chain_attachment_unverified','exact_chain_node_removal_unverified','mutation_unverified'):
            self.assertIn(guard,block)
        self.assertIn('assert_fresh(r.snapshot)',block)
        self.assertIn('assert(not s.mutationPending,"unreconciled_mutation")',block)
        self.assertLess(block.index('retained_chain_attachment_unverified'),block.index('exact_chain=true,removed_edges'))

class CrossoverCompensationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
        self.client=LiveClient(root/'mod',root/'log',root/'evidence','current',.02);self.client.log.write_text('')
        c={'p0':[0,0,0],'p1':[20,2,0],'t0':[20,0,0],'t1':[20,0,0]}
        self.edges=[{'id':i,'node0':i*2,'node1':i*2+1,**c} for i in range(1,6)]
        self.pending={'version':1,'session':'current','sequence':1,'request_id':'failed','operation':'crossover','params':{'execute':True,'radius':70},'publication':{'state':'published'},'log_offset':0}
        self.response={'version':1,'session':'current','request_id':'failed','operation':'crossover','status':'mutation_unverified','result':{'game_constructed':True,'fit':{'pieces':1,'controls':[c]},'returned_edges':[1,2,3,4,5]}}
        self.client.journal.write_text(json.dumps({'session':'current','next_sequence':2,'pending':self.pending}))
        self.response_path=self.client.evidence/'failed.response.json';self.response_path.write_text(json.dumps(self.response));self.original=self.response_path.read_bytes()
        (self.client.evidence/'failed.request.json').write_text(json.dumps({k:self.pending[k] for k in ('version','session','sequence','request_id','operation','params')}))
        slot=self.client._slot(self.pending);slot.parent.mkdir(parents=True);slot.write_bytes(self.client._request_body(self.pending))
        self.good={'session':'current','request_id':'removal','operation':'remove_branch','status':'ok','result':{'game_constructed':True,'removed_edges':[5],'compensated_request':'failed','remaining_through_verified':True,'remaining_endpoints':[{},{}]}}

    def compensate(self):return self.client.compensate_crossover(connector_ids=[5],reason='P47 targeted correction',authority='Astra')

    def test_verified_compensation_preserves_old_failure_and_never_accepts_it(self):
        with patch.object(self.client,'request',side_effect=[{'status':'ok','request_id':'fresh','result':{'edges':self.edges}},self.good]) as calls:
            r=self.compensate()
        self.assertEqual([c.args[0] for c in calls.call_args_list],['inspect','remove_branch'])
        self.assertFalse(r['result']['original_build_accepted']);self.assertEqual(r['result']['original_pending'],self.pending)
        self.assertEqual(self.response_path.read_bytes(),self.original);self.assertNotIn('pending',json.loads(self.client.journal.read_text()))

    def test_wrong_receipt_changed_geometry_or_unknown_removal_never_clears(self):
        for defect in ('foreign','changed','unknown','stale'):
            with self.subTest(defect=defect):
                self.client.journal.write_text(json.dumps({'session':'current','next_sequence':2,'pending':self.pending}))
                intent=self.client.evidence/'failed.compensation_intent.json'
                if intent.exists():intent.unlink()
                rows=json.loads(json.dumps(self.edges));answer=json.loads(json.dumps(self.good))
                if defect=='foreign':self.response['result']['returned_edges']=[1,2,3,4,6];self.response_path.write_text(json.dumps(self.response))
                else:self.response['result']['returned_edges']=[1,2,3,4,5];self.response_path.write_text(json.dumps(self.response))
                if defect=='changed':rows[-1]['p1'][0]+=1
                if defect=='unknown':answer['status']='mutation_unverified';answer['result']['game_constructed']='unknown'
                if defect=='stale':answer['session']='other'
                with patch.object(self.client,'request',side_effect=[{'status':'ok','request_id':'fresh','result':{'edges':rows}},answer]),self.assertRaises((LiveError,ValueError)):
                    self.compensate()
                self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)

    def test_only_durable_exact_corrective_payload_can_cross_mutation_guard(self):
        p={'authorised':True,'edges':[self.edges[-1]],'compensation':{'original_request':'failed'}}
        with self.assertRaises(LiveError):self.client.request('remove_branch',p)
        intent={'original_pending':self.pending,'removal_params':p};(self.client.evidence/'failed.compensation_intent.json').write_text(json.dumps(intent))
        with self.assertRaises(LiveError):self.client.request('remove_branch',p|{'edges':[self.edges[0]]})
        with self.assertRaises(LiveError):self.client.request('build',{'authorised':True})
        def reply(state,body):
            req=state['pending'];self.client._slot(req).write_bytes(body)
            self.client.log.write_text(MARKER+json.dumps({'version':1,'session':'current','operation':'remove_branch','request_id':req['request_id'],'status':'mutation_unverified','result':{'game_constructed':'unknown'}})+'\n')
        with patch.object(self.client,'_publish',side_effect=reply):self.client.request('remove_branch',p,request_id='unknown_remove')
        pending=json.loads(self.client.journal.read_text())['pending'];self.assertEqual(pending['request_id'],'unknown_remove');self.assertEqual(pending['unresolved_mutation'],self.pending)

    def test_native_lowering_and_compensation_keep_fixed_bounds(self):
        source=(Path(__file__).resolve().parents[1]/'implementation/n01_probe/prepared_mod/content/scripts/pif_native.lua').read_text()
        block=source[source.index('local function repartition_two_piece_level'):source.index('function M.scissors_candidate')]
        for guard in ('for j=0,200','for j=0,1000','maxerr+report.sampled_XY_error<=.1','v0>0 and v1>0','p.radius==q.radius','p.fit_radius==(q.fit_radius or q.radius*1.25)','comp.removal_request==p.compensation_request','geometry_constraints={all_path=true'):
            self.assertIn(guard,block)
        self.assertIn('math.min(minimum,(geometry_bounds(cg,f.region,f.min_radius,f.max_grade,1000)))',block)
        remove=source[source.index('function M.remove_branch'):source.index('function M.verify_crossover')]
        self.assertIn('through_edge_removal_forbidden',remove);self.assertIn('unrelated_mutation_pending',remove)

class CrossoverAcceptanceRevisionTests(unittest.TestCase):
    """Native verifier stub models P44's measured 74.207 radius; no Lua execution."""
    def setUp(self):
        from types import SimpleNamespace
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.client=SimpleNamespace(journal=root/'journal.json',evidence=root,session='current')
        self.pending={'operation':'crossover','request_id':'original','params':{'execute':True,'radius':150,'source':{'edge_id':11},'target':{'edge_id':12},'vertical':{'max_grade':1e-6}}}
        self.client.journal.write_text(json.dumps({'session':'current','pending':self.pending}))
        self.original={'session':'current','operation':'crossover','request_id':'original','status':'mutation_unverified',
            'result':{'game_constructed':True,'returned_edges':[1,2,3,4,5],'fit':{'pieces':1,'controls':[{}]}}}
        self.path=root/'original.response.json';self.path.write_text(json.dumps(self.original));self.original_bytes=self.path.read_bytes()
        self.revision={'original_request':'original','radius':70,'reason':'P45 explicit compact throat criterion','authority':'Astra design decision after direct human clarification'}

    def native(self,op,p):
        self.assertEqual(op,'verify_crossover');self.assertFalse(p['execute']);self.assertEqual(p['edge_ids'],[1,2,3,4,5])
        self.assertEqual(p['source'],self.pending['params']['source']);self.assertEqual(p['vertical'],self.pending['params']['vertical'])
        result={'error':'realised_sampled_radius_below_limit:74.207276734492<150'}
        ok=p['radius']<=74.207276734492
        if ok:result={'reconciled_current_state':True,'readback':{'connected':True,'requested_min_radius':p['radius'],'engineering_checks_verified':True},
            'crossover_after':{'requested_route_verified':True},'placements':[{'original_removed':True,'subdivision_sampled_verified':True}]*2,'through_after':[{'requested_route_verified':True}]*2}
        return {'session':'current','operation':op,'request_id':'fresh','status':'ok' if ok else 'error','result':result}

    def test_default_150_still_rejects_and_preserves_pending(self):
        self.client.request=unittest.mock.Mock(side_effect=self.native)
        with self.assertRaises(LiveError):reconcile_constructed_crossover(self.client)
        self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)
        self.assertEqual(self.path.read_bytes(),self.original_bytes)

    def test_explicit_70_uses_fresh_receipt_and_records_both_criteria(self):
        self.client.request=unittest.mock.Mock(side_effect=self.native)
        r=reconcile_constructed_crossover(self.client,acceptance_revision=self.revision)
        self.client.request.assert_called_once();record=r['result'];self.assertFalse(record['automatic_replay'])
        self.assertEqual(record['original_pending'],self.pending)
        self.assertEqual(record['acceptance_revision']['original_criteria'],{'radius':150})
        self.assertEqual(record['acceptance_revision']['revised_criteria'],{'radius':70})
        self.assertNotIn('pending',json.loads(self.client.journal.read_text()))
        self.assertEqual(self.path.read_bytes(),self.original_bytes)

    def test_malformed_unrelated_and_wrong_request_revisions_do_not_send(self):
        bad=[self.revision|{'radius':v} for v in (False,0,-1,float('nan'),float('inf'),'70')]
        bad += [self.revision|{'original_request':'other'},self.revision|{'reason':''},self.revision|{'authority':None},self.revision|{'end_xy':[1,2]}]
        self.client.request=unittest.mock.Mock()
        for revision in bad:
            with self.subTest(revision=revision),self.assertRaises(ValueError):reconcile_constructed_crossover(self.client,acceptance_revision=revision)
        self.client.request.assert_not_called();self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)

    def test_stale_or_missing_engineering_observation_never_clears(self):
        for field,value in (('session','other'),('operation','inspect'),('missing_engineering',True)):
            answer=self.native('verify_crossover',self.pending['params']|{'execute':False,'radius':70,'edge_ids':[1,2,3,4,5]})
            if field=='missing_engineering':answer['result']['readback'].pop('engineering_checks_verified')
            else:answer[field]=value
            self.client.request=unittest.mock.Mock(return_value=answer)
            with self.assertRaises(LiveError):reconcile_constructed_crossover(self.client,acceptance_revision=self.revision)
            self.assertEqual(json.loads(self.client.journal.read_text())['pending'],self.pending)

if __name__ == '__main__':
    unittest.main()
