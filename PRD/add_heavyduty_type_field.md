# 重要保障模型增加“类型”字段需求文档 (PRD)

## 1. 需求背景与概述
为了更好地对重要保障（`HeavyDuty`）信息进行分类管理，现需要在重要保障模型中新增一个“类型”字段。
该字段的类型可选值如下：
- **重要保障** (Choice: `important`)：对应重保时期的保障任务。
- **公司通知** (Choice: `notice`)：公司内部发布的正式通知或公告。
- **值班备忘** (Choice: `memo`)：日常值班的备忘录或记录信息。

此修改涉及后端数据模型、迁移脚本、表单过滤、管理表格、序列化器 API 以及前端大屏聚合数据接口和详情页展示。

---

## 2. 详细设计方案

### 2.1 数据模型 (Models)
在 [models.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/models.py) 中：
- 定义选项集 `HeavyDutyTypeChoices`，继承自 `ChoiceSet`。
- 为 `HeavyDuty` 模型新增 `type` 字段：
  ```python
  type = models.CharField(
      max_length=50,
      choices=HeavyDutyTypeChoices,
      default=HeavyDutyTypeChoices.IMPORTANT,
      verbose_name='类型'
  )
  ```
- 为 `HeavyDuty` 增加 `get_type_color(self)` 辅助方法，以便在模板和表格中为不同的类型呈现对应的 Badge 颜色。

### 2.2 表格设计 (Tables)
在 [tables.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/tables.py) 的 `HeavyDutyTable` 中：
- 新增 `type` 字段列。
- 在 `Meta.fields` 和 `Meta.default_columns` 中把 `'type'` 加到适当位置（如在 `'name'` 之后）。
- 实现 `render_type` 和 `value_type` 以便按状态 Badge 显示不同的类型：
  - “重要保障”：蓝色 (blue)
  - “公司通知”：绿色 (green)
  - “值班备忘”：橙色 (orange)

### 2.3 表单设计 (Forms)
在 [forms.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/forms.py) 中：
- `HeavyDutyForm`：在 `Meta.fields` 中增加 `'type'`，并在 `fieldsets` 中的 `重要保障基本信息` 里新增 `'type'` 字段以支持新增/修改时选择类型。
- `HeavyDutyFilterForm`：添加 `type` 的下拉筛选字段，并将其加入到 fieldsets 的第一组。
- `HeavyDutyImportForm`：在 `Meta.fields` 中加入 `'type'`，支持 CSV 导入时解析该字段。
- `HeavyDutyBulkEditForm`：添加 `type` 的下拉选择，并将其加入到 fieldsets 的 `重保信息` 组中，支持批量修改。

### 2.4 过滤设计 (FilterSets)
在 [filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py) 的 `HeavyDutyFilterSet` 中：
- 增加 `'type'` 到 `Meta.fields`，以便支持在后端接口与前端查询时按类型过滤。

### 2.5 序列化与 API (Serializers & API)
在 [api/serializers.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/api/serializers.py) 的 `HeavyDutySerializer` 中：
- 在 `Meta.fields` 中增加 `'type'` 字段，确保 REST API 能正常读写。

在 [dashboard_views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/dashboard_views.py) 的 `DashboardDataAPI` 中：
- 在返回给大屏的重保列表中，为每个保障项增加 `'type'` 与 `'type_display'` 信息，使得大屏页面前端也能识别该字段。

### 2.6 前端界面 (Templates)
在 [templates/netbox_otnfaults/heavyduty.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/heavyduty.html) 的“重保通知基本信息”面板中：
- 增加一行显示“类型”，并渲染为对应的 Badge。

---

## 3. 数据库迁移 (Migrations)
- 在代码修改完毕后，需要在 Netbox 虚拟环境下运行 `python manage.py makemigrations` 和 `python manage.py migrate` 以生成和应用数据库变更。

---

## 4. 验收与验证方案
- 检查重保列表页是否能正常加载，且多出了“类型”列并渲染为不同的 Badge 颜色。
- 检查重保的创建、修改、批量编辑、导入页面是否能正常对“类型”字段进行操作。
- 检查过滤功能是否正常工作。
- 检查重保详情页面中“类型”是否正确展示。
- 检查大屏 API 是否正常输出含 `'type'` 信息的 JSON。
