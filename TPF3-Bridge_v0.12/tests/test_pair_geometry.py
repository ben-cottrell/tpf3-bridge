"""Independent witnesses supplement the pair's continuous certificates."""
import copy
import hashlib
import json
import math
from pathlib import Path
import unittest

from bridge_pair import fit_pair, point_at, tangent_at, _offset_enclosures, _bezier, _PairBudget


def fixture(angle=0, opposing=False, rotation=0, translation=(0, 0), spacing=4):
    record = json.loads((Path(__file__).resolve().parents[1] / 'pair_example.json').read_text())
    c, s = math.cos(rotation), math.sin(rotation)
    for port in record['ports']:
        end = port['port_id'][1] == '1'
        second = port['port_id'][0] == 'b'
        phi = angle if end else 0
        d = spacing/2 if second else -spacing/2
        x = (500 if end else 0)-d*math.sin(phi)
        y = (100 if end and angle else 0)+d*math.cos(phi)
        port['position_m'] = [translation[0]+c*x-s*y, translation[1]+s*x+c*y, 0]
        sign = -1 if opposing and second else 1
        port['forward_unit'] = [sign*math.cos(phi+rotation), sign*math.sin(phi+rotation), 0]
    if opposing:
        record['connections'][1].update(start_port='b1', end_port='b0')
    record['constraints']['spacing_m'] = spacing
    record['region'] = {'min_m': [translation[0]-2000, translation[1]-2000, -1],
                        'max_m': [translation[0]+2000, translation[1]+2000, 1]}
    return record


def polynomial(points, t):
    degree = len(points)-1
    return [sum(math.comb(degree, i)*t**i*(1-t)**(degree-i)*p[k]
                for i, p in enumerate(points)) for k in range(2)]


def derivative(points):
    n = len(points)-1
    return [[n*(b[k]-a[k]) for k in range(2)] for a, b in zip(points, points[1:])] or [[0, 0]]


class PairGeometryTests(unittest.TestCase):
    def verify(self, record, result):
        self.assertEqual(result['status'], 'pair_ready')
        self.assertEqual(result['search_status'], 'complete')
        self.assertEqual(result['evaluated'], len(result['grid']))
        candidate = result['candidate']
        self.assertTrue(all(c['pass'] for c in candidate['pair_certificates'].values()))
        ports = {p['port_id']: p for p in record['ports']}
        for connection in record['connections']:
            track = connection['track_id']
            for t, key in ((0, 'start_port'), (1, 'end_port')):
                self.assertLess(math.dist(point_at(candidate, track, t), ports[connection[key]]['position_m']), 1e-6)
                self.assertLess(math.dist(tangent_at(candidate, track, t), ports[connection[key]]['forward_unit']), 1e-7)
            for i in range(1, 40):
                t = i/40; step = 1e-5
                before, after = point_at(candidate, track, t-step), point_at(candidate, track, t+step)
                velocity = [(b-a)/(2*step) for a, b in zip(before, after)]
                unit = [v/math.hypot(*velocity) for v in velocity]
                self.assertLess(math.dist(unit, tangent_at(candidate, track, t)), 1e-6)
        a, b = candidate['tracks']
        for i in range(81):
            t = i/80
            p = point_at(candidate, a['track_id'], t)
            q = point_at(candidate, b['track_id'], 1-t if b['reversed'] else t)
            delta = [y-x for x, y in zip(p, q)]
            self.assertAlmostEqual(math.hypot(*delta), record['constraints']['spacing_m'], places=6)
            self.assertAlmostEqual(sum(x*y for x, y in zip(delta, tangent_at(candidate, a['track_id'], t))), 0, places=6)
        # Independent Bernstein evaluation checks analytic offsets and the
        # derivative identities used for radius/length; no production evaluator.
        for track in candidate['tracks']:
            length = 0
            offset = track['offset_m']
            pieces = candidate['centreline']['curves']
            for piece, data in enumerate(pieces):
                controls = data['controls']; d = derivative(controls); dd = derivative(d)
                speeds = []
                for i in range(201):
                    u = i/200
                    p, v, acc = polynomial(controls, u), polynomial(d, u), polynomial(dd, u)
                    speed = math.hypot(*v)
                    k = (v[0]*acc[1]-v[1]*acc[0])/speed**3
                    factor = 1-offset*k
                    self.assertGreater(factor, 0)
                    self.assertLessEqual(abs(k/factor), 1/record['constraints']['min_radius_m'])
                    speeds.append(speed*factor)
                    expected = [p[0]-offset*v[1]/speed, p[1]+offset*v[0]/speed, 0]
                    t = (piece+u)/len(pieces)
                    if track['reversed']: t = 1-t
                    self.assertLess(math.dist(expected, point_at(candidate, track['track_id'], t)), 1e-6)
                    self.assertTrue(all(record['region']['min_m'][j] <= expected[j] <= record['region']['max_m'][j]
                                        for j in range(3)))
                length += (speeds[0]+speeds[-1]+sum((4 if i%2 else 2)*speeds[i] for i in range(1, 200)))/600
            bound = next(r for r in candidate['pair_certificates']['length']['tracks'] if r['track_id'] == track['track_id'])
            self.assertLessEqual(bound['lower_m']-1e-6, length)
            self.assertLessEqual(length, bound['upper_m']+1e-6)
        unhashed = copy.deepcopy(candidate); digest = unhashed.pop('candidate_hash')
        self.assertEqual(digest, hashlib.sha256(json.dumps(unhashed, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest())

    def test_straight_deterministic_and_no_mutation(self):
        record = fixture(); original = copy.deepcopy(record)
        result = fit_pair(record)
        self.verify(record, result)
        self.assertEqual(result, fit_pair(record))
        self.assertEqual(record, original)
        json.dumps(result, allow_nan=False)

    def test_curved_rotated_opposing_and_swapped(self):
        for angle, opposing, rotation in ((math.pi/6, False, 0), (math.pi/6, True, 1.1),
                                          (-math.pi/6, True, -2.7)):
            record = fixture(angle, opposing, rotation, (900000, -900000))
            self.verify(record, fit_pair(record))
            record['connections'].reverse()
            self.verify(record, fit_pair(record))

    def test_heading_boundaries(self):
        for angle in (-math.pi/4, math.pi/4):
            record = fixture(angle)
            self.verify(record, fit_pair(record))

    def test_incompatible_and_crossed(self):
        for kind in ('spacing', 'skew', 'crossed', 'direction'):
            record = fixture(math.pi/6)
            if kind == 'spacing': record['ports'][3]['position_m'][1] += 1
            if kind == 'skew': record['ports'][2]['position_m'][0] += 1
            if kind == 'direction': record['ports'][2]['forward_unit'] = [-1, 0, 0]
            if kind == 'crossed':
                record['connections'][0]['end_port'], record['connections'][1]['end_port'] = 'b1', 'a1'
            result = fit_pair(record)
            self.assertEqual(result['status'], 'unsupported_input', kind)
            self.assertIsNone(result['candidate'])

    def test_radius_spacing_and_length(self):
        for key, value in (('min_radius_m', 1000000), ('min_separation_m', 4.1), ('max_length_m', 499)):
            record = fixture(math.pi/6); record['constraints'][key] = value
            result = fit_pair(record)
            self.assertEqual(result['status'], 'no_accepted_candidate')
            self.assertIsNone(result['candidate'])
        record = fixture(); record['constraints']['min_separation_m'] = 4
        self.verify(record, fit_pair(record))
        record = fixture(math.pi/6, spacing=500)
        result = fit_pair(record)
        self.assertEqual(result['status'], 'incomplete_search')
        self.assertIsNone(result['candidate'])
        self.assertNotIn('selected_index', result)
        self.assertTrue(any('budget' in r['checks'] for r in result['candidate_checks']))
        for row in result['candidate_checks']:
            if row['pass']:
                self.assertGreater(row['checks']['regularity']['factor_lower'], 0)

    def test_region(self):
        record = fixture(); record['region']['max_m'][0] = 100
        self.assertEqual(fit_pair(record)['status'], 'failed_checks')
        record = fixture(); record['region']['min_m'][1] = -2; record['region']['max_m'][1] = 2
        self.verify(record, fit_pair(record))
        record = fixture(math.pi/6)
        # All endpoints inside, but the curve initially dips below this boundary.
        record['region']['min_m'][1] = -2.001
        result = fit_pair(record)
        if result['candidate']:
            self.assertTrue(result['candidate']['pair_certificates']['region']['pass'])
        self.assertTrue(any('region' in r['checks'] and not r['checks']['region']['pass']
                            for r in result['candidate_checks']))

    def test_budgets_and_invalid_evaluation(self):
        for budget in (0, 1, 28):
            record = fixture(); record['constraints']['max_candidates'] = budget
            result = fit_pair(record)
            self.assertEqual(result['status'], 'incomplete_search')
            self.assertEqual(result['evaluated'], budget)
            self.assertIsNone(result['candidate'])
        self.assertEqual(fit_pair({})['status'], 'invalid_input')
        candidate = fit_pair(fixture())['candidate']
        for t in (-.01, 1.01, float('nan'), True):
            with self.assertRaises(ValueError): point_at(candidate, 'a', t)
        with self.assertRaises(ValueError): tangent_at(candidate, 'missing', .5)
        with self.assertRaises(_PairBudget):
            _offset_enclosures([_bezier(((0, 0), (10, 10), (20, 0)))], 2, .00001, max_leaves=1)

    def test_offset_capsules_enclose_independent_polynomial(self):
        controls = ((0, 0), (30, 0), (60, 20), (90, 30))
        curve = _bezier(controls)
        for offset in (-2, 2):
            leaves = _offset_enclosures([curve], offset, .03)
            for leaf in leaves:
                for i in range(11):
                    t = leaf.t0+(leaf.t1-leaf.t0)*i/10
                    p = polynomial(controls, t); v = polynomial(derivative(controls), t)
                    p = [p[0]-offset*v[1]/math.hypot(*v), p[1]+offset*v[0]/math.hypot(*v)]
                    chord = [b-a for a, b in zip(leaf.a, leaf.b)]
                    u = max(0, min(1, sum((p[j]-leaf.a[j])*chord[j] for j in range(2))/sum(x*x for x in chord)))
                    nearest = [leaf.a[j]+u*chord[j] for j in range(2)]
                    self.assertLessEqual(math.dist(p, nearest), leaf.hull_radius_m)


if __name__ == '__main__':
    unittest.main()
