# 割接管理：整改信息增加“再次割接”自关联字段PRD与实施方案

## 1. 背景与目标
在割接实施过程中，若因客观原因或割接效果不理想（例如割接效果为“未完成”或“不理想”），需要对该位置或业务进行二次整改割接。
为了建立起两次割接任务之间的前后关联关系，方便回溯和闭环管理，现需要在割接模型的**整改信息**部分增加一个字段“再次割接”，用来选择并关联另一个已创建的割接对象。

## 2. 详细设计与字段规则

### 2.1 数据库字段定义 (models.py)
在 `CutoverTask` 模型中增加一个自关联的外键字段：
- **字段名**：`re_cutover`
- **关联对象**：`self`（指向 `CutoverTask` 模型自身）
- **删除策略 (`on_delete`)**：`models.SET_NULL`（当关联的再次割接被删除时，原割接任务不受影响，该字段设为空）
- **约束条件**：可空（`null=True, blank=True`），以便在绝大多数首次成功割接中保持为空
- **反向关联 (`related_name`)**：`previous_cutovers`
- **汉化名称 (`verbose_name`)**：`再次割接`
- **说明提示 (`help_text`)**：`本次割接未完成或效果不理想时，可选择下一次再次割接的任务`

### 2.2 表单字段与布局修改 (forms.py)
- **`CutoverTaskForm`**：
  - 声明 `re_cutover` 字段为 `DynamicModelChoiceField`。
  - 将 `re_cutover` 添加在 `fieldsets` 中的“整改信息”分组最末尾（在 `rectification_completion_description` 之后）。
- **`CutoverTaskBulkEditForm`**：
  - 声明 `re_cutover` 为 `DynamicModelChoiceField`。
  - 添加在 `fieldsets` 和 `nullable_fields` 中，以支持批量编辑和置空操作。
- **`CutoverTaskFilterForm`**：
  - 声明 `re_cutover` 为 `DynamicModelChoiceField`。
  - 添加在 `fieldsets` 中，以支持按再次割接对象进行过滤筛选。
- **`CutoverTaskImportForm`**：
  - 声明 `re_cutover` 字段为 `CSVModelChoiceField`（`to_field_name='cutover_no'`），以支持通过再次割接编号进行 CSV 批量导入。

### 2.3 列表表格显示 (tables.py)
- **`CutoverTaskTable`**：
  - 声明 `re_cutover` 为链接列 `tables.Column(linkify=True, verbose_name='再次割接')`。
  - 将其添加在 `Meta.fields` 列表中（处于 `tags` 和 `actions` 之前）。

### 2.4 过滤器与 API 接口 (filtersets.py & serializers.py)
- **`CutoverTaskFilterSet`**：
  - 在 `Meta.fields` 中注册 `'re_cutover'`。
- **`api/serializers.py`**：
  - 定义 `NestedCutoverTaskSerializer` 作为轻量嵌套序列化器。
  - 在 `CutoverTaskSerializer` 中声明 `re_cutover = NestedCutoverTaskSerializer(required=False, allow_null=True)`。
  - 在 `Meta.fields` 列表中增加 `'re_cutover'` 字段以暴露 API 端口。

### 2.5 前端页面渲染 (cutovertask.html)
In the cutover task detail page, the new field is displayed inside the table of the "整改信息" card:
- It resides between `实际完成时间` and `整改完成情况描述`.
- If a subsequent cutover is set, it renders as a hyperlink via `{{ object.re_cutover|linkify }}`; otherwise, it displays "—".

### 2.6 编辑页面渲染 (cutovertask_edit.html)
Since the edit template uses manual field-by-field rendering instead of automatic fieldsets looping, the `re_cutover` field is manually rendered inside the "整改信息" block:
- Adding `{% render_field form.re_cutover %}` right after `rectification_completion_description`.

---

---

## 3. 数据迁移方案
- 新增一个迁移文件（如 `0081_cutovertask_re_cutover.py`）。
- 手动编写迁移逻辑，向 `netbox_otnfaults_cutovertask` 表添加外键列 `re_cutover_id`，定义相应的外键约束，并在反向迁移中安全删除该列。

## 4. 特殊注意事项与故障排查
在修改完后台 Form、前端模板和数据库模型后，若在割接编辑页面（`/plugins/otnfaults/cutovers/add/` 或 `/plugins/otnfaults/cutovers/<id>/edit/`）中仍然找不到“再次割接”字段，请依次排查以下步骤：
1. **执行数据库迁移**：新外键字段需要在数据库中创建列，请确认已经在容器内运行：
   ```bash
   python manage.py migrate
   ```
2. **重启 Netbox 服务**：由于 Rocky Linux / Docker 的 Python 运行环境会缓存表单类和模板，代码修改后需要重启 gunicorn / django-channels 进程或重启容器：
   ```bash
   docker compose restart
   # 或
   systemctl restart netbox
   ```
3. **确认本地分支代码已拉取**：检查 `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html` 与 `forms.py` 文件是否确实包含最新的 `re_cutover` 代码。

