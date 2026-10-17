"""Bounded read-only legacy/enriched dependency comparison; no production fallback."""
import argparse
import json
from pathlib import Path
import time

from bridge_approach import Dependencies
from bridge_operator import Operator
from bridge_signal_benchmark import Counted


class LegacyDependencies(Dependencies):
    """Isolated benchmark reference for the former spatial-witness observation path."""
    def observe_edges(self,ids,semantic_ids=()):
        return super().observe_edges(ids)

    def observe_semantics(self,ids):
        self.observe_edges(ids);self.observe_tracks(ids)
        for ident in sorted(set(ids)):
            e=self.edges[ident]
            for end in (0,1):
                node=e['node'+str(end)]
                if node in self.nodes:continue
                pos=e.get('node_positions',[e['p0'],e['p1']])[end]
                r=self.client.request('discover',{'region':{'min':[x-.5 for x in pos],'max':[x+.5 for x in pos]},'max_edges':16});v=r.get('result',{})
                witnesses=[c for c in v.get('candidates',[]) if c.get('node_id')==node and ident in c.get('incident_edges',[])]
                if r['status']!='ok' or v.get('complete') is not True or not witnesses:raise ValueError('legacy exact incidence witness unavailable')
                observations=[]
                for c in witnesses:
                    incident=self.exact_ids(c.get('incident_edges'),16)
                    if c.get('incidence_complete') is not True or c.get('incident_output_truncated') is not False or c.get('incident_count')!=len(incident):raise ValueError('legacy bounded complete incidence unavailable')
                    owner=c.get('construction_owner','unknown');owner='none' if owner is None else owner
                    observations.append({'incident_edges':sorted(incident),'construction_owner':owner})
                if any(o!=observations[0] for o in observations):raise ValueError('conflicting legacy exact-node witnesses')
                self.nodes[node]=observations[0]


class Measured(Counted):
    def __init__(self,client):
        super().__init__(client);self.phase='dependencies';self.operations={};self.response_bytes=0
    def request(self,operation,params,**kwargs):
        if operation not in ('inspect','operating_inspect','discover','station_lookup'):raise ValueError('benchmark dependency reads only')
        self.operations[operation]=self.operations.get(operation,0)+1
        r=super().request(operation,params,**kwargs)
        self.response_bytes+=len(json.dumps(r,separators=(',',':'),ensure_ascii=False).encode('utf-8'))
        return r
    def report(self,wall):
        c=self.counts.get(self.phase,{})
        return {'requests':c.get('requests',0),'operations':self.operations,'request_wait_seconds':round(c.get('native_seconds',0),6),
                'wall_seconds':round(wall,6),'response_bytes':self.response_bytes,'response_bytes_format':'reencoded_compact_UTF8_JSON'}


def compare(client,packet):
    """Two once-only reads of the SAME explicit current fixture; no route reruns/state writes."""
    if not isinstance(packet,dict) or set(packet)!={'version','session','checks'} or packet['version']!=1 or packet['session']!=client.session:
        raise ValueError('version1 current-session dependency packet required')
    checks=packet['checks']
    if not isinstance(checks,list) or not 1<=len(checks)<=32:raise ValueError('bounded1..32 dependency checks required')
    names=set();all_ids=set();semantic=set()
    for c in checks:
        if not isinstance(c,dict) or set(c)!={'name','kind','edge_ids','selectors'} or c['kind'] not in ('route','station_routes','geometry','crossing'):
            raise ValueError('explicit dependency check fields required')
        if not isinstance(c['name'],str) or not 1<=len(c['name'])<=160 or c['name'] in names:raise ValueError('unique bounded check names required')
        names.add(c['name']);ids=Dependencies.exact_ids(c['edge_ids'],256)
        if not ids:raise ValueError('explicit current exact rails required')
        all_ids.update(ids)
        if c['kind'] in ('route','station_routes'):semantic.update(ids)
        if not isinstance(c['selectors'],list) or len(c['selectors'])>8 or (c['kind']=='station_routes' and not c['selectors']):raise ValueError('bounded explicit station selectors required')
    if len(all_ids)>256:raise ValueError('benchmark bound256 exact edges exceeded')
    def healthy():
        if client.session!=packet['session']:raise ValueError('benchmark session changed')
        journal=getattr(client,'journal',None)
        if journal and Path(journal).exists() and json.loads(Path(journal).read_text()).get('pending'):raise ValueError('benchmark blocked by unresolved native request')
    healthy();values={};metrics={}
    for name,cls in (('legacy',LegacyDependencies),('enriched',Dependencies)):
        healthy();measured=Measured(client);start=time.monotonic();deps=cls(measured)
        deps.observe_edges(sorted(all_ids),semantic_ids=sorted(semantic))
        if semantic:deps.observe_semantics(sorted(semantic))
        values[name]={c['name']:deps.fingerprint(c,c['edge_ids'],c['selectors']) for c in checks}
        healthy();metrics[name]=measured.report(time.monotonic()-start)
    same=values['legacy']==values['enriched']
    return {'status':'ok' if same else 'needs_attention','session':packet['session'],'fingerprints_equal':same,
            'check_count':len(checks),'edge_count':len(all_ids),**metrics,'snapshot_atomic':False,
            'routes_run':0,'construction_run':False,'world_history_reconstructed':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--context',type=Path)
    a=p.parse_args()
    try:
        op=Operator(**({'context':a.context} if a.context else {}));r=compare(op.client(),json.loads(a.input.read_text(encoding='utf-8-sig')))
    except Exception as exc:r={'status':'error','error':str(exc)[:400]}
    print(json.dumps(r,separators=(',',':')));return 0 if r['status']=='ok' else 1


if __name__=='__main__':raise SystemExit(main())
