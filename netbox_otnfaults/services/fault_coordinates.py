from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db.models import Q

from ..models import OtnFault, CutoverTask


@dataclass(frozen=True)
class FaultCoordinate:
    lat: float
    lng: float
    source: str

    @property
    def coords_from_site(self) -> bool:
        return self.source not in ('fault', 'cutover', 'object')


def resolve_location_coordinates(
    obj: Any = None,
    a_site: Any = None,
    z_sites: list[Any] | None = None,
) -> FaultCoordinate | None:
    """Resolve coordinates using shared map fallback policy for OtnFault, CutoverTask or Site pairs."""
    # 1. 如果传入了模型实例，先判断显式自带的经纬度
    if obj is not None:
        model_name = getattr(getattr(obj, '_meta', None), 'model_name', '')
        class_name = obj.__class__.__name__
        
        if model_name == 'otnfault' or class_name == 'OtnFault':
            if getattr(obj, 'interruption_latitude', None) is not None and getattr(obj, 'interruption_longitude', None) is not None:
                return FaultCoordinate(
                    lat=float(obj.interruption_latitude),
                    lng=float(obj.interruption_longitude),
                    source='fault',
                )
        elif model_name == 'cutovertask' or class_name == 'CutoverTask':
            if getattr(obj, 'cutover_latitude', None) is not None and getattr(obj, 'cutover_longitude', None) is not None:
                return FaultCoordinate(
                    lat=float(obj.cutover_latitude),
                    lng=float(obj.cutover_longitude),
                    source='cutover',
                )
        elif getattr(obj, 'latitude', None) is not None and getattr(obj, 'longitude', None) is not None:
            return FaultCoordinate(
                lat=float(obj.latitude),
                lng=float(obj.longitude),
                source='object',
            )

        # 尝试提取模型的 a_site 和 z_sites
        if a_site is None and hasattr(obj, 'interruption_location_a'):
            a_site = obj.interruption_location_a
        if z_sites is None and hasattr(obj, 'interruption_location'):
            z_sites = list(obj.interruption_location.all())

    if z_sites is None:
        z_sites = []

    # 2. 如果没有任何站点信息
    if a_site is None:
        if z_sites:
            return _calculate_sites_center(z_sites, source='sites_center')
        return None

    a_site_coordinate = _site_coordinate(a_site, source='a_site')

    # 3. 若只配置了 1 个 Z 端站点，优先检索两站点之间的光缆路径中点
    if len(z_sites) == 1 and z_sites[0] is not None:
        path = _find_path_between_sites(a_site, z_sites[0])
        if path:
            midpoint = _geometry_midpoint(path.geometry)
            if midpoint is not None:
                lat, lng = midpoint
                return FaultCoordinate(lat=lat, lng=lng, source='path_midpoint')

    # 4. 退回 A 端站点坐标
    if a_site_coordinate is not None:
        return a_site_coordinate

    # 5. 若 A 端站点也无坐标，计算所有配置了坐标的 A/Z 站点算术平均中心
    all_sites = [a_site] + z_sites
    return _calculate_sites_center(all_sites, source='sites_center')


def resolve_fault_coordinates(fault: OtnFault) -> FaultCoordinate | None:
    """Resolve fault coordinates using shared map fallback policy."""
    return resolve_location_coordinates(obj=fault)


def resolve_cutover_coordinates(cutover: CutoverTask) -> FaultCoordinate | None:
    """Resolve cutover coordinates using shared map fallback policy."""
    return resolve_location_coordinates(obj=cutover)


def _site_coordinate(site: Any, source: str) -> FaultCoordinate | None:
    if site is None or getattr(site, 'latitude', None) is None or getattr(site, 'longitude', None) is None:
        return None
    return FaultCoordinate(lat=float(site.latitude), lng=float(site.longitude), source=source)


def _calculate_sites_center(sites: list[Any], source: str) -> FaultCoordinate | None:
    valid_coords = [
        (float(s.latitude), float(s.longitude))
        for s in sites
        if s is not None and getattr(s, 'latitude', None) is not None and getattr(s, 'longitude', None) is not None
    ]
    if not valid_coords:
        return None
    avg_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
    avg_lng = sum(c[1] for c in valid_coords) / len(valid_coords)
    return FaultCoordinate(lat=avg_lat, lng=avg_lng, source=source)


def _find_path_between_sites(a_site: Any, z_site: Any) -> Any:
    try:
        from ..models import OtnPath
        return (
            OtnPath.objects.filter(
                Q(site_a=a_site, site_z=z_site) | Q(site_a=z_site, site_z=a_site)
            )
            .exclude(geometry__isnull=True)
            .exclude(geometry=[])
            .first()
        )
    except Exception:
        return None


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

