"""Deterministic greedy complete-visit scheduler over declared resource templates.

Not a microscopic train simulator, global optimiser, interlocking replica, or
geometry-derived network. Earlier assignments remain fixed. All limitations are
also present in the machine-readable report.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import ceil
from .model import Claim, Platform, Visit, conflict, positive, time_value, validate_stock

FAMILIES = ("common", "banked", "linked")


class BudgetExhausted(Exception):
    pass


@dataclass
class Budget:
    remaining: int
    evaluations: int = 0

    def __post_init__(self):
        time_value(self.remaining, "evaluation budget")

    def use(self):
        if self.remaining <= 0:
            raise BudgetExhausted
        self.remaining -= 1
        self.evaluations += 1


class Calendar:
    def __init__(self):
        self.claims: dict[str, list[Claim]] = {}

    def conflicts(self, claims: list[Claim]) -> list[Claim]:
        hits = set()
        for c in claims:
            for other in self.claims.get(c.resource, []):
                if conflict(c, other):
                    hits.add(other)
        return sorted(hits, key=lambda c: (c.end_ms, c.resource, c.owner))

    def reserve(self, claims: list[Claim]) -> None:
        # All-or-nothing *in-memory model* validation, not a game transaction.
        if self.conflicts(claims):
            raise ValueError("Reservation conflicts with an existing claim")
        for i, a in enumerate(claims):
            if any(conflict(a, b) for b in claims[i+1:]):
                raise ValueError("Reservation contains internally incompatible claims")
        for c in claims:
            self.claims.setdefault(c.resource, []).append(c)
            self.claims[c.resource].sort(key=lambda x: (x.start_ms, x.end_ms, x.owner))

    def earliest(self, resources: tuple[str, ...], start_ms: int, duration_ms: int,
                 owner: str, budget: Budget) -> tuple[int, list[dict]]:
        witnesses = []
        while True:
            budget.use()
            proposed = [Claim(r, start_ms, start_ms + duration_ms, owner) for r in resources]
            hits = self.conflicts(proposed)
            if not hits:
                return start_ms, witnesses
            witnesses.extend(asdict(c) for c in hits)
            start_ms = max(c.end_ms for c in hits)

    def verify(self) -> None:
        for claims in self.claims.values():
            for i, a in enumerate(claims):
                if any(conflict(a, b) for b in claims[i+1:]):
                    raise AssertionError(f"Incompatible resource occupation: {a.resource}")


def clearance_ms(distance_m: float, length_m: float, speed_mps: float,
                 setup_ms: int = 5000, release_ms: int = 3000) -> int:
    """Constant-speed tail-clear surrogate. Includes full train length.

    Rounded upward to integer milliseconds. It does not model braking to a stop.
    """
    for value, name in ((distance_m, "distance"), (length_m, "length"), (speed_mps, "speed")):
        positive(value, name)
    time_value(setup_ms, "setup")
    time_value(release_ms, "release")
    return setup_ms + ceil(1000 * (distance_m + length_m) / speed_mps) + release_ms


def route_resources(family: str, group: str, bank: str, direction: str) -> tuple[str, ...] | None:
    if family not in FAMILIES or group not in {"A", "B"} or bank not in {"A", "B"} or direction not in {"in", "out"}:
        raise ValueError("Invalid route template input")
    portal = f"portal:{group}:{direction}"
    if family == "common":
        return (portal, "throat:shared")
    if family == "banked" and bank != group:
        return None
    if bank == group:
        return (portal, f"throat:{bank}")
    return (portal, "throat:A", "throat:B", "cross_access")


def route_duration(v: Visit, platform: Platform, group: str) -> int:
    # All lengths/speeds here are explicit synthetic fixture parameters.
    return clearance_ms(160.0 if platform.bank == group else 280.0, v.length_m, 8.0)


@dataclass
class Assignment:
    visit_id: str
    stock_id: str
    platform_id: str
    entry_ms: int
    berthed_ms: int
    departure_ms: int
    exit_clear_ms: int
    departure_delay_ms: int
    cross_bank_legs: int
    outgoing_kind: str
    claims: list[Claim]
    witnesses: list[dict]


def fit_visit(v: Visit, p: Platform, family: str, calendar: Calendar, budget: Budget,
              earliest_entry_ms: int, max_wait_ms: int) -> Assignment | None:
    if not p.fits(v.length_m):
        return None
    rin = route_resources(family, v.inbound_group, p.bank, "in")
    rout = route_resources(family, v.outbound_group, p.bank, "out")
    if rin is None or rout is None:
        return None  # Reject arrival-only opportunities before scheduling.
    din = route_duration(v, p, v.inbound_group)
    dout = route_duration(v, p, v.outbound_group)
    t = earliest_entry_ms
    witnesses: list[dict] = []
    while t <= v.requested_entry_ms + max_wait_ms:
        budget.use()
        t, w = calendar.earliest(rin, t, din, v.id, budget)
        witnesses.extend(w)
        if t > v.requested_entry_ms + max_wait_ms:
            return None
        arrived = t + din
        departure = max(v.planned_departure_ms, arrived + v.readiness_ms)
        departure, w = calendar.earliest(rout, departure, dout, v.id, budget)
        witnesses.extend(w)
        berth = Claim(f"berth:{p.id}", t, departure + dout, v.id)
        hits = calendar.conflicts([berth])
        if hits:
            witnesses.extend(asdict(c) for c in hits)
            t = max(c.end_ms for c in hits)
            continue
        claims = [Claim(r, t, arrived, v.id) for r in rin]
        claims += [berth]
        claims += [Claim(r, departure, departure+dout, v.id) for r in rout]
        return Assignment(v.id, v.stock_id, p.id, t, arrived, departure, departure+dout,
                          departure-v.planned_departure_ms,
                          int(v.inbound_group != p.bank)+int(v.outbound_group != p.bank),
                          v.outgoing_kind, claims, witnesses)
    return None


def schedule(platforms: list[Platform], visits: list[Visit], family: str,
             *, closed: set[str] | None = None, horizon_ms: int = 3600000,
             max_wait_ms: int = 7200000, evaluation_budget: int = 100000) -> dict:
    if family not in FAMILIES:
        raise ValueError("Unknown family")
    time_value(horizon_ms, "horizon", positive_only=True)
    time_value(max_wait_ms, "maximum entry wait")
    ids = {p.id for p in platforms}
    if len(ids) != len(platforms) or not platforms:
        raise ValueError("Missing platforms or duplicate physical IDs")
    closed = set() if closed is None else set(closed)
    if not closed.issubset(ids):
        raise ValueError("Closure refers to an unknown physical platform")
    ordered = validate_stock(visits)
    budget = Budget(evaluation_budget)
    calendar = Calendar()
    assigned: dict[str, Assignment] = {}
    rejected: list[dict] = []
    stopped = False
    for v in ordered:
        if stopped:
            rejected.append({"visit_id": v.id, "reason": "search_exhausted"})
            continue
        if v.predecessor and v.predecessor not in assigned:
            rejected.append({"visit_id": v.id, "reason": "predecessor_not_scheduled"})
            continue
        ready = v.requested_entry_ms
        if v.predecessor:
            ready = max(ready, assigned[v.predecessor].exit_clear_ms + v.external_cycle_ms)
        legal = [p for p in platforms if p.id not in closed and p.fits(v.length_m)
                 and route_resources(family, v.inbound_group, p.bank, "in") is not None
                 and route_resources(family, v.outbound_group, p.bank, "out") is not None]
        if not legal:
            rejected.append({"visit_id": v.id, "reason": "no_legal_complete_opportunity",
                             "scope": "declared family, inventory, closures and train profile only"})
            continue
        alternatives = []
        try:
            for p in sorted(legal, key=lambda p: p.id):
                result = fit_visit(v, p, family, calendar, budget, ready, max_wait_ms)
                if result:
                    alternatives.append(result)
        except BudgetExhausted:
            # Deliberately do not claim the partial alternative search is complete.
            stopped = True
            rejected.append({"visit_id": v.id, "reason": "search_exhausted"})
            continue
        if not alternatives:
            rejected.append({"visit_id": v.id, "reason": "not_scheduled_within_entry_wait_budget"})
            continue
        best = min(alternatives, key=lambda a: (a.departure_delay_ms, a.cross_bank_legs, a.entry_ms, a.platform_id))
        calendar.reserve(best.claims)
        assigned[v.id] = best
    calendar.verify()
    values = list(assigned.values())
    trace = []
    for a in values:
        for kind, t in (("entry", a.entry_ms), ("berthed", a.berthed_ms),
                        ("departure", a.departure_ms), ("exit_clear", a.exit_clear_ms)):
            trace.append({"at_ms": t, "kind": kind, "visit_id": a.visit_id,
                          "stock_id": a.stock_id, "platform_id": a.platform_id})
    trace.sort(key=lambda e: (e["at_ms"], e["visit_id"], e["kind"]))
    completed = sum(a.exit_clear_ms <= horizon_ms for a in values)
    by_visit = {v.id: v for v in visits}
    result = {
        "model_version": "0.2.0", "fidelity": "synthetic_resource_templates",
        "family": family, "required_visits": len(visits), "scheduled_visits": len(values),
        "completed_within_horizon": completed,
        "scheduled_residual_at_horizon": len(values)-completed,
        "unscheduled_visits": len(rejected),
        "all_required_scheduled": not rejected,
        "all_required_completed_within_horizon": not rejected and completed == len(visits),
        "horizon_ms": horizon_ms,
        "total_departure_delay_ms": sum(a.departure_delay_ms for a in values),
        "maximum_departure_delay_ms": max((a.departure_delay_ms for a in values), default=0),
        "total_external_entry_wait_ms": sum(a.entry_ms-by_visit[a.visit_id].requested_entry_ms for a in values),
        "cross_bank_legs": sum(a.cross_bank_legs for a in values),
        "candidate_evaluations": budget.evaluations,
        "assignments": [asdict(a) for a in values], "rejected": rejected, "trace": trace,
        "assessments": {"calendar_invariants": "pass", "global_optimality": "not_proven",
                        "full_uk_engineering": "unassessed", "throat_geometry": "unassessed",
                        "spatial_queue_spillback": "unassessed", "passenger_circulation": "unassessed",
                        "game_construction": "not_tested", "game_observation": "not_tested"}
    }
    return result
