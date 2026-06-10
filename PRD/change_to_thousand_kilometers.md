# PRD: 故障统计模块子公司百公里统计口径修改为千公里

## 1. 业务背景
在光传送网（OTN）故障统计中，原先对子公司（分公司）的故障频次、故障历时考核与趋势分析，是基于“百公里”口径（即每百公里发生故障起数或每百公里故障历时小时数）进行计算和展示。为了使数据更具可比性，现要求将子公司共计中的所有“百公里”统计口径调整为“千公里”口径。

## 2. 统计口径与计算公式变更
1. **千公里计算公式**：
   - 原公式（百公里）：`value * 100.0 / length_km`
   - 新公式（千公里）：`value * 1000.0 / length_km`
2. **考核评分扣分系数调整**：
   - 频次扣分原公式：`min(30.0, count_per_100km * 18.0)`
     因为千公里的值是百公里的 10 倍，为了维持原有的考核得分不受口径变化影响，扣分系数需同步除以 10。
     新公式：`min(30.0, count_per_1000km * 1.8)`
   - 历时扣分原公式：`min(25.0, duration_per_100km * 4.0)`
     同理，历时扣分系数需同步除以 10。
     新公式：`min(25.0, duration_per_1000km * 0.4)`

## 3. 修改范围
### 3.1 后端逻辑 (`netbox_otnfaults/statistics_views.py`)
- 重命名 `_per_100km` 辅助函数为 `_per_1000km`，并调整乘数为 `1000.0`。
- 修改 `_calculate_branch_performance_score` 内部的 `deductions` 计算公式。
- 修改 `_empty_branch_performance_metrics`、`_finalize_branch_performance_metrics` 和 `_build_branch_company_statistics` 函数中涉及的返回字典键名：
  - `count_per_100km` -> `count_per_1000km`
  - `duration_per_100km` -> `duration_per_1000km`
  - `valid_duration_per_100km` -> `valid_duration_per_1000km`
  - `week_count_per_100km` -> `week_count_per_1000km`
  - `week_duration_per_100km` -> `week_duration_per_1000km`
  - `week_valid_duration_per_100km` -> `week_valid_duration_per_1000km`
  - `month_count_per_100km` -> `month_count_per_1000km`
  - `month_duration_per_100km` -> `month_duration_per_1000km`
  - `month_valid_duration_per_100km` -> `month_valid_duration_per_1000km`
  - `per_100km` -> `per_1000km`

### 3.2 前端模板 (`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`)
- 修改子公司选项卡中指标切换单选按钮的 `value` 属性（如 `count_per_1000km`、`duration_per_1000km`、`per_1000km`）。
- 将前端界面上的“百公里”文字全部汉化替换为“千公里”（如“百公里起数” -> “千公里起数”，“百公里时长” -> “千公里时长”等）。

### 3.3 前端脚本 (`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`)
- 将读取后端数据的键名从千公里键名进行匹配（如 `count_per_1000km`、`week_count_per_1000km` 等）。
- 调整 ECharts 的 X/Y 轴单位、卡片中的 label 文字以及提示框（tooltip）里的文本口径（例如“起/百公里” -> “起/千公里”，“小时/百公里” -> “小时/千公里”，“有效时长不支持百公里统计” -> “有效时长不支持千公里统计”）。

### 3.4 单元测试 (`tests/test_statistics_branch_company.py`)
- 对齐所有对 `statistics_views.py`、`statistics_dashboard.html`、`statistics_dashboard.js` 进行的 AST/文本断言。
- 确保测试中的“百公里”断言更新为“千公里”，千公里相关字段名能够正常通过测试。

## 4. 验证方法
- 运行本地测试：`python -m unittest tests/test_statistics_branch_company.py` 确保全部测试用例通过。
