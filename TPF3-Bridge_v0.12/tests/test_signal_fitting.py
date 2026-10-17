import copy
import unittest
import bridge_live as live


class Client:
    def __init__(self, accepted=(.25,), outcome='ok', evaluated=True):
        self.calls=[];self.accepted=accepted;self.outcome=outcome;self.evaluated=evaluated
        self.edge={'id':42,'node0':1,'node1':2,'p0':[0,0,0],'p1':[100,0,0],'t0':[100,0,0],'t1':[100,0,0]}
    def request(self,operation,params):
        self.calls.append((operation,copy.deepcopy(params)))
        value={'status':'ok','request_id':str(len(self.calls))}
        if operation=='inspect':return value|{'result':{'edges':[self.edge]}}
        if operation=='operating_control':return value|{'status':self.outcome,'result':{'operating_effects':'unknown' if self.outcome!='ok' else 'verified'}}
        if 'track_ids' in params:return value|{'result':{'tracks':{'records':[{'id':42,'node0':1,'node1':2,'revision':[1,2,3],'objects':[]}]}}}
        p=params['signal_placement']
        return value|{'result':{'signal_placement':{'native_proposal_evaluated':self.evaluated,
            'accepted':any(abs(p['parameter']-u)<1e-8 for u in self.accepted),'seed':{'id':99,'revision':[1,2,3]}}}}


class SignalFitTests(unittest.TestCase):
    def brief(self):return {'edge_id':42,'parameter':.2,'forward':False,'one_way':True,'seed_id':99,'fit_offsets_m':[-2,-5,-10,-20]}
    def test_nominal_success_builds_once_without_geometry_read(self):
        c=Client((.2,));r=live.place_signal(c,self.brief(),execute=True)
        self.assertEqual(r['result']['signal_fit']['selected_offset_m'],0)
        self.assertEqual([x[0] for x in c.calls],['operating_inspect','operating_inspect','operating_control'])
    def test_reject_then_first_accept_and_one_build(self):
        c=Client();b=self.brief();r=live.place_signal(c,b,execute=True)
        previews=[p['signal_placement']['parameter'] for op,p in c.calls if 'signal_placement' in p]
        self.assertEqual(len(previews),3)
        for a,b in zip(previews,[.2,.22,.25]):self.assertAlmostEqual(a,b)
        self.assertEqual(r['result']['signal_fit']['selected_offset_m'],-5)
        self.assertEqual(sum(op=='operating_control' for op,_ in c.calls),1)
        self.assertNotIn('fit_offsets_m',c.calls[-1][1])
    def test_unknown_build_stops_without_more_candidates(self):
        c=Client(outcome='mutation_unverified');r=live.place_signal(c,self.brief(),execute=True)
        self.assertEqual(r['status'],'mutation_unverified')
        self.assertEqual(len(c.calls),6)
    def test_unavailable_preflight_never_builds(self):
        c=Client(evaluated=False)
        with self.assertRaises(live.LiveError):live.place_signal(c,self.brief(),execute=True)
        self.assertEqual(len(c.calls),2)
    def test_invalid_finite_budget_rejected_before_reads(self):
        for offsets in ([float('nan')],[True],[0],[21],[-2,-2],list(range(1,10))):
            c=Client()
            with self.subTest(offsets=offsets),self.assertRaises(ValueError):live.place_signal(c,self.brief()|{'fit_offsets_m':offsets},execute=True)
            self.assertFalse(c.calls)
    def test_same_edge_endpoint_change_stops(self):
        c=Client();c.edge['node0']=9
        with self.assertRaises(live.LiveError):live.place_signal(c,self.brief(),execute=True)
        self.assertEqual(len(c.calls),3)
    def test_empty_valid_window_rejects_without_clipping_or_build(self):
        c=Client();r=live.place_signal(c,self.brief()|{'parameter':.99,'fit_offsets_m':[-2]},execute=True)
        self.assertEqual(r['status'],'error');self.assertEqual(len(c.calls),3)
    def test_read_only_fit_never_submits_command(self):
        c=Client();r=live.place_signal(c,self.brief(),execute=False)
        self.assertTrue(r['result']['signal_placement']['accepted'])
        self.assertFalse(any(op=='operating_control' for op,_ in c.calls))
    def test_replacement_identity_cannot_slide(self):
        c=Client()
        with self.assertRaises(ValueError):live.place_signal(c,self.brief()|{'replace_signal_id':7},execute=True)
        self.assertFalse(c.calls)


if __name__=='__main__':unittest.main()
