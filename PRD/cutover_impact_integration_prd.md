# 割接管理中关联业务整合至影响业务PRD与实施方案

## 1. 背景与目标

目前割接管理中存在两套业务关联体系：
1. **关联业务**：存储在 `CutoverTask.related_customers` 中的 JSON 数据，用于记录关联的裸纤业务、协调状态和协调时间。
2. **影响业务**：通过 `CutoverImpact` 实体模型存储的关联记录，可关联裸纤或电路业务，并记录中断时间、恢复时间等。

为了统一数据结构，简化维护逻辑，现将**关联业务**部分整合成并入**影响业务**（关联业务不再使用）。
同时做以下修正：
- 将原有的“已协调”字段名修改为“协调状态”，作为选择型字段，选项为：已批准、未批准、强制割接。
- 取消原关联业务中的“协调时间”字段。

---

## 2. 数据库与模型设计

### 2.1 新增/修改字段

在 `CutoverImpact` 模型（位于 [models.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/models.py)）中新增协调状态字段：

1. **ChoiceSet 定义**
   ```python
   class CutoverCoordinationStatusChoices(ChoiceSet):
       key = 'CutoverImpact.coordination_status'

       APPROVED = 'approved'
       UNAPPROVED = 'unapproved'
       FORCED = 'forced'

       CHOICES = [
           (APPROVED, '已批准', 'green'),
           (UNAPPROVED, '未批准', 'red'),
           (FORCED, '强制割接', 'orange'),
       ]
   ```

2. **`CutoverImpact` 新增字段**
   ```python
   coordination_status = models.CharField(
       max_length=32,
       choices=CutoverCoordinationStatusChoices,
       default=CutoverCoordinationStatusChoices.UNAPPROVED,
       verbose_name='协调状态'
   )
   ```

### 2.2 废弃/删除字段

1. 从 `CutoverTask` 模型中废除并删除 `related_customers` 字段。
2. 数据迁移完毕后删除该字段的数据库列。

---

## 3. 数据迁移方案

编写数据迁移（Data Migration），在删除 `CutoverTask.related_customers` 前，将现有数据提取并写入 `CutoverImpact` 中：

- **迁移映射逻辑**：
  - 遍历每个 `CutoverTask`，解析其中的 `related_customers` JSON 数组。
  - 对于其中的每个业务项：
    - 若 `service_id` 指向的 `BareFiberService` 存在：
      - 检查当前割接任务下是否已存在该裸纤业务的 `CutoverImpact` 记录。
      - 若不存在，创建新的 `CutoverImpact`：
        - `cutover_task` = 当前 task
        - `service_type` = `'bare_fiber'`
        - `bare_fiber_service_id` = `service_id`
        - `service_site_a` = `task.interruption_location_a`
        - `service_interruption_time` = `task.planned_cutover_time` 或 `timezone.now()` (若为空)
        - `coordination_status` = `'approved'` (如果 `is_coordinated` 为 True) 或 `'unapproved'` (如果 `is_coordinated` 为 False)。
      - 若已存在，则仅更新其 `coordination_status`。

---

## 4. 后端表单、视图与过滤 (Python)

### 4.1 表单修改 ([forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py))
- **`CutoverTaskForm`**：
  - 删除 `related_customers` 表单字段定义及 clean 校验方法。
  - 从 `fieldsets` 中移除 `FieldSet('related_customers', name='关联业务')`。
- **`CutoverTaskImportForm`**：
  - 从 `Meta.fields` 中移除 `related_customers`。
- **`CutoverImpactForm`**：
  - 添加 `coordination_status` 表单字段。
  - 将 `coordination_status` 加进 `fieldsets` 的“业务信息”或“其他”栏中。
- **`CutoverImpactBulkEditForm`**：
  - 增加 `coordination_status` 字段定义。
- **`CutoverImpactFilterForm`**：
  - 增加 `coordination_status` 的选择过滤字段。

### 4.2 视图修改 ([views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/views.py))
- **`CutoverTaskRelatedCustomersView`**：
  - 彻底删除此 View。
- **`CutoverTaskGeneratePlannedTimeView`**：
  - 当生成新的计划时间时，重置所有影响业务的协调状态：
    ```python
    task.impacts.all().update(coordination_status=CutoverCoordinationStatusChoices.UNAPPROVED)
    ```
- **`CutoverTaskView` 和 `CutoverTaskEditView`**：
  - 移除对 `bare_fiber_services` 的上下文构建（之前是传给前端 JS Modal 渲染关联业务选择用的，现在不需要了）。

### 4.3 表格修改 ([tables.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/tables.py))
- **`CutoverImpactTable`**：
  - 在 `Meta.fields` 和 `Meta.default_columns` 中新增 `coordination_status` 列，放在 `actions` 列的前面。
  - 新增渲染函数 `render_coordination_status`，使用 Choice 对应的颜色标签渲染。
- **`CutoverImpactSummaryTable`**：
  - 同上，将 `coordination_status` 包含进 `Meta.fields`，并隐藏 `pk` 等列。

### 4.4 过滤器修改 ([filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py))
- **`CutoverImpactFilterSet`**：
  - 在 `Meta.fields` 中添加 `coordination_status`。

### 4.5 路由修改 ([urls.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/urls.py))
- 删除 `cutovers/<int:pk>/related-customers/` 路由定义。

### 4.6 序列化修改 ([api/serializers.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/api/serializers.py))
- **`CutoverTaskSerializer`**：
  - 移除 `related_customers`。
- **`CutoverImpactSerializer`**：
  - 新增 `coordination_status`。

---

## 5. 前端模板修改 (HTML / JS)

### 5.1 编辑页 ([cutovertask_edit.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html))
- 删除原有的“设置关联业务”的 JS 弹窗结构及 `initRelatedCustomers` 的全部代码（包括 Table 初始化、Modal 绑定和 Flatpickr 绑定等）。
- 在模板中，删除 `{% render_field form.related_customers %}`。

### 5.2 详情页 ([cutovertask.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html))
- 彻底移除关联业务的表单 `<form method="post" action="..." id="cutover-related-customers-form">` 及其相关 HTML、弹窗和底部初始化逻辑脚本。
- 影响业务表格将由于我们在 Table 类中增加了 `coordination_status` 而自动呈现在页面上，无需手动更改表格渲染块。
- 对“计划割接时间”卡片进行 UI 精简：
  - 不再显示“主计划时间”这一行（从卡片体内的表格中移除）。
  - 将原本位于卡片标题栏右侧的 `planned_cutover_time` 时间选择输入框从标题行中移除。
- 在计划时间弹窗中：
  - 将时间选择输入控件放置在弹出 Modal 窗口体内最上方，并设置最大宽度为 `250px`（避免控件撑满导致过长），同时为该 input 设置 `value` 默认值（如果割接任务已有计划时间则默认填充，否则为空）。
  - 将提示文字移动至时间选择控件的下方，使用柔和的警告框样式（`alert alert-warning` 带左侧橙色边线及警告图标）包装，并将字体字号调大（`0.925rem`，移除原本的 `small text-muted` 样式），起到更醒目的警示作用。
  - 当在 Modal 中点击“确认生成”时，使用 JS 校验输入时间非空（`reportValidity()`），验证通过后才执行表单异步提交。
- 在计划割接时间的历史记录列表中，将最新一条记录前面的“第N次”次数标识 Badge 颜色从灰色（`bg-secondary`）变更为与右侧最新旗标一致的绿色（`bg-success`），同时将其时钟图标和时间文本修改为绿色加粗（`fw-bold text-success`），以统一和突出最新一期的 UI 效果。

---

## 6. 验证方案

1. **测试用例**：
   - 创建新割接任务，随后添加一条或多条“影响业务”（例如关联裸纤业务）。
   - 编辑“影响业务”，将其“协调状态”修改为“已批准”或“强制割接”。
   - 在割接详情页查看该影响业务的状态是否正确显示。
   - 点击“生成新的割接时间”，输入新时间，确认生成，查看是否自动重置所有影响业务的协调状态为“未批准”。
2. **数据迁移验证**：
   - 验证迁移后，旧的关联业务记录被成功转换为 CutoverImpact 记录，且协调状态映射正确。
