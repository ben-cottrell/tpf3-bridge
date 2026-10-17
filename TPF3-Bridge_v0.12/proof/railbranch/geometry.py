"""Compose explicit main-line/branch routes with a true shared downstream merge.

Plan geometry uses the frozen Bezier/turnout importer. The return connector's
height uses the v0.9 complete quintic-ramp law. No geometric intersection creates
connectivity. The example is a NEW local junction site, not a refit of v0.9 terrain.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import math
from railcorridor.geometry import Alignment, Knot, digest, number, integer
from railgeom.curves import Bezier, line, evaluate
from railgeom.network import Network, Turnout, RailPath
from railclear.catalogue import import_component, place_synthetic, read_json, exact

ROOT = Path(__file__).resolve().parents[2]
MODES = ('flat', 'flyover', 'diveunder')
ROUTES = ('main_east', 'main_west', 'branch_out', 'branch_in')

@dataclass(frozen=True)
class JunctionSpec:
    span_m: float = 6000.0
    track_centres_m: float = 3.4
    rail_height_m: float = 20.0
    west_spread_y_m: float = -120.0
    branch_centre_y_m: float = 240.0
    merge_x_m: float = 1500.0
    diverge_x_m: float = 1800.0
    branch_parallel_x_m: float = 4500.0
    spread_finish_x_m: float = 1200.0
    level_change_m: float = 7.5
    ramp_m: float = 750.0
    plateau_m: float = 100.0
    minimum_radius_m: float = 300.0
    maximum_grade: float = 0.02
    minimum_vertical_radius_m: float = 5000.0
    crossing_half_band_m: float = 4.0
    lower_envelope_m: float = 4.5
    electrification_m: float = 0.8
    deck_depth_m: float = 1.2
    allowance_m: float = 0.3
    site_y_min_m: float = -150.0
    site_y_max_m: float = 270.0
    holding_stop_x_m: float = 2200.0
    def __post_init__(self):
        for k,v in asdict(self).items(): number(v,k,minimum=-100000,maximum=100000)
        for k in ('span_m','track_centres_m','level_change_m','ramp_m','plateau_m','minimum_radius_m',
                  'maximum_grade','minimum_vertical_radius_m','crossing_half_band_m','lower_envelope_m',
                  'deck_depth_m'):
            if getattr(self,k)<=0: raise ValueError('positive '+k+' required')
        if self.electrification_m<0 or self.allowance_m<0: raise ValueError('negative envelope allowance')
        if not 2.8 <= self.track_centres_m <= 10: raise ValueError('track centre study range')
        if not 0<self.spread_finish_x_m<self.merge_x_m<self.diverge_x_m<self.branch_parallel_x_m<self.span_m:
            raise ValueError('junction longitudinal ordering')
        if self.west_spread_y_m >= -self.track_centres_m or self.branch_centre_y_m <= self.track_centres_m:
            raise ValueError('spread-track arrangement must keep the return approach distinct')
        if self.site_y_min_m>=self.site_y_max_m: raise ValueError('empty site')
        if not self.merge_x_m+40 < self.holding_stop_x_m < self.branch_parallel_x_m:
            raise ValueError('holding stop outside return connection')


def hermite(a,b,m0=0.,m1=0.):
    """Quintic x-affine planar connection with given dy/dx and zero end y''."""
    x0,y0=a; x1,y1=b; L=x1-x0
    if L<=0: raise ValueError('x-affine curve requires positive span')
    ys=(y0,y0+m0*L/5,y0+2*m0*L/5,y1-2*m1*L/5,y1-m1*L/5,y1)
    return Bezier(tuple((x0+i*L/5,y) for i,y in enumerate(ys)))


def state(curve,x):
    x0=curve.at(0)[0]; L=curve.at(1)[0]-x0
    number(x,'x',minimum=x0-1e-7,maximum=x0+L+1e-7)
    t=min(1.,max(0.,(x-x0)/L)); p=curve.at(t)
    d=evaluate(curve.derivative_controls(),t); dd=evaluate(curve.derivative_controls(2),t)
    return p[1],d[1]/L,dd[1]/(L*L)


def y_root(curve,y):
    """Unique root only after the Bernstein derivative sign is checked."""
    dc=curve.derivative_controls()
    if min(v[1] for v in dc)<-1e-9 or max(v[1] for v in dc)<=0: raise ValueError('not monotone rising')
    lo,hi=curve.at(0)[0],curve.at(1)[0]
    if not curve.at(0)[1]<y<curve.at(1)[1]: raise ValueError('root not strictly interior')
    for _ in range(65):
        mid=(lo+hi)/2
        if state(curve,mid)[0]<y:lo=mid
        else:hi=mid
    return (lo+hi)/2


def restrict(curve,a,b):
    """Reparameterise exactly with de Casteljau; supports a subinterval in x."""
    x0=curve.at(0)[0]; L=curve.at(1)[0]-x0
    if not x0-1e-7<=a<b<=x0+L+1e-7:raise ValueError('curve restriction interval')
    def split(c,t):
        rows=[list(c.controls)]
        while len(rows[-1])>1:
            rows.append([((1-t)*p[0]+t*q[0],(1-t)*p[1]+t*q[1]) for p,q in zip(rows[-1],rows[-1][1:])])
        return tuple(r[0] for r in rows),tuple(r[-1] for r in reversed(rows))
    # Avoid constructing zero-chord subcurves at exact endpoints.
    c=curve
    if b<x0+L-1e-9:c=Bezier(split(c,(b-x0)/L)[0])
    if a>x0+1e-9:c=Bezier(split(c,(a-x0)/(b-x0))[1])
    return c


def ordered_curves_lower_gap(upper,lower,a,b,depth=8):
    """Bernstein bound on y_upper(x)-y_lower(x), not perpendicular gauging."""
    ca,cb=restrict(upper,a,b),restrict(lower,a,b)
    if len(ca.controls)!=len(cb.controls):raise ValueError('same-degree gap check required')
    def rec(u,v,n):
        dif=[p[1]-q[1] for p,q in zip(u.controls,v.controls)]
        if not n or min(dif)>0:return min(dif)
        ua,ub=u.split();va,vb=v.split()
        return min(rec(ua,va,n-1),rec(ub,vb,n-1))
    return rec(ca,cb,depth)-1e-8


@dataclass
class Junction:
    spec: JunctionSpec
    mode: str
    network: Network
    routes: dict[str,RailPath]
    height: dict[str,Alignment]
    assessment: dict
    def z(self,edge_id,x): return self.height[edge_id].state(x)['z']
    def point(self,edge_id,x):
        e=self.network.edges[edge_id]
        return (x,state(e.curve,x)[0],self.z(edge_id,x))
    def metric(self,edge_id,x):
        e=self.network.edges[edge_id];yp=state(e.curve,x)[1];zp=self.height[edge_id].state(x)['zp']
        return math.sqrt(1+yp*yp+zp*zp)
    def length(self,edge_id,a=None,b=None,steps=64):
        e=self.network.edges[edge_id]
        a=e.curve.at(0)[0] if a is None else a;b=e.curve.at(1)[0] if b is None else b
        if b<a:return self.length(edge_id,b,a,steps)
        if b-a<1e-9:return 0.
        integer(steps,'Simpson steps',minimum=2,maximum=4096)
        if steps%2:raise ValueError('even Simpson count')
        cuts=sorted({a,b,*[k.x for k in self.height[edge_id].knots if a<k.x<b]});total=0.
        for lo,hi in zip(cuts,cuts[1:]):
            h=(hi-lo)/steps
            total+=h/3*(self.metric(edge_id,lo)+self.metric(edge_id,hi)+sum((4 if i%2 else 2)*self.metric(edge_id,lo+i*h) for i in range(1,steps)))
        return total
    def polyline(self,edge_id,tolerance=.02):
        number(tolerance,'tolerance',minimum=1e-5,maximum=.1)
        e=self.network.edges[edge_id];L=e.curve.at(1)[0]-e.curve.at(0)[0]
        yy=max(abs(v[1]) for v in e.curve.derivative_controls(2))/(L*L)
        zz=max(s['position_second_derivative_upper'] for s in self.height[edge_id].bounds()['segments'])
        B=math.hypot(yy,zz);step=min(25.,math.sqrt(8*tolerance/B)) if B else 25.
        cuts=[k.x for k in self.height[edge_id].knots];points=[];error=0.
        for a,b in zip(cuts,cuts[1:]):
            count=max(1,math.ceil((b-a)/step))
            if len(points)+count>20000:raise ValueError('lowering point budget')
            dx=(b-a)/count;error=max(error,B*dx*dx/8)
            points.extend([list(self.point(edge_id,a+i*dx)) for i in range(count)])
        points.append(list(self.point(edge_id,cuts[-1])))
        return {'points':points,'position_error_bound_m':error+1e-9,'datum':'rail_centreline_xyz_m',
                'scope':'centreline interpolation only; not a vehicle envelope'}


def build(spec=JunctionSpec(),mode='flat',component_path=None):
    if not isinstance(spec,JunctionSpec) or mode not in MODES:raise ValueError('junction specification/mode')
    imported=import_component(read_json(component_path or ROOT/'evidence/component_import_synthetic.json'))
    # This placement family depends on the exact admitted reference geometry.
    if imported.report['status']!='accepted_for_synthetic_tests':raise ValueError('component not admitted')
    g=imported.network;roles={p.role:p for p in g.ports.values()}
    # Roles in importer carry names; inspect endpoints via turnout, never guessed lengths.
    t=next(iter(g.turnouts.values()));nc=g.ports[t.normal].position;rc=g.ports[t.reverse].position
    if math.dist(nc,(40.,0.))>1e-8 or math.dist(rc,(40.,1.5))>1e-8:
        raise ValueError('this bounded family requires the unmodified T40 record')
    n=Network('PASSENGER_BRANCH',metadata={'fidelity':'gb_reference_inspired_authored_components','cant_mm':0})
    comp={}
    for prefix,x,y in [('M',spec.merge_x_m,spec.west_spread_y_m),('D',spec.diverge_x_m,spec.track_centres_m/2)]:
        p=place_synthetic(imported,dx=x,dy=y);names={k:prefix+':'+k for k in p.ports};cnames={k:prefix+':'+k for k in p.turnouts}
        for k,v in p.ports.items():n.port(names[k],v.position,v.role)
        for k,v in p.turnouts.items():
            out=Turnout(cnames[k],names[v.toe],names[v.normal],names[v.reverse],prefix+':'+v.controller)
            n.turnouts[out.id]=out;comp[prefix]=out
        for k,e in p.edges.items():
            n.edge(prefix+':'+k,names[e.u],names[e.v],e.curve,component=cnames[e.component],controller=prefix+':'+e.controller,state=e.state,kind=e.kind)
    east=spec.track_centres_m/2;west=-east;M=comp['M'];D=comp['D'];P=spec.branch_parallel_x_m
    for name,pos in {'W_E':(0.,east),'E_E':(spec.span_m,east),'E_W':(spec.span_m,west),'W_W':(0.,west),
                     'B_OUT':(spec.span_m,spec.branch_centre_y_m+east),'B_IN':(spec.span_m,spec.branch_centre_y_m-east),
                     'WEST_SPREAD':(spec.spread_finish_x_m,spec.west_spread_y_m),
                     'WEST_RETURN':(P,spec.west_spread_y_m),
                     'OUT_PARALLEL':(P,spec.branch_centre_y_m+east),'IN_PARALLEL':(P,spec.branch_centre_y_m-east)}.items():n.port(name,pos,'external' if name in ('W_E','E_E','E_W','W_W','B_OUT','B_IN') else 'internal')
    def connect(eid,u,v,c=None):
        n.edge(eid,u,v,c or line(n.ports[u].position,n.ports[v].position))
    connect('east_approach','W_E',D.toe)
    connect('east_continuation',D.normal,'E_E')
    connect('west_exit','W_W','WEST_SPREAD',hermite(n.ports['W_W'].position,n.ports['WEST_SPREAD'].position))
    connect('west_merge_exit','WEST_SPREAD',M.toe)
    connect('west_approach',M.normal,'WEST_RETURN')
    connect('west_restore','WEST_RETURN','E_W',hermite(n.ports['WEST_RETURN'].position,n.ports['E_W'].position))
    connect('out_connector',D.reverse,'OUT_PARALLEL',hermite(n.ports[D.reverse].position,n.ports['OUT_PARALLEL'].position,.075))
    connect('out_boundary','OUT_PARALLEL','B_OUT')
    connect('return_connector',M.reverse,'IN_PARALLEL',hermite(n.ports[M.reverse].position,n.ports['IN_PARALLEL'].position,.075))
    connect('return_boundary','IN_PARALLEL','B_IN')
    n.validate()
    routes={r:n.one_path(a,b,r) for r,a,b in [('main_east','W_E','E_E'),('main_west','E_W','W_W'),('branch_out','W_E','B_OUT'),('branch_in','B_IN','W_W')]}
    c=n.edges['return_connector'].curve;cx=y_root(c,east)
    band=[y_root(c,east-spec.crossing_half_band_m),y_root(c,east+spec.crossing_half_band_m)]
    z=spec.rail_height_m;change=0. if mode=='flat' else spec.level_change_m*(1 if mode=='flyover' else -1)
    start=cx-spec.plateau_m/2-spec.ramp_m;end=cx+spec.plateau_m/2+spec.ramp_m
    heights={};fail=[]
    if not c.at(0)[0]<start<end<c.at(1)[0]:raise ValueError('full ramp does not fit between real component ports')
    for eid,e in n.edges.items():
        a,b=e.curve.at(0)[0],e.curve.at(1)[0]
        ks=[Knot(a,0,z),Knot(b,0,z)]
        if eid=='return_connector':
            ks=[Knot(a,0,z),Knot(start,0,z),Knot(cx-spec.plateau_m/2,0,z+change),Knot(cx+spec.plateau_m/2,0,z+change),Knot(end,0,z),Knot(b,0,z)]
        heights[eid]=Alignment(tuple(ks))
    j=Junction(spec,mode,n,routes,heights,{})
    checks=[]
    for eid,e in n.edges.items():
        xs=[p[0] for p in e.curve.controls];L=xs[-1]-xs[0]
        if any(abs(x-(xs[0]+i*L/(len(xs)-1)))>1e-6 for i,x in enumerate(xs)):raise ValueError('x-affine component required')
        y1=max(abs(v[1]) for v in e.curve.derivative_controls())/L
        y2=max(abs(v[1]) for v in e.curve.derivative_controls(2))/(L*L)
        vb=heights[eid].bounds();vertical=vb['vertical_curvature_upper']+vb['grade_upper']*y1*y2
        curvature=e.curve.curvature_upper(6)
        row={'edge_id':eid,'radius_lower_bound_m':None if curvature==0 else 1/curvature,
             'curvature_upper_per_m':curvature,'grade_upper':vb['grade_upper'],'vertical_curvature_upper_per_m':vertical,
             'radius_pass':curvature<=1/spec.minimum_radius_m,'grade_pass':vb['grade_upper']<=spec.maximum_grade,
             'vertical_pass':vertical<=1/spec.minimum_vertical_radius_m}
        checks.append(row)
        fail.extend(eid+':'+k for k in ('radius_pass','grade_pass','vertical_pass') if not row[k])
    # These monotone reference planes cover the entire declared crossing band.
    zz=[abs(j.z('return_connector',x)-z) for x in [*band,cx,*[k.x for k in heights['return_connector'].knots if band[0]<k.x<band[1]]]]
    separation=min(zz);required=spec.lower_envelope_m+spec.electrification_m+spec.deck_depth_m+spec.allowance_m
    clearance=mode!='flat' and separation>=required
    if mode!='flat' and not clearance:fail.append('crossing_envelope_insufficient')
    gap=ordered_curves_lower_gap(n.edges['out_connector'].curve,c,n.edges['out_connector'].curve.at(0)[0],P)
    if gap<=0:fail.append('unintended_out_return_crossing_or_unresolved_order')
    ports3={}
    for eid,e in n.edges.items():
        for name,x in ((e.u,e.curve.at(0)[0]),(e.v,e.curve.at(1)[0])):
            p=j.point(eid,x)
            if name in ports3 and math.dist(p,ports3[name])>1e-6:raise ValueError('3D connection discontinuity')
            ports3[name]=p
    # The only grade change ends away from points. All legal joins are level and G2 in plan.
    hull=[min(p[0] for e in n.edges.values() for p in e.curve.controls),min(p[1] for e in n.edges.values() for p in e.curve.controls),
          max(p[0] for e in n.edges.values() for p in e.curve.controls),max(p[1] for e in n.edges.values() for p in e.curve.controls)]
    site_ok=hull[0]>=0 and hull[2]<=spec.span_m and hull[1]>=spec.site_y_min_m and hull[3]<=spec.site_y_max_m
    if not site_ok:fail.append('plan_hull_outside_authorised_junction_site')
    route_records={}
    for rid,r in routes.items():
        total=0.;steps=[]
        for st in r.steps:
            length=j.length(st.edge_id);e=n.edges[st.edge_id]
            steps.append({'edge_id':st.edge_id,'forward':st.forward,'s0_m':total,'s1_m':total+length,'length_m':length,
                          'controller':e.controller,'state':e.state,'component':e.component})
            total+=length
        route_records[rid]={'start':r.start,'end':r.end,'steps':steps,'length_m':total}
    base={'version':'0.10.0','mode':mode,'spec':asdict(spec),'network':n.canonical(),
          'height_profiles':{k:v.record() for k,v in heights.items()},'ports_xyz_m':ports3,'routes':route_records,
          'component_record_hash':imported.record_hash,'component_geometry_hash':imported.geometry_hash,
          'component_authenticity':'authored_synthetic_import_unchanged','curve_checks':checks,'failed_checks':fail,
          'plan_control_hull_m':hull,'site_plan_pass':site_ok,'out_return_y_order_lower_bound_m':gap,
          'crossing':{'edge_ids':['east_continuation','return_connector'],'x_m':cx,'y_m':east,'footprint_x_m':band,
                      'minimum_rail_separation_m':separation,'required_project_separation_m':required,
                      'separated_within_project_envelope':clearance and not fail,
                      'turning_connections':[],'mode':'flat_crossing' if mode=='flat' else mode,
                      'origin':'derived curve intersection and full-ramp envelope; hardware not modelled'},
          'complete_required_routes_connected':True,'internal_open_connection_ports':[],
          'accepted_for_reference_comparison':not fail,
          'geometry_scope':'new 6km junction cell with main-line spread; NOT the unchanged v0.9 terrain route',
          'terrain_assessment':'not_performed_for_new_junction_site',
          'unassessed':['full vehicle/structure gauging','real S&C/diamond hardware and speed rating','terrain/civils/drainage',
                        'actual signal sections and release','grade-sensitive traction','game capability and construction'],
          'station_internal_edits':False,'game_constructed':False,'construction_authorised':False}
    base['candidate_hash']=digest(base);j.assessment=base
    return j


def holding_assessment(j,train_length_m,entry_margin_m=10.,exit_margin_m=10.,stop_x=None):
    from railcorridor.junction import holding_check
    c=j.network.edges['return_connector'].curve;stop=j.spec.holding_stop_x_m if stop_x is None else stop_x
    number(stop,'stop',minimum=c.at(0)[0],maximum=c.at(1)[0])
    # Incoming motion travels west (decreasing x). Tail must clear the west edge of the crossing band.
    cross_exit=j.assessment['crossing']['footprint_x_m'][0]
    available=max(0.,j.length('return_connector',stop,cross_exit)) if stop<cross_exit else 0.
    check=holding_check(available,train_length_m,entry_margin_m,exit_margin_m)
    check.update({'stop_x_m':stop,'crossing_exit_x_m':cross_exit,'candidate_hash':j.assessment['candidate_hash'],
        'track_direction':'decreasing_x','crossing_fouled_by_held_formation':available<train_length_m,
        'signal_or_stop_constructed':False,'intermediate_stopping_simulated':False,
        'scope':'geometric storage between derived crossing footprint and selected front-stop position; margins are project choices'})
    return check
