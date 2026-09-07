# 态势大屏新版外壳 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留旧态势大屏不变的前提下，新增 `/dashboard-v2/` 入口、常规屏31/69且左栏在4K封顶780px的左右布局，以及独立 MapLibre 底图初始化。

**Architecture:** 新版页面使用独立 Django view、模板、CSS 和 ES module JavaScript；只复用项目内的 MapLibre、PMTiles 第三方资源以及插件地图配置。模板通过 `json_script` 安全注入配置，地图模块不调用旧版 `DashboardApp`、`Panels`、`DirectingEngine`、`MapEngine` 或 `DashboardDataAPI`。

**Tech Stack:** Django 5、NetBox 4、Django templates、CSS Grid、MapLibre GL JS、PMTiles、原生 ES modules、Python unittest

**Workflow note:** 按仓库 `AGENTS.md`，直接在当前分支和工作区实施，不创建分支/worktree，不自动暂存或提交。

---

## 文件结构

- Create: `netbox_otnfaults/dashboard_v2_views.py` — 新版页面配置与页面视图。
- Create: `netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html` — 新版页面结构和安全配置载体。
- Create: `netbox_otnfaults/static/netbox_otnfaults/css/dashboard_v2.css` — 独立视觉令牌和31/69布局。
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js` — 独立 MapLibre/PMTiles 初始化与错误状态。
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js` — 时钟和地图启动协调。
- Create: `tests/test_dashboard_v2_shell.py` — 新入口、隔离、布局和地图初始化静态回归测试。
- Create: `tests/dashboard_v2_map_engine.test.mjs` — 实际执行地图模块的 Node 行为测试。
- Modify: `netbox_otnfaults/urls.py` — 注册 `/dashboard-v2/`。
- Modify: `netbox_otnfaults/navigation.py` — 增加“态势大屏（新版）”。
- Modify: `PLAN.md` — 登记本次实施步骤并在执行中更新状态。

### Task 1: 锁定新版入口与旧版隔离边界

**Files:**
- Create: `tests/test_dashboard_v2_shell.py`
- Modify: `PLAN.md`

- [ ] **Step 1: 在 `PLAN.md` 顶部登记未完成任务**

```markdown
## 2026-08-28 态势大屏新版第一阶段外壳

- [ ] 增加新版独立页面视图、路由和菜单入口，保持旧版入口不变。
- [ ] 增加新版常规屏31/69、4K左栏封顶780px的左右布局、现有标题和独立视觉样式。
- [ ] 增加新版 MapLibre/PMTiles 底图初始化、时钟与错误状态。
- [ ] 运行新版定向测试、旧版隔离回归、Python 编译和 JavaScript 语法检查。
```

- [ ] **Step 2: 创建入口和隔离失败测试**

在 `tests/test_dashboard_v2_shell.py` 写入：

```python
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"
VIEW_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_v2_views.py"
TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "dashboard_v2.html"
)
CSS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "css"
    / "dashboard_v2.css"
)
APP_JS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard_v2"
    / "app.js"
)
MAP_JS_PATH = APP_JS_PATH.with_name("map_engine.js")
OLD_TEMPLATE_PATH = TEMPLATE_PATH.with_name("dashboard.html")


class DashboardV2ShellTestCase(unittest.TestCase):
    def test_new_route_and_menu_are_parallel_to_legacy_dashboard(self) -> None:
        urls = URLS_PATH.read_text(encoding="utf-8")
        navigation = NAVIGATION_PATH.read_text(encoding="utf-8")

        self.assertIn("from . import dashboard_v2_views", urls)
        self.assertIn(
            "path('dashboard-v2/', dashboard_v2_views.DashboardV2PageView.as_view(), name='dashboard_v2')",
            urls,
        )
        self.assertIn(
            "path('dashboard/', dashboard_views.DashboardPageView.as_view(), name='dashboard')",
            urls,
        )
        self.assertIn("link='plugins:netbox_otnfaults:dashboard_v2'", navigation)
        self.assertIn("link_text='态势大屏（新版）'", navigation)
        self.assertIn("link='plugins:netbox_otnfaults:dashboard'", navigation)

    def test_new_page_has_its_own_view_template_and_assets(self) -> None:
        self.assertTrue(VIEW_PATH.exists())
        self.assertTrue(TEMPLATE_PATH.exists())
        self.assertTrue(CSS_PATH.exists())
        self.assertTrue(APP_JS_PATH.exists())
        self.assertTrue(MAP_JS_PATH.exists())

        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("netbox_otnfaults/css/dashboard_v2.css", template)
        self.assertIn("netbox_otnfaults/js/dashboard_v2/app.js", template)
        self.assertNotIn("netbox_otnfaults/css/dashboard.css", template)
        self.assertNotIn("js/dashboard/dashboard_app.js", template)
        self.assertNotIn("dashboard_data", template)

    def test_legacy_template_is_not_rewritten_as_v2(self) -> None:
        legacy = OLD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("dashboard_v2.css", legacy)
        self.assertNotIn("js/dashboard_v2/app.js", legacy)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试并确认因新版文件和入口不存在而失败**

Run:

```powershell
python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v
```

Expected: FAIL；报告 `dashboard_v2_views`、`dashboard-v2/` 或新版文件不存在。

### Task 2: 实现独立页面视图、路由和菜单入口

**Files:**
- Create: `netbox_otnfaults/dashboard_v2_views.py`
- Modify: `netbox_otnfaults/urls.py`
- Modify: `netbox_otnfaults/navigation.py`
- Test: `tests/test_dashboard_v2_shell.py`

- [ ] **Step 1: 创建带完整类型提示的新版页面视图**

创建 `netbox_otnfaults/dashboard_v2_views.py`：

```python
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import PermissionRequiredMixin


def _get_dashboard_v2_config() -> dict[str, Any]:
    plugin_settings: dict[str, Any] = settings.PLUGINS_CONFIG.get("netbox_otnfaults", {})
    return {
        "mapCenter": plugin_settings.get("map_default_center", [104.0, 34.3]),
        "mapZoom": plugin_settings.get("map_default_zoom", 4.0),
        "mapPitch": plugin_settings.get("map_default_pitch", 32),
        "useLocalBasemap": plugin_settings.get("use_local_basemap", False),
        "localTilesUrl": plugin_settings.get("local_tiles_url", ""),
        "localGlyphsUrl": plugin_settings.get("local_glyphs_url", ""),
    }


class DashboardV2PageView(PermissionRequiredMixin, View):
    permission_required = "netbox_otnfaults.view_otnfault"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            "netbox_otnfaults/dashboard_v2.html",
            {"dashboard_v2_config": _get_dashboard_v2_config()},
        )
```

- [ ] **Step 2: 注册并行路由**

在 `netbox_otnfaults/urls.py` 的 imports 增加：

```python
from . import dashboard_v2_views
```

在旧大屏路由之后增加：

```python
path('dashboard-v2/', dashboard_v2_views.DashboardV2PageView.as_view(), name='dashboard_v2'),
```

不得修改现有 `dashboard` 和 `dashboard_data` 两条路由。

- [ ] **Step 3: 增加新版菜单项**

在 `netbox_otnfaults/navigation.py` 的旧“态势大屏”菜单项之后增加：

```python
PluginMenuItem(
    link='plugins:netbox_otnfaults:dashboard_v2',
    link_text='态势大屏（新版）',
    permissions=['netbox_otnfaults.view_otnfault'],
),
```

- [ ] **Step 4: 运行入口测试，确认仅因模板和静态资源尚未创建而失败**

Run:

```powershell
python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v
```

Expected: 路由与菜单断言 PASS；文件存在性断言仍 FAIL。

### Task 3: 建立新版页面结构和31/69视觉布局

**Files:**
- Create: `netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html`
- Create: `netbox_otnfaults/static/netbox_otnfaults/css/dashboard_v2.css`
- Modify: `tests/test_dashboard_v2_shell.py`

- [ ] **Step 1: 增加模板和布局失败测试**

在 `DashboardV2ShellTestCase` 增加：

```python
def test_template_keeps_title_and_exposes_two_column_shell(self) -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    self.assertIn("中交信通网络运行态势图", template)
    self.assertIn('id="dashboard-v2-header"', template)
    self.assertIn('id="dashboard-v2-information"', template)
    self.assertIn('id="dashboard-v2-map-stage"', template)
    self.assertIn('id="dashboard-v2-map"', template)
    self.assertIn('id="dashboard-v2-map-status"', template)
    self.assertIn('{{ dashboard_v2_config|json_script:"dashboard-v2-config" }}', template)

def test_stylesheet_uses_31_69_grid_and_existing_visual_tokens(self) -> None:
    css = CSS_PATH.read_text(encoding="utf-8")

    self.assertIn("grid-template-columns: clamp(360px, 31%, 780px) minmax(0, 1fr);", css)
    self.assertIn("gap: 16px;", css)
    self.assertIn("--bg-deep: #060a14;", css)
    self.assertIn("--accent: #00d2ff;", css.lower())
    self.assertIn("'Rajdhani'", css)
    self.assertIn("'JetBrains Mono'", css)
    self.assertIn("'Noto Sans SC'", css)
    self.assertIn("max-width: 780px;", css)
```

- [ ] **Step 2: 创建独立 HTML 页面骨架**

创建 `netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html`，完整内容为：

```html
{% load static %}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>中交信通网络运行态势图</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500&family=Noto+Sans+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
  <link href="{% static 'netbox_otnfaults/lib/maplibre-gl.css' %}" rel="stylesheet">
  <script src="{% static 'netbox_otnfaults/lib/maplibre-gl.js' %}"></script>
  <script src="{% static 'netbox_otnfaults/lib/pmtiles.js' %}"></script>
  <link href="{% static 'netbox_otnfaults/css/dashboard_v2.css' %}" rel="stylesheet">
</head>
<body>
<header id="dashboard-v2-header">
  <div class="dashboard-v2-header-side">
    <span class="dashboard-v2-status-dot" id="dashboard-v2-status-dot"></span>
    <span id="dashboard-v2-status-text">底图初始化中...</span>
  </div>
  <div class="dashboard-v2-heading">
    <h1><span aria-hidden="true">◆</span> 中交信通网络运行态势图 <span aria-hidden="true">◆</span></h1>
    <p>自动化监控 · 智能播控</p>
  </div>
  <div class="dashboard-v2-clock">
    <div id="dashboard-v2-date"></div>
    <div id="dashboard-v2-time"></div>
  </div>
</header>

<main id="dashboard-v2-main">
  <aside id="dashboard-v2-information" aria-label="信息显示区">
    <div class="dashboard-v2-panel-heading">信息显示区</div>
    <div class="dashboard-v2-empty-state">等待功能接入</div>
  </aside>
  <section id="dashboard-v2-map-stage" aria-label="地图区">
    <div id="dashboard-v2-map"></div>
    <div id="dashboard-v2-map-status" role="status">底图初始化中...</div>
  </section>
</main>

{{ dashboard_v2_config|json_script:"dashboard-v2-config" }}
<script type="module" src="{% static 'netbox_otnfaults/js/dashboard_v2/app.js' %}"></script>
</body>
</html>
```

- [ ] **Step 3: 创建独立视觉样式**

创建 `netbox_otnfaults/static/netbox_otnfaults/css/dashboard_v2.css`，完整内容为：

```css
:root {
  --bg-deep: #060a14;
  --bg-primary: #0a0e1a;
  --bg-card: rgba(12, 20, 40, 0.85);
  --border-subtle: rgba(0, 210, 255, 0.12);
  --border-glow: rgba(0, 210, 255, 0.3);
  --text-primary: #e0e8f0;
  --text-secondary: rgba(180, 200, 220, 0.7);
  --accent: #00d2ff;
  --font-title: 'Rajdhani', 'Noto Sans SC', sans-serif;
  --font-data: 'JetBrains Mono', Consolas, monospace;
  --font-body: 'Noto Sans SC', sans-serif;
  --header-height: 64px;
}

* { box-sizing: border-box; }
html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
body { background: var(--bg-deep); color: var(--text-primary); font-family: var(--font-body); }

#dashboard-v2-header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 10;
  height: var(--header-height);
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(180px, 1fr);
  align-items: center;
  padding: 0 24px;
  background: linear-gradient(180deg, rgba(8, 14, 30, 0.98), rgba(6, 10, 20, 0.92));
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
}

.dashboard-v2-header-side {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font: 12px var(--font-data);
}

.dashboard-v2-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.dashboard-v2-status-dot.is-error {
  background: #ff1e1e;
  box-shadow: 0 0 8px #ff1e1e;
}

.dashboard-v2-heading { text-align: center; }
.dashboard-v2-heading h1 {
  margin: 0;
  color: #fff;
  font: 700 22px var(--font-title);
  letter-spacing: 6px;
  text-shadow: 0 0 20px rgba(0, 210, 255, 0.4);
}
.dashboard-v2-heading h1 span { color: var(--accent); font-size: 12px; }
.dashboard-v2-heading p {
  margin: 2px 0 0;
  color: rgba(140, 160, 180, 0.65);
  font-size: 11px;
  letter-spacing: 4px;
}

.dashboard-v2-clock { text-align: right; font-family: var(--font-data); }
#dashboard-v2-date { color: var(--text-secondary); font-size: 11px; }
#dashboard-v2-time { color: var(--accent); font-size: 20px; letter-spacing: 2px; }

#dashboard-v2-main {
  position: fixed;
  inset: var(--header-height) 0 0;
  display: grid;
  grid-template-columns: clamp(360px, 31%, 780px) minmax(0, 1fr);
  gap: 16px;
  padding: 16px;
}

#dashboard-v2-information {
  width: 100%;
  max-width: 780px;
  min-width: 0;
  overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: inset 0 0 24px rgba(0, 210, 255, 0.03);
}

#dashboard-v2-map-stage {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-primary);
}
#dashboard-v2-map { position: absolute; inset: 0; }
#dashboard-v2-map-status {
  position: absolute;
  inset: auto 16px 16px;
  z-index: 2;
  padding: 8px 12px;
  color: var(--text-secondary);
  background: rgba(6, 10, 20, 0.82);
  border: 1px solid var(--border-glow);
  border-radius: 6px;
  font: 12px var(--font-data);
}
#dashboard-v2-map-status.is-ready { display: none; }
#dashboard-v2-map-status.is-error { color: #ffb4b4; border-color: rgba(255, 30, 30, 0.45); }

.dashboard-v2-panel-heading {
  padding: 14px 16px;
  color: var(--accent);
  border-bottom: 1px solid var(--border-subtle);
  font: 600 16px var(--font-title);
  letter-spacing: 2px;
}

.dashboard-v2-empty-state {
  height: calc(100% - 49px);
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  font-size: 13px;
}

@media (min-width: 2500px) {
  :root { --header-height: 76px; }
  #dashboard-v2-main { gap: 24px; padding: 24px; }
}
```

禁止引用旧版 `dashboard.css`。

- [ ] **Step 4: 运行布局测试**

Run:

```powershell
python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v
```

Expected: 模板与布局测试 PASS；JS 文件存在性测试仍 FAIL。

### Task 4: 初始化独立 MapLibre/PMTiles 底图

**Files:**
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js`
- Create: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js`
- Create: `tests/dashboard_v2_map_engine.test.mjs`
- Modify: `tests/test_dashboard_v2_shell.py`

- [ ] **Step 1: 增加地图初始化与错误状态失败测试**

在 `DashboardV2ShellTestCase` 增加：

```python
def test_map_module_is_isolated_and_initializes_pmtiles_basemap(self) -> None:
    source = MAP_JS_PATH.read_text(encoding="utf-8")

    self.assertIn("export function initializeDashboardV2Map", source)
    self.assertIn("new pmtiles.Protocol()", source)
    self.assertIn("maplibregl.addProtocol('pmtiles'", source)
    self.assertIn("'source-layer': 'water'", source)
    self.assertIn("'source-layer': 'transportation'", source)
    self.assertIn("'source-layer': 'boundary'", source)
    self.assertIn("'source-layer': 'place'", source)
    self.assertIn("new maplibregl.Map({", source)
    self.assertIn("container: 'dashboard-v2-map'", source)
    self.assertIn("dragPan.disable()", source)
    self.assertIn("scrollZoom.disable()", source)
    self.assertIn("map.on('error'", source)
    self.assertNotIn("window.MapEngine", source)
    self.assertNotIn("DashboardDataAPI", source)
    self.assertNotIn("fetch(", source)

def test_app_reads_json_config_and_starts_clock_and_map(self) -> None:
    source = APP_JS_PATH.read_text(encoding="utf-8")

    self.assertIn("JSON.parse(configNode.textContent)", source)
    self.assertIn("initializeDashboardV2Map(config", source)
    self.assertIn("setInterval(updateClock, 1000)", source)
    self.assertNotIn("dashboard_data", source)
    self.assertNotIn("fetch(", source)
```

- [ ] **Step 2: 实现独立地图模块**

创建 `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js`，包含以下接口和行为：

```javascript
let pmtilesProtocolRegistered = false;

function resolveUrl(url) {
  return new URL(url, window.location.origin).href;
}

function setMapStatus(message, state) {
  const status = document.getElementById('dashboard-v2-map-status');
  const dot = document.getElementById('dashboard-v2-status-dot');
  const text = document.getElementById('dashboard-v2-status-text');
  if (status) {
    status.textContent = message;
    status.className = state ? `is-${state}` : '';
  }
  if (text) text.textContent = message;
  if (dot) dot.classList.toggle('is-error', state === 'error');
}

function buildStyle(config) {
  const glyphs = config.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf';
  if (!config.useLocalBasemap) {
    return {
      version: 8,
      glyphs,
      sources: {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#060a14' } }],
    };
  }
  if (!config.localTilesUrl) throw new Error('本地底图已启用，但未配置瓦片地址');
  return {
    version: 8,
    glyphs,
    sources: {
      china_local: {
        type: 'vector',
        url: `pmtiles://${resolveUrl(config.localTilesUrl)}`,
        attribution: '© OpenStreetMap',
      },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#060a14' } },
      {
        id: 'landuse-base',
        type: 'fill',
        source: 'china_local',
        'source-layer': 'landuse',
        paint: { 'fill-color': '#0f172a' },
      },
      {
        id: 'landuse-green',
        type: 'fill',
        source: 'china_local',
        'source-layer': 'landuse',
        filter: ['in', 'class', 'park', 'grass', 'wood', 'scrub'],
        paint: { 'fill-color': '#1e293b', 'fill-opacity': 0.3 },
      },
      {
        id: 'water',
        type: 'fill',
        source: 'china_local',
        'source-layer': 'water',
        paint: { 'fill-color': '#020617' },
      },
      {
        id: 'roads-casing',
        type: 'line',
        source: 'china_local',
        'source-layer': 'transportation',
        minzoom: 5,
        paint: { 'line-color': '#334155', 'line-width': { stops: [[5, 1], [10, 4], [15, 8]] } },
      },
      {
        id: 'roads-inner',
        type: 'line',
        source: 'china_local',
        'source-layer': 'transportation',
        minzoom: 5,
        paint: { 'line-color': '#1e293b', 'line-width': { stops: [[5, 0.5], [10, 2.5], [15, 6]] } },
      },
      {
        id: 'boundary',
        type: 'line',
        source: 'china_local',
        'source-layer': 'boundary',
        paint: { 'line-color': '#475569', 'line-width': 1, 'line-dasharray': [2, 2] },
      },
      {
        id: 'place-label',
        type: 'symbol',
        source: 'china_local',
        'source-layer': 'place',
        minzoom: 3,
        layout: {
          'text-field': ['coalesce', ['get', 'name:zh'], ['get', 'name']],
          'text-size': { stops: [[3, 10], [8, 14]] },
          'text-font': ['Open Sans Regular'],
          'text-max-width': 8,
        },
        paint: {
          'text-color': '#94a3b8',
          'text-halo-color': '#0f172a',
          'text-halo-width': 2,
        },
      },
    ],
  };
}

export function initializeDashboardV2Map(config = {}) {
  if (typeof maplibregl === 'undefined') {
    setMapStatus('底图加载失败：MapLibre 未加载', 'error');
    return null;
  }
  try {
    if (config.useLocalBasemap) {
      if (typeof pmtiles === 'undefined') throw new Error('PMTiles 未加载');
      if (!pmtilesProtocolRegistered) {
        const protocol = new pmtiles.Protocol();
        maplibregl.addProtocol('pmtiles', protocol.tile);
        pmtilesProtocolRegistered = true;
      }
    }
    const map = new maplibregl.Map({
      container: 'dashboard-v2-map',
      style: buildStyle(config),
      center: config.mapCenter || [104.0, 34.3],
      zoom: Number(config.mapZoom ?? 4.0),
      pitch: Number(config.mapPitch ?? 32),
      bearing: 0,
      attributionControl: false,
      antialias: true,
    });
    map.dragRotate.disable();
    map.touchZoomRotate.disable();
    map.scrollZoom.disable();
    map.boxZoom.disable();
    map.doubleClickZoom.disable();
    map.dragPan.disable();
    map.on('load', () => setMapStatus('底图在线', 'ready'));
    map.on('error', () => setMapStatus('底图加载失败', 'error'));
    return map;
  } catch (error) {
    setMapStatus(`底图加载失败：${error instanceof Error ? error.message : '未知错误'}`, 'error');
    return null;
  }
}
```

- [ ] **Step 3: 实现应用入口和时钟**

创建 `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js`：

```javascript
import { initializeDashboardV2Map } from './map_engine.js';

function updateClock() {
  const now = new Date();
  const date = document.getElementById('dashboard-v2-date');
  const time = document.getElementById('dashboard-v2-time');
  if (date) {
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    date.textContent = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, '0')}/${String(now.getDate()).padStart(2, '0')} ${weekdays[now.getDay()]}`;
  }
  if (time) {
    time.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
  const configNode = document.getElementById('dashboard-v2-config');
  const config = configNode ? JSON.parse(configNode.textContent) : {};
  initializeDashboardV2Map(config);
});
```

- [ ] **Step 4: 运行新版定向测试和 JavaScript 语法检查**

Run:

```powershell
python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v
node --test --experimental-test-isolation=none tests\dashboard_v2_map_engine.test.mjs
node --check netbox_otnfaults\static\netbox_otnfaults\js\dashboard_v2\map_engine.js
node --check netbox_otnfaults\static\netbox_otnfaults\js\dashboard_v2\app.js
```

Expected: Python静态测试和5项地图行为测试全部 PASS；其中应验证旧开关关闭但 `localTilesUrl` 有效时仍加载原 PMTiles 地址；两个脚本语法检查退出码均为0。

### Task 5: 回归验证与计划收尾

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 编译新增及受影响 Python 文件**

Run:

```powershell
python -m py_compile netbox_otnfaults\dashboard_v2_views.py netbox_otnfaults\urls.py netbox_otnfaults\navigation.py
```

Expected: 退出码0，无输出。

- [ ] **Step 2: 运行新版和旧版隔离回归测试**

Run:

```powershell
python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v
node --test --experimental-test-isolation=none tests\dashboard_v2_map_engine.test.mjs
python -m unittest tests.test_dashboard_situation_board -v
python -m unittest tests.test_dashboard_pmtiles_topology -v
```

Expected: 三组测试全部 PASS。不要把项目当前已知的 `test_dashboard_fault_focus_zoom` 静态断言失败归因于本次新增模块；本计划不修改该旧版测试或实现。

- [ ] **Step 3: 检查旧大屏文件未被意外修改**

Run:

```powershell
git diff -- netbox_otnfaults\dashboard_views.py netbox_otnfaults\templates\netbox_otnfaults\dashboard.html netbox_otnfaults\static\netbox_otnfaults\css\dashboard.css netbox_otnfaults\static\netbox_otnfaults\js\dashboard
```

Expected: 无输出。

- [ ] **Step 4: 检查全部差异和空白错误**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` 无输出；`git status --short` 只包含设计文档、计划、`PLAN.md`、新版文件以及预期的 `urls.py`、`navigation.py` 修改。

- [ ] **Step 5: 更新 `PLAN.md` 状态**

将本次四项任务由 `- [ ]` 更新为 `- [x]`；不执行 `git add`、`git commit`、推送或创建 Pull Request。
