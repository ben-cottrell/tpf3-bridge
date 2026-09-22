"""Connection input checks without game access or temporary directories."""
import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from bridge_connection import UnsupportedConnection, load_connection, validate_connection


EXAMPLE = Path(__file__).resolve().parents[1] / 'connection_example.json'


class ConnectionInputTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EXAMPLE.read_text(encoding='utf-8'))

    def reject(self, group, key, value, exception=ValueError):
        record = copy.deepcopy(self.record)
        record[group][key] = value
        before = copy.deepcopy(record)
        with self.assertRaises(exception):
            validate_connection(record)
        self.assertEqual(record, before)

    def test_example_and_nonmutation(self):
        before = copy.deepcopy(self.record)
        self.assertEqual(validate_connection(self.record), before)
        self.assertEqual(self.record, before)
        self.assertEqual(load_connection(EXAMPLE), before)

    def test_fields_required_and_unknown_at_every_object(self):
        for group in (None, 'coordinate_frame', 'start', 'end', 'region', 'constraints', 'provenance'):
            original = self.record if group is None else self.record[group]
            for key in (*original, 'unknown'):
                with self.subTest(group=group, key=key):
                    record = copy.deepcopy(self.record)
                    target = record if group is None else record[group]
                    if key == 'unknown':
                        target[key] = 0
                    else:
                        del target[key]
                    with self.assertRaises(ValueError):
                        validate_connection(record)
            for value in (None, [], 'object', 1, True):
                record = copy.deepcopy(self.record)
                if group is None:
                    record = value
                else:
                    record[group] = value
                with self.assertRaises(ValueError):
                    validate_connection(record)

    def test_numeric_types_and_finiteness(self):
        for value in (True, False, None, '1', float('inf'), -float('inf'), float('nan'), 10**400):
            for group, key in (('constraints', 'min_radius_m'), ('constraints', 'max_length_m'),
                               ('constraints', 'cant_mm'), ('start', 'grade')):
                self.reject(group, key, value)
            for group, key in (('start', 'position_m'), ('end', 'forward_unit'), ('region', 'min_m')):
                self.reject(group, key, [value, 0, 0])

    def test_limits(self):
        for key, maximum in (('max_candidates', 400), ('curvature_depth', 10)):
            for value in (-1, maximum + 1, True, False, 1.0, '1', None):
                self.reject('constraints', key, value)
            for value in (0, maximum):
                self.record['constraints'][key] = value
                self.assertEqual(validate_connection(self.record), self.record)
        for key in ('min_radius_m', 'max_length_m'):
            for value in (0, -1):
                self.reject('constraints', key, value)

    def test_vectors_and_regions(self):
        for value in (None, {}, [0, 0], [0, 0, 0, 0], (0, 0, 0), [1e9 + 1, 0, 0]):
            self.reject('start', 'position_m', value)
        for value in ([0, 0, 0], [2, 0, 0], [0.999, 0, 0]):
            self.reject('end', 'forward_unit', value)
        for axis in range(3):
            bounds = self.record['region']['max_m'][:]
            bounds[axis] = self.record['region']['min_m'][axis] - 1
            self.reject('region', 'max_m', bounds)

    def test_vertical_and_cant_unsupported(self):
        for group, key, value in (('end', 'position_m', [500, 0, 1e-12]),
                                  ('start', 'forward_unit', [0, 0, 1]),
                                  ('end', 'grade', 1e-12), ('constraints', 'cant_mm', -1)):
            self.reject(group, key, value, UnsupportedConnection)

    def test_translated_rotated_level_and_outside_region_preserved(self):
        for port in ('start', 'end'):
            self.record[port]['position_m'][2] = 30
            self.record[port]['forward_unit'] = [math.sqrt(0.5), math.sqrt(0.5), 0]
        self.record['end']['position_m'][0] = 3000
        self.record['provenance']['source_refs'] = ['evidence/uk_parameters.json']
        before = copy.deepcopy(self.record)
        self.assertEqual(validate_connection(self.record), before)
        self.assertEqual(self.record, before)

    def test_frame_identifiers_roles_and_provenance(self):
        for key, value in (('length_unit', 'ft'), ('up_axis', 'y'), ('handedness', 'left'),
                           ('transform_ref', ''), ('transform_probe_ref', {})):
            self.reject('coordinate_frame', key, value)
        for key in ('port_id', 'native_entity_ref', 'native_port_ref'):
            for value in ('bad id', '', 'a' * 97, True):
                self.reject('start', key, value)
        self.reject('end', 'role', 'unknown')
        for key in self.record['provenance']:
            for value in ('text', {}, [None], [''], ['  '], [True]):
                self.reject('provenance', key, value)
        for key in ('schema_version', 'kind'):
            record = copy.deepcopy(self.record)
            record[key] = 'unknown'
            with self.assertRaises(ValueError):
                validate_connection(record)

    def test_file_entry_rejects_malformed_duplicate_and_nonfinite_json(self):
        valid = EXAMPLE.read_text(encoding='utf-8')
        cases = ['{', valid + '{}', 'null', '[]',
                 valid.replace('"grade": 0', '"grade": 0, "grade": 0'),
                 valid.replace('"schema_version":', '"kind": "plain_track_connection", "schema_version":')]
        cases.extend(valid.replace('"cant_mm": 0', '"cant_mm": ' + v)
                     for v in ('NaN', 'Infinity', '-Infinity', '1e999'))
        for text in cases:
            with self.subTest(text=text[:40]), patch.object(Path, 'read_text', return_value=text):
                with self.assertRaises(ValueError):
                    load_connection('input.json')


if __name__ == '__main__':
    unittest.main()
