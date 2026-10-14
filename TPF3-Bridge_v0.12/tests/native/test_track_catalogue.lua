-- Offline mock-engine coverage. Pass the actual pif_native.lua source to M.run.
-- Does not qualify native track-map enumeration in the game or send native commands.
local M={}
function M.run(source)
 local C={BASE_EDGE=1,BASE_NODE=2,NAME=3}
 local E={RoadType={TRACK=1,STREET=2},BaseEdgeType={NORMAL=0,BRIDGE=1,TUNNEL=2}}
 local function point(x) return {x=x,y=0,z=2} end
 local function base(a,b,x,y,road)
  return {node0=a,node1=b,position0=point(x),position1=point(y),tangent0={x=y-x,y=0,z=0},tangent1={x=y-x,y=0,z=0},
   roadType=road,type=0,typeIndex=0,roadTemplate=7,roadStyle=8,objects={}}
 end
 local bases={[1]=base(10,11,0,10,2),[2]=base(20,21,0,100,1),[3]=base(30,31,1000,1100,1),[4]=base(21,40,100,200,1)}
 local node_edges={[20]={2},[21]={2,4},[40]={4}}
 local names={[2]='Guide west',[800]='Scaffold named signal'};local enumerations=0;local enriched={}
 local operating={inspect=function(p)
  assert(#p.track_ids==1 and p.limit==1)
  enriched[#enriched+1]=p.track_ids[1]
  local objects={}
  if p.track_ids[1]==2 then objects={{id=800,parameter=.5,position={50,0,2},resource='signal',signal={lanes={}}}} end
  return {tracks={records={{objects=objects}}}}
 end}
 local api={type={ComponentType=C,enum=E},engine={system={}},res={}}

 api.engine.getComponent=function(id,component)
  if component==C.BASE_EDGE then return bases[id] end
  if component==C.NAME and names[id] then return {name=names[id]} end
  if component==C.BASE_NODE then return {position=point(id)} end
 end
 api.engine.system.streetConnectorSystem={getConstructionEntityForEdge=function(id) return id==3 and 900 or nil end,getConstructionEntityForNode=function() return nil end}
 api.engine.system.streetSystem={getNodeSegments=function(id) return assert(node_edges[id]) end,
  getNode2TrackEdgeMap=function() enumerations=enumerations+1;return {[20]={2},[21]={2,4},[30]={3},[31]={3},[40]={4}} end}
 local env=setmetatable({api=api,ug_require=function(path) assert(path:find('pif_operating.lua',1,true));return operating end},{__index=_G})
 local native=assert(load(source,'native catalogue under test','t',env))()
 local result=native.track_catalogue({})
 assert(result.complete and not result.truncated and result.examined_edges==3 and result.returned_tracks==2)
 assert(result.examined_TRACK==3 and result.excluded_construction_tracks==1 and result.external_only)
 assert(result.edges[1].id==2 and result.edges[2].id==4 and result.edges[1].structure.classification=='NORMAL')
 assert(result.edges[1].name=='Guide west' and result.edges[1].objects[1].name=='Scaffold named signal')
 assert(result.edges[1].endpoint_incidence[1].free and not result.edges[1].endpoint_incidence[2].free)
 result=native.track_catalogue({max_examined_edges=2,max_tracks=2})
 assert(result.scan_truncated and not result.complete and result.examined_edges==2 and result.returned_tracks==1)
 result=native.track_catalogue({max_tracks=1})
 assert(result.tracks_truncated and not result.complete and result.external_tracks_observed==2 and result.returned_tracks==1)
 bases[4].objects={};for i=1,17 do bases[4].objects[i]={i,0} end
 result=native.track_catalogue({})
 assert(result.metadata_truncated and not result.complete and result.edges[2].objects_truncated)
 bases[4].objects={}
 local region={min={150,-1,1},max={160,1,3}}
 enriched={};result=native.track_catalogue({region=region,max_tracks=1})
 assert(result.region_match_count==1 and result.external_tracks_observed==2 and not result.tracks_truncated)
 assert(#enriched==1 and enriched[1]==4 and result.edges[1].id==4,'outside edge consumed detail/output budget')
 assert(not result.edges[1].endpoint_incidence[1].free,'region boundary fabricated free attachment')
 -- Both endpoints lie outside Y, but Bezier controls bow through the box.
 bases[2].tangent0.y=300;bases[2].tangent1.y=-300
 result=native.track_catalogue({region={min={40,50,1},max={60,80,3}}})
 assert(result.region_match_count==1 and result.edges[1].id==2)
 assert(result.region_false_positives_possible and not result.region_clearance_proof)
 bases[2].tangent0.y=0;bases[2].tangent1.y=0
 result=native.track_catalogue({region={min={200,-1,1},max={201,1,3}}})
 assert(result.region_match_count==1 and result.edges[1].id==4,'inclusive boundary touch omitted')
 result=native.track_catalogue({region={min={-10,-1,1},max={2000,1,3}},max_tracks=1})
 assert(result.region_match_count==2 and result.excluded_construction_tracks==1 and result.tracks_truncated)
 result=native.track_catalogue({region=region,max_examined_edges=1})
 assert(result.region_match_count==0 and result.scan_truncated and not result.complete)
 local tangent=bases[2].tangent0;bases[2].tangent0=nil
 assert(not pcall(native.track_catalogue,{region=region}),'missing geometry silently excluded')
 bases[2].tangent0=tangent
 local before=enumerations
 for _,p in ipairs({{max_tracks=513},{max_examined_edges=0},{execute=true},
  {region={min={0,0,0},max={1,1,0}}},{region={min={0,0},max={1,1,1}}},
  {region={min={0,0,0},max={math.huge,1,1}}}}) do assert(not pcall(native.track_catalogue,p)) end
 assert(enumerations==before,'invalid bounds reached engine enumeration')
 return {passed=true,external_only=true,bounds_checked=true,native_mutation=false,native_enumeration_qualified=false}
end
return M
