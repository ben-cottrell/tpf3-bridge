"""Small immutable model. Time is integer milliseconds; lengths are metres."""
from __future__ import annotations
from dataclasses import dataclass, fields
import math
from typing import Any


def positive(value: float, name: str, *, zero: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a finite number")
    if not math.isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(f"{name} outside its finite nonnegative/positive domain")


def time_value(value: int, name: str, *, positive_only: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be integer milliseconds")
    if value < 0 or (positive_only and value == 0):
        raise ValueError(f"{name} outside its time domain")


def identity(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def strict_record(cls: type, obj: dict[str, Any]):
    if not isinstance(obj, dict):
        raise ValueError(f"Expected object for {cls.__name__}")
    extra = set(obj) - {f.name for f in fields(cls)}
    if extra:
        raise ValueError(f"Unknown fields for {cls.__name__}: {sorted(extra)}")
    try:
        return cls(**obj)
    except TypeError as exc:
        raise ValueError(f"Invalid {cls.__name__}: {exc}") from exc


@dataclass(frozen=True)
class Platform:
    id: str
    label: str
    bank: str
    usable_length_m: float
    margin_each_end_m: float = 5.0

    def __post_init__(self):
        identity(self.id, "platform id")
        identity(self.label, "platform label")
        if self.bank not in {"A", "B"}:
            raise ValueError("Unknown platform bank")
        positive(self.usable_length_m, "usable length")
        positive(self.margin_each_end_m, "margin", zero=True)
        if 2 * self.margin_each_end_m >= self.usable_length_m:
            raise ValueError("Margins consume entire boarding interval")

    def fits(self, length_m: float) -> bool:
        positive(length_m, "train length")
        return length_m + 2 * self.margin_each_end_m <= self.usable_length_m


@dataclass(frozen=True)
class Visit:
    id: str
    stock_id: str
    inbound_group: str
    outbound_group: str
    length_m: float
    requested_entry_ms: int
    planned_departure_ms: int
    dwell_ms: int
    turnback_ms: int
    dispatch_ms: int
    predecessor: str | None = None
    external_cycle_ms: int = 0
    outgoing_kind: str = "passenger"

    def __post_init__(self):
        identity(self.id, "visit id")
        identity(self.stock_id, "stock id")
        if self.inbound_group not in {"A", "B"} or self.outbound_group not in {"A", "B"}:
            raise ValueError("Unknown corridor group")
        if self.outgoing_kind not in {"passenger", "empty_stock"}:
            raise ValueError("Unknown outgoing activity kind")
        positive(self.length_m, "train length")
        for name in ("requested_entry_ms", "planned_departure_ms", "dwell_ms", "turnback_ms", "dispatch_ms", "external_cycle_ms"):
            time_value(getattr(self, name), name)
        if self.planned_departure_ms < self.requested_entry_ms:
            raise ValueError("Planned departure precedes requested entry")
        if self.predecessor is not None:
            identity(self.predecessor, "predecessor")
            if self.external_cycle_ms == 0:
                raise ValueError("A repeated stock visit needs explicit positive external cycle time")

    @property
    def readiness_ms(self) -> int:
        # Deliberately serial activities in this proof, not a universal railway rule.
        return self.dwell_ms + self.turnback_ms + self.dispatch_ms


@dataclass(frozen=True)
class Claim:
    resource: str
    start_ms: int
    end_ms: int
    owner: str
    state: str | None = None  # None = exclusive resource; otherwise a compatible-state lock.

    def __post_init__(self):
        identity(self.resource, "resource")
        identity(self.owner, "claim owner")
        time_value(self.start_ms, "claim start")
        time_value(self.end_ms, "claim end")
        if self.end_ms <= self.start_ms:
            raise ValueError("Claims must have positive duration")
        if self.state is not None:
            identity(self.state, "state")


def conflict(a: Claim, b: Claim) -> bool:
    if a.resource != b.resource:
        return False
    if a.end_ms <= b.start_ms or b.end_ms <= a.start_ms:
        return False
    return a.state is None or b.state is None or a.state != b.state


def legal_traversal(entry: str, exit: str, allowed: set[tuple[str, str]]) -> bool:
    """Coordinate coincidence never contributes a legal movement."""
    return (entry, exit) in allowed


def validate_stock(visits: list[Visit]) -> list[Visit]:
    by_id = {v.id: v for v in visits}
    if len(by_id) != len(visits):
        raise ValueError("Duplicate visit IDs")
    successors: dict[str, str] = {}
    roots: set[str] = set()
    for v in visits:
        if v.predecessor is None:
            if v.stock_id in roots:
                raise ValueError("Duplicate independent stock identity")
            roots.add(v.stock_id)
        else:
            p = by_id.get(v.predecessor)
            if p is None or p.stock_id != v.stock_id:
                raise ValueError("Missing predecessor or changed stock identity")
            if p.length_m != v.length_m:
                raise ValueError("Stock length changed without an implemented formation activity")
            if p.id in successors:
                raise ValueError("One stock unit cannot supply two successors")
            successors[p.id] = v.id
    pending = dict(by_id)
    done: set[str] = set()
    ordered: list[Visit] = []
    while pending:
        ready = [v for v in pending.values() if v.predecessor is None or v.predecessor in done]
        if not ready:
            raise ValueError("Stock dependency cycle")
        v = min(ready, key=lambda x: (x.requested_entry_ms, x.id))
        ordered.append(v)
        done.add(v.id)
        del pending[v.id]
    return ordered
