-- Optional offline Lua fixture: M.run(actual module text), never inside TPF3.
local M={}
function M.run(source)
 local function clone(v) if type(v)~='table' then return v end;local r={};for k,x in pairs(v) do r[k]=clone(x) end;return r end
 local C={BASE_EDGE=1,EDGE_OBJECT=2,PLAYER_OWNED=3,SIGNAL_LIST=4}
 local E={RoadType={TRACK=1},EdgeObjectType={SIGNAL=2}}
 local edges,objects,revisions,players={}, {}, {}, {};local accepted=true
 local function reset()
  edges={[1]={node0=10,node1=11,roadType=1,roadTemplate='track',roadStyle='style',type=1,typeIndex=0,
   position0={x=0,y=0,z=2},position1={x=100,y=0,z=2},tangent0={x=100,y=0,z=0},tangent1={x=100,y=0,z=0},
   objects={{90,2},{91,2},{92,5}}}}
  objects={[90]={edgeObjectConstruction='signal',param=.2,params={},signal=true,edge=1,reversed=false},
   [91]={edgeObjectConstruction='signal',param=.8,params={oneWay=true},signal=true,edge=1,reversed=true},
   [92]={edgeObjectConstruction='other',param=.4,params={seed=1}}}
  revisions={};players={[1]=7};accepted=true
 end
 reset()
 local function xyz(v) return {v.x,v.y,v.z} end
 local function comp(x,t)
  if t==C.BASE_EDGE then return edges[x] elseif t==C.EDGE_OBJECT then return objects[x]
  elseif t==C.SIGNAL_LIST then return objects[x] and objects[x].signal and {} or nil
  elseif t==C.PLAYER_OWNED then return players[x] and {player=players[x]} or nil end
 end
 local function rev(x) return {revisions[x] or 1,2,3} end
 local function fresh(x,r) assert(r[1]==rev(x)[1] and r[2]==2 and r[3]==3,'stale_identity') end
 local function signals(x) local o=assert(objects[x]);return {lanes={{index=0,edge_index=0,edge=o.edge,reversed=o.reversed,type='signal'}}} end
 local function snapshot(x)
  local e=assert(edges[x]);return {id=x,node0=e.node0,node1=e.node1,road_type='TRACK',
   p0=xyz(e.position0),p1=xyz(e.position1),t0=xyz(e.tangent0),t1=xyz(e.tangent1),template=e.roadTemplate,style=e.roadStyle,
   node_positions={xyz(e.position0),xyz(e.position1)},structure={classification='NORMAL',type_index=e.typeIndex,resource_name=''}}
 end
 local function ownership(x) return players[x] and {present=true,player=players[x]} or {present=false} end
 local api={type={ComponentType=C,enum=E},engine={system={streetConnectorSystem={getConstructionEntityForEdge=function() return 0 end}},util={getPlayer=function() return 7 end}}}
 api.type.SimpleProposal={new=function() return {streetProposal={}} end};api.type.Context={new=function() return {} end}
 api.type.SegmentAndEntity={new=function() return setmetatable({},{__newindex=function(t,k,v) rawset(t,k,k=='comp' and clone(v) or v) end}) end}
 api.engine.util.proposal={makeProposalData=function() return {errorState={critical=not accepted,messages={}}} end}
 api.cmd={makeWorldBuildProposalCmd=function(p) return p end}
 local env=setmetatable({api=api},{__index=_G});local module=assert(load(source,'exact signal removal','t',env))().new(comp,rev,fresh,xyz,signals,snapshot,ownership)
 local function setup()
  local s={session='test'};local root={};local state={get=function() return root end,set=function(_,v) root=v end}
  local e=snapshot(1);e.revision=rev(1)
  return {session='test',input_hash=string.rep('a',64),edge_snapshot=e,signals={{id=90,revision=rev(90)}}},s,state
 end
 local function fails(fn,pattern) local ok,e=pcall(fn);assert(not ok and tostring(e):find(pattern,1,true),tostring(e)) end
 local function built(command)
  local p=command.streetProposal;assert(#p.edgesToRemove==1 and #p.edgesToAdd==1 and #p.edgeObjectsToAdd==0 and #p.edgeObjectsToRemove==1)
  assert(p.edgeObjectsToRemove[1]==90 and #p.edgesToAdd[1].comp.objects==2)
  edges[2]=clone(p.edgesToAdd[1].comp);edges[1]=nil;players[2]=players[1];players[1]=nil
  objects[90]=nil;objects[91].edge=2
  return {proposal={proposal={addedSegments={{entity=2}}}}}
 end
 local p,s,state=setup();local summary=module.prepare(p,s,state,'prepared');assert(summary.accepted and summary.prepared_handle=='prepared' and edges[1] and objects[90])
 local cmd,read=module.command({prepared_handle='prepared',input_hash=p.input_hash},s,state)
 local value=read(built(cmd));assert(value.selected_signals_absent and value.existing_objects_retained and value.functional_signals_verified and value.ownership_verified)
 assert(value.replaced_edge==1 and value.replacement_edge==2 and value.removed_signals[1]==90 and objects[91] and objects[92])
 fails(function() module.command({prepared_handle='prepared',input_hash=p.input_hash},s,state) end,'consumed')
 for _,fault in ipairs({'non_signal','foreign','edge_revision','signal_revision','geometry','node','resource','structure','session'}) do
  reset();p,s,state=setup()
  if fault=='non_signal' then p.signals[1]={id=92,revision=rev(92)}
  elseif fault=='foreign' then table.remove(edges[1].objects,1)
  elseif fault=='edge_revision' then revisions[1]=2
  elseif fault=='signal_revision' then revisions[90]=2
  elseif fault=='geometry' then edges[1].tangent0.y=1
  elseif fault=='node' then edges[1].node0=12
  elseif fault=='resource' then edges[1].roadTemplate='different'
  elseif fault=='structure' then edges[1].typeIndex=1
  else p.session='wrong' end
  assert(not pcall(function() module.prepare(p,s,state,'bad') end),fault);assert(edges[1] and objects[90])
 end
 for _,fault in ipairs({'owner','retained_revision','retained_parameter'}) do
  reset();p,s,state=setup();module.prepare(p,s,state,'prepared')
  if fault=='owner' then players[1]=8 elseif fault=='retained_revision' then revisions[91]=2 else objects[92].param=.5 end
  assert(not pcall(function() module.command({prepared_handle='prepared',input_hash=p.input_hash},s,state) end),fault)
  assert(not s.signal_removal and edges[1] and objects[90])
 end
 for _,fault in ipairs({'left_selected','changed_function','lost_object','changed_parameter','changed_params','changed_owner','changed_geometry'}) do
  reset();p,s,state=setup();module.prepare(p,s,state,'prepared')
  cmd,read=module.command({prepared_handle='prepared',input_hash=p.input_hash},s,state);local r=built(cmd)
  if fault=='left_selected' then objects[90]={signal=true}
  elseif fault=='changed_function' then objects[91].reversed=false
  elseif fault=='lost_object' then objects[92]=nil
  elseif fault=='changed_parameter' then objects[92].param=.7
  elseif fault=='changed_params' then objects[92].params.seed=2
  elseif fault=='changed_owner' then players[2]=8
  else edges[2].tangent0.y=1 end
  assert(not pcall(function() read(r) end),fault);assert(not s.signal_removal)
 end
 reset();p,s,state=setup();accepted=false;assert(not module.prepare(p,s,state,'rejected').accepted and not s.signal_removal)
 reset();p,s,state=setup();module.prepare(p,s,state,'prepared');s.session='changed'
 fails(function() module.command({prepared_handle='prepared',input_hash=p.input_hash},s,state) end,'stale_handle')
 return true
end
return M
