-- Bounded exact signal removal using signal_command's established replacement path.
local M={}
function M.new(comp,rev,fresh,xyz,signals,snapshot,ownership)
 local C,E=api.type.ComponentType,api.type['enum']
 local function equal(a,b)
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  for k,v in pairs(a) do if not equal(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
 end
 local function lanes(value,edge)
  local out={};for _,v in ipairs(value.lanes) do
   assert(v.edge==edge,'signal_removal_wrong_edge_lane')
   out[#out+1]={index=v.index,edge_index=v.edge_index,reversed=v.reversed,type=v.type}
  end
  assert(#out>=1 and #out<=8,'signal_removal_lane_bound');return out
 end
 local function parameters(value,depth,budget)
  depth=depth or 0;budget=budget or {count=0}
  if type(value)~='table' then
   assert(type(value)=='string' or type(value)=='number' or type(value)=='boolean','signal_removal_params_unavailable')
   if type(value)=='number' then assert(value==value and math.abs(value)<math.huge,'signal_removal_nonfinite_params') end
   if type(value)=='string' then assert(#value<=512,'signal_removal_params_string_bound') end
   return value
  end
  assert(depth<=4,'signal_removal_params_depth_bound');local out={}
  for k,v in pairs(value) do
   budget.count=budget.count+1;assert(budget.count<=64,'signal_removal_params_bound')
   assert((type(k)=='string' and #k<=128) or (type(k)=='number' and k%1==0),'signal_removal_params_key')
   out[k]=parameters(v,depth+1,budget)
  end
  return out
 end
 local function geometry(actual,expected)
  for _,k in ipairs({'node0','node1','template','style','road_type','structure','node_positions'}) do
   assert(equal(actual[k],expected[k]),'signal_removal_snapshot_changed_'..k)
  end
  for _,k in ipairs({'p0','p1','t0','t1'}) do
   assert(type(expected[k])=='table' and #expected[k]==3,'signal_removal_geometry_required')
   for i=1,3 do assert(type(expected[k][i])=='number' and math.abs(actual[k][i]-expected[k][i])<=.001,'signal_removal_geometry_changed') end
  end
 end
 local function make(p)
  local before=p.edge_snapshot;assert(type(before)=='table' and before.road_type=='TRACK','signal_removal_TRACK_required')
  fresh(before.id,before.revision);local e=assert(comp(before.id,C.BASE_EDGE),'signal_removal_edge_missing')
  assert(e.roadType==E.RoadType.TRACK and #e.objects<=16,'signal_removal_track_object_bound')
  local construction=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(before.id)
  assert(not(construction and construction>0),'signal_removal_construction_owned')
  geometry(snapshot(before.id),before)
  assert(type(p.signals)=='table' and #p.signals>=1 and #p.signals<=16,'signal_removal_selection_bound')
  local selected,ids={},{};for _,v in ipairs(p.signals) do
   assert(type(v.id)=='number' and v.id>0 and v.id%1==0 and not selected[v.id],'signal_removal_duplicate_or_invalid_id')
   fresh(v.id,v.revision);assert(comp(v.id,C.SIGNAL_LIST) and comp(v.id,C.EDGE_OBJECT),'signal_removal_not_signal')
   lanes(signals(v.id),before.id);selected[v.id]=true;ids[#ids+1]=v.id
  end
  local retained,entries,attached={},{},{}
  for _,entry in ipairs(e.objects) do
   assert(not attached[entry[1]],'signal_removal_duplicate_object');attached[entry[1]]=true
   local o=assert(comp(entry[1],C.EDGE_OBJECT),'signal_removal_object_missing')
   if selected[entry[1]] then assert(entry[2]==E.EdgeObjectType.SIGNAL,'signal_removal_not_signal_category')
   else
    entries[#entries+1]={entry[1],entry[2]}
    retained[#retained+1]={id=entry[1],category=entry[2],parameter=o.param,params=parameters(o.params),resource=o.edgeObjectConstruction,
     revision=rev(entry[1]),lanes=comp(entry[1],C.SIGNAL_LIST) and lanes(signals(entry[1]),before.id) or nil}
   end
  end
  for x in pairs(selected) do assert(attached[x],'signal_removal_stale_membership') end
  local own=ownership(before.id)
  local segment=api.type.SegmentAndEntity.new();segment.entity=-1;segment.type=1;segment.comp=e
  local player=comp(before.id,C.PLAYER_OWNED);if player then segment.playerOwned=player end
  segment.comp.objects=entries
  local proposal=api.type.SimpleProposal.new()
  proposal.streetProposal.edgesToRemove={before.id};proposal.streetProposal.edgesToAdd={segment}
  proposal.streetProposal.edgeObjectsToRemove=ids;proposal.streetProposal.edgeObjectsToAdd={}
  local data=api.engine.util.proposal.makeProposalData(proposal,nil);local errors=data.errorState
  local messages={};for i,v in ipairs(errors.messages) do if i<=16 then messages[#messages+1]=tostring(v):sub(1,400) end end
  return proposal,{accepted=not errors.critical and #errors.messages==0,native_proposal_evaluated=true,
   evaluation={critical=errors.critical,messages=messages,message_count=#errors.messages},
   input_hash=p.input_hash,edge_id=before.id,selected_count=#ids,game_constructed=false},retained,own
 end
 local function prepare(p,s,state,rid)
  assert(p.session==s.session and type(p.input_hash)=='string' and #p.input_hash==64,'signal_removal_session_hash_required')
  s.signal_removal=nil
  local _,summary,retained,owner=make(p)
  if summary.accepted then
   s.signal_removal={session=s.session,handle=rid,input=p,input_hash=p.input_hash,retained=retained,owner=owner}
   summary.prepared_handle=rid
  end
  local root=state:get() or {};root.pifLive=s;state:set(root);return summary
 end
 local function command(p,s,state)
  local saved=assert(s.signal_removal,'signal_removal_handle_unavailable_or_consumed')
  assert(saved.session==s.session and saved.handle==p.prepared_handle and saved.input_hash==p.input_hash,'signal_removal_stale_handle')
  s.signal_removal=nil;local root=state:get() or {};root.pifLive=s;state:set(root)
  for _,v in ipairs(saved.retained) do fresh(v.id,v.revision) end
  local proposal,summary,retained,owner=make(saved.input)
  assert(equal(owner,saved.owner) and equal(retained,saved.retained),'signal_removal_retained_state_changed')
  assert(summary.accepted,'native_signal_removal_proposal_rejected')
  local context=api.type.Context.new();context.player=api.engine.util.getPlayer()
  -- Evaluate and commit this same proposal; no alternative command or retry path.
  return api.cmd.makeWorldBuildProposalCmd(proposal,context,false,true),function(r)
   local receipt=r.proposal.proposal;assert(#receipt.addedSegments==1,'signal_removal_receipt_unresolved')
   local replacement=receipt.addedSegments[1].entity
   assert(type(replacement)=='number' and replacement>0 and replacement%1==0,'signal_removal_replacement_identity')
   -- getComponent requires a live entity; deleted IDs must be tested first.
   if replacement~=saved.input.edge_snapshot.id and api.engine.entityExists(saved.input.edge_snapshot.id) then
    assert(not comp(saved.input.edge_snapshot.id,C.BASE_EDGE),'signal_removal_old_edge_still_present')
   end
   local current=snapshot(replacement);geometry(current,saved.input.edge_snapshot)
   assert(equal(ownership(replacement),owner),'signal_removal_ownership_changed')
   local actual=assert(comp(replacement,C.BASE_EDGE),'signal_removal_readback_missing')
   assert(#actual.objects==#retained,'signal_removal_retained_count_changed')
   local found={};for _,entry in ipairs(actual.objects) do
    assert(not found[entry[1]],'signal_removal_duplicate_readback_object');found[entry[1]]=entry[2]
   end
   for _,v in ipairs(saved.input.signals) do
    assert(not found[v.id],'signal_removal_selected_still_present')
    if api.engine.entityExists(v.id) then
     assert(not comp(v.id,C.EDGE_OBJECT) and not comp(v.id,C.SIGNAL_LIST),'signal_removal_selected_still_present')
    end
   end
   for _,v in ipairs(retained) do
    assert(found[v.id]==v.category,'signal_removal_retained_identity_category_changed')
    local o=assert(comp(v.id,C.EDGE_OBJECT),'signal_removal_retained_object_missing')
    assert(o.edgeObjectConstruction==v.resource and math.abs(o.param-v.parameter)<=.0001,'signal_removal_retained_resource_parameter_changed')
    assert(equal(parameters(o.params),v.params),'signal_removal_retained_params_changed')
    assert(equal(v.lanes,comp(v.id,C.SIGNAL_LIST) and lanes(signals(v.id),replacement) or nil),'signal_removal_retained_function_changed')
   end
   current.revision=rev(replacement);local removed={};for _,v in ipairs(saved.input.signals) do removed[#removed+1]=v.id end
   return {input_hash=saved.input_hash,prepared_handle=saved.handle,replaced_edge=saved.input.edge_snapshot.id,
    replacement_edge=replacement,snapshot=current,removed_signals=removed,selected_signals_absent=true,
    existing_objects_retained=true,functional_signals_verified=true,track_geometry_verified=true,
    structure_verified=true,ownership_verified=true,game_constructed=true,
    directed_route_verified=false,physical_operation='requires_separate_observation'}
  end
 end
 return {prepare=prepare,command=command}
end
return M
