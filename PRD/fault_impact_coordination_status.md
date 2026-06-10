# 故障管理：故障影响业务模型增加“协调状态”字段及割接同步功能 PRD

## 1. 背景与目标
在割接任务中，针对受影响的业务会记录“协调状态”（包括已批准、未批准、强制割接）。当该割接任务产生问题或因割接需要直接通过系统界面“生成故障信息”时，为了实现业务信息的完全回溯，需要将原割接受影响业务的“协调状态”也同步携带至生成的“故障影响业务”中。
为此，需要在**故障影响业务模型**中增加同样的“协调状态”字段，并在“通过割接生成故障”时，自动实现该字段的同步与赋值。

## 2. 详细设计与字段规则

### 2.1 数据库字段定义 (models.py)
在 `OtnFaultImpact` 模型中增加以下字段：
- **字段名**：`coordination_status`
- **数据类型**：`models.CharField` (max_length=32)
- **可选值**：直接复用割接影响业务中定义的 `CutoverCoordinationStatusChoices`
  - `'approved'` (已批准，即已协调) -> 绿色
  - `'unapproved'` (未批准) -> 红色
  - `'forced'` (强制割接) -> 橙色
- **默认值**：`CutoverCoordinationStatusChoices.APPROVED` ('approved'，作为已协调的默认值，兼容历史数据)
- **辅助属性**：在模型上定义 `get_coordination_status_color(self)` 以供前端模板使用。

### 2.2 割接生成故障信息逻辑同步 (services/cutover_fault_generation.py)
在 `create_fault_from_cutover` 业务逻辑函数中：
- 遍历源割接任务受影响的业务时，对于创建的 `OtnFaultImpact` 实例，将 `coordination_status` 赋值为原 `CutoverImpact` 中的 `coordination_status`。

### 2.3 UI 表单定义 (forms.py)
- **`OtnFaultImpactForm`** (单实例新建与编辑)：
  - 在 `Meta.fields` 中加入 `'coordination_status'`。
- **`OtnFaultImpactBulkEditForm`** (批量编辑表单)：
  - 声明 `coordination_status = forms.ChoiceField(choices=add_blank_choice(CutoverCoordinationStatusChoices), required=False, label='协调状态')`。
  - 将字段增加至表单 fieldsets 与 `Meta.nullable_fields`（支持批量编辑和置空）。
- **`OtnFaultImpactImportForm`** (批量 CSV 导入)：
  - 在 `Meta.fields` 列表中增加 `'coordination_status'`。
- **`OtnFaultImpactFilterForm`** (过滤器表单)：
  - 声明为 `MultipleChoiceField` 并启用多选以支持复选过滤。

### 2.4 表格及过滤器设计 (tables.py & filtersets.py & views.py)
- **`OtnFaultImpactTable`**：
  - 新增列 `coordination_status = columns.ChoiceFieldColumn(verbose_name='协调状态')`。
  - 将列添加至 `Meta.fields` 与 `Meta.default_columns`。
- **`OtnFaultImpactFilterSet`**：
  - 在 `Meta.fields` 列表中加入 `'coordination_status'` 支持后端过滤。
- **动态隐藏列逻辑 (`views.py`)**：
  - 在故障详情视图 `OtnFaultView.get_extra_context` 中，若当前故障的 `interruption_reason != 'cable_rectification'` 或 `interruption_reason_detail != 'planned_reporting'`，则动态通过 `table.exclude = ('coordination_status',)` 在影响业务的 Summary 列表中隐藏协调状态列。

### 2.5 接口序列化 (api/serializers.py)
- **`OtnFaultImpactSerializer`**：
  - 在 `Meta.fields` 和 `brief_fields` 列表中增加 `'coordination_status'` 字段，以供 API 数据消费。

### 2.6 前端详情模板渲染 (otnfaultimpact.html)
- 在故障影响业务详情页的“影响业务详情”属性表格中，于“业务影响”行后，在**故障原因为“光缆整改 / 计划报备”的条件下**添加“协调状态”行：
  ```html
  {% if object.otn_fault and object.otn_fault.interruption_reason == 'cable_rectification' and object.otn_fault.interruption_reason_detail == 'planned_reporting' %}
  <tr>
      <th scope="row">协调状态</th>
      <td>{% badge object.get_coordination_status_display bg_color=object.get_coordination_status_color %}</td>
  </tr>
  {% endif %}
  ```

---

## 3. 数据库迁移方案
- 新增一个迁移文件 `0082_otnfaultimpact_coordination_status.py`，向表 `netbox_otnfaults_otnfaultimpact` 动态添加 `coordination_status` 字段列及其默认约束。
