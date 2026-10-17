import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from railclear.catalogue import *
from railclear.profiles import resolve_vehicle
from railclear.model import digest

E=Path(__file__).resolve().parents[2]/'evidence'

class CatalogueTests(unittest.TestCase):
    def setUp(self):self.r=read_json(E/'component_import_synthetic.json')
    def test_normalizes_mm(self):
        x=import_component(self.r);self.assertEqual(x.normalized_geometry['gauge'],1.435)
        self.assertEqual(x.network.ports['N'].position,(40.,0.))
    def test_legal_routes(self):
        n=import_component(self.r).network;self.assertEqual(len(n.enumerate_paths('T','N')),1);self.assertEqual(len(n.enumerate_paths('T','R')),1);self.assertEqual(n.enumerate_paths('N','R'),[])
    def test_synthetic_not_authentic(self):
        r=import_component(self.r).report;self.assertEqual(r['status'],'accepted_for_synthetic_tests');self.assertFalse(r['speed_usable_for_UK_design']);self.assertFalse(r['construction_authorised'])
    def test_metadata_only(self):
        r=import_component(read_json(E/'component_import_pending.json'));self.assertIsNone(r.network);self.assertEqual(r.report['status'],'reference_only_missing_geometry')
    def test_unknown_top_level(self):
        self.r['verified']=True
        with self.assertRaises(ValueError):import_component(self.r)
    def test_self_asserted_review(self):
        self.r['source']['reviewed']=True
        with self.assertRaises(ValueError):import_component(self.r)
    def test_origin_mismatch(self):
        self.r['origin_kind']='external_reference'
        with self.assertRaises(ValueError):import_component(self.r)
    def external(self):
        self.r['origin_kind']='external_reference';self.r['source'].update(geometry_evidence='drawing_transcription',reuse_status='permitted');return self.r
    def test_external_not_trusted_by_default(self):self.assertEqual(import_component(self.external()).report['status'],'quarantined_pending_review')
    def test_caller_review_binds_exact_record(self):
        record=self.external();allow=frozenset({digest(record)});r=import_component(record,allow)
        self.assertEqual(r.report['status'],'reviewed_geometry_import');self.assertFalse(r.report['construction_authorised'])
        record['display_name']='changed';self.assertEqual(import_component(record,allow).report['status'],'quarantined_pending_review')
    def test_even_review_does_not_invent_speed(self):
        r=self.external();self.assertFalse(import_component(r,frozenset({digest(r)})).report['speed_usable_for_UK_design'])
    def test_source_speed_admission_separate(self):
        r=self.external();r['limits'].update(diverging_speed_mps=6.,speed_evidence='source_backed_claim')
        x=import_component(r,frozenset({digest(r)}));self.assertTrue(x.report['source_speed_record_reviewed']);self.assertFalse(x.report['speed_usable_for_UK_design']);self.assertFalse(x.report['construction_authorised'])
    def test_external_not_placed_as_synthetic(self):
        r=self.external();x=import_component(r,frozenset({digest(r)}))
        with self.assertRaises(ValueError):place_synthetic(x)
    def test_record_not_aliased(self):
        x=import_component(self.r);self.r['display_name']='mutation';self.assertNotEqual(x.record['display_name'],'mutation')
    def test_display_name_not_geometry(self):
        a=import_component(self.r);self.r['display_name']='renamed';b=import_component(self.r)
        self.assertEqual(a.geometry_hash,b.geometry_hash);self.assertNotEqual(a.record_hash,b.record_hash)
    def test_m_and_mm_same_geometry_hash(self):
        a=import_component(self.r);g=self.r['geometry'];g['units']='m';g['gauge']*=.001
        for p in g['ports']:p['xy']=[x*.001 for x in p['xy']]
        for r in g['routes']:r['bezier_controls']=[[x*.001 for x in p] for p in r['bezier_controls']]
        self.assertEqual(a.geometry_hash,import_component(self.r).geometry_hash)
    def test_placement_rotation_reflection(self):
        n=place_synthetic(import_component(self.r),10,20,math.pi/2,True)
        self.assertAlmostEqual(n.ports['R'].position[0],11.5);self.assertAlmostEqual(n.ports['R'].position[1],60.)
    def test_invalid_transform(self):
        with self.assertRaises(ValueError):place_synthetic(import_component(self.r),mirror=1)
    def test_bad_units(self):
        self.r['geometry']['units']='feet'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_gauge_unit_error(self):
        self.r['geometry']['units']='m'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_unknown_3d(self):
        self.r['geometry']['coordinate_frame']='3D_canted'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_duplicate_ports(self):
        self.r['geometry']['ports'][2]=copy.deepcopy(self.r['geometry']['ports'][1])
        with self.assertRaises(ValueError):import_component(self.r)
    def test_duplicate_routes(self):
        self.r['geometry']['routes'][1]=copy.deepcopy(self.r['geometry']['routes'][0])
        with self.assertRaises(ValueError):import_component(self.r)
    def test_illegal_branch_route(self):
        self.r['geometry']['routes'][1]['from']='N'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_port_curve_disagreement(self):
        self.r['geometry']['ports'][2]['xy'][1]=2000
        with self.assertRaises(ValueError):import_component(self.r)
    def test_toe_tangent_disagreement(self):
        self.r['geometry']['routes'][1]['bezier_controls'][1][1]=100
        with self.assertRaises(ValueError):import_component(self.r)
    def test_missing_speed_value(self):
        self.r['limits']['speed_evidence']='source_backed_claim'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_nan_value(self):
        self.r['limits']['diverging_speed_mps']=math.nan
        with self.assertRaises(ValueError):import_component(self.r)
    def test_unknown_geometry_field(self):
        self.r['geometry']['crossing_ratio_implies_speed']=12
        with self.assertRaises(ValueError):import_component(self.r)
    def test_identifier_path_injection(self):
        self.r['component_id']='../../new_file'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_unknown_schema(self):
        self.r['schema_version']='0.1'
        with self.assertRaises(ValueError):import_component(self.r)
    def test_duplicate_json_field(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):read_json(p)
    def test_json_nan_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError):read_json(p)
    def test_size_budget(self):
        with self.assertRaises(ValueError):read_json(E/'component_import_synthetic.json',max_bytes=10)

class VehicleTests(unittest.TestCase):
    def setUp(self):
        self.r=read_json(E/'vehicle_reference.json');self.a={'use_nominal_length_as_rectangular_body':True,'bogie_centres_m':14.,'lateral_allowance_m':0.,'vertical_scope':'level_zero_cant_plan_only'}
    def test_missing_bogie_not_defaulted(self):self.assertIsNone(resolve_vehicle(self.r)['body'])
    def test_assumptions_required(self):
        x=resolve_vehicle(self.r,self.a);self.assertEqual(x['body'].bogie_centres_m,14);self.assertFalse(x['strict_profile_admitted'])
    def test_nominal_not_unit_length(self):
        x=resolve_vehicle(self.r)['published'];self.assertNotEqual(8*x['nominal_vehicle_length_m'],x['unit_8car_length_m']);self.assertEqual(x['unit_12car_length_m'],242.6)
    def test_source_width(self):self.assertEqual(resolve_vehicle(self.r,self.a)['body'].width_m,2.8)
    def test_origin_not_erased(self):self.assertEqual(resolve_vehicle(self.r,self.a)['body'].fidelity,'reference_informed_assumptions')
    def test_body_length_interpretation_explicit(self):
        self.a['use_nominal_length_as_rectangular_body']=False
        with self.assertRaises(ValueError):resolve_vehicle(self.r,self.a)
    def test_cant_not_ignored(self):
        self.a['vertical_scope']='canted'
        with self.assertRaises(ValueError):resolve_vehicle(self.r,self.a)
    def test_missing_field(self):
        del self.a['bogie_centres_m']
        with self.assertRaises(ValueError):resolve_vehicle(self.r,self.a)
    def test_missing_source_locator(self):
        self.r['published']['width_m']['locator']=''
        with self.assertRaises(ValueError):resolve_vehicle(self.r)
    def test_unknown_vehicle_fields(self):
        self.r['certified']=True
        with self.assertRaises(ValueError):resolve_vehicle(self.r)
