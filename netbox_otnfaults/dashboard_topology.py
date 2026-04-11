from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def build_fault_path_overlays(
    path_objects: Iterable[Any],
    active_fault_site_ids: set[int],
) -> list[dict[str, Any]]:
    overlays: list[dict[str, Any]] = []

    for path_obj in path_objects:
        geometry = getattr(path_obj, "geometry", None)
        if not geometry:
            continue

        has_fault = (
            getattr(path_obj, "site_a_id", None) in active_fault_site_ids
            or getattr(path_obj, "site_z_id", None) in active_fault_site_ids
        )
        if not has_fault:
            continue

        length_km = ""
        calculated_length = getattr(path_obj, "calculated_length", None)
        if calculated_length:
            length_km = f"{float(calculated_length):.1f}km"

        overlays.append(
            {
                "id": path_obj.pk,
                "name": path_obj.name,
                "geometry": geometry,
                "cable_type": getattr(path_obj, "cable_type", "") or "",
                "cable_type_display": (
                    path_obj.get_cable_type_display() if getattr(path_obj, "cable_type", None) else ""
                ),
                "site_a_name": path_obj.site_a.name if getattr(path_obj, "site_a", None) else "",
                "site_z_name": path_obj.site_z.name if getattr(path_obj, "site_z", None) else "",
                "groups": [group.name for group in path_obj.groups.all()],
                "length_km": length_km,
                "has_fault": True,
            }
        )

    return overlays
