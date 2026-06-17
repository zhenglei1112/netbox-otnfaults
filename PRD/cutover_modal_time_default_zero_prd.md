# 割接详情页生成时间弹窗默认整点选择需求文档

本需求旨在优化割接详情页中“生成新的割接时间”这一弹出式修改时间对话框的用户体验。点击“生成新的割接时间”按钮打开弹窗时，时间框中显示或选择的时间应当默认为整点 `00:00`，避免引入散乱的当前系统小时与分钟。

## 详细功能设计

- 在 `cutovertask.html` 中，对 `id_planned_cutover_time_modal` 原生日期时间输入框的初始值进行调整：
  - 使用 Django 过滤器强行将其时分渲染为 `00:00`。
- 在弹出对话框的前端 JS 方法 `showGeneratePlannedTimeModal` 中增加数据拦截纠偏：
  - 若输入框值为空，基于当前日期自动计算并填充为当天的整点：`YYYY-MM-DDT00:00`。
  - 若输入框已有值，通过字符串拆分将 `T` 后的时分内容强行重置为 `00:00`。

## 拟修改文件列表

- **详情页模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)
