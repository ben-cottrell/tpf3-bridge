"""Explicit component ports and traversal permissions; coordinates never join rails."""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from railproof.model import identity, positive
from .curves import Bezier, Point, distance, join_check


@dataclass(frozen=True)
class Port:
    id:str
    position:Point
    role:str="internal"


@dataclass(frozen=True)
class TrackEdge:
    id:str
    u:str
    v:str
    curve:Bezier
    component:str|None=None
    controller:str|None=None
    state:str|None=None
    kind:str="plain_line"


@dataclass(frozen=True)
class Turnout:
    id:str
    toe:str
    normal:str
    reverse:str
    controller:str
    normal_state:str="N"
    reverse_state:str="R"


@dataclass(frozen=True)
class Step:
    edge_id:str
    forward:bool


@dataclass(frozen=True)
class RailPath:
    id:str
    start:str
    end:str
    steps:tuple[Step,...]


@dataclass
class Network:
    id:str
    ports:dict[str,Port]=field(default_factory=dict)
    edges:dict[str,TrackEdge]=field(default_factory=dict)
    turnouts:dict[str,Turnout]=field(default_factory=dict)
    metadata:dict=field(default_factory=dict)

    def port(self,id:str,position:Point,role:str="internal")->str:
        identity(id,"port ID")
        if id in self.ports: raise ValueError(f"Duplicate port {id}")
        self.ports[id]=Port(id,position,role)
        return id

    def edge(self,id:str,u:str,v:str,curve:Bezier,**kwargs)->str:
        identity(id,"edge ID")
        if id in self.edges: raise ValueError(f"Duplicate edge {id}")
        self.edges[id]=TrackEdge(id,u,v,curve,**kwargs)
        return id

    def validate(self)->None:
        identity(self.id,"network ID")
        if not self.ports or not self.edges: raise ValueError("Empty network")
        incidence={p:[] for p in self.ports}
        for key,p in self.ports.items():
            if key!=p.id: raise ValueError("Port ID mismatch")
        for key,e in self.edges.items():
            if key!=e.id or e.u==e.v: raise ValueError("Invalid edge identity")
            if e.u not in self.ports or e.v not in self.ports: raise ValueError("Unknown edge port")
            if distance(e.curve.at(0),self.ports[e.u].position)>1e-6 or distance(e.curve.at(1),self.ports[e.v].position)>1e-6:
                raise ValueError(f"Port/geometry mismatch: {e.id}")
            if bool(e.component)!=bool(e.controller) or bool(e.component)!=bool(e.state):
                raise ValueError("Incomplete component control metadata")
            if e.component and e.component not in self.turnouts: raise ValueError("Unknown component")
            incidence[e.u].append(e); incidence[e.v].append(e)
        for key,t in self.turnouts.items():
            if key!=t.id or t.normal_state==t.reverse_state: raise ValueError("Invalid turnout identity/state map")
            edges=[e for e in self.edges.values() if e.component==t.id]
            actual={(e.u,e.v,e.controller,e.state) for e in edges}
            expected={(t.toe,t.normal,t.controller,t.normal_state),(t.toe,t.reverse,t.controller,t.reverse_state)}
            if actual!=expected or len(edges)!=2: raise ValueError("Turnout needs exactly toe-normal and toe-reverse movements")
        for p,edges in incidence.items():
            internal=[e for e in edges if e.component]
            external=[e for e in edges if not e.component]
            if internal and len(external)>1: raise ValueError("Component port has multiple external connections")
            if not internal and len(edges)>2: raise ValueError("Unmodelled plain-line branch")
            if len(internal)>2 or (len(internal)==2 and internal[0].component!=internal[1].component):
                raise ValueError("Improperly shared component port")
            # Every legal across-port continuation is checked, not just selected routes.
            for a in edges:
                for b in edges:
                    if a.id==b.id or (a.component and a.component==b.component): continue
                    ca=a.curve if a.v==p else a.curve.reversed()
                    cb=b.curve if b.u==p else b.curve.reversed()
                    if not join_check(ca,cb)["pass"]: raise ValueError(f"Non-G2 legal join at {p}: {a.id}/{b.id}")

    def enumerate_paths(self,start:str,end:str,*,max_expansions:int=10000,max_paths:int=128)->list[RailPath]:
        if start not in self.ports or end not in self.ports or start==end:
            raise ValueError("Invalid route endpoints")
        for n in (max_expansions,max_paths):
            if isinstance(n,bool) or not isinstance(n,int) or n<1: raise ValueError("Invalid routing budget")
        adjacency={p:[] for p in self.ports}
        for e in self.edges.values():
            adjacency[e.u].append((e,True,e.v)); adjacency[e.v].append((e,False,e.u))
        result=[]; expansions=0
        stack=[(start,(),frozenset({start}),frozenset())]
        while stack:
            node,steps,seen,used_components=stack.pop(); expansions+=1
            if expansions>max_expansions: raise ValueError("route_search_exhausted")
            if node==end:
                if len(result)>=max_paths: raise ValueError("route_path_limit_exhausted")
                result.append(RailPath(f"{start}__{end}__{len(result)}",start,end,steps)); continue
            for e,forward,nxt in sorted(adjacency[node],key=lambda x:x[0].id,reverse=True):
                if nxt in seen: continue
                # N->toe->R is not one legal traversal of a turnout.
                if e.component and e.component in used_components: continue
                used=used_components|({e.component} if e.component else set())
                stack.append((nxt,steps+(Step(e.id,forward),),seen|{nxt},frozenset(used)))
        return result

    def one_path(self,start:str,end:str,id:str)->RailPath:
        p=self.enumerate_paths(start,end)
        if len(p)!=1: raise ValueError(f"Expected one route for {id}; got {len(p)}")
        return RailPath(id,start,end,p[0].steps)

    def oriented_curve(self,step:Step)->Bezier:
        c=self.edges[step.edge_id].curve
        return c if step.forward else c.reversed()

    def canonical(self)->dict:
        return {"schema_version":"0.3.0","fidelity":"synthetic_eased_components",
                "id":self.id,"metadata":self.metadata,
                "ports":[{"id":p.id,"position_m":list(p.position),"role":p.role} for p in sorted(self.ports.values(),key=lambda x:x.id)],
                "edges":[{"id":e.id,"u":e.u,"v":e.v,"controls_m":[list(p) for p in e.curve.controls],
                          "component":e.component,"controller":e.controller,"state":e.state,"kind":e.kind}
                         for e in sorted(self.edges.values(),key=lambda x:x.id)],
                "turnouts":[vars(t) for t in sorted(self.turnouts.values(),key=lambda x:x.id)]}

    def digest(self)->str:
        return hashlib.sha256(json.dumps(self.canonical(),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
