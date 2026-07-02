# 修复割接实施下钻跳转错误需求与设计文档

## 1. 问题现象
用户在“故障等级与事件汇总”看板上，点击“割接实施”指标卡片时，页面显示 404 错误（页面未找到）或跳转地址错误。

## 2. 问题根源
- **路由前缀错误**：前端跳转代码 `statistics_dashboard.js` 中将链接硬编码为了 `/plugins/netbox-otnfaults/cutovers/`，而在 Netbox 中由于插件 `base_url` 定义为 `otnfaults`，实际可访问的路径为 `/plugins/otnfaults/cutovers/`。
- **过滤维度不一致**：看板上的“割接实施”是按照割接任务的实际开始时间 `CutoverTask.started_at` 字段来计算的。但是，点击跳转链接中使用的却是计划割接时间 `planned_cutover_time_after` / `planned_cutover_time_before`。这会导致跳转到列表后，筛选出的数据和看板卡片中的数值不一致。
- **缺乏实际时间过滤支持**：`CutoverTaskFilterSet` 与 `CutoverTaskFilterForm` 中并未定义针对实际开始时间 `started_at` 的过滤字段，即使在 URL 传递了相应的参数，后台也无法进行过滤。

## 3. 解决方案与修改内容

### 3.1 后端过滤支持
1. 在 `netbox_otnfaults/filtersets.py` 中的 `CutoverTaskFilterSet` 中增加实际开始时间的范围过滤器：
   - `started_at_after` -> 对应字段 `started_at`，操作符为 `gte`（大于等于）。
   - `started_at_before` -> 对应字段 `started_at`，操作符为 `lte`（小于等于）。

2. 在 `netbox_otnfaults/forms.py` 中的 `CutoverTaskFilterForm` 中增加表单输入项：
   - `started_at_after`，类型为 `forms.DateTimeField`，对应 `计划时间` 或新建 `时间信息` 布局。
   - `started_at_before`，类型为 `forms.DateTimeField`。

### 3.2 前端跳转逻辑修正
1. 修改 `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` 中 `#card-cutover-implemented` 的点击事件处理函数。
2. 将跳转的基准 URL 改为 `/plugins/otnfaults/cutovers/`。
3. 将参数中的 `planned_cutover_time_after` / `planned_cutover_time_before` 替换为 `started_at_after` / `started_at_before`。
4. 使用数组拼接参数，避免没有时间范围过滤时出现 URL解析格式错误（例如 `&` 拼接在没有 `?` 的路径后）。

## 4. 影响与回归测试
- 修改会影响到关于看板的某些断言测试（如 `tests/test_statistics_impact_level.py`），如果有硬编码测试 `card-cutover-implemented` 的跳转或代码匹配，需同步进行微调。
