local M={}
local function quote(s)
 return '"'..s:gsub('[%z\1-\31\\"]',function(c)
  if c=='"' then return '\\"' elseif c=='\\' then return '\\\\' end
  return string.format('\\u%04x',string.byte(c))
 end)..'"'
end
function M.json(v)
 local t=type(v)
 if t=='nil' then return 'null' elseif t=='boolean' then return tostring(v)
 elseif t=='number' then assert(v==v and math.abs(v)<math.huge,'nonfinite_response');return string.format('%.17g',v)
 elseif t=='string' then return quote(v)
 elseif t=='table' then
  local parts={};local count=0;local array=true
  for k in pairs(v) do count=count+1;if type(k)~='number' or k%1~=0 or k<1 then array=false end end
  if array and count>0 and #v==count then for i=1,#v do parts[i]=M.json(v[i]) end;return '['..table.concat(parts,',')..']' end
  for k,x in pairs(v) do assert(type(k)=='string','nonstring_key');parts[#parts+1]=quote(k)..':'..M.json(x) end
  table.sort(parts);return '{'..table.concat(parts,',')..'}'
 end
 error('unsupported_response_type_'..t)
end
return M
