# Map Style Preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a per-user map style preference feature for province boundaries, NetBox sites, and OTN paths in the unified map window.

**Architecture:** Add a plugin-owned `OtnMapPreference` model keyed by `user + map_mode`, with a versioned JSON schema validated through a small service module. Map views inject the current user's normalized preference into `window.OTNMapConfig`; a shared frontend service applies styles to MapLibre layers and a floating control previews, resets, and saves the current user's defaults.

**Tech Stack:** Django 5 / NetBox 4 plugin models and views, `JsonResponse`, MapLibre GL JS, Bootstrap 5, source-level Python `unittest` tests.

---

## File Structure

- Create `netbox_otnfaults/services/map_preferences.py`: default schema, validation, normalization, current-user lookup/save helpers, and template context builder.
- Modify `netbox_otnfaults/models.py`: add `OtnMapPreference(NetBoxModel)`.
- Modify `netbox_otnfaults/filtersets.py`: add `OtnMapPreferenceFilterSet`.
- Modify `netbox_otnfaults/urls.py`: add plugin-local GET/POST preference endpoint.
- Modify `netbox_otnfaults/views.py`: add `MapPreferenceView` and inject preference context into unified map views.
- Modify `netbox_otnfaults/map_modes.py`: load the preference service/control JS in unified map modes.
- Modify `netbox_otnfaults/templates/netbox_otnfaults/unified_map.html`: expose `mapStylePreferences` and `mapPreferencesUrl`.
- Create `netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js`: apply normalized styles to province/site/path layers.
- Create `netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js`: floating settings panel with preview/default/save actions.
- Modify `netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js`: instantiate the service after shared layers and register the control.
- Create `tests/test_map_style_preferences.py`: source-level regression coverage.
- Add migration `netbox_otnfaults/migrations/0054_otnmappreference.py` via `makemigrations` if NetBox/Django imports are available in the environment.

---

### Task 1: Source Tests For The Contract

**Files:**
- Create: `tests/test_map_style_preferences.py`
- Read: `docs/superpowers/specs/2026-04-23-map-style-preferences-design.md`

- [ ] **Step 1: Write the failing source tests**

Create `tests/test_map_style_preferences.py`:

```python
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
SERVICE_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "map_preferences.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html"
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
CORE_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "unified_map_core.js"
STYLE_SERVICE_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "services" / "MapStylePreferenceService.js"
STYLE_CONTROL_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "controls" / "MapStylePreferenceControl.js"


class MapStylePreferenceSourceTestCase(unittest.TestCase):
    def test_model_filterset_service_and_endpoint_contract(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8")
        filtersets_source = FILTERSETS_PATH.read_text(encoding="utf-8")
        urls_source = URLS_PATH.read_text(encoding="utf-8")
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        service_source = SERVICE_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnMapPreference(NetBoxModel):", models_source)
        self.assertIn("related_name='otn_map_preferences'", models_source)
        self.assertIn("style_config = models.JSONField(", models_source)
        self.assertIn("schema_version = models.PositiveSmallIntegerField(default=1)", models_source)
        self.assertIn("fields=('user', 'map_mode')", models_source)
        self.assertIn("name='unique_otn_map_preference_user_mode'", models_source)
        self.assertIn("def get_absolute_url(self) -> str:", models_source)

        self.assertIn("class OtnMapPreferenceFilterSet(NetBoxModelFilterSet):", filtersets_source)
        self.assertIn("model = OtnMapPreference", filtersets_source)
        self.assertIn("fields = ('id', 'user', 'map_mode', 'schema_version')", filtersets_source)

        self.assertIn("MAP_STYLE_SCHEMA_VERSION: int = 1", service_source)
        self.assertIn("DEFAULT_MAP_STYLE_CONFIG", service_source)
        self.assertIn("def normalize_map_style_config(", service_source)
        self.assertIn("def get_user_map_style_config(", service_source)
        self.assertIn("def save_user_map_style_config(", service_source)
        self.assertIn("def build_map_preference_context(", service_source)
        self.assertIn("reverse('plugins:netbox_otnfaults:map_preferences'", service_source)

        self.assertIn("path('map/preferences/<str:map_mode>/', views.MapPreferenceView.as_view(), name='map_preferences')", urls_source)
        self.assertIn("class MapPreferenceView(PermissionRequiredMixin, View):", views_source)
        self.assertIn("get_user_map_style_config(request.user, map_mode)", views_source)
        self.assertIn("save_user_map_style_config(request.user, map_mode, payload)", views_source)
        self.assertNotIn("user_id = request.GET", views_source)

    def test_map_views_template_and_assets_are_wired(self) -> None:
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        template_source = TEMPLATE_PATH.read_text(encoding="utf-8")
        modes_source = MAP_MODES_PATH.read_text(encoding="utf-8")
        core_source = CORE_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("build_map_preference_context", views_source)
        self.assertIn("**build_map_preference_context(request, 'fault')", views_source)
        self.assertIn("**build_map_preference_context(request, 'statistics_cable_break')", views_source)
        self.assertIn("**build_map_preference_context(request, map_mode)", views_source)

        self.assertIn("mapStylePreferences: {{ map_style_preferences|safe }}", template_source)
        self.assertIn("mapPreferencesUrl: '{{ map_preferences_url|escapejs }}'", template_source)

        self.assertIn("'services/MapStylePreferenceService.js'", modes_source)
        self.assertIn("'controls/MapStylePreferenceControl.js'", modes_source)
        self.assertIn("this.mapStylePreferenceService = null;", core_source)
        self.assertIn("this._initMapStylePreferences();", core_source)
        self.assertLess(core_source.index("this._initSharedLayers();"), core_source.index("this._initMapStylePreferences();"))
        self.assertIn("new MapStylePreferenceService(this.map, this.config)", core_source)
        self.assertIn("new MapStylePreferenceControl({", core_source)

    def test_frontend_service_and_control_cover_v1_layers_and_actions(self) -> None:
        service_source = STYLE_SERVICE_JS_PATH.read_text(encoding="utf-8")
        control_source = STYLE_CONTROL_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("class MapStylePreferenceService", service_source)
        self.assertIn("DEFAULT_MAP_STYLE_CONFIG", service_source)
        for layer_id in [
            "user-geojson-fill",
            "user-geojson-line",
            "netbox-sites-layer",
            "netbox-sites-labels",
            "otn-paths-layer",
            "otn-paths-highlight-outline",
            "otn-paths-highlight-layer",
        ]:
            self.assertIn(layer_id, service_source)
        self.assertIn("apply(config)", service_source)
        self.assertIn("resetToDefaults()", service_source)

        self.assertIn("class MapStylePreferenceControl", control_source)
        self.assertIn("应用预览", control_source)
        self.assertIn("恢复默认", control_source)
        self.assertIn("保存为我的默认", control_source)
        self.assertIn("fetch(this.preferencesUrl", control_source)
        self.assertIn("X-CSRFToken", control_source)
        self.assertIn("province", control_source)
        self.assertIn("sites", control_source)
        self.assertIn("paths", control_source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing tests**

Run: `python -m unittest tests.test_map_style_preferences`

Expected: FAIL because `OtnMapPreference`, the service, endpoint, and frontend files do not exist yet.

- [ ] **Step 3: Commit the failing tests**

Run:

```powershell
git add tests/test_map_style_preferences.py
git commit -m "test: cover map style preference contract"
```

---

### Task 2: Backend Model, FilterSet, And Service

**Files:**
- Modify: `netbox_otnfaults/models.py`
- Modify: `netbox_otnfaults/filtersets.py`
- Create: `netbox_otnfaults/services/map_preferences.py`
- Create: `netbox_otnfaults/migrations/0054_otnmappreference.py`
- Test: `tests/test_map_style_preferences.py`

- [ ] **Step 1: Add `OtnMapPreference`**

In `netbox_otnfaults/models.py`, add this class after `OtnPath`:

```python
class OtnMapPreference(NetBoxModel):
    """Per-user style preferences for unified map modes."""

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otn_map_preferences',
        verbose_name='用户',
    )
    map_mode = models.CharField(max_length=64, verbose_name='地图模式')
    style_config = models.JSONField(default=dict, blank=True, verbose_name='样式配置')
    schema_version = models.PositiveSmallIntegerField(default=1, verbose_name='配置版本')
    comments = models.TextField(blank=True, verbose_name='评论')

    class Meta:
        ordering = ('user', 'map_mode')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'map_mode'),
                name='unique_otn_map_preference_user_mode',
            )
        ]
        verbose_name = '地图偏好'
        verbose_name_plural = '地图偏好'

    def __str__(self) -> str:
        return f"{self.user} / {self.map_mode}"

    def get_absolute_url(self) -> str:
        return reverse('plugins:netbox_otnfaults:otnfault_map_globe')
```

- [ ] **Step 2: Add `OtnMapPreferenceFilterSet`**

In `netbox_otnfaults/filtersets.py`, import `OtnMapPreference` and add:

```python
class OtnMapPreferenceFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = OtnMapPreference
        fields = ('id', 'user', 'map_mode', 'schema_version')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(map_mode__icontains=value)
            | Q(user__username__icontains=value)
        )
```

- [ ] **Step 3: Create `map_preferences.py`**

Create `netbox_otnfaults/services/map_preferences.py` with default config, type/limit maps, and these public functions:

```python
def normalize_map_style_config(raw_config: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    ...

def get_user_map_style_config(user: Any, map_mode: str) -> dict[str, dict[str, Any]]:
    ...

def save_user_map_style_config(user: Any, map_mode: str, raw_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ...

def build_map_preference_context(request: Any, map_mode: str) -> dict[str, str]:
    ...
```

Use the schema from `docs/superpowers/specs/2026-04-23-map-style-preferences-design.md`. `save_user_map_style_config()` must call `OtnMapPreference.objects.update_or_create(user=user, map_mode=map_mode, defaults={...})`; do not accept a user id from input.

- [ ] **Step 4: Run source tests**

Run: `python -m unittest tests.test_map_style_preferences.MapStylePreferenceSourceTestCase.test_model_filterset_service_and_endpoint_contract`

Expected: FAIL only on missing endpoint/view integration; model, FilterSet, and service assertions pass.

- [ ] **Step 5: Generate migration**

Run in a NetBox runtime: `python manage.py makemigrations netbox_otnfaults`

Expected: `netbox_otnfaults/migrations/0054_otnmappreference.py` is created.

If this repo cannot import a NetBox settings module, create an equivalent manual migration and verify syntax with:

```powershell
python -m py_compile .\netbox_otnfaults\models.py .\netbox_otnfaults\filtersets.py .\netbox_otnfaults\services\map_preferences.py
```

- [ ] **Step 6: Commit backend model and service**

Run:

```powershell
git add netbox_otnfaults/models.py netbox_otnfaults/filtersets.py netbox_otnfaults/services/map_preferences.py netbox_otnfaults/migrations/0054_otnmappreference.py
git commit -m "feat: add map style preference model"
```

---

### Task 3: Endpoint And Template Context

**Files:**
- Modify: `netbox_otnfaults/views.py`
- Modify: `netbox_otnfaults/urls.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/unified_map.html`
- Test: `tests/test_map_style_preferences.py`

- [ ] **Step 1: Add preference service imports**

In `netbox_otnfaults/views.py`, add:

```python
from .services.map_preferences import (
    build_map_preference_context,
    get_user_map_style_config,
    save_user_map_style_config,
)
```

- [ ] **Step 2: Add `MapPreferenceView`**

In `netbox_otnfaults/views.py`, add near the map views:

```python
class MapPreferenceView(PermissionRequiredMixin, View):
    """Current user's per-map-mode style preference endpoint."""

    permission_required = 'netbox_otnfaults.view_otnfault'

    def get(self, request, map_mode: str):
        return JsonResponse({
            'schema_version': 1,
            'style_config': get_user_map_style_config(request.user, map_mode),
        })

    def post(self, request, map_mode: str):
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的 JSON 请求体'}, status=400)

        if not isinstance(payload, dict):
            return JsonResponse({'error': '请求体必须是 JSON 对象'}, status=400)

        raw_style_config = payload.get('style_config', payload)
        if not isinstance(raw_style_config, dict):
            return JsonResponse({'error': 'style_config 必须是 JSON 对象'}, status=400)

        normalized = save_user_map_style_config(request.user, map_mode, raw_style_config)
        return JsonResponse({'schema_version': 1, 'style_config': normalized})
```

- [ ] **Step 3: Add URL and context injection**

In `netbox_otnfaults/urls.py`, add near other map URLs:

```python
path('map/preferences/<str:map_mode>/', views.MapPreferenceView.as_view(), name='map_preferences'),
```

In map render contexts, add:

```python
**build_map_preference_context(request, 'fault'),
**build_map_preference_context(request, 'statistics_cable_break'),
**build_map_preference_context(request, map_mode),
```

Use the first in `OtnFaultGlobeMapView`, the second in `StatisticsCableBreakMapView`, and the third in `LocationMapView`.

- [ ] **Step 4: Inject frontend config**

In `unified_map.html`, inside `window.OTNMapConfig`, add:

```javascript
    mapStylePreferences: {{ map_style_preferences|safe }},
    mapPreferencesUrl: '{{ map_preferences_url|escapejs }}',
```

- [ ] **Step 5: Run tests and syntax checks**

Run:

```powershell
python -m unittest tests.test_map_style_preferences.MapStylePreferenceSourceTestCase.test_model_filterset_service_and_endpoint_contract
python -m py_compile .\netbox_otnfaults\views.py .\netbox_otnfaults\urls.py
```

Expected: test passes; syntax checks pass.

- [ ] **Step 6: Commit endpoint and context**

Run:

```powershell
git add netbox_otnfaults/views.py netbox_otnfaults/urls.py netbox_otnfaults/templates/netbox_otnfaults/unified_map.html
git commit -m "feat: expose map style preference endpoint"
```

---

### Task 4: Frontend Style Service And Control

**Files:**
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js`
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js`
- Modify: `netbox_otnfaults/map_modes.py`
- Test: `tests/test_map_style_preferences.py`

- [ ] **Step 1: Create `MapStylePreferenceService.js`**

Implement a global `MapStylePreferenceService` class with:

```javascript
class MapStylePreferenceService {
  constructor(map, config) {
    this.map = map;
    this.config = config || {};
    this.defaultConfig = MapStylePreferenceService.clone(MapStylePreferenceService.DEFAULT_MAP_STYLE_CONFIG);
    this.currentConfig = this.merge(this.defaultConfig, this.config.mapStylePreferences || {});
  }

  static clone(value) { return JSON.parse(JSON.stringify(value)); }
  merge(baseConfig, overrideConfig) { /* merge province/sites/paths known fields only */ }
  getConfig() { return MapStylePreferenceService.clone(this.currentConfig); }
  resetToDefaults() { this.currentConfig = MapStylePreferenceService.clone(this.defaultConfig); this.apply(this.currentConfig); return this.getConfig(); }
  apply(config) { this.currentConfig = this.merge(this.defaultConfig, config || {}); this.applyProvince(this.currentConfig.province); this.applySites(this.currentConfig.sites); this.applyPaths(this.currentConfig.paths); return this.getConfig(); }
}

window.MapStylePreferenceService = MapStylePreferenceService;
```

The implementation must call `setPaintProperty`, `setLayoutProperty`, and `setLayerZoomRange` for these layer IDs: `user-geojson-fill`, `user-geojson-line`, `netbox-sites-layer`, `netbox-sites-labels`, `otn-paths-layer`, `otn-paths-highlight-outline`, `otn-paths-highlight-layer`.

- [ ] **Step 2: Create `MapStylePreferenceControl.js`**

Implement a global `MapStylePreferenceControl` with MapLibre `onAdd()` / `onRemove()`. It must render a right-side floating panel titled `我的地图样式` and include buttons labeled `应用预览`, `恢复默认`, and `保存为我的默认`.

The save method must POST:

```javascript
await fetch(this.preferencesUrl, {
  method: "POST",
  credentials: "same-origin",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": this.getCsrfToken(),
  },
  body: JSON.stringify({ style_config: styleConfig }),
});
```

The control must collect and save `province`, `sites`, and `paths` groups only.

- [ ] **Step 3: Load assets in map modes**

In `map_modes.py`, add to `fault`, `statistics_cable_break`, `location`, `path`, and `pathgroup`:

```python
'services/MapStylePreferenceService.js',
'controls/MapStylePreferenceControl.js',
```

Put the service before the control.

- [ ] **Step 4: Register service and control in `OTNMapCore`**

In `OTNMapCore.constructor`, add:

```javascript
    this.mapStylePreferenceService = null;
```

After `this._initSharedLayers();`, call:

```javascript
      this._initMapStylePreferences();
```

Add:

```javascript
  _initMapStylePreferences() {
    if (typeof MapStylePreferenceService === "undefined") return;

    this.mapStylePreferenceService = new MapStylePreferenceService(this.map, this.config);
    this.mapStylePreferenceService.apply(this.config.mapStylePreferences || {});

    if (typeof MapStylePreferenceControl !== "undefined") {
      const control = new MapStylePreferenceControl({
        mapStylePreferenceService: this.mapStylePreferenceService,
        preferencesUrl: this.config.mapPreferencesUrl,
      });
      this.mapBase.addControl(control, "top-right");
    }
  }
```

- [ ] **Step 5: Run tests and JS syntax checks**

Run:

```powershell
python -m unittest tests.test_map_style_preferences
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\services\MapStylePreferenceService.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\controls\MapStylePreferenceControl.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\unified_map_core.js
```

Expected: all pass.

- [ ] **Step 6: Commit frontend integration**

Run:

```powershell
git add netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js netbox_otnfaults/map_modes.py
git commit -m "feat: add map style preference control"
```

---

### Task 5: Final Verification And PLAN.md Status

**Files:**
- Modify: `PLAN.md`
- Test: all changed implementation files

- [ ] **Step 1: Update `PLAN.md` after implementation**

Add this section at the top after implementation is complete:

```markdown
## 2026-04-23 地图样式个人偏好

- [x] 增加按用户和地图模式保存的地图样式偏好模型、FilterSet 和迁移。
- [x] 增加插件内偏好 GET/POST 接口，并只允许读写当前用户配置。
- [x] 在统一地图模板注入当前用户样式偏好和保存接口 URL。
- [x] 增加前端样式应用服务，覆盖省界、站点、路径三类共享图层。
- [x] 增加地图内浮动设置面板，支持预览、恢复默认和保存为个人默认。
- [x] 运行源码级回归测试、Python 语法检查和 JavaScript 语法检查。
```

- [ ] **Step 2: Run final focused tests**

Run:

```powershell
python -m unittest tests.test_map_style_preferences
python -m unittest tests.test_statistics_cable_break_overview tests.test_map_framerate_toggle
```

Expected: all pass.

- [ ] **Step 3: Run final syntax checks**

Run:

```powershell
python -m py_compile .\netbox_otnfaults\models.py .\netbox_otnfaults\filtersets.py .\netbox_otnfaults\views.py .\netbox_otnfaults\urls.py .\netbox_otnfaults\map_modes.py .\netbox_otnfaults\services\map_preferences.py
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\services\MapStylePreferenceService.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\controls\MapStylePreferenceControl.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\unified_map_core.js
```

Expected: all pass.

- [ ] **Step 4: Run migration workflow when a NetBox runtime exists**

Run:

```powershell
python manage.py makemigrations netbox_otnfaults
python manage.py migrate
```

Expected: migration applies successfully. If this runtime is unavailable, record that `migrate` was not run.

- [ ] **Step 5: Final git checks and commit**

Run:

```powershell
git status --short
git diff --check
git add PLAN.md tests/test_map_style_preferences.py
git commit -m "test: verify map style preferences"
```

If `tests/test_map_style_preferences.py` is already committed and unchanged, commit only `PLAN.md`.

---

## Self-Review

- Spec coverage: the tasks cover the model, schema validation, current-user API, map context injection, shared layer style application, floating panel UI, and V1 exclusions.
- Scope: the plan does not implement fault marker styles, heatmap styles, viewport defaults, role defaults, named profiles, or import/export.
- Type consistency: Python helpers use `dict[str, Any]`; frontend uses `mapStylePreferences` and `mapPreferencesUrl`, matching template injection and `OTNMapConfig`.
- Runtime gap: this repository has no running NetBox environment. Source tests and syntax checks are required; `migrate` is required only when a NetBox runtime is available.
