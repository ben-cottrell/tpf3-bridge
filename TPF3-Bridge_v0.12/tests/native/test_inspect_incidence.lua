-- Executable optional fixture against FULL pif_native.lua, never inside TPF3.
local M={}
function M.run(source)
 local C={BASE_EDGE=1,BASE_NODE=2};local E={RoadType={TRACK=1,STREET=2},BaseEdgeType={NORMAL=0,BRIDGE=1,TUNNEL=2}}
 local function vec(x,y,z) return {x=x,y=y,z=z} end
 local edges={[1]={node0=10,node1=11,roadType=1,type=0,typeIndex=-1,roadTemplate='track',roadStyle='style',position0=vec(0,0,2),position1=vec(20,0,2),tangent0=vec(20,0,0),tangent1=vec(20,0,0)},
  [2]={node0=11,node1=12,roadType=1,type=0,typeIndex=-1,roadTemplate='track',roadStyle='style',position0=vec(20,0,2),position1=vec(40,0,2),tangent0=vec(20,0,0),tangent1=vec(20,0,0)}}
 local nodes={[10]={position=vec(0,0,2)},[11]={position=vec(20,0,2)},[12]={position=vec(40,0,2)}}
 local incident={[10]={1,99},[11]={1,2},[12]={2}};local owners={[11]=42};local reads=0
 local api={type={ComponentType=C,enum=E},engine={system={}},res={}}
 api.engine.getComponent=function(id,kind) assert(edges[id] or nodes[id],'Invalid entity');return kind==C.BASE_EDGE and edges[id] or kind==C.BASE_NODE and nodes[id] or nil end
 api.engine.system.streetSystem={getNodeSegments=function(id) reads=reads+1;return incident[id] end}
 api.engine.system.streetConnectorSystem={getConstructionEntityForNode=function(id) return owners[id] end}
 local native=assert(load(source,'inspect incidence under test','t',setmetatable({api=api},{__index=_G})))()
 local plain=native.inspect({edge_ids={1,2},structures=true});assert(#plain.edges==2 and not plain.endpoint_incidence and reads==0)
 local r=native.inspect({edge_ids={1,2},structures=true,incidence_edge_ids={1,2}})
 local v=r.endpoint_incidence;assert(v.complete and not v.truncated and v.node_count==3 and #v.nodes==3 and reads==3)
 assert(v.nodes[1].node_id==10 and #v.nodes[1].incident_edges==2 and v.nodes[1].incident_edges[2]==99) -- nonrail segment retained
 assert(v.nodes[1].construction_owner=='none' and v.nodes[2].construction_owner==42)
 for i,e in ipairs(r.edges) do assert(e.node0==plain.edges[i].node0 and e.p0[1]==plain.edges[i].p0[1] and e.structure.classification=='NORMAL') end
 reads=0;r=native.inspect({edge_ids={1,2},incidence_edge_ids={2}});assert(reads==2 and r.endpoint_incidence.node_count==2)
 local function fails(p,pattern) local ok,err=pcall(function() native.inspect(p) end);assert(not ok and tostring(err):find(pattern,1,true),tostring(err)) end
 fails({edge_ids={1,2},incidence_edge_ids={}},'subset_bound')
 fails({edge_ids={1,2},incidence_edge_ids={1,1}},'distinct_incidence')
 fails({edge_ids={1,2},incidence_edge_ids={3}},'distinct_incidence')
 fails({edge_ids={1,1},incidence_edge_ids={1}},'duplicate_incidence_inspect')
 incident[10]={99};fails({edge_ids={1},incidence_edge_ids={1}},'TRACK_missing');incident[10]={1,99}
 incident[10]={1,1};fails({edge_ids={1},incidence_edge_ids={1}},'duplicate_native_incidence');incident[10]={1,99}
 incident[10]=setmetatable({},{__len=function() return 17 end,__index=function() error('must_not_iterate_overbound') end})
 fails({edge_ids={1},incidence_edge_ids={1}},'native_incidence_bound') -- cap BEFORE iteration/sort
 assert(not native.inspect({edge_ids={1}}).endpoint_incidence) -- plain read does not touch unsupported incidence
 incident[10]={1,99};owners[11]='unknown';fails({edge_ids={1},incidence_edge_ids={1}},'construction_owner_unavailable')
 owners[11]=nil;reads=0;r=native.inspect({edge_ids={1,2},incidence_edge_ids={1,2}});assert(r.endpoint_incidence.nodes[2].construction_owner=='none' and reads==3)
 return true
end
return M
