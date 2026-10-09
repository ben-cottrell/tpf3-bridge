-- Live development adapter. Supported mod loader in, JSON game log out.
local MOD="tpf3_bridge_n01_c04_20261001"
local SRC,ID,NAME="tpf3_bridge_pif_live","request","TPF3_BRIDGE_PIF_LIVE_EVENT"
local codec=ug_require(MOD.."::/scripts/pif_codec.lua")
local native=ug_require(MOD.."::/scripts/pif_native.lua")
local operating=ug_require(MOD.."::/scripts/pif_operating.lua")
local guiSession,lastPoll,nextSequence=nil,0,1
local proposalCaptureArmed=false
local function emit(kind,value) debugPrint("TPF3_BRIDGE_LIVE_"..kind.." "..codec.json(value)) end
local function store(state,s) local root=state:get() or {};root.pifLive=s;state:set(root) end
local function identity(x) return type(x)=="string" and #x<=80 and x:match("^[%w_-]+$") end
-- state:get() refreshes engine-backed tables in place on build40408. Native
-- operations call it again while storing, so never mutate that borrowed tree.
-- Work on ordinary Lua tables for the entire request, including its callback.
local function detached(value,seen)
 if type(value)~="table" then return value end
 seen=seen or {};if seen[value] then return seen[value] end
 local result={};seen[value]=result
 for key,item in pairs(value) do result[key]=detached(item,seen) end
 return result
end
function data()
 return {
 update=function(_params,state,_dt)
  state:subscribeToEvent(NAME)
 end,
 guiUpdate=function(_params,_state,_guiState)
  local now=api.util.getApplicationTime()
  if not guiSession then
   guiSession="pif_"..api.util.getLocalTime().."_"..string.format("%.0f",now*1000)
   emit("READY",{version=1,session=guiSession,build=getBuildVersion(),transport="mod_data_modules_and_game_log",native_save_identity="unknown",load_epoch="unknown"})
   api.cmd.sendCommand(api.cmd.makeScriptingSendEventCmd(SRC,ID,NAME,{hello=true,session=guiSession}))
  end
  if now-lastPoll<.5 then return end;lastPoll=now
  local path=MOD.."::/scripts/pif_live/"..guiSession.."/"..string.format("%06d",nextSequence)..".lua"
  local ok,request=pcall(ug_require,path)
  if not ok then return end -- Missing next slot is ordinary idle, not a log stream.
  if type(request)~="table" or request.session~=guiSession or request.sequence~=nextSequence then
   emit("TRANSPORT_ERROR",{session=guiSession,error="invalid_module_envelope",sequence=nextSequence});nextSequence=nextSequence+1;return
  end
  nextSequence=nextSequence+1
  if request.operation=="operating_inspect" and request.params and request.params.capture_cursor==true then
   local observation={session=guiSession,request_id=request.request_id,available=false,source="api.gui.mouse",game_constructed=false}
   local captured,err=pcall(function()
    observation.available=api.gui.mouse.hasTerrainPosition()
    if observation.available then local p=api.gui.mouse.getTerrainPosition();observation.position={p.x,p.y,p.z} end
   end)
   if not captured then observation.available=false;observation.error=tostring(err):sub(1,240) end
   emit("CURSOR",observation)
  end
  if request.operation=="operating_inspect" and request.params and request.params.capture_next_proposal==true then proposalCaptureArmed=true end
  if request.operation=="operating_inspect" and request.params and request.params.focus_entity then
   local entity=request.params.focus_entity
   assert(type(entity)=="number" and entity>0 and entity%1==0,"exact_focus_identity_required")
   api.gui.camera.focusEntity(entity)
  end
  api.cmd.sendCommand(api.cmd.makeScriptingSendEventCmd(SRC,ID,NAME,request),function(_result,success)
   emit("ACK",{session=guiSession,request_id=request.request_id,success=success==true})
  end)
 end,
 guiHandleEvent=function(_params,_state,_guiState,src,id,name,param)
  if not proposalCaptureArmed or (name~="proposalApply" and name~="builder.proposalApply") then return end
  proposalCaptureArmed=false
  local result={source=src,id=id,event=name,diagnostic_only=true,world_replay=false}
  local ok,err=pcall(function()
   if type(param)=="table" then local keys={};for k in pairs(param) do keys[#keys+1]=tostring(k) end;table.sort(keys);result.parameter_keys={};for i=1,math.min(#keys,12) do result.parameter_keys[i]=keys[i] end end
   local p=param.proposal;result.proposal_present=p~=nil
   if not p then return end
   result.removed_entities={};for i,x in ipairs(p.toRemove) do if i<=8 then result.removed_entities[#result.removed_entities+1]=x end end
   result.constructions={};for i,x in ipairs(p.toAdd) do if i<=4 then result.constructions[#result.constructions+1]={resource=x.fileName,player=x.playerEntity} end end
   result.edge_objects={};for i,x in ipairs(p.proposal.edgeObjectsToAdd) do if i<=4 then result.edge_objects[#result.edge_objects+1]={result_entity=x.resultEntity,category=x.category,left=x.left,player=x.playerEntity} end end
   result.added_segments={};for i,x in ipairs(p.proposal.addedSegments) do if i<=4 then result.added_segments[#result.added_segments+1]={entity=x.entity,node0=x.comp.node0,node1=x.comp.node1,objects=x.comp.objects} end end
   result.counts={constructions=#p.toAdd,edge_objects=#p.proposal.edgeObjectsToAdd,segments=#p.proposal.addedSegments}
  end)
  result.inspection_ok=ok;if not ok then result.error=tostring(err):sub(1,400) end
  emit("P66_PROPOSAL_REFERENCE",result)
 end,
 handleEvent=function(_params,state,src,id,name,request)
  if src~=SRC or id~=ID or name~=NAME or type(request)~="table" then return end
  if request.hello==true and identity(request.session) then
   store(state,{session=request.session,sequence=1,fits={},requests={}})
   emit("SESSION",{session=request.session,ready=true});return
  end
  if not identity(request.request_id) or not identity(request.session) then return end
  local root=detached(state:get() or {})
  local engineState=state
  -- All native stores in this request share one detached tree. Only the setter
  -- crosses back to the engine; repeated getters cannot refresh pending edits.
  state={get=function() return root end,set=function(_,value) root=value;engineState:set(value) end}
  local s=root.pifLive
  local function respond(request_id,status,result)
   local response={version=1,session=request.session,request_id=request_id,operation=request.operation,status=status,result=result,build=getBuildVersion()}
   if s then s.requests[request_id]={response=response};if status=="ok" and request.operation=="build" then s.mutationPending=nil end;store(state,s) end
   emit("RESPONSE",response)
  end
  if not s or s.session~=request.session then respond(request.request_id,"error",{error="stale_adapter_session"});return end
  if s.requests[request.request_id] then
   local old=s.requests[request.request_id].response
   if old then emit("RESPONSE",old) else respond(request.request_id,"mutation_unverified",{error="request_still_unreconciled",retry=false}) end
   return
  end
  local ok,errorText=pcall(function()
   assert(request.version==1,"invalid_request_version")
   -- GUI slots enforce delivery order. Engine state snapshots can retain an older
   -- counter across command callbacks; it must not veto a freshly correlated read.
   assert(type(request.sequence)=="number" and request.sequence>0 and request.sequence%1==0,"invalid_request_sequence")
   assert(type(request.params)=="table","invalid_request_parameters")
   s.sequence=request.sequence+1;s.requests[request.request_id]={pending=true};store(state,s)
   local p=request.params
   if request.operation=="extension" then native.extension(p,s,state,request.request_id,respond)
   elseif request.operation=="connection" then native.extension(p,s,state,request.request_id,respond,true)
   elseif request.operation=="test_approach" then native.test_approach(p,s,state,request.request_id,respond)
   elseif request.operation=="inspect" then respond(request.request_id,"ok",native.inspect(p))
   elseif request.operation=="operating_inspect" then respond(request.request_id,"ok",operating.inspect(p))
   elseif request.operation=="operating_control" then operating.control(p,s,state,request.request_id,respond)
   elseif request.operation=="structured_chain" then native.structured_chain(p,s,state,request.request_id,respond)
   elseif request.operation=="station_lookup" then respond(request.request_id,"ok",native.station_lookup(p))
   elseif request.operation=="clear_obstructions" then native.clear_obstructions(p,s,state,request.request_id,respond)
   elseif request.operation=="verify_adjacency" then respond(request.request_id,"ok",native.verify_adjacency(p))
   elseif request.operation=="adjacent" then native.adjacent(p,s,state,request.request_id,respond)
   elseif request.operation=="discover" then respond(request.request_id,"ok",native.discover(p,request.request_id))
   elseif request.operation=="discover_junction" then respond(request.request_id,"ok",native.discover_junction(p,request.request_id))
   elseif request.operation=="discover_interior" then respond(request.request_id,"ok",native.discover_interior(p,request.request_id))
   elseif request.operation=="verify_interior" then respond(request.request_id,"ok",native.verify_interior(p))
   elseif request.operation=="verify_crossover" then respond(request.request_id,"ok",native.verify_crossover(p,s))
   elseif request.operation=="remove_branch" then native.remove_branch(p,s,state,request.request_id,respond)
   elseif request.operation=="repair_crossover" then native.repair_crossover(p,s,state,request.request_id,respond)
   elseif request.operation=="scissors_candidate" then native.scissors_candidate(p,s,state,request.request_id,respond)
   elseif request.operation=="degree_four_candidate" then native.degree_four_candidate(p,s,state,request.request_id,respond)
   elseif request.operation=="inspect_degree_four" then respond(request.request_id,"ok",native.inspect_degree_four(p))
   elseif request.operation=="crossover" then native.crossover(p,s,state,request.request_id,respond)
   elseif request.operation=="interior_junction" then native.interior_junction(p,s,state,request.request_id,respond)
   elseif request.operation=="junction" then native.junction(p,s,state,request.request_id,respond)
   elseif request.operation=="selected_connection" then native.connect_selected(p,s,state,request.request_id,respond)
   elseif request.operation=="corridor" then native.corridor(p,s,state,request.request_id,respond)
   elseif request.operation=="route" then respond(request.request_id,"ok",native.route(p))
   elseif request.operation=="fit" then respond(request.request_id,"ok",native.fit(p,s,request.request_id))
   elseif request.operation=="build" then
    assert(not s.mutationPending,"unreconciled_mutation")
    native.build(p,s,state,request.request_id,respond)
   elseif request.operation=="readback" then
    local f=s.fits[p.fit_request];assert(f,"fit_not_found");local result=native.readback(f)
    if s.mutationPending==f.build_request then s.mutationPending=nil end
    respond(request.request_id,"ok",result)
   else error("unsupported_operation") end
  end)
  if not ok then
   respond(request.request_id,s and s.mutationPending==request.request_id and "mutation_unverified" or "error",{error=tostring(errorText):sub(1,400),retry=false,game_constructed=s and s.mutationPending==request.request_id and "unknown" or false})
  end
 end}
end
