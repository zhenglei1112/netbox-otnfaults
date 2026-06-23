# 割接时间生成逻辑统一需求文档 (PRD)

## 1. 业务背景
在 Netbox OTN 故障插件中，割接任务（`CutoverTask`）具有“计划割接时间”（`planned_cutover_time`）和“计划割接时间记录”（`planned_cutover_times`，以 JSON 数组形式存储）。
- 故障详情页（`cutovertask.html`）：采用只读方式展示历史时间列表，提供“生成新的割接时间”按钮，点击后弹出模态框（Modal）输入新时间，确认后通过 AJAX / POST 提交并重置关联业务协调状态。
- 编辑页面（`cutovertask_edit.html`）：目前将 `planned_cutover_time` 渲染为可直接编辑的输入框，并在旁边放一个“生成新的割接时间”按钮，用户输入并确认后通过 JS 追加到本地的隐藏 JSON 字段中。

为了保持两处地方的操作逻辑和界面一致，需要将编辑页面的生成时间逻辑调整为和详情页一致：
- 界面上不再提供对 `planned_cutover_time` 的直接编辑，显示为只读的列表。
- 点击“生成新的割接时间”按钮时，弹出和详情页一致的输入窗口。
- 在模态框中输入新时间，确认生成后，将新时间追加到本地的 `planned_cutover_times` 历史记录中，并同步更新最新计划时间到 `planned_cutover_time` 隐藏表单项，最后重新渲染只读的历史时间列表。

## 2. 界面与交互规范
1. **隐藏原输入项**：将 Django 表单生成的 `planned_cutover_time` 和 `planned_cutover_times` 字段在编辑页中设为隐藏。
2. **只读时间显示**：新增自定义展示区，第一行以只读方式展示最新计划时间，右侧放置“生成新的割接时间”按钮；第二行展示与详情页完全一致的只读历史时间记录列表。
3. **模态框输入**：点击“生成新的割接时间”按钮时，弹出包含 `type="datetime-local"` 输入框的模态框，样式、警告文字均与详情页一致。
4. **数据同步**：在模态框中确认生成后，更新隐藏的表单输入框，并触发本地更新逻辑，重新渲染页面上的只读历史时间列表。

## 3. 影响范围
- `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html` (前端模板与 JS 逻辑)
