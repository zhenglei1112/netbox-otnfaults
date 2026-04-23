# 地图样式个人偏好设计

## 目标

为 NetBox OTN 故障插件的地图窗口增加配置功能。第一版只保存按人员区分的可视化样式偏好，范围限定为三类共享地图图层：

- 省界图层
- NetBox 站点图层
- OTN 路径图层

设计需要为后续扩展留下空间，例如故障点样式、热力图样式、默认加载图层、默认视角、按角色或全局默认配置等。

## 当前上下文

插件已经采用统一地图架构：

- `unified_map.html` 注入 `window.OTNMapConfig`。
- `map_modes.py` 定义各地图模式需要加载的静态资源。
- `unified_map_core.js` 创建 MapLibre 地图，并加载共享的省界、站点、路径图层。
- `fault_mode.js`、`location_mode.js`、`statistics_cable_break_mode.js` 等模式插件负责各自的地图业务逻辑。
- `LayerToggleControl.js` 当前负责故障地图的视图模式和筛选状态，但它不是持久化的个人样式偏好系统。

新功能必须保持在 `netbox_otnfaults/` 插件目录内实现，不依赖未确认的 NetBox 核心 API 路径。

## 推荐方案

采用插件自有模型和插件内 API：

- 新增 `OtnMapPreference`，以 `user + map_mode` 标识一条个人地图偏好。
- 使用带版本号的 JSON 字段保存样式配置。
- 地图视图把当前用户的偏好注入到 `window.OTNMapConfig`。
- 共享图层创建完成后统一应用样式偏好。
- 在地图窗口内提供浮动设置面板，支持预览、恢复默认和保存。

这个方案能满足“按人员配置保存”，同时保留 JSON schema 扩展能力。

## 数据模型

新增 `OtnMapPreference(NetBoxModel)`。

字段：

- `user`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otn_map_preferences')`
- `map_mode`: `CharField(max_length=64)`
- `style_config`: `JSONField(default=dict, blank=True)`
- `schema_version`: `PositiveSmallIntegerField(default=1)`
- `NetBoxModel` 标准字段

约束：

- `user + map_mode` 唯一约束

方法：

- `get_absolute_url()`
- `__str__()`

该模型需要增加 `FilterSet`，方便后续按 NetBox 插件惯例暴露 REST API 或 GraphQL。第一版地图 UI/API 仍然只允许用户读写自己的配置。

## 样式配置 Schema V1

第一版只保存以下键：

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

服务端必须对白名单字段做校验。未知的顶层键、未知的组内字段需要拒绝或过滤；数值字段需要限制在安全范围内；颜色字段可接受十六进制颜色和当前地图代码中已有的 CSS 颜色字符串。

## API

新增插件内接口：

- `GET /plugins/otnfaults/map/preferences/<map_mode>/`
- `POST /plugins/otnfaults/map/preferences/<map_mode>/`

行为：

- 两个接口都要求用户已登录，并满足插件现有权限要求。
- `GET` 返回当前用户在该 `map_mode` 下的偏好，并与默认值合并。
- `POST` 只校验并保存当前用户自己的偏好。
- 用户不能通过这些接口读取或修改其他人的偏好。
- API 保存成功后返回规范化后的配置，前端以返回结果作为唯一可信形态。

该接口是插件本地接口，不伪造或依赖 NetBox 核心 API 路径。

## 后端流程

地图视图需要根据当前 `map_mode` 解析当前用户样式偏好，并注入模板上下文：

- `map_style_preferences`: 注入为 `window.OTNMapConfig.mapStylePreferences`
- `map_preferences_url`: 当前地图模式的偏好 GET/POST 接口 URL

该逻辑应放在小型 helper/service 中复用，避免在多个地图视图里重复拼装。没有保存记录时 helper 返回默认配置。

## 前端流程

新增两个聚焦模块：

- `services/MapStylePreferenceService.js`
- `controls/MapStylePreferenceControl.js`

`MapStylePreferenceService` 职责：

- 合并默认样式配置和用户已保存配置。
- 将省界、站点、路径样式应用到 MapLibre 图层。
- 某个地图模式不存在目标图层时安全跳过。
- 必要时在地图样式重载后重新应用共享图层样式。

目标图层：

- `user-geojson-fill`
- `user-geojson-line`
- `netbox-sites-layer`
- `netbox-sites-labels`
- `otn-paths-layer`
- `otn-paths-highlight-outline`
- `otn-paths-highlight-layer`

`MapStylePreferenceControl` 职责：

- 在地图窗口内渲染浮动设置面板。
- 提供 V1 中省界、站点、路径三类样式字段的控件。
- 支持“应用预览”、“恢复默认”、“保存为我的默认”。
- 预览只修改当前地图实例。
- 只有点击保存时才调用 API 持久化。
- 保存成功后继续留在当前地图，不刷新 iframe。

该控件应独立于 `LayerToggleControl`。`LayerToggleControl` 当前是故障地图的视图和筛选控制，不应继续承担持久化样式编辑职责。

## UI 设计

入口是地图窗口内的设置按钮。点击后打开右侧浮动面板，标题使用“我的地图样式”或等价中文文案。

面板分区：

- 省界样式
- 站点样式
- 路径样式

每个分区包含显示开关和简单样式字段。UI 使用 NetBox 原生 Bootstrap 5 工具类，不引入 React/Vue。颜色字段第一版可使用原生 color input；透明度、宽度、半径、标签字号使用数值输入。

## 错误处理

- 偏好加载失败时，地图继续使用内置默认样式，并在设置面板内显示非阻塞提示。
- 保存失败时，保留当前预览状态，并在面板内显示校验或网络错误。
- 当前地图模式不存在某个目标图层时，样式应用逻辑跳过该图层，不抛出异常。
- 无效 JSON 或不支持的字段不能入库。

## 测试

第一版测试覆盖：

- `OtnMapPreference` 字段和 `user + map_mode` 唯一约束。
- 模型存在 `FilterSet`。
- 偏好 API 只能读取和写入当前用户的记录。
- 无效或未知样式字段被拒绝或规范化。
- `unified_map.html` 注入 `mapStylePreferences` 和 `mapPreferencesUrl`。
- `map_modes.py` 为相关地图模式加载新的偏好 service/control。
- `MapStylePreferenceService.js` 引用并应用省界、站点、路径图层 ID。
- `MapStylePreferenceControl.js` 包含预览、恢复默认和保存动作。

## V1 不包含

- 故障点样式配置
- 热力图样式配置
- 默认中心点、缩放或投影配置
- 按角色、租户或全局默认的样式配置
- 单用户多个命名样式配置
- 样式预设导入/导出

## 实施说明

- Python 代码遵守 NetBox 插件结构和类型提示要求。
- 所有代码改动保持在 `netbox_otnfaults/` 内。
- 新增模型后需要生成迁移；在真实 NetBox 环境中按项目约束先运行 `makemigrations`，再紧接着运行 `migrate`。
- 当前仓库没有可运行的 NetBox 环境，因此验证以源码级测试和 Python 语法检查为主，除非后续提供运行环境。
