"""Reproducible connected branch-junction study; no game, desktop or model calls."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
from dataclasses import asdict,replace
import argparse
import json
from railclear.catalogue import read_json,exact
from railcorridor.geometry import digest,integer,number
from railops.uk_profiles import gb_track_centres
from .geometry import JunctionSpec,build,MODES,ROUTES,holding_assessment,ROOT
from .operations import compile_resources,default_performance,validate_performance,leg,schedule,check_result
from .adapter import compile_plan,execute,MockJunctionAdapter,manifest


def validate_fixture(f):
    exact(f,{'schema_version','fidelity','junction','performance','formation_reference_key','repetitions','headway_ms','ramp_trials_m','height_trials_m'})
    if f['schema_version']!='0.10.0' or f['fidelity']!='gb_reference_inspired_synthetic_junction':raise ValueError('fixture version/fidelity')
    exact(f['junction'],set(asdict(JunctionSpec())))
    JunctionSpec(**f['junction']);validate_performance(f['performance'])
    if f['formation_reference_key'] not in ('unit_8car_length_m','unit_12car_length_m'):raise ValueError('unknown published formation field')
    integer(f['repetitions'],'repetitions',minimum=1,maximum=20);integer(f['headway_ms'],'headway',minimum=1000,maximum=3600000)
    for key in ('ramp_trials_m','height_trials_m'):
        if not isinstance(f[key],list) or not 1<=len(f[key])<=10:raise ValueError('finite grid required')
        if len(set(f[key]))!=len(f[key]):raise ValueError('duplicate trial value')
        for v in f[key]:number(v,key,minimum=1,maximum=5000)
    return deepcopy(f)


def search_geometry(f,budget=None):
    f=validate_fixture(f);spec=JunctionSpec(**f['junction'])
    grid=[('flat',spec.ramp_m,0.)]+[(m,r,h) for m in ('flyover','diveunder') for r in f['ramp_trials_m'] for h in f['height_trials_m']]
    budget=len(grid) if budget is None else integer(budget,'candidate budget',maximum=1000)
    records=[]
    for mode,r,h in grid[:budget]:
        try:
            j=build(replace(spec,ramp_m=r,level_change_m=h if h else spec.level_change_m),mode)
            a=j.assessment
            records.append({'mode':mode,'ramp_m':r,'height_m':h,'candidate_hash':a['candidate_hash'],
                            'accepted':a['accepted_for_reference_comparison'],'failures':a['failed_checks'],
                            'crossing':a['crossing'],'grade_upper':max(x['grade_upper'] for x in a['curve_checks'])})
        except ValueError as exc:records.append({'mode':mode,'ramp_m':r,'height_m':h,'accepted':False,'failures':[str(exc)]})
    accepted=[r for r in records if r['accepted']]
    best={mode:min((r for r in accepted if r['mode']==mode),key=lambda r:(r['ramp_m'],r['height_m'])) for mode in MODES if any(r['mode']==mode for r in accepted)}
    return {'fixture_hash':digest(f),'status':'search_exhausted' if len(records)<len(grid) else 'grid_complete_candidates_found' if accepted else 'grid_complete_no_candidate',
            'grid_size':len(grid),'evaluated':len(records),'accepted_count':len(accepted),'candidates':records,'selected_by_mode':best,
            'selection_policy':'shortest accepted full ramps then height, within this fixed topology; not whole-civil optimality',
            'construction_authorised':False}


def scenarios(f,flat,formation):
    c=compile_resources(flat);p=f['performance']
    def req(i,r,t,length=formation):return {'id':i,'route':r,'requested_ms':int(t),'train_length_m':length}
    def base(id,requests,description):
        return {'id':id,'requests':requests,'closures':[],'blocked_intervals':[],'horizon_ms':14400000,'max_wait_ms':14400000,'evaluation_budget':100000,'description':description}
    nominal=base('nominal',[req(f'T{i:02d}_{r}',r,i*f['headway_ms']+off) for i in range(f['repetitions']) for r,off in [('main_east',0),('main_west',90000),('branch_out',120000),('branch_in',0)]],
                 'Four required movement families; authored demand, no real timetable claim')
    def pulse(id,rs,res):
        requests=[]
        for i,r in enumerate(rs):
            t=leg(c,r,formation,p);cl=next(cl for cl in t['claims'] if cl['resource']==res)
            requests.append(req(f'P{i}',r,1200000-cl['front_entry_ms']))
        return base(id,requests,'Common fixed requests aligned using flat reference front-entry times; identical request bytes in every mode')
    crossing=pulse('crossing_pulse',('main_east','branch_in'),'crossing:RETURN_OVER_EAST')
    merge=pulse('merge_pulse',('main_west','branch_in'),'body:M:SYNTH_IMPORT_T40')
    downstream=deepcopy(merge);downstream['id']='downstream_blocked';downstream['blocked_intervals']=[{'resource':'track:west_merge_exit','start_ms':1000000,'end_ms':2400000}]
    closed=deepcopy(nominal);closed['id']='branch_return_closed';closed['closures']=['track:return_connector']
    noexit=deepcopy(nominal);noexit['id']='shared_west_exit_closed';noexit['closures']=['track:west_exit']
    long=deepcopy(nominal);long['id']='synthetic_300m';long['description']='Wholly synthetic length stress case; not a named manufacturer formation'
    for r in long['requests']:r['train_length_m']=300.
    horizon=deepcopy(nominal);horizon['id']='short_horizon';horizon['horizon_ms']=180000
    zero=deepcopy(nominal);zero['id']='zero_budget';zero['evaluation_budget']=0
    limited=deepcopy(merge);limited['id']='zero_entry_wait';limited['max_wait_ms']=0
    return [nominal,crossing,merge,downstream,closed,noexit,long,horizon,zero,limited]


def decide(candidates,results,scenario_id,*,max_total_delay_ms=None):
    """Conservative operating filter, separate from build authority or civil choice."""
    integer(max_total_delay_ms,'delay budget',maximum=100000000) if max_total_delay_ms is not None else None
    rows=[];scenario_hashes=set()
    for mode,j in candidates.items():
        r=results[(mode,scenario_id)]
        if r['candidate_hash']!=j.assessment['candidate_hash'] or r.get('result_hash')!=digest({k:v for k,v in r.items() if k!='result_hash'}):raise ValueError('stale decision result')
        if not r['independent_check']['passed']:raise ValueError('unverified decision result')
        scenario_hashes.add(r['scenario_hash'])
        good=r['scheduled']==r['required'] and r['completed']==r['required'] and (max_total_delay_ms is None or r['total_entry_delay_ms_scheduled_only']<=max_total_delay_ms)
        rows.append({'mode':mode,'candidate_hash':r['candidate_hash'],'required':r['required'],'completed':r['completed'],
                     'unscheduled':r['unscheduled'],'residual':r['residual'],'total_delay_ms':r['total_entry_delay_ms_scheduled_only'],'qualifies':good})
    if len(scenario_hashes)!=1:raise ValueError('incomparable scenarios')
    good=[r for r in rows if r['qualifies']]
    return {'scenario_id':scenario_id,'scenario_hash':next(iter(scenario_hashes)),'delay_budget_ms':max_total_delay_ms,
            'status':'operating_alternatives' if good else 'no_tested_candidate_meets_requested_outcome','alternatives':good,'all_results':rows,
            'no_automatic_choice_between_flyover_and_diveunder':True,
            'remaining_decision':'shared merge/downstream constraint remains; choose civil form only after terrain and asset checks',
            'game_constructed':False,'construction_authorised':False}


def write(out,name,value):
    (out/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def run(f,output):
    f=validate_fixture(f);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    spec=JunctionSpec(**f['junction']);ref=read_json(ROOT/'evidence/vehicle_reference.json')
    formation=ref['published'][f['formation_reference_key']]['value']
    write(out,'input_provenance.json',{'fixture_hash':digest(f),'vehicle_reference_hash':digest(ref),'formation_length_m':formation,
          'formation_field':f['formation_reference_key'],'vehicle_source':ref['source_id'],'component_authenticity':'authored_synthetic',
          'gb_nominal_centres_reference':gb_track_centres(applicable=True,straight=True),'junction_boundary_centres_m':spec.track_centres_m,'new_site_not_old_corridor':True,'new_terrain_assessed':False,'new_uk_numerical_rules_imported':False})
    g=search_geometry(f);write(out,'geometry_search.json',g)
    write(out,'limited_search.json',{'zero_budget':search_geometry(f,0),'two_candidate_budget':search_geometry(f,2)})
    candidates={m:build(spec,m) for m in MODES}
    ss=scenarios(f,candidates['flat'],formation);write(out,'scenarios.json',ss)
    results={};rows=[]
    for mode,j in candidates.items():
        write(out,mode+'__geometry.json',j.assessment)
        comp=compile_resources(j);write(out,mode+'__resources.json',comp)
        write(out,mode+'__lowered_edges.json',{eid:j.polyline(eid) for eid in j.network.edges})
        for s in ss:
            r=schedule(j,s,f['performance'])
            if not r['independent_check']['passed']:raise AssertionError(r['independent_check'])
            results[(mode,s['id'])]=r;write(out,mode+'__'+s['id']+'.json',r)
            rows.append({'mode':mode,'scenario':s['id'],'required':r['required'],'completed':r['completed'],'scheduled':r['scheduled'],
                         'unscheduled':r['unscheduled'],'residual':r['residual'],'delay_s':r['total_entry_delay_ms_scheduled_only']/1000,
                         'witness_counts':r['conflict_witness_counts'],'candidate_hash':r['candidate_hash'],'scenario_hash':r['scenario_hash']})
    holds=[holding_assessment(candidates[mode],length,stop_x=x) for mode in MODES for length in (formation,300.) for x in (2200.,2300.)]
    write(out,'holding_geometry_trials.json',holds)
    plans={m:compile_plan(j) for m,j in candidates.items()}
    for m,p in plans.items():write(out,m+'__mock_plan.json',p)
    p=plans['flyover'];ad=MockJunctionAdapter();first=execute(p,ad);repeat=execute(p,ad)
    cases={'clean':first,'repeat':repeat,'flat':execute(plans['flat'],MockJunctionAdapter()),'diveunder':execute(plans['diveunder'],MockJunctionAdapter()),
           'lost_acknowledgement':execute(p,MockJunctionAdapter(drop_ack_at=1)),
           'wrong_geometry':execute(p,MockJunctionAdapter(snap_at=1)),
           'wrong_turnout_state':execute(p,MockJunctionAdapter(corrupt_state_at=1)),
           'partial_failure':execute(p,MockJunctionAdapter(fail_at=2)),
           'stale_world':execute(p,MockJunctionAdapter(revision=1)),
           'stale_terrain':execute(p,MockJunctionAdapter(terrain_revision='changed')),
           'unprobed_game':execute(p,MockJunctionAdapter(capabilities=manifest('tpf3_unprobed')))}
    write(out,'mock_execution_cases.json',cases);write(out,'tpf3_unprobed_capabilities.json',manifest('tpf3_unprobed'))
    decisions=[decide(candidates,results,'crossing_pulse',max_total_delay_ms=0),decide(candidates,results,'merge_pulse',max_total_delay_ms=0),decide(candidates,results,'downstream_blocked',max_total_delay_ms=0)]
    write(out,'decision_packets.json',decisions)
    summary={'release':'0.10.0','fixture_hash':digest(f),'geometry_candidates':g['evaluated'],'geometry_accepted':g['accepted_count'],
             'connected_modes':list(MODES),'required_routes_per_mode':4,'physical_edges_per_mode':14,'turnouts_per_mode':2,
             'scenarios':len(ss),'operating_comparisons':len(rows),'rows':rows,'mock_case_statuses':{k:v['status'] for k,v in cases.items()},
             'mock_operations_by_mode':{k:len(v['operations']) for k,v in plans.items()},
             'game_calls':0,'model_calls_inside_runner':0,'station_internal_edits':False,
             'complete_local_branch_routes':True,'same_as_v09_terrain_route':False,
             'new_site_terrain_and_dynamic_gauge':'unassessed','construction_authorised':False}
    write(out,'summary.json',summary)
    md=['# Connected passenger-branch results — v0.10','',
        'Synthetic junction and operating assumptions. Delay covers scheduled requests only. No real game or capacity validation.','',
        '| Scenario | Form | Completed / required | Unscheduled | Residual | Total entry delay (s) |',
        '|---|---|---:|---:|---:|---:|']
    for r in rows:md.append(f"| {r['scenario']} | {r['mode']} | {r['completed']} / {r['required']} | {r['unscheduled']} | {r['residual']} | {r['delay_s']:.3f} |")
    md += ['', 'The three forms have identical plan topology. Only the return crossing height changes. Flat and separated modes keep the same physical merge.',
           '', 'The motion surrogate is level-track, starts trains at rest, and keeps one speed per movement. It ignores grade-dependent performance. Identical raised/lowered timings therefore do not establish equal real-world performance.',
           '', 'Requests wait outside this model. Holding trials are geometric screens, not evidence of a train stopping at an in-model signal.']
    (out/'comparison.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return summary


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--fixture',type=Path,default=ROOT/'proof/branch_fixtures/release.json');ap.add_argument('--output',type=Path,default=ROOT/'proof/branch_results')
    args=ap.parse_args();r=run(read_json(args.fixture),args.output)
    print(json.dumps({k:r[k] for k in ('release','geometry_candidates','geometry_accepted','scenarios','operating_comparisons','mock_case_statuses')},indent=2))

if __name__=='__main__':main()
