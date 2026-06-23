# 需求文档：割接影响业务保存权限校验

## 1. 业务背景
在网络割接管理过程中，“割接影响业务”（`CutoverImpact`）记录了每次割接对底层裸纤或电路业务的影响及协调状态。为了保证协调状态和业务影响数据的准确性和权威性，只有相关的主管才有权修改或确认这些业务的割接状态。

## 2. 功能需求
在编辑/新增“割接影响业务”时，保存操作需要增加如下权限校验判断：
- 校验条件：当前登录用户（`request.user`）必须是**该割接任务的线路主管**，或者是**受影响业务的业务主管**。
- 例外情况：系统超级用户（`is_superuser`）不受此权限限制。
- 拦截行为：如果当前登录用户不满足上述条件，系统应当阻止保存并把用户留当前页面，同时弹出模式窗口提示信息：“**你不是当前割接/业务的线路（业务）主管，无法修改业务状态。**”
- UI要求：使用模式窗口（Modal）进行提示，样式与交互参考割接详情页中自动设置待实施状态的提示窗口，不使用浏览器自带的普通 `alert` 弹窗。

## 3. 技术设计
### 3.1 关系与字段映射
- **关联割接任务（`CutoverTask`）**：
  - 线路主管字段：`line_supervisor` (ForeignKey to User)
- **关联业务**：
  - 裸纤业务（`BareFiberService`）：业务主管字段 `business_manager` (ForeignKey to User)
  - 电路业务（`CircuitService`）：业务主管字段 `business_manager` (ForeignKey to User)

### 3.2 后端逻辑 (Django View)
在 `CutoverImpactEditView.post` 进行权限校验：
1. 获取正在编辑的 `CutoverImpact` 实例（`obj`）。
2. 从 POST 数据中解析 `cutover_task` ID 和对应的业务服务 ID，必要时以 `obj` 的已有字段做回退兜底。
3. 查询并获取 `line_supervisor` 与 `business_manager`。
4. 判断权限：
   ```python
   is_authorized = False
   if request.user.is_superuser:
       is_authorized = True
   if line_supervisor and line_supervisor == request.user:
       is_authorized = True
   if business_manager and business_manager == request.user:
       is_authorized = True
   ```
5. 若不满足权限，在表单中添加全局错误错误（`form.add_error(None, ...)`），渲染当前编辑页，并在 context 中返回 `show_permission_denied_modal = True`。

### 3.3 前端逻辑 (Jinja2 / Bootstrap Modal)
在 `cutoverimpact_edit.html` 中引入 Bootstrap 5 Modal 组件和对应的 JavaScript：
- 渲染弹窗 HTML 和 Backdrop 遮罩层。
- 在页面 DOM 加载完毕后，检测模板 Context 变量 `show_permission_denied_modal`。如果为真，调用弹窗显示函数。
