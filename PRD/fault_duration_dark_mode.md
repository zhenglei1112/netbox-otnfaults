# 故障历时时间轴深色模式适配

## 1. 需求背景
当前 Netbox 故障详情页面的“故障历时”和“处理历时”部分，由于直接使用了前端硬编码的灰色 `#dee2e6`、白色 `#fff` 以及 Bootstrap 的浅色文字类 `text-dark`、`bg-white`，导致在 Netbox 切换到深色模式时，这些元素依然保持高亮或浅色外观，不仅刺眼且不可读，与 Netbox 现有的深色主题不协调。

## 2. 需求目标
为故障详情页面的故障历时信息部分（含 Timeline 节点、连线、以及历时文本）增加针对深色模式的支持。要求使得信息在深色模式下清晰可读，与现有系统外观融合。

## 3. 实施方案
修改 `otnfault.html` 模板中的样式类和内联样式，利用 Bootstrap 5 的 CSS 变量（CSS Variables）来实现主题自适应。
- 替换 `text-dark` 为 `text-body`
- 将写死的 `#dee2e6` 替换为 `var(--bs-border-color)`
- 将写死的 `#fff` 和 `bg-white` 替换为 `var(--bs-card-bg)` 或 `var(--bs-body-bg)` 和 `bg-body`
- 使用动态 CSS 变量即可自然匹配深色与浅色模式，不需要额外的 JavaScript 或复杂的 CSS 文件。
