# 态势大屏 V2 站点与路径显示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在 V2 省界地图上增加 V1 同口径的站点、PMTiles 基础路径和活动故障路径覆盖，并每 30 秒刷新动态数据。

**Architecture:** V2 视图注入现有 dashboard_data URL 和 otn_paths_pmtiles_url；独立 data_service.js 获取并裁剪动态数据；V2 map_engine.js 负责 PMTiles 路径协议、站点/故障路径 Source 与固定图层顺序；app.js 负责轮询协调。V1 文件不修改。

**Tech Stack:** Django 5、MapLibre GL JS、PMTiles、GeoJSON、ES modules、Node.js node:test、Python unittest

---

## 文件结构

- Modify: netbox_otnfaults/dashboard_v2_views.py — 注入数据 URL、路径 PMTiles URL 和刷新周期。
- Modify: netbox_otnfaults/templates/netbox_otnfaults/dashboard_v2.html — 加载 PMTiles 库，仅供路径 Source 使用。
- Create: netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/data_service.js — 获取并标准化站点与故障路径。
- Modify: netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/map_engine.js — 基础路径、站点、故障路径和固定图层顺序。
- Modify: netbox_otnfaults/static/netbox_otnfaults/js/dashboard_v2/app.js — 首次请求、30 秒轮询和状态协调。
- Modify: tests/test_dashboard_v2_shell.py — 配置、模板和应用入口静态契约。
- Modify: tests/dashboard_v2_map_engine.test.mjs — 地图行为测试。
- Create: tests/dashboard_v2_data_service.test.mjs — 数据服务行为测试。
- Modify: PLAN.md — 本阶段追踪。

### Task 1: 配置与页面依赖

- [ ] 在 tests/test_dashboard_v2_shell.py 中先增加失败断言：视图导入 reverse，配置含 dataUrl、otnPathsPmtilesUrl、refreshInterval=30000，不含 localTilesUrl；模板含 pmtiles.js，但 V2 源码不含 china.pmtiles 或 china_local。
- [ ] 运行 python -m unittest tests.test_dashboard_v2_shell -v，确认失败原因是新配置和脚本尚未存在。
- [ ] 修改 dashboard_v2_views.py，使用 reverse("plugins:netbox_otnfaults:dashboard_data")，读取 otn_paths_pmtiles_url，并输出 30000。
- [ ] 修改 dashboard_v2.html，重新加载 pmtiles.js。
- [ ] 再次运行静态测试，确认只剩后续数据服务/地图入口断言失败。

### Task 2: 独立动态数据服务

- [ ] 创建 tests/dashboard_v2_data_service.test.mjs，先定义三个失败行为：成功响应映射为 {sites, faultPaths}；HTTP 503 抛出含状态的错误；非对象 JSON 抛出格式错误。
- [ ] 运行 node --test --experimental-test-isolation=none tests/dashboard_v2_data_service.test.mjs，确认模块不存在或导出缺失导致 RED。
- [ ] 创建 data_service.js，导出 fetchDashboardMapData(dataUrl)：校验地址，使用 credentials=same-origin 和 X-Requested-With=XMLHttpRequest，校验 HTTP/JSON 顶层结构，将缺失数组标准化为空数组。
- [ ] 重新运行数据服务测试，确认全部通过。

### Task 3: 基础路径、站点与故障路径图层

- [ ] 扩展 tests/dashboard_v2_map_engine.test.mjs 的 FakeMap，使其支持 getSource、getLayer、moveLayer 和 Source.setData。
- [ ] 先增加失败测试：配置 otnPathsPmtilesUrl 时只注册一次 pmtiles 协议，Source URL 为 pmtiles:// 加解析后的路径地址，两个图层 source-layer 均为 otn_paths。
- [ ] 先增加失败测试：renderSites 在地图加载前缓存；加载后过滤非法坐标并创建 sites-glow/sites-core/sites-label；第二次调用只 setData 不重复建层。
- [ ] 先增加失败测试：renderFaultPaths 接受 LineString/坐标数组，跳过非法/Multi 类型错误数据，创建红色覆盖层和标签层；第二次调用只更新 Source。
- [ ] 运行 Node 地图测试，确认上述行为全部失败且现有省界测试仍通过。
- [ ] 在 map_engine.js 增加 PMTiles 协议注册和 otn_paths_pmtiles Source，不读取 localTilesUrl。
- [ ] 增加模块级 mapReady、pendingSites、pendingFaultPaths；实现 renderSites 和 renderFaultPaths。
- [ ] 增加固定图层栈与 restackLayers，保证省界、基础路径、站点和故障路径顺序稳定。
- [ ] 增加综合状态优先级：MapLibre 运行错误最高，其次地图组件加载错误，再次数据刷新错误；成功刷新不得覆盖更高优先级错误。
- [ ] 重新运行 Node 地图测试，确认全部通过。

### Task 4: 应用轮询与完整回归

- [ ] 更新 Python 静态测试，先要求 app.js 导入 fetchDashboardMapData、renderSites、renderFaultPaths 和 reportDashboardV2DataStatus，立即调用刷新并以 config.refreshInterval 或 30000 建立 setInterval。
- [ ] 运行 Python 静态测试确认 RED。
- [ ] 修改 app.js：地图初始化后立即请求；成功渲染 sites/faultPaths 并报告在线；失败仅报告/记录错误，不调用清空渲染；建立 30 秒轮询。
- [ ] 运行 V2 Python、地图 Node 和数据服务 Node 测试。
- [ ] 运行 V1 test_dashboard_situation_board.py 与 test_dashboard_pmtiles_topology.py 回归。
- [ ] 运行 Python py_compile、两个 V2 JS 文件和 data_service.js 的 node --check。
- [ ] 确认 V2 源码不存在 china.pmtiles/china_local/localTilesUrl，且 V1 dashboard_views.py、dashboard.html、dashboard/map_engine.js 无差异。
- [ ] 运行 git diff --check，更新 PLAN.md 为完成。根据项目约定不暂存、不提交。
