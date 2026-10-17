-- Actual route implementation with signal-split TRAIN rows; no game calls.
-- Lua runtime is unavailable in this workspace; run via the existing harness.
local M={}
function M.run(source)
 local function vec(x,y,z)return {x=x,y=y,z=z or 0}end
 local function conn(entity,index)return {entity=entity,index=index or 0}end
 local function row(a,b,x0,x1)
  return {conns={a,b},transportModes={[1]=true},forwardOnly=false,
   geometry={p0=vec(x0,0),p1=vec(x1,0),length=x1-x0}}
 end
 local bases={
  [10]={roadType="TRACK",node0=1,node1=2,position0=vec(0,0),position1=vec(20,0),tangent0=vec(20,0),tangent1=vec(20,0)},
  [20]={roadType="TRACK",node0=2,node1=4,position0=vec(20,0),position1=vec(40,0),tangent0=vec(20,0),tangent1=vec(20,0)}}
 local positions={[1]=vec(0,0),[2]=vec(20,0),[4]=vec(40,0)}
 local networks={
  [10]={edges={row(conn(1),conn(10),0,10),row(conn(10),conn(2),10,20)}},
  [20]={edges={row(conn(2),conn(4),20,40)}}}
 local forward={{ {entity=10,index=0},true },{ {entity=10,index=1},true },{ {entity=20,index=0},true }}
 local backward={{ {entity=20,index=0},false },{ {entity=10,index=1},false },{ {entity=10,index=0},false }}
 local path=forward
 local api={type={enum={RoadType={TRACK="TRACK"},TransportMode={TRAIN=1}},
  ComponentType={BASE_EDGE="base",BASE_NODE="node",TRANSPORT_NETWORK="network"}},engine={
  getComponent=function(id,kind)
   if kind=="base" then return bases[id] elseif kind=="network" then return networks[id]
   elseif kind=="node" and positions[id] then return {position=positions[id]} end
  end,
  system={streetSystem={getNodeSegments=function()return {10,20}end}},
  util={transport={calcPositionAndDirection=function(g,u)
   return {vec(g.p0.x+(g.p1.x-g.p0.x)*u,0),vec(g.p1.x-g.p0.x,0)}
  end},pathfinding={findPathNodeToNode=function()return path end}}}}
 local env=setmetatable({api=api},{__index=_G})
 local native=assert(load(source,"native signal route under test","t",env))()
 local p={source_edge=10,source_node=1,target_edge=20,target_node=4,mode="TRAIN",max_length=100,required_edges={10,20}}
 local out=native.route(p);assert(out.requested_route_verified and out.source.transport_edge.index==0)
 path=backward
 local reverse={source_edge=20,source_node=4,target_edge=10,target_node=1,mode="TRAIN",max_length=100,required_edges={20,10}}
 assert(native.route(reverse).requested_route_verified,"bidirectional signal reverse access rejected")
 networks[10].edges[1].forwardOnly=true
 assert(not native.route(reverse).requested_route_verified,"one-way reverse path accepted")
 networks[10].edges[1].forwardOnly=false;path=forward
 local original=networks[10].edges[2]
 networks[10].edges[2]=row(conn(1),conn(2),0,20)
 local ok,err=pcall(native.route,p);assert(not ok and tostring(err):find("ambiguous_rail_endpoint_lane",1,true))
 networks[10].edges[2]=original
 networks[10].edges[1].geometry.p0=vec(1,0)
 ok,err=pcall(native.route,p);assert(not ok and tostring(err):find("transport_orientation_unestablished",1,true))
 networks[10].edges[1].geometry.p0=vec(0,0)
 -- The physicalnode1 endpoint chooses the last native movement, notrow0.
 local endpoint={source_edge=10,source_node=2,target_edge=20,target_node=4,mode="TRAIN",max_length=100,required_edges={10,20}}
 path={{{entity=10,index=1},false},{{entity=20,index=0},true}}
 out=native.route(endpoint);assert(out.source.transport_edge.index==1)
 -- This artificial path is disconnected; selecting a row never relaxes that guard.
 assert(not out.requested_route_verified)
 return {passed=true,signal_split_endpoint_selection=true,bidirectional_access=true,
  ambiguity_orientation_and_direction_guards_retained=true,no_native_calls=true}
end
return M
