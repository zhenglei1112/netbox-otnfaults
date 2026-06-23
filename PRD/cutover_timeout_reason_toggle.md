# 需求方案：割接管理中，仅当“是否超时”选择为“是”时，才显示“超时原因”字段

为割接管理（CutoverTask）的创建和编辑页面（`cutovertask_edit.html`）引入前端 JavaScript 联动交互。
仅当用户在“割接是否超时”（`is_timeout`）下拉框中选择“是”（`yes`）时，才显示“超时原因”（`timeout_reason`）的表单行；选择其他选项（如“否”、“待判定”）时，自动隐藏“超时原因”整行，以提升界面简洁度。

## 方案设计

### 1. 前端模板修改 (`cutovertask_edit.html`)
在 `<script>` 标签内新增 `initTimeoutReasonToggle` 函数。该函数将：
1. 获取“是否超时”选择框（`#id_is_timeout`）和“超时原因”输入框（`#id_timeout_reason`）。
2. 获取“超时原因”输入框所在的最近外层整行元素（通过 `timeoutReasonInput.closest('.row')`）。
3. 监听选择框的 `change` 事件（以及对应的 TomSelect `change` 事件），根据其值是否为 `'yes'`，动态设置行的 `display` 样式（`'flex'` 或 `'none'`）。
4. 在页面加载和组件初始化时执行一次状态判定。

### 2. 测试脚本修改 (`test_cutover_edit_template.py`)
在测试用例 `CutoverEditTemplateTestCase` 中新增测试方法 `test_timeout_reason_toggle_logic`：
1. 读取 `cutovertask_edit.html` 的文本内容。
2. 验证其中包含 `initTimeoutReasonToggle` 逻辑，且包含正确的 HTML id 选择器 `#id_is_timeout` 和 `#id_timeout_reason`，以及联动控制逻辑的核心代码片段。

## 验证计划

### 自动化测试
运行单元测试脚本：
```bash
python -m unittest tests/test_cutover_edit_template.py
```
确保所有测试断言全部通过。
