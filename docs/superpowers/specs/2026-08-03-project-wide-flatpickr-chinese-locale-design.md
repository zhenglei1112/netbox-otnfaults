# 全项目 Flatpickr 中文化设计

## 目标

覆盖插件当前全部 `DateTimePicker` 和 `DatePicker` 页面，使 Flatpickr 显示中文月份与星期，不遗漏列表筛选、普通编辑、批量编辑和割接生成故障页面。

## 约束与方案

NetBox 4.0 官方 `PluginConfig` 不提供全局 JavaScript 资源属性，因此不使用未受支持的 `javascript` 配置，也不覆盖 NetBox 核心模板。

新增三个插件内共享模板，分别继承 NetBox 的通用列表、普通编辑和批量编辑模板，并加载 `flatpickr_zh.html`。所有此前使用通用模板且包含日期控件的视图显式绑定对应共享模板；已有自定义模板的页面直接加载中文模板。

此前未加载中文模板的页面统一传入 `disable_default_now=True`，只改变界面语言，不新增“打开空字段自动填当前时间”的行为。已经加载中文模板的编辑页保持原行为。

原生 `datetime-local` 输入框由浏览器本地化，不属于本次 Flatpickr 范围。

## 验证

- 25 个此前遗漏的 `DateTimePicker` 和 4 个 `DatePicker` 均具备中文模板加载路径。
- 所有列表筛选与新接入页面禁用自动填时。
- 既有编辑页继续使用原来的中文及自动填时行为。
- 不修改模型、数据库或时间格式。
