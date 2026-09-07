# 态势大屏 V2 仿照一张图底图加载架构 PRD

## 1. 背景与问题
态势大屏 V2 初始化时提示 `地球模式加载失败：Bad response code: 404`。
原因在于 V2 之前强制请求了 `china_local` 本地瓦片服务（`/maps/china.pmtiles`），而 NetBox 默认环境和一张图模块使用的是 `/map-assets/alidade_smooth_dark_local.json` 矢量底图样式。

## 2. 解决方案与技术实现
仿照一张图模块（`NetBoxMapBase`）重构态势大屏 V2 的底图加载机制：
1. **配置对齐**：
   - 在 [dashboard_v2_views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/dashboard_v2_views.py) 中注入 `useLocalBasemap: plugin_settings.get("use_local_basemap", False)`。
2. **双模式底图支持**：
   - **默认模式（`useLocalBasemap=False`）**：
     异步拉取 `/map-assets/alidade_smooth_dark_local.json` 深色样式，解析 `sprite`、`glyphs` 与 `TileJSON` 瓦片为绝对路径，并配置 `projection: { type: 'globe' }` 和深色大气层背景 `sky`。
   - **本地底图模式（`useLocalBasemap=True`）**：
     加载本地 `local_tiles_url`（如 PMTiles）矢量底图。
3. **应用挂载**：
   - [app.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js) 异步等待地图与样式加载完成后挂载调试面板及后续功能。

## 3. 测试与验证
- `tests/test_dashboard_v2_shell.py`：8 项 Python 契约测试全部通过。
- `tests/dashboard_v2_*.test.mjs`：15 项 Node.js 单元测试全部通过。
