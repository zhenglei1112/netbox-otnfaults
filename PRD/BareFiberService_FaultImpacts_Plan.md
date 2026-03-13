# 裸纤业务模型详情页增加关联的故障影响业务信息 - 实施计划

## 1. 需求背景

用户希望在“裸纤业务” (BareFiberService) 的详情页中，能够直接查看到与该裸纤业务相关联的所有“故障影响业务” (OtnFaultImpact) 的信息。

## 2. 详细方案

通过查阅当前代码：
- `OtnFaultImpact` 模型与 `BareFiberService` 模型已有外键关联 (`bare_fiber_service` 字段，且 `related_name='fault_impacts'`)。
- 因此不需要进行数据库结构调整，只需在后台视图（`views.py`）提取数据并在前端模板（`barefiberservice.html`）配置相应的表格渲染即可。

按照项目的UI规范，必须禁用 django_tables2 的默认分页，并使用符合 Netbox 4.x 风格的自定义分页组件。

### 2.1 修改 `netbox_otnfaults/views.py`
在 `BareFiberServiceView` 中重写 `get_extra_context` 方法：
- 接收 `per_page` 以及当前页码的查询参数 (例如 `fault_impacts_page`)。
- 构造 `OtnFaultImpactTable(instance.fault_impacts.all())`，隐藏 `actions` 动作列，以只读展示。
- 使用 `RequestConfig` 或手动 `.paginate()` 将其进行分页处理，随后将其传递给前端进行渲染。

### 2.2 修改 `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice.html`
- 加载 `{％ load render_table from django_tables2 ％}`。
- 增加控制隐藏默认分页的 `<style>`。
- 在页面中现有的主要内容下方增加一个占据整个宽度的表格区块，使用 `render_table` 渲染传入的数据表。
- 参照 `otnpathgroup.html`，补充基于 Bootstrap 5/Netbox 原生风格的自定义底部分页栏（页码器、条目数量展示和改变每页行数的下拉菜单）。

## 3. 验证计划

- **本地验证**: 通过 `/verify-deployment` 工作流确保服务正常重启并没有明显报错。
- **页面测试**: 访问裸纤业务详情页面，检查：
  1. 是否成功显示新表格。
  2. 默认隐去的底层分页功能被移除，且新的分页按钮和跳转功能正常工作。
  3. 各数据显示是否正确（无缺失外键）。
