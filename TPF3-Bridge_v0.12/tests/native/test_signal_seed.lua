-- Actual pif_operating direct seed qualification; no native calls or mutations.
-- Pass module source to M.run under an available Lua runtime.
local M={}
function M.run(source)
 local C={EDGE_OBJECT=1,SIGNAL_LIST=2,BASE_EDGE=3}
 local E={RoadType={TRACK=1},EdgeObjectType={SIGNAL=1}}
 local source_edge={roadType=1,objects={{99,1}}}
 local target={roadType=1,objects={},node0=20,node1=21}
 for _,k in ipairs({'position0','position1','tangent0','tangent1'}) do target[k]={x=0,y=0,z=0} end
 local object={edgeObjectConstruction='observed_signal_resource'}
 local list={signals={{edgePr={{entity=10,index=1},false}}}}
 local api={type={ComponentType=C,enum=E},engine={util={getPlayer=function() return 1 end}}}
 local function clone(v)
  if type(v)~='table' then return v end;local out={};for k,x in pairs(v) do out[k]=clone(x) end;return out
 end
 api.type.SegmentAndEntity={new=function() return setmetatable({},{__newindex=function(t,k,v) rawset(t,k,k=='comp' and clone(v) or v) end}) end}
 api.type.SimpleStreetProposal={EdgeObject={new=function() return {} end}}
 api.type.SimpleProposal={new=function() return {streetProposal={}} end}
 api.type.Context={new=function() return {} end}
 local critical=false;local messages={};local evaluated=0
 api.engine.util.proposal={makeProposalData=function(proposal,context)
  assert(context==nil and #proposal.streetProposal.edgesToAdd==1)
  evaluated=evaluated+1;return {errorState={critical=critical,messages=messages}}
 end}
 api.cmd={makeWorldBuildProposalCmd=function() error('preview/rejection must not construct command') end,
          sendCommand=function() error('preview/rejection must not submit command') end}
 api.engine.forEachEntity=function() error('explicit seed must never enumerate the world') end
 api.engine.getRevision=function() return {num={1,2,3}} end
 api.engine.getComponent=function(x,c)
  if x==99 and c==C.EDGE_OBJECT then return object end
  if x==99 and c==C.SIGNAL_LIST then return list end
  if c==C.BASE_EDGE and x==10 then return source_edge end
  if c==C.BASE_EDGE and x==42 then return target end
 end
 local env=setmetatable({api=api,ug_require=function() return {} end},{__index=_G})
 local native=assert(load(source,'explicit signal seed under test','t',env))()
 local seed=native.inspect({signal_seed={seed_id=99}}).signal_seed
 assert(seed.id==99 and seed.edge==10 and seed.resource==object.edgeObjectConstruction)
 assert(seed.processed==1 and seed.coverage=='explicit_qualified_signal' and not seed.truncated)
 local placement={edge_id=42,revision={1,2,3},seed_id=99,parameter=.4,forward=true,one_way=true}
 local prepared=native.inspect({signal_placement=placement}).signal_placement
 assert(prepared.seed.id==99 and prepared.native_proposal_evaluated and prepared.accepted and evaluated==1)
 assert(#target.objects==0)
 critical=true;messages={'Collision'}
 prepared=native.inspect({signal_placement=placement}).signal_placement
 assert(not prepared.accepted and prepared.evaluation.messages[1]=='Collision')
 local state={};local ok,why
 -- Control requires execute=true, then the same proposal rejection before guard.
 placement.execute=true;placement.action='signal_place'
 ok,why=pcall(native.control,placement,state,{},'reject',function() error('unexpected response') end)
 assert(not ok and tostring(why):find('native_signal_proposal_rejected',1,true) and state.mutationPending==nil)
 placement.execute=nil;placement.action=nil;critical=false;messages={}
 placement.seed_revision={9,2,3}
 ok,why=pcall(native.inspect,{signal_placement=placement});assert(not ok and tostring(why):find('stale_operating_identity',1,true))
 placement.seed_revision=nil;source_edge.objects={}
 ok,why=pcall(native.inspect,{signal_placement=placement});assert(not ok and tostring(why):find('signal_seed_attachment_required',1,true))
 source_edge.objects={{99,1}};source_edge.roadType=2
 ok,why=pcall(native.inspect,{signal_seed={seed_id=99}});assert(not ok and tostring(why):find('signal_seed_TRACK_required',1,true))
 source_edge.roadType=1;object=nil
 ok,why=pcall(native.inspect,{signal_seed={seed_id=99}});assert(not ok and tostring(why):find('signal_seed_edge_object_missing',1,true))
 return true
end
return M
