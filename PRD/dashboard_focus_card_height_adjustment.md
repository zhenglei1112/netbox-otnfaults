# 焦点详情卡片高度回调微调需求

## 1. 需求背景与问题分析
- **当前表现**：在部分浏览器及屏幕字形渲染环境下，焦点详情卡片内渲染的故障/割接等多行信息超出容器空间，导致卡片内部产生了不该出现的竖向滚动条。
- **根本原因**：之前为了压实侧边栏排版，将右下角焦点卡片 `#event-focus-card` 的高度压缩过多（常规屏 165px，4K屏 310px）。在文字字形排版较紧凑的情况下容易溢出容器导致滚动条出现。
- **优化方案**：在保证卡片紧凑、消除大面积留白的基础上，适度增加高度值（常规屏调整回 175px，4K屏自适应调整回 325px），使其刚好安全包裹全部详情信息，彻底消除竖向滚动条。

## 2. 实施方案
- **修改文件**：[dashboard.css](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/css/dashboard.css)
- **常规屏修改**：
  - 定位 `#event-focus-card` 元素样式。
  - 将 `height` 及 `flex: 0 0` 值从 `165px` 调整为 `175px`。
- **4K大屏修改**：
  - 定位 `@media (min-width: 2500px)` 媒体查询内的 `#event-focus-card`。
  - 将 `height !important` 及 `flex: 0 0 ... !important` 值从 `310px` 调整为 `325px`。

## 3. 任务分解 (Task List)
1. [x] 修改 `dashboard.css` 中常规屏的 `#event-focus-card` 高度为 175px。
2. [x] 修改 `dashboard.css` 中大屏 `@media` 下的 `#event-focus-card` 高度为 325px。
3. [x] 同步更新 `task.md` 与 `walkthrough.md` 里的任务和结果说明。
4. [x] 产出本需求文档保存至 PRD 目录。
