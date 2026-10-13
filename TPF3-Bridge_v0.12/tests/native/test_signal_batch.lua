-- Run M.run(actual module source) under an available Lua runtime, never in game.
local M={}
function M.run(source)
 local function clone(v) if type(v)~='table' then return v end;local r={};for k,x in pairs(v) do r[k]=clone(x) end;return r end
 local C={BASE_EDGE=1,EDGE_OBJECT=2,PLAYER_OWNED=3,SIGNAL_LIST=4}
 local E={RoadType={TRACK=1},EdgeObjectType={SIGNAL=2}}
 local edges,objects={},{};local revisions={};local incidence={};local owner;local critical=false
 local function geometry(x,n0,n1,reverse)
  local e={node0=n0,node1=n1,roadType=1,roadTemplate='track',roadStyle='style',type=1,typeIndex=0,objects={}}
  local a,b=reverse and 800 or 0,reverse and 400 or 400
  e.position0={x=a,y=0,z=2};e.position1={x=b,y=0,z=2}
  e.tangent0={x=b-a,y=0,z=0};e.tangent1=clone(e.tangent0);edges[x]=e;return e
 end
 geometry(1,10,11,false);geometry(2,12,11,true)
 edges[1].objects={{90,5}};objects[90]={edgeObjectConstruction='retained',param=.1}
 objects[99]={edgeObjectConstruction='signal'}
 incidence[10]={1};incidence[11]={1,2};incidence[12]={2}
 local api={type={ComponentType=C,enum=E,Signal={Type={ONE_WAY_SIGNAL=1,SIGNAL=2}}},engine={util={getPlayer=function() return 7 end}}}
 local function comp(x,t) if t==C.BASE_EDGE then return edges[x] elseif t==C.EDGE_OBJECT then return objects[x] end end
 local function rev(x) return {revisions[x] or 1,2,3} end
 local function fresh(x,r) assert(rev(x)[1]==r[1],'stale_operating_identity') end
 local function xyz(v) return {v.x,v.y,v.z} end
 local signal_rows={}
 local function signals(x) return assert(signal_rows[x],'missing signal') end
 local function seed(x) assert(x==99,'explicit seed');return {id=99,revision=rev(99),resource='signal'} end
 api.engine.system={streetConnectorSystem={getConstructionEntityForEdge=function() return owner end,getConstructionEntityForNode=function() return owner end},
  streetSystem={getNodeTrackSegments=function(x) return incidence[x] end,getNodeSegments=function(x) return incidence[x] end}}
 api.type.SegmentAndEntity={new=function() return setmetatable({},{__newindex=function(t,k,v) rawset(t,k,k=='comp' and clone(v) or v) end}) end}
 api.type.SimpleStreetProposal={EdgeObject={new=function() return {} end}}
 api.type.SimpleProposal={new=function() return {streetProposal={}} end};api.type.Context={new=function() return {} end}
 api.engine.util.proposal={makeProposalData=function() return {errorState={critical=critical,messages=critical and {'rejected'} or {}}} end}
 api.cmd={makeWorldBuildProposalCmd=function(p) return p end}
 local env=setmetatable({api=api},{__index=_G});local module=assert(load(source,'bulk signalling','t',env))();local batch=module.new(comp,rev,fresh,xyz,signals,seed)
 local function snapshot(x) local e=edges[x];return {id=x,node0=e.node0,node1=e.node1,p0=xyz(e.position0),p1=xyz(e.position1),t0=xyz(e.tangent0),t1=xyz(e.tangent1),template='track',style='style'} end
 local input={edges={snapshot(1),snapshot(2)},seed_id=99,start_node=10,input_hash=string.rep('a',64),placements={
  {edge_id=1,parameter=.3,forward=true,one_way=true,distance=120},
  {edge_id=1,parameter=.8,forward=true,one_way=true,distance=320},
  {edge_id=2,parameter=.6,forward=false,one_way=true,distance=560}}}
 local s={session='one'};local root={pifLive=s};local state={get=function() return root end,set=function(_,v) root=v end}
 local function fails(fn,text) local ok,why=pcall(fn);assert(not ok and tostring(why):find(text,1,true),tostring(why)) end
 critical=true;assert(not batch.prepare(input,s,state,'reject').accepted and not s.signal_batch);critical=false
 local q=clone(input);q.placements[4]=clone(q.placements[1]);fails(function() batch.prepare(q,s,state,'dup') end,'duplicate_parameter')
 q=clone(input);q.excluded_intervals={{100,150}};fails(function() batch.prepare(q,s,state,'excluded') end,'excluded_interval')
 q=clone(input);q.edges={};for i=1,17 do q.edges[i]=snapshot(1) end;fails(function() batch.prepare(q,s,state,'limit') end,'edge_bound')
 q=clone(input);q.placements={};for i=1,65 do q.placements[i]=input.placements[1] end;fails(function() batch.prepare(q,s,state,'limit') end,'placement_bound')
 for i=1,15 do edges[1].objects[i]={90+i,5};objects[90+i]={param=.01*i,edgeObjectConstruction='retained'} end
 objects[99]={edgeObjectConstruction='signal',param=.09}
 fails(function() batch.prepare(input,s,state,'objects') end,'object_bound');edges[1].objects={{90,5}}
 incidence[11]={1,2,3};fails(function() batch.prepare(input,s,state,'junction') end,'changed_incidence');incidence[11]={1,2}
 owner=20;fails(function() batch.prepare(input,s,state,'station') end,'construction_owned');owner=nil
 assert(batch.prepare(input,s,state,'prepared').prepared_handle=='prepared')
 fails(function() batch.command({prepared_handle='wrong',input_hash=input.input_hash},s,state) end,'mismatched_handle')
 revisions[1]=2;fails(function() batch.command({prepared_handle='prepared',input_hash=input.input_hash},s,state) end,'stale_operating_identity')
 assert(not s.signal_batch);revisions[1]=nil
 batch.prepare(input,s,state,'object-stale');objects[90].param=.2
 fails(function() batch.command({prepared_handle='object-stale',input_hash=input.input_hash},s,state) end,'stale_object_state');objects[90].param=.1
 batch.prepare(input,s,state,'prepared2');s.session='other'
 fails(function() batch.command({prepared_handle='prepared2',input_hash=input.input_hash},s,state) end,'mismatched_handle');s.session='one'
 local reordered=clone(input);reordered.placements={input.placements[3],input.placements[1],input.placements[2]}
 batch.prepare(reordered,s,state,'reordered');local ordering=batch.command({prepared_handle='reordered',input_hash=input.input_hash},s,state)
 assert(ordering.streetProposal.edgesToAdd[1].comp.objects[2][1]==-400000000)
 assert(ordering.streetProposal.edgeObjectsToAdd[1].param==.3)
 batch.prepare(input,s,state,'final');local command,read=batch.command({prepared_handle='final',input_hash=input.input_hash},s,state)
 fails(function() batch.command({prepared_handle='final',input_hash=input.input_hash},s,state) end,'consumed')
 assert(#command.streetProposal.edgesToRemove==2 and #command.streetProposal.edgesToAdd==2 and #command.streetProposal.edgeObjectsToAdd==3)
 assert(#command.streetProposal.edgesToAdd[1].comp.objects==3 and #command.streetProposal.edgesToAdd[2].comp.objects==1)
 local segments={}
 for i,segment in ipairs(command.streetProposal.edgesToAdd) do
  local actual=100+i;edges[actual]=clone(segment.comp);segments[#segments+1]={entity=actual}
  local new={};for _,entry in ipairs(edges[actual].objects) do
   if entry[1]>0 then new[#new+1]=entry else
    local index=-entry[1]-400000000+1;local spec=input.placements[index];local ident=1000+index
    new[#new+1]={ident,2};signal_rows[ident]={id=ident,param=spec.parameter,resource='signal',lanes={{edge=actual,reversed=spec.forward,type='1'}}}
   end
  end;edges[actual].objects=new
 end
 local receipt={proposal={proposal={addedSegments={segments[2],segments[1]}}}}
 local result=read(receipt);assert(#result.mapping==2 and #result.placements==3 and result.placements[3].travel_forward==false)
 assert(result.existing_objects_retained and result.track_geometry_verified and result.functional_signals_verified)
 local retained=edges[101].objects[1];table.remove(edges[101].objects,1)
 fails(function() read(receipt) end,'existing_object_removed');table.insert(edges[101].objects,1,retained)
 signal_rows[1001].lanes[1].reversed=false;fails(function() read(receipt) end,'direction_mismatch');signal_rows[1001].lanes[1].reversed=true
 edges[101].position0.x=5;fails(function() read(receipt) end,'geometry_changed')
 return true
end
return M
