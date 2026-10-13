-- Pure bounded diagnostics against actual pif_signal_batch.lua; no API calls.
local M={}
function M.run(source)
 local module=assert(load(source,'proposal collision diagnostics','t',_G))()
 local function collect(rows) return module.collision_diagnostics({collisionInfo={collisionEntities=rows}}) end
 local r=collect({});assert(r.collision_info_available and r.collision_count==0 and not r.collision_output_truncated)
 r=collect({{entity=123},{entity=-1}});assert(r.collision_entities[1]==123 and r.collision_entities[2]==-1 and r.collision_count==2)
 local rows={};for i=1,16 do rows[i]={entity=i} end
 setmetatable(rows,{__len=function() return 20 end,__index=function(_,k) if k>16 then error('must_not_read_beyond_cap') end end})
 r=collect(rows);assert(r.collision_info_available and #r.collision_entities==16 and r.collision_count==20 and r.collision_output_truncated)
 for _,data in ipairs({{}, {collisionInfo={}}, {collisionInfo={collisionEntities=''}},
  {collisionInfo={collisionEntities={{entity='unknown'}}}}, {collisionInfo={collisionEntities={{entity=.5}}}},
  {collisionInfo={collisionEntities={{entity=false}}}}}) do
  r=module.collision_diagnostics(data)
  assert(not r.collision_info_available and r.collision_count=='unavailable' and r.collision_output_truncated=='unknown' and #r.collision_entities==0)
 end
 return true
end
return M
