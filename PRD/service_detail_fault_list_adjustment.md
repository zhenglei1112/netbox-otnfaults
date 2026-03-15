# 业务详情页关联故障列表调整方案

## 1. 需求背景
裸纤业务（BareFiberService）和电路业务（CircuitService）的详情页底部显示了关联的故障影响记录。用户希望该列表的字段项和顺序能与主“故障列表”保持一致，但需要使用一套独立的表格配置，以便能够单独定制。

## 2. 字段调整明细
目标显示的列及其顺序（参考故障主列表）：

| 顺序 | 字段名 (内部) | 对应主故障字段 | 显示名称 (UI) |
| :--- | :--- | :--- | :--- |
| 1 | `otn_fault` | `fault_number` | 故障编号 |
| 2 | `fault_category` | `otn_fault__fault_category` | 故障分类 |
| 3 | `duty_officer` | `otn_fault__duty_officer` | 值守人员 |
| 4 | `interruption_location_a` | `otn_fault__interruption_location_a` | 故障位置A端站点 |
| 5 | `interruption_location` | `otn_fault__interruption_location` | 故障位置Z端站点 |
| 6 | `service_interruption_time` | (业务级时间) | 故障中断时间 |
| 7 | `service_duration` | (业务级历时) | 故障历时 |
| 8 | `fault_status` | `otn_fault__fault_status` | 处理状态 |

## 3. 实现逻辑
1.  **新建表格类**：在 `netbox_otnfaults/tables.py` 中新增 `OtnFaultImpactDetailTable` 类，继承自 `OtnFaultImpactTable`。
2.  **定义关联列**：通过 `accessor='otn_fault__xxx'` 引入主故障的相关信息。
3.  **更新视图**：修改 `netbox_otnfaults/views.py` 中的 `BareFiberServiceView` 和 `CircuitServiceView`，将其 `fault_impacts_table` 的实例化类更改为新定义的 `OtnFaultImpactDetailTable`。

## 4. 任务清单
- [ ] 在 `netbox_otnfaults/tables.py` 中定义 `OtnFaultImpactDetailTable`。
- [ ] 在 `netbox_otnfaults/views.py` 中导入并使用该新表格。
- [ ] 确保新表格在详情页显示时包含 ID (pk) 和 动作 (actions) 字段（虽然通常被 hide，但作为可用项）。
