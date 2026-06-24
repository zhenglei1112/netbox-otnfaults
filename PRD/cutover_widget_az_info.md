# 需求文档：今明割接任务小组件增加显示割接的AZ端站点信息

## 1. 变更背景与目的
在当前版本中，“今明割接任务”小组件仅显示了割接编号、时间、类型、状态、省份和具体地点以及主管人。为了便于运维人员直观地了解受割接影响的具体段落和网络拓扑，需要在任务卡片中直接展示该割接所涉及的A端站点与Z端站点信息。

## 2. 详细技术方案

### 2.1 后端查询与数据准备
优化 `netbox_otnfaults/dashboard.py` 中的 `OtnTodayTomorrowCutoverWidget` 查询：
1. **防范 N+1 问题**：将 A 端站点（`interruption_location_a`）加入 `select_related`；将 Z 端站点（`interruption_location`）加入 `prefetch_related`。
2. **提取字段**：
   - A端站点名称：`cutover.interruption_location_a.name`
   - Z端站点名称列表（通过逗号拼接）：`site_z = ", ".join([site.name for site in cutover.interruption_location.all()])`

### 2.2 前端页面呈现
修改 `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_today_tomorrow_cutover_widget.html`：
1. **版面规划**：在卡片内的“省份-具体地址”行下方，引入专门的 AZ 站点信息显示排版。
2. **美观设计**：
   - 采用精致的小胶囊标签风格呈现。
   - A端：前缀标为 **A:**，淡蓝色背景。
   - Z端：前缀标为 **Z:**，淡绿色背景。
   - 两端之间使用 `↔` 或箭头图标连接，体现链路连接感。
   - 兼容支持 Netbox 4.x 的日间与夜间暗黑模式下的颜色对比度。

## 3. 验收标准
- 割接卡片上能正确且美观地渲染出 A端 和 Z端 的站点名称。
- 多Z端站点的情况下能够用逗号拼接。
- 卡片无溢出、无乱码，能正常自适应宽度。
