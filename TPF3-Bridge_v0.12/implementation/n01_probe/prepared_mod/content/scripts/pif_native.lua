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
local function assert_fresh(original)
 local current=edge(original.id)
 assert(current.node0==original.node0 and current.node1==original.node1 and
  near(current.p0,original.p0,.001) and near(current.p1,original.p1,.001) and
  near(current.t0,original.t0,.001) and near(current.t1,original.t1,.001) and
  current.template==original.template and current.style==original.style,"stale_attachment")
 return current
end
local function in_region(p,region)
 assert(p[1]>=region.min[1] and p[1]<=region.max[1] and p[2]>=region.min[2] and p[2]<=region.max[2] and p[3]>=region.min[3] and p[3]<=region.max[3],"outside_authorised_region")
end
local function sample(g,u,forward)
 if forward==nil then forward=true end
 local row=api.engine.util.transport.calcPositionAndDirection(g,u,forward)
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
local function slope(t) return t[3]/math.sqrt(t[1]^2+t[2]^2) end
local function native_geometry(id)
 local n=api.engine.getComponent(id,api.type.ComponentType.TRANSPORT_NETWORK);assert(n and n.edges,"network_unavailable")
 local g,count=nil,0
 for _,row in ipairs(n.edges) do
  if row.transportModes[E.TransportMode.TRAIN]==true or row.transportModes[E.TransportMode.ELECTRIC_TRAIN]==true then g=row.geometry;count=count+1 end
 end
 assert(count==1 and g,"rail_movement_geometry_not_unique");return g
end
-- Engineering checks on native geometry, not a replacement curve generator.
-- Seventeen observations are a sampled check, not continuous curvature/clearance proof.
local function geometry_bounds(g,region,minradius,maxgrade,divisions)
 divisions=divisions or 16
 local minimum,maximum=math.huge,0
 for j=0,divisions do
  local u=j/divisions
  local pos,dir=sample(g,u);in_region(pos,region)
  local grade=math.abs(slope(dir));assert(finite(grade) and grade<=maxgrade+.000001,"realised_sampled_grade_exceeds_limit");maximum=math.max(maximum,grade)
  local radius=math.huge
  if g.type==api.type.EdgeGeometry.Type.ARC then radius=math.abs(g.arc.radius)
  elseif g.type==api.type.EdgeGeometry.Type.CUBIC_SPLINE then
   local c=g.cubicSpline;local p0,p1,t0,t1=c.pos[1],c.pos[2],c.tangent[1],c.tangent[2]
   local function derivative(k)
    return (6*u*u-6*u)*p0[k]+(3*u*u-4*u+1)*t0[k]+(-6*u*u+6*u)*p1[k]+(3*u*u-2*u)*t1[k],
     (12*u-6)*p0[k]+(6*u-4)*t0[k]+(-12*u+6)*p1[k]+(6*u-2)*t1[k]
   end
   local dx,ddx=derivative("x");local dy,ddy=derivative("y");local speed2=dx*dx+dy*dy
   assert(speed2>1e-12,"realised_irregular_curve")
   local cross=math.abs(dx*ddy-dy*ddx);if cross>1e-12 then radius=speed2^1.5/cross end
  else assert(g.type==api.type.EdgeGeometry.Type.STRAIGHT,"unsupported_realised_geometry") end
  assert(radius>=minradius,"realised_sampled_radius_below_limit:"..radius.."<"..minradius);minimum=math.min(minimum,radius)
 end
 return minimum,maximum
end
function M.inspect(p)
 assert(type(p.edge_ids)=="table" and #p.edge_ids>=1 and #p.edge_ids<=16,"edge_read_bound")
 local out={};for _,id in ipairs(p.edge_ids) do
  local e=edge(id)
  if p.geometry==true then
   local g=native_geometry(id);local samples={}
   for _,u in ipairs({0,.25,.5,.75,1}) do local pos,dir=sample(g,u);samples[#samples+1]={u=u,pos=pos,direction=dir} end
   local network=api.engine.getComponent(id,api.type.ComponentType.TRANSPORT_NETWORK);local connections={}
   for _,row in ipairs(network.edges) do if row.transportModes[E.TransportMode.TRAIN]==true then
    for _,n in ipairs(row.conns) do connections[#connections+1]={entity=n.entity,index=n.index} end
   end end
   e.movement_geometry={type=g.type,length=g.length,samples=samples,connections=connections,
    radius=g.type==api.type.EdgeGeometry.Type.ARC and g.arc.radius or nil}
  end
  out[#out+1]=e
  if p.geometry_constraints then
   local q=p.geometry_constraints
   local radius,grade=geometry_bounds(cubic({p0=e.p0,p1=e.p1,t0=e.t0,t1=e.t1,length=distance(e.p0,e.p1)}),q.region,q.radius,q.max_grade)
   e.engineering_checks={sampled_verified=true,min_sampled_radius=radius~=math.huge and radius or nil,max_sampled_grade=grade,samples=17,continuous_proof=false}
  end
  if p.resources==true then
   local resource=api.res.streetTemplateRep.findAndGet(e.template)
   e.resource={track_distance=resource.trackDistance,min_curve_radius=resource.minCurveRadius,
    min_curve_radius_build=resource.minCurveRadiusBuild,road_type=tostring(resource.roadType)}
  end
 end
 local result={edges=out,game_constructed=false,native_save_identity="unknown",load_epoch="unknown"}
 if p.site then
  local q=p.site;assert(type(q.region)=="table","site_region_required");vector(q.region.min);vector(q.region.max)
  assert(#q.region.min==3 and #q.region.max==3,"site_region_xyz_required")
  for i=1,3 do assert(q.region.min[i]<q.region.max[i] and q.region.max[i]-q.region.min[i]<=400,"site_region_bound") end
  assert(type(q.positions)=="table" and #q.positions<=8,"site_terrain_sample_bound")
  local observed,seen={},{};local queried,processed,truncated=0,0,false
  api.engine.system.octreeSystem.findIntersectingEntities(api.type.Box3.new(v(q.region.min),v(q.region.max)),function(id,_volume)
   queried=queried+1;if processed>=256 then truncated=true;return end;processed=processed+1
   if seen[id] then return end;seen[id]=true
   local base=api.engine.getComponent(id,api.type.ComponentType.BASE_EDGE)
   local building=api.engine.getComponent(id,api.type.ComponentType.TOWN_BUILDING)
   local construction=api.engine.getComponent(id,api.type.ComponentType.CONSTRUCTION)
   if base or building or construction then
    if #observed>=32 then truncated=true;return end
    local row={entity=id,base_edge=base~=nil,town_building=building~=nil,construction=construction~=nil}
    if base then row.road_type=tostring(base.roadType);row.TRACK=base.roadType==E.RoadType.TRACK;row.node0=base.node0;row.node1=base.node1;row.p0=arr(base.position0);row.p1=arr(base.position1);row.t0=arr(base.tangent0);row.t1=arr(base.tangent1) end
    observed[#observed+1]=row
   end
  end)
  local terrain={}
  for _,pos in ipairs(q.positions) do
   vector(pos);assert(#pos==2,"terrain_position_needs_xy");assert(pos[1]>=q.region.min[1] and pos[1]<=q.region.max[1] and pos[2]>=q.region.min[2] and pos[2]<=q.region.max[2],"terrain_position_outside_site")
   local xy=api.type.Vec2f.new(pos[1],pos[2]);terrain[#terrain+1]={xy=pos,height=api.engine.terrain.getHeightAt(xy),valid=api.engine.terrain.isValidCoordinate(xy)}
  end
  result.site={region=q.region,entities=observed,terrain=terrain,queried=queried,processed=processed,truncated=truncated,classification="BASE_EDGE,TOWN_BUILDING,CONSTRUCTION only;other incidental categories not exported",game_constructed=false}
 end
 return result
end
-- Explicit small road clearance from a bounded fresh site observation. TRACK is
-- always rejected here; this is not a broad world bulldozer or automatic repair.
function M.clear_obstructions(p,s,state,request_id,respond)
 assert(p.authorised==true and type(p.edges)=="table" and #p.edges>=1 and #p.edges<=8,"road_clearance_bound")
 assert(not s.mutationPending,"unreconciled_mutation");vector(p.region.min);vector(p.region.max)
 for k=1,3 do assert(p.region.min[k]<p.region.max[k] and p.region.max[k]-p.region.min[k]<=400,"road_clearance_region_bound") end
 local ids,seen={},{}
 for _,q in ipairs(p.edges) do
  assert(q.TRACK==false and type(q.entity)=="number" and not seen[q.entity],"only_observed_non_TRACK_edge_clearance")
  local e=api.engine.getComponent(q.entity,api.type.ComponentType.BASE_EDGE)
  assert(e and e.roadType~=E.RoadType.TRACK and tostring(e.roadType)==q.road_type and e.type==E.BaseEdgeType.NORMAL,"clearance_not_ordinary_road")
  assert(e.node0==q.node0 and e.node1==q.node1,"stale_clearance_identity")
  for _,pair in ipairs({{arr(e.position0),q.p0},{arr(e.position1),q.p1},{arr(e.tangent0),q.t0},{arr(e.tangent1),q.t1}}) do assert(near(pair[1],pair[2],.001),"stale_clearance_geometry") end
  in_region(q.p0,p.region);in_region(q.p1,p.region)
  local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(q.entity);assert(not(owner and owner>0),"construction_owned_road_clearance_unsupported")
  seen[q.entity]=true;ids[#ids+1]=q.entity
 end
 local proposal=api.engine.util.proposal.makeSegmentsRemoveProposal(ids)
 s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
 api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(_,success)
  local ok,r=pcall(function()
   assert(success==true,"native_road_clearance_rejected")
   for _,id in ipairs(ids) do assert(not api.engine.entityExists(id) or api.engine.getComponent(id,api.type.ComponentType.BASE_EDGE)==nil,"road_removal_unverified") end
   s.mutationPending=nil;return {game_constructed=true,removed_road_edges=ids,native_effect_history_complete=false,rollback=false}
  end)
  respond(request_id,ok and "ok" or "mutation_unverified",ok and r or {error=tostring(r):sub(1,400),game_constructed="unknown",retry=false})
 end)
end
-- Native normal-offset geometry and sampler, not a Python parallel-curve fitter.
local function offset_geometry(e,spacing)
 local g=cubic({p0=e.p0,p1=e.p1,t0=e.t0,t1=e.t1,length=distance(e.p0,e.p1)})
 local offset=api.type.EdgeGeometry.CubicOffsetSpline.new()
 offset.pos=g.cubicSpline.pos;offset.tangent=g.cubicSpline.tangent;offset.offset=spacing
 g.type=api.type.EdgeGeometry.Type.CUBIC_OFFSET_SPLINE;g.cubicOffsetSpline=offset
 return g
end
local function directed_rows(refs,fresh)
 assert(type(refs)=="table" and #refs>=1 and #refs<=16,"adjacent_reference_bound")
 local rows,seen,last={},{};local nodes={}
 for _,ref in ipairs(refs) do
  assert(type(ref.forward)=="boolean","reference_direction_required")
  local original=fresh and assert_fresh(ref.edge) or edge(ref.edge.id)
  assert(not seen[original.id],"duplicate_reference_edge");seen[original.id]=true
  local e=original
  if not ref.forward then e={id=original.id,node0=original.node1,node1=original.node0,p0=original.p1,p1=original.p0,
   t0={-original.t1[1],-original.t1[2],-original.t1[3]},t1={-original.t0[1],-original.t0[2],-original.t0[3]},template=original.template,style=original.style} end
  assert(not last or last==e.node0,"reference_chain_disconnected");last=e.node1
  nodes[e.node0]=true;nodes[e.node1]=true;rows[#rows+1]=e
 end
 return rows,nodes
end
function M.verify_adjacency(p)
 assert(finite(p.spacing) and math.abs(p.spacing)>0 and math.abs(p.spacing)<=20,"invalid_track_spacing")
 assert(finite(p.tolerance) and p.tolerance>0 and p.tolerance<=.5,"invalid_spacing_tolerance")
 local graded=p.vertical_mode=="native_shared_height_v1";local ztol=graded and p.vertical_tolerance or .001
 assert(p.vertical_mode==nil or graded,"unsupported_vertical_mode")
 assert(finite(ztol) and ztol>0 and (not graded or ztol<=math.min(.05,p.tolerance)),"invalid_vertical_tolerance")
 local maxheight=0
 local refs,refnodes=directed_rows(p.reference,false);local adjacent,adjnodes=directed_rows(p.adjacent,false)
 for node in pairs(adjnodes) do assert(not refnodes[node],"adjacent_tracks_share_node") end
 local maximum,minimum,maxdistance,maxheading,observations=0,math.huge,0,0,0
 local correspondence={};local curved_length=0
 for _,a in ipairs(refs) do
  local original=cubic({p0=a.p0,p1=a.p1,t0=a.t0,t1=a.t1,length=distance(a.p0,a.p1)})
  local wanted=offset_geometry(a,p.spacing)
  local r=geometry_bounds(original,p.region,p.radius,p.max_grade)
  if r<math.huge and angle(a.t0,a.t1)>=1 then curved_length=curved_length+distance(a.p0,a.p1) end
  for j=0,16 do
   local u=j/16;local pos,dir=sample(original,u);local expected,expected_dir=sample(wanted,u)
   local tangent=norm(dir);local dx,dy=expected[1]-pos[1],expected[2]-pos[2]
   local signed=-tangent[2]*dx+tangent[1]*dy
   assert(math.abs(signed-p.spacing)<=p.tolerance and math.abs(tangent[1]*dx+tangent[2]*dy)<=p.tolerance and math.abs(expected[3]-pos[3])<=.001,"native_offset_side_or_normal_mismatch")
   local best,bestdir,bestpos,bestid,bestu=math.huge,nil,nil,nil,nil
   for _,b in ipairs(adjacent) do
    assert(a.id~=b.id,"adjacent_tracks_share_edge")
    local g=cubic({p0=b.p0,p1=b.p1,t0=b.t0,t1=b.t1,length=distance(b.p0,b.p1)})
    local located=g:locate(v(expected),64,p.tolerance)
    if located and finite(located[1]) and located[1]>=0 and located[1]<=1 then
     local q,d=sample(g,located[1]);local error=math.sqrt((q[1]-expected[1])^2+(q[2]-expected[2])^2+(q[3]-expected[3])^2)
     if error<best then best=error;bestdir=d;bestpos=q;bestid=b.id;bestu=located[1] end
    end
   end
   assert(best<=p.tolerance,"sampled_adjacent_alignment_failed")
   local dz=math.abs(bestpos[3]-pos[3]);assert(dz<=ztol,"realised_height_transfer_exceeds_limit");maxheight=math.max(maxheight,dz)
   local heading=angle(expected_dir,bestdir);assert(heading<=1,"sampled_adjacent_heading_failed")
   local ax,ay=bestpos[1]-pos[1],bestpos[2]-pos[2]
   local actual_signed=-tangent[2]*ax+tangent[1]*ay;local along=tangent[1]*ax+tangent[2]*ay
   assert(math.abs(actual_signed-p.spacing)<=p.tolerance and math.abs(along)<=p.tolerance,"realised_normal_spacing_failed")
   correspondence[#correspondence+1]={reference_edge=a.id,reference_u=u,adjacent_edge=bestid,adjacent_u=bestu,
    reference_pos=pos,reference_direction=tangent,adjacent_pos=bestpos,signed_normal=actual_signed,tangential=along,error=best}
   maximum=math.max(maximum,best);minimum=math.min(minimum,math.abs(actual_signed));maxdistance=math.max(maxdistance,math.abs(actual_signed))
   maxheading=math.max(maxheading,heading);observations=observations+1
  end
 end
 for _,b in ipairs(adjacent) do geometry_bounds(cubic({p0=b.p0,p1=b.p1,t0=b.t0,t1=b.t1,length=distance(b.p0,b.p1)}),p.region,p.radius,p.max_grade) end
 return {sampled_verified=true,independent_native_nodes=true,spacing=p.spacing,tolerance=p.tolerance,samples=observations,
  max_sampled_offset_error=maximum,min_sampled_separation=minimum,max_sampled_separation=maxdistance,max_heading_error=maxheading,
  correspondence=correspondence,curved_reference_chord_length=curved_length,
  spacing_convention="horizontal_signed_normal",vertical_tolerance=ztol,max_sampled_height_difference=maxheight,
  continuous_clearance_proof=false,vehicle_clearance="unprobed",game_constructed=false}
end
function M.adjacent(p,s,state,request_id,respond)
 local stage="inspect";local ok,err=pcall(function()
  assert(type(p.execute)=="boolean","invalid_execution_option")
  local refs=directed_rows(p.reference,true);local controls,samples={},{}
  local template=api.res.streetTemplateRep.findAndGet(refs[1].template)
  assert(finite(template.trackDistance) and template.trackDistance>0 and template.trackDistance<=20,"native_track_distance_unavailable")
  assert(math.abs(math.abs(p.spacing)-template.trackDistance)<=.001,"spacing_must_match_native_template")
  local graded=p.vertical_mode=="native_shared_height_v1"
  assert(p.vertical_mode==nil or graded,"unsupported_vertical_mode")
  local ztol=graded and p.vertical_tolerance or .001
  assert(finite(ztol) and ztol>0 and (not graded or ztol<=math.min(.05,p.tolerance)),"invalid_vertical_tolerance")
  local reference_length,offset_length=0,0;local geometries={}
  for i,e in ipairs(refs) do
   if not graded then assert(math.abs(e.p1[3]-e.p0[3])<=.001 and math.abs(slope(e.t0))<=.000001 and math.abs(slope(e.t1))<=.000001,"vertical_mode_required") end
   local base=api.engine.getComponent(e.id,api.type.ComponentType.BASE_EDGE)
   assert(base.type==E.BaseEdgeType.NORMAL and #base.objects==0,"unsupported_adjacent_reference")
   local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(e.id);assert(not(owner and owner>0),"construction_owned_reference")
   assert(e.template==refs[1].template and e.style==refs[1].style,"incompatible_reference_resources")
   local original=cubic({p0=e.p0,p1=e.p1,t0=e.t0,t1=e.t1,length=distance(e.p0,e.p1)})
   geometry_bounds(original,p.region,p.radius,p.max_grade)
   local g=offset_geometry(e,p.spacing);local p0,t0=sample(g,0);local p1,t1=sample(g,1)
   controls[i]={p0=p0,p1=p1,t0=t0,t1=t1,length=distance(p0,p1)};geometries[i]=g;samples[i]={}
   -- Bounded native samples estimate each chain's XY length. This is a height
   -- representation transfer, not a fitter or a continuous length proof.
   local rp,op=sample(original,0),p0
   for j=1,32 do local rq=sample(original,j/32);local oq=sample(g,j/32)
    reference_length=reference_length+distance(rp,rq);offset_length=offset_length+distance(op,oq);rp,op=rq,oq
   end
  end
  assert(reference_length>0 and offset_length>0,"offset_length_unavailable")
  local grade_scale=reference_length/offset_length
  if graded then
   -- One shared length conversion keeps internal grades continuous across the
   -- native piece joins. Heights at every reference boundary remain exact;
   -- native cubic interpolation must stay within the explicit interior Z budget.
   -- Fixed real attachment grades take precedence at the two outer boundaries.
   for i,c in ipairs(controls) do
    local first,last=slope(refs[i].t0)*grade_scale,slope(refs[i].t1)*grade_scale
    if p.attachments and i==1 then local _,_,_,g=anchor(p.attachments.source);first=g end
    if p.attachments and i==#controls then local _,_,_,g=anchor(p.attachments.target);last=-g end
    c.t0[3]=first*math.sqrt(c.t0[1]^2+c.t0[2]^2);c.t1[3]=last*math.sqrt(c.t1[1]^2+c.t1[2]^2)
   end
  end
  local max_height_error=0
  for i,c in ipairs(controls) do
   if i>1 then assert(near(c.p0,controls[i-1].p1,.001) and angle(c.t0,controls[i-1].t1)<=.1 and math.abs(slope(c.t0)-slope(controls[i-1].t1))<=.000001,"native_offset_join_failed") end
   geometry_bounds(cubic(c),p.region,p.radius,p.max_grade)
   for j=0,32 do local u=j/32;local pos,dir=sample(geometries[i],u);local q,d=sample(cubic(c),u)
    local dz=math.abs(pos[3]-q[3]);max_height_error=math.max(max_height_error,dz)
    assert(distance(pos,q)<=p.tolerance and dz<=ztol and angle(dir,d)<=1,"native_offset_conversion_failed")
    samples[i][#samples[i]+1]={u=u,pos=graded and q or pos,dir=graded and d or dir,base_pos=q}
   end
  end
  local attachment=nil
  if p.attachments then
   local a,pos,dir,grade=anchor(p.attachments.source);local z,zpos,zdir,zgrade=anchor(p.attachments.target)
   assert(a.id~=z.id and p.attachments.source.anchor_node~=p.attachments.target.anchor_node,"distinct_offset_attachments_required")
   for _,q in ipairs({p.attachments.source,p.attachments.target}) do
    local ids=api.engine.system.streetSystem.getNodeSegments(q.anchor_node)
    assert(#ids==1 and ids[1]==q.anchor_edge,"offset_attachment_not_free")
   end
   assert(a.template==refs[1].template and z.template==a.template and a.style==refs[1].style and z.style==a.style,"incompatible_offset_attachments")
   local first,last=controls[1],controls[#controls]
   assert(near(pos,first.p0,.001) and near(zpos,last.p1,.001),"offset_boundary_position_incompatible")
   assert(angle(dir,first.t0)<=.1 and angle({-zdir[1],-zdir[2],0},last.t1)<=.1,"offset_boundary_direction_incompatible")
   assert(math.abs(grade-slope(first.t0))<=.000001 and math.abs(-zgrade-slope(last.t1))<=.000001,"offset_boundary_grade_incompatible")
   attachment={anchor=a,node=p.attachments.source.anchor_node,target={edge=z,node=p.attachments.target.anchor_node,direction={-zdir[1],-zdir[2],0}}}
  end
  stage="preflight"
  local value={game_constructed=false,controls=controls,native_track_distance=template.trackDistance,spacing=p.spacing,
   native_geometry="CUBIC_OFFSET_SPLINE",spacing_convention="horizontal_signed_normal",vertical_mode=p.vertical_mode,vertical_tolerance=ztol,
   height_transfer=graded and "native_cubic_shared_boundary_heights_length_scaled_grades_fixed_attachments" or "level_native_offset",
   reference_sampled_XY_length=reference_length,offset_sampled_XY_length=offset_length,grade_scale=grade_scale,max_sampled_height_transfer_error=max_height_error,sampled_only=true}
  if not p.execute then respond(request_id,"ok",value);return end
  assert(not s.mutationPending,"unreconciled_mutation");directed_rows(p.reference,true)
  local proposal=api.type.SimpleProposal.new();local nodes,segments={},{}
  local nodeids={}
  for i=1,#controls+1 do
   if attachment and i==1 then nodeids[i]=attachment.node
   elseif attachment and i==#controls+1 then nodeids[i]=attachment.target.node
   else local node=api.type.NodeAndEntity.new();node.entity=-100-i;node.comp.position=v(i==1 and controls[1].p0 or controls[i-1].p1);nodes[#nodes+1]=node;nodeids[i]=node.entity end
  end
  for i,c in ipairs(controls) do local seg=api.type.SegmentAndEntity.new();seg.entity=-i;seg.type=1
   seg.comp=api.engine.getComponent(refs[i].id,api.type.ComponentType.BASE_EDGE):clone()
   seg.comp.node0=nodeids[i];seg.comp.node1=nodeids[i+1];seg.comp.position0=v(c.p0);seg.comp.position1=v(c.p1);seg.comp.tangent0=v(c.t0);seg.comp.tangent1=v(c.t1);segments[i]=seg
  end
  proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd=segments
  stage="build";s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
  api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
   local ids={};local checked,result=pcall(function()
    assert(success==true,"native_adjacent_construction_rejected")
    local other_ids={}
    for _,item in ipairs(res.proposal.proposal.addedSegments) do
     local e=api.engine.getComponent(item.entity,api.type.ComponentType.BASE_EDGE)
     if e and e.roadType==E.RoadType.TRACK then ids[#ids+1]=item.entity else other_ids[#other_ids+1]=item.entity end
    end
    value.other_added_segments=other_ids
    local first
    for _,id in ipairs(ids) do local e=edge(id);if near(e.p0,controls[1].p0,.001) then assert(not first,"ambiguous_adjacent_start");first=e.node0 end end
    local f={anchor=attachment and attachment.anchor or refs[1],target=attachment and attachment.target or nil,node=first,ids=ids,controls=controls,samples=samples,region=p.region,grade=slope(controls[1].t0),end_grade=slope(controls[#controls].t1),max_grade=p.max_grade,min_radius=p.radius}
    local rb=M.readback(f);local paired={};for _,id in ipairs(rb.ordered_edges) do paired[#paired+1]={edge={id=id},forward=true} end
    local checked=M.verify_adjacency({reference=p.reference,adjacent=paired,spacing=p.spacing,tolerance=p.tolerance,region=p.region,radius=p.radius,max_grade=p.max_grade,vertical_mode=p.vertical_mode,vertical_tolerance=p.vertical_tolerance})
    directed_rows(p.reference,true);s.mutationPending=nil
    value.game_constructed=true;value.readback=rb;value.adjacency=checked;return value
   end)
   respond(request_id,checked and "ok" or "mutation_unverified",checked and result or {error=tostring(result):sub(1,400),stage=stage,returned_edges=ids,game_constructed="unknown",retry=false})
  end)
 end)
 if not ok then respond(request_id,"error",{error=tostring(err):sub(1,400),stage=stage,game_constructed=false,retry=false}) end
end
local function region_check(region)
 assert(type(region)=="table","region_required");vector(region.min);vector(region.max)
 assert(#region.min==3 and #region.max==3,"region_needs_xyz")
 for i=1,3 do assert(region.max[i]>region.min[i] and region.max[i]-region.min[i]<=400,"discovery_region_bound") end
end
local function inside(pos,r)
 for i=1,3 do if pos[i]<r.min[i] or pos[i]>r.max[i] then return false end end;return true
end
local function incidence(id)
 local segments=api.engine.system.streetSystem.getNodeSegments(id)
 assert(type(segments)=="table","native_incidence_unavailable")
 local ids,seen={},{};for _,eid in ipairs(segments) do assert(not seen[eid],"duplicate_native_incidence");seen[eid]=true;ids[#ids+1]=eid end
 table.sort(ids)
 local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForNode(id)
 assert(owner==nil or type(owner)=="number","construction_owner_unavailable")
 return ids,owner
end
function M.discover(p,request_id)
 region_check(p.region)
 assert(type(p.max_edges)=="number" and p.max_edges%1==0 and p.max_edges>=1 and p.max_edges<=16,"discovery_edge_bound")
 local ids,seen={},{};local queried,processed,truncated=0,0,false
 api.engine.system.octreeSystem.findIntersectingEntities(api.type.Box3.new(v(p.region.min),v(p.region.max)),function(id,_volume)
  queried=queried+1
  if processed>=256 then truncated=true;return end
  processed=processed+1
  if seen[id] then return end;seen[id]=true
  local base=api.engine.getComponent(id,api.type.ComponentType.BASE_EDGE)
  if base and base.roadType==E.RoadType.TRACK then
   if #ids<p.max_edges then ids[#ids+1]=id else truncated=true end
  end
 end)
 table.sort(ids);local edges,candidates={},{}
 for _,id in ipairs(ids) do
  local a=edge(id);edges[#edges+1]=a
  for _,node in ipairs({a.node0,a.node1}) do
   local _,pos,direction,grade=anchor({anchor_edge=id,anchor_node=node})
   if inside(pos,p.region) then
    local all,owner=incidence(node);local free=#all==1 and all[1]==id and not (owner and owner>0)
    local retained={};for i=1,math.min(#all,16) do retained[i]=all[i] end
    candidates[#candidates+1]={ref=request_id..":E"..id..":N"..node,edge_id=id,node_id=node,pos=pos,
     outward_direction=direction,grade=grade,template=a.template,style=a.style,edge_snapshot=a,
     eligible=free,eligibility=free and "single_incident_TRACK_unowned" or "not_free_or_construction_owned",
     incident_count=#all,incident_edges=retained,incidence_complete=true,incident_output_truncated=#all>16,
     construction_owner=owner or "none"}
   end
  end
 end
 return {edges=edges,candidates=candidates,region=p.region,queried_candidates=queried,processed_candidates=processed,
  edge_count=#edges,candidate_count=#candidates,truncated=truncated,complete=not truncated,game_constructed=false,
  native_save_identity="unknown",load_epoch="unknown",identity_scope="current_adapter_session_only"}
end
-- Bounded named station catalogue followed by exact external TRACK incidence.
function M.station_lookup(p)
 assert(type(p.name)=="string" and #p.name>0 and #p.name<=120,"station_name_required")
 assert(finite(p.max_groups) and p.max_groups%1==0 and p.max_groups>=1 and p.max_groups<=256,"station_group_bound")
 assert(finite(p.max_external_edges) and p.max_external_edges%1==0 and p.max_external_edges>=1 and p.max_external_edges<=64,"external_track_bound")
 assert(finite(p.max_lead_distance) and p.max_lead_distance>0 and p.max_lead_distance<=800,"external_distance_bound")
 local out={name=p.name,matches={},ports={},external_edges={},game_constructed=false,native_save_identity="unknown",load_epoch="unknown",platform_route_association="unprobed"}
 local groups=api.engine.getEntitiesWithComponent(api.type.ComponentType.STATION_GROUP)
 out.group_count=#groups
 if #groups>p.max_groups then out.outcome="lookup_budget_exhausted";out.complete=false;return out end
 for _,id in ipairs(groups) do
  local name=api.engine.getComponent(id,api.type.ComponentType.NAME)
  if name and name.name==p.name then out.matches[#out.matches+1]={group_id=id,name=name.name} end
 end
 if #out.matches~=1 then out.outcome=#out.matches==0 and "not_found" or "ambiguous_station";out.complete=true;return out end
 local id=out.matches[1].group_id;local group=api.engine.getComponent(id,api.type.ComponentType.STATION_GROUP)
 assert(group and #group.stations<=32,"station_member_bound")
 local function revision(eid) local r=api.engine.getRevision(eid);return {r.num[1],r.num[2],r.num[3]} end
 out.group_id=id;out.group_revision=revision(id);out.stations={};out.constructions={}
 local constructors,owned,frozen_nodes={},{},{}
 for _,sid in ipairs(group.stations) do
  local station=api.engine.getComponent(sid,api.type.ComponentType.STATION)
  assert(station and #station.terminals<=64,"station_terminal_bound")
  local cid=api.engine.system.streetConnectorSystem.getConstructionEntityForStation(sid)
  assert(cid and cid>0,"station_construction_unavailable")
  local terminals={}
  for index,t in ipairs(station.terminals) do
   assert(#t.vehicleEdges<=64,"station_terminal_edge_bound")
   local edge_ids={}
   for _,place in ipairs(t.vehicleEdges) do edge_ids[#edge_ids+1]=place.edgeId.entity end
   terminals[#terminals+1]={index=index,vehicle_edges=edge_ids,vehicle_node={entity=t.vehicleNodeId.entity,index=t.vehicleNodeId.index}}
  end
  out.stations[#out.stations+1]={station_id=sid,construction_id=cid,terminal_count=#station.terminals,terminals=terminals}
  constructors[cid]=true
 end
 local frozen_count,node_count=0,0;local seeds={}
 for cid in pairs(constructors) do
  local c=api.engine.getComponent(cid,api.type.ComponentType.CONSTRUCTION)
  assert(c and #c.frozenEdges<=512,"station_frozen_track_bound")
  local row={construction_id=cid,revision=revision(cid),resource=c.fileName,position=arr(c.transf:getTransl()),frozen_tracks={}}
  for _,eid in ipairs(c.frozenEdges) do
   local base=api.engine.getComponent(eid,api.type.ComponentType.BASE_EDGE)
   if base and base.roadType==E.RoadType.TRACK then
    frozen_count=frozen_count+1;assert(frozen_count<=512,"station_frozen_track_bound")
    owned[eid]=cid;row.frozen_tracks[#row.frozen_tracks+1]={edge_id=eid,node0=base.node0,node1=base.node1}
    for _,nid in ipairs({base.node0,base.node1}) do if not frozen_nodes[nid] then
     node_count=node_count+1;assert(node_count<=1024,"station_node_bound")
     frozen_nodes[nid]=true;seeds[#seeds+1]={node=nid,construction_id=cid,frozen_edge=eid}
    end end
   end
  end
  out.constructions[#out.constructions+1]=row
 end
 assert(#out.constructions>=1 and #out.constructions<=8,"station_construction_bound")
 table.sort(out.constructions,function(a,b) return a.construction_id<b.construction_id end)
 table.sort(seeds,function(a,b) return a.node<b.node end)
 local seen,queue,ports={}, {},{};local truncated=false
 local function extend(seed,path,origin)
  local all=incidence(seed.node);assert(#all<=16,"station_node_incidence_bound")
  for _,eid in ipairs(all) do if not owned[eid] and not seen[eid] then
   local base=api.engine.getComponent(eid,api.type.ComponentType.BASE_EDGE)
   local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(eid)
   if base and base.roadType==E.RoadType.TRACK and not(owner and owner>0) then
    if #out.external_edges>=p.max_external_edges then truncated=true
    else
     seen[eid]=true;local e=edge(eid);out.external_edges[#out.external_edges+1]=e
     local nextnode=e.node0==seed.node and e.node1 or e.node0
     local chain={};for _,k in ipairs(path) do chain[#chain+1]=k end;chain[#chain+1]=eid
     local start=origin or arr(api.engine.getComponent(seed.node,api.type.ComponentType.BASE_NODE).position)
     local _,pos,dir,grade=anchor({anchor_edge=eid,anchor_node=nextnode})
     if math.sqrt((pos[1]-start[1])^2+(pos[2]-start[2])^2+(pos[3]-start[3])^2)>p.max_lead_distance then truncated=true
     else
      local incident,node_owner=incidence(nextnode)
      if #incident==1 and incident[1]==eid and not(node_owner and node_owner>0) and not ports[nextnode] then
       ports[nextnode]=true
       out.ports[#out.ports+1]={edge_id=eid,node_id=nextnode,pos=pos,outward_direction=dir,grade=grade,template=e.template,style=e.style,edge_snapshot=e,
        incident_count=1,incident_edges=incident,incidence_complete=true,incident_output_truncated=false,construction_owner=node_owner or "none",eligible=true,
        association={kind="exact_TRACK_incidence_chain",construction_id=seed.construction_id,frozen_edge=seed.frozen_edge,edge_ids=chain,platform_terminal="unknown",native_TRAIN_route="unprobed"}}
      else queue[#queue+1]={node=nextnode,construction_id=seed.construction_id,frozen_edge=seed.frozen_edge,path=chain,origin=start} end
     end
    end
   end
  end end
 end
 for _,seed in ipairs(seeds) do extend(seed,{}) end
 local at=1;while at<=#queue do local q=queue[at];at=at+1;extend(q,q.path,q.origin) end
 table.sort(out.ports,function(a,b) return a.node_id<b.node_id end)
 for _,port in ipairs(out.ports) do
  local matched={}
  for _,station in ipairs(out.stations) do
   for _,terminal in ipairs(station.terminals) do
    for _,terminal_edge in ipairs(terminal.vehicle_edges) do
     if terminal_edge==port.association.frozen_edge then
      matched[#matched+1]={station_id=station.station_id,terminal_index=terminal.index,vehicle_edge=terminal_edge}
     end
    end
   end
  end
  port.association.terminal_identity_matches=matched
  port.association.platform_terminal=#matched==1 and matched[1] or "unknown"
 end
 out.complete=not truncated;out.truncated=truncated;out.outcome=truncated and "external_observation_incomplete" or "resolved"
 out.free_connection_count=#out.ports;out.frozen_TRACK_count=frozen_count;out.processed_station_nodes=node_count
 return out
end
local function interior_location(a,p)
 local base=api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)
 assert(base.type==E.BaseEdgeType.NORMAL and #base.objects==0,"unsupported_split_edge_type_or_objects")
 local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(a.id)
 assert(not (owner and owner>0),"construction_owned_split_unsupported")
 for _,id in ipairs({a.node0,a.node1}) do local _,owner=incidence(id);assert(not (owner and owner>0),"construction_owned_split_unsupported") end
 vector(p.guide_xyz);vector(p.travel_direction)
 assert(finite(p.placement_tolerance) and p.placement_tolerance>0 and p.placement_tolerance<=10,"invalid_placement_tolerance")
 local g=cubic({p0=a.p0,p1=a.p1,t0=a.t0,t1=a.t1,length=1})
 local located=g:locate(v(p.guide_xyz),32,p.placement_tolerance)
 assert(located[2]==true and finite(located[1]) and located[1]>=.05 and located[1]<=.95,"no_supported_interior_location")
 local u=located[1];local at=g:calcPos(u)
 local pos,tangent=arr(at[1]),arr(at[2]);local d=norm(tangent);local forward=true
 if angle(d,p.travel_direction)>angle({-d[1],-d[2],0},p.travel_direction) then forward=false;d={-d[1],-d[2],0} end
 assert(angle(d,p.travel_direction)<=p.heading_tolerance_deg,"interior_direction_mismatch")
 assert((pos[1]-p.guide_xyz[1])^2+(pos[2]-p.guide_xyz[2])^2+(pos[3]-p.guide_xyz[3])^2<=p.placement_tolerance^2,"interior_location_outside_tolerance")
 return {edge_id=a.id,edge_snapshot=a,parameter=u,pos=pos,outward_direction=d,grade=slope(tangent)*(forward and 1 or -1),
  canonical_forward=forward,interior_eligible=true,placement_tolerance=p.placement_tolerance}
end
function M.discover_interior(p,request_id)
 local result=M.discover(p,request_id);result.candidates={};result.rejections={}
 for _,a in ipairs(result.edges) do
  local ok,c=pcall(interior_location,a,p)
  if ok then c.ref=request_id..":E"..a.id..":U"..c.parameter;result.candidates[#result.candidates+1]=c
  else result.rejections[#result.rejections+1]={edge=a.id,error=tostring(c):sub(1,250)} end
 end
 result.candidate_count=#result.candidates;return result
end
function M.discover_junction(p,request_id)
 local result=M.discover(p,request_id)
 for _,c in ipairs(result.candidates) do
  c.junction_eligible=false
  if c.incident_count==2 and c.incidence_complete and not c.incident_output_truncated and
   not (type(c.construction_owner)=="number" and c.construction_owner>0) then
   local other=c.incident_edges[1]==c.edge_id and c.incident_edges[2] or c.incident_edges[1]
   local ok,t=pcall(edge,other)
   if ok and (t.node0==c.node_id or t.node1==c.node_id) then
    local _,_,d,g=anchor({anchor_edge=other,anchor_node=c.node_id})
    if t.template==c.template and t.style==c.style and angle(c.outward_direction,{-d[1],-d[2],0})<=.1 and math.abs(c.grade+g)<=.000001 then
     c.junction_eligible=true;c.junction_eligibility="two_incident_compatible_TRACK_unowned"
     c.through_edge=other;c.through_snapshot=t
    end
   end
  end
 end
 return result
end
local function selected_attachments(p,junction)
 assert(type(p.source)=="table" and type(p.target)=="table","selected_candidates_required")
 assert(p.execute==nil or type(p.execute)=="boolean","invalid_selected_execution")
 for _,c in ipairs({p.source,p.target}) do
  local current=assert_fresh(c.edge_snapshot)
  assert(current.id==c.edge_id and (current.node0==c.node_id or current.node1==c.node_id),"selected_endpoint_mismatch")
  local all,owner=incidence(c.node_id)
  if junction and c==p.source then
   local through=assert_fresh(c.through_snapshot)
   assert(#all==2 and ((all[1]==c.edge_id and all[2]==through.id) or (all[2]==c.edge_id and all[1]==through.id)) and
    through.id==c.through_edge and not (owner and owner>0),"selected_junction_not_supported")
   local _,_,d,g=anchor({anchor_edge=through.id,anchor_node=c.node_id})
   local _,_,incoming,grade=anchor({anchor_edge=c.edge_id,anchor_node=c.node_id})
   assert(through.template==current.template and through.style==current.style and
    angle(incoming,{-d[1],-d[2],0})<=.1 and math.abs(grade+g)<=.000001,"unsupported_through_alignment")
  else assert(#all==1 and all[1]==c.edge_id and not (owner and owner>0),"selected_endpoint_not_free") end
 end
end
-- Existing two-edge through attachment only; native routing decides movement support.
function M.junction(p,s,state,request_id,respond)
 selected_attachments(p,true)
 local source=p.source;local through=source.through_snapshot;local incoming=source.edge_snapshot
 local function other(e) return e.node0==source.node_id and e.node1 or e.node0 end
 local route_params={source_edge=source.edge_id,source_node=other(incoming),target_edge=through.id,target_node=other(through),
  mode="TRAIN",max_length=p.max_route_length,required_edges={source.edge_id,through.id}}
 local before=M.route(route_params)
 assert(before.requested_route_verified,"existing_through_route_unverified")
 M.extension({execute=p.execute==true,brief={anchor_edge=source.edge_id,anchor_node=source.node_id,
  target_edge=p.target.edge_id,target_node=p.target.node_id,radius=p.radius,region=p.region,vertical=p.vertical}},s,state,request_id,
  function(id,status,value)
   value.through_before=before
   if status=="ok" and p.execute then
    local ok,err=pcall(function()
     assert_fresh(through);assert_fresh(incoming)
     local ids=incidence(source.node_id);local expected={[incoming.id]=true,[through.id]=true,[value.readback.ordered_edges[1]]=true}
     assert(#ids==3,"junction_incidence_mismatch")
     for _,eid in ipairs(ids) do assert(expected[eid],"junction_incidence_mismatch");edge(eid) end
     route_params.junction_node=source.node_id
     local after=M.route(route_params)
     value.through_after=after;assert(after.requested_route_verified,"realised_through_route_unverified")
     local target=p.target.edge_snapshot;local required={incoming.id,target.id}
     for _,eid in ipairs(value.readback.ordered_edges) do required[#required+1]=eid end
     local branch=M.route({source_edge=incoming.id,source_node=other(incoming),target_edge=target.id,
      target_node=target.node0==p.target.node_id and target.node1 or target.node0,mode="TRAIN",
      max_length=p.max_route_length,required_edges=required,junction_node=source.node_id,
      geometry_constraints={edge_ids=value.readback.ordered_edges,junction_node=source.node_id,
       region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}})
     value.branch_after=branch;assert(branch.requested_route_verified,"realised_branch_route_unverified")
     value.readback.attachments.source_incident_edges=ids
     value.junction={node=source.node_id,incoming_edge=incoming.id,through_edge=through.id,branch_edge=value.readback.ordered_edges[1],
      incident_edges=ids,exact_native_identity=true,through_route_verified=true,branch_geometry_verified=true,
      min_sampled_radius=branch.min_sampled_radius,max_sampled_grade=branch.max_sampled_grade}
    end)
    if not ok then status="mutation_unverified";value.error=tostring(err):sub(1,400);value.game_constructed=true;value.retry=false end
   end
   respond(id,status,value)
  end,true,{node=source.node_id,radius=p.radius})
end
function M.connect_selected(p,s,state,request_id,respond)
 selected_attachments(p)
 M.extension({execute=p.execute==true,brief={anchor_edge=p.source.edge_id,anchor_node=p.source.node_id,
  target_edge=p.target.edge_id,target_node=p.target.node_id,radius=p.radius,region=p.region,vertical=p.vertical}},s,state,request_id,respond,true)
end
local function node_id(n)
 assert(n and type(n.entity)=="number" and type(n.index)=="number","transport_node_identity_unavailable")
 return {entity=n.entity,index=n.index}
end
local function same_node(a,b) return a.entity==b.entity and a.index==b.index end
local function rail_lane(id,mode,junction_node,junction_nodes)
 local base=edge(id);local n=api.engine.getComponent(id,api.type.ComponentType.TRANSPORT_NETWORK)
 assert(n and n.edges,"transport_network_unavailable")
 local found,index=nil,nil
 for i,row in ipairs(n.edges) do
  if row.transportModes[mode]==true then assert(not found,"ambiguous_rail_transport_lane");found=row;index=i-1 end
 end
 assert(found and #found.conns==2,"rail_transport_lane_unavailable")
 local p0=sample(found.geometry,0);local p1=sample(found.geometry,1)
 -- Geometry verifies the native row's orientation; identities come from conns.
 local trimmed=junction_node and (base.node0==junction_node or base.node1==junction_node)
 for _,n in ipairs(junction_nodes or {}) do if base.node0==n or base.node1==n then trimmed=true end end
 if trimmed then
  -- Turnout movement edges are trimmed. Native connection entities establish
  -- correspondence; their indexes name distinct native junction ports.
  assert(found.conns[1].entity==base.node0 and found.conns[2].entity==base.node1,"junction_transport_identity_mismatch")
 else assert(distance(p0,base.p0)<=.001 and distance(p1,base.p1)<=.001,"transport_orientation_unestablished") end
 return base,found,index
end
function M.route(p)
 assert(p.mode=="TRAIN" or p.mode=="ELECTRIC_TRAIN","unsupported_route_mode")
 assert(finite(p.max_length) and p.max_length>0 and p.max_length<=8000,"invalid_route_length_bound")
 assert(type(p.required_edges)=="table" and #p.required_edges>=1 and #p.required_edges<=32,"route_required_edge_bound")
 local mode=E.TransportMode[p.mode]
 local a,start,index=rail_lane(p.source_edge,mode,p.junction_node,p.junction_nodes);local b,finish,target_index=rail_lane(p.target_edge,mode,p.junction_node,p.junction_nodes)
 assert((p.source_edge~=p.target_edge or p.single_edge==true) and p.source_node~=p.target_node,"distinct_route_attachments_required")
 assert(p.source_node==a.node0 or p.source_node==a.node1,"source_not_edge_endpoint")
 assert(p.target_node==b.node0 or p.target_node==b.node1,"target_not_edge_endpoint")
 local dir=p.source_node==a.node0
 local origin=node_id(start.conns[dir and 1 or 2])
 local destination=node_id(finish.conns[p.target_node==b.node0 and 1 or 2])
 local expected,seen={},{}
 for _,id in ipairs(p.required_edges) do edge(id);assert(not expected[id],"duplicate_required_edge");expected[id]=true end
 local native_origin=start.conns[dir and 1 or 2]
 local native_destination=finish.conns[p.target_node==b.node0 and 1 or 2]
 local path=api.engine.util.pathfinding.findPathNodeToNode({native_origin},{native_destination},{mode})
 assert(type(path)=="table","native_path_result_contract")
 local out={native_path_found=#path>0,requested_route_verified=false,path={},path_count=#path,truncated=#path>64,
  source={base_edge=p.source_edge,base_node=p.source_node,transport_edge={entity=p.source_edge,index=index},forward=dir,transport_origin=origin},
  target={base_edge=p.target_edge,base_node=p.target_node,transport_destination=destination},
  mode=p.mode,max_length=p.max_length,query="api.engine.util.pathfinding.findPathNodeToNode",game_constructed=false,
  native_search_length_bound=false,length_bound_is_acceptance_only=true,
  train_traversal="unprobed",reservation_availability="unprobed",native_save_identity="unknown",load_epoch="unknown"}
 if #path==0 then out.reason="no_native_path_returned";return out end
 if out.truncated then out.reason="native_path_observation_bound";return out end
 local previous,length,continuous=nil,0,true
 for i,item in ipairs(path) do
  local id,forward=item[1],item[2]
  assert(id and type(forward)=="boolean","native_path_entry_contract")
  local network=api.engine.getComponent(id.entity,api.type.ComponentType.TRANSPORT_NETWORK)
  local row=network and network.edges and network.edges[id.index+1]
  assert(row and #row.conns==2 and row.transportModes[mode]==true,"returned_transport_edge_unavailable")
  local from=node_id(row.conns[forward and 1 or 2]);local to=node_id(row.conns[forward and 2 or 1])
  if previous and not same_node(previous,from) then continuous=false end
  if row.forwardOnly and not forward then continuous=false end
  local base=api.engine.getComponent(id.entity,api.type.ComponentType.BASE_EDGE)
  local track=base and base.roadType==E.RoadType.TRACK or false
  if track then seen[id.entity]=true end
  assert(finite(row.geometry.length) and row.geometry.length>=0,"native_path_length_unavailable")
  length=length+row.geometry.length
  if p.geometry_constraints then
   local q=p.geometry_constraints;local check=q.all_path==true or id.entity==q.junction_node
   for _,eid in ipairs(q.edge_ids) do if id.entity==eid then check=true end end
   if check then
    local radius,grade=geometry_bounds(row.geometry,q.region,q.radius,q.max_grade)
    out.min_sampled_radius=math.min(out.min_sampled_radius or math.huge,radius)
    out.max_sampled_grade=math.max(out.max_sampled_grade or 0,grade)
   end
  end
  out.path[i]={edge={entity=id.entity,index=id.index},forward=forward,from=from,to=to,
   confirmed_TRACK=track,forward_only=row.forwardOnly,length=row.geometry.length}
  previous=to
 end
 local missing={};for _,id in ipairs(p.required_edges) do if not seen[id] then missing[#missing+1]=id end end
 out.missing_required_edges=missing;out.total_path_length=length;out.transport_continuous=continuous
 out.origin_matches=same_node(out.path[1].from,origin);out.destination_matches=same_node(previous,destination)
 out.source_approach_in_path=seen[p.source_edge]==true;out.target_approach_in_path=seen[p.target_edge]==true
 local first,last=out.path[1],out.path[#out.path]
 out.source_direction_matches=first.edge.entity==p.source_edge and first.edge.index==index and first.forward==dir
 out.target_direction_matches=last.edge.entity==p.target_edge and last.edge.index==target_index and last.forward==(p.target_node==b.node1)
 out.requested_route_verified=continuous and out.origin_matches and out.destination_matches and #missing==0 and
  out.source_direction_matches and out.target_direction_matches and length<=p.max_length+.001
 if out.min_sampled_radius==math.huge then out.min_sampled_radius=nil;out.straight_only=true end
 if not out.requested_route_verified then out.reason=length>p.max_length+.001 and "native_path_exceeds_requested_length" or "native_path_does_not_establish_requested_route" end
 return out
end
function M.fit(p,s,request_id,target,start,diagnostics)
 vector(p.end_xy);vector(p.end_direction)
 assert(finite(p.radius) and p.radius>0,"invalid_radius")
 local fitradius=p.fit_radius or p.radius*1.05
 assert(finite(fitradius) and fitradius>=p.radius,"invalid_native_fit_radius")
 assert(type(p.region)=="table","region_required");vector(p.region.min);vector(p.region.max)
 assert(#p.region.min==3 and #p.region.max==3,"region_needs_xyz")
 for i=1,3 do assert(p.region.max[i]>p.region.min[i],"invalid_region") end
 -- Longer connection envelope; discovery remains local and total fit length<=800.
 local region_bound=start and 3000 or 1000
 assert(p.region.max[1]-p.region.min[1]<=region_bound and p.region.max[2]-p.region.min[2]<=region_bound,"fit_region_bound")
 -- start is invocation-local corridor intent, never an external/native entity claim.
 local a,pos,t0,grade
 if start then a=start.anchor;pos=start.pos;t0=start.direction;grade=start.grade
 else a,pos,t0,grade=anchor(p) end
 in_region(pos,p.region)
 local t1=norm(p.end_direction)
 local result=api.engine.util.pathfinding.findDubinsPath(v({pos[1],pos[2],0}),v(t0),v({p.end_xy[1],p.end_xy[2],0}),v(t1),fitradius)
 assert(type(result)=="table" and #result>0 and #result<=8,"no_supported_bounded_fit")
 local native_parts={}
 for i,row in ipairs(result) do
  local g=row[1];local p0,d0=sample(g,0,row[2]);local p1,d1=sample(g,1,row[2])
  native_parts[i]={type=tostring(g.type),length=g.length,forward=row[2],start=p0,finish=p1,
   tangent_start=d0,tangent_finish=d1,radius=g.type==api.type.EdgeGeometry.Type.ARC and g.arc.radius or nil}
 end
 if diagnostics then diagnostics.native_parts=native_parts;diagnostics.native_fit_radius=fitradius end
 -- Native float precision can emit sub-millimetre ARC parts on a straight leg.
 -- Remove only collectively <=the existing0.001 endpoint tolerance, with equally
 -- tiny heading changes. All remaining joins/endpoints and hard bounds still apply.
 local filtered,discarded,discardedlength={},{},0
 for _,row in ipairs(result) do
  local g=row[1];assert(g and finite(g.length) and g.length>0,"invalid_fit_length")
  local skip=false
  if g.type==api.type.EdgeGeometry.Type.ARC and g.length<=.001 then
   assert(finite(g.arc.radius) and math.abs(g.arc.radius)>=fitradius-.001,"fit_radius_below_selected_constraint")
   local p0,d0=sample(g,0,row[2]);local p1,d1=sample(g,1,row[2])
   if distance(p0,p1)<=.001 and angle(d0,d1)<=.001 then
    skip=true;discardedlength=discardedlength+g.length
    discarded[#discarded+1]={length=g.length,start=p0,finish=p1,heading_change=angle(d0,d1)}
   end
  end
  if not skip then filtered[#filtered+1]=row end
 end
 -- If individually tiny pieces exceed the collective discard budget, retain
 -- ALL native parts. Eligible near-straight lowering below can represent them
 -- safely; other paths still face the unchanged conversion/engineering checks.
 if discardedlength>.001 then
  if diagnostics then diagnostics.retained_tiny_parts_reason="aggregate_exceeds_discard_budget";diagnostics.retained_tiny_total_length=discardedlength end
  filtered=result;discarded={};discardedlength=0
 end
 assert(discardedlength<=.001 and #filtered>0,"unsupported_degenerate_native_fit")
 result=filtered
 if diagnostics then diagnostics.discarded_native_tiny_parts=discarded;diagnostics.discarded_native_total_length=discardedlength end
 local controls,samples,total,maxerr,maxheading={}, {},0,0,0
 local orientation={forward_parts=0,backward_parametrised_parts=0};local orientation_evidence={}
 for i,row in ipairs(result) do
  assert(type(row[2])=="boolean","native_direction_flag_unavailable")
  local g=row[1];assert(g and finite(g.length) and g.length>0,"invalid_fit_length")
  assert(g.type==api.type.EdgeGeometry.Type.ARC or g.type==api.type.EdgeGeometry.Type.STRAIGHT,"unsupported_fit_family")
  if g.type==api.type.EdgeGeometry.Type.ARC then assert(math.abs(g.arc.radius)>=fitradius-.001,"fit_radius_below_selected_constraint") end
  -- The declared flag is EdgeGeometry traversal direction. Ask the native sampler
  -- to apply it; never equate canonical orientation with railway reversal.
  local p0,d0=sample(g,0,row[2]);local p1,d1=sample(g,1,row[2])
  if row[2] then orientation.forward_parts=orientation.forward_parts+1
  else
   orientation.backward_parametrised_parts=orientation.backward_parametrised_parts+1
   local raw0,rawdir0=sample(g,0,true);local raw1,rawdir1=sample(g,1,true)
   assert(distance(raw0,p1)<=.001 and distance(raw1,p0)<=.001 and
    angle(rawdir0,{-d1[1],-d1[2],0})<=.1 and angle(rawdir1,{-d0[1],-d0[2],0})<=.1,"native_orientation_contract_mismatch")
   orientation_evidence[#orientation_evidence+1]={piece=i,forward=false,length=g.length,
    canonical_start=raw0,canonical_finish=raw1,canonical_tangent_start=rawdir0,canonical_tangent_finish=rawdir1,
    -- Snapshot planar native values before controls receive their height profile.
    travel_start={p0[1],p0[2],p0[3]},travel_finish={p1[1],p1[2],p1[3]},
    travel_tangent_start={d0[1],d0[2],d0[3]},travel_tangent_finish={d1[1],d1[2],d1[3]}}
  end
  if i==1 then assert(distance(p0,pos)<=.001 and angle(d0,t0)<=.1,"fit_start_mismatch");p0[1]=pos[1];p0[2]=pos[2]
  else assert(distance(p0,controls[i-1].p1)<=.001 and angle(d0,controls[i-1].t1)<=.1,"fit_join_mismatch");p0[1]=controls[i-1].p1[1];p0[2]=controls[i-1].p1[2] end
  p0[3]=pos[3]+grade*total;p1[3]=pos[3]+grade*(total+g.length)
  d0[3]=grade*g.length;d1[3]=grade*g.length
  local c={p0=p0,p1=p1,t0=d0,t1=d1,length=g.length};controls[i]=c
  total=total+g.length
 end
 assert(total<=800,"fit_length_bound")
 local last=controls[#controls];assert(distance(last.p1,p.end_xy)<=.001 and angle(last.t1,t1)<=.1,"fit_end_mismatch")
 -- A nearly straight native ARC/STRAIGHT/ARC path can have millimetre ARC
 -- pieces whose endpoints lose the transverse displacement at map float scale.
 -- Lower that native path as one cubic, rather than construct invalid fragments.
 -- This neither discards longer parts nor changes any engineering/conversion bound.
 local original_controls=controls;local nearstraight=nil
 local straight_count,arc_turn=0,0
 for _,row in ipairs(result) do
  local g=row[1]
  if g.type==api.type.EdgeGeometry.Type.STRAIGHT then straight_count=straight_count+1
  else arc_turn=arc_turn+g.length/math.abs(g.arc.radius)*180/math.pi end
 end
 local function sample_path(at)
  local offset=0
  for i,row in ipairs(result) do
   local length=row[1].length
   if at<=offset+length or i==#result then return sample(row[1],math.max(0,math.min(1,(at-offset)/length)),row[2]) end
   offset=offset+length
  end
 end
 if #controls>1 and straight_count==1 and arc_turn<=.1 then
  local first=controls[1];local a,b=norm(first.t0),norm(last.t1)
  local c={p0={first.p0[1],first.p0[2],first.p0[3]},p1={last.p1[1],last.p1[2],last.p1[3]},
   t0={a[1]*total,a[2]*total,grade*total},t1={b[1]*total,b[2]*total,grade*total},length=total}
  local g=cubic(c);local offset,count=0,0
  -- Check every original native part, including both ends of short fragments.
  for _,row in ipairs(result) do
   for j=0,16 do
    local u=j/16;local np=sample(row[1],u,row[2]);local cp=sample(g,(offset+u*row[1].length)/total)
    maxerr=math.max(maxerr,distance(np,cp));count=count+1
   end
   offset=offset+row[1].length
  end
  assert(maxerr<=.1,"sampled_conversion_outside_tolerance")
  nearstraight={original_pieces=#controls,proposal_pieces=1,arc_turn_deg=arc_turn,sample_count=count,sampled_XY_error=maxerr,sampled_only=true}
  controls={c};last=c
 end
 if diagnostics then diagnostics.original_converted_controls=original_controls;diagnostics.nearstraight_repartition=nearstraight end
 local endgrade=target and target.grade or grade
 local endheight=target and target.pos[3] or last.p1[3]
 local profile,maxgrade=nil,nil
 if p.vertical then
  local q=p.vertical;assert(type(q)=="table" and finite(q.max_grade) and q.max_grade>0,"invalid_vertical_limit")
  maxgrade=q.max_grade
  if not target then
   assert(finite(q.end_height) and finite(q.end_grade),"vertical_endpoint_required")
   endheight=q.end_height;endgrade=q.end_grade
  end
  assert(math.abs(grade)<=maxgrade and math.abs(endgrade)<=maxgrade,"endpoint_grade_exceeds_limit")
  -- The engine supplies the vertical interpolation. This is one explicitly
  -- chosen native cubic height profile over cumulative native XY fit length.
  profile=cubic({p0={0,0,pos[3]},p1={total,0,endheight},t0={total,0,grade*total},
                 t1={total,0,endgrade*total},length=total})
 elseif target then
  assert(math.abs(grade-target.grade)<=.000001,"unsupported_endpoint_grades")
  assert(math.abs(last.p1[3]-target.pos[3])<=.001,"unsupported_endpoint_height")
 end
 if target then
  last.p1={target.pos[1],target.pos[2],target.pos[3]};last.t1[3]=target.grade*last.length
  in_region(last.p1,p.region)
 end
 local offset,maxsampledgrade,maxzerr,minsampledradius=0,0,0,math.huge
 local vertical_samples={}
 if diagnostics then diagnostics.converted_controls=controls end
 for i,c in ipairs(controls) do
  if profile then
   local p0,d0=sample(profile,offset/total);local p1,d1=sample(profile,(offset+c.length)/total)
   c.p0[3]=i==1 and pos[3] or controls[i-1].p1[3];c.p1[3]=i==#controls and endheight or p1[3]
   c.t0[3]=slope(d0)*math.sqrt(c.t0[1]^2+c.t0[2]^2)
   c.t1[3]=slope(d1)*math.sqrt(c.t1[1]^2+c.t1[2]^2)
  end
  local cg=cubic(c);samples[i]={};vertical_samples[i]={}
  if diagnostics then diagnostics.checking_piece=i end
  local checkedradius=geometry_bounds(cg,p.region,p.radius,maxgrade or math.abs(grade))
  minsampledradius=math.min(minsampledradius,checkedradius)
  for _,u in ipairs({0,.25,.5,.75,1}) do
   local np,nd
   if nearstraight then np,nd=sample_path(offset+u*c.length) else np,nd=sample(result[i][1],u,result[i][2]) end
   local cp,cd=sample(cg,u)
   maxerr=math.max(maxerr,distance(np,cp));if u==0 or u==1 then maxheading=math.max(maxheading,angle(nd,cd)) end
   local grade_here=slope(cd);maxsampledgrade=math.max(maxsampledgrade,math.abs(grade_here))
   if maxgrade then assert(math.abs(grade_here)<=maxgrade+.000001,"sampled_grade_exceeds_limit") end
   if profile then local vp=sample(profile,(offset+u*c.length)/total);maxzerr=math.max(maxzerr,math.abs(cp[3]-vp[3])) end
   in_region(cp,p.region)
   samples[i][#samples[i]+1]={u=u,pos=np,dir=nd,base_pos=cp,base_grade=grade_here}
   vertical_samples[i][#vertical_samples[i]+1]={u=u,height=cp[3],grade=grade_here}
  end
  if i>1 then assert(math.abs(c.p0[3]-controls[i-1].p1[3])<=.001 and math.abs(slope(c.t0)-slope(controls[i-1].t1))<=.000001,"vertical_join_mismatch") end
  offset=offset+c.length
 end
 assert(maxerr<=.1 and maxheading<=.1,"sampled_conversion_outside_tolerance")
 assert(maxzerr<=.001,"native_vertical_subdivision_mismatch")
 assert(math.abs(slope(controls[1].t0)-grade)<=.000001 and math.abs(slope(last.t1)-endgrade)<=.000001,"endpoint_grade_mismatch")
 s.fits[request_id]={anchor=a,node=p.anchor_node,target=target,controls=controls,samples=samples,region=p.region,total_length=total,grade=grade,end_grade=endgrade,max_grade=maxgrade,min_radius=p.radius,built=false}
 return {fit_request=request_id,pieces=#controls,total_length=total,start_node=p.anchor_node,target_node=target and target.node or nil,start=pos,finish=last.p1,radius=p.radius,grade=grade,end_grade=endgrade,
  native_parts=native_parts,original_native_controls=nearstraight and original_controls or nil,nearstraight_repartition=nearstraight,
  discarded_native_tiny_parts=discarded,discarded_native_total_length=discardedlength,
  vertical_domain=profile and "native_cubic_endpoint_height_grade" or "constant_grade_compatible_endpoints",max_grade=maxgrade,max_sampled_grade=maxsampledgrade,sampled_Z_error=maxzerr,
  vertical_samples=profile and vertical_samples or nil,controls=controls,sampled_XY_error=maxerr,endpoint_heading_error=maxheading,
  native_fit_radius=fitradius,requested_min_radius=p.radius,min_sampled_converted_radius=minsampledradius~=math.huge and minsampledradius or nil,
  native_orientation=orientation,orientation_evidence=orientation_evidence,sampled_only=true,game_constructed=false}
end
function M.readback(f)
 assert(f.ids and #f.ids==#f.controls,"construction_receipt_incomplete")
 local remaining={};for _,id in ipairs(f.ids) do assert(not remaining[id],"duplicate_receipt_edge");remaining[id]=true end
 local current=f.node;local ordered,nodes,observations={},{current},{};local maxerr,maxheading,maxzerr,maxgrade,maxjoinz,maxjoingrade=0,0,0,0,0,0
 assert(finite(f.min_radius) and f.min_radius>0,"realised_radius_requirement_missing")
 local minradius=math.huge
 for i,c in ipairs(f.controls) do
  local found,e=nil,nil
  for id in pairs(remaining) do local x=edge(id);if x.node0==current then assert(not found,"ambiguous_connection");found=id;e=x end end
  assert(found,"actual_connection_missing");remaining[found]=nil
  assert(e.template==f.anchor.template and e.style==f.anchor.style,"resource_mismatch")
  assert(near(e.p0,c.p0,.001) and near(e.p1,c.p1,.001) and near(e.t0,c.t0,.001) and near(e.t1,c.t1,.001),"realised_controls_differ")
  local ng=native_geometry(found)
  local actualbase=cubic({p0=e.p0,p1=e.p1,t0=e.t0,t1=e.t1,length=c.length})
  for _,expected in ipairs(f.samples[i]) do
   local pos,dir=sample(ng,expected.u)
   local comparison_pos,comparison_dir=pos,dir
   if f.junction_node then comparison_pos,comparison_dir=sample(actualbase,expected.u) end
   maxerr=math.max(maxerr,distance(comparison_pos,expected.pos))
   if expected.u==0 or expected.u==1 then maxheading=math.max(maxheading,angle(comparison_dir,expected.dir)) end
   -- Movement Z can differ from BaseEdge profile; C13 established that distinction.
   local bp,bd=sample(actualbase,expected.u);local bg=slope(bd)
   maxzerr=math.max(maxzerr,math.abs(bp[3]-expected.base_pos[3]));maxgrade=math.max(maxgrade,math.abs(bg))
   if f.max_grade then assert(math.abs(bg)<=f.max_grade+.000001,"realised_sampled_grade_exceeds_limit") end
   in_region({pos[1],pos[2],bp[3]},f.region)
  end
  local checkedradius=geometry_bounds(actualbase,f.region,f.min_radius,f.max_grade or math.abs(f.grade))
  minradius=math.min(minradius,checkedradius)
  if f.junction_node then geometry_bounds(ng,f.region,f.min_radius,f.max_grade) end
  if i>1 then
   local prev=observations[i-1];maxjoinz=math.max(maxjoinz,math.abs(prev.p1[3]-e.p0[3]));maxjoingrade=math.max(maxjoingrade,math.abs(slope(prev.t1)-slope(e.t0)))
  end
  ordered[#ordered+1]=found;nodes[#nodes+1]=e.node1;observations[#observations+1]=e;current=e.node1
 end
 for _ in pairs(remaining) do error("unreconciled_returned_edge") end
 assert(maxerr<=.1 and maxheading<=.1,"realised_sampled_shape_failed")
 assert(maxzerr<=.001 and maxjoinz<=.001 and maxjoingrade<=.000001,"realised_vertical_profile_failed")
 assert(math.abs(slope(observations[1].t0)-f.grade)<=.000001 and math.abs(slope(observations[#observations].t1)-f.end_grade)<=.000001,"realised_endpoint_grade_failed")
 local attachments=nil
 if f.target then
  assert(current==f.target.node,"actual_target_attachment_missing")
  local source,target=assert_fresh(f.anchor),assert_fresh(f.target.edge)
  assert(source.node0==f.node or source.node1==f.node,"source_incidence_missing")
  assert(target.node0==current or target.node1==current,"target_incidence_missing")
  assert(angle(observations[#observations].t1,f.target.direction)<=.1,"target_travel_direction_mismatch")
  attachments={source_edge=source.id,source_node=f.node,target_edge=target.id,target_node=current,
   source_incident_edges={source.id,ordered[1]},target_incident_edges={ordered[#ordered],target.id},
   exact_native_identity=true,resources_compatible=true}
 end
 local guides={}
 for _,g in ipairs(f.guides or {}) do
  local before,after=observations[g.after_piece],observations[g.after_piece+1]
  assert(before and after and before.node1==after.node0,"guide_shared_node_missing")
  assert(near(before.p1,g.pos,.001) and near(after.p0,g.pos,.001),"guide_position_mismatch")
  assert(angle(before.t1,g.direction)<=.1 and angle(after.t0,g.direction)<=.1,"guide_heading_mismatch")
  assert(math.abs(slope(before.t1)-g.grade)<=.000001 and math.abs(slope(after.t0)-g.grade)<=.000001,"guide_grade_mismatch")
  guides[#guides+1]={node=before.node1,after_piece=g.after_piece,position=before.p1,grade=slope(before.t1),verified=true}
 end
 return {ordered_edges=ordered,ordered_nodes=nodes,edges=observations,attachments=attachments,connected=true,realised_guides=guides,sampled_XY_error=maxerr,sampled_base_Z_error=maxzerr,max_sampled_grade=maxgrade,max_join_height_gap=maxjoinz,max_join_grade_gap=maxjoingrade,endpoint_heading_error=maxheading,engineering_checks_verified=true,straight_only=minradius==math.huge,requested_min_radius=f.min_radius,min_sampled_radius=minradius~=math.huge and minradius or nil,sampled_only=true,game_constructed=true,train_traversal="unprobed",native_effect_history_complete=false}
end
function M.build(p,s,state,request_id,respond)
 assert(p.authorised==true,"explicit_build_option_required")
 local f=s.fits[p.fit_request];assert(f and not f.built,"fit_missing_or_already_consumed")
 assert_fresh(f.anchor)
 if f.target then assert_fresh(f.target.edge) end
 local h=api.res.streetTemplateRep.find(f.anchor.template);local resource=api.res.streetTemplateRep.get(h)
 assert(resource and resource.laneConfigs and #resource.laneConfigs>0,"track_template_unavailable")
 local proposal=api.type.SimpleProposal.new();local segments,newnodes={},{};local count=#f.controls
 for i,c in ipairs(f.controls) do
  local node1
  if f.target and i==count then node1=f.target.node
  else
   local n=api.type.NodeAndEntity.new();n.entity=-count-i;n.comp.position=v(c.p1);newnodes[#newnodes+1]=n;node1=n.entity
  end
  local e=api.type.SegmentAndEntity.new();e.entity=-i;e.type=1
  e.comp.node0=i==1 and f.node or (-count-i+1);e.comp.node1=node1
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
   local receipt=res.proposal.proposal;f.ids={};f.other_added_segments={}
   for _,item in ipairs(receipt.addedSegments) do
    local e=api.engine.getComponent(item.entity,api.type.ComponentType.BASE_EDGE)
    if e and e.roadType==E.RoadType.TRACK then f.ids[#f.ids+1]=item.entity else f.other_added_segments[#f.other_added_segments+1]=item.entity end
   end
   f.effects={added_segments=#receipt.addedSegments,added_nodes=#receipt.addedNodes,removed_segments=#receipt.removedSegments,removed_nodes=#receipt.removedNodes}
   assert(success==true,"native_construction_rejected")
   local result=M.readback(f);result.effects=f.effects;result.other_added_segments=f.other_added_segments;result.fit_request=p.fit_request;return result
  end)
  respond(request_id,ok and "ok" or "mutation_unverified",ok and value or {error=tostring(value):sub(1,400),effects=f.effects,returned_edges=f.ids,game_constructed="unknown",retry=false})
 end
 f.built=true;f.build_request=request_id;s.mutationPending=request_id
 local root=state:get() or {};root.pifLive=s;state:set(root)
 local cmd=api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false)
 api.cmd.sendCommand(cmd,callback)
end
-- Pre-fit every ordered leg with native geometry, then submit one joined proposal.
-- Guide boundaries are intent until the build receipt reacquires actual node IDs.
function M.corridor(p,s,state,request_id,respond)
 local stage,fit,fitted="inspect",nil,nil
 local function reply(status,value) value.stage=stage;value.fit=fit;respond(request_id,status,value) end
 local ok,err=pcall(function()
  selected_attachments(p)
  assert(type(p.guides)=="table" and #p.guides>=1 and #p.guides<=3,"corridor_guide_bound")
  assert(type(p.vertical)=="table" and finite(p.vertical.max_grade) and p.vertical.max_grade>0,"invalid_vertical_limit")
  local a,pos,direction,grade=anchor({anchor_edge=p.source.edge_id,anchor_node=p.source.node_id})
  local t,tp,td,tg=anchor({anchor_edge=p.target.edge_id,anchor_node=p.target.node_id})
  assert(a.template==t.template and a.style==t.style,"unsupported_attachment_resources")
  local target={edge=t,node=p.target.node_id,pos=tp,direction={-td[1],-td[2],0},grade=-tg}
  local goals={}
  for _,g in ipairs(p.guides) do
   vector(g.position);assert(#g.position==3,"guide_needs_xyz");vector(g.travel_direction)
   assert(#g.travel_direction==2 and finite(g.grade) and math.abs(g.grade)<=p.vertical.max_grade,"invalid_guide_grade_direction")
   in_region(g.position,p.region)
   goals[#goals+1]={pos=g.position,direction=norm(g.travel_direction),grade=g.grade}
  end
  goals[#goals+1]=target
  local all={anchor=a,node=p.source.node_id,target=target,controls={},samples={},guides={},region=p.region,
   grade=grade,end_grade=target.grade,max_grade=p.vertical.max_grade,min_radius=p.radius,total_length=0,built=false}
  local start={anchor=a,pos=pos,direction=direction,grade=grade}
  fit={legs={},pieces=0,total_length=0,radius=p.radius,grade=grade,end_grade=target.grade,max_grade=p.vertical.max_grade,
   max_sampled_grade=0,sampled_XY_error=0,sampled_Z_error=0,sampled_only=true,guide_nodes_realised=false,game_constructed=false,
   native_orientation={forward_parts=0,backward_parametrised_parts=0},orientation_evidence={}}
  stage="fit"
  for i,goal in ipairs(goals) do
   local id=request_id.."_leg_"..i
   local leg=M.fit({anchor_edge=a.id,anchor_node=p.source.node_id,end_xy={goal.pos[1],goal.pos[2]},end_direction=goal.direction,
    radius=p.radius,fit_radius=p.radius*1.25,region=p.region,vertical={max_grade=p.vertical.max_grade}},s,id,goal,start)
   local f=s.fits[id];local first=#all.controls+1
   for j,c in ipairs(f.controls) do all.controls[#all.controls+1]=c;all.samples[#all.samples+1]=f.samples[j] end
   all.total_length=all.total_length+leg.total_length
   assert(all.total_length<=3200 and #all.controls<=32,"corridor_fit_bound")
   fit.legs[i]={index=i,first_piece=first,last_piece=#all.controls,length=leg.total_length,start=start.pos,finish=goal.pos,
    grade=start.grade,end_grade=goal.grade,max_sampled_grade=leg.max_sampled_grade}
   for key,value in pairs(leg.native_orientation) do fit.native_orientation[key]=fit.native_orientation[key]+value end
   if #leg.orientation_evidence>0 then fit.orientation_evidence[#fit.orientation_evidence+1]={leg=i,parts=leg.orientation_evidence} end
   fit.max_sampled_grade=math.max(fit.max_sampled_grade,leg.max_sampled_grade)
   fit.sampled_XY_error=math.max(fit.sampled_XY_error,leg.sampled_XY_error)
   fit.sampled_Z_error=math.max(fit.sampled_Z_error,leg.sampled_Z_error)
   if i<#goals then all.guides[#all.guides+1]={after_piece=#all.controls,pos=goal.pos,direction=goal.direction,grade=goal.grade} end
   local last=f.controls[#f.controls];start={anchor=a,pos=last.p1,direction=norm(last.t1),grade=slope(last.t1)}
  end
  fit.pieces=#all.controls;fit.total_length=all.total_length;fit.controls=all.controls;fitted=all
  local fit_id=request_id.."_corridor_fit";s.fits[fit_id]=all
  if not p.execute then reply("ok",{game_constructed=false});return end
  stage="build";assert(not s.mutationPending,"unreconciled_mutation")
  M.build({fit_request=fit_id,authorised=true},s,state,request_id,function(_id,status,value)
   if status~="ok" then reply(status,value);return end
   stage="readback";local verified,result=pcall(M.readback,fitted)
   if not verified then reply("mutation_unverified",{error=tostring(result):sub(1,400),game_constructed=true,
    returned_edges=value.ordered_edges,initial_readback=value,effects=value.effects,retry=false});return end
   s.mutationPending=nil
   reply("ok",{game_constructed=true,readback=result,effects=value.effects})
  end)
 end)
 if not ok then
  local uncertain=s.mutationPending==request_id
  reply(uncertain and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),game_constructed=uncertain and "unknown" or false,retry=false})
 end
end
function M.extension(p,s,state,request_id,respond,connect_mode,junction_context)
 local stage,stages,fit="inspect",{},nil
 local fit_diagnostics={}
 local function reply(status,value)
  value.stage=stage;value.stages=stages;value.fit=fit
  if stage=="fit" and status~="ok" then value.fit_diagnostics=fit_diagnostics end
  respond(request_id,status,value)
 end
 local ok,err=pcall(function()
  assert(type(p.brief)=="table" and type(p.execute)=="boolean","invalid_extension_brief")
  local b=p.brief;local inspection=M.inspect({edge_ids=connect_mode and {b.anchor_edge,b.target_edge} or {b.anchor_edge}})
  local a=inspection.edges[1];assert(b.anchor_node==a.node0 or b.anchor_node==a.node1,"anchor_not_edge_endpoint")
  local target=nil
  if connect_mode then
   assert(b.anchor_node~=b.target_node and b.anchor_edge~=b.target_edge,"distinct_attachments_required")
   assert(b.target_node==inspection.edges[2].node0 or b.target_node==inspection.edges[2].node1,"target_not_edge_endpoint")
   local t,pos,outward,grade=anchor({anchor_edge=b.target_edge,anchor_node=b.target_node})
   assert(a.template==t.template and a.style==t.style,"unsupported_attachment_resources")
   target={edge=t,node=b.target_node,pos=pos,direction={-outward[1],-outward[2],0},grade=-grade}
   b={anchor_edge=b.anchor_edge,anchor_node=b.anchor_node,end_xy={pos[1],pos[2]},end_direction=target.direction,radius=b.radius,region=b.region,vertical=b.vertical}
  end
  stages[#stages+1]={stage="inspect",status="ok"}
  stage="fit"
  -- A small explicit native-fit margin accommodates ARC-to-cubic conversion;
  -- the requested minimum remains binding on sampled realised branch geometry.
  if junction_context then b.fit_radius=junction_context.radius*1.05 end
  local fit_id=request_id.."_fit";fit=M.fit(b,s,fit_id,target,nil,fit_diagnostics)
  local fitted=s.fits[fit_id] -- retain invocation-local data across command callback
  if junction_context then
   fitted.junction_node=junction_context.node;fitted.min_radius=junction_context.radius
   fit.requested_min_radius=junction_context.radius
   for _,c in ipairs(fitted.controls) do geometry_bounds(cubic(c),fitted.region,fitted.min_radius,fitted.max_grade) end
  end
  stages[#stages+1]={stage="fit",status="ok"}
  if not p.execute then reply("ok",{game_constructed=false});return end
  stage="build";assert(not s.mutationPending,"unreconciled_mutation")
  M.build({fit_request=fit_id,authorised=true},s,state,request_id,function(_id,status,value)
   if status~="ok" then reply(status,value);return end
   stages[#stages+1]={stage="build",status="ok"}
   -- A separate fresh native component/geometry query after the build callback's
   -- own readback, using invocation-local receipt rather than lagging script state.
   stage="readback";local verified,result=pcall(M.readback,fitted)
   if not verified then reply("mutation_unverified",{error=tostring(result):sub(1,400),game_constructed=true,initial_readback=value,returned_edges=value.ordered_edges,effects=value.effects,retry=false});return end
   stages[#stages+1]={stage="readback",status="ok"}
   s.mutationPending=nil
   reply("ok",{game_constructed=true,readback=result,effects=value.effects})
  end)
 end)
 if not ok then
  stages[#stages+1]={stage=stage,status="error"}
  local uncertain=s.mutationPending==request_id
  reply(uncertain and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),reason_class=tostring(err):find("unsupported_",1,true) and "unsupported_input" or "failed_check",game_constructed=uncertain and "unknown" or false,retry=false})
 end
end
-- Disposable-world test fixture, not a planner: place one short independent
-- approach at a native-fitted finish, with the same template, tangent and grade.
-- Native evaluation and one coherent remove/replace/add proposal. No Python fitter.
local function interior_splits(a,parameter,region,radius,max_grade,second_parameter)
  local g=cubic({p0=a.p0,p1=a.p1,t0=a.t0,t1=a.t1,length=1});local splits={}
  local intervals={{0,parameter},{parameter,1}}
  if second_parameter then
   assert(finite(second_parameter) and parameter<second_parameter and second_parameter<1,"ordered_native_split_parameters_required")
   intervals={{0,parameter},{parameter,second_parameter},{second_parameter,1}}
  end
  for i,interval in ipairs(intervals) do
   local x,y=interval[1],interval[2];local first,last=g:calcPos(x),g:calcPos(y)
   local t0,t1=arr(first[2]),arr(last[2]);for k=1,3 do t0[k]=t0[k]*(y-x);t1[k]=t1[k]*(y-x) end
   splits[i]={p0=arr(first[1]),p1=arr(last[1]),t0=t0,t1=t1,length=1}
   geometry_bounds(cubic(splits[i]),region,radius,max_grade)
   for _,u in ipairs({0,.25,.5,.75,1}) do
    local original=g:calcPos(x+u*(y-x));local derived=cubic(splits[i]):calcPos(u)
    assert(near(arr(original[1]),arr(derived[1]),.001) and angle(arr(original[2]),arr(derived[2]))<=.1,"native_subdivision_mismatch")
    in_region(arr(derived[1]),region)
   end
  end
 return splits
end
local function interior_readback(a,c,splits,f,te,ids,p,before)
 local target=p.target
    assert(#ids==#f.controls+2,"split_receipt_incomplete")
    local original_start=c.canonical_forward and a.node0 or a.node1;local original_finish=c.canonical_forward and a.node1 or a.node0
    local placement={original_edge=a.id,original_nodes={a.node0,a.node1},parameter=c.parameter,position=c.pos,canonical_forward=c.canonical_forward,subdivision_sampled_verified=true}
    local left,right=nil,nil
    for _,eid in ipairs(ids) do local e=edge(eid);if e.node0==a.node0 then assert(not left,"ambiguous_split_left");left=e end;if e.node1==a.node1 then assert(not right,"ambiguous_split_right");right=e end end
    assert(left and right and left.node1==right.node0,"split_shared_identity_missing")
    local junction=left.node1;assert(junction~=a.node0 and junction~=a.node1 and near(left.p1,c.pos,.001),"realised_interior_location_mismatch")
    for i,e in ipairs({left,right}) do for _,k in ipairs({"p0","p1","t0","t1"}) do assert(near(e[k],splits[i][k],.001),"realised_through_controls_differ") end;assert(e.template==a.template and e.style==a.style,"through_resources_differ") end
    assert(not api.engine.entityExists(a.id) or api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)==nil,"old_split_edge_still_present")
    local incoming,through=c.canonical_forward and left or right,c.canonical_forward and right or left
    f.node=junction;f.junction_node=junction;f.anchor=incoming;f.ids={}
    for _,eid in ipairs(ids) do if eid~=left.id and eid~=right.id then f.ids[#f.ids+1]=eid end end
    local rb=M.readback(f);local free_end=nil
    if not te then
     local node=rb.ordered_nodes[#rb.ordered_nodes];local last=rb.edges[#rb.edges];local all,owner=incidence(node)
     assert(#all==1 and all[1]==last.id and not(owner and owner>0),"realised_free_lead_not_free")
     assert(near(last.p1,p.end_xyz,.001) and angle(last.t1,p.end_direction)<=.1,"realised_free_lead_endpoint_mismatch")
     free_end={node=node,edge=last.id,position=last.p1,outward_direction=norm(last.t1),incident_edges=all,
      exact_native_identity=true,free=true}
    end
    local incident=incidence(junction)
    assert(#incident==3,"split_junction_incidence_mismatch")
    local expected={[left.id]=true,[right.id]=true,[rb.ordered_edges[1]]=true};for _,eid in ipairs(incident) do assert(expected[eid],"split_junction_incidence_mismatch") end
    local junctions={junction};for _,n in ipairs(p.junction_nodes or {}) do junctions[#junctions+1]=n end
    local after=M.route({source_edge=incoming.id,source_node=original_start,target_edge=through.id,target_node=original_finish,
     junction_node=junction,junction_nodes=junctions,mode="TRAIN",required_edges={incoming.id,through.id},max_length=p.max_route_length,
     geometry_constraints={edge_ids={incoming.id,through.id},junction_node=junction,region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}})
    local required={incoming.id};if te then required[#required+1]=te.id end;for _,eid in ipairs(rb.ordered_edges) do required[#required+1]=eid end
    local branch=M.route({source_edge=incoming.id,source_node=original_start,target_edge=te and te.id or rb.ordered_edges[#rb.ordered_edges],target_node=te and (te.node0==target.node_id and te.node1 or te.node0) or rb.ordered_nodes[#rb.ordered_nodes],
     junction_node=junction,junction_nodes=junctions,mode="TRAIN",required_edges=required,max_length=p.max_route_length,
     geometry_constraints={edge_ids=rb.ordered_edges,junction_node=junction,region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}})
    assert(after.requested_route_verified and branch.requested_route_verified,"realised_split_movements_unverified")
    if rb.attachments then rb.attachments.source_incident_edges=incident end
    placement.junction_node=junction;placement.replacement_edges={left.id,right.id};placement.incoming=incoming;placement.through=through;placement.original_removed=true;placement.game_constructed=true
    return {game_constructed=true,placement=placement,readback=rb,free_end=free_end,through_before=before,through_after=after,branch_after=branch,
     junction={node=junction,incoming_edge=incoming.id,through_edge=through.id,branch_edge=rb.ordered_edges[1],incident_edges=incident,
      exact_native_identity=true,through_route_verified=true,branch_geometry_verified=true,min_sampled_radius=branch.min_sampled_radius,max_sampled_grade=branch.max_sampled_grade}}
end
function M.interior_junction(p,s,state,request_id,respond)
 local stage,fit="inspect",nil
 local function reply(status,value) value.stage=stage;value.fit=fit;respond(request_id,status,value) end
 local ok,err=pcall(function()
  assert(type(p.execute)=="boolean","invalid_execution_option")
  local a=assert_fresh(p.source.edge_snapshot);local c=interior_location(a,p.location)
  assert(math.abs(c.parameter-p.source.parameter)<=.000001,"stale_interior_location")
  local target=p.target;local te,tp,td,tg
  if target then
   te=assert_fresh(target.edge_snapshot)
   local all,owner=incidence(target.node_id)
   assert(#all==1 and all[1]==te.id and not (owner and owner>0),"selected_endpoint_not_free")
   assert(target.node_id==te.node0 or target.node_id==te.node1,"target_endpoint_mismatch")
   assert(a.id~=te.id and a.node0~=target.node_id and a.node1~=target.node_id,"distinct_split_target_required")
   local ignored;ignored,tp,td,tg=anchor({anchor_edge=te.id,anchor_node=target.node_id});td={-td[1],-td[2],0};tg=-tg
  else
   -- A level fitted turnout lead ending in a new free attachment, for composition.
   vector(p.end_xyz);assert(#p.end_xyz==3,"free_lead_endpoint_XYZ_required");vector(p.end_direction)
   assert(p.vertical.max_grade==0 and math.abs(c.grade)<=.000001 and math.abs(p.end_xyz[3]-c.pos[3])<=.001,"level_free_lead_required")
   tp=p.end_xyz;td=p.end_direction;tg=0
  end
  local original_start=c.canonical_forward and a.node0 or a.node1;local original_finish=c.canonical_forward and a.node1 or a.node0
  local before=M.route({source_edge=a.id,source_node=original_start,target_edge=a.id,target_node=original_finish,
   single_edge=true,junction_nodes=p.junction_nodes,mode="TRAIN",required_edges={a.id},max_length=p.max_route_length})
  assert(before.requested_route_verified,"existing_through_route_unverified")
  local splits=interior_splits(a,c.parameter,p.region,p.radius,p.vertical.max_grade)
  stage="fit"
  local fit_id=request_id.."_fit";fit=M.fit({end_xy={tp[1],tp[2]},end_direction=td,radius=p.radius,fit_radius=p.fit_radius or p.radius*1.05,region=p.region,vertical=te and p.vertical or nil},s,fit_id,
   te and {edge=te,node=target.node_id,pos=tp,direction=td,grade=tg} or nil,{anchor=a,pos=c.pos,direction=c.outward_direction,grade=c.grade})
  fit.start_node=nil;fit.requested_min_radius=p.radius
  local f=s.fits[fit_id];f.node=-100;f.junction_node=-100;f.min_radius=p.radius
  -- Free leads use the already-validated level profile without M.fit's positive
  -- vertical option. Preserve the explicit zero limit for realised junction checks.
  f.max_grade=p.vertical.max_grade;fit.max_grade=p.vertical.max_grade
  for _,ctrl in ipairs(f.controls) do geometry_bounds(cubic(ctrl),p.region,p.radius,p.vertical.max_grade) end
  local placement={original_edge=a.id,original_nodes={a.node0,a.node1},parameter=c.parameter,position=c.pos,
   canonical_forward=c.canonical_forward,subdivision_sampled_verified=true,game_constructed=false}
  if not p.execute then reply("ok",{game_constructed=false,placement=placement,through_before=before});return end
  assert(not s.mutationPending,"unreconciled_mutation");assert_fresh(a);if te then assert_fresh(te) end
  stage="build";local proposal=api.type.SimpleProposal.new();local segments,nodes={},{}
  local n=api.type.NodeAndEntity.new();n.entity=-100;n.comp.position=v(c.pos);nodes[1]=n
  local base=api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)
  local function segment(ctrl,id,node0,node1,clone)
   local e=api.type.SegmentAndEntity.new();e.entity=id;e.type=1
   if clone then e.comp=base:clone() end
   e.comp.node0=node0;e.comp.node1=node1;e.comp.position0=v(ctrl.p0);e.comp.position1=v(ctrl.p1);e.comp.tangent0=v(ctrl.t0);e.comp.tangent1=v(ctrl.t1)
   if not clone then e.comp.type=E.BaseEdgeType.NORMAL;e.comp.typeIndex=1;e.comp.laneConfigs=base.laneConfigs;e.comp.roadType=E.RoadType.TRACK;e.comp.roadTemplate=a.template;e.comp.roadStyle=a.style end
   segments[#segments+1]=e
  end
  segment(splits[1],-1,a.node0,-100,true);segment(splits[2],-2,-100,a.node1,true)
  for i,ctrl in ipairs(f.controls) do
   local finish=target and target.node_id or nil
   if i<#f.controls or not target then local nn=api.type.NodeAndEntity.new();nn.entity=-100-i;nn.comp.position=v(ctrl.p1);nodes[#nodes+1]=nn;finish=nn.entity end
   segment(ctrl,-2-i,i==1 and -100 or -100-i+1,finish,false)
  end
  proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd=segments;proposal.streetProposal.edgesToRemove={a.id}
  f.built=true;f.build_request=request_id;s.mutationPending=request_id
  local root=state:get() or {};root.pifLive=s;state:set(root)
  api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
   if success~=true then s.mutationPending=nil;reply("error",{error="native_construction_rejected",native_command_success=false,game_constructed="unknown",retry=false});return end
   local receipt=res.proposal.proposal;local ids={};for _,e in ipairs(receipt.addedSegments) do ids[#ids+1]=e.entity end
   local checked,value=pcall(function()
    local value=interior_readback(a,c,splits,f,te,ids,p,before)
    value.effects={receipt_added_segments=#ids,receipt_added_nodes=#receipt.addedNodes,receipt_removed_segments=#receipt.removedSegments,receipt_removed_nodes=#receipt.removedNodes,original_edge_removed=true}
    s.mutationPending=nil;return value
   end)
   reply(checked and "ok" or "mutation_unverified",checked and value or {error=tostring(value):sub(1,400),returned_edges=ids,game_constructed=true,retry=false})
  end)
 end)
 if not ok then local uncertain=s.mutationPending==request_id;reply(uncertain and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),game_constructed=uncertain and "unknown" or false,retry=false}) end
end
-- Two interior attachments, one coherent native crossover proposal.
local function reacquire_split(a,c,splits,ids)
 local left,right
 for _,id in ipairs(ids) do local e=edge(id)
  if e.node0==a.node0 then assert(not left,"ambiguous_split_left");left=e end
  if e.node1==a.node1 then assert(not right,"ambiguous_split_right");right=e end
 end
 assert(left and right and left.node1==right.node0,"split_shared_identity_missing")
 assert(near(left.p1,c.pos,.001) and left.node1~=a.node0 and left.node1~=a.node1,"split_location_mismatch")
 for i,e in ipairs({left,right}) do
  for _,k in ipairs({"p0","p1","t0","t1"}) do assert(near(e[k],splits[i][k],.001),"realised_through_controls_differ") end
  assert(e.template==a.template and e.style==a.style,"through_resources_differ")
 end
 assert(not api.engine.entityExists(a.id) or api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)==nil,"old_split_edge_still_present")
 return {original_edge=a.id,original_nodes={a.node0,a.node1},parameter=c.parameter,position=c.pos,junction_node=left.node1,
  original_removed=true,subdivision_sampled_verified=true,replacement_edges={left.id,right.id},
  incoming=c.canonical_forward and left or right,through=c.canonical_forward and right or left}
end
local function crossover_readback(a,b,c,d,splits,f,ids,p,before)
    assert(#ids==#f.controls+4,"crossover_receipt_incomplete")
    local placements={reacquire_split(a,c,splits[1],ids),reacquire_split(b,d,splits[2],ids)}
    local x,y=placements[1],placements[2];local excluded={}
    for _,t in ipairs(placements) do for _,id in ipairs(t.replacement_edges) do excluded[id]=true end end
    f.ids={};for _,id in ipairs(ids) do if not excluded[id] then f.ids[#f.ids+1]=id end end
    f.node=x.junction_node;f.junction_node=x.junction_node;f.anchor=x.incoming
    f.target={edge=y.through,node=y.junction_node,direction=d.outward_direction,grade=d.grade}
    local rb=M.readback(f);local junctions={x.junction_node,y.junction_node}
    for i,t in ipairs(placements) do local all=incidence(t.junction_node);local branchid=i==1 and rb.ordered_edges[1] or rb.ordered_edges[#rb.ordered_edges]
     assert(#all==3,"crossover_incidence_mismatch");local expected={[t.incoming.id]=true,[t.through.id]=true,[branchid]=true}
     for _,id in ipairs(all) do assert(expected[id],"crossover_incidence_mismatch") end;t.incident_edges=all
    end
    local routes={}
    local function other(e,n) return e.node0==n and e.node1 or e.node0 end
    for i,t in ipairs(placements) do routes[i]=M.route({source_edge=t.incoming.id,source_node=other(t.incoming,t.junction_node),target_edge=t.through.id,
     target_node=other(t.through,t.junction_node),junction_nodes=junctions,mode="TRAIN",required_edges=t.replacement_edges,max_length=p.max_route_length,
     geometry_constraints={all_path=true,edge_ids={},region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}});assert(routes[i].requested_route_verified,"through_movement_unverified") end
    local required={x.incoming.id,y.through.id};for _,id in ipairs(rb.ordered_edges) do required[#required+1]=id end
    local crossing=M.route({source_edge=x.incoming.id,source_node=other(x.incoming,x.junction_node),target_edge=y.through.id,target_node=other(y.through,y.junction_node),
     junction_nodes=junctions,mode="TRAIN",required_edges=required,max_length=p.max_route_length,
     geometry_constraints={all_path=true,edge_ids={},region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}})
    assert(crossing.requested_route_verified,"crossover_movement_unverified")
    return {game_constructed=true,placements=placements,readback=rb,through_before=before,through_after=routes,crossover_after=crossing,
     junction_nodes=junctions,native_effect_history_complete=false}
end
local repartition_native_fit
function M.crossover(p,s,state,request_id,respond)
 local stage,fit="inspect",nil
 local function reply(status,value) value.stage=stage;value.fit=fit;respond(request_id,status,value) end
 local ok,err=pcall(function()
  assert(type(p.execute)=="boolean","invalid_execution_option")
  assert(p.representation==nil or p.representation=="native_parts" or p.representation=="single_cubic_level","unsupported_crossover_representation")
  local a,b=assert_fresh(p.source.edge_snapshot),assert_fresh(p.target.edge_snapshot)
  assert(a.id~=b.id and a.node0~=b.node0 and a.node0~=b.node1 and a.node1~=b.node0 and a.node1~=b.node1,"distinct_through_tracks_required")
  assert(a.template==b.template and a.style==b.style,"incompatible_track_resources")
  local c,d=interior_location(a,p.location),interior_location(b,p.target_location)
  assert(math.abs(c.parameter-p.source.parameter)<=.000001 and math.abs(d.parameter-p.target.parameter)<=.000001,"stale_interior_location")
  local splits={interior_splits(a,c.parameter,p.region,p.radius,p.vertical.max_grade),interior_splits(b,d.parameter,p.region,p.radius,p.vertical.max_grade)}
  local before={}
  for i,x in ipairs({{a,c},{b,d}}) do
   before[i]=M.route({source_edge=x[1].id,source_node=x[2].canonical_forward and x[1].node0 or x[1].node1,
    target_edge=x[1].id,target_node=x[2].canonical_forward and x[1].node1 or x[1].node0,single_edge=true,
    junction_nodes=p.junction_nodes,mode="TRAIN",required_edges={x[1].id},max_length=p.max_route_length})
   assert(before[i].requested_route_verified,"existing_through_route_unverified")
  end
  stage="fit";local fitid=request_id.."_fit"
  fit=M.fit({end_xy={d.pos[1],d.pos[2]},end_direction=d.outward_direction,radius=p.radius,fit_radius=p.fit_radius or p.radius*1.25,region=p.region,vertical=p.vertical},s,fitid,
   {edge=b,pos=d.pos,direction=d.outward_direction,grade=d.grade},{anchor=a,pos=c.pos,direction=c.outward_direction,grade=c.grade})
  fit.requested_min_radius=p.radius;fit.start_node=nil;fit.target_node=nil
  local f=s.fits[fitid];f.min_radius=p.radius
  if p.representation=="single_cubic_level" then repartition_native_fit(f,fit,334) end
  for _,ctrl in ipairs(f.controls) do geometry_bounds(cubic(ctrl),p.region,p.radius,p.vertical.max_grade) end
  if not p.execute then reply("ok",{game_constructed=false,through_before=before});return end
  assert(not s.mutationPending,"unreconciled_mutation");assert_fresh(a);assert_fresh(b)
  stage="build";local proposal=api.type.SimpleProposal.new();local segments,nodes={},{}
  for i,candidate in ipairs({c,d}) do local n=api.type.NodeAndEntity.new();n.entity=-100*i;n.comp.position=v(candidate.pos);nodes[#nodes+1]=n end
  local function add(ctrl,n0,n1,base)
   local e=api.type.SegmentAndEntity.new();e.entity=-#segments-1;e.type=1;e.comp=base:clone()
   e.comp.node0=n0;e.comp.node1=n1;e.comp.position0=v(ctrl.p0);e.comp.position1=v(ctrl.p1);e.comp.tangent0=v(ctrl.t0);e.comp.tangent1=v(ctrl.t1)
   segments[#segments+1]=e
  end
  for i,x in ipairs({a,b}) do local base=api.engine.getComponent(x.id,api.type.ComponentType.BASE_EDGE)
   add(splits[i][1],x.node0,-100*i,base);add(splits[i][2],-100*i,x.node1,base)
  end
  local base=api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)
  for i,ctrl in ipairs(f.controls) do
   local finish=-200
   if i<#f.controls then local n=api.type.NodeAndEntity.new();n.entity=-300-i;n.comp.position=v(ctrl.p1);nodes[#nodes+1]=n;finish=n.entity end
   add(ctrl,i==1 and -100 or -300-i+1,finish,base)
  end
  proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd=segments;proposal.streetProposal.edgesToRemove={a.id,b.id}
  s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
  api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
   if success~=true then s.mutationPending=nil;reply("error",{error="native_construction_rejected",game_constructed="unknown",retry=false});return end
   local ids={};for _,e in ipairs(res.proposal.proposal.addedSegments) do ids[#ids+1]=e.entity end
   local checked,value=pcall(function()
    local value=crossover_readback(a,b,c,d,splits,f,ids,p,before);s.mutationPending=nil;return value
   end)
   reply(checked and "ok" or "mutation_unverified",checked and value or {error=tostring(value):sub(1,400),returned_edges=ids,game_constructed=true,retry=false})
  end)
 end)
 if not ok then reply(s.mutationPending==request_id and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),game_constructed=s.mutationPending==request_id and "unknown" or false,retry=false}) end
end

-- Bounded explicit removal of an observed failed test branch, not rollback.
function M.remove_branch(p,s,state,request_id,respond)
 assert(p.free_ends==nil or type(p.free_ends)=="boolean","invalid_free_end_removal_option")
 assert(p.exact_chain==nil or type(p.exact_chain)=="boolean","invalid_exact_chain_option")
 local exact=p.exact_chain==true
 assert(not exact or (not p.free_ends and not p.isolated_fixture and not p.compensation),"conflicting_chain_removal_modes")
 assert(p.authorised==true and type(p.edges)=="table" and #p.edges>=1 and #p.edges<=((p.free_ends or exact) and 16 or 8),"invalid_branch_removal")
 local compensation=p.compensation
 if compensation then
  local r=compensation.original_response;local q=compensation.original_params
  assert(type(compensation.reason)=="string" and #compensation.reason>0 and type(compensation.authority)=="string" and #compensation.authority>0,"explicit_compensation_authority_required")
  assert(r and r.request_id==compensation.original_request and r.operation=="crossover" and r.status=="mutation_unverified" and r.result.game_constructed==true and q.execute==true,"constructed_crossover_receipt_required")
  local saved=s.requests[compensation.original_request]
  if r.session==s.session then assert(saved and saved.response and saved.response.result.returned_edges and #saved.response.result.returned_edges==#r.result.returned_edges,"native_receipt_missing")
   for i,id in ipairs(r.result.returned_edges) do assert(saved.response.result.returned_edges[i]==id,"native_receipt_mismatch") end
  else assert(not s.mutationPending,"cross_session_compensation_guard_conflict") end
  assert(not s.mutationPending or s.mutationPending==compensation.original_request,"unrelated_mutation_pending")
  assert(not p.free_ends and not p.isolated_fixture and #p.edges==r.result.fit.pieces,"exact_crossover_compensation_only")
  local controls=r.result.fit.controls;local ids=r.result.returned_edges;assert(#ids==#controls+4,"incomplete_original_receipt")
  local seen={};for _,id in ipairs(ids) do assert(not seen[id],"duplicate_original_receipt");seen[id]=true;edge(id) end
  for i,e in ipairs(p.edges) do assert(seen[e.id],"removal_outside_original_receipt")
   for _,k in ipairs({"p0","p1","t0","t1"}) do assert(near(e[k],controls[i][k],.001),"removal_controls_not_original_fit") end
  end
  local f=r.result.fit
  local c={parameter=q.source.parameter,pos=f.start,canonical_forward=q.source.canonical_forward}
  local d={parameter=q.target.parameter,pos=f.finish,canonical_forward=q.target.canonical_forward}
  local a,b=q.source.edge_snapshot,q.target.edge_snapshot
  local x=reacquire_split(a,c,interior_splits(a,c.parameter,q.region,q.radius,q.vertical.max_grade),ids)
  local y=reacquire_split(b,d,interior_splits(b,d.parameter,q.region,q.radius,q.vertical.max_grade),ids)
  assert(p.edges[1].node0==x.junction_node and p.edges[#p.edges].node1==y.junction_node,"compensation_attachment_mismatch")
  for _,v in ipairs({x,y}) do for _,id in ipairs(v.replacement_edges) do for _,e in ipairs(p.edges) do assert(e.id~=id,"through_edge_removal_forbidden") end end end
 else assert(not s.mutationPending,"unreconciled_mutation") end
 local ids,expected={},{};local interior={};local selected_nodes={};local retained={};local retained_nodes={}
 for i,snapshot in ipairs(p.edges) do
  local a=assert_fresh(snapshot);assert(not expected[a.id],"duplicate_removal_edge");expected[a.id]=true;ids[#ids+1]=a.id
  local base=api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)
  assert(base.type==E.BaseEdgeType.NORMAL and #base.objects==0,"unsupported_removal_edge")
  local owner=api.engine.system.streetConnectorSystem.getConstructionEntityForEdge(a.id);assert(not (owner and owner>0),"construction_owned_removal")
  if exact then
   assert(a.node0~=a.node1,"removal_chain_loop")
   for _,node in ipairs({a.node0,a.node1}) do selected_nodes[node]=selected_nodes[node] or {};table.insert(selected_nodes[node],a.id) end
  elseif i>1 then assert(p.edges[i-1].node1==a.node0,"removal_chain_disconnected");interior[#interior+1]=a.node0 end
 end
 if exact then
  local endpoints={};local visited={};local frontier={p.edges[1].node0}
  while #frontier>0 do local node=table.remove(frontier)
   if not visited[node] then visited[node]=true;for _,id in ipairs(selected_nodes[node]) do local e=edge(id);frontier[#frontier+1]=e.node0==node and e.node1 or e.node0 end end
  end
  for node,chosen in pairs(selected_nodes) do
   assert(visited[node] and #chosen<=2,"removal_chain_branched_or_disconnected")
   local all,owner=incidence(node);assert(not(owner and owner>0),"construction_owned_removal_node")
   if #chosen==2 then assert(#all==2,"removal_node_not_exclusive");interior[#interior+1]=node
   else
    endpoints[#endpoints+1]=node;assert(#all>=1 and #all<=16,"removal_endpoint_degree_unsupported")
    local selected_count=0;local remaining={}
    for _,id in ipairs(all) do if expected[id] then selected_count=selected_count+1 else remaining[#remaining+1]=id end end
    assert(selected_count==1,"removal_endpoint_chain_ambiguous")
    if #all==1 then interior[#interior+1]=node
    else
     retained_nodes[node]=remaining
     for _,id in ipairs(remaining) do retained[#retained+1]={node=node,snapshot=edge(id)} end
    end
   end
  end
  assert(#endpoints==2,"removal_chain_not_open")
 end
 for _,node in ipairs(interior) do local all,owner=incidence(node);assert((#all==2 or (exact and #all==1)) and not(owner and owner>0),"removal_node_not_exclusive");for _,id in ipairs(all) do assert(expected[id],"removal_node_not_exclusive") end end
 local isolated=p.isolated_fixture==true
 if exact then
  -- Endpoint policy and exclusive nodes have already been established above.
 elseif isolated then
  assert(#p.edges==1 and not p.free_ends,"isolated_fixture_needs_one_edge")
  for _,node in ipairs({p.edges[1].node0,p.edges[1].node1}) do local all,owner=incidence(node);assert(#all==1 and all[1]==ids[1] and not(owner and owner>0),"fixture_not_isolated");interior[#interior+1]=node end
 elseif p.free_ends then
  for _,node in ipairs({p.edges[1].node0,p.edges[#p.edges].node1}) do
   local all,owner=incidence(node);assert(#all==2 and not(owner and owner>0),"removal_endpoint_not_two_edge_attachment")
   local removed=0;for _,id in ipairs(all) do if expected[id] then removed=removed+1 else edge(id) end end
   assert(removed==1,"removal_endpoint_chain_ambiguous")
  end
 end
 local proposal=api.type.SimpleProposal.new();proposal.streetProposal.edgesToRemove=ids;proposal.streetProposal.nodesToRemove=interior
 s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
 api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(_,success)
  local ok,value=pcall(function()
   assert(success==true,"native_removal_rejected")
   for _,id in ipairs(ids) do assert(not api.engine.entityExists(id) or api.engine.getComponent(id,api.type.ComponentType.BASE_EDGE)==nil,"branch_edge_removal_unverified") end
   if exact then
    for _,node in ipairs(interior) do assert(not api.engine.entityExists(node),"exact_chain_node_removal_unverified") end
    local attachments={}
    for node,remaining in pairs(retained_nodes) do local all,owner=incidence(node);local wanted={}
     for _,id in ipairs(remaining) do wanted[id]=true end
     assert(#all==#remaining and not(owner and owner>0),"retained_chain_incidence_unverified")
     for _,id in ipairs(all) do assert(wanted[id],"retained_chain_incidence_unverified") end
    end
    for _,r in ipairs(retained) do local a=assert_fresh(r.snapshot)
     assert(a.node0==r.node or a.node1==r.node,"retained_chain_attachment_unverified")
     attachments[#attachments+1]={node=r.node,edge=a,incident_edges=retained_nodes[r.node]}
    end
    s.mutationPending=nil;return {game_constructed=true,exact_chain=true,removed_edges=ids,removed_nodes=interior,retained_attachments=attachments,native_effect_history_complete=false,rollback=false}
   end
   if isolated then
    for _,node in ipairs(interior) do assert(not api.engine.entityExists(node),"isolated_fixture_node_removal_unverified") end
    s.mutationPending=nil;return {game_constructed=true,removed_edges=ids,removed_nodes=interior,isolated_fixture=true,native_effect_history_complete=false,rollback=false}
   end
   local endpoints={p.edges[1].node0,p.edges[#p.edges].node1};local observations={}
   for _,node in ipairs(endpoints) do local all=incidence(node);assert(#all==(p.free_ends==true and 1 or 2),"remaining_through_incidence_unverified");for _,id in ipairs(all) do edge(id) end;observations[#observations+1]={node=node,incident_edges=all} end
   local through={}
   if compensation then
    local q=compensation.original_params
    for _,o in ipairs(observations) do
     local a,b=edge(o.incident_edges[1]),edge(o.incident_edges[2])
     local function other(e) return e.node0==o.node and e.node1 or e.node0 end
     for _,reverse in ipairs({false,true}) do
      local x,y=reverse and b or a,reverse and a or b
      local check=M.route({source_edge=x.id,source_node=other(x),target_edge=y.id,target_node=other(y),junction_nodes=endpoints,mode="TRAIN",required_edges={a.id,b.id},max_length=q.max_route_length,
       geometry_constraints={all_path=true,edge_ids={},region=q.region,radius=q.radius,max_grade=q.vertical.max_grade}})
      assert(check.requested_route_verified,"compensated_through_function_unverified");through[#through+1]=check
     end
    end
    s.compensated=s.compensated or {};s.compensated[compensation.original_request]={removal_request=request_id,original_build_accepted=false,original_params=compensation.original_params}
   end
   s.mutationPending=nil;return {game_constructed=true,removed_edges=ids,remaining_endpoints=observations,through_after=through,
    compensated_request=compensation and compensation.original_request or nil,remaining_through_verified=compensation and true or nil,original_build_accepted=false,native_effect_history_complete=false,rollback=false}
  end)
  respond(request_id,ok and "ok" or "mutation_unverified",ok and value or {game_constructed="unknown",error=tostring(value):sub(1,400),retry=false})
 end)
end

function M.verify_crossover(p,s)
 local a,b=p.source.edge_snapshot,p.target.edge_snapshot
 local c={parameter=p.source.parameter,pos=p.fit.start,canonical_forward=p.source.canonical_forward}
 local d={parameter=p.target.parameter,pos=p.fit.finish,canonical_forward=p.target.canonical_forward,outward_direction=p.target.outward_direction,grade=p.target.grade}
 assert(a.id==p.source.edge_id and b.id==p.target.edge_id and a.id~=b.id,"invalid_recorded_crossover")
 assert(finite(c.parameter) and c.parameter>=.05 and c.parameter<=.95 and finite(d.parameter) and d.parameter>=.05 and d.parameter<=.95,"invalid_recorded_split")
 assert(type(p.edge_ids)=="table" and #p.edge_ids==p.fit.pieces+4 and #p.edge_ids<=12,"invalid_crossover_receipt")
 local splits={interior_splits(a,c.parameter,p.region,p.radius,p.vertical.max_grade),interior_splits(b,d.parameter,p.region,p.radius,p.vertical.max_grade)}
 assert(near(c.pos,splits[1][1].p1,.001) and near(d.pos,splits[2][1].p1,.001),"recorded_crossover_location_mismatch")
 local f={controls=p.fit.controls,samples={},region=p.region,grade=p.fit.grade,end_grade=p.fit.end_grade,max_grade=p.vertical.max_grade,min_radius=p.radius}
 assert(#f.controls==p.fit.pieces,"recorded_controls_incomplete")
 for i,ctrl in ipairs(f.controls) do f.samples[i]={};for _,u in ipairs({0,.25,.5,.75,1}) do local pos,dir=sample(cubic(ctrl),u);f.samples[i][#f.samples[i]+1]={u=u,pos=pos,dir=dir,base_pos=pos} end end
 local value=crossover_readback(a,b,c,d,splits,f,p.edge_ids,p,p.through_before)
 value.reconciled_current_state=true;value.automatic_replay=false
 if s and s.mutationPending==p.original_request then s.mutationPending=nil end
 return value
end

-- Read-only reconciliation from recorded controls and exact returned identities.
-- No fitting, preview or construction is performed; do not reconstruct engine history.
function M.verify_interior(p)
 local a=p.source.edge_snapshot;local c={parameter=p.parameter,canonical_forward=p.source.canonical_forward,pos=p.fit.start}
 assert(a.id==p.source.edge_id and finite(c.parameter) and c.parameter>=.05 and c.parameter<=.95,"invalid_recorded_interior")
 assert(type(p.edge_ids)=="table" and #p.edge_ids==p.fit.pieces+2 and #p.edge_ids<=10,"invalid_split_receipt")
 local te,td,tg=nil,nil,p.fit.end_grade
 if p.target then
  te=assert_fresh(p.target.edge_snapshot);local _,tp;_,tp,td,tg=anchor({anchor_edge=te.id,anchor_node=p.target.node_id});td={-td[1],-td[2],0};tg=-tg
 else
  vector(p.end_xyz);vector(p.end_direction)
  assert(#p.end_xyz==3 and p.vertical.max_grade==0 and finite(p.fit.grade) and math.abs(p.fit.grade)<=.000001 and
   finite(tg) and math.abs(tg)<=.000001,"recorded_free_lead_not_level")
 end
 local splits=interior_splits(a,c.parameter,p.region,p.radius,p.vertical.max_grade)
 local f={anchor=a,target=te and {edge=te,node=p.target.node_id,direction=td} or nil,controls=p.fit.controls,samples={},region=p.region,grade=p.fit.grade,end_grade=tg,max_grade=p.vertical.max_grade,min_radius=p.radius}
 assert(#f.controls==p.fit.pieces and near(c.pos,splits[1].p1,.001),"recorded_split_fit_mismatch")
 if not te then local last=f.controls[#f.controls]
  assert(near(last.p1,p.end_xyz,.001) and angle(last.t1,p.end_direction)<=.1,"recorded_free_lead_endpoint_mismatch")
 end
 for i,ctrl in ipairs(f.controls) do f.samples[i]={};for _,u in ipairs({0,.25,.5,.75,1}) do local pos,dir=sample(cubic(ctrl),u);f.samples[i][#f.samples[i]+1]={u=u,pos=pos,dir=dir,base_pos=pos} end end
 local result=interior_readback(a,c,splits,f,te,p.edge_ids,p,p.through_before)
 result.reconciled_current_state=true;result.automatic_replay=false;result.native_effect_history_complete=false
 return result
end
function M.test_approach(p,s,state,request_id,respond)
 assert(p.authorised==true and finite(p.length) and p.length>=5 and p.length<=60,"invalid_test_approach")
 assert(not s.mutationPending,"unreconciled_mutation")
 local f,c,direction
 if p.fixture then
  -- Explicit disposable test-stub placement, not production corridor fitting.
  local q=p.fixture;vector(q.position);vector(q.travel_direction)
  assert(#q.position==3 and #q.travel_direction==2 and finite(q.grade) and math.abs(q.grade)<=.04,"invalid_test_fixture_seed")
  local a=edge(q.template_edge);assert(type(q.region)=="table","fixture_region_required")
  vector(q.region.min);vector(q.region.max)
  assert(#q.region.min==3 and #q.region.max==3,"fixture_region_needs_xyz")
  for i=1,3 do assert(q.region.max[i]>q.region.min[i] and q.region.max[i]-q.region.min[i]<=100,"fixture_region_bound") end
  in_region(q.position,q.region);direction=norm(q.travel_direction)
  f={anchor=a,region=q.region,end_grade=q.grade};c={p1=q.position}
 else
  M.fit(p.brief,s,request_id.."_fixture_fit")
  f=s.fits[request_id.."_fixture_fit"];c=f.controls[#f.controls];direction=norm(c.t1)
 end
 local finish={c.p1[1]+direction[1]*p.length,c.p1[2]+direction[2]*p.length,c.p1[3]+f.end_grade*p.length}
 in_region(finish,f.region);assert_fresh(f.anchor)
 local resource=api.res.streetTemplateRep.get(api.res.streetTemplateRep.find(f.anchor.template))
 assert(resource and resource.laneConfigs,"track_template_unavailable")
 local proposal=api.type.SimpleProposal.new();local nodes={}
 for i,pos in ipairs({c.p1,finish}) do local n=api.type.NodeAndEntity.new();n.entity=-i-1;n.comp.position=v(pos);nodes[i]=n end
 local e=api.type.SegmentAndEntity.new();e.entity=-1;e.type=1;e.comp.node0=-2;e.comp.node1=-3
 e.comp.position0=v(c.p1);e.comp.position1=v(finish)
 e.comp.tangent0=v({direction[1]*p.length,direction[2]*p.length,f.end_grade*p.length});e.comp.tangent1=e.comp.tangent0
 e.comp.type=E.BaseEdgeType.NORMAL;e.comp.typeIndex=1;e.comp.laneConfigs=resource.laneConfigs
 e.comp.roadTemplate=f.anchor.template;e.comp.roadStyle=f.anchor.style;e.comp.roadType=E.RoadType.TRACK
 proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd={e}
 s.mutationPending=request_id
 local root=state:get() or {};root.pifLive=s;state:set(root)
 api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
  local ok,result=pcall(function()
   assert(success==true,"native_test_approach_rejected")
   local receipt=res.proposal.proposal;assert(#receipt.addedSegments==1,"approach_receipt_incomplete")
   local actual=M.inspect({edge_ids={receipt.addedSegments[1].entity}})
   assert(near(actual.edges[1].p0,c.p1,.001) and near(actual.edges[1].p1,finish,.001),"approach_realisation_mismatch")
   actual.game_constructed=true;actual.test_fixture=true;return actual
  end)
  if ok then s.mutationPending=nil end
  respond(request_id,ok and "ok" or "mutation_unverified",ok and result or {error=tostring(result):sub(1,400),game_constructed="unknown",retry=false})
 end)
end
-- Caller-paired ordinary four-arm TRACK node. Version1 cardinal pairing retained.
local function crossing_roles(p)
 local pairing=p.pairs or {{"W","E"},{"S","N"}}
 assert(type(pairing)=="table" and #pairing==2,"two_explicit_crossing_pairs_required")
 local names,seen={},{}
 for _,pair in ipairs(pairing) do
  assert(type(pair)=="table" and #pair==2,"two_roles_per_crossing_pair_required")
  for _,name in ipairs(pair) do assert(type(name)=="string" and #name<=40 and not seen[name],"distinct_crossing_roles_required");seen[name]=true;names[#names+1]=name end
 end
 assert(type(p.ports)=="table","four_named_ports_required")
 local count=0;for name in pairs(p.ports) do assert(seen[name],"unexpected_crossing_port");count=count+1 end
 assert(count==4,"four_named_ports_required");return names,pairing
end
-- P35/P36: native formation semantics are qualified by current movement readback.
-- No custom transport flags or presumed movement semantics are supplied.
function M.inspect_degree_four(p)
 local arms,ports={},{}
 local names,pairing=crossing_roles(p)
 local center=api.engine.getComponent(p.center_node,api.type.ComponentType.BASE_NODE)
 assert(center,"current_center_node_missing")
 local center_position=arr(center.position)
 if p.center then assert(near(center_position,p.center,.001),"center_position_changed") end
 assert(type(p.arm_edges)=="table" and #p.arm_edges==4,"four_recorded_arms_required")
 local ids=api.engine.system.streetSystem.getNodeSegments(p.center_node)
 assert(#ids==4,"current_degree_four_incidence_missing")
 local expected={};for _,id in ipairs(p.arm_edges) do expected[id]=true end
 for _,id in ipairs(ids) do assert(expected[id],"current_crossing_incidence_changed");arms[#arms+1]=edge(id) end
 for name,q in pairs(p.ports) do
  local stub=assert_fresh(q.edge_snapshot);assert(q.node_id==stub.node0 or q.node_id==stub.node1,"attachment_changed")
  local attached=nil
  for _,a in ipairs(arms) do if a.node0==q.node_id or a.node1==q.node_id then assert(not attached,"ambiguous_arm_identity");attached=a end end
  assert(attached and (attached.node0==p.center_node or attached.node1==p.center_node),"exact_arm_attachment_missing")
  ports[name]={stub=stub,arm=attached,node=q.node_id}
 end
 local network=api.engine.getComponent(p.center_node,api.type.ComponentType.TRANSPORT_NETWORK)
 local movements={};local truncated=false
 if network and network.edges then for i,row in ipairs(network.edges) do
  if i<=16 then
   local connections={};for j,n in ipairs(row.conns) do if j<=4 then connections[#connections+1]=node_id(n) else truncated=true end end
   movements[#movements+1]={index=i-1,TRAIN=row.transportModes[E.TransportMode.TRAIN]==true,connections=connections,length=row.geometry.length,forward_only=row.forwardOnly}
  else truncated=true end
 end end
 local cfg=api.engine.getComponent(p.center_node,api.type.ComponentType.BASE_NODE_CONFIG)
 local node_config={available=cfg~=nil,double_slip_switch="unknown"}
 if cfg then node_config.double_slip_switch=cfg.doubleSlipSwitch end
 local result={experimental=true,game_constructed=false,center_node=p.center_node,center_position=center_position,arms=arms,ports=ports,
  native_node_transport=movements,transport_truncated=truncated,base_node_config=node_config,pairs=pairing,routes={},
  native_effect_history_complete=false,train_traversal="unprobed",reservation_availability="unprobed"}
 for _,from in ipairs(names) do for _,to in ipairs(names) do if from~=to then
  local a,z=ports[from].stub,ports[to].stub
  local q={source_edge=a.id,source_node=a.node0==ports[from].node and a.node1 or a.node0,
   target_edge=z.id,target_node=z.node0==ports[to].node and z.node1 or z.node0,
   required_edges={a.id,z.id},mode="TRAIN",max_length=1000,junction_nodes={p.center_node}}
  local ok,r=pcall(M.route,q);result.routes[#result.routes+1]={from=from,to=to,status=ok and "ok" or "route_error",result=ok and r or {error=tostring(r):sub(1,400)}}
 end end end
 return result
end
function M.degree_four_candidate(p,s,state,request_id,respond)
 assert(type(p.execute)=="boolean" and type(p.ports)=="table","experimental_candidate_parameters_required")
 vector(p.center);assert(#p.center==3,"center_XYZ_required");in_region(p.center,p.region)
 local names,pairing=crossing_roles(p)
 local nodes={};local segments={};local before={}
 local centre=api.type.NodeAndEntity.new();centre.entity=-10;centre.comp.position=v(p.center);nodes[1]=centre
 local resource,template,style
 for i,name in ipairs(names) do
  local q=p.ports[name];assert(q,"named_arm_missing")
  local a=assert_fresh(q.edge_snapshot);local e,pos,direction,grade=anchor({anchor_edge=a.id,anchor_node=q.node_id})
  local inc=api.engine.system.streetSystem.getNodeSegments(q.node_id);assert(#inc==1 and inc[1]==a.id,"candidate_attachment_not_free")
  local dx,dy=p.center[1]-pos[1],p.center[2]-pos[2];local length=math.sqrt(dx*dx+dy*dy)
  assert(length>0 and length<=300 and (p.pairs or length>=20) and math.abs(pos[3]-p.center[3])<=.001 and math.abs(grade)<=1e-6,"level_bounded_candidate_required")
  -- The caller supplies one rotated/translated orthogonal experiment. Validate
  -- its actual native arm directions, rather than imposing any transport edges.
  assert(angle(direction,{dx,dy,0})<=.1,"arm_tangent_not_toward_center")
  if not template then template=a.template;style=a.style;resource=api.res.streetTemplateRep.get(api.res.streetTemplateRep.find(template)) end
  assert(a.template==template and a.style==style and resource and resource.laneConfigs,"incompatible_candidate_resources")
  in_region(pos,p.region)
  before[i]=M.route({source_edge=a.id,source_node=a.node0,target_edge=a.id,target_node=a.node1,single_edge=true,required_edges={a.id},mode="TRAIN",max_length=1000})
  assert(before[i].requested_route_verified,"original_stub_route_unverified")
  local seg=api.type.SegmentAndEntity.new();seg.entity=-i;seg.type=1
  seg.comp.node0=q.node_id;seg.comp.node1=-10;seg.comp.position0=v(pos);seg.comp.position1=v(p.center)
  seg.comp.tangent0=v({dx,dy,0});seg.comp.tangent1=seg.comp.tangent0
  seg.comp.type=E.BaseEdgeType.NORMAL;seg.comp.typeIndex=1;seg.comp.laneConfigs=resource.laneConfigs
  seg.comp.roadTemplate=template;seg.comp.roadStyle=style;seg.comp.roadType=E.RoadType.TRACK;segments[i]=seg
 end
 local function toward(q) local _,pos=anchor({anchor_edge=q.edge_snapshot.id,anchor_node=q.node_id});return norm({p.center[1]-pos[1],p.center[2]-pos[2]}) end
 local w,e,n,ss=toward(p.ports[pairing[1][1]]),toward(p.ports[pairing[1][2]]),toward(p.ports[pairing[2][1]]),toward(p.ports[pairing[2][2]])
 local dot=math.abs(w[1]*n[1]+w[2]*n[2])
 assert(angle(w,{-e[1],-e[2]})<=.1 and angle(n,{-ss[1],-ss[2]})<=.1 and dot<.999,"nondegenerate_opposed_arm_domain_required")
 if not p.pairs then assert(dot<=.001,"orthogonal_opposed_arm_domain_required") end
 local value={experimental=true,stage="preflight",game_constructed=false,through_before=before,
  pairs=pairing,crossing_angle_deg=math.acos(math.min(1,dot))*180/math.pi,requested_representation="four_ordinary_TRACK_arms_one_BaseNode",crossing_semantics="unqualified",preview="no_existing_SimpleProposal_preview_exposed"}
 if not p.execute then respond(request_id,"ok",value);return end
 assert(p.authorised==true and not s.mutationPending,"explicit_authority_and_clear_journal_required")
 local proposal=api.type.SimpleProposal.new();proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd=segments
 s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
 api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
  local ids={};value.stage="build";value.native_command_success=success==true
  if success~=true then value.game_constructed="unknown";value.error="native_degree_four_candidate_rejected";value.retry=false;respond(request_id,"mutation_unverified",value);return end
  local ok,out=pcall(function()
   local receipt=res.proposal.proposal
   value.effects={added_segments=#receipt.addedSegments,added_nodes=#receipt.addedNodes,removed_segments=#receipt.removedSegments,removed_nodes=#receipt.removedNodes}
   for _,x in ipairs(receipt.addedSegments) do ids[#ids+1]=x.entity end;value.returned_edges=ids
   assert(#ids==4,"candidate_receipt_not_four_TRACK_arms")
   local centres={}
   for _,id in ipairs(ids) do local a=edge(id)
    for _,node in ipairs({a.node0,a.node1}) do local known=false;for _,q in pairs(p.ports) do if node==q.node_id then known=true end end;if not known then centres[node]=(centres[node] or 0)+1 end end
   end
   local center,count=nil,0;for node,c in pairs(centres) do assert(c==4,"new_shared_center_identity_unestablished");center=node;count=count+1 end;assert(count==1,"one_native_center_required")
   value.readback=M.inspect_degree_four({center_node=center,center=p.center,arm_edges=ids,ports=p.ports,pairs=p.pairs})
   value.center_node=center;value.arm_edges=ids;value.game_constructed=true;value.stage="readback";s.mutationPending=nil;return value
  end)
  if not ok then value.error=tostring(out):sub(1,400);value.game_constructed="unknown";value.retry=false end
  respond(request_id,ok and "ok" or "mutation_unverified",ok and out or value)
 end)
end
-- P38: remove internal fit-part nodes only after checking a single native cubic
-- against every original part. This is a sampled lowering approximation, not an
-- engine minimum-segment rule or continuous equality proof.
repartition_native_fit=function(f,report,divisions)
 local original=f.controls;local first,last=original[1],original[#original];local total=f.total_length
 assert(#original>=1 and #original<=8 and total>0 and total<=800,"bounded_repartition_fit_required")
 assert(math.abs(f.grade)<=.000001 and math.abs(f.end_grade)<=.000001 and math.abs(first.p0[3]-last.p1[3])<=.000001,"repartition_level_only")
 for _,part in ipairs(original) do
  assert(math.abs(part.p0[3]-first.p0[3])<=.000001 and math.abs(part.p1[3]-first.p0[3])<=.000001 and math.abs(part.t0[3])<=.000001 and math.abs(part.t1[3])<=.000001,"repartition_level_only")
 end
 divisions=divisions or 32
 local a,b=norm(first.t0),norm(last.t1)
 local c={p0=first.p0,p1=last.p1,t0={a[1]*total,a[2]*total,0},t1={b[1]*total,b[2]*total,0},length=total}
 local cg=cubic(c);local samples,offset,maxerr={},0,0
 for _,part in ipairs(original) do
  local source=cubic(part)
  for j=0,divisions do
   local u=(offset+j/divisions*part.length)/total;local pos,dir=sample(source,j/divisions);local bp=sample(cg,u)
   maxerr=math.max(maxerr,distance(pos,bp))
   samples[#samples+1]={u=u,pos=pos,dir=dir,base_pos=bp}
  end
  offset=offset+part.length
 end
 assert(maxerr+report.sampled_XY_error<=.1,"scissors_repartition_outside_conversion_tolerance")
 assert(angle(c.t0,first.t0)<=.1 and angle(c.t1,last.t1)<=.1,"scissors_repartition_heading_mismatch")
 local radius=geometry_bounds(cg,f.region,f.min_radius,0)
 report.original_native_controls=original
 report.repartition={original_pieces=#original,proposal_pieces=1,sample_count=#samples,
  sampled_XY_error=maxerr,sampled_combined_conversion_error=maxerr+report.sampled_XY_error,
  sampled_only=true,min_sampled_radius=radius}
 report.controls={c};report.pieces=1;report.min_sampled_converted_radius=radius
 f.controls={c};f.samples={samples}
end
-- Complete connected pointwork avoids isolated near-parent free turnout stubs.
local function repartition_two_piece_level(f,report)
 local original=f.controls;local total=f.total_length;local height=original[1].p0[3]
 assert(#original>=1 and #original<=8 and finite(total) and total>0 and total<=800,"bounded_two_piece_fit_required")
 assert(math.abs(f.grade)<=1e-6 and math.abs(f.end_grade)<=1e-6,"two_piece_level_only")
 for _,c in ipairs(original) do assert(math.abs(c.p0[3]-height)<=1e-6 and math.abs(c.p1[3]-height)<=1e-6 and math.abs(c.t0[3])<=1e-6 and math.abs(c.t1[3])<=1e-6,"two_piece_level_only") end
 local function evaluate(c,u,derivative)
  local weights=derivative and {6*u*u-6*u,-6*u*u+6*u,3*u*u-4*u+1,3*u*u-2*u}
   or {2*u^3-3*u*u+1,-2*u^3+3*u*u,u^3-2*u*u+u,u^3-u*u}
  local out={};for k=1,3 do out[k]=weights[1]*c.p0[k]+weights[2]*c.p1[k]+weights[3]*c.t0[k]+weights[4]*c.t1[k] end;return out
 end
 local function original_sample(s)
  for i,c in ipairs(original) do if s<=c.length or i==#original then return evaluate(c,s/c.length),evaluate(c,s/c.length,true) end;s=s-c.length end
 end
 local controls,samples={},{};local maxerr,minimum=0,math.huge;local handles={}
 for half=1,2 do
  local start=(half-1)*total/2;local finish=half*total/2
  local p0,d0=original_sample(start);local p1,d1=original_sample(finish);local a,b=norm(d0),norm(d1)
  local aa,ab,bb,ar,br=0,0,0,0,0
  for j=0,200 do
   local u=j/200;local q=original_sample(start+(finish-start)*u)
   local h0,h1,h2,h3=2*u^3-3*u*u+1,-2*u^3+3*u*u,u^3-2*u*u+u,u^3-u*u
   for k=1,2 do local x,y,z=h2*a[k],h3*b[k],q[k]-h0*p0[k]-h1*p1[k]
    aa=aa+x*x;ab=ab+x*y;bb=bb+y*y;ar=ar+x*z;br=br+y*z
   end
  end
  local det=aa*bb-ab*ab;assert(finite(det) and det>1e-12,"two_piece_singular_handles")
  local v0,v1=(ar*bb-br*ab)/det,(br*aa-ar*ab)/det
  assert(finite(v0) and finite(v1) and v0>0 and v1>0,"two_piece_invalid_handles")
  local c={p0=p0,p1=p1,t0={a[1]*v0,a[2]*v0,0},t1={b[1]*v1,b[2]*v1,0},length=finish-start}
  local cg=cubic(c);samples[half]={};controls[half]=c;handles[half]={v0,v1}
  for j=0,1000 do
   local u=j/1000;local q,d=original_sample(start+(finish-start)*u);local pos=sample(cg,u)
   maxerr=math.max(maxerr,distance(q,pos))
   if j%5==0 then samples[half][#samples[half]+1]={u=u,pos=q,dir=d,base_pos=pos} end
  end
  minimum=math.min(minimum,(geometry_bounds(cg,f.region,f.min_radius,f.max_grade,1000)))
  assert(angle(c.t0,d0)<=.1 and angle(c.t1,d1)<=.1,"two_piece_heading_mismatch")
 end
 assert(near(controls[1].p0,original[1].p0,.001) and near(controls[2].p1,original[#original].p1,.001) and near(controls[1].p1,controls[2].p0,.001),"two_piece_boundary_mismatch")
 assert(angle(controls[1].t1,controls[2].t0)<=.1,"two_piece_join_heading_mismatch")
 assert(maxerr+report.sampled_XY_error<=.1,"two_piece_outside_conversion_tolerance")
 report.original_native_controls=report.original_native_controls or original;report.pre_two_piece_controls=original
 report.repartition={method="two_piece_level_midpoint_ls201",original_pieces=#original,proposal_pieces=2,handles=handles,
  check_samples_per_half=1001,sampled_XY_error=maxerr,sampled_combined_conversion_error=maxerr+report.sampled_XY_error,min_sampled_radius=minimum,sampled_only=true}
 report.controls=controls;report.pieces=2;report.min_sampled_converted_radius=minimum;f.controls=controls;f.samples=samples
end
function M.repair_crossover(p,s,state,request_id,respond)
 local comp=s.compensated and s.compensated[p.original_request]
 assert(comp and comp.removal_request==p.compensation_request,"verified_compensation_required")
 assert(type(p.execute)=="boolean" and p.representation=="two_piece_level_midpoint","explicit_two_piece_repair_required")
 local q=comp.original_params
 assert(p.radius==q.radius and p.fit_radius==(q.fit_radius or q.radius*1.25),"repair_criterion_changed")
 for k=1,3 do assert(p.region.min[k]==q.region.min[k] and p.region.max[k]==q.region.max[k],"repair_region_changed") end
 assert(p.vertical.max_grade==q.vertical.max_grade,"repair_grade_changed")
 local removal=s.requests[p.compensation_request].response.result;local endpoints=removal.remaining_endpoints
 assert(p.source.node_id==endpoints[1].node and p.target.node_id==endpoints[2].node,"repair_endpoint_identity_changed")
 local a,b=assert_fresh(p.source.edge_snapshot),assert_fresh(p.target.edge_snapshot)
 local function member(id,rows) for _,x in ipairs(rows) do if x==id then return true end end;return false end
 assert(member(a.id,endpoints[1].incident_edges) and member(b.id,endpoints[2].incident_edges) and a.template==b.template and a.style==b.style,"repair_through_attachment_mismatch")
 local _,pos,dir,grade=anchor({anchor_edge=a.id,anchor_node=p.source.node_id})
 local _,tp,td,tg=anchor({anchor_edge=b.id,anchor_node=p.target.node_id});td={-td[1],-td[2],0};tg=-tg
 local fitid=request_id.."_fit"
 local fit=M.fit({end_xy={tp[1],tp[2]},end_direction=td,radius=p.radius,fit_radius=p.fit_radius,region=p.region,vertical=p.vertical},s,fitid,
  {edge=b,node=p.target.node_id,pos=tp,direction=td,grade=tg},{anchor=a,pos=pos,direction=dir,grade=grade})
 local f=s.fits[fitid];f.node=p.source.node_id;f.junction_node=f.node;repartition_two_piece_level(f,fit)
 if not p.execute then respond(request_id,"ok",{fit=fit,game_constructed=false});return end
 assert(not s.mutationPending,"unreconciled_mutation")
 M.build({authorised=true,fit_request=fitid},s,state,request_id,function(rid,status,result)
  result.fit=fit;result.original_compensated_request=p.original_request
  if status=="ok" then
   local ok,value=pcall(function()
    local junctions={p.source.node_id,p.target.node_id};local routes={}
    local function other(e,n) return e.node0==n and e.node1 or e.node0 end
    for _,reverse in ipairs({false,true}) do
     local x,y=reverse and b or a,reverse and a or b;local xn,yn=reverse and p.target.node_id or p.source.node_id,reverse and p.source.node_id or p.target.node_id
     local required={a.id,b.id};for _,id in ipairs(result.ordered_edges) do required[#required+1]=id end
     local route=M.route({source_edge=x.id,source_node=other(x,xn),target_edge=y.id,target_node=other(y,yn),junction_nodes=junctions,mode="TRAIN",required_edges=required,max_length=p.max_route_length,
      geometry_constraints={all_path=true,edge_ids={},region=p.region,radius=p.radius,max_grade=p.vertical.max_grade}})
     assert(route.requested_route_verified,"corrected_crossover_movement_unverified");routes[#routes+1]=route
    end
    result.routes=routes;s.mutationPending=nil;return result
   end)
   if not ok then status="mutation_unverified";result.error=tostring(value):sub(1,400) end
  end
  respond(rid,status,result)
 end)
end
function M.scissors_candidate(p,s,state,request_id,respond)
 local stage="inspect";local names={"L0","L1","R0","R1"};local fittings,locations,originals,splits={},{},{},{}
 local function reply(status,value) value.stage=stage;value.assembly="connected_pointwork";respond(request_id,status,value) end
 local ok,err=pcall(function()
  assert(type(p.execute)=="boolean" and type(p.leads)=="table","scissors_parameters_required")
  assert(p.radius>=60 and p.fit_radius>=70 and p.fit_radius>=p.radius,"scissors_radius_requirements")
  vector(p.center);in_region(p.center,p.region)
  local fits={}
  for _,name in ipairs(names) do
   local q=p.leads[name];assert(q and not q.target,"explicit_four_native_interior_roles_required")
   local a=assert_fresh(q.source.edge_snapshot);local c=interior_location(a,q.location)
   assert(math.abs(c.parameter-q.source.parameter)<=.000001,"stale_interior_location")
   assert(math.abs(c.grade)<=.000001 and math.abs(c.pos[3]-p.center[3])<=.001 and math.abs(q.end_xyz[3]-p.center[3])<=.001,"level_scissors_required")
   locations[name]=c
   local id=request_id.."_"..name
   fits[name]=M.fit({end_xy={q.end_xyz[1],q.end_xyz[2]},end_direction=q.end_direction,radius=p.radius,fit_radius=p.fit_radius,region=p.region},s,id,nil,
     {anchor=a,pos=c.pos,direction=c.outward_direction,grade=c.grade})
   local f=s.fits[id];f.min_radius=p.radius;f.max_grade=0;fittings[name]=f
   if p.repartition==true then repartition_native_fit(f,fits[name]) end
  end
  for i=0,1 do
   local left,right=locations["L"..i],locations["R"..i]
   assert(left.edge_id==right.edge_id and left.canonical_forward and not right.canonical_forward,"ordered_same_native_running_edge_required")
   local a=assert_fresh(left.edge_snapshot);originals[i+1]=a
   splits[i+1]=interior_splits(a,left.parameter,p.region,p.radius,0,right.parameter)
   local through=M.route({source_edge=a.id,source_node=a.node0,target_edge=a.id,target_node=a.node1,single_edge=true,
    mode="TRAIN",required_edges={a.id},max_length=p.max_route_length})
   assert(through.requested_route_verified,"existing_through_route_unverified")
  end
  assert(originals[1].id~=originals[2].id,"distinct_running_rails_required")
  assert(originals[1].template==originals[2].template and originals[1].style==originals[2].style,"incompatible_track_resources")
  if not p.execute then reply("ok",{game_constructed=false,fits=fits,originals=originals,split_preview=splits});return end
  assert(not s.mutationPending,"unreconciled_mutation")
  for _,a in ipairs(originals) do assert_fresh(a) end
  stage="build";local proposal=api.type.SimpleProposal.new();local nodes,segments,expected={}, {}, {};local temporary=-1000
  local role_nodes,through_indices,branch_indices,arm_indices={},{},{},{}
  local function node(pos) temporary=temporary-1;local n=api.type.NodeAndEntity.new();n.entity=temporary;n.comp.position=v(pos);nodes[#nodes+1]=n;return temporary end
  for _,name in ipairs(names) do role_nodes[name]=node(locations[name].pos) end
  local center_node=node(p.center)
  local function add(ctrl,n0,n1,base)
   local e=api.type.SegmentAndEntity.new();e.entity=-#segments-1;e.type=1;e.comp=base:clone()
   e.comp.node0=n0;e.comp.node1=n1;e.comp.position0=v(ctrl.p0);e.comp.position1=v(ctrl.p1);e.comp.tangent0=v(ctrl.t0);e.comp.tangent1=v(ctrl.t1)
   segments[#segments+1]=e;expected[#expected+1]={ctrl=ctrl,node0=n0,node1=n1};return #segments
  end
  for i,a in ipairs(originals) do
   local base=api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE);local chain={a.node0,role_nodes["L"..(i-1)],role_nodes["R"..(i-1)],a.node1}
   through_indices[i]={}
   for j,ctrl in ipairs(splits[i]) do through_indices[i][j]=add(ctrl,chain[j],chain[j+1],base) end
  end
  for _,name in ipairs(names) do
   local f=fittings[name];local base=api.engine.getComponent(f.anchor.id,api.type.ComponentType.BASE_EDGE);local current=role_nodes[name]
   branch_indices[name]={}
   for _,ctrl in ipairs(f.controls) do local finish=node(ctrl.p1);branch_indices[name][#branch_indices[name]+1]=add(ctrl,current,finish,base);current=finish end
   local tip=f.controls[#f.controls].p1;local delta={p.center[1]-tip[1],p.center[2]-tip[2],0};local length=distance(tip,p.center)
   assert(length>0 and length<=300 and angle(delta,f.controls[#f.controls].t1)<=.1,"exact_crossing_arm_required")
   arm_indices[name]={ctrl={p0=tip,p1=p.center,t0=delta,t1=delta,length=length},node0=current,node1=center_node,base=base}
  end
  for _,name in ipairs(names) do local arm=arm_indices[name];arm.index=add(arm.ctrl,arm.node0,arm.node1,arm.base) end
  assert(#segments<=40 and #nodes<=40,"bounded_scissors_proposal_required")
  proposal.streetProposal.nodesToAdd=nodes;proposal.streetProposal.edgesToAdd=segments;proposal.streetProposal.edgesToRemove={originals[1].id,originals[2].id}
  s.mutationPending=request_id;local root=state:get() or {};root.pifLive=s;state:set(root)
  api.cmd.sendCommand(api.cmd.makeWorldBuildProposalCmd(proposal,nil,false,false),function(res,success)
   if success~=true then s.mutationPending=nil;reply("error",{error="native_construction_rejected",native_command_success=false,game_constructed="unknown",retry=false,
    proposal_segments=#segments,proposal_nodes=#nodes,original_edges={originals[1].id,originals[2].id}});return end
   local ids={};for _,e in ipairs(res.proposal.proposal.addedSegments) do ids[#ids+1]=e.entity end
   local checked,value=pcall(function()
    assert(#ids==#expected,"scissors_receipt_incomplete")
    local remaining,matched,mapping={}, {}, {}
    for _,id in ipairs(ids) do remaining[id]=edge(id) end
    local function mapped(id) return id>0 and id or mapping[id] end
    -- Reacquire only receipt identities, anchored in exact original native nodes.
    -- Controls verify correspondence; there is no nearest-world-entity matching.
    for i,x in ipairs(expected) do
     local start=mapped(x.node0);assert(start,"receipt_start_identity_unestablished");local selected=nil
     for id,e in pairs(remaining) do
      local valid=e.node0==start and (not mapped(x.node1) or e.node1==mapped(x.node1))
      for _,k in ipairs({"p0","p1","t0","t1"}) do valid=valid and near(e[k],x.ctrl[k],.001) end
      if valid then assert(not selected,"ambiguous_receipt_correspondence");selected=e end
     end
     assert(selected,"exact_receipt_correspondence_missing");mapping[x.node1]=selected.node1;remaining[selected.id]=nil;matched[i]=selected
     assert(selected.template==originals[1].template and selected.style==originals[1].style,"scissors_resource_mismatch")
    end
    for _ in pairs(remaining) do error("unreconciled_scissors_receipt") end
    for _,a in ipairs(originals) do assert(not api.engine.entityExists(a.id) or api.engine.getComponent(a.id,api.type.ComponentType.BASE_EDGE)==nil,"old_running_edge_still_present") end
    local leads,ports,arms={}, {}, {}
    for _,name in ipairs(names) do
     local i=tonumber(name:sub(2,2))+1;local left=name:sub(1,1)=="L";local incoming=matched[through_indices[i][left and 1 or 3]];local through=matched[through_indices[i][2]]
     local junction=mapped(role_nodes[name]);local incident=incidence(junction)
     local f=fittings[name];f.node=junction;f.junction_node=junction;f.anchor=incoming;f.ids={}
     for _,index in ipairs(branch_indices[name]) do f.ids[#f.ids+1]=matched[index].id end
     assert(#incident==3,"scissors_turnout_degree_mismatch")
     local wanted={[incoming.id]=true,[through.id]=true,[f.ids[1]]=true};for _,id in ipairs(incident) do assert(wanted[id],"scissors_turnout_identity_mismatch") end
     local rb=M.readback(f);local arm=matched[arm_indices[name].index]
     assert(arm.node0==rb.ordered_nodes[#rb.ordered_nodes] and arm.node1==mapped(center_node),"scissors_arm_identity_mismatch")
     leads[name]={readback=rb,junction={node=junction,incoming_edge=incoming.id,through_edge=through.id,branch_edge=f.ids[1],incident_edges=incident,exact_native_identity=true}}
     ports[name]={edge_snapshot=rb.edges[#rb.edges],node_id=arm.node0};arms[#arms+1]=arm.id
    end
    local center=mapped(center_node);local incident=incidence(center);assert(#incident==4,"scissors_crossing_degree_mismatch")
    local wanted={};for _,id in ipairs(arms) do wanted[id]=true end;for _,id in ipairs(incident) do assert(wanted[id],"scissors_crossing_identity_mismatch") end
    s.mutationPending=nil;return {game_constructed=true,leads=leads,ports=ports,arm_edges=arms,center_node=center,returned_edges=ids,
     original_edges={originals[1].id,originals[2].id},effects={added_segments=#ids,added_nodes=#res.proposal.proposal.addedNodes,removed_segments=#res.proposal.proposal.removedSegments},exact_receipt_mapping=true}
   end)
   reply(checked and "ok" or "mutation_unverified",checked and value or {error=tostring(value):sub(1,400),returned_edges=ids,game_constructed=true,retry=false})
  end)
 end)
 if not ok then reply(s.mutationPending==request_id and "mutation_unverified" or "error",{error=tostring(err):sub(1,400),game_constructed=s.mutationPending==request_id and "unknown" or false,retry=false}) end
end
return M
