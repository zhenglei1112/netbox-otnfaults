# 故障统计业务中断卡片实施文档

## 1. 背景与目标

根据手绘图，故障统计模块需要在业务故障统计区域增加“业务中断”汇总卡片，用于在当前统计周期内集中展示业务中断的 SLA、时长、次数、分类构成、趋势和中断日历。

现有实现已经具备业务统计基础：

- 后端入口：`netbox_otnfaults/statistics_views.py` 中的 `StatisticsServiceDataView`
- 数据来源：`OtnFaultImpact`，关联 `OtnFault`、`BareFiberService`、`CircuitService`
- 前端入口：`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` 中的 `loadServiceData()`、`renderServiceCards()`
- 页面容器：`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html` 中的 `#tab-service` 与 `#tab-circuit-service`
- 既有测试：`tests/test_statistics_service_sorting.py`、`tests/test_statistics_dashboard_assets.py`

本次目标是在不改变现有业务明细表和业务卡片下钻行为的前提下，增加一个可复用的业务中断汇总区。它应优先使用现有 `statistics/service-data/` API 扩展数据结构，不新增 NetBox 核心 API，也不修改 NetBox 核心目录。

## 2. 页面设计

### 2.1 页面位置

在“裸纤业务故障”和“电路业务故障”两个 Tab 顶部，各增加一块业务中断汇总区：

- `#service-interruption-overview`：裸纤业务中断汇总
- `#circuit-service-interruption-overview`：电路业务中断汇总

位置放在现有 `service-cards-container` / `circuit-service-cards-container` 之前。这样用户进入业务统计 Tab 时先看到总览，再向下查看按业务拆分的卡片和明细。

### 2.2 信息层级

汇总区按三段展示：

1. 顶部 KPI 行
   - 周期标题：复用现有 `period` 文案，例如“2026年4月第4周”
   - 周期业务里程：优先展示可计算的业务总里程，不能计算时显示 `-`
   - SLA：周期业务可用率
   - 业务中断总时长
   - 业务中断次数

2. 中部分类矩阵
   - 光缆中断
   - 光缆抖动
   - 光缆劣化
   - 设备故障
   - 供电故障
   - 空调故障
   - 其他
   - 长时中断
   - 超时中断
   - 重复中断

3. 底部趋势与日历
   - 月度趋势柱图：当前年份 1 月至 12 月的业务中断次数与中断时长
   - 中断日历：当前统计周期或当前月份的每日中断次数热力点

## 3. 统计口径

### 3.1 基础数据集

当前周期业务影响记录：

```python
OtnFaultImpact.objects.select_related(
    "otn_fault",
    "bare_fiber_service",
    "circuit_service",
).filter(
    service_interruption_time__gte=start_date,
    service_interruption_time__lt=end_date,
)
```

按 Tab 过滤：

- 裸纤业务：`service_type == ServiceTypeChoices.BARE_FIBER`
- 电路业务：`service_type == ServiceTypeChoices.CIRCUIT`

未恢复业务影响使用 `timezone.localtime()` 作为临时恢复时间计算当前历时，但明细仍显示“未恢复”。

### 3.2 KPI 口径

| 字段 | 口径 |
| --- | --- |
| `interruption_count` | 当前业务类型下 `OtnFaultImpact` 条数 |
| `total_duration` | 每条影响的 `service_recovery_time/service_interruption_time` 差值小时数之和；未恢复使用当前时间 |
| `avg_duration` | `total_duration / interruption_count` |
| `long_count` | 单次业务中断历时大于等于 6 小时的条数 |
| `timeout_count` | 关联 `OtnFault.timeout == True` 的条数 |
| `repeat_count` | 同一业务 60 天内再次出现业务影响的条数，沿用现有 per-service 逻辑 |
| `sla` | 按业务维度合并重叠不可用时段后计算可用率 |

SLA 计算需要避免同一业务在重叠时段内重复扣减不可用时长：

```text
业务不可用小时数 = 按 service_key 分组合并重叠区间后的小时数之和
业务总小时数 = 周期小时数 * 当前业务类型下受统计业务数量
SLA = (业务总小时数 - 业务不可用小时数) / 业务总小时数 * 100
```

如果当前周期没有业务记录，SLA 显示为 `100.0000`，但前端应同时显示“当前周期无业务中断记录”，避免误读为全量业务可用性评估。

### 3.3 分类口径

分类优先使用 `imp.otn_fault.fault_category`：

- `fiber_break` -> 光缆中断
- `fiber_jitter` -> 光缆抖动
- `fiber_degradation` -> 光缆劣化
- `device_fault` -> 设备故障
- `power_fault` -> 供电故障
- `ac_fault` -> 空调故障
- 空值或无法识别 -> 其他

割接相关口径使用现有字段表达：

- 光缆整改：`otn_fault.interruption_reason == "cable_rectification"`
- 计划报备：`otn_fault.interruption_reason_detail == "planned_reporting"`
- 非报备：`otn_fault.interruption_reason_detail == "unplanned_reporting"`

手绘图中出现的“强制割接、统管割接、计划割接、应急割接、外协超割”等目前没有一一对应的独立模型字段。第一阶段不新增数据库字段，只将其落到文档中的待确认扩展项。后续如确认需要录入，应先扩展 `OtnFault` 的割接类型 Choice 字段，再补迁移、FilterSet、表单和 API 序列化。

### 3.4 趋势与日历口径

月度趋势固定按当前筛选日期所在年份生成 12 个月数据：

- `month_labels`: `["1月", "2月", ..., "12月"]`
- `count_series`: 每月业务中断条数
- `duration_series`: 每月业务中断总时长
- `timeout_series`: 每月超时中断条数

中断日历按当前统计周期生成每日数据：

- 年统计：可只返回当前选中月份或按月聚合，避免 365 个点挤压页面
- 月统计：返回当月每日数据
- 周统计：返回周一至周日每日数据

推荐第一阶段采用“当前统计周期每日数据”，前端根据点数自动布局。

## 4. API 响应结构

在 `StatisticsServiceDataView` 现有响应中增加 `overview` 字段，保留 `services` 和 `details` 兼容现有前端。

```json
{
  "period": {},
  "period_total_hours": 168.0,
  "overview": {
    "bare_fiber": {
      "label": "裸纤业务",
      "service_type": "裸纤业务",
      "business_distance_km": null,
      "interruption_count": 12,
      "total_duration": 98.5,
      "avg_duration": 8.21,
      "long_count": 5,
      "timeout_count": 3,
      "repeat_count": 2,
      "sla": 99.9414,
      "categories": [
        {"key": "fiber_break", "label": "光缆中断", "count": 8, "duration": 80.0},
        {"key": "fiber_jitter", "label": "光缆抖动", "count": 2, "duration": 6.5},
        {"key": "fiber_degradation", "label": "光缆劣化", "count": 1, "duration": 2.0},
        {"key": "other", "label": "其他", "count": 1, "duration": 10.0}
      ],
      "rectification": {
        "total": 3,
        "planned": 2,
        "unplanned": 1
      },
      "monthly_trend": {
        "labels": ["1月", "2月", "3月", "4月"],
        "counts": [1, 0, 3, 8],
        "durations": [2.0, 0.0, 18.5, 78.0],
        "timeouts": [0, 0, 1, 2]
      },
      "calendar": [
        {"date": "2026-04-01", "count": 2, "duration": 4.5, "timeout_count": 1}
      ]
    },
    "circuit": {
      "label": "电路业务",
      "service_type": "电路业务",
      "business_distance_km": null,
      "interruption_count": 0,
      "total_duration": 0.0,
      "avg_duration": 0.0,
      "long_count": 0,
      "timeout_count": 0,
      "repeat_count": 0,
      "sla": 100.0,
      "categories": [],
      "rectification": {"total": 0, "planned": 0, "unplanned": 0},
      "monthly_trend": {"labels": [], "counts": [], "durations": [], "timeouts": []},
      "calendar": []
    }
  },
  "services": [],
  "details": []
}
```

## 5. 后端实施

### 5.1 修改文件

- 修改：`netbox_otnfaults/statistics_views.py`
- 测试：新增或扩展 `tests/test_statistics_service_overview.py`

### 5.2 建议函数拆分

在 `statistics_views.py` 中新增纯函数，便于源码级单元测试：

```python
def _service_key_for_impact(impact: OtnFaultImpact) -> tuple[str, str, str, int]:
    """Return service key, name, type label, and sort rank for an impact."""
```

```python
def _merge_unavailable_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Merge overlapping unavailable intervals."""
```

```python
def _build_service_interruption_overview(
    impacts: list[OtnFaultImpact],
    start_date: datetime,
    end_date: datetime,
    now: datetime,
    service_type: str,
) -> dict[str, object]:
    """Build one overview block for bare fiber or circuit service impacts."""
```

```python
def _build_service_monthly_trend(
    service_type: str,
    selected_year: int,
    now: datetime,
) -> dict[str, list[object]]:
    """Build 12-month interruption count, duration, and timeout trend."""
```

```python
def _build_service_interruption_calendar(
    impacts: list[OtnFaultImpact],
    start_date: datetime,
    end_date: datetime,
    now: datetime,
) -> list[dict[str, object]]:
    """Build daily interruption count and duration for the active period."""
```

所有新增 Python 函数需要带类型提示。现有视图内部变量类型也应在新增逻辑中保持明确。

### 5.3 查询优化

当前 API 已使用 `select_related("otn_fault", "bare_fiber_service", "circuit_service")`。新增趋势数据时不要对每个月循环查询 12 次，建议一次查询全年数据后在 Python 中按月份聚合：

```python
year_start = timezone.make_aware(datetime(selected_year, 1, 1))
year_end = timezone.make_aware(datetime(selected_year + 1, 1, 1))
year_impacts = list(
    OtnFaultImpact.objects.select_related(
        "otn_fault",
        "bare_fiber_service",
        "circuit_service",
    ).filter(
        service_interruption_time__gte=year_start,
        service_interruption_time__lt=year_end,
    )
)
```

### 5.4 兼容性要求

- 不删除或改名现有 `services` 字段。
- 不改变现有 `details` 字段。
- 不改变现有 `services_result.sort(key=lambda x: (x['sort_rank'], -x['count'], x['name']))` 排序口径。
- 不改变现有业务卡片点击过滤明细行为。

## 6. 前端实施

### 6.1 修改文件

- 修改：`netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- 修改：`netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- 修改：`netbox_otnfaults/static/netbox_otnfaults/css/statistics_dashboard.css`
- 测试：扩展 `tests/test_statistics_dashboard_assets.py`

### 6.2 模板容器

在 `#tab-service` 中加入：

```html
<div id="service-interruption-overview" class="business-interruption-overview mb-4">
  <div class="text-center text-muted py-5">
    <i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...
  </div>
</div>
```

在 `#tab-circuit-service` 中加入：

```html
<div id="circuit-service-interruption-overview" class="business-interruption-overview mb-4">
  <div class="text-center text-muted py-5">
    <i class="mdi mdi-loading mdi-spin me-1"></i> 数据加载中...
  </div>
</div>
```

### 6.3 JS 渲染入口

在 `loadServiceData()` 成功后增加：

```javascript
renderBusinessInterruptionOverview(
    data.overview && data.overview.bare_fiber,
    'service-interruption-overview'
);
renderBusinessInterruptionOverview(
    data.overview && data.overview.circuit,
    'circuit-service-interruption-overview'
);
```

新增渲染函数：

```javascript
function renderBusinessInterruptionOverview(overview, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!overview) {
        container.innerHTML = '<div class="text-center text-muted py-5">暂无业务中断汇总数据</div>';
        return;
    }

    const slaColor = getSlaColor(overview.sla);
    const categoryHtml = (overview.categories || []).map(renderBusinessInterruptionCategory).join('');

    container.innerHTML = `
        <section class="statistics-business-interruption-card">
            <div class="statistics-business-interruption-kpis">
                ${renderBusinessInterruptionKpi('SLA', overview.sla, '%', slaColor)}
                ${renderBusinessInterruptionKpi('业务中断时长', overview.total_duration, '小时')}
                ${renderBusinessInterruptionKpi('业务中断次数', overview.interruption_count, '次')}
                ${renderBusinessInterruptionKpi('长时中断', overview.long_count, '次')}
                ${renderBusinessInterruptionKpi('超时中断', overview.timeout_count, '次')}
            </div>
            <div class="statistics-business-interruption-categories">
                ${categoryHtml || '<span class="text-muted small">当前周期无分类数据</span>'}
            </div>
            <div class="statistics-business-interruption-charts">
                <div class="statistics-business-interruption-chart" id="${containerId}-monthly-chart"></div>
                <div class="statistics-business-interruption-calendar" id="${containerId}-calendar"></div>
            </div>
            <div class="statistics-strip-card-footer">${escapeHtml(overview.label || '业务中断')}</div>
        </section>
    `;

    renderBusinessInterruptionMonthlyChart(`${containerId}-monthly-chart`, overview.monthly_trend);
    renderBusinessInterruptionCalendar(`${containerId}-calendar`, overview.calendar);
}
```

复用现有 ECharts 初始化和主题工具，避免引入新图表库。

### 6.4 样式要求

CSS 应复用现有 `statistics-strip-card` 的视觉语言：

- 白底
- 细边框
- 底部蓝绿色标题条
- 指标横向分栏
- 移动端自动换行
- 不使用独立营销式大卡片

建议新增类名：

- `.statistics-business-interruption-card`
- `.statistics-business-interruption-kpis`
- `.statistics-business-interruption-kpi`
- `.statistics-business-interruption-categories`
- `.statistics-business-interruption-category`
- `.statistics-business-interruption-charts`
- `.statistics-business-interruption-chart`
- `.statistics-business-interruption-calendar`

图表高度建议固定：

```css
.statistics-business-interruption-chart {
  min-height: 220px;
}

.statistics-business-interruption-calendar {
  min-height: 160px;
}
```

## 7. 测试计划

### 7.1 后端测试

新增 `tests/test_statistics_service_overview.py`，覆盖：

- API 响应包含 `overview.bare_fiber` 与 `overview.circuit`
- 裸纤与电路业务分别聚合，不互相混入
- SLA 合并同一业务重叠不可用时段
- 分类计数覆盖光缆中断、抖动、劣化、设备、供电、空调和其他
- 光缆整改的 `planned_reporting` / `unplanned_reporting` 统计正确
- 未恢复业务使用当前时间计算历时
- 月度趋势返回 12 个月结构
- 日历数据按日期聚合

### 7.2 前端源码级测试

扩展 `tests/test_statistics_dashboard_assets.py`，覆盖：

- 模板包含 `service-interruption-overview`
- 模板包含 `circuit-service-interruption-overview`
- JS 包含 `renderBusinessInterruptionOverview`
- JS 在 `loadServiceData()` 成功后渲染两个 overview
- JS 包含 SLA 颜色阈值
- CSS 包含 `.statistics-business-interruption-card`
- CSS 固定趋势图和日历容器高度

### 7.3 验证命令

```powershell
python -m unittest tests.test_statistics_service_overview
python -m unittest tests.test_statistics_dashboard_assets tests.test_statistics_service_sorting
node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js
python -m py_compile netbox_otnfaults/statistics_views.py
```

## 8. 实施步骤

1. 先写后端测试，锁定 `overview` 响应结构与 SLA 合并口径。
2. 在 `statistics_views.py` 中抽出业务 key、区间合并、分类聚合、趋势聚合、日历聚合 helper。
3. 在 `StatisticsServiceDataView.get()` 中生成 `overview`，保持现有 `services/details` 不变。
4. 写前端源码级测试，锁定模板容器、JS 渲染入口和 CSS 类名。
5. 修改 `statistics_dashboard.html`，在两个业务 Tab 顶部加入 overview 容器。
6. 修改 `statistics_dashboard.js`，增加 overview 渲染、趋势图和日历渲染。
7. 修改 `statistics_dashboard.css`，补充汇总卡片、分类矩阵、图表和响应式样式。
8. 运行后端、前端源码级测试和语法检查。
9. 如后续确认需要“强制割接/统管割接/应急割接/外协超割”独立统计，再单独新增模型字段与迁移，不与本次 UI 汇总混在一起。

## 9. 风险与待确认项

- 业务总里程目前没有明确统一字段。第一阶段 `business_distance_km` 返回 `null`，前端显示 `- km`；如需计算，需确认裸纤业务和电路业务分别使用哪个长度字段。
- 手绘图中的割接细分项没有现成字段，不应强行用文本匹配评论或故障详情。
- 年统计下的日历如果展示 365 个点会过密，第一阶段建议展示当前统计周期的每日聚合，后续可加月选择。
- 当前业务统计 API 查询的是 `service_interruption_time` 落在周期内的记录，不包含周期前开始、周期内仍未恢复的跨周期中断。若业务要求 SLA 覆盖跨周期不可用，应另行调整查询为“与周期有交集”的区间查询。
