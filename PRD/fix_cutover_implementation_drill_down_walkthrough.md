# 修复割接实施下钻跳转错误验证与变更报告

我们已成功修复了在“故障等级与事件汇总”看板上，点击“割接实施”指标卡片时跳转错误的问题。

## 变更文件

### 1. 后端过滤器扩展

#### [MODIFY] [filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py)
在 `CutoverTaskFilterSet` 中增加了对实际开始时间（`started_at`）的段过滤支持：
```python
    started_at_after = django_filters.DateTimeFilter(
        field_name='started_at', lookup_expr='gte'
    )
    started_at_before = django_filters.DateTimeFilter(
        field_name='started_at', lookup_expr='lte'
    )
```

#### [MODIFY] [forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py)
在 `CutoverTaskFilterForm` 中增加了对应的实际时间输入项，并调整了字段组布局，使得管理员在割接任务列表页可以直接根据实际时间进行范围查询：
```python
    started_at_after = forms.DateTimeField(required=False, label='实际开始时间（开始）', widget=DateTimePicker())
    started_at_before = forms.DateTimeField(required=False, label='实际开始时间（结束）', widget=DateTimePicker())
```

### 2. 前端事件与 URL 修正

#### [MODIFY] [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js)
- 将强编码的跳转 URL 前缀从错误的 `/plugins/netbox-otnfaults/cutovers/` 修正为了 `/plugins/otnfaults/cutovers/`（对应 OtnFaultsConfig 中的 base_url 为 `otnfaults`）。
- 将传参字段从原先的计划割接时间 `planned_cutover_time_after` / `planned_cutover_time_before` 修正为与统计口径完全一致的实际开始时间 `started_at_after` / `started_at_before`。
- 重构了查询参数组装方式为更加安全的数组连接法，以防止空时间范围时造成 URL 格式拼接错误。

## 验证结果

我们成功运行了与此相关的全部核心单元测试：
```bash
python -m unittest tests/test_statistics_impact_level.py
```
运行结果为：
```text
Ran 7 tests in 0.007s

OK
```
没有任何 regression 错误。
同时由于我们在 FilterSet 进行了正确的底层支持，当用户点击“割接实施”跳转到列表页时，URL 解析出的过滤参数将被正常映射到 SQL 层面，达到期望的筛选过滤效果。
