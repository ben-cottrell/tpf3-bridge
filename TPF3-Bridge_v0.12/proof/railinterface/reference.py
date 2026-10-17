"""Narrow checks on a reviewed reference copy, not unseen current clauses.

Every result separates numerical agreement from evidence admission. Public
catalogue continuity does not substitute for reading the current full issue.
"""
from __future__ import annotations
import math
from pathlib import Path
from railclear.catalogue import read_json
from railclear.model import digest
EVIDENCE = Path(__file__).resolve().parents[2] / 'evidence'


def number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('invalid_finite_number:'+name)
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError('invalid_number_domain:'+name)
    return float(value)


def tri(value, name):
    if value is not None and type(value) is not bool:
        raise ValueError('invalid_tristate:'+name)
    return value


def reference():
    data = read_json(EVIDENCE/'platform_reference.json')
    if data['schema_version'] != '0.8.0' or data['current_full_issue_reviewed'] is not False:
        raise ValueError('unsupported_reference_admission')
    return data


def result(name, status, **details):
    ref = reference()
    return {'check': name, 'status': status, 'source_id': ref['source_id'],
            'source_issue': ref['source_issue'], 'reference_record_hash': digest(ref),
            'evidence_scope': ref['evidence_scope'], 'current_uk_compliance': 'unassessed',
            'construction_authorised': False, **details}


def height_check(height_mm, *, applicable, stage='design', legacy_stock=False,
                 linked_lower_sector_adjustment_confirmed=None):
    tri(applicable, 'applicable'); tri(legacy_stock, 'legacy_stock')
    tri(linked_lower_sector_adjustment_confirmed, 'linked_adjustment')
    if stage not in ('design', 'build_maintenance'):
        raise ValueError('unsupported_height_stage')
    if applicable is False: return result('platform_height','not_applicable')
    if applicable is None or legacy_stock is None or height_mm is None:
        return result('platform_height','unassessed',reason='missing_scope_or_input')
    h=number(height_mm,'height_mm',positive=True);r=reference()
    low=r['normal_design_height_mm']-(r['legacy_height_lower_tolerance_mm'] if legacy_stock else r['normal_height_lower_tolerance_mm'])
    high=r['normal_design_height_mm']
    if stage == 'build_maintenance':
        if linked_lower_sector_adjustment_confirmed is not True:
            return result('platform_height','unassessed',reason='linked_lower_sector_adjustment_not_confirmed')
        high += r['build_maintenance_additional_height_mm']
    return result('platform_height', 'reference_clause_pass' if low<=h<=high else 'reference_clause_fail',
                  measured_mm=h, permitted_interval_mm=[low,high], stage=stage,
                  datum='perpendicular_to_rail_plane',clause=r['height_clause'])


def offset_check(offset_mm, *, applicable, resolved_minimum_mm, minimum_origin):
    tri(applicable,'applicable')
    if minimum_origin not in ('explicit_standard_case_reference','draft_curve_example','unresolved'):
        raise ValueError('unknown_offset_origin')
    if applicable is False:return result('platform_offset','not_applicable')
    if applicable is None or offset_mm is None or resolved_minimum_mm is None or minimum_origin=='unresolved':
        return result('platform_offset','unassessed',reason='minimum_and_applicability_required')
    offset=number(offset_mm,'offset',positive=True);low=number(resolved_minimum_mm,'minimum',positive=True)
    r=reference();high=low+r['offset_positive_tolerance_mm']
    return result('platform_offset','reference_clause_pass' if low<=offset<=high else 'reference_clause_fail',
                  measured_mm=offset,permitted_interval_mm=[low,high],minimum_origin=minimum_origin,
                  datum=r['offset_datum'],clause=r['offset_clause'])


def draft_curve_offset(radius_m, *, straight=False, standard_case_confirmed=None):
    """S066 draft Appendix C standard case only; no current-rule promotion.

    The equation is kept unrounded. Its rounded example table is not treated as
    a second definition and the jump at R=360 remains source-explicit.
    """
    if type(straight) is not bool:raise ValueError('invalid_straight_flag')
    tri(standard_case_confirmed,'standard_case')
    if straight and radius_m is not None:raise ValueError('straight_and_radius_conflict')
    if not straight and radius_m is not None:number(radius_m,'radius',positive=True)
    base={'source_id':'S066','source_issue':'GIRT7073 Three Draft 1l March 2023',
          'clause':'C.1.1 Table 10','current_uk_compliance':'unassessed','construction_authorised':False,
          'special_cases_implemented':False}
    if standard_case_confirmed is not True or (not straight and radius_m is None):
        return {**base,'status':'unassessed','minimum_offset_mm':None}
    if not straight and radius_m<160:
        return {**base,'status':'outside_reviewed_draft_domain','minimum_offset_mm':None}
    value=730. if straight or radius_m>=360 else 658.+26000./radius_m
    return {**base,'status':'draft_reference_value','minimum_offset_mm':value}


def width_requirement(permissible_speeds_mph, *, applicable=True):
    tri(applicable,'applicable')
    if not isinstance(permissible_speeds_mph,(list,tuple)) or len(permissible_speeds_mph) not in (1,2):
        raise ValueError('one_or_two_platform_faces_required')
    for speed in permissible_speeds_mph:
        if speed is not None:number(speed,'permissible_speed',nonnegative=True)
    if applicable is False:return result('usable_width','not_applicable')
    if applicable is None or None in permissible_speeds_mph:
        return result('usable_width','unassessed',reason='unknown_permissible_or_enhanced_speed')
    r=reference();high=sum(s>r['width_speed_threshold_mph'] for s in permissible_speeds_mph)
    if len(permissible_speeds_mph)==1:
        v=r['single_face_high_speed_min_m' if high else 'single_face_low_speed_min_m']
    else:v=r[('island_neither_high_min_m','island_one_high_min_m','island_both_high_min_m')[high]]
    edges=[r['obstacle_high_speed_edge_clear_m' if s>r['width_speed_threshold_mph'] else 'obstacle_low_speed_edge_clear_m'] for s in permissible_speeds_mph]
    return result('usable_width','reference_requirement_value',minimum_width_m=v,edge_obstacle_clearances_m=edges,
                  permissible_or_enhanced_speeds_mph=list(permissible_speeds_mph),clause=r['width_clause'],
                  exceptional_reductions_applied=False,demand_capacity_status='unassessed')


def taper_length(delta_mm, kind):
    value=number(delta_mm,'delta')
    if kind not in ('height','offset'):raise ValueError('unknown_taper_kind')
    r=reference();length=abs(value)/1000*r[kind+'_taper_max_ratio']
    return result('taper','reference_lower_bound',minimum_longitudinal_length_m=length,
                  kind=kind,clause=r['taper_clause'],coping_unit_compatibility='unassessed' if kind=='offset' else 'not_evaluated')
