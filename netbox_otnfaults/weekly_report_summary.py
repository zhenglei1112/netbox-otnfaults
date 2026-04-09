"""Helpers for weekly report summary payloads."""

from typing import Any


def build_bare_fiber_summary(
    total_services: int, impacted_services: list[dict[str, Any]]
) -> dict[str, int]:
    """Build summary counts for bare fiber services."""

    interruption_count = sum(
        1 for service in impacted_services if service.get("status") == "interruption"
    )
    jitter_count = sum(
        1 for service in impacted_services if service.get("status") == "jitter"
    )
    normal_count = max(total_services - interruption_count - jitter_count, 0)

    return {
        "interruption": interruption_count,
        "jitter": jitter_count,
        "normal": normal_count,
    }
