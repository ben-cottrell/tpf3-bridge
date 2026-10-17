"""Typed primary-research component references, never guessed CAD geometry."""
from __future__ import annotations
import copy
from .reference import EVIDENCE,number
from railclear.catalogue import read_json,exact
from railclear.model import digest

RECORD_FIELDS=('id','source_id','source_locator','scope','component_description','quantities','geometry','geometry_missing','speed_kind','source_figure_is_dimensional_component_drawing','eligible_for_station_placement')
QUANTITIES={
 'reported_switch_radius_m':('length','reported_local_switch_radius'),
 'reported_crossing_ratio_denominator':('dimensionless','reported_crossing_ratio'),
 'reported_nominal_gauge_mm':('length','reported_track_gauge'),
 'reported_facing_through_line_speed_kmh':('speed','reported_facing_through_line_speed'),
 'reported_trailing_diverging_line_speed_kmh':('speed','reported_trailing_diverging_line_speed'),
 'movable_stub_beam_length_m':('length','research_movable_stub_beam_not_complete_turnout')}


def resolve_component_reference(record):
    exact(record,RECORD_FIELDS)
    r=copy.deepcopy(record)
    for key in ('id','source_id','source_locator','scope','component_description','speed_kind'):
        if not isinstance(r[key],str) or not r[key].strip():raise ValueError('missing_source_scope')
    if r['geometry'] is not None or r['eligible_for_station_placement'] is not False or r['source_figure_is_dimensional_component_drawing'] is not False:
        raise ValueError('reference_record_cannot_self_promote')
    if not isinstance(r['geometry_missing'],list) or not r['geometry_missing'] or any(not isinstance(s,str) or not s for s in r['geometry_missing']):
        raise ValueError('missing_geometry_gaps')
    if not isinstance(r['quantities'],dict) or not r['quantities'] or set(r['quantities'])-set(QUANTITIES):
        raise ValueError('unsupported_quantity_semantics')
    for name,v in r['quantities'].items():number(v,name,positive=True)
    r.update({'status':'reference_only_missing_geometry','record_hash':digest(record),
        'quantity_semantics':{k:{'dimension':QUANTITIES[k][0],'scope':QUANTITIES[k][1]} for k in r['quantities']},
        'full_turnout_geometry_imported':False,'speed_usable_as_general_rating':False,'construction_authorised':False})
    return r


def load_component_references():
    r=read_json(EVIDENCE/'component_field_references.json')
    exact(r,('schema_version','records','authentic_complete_turnout_imported','construction_authorised'))
    if r['schema_version']!='0.8.0' or r['authentic_complete_turnout_imported'] is not False or r['construction_authorised'] is not False:
        raise ValueError('invalid_component_registry')
    out=[resolve_component_reference(x) for x in r['records']]
    if len({x['id'] for x in out})!=len(out):raise ValueError('duplicate_component_reference')
    return out


def compare_like_quantity(resolved,quantity,value,*,candidate_scope):
    if quantity not in resolved['quantities']:raise ValueError('quantity_not_supplied_by_source')
    value=number(value,'candidate_quantity',positive=True)
    expected_scope=resolved['quantity_semantics'][quantity]['scope']
    if candidate_scope!=expected_scope:
        return {'status':'not_comparable','reason':'different_component_or_measurement_scope',
                'source_quantity_scope':expected_scope,'candidate_quantity_scope':candidate_scope,
                'construction_authorised':False}
    reference_value=resolved['quantities'][quantity]
    return {'status':'scalar_comparison_only','source_value':reference_value,'candidate_value':value,
            'difference':value-reference_value,'source_id':resolved['source_id'],
            'whole_component_compatibility':'unassessed','construction_authorised':False}
