# 割接实施统计口径核对与修复计划

在割接实施数据统计中，用户遇到“仪表盘显示1，但点击跳转后割接任务列表显示2条数据”的不一致问题。
通过对代码和数据流进行深度调研分析，我们发现了如下两个口径不一致的原因：

1. **省份过滤器（Province Filter）映射失效**：
   - **仪表盘统计**：在后端，通过 `province__name__in=selected_provinces` 对省份进行过滤（例如值为 `['江苏']`）。
   - **列表页跳转**：前端点击跳转时，URL 参数拼接了 `province=江苏` 并重定向至割接列表页 `/plugins/otnfaults/cutovers/`。
   - **列表过滤解析**：通用列表页的过滤器 `CutoverTaskFilterSet` 对 `province` 的定义继承自 `NetBoxModelFilterSet` 的默认行为，它是一个基于 `Region` 外键的 `ModelMultipleChoiceFilter`。该过滤器仅支持传入 Region 的 `id` (UUID) 或 `slug`。当接收到中文名字 `province=江苏` 时，过滤器清洗失败，直接忽略了该过滤条件，退化为展示**全国**的割接任务（在对应期间全国共有 2 条，而江苏只有 1 条）。

2. **周期边界过滤参数不同步**：
   - **仪表盘统计**：后端对当前周期的统计为半开区间 `[start_date, end_date)`。即使是“当前周”，也是统计至该周结束（即下周一的 00:00:00）。
   - **列表页跳转**：当前端判断为“当前周”时，会将 `started_at_before` 参数限制为“今天的 23:59:59”，忽略了该周可能存在的属于未来日期的已实施割接任务，导致点击跳转后可能漏掉临界数据。

## 方案设计

为解决上述口径不一致，提出以下修复措施：

### 1. 兼容中文名称的省份关联过滤器
在 [filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py) 中，定义一个自定义的 `RegionMultipleChoiceFilter`。
该过滤器继承自 `ModelMultipleChoiceFilter`，在 django-filter 自带清洗（按 ID/PK 查找）返回空时，如果 URL 参数中确实含有 `province`，它会从 `request` 中提取原始值，并在 `province__name` 或 `province__slug` 中进行匹配。
由此，在通用列表页中，无论过滤参数传入的是主键 ID、URL slug 还是中文名称，都可以完美兼容并正确应用过滤条件。

### 2. 同步前端跳转的时间区间边界
在 [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js) 中，让 `buildLocalPeriodForDate` 返回值中附带本周期的实际结束时间 `actualEnd`。
在点击“割接实施”进行页面跳转时，若为当前周期，`started_at_before` 采用 `actualEnd`（即本周期的最后一天结束 `23:59:59`），从而与后端仪表盘大字的周期口径（计算整个周期）完全保持一致。

---

## 拟修改文件

### 1. 后端过滤器定义
#### [MODIFY] [filtersets.py](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/filtersets.py)
- 导入 `Region` 模型。
- 新增 `RegionMultipleChoiceFilter` 自定义过滤器类。
- 在 `CutoverTaskFilterSet` 中，显式将 `province` 字段定义为 `RegionMultipleChoiceFilter`。
- 在 `OtnFaultFilterSet` 中，显式将 `province` 字段定义为 `RegionMultipleChoiceFilter`，保持统计交互的稳健性。

### 2. 前端跳转逻辑
#### [MODIFY] [statistics_dashboard.js](file:///d:/Src/netbox-otnfaults/netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js)
- 修改 `buildLocalPeriodForDate` 返回对象，添加 `actualEnd` 属性。
- 修改 `card-cutover-implemented` 的点击事件处理函数，在拼接 `started_at_before` 参数时使用 `period.actualEnd` 以替换动态获取的 `todayStr`。

---

## 验证方案

由于没有实际的 Netbox 运行环境，我们将通过以下方式进行验证：
1. **测试脚本验证**：编写或运行单元测试，验证 `CutoverTaskFilterSet` 传入 `province=江苏` 时的过滤效果。
2. **代码审查**：检查修改是否符合 Netbox 4.x 编码规范。
