# 裸纤业务模型详情页增加故障影响业务的时间过滤与统计 - 需求文档与实施计划

## 1. 需求背景
在“裸纤业务” (BareFiberService) 的详情页中，当前已展示了关联的故障影响业务 (OtnFaultImpact) 列表。用户希望能够按照时间维度对这些业务进行快速过滤，并直观地查看汇总的故障统计数据，包括：
- 故障数量
- 总故障时长
- 平均故障时长

时间过滤维度包括：本周、本月、本年、过去七天、过去一个月。过滤基准为“故障中断时间” (`service_interruption_time`)。

## 2. 需求详情

### 2.1 界面交互
- 在“关联的故障影响业务”卡片的表头 (或紧接其下的区域)，增加五个过滤按钮：
  - 本周
  - 本月
  - 本年
  - 过去七天
  - 过去一个月
  - (可选)增加“全部”按钮以重置过滤。
- 在表格上方展示统计数据汇总区域：
  - **故障数量**: X 次
  - **总故障时长**: X 小时 (或拆分为天/小时/分)
  - **平均故障时长**: X 小时

### 2.2 数据过滤与统计逻辑
- **时间范围计算** (以当前系统时间为准):
  - 本周：本周一 00:00 起
  - 本月：本月1日 00:00 起
  - 本年：本年1月1日 00:00 起
  - 过去七天：当前时间往前推 7*24 小时 (或日期往前推7天)
  - 过去一个月：当前时间往前推 30 天
- **统计字段算式**:
  - `故障数量` = 过滤后结果集的个数
  - `总故障时长` = 汇总所有包含 `service_interruption_time` 和 `service_recovery_time` 的记录的持续时间。
  - `平均故障时长` = `总故障时长` / 有恢复时间的故障数量 (或总故障数量)。

## 3. 实施计划

### 3.1 修改 `netbox_otnfaults/views.py`
在 `BareFiberServiceView` 的 `get_extra_context` 方法中：
1. **解析查询参数**: 读取 `time_filter` GET 参数。
2. **构建时间过滤条件**:
   - 使用 `django.utils.timezone.now()` 获取当前时间。
   - 根据选定的 `time_filter` 构造 `created_after` 边界并应用于 `instance.fault_impacts.filter(service_interruption_time__gte=...)`。
3. **计算统计数据**:
   - 遍历过滤后的查询集，若记录拥有有效的 `service_recovery_time`，累加 `(service_recovery_time - service_interruption_time).total_seconds()` 到总时长。
   - 统计符合条件的条目数。
   - 将秒数转换并格式化为 `XX.XX小时` 或者 `X天X小时`。
4. **注入 Context**:
   - 将 `time_filter` 及相关统计计算结果（故障数、总时长、平均时长）以及过滤后的表格对象返回到模板。

### 3.2 修改 `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice.html`
1. **添加时间过滤按钮栏**:
   - 在表格上方使用 Bootstrap 5 的 `btn-group` 或一组 `btn`，绑定对应查询串如 `?time_filter=this_week`。高亮当前选中的过滤项。
2. **添加统计数据展示区**:
   - 展现 "故障数量"、"总故障时长"、"平均故障时长"。可以使用 Bootstrap 的 `badge` 或小卡片展示。
3. **保留当前页码相关参数(可选)**: 确保如果点击过滤就定位到第一页，这可以通过仅设置 `?time_filter=xxx` 来实现。如果变更分页数量需要保留 `time_filter`，修改分页控件里的 URL。

## 4. 影响范围
- `views.py` 中的 `BareFiberServiceView`
- `templates/netbox_otnfaults/barefiberservice.html`

## 5. 验证方式
- 访问具有不同时间跨度历史故障数据的裸纤业务。
- 逐个点击时间过滤按钮，检查相关表格行数目以及统计数据的正确性。
