# 态势大屏 V2 省界 GeoJSON 地图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让态势大屏 V2 停止加载 `china.pmtiles`，改为在深色 MapLibre 背景上加载并渲染现有省界 GeoJSON。

**Architecture:** Django 视图使用静态文件解析器把省界 URL 注入 V2 JSON 配置。V2 地图引擎只创建空背景 Style，在 `load` 事件中请求 GeoJSON、转换坐标并增加五个省界图层；V1 文件保持不变。

**Tech Stack:** Django 5、Django staticfiles、MapLibre GL JS、GeoJSON、Node.js `node:test`、Python `unittest`

---

## 文件结构

- Modify: `netbox_otnfaults/dashboard_v2_views.py` — 输出地图视角、字体和省界静态 URL，不再输出 PMTiles 底图配置。
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html` — 移除 PMTiles 脚本并把状态文案改为省界地图语义。
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js` — 纯背景地图、省界请求、坐标转换、图层注册和错误状态。
- Modify: `tests/test_dashboard_v2_shell.py` — 锁定模板、配置和源码隔离要求。
- Modify: `tests/dashboard_v2_map_engine.test.mjs` — 验证真实模块的省界加载行为。
- Modify: `PLAN.md` — 记录本阶段步骤和验证结果。

### Task 1: 锁定 V2 不再依赖 PMTiles

**Files:**
- Modify: `tests/test_dashboard_v2_shell.py`
- Modify: `netbox_otnfaults/dashboard_v2_views.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html`

- [ ] **Step 1: 编写失败的静态回归测试**

测试应断言模板不包含 `pmtiles.js`，视图使用 `static("netbox_otnfaults/data/中国_省.geojson")` 输出 `provinceGeoJsonUrl`，V2 地图源码不包含 `pmtiles.Protocol`、`pmtiles://`、`china_local` 或 `localTilesUrl`。

- [ ] **Step 2: 运行定向测试并确认按预期失败**

Run: `python -m unittest tests.test_dashboard_v2_shell -v`

Expected: FAIL，失败信息指出模板仍加载 `pmtiles.js` 或地图引擎仍包含 PMTiles 初始化。

- [ ] **Step 3: 最小化修改视图与模板**

视图配置改为：

```python
from django.templatetags.static import static

return {
    "mapCenter": plugin_settings.get("map_default_center", [104.0, 34.3]),
    "mapZoom": plugin_settings.get("map_default_zoom", 4.0),
    "mapPitch": plugin_settings.get("map_default_pitch", 32),
    "localGlyphsUrl": plugin_settings.get("local_glyphs_url", ""),
    "provinceGeoJsonUrl": static("netbox_otnfaults/data/中国_省.geojson"),
}
```

模板删除 PMTiles 脚本，并将“底图初始化中”改为“省界初始化中”。

- [ ] **Step 4: 暂不要求全部静态测试通过**

地图源码尚未改造，确认失败范围只剩 Task 2 的地图行为断言。

### Task 2: 用行为测试定义省界加载链路

**Files:**
- Modify: `tests/dashboard_v2_map_engine.test.mjs`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js`

- [ ] **Step 1: 重写 Fake MapLibre 和 fetch 测试桩**

`FakeMap` 增加 `addSource()`、`addLayer()`，测试状态记录请求 URL、Source 和图层顺序。示例 GeoJSON 使用一个 Polygon，并保留转换前坐标用于断言。

- [ ] **Step 2: 编写失败行为测试**

覆盖以下行为：

```javascript
assert.deepEqual(map.options.style.sources, {});
await map.handlers.load();
assert.equal(fetchCalls[0], '/static/netbox_otnfaults/data/中国_省.geojson');
assert.ok(map.sources.provinces);
assert.deepEqual(map.layers.map((layer) => layer.id), [
  'province-shadow',
  'province-extrusion',
  'province-border-glow-bottom',
  'province-border-top',
  'province-labels',
]);
assert.notDeepEqual(convertedCoordinate, originalCoordinate);
```

另写 HTTP 404、MapLibre 构造异常和 `error` 后迟到 `load` 不覆盖错误状态的测试。

- [ ] **Step 3: 运行 Node 测试并确认按预期失败**

Run: `node --test --experimental-test-isolation=none tests/dashboard_v2_map_engine.test.mjs`

Expected: FAIL，旧模块仍创建 PMTiles Source，且没有 `provinces` Source。

- [ ] **Step 4: 实现纯背景 Style 和坐标转换**

`buildStyle()` 只保留 `background` Layer和字体 URL。增加 V1 同口径的 `_transformLat`、`_transformLng`、`gcj02ToWgs84` 与 `convertGeoJsonCoords`，递归转换 Feature geometry coordinates。

- [ ] **Step 5: 实现省界 Source 与五个图层**

`loadProvinceLayer(map, url)` 请求并校验 GeoJSON，注册 `provinces` Source，按设计顺序添加五个图层。标签读取 `name`，使用 `Noto Sans SC Regular`，并过滤非省份边界名称。

- [ ] **Step 6: 实现异步状态和粘性错误**

地图 `load` 期间显示“省界加载中”，成功后显示“省界地图就绪”。fetch、JSON、MapLibre 和运行时错误统一显示“省界加载失败”，且 `hasLoadError` 为真时任何成功回调不得覆盖错误状态。

- [ ] **Step 7: 运行 Node 测试并确认通过**

Run: `node --test --experimental-test-isolation=none tests/dashboard_v2_map_engine.test.mjs`

Expected: PASS，0 failures。

### Task 3: 完成隔离回归和文档同步

**Files:**
- Modify: `tests/test_dashboard_v2_shell.py`
- Modify: `PLAN.md`
- Modify: `docs/superpowers/specs/2026-08-29-dashboard-v2-province-geojson-design.md`

- [ ] **Step 1: 运行 V2 Python 静态测试**

Run: `python -m unittest discover -s tests -p 'test_dashboard_v2_shell.py' -v`

Expected: PASS。

- [ ] **Step 2: 运行 V1 回归测试**

Run: `python -m unittest discover -s tests -p 'test_dashboard_situation_board.py' -v`

Run: `python -m unittest discover -s tests -p 'test_dashboard_pmtiles_topology.py' -v`

Expected: 两组测试均 PASS，证明 V1 页面与拓扑逻辑未改变。

- [ ] **Step 3: 运行语法检查**

Run: `python -m py_compile netbox_otnfaults/dashboard_v2_views.py`

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js`

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js`

Expected: 全部 exit 0。

- [ ] **Step 4: 检查 V1 隔离与工作区差异**

Run: `git diff -- netbox_otnfaults/dashboard_views.py netbox_otnfaults/templates/netbox_otnfaults/dashboard.html netbox_otnfaults/static/netbox_otnfaults/js/dashboard`

Expected: 无输出。

Run: `git diff --check`

Expected: exit 0。

- [ ] **Step 5: 更新计划状态**

将 `PLAN.md` 中本阶段任务标记为完成，并记录 V2 不再请求 `china.pmtiles`。根据项目约定不暂存、不提交。
