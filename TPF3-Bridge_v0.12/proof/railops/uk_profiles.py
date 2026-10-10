"""Narrow source-backed checks, nominal lookups and explicit profile admission.

These are not whole-network approval. Values are loaded from the authored
versioned register, not inferred from a rule title. Source applicability remains
an explicit input. Guidance outputs and nominal references are not pass verdicts.
"""
from pathlib import Path
import json
from railproof.model import positive
from railproof.rules import platform_cant, platform_radius, gb_platform_interface

REGISTER = Path(__file__).resolve().parents[2]/'evidence'/'uk_parameters.json'


def register() -> dict:
    data=json.loads(REGISTER.read_text(encoding='utf-8'))
    if data.get('schema_version')!='0.4.0' or data.get('whole_profile_approved') is not False:
        raise ValueError('Unrecognised numerical register or unsupported approval claim')
    rows=data.get('parameters')
    if not isinstance(rows,list) or not rows:
        raise ValueError('Missing numerical records')
    ids=set()
    for row in rows:
        if not isinstance(row,dict): raise ValueError('Parameter must be an object')
        for key in ('id','units','source_id','source_issue','clause','kind','applicability','verification'):
            if not isinstance(row.get(key),str) or not row[key].strip():
                raise ValueError('Missing parameter provenance or units')
        if row['id'] in ids: raise ValueError('Duplicate parameter ID')
        ids.add(row['id']); positive(row.get('value'),'registered value')
        if type(row.get('printed_page')) is not int or row['printed_page']<1:
            raise ValueError('Invalid printed page')
        if row.get('pdf_page_index')!=row['printed_page']-1:
            raise ValueError('Page-index mismatch in this register')
        if row['verification']!='selected_clause_text_and_page_image_reviewed':
            raise ValueError('Unreviewed value cannot enter this executable register')
    return data


def parameter(key: str) -> dict:
    matches=[r for r in register()['parameters'] if r['id']==key]
    if len(matches)!=1:
        raise ValueError('Missing or duplicate parameter')
    return matches[0]


def flag(value, name: str):
    if value is not None and type(value) is not bool:
        raise ValueError(f'{name} must be true, false or null')


def scope(applicable, override_pending=False):
    flag(applicable,'applicability')
    if type(override_pending) is not bool:
        raise ValueError('override_pending must be boolean')
    if applicable is False:
        return {'status':'not_applicable','reason':'explicit clause scope excludes this instance'}
    if applicable is None or override_pending:
        return {'status':'unassessed','reason':'clause scope or permitted alternative unresolved'}
    return None


def nominal_gauge(*, applicable: bool|None) -> dict:
    early=scope(applicable)
    if early: return early
    p=parameter('GB_NOMINAL_GAUGE')
    return {'status':'reference_value','parameter_id':p['id'],'value':p['value'],'units':p['units'],
            'source_id':p['source_id'],'clause':p['clause'],
            'not_assessed':['gauge tolerances','gauge widening','track condition']}


def gb_track_centres(*, applicable: bool|None, straight: bool|None,
                     radius_m: float|None=None, reduction_pending: bool=False) -> dict:
    flag(straight,'straight')
    early=scope(applicable,reduction_pending)
    if early: return early
    if straight is None: return {'status':'unassessed','reason':'geometry type unknown'}
    if straight and radius_m is not None:
        raise ValueError('A straight must not also have a finite radius')
    if not straight:
        if radius_m is None: return {'status':'unassessed','reason':'curve radius unknown'}
        positive(radius_m,'radius')
        if radius_m<parameter('GB_CENTRES_RADIUS_SCOPE')['value']:
            return {'status':'unassessed','reason':'radius outside imported GB nominal-centres scope'}
    p=parameter('GB_NOMINAL_TRACK_CENTRES')
    return {'status':'reference_value','parameter_id':p['id'],'value':p['value'],'units':p['units'],
            'source_id':p['source_id'],'clause':p['clause'],
            'not_assessed':['swept vehicle clearance','aerodynamic or route-specific constraints',
                            'platform island space','exceptions and national technical rules']}


def new_line_radius(radius_m: float|None, *, applicable: bool|None, new_line: bool|None,
                    straight: bool=False, override_pending: bool=False) -> dict:
    flag(new_line,'new_line')
    if type(straight) is not bool: raise ValueError('straight must be boolean')
    early=scope(applicable,override_pending)
    if early: return early
    if new_line is False: return {'status':'not_applicable','reason':'new-line floor only'}
    if new_line is None: return {'status':'unassessed','reason':'line status unknown'}
    p=parameter('NEW_LINE_HORIZONTAL_RADIUS_FLOOR')
    if straight:
        if radius_m is not None: raise ValueError('Straight with finite radius')
        return {'status':'pass','parameter_id':p['id'],'geometry':'straight','scope':'this floor only'}
    if radius_m is None: return {'status':'unassessed','reason':'missing radius'}
    positive(radius_m,'radius')
    return {'status':'pass' if radius_m>=p['value'] else 'fail','parameter_id':p['id'],
            'value_m':radius_m,'limit_m':p['value'],'source_id':p['source_id'],'clause':p['clause'],
            'scope':'base floor only; speed, reverse curves and platform criteria remain separate'}


def coupling_platform_gradient(grade_magnitude: float|None, *, applicable: bool|None,
        new_line: bool|None, regular_attach_detach: bool|None, override_pending: bool=False) -> dict:
    flag(new_line,'new_line');flag(regular_attach_detach,'regular_attach_detach')
    early=scope(applicable,override_pending)
    if early: return early
    if new_line is False or regular_attach_detach is False:
        return {'status':'not_applicable','reason':'not the new-line regular attachment/detachment case'}
    if new_line is None or regular_attach_detach is None or grade_magnitude is None:
        return {'status':'unassessed','reason':'missing grade or applicability conditions'}
    positive(grade_magnitude,'grade magnitude',zero=True)
    p=parameter('NEW_COUPLING_PLATFORM_GRADIENT')
    return {'status':'pass' if grade_magnitude<=p['value'] else 'fail','parameter_id':p['id'],
            'value_fraction':grade_magnitude,'limit_fraction':p['value'],
            'source_id':p['source_id'],'clause':p['clause'],'scope':'not a universal station-gradient rule'}


def vertical_radius(radius_m: float|None, *, kind: str, applicable: bool|None,
                    marshalling_hump: bool|None=False, override_pending: bool=False) -> dict:
    if kind not in ('crest','sag'): raise ValueError('Vertical curve kind must be crest or sag')
    flag(marshalling_hump,'marshalling_hump')
    early=scope(applicable,override_pending)
    if early: return early
    if marshalling_hump is True:
        return {'status':'not_applicable','reason':'hump exception not imported in passenger profile'}
    if marshalling_hump is None or radius_m is None:
        return {'status':'unassessed','reason':'missing radius or hump status'}
    positive(radius_m,'vertical radius')
    p=parameter('VERTICAL_CREST_FLOOR' if kind=='crest' else 'VERTICAL_SAG_FLOOR')
    return {'status':'pass' if radius_m>=p['value'] else 'fail','parameter_id':p['id'],
            'value_m':radius_m,'limit_m':p['value'],'source_id':p['source_id'],'clause':p['clause'],
            'scope':'base floor only, not a speed-dependent vertical design'}


def platform_zone_widths(*, applicable: bool|None, method: str, block_passengers: float|None,
                        block_length_m: float|None, circulation_peak_5min: float|None) -> dict:
    """NR method-two Zone B/C only; no complete platform or accessibility verdict."""
    early=scope(applicable)
    if early: return early
    if method!='platform_waiting_method_two':
        return {'status':'unassessed','reason':'different demand/dispatch method requires its own equations'}
    if any(x is None for x in (block_passengers,block_length_m,circulation_peak_5min)):
        return {'status':'unassessed','reason':'missing disaggregated demand or block length'}
    positive(block_passengers,'block passengers',zero=True)
    positive(block_length_m,'block length')
    positive(circulation_peak_5min,'circulation demand',zero=True)
    b=parameter('NR_ZONE_B_AREA_PER_PERSON')['value']*block_passengers/block_length_m
    c=circulation_peak_5min/(5*parameter('NR_ZONE_C_FLOW_PER_MIN_METRE')['value'])
    return {'status':'guidance_calculation','zone_B_m':b,'zone_C_m':c,'source_id':'S040',
            'printed_pages':[42,43],'full_platform_width_status':'unassessed',
            'not_included':['Zone A edge treatment','Zone D and obstacles','island opposite face',
                            'accessibility and minimum widths','demand validation'],
            'demand_condition':'B and C populations must not be double-counted'}


def admission(mode: str, *, synthetic_components: bool, mandatory_unknowns: list[str],
              game_tested: bool=False) -> dict:
    if mode not in ('synthetic_regression','gb_reference_inspired','gb_rules_strict'):
        raise ValueError('Unknown design mode')
    if type(synthetic_components) is not bool or type(game_tested) is not bool:
        raise ValueError('Admission flags must be boolean')
    if not isinstance(mandatory_unknowns,list) or any(not isinstance(x,str) or not x.strip() for x in mandatory_unknowns):
        raise ValueError('Unknowns must be explicit nonempty field IDs')
    unresolved=list(dict.fromkeys(mandatory_unknowns))
    if synthetic_components: unresolved.append('authentic_component_catalogue')
    strict_clear=mode=='gb_rules_strict' and not unresolved
    return {'mode':mode,'offline_analysis_allowed':mode!='gb_rules_strict' or strict_clear,
            'UK_profile_gate':'resolved_inputs_only' if strict_clear else 'not_passed',
            'construction_authorised':False, # Never an authority-granting interface.
            'game_status':'tested_declared_scope' if game_tested else 'not_tested',
            'unresolved':unresolved,'synthetic_components':synthetic_components,
            'scope':'input admission only; no legal, safety or whole-network certification'}
