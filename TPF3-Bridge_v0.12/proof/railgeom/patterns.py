"""Authored synthetic fitting families; not replicas of commercial UK S&C."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from railproof.model import positive, strict_record
from .curves import Bezier, line, eased_branch, finite, distance
from .network import Network, Turnout, RailPath


@dataclass(frozen=True)
class GeometryProfile:
    minimum_radius_m:float=300.0
    envelope_half_width_m:float=1.75
    envelope_gap_m:float=0.5
    flatness_m:float=0.01
    length_gap_m:float=0.0001
    fidelity:str="synthetic"
    def __post_init__(self):
        for name in ("minimum_radius_m","envelope_half_width_m","flatness_m","length_gap_m"):
            positive(getattr(self,name),name)
        positive(self.envelope_gap_m,"envelope gap",zero=True)
        if self.fidelity!="synthetic": raise ValueError("No approved UK component profile exists in this proof")
    @property
    def separation_m(self)->float: return 2*self.envelope_half_width_m+self.envelope_gap_m


@dataclass(frozen=True)
class CrossoverSpec:
    spacing_m:float=4.5
    turnout_span_m:float=40.0
    branch_slope:float=0.075
    maximum_span_m:float=120.0
    linked_controller:bool=True
    def __post_init__(self):
        for name in ("spacing_m","turnout_span_m","branch_slope","maximum_span_m"):
            positive(getattr(self,name),name)
        if self.branch_slope>0.25: raise ValueError("Synthetic branch slope outside supported 0..0.25 range")
        if not isinstance(self.linked_controller,bool): raise ValueError("linked_controller must be bool")


@dataclass(frozen=True)
class FanSpec:
    platform_count:int=4
    spacing_m:float=12.0
    turnout_span_m:float=50.0
    branch_slope:float=0.1
    first_toe_x_m:float=50.0
    toe_step_m:float=150.0
    platform_start_x_m:float=650.0
    boarding_length_m:float=260.0
    margin_m:float=5.0
    site_end_x_m:float=1000.0
    def __post_init__(self):
        if isinstance(self.platform_count,bool) or not isinstance(self.platform_count,int) or not 2<=self.platform_count<=8:
            raise ValueError("Prototype fan supports 2..8 physical platform roads")
        for name in ("spacing_m","turnout_span_m","branch_slope","first_toe_x_m","toe_step_m","platform_start_x_m","boarding_length_m","site_end_x_m"):
            positive(getattr(self,name),name)
        positive(self.margin_m,"margin",zero=True)
        if self.branch_slope>0.25: raise ValueError("Branch slope outside supported range")
        if self.toe_step_m<=self.turnout_span_m: raise ValueError("Turnout spans overlap on spine")
        if self.margin_m*2>=self.boarding_length_m: raise ValueError("Margins consume platform")
        if self.platform_start_x_m+self.boarding_length_m>self.site_end_x_m:
            raise ValueError("Platform exceeds authorised site boundary")


@dataclass
class Assembly:
    network:Network
    routes:dict[str,RailPath]
    platforms:dict[str,dict]
    profile:GeometryProfile


def add_turnout(n:Network,id:str,origin:tuple[float,float],length:float,slope:float,
                angle:float=0,controller:str|None=None)->Turnout:
    c=controller or id
    normal=line((0.,0.),(length,0.)).transformed(*origin,angle)
    reverse=eased_branch(length,slope).transformed(*origin,angle)
    t=Turnout(id,f"{id}:T",f"{id}:N",f"{id}:R",c)
    if id in n.turnouts: raise ValueError("Duplicate turnout")
    n.turnouts[id]=t
    n.port(t.toe,normal.at(0)); n.port(t.normal,normal.at(1)); n.port(t.reverse,reverse.at(1))
    n.edge(f"{id}:normal",t.toe,t.normal,normal,component=id,controller=c,state="N",kind="synthetic_turnout_through")
    n.edge(f"{id}:reverse",t.toe,t.reverse,reverse,component=id,controller=c,state="R",kind="synthetic_turnout_diverging")
    return t


def connector_dimensions(offset:float,L:float,m:float)->tuple[float,float]:
    """Two eased bends plus a positive tangent: X=L+offset/m."""
    vertical_tangent=offset-m*L
    if vertical_tangent<=1e-6: raise ValueError("No positive connecting tangent for selected synthetic component")
    return L+offset/m,vertical_tangent/math.sin(math.atan(m))


def build_crossover(spec:CrossoverSpec=CrossoverSpec(),profile:GeometryProfile=GeometryProfile())->Assembly:
    if spec.spacing_m<profile.separation_m: raise ValueError("Parallel tracks fail declared independent-envelope separation")
    X,K=connector_dimensions(spec.spacing_m,spec.turnout_span_m,spec.branch_slope)
    if X>spec.maximum_span_m+1e-8: raise ValueError("crossover_exceeds_authorised_span")
    n=Network("synthetic_crossover",metadata={"pattern":"single_crossover","spec":asdict(spec),
               "profile":asdict(profile),"span_m":X,"connector_length_m":K,
               "catalogue":"SYNTH_EASED_1","vertical_profile":"level","cant_mm":0})
    common="CROSSOVER_CONTROL" if spec.linked_controller else None
    a=add_turnout(n,"T1",(0.,0.),spec.turnout_span_m,spec.branch_slope,controller=common)
    b=add_turnout(n,"T2",(X,spec.spacing_m),spec.turnout_span_m,spec.branch_slope,math.pi,common)
    low_e=n.port("LOW_E",(X,0.),"external")
    high_w=n.port("HIGH_W",(0.,spec.spacing_m),"external")
    n.edge("lower_continuation",a.normal,low_e,line(n.ports[a.normal].position,n.ports[low_e].position))
    n.edge("upper_continuation",high_w,b.normal,line(n.ports[high_w].position,n.ports[b.normal].position))
    n.edge("diagonal",a.reverse,b.reverse,line(n.ports[a.reverse].position,n.ports[b.reverse].position))
    n.validate()
    routes={}
    for id,u,v in (("lower_through",a.toe,low_e),("upper_through",high_w,b.toe),
                   ("cross_forward",a.toe,b.toe),("cross_reverse",b.toe,a.toe)):
        routes[id]=n.one_path(u,v,id)
    return Assembly(n,routes,{},profile)


def build_fan(spec:FanSpec=FanSpec(),profile:GeometryProfile=GeometryProfile())->Assembly:
    if spec.spacing_m<profile.separation_m: raise ValueError("Platform roads fail declared independent-envelope separation")
    n=Network("synthetic_platform_bank",metadata={"pattern":"single_spine_platform_fan","spec":asdict(spec),
              "profile":asdict(profile),"catalogue":"SYNTH_EASED_1","vertical_profile":"level","cant_mm":0,
              "scope":"one bidirectional approach, not the v0.2 four-track station brief"})
    entry=n.port("APPROACH",(0.,0.),"external")
    previous=entry; branch_ends={}; finish_x=[]
    for i in range(spec.platform_count-1):
        # Farthest platform branches first; shorter offsets are taken later.
        y=(spec.platform_count-1-i)*spec.spacing_m
        toe_x=spec.first_toe_x_m+i*spec.toe_step_m
        t=add_turnout(n,f"F{i+1}",(toe_x,0.),spec.turnout_span_m,spec.branch_slope)
        n.edge(f"spine_{i}",previous,t.toe,line(n.ports[previous].position,n.ports[t.toe].position))
        previous=t.normal
        X,K=connector_dimensions(y,spec.turnout_span_m,spec.branch_slope)
        end_x=toe_x+X
        if end_x>=spec.platform_start_x_m-1e-6: raise ValueError("fan_does_not_clear_platform_start")
        # Reverse another eased branch at the parallel-end marker. It is plain
        # line here, NOT an invented extra turnout or a second connection.
        finish=eased_branch(spec.turnout_span_m,spec.branch_slope).transformed(end_x,y,math.pi).reversed()
        q=n.port(f"return_{i}:start",finish.at(0)); r=n.port(f"return_{i}:end",finish.at(1))
        n.edge(f"diagonal_{i}",t.reverse,q,line(n.ports[t.reverse].position,n.ports[q].position))
        n.edge(f"return_{i}",q,r,finish,kind="plain_line_eased_return")
        branch_ends[spec.platform_count-i]=r; finish_x.append(end_x)
    branch_ends[1]=previous
    routes={}; platforms={}
    for j in range(1,spec.platform_count+1):
        y=(j-1)*spec.spacing_m
        marker_x=spec.platform_start_x_m+spec.margin_m
        marker=n.port(f"BERTH_P{j}",(marker_x,y),"berth_rear_stop_marker")
        end=n.port(f"BUFFER_P{j}",(spec.platform_start_x_m+spec.boarding_length_m,y),"terminal_limit")
        n.edge(f"lead_P{j}",branch_ends[j],marker,line(n.ports[branch_ends[j]].position,n.ports[marker].position))
        storage=n.edge(f"storage_P{j}",marker,end,line(n.ports[marker].position,n.ports[end].position),kind="platform_storage")
        platforms[f"P{j}"]={"id":f"P{j}","label":str(j),"bank":"A","usable_length_m":spec.boarding_length_m,
            "margin_each_end_m":spec.margin_m,"marker_port":marker,"storage_edge":storage,
            "boarding_interval_x_m":[spec.platform_start_x_m,spec.platform_start_x_m+spec.boarding_length_m],
            "stop_mode":"rear_at_entry_marker; front=marker+train_length; synthetic"}
        routes[f"P{j}:in"]=n.one_path(entry,marker,f"P{j}:in")
        routes[f"P{j}:out"]=n.one_path(marker,entry,f"P{j}:out")
    n.metadata["last_fan_curve_end_x_m"]=max(finish_x)
    n.validate()
    return Assembly(n,routes,platforms,profile)
