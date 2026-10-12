-- One prepared, session-bound native proposal; no individual fallback or replay.
local M={}
function M.new(comp,rev,fresh,xyz,signals,seed,snapshot)
 local C,E=api.type.ComponentType,api.type['enum']
 local function plain(x)
  local e=assert(comp(x,C.BASE_EDGE),'signal_batch_edge_missing')
  assert(e.roadType==E.RoadType.TRACK,'signal_batch_TRACK_required')
  local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(x)
  assert(not(owner and owner>0),'signal_batch_construction_owned')
  return e
 end
 local function geometry(x,e)
  return {id=x,revision=rev(x),node0=e.node0,node1=e.node1,p0=xyz(e.position0),p1=xyz(e.position1),
   t0=xyz(e.tangent0),t1=xyz(e.tangent1),template=e.roadTemplate,style=e.roadStyle,road_type='TRACK',native_type=e.type,native_type_index=e.typeIndex}
 end
 local function matches(e,row)
  assert(e.node0==row.node0 and e.node1==row.node1 and e.roadTemplate==row.template and e.roadStyle==row.style,'signal_batch_snapshot_changed')
  if row.native_type then assert(e.type==row.native_type and e.typeIndex==row.native_type_index,'signal_batch_structure_changed') end
  for field,key in pairs({position0='p0',position1='p1',tangent0='t0',tangent1='t1'}) do
   local a=xyz(e[field]);assert(type(row[key])=='table' and #row[key]==3,'signal_batch_geometry_required')
   for i=1,3 do assert(type(row[key][i])=='number' and math.abs(a[i]-row[key][i])<=.001,'signal_batch_geometry_changed') end
  end
 end
 local function through(node,a,b)
  assert(a~=b,'signal_batch_loop')
  local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForNode(node)
  assert(not(owner and owner>0),'signal_batch_station_or_construction_node')
  local ids=api.engine.system.streetSystem.getNodeTrackSegments(node)
  assert(#ids==2 and ((ids[1]==a and ids[2]==b) or (ids[1]==b and ids[2]==a)),'signal_batch_junction_or_changed_incidence')
  local all=api.engine.system.streetSystem.getNodeSegments(node)
  assert(#all==2,'signal_batch_nonrail_junction')
 end
 local function check(p)
  assert(type(p.edges)=='table' and #p.edges>=1 and #p.edges<=16,'signal_batch_edge_bound')
  local current=p.start_node;local visited={};visited[current]=true;local seen={}
  if p.before_edge then through(current,p.before_edge,p.edges[1].id) end
  for i,row in ipairs(p.edges) do
   assert(not seen[row.id],'signal_batch_duplicate_edge');seen[row.id]=true
   local e=plain(row.id);matches(e,row);if row.revision then fresh(row.id,row.revision) end
   assert(current==e.node0 or current==e.node1,'signal_batch_disconnected')
   current=current==e.node0 and e.node1 or e.node0
   assert(not visited[current],'signal_batch_loop');visited[current]=true
   if i<#p.edges then through(current,row.id,p.edges[i+1].id) end
  end
  if p.after_edge then through(current,p.edges[#p.edges].id,p.after_edge) end
  return {checked=true,edge_count=#p.edges,game_constructed=false}
 end
 local function make(p)
  check(p)
  assert(type(p.placements)=='table' and #p.placements>=1 and #p.placements<=64,'signal_batch_placement_bound')
  assert(type(p.input_hash)=='string' and #p.input_hash==64,'signal_batch_input_hash_required')
  local template=seed(p.seed_id);if p.seed_revision then fresh(template.id,p.seed_revision) end
  local proposal=api.type.SimpleProposal.new();local remove,add,objects={},{},{}
  local rows,base,byid={},{},{}
  for i,row in ipairs(p.edges) do
   assert(not byid[row.id],'signal_batch_duplicate_edge');local e=plain(row.id);matches(e,row)
   if row.revision then fresh(row.id,row.revision) end
   rows[i]=geometry(row.id,e);rows[i].objects={};base[i]=e;byid[row.id]=i
   assert(#e.objects<=16,'signal_batch_object_bound')
   rows[i].object_state={}
   for _,entry in ipairs(e.objects) do
    rows[i].objects[#rows[i].objects+1]={entry[1],entry[2]}
    local o=assert(comp(entry[1],C.EDGE_OBJECT),'signal_batch_existing_object_unavailable')
    rows[i].object_state[#rows[i].object_state+1]={id=entry[1],parameter=o.param,resource=o.edgeObjectConstruction}
   end
   if row.objects then
    assert(#row.objects==#rows[i].objects,'signal_batch_stale_objects')
    local expected={};for _,entry in ipairs(row.objects) do expected[entry[1]]=entry[2] end
    for _,entry in ipairs(rows[i].objects) do assert(expected[entry[1]]==entry[2],'signal_batch_stale_objects') end
    for _,object in ipairs(row.object_state or {}) do
     local o=assert(comp(object.id,C.EDGE_OBJECT),'signal_batch_stale_objects')
     assert(o.edgeObjectConstruction==object.resource and math.abs(o.param-object.parameter)<=.0001,'signal_batch_stale_object_state')
    end
   end
  end
  local placed={};for i=1,#base do placed[i]={} end
  for index,q in ipairs(p.placements) do
   local i=assert(byid[q.edge_id],'signal_batch_placement_edge_missing')
   assert(type(q.parameter)=='number' and q.parameter>0 and q.parameter<1,'signal_batch_interior_parameter')
   assert(type(q.forward)=='boolean' and type(q.one_way)=='boolean','signal_batch_direction_required')
   for _,interval in ipairs(p.excluded_intervals or {}) do
    assert(type(q.distance)=='number' and (q.distance<interval[1] or q.distance>interval[2]),'signal_batch_excluded_interval')
   end
   for _,old in ipairs(rows[i].objects) do
    local o=comp(old[1],C.EDGE_OBJECT)
    assert(not comp(old[1],C.SIGNAL_LIST) or not o or math.abs(o.param-q.parameter)>.0001,'signal_batch_existing_signal_collision')
   end
   for _,old in ipairs(placed[i]) do assert(math.abs(old.q.parameter-q.parameter)>.0001,'signal_batch_duplicate_parameter') end
   placed[i][#placed[i]+1]={index=index,q=q}
  end
  local affected={}
  for i,e in ipairs(base) do
   if #placed[i]>0 then
    assert(#rows[i].objects+#placed[i]<=16,'signal_batch_object_bound')
    affected[#affected+1]=i;local n=#affected
    local entries={};for _,entry in ipairs(rows[i].objects) do entries[#entries+1]={entry[1],entry[2]} end
    for _,item in ipairs(placed[i]) do
     -- Native placeholders follow edgeObjectsToAdd order, not input placement order.
     entries[#entries+1]={-400000000-#objects,E.EdgeObjectType.SIGNAL}
     local o=api.type.SimpleStreetProposal.EdgeObject.new();o.edgeEntity=-n;o.param=item.q.parameter
     o.left=not item.q.forward;o.oneWay=item.q.one_way;o.model=comp(template.id,C.EDGE_OBJECT).edgeObjectConstruction
     o.playerEntity=api.engine.util.getPlayer();objects[#objects+1]=o
    end
    local segment=api.type.SegmentAndEntity.new();segment.entity=-n;segment.type=1;segment.comp=e
    local owner=comp(rows[i].id,C.PLAYER_OWNED);if owner then segment.playerOwned=owner end
    segment.comp.objects=entries;remove[#remove+1]=rows[i].id;add[#add+1]=segment
   end
  end
  proposal.streetProposal.edgesToRemove=remove;proposal.streetProposal.edgesToAdd=add
  proposal.streetProposal.edgeObjectsToAdd=objects;proposal.streetProposal.edgeObjectsToRemove={}
  local data=api.engine.util.proposal.makeProposalData(proposal,nil);local errors=data.errorState
  local messages={};for i,v in ipairs(errors.messages) do if i<=16 then messages[#messages+1]=tostring(v):sub(1,400) end end
  local summary={accepted=not errors.critical and #errors.messages==0,native_proposal_evaluated=true,
   edge_count=#affected,placement_count=#p.placements,input_hash=p.input_hash,seed=template,
   evaluation={critical=errors.critical,messages=messages,message_count=#errors.messages},game_constructed=false}
  return proposal,summary,rows,affected,placed
 end
 local function prepare(p,s,state,rid)
  assert(s and state and rid,'signal_batch_session_required')
  s.signal_batch=nil
  local _,summary,rows=make(p)
  if summary.accepted then
   -- Only one outstanding handle, so preparation cannot create an unbounded cache.
   local saved={};for k,v in pairs(p) do saved[k]=v end
   saved.edges=rows;s.signal_batch={handle=rid,session=s.session,input=saved,input_hash=p.input_hash,seed_revision=summary.seed.revision}
   local root=state:get() or {};root.pifLive=s;state:set(root);summary.prepared_handle=rid
  end
  return summary
 end
 local function command(p,s,state)
  local saved=assert(s.signal_batch,'signal_batch_handle_unavailable_or_consumed')
  assert(saved.session==s.session and saved.handle==p.prepared_handle and saved.input_hash==p.input_hash,'signal_batch_stale_or_mismatched_handle')
  -- Consume before any fallible revalidation/submission. A different request cannot replay it.
  s.signal_batch=nil;local root=state:get() or {};root.pifLive=s;state:set(root)
  local input=saved.input;input.seed_revision=saved.seed_revision
  local proposal,summary,rows,affected,placed=make(input);assert(summary.accepted,'native_signal_batch_proposal_rejected')
  local context=api.type.Context.new();context.player=api.engine.util.getPlayer()
  return api.cmd.makeWorldBuildProposalCmd(proposal,context,false,true),function(r)
   local segments=r.proposal.proposal.addedSegments;assert(#segments==#affected,'signal_batch_receipt_count')
   local used,signal_ids,mapping,result={}, {}, {}, {}
   -- Match exact retained endpoint identities; receipt order is not authoritative.
   for _,index in ipairs(affected) do
    local before=rows[index];local replacement,e
    for _,segment in ipairs(segments) do
     local candidate=segment.entity;local observed=plain(candidate)
     if observed.node0==before.node0 and observed.node1==before.node1 then
      assert(not replacement,'signal_batch_ambiguous_receipt');replacement=candidate;e=observed
     end
    end
    assert(replacement and not used[replacement],'signal_batch_replacement_unresolved');used[replacement]=true;matches(e,before)
    local old,retained,new={},{},{};for _,entry in ipairs(before.objects) do old[entry[1]]=entry[2] end
    assert(#e.objects<=16,'signal_batch_readback_object_bound')
    for _,entry in ipairs(e.objects) do
     if old[entry[1]] then assert(old[entry[1]]==entry[2],'signal_batch_retained_category_changed');retained[entry[1]]=true
     else assert(entry[2]==E.EdgeObjectType.SIGNAL,'signal_batch_unexpected_object');new[#new+1]=signals(entry[1]) end
    end
    for x in pairs(old) do assert(retained[x],'signal_batch_existing_object_removed') end
    for _,object in ipairs(before.object_state) do
     local o=assert(comp(object.id,C.EDGE_OBJECT),'signal_batch_retained_object_unavailable')
     assert(o.edgeObjectConstruction==object.resource and math.abs(o.param-object.parameter)<=.0001,'signal_batch_retained_object_changed')
    end
    assert(#new==#placed[index],'signal_batch_new_signal_count')
    local matched={}
    for _,item in ipairs(placed[index]) do
     local signal
     for _,v in ipairs(new) do if math.abs(v.param-item.q.parameter)<=.0001 then assert(not signal,'signal_batch_ambiguous_signal');signal=v end end
     assert(signal and not matched[signal.id] and not signal_ids[signal.id] and signal.resource==summary.seed.resource,'signal_batch_signal_identity_or_resource');matched[signal.id]=true;signal_ids[signal.id]=true
     local kind=item.q.one_way and api.type.Signal.Type.ONE_WAY_SIGNAL or api.type.Signal.Type.SIGNAL;local verified
     for _,lane in ipairs(signal.lanes) do if lane.edge==replacement and lane.reversed==item.q.forward and lane.type==tostring(kind) then verified=lane end end
     assert(verified,'signal_batch_functional_direction_mismatch')
     result[item.index]={replaced_edge=before.id,replacement_edge=replacement,
      signal={id=signal.id,param=signal.param,resource=signal.resource,revision=signal.revision,native_lane=verified},travel_forward=item.q.forward}
    end
    local row=snapshot and snapshot(replacement) or geometry(replacement,e);row.revision=rev(replacement)
    mapping[#mapping+1]={replaced_edge=before.id,replacement_edge=replacement,snapshot=row}
   end
   return {input_hash=saved.input_hash,prepared_handle=saved.handle,mapping=mapping,placements=result,
    track_geometry_verified=true,existing_objects_retained=true,functional_signals_verified=true,
    game_constructed=true,directed_route_verified=false,physical_operation='requires_separate_observation'}
  end
 end
 return {prepare=prepare,command=command,check=check}
end
return M
