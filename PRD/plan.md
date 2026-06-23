# 故障模型省份必填与割接超时/影响非必填及协调状态修改方案

## 1. 需求背景
根据业务需要，为了规范数据的完整性，并优化用户的填写体验，现需对以下字段的约束及布局进行调整：
1. 在故障（`OtnFault`）模型中，省份字段（`province`）必须成为必填字段，避免出现未归属省份的物理故障。
2. 在割接任务（`CutoverTask`）模型中，割接是否超时字段（`is_timeout`）不需要强制必填，改为非必填字段。
3. 在割接影响业务（`CutoverImpact`）模型中：
   - 将“业务影响”（`business_impact`）和“业务故障时间”（`service_interruption_time`）都设置为非必填。
   - 对“协调状态”（`coordination_status`）字段，增加 **“待协调”**（`pending`）选项并将其作为默认值。
   - 在割接影响业务的编辑表单中，将“协调状态”字段由“影响时间”组移入“业务信息”组。
4. 在割接时间重新生成时，联动清除状态的逻辑改为将协调状态重置为最新的默认值 **“待协调”**（`pending`）。

## 2. 字段修改逻辑

### 2.1 故障模型 (OtnFault)
- **目标字段**：`province` (省份)
- **修改位置**：`netbox_otnfaults/models.py` 中的 `OtnFault` 类。
- **修改详情**：
  将 `province = models.ForeignKey(..., blank=True, null=True)` 的 `blank=True, null=True` 移除。
- **表单配合**：`netbox_otnfaults/forms.py` 中的 `OtnFaultForm.province` 字段需将 `required=False` 修改为 `required=True`。

### 2.2 割接模型 (CutoverTask)
- **目标字段**：`is_timeout` (割接是否超时)
- **修改位置**：`netbox_otnfaults/models.py` 中的 `CutoverTask` 类。
- **修改详情**：
  将 `is_timeout` 字段添加 `blank=True` 选项。

### 2.3 割接影响业务模型 (CutoverImpact)
- **目标字段**：`business_impact` (业务影响) 与 `service_interruption_time` (业务故障时间)
- **修改位置**：`netbox_otnfaults/models.py` 中的 `CutoverImpact` 类。
- **修改详情**：
  - 将 `business_impact` 字段添加 `blank=True` 选项。
  - 将 `service_interruption_time` 字段添加 `blank=True, null=True` 属性。
- **目标字段**：`coordination_status` (协调状态)
- **修改位置**：
  - `netbox_otnfaults/models.py` 中的 `CutoverCoordinationStatusChoices` 选择类增加 `PENDING = 'pending'`（文案：'待协调'，颜色：'blue'），并放在 CHOICES 列表的首位。
  - `CutoverImpact.coordination_status` 字段的 `default` 设为 `CutoverCoordinationStatusChoices.PENDING`。
- **表单布局修改**：
  - 在 `forms.py` 的 `CutoverImpactForm` 表单的 `fieldsets` 中，将 `'coordination_status'` 从 `'影响时间'` 的 FieldSet 移入 `'业务信息'` 的 FieldSet。
- **关联逻辑修改**：
  - 在 `views.py` 中重新生成割接时间时，将 impacts 列表状态更新中的 `coordination_status` 设为 `CutoverCoordinationStatusChoices.PENDING`。

## 3. 数据库迁移
更新 Django 迁移文件 `netbox_otnfaults/migrations/0088_alter_otnfault_province_and_more.py`：
- 依赖迁移：`0087_statistics_query_indexes`
- 修改操作：
  - `AlterField` on `OtnFault.province` (`null=False`)
  - `AlterField` on `CutoverTask.is_timeout` (`blank=True`)
  - `AlterField` on `CutoverImpact.business_impact` (`blank=True`)
  - `AlterField` on `CutoverImpact.service_interruption_time` (`null=True`)
  - `AlterField` on `CutoverImpact.coordination_status` (更新 choices 并在数据库层面变更默认值)

## 4. 实施步骤
1. 提请用户审核本方案；
2. 审核通过后，修改 `models.py` 字段定义；
3. 修改 `forms.py` 表单字段约束及布局；
4. 修改 `views.py` 关联的默认值更新逻辑；
5. 编写并更新 `0088_alter_otnfault_province_and_more.py` 迁移文件；
6. 运行全部单元测试进行校验。
