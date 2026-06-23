# 割接影响业务 A/Z 站点默认值设置需求文档 (PRD)

## 1. 背景与目的
在割接管理模块中，割接影响业务（`CutoverImpact`）用来记录某次割接任务影响的裸纤业务或电路业务。
目前，当用户在割接任务详情页点击“增加一个影响的业务”按钮时，系统会跳转到新增割接影响业务表单页面，并且 URL 中会携带割接任务的 ID（例如 `?cutover_task=1`）。
然而，目前在表单初始化时，割接任务所关联的 **割接位置 A 端站点** 和 **割接位置 Z 端站点** 没有成功设置为“业务站点 A”和“业务站点 Z”的默认值，导致用户必须手动重复选择这两个站点，影响了使用体验。

本需求旨在确保新增“割接影响业务”时，若关联了割接任务，系统会自动将该割接任务的 A 端和 Z 端站点预填为该影响业务的“业务站点 A”与“业务站点 Z”的默认值。

## 2. 详细设计
在 `netbox_otnfaults/forms.py` 中的 `CutoverImpactForm` 类的初始化方法 `__init__` 中：
1. 检查是否存在 `cutover_task_id`（来自 `initial` 字典或 `self.instance.cutover_task_id`）。
2. 若存在，根据 `cutover_task_id` 查询对应的 `CutoverTask` 实例。
3. 将割接任务中的如下属性，分别写入表单实例的 `self.initial` 字典中：
   - `cutover_task`: `cutover.pk`
   - `service_interruption_time`: `cutover.planned_cutover_time`
   - `service_site_a`: `cutover.interruption_location_a_id`
   - `service_site_z`: 该割接任务关联的 Z 端站点 ID 列表（`list(cutover.interruption_location.values_list('pk', flat=True))`）

由于 Django `ModelForm` 的机制，如果在 `super().__init__` 之后仅修改 `self.fields[field_name].initial`，会导致因 `self.initial` 中对应键为 `None` 而失效。因此，必须修改 `self.initial` 字典对应的键值对。

## 3. 影响范围
- 表单：`netbox_otnfaults/forms.py` 中的 `CutoverImpactForm`
- 模块：割接影响业务新增页面。

## 4. 验证计划
在本地测试环境中执行 unittest 测试套件，确保修改未破坏任何现有逻辑，并手动确认初始化逻辑能够正确设置。
