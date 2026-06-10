# 割接任务新增“割接类型”字段需求与实施计划

## 1. 需求背景与功能说明
为割接任务模型（`CutoverTask`）增加一个割接类型字段（`cutover_type`）。该字段为选择型字段，包含以下三个选项：
1. **光缆割接**（键值：`fiber`，展示值：光缆割接，预设颜色：蓝色）
2. **电源割接**（键值：`power`，展示值：电源割接，预设颜色：橙色）
3. **机房搬迁**（键值：`room_migration`，展示值：机房搬迁，预设颜色：绿色）

默认值为 `fiber`（光缆割接），以兼容存量数据。

## 2. 影响范围与修改方案

### 2.1 数据库与模型层 (`models.py`)
- **[MODIFY] [models.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/models.py)**
  1. 定义 `CutoverTypeChoices(ChoiceSet)` 选择集：
     ```python
     class CutoverTypeChoices(ChoiceSet):
         key = 'CutoverTask.cutover_type'
         FIBER = 'fiber'
         POWER = 'power'
         ROOM_MIGRATION = 'room_migration'
         CHOICES = [
             (FIBER, '光缆割接', 'blue'),
             (POWER, '电源割接', 'orange'),
             (ROOM_MIGRATION, '机房搬迁', 'green'),
         ]
     ```
  2. 在 `CutoverTask` 模型中增加 `cutover_type` 字段：
     ```python
     cutover_type = models.CharField(
         max_length=50,
         choices=CutoverTypeChoices,
         default=CutoverTypeChoices.FIBER,
         verbose_name='割接类型'
     )
     ```
  3. 为 `CutoverTask` 提供颜色提取方法：
     ```python
     def get_cutover_type_color(self) -> str | None:
         return CutoverTypeChoices.colors.get(self.cutover_type)
     ```

### 2.2 表单层 (`forms.py`)
- **[MODIFY] [forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py)**
  1. 导入 `CutoverTypeChoices`。
  2. `CutoverTaskForm`：
     - 在 `Meta.fields` 中加入 `'cutover_type'`。
     - 在 `fieldsets` 的 `割接信息` 组内，将 `'cutover_type'` 加入到 `'status'` 后面。
  3. `CutoverTaskFilterForm`：
     - 新增 `cutover_type = forms.ChoiceField(choices=add_blank_choice(CutoverTypeChoices), required=False, label='割接类型')` 字段。
     - 在 `fieldsets` 的 `'cutover_no'` / `'status'` 后面引入 `'cutover_type'`。
  4. `CutoverTaskImportForm`：
     - 在 `Meta.fields` 中加入 `'cutover_type'`。
  5. `CutoverTaskBulkEditForm`：
     - 新增 `cutover_type = forms.ChoiceField(choices=add_blank_choice(CutoverTypeChoices), required=False, label='割接类型')` 字段。
     - 在 `fieldsets` 的 `'status'` 后面引入 `'cutover_type'`。

### 2.3 列表渲染层 (`tables.py`)
- **[MODIFY] [tables.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/tables.py)**
  1. 导入 `CutoverTypeChoices`。
  2. 在 `CutoverTaskTable` 中增加：
     ```python
     cutover_type = columns.ChoiceFieldColumn(verbose_name='割接类型')
     ```
  3. 在 `Meta.fields` 与 `Meta.default_columns` 中把 `'cutover_type'` 加到 `'status'` 字段的后方。
  4. 增加相应渲染和导出转换逻辑：
     ```python
     def render_cutover_type(self, value, record):
         color = record.get_cutover_type_color() or 'secondary'
         return format_html('<span class="badge bg-{} text-white">{}</span>', color, record.get_cutover_type_display())

     def value_cutover_type(self, value: str | None, record: CutoverTask) -> str:
         return _display_or_empty(record.get_cutover_type_display())
     ```

### 2.4 过滤器层 (`filtersets.py`)
- **[MODIFY] [filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py)**
  1. 导入 `CutoverTypeChoices`。
  2. 在 `CutoverTaskFilterSet` 的 `Meta.fields` 中增加 `'cutover_type'`。

### 2.5 API序列化层 (`api/serializers.py`)
- **[MODIFY] [serializers.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/api/serializers.py)**
  1. 在 `CutoverTaskSerializer` 的 `Meta.fields` 中增加 `'cutover_type'`。

### 2.6 模板展示与编辑层
- **[MODIFY] [cutovertask.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)**
  在“状态”列下方，渲染割接类型字段：
  ```html
  <tr>
    <th scope="row">割接类型</th>
    <td>
      <span class="badge bg-{{ object.get_cutover_type_color|default:'secondary' }} text-white">{{ object.get_cutover_type_display|default:"—" }}</span>
    </td>
  </tr>
  ```
- **[MODIFY] [cutovertask_edit.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html)**
  在 `form.status` 字段下方渲染新增字段：
  ```html
  {% render_field form.cutover_type %}
  ```

## 3. 验证计划
由于没有实际运行的 Netbox 容器环境，我们将通过以下方式进行验证：
1. **静态代码检查**：检查所有引用 `cutover_type` 字段的文件是否导入正确，且语法无误。
2. **单元测试验证**：运行现有的单元测试，确认原有割接测试和表单验证全部通过：
   - `python manage.py test netbox_otnfaults.tests.test_cutover_edit_template`
   - `python manage.py test netbox_otnfaults.tests.test_cutover_management_scaffold`
3. **数据库迁移生成**：在能够运行命令的终端下，尝试运行 `makemigrations` 生成对应的割接类型字段迁移文件。
