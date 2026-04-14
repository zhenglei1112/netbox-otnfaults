# 光网故障多维统计与下钻展示页面 (PRD & 执行计划)

## 1. 目标说明 (Goal)
构建一个支持多维时间过滤、多维度聚合和下钻交互的“故障统计看板”。
主要功能包括：
1. **时间过滤**：按年、月、周进行统计（可选择对应的年份、月份、周数），支持“本年/本月/本周截至当前”的范围筛选。
2. **多维统计图表**：
   - **光缆属性**：自建、租赁、协调（基于 `OtnFault.resource_type` 映射）。
   - **省份**：全国各省份（基于 `OtnFault.province` 关联）。
   - **一级原因**：基于 `OtnFault.interruption_reason` 选项。
3. **关键 KPI 指标计算**：
   - **故障数**：所选范围内的故障总次数。
   - **故障总时长**：累计中断时长。
   - **故障平均时长**：平均单次时长。
   - **长时故障总数**：≥6小时的故障数。
   - **重复故障数**：若某单次故障在过去 60 天内发过生相同“路径/站点”的故障，则记录为重复。
4. **报表下钻 (Drill-down)**：
   - 点击各类统计图表（如省份柱状图或原因饼图）的特定切片，可在页面底部自动展示过滤后的故障详细列表。

## 2. 方案设计 (Proposed Changes)

### 2.1 后端 API 与路由设计 (Backend)
- **新增视图** `netbox_otnfaults/statistics_views.py`：
  - `FaultStatisticsPageView`：只渲染基础 HTML 框架。
  - `FaultStatisticsDataAPI`：接收 `time_type`, `year`, `month`, `week`, `to_date` 等参数，进行复杂的 QuerySet 过滤与 Annotation 统计。
- **配置路由** `netbox_otnfaults/urls.py`：
  - 增加 `path('statistics/', statistics_views.FaultStatisticsPageView.as_view(), name='statistics')`。
  - 增加 `path('statistics/data/', statistics_views.FaultStatisticsDataAPI.as_view(), name='statistics_data')`。
- **导航菜单** `netbox_otnfaults/navigation.py`：
  - 在“地图”侧边栏分组中加入 `PluginMenuItem(link='plugins:netbox_otnfaults:statistics', link_text='故障统计看板')`。

### 2.2 核心业务逻辑说明
关于**重复故障数**算法说明：
- 针对选定时间内的所有故障。
- 如果其发生时间（`fault_occurrence_time`）的前 60 天内，查询系统中是否存在另一个故障 `pre_fault` 满足：
  1. `pre_fault.interruption_location_a` == 当前 `fault.interruption_location_a`
  2. `pre_fault.interruption_location` 与当前 `fault.interruption_location` 存在交集（同一点Z可能出现导致同路径复发）。
- 若存在上述 `pre_fault`，则视为该次故障属于“重复故障”。

### 2.3 前端与可视化设计 (Frontend)
- **模板文件**：`templates/netbox_otnfaults/statistics_dashboard.html`
- **静态资源**：`static/netbox_otnfaults/js/statistics_dashboard.js` 和 CSS。
- **图表实现**：为了支持复杂的下钻功能和多维统计渲染，拟使用 **ECharts** (通过 CDN 引入。NetBox 4.x原生不包括，若需要完全走内网可使用内联或基础 JS 模拟)。因为其支持丰富的图表交互事件 (如 `chart.on('click', handler)`)，可以很方便地实现点选某省份后联动过滤底层表格。

## 3. 待确认疑问 (Open Questions)
1. **ECharts 依赖引入**：由于 Netbox 默认没有集成 ECharts，是否同意通过 `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js` 的形式引入？若只能内网访问，我们可能需要使用较简单的原生 JS 图表或要求用户上传 ECharts 到 static 目录。
2. **“重复故障”判断依据**：我假设的是前 60 天内，“A 端站点相同且 Z 端站点存在交集”的故障可判定为重名路径断点。这与业务常识是否吻合？

## 4. 测试与验证计划 (Verification Plan)
1. 访问新菜单项“故障统计看板”，确保页面能正常加载 ECharts 和过滤表单。
2. 更改过滤表单为“2024年 截至当前”，检查各类 KPI 数值是否正确。
3. 点击“光缆属性 - 自建”饼图区块，检查页面下方的表格是否只显示自建类故障。
4. 验证“重复故障数”计数的 SQL/Python 实现性能，在几千条数据时不会超时。
