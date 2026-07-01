# YoY and PoP Dashboard Comparison Walkthrough & Verification Report

This document records the final code design, changes, and automated verification status for the unified comparison period and Year-over-Year (YoY) metrics.

## 1. Feature Specifications & Rationale

| Dimension | PoP Period | YoY Period |
|---|---|---|
| Year (年) | Previous Year (上一年) | Previous Year (YoY and PoP display once as "较去年") |
| Half-Year (半年) | Previous half-year | Same half-year of previous year |
| Quarter (季度) | Previous quarter | Same quarter of previous year |
| Month (月) | Previous month | Same month of previous year |
| Week (周) | Previous ISO Week | Retreat exactly 364 days from current window |

**Week YoY alignment reason**: Retreating 364 days aligns day-of-week precisely (e.g., Monday to Monday) and keeps the exact 7-day window size without needing complex ISO week boundaries.

---

## 2. Implemented Code Changes

### 后端设计与重构 (Python / Django)
- **解包升级**：[netbox_otnfaults/statistics_views.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/statistics_views.py) `_parse_time_range(request)` 返回 7 元组：
  `start_date, end_date, prev_start_date, prev_end_date, yoy_start_date, yoy_end_date, filter_type`
- **公共计算抽取**：新增 `_compute_comparison_period_data` 方法。此方法对任何统计周期（环比/同比）进行全指标（KPI、影响程度、总体大类、挂起/其它、光缆中断、子公司、裸纤）的统一聚合计算，消除了重复查询逻辑。
- **视图主入口重构**：`FaultStatisticsDataAPI.get()` 重构为通过 `_compute_comparison_period_data()` 一键拉取 `prev_data` 与 `yoy_data`。数据字典中新增 `yoy_kpis` 等 7 大类 YoY 指标，实现完全向下兼容。
- **子公司环同比口径对齐**：修复了省份筛选模式下子公司环同比口径失真的 P1 Bug。在 `_compute_comparison_period_data()` 内部计算时，同时保留了未经省份过滤的周期故障列表 `unfiltered_all_faults = list(qs_period)`，并将其传入 `_build_branch_company_statistics()`，从而与当前周期调用子公司统计时传入的 `unfiltered_current_faults` 保持完全相同的全量分公司口径。同时物理总体、影响等级统计仍使用经过省份过滤的 `all_faults`。
- **缓存架构双防升级 (Schema V2 & 结构强校验)**：为规避老格式缓存导致生产环境同比数据短期缺失的 P2 级 Bug，对缓存键格式与缓存命中判定逻辑进行了升级。将缓存 Key 结构命名由 `fault-summary` 升级为 `fault-summary:v2`。同时，在读取缓存时新增强校验断言 `if 'yoy_kpis' in cached_data`，双重保证在热部署上线后，任何不含同比数据的老格式缓存都将被拒绝并自动执行重算，确保平滑发布。

### 前端逻辑重构 (HTML5 / JS / Bootstrap5)
- **多维度趋势引擎**：在 [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js) 中增加 `buildComparisonTrendHtml()`，它接受当前值、环比值与同比值，输出包含“环比 +/-X”和“同比 +/-Y”的 HTML 片段。
- **年维度展示折叠**：当前维度为年（`year`）时，`buildComparisonTrendHtml` 会自动过滤为单行“较去年”的环比趋势。
- **卡片卡槽扩展**：重构 `buildFlexItemCore` 与 `buildFlexGroup` 适配同比项的传入与比对，支持在密集卡片和列表项内自动渲染同比与环比数值。
- **裸纤卡片布局优化**：隐藏裸纤中断情况卡片中与页脚重复的中央标签，且在 `renderBareFiberInterruption` 中调用趋势引擎时指定 `shortFormat`（单行显示），从而将裸纤指标、同比、环比对齐在同一行内展示，杜绝换行（目前已随全局改动统一显示“环比/同比”全称标签）。
- **保留主指标颜色**：将 `applyTrendValueColor()` 调整为直接返回的空操作（No-op）函数。同时，在 `buildFlexItemCore` 中移除了调用 `getTrendValueClass` 来重写列表卡片数字颜色的逻辑，改为直接应用默认的主题色彩 Class（`colorClass`）。由此实现了无论大 KPIs、列表格子小卡片还是裸纤看板，所有的主指标数值一律固定为系统默认颜色，绝不再根据环比升降进行红/绿变色，使数据展示更为高雅和严谨。
- **静态测试断言死代码清理**：删除了 `statistics_dashboard.js` 中此前为了临时兼容老断言而保留的注释行（如已废弃的旧版本两参数渲染调用等）。同步更新了 `test_statistics_cable_break_overview.py` 中的静态断言，使其全部对准真实运行的最新代码逻辑。这彻底清除了测试可能会被死注释行误导通过的潜在隐患，提高了测试的可信度。
- **百分比单一指标展示优化**：应最新产品优化要求，所有环同比趋势数据改为只展示百分比变动幅度（如 `环比 -21.4%`、`同比 +100.0%` 或 `较去年 -12.5%`），移除了此前版本在括号中展现的具体数值差值及单位，进一步净化了 UI 字符空间，使页面卡片布局视觉焦点更为集中。
- **故障等级与事件汇总环比绝对值还原**：为趋势引擎添加了 `simpleDiffOnly` 模式。在此模式下，指标趋势将只计算并显示环比变化绝对值（形如 `+3` 或 `-20`），不包含任何百分比、同比或文字标签，且在差值为 $0$ 时保持不显示（即还原为空白）。该配置已应用在“故障等级与事件汇总”卡片的 8 个小格子里，且特别定制使其排版挂载为主指标的**右侧行内（同行、不折行）**展现，保持了小彩色卡片紧凑、平衡的视觉美感。
- **卡片高度与独立成行排版优化**：除裸纤业务中断卡片（因横向较宽，保留指标行内右侧单行格式）外，将所有涉及环同比的列表格卡片以及主看板大 KPIs 中的趋势标签移动到了主指标（大数字）正下方独立成行。同时在趋势行内，环比与同比采用**横向并排、不折行**的 Flexbox 排布（中间以优雅的 gap 间距拉开）。并且将卡片的最小高度统一从 `6.4rem` 调优增加至 `7.4rem`。这兼顾了卡片垂直舒展性与横向防重叠安全性，使得布局极为清爽美观。

---

## 3. Test Coverage & Verification

All automated tests in the test suite pass with successful results:
```powershell
python -m unittest discover -s tests -p "test_statistics_*.py"
```

140 tests have been run and verified. Updated static string assert cases to match refactored signatures in the following files:
- `tests/test_statistics_dashboard_assets.py`
- `tests/test_statistics_bare_fiber_interruption.py`
- `tests/test_statistics_branch_company.py`
- `tests/test_statistics_cable_break_overview.py`
