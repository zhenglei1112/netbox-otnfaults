# 故障类型英转中映射脚本实施计划

## 1. 需求分析
用户需要编写一个NetBox自定义脚本，将系统中历史存在的英文故障类型（`power`, `device`, `fiber`, `other`, `pigtail`）映射并更新为现有的中文故障类型对应的系统内部标识（Choices）。

现有中文选项定义（位于 `models.py` 的 `FaultCategoryChoices`）：
- `fiber_break`: 光缆中断
- `ac_fault`: 空调故障
- `fiber_degradation`: 光缆劣化
- `fiber_jitter`: 光缆抖动
- `device_fault`: 设备故障
- `power_fault`: 供电故障

根据既往逻辑（如 `weekly_fault_report.py` 中遗留的映射逻辑）：
- `power` -> `power_fault` (供电故障)
- `device` -> `device_fault` (设备故障)
- `fiber` -> `fiber_break` (光缆故障/中断)
- `pigtail` -> `ac_fault` (在历史代码中pigtail映射为空调故障)
- `other` -> 现有无“其他”分类，将其置空 (`None`) 或保留，这里考虑将其置空。

## 2. 实施方案
### 2.1 编写修复脚本
在 `netbox_otnfaults/scripts/` 目录下创建新脚本 `update_fault_types.py`。
该脚本继承自 `Script`（NetBox 自定义脚本标准）。
脚本执行时：
1. 遍历所有 `OtnFault` 数据。
2. 检查 `fault_category` 字段。
3. 如果满足旧的英文名称，则修改为对应的标准Choice关键字，并记录日志。
4. 使用 `commit` 变量控制是否真正保存到数据库。

### 2.2 修复 `weekly_fault_report.py`（附带）
原本的报表代码里硬编码了 `power`, `fiber` 等关键字，故障类型迁移后，相关的 `get_top_power_fault_sites` 等方法中的判定需要改为新的标准字典，保证报表在数据更新后依旧可用。

## 3. 任务分解
1. [x] 撰写实施计划。
2. [ ] 编写数据迁移修复脚本 `scripts/update_fault_types.py`。
3. [ ] 修复并调整 `scripts/weekly_fault_report.py` 中的过时映射逻辑。
