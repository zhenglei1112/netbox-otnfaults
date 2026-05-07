import json
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse

from netbox_otnfaults.models import OtnMapPreference


MAP_STYLE_SCHEMA_VERSION: int = 1
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
RGBA_COLOR_RE = re.compile(
    r"^rgba\(\s*(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\s*,\s*"
    r"(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\s*,\s*"
    r"(?:\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\s*,\s*"
    r"(?:0|0?\.\d+|1(?:\.0+)?)\s*\)$"
)

DEFAULT_MAP_STYLE_CONFIG: dict[str, dict[str, Any]] = {
    "province": {
        "visible": True,
        "fillColor": "#2c3e50",
        "fillOpacity": 0.05,
        "lineColor": "rgba(90, 140, 190, 0.7)",
        "lineWidth": 1.5,
        "lineOpacity": 0.9,
    },
    "sites": {
        "visible": True,
        "circleColor": "#00aaff",
        "circleRadius": 3,
        "strokeColor": "#ffffff",
        "strokeWidth": 1,
        "labelColor": "#1a1a1a",
        "labelSize": 14,
        "labelMinZoom": 6,
    },
    "paths": {
        "visible": True,
        "lineColor": "#00cc66",
        "lineWidth": 2,
        "lineOpacity": 0.8,
        "highlightColor": "#FFD700",
        "highlightWidth": 5,
    },
}

MAP_STYLE_FIELD_RULES: dict[str, dict[str, dict[str, Any]]] = {
    "province": {
        "visible": {"type": "bool"},
        "fillColor": {"type": "color"},
        "fillOpacity": {"type": "float", "min": 0.0, "max": 1.0},
        "lineColor": {"type": "color"},
        "lineWidth": {"type": "float", "min": 0.0, "max": 10.0},
        "lineOpacity": {"type": "float", "min": 0.0, "max": 1.0},
    },
    "sites": {
        "visible": {"type": "bool"},
        "circleColor": {"type": "color"},
        "circleRadius": {"type": "float", "min": 1.0, "max": 24.0},
        "strokeColor": {"type": "color"},
        "strokeWidth": {"type": "float", "min": 0.0, "max": 8.0},
        "labelColor": {"type": "color"},
        "labelSize": {"type": "float", "min": 8.0, "max": 36.0},
        "labelMinZoom": {"type": "float", "min": 0.0, "max": 24.0},
    },
    "paths": {
        "visible": {"type": "bool"},
        "lineColor": {"type": "color"},
        "lineWidth": {"type": "float", "min": 0.5, "max": 12.0},
        "lineOpacity": {"type": "float", "min": 0.0, "max": 1.0},
        "highlightColor": {"type": "color"},
        "highlightWidth": {"type": "float", "min": 1.0, "max": 20.0},
    },
}


def _clone_default_config() -> dict[str, dict[str, Any]]:
    return json.loads(json.dumps(DEFAULT_MAP_STYLE_CONFIG))


def _normalize_color(value: Any, group_name: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{group_name}.{field_name} must be a string color value.")
    if HEX_COLOR_RE.match(value) or RGBA_COLOR_RE.match(value):
        return value
    raise ValidationError(f"{group_name}.{field_name} is not a supported color value.")


def _normalize_number(value: Any, rule: dict[str, Any], group_name: str, field_name: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{group_name}.{field_name} must be numeric.")
    normalized = float(value)
    if normalized < rule["min"] or normalized > rule["max"]:
        raise ValidationError(f"{group_name}.{field_name} is out of range.")
    return int(normalized) if float(normalized).is_integer() else normalized


def normalize_map_style_config(raw_config: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    normalized = _clone_default_config()
    if raw_config is None:
        return normalized
    if not isinstance(raw_config, dict):
        raise ValidationError("style_config must be a JSON object.")

    for group_name, group_value in raw_config.items():
        if group_name not in MAP_STYLE_FIELD_RULES:
            raise ValidationError(f"Unsupported style group: {group_name}")
        if not isinstance(group_value, dict):
            raise ValidationError(f"{group_name} must be a JSON object.")

        for field_name, field_value in group_value.items():
            rule = MAP_STYLE_FIELD_RULES[group_name].get(field_name)
            if rule is None:
                raise ValidationError(f"Unsupported style field: {group_name}.{field_name}")

            if rule["type"] == "bool":
                if not isinstance(field_value, bool):
                    raise ValidationError(f"{group_name}.{field_name} must be a boolean.")
                normalized[group_name][field_name] = field_value
            elif rule["type"] == "color":
                normalized[group_name][field_name] = _normalize_color(field_value, group_name, field_name)
            else:
                normalized[group_name][field_name] = _normalize_number(field_value, rule, group_name, field_name)

    return normalized


def get_user_map_style_config(user: Any, map_mode: str) -> dict[str, dict[str, Any]]:
    default_config = _clone_default_config()
    if not getattr(user, "is_authenticated", False):
        return default_config

    preference = OtnMapPreference.objects.filter(user=user, map_mode=map_mode).first()
    if preference is None:
        return default_config
    return normalize_map_style_config(preference.style_config)


def save_user_map_style_config(user: Any, map_mode: str, raw_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not getattr(user, "is_authenticated", False):
        raise ValidationError("Authentication is required.")

    normalized = normalize_map_style_config(raw_config)
    preference = OtnMapPreference.objects.filter(user=user, map_mode=map_mode).first()
    if preference is None:
        preference = OtnMapPreference(
            user=user,
            map_mode=map_mode,
            style_config=normalized,
            schema_version=MAP_STYLE_SCHEMA_VERSION,
            tags=[],
            custom_field_data={},
        )
        preference.save()
    else:
        preference.style_config = normalized
        preference.schema_version = MAP_STYLE_SCHEMA_VERSION
        if preference.tags is None:
            preference.tags = []
        if preference.custom_field_data is None:
            preference.custom_field_data = {}
        preference.save(update_fields=("style_config", "schema_version", "tags", "custom_field_data", "last_updated"))
    return normalized


def build_map_preference_context(request: Any, map_mode: str) -> dict[str, str]:
    style_config = get_user_map_style_config(request.user, map_mode)
    return {
        "map_style_preferences": json.dumps(style_config, cls=DjangoJSONEncoder),
        "map_preferences_url": reverse('plugins:netbox_otnfaults:map_preferences', args=[map_mode]),
    }
