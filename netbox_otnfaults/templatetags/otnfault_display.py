from typing import Iterable

from django import template

from netbox_otnfaults.models import (
    PowerRectificationMeasureChoices,
    PowerRootCauseAnalysisChoices,
    RecoveryModeChoices,
)


register = template.Library()


CHOICE_SETS = {
    "recovery_mode": RecoveryModeChoices,
    "root_cause_analysis": PowerRootCauseAnalysisChoices,
    "rectification_measures": PowerRectificationMeasureChoices,
}


@register.filter
def otnfault_choice_labels(values: Iterable[str] | str | None, field_name: str) -> list[str]:
    """Return display labels for multi-select OTN fault choice fields."""
    choice_set = CHOICE_SETS.get(field_name)
    if choice_set is None or not values:
        return []

    if isinstance(values, str):
        selected_values = [value.strip() for value in values.split(",") if value.strip()]
    else:
        selected_values = [value for value in values if value]

    labels = {
        value: label
        for value, label, *_ in choice_set.CHOICES
    }
    return [labels.get(value, value) for value in selected_values]
