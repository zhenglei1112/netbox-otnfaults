# 取消割接影响业务保存身份校验设计

## 目标

删除 `CutoverImpactEditView` 中基于割接线路主管、业务主管和超级管理员身份的自定义保存校验。所有拥有 NetBox `change_cutoverimpact` 权限的用户均可通过普通编辑页面保存割接影响业务。

## 设计

- 删除 `CutoverImpactEditView.post()` 覆盖方法及其中解析割接任务、解析业务主管、比较当前用户和返回权限错误表单的全部逻辑。
- 保留 NetBox `generic.ObjectEditView` 自带的模型权限校验和标准保存流程。
- 保留 `alter_object()`：新增割接影响业务时，仍可从 URL 查询参数预填 `cutover_task`。
- 删除编辑模板中仅由该后端校验触发的权限拒绝模态框及自动弹出脚本，避免遗留不可达代码。
- 不修改割接任务、割接影响业务模型、REST API、批量编辑或其他模块权限逻辑。

## 数据流

编辑表单提交后直接进入 `generic.ObjectEditView.post()`。NetBox 首先验证用户的对象变更权限，再执行表单校验与保存，不再附加线路主管或业务主管身份条件。

## 测试

- 先增加回归测试，断言 `CutoverImpactEditView` 不再覆盖 `post()`，并确认旧身份判断和拒绝提示已移除。
- 在生产代码修改前运行该测试，确认测试因旧逻辑仍存在而失败。
- 删除旧逻辑后重新运行目标测试和相关割接管理测试。
- 对修改过的 Python 文件执行编译检查。

## 非目标

- 不改变 NetBox 的 `add_cutoverimpact`、`change_cutoverimpact` 等权限。
- 不引入新的角色、配置开关或对象级权限规则。
- 不调整割接影响业务的字段、状态或保存内容。
