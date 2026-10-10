-- Bounded native operating evidence. Routing, signalling and motion stay native.
local M={}
local stations=ug_require('tpf3_bridge_n01_c04_20261001::/scripts/pif_stations.lua')
local C,E=api.type.ComponentType,api.type["enum"]
local function id(x) assert(type(x)=="number" and x>0 and x%1==0,"exact_entity_id_required");return x end
local function comp(x,t) return api.engine.getComponent(id(x),t) end
local function rev(x) local r=api.engine.getRevision(x);return {r.num[1],r.num[2],r.num[3]} end
local function xyz(v) return {v.x,v.y,v.z} end
local function terminal(t) return {station=t.station,terminal=t.terminal} end
local function named(x) local n=comp(x,C.NAME);return n and n.name or "unnamed" end
local function fresh(x,r)
 assert(type(r)=="table" and #r==3,"revision_required");local actual=rev(x)
 for i=1,3 do assert(actual[i]==r[i],"stale_operating_identity") end
end
local function line(x)
 local l=assert(comp(x,C.LINE),"line_missing");assert(#l.stops<=16,"line_stop_bound")
 local rows={};for _,s in ipairs(l.stops) do
  local alternatives={};assert(#s.alternativeTerminals<=8,"alternative_terminal_bound")
  for _,a in ipairs(s.alternativeTerminals) do alternatives[#alternatives+1]=terminal(a) end
  rows[#rows+1]={station_group=s.stationGroup,station=s.station,terminal=s.terminal,
   alternatives=alternatives,min_wait=s.minWaitingTime,max_wait=s.maxWaitingTime,
   load_mode=tostring(s.loadMode),waypoint_count=#s.waypoints}
 end
 return {id=x,name=named(x),revision=rev(x),stops=rows}
end
local function vehicle(x)
 local t=assert(comp(x,C.TRANSPORT_VEHICLE),"vehicle_missing")
 local row={id=x,name=named(x),revision=rev(x),carrier=tostring(t.carrier),state=tostring(t.state),
  line=t.line,stop_index=t.stopIndex,depot=t.depot,user_stopped=t.userStopped,no_path=t.noPath,
  auto_departure=t.autoDeparture,load_state=tostring(t.loadState),
  arrival_terminal=terminal(t.arrivalStationTerminal),arrival_terminal_locked=t.arrivalStationTerminalLocked,
  waiting_cause="not_inferred",physical_passage="requires_separate_observations"}
 local configuration=t.transportVehicleConfig;local parts={}
 assert(#configuration.vehicles<=8,"vehicle_configuration_read_bound")
 for _,unit in ipairs(configuration.vehicles) do
  local loads={};assert(#unit.part.compartment2loadConfig<=32,"vehicle_load_read_bound")
  for _,load in ipairs(unit.part.compartment2loadConfig) do loads[#loads+1]={index=load.loadConfigIndex,cargo_type_id=load.cargoTypeId} end
  local auto={};for _,v in ipairs(unit.autoLoadConfig) do auto[#auto+1]=v end
  parts[#parts+1]={model_id=unit.part.modelId,reversed=unit.part.reversed,loads=loads,auto_load=auto}
 end
 local groups,names={},{};for _,v in ipairs(configuration.vehicleGroups) do groups[#groups+1]=v end
 for _,v in ipairs(configuration.muFileNames) do names[#names+1]=v end
 row.configuration={parts=parts,groups=groups,mu_file_names=names}
 local m=comp(x,C.MOVE_PATH)
 if m then
  row.position=xyz(api.engine.util.vehicle.getPosition(x));row.direction=xyz(api.engine.util.vehicle.getDirection(x))
  row.speed=api.engine.util.vehicle.getSpeed(x);row.path_state=tostring(m.state);row.blocked=m.blocked
  row.path_index=m.dyn.pathPos.edgeIndex;row.path_parameter=m.dyn.pathPos.pos01
  local e=m.path.edges[row.path_index+1]
  if e then
   local ok,edge=pcall(function() return {entity=e[1].entity,index=e[1].index,forward=e[2]} end)
   if ok then row.current_edge=edge else
    row.current_edge_unavailable="native_path_pair_shape_unestablished"
    row.path_pair_kind=type(e) -- Native userdata cannot be traversed with pairs.
   end
  end
 end
 return row
end
local function signals(x)
 local s=assert(comp(x,C.SIGNAL_LIST),"signal_list_missing");assert(#s.signals<=8,"signal_lane_bound")
 local result={id=x,revision=rev(x),lanes={}};local o=comp(x,C.EDGE_OBJECT)
 if o then result.param=o.param;result.resource=o.edgeObjectConstruction;result.position=xyz(o.transf:getTransl());result.one_way_param=o.params.oneWay end
 for i,v in ipairs(s.signals) do
  result.lanes[#result.lanes+1]={index=i-1,type=tostring(v.type),edge=v.edgePr[1].entity,
   edge_index=v.edgePr[1].index,reversed=v.edgePr[2],animation_state=v.state}
 end
 return result
end
-- API contract reference: installed Auto Signals submit; independent bounded implementation.
local function signal_seed()
 local processed,visited,selected=0,0,nil
 api.engine.forEachEntity(function(x)
  visited=visited+1
  if selected or processed>=100000 then return end
  processed=processed+1
  local ok,value=pcall(function()
   local o=assert(comp(x,C.EDGE_OBJECT));local s=assert(comp(x,C.SIGNAL_LIST))
   assert(#s.signals>=1 and #s.signals<=8)
   local edge_id=s.signals[1].edgePr[1].entity
   local edge=assert(comp(edge_id,C.BASE_EDGE));assert(edge.roadType==E.RoadType.TRACK)
   local attached=false;for _,entry in ipairs(edge.objects) do if entry[1]==x then attached=true end end
   assert(attached and o.edgeObjectConstruction~=nil)
   return {id=x,revision=rev(x),edge=edge_id,resource=o.edgeObjectConstruction}
  end)
  if ok then selected=value end
 end)
 if selected then selected.processed=processed;selected.entity_count=visited;selected.coverage="first_qualified_signal";return selected end
 return {availability=processed<visited and "signal_seed_search_bound_exhausted" or "functional_signal_template_required",
  processed=processed,entity_count=visited,truncated=processed<visited}
end
local function signal_prepare(p)
 assert(type(p.parameter)=="number" and p.parameter==p.parameter and p.parameter>0 and p.parameter<1,"signal_parameter_inside_edge_required")
 assert(type(p.forward)=="boolean" and type(p.one_way)=="boolean","explicit_signal_direction_and_one_way_required")
 fresh(p.edge_id,p.revision)
 local edge=assert(comp(p.edge_id,C.BASE_EDGE),"signal_target_edge_missing")
 assert(edge.roadType==E.RoadType.TRACK,"signal_target_track_required")
 assert(#edge.objects<=15,"signal_target_object_bound")
 local seed=signal_seed();assert(seed.id,seed.availability)
 if p.seed_id then assert(seed.id==p.seed_id,"signal_template_changed");fresh(seed.id,p.seed_revision) end
 for _,entry in ipairs(edge.objects) do
  local s=comp(entry[1],C.SIGNAL_LIST)
  if s then
   local o=comp(entry[1],C.EDGE_OBJECT)
   assert(entry[1]==p.replace_signal_id or not o or math.abs(o.param-p.parameter)>.0001,"signal_already_at_parameter")
  end
 end
 if p.replace_signal_id then
  fresh(p.replace_signal_id,p.replace_signal_revision);local old=signals(p.replace_signal_id);local attached=false
  for _,entry in ipairs(edge.objects) do if entry[1]==p.replace_signal_id then attached=true end end
  assert(attached and math.abs(old.param-p.parameter)<=.0001,'replacement_signal_not_at_exact_attachment')
 end
 return edge,seed,{edge=p.edge_id,revision=rev(p.edge_id),parameter=p.parameter,forward=p.forward,
  one_way=p.one_way,seed=seed,node0=edge.node0,node1=edge.node1,command_submitted=false}
end
local function signal_command(p)
 local edge,seed,summary=signal_prepare(p)
 local before={node0=edge.node0,node1=edge.node1,p0=xyz(edge.position0),p1=xyz(edge.position1),
  t0=xyz(edge.tangent0),t1=xyz(edge.tangent1),template=edge.roadTemplate,style=edge.roadStyle,objects={}}
 local objects={};for _,entry in ipairs(edge.objects) do if entry[1]~=p.replace_signal_id then objects[#objects+1]={entry[1],entry[2]};before.objects[entry[1]]=entry[2] end end
 objects[#objects+1]={-400000000,E.EdgeObjectType.SIGNAL}
 local segment=api.type.SegmentAndEntity.new();segment.entity=-1;segment.type=1;segment.comp=edge
 local owner=comp(p.edge_id,C.PLAYER_OWNED);if owner then segment.playerOwned=owner end
 segment.comp.objects=objects
 local addition=api.type.SimpleStreetProposal.EdgeObject.new()
 -- Public forward is node0->node1 travel, not the native side/orientation bit.
 -- Build40420 isolated TRAIN reads proved left=true permits reverse travel.
 addition.edgeEntity=-1;addition.param=p.parameter;addition.left=not p.forward;addition.oneWay=p.one_way
 addition.model=comp(seed.id,C.EDGE_OBJECT).edgeObjectConstruction -- Keep the actual native resource value.
 addition.playerEntity=api.engine.util.getPlayer()
 local proposal=api.type.SimpleProposal.new()
 proposal.streetProposal.edgesToRemove={p.edge_id};proposal.streetProposal.edgesToAdd={segment}
 proposal.streetProposal.edgeObjectsToAdd={addition};proposal.streetProposal.edgeObjectsToRemove=p.replace_signal_id and {p.replace_signal_id} or {}
 local context=api.type.Context.new();context.player=api.engine.util.getPlayer()
 return api.cmd.makeWorldBuildProposalCmd(proposal,context,false,true),function(r)
  local receipt=r.proposal.proposal;assert(#receipt.addedSegments==1,"signal_replacement_receipt_unresolved")
  local replacement=id(receipt.addedSegments[1].entity);local actual=assert(comp(replacement,C.BASE_EDGE))
  assert(actual.node0==before.node0 and actual.node1==before.node1 and actual.roadTemplate==before.template and actual.roadStyle==before.style,"signal_track_identity_or_resource_changed")
  for field,expected in pairs({position0=before.p0,position1=before.p1,tangent0=before.t0,tangent1=before.t1}) do
   local found=xyz(actual[field]);for i=1,3 do assert(math.abs(found[i]-expected[i])<=.001,"signal_track_geometry_changed") end
  end
  local retained,new={},{}
  assert(#actual.objects<=16,"signal_readback_object_bound")
  for _,entry in ipairs(actual.objects) do
   if before.objects[entry[1]] then assert(entry[2]==before.objects[entry[1]],"signal_retained_object_category_changed");retained[entry[1]]=true
   else new[#new+1]=entry[1] end
  end
  for x in pairs(before.objects) do assert(retained[x],"signal_existing_object_removed") end
  assert(#new==1 and (new[1]~=seed.id or seed.id==p.replace_signal_id),"new_signal_identity_unresolved")
  if seed.id~=p.replace_signal_id then fresh(seed.id,seed.revision) end;local result=signals(new[1])
  assert(result.resource==seed.resource and math.abs(result.param-p.parameter)<=.0001,"signal_resource_or_parameter_mismatch")
  local kind=p.one_way and api.type.Signal.Type.ONE_WAY_SIGNAL or api.type.Signal.Type.SIGNAL
  local lane_ok=false
  for _,lane in ipairs(result.lanes) do
   if lane.edge==replacement and lane.reversed==p.forward and lane.type==tostring(kind) then lane_ok=true end
  end
  assert(lane_ok,"functional_signal_direction_or_type_mismatch")
  return {signal=result,replacement_edge=replacement,replaced_edge=p.edge_id,replaced_signal=p.replace_signal_id,seed=seed.id~=p.replace_signal_id and signals(seed.id) or seed,
   track_geometry_verified=true,existing_objects_retained=true,functional_signal_verified=true,
   travel_forward=p.forward,native_left=not p.forward,directed_route_verified=false,
   game_constructed=true,physical_operation="requires_separate_observation"}
 end
end
local function bounded(ids,limit,read)
 local out={count=#ids,records={},truncated=#ids>limit}
 for i=1,math.min(#ids,limit) do out.records[i]=read(ids[i]) end
 return out
end
local function prepare_vehicle(p)
  fresh(p.depot_id,p.revision);local d=assert(comp(p.depot_id,C.VEHICLE_DEPOT),"depot_missing")
  local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForDepot(p.depot_id)
  local construction=assert(comp(owner,C.CONSTRUCTION),"depot_construction_missing")
  assert(construction.fileName:find("/depots/rail/",1,true),"rail_depot_required")
  assert(type(p.parts)=="table" and #p.parts>=1 and #p.parts<=8,"vehicle_consist_bound")
  local phase="game_clock"
  local prepared_config,summary
  local ok,problem=pcall(function()
  local clock=assert(comp(api.engine.util.getWorld(),C.GAME_TIME),"game_time_identity_unavailable")
  local now=clock.gameTime
  phase="vehicle_config"
  local config=api.type.TransportVehicleConfig.new();local parts,groups,names={}, {}, {}
  local records={}
  for _,spec in ipairs(p.parts) do
   assert(type(spec.resource)=="string" and type(spec.reversed)=="boolean","vehicle_part_required")
   local model_id=api.res.modelRep.find(spec.resource);assert(model_id>=0,"vehicle_model_missing")
   local metadata=api.res.modelRep.get(model_id).metadata;local t=assert(metadata.transportVehicle,"vehicle_metadata_missing")
   assert(t.carrier=="RAIL" or t.carrier==E.Carrier.RAIL,"rail_vehicle_required")
   phase="vehicle_part_constructor"
   local item=api.type.TransportVehiclePart.new();local part=item.part
   phase="vehicle_part_fields"
   part.modelId=model_id;part.reversed=spec.reversed
   local loads,auto,load_records={},{},{};assert(#(t.compartments or {})<=32,"vehicle_compartment_bound")
   phase="vehicle_load_selection:"..spec.resource
   for i,compartment in ipairs(t.compartments or {}) do
    -- Build40408 UI reference uses a real zero-based config and cargo=-1
    -- with autoLoadConfig=true, including legitimate zero-capacity locomotive compartments.
    local choices=compartment.loadConfigs;assert(#choices>=1 and #choices<=32,"vehicle_load_config_bound")
    local load
    for index,choice in ipairs(choices) do
     local cargo=api.engine.util.vehicle.getAllCargoForCargoTypeSet(choice.cargoEntry.cargoTypeSet)
     if #cargo>0 or choice.cargoEntry.capacity==0 then
      if #cargo>0 then assert(type(cargo[1])=="number" and cargo[1]>=0 and cargo[1]%1==0,"vehicle_cargo_identity_invalid") end
      load=api.type.LoadConfig.new();load.loadConfigIndex=index-1;load.cargoTypeId=-1
      load_records[i]={index=index-1,cargo_type_id=-1,capacity=choice.cargoEntry.capacity,auto_load=true};break
     end
    end
    assert(load and load.loadConfigIndex>=0,"vehicle_compatible_load_config_unavailable")
    loads[i]=load;auto[i]=true
   end
   phase="vehicle_load_config"
   part.compartment2loadConfig=loads;part.color=api.type.Vec3f.new(.2,.6,.9)
   phase="vehicle_purchase_time"
   item.part=part;item.purchaseTime=now
   phase="vehicle_maintenance_fields"
   item.maintenanceChange=0;item.maintenanceState=0;item.autoLoadConfig=auto
   parts[#parts+1]=item;groups[#groups+1]=1;names[#names+1]=""
   records[#records+1]={resource=spec.resource,model_id=model_id,reversed=spec.reversed,loads=load_records}
  end
  phase="vehicle_config_fields"
  config.vehicles=parts;config.vehicleGroups=groups;config.muFileNames=names
  prepared_config=config
  summary={config_version="p66_native_ui_auto_load_v2",depot=p.depot_id,depot_revision=rev(p.depot_id),
   parts=records,valid_nonnegative_load_configs=true,command_submitted=false}
  end)
  if not ok then
   local detail=tostring(problem)
   if type(problem)=="table" then
    local rows={};for k,v in pairs(problem) do if #rows>=8 then break end;rows[#rows+1]=tostring(k).."="..tostring(v):sub(1,160) end
    detail=table.concat(rows,"; ")
   end
   error("vehicle_buy_prepare:"..phase..": "..detail:sub(1,600))
  end
  return prepared_config,summary
end
local function depot_prepare(p)
 assert(type(p.resource)=="string" and p.resource:find("/depots/rail/",1,true),"depot_resource_required")
 local resource=api.res.constructionRep.find(p.resource);assert(resource>=0,"construction_resource_missing")
 local desc=api.res.constructionRep.get(resource)
 assert(type(p.template)=="number" and p.template%1==0 and p.template>=0 and p.template<#desc.constructionTemplates,"construction_template_index_invalid")
 assert(type(p.position)=="table" and #p.position==3,"asset_position_required")
 for _,v in ipairs(p.position) do assert(type(v)=="number" and v==v and math.abs(v)<100000,"asset_position_invalid") end
 assert(type(p.angle)=="number" and p.angle==p.angle and math.abs(p.angle)<100,"asset_angle_invalid")
 assert(type(p.name)=="string" and #p.name>0 and #p.name<=80,"asset_name_required")
 local result=api.engine.util.construction.getConstructionResult(p.resource,p.template,p.params or {})
 assert(#result.subconstructions>=1 and #result.subconstructions<=8,"asset_subconstruction_bound")
 local q=api.type.SimpleProposal.new();local c=api.type.SimpleProposal.ConstructionEntity.new()
 c.fileName=p.resource;c.params=result.params;c.name=p.name;c.playerEntity=api.engine.util.getPlayer();c.autoFillSlots=false
 local co,si=math.cos(p.angle),math.sin(p.angle)
 c.transf=api.type.Mat4f.new(api.type.Vec4f.new(co,si,0,0),api.type.Vec4f.new(-si,co,0,0),
  api.type.Vec4f.new(0,0,1,0),api.type.Vec4f.new(p.position[1],p.position[2],p.position[3],1))
 q.constructionsToAdd={c};local ctx=api.type.Context.new();ctx.player=api.engine.util.getPlayer()
 local cmd=api.cmd.makeWorldBuildProposalCmd(q,ctx,false,true)
 local keys={};for k in pairs(result.params) do keys[#keys+1]=tostring(k) end;table.sort(keys)
 local record={resource=p.resource,template=p.template,processed_parameter_keys=keys,construction_count=1,
  command_constructed=true,native_command_submitted=false,game_constructed=false,
  acceptance="command_preparation_only; native construction and attachment not yet demonstrated"}
 if p.diagnose_legacy then
  local ok,err=pcall(api.cmd.makeWorldBuildProposalCmd,q,nil,false,true)
  record.processed_without_context={command_constructed=ok,error=not ok and tostring(err):sub(1,400) or nil}
  c.params=p.params or {};q.constructionsToAdd={c}
  ok,err=pcall(api.cmd.makeWorldBuildProposalCmd,q,ctx,false,true)
  record.raw_with_context={command_constructed=ok,error=not ok and tostring(err):sub(1,400) or nil}
 end
 return cmd,record
end
local function depot_service_path(d,q)
 assert(type(q.required_edges)=="table" and #q.required_edges>=1 and #q.required_edges<=16,"depot_route_edge_bound")
 local base=assert(comp(q.edge,C.BASE_EDGE),"service_track_missing")
 assert(base.roadType==E.RoadType.TRACK and (q.node==base.node0 or q.node==base.node1),"service_not_TRACK_endpoint")
 local network=assert(comp(q.edge,C.TRANSPORT_NETWORK),"service_transport_missing")
 local destination=nil
 for _,row in ipairs(network.edges) do
  if row.transportModes[E.TransportMode.TRAIN]==true then
   assert(not destination and #row.conns==2,"service_transport_ambiguous")
   assert(row.conns[1].entity==base.node0 and row.conns[2].entity==base.node1,"service_transport_identity_mismatch")
   destination=row.conns[q.node==base.node0 and 1 or 2]
  end
 end
 assert(destination and #d.outNodes>=1 and #d.outNodes<=8,"depot_route_attachment_missing")
 -- The API accepts Lua lists of native NodeId values, not a component's
 -- native vector wrapper as the outer query argument.
 local origins={};for _,node in ipairs(d.outNodes) do origins[#origins+1]=node end
 local path=api.engine.util.pathfinding.findPathNodeToNode(origins,{destination},{E.TransportMode.TRAIN})
 assert(type(path)=="table","native_depot_path_contract")
 local out={native_path_found=#path>0,verified=false,path_count=#path,truncated=#path>64,path={},
  destination={entity=destination.entity,index=destination.index},query="findPathNodeToNode",
  train_dispatch="unprobed",native_search_bound=false,read_only=true}
 if #path==0 or out.truncated then return out end
 local function same(a,b) return a.entity==b.entity and a.index==b.index end
 local previous,seen,continuous=nil,{},true
 for i,item in ipairs(path) do
  local eid,forward=item[1],item[2];assert(type(forward)=="boolean","native_depot_path_direction")
  local row=assert(comp(eid.entity,C.TRANSPORT_NETWORK).edges[eid.index+1],"depot_path_row_missing")
  assert(#row.conns==2 and row.transportModes[E.TransportMode.TRAIN]==true,"depot_path_not_train")
  local from,to=row.conns[forward and 1 or 2],row.conns[forward and 2 or 1]
  if previous and not same(previous,from) or row.forwardOnly and not forward then continuous=false end
  if i==1 then
   local matches=false;for _,node in ipairs(d.outNodes) do if same(node,from) then matches=true end end
   out.origin_matches=matches
  end
  local b=comp(eid.entity,C.BASE_EDGE);if b and b.roadType==E.RoadType.TRACK then seen[eid.entity]=true end
  out.path[i]={edge={entity=eid.entity,index=eid.index},forward=forward,
   from={entity=from.entity,index=from.index},to={entity=to.entity,index=to.index}}
  previous=to
 end
 local missing={};for _,eid in ipairs(q.required_edges) do if not seen[id(eid)] then missing[#missing+1]=eid end end
 out.missing_required_edges=missing;out.transport_continuous=continuous;out.destination_matches=same(previous,destination)
 out.verified=out.origin_matches and continuous and out.destination_matches and #missing==0
 return out
end
local function depot_readback(x,p)
 local built=assert(comp(x,C.CONSTRUCTION),"depot_construction_missing")
 assert(built.fileName==p.resource,"depot_resource_readback_mismatch")
 local position=xyz(built.transf:getTransl())
 for i=1,3 do assert(math.abs(position[i]-p.position[i])<=.01,"depot_position_readback_mismatch") end
 assert(#built.depots>=1 and #built.depots<=8 and #built.frozenNodes<=32 and #built.frozenEdges<=32,"depot_readback_bound")
 local depots={}
 for _,entity in ipairs(built.depots) do
  local d=assert(comp(entity,C.VEHICLE_DEPOT),"native_depot_component_missing")
  assert(api.engine.system.streetConnectorSystem.getConstructionEntityForDepot(entity)==x,"depot_construction_identity_mismatch")
  local nodes,exits={},{};assert(#d.inNodes<=8 and #d.outNodes<=8,"depot_node_bound")
  for _,n in ipairs(d.inNodes) do nodes[#nodes+1]={entity=n.entity,index=n.index} end
  for _,n in ipairs(d.outNodes) do exits[#exits+1]={entity=n.entity,index=n.index} end
  depots[#depots+1]={id=entity,revision=rev(entity),in_nodes=nodes,out_nodes=exits,construction=x,
   carrier=d.carrier and tostring(d.carrier) or "unavailable_in_observed_runtime",
   service_route=p.service_target and depot_service_path(d,p.service_target) or nil}
 end
 return {construction={id=x,revision=rev(x),resource=built.fileName,name=named(x),position=position,
   depots=built.depots,frozen_nodes=built.frozenNodes,frozen_edges=built.frozenEdges},depots=depots,
  native_depot_identity_verified=true,game_constructed=true,world_mutated_by_readback=false,
  attachment="requires_exact_native_node_and_route_readback",dispatch="not_demonstrated"}
end
function M.inspect(p)
 local limit=p.limit or 16;assert(type(limit)=="number" and limit%1==0 and limit>=1 and limit<=32,"operating_read_bound")
 local out={game_constructed=false,player=api.engine.util.getPlayer(),save_identity="unknown",load_epoch="adapter_session_only"}
 if p.station_catalogue then return stations.catalogue() end
 if p.station_preparation then local _,r=stations.prepare(p.station_preparation);out.station_preparation=r;return out end
 if p.station_readback then local q=p.station_readback;out.station_readback=stations.readback(id(q.construction_id),q);return out end
 if p.signal_seed then out.signal_seed=signal_seed();return out end
 if p.signal_placement then local _,_,summary=signal_prepare(p.signal_placement);out.signal_placement=summary;return out end
 if p.vehicle_asset_resources then
  assert(#p.vehicle_asset_resources>=1 and #p.vehicle_asset_resources<=8,"selected_vehicle_asset_bound")
  local function entries(values)
   local out={length=#values,kind=type(values),entries={},truncated=false}
   for k,v in pairs(values) do
    if #out.entries>=32 then out.truncated=true;break end
    out.entries[#out.entries+1]={key=tostring(k),value=(type(v)=="number" or type(v)=="string" or type(v)=="boolean") and v or tostring(v)}
   end
   return out
  end
  local records={}
  for _,resource in ipairs(p.vehicle_asset_resources) do
   local model_id=api.res.modelRep.find(resource);assert(model_id>=0,"vehicle_model_missing")
   local t=assert(api.res.modelRep.get(model_id).metadata.transportVehicle,"vehicle_metadata_missing")
   assert(#t.compartments<=8,"selected_vehicle_compartment_bound")
   local row={resource=resource,model_id=model_id,compartment_length=#t.compartments,compartments={}}
   for k,compartment in pairs(t.compartments) do
    assert(#row.compartments<8,"selected_vehicle_compartment_bound")
    local item={key=tostring(k),config_length=#compartment.loadConfigs,configs={}}
    for j,config in pairs(compartment.loadConfigs) do
     assert(#item.configs<8,"selected_vehicle_config_bound")
     local cargo=config.cargoEntry;local set=cargo.cargoTypeSet
     local native=api.engine.util.vehicle.getAllCargoForCargoTypeSet(set)
     item.configs[#item.configs+1]={key=tostring(j),capacity=cargo.capacity,
      set={classes_included=entries(set.cargoClassesIncluded),classes_excluded=entries(set.cargoClassesExcluded),
       types_included=entries(set.cargoTypesIncluded),types_excluded=entries(set.cargoTypesExcluded)},
      compatible_cargo=entries(native)}
    end
    row.compartments[#row.compartments+1]=item
   end
   records[#records+1]=row
  end
  out.vehicle_asset_metadata=records;return out
 end
 if p.vehicle_purchase then
  local _,summary=prepare_vehicle(p.vehicle_purchase);out.vehicle_purchase=summary;return out
 end
 if p.vehicle_assets then
  local records,count={},0
  for k,name in pairs(api.res.modelRep.getAll()) do
   local model=api.res.modelRep.get(k);local m=model.metadata;local t=m.transportVehicle
   if t and (t.carrier=="RAIL" or t.carrier==E.Carrier.RAIL) then
    count=count+1
    if #records<limit then
     local engines={};for _,e in ipairs(m.landVehicle and m.landVehicle.engines or {}) do
      engines[#engines+1]={type=tostring(e.type),power=e.power,tractive_effort=e.tractiveEffort}
     end
     records[#records+1]={model_id=k,resource=name,name=m.description and m.description.name,
      length=api.engine.util.vehicle.getLength(model),engines=engines,compartments=#(t.compartments or {}),
      availability=m.availability and {year_from=m.availability.yearFrom,year_to=m.availability.yearTo},
      top_speed=m.landVehicle and m.landVehicle.topSpeed}
    end
   end
  end
  out.vehicle_assets={count=count,records=records,truncated=count>#records};return out
 end
 if p.asset_geometry then
  local a=p.asset_geometry
  assert(type(a.resource)=="string" and a.resource:find("/depots/rail/",1,true),"depot_geometry_resource_required")
  local resource=api.res.constructionRep.find(a.resource);assert(resource>=0,"construction_resource_missing")
  local desc=api.res.constructionRep.get(resource)
  assert(type(a.template)=="number" and a.template%1==0 and a.template>=0 and a.template<#desc.constructionTemplates,"construction_template_index_invalid")
  local result=api.engine.util.construction.getConstructionResult(a.resource,a.template,a.params or {})
  assert(#result.subconstructions<=8,"asset_subconstruction_bound")
  local rows={}
  for _,sub in ipairs(result.subconstructions) do
   local row={models={},colliders={},model_count=#sub.models,collider_count=#sub.colliders,
    models_truncated=#sub.models>32,colliders_truncated=#sub.colliders>16}
   for i,m in ipairs(sub.models) do
    if i>32 then break end
    local item={resource=m.id,local_translation=xyz(m.transf:getTransl()),tag=m.tag}
    local model=api.res.modelRep.find(m.id)
    if model>=0 then local b=api.res.modelRep.get(model).boundingInfo;item.model_bounds={min=xyz(b.bbMin),max=xyz(b.bbMax)}
    else item.model_bounds="resource_not_resolved" end
    row.models[#row.models+1]=item
   end
   for i,v in ipairs(sub.colliders) do
    if i>16 then break end
    local item={type=tostring(v.type),local_translation=xyz(v.transf:getTransl())}
    if v.type==api.type.Collider.Type.BOX then item.half_extents=xyz(v.box.halfExtents) end
    row.colliders[#row.colliders+1]=item
   end
   rows[#rows+1]=row
  end
  out.asset_geometry={resource=a.resource,template=a.template,subconstructions=rows,
   source="api.engine.util.construction.getConstructionResult",frame="asset_local",
   world_preview="not_performed",attachment_ports="not_exposed_by_inspected_result_contract",buildable_not_demonstrated=true}
  return out
 end
 if p.depot_preparation then
  local _,record=depot_prepare(p.depot_preparation);out.depot_preparation=record;return out
 end
 if p.depot_readback then
  local q=p.depot_readback;out.depot_readback=depot_readback(id(q.construction_id),q);return out
 end
 if p.asset_preview then
  error("asset_world_preview_unavailable: makeProposalData requires Proposal; SimpleProposal conversion not established")
 end
 if p.asset_kind then
  assert(p.asset_kind=="signal" or p.asset_kind=="depot","operating_asset_kind")
  local records={};local count=0
  for k,name in pairs(api.res.constructionRep.getAll()) do
   local match=p.asset_kind=="signal" and name:find("/signal/",1,true) or p.asset_kind=="depot" and name:find("/depots/rail/",1,true)
   if match then count=count+1;if #records<limit then
    local d=api.res.constructionRep.get(k);local params={}
    for _,v in ipairs(d.params) do params[#params+1]={key=v.key,default_index=v.defaultIndex} end
    records[#records+1]={id=k,resource=name,params=params,template_count=#d.constructionTemplates,
     snaps_track=d.edgeObject and d.edgeObject.snapToTrack or false}
   end end
  end
  table.sort(records,function(a,b)return a.resource<b.resource end)
  out.assets={count=count,records=records,truncated=count>#records};return out
 end
 if p.track_ids then
  assert(#p.track_ids>=1 and #p.track_ids<=16,"track_object_read_bound")
  out.tracks=bounded(p.track_ids,limit,function(x)
   local edge=assert(comp(x,C.BASE_EDGE),"base_edge_missing")
   assert(edge.roadType==E.RoadType.TRACK,"confirmed_track_required")
   local objects={};assert(#edge.objects<=16,"edge_object_read_bound")
   for _,entry in ipairs(edge.objects) do
    local object=id(entry[1]);local o=assert(comp(object,C.EDGE_OBJECT),"edge_object_missing")
    local row={id=object,category=tostring(entry[2]),resource=o.edgeObjectConstruction,
     parameter=o.param,position=xyz(o.transf:getTransl()),params=o.params,revision=rev(object)}
    if comp(object,C.SIGNAL_LIST) then row.signal=signals(object) end
    objects[#objects+1]=row
   end
   return {id=x,node0=edge.node0,node1=edge.node1,revision=rev(x),objects=objects}
  end);return out
 end
 if p.vehicle_ids then assert(#p.vehicle_ids>=1 and #p.vehicle_ids<=16,"vehicle_read_bound");out.vehicles=bounded(p.vehicle_ids,limit,vehicle);return out end
 out.lines=bounded(api.engine.system.lineSystem.getLines(),limit,line)
 out.vehicles=bounded(api.engine.util.vehicle.getVehiclesByCarrier(E.Carrier.RAIL),limit,vehicle)
 if p.signal_ids then
  assert(#p.signal_ids<=16,"signal_read_bound");out.signals=bounded(p.signal_ids,limit,signals)
 else out.signals={availability="exact_signal_ids_required",count="unknown",records={},coverage="not_global"} end
 local depot_ok,depot_result=pcall(function() return bounded(p.depot_ids or api.engine.getEntitiesWithComponent(C.VEHICLE_DEPOT),limit,function(x)
  local d=comp(x,C.VEHICLE_DEPOT);local nodes={}
  for _,n in ipairs(d.inNodes) do nodes[#nodes+1]={entity=n.entity,index=n.index} end
  return {id=x,revision=rev(x),carrier=tostring(d.carrier),in_nodes=nodes,
   construction=api.engine.system.streetConnectorSystem.getConstructionEntityForDepot(x)}
 end) end)
 out.depots=depot_ok and depot_result or {availability="unavailable",count="unknown",records={},error=tostring(depot_result):sub(1,240)}
 return out
end
local function checked_stop(s)
 local group=assert(comp(s.station_group,C.STATION_GROUP),"station_group_missing")
 assert(type(s.station)=="number" and s.station%1==0 and s.station>=0 and s.station<#group.stations,"station_index_invalid")
 local station=assert(comp(group.stations[s.station+1],C.STATION),"station_missing")
 assert(type(s.terminal)=="number" and s.terminal%1==0 and s.terminal>=0 and s.terminal<#station.terminals,"terminal_index_invalid")
 return api.type.StationTerminal.new(s.station,s.terminal)
end
local function configuration(p)
 assert(type(p.stops)=="table" and #p.stops>=2 and #p.stops<=8,"service_stop_bound")
 local l=api.type.Line.new();local stops={}
 for _,s in ipairs(p.stops) do
  checked_stop(s);local stop=api.type.Line.Stop.new();stop.stationGroup=s.station_group;stop.station=s.station;stop.terminal=s.terminal
  local alternatives={};local seen={[s.station..":"..s.terminal]=true};assert(#(s.alternatives or {})<=8,"alternative_terminal_bound")
  for _,a in ipairs(s.alternatives or {}) do
   local key=a.station..":"..a.terminal;assert(not seen[key],"duplicate_alternative_terminal");seen[key]=true
   alternatives[#alternatives+1]=checked_stop({station_group=s.station_group,station=a.station,terminal=a.terminal})
  end
  stop.alternativeTerminals=alternatives;stop.loadMode=api.type.Line.LoadMode.LOAD_IF_AVAILABLE
  assert(type(s.min_wait or 0)=="number" and (s.min_wait or 0)>=0 and (s.min_wait or 0)<=120,"waiting_time_bound")
  stop.minWaitingTime=s.min_wait or 0;stop.maxWaitingTime=120;stop.maxAdditionalWaitingTime=0
  stops[#stops+1]=stop
 end
 l.stops=stops;return l
end
local function verified_line(x,p)
 local actual=line(x);assert(#actual.stops==#p.stops,"service_stop_readback_mismatch")
 for i,wanted in ipairs(p.stops) do
  local observed=actual.stops[i]
  assert(observed.station_group==wanted.station_group and observed.station==wanted.station and observed.terminal==wanted.terminal,"service_terminal_readback_mismatch")
  local expected={};for _,a in ipairs(wanted.alternatives or {}) do expected[a.station..":"..a.terminal]=true end
  assert(#observed.alternatives==#(wanted.alternatives or {}),"service_alternative_readback_mismatch")
  for _,a in ipairs(observed.alternatives) do
   local key=a.station..":"..a.terminal;assert(expected[key],"service_alternative_readback_mismatch");expected[key]=nil
  end
  assert(next(expected)==nil,"service_alternative_readback_mismatch")
  assert(observed.min_wait==(wanted.min_wait or 0) and observed.max_wait==120,"service_wait_readback_mismatch")
 end
 return {line=actual,configuration_verified=true,reachability="requires_separate_native_route_checks",physical_operation="not_demonstrated_by_configuration"}
end
local function depot_command(p)
 local cmd,prepared=depot_prepare(p)
 return cmd,function(r)
  assert(#r.resultEntities<=128,"asset_receipt_bound")
  local found={}
  for _,entry in ipairs(r.resultEntities) do
   local x=type(entry)=="number" and entry or entry[1];local built=comp(x,C.CONSTRUCTION)
   if built and built.fileName==p.resource then
    assert(#built.depots<=8 and #built.frozenNodes<=32 and #built.frozenEdges<=32,"depot_readback_bound")
    found[#found+1]={id=x,revision=rev(x),resource=built.fileName,position=xyz(built.transf:getTransl()),
     depots=built.depots,frozen_nodes=built.frozenNodes,frozen_edges=built.frozenEdges}
   end
  end
  assert(#found==1,"depot_construction_readback_unresolved")
  assert(#found[1].depots>0,"depot_component_not_realised")
  local actual=depot_readback(found[1].id,p);actual.preparation=prepared
  actual.asset_preview="unavailable_for_this_SimpleProposal_path";actual.physical_operation="not_demonstrated_by_construction"
  return actual
 end
end
function M.control(p,s,state,request_id,respond)
 assert(p.execute==true,"explicit_operating_execute_required");assert(not s.mutationPending,"unreconciled_mutation")
 local cmd,read
 if p.action=="station_build" then
  cmd,read=stations.command(p)
 elseif p.action=="signal_place" then
  cmd,read=signal_command(p)
 elseif p.action=="depot_build" then
  cmd,read=depot_command(p)
 elseif p.action=="vehicle_buy" then
  local config,summary=prepare_vehicle(p)
  cmd=api.cmd.makeVehicleBuyCmd(api.engine.util.getPlayer(),p.depot_id,config)
  read=function(r) return {vehicle=vehicle(id(r.resultVehicleEntity)),purchase_verified=true,
   consist_parts=#p.parts,configuration=summary,physical_operation="not_demonstrated_by_purchase"} end
 elseif p.action=="line_create" then
  assert(type(p.name)=="string" and #p.name>=1 and #p.name<=80,"service_name_required")
  for _,x in ipairs(api.engine.system.lineSystem.getLines()) do assert(named(x)~=p.name,"service_name_already_exists") end
  cmd=api.cmd.makeLineCreateCmd(p.name,api.type.Vec3f.new(.2,.6,.9),api.engine.util.getPlayer(),configuration(p))
  read=function(r) return verified_line(id(r.resultEntity),p) end
 elseif p.action=="line_update" then
  fresh(p.line_id,p.revision);assert(comp(p.line_id,C.LINE),"line_missing")
  cmd=api.cmd.makeLineUpdateCmd(p.line_id,configuration(p));read=function() return verified_line(p.line_id,p) end
 elseif p.action=="vehicle_assign" then
  fresh(p.vehicle_id,p.revision);assert(comp(p.vehicle_id,C.TRANSPORT_VEHICLE),"vehicle_missing");local target=line(p.line_id)
  assert(type(p.stop_index)=="number" and p.stop_index%1==0 and p.stop_index>=0 and p.stop_index<#target.stops,"stop_index_invalid")
  cmd=api.cmd.makeVehicleSetLineCmd(p.vehicle_id,p.line_id,p.stop_index);read=function() local v=vehicle(p.vehicle_id);assert(v.line==p.line_id,"assignment_readback_mismatch");return {vehicle=v} end
 elseif p.action=="vehicle_stop" or p.action=="vehicle_manual_departure" then
  fresh(p.vehicle_id,p.revision);assert(type(p.value)=="boolean","operating_boolean_required")
  cmd=p.action=="vehicle_stop" and api.cmd.makeVehicleSetStoppedByUserCmd(p.vehicle_id,p.value) or api.cmd.makeVehicleSetManualDepartureCmd(p.vehicle_id,p.value)
  read=function() local v=vehicle(p.vehicle_id);assert((p.action=="vehicle_stop" and v.user_stopped==p.value) or (p.action=="vehicle_manual_departure" and v.auto_departure==not p.value),"vehicle_control_readback_mismatch");return {vehicle=v} end
 else error("unsupported_operating_action") end
 s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
 api.cmd.sendCommand(cmd,function(result,success)
  if success~=true then
   s.mutationPending=nil
   respond(request_id,"error",{error="native_operating_command_rejected",native_command_success=false,
    game_constructed=false,operating_effects="unknown",retry=false});return
  end
  local ok,value=pcall(function() assert(success==true,"native_operating_command_rejected");return read(result) end)
  if ok then s.mutationPending=nil;value.native_command_success=true;value.game_constructed=value.game_constructed or false;value.native_operating_state_changed=true end
  respond(request_id,ok and "ok" or "mutation_unverified",ok and value or {error=tostring(value):sub(1,400),retry=false,game_constructed=false,operating_effects="unknown"})
 end)
end
return M
