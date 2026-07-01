# OTN 故障统计统一比较周期与同比口径需求文档

## 1. 业务背景
在现有的 Netbox OTN 故障统计看板中，只支持了“环比”周期的展示。为了更全面地评估故障趋势与治理效果，需要新增“同比”维度的比对。
本方案建议采用“统一比较周期”方案，在后端扩展解析函数，一次性返回当前周期、环比周期和同比周期。前端相应地扩展趋势渲染组件，能够支持多比较项（环比/同比）的动态排版展示。

## 2. 同比口径定义

根据当前选中的时间统计维度，同比口径建议对齐如下：

| 当前维度 | 现有环比范围 | 新增同比范围 | 备注说明 |
| :--- | :--- | :--- | :--- |
| **年** | 上一年 | 上一年 | 与环比范围重合，在前端建议只展示一个“较去年” |
| **半年** | 上一个半年 | 去年同期半年 | 例如 2026年上半年 同比为 2025年上半年 |
| **季度** | 上一季度 | 去年同季度 | 例如 2026年Q2 同比为 2025年Q2 |
| **月** | 上月 | 去年同月 | 例如 2026年7月 同比为 2025年7月 |
| **周** | 上周 | 整体回退 364 天 | 对应 ISO 周，通过当前周起止整体回退 364 天（52周）以对齐星期几并保持统计窗口长度一致 |

## 3. 后端设计

### 3.1 扩展时间范围解析
后端修改 `netbox_otnfaults/statistics_views.py` 中的 `_parse_time_range(request)` 函数。
原本返回：`(start_date, end_date, prev_start_date, prev_end_date, filter_type)`。
修改为返回 7 元组：`(start_date, end_date, prev_start_date, prev_end_date, yoy_start_date, yoy_end_date, filter_type)`。

对于 `yoy_start_date` 和 `yoy_end_date` 的计算算法：
- **年 (year)**: 
  - `yoy_start_date = timezone.datetime(year - 1, 1, 1, tzinfo=tz)`
  - `yoy_end_date = start_date`
- **半年 (half)**:
  - `yoy_start_date = timezone.datetime(year - 1, start_month, 1, tzinfo=tz)`
  - `yoy_end_date = timezone.datetime(end_year - 1, end_month, 1, tzinfo=tz)`
- **季度 (quarter)**:
  - `yoy_start_date = timezone.datetime(year - 1, start_month, 1, tzinfo=tz)`
  - `yoy_end_date = timezone.datetime(end_year - 1, end_month, 1, tzinfo=tz)`
- **月 (month)**:
  - `yoy_start_date = timezone.datetime(year - 1, month, 1, tzinfo=tz)`
  - `yoy_end_date = timezone.datetime(next_month_year - 1, next_month, 1, tzinfo=tz)`
- **周 (week)**:
  - `yoy_start_date = start_date - timedelta(days=364)`
  - `yoy_end_date = end_date - timedelta(days=364)`

由于改动了 `_parse_time_range()` 的签名，以下调用该函数的所有位置均需同步更新解包签名（包括 `_yoy_start_date` 和 `_yoy_end_date`）：
1. `netbox_otnfaults/views.py` (2处)
2. `netbox_otnfaults/statistics_views.py` (4处)

### 3.2 抽象通用周期计算函数
在 `netbox_otnfaults/statistics_views.py` 中新增 `_compute_comparison_period_data(...)`，用于计算非当前期的时间区间（环比和同比）下的全维度统计数据，消除重复的统计逻辑：
- 裸纤业务中断情况汇总
- 影响程度等级卡片与未关闭割接统计
- 各分类故障 KPI 汇总
- 光缆中断故障的平均历时及长时统计
- 重复故障检测 (通过 `detect_repeat_faults` 库函数)
- 子公司相关绩效扣分与统计

在 `FaultStatisticsDataAPI` 中，分别以当前、环比、同比三个时间周期获取数据。环比和同比直接复用该通用计算函数。

### 3.3 扩展 API 报文结构
API 响应中新增 `yoy_*` 同比字段组：
- `yoy_kpis`: 同比核心指标
- `yoy_impact_level_summary`: 同比故障等级汇总
- `yoy_charts`: 同比图表分类 (包含 `category`, `ring_fiber`, `ring_power`, `ring_environment` 等)
- `yoy_cable_break_overview`: 同比光缆中断概览
- `yoy_bare_fiber_interruption`: 同比裸纤业务中断
- `yoy_branch_company`: 同比子公司数据
- `yoy_other_overview`: 同比挂起及其它故障汇总

---

## 4. 前端设计

### 4.1 趋势渲染引擎扩展
在 `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` 中重写趋势渲染器：
1. **统一趋势构造器**：新增 `buildComparisonTrendHtml(currentVal, prevVal, yoyVal, integer, shortFormat)` 函数，复用红升绿降规则（值增加为 `text-danger` 红色，减少为 `text-success` 绿色，持平为 `text-muted` 0 灰色）。
2. **年维度特殊展示**：如果当前统计维度 `filter_type` 为 `year`，环比与同比范围重叠，因此仅展示单行“较去年 `+X`”或“较去年 `0`”。
3. **两行小标签**（默认格式）：对核心指标卡片，换行排列：
   - 环比 `+3`
   - 同比 `-2`
4. **单行短格式**（空间紧张）：对图块右侧色块等小空间，采用横向排版：
   - `环 +3  同 -2`

### 4.2 核心指标卡与子卡片适配
- 扩展 `renderTrendBesideMetric` 函数签名，添加 `yoyValue` 和 `shortFormat` 参数。
- 修改 `buildFlexGroup` 与 `buildFlexItemCore` 以接受 `yoyItems` 参数，实现子项目卡片上环同比的正确解析 and 渲染。
- 修改 `renderKPIs`, `renderImpactLevelOverview`, `renderOverallSummary`, `renderOverallOtherSummary`, `renderCableBreakOverview`, `renderBranchCompanyOverview`, `renderBareFiberInterruption` 的渲染流水线。

---

## 5. 校验与测试计划
1. **静态特征测试**：运行 `python -m unittest discover -s tests -p "test_statistics_*.py"`，并根据签名的微调修改对应的静态断言，确保所有的测试全部绿灯通过。
2. **逻辑核对**：
   - 跨年周同比的计算正确性。
   - 无同比数据时（如历史首年）显示 `同比 --`。
   - 年维度下趋势显示为单行且只展示“较去年”。
