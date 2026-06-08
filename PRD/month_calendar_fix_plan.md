# 故障日历显示时长修复计划

调整故障统计模块中不同业务故障卡片的故障日历（月历图带颜色色块）默认显示时间。

## 需求说明
- **裸纤业务卡片** 与 **电路业务卡片** 故障日历默认显示 **3个月**。
- **子公司绩效卡片** 故障日历默认显示 **6个月**。
- 支持点击展开按钮拉取从年初至今的完整故障日历。
- 同步更新指标说明文案与相关自动化测试，确保测试全部通过。

## 涉及的修改

---

### 1. 后端视图服务 (Django Views)

#### [MODIFY] [statistics_views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/statistics_views.py)
- 修改 `_build_recent_calendar_months` 函数，引入 `num_months` 变量，默认值为 `6`。
- 在 `ServiceStatisticsDataAPI.get` 方法中，调用 `_build_recent_calendar_months` 时显式指定 `num_months=3`。

---

### 2. 前端展示逻辑 (JS & HTML)

#### [MODIFY] [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js)
- 将 `renderServiceInterruptCalendar` 中，`aria-label="近六个月业务中断日历"` 更改为 `aria-label="近三个月业务中断日历"`。

#### [MODIFY] [statistics_dashboard.html](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html)
- 更新说明指标文档：
  - 将 “业务卡片展示年度累计、本期间、运行月历和近六个月中断日历” 改为 “业务卡片展示年度累计、本期间、运行月历 and 近三个月中断日历”
  - 将 “中断日历默认展示近六个月，可展开查看所选年份截至当前月份的业务中断次数” 改为 “中断日历默认展示近三个月（子公司绩效考核卡片默认展示近六个月），可展开查看所选年份截至当前月份的业务中断次数”

---

### 3. 测试用例适配 (Tests)

#### [MODIFY] [test_statistics_dashboard_assets.py](file:///d:/Src/netbox-otnfaults/tests/test_statistics_dashboard_assets.py)
- 更新 `test_statistics_dashboard_exposes_metric_explanation_modal` 测试方法中关于近六个月和近三个月描述的断言。

#### [MODIFY] [test_statistics_cable_break_overview.py](file:///d:/Src/netbox-otnfaults/tests/test_statistics_cable_break_overview.py)
- 更新 `test_service_cards_render_runtime_calendar_chart` 测试方法中对于 `aria-label` 中 `近六个月业务中断日历` 的断言为 `近三个月业务中断日历`。

## 验证计划

### 自动化测试
运行相关测试用例，确保没有任何断言失败。
```bash
python manage.py test tests.test_statistics_dashboard_assets
python manage.py test tests.test_statistics_cable_break_overview
```
