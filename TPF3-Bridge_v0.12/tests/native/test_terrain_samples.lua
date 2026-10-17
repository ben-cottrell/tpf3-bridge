-- Offline source/mock test; pass actual pif_native.lua source to M.run.
-- No native engine or terrain mutations. A Lua runtime is needed to execute it.
local M={}
function M.run(source)
 local checked,heights,bases=0,0,0
 local terrain={
  isValidCoordinate=function(xy) checked=checked+1;return math.abs(xy.x)<=24000 and math.abs(xy.y)<=24000 end,
  getHeightAt=function(xy) heights=heights+1;return xy.x+xy.y+5 end,
  getBaseHeightAt=function(xy) bases=bases+1;return xy.x+xy.y+2 end}
 local api={type={enum={},Vec2f={new=function(x,y) return {x=x,y=y} end}},engine={terrain=terrain}}
 local env=setmetatable({api=api},{__index=_G})
 local native=assert(load(source,'point terrain query under test','t',env))()
 local positions={};for i=1,128 do positions[i]={i*180,-i*180} end
 local result=native.terrain_samples({positions=positions})
 assert(#result.terrain==128 and checked==128 and heights==128 and bases==128)
 assert(result.game_constructed==false and result.sampled_only==true)
 for i,row in ipairs(result.terrain) do
  assert(row.xy==positions[i] and row.height==5 and row.base_height==2 and row.valid)
 end
 local before=checked
 for _,p in ipairs({{positions={}},{positions={{0,0,1}}},{positions={{0/0,0}}},{positions={{0,0}},execute=true}}) do
  assert(not pcall(native.terrain_samples,p))
 end
 positions[129]={0,0};assert(not pcall(native.terrain_samples,{positions=positions}))
 assert(checked==before,'invalid shape/fields reached terrain API')
 local prior_height=heights
 assert(not pcall(native.terrain_samples,{positions={{24001,0}}}))
 assert(heights==prior_height,'outside-map coordinate was sampled')
 return {passed=true,ordered128_samples=true,no_object_queries=true,native_mutation=false}
end
return M
