# 态势大屏 V2 省界 GeoJSON 地图设计

## 目标

态势大屏 V2 不再加载 `china.pmtiles` 或任何在线/本地瓦片底图。地图区域使用 MapLibre 的纯色深色背景，并独立加载项目现有的 `中国_省.geojson`，形成与 V1 一致的中国省界视觉骨架。

V1 页面、视图和地图引擎保持不变。

## 地图数据流

1. Django 视图通过 staticfiles URL 解析器生成 `中国_省.geojson` 的静态文件地址，并写入 V2 的 JSON 配置。
2. V2 创建只包含深色背景的 MapLibre Style，不注册 PMTiles 协议，也不创建 PMTiles Source。
3. MapLibre 触发 `load` 后，V2 地图引擎请求省界 GeoJSON。
4. 地图引擎递归遍历 GeoJSON 坐标，将 GCJ-02 转换为 WGS-84，以便后续站点、故障和 OTN 路径使用统一坐标系。
5. 转换后的数据注册为 `provinces` GeoJSON Source，并由独立的省界图层引用。

## 图层设计

省界图层沿用 V1 的视觉顺序：

1. `province-shadow`：深色偏移阴影，增强地图轮廓的悬浮感。
2. `province-extrusion`：省区主体，保持当前 V1 的深蓝色视觉基调。
3. `province-border-glow-bottom`：宽线模糊发光边界。
4. `province-border-top`：清晰省界轮廓。
5. `province-labels`：读取 Feature 的 `name` 属性显示省份名称，并过滤境界线、国界、九段线和十段线等非省份标签。

标签继续使用现有 `local_glyphs_url` 字体服务。字体资源不属于底图，因此保留该配置；`local_tiles_url`、`use_local_basemap` 和 PMTiles 脚本不再进入 V2 页面运行链路。

## 状态与错误处理

- 地图创建期间显示“省界加载中”。
- GeoJSON 请求成功且图层完成注册后显示地图就绪状态。
- HTTP 错误、JSON 解析错误、坐标数据错误或 MapLibre 运行错误都应显示明确的省界加载失败状态。
- 一旦发生加载错误，后续迟到的 `load` 或其他成功事件不得覆盖错误状态。
- 加载失败时保留深色背景和页面布局，不影响左侧信息区。

## 隔离要求

- 不修改 V1 的 `dashboard.html`、`dashboard/map_engine.js` 或 `dashboard_views.py`。
- V2 继续使用自己的 `dashboard_v2/map_engine.js` 和 `dashboard_v2/app.js`。
- V2 不请求 `china.pmtiles`，不注册 `pmtiles://` 协议，也不依赖 `pmtiles.js`。
- 当前阶段不加载站点、路径、故障或其他业务数据。

## 测试要求

- Python 静态测试确认 V2 配置注入省界静态地址，且模板不加载 `pmtiles.js`。
- JavaScript 行为测试确认 MapLibre Style 不包含 PMTiles Source。
- JavaScript 行为测试确认地图 `load` 后请求省界 GeoJSON、注册 `provinces` Source，并按顺序增加五个省界图层。
- 行为测试确认坐标转换发生，且加载失败时错误状态保持可见。
- 继续运行 V1 态势大屏和 PMTiles 拓扑回归测试，证明旧模块未受影响。

## 完成标准

打开 V2 页面时，浏览器网络请求中不再出现 `china.pmtiles`；地图区域显示深色背景、中国省界轮廓及省份标签，控制台没有由 V2 产生的 PMTiles 404。
