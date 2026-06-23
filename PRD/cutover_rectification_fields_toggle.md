# 需求方案：割接管理中，仅当选择“需要整改”时才显示后续整改字段

为割接管理（CutoverTask）的创建 and 编辑页面（`cutovertask_edit.html`）引入前端 JavaScript 联动交互。
仅当用户在“是否整改”（`rectification_status`）下拉框中选择“需要整改”（`required`）时，才显示后续的 8 个整改相关字段；选择其他选项（如“无需整改”、“重复合并”或空值）时，自动隐藏这些后续字段的整行，以提升界面简洁度。

## 方案设计

### 1. 前端模板修改 (`cutovertask_edit.html`)
在 `<script>` 标签内新增 `initRectificationFieldsToggle` 函数。该函数将：
1. 获取“是否整改”选择框（`#id_rectification_status`）。
2. 获取后续 8 个字段（`id_rectification_measures`, `id_rectification_description`, `id_rectification_subject`, `id_rectification_progress`, `id_planned_completion_time`, `id_actual_completion_time`, `id_rectification_completion_description`, `id_re_cutover`）的输入框最近外层整行元素。
3. 监听选择框的 `change` 事件（以及对应的 TomSelect `change` 事件），根据其值是否为 `'required'`，动态设置后续所有行的 `display` 样式（`'flex'` 或 `'none'`）。
4. 在页面加载和组件初始化时执行一次状态判定。

### 2. 测试脚本修改 (`test_cutover_edit_template.py`)
在测试用例 `CutoverEditTemplateTestCase` 中新增测试方法 `test_rectification_fields_toggle_logic`：
1. 读取 `cutovertask_edit.html` 的文本内容。
2. 验证其中包含 `initRectificationFieldsToggle` 逻辑，且包含正确的 HTML id 选择器 `#id_rectification_status` 和后续字段（例如 `#id_rectification_measures` 等），以及联动控制逻辑的核心代码片段。

## 验证计划

### 自动化测试
运行单元测试脚本：
```bash
python -m unittest tests/test_cutover_edit_template.py
```
确保所有测试断言全部通过。
