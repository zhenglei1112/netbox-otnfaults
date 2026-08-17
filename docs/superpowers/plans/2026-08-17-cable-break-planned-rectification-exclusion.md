# 光缆中断计划整改故障排除 Implementation Plan

> **For agentic workers:** 按任务顺序在当前工作区执行；先验证测试失败，再实现最小修改。受项目 `AGENTS.md` 约束，不创建 worktree、分支或 Git 提交。

**Goal:** 从“光缆中断情况”的全部统计、明细和地图数据中排除一级原因为光缆整改且二级原因为计划报备的故障。

**Architecture:** 在 `statistics_views.py` 提取一个接受 `QuerySet` 并返回排除后 `QuerySet` 的统一 ORM 函数。光缆中断基础查询、物理每日图查询和下钻明细作用域统一调用该函数；其余指标、分公司统计和地图继续复用基础查询。

**Tech Stack:** Python 3、Django ORM、`unittest` 源码级回归测试。

---

### Task 1: 用回归测试锁定统一排除口径

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`

- [ ] **Step 1: 写入失败测试**

在 `StatisticsCableBreakOverviewTestCase` 中增加：

```python
def test_cable_break_scope_excludes_only_planned_rectification_faults(self) -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")
    helper_source = source.split(
        "def _exclude_planned_rectification_faults", 1
    )[1].split("def get_cable_break_base_queryset", 1)[0]
    base_source = source.split(
        "def get_cable_break_base_queryset", 1
    )[1].split("def _occurrence_period_for_fault", 1)[0]
    details_source = source.split(
        "class FaultStatisticsDetailsAPI", 1
    )[1].split("class FaultRepeatsAPI", 1)[0]
    physical_daily_source = source.split(
        "physical_daily_faults = list(", 1
    )[1].split("physical_daily_stats =", 1)[0]

    self.assertIn("interruption_reason='cable_rectification'", helper_source)
    self.assertIn("interruption_reason_detail='planned_reporting'", helper_source)
    self.assertIn("return queryset.exclude(", helper_source)
    self.assertIn("_exclude_planned_rectification_faults(", base_source)
    self.assertIn("_exclude_planned_rectification_faults(", details_source)
    self.assertIn("_exclude_planned_rectification_faults(", physical_daily_source)
    self.assertGreaterEqual(source.count("_exclude_planned_rectification_faults("), 5)
```

该测试通过同一个 `.exclude()` 调用中的两个字段锁定 AND 组合语义，并要求定义位置、基础查询、重复中断历史、物理每日图及明细共至少五处出现函数名（一次定义、四处调用）。

- [ ] **Step 2: 运行测试并确认因缺少统一函数而失败**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_cable_break_scope_excludes_only_planned_rectification_faults`

Expected: `FAIL` 或 `ERROR`，原因是源码中尚无 `def _exclude_planned_rectification_faults`。

### Task 2: 实现统一 ORM 排除规则

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`

- [ ] **Step 1: 在光缆中断基础查询前增加统一函数**

```python
def _exclude_planned_rectification_faults(queryset: QuerySet) -> QuerySet:
    """Exclude cable-break faults recorded as planned rectification work."""
    return queryset.exclude(
        interruption_reason='cable_rectification',
        interruption_reason_detail='planned_reporting',
    )
```

- [ ] **Step 2: 让基础查询应用统一函数**

将 `get_cable_break_base_queryset()` 的返回表达式包装为：

```python
return _exclude_planned_rectification_faults(
    OtnFault.objects.select_related(
        'province', 'interruption_location_a', 'handling_unit'
    )
    .prefetch_related('interruption_location')
    .filter(
        fault_occurrence_time__gte=start_date,
        fault_occurrence_time__lt=end_date,
        fault_category=FaultCategoryChoices.FIBER_BREAK,
    )
    .filter(is_suspended=False)
    .exclude(fault_status=FaultStatusChoices.SUSPENDED)
)
```

- [ ] **Step 3: 让物理每日图查询应用统一函数**

在 `_apply_physical_province_filter()` 前，将现有光缆中断查询集包装为：

```python
_exclude_planned_rectification_faults(
    qs_all.filter(
        fault_occurrence_time__gte=physical_daily_start,
        fault_occurrence_time__lt=physical_daily_end,
        fault_category=FaultCategoryChoices.FIBER_BREAK,
    ).filter(
        is_suspended=False,
    ).exclude(
        fault_status=FaultStatusChoices.SUSPENDED
    )
)
```

- [ ] **Step 4: 让下钻明细光缆中断作用域应用统一函数**

在 `apply_cable_break_scope()` 的 `detail_scope == 'cable_break'` 分支中，保留类型和非挂起过滤后增加：

```python
queryset = _exclude_planned_rectification_faults(queryset)
```

- [ ] **Step 5: 让重复中断历史参照查询应用统一函数**

将前 60 天 `p_past_qs` 查询包装为：

```python
p_past_qs = _exclude_planned_rectification_faults(
    OtnFault.objects.filter(
        fault_occurrence_time__gte=p_check_start,
        fault_occurrence_time__lt=end_date,
        fault_category__in=[
            FaultCategoryChoices.FIBER_BREAK,
            FaultCategoryChoices.FIBER_DEGRADATION,
            FaultCategoryChoices.FIBER_JITTER,
        ],
    )
    .select_related('interruption_location_a')
    .prefetch_related('interruption_location')
)
```

- [ ] **Step 6: 运行新增测试并确认通过**

Run: `python -m unittest tests.test_statistics_cable_break_overview.StatisticsCableBreakOverviewTestCase.test_cable_break_scope_excludes_only_planned_rectification_faults`

Expected: `OK`。

### Task 3: 回归验证与收尾

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 运行光缆中断统计测试**

Run: `python -m unittest tests.test_statistics_cable_break_overview`

Expected: `OK`，允许仓库中既有的显式跳过用例。

- [ ] **Step 2: 运行 Python 编译检查**

Run: `python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_cable_break_overview.py`

Expected: exit code 0，无输出。

- [ ] **Step 3: 检查修改范围**

Run: `git diff --check`，然后运行 `git diff -- netbox_otnfaults/statistics_views.py tests/test_statistics_cable_break_overview.py PLAN.md docs/superpowers/specs/2026-08-17-cable-break-planned-rectification-exclusion-design.md docs/superpowers/plans/2026-08-17-cable-break-planned-rectification-exclusion.md`

Expected: 无空白错误；差异只包含本次统计口径、测试和文档修改。

- [ ] **Step 4: 更新项目计划状态**

将 `PLAN.md` 本任务三项全部标记为 `[x]`。不暂存、不提交、不推送。
