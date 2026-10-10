"""Named data tasks over existing native operating APIs; no simulator or polling."""
import bridge_live as live
import bridge_station as station

KINDS={'signal','station','depot','operating','observe'}
ACTIONS={'vehicle_buy','line_create','line_update','vehicle_assign','vehicle_stop','vehicle_manual_departure'}

def validate(kind,brief,earlier):
    def check(value):
        if isinstance(value,dict):
            if set(value)=={'result','path'}:
                if value['result'] not in earlier or not isinstance(value['path'],list) or not 1<=len(value['path'])<=8 or any(not isinstance(k,str) for k in value['path']):raise ValueError('result reference requires an earlier task and bounded field path')
            elif set(value)=={'role','field'}:
                if not isinstance(value['role'],str) or value['field'] not in ('edge_id','node_id','grade','operating_terminal'):raise ValueError('explicit role operating field required')
            else:
                for v in value.values():check(v)
        elif isinstance(value,list):
            for v in value:check(v)
    check(brief)
    if kind=='operating':
        action=brief.get('action')
        if action not in ACTIONS:raise ValueError('unsupported native operating action')
        if 'execute' in brief:raise ValueError('operator owns execution flag')
        if action in ('line_create','line_update'):
            if not isinstance(brief.get('stops'),list) or not 2<=len(brief['stops'])<=8:raise ValueError('native service requires2..8 stops')
            for stop in brief['stops']:
                if len(stop.get('alternatives',[]))>8:raise ValueError('at most8 explicit alternative terminals')
        if action=='vehicle_buy' and (not isinstance(brief.get('parts'),list) or not 1<=len(brief['parts'])<=8):raise ValueError('native consist requires1..8 parts')

def role_names(value):
    if isinstance(value,dict):
        if set(value)=={'role','field'}:return {value['role']}
        return set().union(*(role_names(v) for v in value.values()))
    if isinstance(value,list):return set().union(*(role_names(v) for v in value))
    return set()

def references(value,steps,roles):
    if isinstance(value,dict):
        if set(value)=={'result','path'}:
            path=value['path']
            if not isinstance(path,list) or not 1<=len(path)<=8 or any(not isinstance(k,str) for k in path):raise ValueError('bounded result field path required')
            result=steps[value['result']]['result']
            for key in path:result=result[key]
            return result
        if set(value)=={'role','field'}:
            role=roles[value['role']];field=value['field']
            if field=='operating_terminal':return role[field]
            if field not in ('edge_id','node_id','grade'):raise ValueError('unsupported role operating field')
            return role['candidate'][field]
        return {k:references(v,steps,roles) for k,v in value.items()}
    if isinstance(value,list):return [references(v,steps,roles) for v in value]
    return value

def perform(client,kind,brief):
    if kind=='signal':return live.place_signal(client,brief,execute=True)
    if kind=='station':return station.place_station(client,brief,execute=True)
    if kind=='depot':return live.place_depot(client,brief,execute=True)
    if kind=='observe':
        if set(brief)-{'vehicle_ids','track_ids','signal_ids','limit'}:raise ValueError('only bounded representative operating observation supported')
        if not any(k in brief for k in ('vehicle_ids','track_ids','signal_ids')):raise ValueError('explicit observation IDs required')
        if sum(k in brief for k in ('vehicle_ids','track_ids','signal_ids'))!=1:raise ValueError('one observation category per step')
        if type(brief.get('limit',16)) is not int or not 1<=brief.get('limit',16)<=16:raise ValueError('observation limit1..16')
        ids=next(brief[k] for k in ('vehicle_ids','track_ids','signal_ids') if k in brief)
        if not isinstance(ids,list) or not 1<=len(ids)<=16 or any(type(x) is not int or x<=0 for x in ids):raise ValueError('1..16 exact observation IDs required')
        return client.request('operating_inspect',brief)
    if kind!='operating' or brief.get('action') not in ACTIONS:raise ValueError('unsupported native operating task')
    q=dict(brief);action=q['action']
    if 'execute' in q:raise ValueError('operator owns execution flag')
    if action=='vehicle_buy':
        # The existing native purchase preparation checks exact depot revision,
        # actual rail models, consist/load configuration; no asset guessing.
        prepared=client.request('operating_inspect',{'vehicle_purchase':q})
        if prepared['status']!='ok':return prepared
    elif action in ('line_update','vehicle_assign','vehicle_stop','vehicle_manual_departure'):
        category,key=('lines','line_id') if action=='line_update' else ('vehicles','vehicle_id')
        params={'limit':16} if category=='lines' else {'vehicle_ids':[q[key]],'limit':1}
        current=client.request('operating_inspect',params)
        if current['status']!='ok':return current
        rows=current.get('result',{}).get(category,{}).get('records',[])
        rows=[r for r in rows if r['id']==q[key]]
        if len(rows)!=1:raise live.LiveError('operating_identity_unavailable','exact current operating identity not in bounded read')
        if 'revision' in q and q['revision']!=rows[0]['revision']:raise live.LiveError('stale_operating_identity','explicit operating revision changed')
        q['revision']=rows[0]['revision']
    return client.request('operating_control',dict(q,execute=True))
