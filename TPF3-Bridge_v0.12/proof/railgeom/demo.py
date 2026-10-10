"""Run v0.3 geometry-derived examples: python -m railgeom.demo --output geometry_results."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import re
from railproof.model import Visit, strict_record
from .patterns import CrossoverSpec, FanSpec, GeometryProfile, build_crossover, build_fan
from .compiler import compile_assembly
from .operations import TimingProfile, schedule_routes, schedule_bank
from .search import fit_crossover


def read_fixture(path:Path)->dict:
    o=json.loads(path.read_text(encoding="utf-8"))
    expected={"schema_version","fidelity","profile","crossover","fan","timing","visits","scenarios","description"}
    if not isinstance(o,dict) or set(o)!=expected: raise ValueError("Unexpected geometry fixture fields")
    if o["schema_version"]!="0.3.0" or o["fidelity"]!="synthetic": raise ValueError("Only synthetic v0.3 fixtures supported")
    strict_record(GeometryProfile,o["profile"]);strict_record(CrossoverSpec,o["crossover"])
    strict_record(FanSpec,o["fan"]);strict_record(TimingProfile,o["timing"])
    if not isinstance(o["visits"],list) or not o["visits"]: raise ValueError("Missing visit list")
    for v in o["visits"]: strict_record(Visit,v)
    seen=set()
    if not isinstance(o["scenarios"],list) or not o["scenarios"]: raise ValueError("Missing scenarios")
    for s in o["scenarios"]:
        if not isinstance(s,dict) or set(s)!={"id","closed_platform_ids","train_length_override_m","horizon_ms","evaluation_budget"}:
            raise ValueError("Unexpected scenario fields")
        if not isinstance(s["id"],str) or not re.fullmatch(r"[a-z0-9_-]+",s["id"]) or s["id"] in seen:
            raise ValueError("Invalid/duplicate scenario ID")
        seen.add(s["id"])
        if not isinstance(s["closed_platform_ids"],list) or len(set(s["closed_platform_ids"]))!=len(s["closed_platform_ids"]):
            raise ValueError("Invalid closure IDs")
    return o


def write(path:Path,obj)->None:
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def run(fixture:Path,output:Path)->dict:
    o=read_fixture(fixture);output.mkdir(parents=True,exist_ok=True)
    p=strict_record(GeometryProfile,o["profile"]); t=strict_record(TimingProfile,o["timing"])
    cs=strict_record(CrossoverSpec,o["crossover"]);fs=strict_record(FanSpec,o["fan"])
    crossover=compile_assembly(build_crossover(cs,p));fan=compile_assembly(build_fan(fs,p))
    write(output/"crossover_compiled.json",crossover.export());write(output/"fan_compiled.json",fan.export())
    requests=[{"id":id,"route":route,"requested_ms":0,"train_length_m":160.0}
              for id,route in (("lower","lower_through"),("upper","upper_through"),("crossing","cross_forward"))]
    crossing=schedule_routes(crossover,requests,t);write(output/"crossover_route_test.json",crossing)
    visits=[strict_record(Visit,v) for v in o["visits"]];rows=[]
    for s in o["scenarios"]:
        current=visits if s["train_length_override_m"] is None else [replace(v,length_m=s["train_length_override_m"]) for v in visits]
        r=schedule_bank(fan,current,closed=set(s["closed_platform_ids"]),horizon_ms=s["horizon_ms"],
                        evaluation_budget=s["evaluation_budget"],timing=t)
        r["scenario_id"]=s["id"];write(output/f"bank__{s['id']}.json",r)
        rows.append({"scenario_id":s["id"],**{k:r[k] for k in ("required_visits","scheduled_visits","unscheduled_visits",
            "completed_within_horizon","scheduled_residual_at_horizon","total_departure_delay_ms","candidate_evaluations")}})
    fits={"within_100m":fit_crossover(4.5,100,p),"within_70m":fit_crossover(4.5,70,p),
          "one_evaluation":fit_crossover(4.5,100,p,evaluation_budget=1)}
    write(output/"crossover_search.json",fits)
    sensitivity=[]
    # This is a geometry sensitivity exercise, not a same-site station ranking.
    for id,spec in (("compact",replace(fs,toe_step_m=75,platform_start_x_m=500)),
                    ("baseline",fs),("extended",replace(fs,toe_step_m=190,platform_start_x_m=800,site_end_x_m=1100))):
        c=compile_assembly(build_fan(spec,p))
        sensitivity.append({"id":id,"spec":asdict(spec),"compile_hash":c.compile_hash,
             "resource_count":len(c.provenance["resources"]),"proximity_pair_count":len(c.provenance["proximity_contacts"]),
             "route_lengths_upper_m":{id:r.length_upper_m for id,r in c.routes.items() if id.endswith(":in")},
             "interpretation":"different geometry/boundaries; not an equivalent-brief optimisation comparison"})
    write(output/"fan_geometry_sensitivity.json",sensitivity)
    summary={"release_version":"0.3.0","python":platform.python_version(),
        "input_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),"fixture":"geometry_fixtures/release.json",
        "crossover":{"span_m":crossover.provenance["network"]["metadata"]["span_m"],
          "routes":len(crossover.routes),"track_edges":len(crossover.edge_requirements),
          "resources":len(crossover.provenance["resources"]),"compile_hash":crossover.compile_hash,
          "cross_route_length_interval_m":[crossover.routes["cross_forward"].length_lower_m,crossover.routes["cross_forward"].length_upper_m]},
        "fan":{"physical_platform_roads":len(fan.platforms),"approach_tracks":1,"routes":len(fan.routes),
          "track_edges":len(fan.edge_requirements),"resources":len(fan.provenance["resources"]),"compile_hash":fan.compile_hash,
          "last_fan_curve_end_x_m":fan.provenance["network"]["metadata"]["last_fan_curve_end_x_m"]},
        "bank_scenarios":rows,"search_statuses":{k:v["status"] for k,v in fits.items()},
        "external_model_or_game_calls_in_runner":0,"measured_plan_credit_savings":None,
        "limitations":["synthetic catalogue, not UK-approved specialwork","one-approach bank, not complete four-approach station",
            "whole-leg lock/release surrogate, not sectional interlocking","proxy corridor width, not kinematic vehicle gauging",
            "no game construction or observation","no global optimiser or passenger/spatial queue model"]}
    write(output/"summary.json",summary)
    packet={"packet_kind":"executed_geometry_proof","status":"synthetic_components_ready_for_next_stage",
        "crossover_parallel_through_starts_ms":[r["start_ms"] for r in crossing["requests"][:2]],
        "crossover_conflicting_move_start_ms":crossing["requests"][2]["start_ms"],
        "best_100m_grid_candidate":fits["within_100m"]["best_in_evaluated_set"],
        "fan_required_movements_compiled":len(fan.routes),"geometry_source":"authored_synthetic_components",
        "engineering_status":"scoped_proxy_checks_only","game_status":"not_tested","construction_approval":False,
        "detailed_refs":["summary.json","crossover_compiled.json","fan_compiled.json","crossover_search.json"],
        "next_gate":"platform-aware sectional resource occupation and train-motion model; retain whole-leg baseline"}
    write(output/"decision_packet.json",packet)
    lines=["# Executed v0.3 geometry-derived examples","",
        "Synthetic components and service data; whole-leg scheduling; no real-station capacity or game-performance claim.","",
        "## Crossover route reservations","","| Route | Requested (s) | Start (s) | Clear (s) | Wait (s) |","|---|---:|---:|---:|---:|"]
    for r in crossing["requests"]:lines.append(f"| {r['route']} | {r['requested_ms']/1000:.3f} | {r['start_ms']/1000:.3f} | {r['clear_ms']/1000:.3f} | {r['wait_ms']/1000:.3f} |")
    lines += ["","## Four-platform bank scenarios","","| Scenario | Scheduled / required | Completed | Unscheduled | Residual | Departure delay, scheduled only (s) |","|---|---:|---:|---:|---:|---:|"]
    for r in rows:lines.append(f"| {r['scenario_id']} | {r['scheduled_visits']}/{r['required_visits']} | {r['completed_within_horizon']} | {r['unscheduled_visits']} | {r['scheduled_residual_at_horizon']} | {r['total_departure_delay_ms']/1000:.3f} |")
    lines += ["","## Bounded crossover fitting","","| Request | Evaluations | Fitted candidates | Status |","|---|---:|---:|---|"]
    for k,v in fits.items():lines.append(f"| {k} | {v['evaluations']} | {v['feasible_candidates']} | {v['status']} |")
    lines += ["","A low-delay row with missing required visits is not a successful design. No candidate here authorises game construction.",
       "The bank has ONE bidirectional approach; do not present it as the four-approach v0.2 station.",""]
    (output/"comparison.md").write_text("\n".join(lines),encoding="utf-8")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture",type=Path,default=Path(__file__).resolve().parents[1]/"geometry_fixtures"/"release.json")
    parser.add_argument("--output",type=Path,default=Path("geometry_results"))
    args=parser.parse_args()
    try: result=run(args.fixture,args.output)
    except (ValueError,TypeError,OSError) as exc: parser.exit(2,f"Invalid input or output: {exc}\n")
    print(f"Compiled crossover and {result['fan']['physical_platform_roads']}-platform bank; ran {len(result['bank_scenarios'])} bank scenarios. Output: {args.output}")


if __name__=="__main__": main()
