# 故障影响业务时间自动填充需求与设计

## 1. 需求背景
当用户在“故障影响业务”编辑页面添加或修改业务故障影响时，如果业务的“业务故障时间”（`service_interruption_time`） and “业务恢复时间”（`service_recovery_time`）未填写，但在表单中指定了“直接故障”（`otn_fault`），系统应该自动采用该直接故障对应的“故障起始时间”（`fault_occurrence_time`） and “故障恢复时间”（`fault_recovery_time`）进行填充，以提升录入效率并确保数据完整性。

## 2. 详细设计

### 2.1 后端模型校验与自动填充 (`models.py`)
在 `OtnFaultImpact` 模型类的 `clean` 方法中进行以下逻辑处理：
- 检查是否存在关联的直接故障 `otn_fault`。
- 如果 `service_interruption_time` 属性为空，并且关联的 `otn_fault` 包含 `fault_occurrence_time`，则自动将其填充为 `otn_fault.fault_occurrence_time`。
- 如果 `service_recovery_time` 属性为空，并且关联的 `otn_fault` 包含 `fault_recovery_time`，则自动将其填充为 `otn_fault.fault_recovery_time`。
- 如果 `service_site_a` 属性为空，并且关联的 `otn_fault` 包含 `interruption_location_a`，则自动将其填充为 `otn_fault.interruption_location_a`。

### 2.2 后端表单校验与自动填充 (`forms.py`)
在 `OtnFaultImpactForm` 表单类的 `clean` 方法中进行以下处理，以确保通过页面表单提交时，数据的验证和清洗也得到同样的填充：
- 在 `super().clean()` 调用后获取 `cleaned_data`。
- 提取并检查 `cleaned_data` 中的直接故障实例 `otn_fault`。
- 若 `service_interruption_time` 为空，使用直接故障的 `fault_occurrence_time` 填充 `cleaned_data`。
- 若 `service_recovery_time` 为空，使用直接故障 of `fault_recovery_time` 填充 `cleaned_data`。
- 若 `service_site_a` 为空，使用直接故障 of `interruption_location_a` 填充 `cleaned_data`。
- 若 `service_site_z` 为空，使用直接故障 of `interruption_location`（所有关联站点列表）填充 `cleaned_data`。

### 2.3 前端页面动态交互与自动填充 (`otnfaultimpact_edit.html`)
在“添加/编辑故障影响业务”页面的 JavaScript 逻辑中增加以下联动交互：
- 监听直接故障（`id_otn_fault`）选择框的 `change` 更改事件。
- 当用户手动选中了一个具体的故障时，自动提取其选中项的值（即故障ID）。
- 发送一个 AJAX 请求访问 Netbox 的 REST API 终点（`/api/plugins/otnfaults/faults/${faultId}/`）以拉取此直接故障的详情数据。
- 判断页面上的“业务故障时间”与“业务恢复时间”输入框。如果为空，则分别把 API 返回的该故障的 `fault_occurrence_time` 和 `fault_recovery_time` 日期实例使用 flatpickr 实例的 `setDate(date, true)` 方法回填至页面中。
- 判断页面上的“业务站点A” (`id_service_site_a`) 与“业务站点Z” (`id_service_site_z`) 下拉框：
  - **新增模式**：总是用直接故障的 `interruption_location_a` 和 `interruption_location` 对业务站点 A 和 Z 进行覆盖填充（若无则清空）。
  - **编辑模式**：仅在“业务站点A”或“业务站点Z”为空时，才将故障的对应站点信息填入。
  - **回显方案**：由于站点下拉框使用的是 TomSelect 组件，在写入值时，需将选项值 `id` 和文本 `display` 用 `tomselect.addOption` 先存入，再调用 `tomselect.setValue` 确认回填。

### 2.4 单元测试校验 (`tests/`)
在 `tests/` 下创建一个新的静态断言测试文件 `test_otnfaultimpact_time_populate.py`，用于验证模型和表单中是否已编写上述自动填充逻辑的源码结构，保证后续代码迭代时此逻辑不被意外遗漏或修改。
