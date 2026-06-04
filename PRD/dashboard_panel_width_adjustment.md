# 左右侧边栏宽度略微调窄需求

## 1. 需求背景与问题分析
- **当前表现**：左右两侧的面板占用了较多的横向宽度，使得中央核心的地图演播区的横向占比相对较小，特别是在大屏展示时，期望两侧能略微收窄以给中央地图留出更广阔的展示视野。
- **优化方案**：
  - 常规屏：将侧边栏宽度从原来的 `320px` 调窄为 `300px`。
  - 4K 大屏：将侧边栏自适应宽度从原来的 `600px` 调窄为 `560px`。
  - 这一变化只通过调整全局 CSS 变量 `--panel-w` 实现，整个布局结构无缝贴合。

## 2. 实施方案
- **修改文件**：[dashboard.css](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css)
- **常规屏修改**：
  - 定位 `:root`。
  - 将 `--panel-w` 从 `320px` 改为 `300px`。
- **4K大屏修改**：
  - 定位 `@media (min-width: 2500px)` 下的 `:root`。
  - 将 `--panel-w` 从 `600px` 改为 `560px`。

## 3. 任务分解 (Task List)
1. [x] 修改 `dashboard.css` 中常规屏下的 `--panel-w` 变量为 300px。
2. [x] 修改 `dashboard.css` 中 4K 媒体查询下的 `--panel-w` 变量为 560px。
3. [x] 确认修改对左右布局自适应正常，无元素物理溢出。
4. [x] 产出本需求文档保存至 PRD 目录。
