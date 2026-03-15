# 故障影响业务列表界面默认字段调整方案

## 1. 需求背景
根据用户提供的截图，调整 NetBox 故障影响业务（OtnFaultImpact）模型主列表界面的默认显示字段及其排列顺序。

## 2. 字段调整明细
目标显示的列及其顺序如下：

| 顺序 | 字段名 (内部) | 显示名称 (UI) | 说明 |
| :--- | :--- | :--- | :--- |
| 1 | `pk` | ID | 需在 default_columns 中显式包含 |
| 2 | `service_type` | 业务类型 | |
| 3 | `service_name` | 业务名称 | |
| 4 | `service_interruption_time` | 业务故障时间 | |
| 5 | `service_recovery_time` | 业务恢复时间 | |
| 6 | `service_duration` | 故障历时 | |
| 7 | `otn_fault` | 直接故障 | |

## 3. 实现逻辑
修改 `netbox_otnfaults/tables.py` 中的 `OtnFaultImpactTable` 类，更新其 `Meta` 类的以下属性：
- **`default_columns`**: 设置默认显示的列清单及其严格顺序。
- **`fields`**: 同步调整列表顺序。

## 4. 任务清单
- [ ] 修改 `d:\Src\netbox-otnfaults\netbox_otnfaults\tables.py` 中的 `OtnFaultImpactTable.Meta`。
- [ ] 将 `pk` 加入 `default_columns`。
- [ ] 确保 `otn_fault` 移动到最后。
- [ ] 移除 `tags`。
