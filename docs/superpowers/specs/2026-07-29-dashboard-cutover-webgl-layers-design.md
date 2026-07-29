# 态势大屏割接 WebGL 图层设计

## 背景

态势大屏中的站点、路径和故障点均由 MapLibre WebGL 图层绘制，割接点仍使用
`maplibregl.Marker` 创建 DOM 元素。DOM Marker 与地图图层采用不同的定位和合成
管线，在屏幕缩放、地图动画、倾斜和响应式布局变化时可能出现像素偏差。

项目此前已经因相同原因将故障点从 HTML Marker 迁移至 WebGL Circle Layer。
割接点应复用这一稳定模式。

## 目标

- 割接点全部通过 MapLibre WebGL 图层绘制，不再创建 HTML Marker。
- 保留黄色光晕、黄色核心和白色扳手的现有视觉语义。
- 坐标、数据窗口、事件列表和割接状态逻辑保持不变。
- 割接数据刷新时更新现有 GeoJSON source，不重复创建图层。
- 割接图层遵循态势大屏统一的图层堆叠顺序。

## 方案

### 数据源

`renderCutoverMarkers()` 将有效割接转换为 `FeatureCollection`。每个 Feature 使用
`[lng, lat]` 点坐标，并携带割接 ID 等必要属性。无有效坐标的割接不生成 Feature；
保留现有按 A 端站点名称匹配坐标的兼容回退。

首次渲染时创建 `cutovers` GeoJSON source，后续渲染仅调用 `setData()`。

### 图层

割接点由三个图层组成：

1. `cutovers-glow`：Circle Layer，绘制半透明黄色光晕。
2. `cutovers-core`：Circle Layer，绘制黄色核心和白色描边。
3. `cutovers-icon`：Symbol Layer，绘制白色扳手。

扳手沿用项目现有 SVG 路径，在浏览器端生成固定尺寸的透明图像并通过
`map.addImage()` 注册。Symbol Layer 通过 `icon-image` 使用该图像。图像仅注册一次，
注册失败时仍保留光晕和核心，避免整个割接图层不可见。

三个图层加入 `DASHBOARD_LAYER_STACK`，位于故障点图层之上，确保割接点不会被站点、
路径或故障点遮挡。

### 清理

删除 `renderCutoverMarkers()` 中创建、保存和移除 `maplibregl.Marker` 的逻辑。
删除仅供态势大屏 HTML Marker 使用的 `.cutover-map-marker`、
`.cutover-marker-glow` 和 `.cutover-marker-core` 样式；其他页面的割接样式不受影响。

## 错误处理

- 地图尚未就绪时继续缓存待渲染数据。
- 经纬度为空或不是有效数值时跳过该 Feature。
- 扳手图片尚未注册时先建立圆形图层；图片加载成功后建立 Symbol Layer并恢复统一
  图层排序。
- 重复刷新不得重复添加 source、image 或 layer。

## 测试

回归测试应锁定：

- 态势大屏不再调用 `new maplibregl.Marker` 或维护 `_cutoverMarkers`。
- 割接使用独立 GeoJSON source，后续刷新调用 `setData()`。
- 光晕、核心和扳手均为 MapLibre 图层。
- 三个割接图层进入统一图层排序且顺序正确。
- 无有效坐标的割接不会生成 Feature。
- 旧 HTML Marker 专用 CSS 已移除。
- JavaScript 语法检查和相关 Python 测试全部通过。

## 非目标

- 不修改后端割接坐标解析和接口字段。
- 不修改割接事件卡片、详情页或故障地图模块。
- 不增加割接呼吸动画、点击弹窗或新的地图交互。
- 不修改数据库结构。
