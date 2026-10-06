import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser(description='Independent checks of saved structured-junction native evidence.');p.add_argument('--prepared',required=True);p.add_argument('--built',required=True);a=p.parse_args()
prepared=json.loads(Path(a.prepared).read_text(encoding='utf-8'));built=json.loads(Path(a.built).read_text(encoding='utf-8'))
assert prepared['status']==built['status']=='ok';assert prepared['session']==built['session']
pv,bv=prepared['result'],built['result'];assert bv['prepared_request']==pv['prepared_request']
edges={e['id']:e for e in bv['structure_readback']['edges']};order=bv['readback']['ordered_edges'];nodes=bv['readback']['ordered_nodes']
assert len(order)==len(pv['segments']) and len(set(order))==len(order) and len(nodes)==len(order)+1

def value(c,u):
 return [(2*u**3-3*u*u+1)*c['p0'][i]+(u**3-2*u*u+u)*c['t0'][i]+(-2*u**3+3*u*u)*c['p1'][i]+(u**3-u*u)*c['t1'][i] for i in range(3)]
def norm(v):return math.sqrt(sum(x*x for x in v))
for i,(eid,seg) in enumerate(zip(order,pv['segments'])):
 e=edges[eid];assert e['road_type']=='TRACK' and (e['node0'],e['node1'])==(nodes[i],nodes[i+1])
 for k in ['p0','p1','t0','t1']:assert norm([e[k][j]-seg['controls'][k][j] for j in range(3)])<.002
 assert e['structure']['classification']==seg['structure']['classification']
 if e['structure']['classification']!='NORMAL':assert e['structure']['resource_name']==seg['structure']['resource_name']
 # Portal splits preserve their original fitted native cubic at independent samples.
 interval=seg.get('parameter_interval',[0,1]);original=pv['fit_legs'][seg['leg']-1]['controls'][0]
 if 'parameter_interval' in seg:
  for u in [.1,.35,.65,.9]:assert norm([x-y for x,y in zip(value(seg['controls'],u),value(original,interval[0]+u*(interval[1]-interval[0])))])<.002
assert nodes[0]==bv['junction_nodes'][0] and nodes[-1]==bv['junction_nodes'][1]
for route in bv['through_after']+[bv['crossover_after']]:
 assert route['requested_route_verified'] and route['transport_continuous'] and not route['truncated']
 for previous,current in zip(route['path'],route['path'][1:]):assert previous['to']==current['from']
assert bv['prepared_geometry_reused'] and not bv['geometry_refitted']
print(json.dumps({'status':'passed','native_branch_edges':order,'junction_nodes':nodes[0::len(nodes)-1],'route_checks':len(bv['through_after'])+1,'portal_subdivision_preserves_shape':True,'scope':'saved native geometry/identity/structure/path evidence; no train traversal proof'}))
