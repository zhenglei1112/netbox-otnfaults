# 地图样式偏好实现计划

> **致智能体工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现本计划。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 在统一地图窗口中构建按用户保存的地图样式偏好功能，覆盖省界、NetBox 站点和 OTN 路径图层。

**架构：** 新增插件专属 `OtnMapPreference` 模型，以 `user + map_mode` 为唯一键，通过小型服务模块验证带版本号的 JSON 配置。地图视图将当前用户的归一化偏好注入 `window.OTNMapConfig`；前端共享服务将样式应用到 MapLibre 图层，浮动控件支持预览、重置和保存当前用户的默认设置。

**技术栈：** Django 5 / NetBox 4 插件模型与视图、`JsonResponse`、MapLibre GL JS、Bootstrap 5、源码级 Python `unittest` 测试。

---

## 文件结构

- 新建 `netbox_otnfaults/services/map_preferences.py`：默认配置、校验、归一化、当前用户查询/保存辅助函数及模板上下文构建器。
- 修改 `netbox_otnfaults/models.py`：新增 `OtnMapPreference(NetBoxModel)`。
- 修改 `netbox_otnfaults/filtersets.py`：新增 `OtnMapPreferenceFilterSet`。
- 修改 `netbox_otnfaults/urls.py`：新增插件内 GET/POST 偏好接口。
- 修改 `netbox_otnfaults/views.py`：新增 `MapPreferenceView` 并在统一地图视图中注入偏好上下文。
- 修改 `netbox_otnfaults/map_modes.py`：在统一地图模式中加载偏好服务/控件 JS。
- 修改 `netbox_otnfaults/templates/netbox_otnfaults/unified_map.html`：暴露 `mapStylePreferences` 和 `mapPreferencesUrl`。
- 新建 `netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js`：将归一化样式应用到省界/站点/路径图层。
- 新建 `netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js`：浮动设置面板，支持预览/恢复默认/保存操作。
- 修改 `netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js`：在共享图层之后实例化服务并注册控件。
- 新建 `tests/test_map_style_preferences.py`：源码级回归覆盖。
- 如环境中可用 NetBox/Django 导入，则通过 `makemigrations` 添加迁移 `netbox_otnfaults/migrations/0054_otnmappreference.py`。

---

### 任务 1：契约源码测试

**文件：**
- 新建：`tests/test_map_style_preferences.py`
- 参考：`docs/superpowers/specs/2026-04-23-map-style-preferences-design.md`

- [ ] **步骤 1：编写失败的源码测试**

新建 `tests/test_map_style_preferences.py`：

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

- [ ] **步骤 2：运行失败的测试**

运行：`python -m unittest tests.test_map_style_preferences`

预期结果：失败，因为 `OtnMapPreference`、服务、接口和前端文件尚不存在。

- [ ] **步骤 3：提交失败的测试**

运行：

```powershell
git add tests/test_map_style_preferences.py
git commit -m "test: cover map style preference contract"
```

---

### 任务 2：后端模型、FilterSet 与服务

**文件：**
- 修改：`netbox_otnfaults/models.py`
- 修改：`netbox_otnfaults/filtersets.py`
- 新建：`netbox_otnfaults/services/map_preferences.py`
- 新建：`netbox_otnfaults/migrations/0054_otnmappreference.py`
- 测试：`tests/test_map_style_preferences.py`

- [ ] **步骤 1：添加 `OtnMapPreference`**

在 `netbox_otnfaults/models.py` 中，于 `OtnPath` 之后添加以下类：

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

- [ ] **步骤 2：添加 `OtnMapPreferenceFilterSet`**

在 `netbox_otnfaults/filtersets.py` 中导入 `OtnMapPreference` 并添加：

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

- [ ] **步骤 3：创建 `map_preferences.py`**

新建 `netbox_otnfaults/services/map_preferences.py`，包含默认配置、类型/限制映射及以下公共函数：

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

使用 `docs/superpowers/specs/2026-04-23-map-style-preferences-design.md` 中的配置模式。`save_user_map_style_config()` 必须调用 `OtnMapPreference.objects.update_or_create(user=user, map_mode=map_mode, defaults={...})`；不接受来自输入的用户 ID。

- [ ] **步骤 4：运行源码测试**

运行：`python -m unittest tests.test_map_style_preferences.MapStylePreferenceSourceTestCase.test_model_filterset_service_and_endpoint_contract`

预期结果：仅在缺失的接口/视图集成部分失败；模型、FilterSet 和服务的断言通过。

- [ ] **步骤 5：生成迁移**

在 NetBox 运行环境中执行：`python manage.py makemigrations netbox_otnfaults`

预期结果：`netbox_otnfaults/migrations/0054_otnmappreference.py` 已创建。

如果本仓库无法导入 NetBox 设置模块，创建等效的手动迁移并通过以下命令验证语法：

```powershell
python -m py_compile .\netbox_otnfaults\models.py .\netbox_otnfaults\filtersets.py .\netbox_otnfaults\services\map_preferences.py
```

- [ ] **步骤 6：提交后端模型和服务**

运行：

```powershell
git add netbox_otnfaults/models.py netbox_otnfaults/filtersets.py netbox_otnfaults/services/map_preferences.py netbox_otnfaults/migrations/0054_otnmappreference.py
git commit -m "feat: add map style preference model"
```

---

### 任务 3：接口与模板上下文

**文件：**
- 修改：`netbox_otnfaults/views.py`
- 修改：`netbox_otnfaults/urls.py`
- 修改：`netbox_otnfaults/templates/netbox_otnfaults/unified_map.html`
- 测试：`tests/test_map_style_preferences.py`

- [ ] **步骤 1：添加偏好服务导入**

在 `netbox_otnfaults/views.py` 中添加：

```python
from .services.map_preferences import (
    build_map_preference_context,
    get_user_map_style_config,
    save_user_map_style_config,
)
```

- [ ] **步骤 2：添加 `MapPreferenceView`**

在 `netbox_otnfaults/views.py` 的地图视图附近添加：

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

- [ ] **步骤 3：添加 URL 和上下文注入**

在 `netbox_otnfaults/urls.py` 的其他地图 URL 附近添加：

```python
path('map/preferences/<str:map_mode>/', views.MapPreferenceView.as_view(), name='map_preferences'),
```

在地图渲染上下文中添加：

```python
**build_map_preference_context(request, 'fault'),
**build_map_preference_context(request, 'statistics_cable_break'),
**build_map_preference_context(request, map_mode),
```

第一个用于 `OtnFaultGlobeMapView`，第二个用于 `StatisticsCableBreakMapView`，第三个用于 `LocationMapView`。

- [ ] **步骤 4：注入前端配置**

在 `unified_map.html` 的 `window.OTNMapConfig` 内添加：

```javascript
    mapStylePreferences: {{ map_style_preferences|safe }},
    mapPreferencesUrl: '{{ map_preferences_url|escapejs }}',
```

- [ ] **步骤 5：运行测试和语法检查**

运行：

```powershell
python -m unittest tests.test_map_style_preferences.MapStylePreferenceSourceTestCase.test_model_filterset_service_and_endpoint_contract
python -m py_compile .\netbox_otnfaults\views.py .\netbox_otnfaults\urls.py
```

预期结果：测试通过；语法检查通过。

- [ ] **步骤 6：提交接口和上下文**

运行：

```powershell
git add netbox_otnfaults/views.py netbox_otnfaults/urls.py netbox_otnfaults/templates/netbox_otnfaults/unified_map.html
git commit -m "feat: expose map style preference endpoint"
```

---

### 任务 4：前端样式服务与控件

**文件：**
- 新建：`netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js`
- 新建：`netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js`
- 修改：`netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js`
- 修改：`netbox_otnfaults/map_modes.py`
- 测试：`tests/test_map_style_preferences.py`

- [ ] **步骤 1：创建 `MapStylePreferenceService.js`**

实现一个全局 `MapStylePreferenceService` 类，包含：

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

实现必须对以下图层 ID 调用 `setPaintProperty`、`setLayoutProperty` 和 `setLayerZoomRange`：`user-geojson-fill`、`user-geojson-line`、`netbox-sites-layer`、`netbox-sites-labels`、`otn-paths-layer`、`otn-paths-highlight-outline`、`otn-paths-highlight-layer`。

- [ ] **步骤 2：创建 `MapStylePreferenceControl.js`**

实现一个全局 `MapStylePreferenceControl`，包含 MapLibre 的 `onAdd()` / `onRemove()`。必须渲染一个右侧浮动面板，标题为 `我的地图样式`，并包含 `应用预览`、`恢复默认`、`保存为我的默认` 三个按钮。

保存方法必须发送 POST 请求：

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

控件必须仅收集和保存 `province`、`sites` 和 `paths` 三个组。

- [ ] **步骤 3：在地图模式中加载资源**

在 `map_modes.py` 中，向 `fault`、`statistics_cable_break`、`location`、`path` 和 `pathgroup` 添加：

```python
'services/MapStylePreferenceService.js',
'controls/MapStylePreferenceControl.js',
```

服务放在控件之前。

- [ ] **步骤 4：在 `OTNMapCore` 中注册服务和控件**

在 `OTNMapCore.constructor` 中添加：

```javascript
    this.mapStylePreferenceService = null;
```

在 `this._initSharedLayers();` 之后调用：

```javascript
      this._initMapStylePreferences();
```

添加：

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

- [ ] **步骤 5：运行测试和 JS 语法检查**

运行：

```powershell
python -m unittest tests.test_map_style_preferences
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\services\MapStylePreferenceService.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\controls\MapStylePreferenceControl.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\unified_map_core.js
```

预期结果：全部通过。

- [ ] **步骤 6：提交前端集成**

运行：

```powershell
git add netbox_otnfaults/static/netbox_otnfaults/js/services/MapStylePreferenceService.js netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js netbox_otnfaults/static/netbox_otnfaults/js/unified_map_core.js netbox_otnfaults/map_modes.py
git commit -m "feat: add map style preference control"
```

---

### 任务 5：最终验证与 PLAN.md 状态

**文件：**
- 修改：`PLAN.md`
- 测试：所有已修改的实现文件

- [ ] **步骤 1：实现完成后更新 `PLAN.md`**

实现完成后在顶部添加以下部分：

```markdown
## 2026-04-23 地图样式个人偏好

- [x] 增加按用户和地图模式保存的地图样式偏好模型、FilterSet 和迁移。
- [x] 增加插件内偏好 GET/POST 接口，并只允许读写当前用户配置。
- [x] 在统一地图模板注入当前用户样式偏好和保存接口 URL。
- [x] 增加前端样式应用服务，覆盖省界、站点、路径三类共享图层。
- [x] 增加地图内浮动设置面板，支持预览、恢复默认和保存为个人默认。
- [x] 运行源码级回归测试、Python 语法检查和 JavaScript 语法检查。
```

- [ ] **步骤 2：运行最终聚焦测试**

运行：

```powershell
python -m unittest tests.test_map_style_preferences
python -m unittest tests.test_statistics_cable_break_overview tests.test_map_framerate_toggle
```

预期结果：全部通过。

- [ ] **步骤 3：运行最终语法检查**

运行：

```powershell
python -m py_compile .\netbox_otnfaults\models.py .\netbox_otnfaults\filtersets.py .\netbox_otnfaults\views.py .\netbox_otnfaults\urls.py .\netbox_otnfaults\map_modes.py .\netbox_otnfaults\services\map_preferences.py
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\services\MapStylePreferenceService.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\controls\MapStylePreferenceControl.js
node --check .\netbox_otnfaults\static\netbox_otnfaults\js\unified_map_core.js
```

预期结果：全部通过。

- [ ] **步骤 4：在 NetBox 运行环境存在时执行迁移工作流**

运行：

```powershell
python manage.py makemigrations netbox_otnfaults
python manage.py migrate
```

预期结果：迁移成功应用。如果运行环境不可用，记录 `migrate` 未执行。

- [ ] **步骤 5：最终 git 检查并提交**

运行：

```powershell
git status --short
git diff --check
git add PLAN.md tests/test_map_style_preferences.py
git commit -m "test: verify map style preferences"
```

如果 `tests/test_map_style_preferences.py` 已提交且未更改，则仅提交 `PLAN.md`。

---

## 自审

- 规格覆盖：任务覆盖了模型、配置模式验证、当前用户 API、地图上下文注入、共享图层样式应用、浮动面板 UI 和 V1 排除项。
- 范围：本计划不实现故障标记样式、热力图样式、视窗默认值、角色默认值、命名配置文件或导入/导出功能。
- 类型一致性：Python 辅助函数使用 `dict[str, Any]`；前端使用 `mapStylePreferences` 和 `mapPreferencesUrl`，与模板注入和 `OTNMapConfig` 一致。
- 运行环境差异：本仓库没有运行中的 NetBox 环境。源码测试和语法检查是必须的；`migrate` 仅在 NetBox 运行环境可用时才需执行。
