import copy,unittest
from railgeom.network import Network,RailPath
from railgeom.patterns import Assembly,GeometryProfile
from railgeom.curves import line
from railcompact.crossings import validate_crossings
from railcompact.compiler import compile_assembly
from railgeom.compiler import compile_assembly as legacy_compile
from compact_support import model

def diamond():
    n=Network('test_diamond')
    for k,p in [('AW',(-10.,0.)),('AE',(10.,0.)),('BW',(0.,-10.)),('BE',(0.,10.))]:n.port(k,p)
    n.edge('A','AW','AE',line((-10.,0.),(10.,0.)));n.edge('B','BW','BE',line((0.,-10.),(0.,10.)))
    n.metadata['diamond_crossings']=[{'id':'X','edges':['A','B'],'position_m':[0.,0.],
       'kind':'synthetic_fixed_crossing_two_nonconnecting_routes','source_kind':'authored_synthetic','hardware_and_flange_clearance':'unassessed'}]
    routes={k:n.one_path(u,v,k) for k,u,v in [('A','AW','AE'),('B','BW','BE')]}
    return Assembly(n,routes,{},GeometryProfile())

class CrossingTests(unittest.TestCase):
    def test_no_turning_connection(self):
        a=diamond();self.assertEqual(a.network.enumerate_paths('AW','BE'),[])
    def test_both_routes_claim_diamond(self):
        c=compile_assembly(diamond())
        for r in c.routes.values():self.assertIn('diamond:X',{q.resource for q in r.requirements})
    def test_scissors_recovery_routes_claim_diamond(self):
        c=model()[1]
        for rid in ('A:B1:in','A:B1:out','B:A4:in','B:A4:out'):self.assertIn('diamond:INNER_DIAMOND',{q.resource for q in c.routes[rid].requirements})
    def test_normal_routes_do_not_claim_diamond(self):
        c=model()[1]
        for g in ('A','B'):
            for i in range(1,5):
                for d in ('in','out'):self.assertNotIn('diamond:INNER_DIAMOND',{q.resource for q in c.routes[f'{g}:{g}{i}:{d}'].requirements})
    def test_missing_declaration_rejects_crossing(self):
        a=diamond();a.network.metadata['diamond_crossings']=[]
        with self.assertRaisesRegex(ValueError,'centreline_contact'):compile_assembly(a)
    def test_old_compiler_still_rejects_crossing(self):
        with self.assertRaisesRegex(ValueError,'centreline_contact'):legacy_compile(diamond())
    def test_wrong_crossing_position_rejected(self):
        a=diamond();a.network.metadata['diamond_crossings'][0]['position_m']=[1.,0.]
        with self.assertRaisesRegex(ValueError,'location'):compile_assembly(a)
    def test_same_edge_cannot_form_crossing(self):
        a=diamond();a.network.metadata['diamond_crossings'][0]['edges']=['A','A']
        with self.assertRaises(ValueError):validate_crossings(a.network)
    def test_unknown_edge_rejected(self):
        a=diamond();a.network.metadata['diamond_crossings'][0]['edges']=['A','missing']
        with self.assertRaises(ValueError):validate_crossings(a.network)
    def test_duplicate_crossing_rejected(self):
        a=diamond();a.network.metadata['diamond_crossings']*=2
        with self.assertRaises(ValueError):validate_crossings(a.network)
    def test_false_authenticity_rejected(self):
        for k,v in [('source_kind','authentic_uk'),('kind','double_slip'),('hardware_and_flange_clearance','pass')]:
            a=diamond();a.network.metadata['diamond_crossings'][0][k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate_crossings(a.network)
    def test_nonfinite_or_boolean_location_rejected(self):
        for x in (True,float('nan'),float('inf')):
            a=diamond();a.network.metadata['diamond_crossings'][0]['position_m']=[x,0.]
            with self.subTest(x=x),self.assertRaises(ValueError):validate_crossings(a.network)
    def test_parallel_false_declaration_rejected(self):
        a=diamond();n=a.network;n.ports.clear();n.edges.clear()
        for k,p in [('AW',(-10.,0.)),('AE',(10.,0.)),('BW',(-10.,10.)),('BE',(10.,10.))]:n.port(k,p)
        n.edge('A','AW','AE',line((-10.,0.),(10.,0.)));n.edge('B','BW','BE',line((-10.,10.),(10.,10.)))
        with self.assertRaisesRegex(ValueError,'parallel'):validate_crossings(n)
    def test_crossing_contract_not_extra_commands(self):
        a=diamond();a.network.metadata['diamond_crossings'][0]['execute']='ignored?'
        with self.assertRaises(ValueError):validate_crossings(a.network)
    def test_provenance_records_no_connectivity(self):
        c=compile_assembly(diamond());r=c.provenance['resources']['diamond:X'];self.assertFalse(r['rail_connection_created'])
    def test_adding_unrelated_crossing_does_not_whitelist_other_contacts(self):
        a=diamond();n=a.network;n.port('CW',(-10.,5.));n.port('CE',(10.,5.));n.edge('C','CW','CE',line((-10.,5.),(10.,5.)))
        with self.assertRaisesRegex(ValueError,'centreline_contact'):compile_assembly(a)
