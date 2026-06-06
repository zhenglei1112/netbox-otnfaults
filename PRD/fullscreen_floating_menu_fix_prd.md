# 一张图模块全屏状态下浮动菜单遮挡修复 PRD

## 1. 问题背景与现象
在一张图（地图）模块中，右侧包含“图层显示”与“地图样式设置”两个悬浮控制按钮。
- 在正常窗口模式下，鼠标悬浮至上述按钮可正常拉起对应的浮动设置菜单。
- 在全屏显示模式下（使用 HTML5 Fullscreen API 将地图容器全屏），悬浮菜单则不显示。

## 2. 原因分析
- 现有的 `LayerToggleControl.js` 和 `MapStylePreferenceControl.js` 中，浮动菜单（`.view-control-menu.floating-menu`）在展示时，直接通过 `document.body.appendChild(menu)` 挂载到系统的 `body` 根节点上。
- 在启用 HTML5 Fullscreen 时，浏览器将选中的全屏元素（如 `div#map` 或 `.card`）提升至独立的最顶层上下文（Fullscreen 层）。
- 由于 `body` 根节点本身不处于该 Fullscreen 上下文中，所有挂载在 `body` 根目录而不在全屏元素内部的子孙节点均会被隐藏，从而导致用户在全屏下无法看到悬浮菜单。

## 3. 修复方案
在浮动菜单创建并进行节点挂载（`appendChild`）时，检测当前系统是否正处于 HTML5 全屏状态：
1. 通过 `document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement` 获取当前正处于全屏状态的元素。
2. 如果存在全屏元素，将菜单节点挂载至该全屏元素内部（例如：`fullscreenEl.appendChild(menu)`）；
3. 如果不存在全屏元素（正常状态），则继续挂载至 `document.body.appendChild(menu)`。
4. 由于菜单采用 `position: fixed` 定位，且通过 `getBoundingClientRect()` 动态获取按钮位置并计算菜单的 `top` 与 `left`，在全屏元素内部挂载并使用 `fixed` 定位，能够确保在全屏层完美呈现在按钮旁，且能适配视口变化。

## 4. 影响范围与改动文件
- [Modify] [LayerToggleControl.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/controls/LayerToggleControl.js)：修改 `createMenu` 挂载逻辑。
- [Modify] [MapStylePreferenceControl.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js)：修改 `createMenu` 挂载逻辑。
