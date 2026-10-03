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
local function slope(t) return t[3]/math.sqrt(t[1]^2+t[2]^2) end
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
function M.connect_selected(p,s,state,request_id,respond)
 assert(type(p.source)=="table" and type(p.target)=="table","selected_candidates_required")
 assert(p.execute==nil or type(p.execute)=="boolean","invalid_selected_execution")
 for _,c in ipairs({p.source,p.target}) do
  local current=assert_fresh(c.edge_snapshot)
  assert(current.id==c.edge_id and (current.node0==c.node_id or current.node1==c.node_id),"selected_endpoint_mismatch")
  local all,owner=incidence(c.node_id)
  assert(#all==1 and all[1]==c.edge_id and not (owner and owner>0),"selected_endpoint_not_free")
 end
 M.extension({execute=p.execute==true,brief={anchor_edge=p.source.edge_id,anchor_node=p.source.node_id,
  target_edge=p.target.edge_id,target_node=p.target.node_id,radius=p.radius,region=p.region,vertical=p.vertical}},s,state,request_id,respond,true)
end
local function node_id(n)
 assert(n and type(n.entity)=="number" and type(n.index)=="number","transport_node_identity_unavailable")
 return {entity=n.entity,index=n.index}
end
local function same_node(a,b) return a.entity==b.entity and a.index==b.index end
local function rail_lane(id,mode)
 local base=edge(id);local n=api.engine.getComponent(id,api.type.ComponentType.TRANSPORT_NETWORK)
 assert(n and n.edges,"transport_network_unavailable")
 local found,index=nil,nil
 for i,row in ipairs(n.edges) do
  if row.transportModes[mode]==true then assert(not found,"ambiguous_rail_transport_lane");found=row;index=i-1 end
 end
 assert(found and #found.conns==2,"rail_transport_lane_unavailable")
 local p0=sample(found.geometry,0);local p1=sample(found.geometry,1)
 -- Geometry verifies the native row's orientation; identities come from conns.
 assert(distance(p0,base.p0)<=.001 and distance(p1,base.p1)<=.001,"transport_orientation_unestablished")
 return base,found,index
end
function M.route(p)
 assert(p.mode=="TRAIN" or p.mode=="ELECTRIC_TRAIN","unsupported_route_mode")
 assert(finite(p.max_length) and p.max_length>0 and p.max_length<=800,"invalid_route_length_bound")
 assert(type(p.required_edges)=="table" and #p.required_edges>=1 and #p.required_edges<=16,"route_required_edge_bound")
 local mode=E.TransportMode[p.mode]
 local a,start,index=rail_lane(p.source_edge,mode);local b,finish,target_index=rail_lane(p.target_edge,mode)
 assert(p.source_edge~=p.target_edge and p.source_node~=p.target_node,"distinct_route_attachments_required")
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
 if not out.requested_route_verified then out.reason=length>p.max_length+.001 and "native_path_exceeds_requested_length" or "native_path_does_not_establish_requested_route" end
 return out
end
function M.fit(p,s,request_id,target)
 vector(p.end_xy);vector(p.end_direction)
 assert(finite(p.radius) and p.radius>0,"invalid_radius")
 assert(type(p.region)=="table","region_required");vector(p.region.min);vector(p.region.max)
 assert(#p.region.min==3 and #p.region.max==3,"region_needs_xyz")
 for i=1,3 do assert(p.region.max[i]>p.region.min[i],"invalid_region") end
 -- Longer connection envelope; discovery remains local and total fit length<=800.
 assert(p.region.max[1]-p.region.min[1]<=1000 and p.region.max[2]-p.region.min[2]<=1000,"fit_region_bound")
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
  local c={p0=p0,p1=p1,t0=d0,t1=d1,length=g.length};controls[i]=c
  total=total+g.length
 end
 assert(total<=800,"fit_length_bound")
 local last=controls[#controls];assert(distance(last.p1,p.end_xy)<=.001 and angle(last.t1,t1)<=.1,"fit_end_mismatch")
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
 local offset,maxsampledgrade,maxzerr=0,0,0
 local vertical_samples={}
 for i,c in ipairs(controls) do
  if profile then
   local p0,d0=sample(profile,offset/total);local p1,d1=sample(profile,(offset+c.length)/total)
   c.p0[3]=i==1 and pos[3] or controls[i-1].p1[3];c.p1[3]=i==#controls and endheight or p1[3]
   c.t0[3]=slope(d0)*math.sqrt(c.t0[1]^2+c.t0[2]^2)
   c.t1[3]=slope(d1)*math.sqrt(c.t1[1]^2+c.t1[2]^2)
  end
  local cg=cubic(c);samples[i]={};vertical_samples[i]={}
  for _,u in ipairs({0,.25,.5,.75,1}) do
   local np,nd=sample(result[i][1],u);local cp,cd=sample(cg,u)
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
 s.fits[request_id]={anchor=a,node=p.anchor_node,target=target,controls=controls,samples=samples,region=p.region,total_length=total,grade=grade,end_grade=endgrade,max_grade=maxgrade,built=false}
 return {fit_request=request_id,pieces=#controls,total_length=total,start_node=p.anchor_node,target_node=target and target.node or nil,start=pos,finish=last.p1,radius=p.radius,grade=grade,end_grade=endgrade,
  vertical_domain=profile and "native_cubic_endpoint_height_grade" or "constant_grade_compatible_endpoints",max_grade=maxgrade,max_sampled_grade=maxsampledgrade,sampled_Z_error=maxzerr,
  vertical_samples=profile and vertical_samples or nil,controls=profile and controls or nil,sampled_XY_error=maxerr,endpoint_heading_error=maxheading,sampled_only=true,game_constructed=false}
end
function M.readback(f)
 assert(f.ids and #f.ids==#f.controls,"construction_receipt_incomplete")
 local remaining={};for _,id in ipairs(f.ids) do assert(not remaining[id],"duplicate_receipt_edge");remaining[id]=true end
 local current=f.node;local ordered,nodes,observations={},{current},{};local maxerr,maxheading,maxzerr,maxgrade,maxjoinz,maxjoingrade=0,0,0,0,0,0
 for i,c in ipairs(f.controls) do
  local found,e=nil,nil
  for id in pairs(remaining) do local x=edge(id);if x.node0==current then assert(not found,"ambiguous_connection");found=id;e=x end end
  assert(found,"actual_connection_missing");remaining[found]=nil
  assert(e.template==f.anchor.template and e.style==f.anchor.style,"resource_mismatch")
  assert(near(e.p0,c.p0,.001) and near(e.p1,c.p1,.001) and near(e.t0,c.t0,.001) and near(e.t1,c.t1,.001),"realised_controls_differ")
  local ng=native_geometry(found)
  local actualbase=cubic({p0=e.p0,p1=e.p1,t0=e.t0,t1=e.t1,length=c.length})
  for _,expected in ipairs(f.samples[i]) do
   local pos,dir=sample(ng,expected.u);maxerr=math.max(maxerr,distance(pos,expected.pos))
   if expected.u==0 or expected.u==1 then maxheading=math.max(maxheading,angle(dir,expected.dir)) end
   -- Movement Z can differ from BaseEdge profile; C13 established that distinction.
   local bp,bd=sample(actualbase,expected.u);local bg=slope(bd)
   maxzerr=math.max(maxzerr,math.abs(bp[3]-expected.base_pos[3]));maxgrade=math.max(maxgrade,math.abs(bg))
   if f.max_grade then assert(math.abs(bg)<=f.max_grade+.000001,"realised_sampled_grade_exceeds_limit") end
   in_region({pos[1],pos[2],bp[3]},f.region)
  end
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
 return {ordered_edges=ordered,ordered_nodes=nodes,edges=observations,attachments=attachments,connected=true,sampled_XY_error=maxerr,sampled_base_Z_error=maxzerr,max_sampled_grade=maxgrade,max_join_height_gap=maxjoinz,max_join_grade_gap=maxjoingrade,endpoint_heading_error=maxheading,sampled_only=true,game_constructed=true,train_traversal="unprobed",native_effect_history_complete=false}
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
function M.extension(p,s,state,request_id,respond,connect_mode)
 local stage,stages,fit="inspect",{},nil
 local function reply(status,value)
  value.stage=stage;value.stages=stages;value.fit=fit
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
  stage="fit";local fit_id=request_id.."_fit";fit=M.fit(b,s,fit_id,target)
  local fitted=s.fits[fit_id] -- retain invocation-local data across command callback
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
function M.test_approach(p,s,state,request_id,respond)
 assert(p.authorised==true and finite(p.length) and p.length>=5 and p.length<=60,"invalid_test_approach")
 assert(not s.mutationPending,"unreconciled_mutation")
 M.fit(p.brief,s,request_id.."_fixture_fit")
 local f=s.fits[request_id.."_fixture_fit"];local c=f.controls[#f.controls];local direction=norm(c.t1)
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
return M
