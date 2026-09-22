"""Offline v0.12 contract checks. No server, socket, model, or game calls.

Requires the development dependency jsonschema. JSON Schema checks shape;
semantic checks cover selected cross-field invariants. Neither grants authority
nor proves native game support. Do not expose this module as a world-edit API.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 1_048_576


def _pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k}")
        result[k] = v
    return result


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = MAX_BYTES) -> Any:
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("invalid input byte limit")
    with Path(path).open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("input byte budget exceeded")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_reject_constant)
        _finite_tree(value)
    except (RecursionError, UnicodeDecodeError) as exc:
        raise ValueError("invalid or excessively nested UTF-8 JSON") from exc
    return value


def _finite_tree(value, depth=0):
    if depth > 64:
        raise ValueError("nesting budget exceeded")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite value")
    if isinstance(value, dict):
        for v in value.values():
            _finite_tree(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            _finite_tree(v, depth + 1)


def digest(value: Any) -> str:
    _finite_tree(value)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def master_schema() -> dict:
    return read_json(ROOT / "contracts/bridge.schema.json")


def validator(definition: str):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError("Install the pinned development requirements in requirements-contracts.txt") from exc
    master = master_schema()
    if definition not in master["$defs"]:
        raise ValueError("unknown definition")
    # References are local-only. This validator does not fetch schemas from a URL.
    schema = {"$schema": master["$schema"], "$defs": master["$defs"],
              "$ref": "#/$defs/" + definition}
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def contains(outer: dict, inner: dict) -> bool:
    return all(a <= b <= c <= d for a, b, c, d in zip(
        outer["min_m"], inner["min_m"], inner["max_m"], outer["max_m"]))


def point_in(box, point):
    return all(a <= x <= b for a, x, b in zip(box["min_m"], point, box["max_m"]))


def semantic_errors(definition: str, data: dict) -> list[str]:
    errors = []
    def walk(value):
        if isinstance(value, dict):
            if set(value) == {"min_m", "max_m"}:
                if any(a >= b for a, b in zip(value["min_m"], value["max_m"])):
                    errors.append("invalid_bounds")
            if "forward_unit" in value:
                if abs(sum(x*x for x in value["forward_unit"]) - 1.0) > 1e-8:
                    errors.append("nonunit_port_direction")
                h = math.hypot(*value["forward_unit"][:2])
                if h <= 1e-12 or abs(value["forward_unit"][2]/h-value["grade"]) > 1e-8:
                    errors.append("port_grade_direction_mismatch")
            for v in value.values():walk(v)
        elif isinstance(value, list):
            for v in value:walk(v)
    walk(data)
    if definition in {"DesignInput", "ReviseInput"}:
        errors.extend(semantic_errors("DesignBrief", data.get("brief", data.get("replacement_brief"))))
    if definition == "DesignBrief":
        ids = [p["port_id"] for p in data["ports"]]
        if len(ids) != len(set(ids)):errors.append("duplicate_port_id")
        if any(not point_in(data["effect_region"], p["position_m"]) for p in data["ports"]):
            errors.append("port_outside_region")
        p = data["preservation"]
        if set(p["protected_asset_refs"]) & set(p["permitted_delete_refs"]):
            errors.append("protected_delete_conflict")
        units = {"route_speed":"m/s", "maximum_gradient":"m/m", "minimum_radius":"m", "design_train_length":"m"}
        if any(data["targets"][n]["unit"] != u for n,u in units.items()):errors.append("target_unit_mismatch")
        if any(data["targets"][n]["value"] <= 0 for n in ("route_speed","minimum_radius","design_train_length")):
            errors.append("nonpositive_target")
    if definition == "Snapshot":
        c = data["capture"]
        if c["end_tick"] < c["start_tick"]:errors.append("capture_time_reversed")
        if c["complete_for_scope"] and (c["missing_refs"] or c["consistency"]=="inconsistent"):
            errors.append("false_snapshot_completeness")
        if c["consistency"] == "single_tick" and c["end_tick"] != c["start_tick"]:
            errors.append("false_single_tick_capture")
        if data["binding"]["environment"] == "game" and not data["coordinate_frame"]["transform_probe_ref"]:
            errors.append("unprobed_coordinate_transform")
    if definition == "CapabilityManifest":
        names=[c["capability_id"] for c in data["capabilities"]]
        if len(names)!=len(set(names)):errors.append("duplicate_capability")
        for c in data["capabilities"]:
            e=c["evidence"]
            if e["level"] != "unknown" and not e["record_refs"]:errors.append("capability_evidence_missing")
            if e["level"] == "demonstrated":
                if not e["probe_ids"]:errors.append("demonstration_probe_missing")
                if c["environment"]=="game" and (not c["game_build"] or not c["adapter_build"] or not e["native_symbols"]):
                    errors.append("demonstration_game_binding_missing")
    if definition == "ConstructionPlan":
        if data["plan_hash"] != digest({k:v for k,v in data.items() if k!="plan_hash"}):errors.append("plan_hash_mismatch")
        seen=set();kinds=set();edge_ids=set();node_positions={};asset_removals=set()
        for op in data["operations"]:
            if op["content_hash"] != digest({k:v for k,v in op.items() if k!="content_hash"}):errors.append("operation_hash_mismatch")
            if op["operation_id"] in seen:errors.append("duplicate_operation_id")
            if any(dep not in seen for dep in op["depends_on"]):errors.append("dependency_order_invalid")
            seen.add(op["operation_id"]);kinds.add(op["kind"])
            if not contains(data["effect_region"],op["expected_effect_region"]):errors.append("operation_region_exceeds_plan")
            p=op["payload"]
            if op["kind"]=="build_track":
                if p["edge_ref"] in edge_ids:errors.append("duplicate_physical_edge")
                edge_ids.add(p["edge_ref"])
                if p["start_node_ref"]==p["end_node_ref"]:errors.append("unsupported_self_loop")
                if any(not point_in(op["expected_effect_region"],x) for x in p["centreline_m"]):errors.append("geometry_outside_effect_region")
                if any(a==b for a,b in zip(p["centreline_m"],p["centreline_m"][1:])):errors.append("zero_length_segment")
                for node,pos in ((p["start_node_ref"],p["centreline_m"][0]),(p["end_node_ref"],p["centreline_m"][-1])):
                    if node in node_positions and node_positions[node]!=pos:errors.append("shared_node_position_mismatch")
                    node_positions[node]=pos
            elif op["kind"]=="build_structure":
                if not contains(op["expected_effect_region"],p["footprint"]) or any(not point_in(p["footprint"],x) for x in p["path_m"]):errors.append("structure_outside_footprint")
            elif op["kind"]=="place_signal":
                if not point_in(op["expected_effect_region"],p["position_m"]):errors.append("signal_outside_effect_region")
            elif op["kind"]=="remove_assets":
                if data["scope"]=="create_only":errors.append("delete_in_create_only_plan")
                if set(p["native_entity_refs"])!=set(p["expected_content_hashes"]):errors.append("delete_hashes_incomplete")
                if asset_removals.intersection(p["native_entity_refs"]):errors.append("duplicate_delete_target")
                asset_removals.update(p["native_entity_refs"])
        rule=read_json(ROOT/"contracts/operation_capabilities.json")
        required=set(rule["always_required"])|{rule["kind_to_capability"][k] for k in kinds}
        if set(data["required_capabilities"])!=required:errors.append("derived_capabilities_mismatch")
        if data["execution_mode"]=="live" and data["binding"]["environment"]!="game":errors.append("live_plan_has_nongame_binding")
        if data["execution_mode"]=="mock" and data["binding"]["environment"]!="mock":errors.append("mock_plan_has_nonmock_binding")
    if definition == "DecisionPacket":
        if data["status"]=="design_ready":
            usable=any(all(not c["mandatory_for_request"] or c["status"] in ("pass","not_applicable") for c in a["checks"]) for a in data["alternatives"])
            if not usable or data["blockers"]:errors.append("design_ready_with_blocker")
    if definition == "RealisationReport":
        if data["status"]=="game_traversal_observed" and (data["binding"]["environment"]!="game" or not data["observation_refs"]):
            errors.append("game_observation_not_established")
        if data["status"]=="mock_verified" and data["binding"]["environment"]!="mock":errors.append("mock_status_environment_mismatch")
        if data["status"] in ("mock_verified","geometry_verified","topology_verified","game_traversal_observed"):
            if any(c["mandatory_for_request"] and c["status"] not in ("pass","not_applicable") for c in data["checks"]):errors.append("verified_result_with_failed_required_check")
    return sorted(set(errors))


def validate(definition: str, data: Any) -> list[str]:
    try:_finite_tree(data)
    except ValueError as exc:return [str(exc)]
    vs=validator(definition)
    errors=["schema:"+"/".join(map(str,e.absolute_path))+":"+e.message for e in vs.iter_errors(data)]
    if errors:return sorted(errors)
    return semantic_errors(definition,data)


def preflight_contract(plan, manifest, authority, trusted_context):
    """Selected offline policy checks. trusted_context is an assumed host input.

    A real implementation MUST resolve/verify approval_ref in trusted storage;
    accepting a caller-supplied Authority object as authenticated is forbidden.
    This function does not implement that storage, identity, clock, or a write.
    """
    errors=[]
    for name,data in (("ConstructionPlan",plan),("CapabilityManifest",manifest),("Authority",authority)):
        errors.extend(validate(name,data))
    if errors:return {"contract_preflight_passed":False,"errors":sorted(set(errors)),"writes_performed":0,"live_execution_authorised":False}
    ctx=trusted_context;b=plan["binding"]
    if authority["authority_ref"] not in ctx["host_resolved_authority_refs"]:errors.append("authority_not_host_resolved")
    if authority["principal_ref"]!=ctx["principal_ref"]:errors.append("authority_principal_mismatch")
    if authority["expires_unix_ms"]<=ctx["now_unix_ms"]:errors.append("authority_expired")
    if authority["plan_hash"]!=plan["plan_hash"]:errors.append("authority_plan_mismatch")
    if any(authority[k]!=b[k] for k in ("save_id","load_epoch")):errors.append("authority_save_epoch_mismatch")
    if not contains(authority["effect_region"],plan["effect_region"]):errors.append("authority_region_too_small")
    if ctx["current_binding"]!=b:errors.append("snapshot_binding_stale")
    if any(op["kind"] not in authority["allowed_kinds"] for op in plan["operations"]):errors.append("operation_kind_not_authorised")
    if len(plan["operations"])>authority["maximum_write_attempts"]:errors.append("authority_write_budget_exceeded")
    for op in plan["operations"]:
        if op["kind"]=="remove_assets":
            targets=set(op["payload"]["native_entity_refs"])
            if not targets.issubset(authority["permitted_delete_refs"]):errors.append("delete_target_not_authorised")
            if targets.intersection(ctx["protected_asset_refs"]):errors.append("protected_asset_deletion")
    caps={c["capability_id"]:c for c in manifest["capabilities"]}
    env="game" if plan["execution_mode"]=="live" else "mock"
    for name in plan["required_capabilities"]:
        c=caps.get(name)
        if not c or c["environment"]!=env or c["evidence"]["level"]!="demonstrated":errors.append("capability_not_demonstrated:"+name)
        elif env=="game" and (c["game_build"]!=b["game_build"] or c["adapter_build"]!=b["adapter_build"]):errors.append("capability_build_stale:"+name)
    return {"contract_preflight_passed":not errors,"errors":sorted(set(errors)),"writes_performed":0,"live_execution_authorised":False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path",type=Path,nargs="?")
    parser.add_argument("--definition")
    args=parser.parse_args()
    if bool(args.path)!=bool(args.definition):parser.error("path and --definition must be supplied together")
    records=[]
    if args.path:
        records=[{"path":str(args.path),"definition":args.definition,"errors":validate(args.definition,read_json(args.path))}]
    else:
        for item in read_json(ROOT/"contracts/example_index.json")["examples"]:
            records.append({"path":item["path"],"definition":item["definition"],"errors":validate(item["definition"],read_json(ROOT/"contracts"/item["path"]))})
    out={"kind":"offline_contract_example_validation","successful":all(not r["errors"] for r in records),"records":records,"game_calls":0,"writes_performed":0}
    print(json.dumps(out,indent=2));return 0 if out["successful"] else 1

if __name__=="__main__":raise SystemExit(main())
