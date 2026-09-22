"""Independent connection witnesses supplement continuous kernel bounds."""
import copy
import json
import math
from pathlib import Path
import unittest

from bridge_connection import fit_connection, _connection_region_bound


def fixture():
    value = json.loads((Path(__file__).resolve().parents[1] / 'connection_example.json').read_text())
    value['start']['position_m'] = [0, 0, 0]
    value['end']['position_m'] = [500, 0, 0]
    for key in ('start', 'end'):
        value[key]['forward_unit'] = [1, 0, 0]
    value['region'] = {'min_m': [-2000, -2000, -1], 'max_m': [2000, 2000, 1]}
    value['constraints'].update(min_radius_m=80, max_length_m=2000,
                                max_candidates=100, curvature_depth=6)
    return value


def polynomial(points, t):
    n = len(points)-1
    return tuple(sum(math.comb(n, i)*t**i*(1-t)**(n-i)*p[k]
                     for i, p in enumerate(points)) for k in range(2))


def derivative(points):
    n = len(points)-1
    return [(n*(b[0]-a[0]), n*(b[1]-a[1])) for a, b in zip(points, points[1:])]


class ConnectionGeometryTests(unittest.TestCase):
    def verify(self, record, result):
        self.assertEqual(result['status'], 'connection_ready')
        self.assertEqual(result['search_status'], 'complete')
        self.assertEqual(result['evaluated'], len(result['grid']))
        self.assertLessEqual(result['evaluated'], 100)
        selected = result['candidate_checks'][result['selected_index']]
        self.assertTrue(selected['pass'])
        controls = [c['controls'] for c in result['candidate']['curves']]
        self.assertEqual(controls[0][0], record['start']['position_m'][:2])
        self.assertEqual(controls[-1][-1], record['end']['position_m'][:2])
        self.assertEqual(result['candidate']['elevation_m'], record['start']['position_m'][2])
        for points, t, port in ((controls[0], 0, 'start'), (controls[-1], 1, 'end')):
            d = polynomial(derivative(points), t)
            tangent = [x/math.hypot(*d) for x in d]
            self.assertLess(math.dist(tangent, record[port]['forward_unit'][:2]), 1e-7)
        length = 0
        for piece, points in enumerate(controls):
            d = derivative(points)
            dd = derivative(d) if len(d) > 1 else [(0, 0)]
            speeds = []
            for i in range(401):
                t = i/400
                p, v, acc = polynomial(points, t), polynomial(d, t), polynomial(dd, t)
                speed = math.hypot(*v)
                speeds.append(speed)
                self.assertGreater(sum(v[k]*record['start']['forward_unit'][k] for k in range(2)), 0)
                curvature = abs(v[0]*acc[1]-v[1]*acc[0])/speed**3
                self.assertLessEqual(curvature, selected['checks']['curvature']['upper_per_m'][piece]+1e-10)
                for k in range(2):
                    self.assertLessEqual(record['region']['min_m'][k]-1e-8, p[k])
                    self.assertLessEqual(p[k], record['region']['max_m'][k]+1e-8)
            length += (speeds[0]+speeds[-1]+sum((4 if i%2 else 2)*speeds[i] for i in range(1, 400)))/1200
        bounds = selected['checks']['length']
        self.assertLessEqual(bounds['lower_m']-1e-7, length)
        self.assertLessEqual(length, bounds['upper_m']+1e-7)
        self.assertLessEqual(bounds['upper_m'], record['constraints']['max_length_m'])

    def test_straight_and_deterministic_nonmutation(self):
        record = fixture()
        original = copy.deepcopy(record)
        result = fit_connection(record)
        self.verify(record, result)
        self.assertEqual(len(result['candidate']['curves'][0]['controls']), 2)
        self.assertEqual(result, fit_connection(record))
        self.assertEqual(record, original)
        json.dumps(result, allow_nan=False)

    def test_heading_and_rigid_map_transforms(self):
        for angle, translation in ((0, (0, 0)), (1.1, (100, -200)),
                                   (-2.7, (9000000, -9000000))):
            record = fixture()
            record['end']['position_m'] = [500, 100, 0]
            record['end']['forward_unit'] = [math.cos(math.pi/6), .5, 0]
            c, s = math.cos(angle), math.sin(angle)
            for key in ('start', 'end'):
                x, y, z = record[key]['position_m']
                record[key]['position_m'] = [translation[0]+c*x-s*y, translation[1]+s*x+c*y, z]
                x, y, z = record[key]['forward_unit']
                record[key]['forward_unit'] = [c*x-s*y, s*x+c*y, z]
            record['region'] = {'min_m': [translation[0]-2000, translation[1]-2000, -1],
                                'max_m': [translation[0]+2000, translation[1]+2000, 1]}
            with self.subTest(angle=angle):
                self.verify(record, fit_connection(record))

    def test_tight_radius_and_length_are_not_relaxed(self):
        record = fixture()
        record['end']['position_m'] = [10, 10, 0]
        record['end']['forward_unit'] = [math.cos(math.pi/6), .5, 0]
        record['constraints']['min_radius_m'] = 10000
        result = fit_connection(record)
        self.assertEqual(result['status'], 'no_accepted_candidate')
        self.assertEqual(result['search_status'], 'complete')
        self.assertIsNone(result['candidate'])
        record = fixture()
        record['constraints']['max_length_m'] = 499
        self.assertEqual(fit_connection(record)['status'], 'no_accepted_candidate')

    def test_span_across_kernel_map_bounds(self):
        record = fixture()
        record['start']['position_m'] = [-9000000, 0, 0]
        record['end']['position_m'] = [9000000, 0, 0]
        record['region'] = {'min_m': [-10000000, -2000000, -1],
                            'max_m': [10000000, 2000000, 1]}
        record['constraints']['max_length_m'] = 20000000
        self.verify(record, fit_connection(record))

    def test_outside_region(self):
        record = fixture()
        record['region']['max_m'][0] = 100
        result = fit_connection(record)
        self.assertEqual(result['status'], 'failed_checks')
        self.assertEqual(result['evaluated'], 0)

    def test_zero_and_partial_budget_discard_winners(self):
        for budget in (0, 1, 28):
            record = fixture()
            record['constraints']['max_candidates'] = budget
            result = fit_connection(record)
            self.assertEqual(result['status'], 'incomplete_search')
            self.assertEqual(result['evaluated'], budget)
            self.assertIsNone(result['candidate'])
            self.assertEqual(len(result['grid']), 29)
            if budget:
                self.assertTrue(result['candidate_checks'][0]['pass'])
        record['constraints']['max_candidates'] = 29
        self.verify(record, fit_connection(record))

    def test_invalid_and_relative_domain(self):
        self.assertEqual(fit_connection({})['status'], 'invalid_input')
        for position, heading in (([-1, 0, 0], [1, 0, 0]), ([0, 1, 0], [1, 0, 0]),
                                  ([500, 0, 0], [0, 1, 0]), ([10000001, 0, 0], [1, 0, 0])):
            record = fixture()
            record['end'].update(position_m=position, forward_unit=heading)
            self.assertEqual(fit_connection(record)['status'], 'unsupported_input')
        for angle in (-math.pi/4, math.pi/4):
            record = fixture()
            record['end']['forward_unit'] = [math.cos(angle), math.sin(angle), 0]
            self.assertNotEqual(fit_connection(record)['status'], 'unsupported_input')

    def test_all_two_piece_joins_and_affine_projection(self):
        record = fixture()
        record['end']['position_m'][1] = 100
        result = fit_connection(record)
        for row in result['candidate_checks'][2:]:
            self.assertTrue(row['checks']['joins']['pass'])
            a, b = [c['controls'] for c in row['curves']]
            self.assertEqual(a[-1], b[0])
            for points in (a, b):
                d, dd = derivative(points), derivative(derivative(points))
                self.assertAlmostEqual(max(v[0] for v in d), min(v[0] for v in d))
                for t in (0, 1):
                    v, acc = polynomial(d, t), polynomial(dd, t)
                    self.assertAlmostEqual(v[0]*acc[1]-v[1]*acc[0], 0, places=6)
            va, vb = polynomial(derivative(a), 1), polynomial(derivative(b), 0)
            self.assertAlmostEqual(va[1]/va[0], vb[1]/vb[0])

    def test_continuous_hulls_subdivide_and_reject_excursions(self):
        fit_connection(fixture())  # initialise the existing proof import path
        from railgeom.curves import Bezier
        c = Bezier(((0., 0.), (5., 2.), (10., 0.)))
        good = _connection_region_bound(c, [0, 0], [10, 1.1])
        self.assertTrue(good['pass'])
        self.assertIn('children', good)
        self.assertFalse(_connection_region_bound(c, [0, 0], [10, .9])['pass'])


if __name__ == '__main__':
    unittest.main()
