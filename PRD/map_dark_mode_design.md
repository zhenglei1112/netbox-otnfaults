# 地图全域（图层、弹窗、控件）深色模式适配设计

## 1. 需求背景
随着整个 Netbox 核心逐渐切换到深色模式（Dark Theme），作为大屏及系统核心部分呈现的“故障分布地图”以及对应的弹窗、控件也应当无缝支持深色模式。由于现有地图中图层（省界、站点字体等）、原生及自定义的地图控件、Popup 等诸多元素都使用写死的浅色系配色，当用户启用系统的“深色模式”时，全白刺眼的版面将导致视觉体验极差。必须对此进行适配。

## 2. 需求目标
为故障分布图窗口设计并实现一套全面的深色模式方案。
1. **底图和图层感知深色**：底图海洋/陆域变暗；省界图层（如 `user-geojson-line`/`fill`）、站点图层（`netbox-sites`）动态根据深浅模式自行调整配色。
2. **地图上各类弹窗**：故障信息的详细展示与各类弹出信息框使用跟随深色模式的背景和文字。
3. **各类按钮和模块**：地图缩放、图层选择、空间查询控件下拉栏、左上搜索框、右下悬浮图表等控件同步跟随外观。

## 3. 实施方案
### 3.1 监听机制
通过对 `document.documentElement` (`<html>` 标记) 上的 `data-bs-theme` 属性设立 `MutationObserver` 监听。当值变为 `dark` 或者 `light` 时，触发全局事件让地图执行色彩变更。

### 3.2 图层样式动态覆盖 (MapLibre API)
在 JS 端调用 `map.setPaintProperty()` 以改变当前可见图层的色彩和透明度：
- **底图 (background / landuse / water / road_*)**：统一改用极深的灰黑或暗深蓝色（例如底色 `#060a14`、水体 `#000000`）。
- **矢量图层 (GeoJSON - Sites / Labels)**：将站点文字或弹窗外边缘发光 `text-halo-color` 改为与深色融合的颜色。

### 3.3 HTML / CSS 基于属性的纯样式适配
调整覆盖 `.maplibregl-popup-content` 和 `.maplibregl-ctrl` 组件：
```css
[data-bs-theme="dark"] .maplibregl-ctrl-group {
    background-color: var(--bs-body-bg);
}
/* 等等 */
```
使得所有依附在地图上的 DOM 元素直接通过 CSS 原生响应深色主题。
