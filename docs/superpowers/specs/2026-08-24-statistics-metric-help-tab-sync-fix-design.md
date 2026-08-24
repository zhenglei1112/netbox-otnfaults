# 故障统计指标说明 Tab 同步修复设计

## 目标

点击故障统计页顶部“指标说明”按钮时，说明弹窗自动切换到与当前主 Tab 对应的说明 Tab。

## 根因

现有代码已经建立主 Tab 与说明 Tab 的映射，但只在弹窗 `show.bs.modal` 事件中通过全局 `bootstrap.Tab.getOrCreateInstance()` 切换。NetBox 页面运行环境未必暴露兼容的全局 Tab API，导致映射存在但实际切换未执行。现有测试只检查源码字符串，没有验证不依赖全局 API 的可执行交互路径。

## 设计

- 保留现有五组 Tab 映射和说明内容。
- 在“指标说明”按钮点击时读取 `#statisticsTab` 内当前激活的主 Tab。
- 找到对应说明 Tab 后调用其原生 `click()`，复用已有 `data-bs-toggle="tab"` 行为，并在弹窗打开前完成切换。
- 不手工维护 `active`、`show` 或 `aria-selected`，避免与 Bootstrap 内部状态分离。
- 删除不再需要的弹窗 `show.bs.modal` 直接 API 调用。

## 测试

- 回归测试锁定按钮点击监听、当前主 Tab 查询、映射查找和说明 Tab `click()`。
- 回归测试禁止重新依赖 `bootstrap.Tab.getOrCreateInstance()`。
- 运行统计页资源测试、JavaScript 语法检查和相关统计回归测试。

## 非目标

- 不修改指标说明文案。
- 不修改统计数据、筛选条件或主 Tab 切换行为。
- 不重构统计页其他 JavaScript。

## 激活 Tab 底边视觉修复

说明弹窗位于 `.page-statistics` 容器之外，主页面的激活 Tab 样式不会作用于弹窗，导致选中说明 Tab 仍显示默认底边横线。

- 仅对 `.statistics-metric-help-tabs .nav-link.active` 设置与弹窗表面一致的底边颜色。
- 保留未选区域的导航基线，不移除整个 Tab 列表的底边。
- 不调整弹窗 DOM 位置、Tab 尺寸或其他导航样式。
- 使用 CSS 源码回归测试锁定局部选择器及底边颜色，并提升 CSS 缓存版本。
