"""Bounded fresh semantic roles, not a duplicate native world or ID cache authority."""
import copy
import json
import math
import re
import uuid
from pathlib import Path
import bridge_live as live
import bridge_station as station


def simple_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',name):raise ValueError('simple bounded registry/role name required')
    return name


def checked_intent(intent):
    if set(intent)-{'region','max_edges','guide_xyz','travel_direction','heading_tolerance_deg','placement_tolerance','allow_bridge','refine_position'}:raise ValueError('unsupported role intent')
    for values,n in [(intent['guide_xyz'],3),(intent['travel_direction'],2),(intent['region']['min'],3),(intent['region']['max'],3)]:
        if not isinstance(values,list) or len(values)!=n or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):raise ValueError('finite role vectors required')
    if math.hypot(*intent['travel_direction'])==0:raise ValueError('nonzero role direction required')
    if any(not 0<b-a<=400 for a,b in zip(intent['region']['min'],intent['region']['max'])):raise ValueError('bounded ordered role region required')
    for key,default,bound in [('placement_tolerance',.15,10),('heading_tolerance_deg',2,180)]:
        value=intent.get(key,default)
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=bound:raise ValueError('bounded explicit role tolerances required')
    if type(intent.get('max_edges',16)) is not int or not 1<=intent.get('max_edges',16)<=16:raise ValueError('role edge observation bound')
    return dict(intent,max_edges=intent.get('max_edges',16),placement_tolerance=intent.get('placement_tolerance',.15),heading_tolerance_deg=intent.get('heading_tolerance_deg',2))


def diagnose(client,intent,mode='free'):
    if mode not in ('free','interior','connected','station_exit'):raise ValueError('free/interior/connected/station_exit role mode required')
    q=checked_intent(intent);operation={'free':'discover','interior':'discover_interior','connected':'discover_junction','station_exit':'discover'}[mode]
    response=client.request(operation,q);value=response.get('result',{});rows=[]
    for c in value.get('candidates',[])[:32]:
        reasons=[];d=c.get('outward_direction',[])
        if len(d)<2 or math.hypot(*d[:2])==0:reasons.append('direction_unavailable')
        else:
            a=q['travel_direction'];heading=math.degrees(math.acos(max(-1,min(1,sum(d[i]*a[i] for i in (0,1))/(math.hypot(*d[:2])*math.hypot(*a))))))
            if heading>q['heading_tolerance_deg']:reasons.append('direction_mismatch')
        if len(c.get('pos',[]))!=3 or math.dist(c['pos'],q['guide_xyz'])>q['placement_tolerance']:reasons.append('outside_declared_location')
        if mode!='station_exit' and isinstance(c.get('construction_owner'),(int,float)) and c['construction_owner']>0:reasons.append('construction_owned')
        if mode!='interior' and (c.get('incidence_complete') is not True or c.get('incident_output_truncated')):reasons.append('incidence_incomplete')
        eligible=(c.get('incident_count')==1 and c.get('incident_edges')==[c.get('edge_id')]) if mode=='station_exit' else c.get({'free':'eligible','interior':'interior_eligible','connected':'junction_eligible'}[mode]) is True
        if not eligible:reasons.append('connected_endpoint_unsupported' if c.get('incident_count',0)>1 else 'adapter_attachment_exclusion')
        rows.append({'edge':c.get('edge_id'),'node':c.get('node_id'),'eligible':eligible and not reasons,'reasons':reasons,'candidate':c})
    rejections=[{'edge':r.get('edge'),'reason':r.get('reason','adapter_check_failed'),'detail':r.get('error','unknown')} for r in value.get('rejections',[])[:16]]
    complete=response.get('status')=='ok' and value.get('complete') is True and len(value.get('candidates',[]))<=32 and len(value.get('rejections',[]))<=16
    return {'status':'ok' if complete else 'incomplete','mode':mode,'complete':complete,'request_id':response.get('request_id'),
            'reason_class':'adapter_attachment_eligibility','native_proposal_evaluated':False,'candidates':rows,'rejections':rejections,
            'native_status':response.get('status'),'error':value.get('error')}


class InterfaceRegistry:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def path(self,name):return self.root/(simple_name(name)+'.json')
    def load(self,name):return json.loads(self.path(name).read_text())
    def observe(self,client,roles):
        resolved={};surveys={}
        for name,role in roles.items():
            simple_name(name)
            if set(role)-{'station','intent','mode','grade'}:raise ValueError('unsupported role definition')
            q=checked_intent(role['intent']);mode=role.get('mode','free')
            if 'station' not in role:raise ValueError('persistent role requires exact station association')
            spec=role['station']
            if set(spec)-{'name','construction','terminal_index'}:raise ValueError('bounded station role selector required')
            if 'terminal_index' in spec and (type(spec['terminal_index']) is not int or not 1<=spec['terminal_index']<=64):raise ValueError('one-based native terminal index1..64 required')
            if 'grade' in role and (type(role['grade']) not in (int,float) or not math.isfinite(role['grade'])):raise ValueError('finite role grade required')
            key=spec['name']
            if key not in surveys:
                response=client.request('station_lookup',station.parameters({'name':key}))
                v=station.normalized_station(response.get('result',{}))
                if response['status']!='ok' or v.get('complete') is not True or v.get('outcome')!='resolved':raise live.LiveError('station_role_unavailable',v.get('outcome',response['status']))
                surveys[key]=v
            v=surveys[key];selector=spec['construction']
            if set(selector)!={'resource','position'}:raise ValueError('observed construction resource/position required')
            constructions=[c for c in v['constructions'] if c['resource']==selector['resource'] and c['position']==selector['position']]
            if len(constructions)!=1:raise live.LiveError('ambiguous_or_changed_construction','station construction semantic selector is not unique/current')
            cid=constructions[0]['construction_id'];diagnostic=diagnose(client,q,mode)
            if not diagnostic['complete']:raise live.LiveError('discovery_incomplete','role read is incomplete')
            candidates=[]
            for row in diagnostic['candidates']:
                if not row['eligible']:continue
                c=row['candidate'];associations=[]
                if mode=='station_exit':
                    assoc=station.associate_station_exit(v,c,cid)
                    if assoc:associations.append(assoc)
                for port in ([] if mode=='station_exit' else v['ports']):
                    assoc=port['association']
                    if assoc['construction_id']!=cid:continue
                    if mode=='free' and (port['edge_id']!=c['edge_id'] or port['node_id']!=c['node_id']):continue
                    if mode!='free' and c['edge_id'] not in assoc['edge_ids']:continue
                    if 'frozen_tracks' in constructions[0]:
                        assoc=assoc|{'terminal_identity_matches':station.terminal_component_matches(v,cid,assoc['frozen_edge'])}
                    terminal_matches=assoc.get('terminal_identity_matches',[])
                    if 'terminal_index' in spec:
                        terminal_matches=[t for t in terminal_matches if t['terminal_index']==spec['terminal_index']]
                        if len(terminal_matches)!=1:continue
                    associations.append(assoc)
                if 'terminal_index' in spec:
                    associations=[a for a in associations if len([t for t in a.get('terminal_identity_matches',[]) if t['terminal_index']==spec['terminal_index']])==1]
                if associations and ('grade' not in role or abs(c['grade']-role['grade'])<=.000001):candidates.append((c,associations))
            # No ranking by nearest position: identity is exact station incidence.
            if len(candidates)!=1:raise live.LiveError('ambiguous_role' if candidates else 'role_unavailable','exact station-associated role is not uniquely resolved')
            c,associations=candidates[0];c=copy.deepcopy(c);c.pop('ref',None)
            resolved[name]={'session':client.session,'group_id':v['group_id'],'construction_id':cid,'candidate':c,'mode':mode,
                            'associations':associations,'terminal_association':'exact' if 'terminal_index' in spec else 'unqualified',
                            'native_save_identity':v.get('native_save_identity','unknown')}
            if 'terminal_index' in spec:
                matched={(t['station_id'],t['terminal_index']) for assoc in associations for t in assoc.get('terminal_identity_matches',[]) if t['terminal_index']==spec['terminal_index']}
                if len(matched)!=1:raise live.LiveError('ambiguous_terminal','role terminal association is not unique')
                sid,index=next(iter(matched));positions=[i for i,s in enumerate(v['stations']) if s['station_id']==sid]
                if len(positions)!=1:raise live.LiveError('terminal_station_unavailable','exact terminal station missing')
                resolved[name]['operating_terminal']={'station_group':v['group_id'],'station':positions[0],'terminal':index-1}
        # Reacquire station identities/topology before accepting the non-atomic reads.
        for name,v in surveys.items():
            final=client.request('station_lookup',station.parameters({'name':name}))
            if final['status']!='ok' or station.normalized_station(final.get('result',{}))!=v:raise live.LiveError('stale_station','station role topology changed during observation')
        if any(x['session']!=client.session for x in resolved.values()):raise live.LiveError('session_changed','role observation crossed session')
        return resolved
    def register(self,client,name,revision,roles):
        simple_name(name)
        if not isinstance(revision,str) or not 1<=len(revision)<=80 or not isinstance(roles,dict) or not 1<=len(roles)<=64:raise ValueError('explicit revision and1..64 roles required')
        path=self.path(name)
        if path.exists() and self.load(name)['revision']==revision:raise ValueError('new registry revision required')
        resolved=self.observe(client,roles)
        record={'version':1,'name':name,'revision':revision,'roles':copy.deepcopy(roles),'resolved':resolved,'session':client.session}
        if path.exists():
            old=self.load(name);history=self.root/(name+'.'+uuid.uuid4().hex+'.previous.json');live.atomic_json(history,old)
        live.atomic_json(path,record)
        return {'status':'ok','name':name,'revision':revision,'roles':len(roles),'evidence':str(path),'game_constructed':False}
    def resolve(self,client,name,revision,names=None):
        record=self.load(name)
        if record['revision']!=revision:raise ValueError('registry revision changed')
        selected=record['roles']
        if names is not None:
            if not isinstance(names,list) or not 1<=len(names)<=64 or len(set(names))!=len(names):raise ValueError('bounded distinct requested role names required')
            selected={simple_name(n):record['roles'][n] for n in names}
        resolved=self.observe(client,selected)
        evidence=self.root/(name+'.'+uuid.uuid4().hex+'.resolved.json')
        live.atomic_json(evidence,{'name':name,'revision':revision,'session':client.session,'resolved':resolved})
        return {'status':'ok','name':name,'revision':revision,'resolved':resolved,'evidence':str(evidence),'game_constructed':False}
