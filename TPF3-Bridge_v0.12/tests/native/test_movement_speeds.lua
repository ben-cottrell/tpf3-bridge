-- Actual native.inspect under a bounded mock engine. No game commands.
local M={}
function M.run(source)
 local C={BASE_EDGE=1,BASE_NODE=2,TRANSPORT_NETWORK=3,CONSTRUCTION=4,BASE_PARALLEL_STRIP=5,BOUNDING_VOLUME=6,MODEL_INSTANCE_LIST=7}
 local E={RoadType={TRACK=1},TransportMode={TRAIN=1}}
 local function point(x) return {x=x,y=0,z=2} end
 local base={node0=10,node1=11,position0=point(0),position1=point(30),tangent0=point(30),tangent1=point(30),roadType=1,roadTemplate=7,roadStyle=8}
 local function movement(train,speed,curve)
  return {transportModes={[1]=train},speedLimit=speed,curveSpeedLimit=curve,conns={{entity=10,index=0},{entity=11,index=1}}}
 end
 local networks={[1]={edges={movement(true,40,20),movement(false,99,99),movement(true,35,0/0)}},[10]={edges={movement(true,30,12)}}}
 local reads=0
 local api={type={ComponentType=C,enum=E},engine={}}
 api.engine.entityExists=function(id) return id==10 or id==11 end
 api.engine.getComponent=function(id,component)
  if component==C.BASE_EDGE and id==1 then return base end
  if component==C.BASE_NODE and (id==10 or id==11) then return {position=point(id)} end
  if component==C.TRANSPORT_NETWORK then reads=reads+1;return networks[id] end
 end
 local native=assert(load(source,'movement speeds under test','t',setmetatable({api=api},{__index=_G})))()
 local plain=native.inspect({edge_ids={1}});assert(reads==0 and plain.edges[1].movement_speeds==nil)
 local result=native.inspect({edge_ids={1},entity_ids={10},movement_speeds=true})
 local track=result.edges[1].movement_speeds;local node=result.entities[1].movement_speeds
 assert(track.available and track.complete and not track.truncated and track.examined_rows==3 and #track.rows==2)
 assert(track.units=='unknown_native_units' and track.entity_kind=='track_edge')
 assert(track.rows[1].network_entity==1 and track.rows[1].movement_index==0 and track.rows[1].speedLimit==40 and track.rows[1].curveSpeedLimit==20)
 assert(track.rows[2].movement_index==2 and track.rows[2].curveSpeedLimit==nil and track.rows[2].curveSpeedLimit_state=='unavailable')
 assert(node.rows[1].network_entity==10 and node.rows[1].entity_kind=='node' and node.rows[1].curveSpeedLimit==12)
 local only=native.inspect({edge_ids={},entity_ids={11},movement_speeds=true})
 assert(not only.entities[1].movement_speeds.available and not only.entities[1].movement_speeds.complete)
 networks[1].edges={};for i=1,70 do networks[1].edges[i]=movement(false,1,1) end
 local bounded=native.inspect({edge_ids={1},movement_speeds=true}).edges[1].movement_speeds
 assert(bounded.examined_rows==64 and bounded.truncated and not bounded.complete)
 for i=1,70 do networks[1].edges[i]=movement(true,1,1) end
 bounded=native.inspect({edge_ids={1},movement_speeds=true}).edges[1].movement_speeds
 assert(#bounded.rows==16 and bounded.truncated and bounded.examined_rows==17)
 networks[1].edges={movement(true,1,1)};for i=1,8 do networks[1].edges[1].conns[i]={entity=i,index=0} end
 local row=native.inspect({edge_ids={1},movement_speeds=true}).edges[1].movement_speeds.rows[1]
 assert(#row.connections==4 and row.connections_truncated)
 assert(not pcall(native.inspect,{edge_ids={1},movement_speeds='yes'}))
 return {passed=true,opt_in=true,exact_identity=true,bounds=true,no_mutation=true}
end
return M
