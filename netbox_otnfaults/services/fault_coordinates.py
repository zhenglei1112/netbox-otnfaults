from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from ..models import OtnFault, OtnPath


@dataclass(frozen=True)
class FaultCoordinate:
    lat: float
    lng: float
    source: str

    @property
    def coords_from_site(self) -> bool:
        return self.source != 'fault'


def resolve_fault_coordinates(fault: OtnFault) -> FaultCoordinate | None:
    """Resolve fault coordinates using one shared map fallback policy."""
    if fault.interruption_latitude is not None and fault.interruption_longitude is not None:
        return FaultCoordinate(
            lat=float(fault.interruption_latitude),
            lng=float(fault.interruption_longitude),
            source='fault',
        )

    a_site = fault.interruption_location_a
    if a_site is None:
        return None

    a_site_coordinate = _site_coordinate(a_site, source='a_site')
    if a_site_coordinate is None:
        return None

    z_sites = list(fault.interruption_location.all())
    if len(z_sites) == 0:
        return _site_coordinate(a_site, source='a_site')

    if len(z_sites) == 1:
        path = _find_path_between_sites(a_site, z_sites[0])
        if path:
            midpoint = _geometry_midpoint(path.geometry)
            if midpoint is not None:
                lat, lng = midpoint
                return FaultCoordinate(lat=lat, lng=lng, source='path_midpoint')
        return a_site_coordinate

    return _site_coordinate(a_site, source='a_site')


def _site_coordinate(site: Any, source: str) -> FaultCoordinate | None:
    if site.latitude is None or site.longitude is None:
        return None
    return FaultCoordinate(lat=float(site.latitude), lng=float(site.longitude), source=source)


def _find_path_between_sites(a_site: Any, z_site: Any) -> OtnPath | None:
    return (
        OtnPath.objects.filter(
            Q(site_a=a_site, site_z=z_site) | Q(site_a=z_site, site_z=a_site)
        )
        .exclude(geometry__isnull=True)
        .exclude(geometry=[])
        .first()
    )


def _geometry_midpoint(geometry: Any) -> tuple[float, float] | None:
    if isinstance(geometry, dict):
        coords = geometry.get('coordinates')
    else:
        coords = geometry

    if not isinstance(coords, list) or not coords:
        return None

    midpoint = coords[len(coords) // 2]
    if not isinstance(midpoint, (list, tuple)) or len(midpoint) < 2:
        return None

    lng, lat = midpoint[0], midpoint[1]
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)
