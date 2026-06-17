# 割接管理单位选择“本部”时自动设置单位名称 PRD

## 1. 业务背景
在 Netbox 可视化插件的割接管理中，割接管理单位常常在选择“本部”时需要重复填写对应的管理单位全称（交通运输部通信信息中心网络公司）。为了提高用户体验并减少录入错误，需在编辑页面及后端数据保存时实现当管理单位为“本部”时自动设置割接管理单位名称的逻辑。

## 2. 功能需求
1. **编辑页面动态交互**：
   - 当用户在“割接管理单位”（`management_unit`）下拉菜单中选择“本部”（英文代码为 `headquarters`）时，系统需立刻自动在“割接管理单位名称”（`management_unit_name`）输入框中填入“交通运输部通信信息中心网络公司”。
   - 若用户选择非“本部”选项时，系统自动清理该名称输入框（设为空字符串）。
   - 页面加载时，若已选“本部”且名称输入框为空，系统自动填充该默认名称。

2. **后端健壮性保证**：
   - 在后端保存或校验数据（`CutoverTask` 模型的 `clean()` 校验函数）时，如果判断管理单位为 `headquarters` 且管理单位名称为空，自动将其设置为“交通运输部通信信息中心网络公司”。

## 3. 实现方案

### 3.1 前端修改
在 `netbox_otnfaults/templates/netbox_otnfaults/cutovertask_edit.html` 底部的 Javascript 脚本中，添加管理单位改变的监听器。
考虑到 Netbox 使用了 TomSelect 对 `<select>` 元素进行了包装，我们需要通过原生 `change` 事件以及 `tomselect.on('change')` 两种方式双重保障，确保在修改管理单位时能够触发填充逻辑。

### 3.2 后端修改
在 `netbox_otnfaults/models.py` 的 `CutoverTask` 模型中的 `clean()` 方法里增加同步填充逻辑：
```python
if self.management_unit == CutoverManagementUnitChoices.HEADQUARTERS and not self.management_unit_name:
    self.management_unit_name = '交通运输部通信信息中心网络公司'
```

### 3.3 单元测试
在 `tests/test_cutover_edit_template.py` 中编写测试，通过匹配模板文件中的 JS 代码片段确认该自动填充的交互逻辑没有缺失。
