-- Actual grouped preparation with independent analytic test doubles. No game calls.
-- M.run(full pif_native.lua source) requires an already available Lua runtime.
local M={}
function M.run(source)
 local function clone(v) if type(v)~='table' then return v end;local r={};for k,x in pairs(v) do r[k]=clone(x) end;return r end
 local function vec(x,y,z) return {x=x,y=y,z=z} end
 local function hermite(p0,p1,t0,t1,u)
  return (2*u^3-3*u^2+1)*p0+(u^3-2*u^2+u)*t0+(-2*u^3+3*u^2)*p1+(u^3-u^2)*t1,
   (6*u^2-6*u)*p0+(3*u^2-4*u+1)*t0+(-6*u^2+6*u)*p1+(3*u^2-2*u)*t1,
   (12*u-6)*p0+(6*u-4)*t0+(-12*u+6)*p1+(6*u-2)*t1
 end
 local function calculate(g,u)
  local spline=g.type==2 and g.cubicOffsetSpline or g.cubicSpline
  local x,dx,ddx=hermite(spline.pos[1].x,spline.pos[2].x,spline.tangent[1].x,spline.tangent[2].x,u)
  local y,dy,ddy=hermite(spline.pos[1].y,spline.pos[2].y,spline.tangent[1].y,spline.tangent[2].y,u)
  if g.type==2 then
   local length=math.sqrt(dx*dx+dy*dy);local dot=dx*ddx+dy*ddy;local spacing=spline.offset
   x=x-spacing*dy/length;y=y+spacing*dx/length
   dx,dy=dx+spacing*(-ddy/length+dy*dot/length^3),dy+spacing*(ddx/length-dx*dot/length^3)
  end
  local z,dz=hermite(g.height.x,g.height.y,g.tangent.x,g.tangent.y,u)
  return {vec(x,y,z),vec(dx,dy,dz)}
 end
 local C={BASE_EDGE=1,BASE_NODE=2,TRANSPORT_NETWORK=3};local E={RoadType={TRACK=1},BaseEdgeType={NORMAL=1,BRIDGE=2,TUNNEL=3},TransportMode={TRAIN=1,ELECTRIC_TRAIN=2}}
 local api={type={enum=E,ComponentType=C,Vec2f={new=vec},Vec3f={new=vec}},engine={util={transport={calcPositionAndDirection=calculate}}},res={}}
 api.type.EdgeGeometry={Type={CUBIC_SPLINE=1,CUBIC_OFFSET_SPLINE=2,ARC=3,STRAIGHT=4},CubicSpline={new=function() return {} end},CubicOffsetSpline={new=function() return {} end},
  new=function() local g={};g.calcPos=function(_,u) return calculate(g,u) end;return g end}
 api.type.SimpleProposal={new=function() return {streetProposal={}} end}
 api.type.SegmentAndEntity={new=function() return {comp={}} end};api.type.NodeAndEntity={new=function() return {comp={}} end}
 local edges,nodes,incidents,networks={}, {}, {}, {};local d=5;local reject=false;local submissions=0;local evaluated;local succeed=false;local corrupt_structure=false
 local resource={trackDistance=d,laneConfigs={{}},streetStyle='style'}
 api.res.streetTemplateRep={find=function() return 1 end,get=function() return resource end,findAndGet=function() return resource end}
 for _,name in ipairs({'bridgeTypeRep','tunnelTypeRep'}) do api.res[name]={find=function() return 1 end,getName=function() return 'observed' end,get=function() return {} end} end
 api.engine.getComponent=function(id,c) return c==C.BASE_EDGE and edges[id] or c==C.BASE_NODE and nodes[id] or c==C.TRANSPORT_NETWORK and networks[id] or nil end
 api.engine.system={streetSystem={getNodeSegments=function(id) return incidents[id] end},streetConnectorSystem={getConstructionEntityForNode=function() return nil end}}
 api.engine.util.proposal={makeProposalData=function(proposal) evaluated=proposal;return {errorState={critical=reject,messages={},warnings={}}} end}
 api.cmd={makeWorldBuildProposalCmd=function(p) return p end,sendCommand=function(proposal,callback)
  submissions=submissions+1;if not succeed then callback({},false);return end
  local mapping={};local receipt={addedSegments={},addedNodes={},removedSegments={},removedNodes={}}
  for i,row in ipairs(proposal.streetProposal.nodesToAdd) do
   local id=10000+i;mapping[row.entity]=id;nodes[id]=clone(row.comp);receipt.addedNodes[#receipt.addedNodes+1]={entity=id}
  end
  for i,row in ipairs(proposal.streetProposal.edgesToAdd) do
   local id=20000+i;local comp=clone(row.comp);comp.node0=mapping[comp.node0] or comp.node0;comp.node1=mapping[comp.node1] or comp.node1
   edges[id]=comp
   local g=api.type.EdgeGeometry.new();g.type=1;g.cubicSpline={pos={comp.position0,comp.position1},tangent={comp.tangent0,comp.tangent1}}
   g.height=vec(comp.position0.z,comp.position1.z);g.tangent=vec(comp.tangent0.z,comp.tangent1.z)
   networks[id]={edges={{transportModes={[1]=true},geometry=g}}}
   if corrupt_structure then comp.type=E.BaseEdgeType.TUNNEL end
   table.insert(receipt.addedSegments,1,{entity=id}) -- deliberately reverse native receipt order
  end
  callback({proposal={proposal=receipt}},true)
 end}
 local native=assert(load(source,'native grouped family under test','t',setmetatable({api=api},{__index=_G})))()
 native.inspect=function(p) return {edges=p.edge_ids} end -- avoid unrelated diagnostic APIs; actual readback remains under test
 local root_control;local fits=0
 native.fit=function(_,s,id)
  fits=fits+1;s.fits[id]={controls={clone(root_control)}}
  return {pieces=1,representation='native_parts',native_dubins_fit_invoked=true}
 end
 local function stub(id,pos,direction,source_end)
  local delta={10*direction[1],10*direction[2],0};local p0,p1={},{ }
  for k=1,3 do p0[k]=pos[k]-(source_end and delta[k] or 0);p1[k]=pos[k]+(source_end and 0 or delta[k]) end
  local n0,n1=id*2,id*2+1
  edges[id]={node0=n0,node1=n1,position0=vec(table.unpack(p0)),position1=vec(table.unpack(p1)),tangent0=vec(table.unpack(delta)),tangent1=vec(table.unpack(delta)),roadType=1,roadTemplate='track',roadStyle='style'}
  nodes[n0]={position=vec(table.unpack(p0))};nodes[n1]={position=vec(table.unpack(p1))};incidents[n0]={id};incidents[n1]={id}
  local row={id=id,node0=n0,node1=n1,p0=p0,p1=p1,t0=delta,t1=delta,template='track',style='style'}
  return {edge_id=id,node_id=source_end and n1 or n0,edge_snapshot=row}
 end
 local function input(count,height,kind)
  edges={};nodes={};incidents={};root_control={p0={0,0,0},p1={600,60,height},t0={600,0,0},t1={590.88465,104.18891,0},length=603}
  local angle=math.atan(root_control.t1[2],root_control.t1[1]);local enddir={math.cos(angle),math.sin(angle)}
  local p={prepare=true,groups={}};local region={min={-20,-30,-5},max={640,110,20}}
  for i=1,count do
   local spacing=(i-1)*d
   local a={0,spacing,0};local b={600-spacing*enddir[2],60+spacing*enddir[1],height}
   local g={new_alignment=true,source=stub(i*10,a,{1,0},true),target=stub(i*10+1,b,enddir,false),guides={},region=region,vertical={max_grade=.025},radius=0}
   if i==1 then g.representation='native_parts';g.structures={{classification=kind or 'NORMAL',resource_name=kind and 'observed' or nil}}
   else g.normal_offset_from={group_index=1,spacing=spacing,reverse=false} end
   p.groups[i]=g
  end
  return p
 end
 local function run(p)
  local s={fits={}};local state={get=function() return {} end,set=function() end};local response
  fits=0;native.structured_chain(p,s,state,'family',function(_,status,value) response={status=status,result=value} end)
  return response,s,state
 end
 local function fails(p,text)
  local ok,why=pcall(run,p);assert(not ok and tostring(why):find(text,1,true),tostring(why))
 end
 for _,count in ipairs({2,4}) do for _,height in ipairs({0,6}) do for _,kind in ipairs({'NORMAL','BRIDGE','TUNNEL'}) do
  local selected_kind;if kind~='NORMAL' then selected_kind=kind end
  local p=input(count,height,selected_kind);local response,s=run(p)
  assert(response.status=='ok' and fits==1 and #response.result.groups==count and #response.result.segments<=20)
  for _,segment in ipairs(evaluated.streetProposal.edgesToAdd) do assert(segment.comp.distance==d and segment.comp.type==E.BaseEdgeType[kind]) end
  for i=2,count do
   local legs=response.result.groups[i].fit_legs;assert(legs[1].reference_group==1 and legs[1].structure_inherited_from_reference)
   assert(legs[1].sampled_conversion_XY_error<=.1 and response.result.groups[i].shared_track_distance==d)
  end
  assert(submissions==0)
 end end end
 local p=input(2,6);p.groups[2].normal_offset_from.group_index=2;fails(p,'earlier_member')
 p=input(2,6);p.groups[2].normal_offset_from.spacing=7;fails(p,'native_spacing')
 p=input(2,6);p.groups[2].structures={{classification='NORMAL'}};fails(p,'inherited')
 p=input(2,6);p.groups[2].target.edge_snapshot.p0[1]=0;fails(p,'stale_attachment')
 p=input(2,6);incidents[p.groups[2].source.node_id]={20,999};fails(p,'endpoint_not_free')
 p=input(2,6);edges[20].position1.y=6;p.groups[2].source.edge_snapshot.p1[2]=6;nodes[41].position.y=6
 fails(p,'boundary_position_incompatible')
 p=input(2,6);reject=true;local rejected=run(p);assert(rejected.status=='no_accepted_candidate' and submissions==0);reject=false
 -- Revalidation is immediately before submission, not just at preparation.
 for _,change in ipairs({function() edges[20].position1.y=99 end,function() incidents[41]={20,999} end,function() resource.trackDistance=6 end}) do
  p=input(2,6);local response,s,state=run(p);local before=submissions;change()
  local ok=pcall(native.structured_chain,{execute=true,prepared_request='family'},s,state,'stale',function() end)
  assert(not ok and submissions==before);resource.trackDistance=d
 end
 -- Mixed structures subdivide the reference and inherit in order on all roads.
 p=input(2,6);p.groups[1].structures={{spans={{classification='NORMAL',until_u=.3},{classification='BRIDGE',resource_name='observed',until_u=.7},{classification='NORMAL',until_u=1}}}}
 local response,s,state=run(p);local group=s.prepared_structures.family.groups[2];local seen_bridge=false;local returned_normal=false
 for _,segment in ipairs(group.segments) do
  if segment.structure.classification=='BRIDGE' then assert(not returned_normal);seen_bridge=true
  elseif seen_bridge then returned_normal=true end
 end
 assert(seen_bridge and returned_normal)
 succeed=true;local last
 native.structured_chain({execute=true,prepared_request='family'},s,state,'success',function(_,status,value) last={status=status,result=value} end)
 assert(last.status=='ok' and s.mutationPending==nil and #last.result.groups==2)
 for i,row in ipairs(last.result.groups) do
  local ids=row.readback.ordered_edges;assert(edges[ids[1]].node0==p.groups[i].source.node_id and edges[ids[#ids]].node1==p.groups[i].target.node_id)
 end
 p=input(2,6);response,s,state=run(p);corrupt_structure=true
 native.structured_chain({execute=true,prepared_request='family'},s,state,'wrong_structure',function(_,status,value) last={status=status,result=value} end)
 assert(last.status=='mutation_unverified' and s.mutationPending=='wrong_structure');corrupt_structure=false;succeed=false
 p=input(2,6);local response,s,state=run(p)
 local before=submissions;native.structured_chain({execute=true,prepared_request='family'},s,state,'execute',function(_,status,value) last={status=status,result=value} end)
 assert(last.status=='mutation_unverified' and submissions==before+1 and s.mutationPending=='execute')
 local ok=pcall(native.structured_chain,{execute=true,prepared_request='family'},s,state,'retry',function() end)
 assert(not ok and submissions==before+1)
 return true
end
return M
