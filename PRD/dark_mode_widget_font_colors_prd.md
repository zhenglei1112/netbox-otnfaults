# 仪表盘小组件深色模式字体颜色优化需求与设计方案

## 1. 背景与目标
目前，在 Netbox 4.x 系统的深色模式下，OTN 插件自定义的五个仪表盘小组件（故障日历、割接日历、今明割接、复核故障、协调割接）存在部分文字显示不明晰的问题。
其核心原因为：
- 代码中硬编码了浅色模式下的灰色值（如 `#6c757d`、`#adb5bd`），这些颜色在深色背景下因对比度极低而难以看清。
- 使用了非标准的主题变量 `--nbx-body-color` 并硬编码了兜底值 `#212529`（几乎为黑色）与 `#495057`，在深色模式下退化为兜底值导致字体完全无法识别。

**目标**：
修改上述五个小组件的模板 CSS，使其在深色模式下字体清晰可见，且整体配色与 Netbox 原生小组件完全一致。

---

## 2. 核心技术方案
为了满足可维护性与自适应要求，我们将放弃直接在深色模式下硬编码白色（如 `#ffffff`），而是**采用 Bootstrap 5 的标准主题 CSS 变量**：
1. **主要文字 / 标题**：使用 `var(--bs-body-color)`。
   - 浅色模式下自动为深灰/黑色（接近 `#212529`）；
   - 深色模式下自动为浅灰色/白色（接近 `#e3e3e3`/`#fff`），与 Netbox 官方的文本颜色完全一致。
2. **次要文字 / 图例 / 表头 / 无数据提示**：使用 `var(--bs-secondary-color)`。
   - 浅色模式下自动为中灰色（接近 `#6c757d`）；
   - 深色模式下自动为明亮的灰白色（接近 `#adb5bd`）。
3. **外部月份日期（非当月日期）淡化**：
   - 使用 `color: var(--bs-body-color); opacity: 0.4;`，以百分比透明度的方式在任意模式下自然淡化非当月日期，避免硬编码色值。

---

## 3. 具体修改设计

### 3.1 故障日历 (`dashboard_calendar_widget.html`)
- **标题月份**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **周表头（一至日）**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **日期数字**：`color: var(--nbx-body-color, #495057);` $\rightarrow$ `color: var(--bs-body-color);`
- **非本月日期**：`color: #adb5bd;` $\rightarrow$ `color: var(--bs-body-color); opacity: 0.4;`
- **图例文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`

### 3.2 割接日历 (`dashboard_cutover_calendar_widget.html`)
- **标题月份**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **周表头（一至日）**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **日期数字**：`color: var(--nbx-body-color, #495057);` $\rightarrow$ `color: var(--bs-body-color);`
- **非本月日期**：`color: #adb5bd;` $\rightarrow$ `color: var(--bs-body-color); opacity: 0.4;`
- **割接项标题/省份**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **已取消割接项文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color); opacity: 0.6;`
- **影响业务数文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **图例文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **暂无计划割接提示**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`

### 3.3 今明割接 (`dashboard_today_tomorrow_cutover_widget.html`)
- **割接分组标题（今日/明日割接）**：`color: var(--nbx-body-color, #495057);` $\rightarrow$ `color: var(--bs-body-color);`
- **割接卡片主字体**：`color: var(--nbx-body-color, #212529) !important;` $\rightarrow$ `color: var(--bs-body-color) !important;`
- **割接时间**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **割接详情（省份+位置）**：`color: var(--nbx-body-color, #495057);` $\rightarrow$ `color: var(--bs-body-color);`
- **割接编号/主管人员文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **无计划任务空状态提示**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **空状态图标**：`color: #adb5bd;` $\rightarrow$ `color: var(--bs-secondary-color); opacity: 0.7;`

### 3.4 复核故障 (`dashboard_pending_review_widget.html`)
- **待复核数量（非零）**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **待复核数量（为零）**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **“待复核故障”描述标签**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **暂无任务状态容器文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`

### 3.5 协调割接 (`dashboard_pending_coordination_widget.html`)
- **待协调数量（非零）**：`color: var(--nbx-body-color, #212529);` $\rightarrow$ `color: var(--bs-body-color);`
- **待协调数量（为零）**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **“待协调割接”描述标签**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`
- **暂无协调任务文字**：`color: #6c757d;` $\rightarrow$ `color: var(--bs-secondary-color);`

---

## 5. 影响范围与验证计划
- **修改文件**：
  - `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_calendar_widget.html`
  - `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_cutover_calendar_widget.html`
  - `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_today_tomorrow_cutover_widget.html`
  - `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_pending_review_widget.html`
  - `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_pending_coordination_widget.html`
- **测试验证**：
  - 检查模板渲染是否正常，确保未引入语法错误。
  - 交付用户在 Netbox 页面，通过系统右上角切换“浅色模式（Light Mode）”与“深色模式（Dark Mode）”，验证五个小组件的标题、正文、副标题及辅助灰色文本在深色模式下是否清晰可见、对比度舒适，且色彩表现与 DCIM / 外购合同等官方小组件完美对齐。
