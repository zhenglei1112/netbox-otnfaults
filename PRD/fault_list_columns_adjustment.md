# 故障列表界面默认字段调整方案

## 1. 需求背景
根据用户提供的截图，调整 NetBox 故障（OtnFault）模型列表界面的默认显示字段及其排列顺序，以符合实际业务查看习惯。

## 2. 字段调整明细
目标显示的列及其顺序如下：

| 顺序 | 字段名 (内部) | 显示名称 (UI) |
| :--- | :--- | :--- |
| 1 | `fault_number` | 故障编号 |
| 2 | `fault_category` | 故障分类 |
| 3 | `duty_officer` | 值守人员 |
| 4 | `interruption_location_a` | 故障位置A端站点 |
| 5 | `interruption_location` | 故障位置Z端站点 |
| 6 | `fault_occurrence_time` | 故障中断时间 |
| 7 | `fault_duration` | 故障历时 |
| 8 | `fault_status` | 处理状态 |

## 3. 实现逻辑
修改 `netbox_otnfaults/tables.py` 中的 `OtnFaultTable` 类，更新其 `Meta` 类的以下属性：
- **`default_columns`**: 设置默认显示的列清单及其严格顺序。
- **`fields`**: 同步调整可用字段的总清单顺序，方便用户在“列设置”中查找。

## 4. 任务清单
- [ ] 修改 `d:\Src\netbox-otnfaults\netbox_otnfaults\tables.py` 中的 `OtnFaultTable.Meta`。
- [ ] 移除现有 `default_columns` 中的 `urgency` 和 `tags`（截图未显示）。
- [ ] 调整 `default_columns` 的顺序与截图完全一致。
