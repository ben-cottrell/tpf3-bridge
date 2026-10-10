"""Explicit pair input checks without temporary directories or game access."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bridge_pair import UnsupportedPair, load_pair, validate_pair
from tools.pair_acceptance import fixture, snapshot


ROOT = Path(__file__).resolve().parents[1]


class PairInputTests(unittest.TestCase):
    def reject(self, record, exception=ValueError):
        before = copy.deepcopy(record)
        with self.assertRaises(exception):
            validate_pair(record)
        self.assertEqual(record, before)

    def test_examples_and_nonmutation(self):
        self.assertEqual(load_pair(ROOT / 'pair_example.json'), fixture())
        authored = json.loads((ROOT / 'pair_snapshot_example.json').read_text(encoding='utf-8'))
        self.assertEqual(authored, snapshot(fixture()))
        for curved in (False, True):
            for opposing in (False, True):
                record = fixture(curved=curved, opposing=opposing)
                before = copy.deepcopy(record)
                self.assertIs(validate_pair(record), record)
                self.assertEqual(record, before)

    def test_required_unknown_and_object_types(self):
        paths = [(), ('coordinate_frame',), ('region',), ('constraints',), ('provenance',)]
        paths += [('ports', i) for i in range(4)]
        paths += [('connections', i) for i in range(2)]
        for path in paths:
            original = fixture()
            for part in path:
                original = original[part]
            for key in [*original, 'unknown']:
                record = fixture()
                target = record
                for part in path:
                    target = target[part]
                if key == 'unknown':
                    target[key] = True
                else:
                    del target[key]
                self.reject(record)
            for value in (None, [], 'object', 1, True):
                record = fixture()
                if path:
                    target = record
                    for part in path[:-1]:
                        target = target[part]
                    target[path[-1]] = value
                else:
                    record = value
                self.reject(record)

    def test_cardinality_and_explicit_unique_pairing(self):
        for key in ('ports', 'connections'):
            for value in (None, {}, 'list', [], fixture()[key][:-1], fixture()[key] * 2):
                record = fixture()
                record[key] = value
                self.reject(record)
        for key, value in [('track_id', 'a'), ('start_port', 'a0'),
                           ('end_port', 'b0'), ('end_port', 'missing')]:
            record = fixture()
            record['connections'][1][key] = value
            self.reject(record)
        record = fixture()
        record['ports'][3]['port_id'] = 'a0'
        self.reject(record)
        for key in ('track_id', 'start_port', 'end_port'):
            for value in (None, [], True, '', 'bad id', 'a' * 97):
                record = fixture()
                record['connections'][0][key] = value
                self.reject(record)
        record = fixture(opposing=True)
        record['ports'].reverse()
        record['connections'].reverse()
        self.assertEqual(validate_pair(record), record)

    def test_numeric_limits(self):
        for key in fixture()['constraints']:
            for value in (True, None, '1', float('inf'), float('nan'), 10**400):
                record = fixture()
                record['constraints'][key] = value
                self.reject(record)
        positive = ('min_radius_m', 'max_length_m', 'spacing_m', 'min_separation_m',
                    'lowering_tolerance_m', 'realised_tolerance_m')
        for key in positive:
            for value in (0, -1):
                record = fixture()
                record['constraints'][key] = value
                self.reject(record)
        for key, maximum in [('max_candidates', 400), ('curvature_depth', 10)]:
            for value in (-1, maximum + 1, 1.5):
                record = fixture()
                record['constraints'][key] = value
                self.reject(record)
            for value in (0, maximum):
                record = fixture()
                record['constraints'][key] = value
                self.assertEqual(validate_pair(record), record)

    def test_all_ports_use_shared_validation(self):
        for index in range(4):
            for key, value in [('position_m', [True, 0, 0]), ('position_m', [1e9 + 1, 0, 0]),
                               ('forward_unit', [0, 0, 0]), ('forward_unit', [2, 0, 0]),
                               ('grade', None), ('role', 'unknown'), ('port_id', []),
                               ('native_entity_ref', 'bad id'), ('native_port_ref', True)]:
                record = fixture()
                record['ports'][index][key] = value
                self.reject(record)

    def test_unsupported_level_frame_and_cant(self):
        for index in range(4):
            for key, value in [('position_m', [500, 0, 1e-12]),
                               ('forward_unit', [0, 0, 1]), ('grade', 1e-12)]:
                record = fixture()
                record['ports'][index][key] = value
                self.reject(record, UnsupportedPair)
        record = fixture()
        for port in record['ports'][2:]:
            port['position_m'][2] = 1
        self.reject(record, UnsupportedPair)
        for group, key, value in [('constraints', 'cant_mm', 1),
                                  ('coordinate_frame', 'length_unit', 'ft'),
                                  ('coordinate_frame', 'up_axis', 'y'),
                                  ('coordinate_frame', 'handedness', 'left')]:
            record = fixture()
            record[group][key] = value
            self.reject(record, UnsupportedPair)

    def test_shared_metadata_validation(self):
        for key in ('schema_version', 'kind'):
            record = fixture()
            record[key] = 'unknown'
            self.reject(record)
        for key in fixture()['provenance']:
            for value in ('text', [None], ['  ']):
                record = fixture()
                record['provenance'][key] = value
                self.reject(record)
        record = fixture()
        record['coordinate_frame']['transform_ref'] = None
        self.reject(record)
        record = fixture()
        record['region']['min_m'][0] = 3000
        self.reject(record)

    def test_geometry_is_deferred_and_metadata_preserved(self):
        record = fixture()
        record['ports'][3]['position_m'] = [-3000, 50, 30]
        record['ports'][3]['forward_unit'] = [-1, 0, 0]
        for port in record['ports']:
            port['position_m'][2] = 30
        record['provenance']['source_refs'] = ['evidence/uk_parameters.json']
        before = copy.deepcopy(record)
        self.assertEqual(validate_pair(record), before)
        self.assertEqual(record, before)

    def test_strict_json(self):
        valid = json.dumps(fixture())
        cases = ['{', valid + '{}', 'null', '[]',
                 valid.replace('"grade": 0', '"grade": 0, "grade": 0'),
                 valid.replace('"kind":', '"kind": "duplicate", "kind":')]
        cases += [valid.replace('"cant_mm": 0', '"cant_mm": ' + value)
                  for value in ('NaN', 'Infinity', '-Infinity', '1e999')]
        for text in cases:
            with patch.object(Path, 'read_text', return_value=text):
                with self.assertRaises(ValueError):
                    load_pair('input.json')


if __name__ == '__main__':
    unittest.main()
