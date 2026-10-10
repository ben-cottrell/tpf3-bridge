"""One mathematical plain-line shift, not a turnout or station-throat generator."""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt, isfinite
from .model import positive

def signed_finite(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise ValueError("Offset must be a finite signed number")


@dataclass(frozen=True)
class PlainLineShift:
    length_m: float
    offset_m: float

    def __post_init__(self):
        positive(self.length_m, "shift length")
        signed_finite(self.offset_m)

    def evaluate(self, x_m: float) -> dict[str, float]:
        positive(x_m, "x", zero=True)
        if x_m > self.length_m:
            raise ValueError("Coordinate outside shift interval")
        u = x_m / self.length_m
        d, L = self.offset_m, self.length_m
        y = d*(10*u**3 - 15*u**4 + 6*u**5)
        dy = d/L*(30*u**2 - 60*u**3 + 30*u**4)
        ddy = d/L**2*(60*u - 180*u**2 + 120*u**3)
        return {"x_m": x_m, "y_m": y, "dy_dx": dy, "d2y_dx2": ddy,
                "curvature_per_m": ddy/(1+dy*dy)**1.5}

    def curvature_upper_bound(self) -> float:
        return (10/sqrt(3))*abs(self.offset_m)/self.length_m**2

    def certify_radius(self, minimum_radius_m: float) -> dict:
        positive(minimum_radius_m, "minimum radius")
        bound = self.curvature_upper_bound()
        return {"status": "pass_sufficient_bound" if bound <= 1/minimum_radius_m else "not_certified_by_bound",
                "maximum_curvature_bound_per_m": bound,
                "scope": "horizontal curvature of this analytic plain-line shift only"}


def sufficient_length(offset_m: float, minimum_radius_m: float) -> float:
    signed_finite(offset_m)
    positive(minimum_radius_m, "minimum radius")
    return sqrt((10/sqrt(3))*abs(offset_m)*minimum_radius_m)
