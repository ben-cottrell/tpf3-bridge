-- Basic native station construction. Native modules own detailed realisation.
local M={}
local C,E=api.type.ComponentType,api.type['enum']
local function xyz(v) return {v.x,v.y,v.z} end
local function rev(x) local r=api.engine.getRevision(x);return {r.num[1],r.num[2],r.num[3]} end
local function comp(x,t) return api.engine.getComponent(x,t) end
function M.catalogue()
 local out={assets={},groups={},game_constructed=false}
 for k,name in pairs(api.res.constructionRep.getAll()) do
  if name:find('/stations/rail/',1,true) then
   assert(#out.assets<32,'station_asset_bound');local d=api.res.constructionRep.get(k);local templates={}
   for i,t in ipairs(d.constructionTemplates) do
    assert(i<=32,'station_template_bound');local params={}
    for _,p in ipairs(t.data.params) do params[#params+1]={key=p.key,default_index=p.defaultIndex,values=p.values} end
    templates[#templates+1]={index=i-1,params=params}
   end
   out.assets[#out.assets+1]={resource=name,id=k,templates=templates}
  end
 end
 local groups=api.engine.getEntitiesWithComponent(C.STATION_GROUP);assert(#groups<=256,'station_group_bound')
 for _,x in ipairs(groups) do
  local g=comp(x,C.STATION_GROUP);assert(#g.stations<=32,'station_member_bound');local members={}
  for _,s in ipairs(g.stations) do
   local station=comp(s,C.STATION);members[#members+1]={id=s,terminal_count=#station.terminals,
    construction=api.engine.system.streetConnectorSystem.getConstructionEntityForStation(s)}
  end
  local n=comp(x,C.NAME);out.groups[#out.groups+1]={id=x,name=n and n.name or 'unnamed',stations=members}
 end
 return out
end
function M.prepare(p)
 assert(p.resource=='::/stations/rail/modular_station/modular_station.con','supported_station_resource_required')
 assert(type(p.template)=='number' and p.template%1==0 and p.template>=0 and p.template<=5,'passenger_template_required')
 assert(type(p.params)=='table' and type(p.params.tracks)=='number' and p.params.tracks%1==0 and p.params.tracks>=1 and p.params.tracks<=8,'station_track_count_required')
 assert(type(p.params.length)=='number' and p.params.length%1==0 and p.params.length>=1 and p.params.length<=5,'station_length_required')
 assert(type(p.position)=='table' and #p.position==3,'station_position_required')
 for _,v in ipairs(p.position) do assert(type(v)=='number' and v==v and math.abs(v)<100000,'station_position_invalid') end
 assert(type(p.angle)=='number' and p.angle==p.angle and math.abs(p.angle)<100,'station_angle_invalid')
 assert(type(p.name)=='string' and #p.name>0 and #p.name<=80,'station_name_required')
 local resource=api.res.constructionRep.find(p.resource);assert(resource>=0,'station_resource_missing')
 local result=api.engine.util.construction.getConstructionResult(p.resource,p.template,p.params)
 assert(#result.subconstructions>=1 and #result.subconstructions<=8,'station_subconstruction_bound')
 assert(result.params.modules,'processed_station_modules_missing')
 local q=api.type.SimpleProposal.new();local c=api.type.SimpleProposal.ConstructionEntity.new()
 c.fileName=p.resource;c.params=result.params;c.name=p.name;c.playerEntity=api.engine.util.getPlayer();c.autoFillSlots=false
 local co,si=math.cos(p.angle),math.sin(p.angle)
 c.transf=api.type.Mat4f.new(api.type.Vec4f.new(co,si,0,0),api.type.Vec4f.new(-si,co,0,0),
  api.type.Vec4f.new(0,0,1,0),api.type.Vec4f.new(p.position[1],p.position[2],p.position[3],1))
 q.constructionsToAdd={c};local ctx=api.type.Context.new();ctx.player=api.engine.util.getPlayer()
 local cmd=api.cmd.makeWorldBuildProposalCmd(q,ctx,false,true);local count=0
 for _ in pairs(result.params.modules) do count=count+1 end
 return cmd,{resource=p.resource,template=p.template,module_count=count,command_constructed=true,
  native_command_submitted=false,game_constructed=false,world_preview='not_performed',attachment='unprobed'}
end
function M.readback(x,p)
 local c=assert(comp(x,C.CONSTRUCTION),'station_construction_missing')
 assert(c.fileName==p.resource,'station_resource_mismatch');assert(#c.stations>=1 and #c.stations<=8,'station_member_bound')
 local pos=xyz(c.transf:getTransl());for i=1,3 do assert(math.abs(pos[i]-p.position[i])<=.01,'station_position_mismatch') end
 assert(#c.frozenEdges<=512 and #c.frozenNodes<=1024,'station_geometry_bound')
 local out={construction=x,resource=c.fileName,position=pos,revision=rev(x),stations={},ports={},
  game_constructed=true,world_mutated_by_readback=false,service='unprobed',physical_operation='unprobed'}
 for _,sid in ipairs(c.stations) do
  assert(api.engine.system.streetConnectorSystem.getConstructionEntityForStation(sid)==x,'station_ownership_mismatch')
  local s=assert(comp(sid,C.STATION),'station_missing');assert(#s.terminals>=1 and #s.terminals<=64,'station_terminal_bound')
  local group=api.engine.system.stationGroupSystem.getStationGroup(sid);local g=assert(comp(group,C.STATION_GROUP),'station_group_missing')
  local index=nil;for i,v in ipairs(g.stations) do if v==sid then index=i-1 end end;assert(index,'station_group_membership_missing')
  local terminals={};for i,t in ipairs(s.terminals) do
   assert(#t.vehicleEdges<=64,'station_terminal_edge_bound');local edges={}
   for _,v in ipairs(t.vehicleEdges) do edges[#edges+1]={entity=v.edgeId.entity,index=v.edgeId.index} end
   terminals[#terminals+1]={index=i-1,vehicle_node={entity=t.vehicleNodeId.entity,index=t.vehicleNodeId.index},vehicle_edges=edges}
  end
  out.stations[#out.stations+1]={id=sid,group=group,station_index=index,terminals=terminals}
 end
 local seen={}
 for _,eid in ipairs(c.frozenEdges) do
  local e=comp(eid,C.BASE_EDGE)
  if e and e.roadType==E.RoadType.TRACK then
   for _,nid in ipairs({e.node0,e.node1}) do if not seen[nid] then
    seen[nid]=true;local incident=api.engine.system.streetSystem.getNodeSegments(nid)
    assert(#incident<=16,'station_port_incidence_bound')
    if #incident==1 then
     assert(#out.ports<32,'station_port_bound');local n=assert(comp(nid,C.BASE_NODE),'station_node_missing')
     local d=nid==e.node0 and e.tangent0 or e.tangent1;local sign=nid==e.node0 and -1 or 1
     out.ports[#out.ports+1]={node=nid,edge=eid,position=xyz(n.position),outward_direction={sign*d.x,sign*d.y,sign*d.z},
      incident_edges={eid},owner=api.engine.system.streetConnectorSystem.getConstructionEntityForNode(nid),identity='exact_TRACK_incidence'}
    end
   end end
  end
 end
 table.sort(out.ports,function(a,b)return a.node<b.node end)
 return out
end
function M.command(p)
 local cmd,prepared=M.prepare(p)
 return cmd,function(r)
  assert(#r.resultEntities<=128,'station_receipt_bound');local found={}
  for _,v in ipairs(r.resultEntities) do
   local x=type(v)=='number' and v or v[1];local c=comp(x,C.CONSTRUCTION)
   if c and c.fileName==p.resource then found[#found+1]=x end
  end
  assert(#found==1,'station_construction_receipt_unresolved');local out=M.readback(found[1],p);out.preparation=prepared;return out
 end
end
return M
