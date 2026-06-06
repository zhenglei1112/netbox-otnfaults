# 颜色选择器弹出后地图样式菜单消失修复计划

## 1. 问题背景与现象
在 Mac 电脑的 Edge（或 Chrome 等基于 Chromium 的浏览器）中，点击地图样式设置菜单中的颜色块会拉起操作系统的原生颜色盘（Color Picker）。
然而在拉起色盘或鼠标往色盘移动时，由于鼠标离开了地图样式菜单，触发了 `mouseleave` 延时隐藏事件，导致整个地图样式设置菜单直接消失，用户无法继续使用或保存样式。

## 2. 核心原因
- 原生的 `<input type="color">` 弹窗不属于浏览器的 DOM 树，且其生命周期由操作系统接管。
- 鼠标往颜色面板移动，或者焦点发生转移时，会触发地图样式配置菜单 `menu` 节点的 `mouseleave` 事件。
- 此时 `mouseleave` 延时 200ms 的机制强行调用了 `hideMenu()` 销毁了整个组件，从而发生了上述 Bug。

## 3. 修复方案
在 `MapStylePreferenceControl.js` 中引入颜色选择器的激活状态标记（`this.colorPickerActive`）和鼠标位置标记（`this.mouseInsideMenu`）：
1. **防卫机制**：在 `hideMenuWithDelay`、`hideMenu` 和全局点击关闭事件中，如果 `this.colorPickerActive` 为 `true`，则直接忽略关闭/销毁逻辑。
2. **状态联动**：
   - 当 `<input type="color">` 触发 `focus` 事件时，将 `this.colorPickerActive` 设为 `true`。
   - 当其触发 `change` 事件（即用户已选择好颜色）时，显式调用 `input.blur()` 让其失焦。
   - 当其触发 `blur` 事件时，重置 `this.colorPickerActive` 为 `false`。并且，如果此时鼠标已经移出菜单（即 `!this.mouseInsideMenu`），则自动补发一次 `hideMenuWithDelay()` 以使菜单恢复正常的鼠标离屏隐藏逻辑。
3. **鼠标移入移出更新**：
   - 鼠标移入菜单更新 `this.mouseInsideMenu = true;`。
   - 鼠标移出菜单更新 `this.mouseInsideMenu = false;` 并执行 `hideMenuWithDelay()`。

## 4. 改动文件
- [Modify] [MapStylePreferenceControl.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/controls/MapStylePreferenceControl.js)
