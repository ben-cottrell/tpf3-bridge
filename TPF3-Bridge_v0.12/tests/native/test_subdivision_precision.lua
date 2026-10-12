-- Actual Lua guard exercised via its local upvalue; no engine/game calls.
-- Requires Lua5.3+ string.pack for IEEEfloat32 replay. Runtime unavailable here.
local M={}
local function upvalue(fn,name)
 for i=1,64 do local key,value=debug.getupvalue(fn,i);if not key then break end;if key==name then return value end end
 error('missing native upvalue '..name)
end
function M.run(source)
 local env=setmetatable({api={type={enum={}}}},{__index=_G})
 local native=assert(load(source,'native subdivision guard under test','t',env))()
 local split=upvalue(native.interior_junction,'interior_splits')
 local near=upvalue(split,'subdivision_position_near')
 local f=function(x)return (string.unpack('f',string.pack('f',x)))end
 local c={p0={-3540.843994140625,-13610.01953125,.9021682739257812},p1={-3578.908203125,-13708.53515625,.9021682739257812},t0={-35.80976867675781,-99.31127166748047,0},t1={-32.63361740112305,-100.43174743652344,0}}
 local function value(c,u,derivative)
  local b=derivative and {6*u*u-6*u,3*u*u-4*u+1,-6*u*u+6*u,3*u*u-2*u} or {2*u^3-3*u*u+1,u^3-2*u*u+u,-2*u^3+3*u*u,u^3-u*u}
  local result={};for i=1,3 do local x=f(f(b[1])*c.p0[i]);for j,key in ipairs({'t0','p1','t1'}) do x=f(x+f(f(b[j+1])*c[key][i])) end;result[i]=x end;return result
 end
 local maximum=0
 for _,range in ipairs({{0,.375},{.375,1}}) do
  local lo,hi=range[1],range[2];local child={p0=value(c,lo),p1=value(c,hi),t0=value(c,lo,true),t1=value(c,hi,true)}
  for i=1,3 do child.t0[i]=f(child.t0[i]*(hi-lo));child.t1[i]=f(child.t1[i]*(hi-lo)) end
  for _,u in ipairs({0,.25,.5,.75,1}) do
   local a,b=value(c,lo+u*(hi-lo)),value(child,u);assert(near(a,b,c))
   for i=1,3 do maximum=math.max(maximum,math.abs(a[i]-b[i])) end
  end
 end
 assert(maximum==.001953125,'large-coordinate float32 regression not reproduced')
 local a=value(c,.5);local b={a[1],a[2]+.02,a[3]};assert(not near(a,b,c),'centimetre shape change accepted')
 local small={p0={0,0,0},p1={40,100,0}};assert(not near({20,50,0},{20,50.002,0},small),'small-coordinate tolerance weakened')
 assert(source:find('angle(arr(original[2]),arr(derived[2]))<=.1',1,true),'tangent guard changed')
 return {passed=true,float32_equivalence=true,wrong_geometry_rejected=true,no_native_calls=true}
end
return M
