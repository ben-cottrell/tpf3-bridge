-- Run against the actual GameScript source, using a refreshing fake engine state.
-- No native commands, filesystem operations or game-world writes are performed.
local M={}
local function copy(value)
 if type(value)~="table" then return value end
 local out={};for key,item in pairs(value) do out[key]=copy(item) end;return out
end
local function refresh(target,source)
 local keys={};for key in pairs(target) do keys[#keys+1]=key end
 for _,key in ipairs(keys) do if source[key]==nil then target[key]=nil end end
 for key,item in pairs(source) do
  if type(item)=="table" then
   if type(target[key])~="table" then target[key]={} end
   refresh(target[key],item)
  else target[key]=item end
 end
end
local function exercise(source)
 local committed,borrowed={},{};local responses={};local builds=0
 local state={}
 function state:get() refresh(borrowed,committed);return borrowed end
 function state:set(value) committed=copy(value) end
 local native={}
 function native.inspect() return {read_only=true} end
 function native.interior_junction(p,s,backend,id,respond)
  s.prepared_interiors=s.prepared_interiors or {}
  if p.prepare then
   s.prepared_interiors[id]={controls={p0={1,2,3},p1={4,5,3}},used=false}
  else
   local record=assert(s.prepared_interiors[p.prepared_request],"missing_or_consumed")
   assert(record.controls.p0[1]==1 and record.controls.p1[2]==5,"accepted_geometry_changed")
   s.prepared_interiors[p.prepared_request]=nil;builds=builds+1
  end
  local root=backend:get();root.pifLive=s;backend:set(root)
  respond(id,"ok",{game_constructed=false,prepared_request=id})
 end
 local env=setmetatable({getBuildVersion=function() return "fake_build" end,debugPrint=function() end},{__index=_G})
 env.ug_require=function(path)
  if path:find("pif_codec",1,true) then
   return {json=function(value) if value.request_id and value.status then responses[#responses+1]=copy(value) end;return "{}" end}
  end
  return native
 end
 assert(load(source,"GameScript under test","t",env))()
 local handler=env.data().handleEvent
 local function send(id,sequence,operation,params)
  handler(nil,state,"tpf3_bridge_pif_live","request","TPF3_BRIDGE_PIF_LIVE_EVENT",
   {version=1,session="test_session",request_id=id,sequence=sequence,operation=operation,params=params})
  return responses[#responses]
 end
 handler(nil,state,"tpf3_bridge_pif_live","request","TPF3_BRIDGE_PIF_LIVE_EVENT",{hello=true,session="test_session"})
 assert(send("prepared",1,"interior_junction",{prepare=true}).status=="ok")
 assert((state:get().pifLive.prepared_interiors or {}).prepared,"preparation_lost")
 assert(send("inspection",2,"inspect",{}).status=="ok")
 assert(state:get().pifLive.sequence==3,"request_counter_lost")
 assert(state:get().pifLive.prepared_interiors.prepared,"inspection_lost_preparation")
 assert(send("consume",3,"interior_junction",{prepared_request="prepared"}).status=="ok")
 assert(not state:get().pifLive.prepared_interiors.prepared,"consumption_lost")
 assert(send("second_consume",4,"interior_junction",{prepared_request="prepared"}).status=="error")
 assert(send("consume",5,"interior_junction",{prepared_request="prepared"}).status=="ok")
 assert(builds==1,"duplicate_execution")
 return true
end
function M.run(source)
 assert(exercise(source))
 local start=assert(source:find("  local root=detached(state:get() or {})",1,true),"detached_state_boundary_not_found")
 local finish=assert(source:find("  local function respond",start,true),"response_boundary_not_found")
 local broken=source:sub(1,start-1).."  local root=state:get() or {};local s=root.pifLive\n"..source:sub(finish)
 local ok,err=pcall(exercise,broken)
 assert(not ok and tostring(err):find("preparation_lost",1,true),"regression_did_not_detect_original_failure")
 return {passed=true,original_failure_detected=true,prepared_survives_inspection=true,
  counter_persists=true,consumption_persists=true,duplicate_submission_not_executed=true,native_mutation=false}
end
return M
