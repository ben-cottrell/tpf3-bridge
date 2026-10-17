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
 local seed_mode=false;local seed_wrong_class=false;local seed_wrong_resource=false
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
   if seed_mode then
    incidents[comp.node0]={id};incidents[comp.node1]={id}
    if seed_wrong_class then comp.type=E.BaseEdgeType.BRIDGE end
   end
   table.insert(receipt.addedSegments,1,{entity=id}) -- deliberately reverse native receipt order
  end
  callback({proposal={proposal=receipt}},true)
 end}
 local native=assert(load(source,'native grouped family under test','t',setmetatable({api=api},{__index=_G})))()
 native.inspect=function(p) return {edges=p.edge_ids} end -- avoid unrelated diagnostic APIs; actual readback remains under test
 local root_control,root_parts;local fits=0;local actual_fit=native.fit
 native.fit=function(_,s,id)
  local parts=root_parts or {root_control};fits=fits+1;s.fits[id]={controls=clone(parts)}
  return {pieces=#parts,representation='native_parts',native_dubins_fit_invoked=true}
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
  edges={};nodes={};incidents={};root_parts=nil;root_control={p0={0,0,0},p1={600,60,height},t0={600,0,0},t1={590.88465,104.18891,0},length=603}
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
 -- A grade-C1 reference with curvature changes between tiny native parts.
 -- Shared Z parameters deliberately imply NONZERO derived physical grade jumps.
 local function profile_input(spacing,reverse)
  local p=input(2,1);local direction={1,0};local end_y=(.006666666666666667*91*91+6*.15+4*1.82)/6
  root_parts={
   {p0={0,0,0},p1={3,.03,.0045},t0={3,0,0},t1={3,.06,.009},length=3},
   {p0={3,.03,.0045},p1={6,.09,.0135},t0={3,.06,.009},t1={3,.06,.009},length=3},
   {p0={6,.09,.0135},p1={9,.15,.0225},t0={3,.06,.009},t1={3,.06,.009},length=3},
   {p0={9,.15,.0225},p1={100,end_y,1},t0={91,1.82,.273},t1={91,0,0},length=91}}
  for i,g in ipairs(p.groups) do g.region={min={-20,-30,-5},max={140,60,5}} end
  p.groups[1].source=stub(10,{0,0,0},direction,true);p.groups[1].target=stub(11,{100,end_y,1},direction,false)
  local a,b={0,spacing,0},{100,end_y+spacing,1};local travel=direction
  if reverse then a,b=b,a;travel={-1,0} end
  p.groups[2].source=stub(20,a,travel,true);p.groups[2].target=stub(21,b,travel,false)
  p.groups[2].normal_offset_from={group_index=1,spacing=spacing,reverse=reverse};return p
 end
 local function realised(spacing,reverse)
  local p=profile_input(spacing,reverse);local ready,s,state=run(p);assert(ready.status=='ok')
  local record=s.prepared_structures.family;local f=record.groups[2].fitted
  assert(f.normal_offset_join_contract=='shared_reference_parameter' and not record.groups[1].fitted.normal_offset_join_contract)
  succeed=true;local result
  native.structured_chain({execute=true,prepared_request='family'},s,state,'graded_parts',function(_,status,value) result={status=status,result=value} end)
  assert(result.status=='ok' and not s.mutationPending,tostring(result.result.error))
  local rb=result.result.groups[2].readback
  assert(rb.max_join_grade_gap>1e-6 and rb.prepared_max_join_grade_gap>1e-6 and rb.max_signed_join_grade_residual<=1e-6)
  assert(rb.join_grade_contract=='shared_reference_parameter');return f
 end
 for _,spacing in ipairs({d,-d}) do for _,reverse in ipairs({false,true}) do realised(spacing,reverse) end end
 local function check_failure(f,pattern)
  local ok,why=pcall(native.readback,f);assert(not ok and tostring(why):find(pattern,1,true),tostring(why))
 end
 local f=realised(d,false);f.normal_offset_join_contract=nil;check_failure(f,'realised_vertical_profile_failed') -- ordinary zero gate remains
 f=realised(d,false)
 local left,right=edges[f.ids[1]],edges[f.ids[2]]
 local function grade(t) return t.z/math.sqrt(t.x*t.x+t.y*t.y) end
 local before,after=grade(left.tangent1),grade(right.tangent0)
 local flipped=(2*after-before)*math.sqrt(left.tangent1.x^2+left.tangent1.y^2)
 assert(math.abs(flipped-left.tangent1.z)<.001);left.tangent1.z=flipped
 check_failure(f,'realised_vertical_profile_failed') -- SAME absolute max, wrong SIGN
 f=realised(d,false);left,right=edges[f.ids[1]],edges[f.ids[2]]
 local delta=grade(left.tangent1)-grade(right.tangent0)
 right.tangent0.z=right.tangent0.z+delta*math.sqrt(right.tangent0.x^2+right.tangent0.y^2)
 right.tangent1.z=right.tangent1.z+delta*math.sqrt(right.tangent1.x^2+right.tangent1.y^2)
 check_failure(f,'realised_vertical_profile_failed') -- moved a jump to another join
 f=realised(d,false);edges[f.ids[1]].position1.z=edges[f.ids[1]].position1.z+.002
 check_failure(f,'realised_controls_differ')
 f=realised(d,false);f.max_grade=1e-6;check_failure(f,'realised_sampled_grade_exceeds_limit')
 f=realised(d,false);f.min_radius=100000;check_failure(f,'realised_sampled_radius_below_limit')
 f=realised(d,false);f.end_grade=.01;check_failure(f,'realised_endpoint_grade_failed')
 f=realised(d,false);edges[f.ids[2]].node0=999;check_failure(f,'actual_connection_missing')
 local spoof=profile_input(d,false);spoof.normal_offset_join_contract='shared_reference_parameter';fails(spoof,'adapter_only')
 spoof=profile_input(d,false);spoof.groups[2].normal_offset_join_contract='shared_reference_parameter';fails(spoof,'unsupported')
 local ok,why=pcall(actual_fit,{normal_offset_join_contract='shared_reference_parameter'});assert(not ok and tostring(why):find('adapter_only',1,true))
 ok,why=pcall(native.verify_interior,{fit={normal_offset_join_contract='shared_reference_parameter'}});assert(not ok and tostring(why):find('adapter_only',1,true))
 -- Actual freestanding preparation and committed checks, same one-span path.
 -- Mock inspect supplies component facts; production assertions remain active.
 seed_mode=true;resource.roadType=E.RoadType.TRACK;corrupt_structure=false;reject=false;succeed=true
 native.inspect=function(p)
  local rows={}
  for _,id in ipairs(p.edge_ids) do
   local e=edges[id];local function a(v) return {v.x,v.y,v.z} end
   rows[#rows+1]={id=id,node0=e.node0,node1=e.node1,p0=a(e.position0),p1=a(e.position1),
    t0=a(e.tangent0),t1=a(e.tangent1),road_type='TRACK',template='track',style='style',
    structure={classification=e.type==E.BaseEdgeType.TUNNEL and 'TUNNEL' or 'BRIDGE',
     resource_name=seed_wrong_resource and 'wrong.resource' or 'observed'}}
  end
  return {edges=rows}
 end
 for _,fault in ipairs({'none','classification','resource'}) do
  edges={};nodes={};incidents={};networks={};seed_wrong_class=false;seed_wrong_resource=false
  local p={prepare=true,new_alignment=true,freestanding=true,track={template='track',style='style'},
   source={position={0,0,0},travel_direction={1,0},grade=.01},
   target={position={5,0,.05},travel_direction={1,0},grade=.01},
   guides={},structures={{classification='TUNNEL',resource_name='observed'}},
   representation='endpoint_cubic',radius=0,handle_scale=1,
   vertical={max_grade=.04},region={min={-1,-1,-1},max={6,1,1}}}
  local response,s,state=run(p);assert(response.status=='ok')
  local record=s.prepared_structures.family
  assert(record.freestanding and #record.segments==1 and record.segments[1].structure.classification=='TUNNEL')
  seed_wrong_class=fault=='classification';seed_wrong_resource=fault=='resource'
  local result
  native.structured_chain({execute=true,prepared_request='family'},s,state,'seed-build',function(_,status,value) result={status=status,result=value} end)
  if fault=='none' then assert(result.status=='ok' and result.result.freestanding and #result.result.ordered_edges==1)
  else assert(result.status=='mutation_unverified','wrong committed structure accepted') end
 end
 succeed=false
 return true
end
return M
