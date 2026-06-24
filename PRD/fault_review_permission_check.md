# 需求文档：故障复核权限校验需求

## 1. 业务背景
在物理故障管理中，“故障复核”是核对故障现象、恢复状态、时长统计以及保障业务恢复准确性的重要关口。为了规范复核流程并避免误操作，系统需要做权限限制：只有当前故障在录入时指定的“线路主管”和“运维主管”，才能分别对自己分管的复核 checkbox 进行勾选或变更操作。

## 2. 功能需求
在故障（`OtnFault`）的编辑页面上：
- **线路主管复核**（`manager_reviewed`）：只有该故障的“线路主管”（`line_manager`）才可以进行点击勾选或取消勾选。如果非该故障的线路主管点击，应弹出模式的错误提示窗口（Modal）：“**只有当前故障的线路主管才可以进行复核操作。**”，并且 checkbox 状态不能被改变。
- **网管人员复核**（`noc_reviewed`）：只有该故障的“运维主管”（`operations_manager`）之一才可以进行点击勾选或取消勾选。如果非该故障的运维主管点击，应弹出模式的错误提示窗口（Modal）：“**只有当前故障的运维主管才可以进行复核操作。**”，并且 checkbox 状态不能被改变。
- **权限例外**：若当前登录用户是系统超级用户（`is_superuser`），则不受以上任何限制，可以任意勾选或取消勾选。
- **安全后端校验**：在保存故障数据提交（`POST`）时，后端必须在 Django Form 的 `clean` 方法中做对应校验，防止通过前端黑客手段绕过。若权限不符，应抛出对应的 ValidationError 拦截保存。

## 3. 技术设计
### 3.1 关系与字段映射
- **故障模型（`OtnFault`）**：
  - 线路主管字段：`line_manager` (ForeignKey to User)
  - 运维主管字段：`operations_manager` (ManyToManyField to User)
  - 线路主管复核：`manager_reviewed` (BooleanField，前端 ID 为 `id_manager_reviewed`)
  - 网管人员复核：`noc_reviewed` (BooleanField，前端 ID 为 `id_noc_reviewed`)

### 3.2 前端 JavaScript 逻辑
在 `otnfault_edit.html` 故障编辑页面模板的最下方 JavaScript 脚本中：
1. 声明并获取当前数据状态变量：
   - 当前登录用户的 ID (`currentUserId = "{{ request.user.id|default:'' }}"`)
   - 当前登录用户是否为超级用户 (`isSuperUser = {% if request.user.is_superuser %}true{% else %}false{% endif %}`)
   - 该故障原本在数据库中保存的线路主管 ID (`faultLineManagerId = "{{ form.instance.line_manager.id|default:'' }}"`)
   - 该故障原本在数据库中保存的运维主管 ID 列表 (`faultOpsManagerIds = [{% for user in form.instance.operations_manager.all %}"{{ user.id }}",{% endfor %}]`)
2. 在 `initReviewLogic` 初始化时，为 `id_manager_reviewed` 和 `id_noc_reviewed` 两个 checkbox 绑定 `click` 事件监听器：
   - 监听器内判断如果不是超级用户，则进行权限判断：
     - 若点击 `id_manager_reviewed` 且 `currentUserId !== faultLineManagerId`，调用 `e.preventDefault()` 阻止勾选并弹出错误 Modal，提示：“**只有当前故障的线路主管才可以进行复核操作。**”。
     - 若点击 `id_noc_reviewed` 且 `!faultOpsManagerIds.includes(currentUserId)`，调用 `e.preventDefault()` 阻止勾选并弹出错误 Modal，提示：“**只有当前故障的运维主管才可以进行复核操作。**”。
3. 注入一个自定义的错误提示 Modal（`permissionErrorModal`），采用 Bootstrap 5 的标准警告样式，替代原生的 `alert()` 弹窗。

### 3.3 后端 Django 校验逻辑
在 `OtnFaultForm` 的 `clean` 方法中：
1. 校验 `manager_reviewed` 字段值是否发生改变（`cleaned_data.get('manager_reviewed') != self.instance.manager_reviewed`）：
   - 若改变且用户不是超级用户，检查当前用户是否等于 `self.instance.line_manager`。如果不符，抛出 `ValidationError({'manager_reviewed': '只有当前故障的线路主管才可以进行复核操作。'})`。
2. 校验 `noc_reviewed` 字段值是否发生改变（`cleaned_data.get('noc_reviewed') != self.instance.noc_reviewed`）：
   - 若改变且用户不是超级用户，检查当前用户是否在 `self.instance.operations_manager.all()` 中。如果不符，抛出 `ValidationError({'noc_reviewed': '只有当前故障的运维主管才可以进行复核操作。'})`。
