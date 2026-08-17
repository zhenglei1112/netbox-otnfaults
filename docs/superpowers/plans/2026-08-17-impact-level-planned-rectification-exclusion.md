# 故障影响等级统计排除计划整改故障 Implementation Plan

> **For agentic workers:** 按任务顺序在当前工作区执行；先验证测试失败，再实现最小修改。受项目 `AGENTS.md` 约束，不创建 worktree、分支或 Git 提交。

**Goal:** 让“故障和异常事件（按影响程度划分等级）”的当前期、对比期、环形图和下钻明细统一排除“光缆整改 + 计划报备”故障。

**Architecture:** 复用 `statistics_views.py` 已有 `_exclude_planned_rectification_faults()`。当前期和对比期在 `_annotate_class_i_business_impact()` 前过滤，等级聚合与环形图自然共享结果；下钻接口在出现 `impact_level` 或 `fault_group` 参数时应用同一过滤。

**Tech Stack:** Python 3、Django ORM、`unittest` 源码级回归测试。

---

### Task 1: 锁定影响等级统计与下钻口径

**Files:**
- Modify: `tests/test_statistics_impact_level.py`

- [ ] **Step 1: 增加当前期与对比期失败测试**

```python
def test_impact_level_period_queries_exclude_planned_rectification_faults(self) -> None:
    source = _read(STATISTICS_VIEWS_PATH)
    comparison_source = source.split(
        "def _compute_comparison_period_data", 1
    )[1].split("class FaultStatisticsDataAPI", 1)[0]
    current_source = source.split(
        "class FaultStatisticsDataAPI", 1
    )[1].split("class FaultStatisticsDetailsAPI", 1)[0]

    self.assertIn(
        "_annotate_class_i_business_impact(\n"
        "        _exclude_planned_rectification_faults(filtered_qs)\n"
        "    )",
        comparison_source,
    )
    self.assertIn(
        "_annotate_class_i_business_impact(\n"
        "            _exclude_planned_rectification_faults(filtered_current_qs)\n"
        "        )",
        current_source,
    )
```

- [ ] **Step 2: 增加下钻失败测试**

```python
def test_impact_level_and_ring_details_exclude_planned_rectification_faults(self) -> None:
    source = _read(STATISTICS_VIEWS_PATH)
    details_source = source.split(
        "class FaultStatisticsDetailsAPI", 1
    )[1].split("class FaultRepeatsAPI", 1)[0]

    exclusion_index = details_source.index("if impact_level or fault_group:")
    impact_filter_index = details_source.index("if impact_level:")
    self.assertLess(exclusion_index, impact_filter_index)
    self.assertIn(
        "queryset = _exclude_planned_rectification_faults(queryset)",
        details_source[exclusion_index:impact_filter_index],
    )
```

- [ ] **Step 3: 运行新增测试并确认失败原因正确**

Run: `python -m unittest tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_impact_level_period_queries_exclude_planned_rectification_faults tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_impact_level_and_ring_details_exclude_planned_rectification_faults`

Expected: `FAIL` 或 `ERROR`，原因是三个影响等级入口尚未应用统一排除函数。

### Task 2: 接入统一排除函数

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`

- [ ] **Step 1: 修改对比周期注解查询**

```python
annotated_qs = _annotate_class_i_business_impact(
    _exclude_planned_rectification_faults(filtered_qs)
)
```

- [ ] **Step 2: 修改当前周期注解查询**

```python
annotated_current_qs = _annotate_class_i_business_impact(
    _exclude_planned_rectification_faults(filtered_current_qs)
)
```

- [ ] **Step 3: 修改影响等级与环形图下钻查询**

在 `apply_detail_filters()` 中、`if impact_level:` 之前增加：

```python
if impact_level or fault_group:
    queryset = _exclude_planned_rectification_faults(queryset)
```

- [ ] **Step 4: 运行新增测试并确认通过**

Run: `python -m unittest tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_impact_level_period_queries_exclude_planned_rectification_faults tests.test_statistics_impact_level.StatisticsImpactLevelTestCase.test_impact_level_and_ring_details_exclude_planned_rectification_faults`

Expected: `OK`。

### Task 3: 回归验证与收尾

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 运行相关统计测试**

Run: `python -m unittest tests.test_statistics_impact_level tests.test_statistics_cable_break_overview`

Expected: `OK`。

- [ ] **Step 2: 运行 Python 编译检查**

Run: `python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_impact_level.py tests/test_statistics_cable_break_overview.py`

Expected: exit code 0，无输出。

- [ ] **Step 3: 检查差异**

Run: `git diff --check`

Expected: exit code 0，无空白错误。

- [ ] **Step 4: 更新 `PLAN.md` 本任务为完成**

将三项标记为 `[x]`。不暂存、不提交、不推送。
