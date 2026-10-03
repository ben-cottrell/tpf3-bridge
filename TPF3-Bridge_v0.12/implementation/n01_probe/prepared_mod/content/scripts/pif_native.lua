-- Focused live operations using C11 native fitting and C13 representation/proposal.
local M={}
local E=api.type["enum"]
local function finite(x) return type(x)=="number" and x==x and math.abs(x)<math.huge end
local function v(a) return api.type.Vec3f.new(a[1],a[2],a[3] or 0) end
local function arr(p) return {p.x,p.y,p.z} end
local function norm(a) local n=math.sqrt(a[1]^2+a[2]^2);assert(finite(n) and n>1e-9,"zero_direction");return {a[1]/n,a[2]/n,0} end
local function distance(a,b) return math.sqrt((a[1]-b[1])^2+(a[2]-b[2])^2) end
local function near(a,b,tol) return math.abs(a[1]-b[1])<=tol and math.abs(a[2]-b[2])<=tol and math.abs(a[3]-b[3])<=tol end
local function angle(a,b) a=norm(a);b=norm(b);return math.acos(math.max(-1,math.min(1,a[1]*b[1]+a[2]*b[2])))*180/math.pi end
local function vector(a) assert(type(a)=="table" and #a>=2 and #a<=3,"invalid_vector");for _,x in ipairs(a) do assert(finite(x),"nonfinite_vector") end end
local function edge(id)
 assert(type(id)=="number" and id>0 and id%1==0,"invalid_edge_id")
 local e=api.engine.getComponent(id,api.type.ComponentType.BASE_EDGE)
 assert(e and e.roadType==E.RoadType.TRACK,"entity_not_TRACK")
 local n0=api.engine.getComponent(e.node0,api.type.ComponentType.BASE_NODE)
 local n1=api.engine.getComponent(e.node1,api.type.ComponentType.BASE_NODE)
 assert(n0 and n1 and near(arr(n0.position),arr(e.position0),.001) and near(arr(n1.position),arr(e.position1),.001),"endpoint_node_mismatch")
 return {id=id,node0=e.node0,node1=e.node1,p0=arr(e.position0),p1=arr(e.position1),t0=arr(e.tangent0),t1=arr(e.tangent1),template=e.roadTemplate,style=e.roadStyle,road_type="TRACK"}
end
local function anchor(p)
 local a=edge(p.anchor_edge);assert(p.anchor_node==a.node0 or p.anchor_node==a.node1,"anchor_not_edge_endpoint")
 local pos,tangent
 if p.anchor_node==a.node1 then pos=a.p1;tangent=a.t1 else pos=a.p0;tangent={-a.t0[1],-a.t0[2],-a.t0[3]} end
 return a,pos,norm(tangent),tangent[3]/math.sqrt(tangent[1]^2+tangent[2]^2)
end
local function in_region(p,region)
 assert(p[1]>=region.min[1] and p[1]<=region.max[1] and p[2]>=region.min[2] and p[2]<=region.max[2] and p[3]>=region.min[3] and p[3]<=region.max[3],"outside_authorised_region")
end
local function sample(g,u)
 local row=api.engine.util.transport.calcPositionAndDirection(g,u,true)
 assert(type(row)=="table" and row[1] and row[2],"sample_contract")
 local p,t=arr(row[1]),arr(row[2]);vector(p);vector(t);norm(t);return p,t
end
local function cubic(c)
 local g=api.type.EdgeGeometry.new();g.type=api.type.EdgeGeometry.Type.CUBIC_SPLINE
 local cs=api.type.EdgeGeometry.CubicSpline.new()
 cs.pos={api.type.Vec2f.new(c.p0[1],c.p0[2]),api.type.Vec2f.new(c.p1[1],c.p1[2])}
 cs.tangent={api.type.Vec2f.new(c.t0[1],c.t0[2]),api.type.Vec2f.new(c.t1[1],c.t1[2])}
 g.cubicSpline=cs;g.height=api.type.Vec2f.new(c.p0[3],c.p1[3]);g.tangent=api.type.Vec2f.new(c.t0[3],c.t1[3]);g.length=c.length
 assert(g.cubicSpline.pos[1].x==cs.pos[1].x and g.cubicSpline.pos[2].y==cs.pos[2].y,"whole_member_writeback_failed")
 return g
end
local function native_geometry(id)
 local n=api.engine.getComponent(id,api.type.ComponentType.TRANSPORT_NETWORK);assert(n and n.edges,"network_unavailable")
 local g,count=nil,0
 for _,row in ipairs(n.edges) do
  if row.transportModes[E.TransportMode.TRAIN]==true or row.transportModes[E.TransportMode.ELECTRIC_TRAIN]==true then g=row.geometry;count=count+1 end
 end
 assert(count==1 and g,"rail_movement_geometry_not_unique");return g
end
function M.inspect(p)
 assert(type(p.edge_ids)=="table" and #p.edge_ids>=1 and #p.edge_ids<=16,"edge_read_bound")
 local out={};for _,id in ipairs(p.edge_ids) do out[#out+1]=edge(id) end
 return {edges=out,game_constructed=false,native_save_identity="unknown",load_epoch="unknown"}
end
function M.fit(p,s,request_id)
 vector(p.end_xy);vector(p.end_direction)
 assert(finite(p.radius) and p.radius>0,"invalid_radius")
 assert(type(p.region)=="table","region_required");vector(p.region.min);vector(p.region.max)
 assert(#p.region.min==3 and #p.region.max==3,"region_needs_xyz")
 for i=1,3 do assert(p.region.max[i]>p.region.min[i],"invalid_region") end
 assert(p.region.max[1]-p.region.min[1]<=400 and p.region.max[2]-p.region.min[2]<=400,"P01_local_region_bound")
 local a,pos,t0,grade=anchor(p);in_region(pos,p.region)
 local t1=norm(p.end_direction)
 local result=api.engine.util.pathfinding.findDubinsPath(v({pos[1],pos[2],0}),v(t0),v({p.end_xy[1],p.end_xy[2],0}),v(t1),p.radius)
 assert(type(result)=="table" and #result>0 and #result<=8,"no_supported_bounded_fit")
 local controls,samples,total,maxerr,maxheading={}, {},0,0,0
 for i,row in ipairs(result) do
  assert(row[2]==true,"unsupported_reverse_geometry")
  local g=row[1];assert(g and finite(g.length) and g.length>0,"invalid_fit_length")
  assert(g.type==api.type.EdgeGeometry.Type.ARC or g.type==api.type.EdgeGeometry.Type.STRAIGHT,"unsupported_fit_family")
  if g.type==api.type.EdgeGeometry.Type.ARC then assert(math.abs(g.arc.radius)>=p.radius-.001,"fit_radius_below_selected_constraint") end
  local p0,d0=sample(g,0);local p1,d1=sample(g,1)
  if i==1 then assert(distance(p0,pos)<=.001 and angle(d0,t0)<=.1,"fit_start_mismatch");p0[1]=pos[1];p0[2]=pos[2]
  else assert(distance(p0,controls[i-1].p1)<=.001 and angle(d0,controls[i-1].t1)<=.1,"fit_join_mismatch");p0[1]=controls[i-1].p1[1];p0[2]=controls[i-1].p1[2] end
  p0[3]=pos[3]+grade*total;p1[3]=pos[3]+grade*(total+g.length)
  d0[3]=grade*g.length;d1[3]=grade*g.length
  local c={p0=p0,p1=p1,t0=d0,t1=d1,length=g.length};controls[i]=c;samples[i]={}
  local cg=cubic(c)
  for _,u in ipairs({0,.25,.5,.75,1}) do
   local np,nd=sample(g,u);local cp,cd=sample(cg,u)
   maxerr=math.max(maxerr,distance(np,cp));if u==0 or u==1 then maxheading=math.max(maxheading,angle(nd,cd)) end
   samples[i][#samples[i]+1]={u=u,pos=np,dir=nd}
   in_region({cp[1],cp[2],p0[3]+u*(p1[3]-p0[3])},p.region)
  end
  total=total+g.length
 end
 assert(total<=800,"fit_length_bound")
 local last=controls[#controls];assert(distance(last.p1,p.end_xy)<=.001 and angle(last.t1,t1)<=.1,"fit_end_mismatch")
 assert(maxerr<=.1 and maxheading<=.1,"sampled_conversion_outside_tolerance")
 s.fits[request_id]={anchor=a,node=p.anchor_node,controls=controls,samples=samples,region=p.region,total_length=total,grade=grade,built=false}
 return {fit_request=request_id,pieces=#controls,total_length=total,start_node=p.anchor_node,start=pos,finish=last.p1,radius=p.radius,grade=grade,sampled_XY_error=maxerr,endpoint_heading_error=maxheading,sampled_only=true,game_constructed=false}
end
function M.readback(f)
 assert(f.ids and #f.ids==#f.controls,"construction_receipt_incomplete")
 local remaining={};for _,id in ipairs(f.ids) do assert(not remaining[id],"duplicate_receipt_edge");remaining[id]=true end
 local current=f.node;local ordered,nodes,observations={},{current},{};local maxerr,maxheading=0,0
 for i,c in ipairs(f.controls) do
  local found,e=nil,nil
  for id in pairs(remaining) do local x=edge(id);if x.node0==current then assert(not found,"ambiguous_connection");found=id;e=x end end
  assert(found,"actual_connection_missing");remaining[found]=nil
  assert(e.template==f.anchor.template and e.style==f.anchor.style,"resource_mismatch")
  assert(near(e.p0,c.p0,.001) and near(e.p1,c.p1,.001) and near(e.t0,c.t0,.001) and near(e.t1,c.t1,.001),"realised_controls_differ")
  local ng=native_geometry(found)
  for _,expected in ipairs(f.samples[i]) do
   local pos,dir=sample(ng,expected.u);maxerr=math.max(maxerr,distance(pos,expected.pos))
   if expected.u==0 or expected.u==1 then maxheading=math.max(maxheading,angle(dir,expected.dir)) end
   -- Movement Z can differ from BaseEdge profile; C13 established that distinction.
   in_region({pos[1],pos[2],c.p0[3]+expected.u*(c.p1[3]-c.p0[3])},f.region)
  end
  ordered[#ordered+1]=found;nodes[#nodes+1]=e.node1;observations[#observations+1]=e;current=e.node1
 end
 for _ in pairs(remaining) do error("unreconciled_returned_edge") end
 assert(maxerr<=.1 and maxheading<=.1,"realised_sampled_shape_failed")
 return {ordered_edges=ordered,ordered_nodes=nodes,edges=observations,connected=true,sampled_XY_error=maxerr,endpoint_heading_error=maxheading,sampled_only=true,game_constructed=true,train_traversal="unprobed",native_effect_history_complete=false}
end
function M.build(p,s,state,request_id,respond)
 assert(p.authorised==true,"explicit_build_option_required")
 local f=s.fits[p.fit_request];assert(f and not f.built,"fit_missing_or_already_consumed")
 local fresh=edge(f.anchor.id)
 assert(fresh.node0==f.anchor.node0 and fresh.node1==f.anchor.node1 and near(fresh.p0,f.anchor.p0,.001) and near(fresh.p1,f.anchor.p1,.001) and near(fresh.t0,f.anchor.t0,.001) and near(fresh.t1,f.anchor.t1,.001) and fresh.template==f.anchor.template and fresh.style==f.anchor.style,"stale_anchor")
 local h=api.res.streetTemplateRep.find(f.anchor.template);local resource=api.res.streetTemplateRep.get(h)
 assert(resource and resource.laneConfigs and #resource.laneConfigs>0,"track_template_unavailable")
 local proposal=api.type.SimpleProposal.new();local segments,newnodes={},{};local count=#f.controls
 for i,c in ipairs(f.controls) do
  local n=api.type.NodeAndEntity.new();n.entity=-count-i;n.comp.position=v(c.p1);newnodes[i]=n
  local e=api.type.SegmentAndEntity.new();e.entity=-i;e.type=1
  e.comp.node0=i==1 and f.node or (-count-i+1);e.comp.node1=n.entity
  e.comp.position0=v(c.p0);e.comp.position1=v(c.p1);e.comp.tangent0=v(c.t0);e.comp.tangent1=v(c.t1)
  e.comp.type=E.BaseEdgeType.NORMAL;e.comp.typeIndex=1;e.comp.laneConfigs=resource.laneConfigs
  e.comp.roadTemplate=f.anchor.template;e.comp.roadStyle=f.anchor.style;e.comp.roadType=E.RoadType.TRACK
  segments[i]=e
 end
 proposal.streetProposal.nodesToAdd=newnodes;proposal.streetProposal.edgesToAdd=segments
 local function callback(res,success,_entities)
  if success~=true then
   -- These are proposal placeholders, not realised identities or effects.
   s.mutationPending=nil
   respond(request_id,"error",{error="native_construction_rejected",game_constructed="unknown",native_command_success=false,retry=false})
   return
  end
  local ok,value=pcall(function()
   local receipt=res.proposal.proposal;f.ids={};for _,e in ipairs(receipt.addedSegments) do f.ids[#f.ids+1]=e.entity end
   f.effects={added_segments=#receipt.addedSegments,added_nodes=#receipt.addedNodes,removed_segments=#receipt.removedSegments,removed_nodes=#receipt.removedNodes}
   assert(success==true,"native_construction_rejected")
   local result=M.readback(f);result.effects=f.effects;result.fit_request=p.fit_request;return result
  end)
  respond(request_id,ok and "ok" or "mutation_unverified",ok and value or {error=tostring(value):sub(1,400),effects=f.effects,returned_edges=f.ids,game_constructed="unknown",retry=false})
 end
 f.built=true;f.build_request=request_id;s.mutationPending=request_id
 local root=state:get() or {};root.pifLive=s;state:set(root)
 local cmd=api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false)
 api.cmd.sendCommand(cmd,callback)
end
function M.extension(p,s,state,request_id,respond)
 local stage,stages,fit="inspect",{},nil
 local function reply(status,value)
  value.stage=stage;value.stages=stages;value.fit=fit
  respond(request_id,status,value)
 end
 local ok,err=pcall(function()
  assert(type(p.brief)=="table" and type(p.execute)=="boolean","invalid_extension_brief")
  local b=p.brief;local inspection=M.inspect({edge_ids={b.anchor_edge}})
  local a=inspection.edges[1];assert(b.anchor_node==a.node0 or b.anchor_node==a.node1,"anchor_not_edge_endpoint")
  stages[#stages+1]={stage="inspect",status="ok"}
  stage="fit";local fit_id=request_id.."_fit";fit=M.fit(b,s,fit_id)
  stages[#stages+1]={stage="fit",status="ok"}
  if not p.execute then reply("ok",{game_constructed=false});return end
  stage="build";assert(not s.mutationPending,"unreconciled_mutation")
  M.build({fit_request=fit_id,authorised=true},s,state,request_id,function(_id,status,value)
   if status~="ok" then reply(status,value);return end
   stages[#stages+1]={stage="build",status="ok"}
   -- A separate fresh native component/geometry query after the build callback's
   -- own readback, using invocation-local receipt rather than lagging script state.
   stage="readback";local verified,result=pcall(M.readback,s.fits[fit_id])
   if not verified then reply("mutation_unverified",{error=tostring(result):sub(1,400),game_constructed=true,retry=false});return end
   stages[#stages+1]={stage="readback",status="ok"}
   s.mutationPending=nil
   reply("ok",{game_constructed=true,readback=result,effects=value.effects})
  end)
 end)
 if not ok then
  stages[#stages+1]={stage=stage,status="error"}
  local uncertain=s.mutationPending==request_id
  reply(uncertain and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),game_constructed=uncertain and "unknown" or false,retry=false})
 end
end
return M
