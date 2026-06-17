# 割接模型编辑页面计划割接时间默认整点选择需求文档

本需求旨在优化割接信息维护页面（新建/编辑页面）中的用户体验。当用户为“计划割接时间”字段首次选择日期时间时，选择器的时分部分应当默认设为 `00:00`（整点），避免默认填充为当前零散的系统时间。

## 详细功能设计

- 在 `cutovertask_edit.html` 页面的前端脚本中，获取计划割接时间的 `flatpickr` 实例。
- 无论用户何时首次打开它，只要当前输入框为空，自动将其默认时间设为当天的 `00:00`。
- 设置 `defaultHour = 0` 和 `defaultMinute = 0`，确保用户点击日期时，时分的选择默认从 `00:00` 开始。
- 该调整仅在割接表单的“计划割接时间”这一特定日期时间字段生效。

## 拟修改文件列表

- **编辑页模板**：[netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html)
