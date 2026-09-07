# 态势大屏 V2 站点与路径显示设计

## 目标

在现有 V2“深色背景 + 省界 GeoJSON”地图上，按照 V1 当前实现增加站点、基础路径和故障路径显示。

本阶段不增加故障点、割接点、事件聚焦、自动播控或左侧业务卡片。V1 页面、视图和 JavaScript 保持不变。

## 数据来源

### 站点与故障路径

复用 V1 现有的 dashboard/data/ 接口：

- sites：所有具备有效经纬度的站点。
- fault_paths：仅与当前活动故障相关的路径覆盖数据。

V2 页面加载后立即请求一次，之后每 30 秒刷新。V2 只消费上述两个字段，忽略接口中的故障点、割接、趋势和卡片数据。

### 基础路径

复用插件配置中的 otn_paths_pmtiles_url，通过 PMTiles Source 加载全部 OTN 基础路径：

    pmtiles://<otn_paths_pmtiles_url>

基础路径的 Source Layer 固定为 otn_paths。V2 重新加载 pmtiles.js 并注册 PMTiles 协议，但不读取 local_tiles_url，也不创建 china.pmtiles 底图 Source。

## 模块边界

### Django 视图

dashboard_v2_views.py 在现有地图配置基础上增加：

- dataUrl：V1 现有 dashboard_data URL。
- otnPathsPmtilesUrl：插件配置的路径 PMTiles 地址。
- refreshInterval：30000 毫秒。

不重新加入 useLocalBasemap 或 localTilesUrl。

### 数据服务

新增独立的 dashboard_v2/data_service.js：

- 使用同源凭据请求 dataUrl。
- 检查 HTTP 状态和 JSON 顶层结构。
- 只返回标准化后的 sites 和 faultPaths。
- 请求失败时抛出带 HTTP 状态或解析原因的错误。

### V2 地图引擎

dashboard_v2/map_engine.js 继续负责省界，并新增：

- 注册 PMTiles 协议。
- 加载基础路径 PMTiles Source 和两条绿色路径图层。
- 将站点数组转换为 GeoJSON，并创建或更新站点 Source。
- 将故障路径几何标准化为 GeoJSON，并创建或更新故障路径 Source。
- 在地图尚未完成初始化时缓存最近一次站点和故障路径数据，地图就绪后一次性渲染。
- 每次新增图层后恢复固定图层顺序。

### V2 应用入口

dashboard_v2/app.js 负责：

- 初始化时钟和地图。
- 立即刷新站点与故障路径数据。
- 每 30 秒执行后续刷新。
- 成功时调用地图引擎的 renderSites() 和 renderFaultPaths()。
- 刷新失败时保留上一次已渲染数据，不清空地图。

## 图层与样式

固定顺序由下至上：

1. background
2. province-shadow
3. province-extrusion
4. province-border-glow-bottom
5. province-border-top
6. province-labels
7. otn-paths-base-glow
8. otn-paths-base-main
9. sites-glow
10. sites-core
11. sites-label
12. paths-fault-glow
13. paths-fault-main
14. paths-label
15. paths-detail

### 基础路径

- 光晕：半透明绿色宽线。
- 主线：绿色细线，随缩放级别调整宽度。
- 不增加光流动画，避免 LineAtlas 纹理累积问题。

### 站点

- 光晕：半透明绿色圆。
- 核心：绿色圆点和描边。
- 标签：Noto Sans SC Regular，缩放级别 6 起显示。
- 丢弃空值、非数字或超出经纬度范围的站点坐标。
- 本阶段不创建 V1 的聚焦站点图层，因为尚未接入事件聚焦。

### 故障路径

- 接受 GeoJSON Geometry 对象或坐标数组。
- 丢弃无法解析、坐标不足或非 LineString/MultiLineString 的路径。
- 使用红色光晕和红色主线覆盖基础路径。
- 缩放级别 5.5 起显示路径名称，7.5 起显示类型和长度详情。

## 状态与错误处理

- 省界成功仍以“省界地图就绪”为地图基础状态。
- PMTiles 库缺失、路径地址缺失或基础路径加载错误时，显示明确错误，但保留省界和已经可用的站点数据。
- 数据接口刷新失败时不清空现有站点或故障路径；在控制台记录一次明确错误，并将页面状态更新为“业务数据刷新失败”。
- 后续刷新成功后可恢复为“态势数据在线”。
- 异步成功回调不得覆盖 MapLibre 已产生的底层地图错误。

## 性能约束

- 基础路径继续使用 PMTiles，禁止通过 dashboard/data/ 返回全量路径。
- 站点和故障路径 Source 首次创建，后续仅调用 setData()。
- 定时刷新不得重复创建图层或重复注册 PMTiles 协议。
- 刷新周期沿用 V1 的 30 秒，不引入更高频率轮询。

## 测试要求

- Python 静态测试确认 V2 配置包含 dataUrl、otnPathsPmtilesUrl 和 30 秒刷新周期，但不包含 localTilesUrl。
- 模板测试确认重新加载 pmtiles.js，同时 V2 地图源码不出现 china.pmtiles 或 china_local。
- Node 地图行为测试确认 PMTiles 仅注册一次、基础路径 Source 使用配置地址和 otn_paths Source Layer。
- Node 行为测试确认站点坐标过滤、Source 首次创建与后续 setData()。
- Node 行为测试确认故障路径几何标准化、无效数据跳过和红色覆盖图层顺序。
- 数据服务测试确认成功标准化、HTTP 失败和无效 JSON 行为。
- 应用入口源码测试确认立即加载并按 30000 毫秒刷新。
- 继续运行省界测试和 V1 态势大屏/PMTiles 拓扑回归测试。

## 完成标准

打开 V2 页面后：

- 仍不请求 china.pmtiles。
- 显示省界、全部绿色基础路径、有效站点及其名称。
- 活动故障相关路径以红色覆盖。
- 30 秒刷新不会重复增加 Source、Layer 或 PMTiles 协议。
- 单次接口失败不会清空已经显示的站点和路径。
