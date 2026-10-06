"""Check saved native inspection evidence; never query or mutate the game."""
import argparse
import json
import math
from pathlib import Path


def check_structure(record, expected_class, expected_resource=None):
    if record.get('classification') != expected_class:
        raise ValueError('native structure classification differs')
    if type(record.get('type_index')) is not int:
        raise ValueError('missing native resource index')
    if record.get('instance_parameters') != 'not_exposed_by_BaseEdge':
        raise ValueError('instance parameter evidence overstated')
    if expected_class == 'NORMAL':
        if record.get('resource_state') != 'not_applicable' or 'resource_name' in record:
            raise ValueError('ordinary edge incorrectly assigned structure resource')
        return
    repository = {'BRIDGE': 'bridgeTypeRep', 'TUNNEL': 'tunnelTypeRep'}[expected_class]
    if (record.get('resource_state') != 'resolved' or record.get('repository') != repository
            or record.get('resource_name') != expected_resource):
        raise ValueError('selected native structure resource unresolved or mismatched')
    parameters = record.get('resource_parameters')
    if not isinstance(parameters, dict) or not isinstance(parameters.get('carriers'), list):
        raise ValueError('missing bounded resource configuration')
    if len(parameters['carriers']) > 8 or type(parameters.get('carriers_truncated')) is not bool:
        raise ValueError('carrier observation unbounded')
    for value in parameters.values():
        if type(value) in (int, float) and not math.isfinite(value):
            raise ValueError('nonfinite resource parameter')


def check_evidence(directory):
    def read(name): return json.loads((directory / name).read_text(encoding='utf-8'))
    rail = read('rail_structures.json')
    ordinary = read('ordinary_compatibility.json')
    road = read('road_structure.json')
    invalid = read('invalid_structure_flag.json')
    for response in (rail, ordinary, road):
        if response['status'] != 'ok' or response['session'] != rail['session']:
            raise ValueError('failed or mixed-session native evidence')
    edges = {edge['id']: edge for edge in rail['result']['edges']}
    for edge_id in (61045, 63416, 63098):
        check_structure(edges[edge_id]['structure'], 'NORMAL')
    for edge_id in (67251, 67265):
        check_structure(edges[edge_id]['structure'], 'BRIDGE', '::/infrastructure/bridge/stone.bridge')
    for edge_id in (63362, 63150):
        check_structure(edges[edge_id]['structure'], 'TUNNEL', '::/infrastructure/tunnel/tunnel_b.tunnel')
    plain = ordinary['result']['edges'][0]
    if 'structure' in plain or plain != {k: v for k, v in edges[61045].items() if k != 'structure'}:
        raise ValueError('default inspection compatibility changed')
    site = road['result']['site']
    if site['truncated']:
        raise ValueError('road evidence incomplete')
    bridge = next(e for e in site['entities'] if e['entity'] == 64072)
    if bridge['TRACK'] or (bridge['node0'], bridge['node1']) != (64070, 64071):
        raise ValueError('wrong road reference identity')
    check_structure(bridge['structure'], 'BRIDGE', '::/infrastructure/bridge/stone.bridge')
    if (invalid['session'] != rail['session'] or invalid['status'] == 'ok'
            or 'structures_flag_boolean_required' not in json.dumps(invalid)):
        raise ValueError('malformed structures flag not rejected')
    return {'status': 'passed', 'session': rail['session'], 'confirmed_rail_edges': 7,
            'confirmed_road_bridge': 64072, 'default_compatibility': True,
            'malformed_flag_rejected': True, 'native_reads_replayed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    print(json.dumps(check_evidence(parser.parse_args().evidence), separators=(',', ':')))
