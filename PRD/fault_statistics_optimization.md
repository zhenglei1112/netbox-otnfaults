# 故障统计模块性能优化方案

本文档针对 Netbox OTN 故障可视化插件的“故障统计模块”在进入页面和切换统计周期时加载缓慢的问题，基于当前 `netbox_otnfaults/statistics_views.py`、`netbox_otnfaults/models.py` 和 `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js` 的实际实现进行修正，形成可落地的优化方案。

---

## 1. 性能瓶颈分析

### 1.1 重复故障检测存在多套近似 O(N*M) 实现

当前重复故障判定分散在多处：

- `_count_repeat_fiber_faults()`
- `_build_repeat_fault_id_set()`
- `FaultStatisticsDataAPI.get()` 内部的 KPI 重复判定
- `FaultStatisticsDataAPI.get()` 内部的 UI 双向重复展示判定
- `matched_preceding_faults` 的前序周期匹配逻辑

这些逻辑都围绕“相同 A 端站点，并且 Z 端站点存在交集，60 天内再次发生”的规则运行，但实现方式不统一，且大量使用当前故障列表与历史故障列表的嵌套扫描。故障数量增加时，CPU 时间会随故障数和历史对比集共同增长。

需要注意：重复故障在当前代码中存在两种语义：

- **KPI 口径**：只统计当前故障之前 60 天内已有相同 A/Z 链路故障的记录。
- **UI 展示口径**：为了表格下钻展示，会标记前后 60 天内有关联的重复故障，并可能展示前序周期中的匹配故障。

后续重构不能只替换循环，必须同时保留这两种统计语义。

### 1.2 主统计接口一次性返回大量明细数据

`FaultStatisticsDataAPI` 在一次请求中返回 KPI、图表、分子公司统计、裸纤中断统计，同时还返回：

- `details`
- `branch_company_details`

这些明细字段包含故障编号、时间字符串、站点名称拼接、分类名称、URL、重复标记等大量字段。前端在 `statistics_dashboard.js` 中将它们保存为 `currentAllDetails` 和 `currentBranchCompanyDetails`，再做本地过滤和渲染。

这会导致三个问题：

- 后端 JSON 序列化耗时增加。
- 响应体积变大，网络传输变慢。
- 浏览器解析和 DOM 渲染卡顿，尤其在切换周期时明显。

### 1.3 历史周期统计缺少缓存

按年、月、周切换时，已结束的历史周期会重复执行数据库查询、Python 聚合和 JSON 构造。对于已经结束的周期，统计口径在没有数据变更时是稳定的，应缓存主统计响应。

但缓存边界需要谨慎：统计结果不仅依赖 `OtnFault` 本表，还依赖故障 Z 端站点 M2M、`OtnFaultImpact`、业务对象、站点、省份等关联数据。不能只在 `OtnFault.save()` 中粗略清缓存。

### 1.4 业务统计接口同时承担卡片、日历和明细输出

`ServiceStatisticsDataAPI` 已经先查询周期内的 `OtnFaultImpact`，并不是对所有业务都查询影响记录。但当前实现会预先初始化所有 `BareFiberService`，并为每个服务构造：

- 当前周期统计
- 年度统计
- 12 个月月度 SLA
- 近三个月日历
- 年内完整日历
- 明细列表

因此真正的瓶颈不只是“空 SLA 合并”，还包括全量服务卡片、日历 payload 和明细数组的一次性返回。

### 1.5 统计查询缺少面向时间范围的索引

`OtnFault` 和 `OtnFaultImpact` 中高频过滤字段缺少显式 B-Tree 索引，尤其是时间范围过滤与类别/状态组合过滤：

- `OtnFault.fault_occurrence_time`
- `OtnFault.fault_category`
- `OtnFault.fault_status`
- `OtnFault.is_suspended`
- `OtnFaultImpact.service_interruption_time`
- `OtnFaultImpact.service_type`
- `OtnFaultImpact.business_impact`

仅添加低基数字段单列索引收益有限，应优先考虑与时间字段组合的复合索引。

---

## 2. 优化方案设计

### 2.1 统一重复故障检测服务

新增一个统一的重复故障检测辅助函数或小型服务，集中负责 A/Z 链路索引、KPI 重复 ID、UI 重复 ID 和前序周期匹配结果。

建议返回结构：

```python
@dataclass(frozen=True)
class RepeatFaultResult:
    kpi_repeat_ids: set[int]
    ui_repeat_ids: set[int]
    matched_preceding_faults: list[OtnFault]
```

核心策略：

1. 一次性预取参与对比的故障和 Z 端站点。
2. 以 `(interruption_location_a_id, z_site_id)` 建立链路索引。
3. 每个链路下按 `fault_occurrence_time` 排序。
4. 使用滑动窗口或二分查找定位 60 天范围，而不是扫描全部历史故障。

复杂度目标应表述为“从近似 O(N*M) 降低为按链路分桶后的 O(N log N) 或接近线性”，不要简单写成绝对 O(N)。当某条 A/Z 链路历史故障极多时，仍需要处理该链路桶内的数据。

必须保留以下语义：

- KPI 只看当前故障之前 60 天。
- UI 重复标记允许前后 60 天双向匹配。
- 前序周期中与当前周期故障匹配的记录仍可进入下钻明细，但应由明细接口按需返回。

### 2.2 主统计接口瘦身，明细下钻分页

将 `FaultStatisticsDataAPI` 拆成两个层次：

1. **主统计接口**：继续返回周期、KPI、图表、分子公司聚合、裸纤中断概览等汇总数据。
2. **明细下钻接口**：按需返回故障明细，支持服务端过滤、排序和分页。

主统计接口不再返回：

- `details`
- `branch_company_details`

新增接口建议使用插件现有 URL 命名风格：

```text
plugins/netbox-otnfaults/statistics/details/
plugins/netbox-otnfaults/statistics/service-details/
```

实际路径以 `netbox_otnfaults/urls.py` 中注册的插件 URL 为准，不在文档中臆造 Netbox 核心 API 路径。

明细接口参数建议：

- `filter_type`
- `year`
- `month`
- `week`
- `calendar_year`
- `calendar_month`
- `provinces`
- `scope`: `physical` / `branch_company`
- `category`
- `province`
- `reason`
- `resource_type`
- `source_group`
- `duration_bucket`
- `is_repeat`
- `is_long`
- `in_period`
- `page`
- `per_page`
- `ordering`

分页响应建议：

```json
{
  "results": [],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 100,
    "start": 1,
    "end": 25,
    "pages": 4
  }
}
```

前端改造要求：

- 切换统计周期时只请求主统计接口。
- 明细表格进入可见区域、用户点击图表项或点击下钻筛选时，再请求明细接口。
- 原本依赖 `currentAllDetails` 和 `currentBranchCompanyDetails` 的本地过滤逻辑迁移到服务端参数。
- 明细表格分页 UI 遵循 AGENTS.md 中的自定义分页规范：隐藏 django_tables2 默认分页，使用页码导航、显示信息和每页选择。

### 2.3 历史周期缓存

对已结束周期的主统计接口响应启用 Django Cache。缓存对象应优先覆盖汇总响应，不建议先缓存大明细数组。

缓存 Key 建议包含：

- 统计版本号
- 接口类型
- `filter_type`
- 周期参数
- 省份筛选 hash
- 用户权限相关维度（如后续存在按权限裁剪数据）

示例：

```text
otnfaults:stats:v{version}:fault-summary:{filter_type}:{period_key}:{provinces_hash}
```

缓存策略：

- 已结束周期：可缓存 24 小时或更长。
- 当前周期：默认不缓存，或使用 1-5 分钟短缓存。
- 明细接口：优先依赖分页和数据库索引，暂不作为第一阶段缓存目标。

缓存失效建议采用“版本号失效”而不是逐个删除 key：

- 保存一个全局统计缓存版本号，例如 `otnfaults:stats:version`。
- 数据变更时递增版本号。
- 新请求自动使用新版本 key，旧缓存自然过期。

需要触发失效的事件至少包括：

- `OtnFault` 的 `post_save` / `post_delete`
- `OtnFault.interruption_location` 的 `m2m_changed`
- `OtnFaultImpact` 的 `post_save` / `post_delete`
- 如后续统计依赖业务属性、站点省份等字段，应补充对应失效触发或采用管理命令手动清理缓存。

### 2.4 业务统计接口拆分与按需加载

`ServiceStatisticsDataAPI` 应拆分为汇总接口和明细接口，并减少默认返回范围。

建议第一阶段目标：

- 默认只返回当前周期或年度内有故障影响的服务卡片。
- “全部裸纤业务”视图改为分页加载，不在主接口一次性返回所有服务。
- 服务明细从 `details` 中剥离，新增服务明细分页接口。
- 日历数据只在服务卡片展开或用户进入对应视图时加载。

SLA 计算策略：

- 有 `OtnFaultImpact` 的服务计算合并中断时段。
- 无影响服务默认 SLA 为 100%，仅在用户请求“全部业务”列表时按分页返回。
- 年度 SLA、月度 SLA 可以保留实时计算，但应只对当前响应页或有影响服务计算。
- 如果后续数据量继续扩大，再引入 `ServiceMonthlySla` 快照表或管理命令生成月度快照。

### 2.5 数据库索引优化

优先增加面向统计查询的复合索引，而不是只添加低基数字段单列索引。

建议索引：

```python
models.Index(
    fields=["fault_occurrence_time", "fault_category"],
    name="otnfault_occ_cat_idx",
)
models.Index(
    fields=["fault_occurrence_time", "is_suspended", "fault_status"],
    name="otnfault_occ_state_idx",
)
models.Index(
    fields=["service_interruption_time", "service_type", "business_impact"],
    name="otnimpact_time_type_biz_idx",
)
```

可选索引：

- 如果分子公司统计大量依赖 `province`，可评估 `OtnFault(province, fault_occurrence_time)`。
- 如果业务明细经常按服务过滤，可评估 `OtnFaultImpact(bare_fiber_service, service_interruption_time)` 和 `OtnFaultImpact(circuit_service, service_interruption_time)`。

索引实施要求：

- 先检查已有迁移和数据库实际索引，避免重复索引。
- 添加迁移后按项目约束执行 `makemigrations` 后紧接 `migrate`。
- 迁移文件只放在 `netbox_otnfaults/migrations/`，不得修改 Netbox 核心目录。

---

## 3. 实施步骤规划

### 步骤一：建立性能基线

- [ ] 为 `FaultStatisticsDataAPI` 和 `ServiceStatisticsDataAPI` 增加临时日志或测试计时，分别记录数据库查询、重复检测、聚合计算、JSON 序列化耗时。
- [ ] 记录典型周期响应体大小。
- [ ] 补充或更新现有统计测试，固定 KPI、重复故障、分子公司统计和服务统计的关键口径。

### 步骤二：重复故障算法统一

- [ ] 新增统一重复故障检测辅助函数，返回 `kpi_repeat_ids`、`ui_repeat_ids` 和 `matched_preceding_faults`。
- [ ] 替换 `_count_repeat_fiber_faults()`、`_build_repeat_fault_id_set()` 和 `FaultStatisticsDataAPI.get()` 内部手写循环。
- [ ] 保留 KPI 单向口径、UI 双向口径和前序周期匹配口径。
- [ ] 使用现有重复故障相关测试验证统计结果不变。

### 步骤三：主接口瘦身与明细分页接口

- [ ] 新增故障统计明细分页接口。
- [ ] 新增分子公司明细分页能力，可通过 `scope=branch_company` 实现，也可拆成独立接口。
- [ ] 从 `FaultStatisticsDataAPI` 响应中移除 `details` 和 `branch_company_details`。
- [ ] 修改 `statistics_dashboard.js`，将本地明细过滤改为服务端查询参数。
- [ ] 按 AGENTS.md 的分页 UI 规范实现自定义分页控件。

### 步骤四：业务统计接口拆分

- [ ] 从 `ServiceStatisticsDataAPI` 中拆出服务影响明细分页接口。
- [ ] 默认只返回有故障影响的服务卡片。
- [ ] 全部业务列表和日历详情改为按需分页或展开后加载。
- [ ] 保持无故障业务 SLA 默认为 100%，避免为默认不可见数据构造完整月度和日历 payload。

### 步骤五：数据库索引与迁移

- [ ] 在 `OtnFault.Meta.indexes` 和 `OtnFaultImpact.Meta.indexes` 中添加统计查询复合索引。
- [ ] 生成迁移并紧接运行迁移。
- [ ] 使用典型统计查询对比索引前后的查询计划或耗时。

### 步骤六：历史周期缓存

- [ ] 为主统计接口增加历史周期缓存。
- [ ] 使用统计缓存版本号实现主动失效。
- [ ] 添加 `OtnFault`、故障 Z 端站点 M2M、`OtnFaultImpact` 的缓存版本递增触发。
- [ ] 当前周期默认不缓存或仅短缓存。

---

## 4. 验收标准

- [ ] 切换历史月/年周期时，主统计接口响应时间明显下降。
- [ ] 主统计接口响应体不再包含全量故障明细数组。
- [ ] 明细表格支持服务端分页、筛选和每页 25/50/100/250/500 条选择。
- [ ] 重复故障 KPI 与现有测试口径一致。
- [ ] 分子公司重复故障、前序周期重复展示逻辑保持一致。
- [ ] 业务统计默认加载不再构造所有无故障业务的完整日历 payload。
- [ ] 新增索引迁移可正常执行，且不修改 Netbox 核心目录。
