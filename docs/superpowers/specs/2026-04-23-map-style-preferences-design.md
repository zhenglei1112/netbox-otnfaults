# Map Style Preferences Design

## Purpose

Add a map-window configuration feature for the NetBox OTN faults plugin. The first version saves per-user visual style preferences for three shared map layer groups:

- Province boundary layer
- NetBox site layer
- OTN path layer

The design intentionally leaves room for later preferences such as fault marker styling, heatmap styling, default layer loading, viewport defaults, and role/global defaults.

## Current Context

The plugin already uses a unified map architecture:

- `unified_map.html` injects `window.OTNMapConfig`.
- `map_modes.py` defines mode-specific static assets.
- `unified_map_core.js` creates the MapLibre map and shared province/site/path layers.
- Mode plugins such as `fault_mode.js`, `location_mode.js`, and `statistics_cable_break_mode.js` add mode-specific behavior.
- `LayerToggleControl.js` currently manages view/filter state for fault maps, but it is not a persistent per-user style preference system.

The new feature should stay inside `netbox_otnfaults/` and must not rely on undocumented NetBox core APIs.

## Recommended Approach

Use a plugin-owned model and API:

- Add `OtnMapPreference`, keyed by `user + map_mode`.
- Store map style preferences in a versioned JSON field.
- Inject the current user's preference into `window.OTNMapConfig`.
- Apply style preferences after shared layers are created.
- Provide a floating map settings panel for preview, reset, and save.

This satisfies the requirement to save by person while keeping the schema extensible.

## Data Model

Add `OtnMapPreference(NetBoxModel)`.

Fields:

- `user`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otn_map_preferences')`
- `map_mode`: `CharField(max_length=64)`
- `style_config`: `JSONField(default=dict, blank=True)`
- `schema_version`: `PositiveSmallIntegerField(default=1)`
- standard `NetBoxModel` fields

Constraints:

- Unique constraint on `user + map_mode`

Methods:

- `get_absolute_url()`
- `__str__()`

The model should have a `FilterSet` so it can be exposed consistently through NetBox plugin patterns later. The initial UI/API should still limit users to their own preferences.

## Style Config Schema V1

The first version stores only these keys:

```json
{
  "province": {
    "visible": true,
    "fillColor": "#2c3e50",
    "fillOpacity": 0.05,
    "lineColor": "rgba(90, 140, 190, 0.7)",
    "lineWidth": 1.5,
    "lineOpacity": 0.9
  },
  "sites": {
    "visible": true,
    "circleColor": "#00aaff",
    "circleRadius": 6,
    "strokeColor": "#ffffff",
    "strokeWidth": 1,
    "labelColor": "#1a1a1a",
    "labelSize": 14,
    "labelMinZoom": 6
  },
  "paths": {
    "visible": true,
    "lineColor": "#00cc66",
    "lineWidth": 2,
    "lineOpacity": 0.8,
    "highlightColor": "#FFD700",
    "highlightWidth": 5
  }
}
```

Unknown top-level keys and unknown fields inside known groups should be rejected or filtered server-side. Numeric fields should be clamped to safe ranges. Color fields should accept hex colors and existing CSS color strings used by the current map styles.

## API

Add plugin-local endpoints:

- `GET /plugins/otnfaults/map/preferences/<map_mode>/`
- `POST /plugins/otnfaults/map/preferences/<map_mode>/`

Behavior:

- Both endpoints require an authenticated user and existing plugin permissions.
- `GET` returns the current user's saved preference for the map mode, merged with defaults.
- `POST` validates and saves only the current user's preference.
- Users cannot read or write another user's preferences through these endpoints.
- The API should return a normalized config so the frontend has one canonical shape after save.

This avoids inventing or depending on NetBox core API paths.

## Backend Flow

Map views should resolve the current user's style preference for the active `map_mode` and inject it into the map context:

- `map_style_preferences`: JSON for `window.OTNMapConfig.mapStylePreferences`
- `map_preferences_url`: URL for the current mode's GET/POST endpoint

This should be done through a small helper/service rather than duplicated across map views. The helper should return defaults when no preference exists.

## Frontend Flow

Add two focused frontend modules:

- `services/MapStylePreferenceService.js`
- `controls/MapStylePreferenceControl.js`

`MapStylePreferenceService` responsibilities:

- Merge default style config with saved user config.
- Apply province, site, and path styles to MapLibre layers.
- Safely no-op when a layer is absent in a map mode.
- Re-apply shared styles after style reload events where relevant.

Target layers:

- `user-geojson-fill`
- `user-geojson-line`
- `netbox-sites-layer`
- `netbox-sites-labels`
- `otn-paths-layer`
- `otn-paths-highlight-outline`
- `otn-paths-highlight-layer`

`MapStylePreferenceControl` responsibilities:

- Render a floating settings panel inside the map window.
- Provide controls for the V1 province/site/path fields.
- Support `Apply Preview`, `Restore Defaults`, and `Save as My Default`.
- Apply preview changes immediately to the current map instance.
- Save only when the user clicks save.
- Keep the map open after save; do not refresh the iframe.

The control should be independent from `LayerToggleControl`, because `LayerToggleControl` is currently a fault-map view/filter control rather than a persistent style preference editor.

## UI Design

The entry point is a settings button in the map window. It opens a right-side floating panel titled "My Map Style" or equivalent localized Chinese text.

Panel sections:

- Province boundary style
- Site style
- Path style

Each section includes a visibility toggle and simple style fields. The UI should use NetBox/Bootstrap 5 styling and avoid adding React/Vue. Color fields can start as native color inputs where possible, with numeric inputs for opacity, width, radius, and label size.

## Error Handling

- If preference loading fails, the map should continue with built-in defaults and show a non-blocking message in the settings panel.
- If save fails, keep the current preview in place and show the validation or network error in the panel.
- If a configured layer does not exist in a mode, skip it without throwing.
- Invalid JSON or unsupported fields should not be persisted.

## Testing

Initial coverage should include:

- `OtnMapPreference` fields and `user + map_mode` uniqueness.
- FilterSet exists for the model.
- Preference API reads/writes only the current user's record.
- Invalid or unknown style fields are rejected or normalized.
- `unified_map.html` injects `mapStylePreferences` and `mapPreferencesUrl`.
- `map_modes.py` loads the new preference service/control for relevant map modes.
- `MapStylePreferenceService.js` references and applies the province, site, and path layer IDs.
- `MapStylePreferenceControl.js` includes preview, restore defaults, and save actions.

## Out Of Scope For V1

- Fault marker style configuration
- Heatmap style configuration
- Default viewport, projection, or zoom configuration
- Role-based, tenant-based, or global default style profiles
- Multiple named style profiles per user
- Import/export of style presets

## Implementation Notes

- Follow NetBox plugin structure and type hints in Python.
- Keep all changes inside `netbox_otnfaults/`.
- Add migrations and run `makemigrations` then `migrate` in a real NetBox environment when available.
- This repository does not have a running NetBox environment, so verification will rely on source tests and Python syntax checks unless the user provides a runtime.
