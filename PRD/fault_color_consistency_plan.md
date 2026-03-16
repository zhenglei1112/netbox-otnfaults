# 故障分类颜色一致性修正方案

## 问题分析
用户反馈故障分类（`fault_category`）在不同列表中的颜色显示不一致。
根据代码和截图分析：
1. `OtnFault` 模型定义了 `FaultCategoryChoices`，包含颜色定义（如 `fiber_break` 为 `red`）。
2. 在 `OtnFaultTable` 等表格中，`fault_category` 使用了 `columns.ChoiceFieldColumn`。
3. 在业务详情页的 `OtnFaultImpactDetailTable` 中，该字段通过 `accessor='otn_fault__fault_category'` 跨表访问。
4. **根本原因**：当 `ChoiceFieldColumn` 使用 `accessor` 跨关系访问字段时，NetBox 往往无法自动关联到原始模型字段定义的 `choices` 和颜色映射，导致回退到默认的灰色背景。

## 解决方案
在 `tables.py` 中，为所有使用 `ChoiceFieldColumn` 的列明确指定 `choices` 参数。这将强制表格列使用指定的选项集（及其关联的颜色映射）。

## 任务清单
- [ ] 修改 `netbox_otnfaults/tables.py`：
    - 从 `.models` 导入所有的 ChoiceSet 类。
    - 为 `OtnFaultTable` 中的 `ChoiceFieldColumn` 字段（`fault_category`, `urgency`, `fault_status` 等）添加 `choices` 参数。
    - 为 `ContractOtnFaultTable` 中的相应字段添加 `choices` 参数。
    - 为 `OtnFaultImpactDetailTable` 中的 `fault_category` 添加 `choices=FaultCategoryChoices`。
    - 为 `OtnFaultImpactTable` 中的 `service_type` 添加 `choices=ServiceTypeChoices`。

## 详细修改计划

### 1. 修改 `tables.py` 导入
```python
from .models import (
    OtnFault, OtnFaultImpact, OtnPath, OtnPathGroup, OtnPathGroupSite, 
    PathGroupSiteRoleChoices, BareFiberService, CircuitService,
    FaultCategoryChoices, FaultStatusChoices, UrgencyChoices, 
    MaintenanceModeChoices, RecoveryModeChoices, ResourceTypeChoices, 
    CableRouteChoices, CableBreakLocationChoices, ServiceTypeChoices
)
```

### 2. 更新 `OtnFaultTable`
```python
    fault_category = columns.ChoiceFieldColumn(
        choices=FaultCategoryChoices,
        verbose_name='故障分类'
    )
    # ... 对其他选择字段同样处理 ...
```

### 3. 更新 `OtnFaultImpactDetailTable` (关键 fix)
```python
    fault_category = columns.ChoiceFieldColumn(
        accessor='otn_fault__fault_category',
        choices=FaultCategoryChoices,
        verbose_name='故障分类'
    )
```
