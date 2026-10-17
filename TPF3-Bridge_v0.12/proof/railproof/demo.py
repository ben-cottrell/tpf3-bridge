"""Run the supplied synthetic cases: python -m railproof.demo --output results."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform as environment
from .engine import FAMILIES, schedule
from .model import Platform, Visit, strict_record
from .geometry import PlainLineShift, sufficient_length
from .rules import platform_cant, platform_radius, gb_platform_interface


def read_fixture(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "fidelity", "scenario_id", "platforms", "visits", "closed_platform_ids",
                "horizon_ms", "max_wait_ms", "evaluation_budget", "description"}
    if not isinstance(obj, dict) or set(obj) != required:
        raise ValueError("Unexpected or missing top-level fixture fields")
    if obj["schema_version"] != "0.2.0" or obj["fidelity"] != "synthetic":
        raise ValueError("This runner accepts only explicitly synthetic v0.2 fixtures")
    if not isinstance(obj["closed_platform_ids"], list) or len(set(obj["closed_platform_ids"])) != len(obj["closed_platform_ids"]):
        raise ValueError("Closure IDs must be a unique list")
    return obj


def run(fixture_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparisons = []
    input_hashes = {}
    for path in sorted(fixture_dir.glob("*.json")):
        obj = read_fixture(path)
        sid = obj["scenario_id"]
        # scenario IDs are data, never arbitrary output paths.
        if not isinstance(sid, str) or not sid or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in sid):
            raise ValueError("Invalid scenario identifier")
        if sid in input_hashes:
            raise ValueError("Duplicate scenario ID")
        input_hashes[sid] = hashlib.sha256(path.read_bytes()).hexdigest()
        platforms = [strict_record(Platform, p) for p in obj["platforms"]]
        visits = [strict_record(Visit, v) for v in obj["visits"]]
        for family in FAMILIES:
            result = schedule(platforms, visits, family, closed=set(obj["closed_platform_ids"]),
                              horizon_ms=obj["horizon_ms"], max_wait_ms=obj["max_wait_ms"],
                              evaluation_budget=obj["evaluation_budget"])
            result["scenario_id"] = sid
            result["input_sha256"] = input_hashes[sid]
            filename = f"{sid}__{family}.json"
            (output_dir / filename).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            comparisons.append({"scenario_id": sid, **{k: result[k] for k in (
                "family", "required_visits", "scheduled_visits", "completed_within_horizon",
                "scheduled_residual_at_horizon", "unscheduled_visits", "total_departure_delay_ms",
                "maximum_departure_delay_ms", "cross_bank_legs", "candidate_evaluations")},
                "trace_file": filename})
    if not input_hashes:
        raise ValueError("No fixtures found")
    geometry = {"scope": "isolated analytic plain-line shift; not a turnout or fitted throat",
                "offset_m": 4.5, "synthetic_minimum_radius_m": 300,
                "sufficient_length_m": sufficient_length(4.5, 300),
                "at_100m": PlainLineShift(100, 4.5).certify_radius(300),
                "at_60m": PlainLineShift(60, 4.5).certify_radius(300)}
    rules = {"cant_example": platform_cant(110, applicable=True, normal_service_stop=True),
             "radius_example": platform_radius(300, applicable=True, new_line=True),
             "existing_track_example": platform_radius(250, applicable=True, new_line=False),
             "national_interface_example": gb_platform_interface(),
             "whole_station_uk_engineering": "unassessed"}
    summary = {"proof_version": "0.2.0", "python": environment.python_version(),
               "platform": environment.platform(), "scenario_count": len(input_hashes),
               "family_count": len(FAMILIES), "comparison_count": len(comparisons),
               "input_sha256": input_hashes, "comparisons": comparisons,
               "geometry_demonstration": geometry, "scoped_rule_demonstration": rules,
               "external_model_or_game_calls_in_runner": 0,
               "measured_plan_credit_savings": None}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    packet = {"packet_kind": "executed_offline_proof", "status": "offline_comparison_ready",
              "scope": "three declared resource families; no station geometry generated",
              "tested_scenarios": list(input_hashes), "family_count": 3,
              "decision": "Use these tests to implement the joint topology/geometry stage; do not commit construction.",
              "engineering_status": "unassessed_whole_station", "game_status": "not_tested",
              "detailed_result": "summary.json", "credit_saving": None}
    (output_dir / "decision_packet.json").write_text(json.dumps(packet, indent=2)+"\n", encoding="utf-8")
    lines = ["# Executed synthetic case results", "", "Generated by `python -m railproof.demo`. No real-station capacity claim.", "",
             "| Scenario | Family | Scheduled | Completed by horizon | Unscheduled | Residual | Total departure delay (s) | Maximum delay (s) | Cross-bank legs |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in comparisons:
        lines.append(f"| {r['scenario_id']} | {r['family']} | {r['scheduled_visits']}/{r['required_visits']} | {r['completed_within_horizon']} | {r['unscheduled_visits']} | {r['scheduled_residual_at_horizon']} | {r['total_departure_delay_ms']/1000:.3f} | {r['maximum_departure_delay_ms']/1000:.3f} | {r['cross_bank_legs']} |")
    lines += ["", "Delay totals cover scheduled visits only. Never compare an incomplete low-delay row as though it served all demand.",
              "Residual counts concern scheduled visits unfinished at the declared horizon; unscheduled work is a separate count.",
              "The resource calendars are verified; spatial queue spillback, full engineering geometry and game behaviour are not assessed.", ""]
    (output_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).resolve().parents[1] / "fixtures")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    try:
        summary = run(args.fixtures, args.output)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"Invalid input or output: {exc}\n")
    print(f"Completed {summary['comparison_count']} synthetic comparisons; output: {args.output}")

if __name__ == "__main__":
    main()
