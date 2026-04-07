# 每周通报大屏 Tabler 重构设计

**日期：** 2026-04-07

**目标**

将每周通报页面从偏“投屏大屏”的定制视觉，重构为基于 Tabler 设计语言的标准运营看板页面，提升日常查看体验、响应式适配和后续维护性，同时尽量复用现有后端接口和 ECharts 数据渲染逻辑。

## 背景与当前实现

当前周报页面由以下几个核心文件构成：

- `netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html`
- `netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css`
- `netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js`
- `netbox_otnfaults/weekly_report_views.py`

当前页面特征：

- 使用自定义“大屏”式布局与高装饰视觉
- 页面结构固定，偏向全屏展示，不利于普通浏览器窗口查看
- 数据源已经具备完整周报聚合能力，无需重做主要统计逻辑
- 前端渲染以原生 JS + ECharts 为主，没有引入 React/Vue

## 重构目标

本次重构聚焦于“Tabler 标准 dashboard 化”，而不是简单换皮。

明确目标如下：

- 页面视觉风格向 Tabler 靠拢，采用更标准的运营看板布局
- 保留现有周报业务语义和主要数据口径
- 兼顾桌面端日常查看与大屏展示，但优先普通 dashboard 的可读性
- 保持实现技术轻量，不引入 React/Vue
- 尽量不改动后端 API 结构，降低联动风险

非目标：

- 不改造 NetBox 核心目录
- 不重做周报数据计算规则
- 不在本次重构中引入新的图表库
- 不把页面拆成复杂前端框架工程

## 方案选择

已确认采用的方案是：

**Tabler 标准卡片化重构**

选择原因：

- 最贴近 Tabler 的使用方式
- 能最大化利用 Bootstrap/Tabler 的卡片、统计块、表格和徽标语义
- 可以复用现有 API 和图表渲染逻辑，改造成本可控
- 相比保留旧大屏骨架，更容易得到风格统一、后续可维护的结果

## 页面信息架构

重构后的页面按四层信息结构组织：

### 1. 顶部概览栏

包含：

- 页面标题“每周通报”
- 当前统计周期
- 数据更新时间或页面加载时间
- 简短说明徽标，例如“按周统计”“自动汇总”

设计要求：

- 使用 Tabler 风格的 page header
- 标题信息左对齐，辅助信息放右侧或标题下方
- 不再保留现在强装饰性的发光标题背景

### 2. KPI 概览区

保留现有四类核心指标：

- 本周故障总数
- 本周中断总时长
- 自建光缆统计
- 协调/租赁统计

设计要求：

- 以 Tabler card/stats 风格展示
- “总数”“总时长”作为第一优先级，体量更大
- 环比变化以 badge 或 trend 文本显示
- 自建与协调/租赁为次级卡片，强调结构性对比

### 3. 中部分析区

拆分为三个清晰模块：

- 主要原因分析图表
- 重点影响省份列表
- 重大事件摘要

设计要求：

- 原因分析保持 ECharts 柱状图，但颜色贴近 Tabler 的低饱和蓝系
- 重点省份改为卡片列表或紧凑列表项，不保留旧版“省份竖牌”样式
- 重大事件改为告警列表卡片，突出位置、时长、原因和摘要

### 4. 底部业务影响区

用于展示裸纤业务影响。

设计要求：

- 使用更标准的 Tabler table/card 呈现
- 中断、抖动、正常状态使用明确 badge 区分
- 正常业务不要再与异常数据混成一条“大说明”，应保持结构清楚
- 表格在窄屏下允许横向滚动，避免压缩导致不可读

## 视觉与交互设计

### 视觉方向

新的视觉风格应满足：

- 浅色背景、白色卡片、柔和阴影
- 以蓝色体系为主色，红色和黄色只用于风险提示
- 减少过强渐变、发光、赛博风装饰
- 字体层级更接近标准后台 dashboard

### 交互要求

- 页面初始加载后自动请求周报数据
- 保留现有失败兜底，但需要补充更友好的空状态和错误状态
- 页面在宽屏和普通桌面窗口下都应保持清晰排版
- 图表应保留 resize 行为

## 技术实现边界

本次预计改动文件如下：

- 修改 `netbox_otnfaults/templates/netbox_otnfaults/weekly_report_dashboard.html`
- 修改 `netbox_otnfaults/static/netbox_otnfaults/css/weekly_report_dashboard.css`
- 修改 `netbox_otnfaults/static/netbox_otnfaults/js/weekly_report_dashboard.js`
- 视需要小幅修改 `netbox_otnfaults/weekly_report_views.py`

后端调整原则：

- 若现有接口已足够支撑新页面，则不修改数据结构
- 如需补充“刷新时间”或更明确的展示字段，可做最小增量调整
- 保持 JSON 输出兼容现有前端所需字段，避免引入额外复杂度

## 组件映射

现有页面模块与重构后模块的对应关系如下：

- 旧标题区 -> Tabler page header
- 旧 KPI 大块 -> Tabler stats cards
- 旧原因分析面板 -> Tabler card + ECharts
- 旧重点省份块 -> Tabler list/card group
- 旧重大事件块 -> Tabler alert/list card
- 旧裸纤影响表 -> Tabler card + responsive table

## 风险与控制

主要风险：

- 当前模板和脚本文件存在编码异常痕迹，重构时需避免继续放大乱码问题
- 旧 JS 中部分字符串拼接和 HTML 结构耦合较强，模板改动后需要同步整理渲染函数
- 如果直接引用外部 CDN 版 Tabler，运行环境可能受网络条件影响

控制策略：

- 优先重写目标页面模板中需要改动的中文文案，确保 UTF-8 正常
- 对 JS 渲染函数做适度整理，使其围绕新的 DOM 结构输出
- Tabler 接入优先采用其 CSS/组件语义；是否使用 CDN 在实施阶段根据环境再定

## 验收标准

当满足以下条件时，认为本次重构完成：

- 页面整体视觉明显转为 Tabler 风格 dashboard
- 现有周报数据能正确加载并映射到新布局
- KPI、原因分析、重点省份、重大事件、裸纤影响五个板块均可正常展示
- 页面在常规桌面浏览窗口下可读性明显优于旧版大屏布局
- 不引入 React/Vue，不修改 NetBox 核心目录

## 实施建议

实施时优先顺序为：

1. 先重建模板结构，明确新的 DOM 分区
2. 再重写样式，让页面先稳定成型
3. 最后适配 JS 渲染逻辑和空状态、错误状态
4. 如有必要，再补最小后端字段
