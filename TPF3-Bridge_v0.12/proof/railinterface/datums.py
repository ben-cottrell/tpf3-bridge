"""Explicit rail-plane datum transforms; not a full lower-sector gauge model."""
from dataclasses import dataclass
import math
from .reference import number


@dataclass(frozen=True)
class RailSection:
    gauge_mm: float = 1435.
    origin_y_m: float = 0.
    origin_z_m: float = 0.
    rail_plane_angle_rad: float = 0.

    def __post_init__(self):
        number(self.gauge_mm,'gauge_mm',positive=True)
        number(self.origin_y_m,'origin_y');number(self.origin_z_m,'origin_z')
        angle=number(self.rail_plane_angle_rad,'rail_plane_angle')
        if abs(angle)>=math.pi/4:raise ValueError('unsupported_section_angle')

    def edge(self, *, nearest_rail_offset_mm, height_mm, side):
        """Gauge is distance between running edges, not rail-head centres.

        Origin is the gauge midpoint projected onto the rail-top plane. The
        explicit plane angle is NOT derived by dividing cant by track gauge.
        """
        if type(side) is not int or side not in (-1,1):raise ValueError('side_must_be_signed_unit')
        o=number(nearest_rail_offset_mm,'nearest_rail_offset',positive=True)
        h=number(height_mm,'height',nonnegative=True)
        lateral=side*(self.gauge_mm/2+o)/1000
        height=h/1000;c=math.cos(self.rail_plane_angle_rad);s=math.sin(self.rail_plane_angle_rad)
        return (self.origin_y_m+lateral*c-height*s,self.origin_z_m+lateral*s+height*c)

    def measure(self, point_yz, *, side):
        if type(side) is not int or side not in (-1,1):raise ValueError('side_must_be_signed_unit')
        if not isinstance(point_yz,(list,tuple)) or len(point_yz)!=2:raise ValueError('expected_yz_pair')
        y=number(point_yz[0],'y')-self.origin_y_m;z=number(point_yz[1],'z')-self.origin_z_m
        c=math.cos(self.rail_plane_angle_rad);s=math.sin(self.rail_plane_angle_rad)
        lateral=y*c+z*s;vertical=-y*s+z*c
        if side*lateral <= 0:raise ValueError('point_on_wrong_side')
        return {'nearest_rail_offset_mm':side*lateral*1000-self.gauge_mm/2,
                'height_mm_perpendicular_to_rail_plane':vertical*1000}
