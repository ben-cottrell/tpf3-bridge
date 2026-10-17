"""Two narrowly scoped NTSN clause checks and one unresolved-specific-case guard.

Source S058: Infrastructure NTSN issue 2, May 2025; see evidence/rules.json.
The caller must declare clause applicability. These evaluators do not determine
legal project scope, authorise exceptions, or establish whole-railway compliance.
"""
from __future__ import annotations
from .model import positive


def _scope(applicable: bool | None, override_pending: bool) -> dict | None:
    if applicable is not None and type(applicable) is not bool:
        raise ValueError("Applicability must be true, false or null")
    if type(override_pending) is not bool:
        raise ValueError("Override flag must be boolean")
    if applicable is False:
        return {"status": "not_applicable", "reason": "caller-declared clause applicability"}
    if applicable is None or override_pending:
        return {"status": "unassessed", "reason": "scope or alternative requirement unresolved"}
    return None


def platform_cant(cant_magnitude_mm: float | None, *, applicable: bool | None,
                  normal_service_stop: bool | None, override_pending: bool = False) -> dict:
    early = _scope(applicable, override_pending)
    if early:
        return early
    if normal_service_stop is not None and type(normal_service_stop) is not bool:
        raise ValueError("Stop condition must be true, false or null")
    if normal_service_stop is False:
        return {"status": "not_applicable", "reason": "not a normal-service stopping-platform check"}
    if normal_service_stop is None or cant_magnitude_mm is None:
        return {"status": "unassessed", "reason": "missing stop or cant input"}
    positive(cant_magnitude_mm, "cant magnitude", zero=True)
    return {"status": "pass" if cant_magnitude_mm <= 110 else "fail",
            "rule_id": "NTSN2_PLATFORM_CANT", "source_id": "S058", "clause": "4.2.4.2(2)",
            "value_mm": cant_magnitude_mm, "limit_mm": 110}


def platform_radius(radius_m: float | None, *, applicable: bool | None,
                    new_line: bool | None, straight: bool = False,
                    override_pending: bool = False) -> dict:
    early = _scope(applicable, override_pending)
    if early:
        return early
    if new_line is not None and type(new_line) is not bool:
        raise ValueError("New-line condition must be true, false or null")
    if type(straight) is not bool:
        raise ValueError("Straight flag must be boolean")
    if new_line is False:
        return {"status": "not_applicable", "reason": "this new-line criterion does not establish existing-track acceptability"}
    if new_line is None:
        return {"status": "unassessed", "reason": "line status unknown"}
    if straight:
        if radius_m is not None:
            raise ValueError("Straight geometry must not also carry a finite radius")
        return {"status": "pass", "rule_id": "NTSN2_PLATFORM_RADIUS", "source_id": "S058",
                "clause": "4.2.9.4(1)", "geometry": "straight"}
    if radius_m is None:
        return {"status": "unassessed", "reason": "radius unknown"}
    positive(radius_m, "radius")
    return {"status": "pass" if radius_m >= 300 else "fail", "rule_id": "NTSN2_PLATFORM_RADIUS",
            "source_id": "S058", "clause": "4.2.9.4(1)", "value_m": radius_m, "limit_m": 300}


def gb_platform_interface() -> dict:
    return {"status": "unassessed", "source_id": "S058", "clauses": ["7.7.17.6", "7.7.17.7"],
            "reason": "selected national-rule platform height/offset route not numerically imported"}
