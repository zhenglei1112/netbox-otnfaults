# 割接影响业务实现方案

## 1. 需求概述
为“割接管理”模块新增“割接影响业务”功能，使 `CutoverTask` 能独立关联和管理受影响的裸纤业务、电路业务，并在割接详情页展示受影响业务列表。

实现应以现有 `OtnFaultImpact` 为主要参照，但不能机械复制字段名、反向关系名和路由名。新增模型、表单、表格、API、模板都必须使用 `CutoverImpact` 专属命名，避免与故障影响业务发生反向关系冲突。

## 2. 数据库模型设计 (models.py)
新增 `CutoverImpact` 模型：
- 继承 `NetBoxModel` 和 `ImageAttachmentsMixin`。
- **关联父项**: `cutover_task`，`ForeignKey` 指向 `CutoverTask`，`related_name='impacts'`，`on_delete=models.CASCADE`。
- **业务类型**: `service_type`，复用 `ServiceTypeChoices`，支持裸纤业务和电路业务。
- **业务关联**:
  - `bare_fiber_service`，`ForeignKey` 指向 `BareFiberService`，允许为空，`related_name='cutover_impacts'`。
  - `circuit_service`，`ForeignKey` 指向 `CircuitService`，允许为空，`related_name='cutover_impacts'`。
- **业务站点**:
  - `service_site_a`，`ForeignKey` 指向 `dcim.Site`，允许为空，`related_name='cutover_impact_service_site_a'`。
  - `service_site_z`，`ManyToManyField` 指向 `dcim.Site`，允许为空，`related_name='cutover_impact_service_site_z'`。
- **影响情况**: `business_impact`，复用 `BusinessImpactChoices`。
- **时间字段**:
  - `service_interruption_time`: 业务中断时间。
  - `service_recovery_time`: 业务恢复时间，允许为空。
- **通用字段**: `tags`、`comments`，与 `OtnFaultImpact` 保持一致。
- **排序**: 默认按 `-service_interruption_time` 排序。
- **约束**:
  - `unique_cutover_bare_fiber`: 同一个割接任务下不能重复添加同一个裸纤业务，条件为 `bare_fiber_service__isnull=False`。
  - `unique_cutover_circuit`: 同一个割接任务下不能重复添加同一个电路业务，条件为 `circuit_service__isnull=False`。
- **方法属性**:
  - `__str__()` 返回 `割接任务 - 业务名称`。
  - `get_absolute_url()` 指向 `plugins:netbox_otnfaults:cutoverimpact`。
  - `clean()` 校验业务类型和业务字段匹配关系。
  - 裸纤业务时必须有 `bare_fiber_service`，并清空 `circuit_service`。
  - 电路业务时必须有 `circuit_service`，并清空 `bare_fiber_service`、`service_site_a`。
  - `service_site_z` 是 M2M 字段，不能只在 `clean()` 中处理；电路业务时需要在 `save()` 后执行 `self.service_site_z.clear()`。
  - `service_duration` 和 `service_duration_info` 复用 `OtnFaultImpact` 的历时计算逻辑。
  - `get_service_type_color()` 和 `get_business_impact_color()` 复用对应 ChoiceSet 颜色。

## 3. 表单设计 (forms.py)
新增以下表单，命名应与现有 NetBox 视图类匹配：
- `CutoverImpactImportForm`: 继承 `NetBoxModelImportForm`，用于批量导入。`cutover_task` 建议通过 `cutover_no` 识别；裸纤、电路业务可按现有业务名称字段识别。
- `CutoverImpactForm`: 继承 `NetBoxModelForm`，用于新增和编辑。
- `CutoverImpactBulkEditForm`: 继承 `NetBoxModelBulkEditForm`，用于批量编辑。
- `CutoverImpactFilterForm`: 继承 `NetBoxModelFilterSetForm`，用于列表页过滤。

`CutoverImpactForm` 需包含以下行为：
- 支持从 URL 参数 `cutover_task` 初始化父割接任务。
- 新增割接影响业务时，若父割接已有 `planned_cutover_time`，可作为业务中断时间默认值；业务恢复时间由割接影响业务记录自身维护。
- 裸纤业务显示 `bare_fiber_service`、`service_site_a`、`service_site_z`。
- 电路业务显示电路三级联动字段，并隐藏真实 `circuit_service` 字段。
- 电路三级联动逻辑可复用 `OtnFaultImpactForm` 的 `circuit_business_category`、`circuit_service_group`、`circuit_special_line_name` 实现方式。
- `clean()` 中需把用户选择的专线 ID 回填到真实 `circuit_service` 字段。

`CutoverImpactFilterForm` 需支持：
- `cutover_task`
- `service_type`
- `bare_fiber_service`
- `circuit_service`
- `circuit_business_category`
- `circuit_service_group`
- `business_impact`
- `service_interruption_time_after`
- `service_interruption_time_before`
- `service_recovery_time`
- `tag`

## 4. 表格设计 (tables.py)
新增 `CutoverImpactTable`，参照 `OtnFaultImpactTable`：
- 列包含：ID、所属割接、业务类型、业务名称、业务组、A端站点、Z端站点、影响情况、中断时间、恢复时间、中断历时、评论、标签、操作列。
- `service_name` 使用计算列，根据 `service_type` 链接到 `BareFiberService` 或 `CircuitService`。
- `service_duration` 使用与故障影响业务一致的展示和导出逻辑。
- `actions` 必须始终是 `Meta.fields` 的最后一列；后续新增业务字段只能放在 `actions` 前。

建议同时新增 `CutoverImpactSummaryTable`，用于割接详情页嵌入展示：
- 默认列建议为：ID、业务类型、业务名称、中断时间、恢复时间、中断历时、业务影响、操作列。
- 详情页表格可隐藏不必要的父割接列，避免重复展示当前割接任务。

## 5. 过滤与 API (filtersets.py, api/)
新增 `CutoverImpactFilterSet`：
- 支持 `cutover_task`、`service_type`、`bare_fiber_service`、`circuit_service`、`business_impact`。
- 支持电路业务派生过滤：`circuit_service__business_category`、`circuit_service__service_group`。
- 支持业务中断时间范围过滤：`service_interruption_time_after` 和 `service_interruption_time_before`。
- `search()` 应覆盖割接编号、裸纤业务名称、电路业务名称、评论等常用字段。

API 层需要分别修改：
- `api/serializers.py`: 新增 `CutoverImpactSerializer`，使用 `NetBoxModelSerializer`。
- `api/views.py`: 新增 `CutoverImpactViewSet`，使用 `NetBoxModelViewSet`。
- `api/urls.py`: 注册 API 路由，例如 `router.register('cutover-impacts', views.CutoverImpactViewSet)`。

不要把 API 路由注册写在 `api/views.py` 中。

## 6. 视图逻辑 (views.py)
新增标准 NetBox CRUD 视图：
- `CutoverImpactListView`
- `CutoverImpactView`
- `CutoverImpactEditView`
- `CutoverImpactDeleteView`
- `CutoverImpactBulkImportView`
- `CutoverImpactBulkEditView`
- `CutoverImpactBulkDeleteView`

实现要求：
- `CutoverImpactListView` 使用 `ExcelFriendlyCSVExportMixin`、`CutoverImpactTable`、`CutoverImpactFilterSet`、`CutoverImpactFilterForm`。
- `CutoverImpactView` 使用 `@register_model_view(CutoverImpact)`。
- `CutoverImpactEditView` 需要支持通过 `?cutover_task=<id>` 初始化父割接任务和默认时间。
- 新增成功后默认跳转到 `CutoverImpact` 自身详情页；点击“保存并添加另一个”时保留 `cutover_task` 参数。
- `CutoverImpactBulkEditView` 需要绑定 `CutoverImpactBulkEditForm`。

修改 `CutoverTaskView.get_extra_context()`：
- 查询直接关联影响业务：`instance.impacts.all().distinct()`。
- 使用 `CutoverImpactSummaryTable(impacts, prefix='impact-')`。
- 使用 `RequestConfig(request, paginate={'per_page': per_page}).configure(table)` 或 `table.paginate()`。
- `per_page` 从 `impact_per_page` 或统一自定义分页参数读取，默认 25。

## 7. 前端模板 (templates/)
新增模板：
- `cutoverimpact.html`: 割接影响业务详情页。
- `cutoverimpact_edit.html`: 割接影响业务编辑页，包含电路三级联动脚本和时间控件脚本。
- `cutoverimpact_list.html`: 如需自定义列表页分页和筛选布局，则新增；否则可沿用通用列表模板。

修改模板：
- `cutovertask.html`: 增加“影响业务”面板，渲染 `impacts_table`。
- 面板标题处提供“新增影响业务”按钮，链接到 `cutoverimpact_add`，并携带 `?cutover_task={{ object.pk }}`。
- 嵌入表格必须使用项目自定义分页 UI，隐藏 `django_tables2` 默认分页。

割接详情页自定义分页结构必须包含：
- 页码导航：`‹ 1 2 ... 5 6 7 ... 10 ›`
- 显示信息：`显示 1-25 共 100`
- 每页选择：25/50/100/250/500

多表格分页要求：
- 割接详情页若已有其他表格，影响业务表格必须使用独立分页参数。
- 建议使用 `prefix='impact-'` 或明确的 `impact_page`、`impact_per_page`，但模板和视图必须保持一致。

## 8. 路由与菜单 (urls.py, navigation.py)
`urls.py` 需注册页面路由：
- `cutover-impacts/`
- `cutover-impacts/add/`
- `cutover-impacts/import/`
- `cutover-impacts/edit/`
- `cutover-impacts/bulk-delete/`
- `cutover-impacts/<int:pk>/`
- `cutover-impacts/<int:pk>/edit/`
- `cutover-impacts/<int:pk>/delete/`
- `cutover-impacts/<int:pk>/changelog/`

`navigation.py` 可在割接管理菜单组中补充“割接影响业务”入口。若割接影响业务主要从割接详情页进入，可暂不加入一级菜单，但需要保证列表页 URL 可访问。

## 9. 迁移与数据安全
- 新增模型后运行 `makemigrations`，并检查迁移文件只涉及 `netbox_otnfaults` 插件目录。
- 运行 `migrate` 前先确认唯一约束命名不会与现有迁移冲突。
- 不修改 NetBox 核心目录。
- 不变更 `OtnFaultImpact` 既有字段语义，避免影响故障统计、周报和同步脚本。

## 10. 测试与验收
至少补充源代码级回归测试，覆盖以下内容：
- `models.py` 包含 `class CutoverImpact(NetBoxModel, ImageAttachmentsMixin)`。
- `CutoverImpact` 定义 `get_absolute_url()`。
- `CutoverImpact` 的 `service_site_a`、`service_site_z`、业务服务字段使用 cutover 专属 `related_name`。
- `CutoverImpact` 包含裸纤和电路唯一约束。
- `CutoverImpactForm`、`CutoverImpactImportForm`、`CutoverImpactBulkEditForm`、`CutoverImpactFilterForm` 均已定义。
- `CutoverImpactTable` 的 `actions` 在 `Meta.fields` 最后一列。
- `CutoverImpactFilterSet` 暴露割接、业务、时间范围和电路分类过滤。
- `CutoverImpactSerializer`、`CutoverImpactViewSet`、`api/urls.py` 路由均已注册。
- `CutoverTaskView` 向模板注入 `impacts_table`。
- `cutovertask.html` 渲染影响业务表格，并包含新增影响业务入口。

可运行验证命令：
```powershell
python -m compileall netbox_otnfaults tests
```

如本地具备 NetBox/Django 测试环境，再运行相关单元测试和迁移检查。

## 11. 实施步骤
1. 在 `PLAN.md` 增加本功能实施清单。
2. 在 `models.py` 新增 `CutoverImpact`，生成并检查迁移。
3. 完善 `forms.py`、`tables.py`、`filtersets.py`。
4. 编写 CRUD 视图并配置 `urls.py`。
5. 完成 API serializer、viewset 和 `api/urls.py` 注册。
6. 创建 `cutoverimpact.html`、`cutoverimpact_edit.html`，修改 `cutovertask.html`。
7. 添加源代码级回归测试。
8. 运行 `python -m compileall netbox_otnfaults tests`。
9. 若具备 NetBox 环境，继续运行迁移和页面级验证。
