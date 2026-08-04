from __future__ import annotations

from collections.abc import Mapping


CUTOVER_COMPLETION_REQUIRED_FIELDS: tuple[str, ...] = (
    'started_at',
    'completed_at',
    'closed_at',
    'is_timeout',
    'cutover_result',
    'rectification_status',
)


def find_missing_cutover_completion_fields(
    values: Mapping[str, object],
    *,
    completed_status: str,
) -> tuple[str, ...]:
    if values.get('status') != completed_status:
        return ()

    return tuple(
        field_name
        for field_name in CUTOVER_COMPLETION_REQUIRED_FIELDS
        if values.get(field_name) in (None, '')
    )

