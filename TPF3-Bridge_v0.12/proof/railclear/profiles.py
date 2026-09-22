"""Published vehicle dimensions do not by themselves define a dynamic gauge."""
from .catalogue import exact, identifier, text
from .model import Body, positive, digest


def resolve_vehicle(record:dict,assumptions:dict|None=None)->dict:
    exact(record,('schema_version','profile_id','source_id','source_issue','published','missing_geometry'))
    if record['schema_version']!='0.5.0':raise ValueError('Vehicle record version')
    identifier(record['profile_id']);identifier(record['source_id']);text(record['source_issue'],'issue')
    fields=('nominal_vehicle_length_m','width_m','unit_8car_length_m','unit_12car_length_m')
    exact(record['published'],fields)
    values={}
    for key,v in record['published'].items():
        exact(v,('value','locator','kind'));positive(v['value'],key);text(v['locator'],'locator')
        if v['kind']!='manufacturer_catalogue':raise ValueError('Unsupported published claim kind')
        values[key]=v['value']
    required={'exact_body_outline','bogie_pivot_positions','suspension_allowances','cross_section','coupler_geometry'}
    if not isinstance(record['missing_geometry'],list) or set(record['missing_geometry'])!=required or len(record['missing_geometry'])!=len(required):
        raise ValueError('This partial manufacturer-profile adapter requires explicit missing geometry')
    result={'profile_id':record['profile_id'],'source_id':record['source_id'],'record_hash':digest(record),
            'published':values,'unresolved':sorted(required),'full_UK_gauging':'unassessed',
            'strict_profile_admitted':False,'formation_layout':'unassessed','body':None}
    if assumptions is not None:
        exact(assumptions,('use_nominal_length_as_rectangular_body','bogie_centres_m','lateral_allowance_m','vertical_scope'))
        if assumptions['use_nominal_length_as_rectangular_body'] is not True:raise ValueError('Body-length interpretation must be explicit')
        if assumptions['vertical_scope']!='level_zero_cant_plan_only':raise ValueError('This profile has no 3D/cant implementation')
        body=Body(values['nominal_vehicle_length_m'],values['width_m'],assumptions['bogie_centres_m'],
                  assumptions['lateral_allowance_m'],'reference_informed_assumptions',record['profile_id'])
        result.update({'body':body,'assumptions':dict(assumptions),'assumption_hash':digest(assumptions),
                       'status':'resolved_for_declared_static_study'})
    else:result['status']='reference_only_missing_geometry'
    return result
