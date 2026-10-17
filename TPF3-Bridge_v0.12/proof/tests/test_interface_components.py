import copy
import unittest
from railinterface.components import *
from railclear.catalogue import read_json
from railinterface.reference import EVIDENCE

class ComponentEvidenceTests(unittest.TestCase):
    def setUp(self):self.records=read_json(EVIDENCE/'component_field_references.json')['records']
    def test_source_local_switch_dimensions_retained(self):
        r=resolve_component_reference(self.records[0]);q=r['quantities']
        self.assertEqual(q['reported_switch_radius_m'],1650);self.assertEqual(q['reported_crossing_ratio_denominator'],28)
    def test_local_speed_not_general_rating(self):
        r=resolve_component_reference(self.records[0]);self.assertFalse(r['speed_usable_as_general_rating'])
        self.assertEqual(r['quantities']['reported_trailing_diverging_line_speed_kmh'],105)
    def test_source_geometry_remains_missing(self):
        for r in load_component_references():
            self.assertEqual(r['status'],'reference_only_missing_geometry');self.assertIsNone(r['geometry']);self.assertFalse(r['full_turnout_geometry_imported'])
    def test_stub_beam_not_turnout_length(self):
        r=resolve_component_reference(self.records[1])
        self.assertEqual(r['quantities']['movable_stub_beam_length_m'],7.8)
        self.assertEqual(compare_like_quantity(r,'movable_stub_beam_length_m',40,candidate_scope='whole_turnout_length')['status'],'not_comparable')
    def test_crossing_ratio_not_exit_slope(self):
        r=resolve_component_reference(self.records[0])
        self.assertEqual(compare_like_quantity(r,'reported_crossing_ratio_denominator',28,candidate_scope='branch_exit_tangent')['status'],'not_comparable')
    def test_same_quantity_numeric_comparison_does_not_approve(self):
        r=resolve_component_reference(self.records[0]);c=compare_like_quantity(r,'reported_switch_radius_m',1650,candidate_scope='reported_local_switch_radius')
        self.assertEqual(c['difference'],0);self.assertEqual(c['whole_component_compatibility'],'unassessed')
    def test_unknown_quantity_rejected(self):
        r=resolve_component_reference(self.records[0])
        with self.assertRaises(ValueError):compare_like_quantity(r,'turnout_length_m',40,candidate_scope='length')
    def test_self_promoted_geometry_rejected(self):
        for key,value in (('geometry',{}),('eligible_for_station_placement',True),('source_figure_is_dimensional_component_drawing',True)):
            r=copy.deepcopy(self.records[0]);r[key]=value
            with self.assertRaises(ValueError):resolve_component_reference(r)
    def test_unknown_record_fields_rejected(self):
        r=copy.deepcopy(self.records[0]);r['verified']=True
        with self.assertRaises(ValueError):resolve_component_reference(r)
    def test_bad_numeric_values_rejected(self):
        for v in (False,-1,float('nan')):
            r=copy.deepcopy(self.records[0]);r['quantities']['reported_switch_radius_m']=v
            with self.assertRaises(ValueError):resolve_component_reference(r)
    def test_missing_source_locator_rejected(self):
        r=copy.deepcopy(self.records[0]);r['source_locator']=''
        with self.assertRaises(ValueError):resolve_component_reference(r)
    def test_missing_geometry_gaps_rejected(self):
        r=copy.deepcopy(self.records[0]);r['geometry_missing']=[]
        with self.assertRaises(ValueError):resolve_component_reference(r)
    def test_input_mutation_does_not_change_resolved_record(self):
        source=copy.deepcopy(self.records[0]);resolved=resolve_component_reference(source)
        source['quantities']['reported_switch_radius_m']=1
        self.assertEqual(resolved['quantities']['reported_switch_radius_m'],1650)
    def test_record_hash_changes_when_source_scope_changes(self):
        a=resolve_component_reference(self.records[0]);r=copy.deepcopy(self.records[0]);r['source_locator']+=' changed'
        b=resolve_component_reference(r);self.assertNotEqual(a['record_hash'],b['record_hash'])
