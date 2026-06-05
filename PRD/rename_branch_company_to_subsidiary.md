# 将系统所有的“分公司”修改为“子公司”需求与执行计划文档

## 需求背景
根据业务调整要求，需要将 OTN 故障可视化插件中所有在前端展示给用户的“分公司”字样修改为“子公司”。

## 修改范围及具体内容

### 1. 前端模板 (`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`)
- 修改 Tab 导航栏按钮文本：
  - `分公司（省份）故障` -> `子公司（省份）故障`
  - `分公司绩效评分` -> `子公司绩效评分`
- 修改卡片等元素底部文本：
  - `六省分公司` -> `六省子公司`
- 修改 ECharts 各图表切换按钮的 `aria-label` 中的“分公司”为“子公司”：
  - `分公司故障数指标切换` -> `子公司故障数指标切换`
  - `分公司故障历时指标切换` -> `子公司故障历时指标切换`
  - `分公司箱线图指标切换` -> `子公司箱线图指标切换`
  - `分公司有效平均历时指标切换` -> `子公司有效平均历时指标切换`
  - `分公司周趋势指标切换` -> `子公司周趋势指标切换`
  - `分公司周趋势百公里切换` -> `子公司周趋势百公里切换`
- 调整相关 HTML 注释，保持代码整洁。

### 2. 前端 JS 逻辑 (`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`)
- 修改无数据提示及 aria-label 属性：
  - `aria-label="本年分公司故障月度统计"` -> `aria-label="本年子公司故障月度统计"`
  - `aria-label="近六个月分公司中断日历"` -> `aria-label="近六个月子公司中断日历"`
  - `暂无分公司绩效考核数据` -> `暂无子公司绩效考核数据`
  - `当前分公司范围及过滤条件下，无可展示的故障数据` -> `当前子公司范围及过滤条件下，无可展示的故障数据`

### 3. 后端视图数据返回 (`netbox_otnfaults/statistics_views.py`)
- 修改接口返回的绩效卡片标签：
  - `'label': f'{province}分公司'` -> `'label': f'{province}子公司'`

### 4. 单元测试 (`tests/test_statistics_branch_company.py`)
- 修改对模板的断言字符串：
  - `self.assertIn('分公司（省份）故障', template)` -> `self.assertIn('子公司（省份）故障', template)`
  - `self.assertIn('分公司绩效评分', template)` -> `self.assertIn('子公司绩效评分', template)`

## 验证方案
在本地命令行中执行以下单元测试，确保测试用例全部通过：
```bash
python -m unittest tests/test_statistics_branch_company.py
```
由于此修改只改动界面文案，测试全通即可证明没有破坏性影响。
