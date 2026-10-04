-- Live development adapter. Supported mod loader in, JSON game log out.
local MOD="tpf3_bridge_n01_c04_20261001"
local SRC,ID,NAME="tpf3_bridge_pif_live","request","TPF3_BRIDGE_PIF_LIVE_EVENT"
local codec=ug_require(MOD.."::/scripts/pif_codec.lua")
local native=ug_require(MOD.."::/scripts/pif_native.lua")
local guiSession,lastPoll,nextSequence=nil,0,1
local function emit(kind,value) debugPrint("TPF3_BRIDGE_LIVE_"..kind.." "..codec.json(value)) end
local function store(state,s) local root=state:get() or {};root.pifLive=s;state:set(root) end
local function identity(x) return type(x)=="string" and #x<=80 and x:match("^[%w_-]+$") end
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
  api.cmd.sendCommand(api.cmd.makeScriptingSendEventCmd(SRC,ID,NAME,request),function(_result,success)
   emit("ACK",{session=guiSession,request_id=request.request_id,success=success==true})
  end)
 end,
 handleEvent=function(_params,state,src,id,name,request)
  if src~=SRC or id~=ID or name~=NAME or type(request)~="table" then return end
  if request.hello==true and identity(request.session) then
   store(state,{session=request.session,sequence=1,fits={},requests={}})
   emit("SESSION",{session=request.session,ready=true});return
  end
  if not identity(request.request_id) or not identity(request.session) then return end
  local root=state:get() or {};local s=root.pifLive
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
   elseif request.operation=="clear_obstructions" then native.clear_obstructions(p,s,state,request.request_id,respond)
   elseif request.operation=="verify_adjacency" then respond(request.request_id,"ok",native.verify_adjacency(p))
   elseif request.operation=="adjacent" then native.adjacent(p,s,state,request.request_id,respond)
   elseif request.operation=="discover" then respond(request.request_id,"ok",native.discover(p,request.request_id))
   elseif request.operation=="discover_junction" then respond(request.request_id,"ok",native.discover_junction(p,request.request_id))
   elseif request.operation=="discover_interior" then respond(request.request_id,"ok",native.discover_interior(p,request.request_id))
   elseif request.operation=="verify_interior" then respond(request.request_id,"ok",native.verify_interior(p))
   elseif request.operation=="verify_crossover" then respond(request.request_id,"ok",native.verify_crossover(p,s))
   elseif request.operation=="remove_branch" then native.remove_branch(p,s,state,request.request_id,respond)
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
