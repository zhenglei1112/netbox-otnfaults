# 裸纤业务中断故障明细下钻 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development task-by-task and superpowers:verification-before-completion before reporting success. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 点击“裸纤业务中断情况”四张卡片时，下方明细返回当前周期内导致裸纤业务中断的去重故障列表。

**Architecture:** 提取有效 `OtnFaultImpact` 共用筛选函数，让概览统计和明细 API 共享口径。前端为四张卡片统一设置 `bare_fiber_interruption=true`；物理故障页记录明细范围，子公司页叠加现有 `scope=branch_company`。

**Tech Stack:** Python、Django 5、NetBox 4、原生 JavaScript、unittest。

---

### Task 1: 添加失败回归测试

**Files:**
- Modify: `tests/test_statistics_bare_fiber_interruption.py`
- Modify: `tests/test_statistics_branch_company.py`

- [ ] **Step 1: 测试共享后端口径**

增加源码边界断言：

```python
def test_fault_details_reuse_bare_fiber_interruption_scope(self) -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")
    helper_source = source.split(
        "def _get_filtered_bare_fiber_interruption_impacts(", 1
    )[1].split("\n\n\ndef _compute_bare_fiber_interruption_overview", 1)[0]
    details_source = source.split("class FaultStatisticsDetailsAPI", 1)[1].split(
        "\n\nclass FaultStatisticsServiceDetailsAPI", 1
    )[0]
    self.assertIn("service_interruption_time__gte=start_date", helper_source)
    self.assertIn("BusinessImpactChoices.NOT_INTERRUPTED", helper_source)
    self.assertIn("if bare_fiber_interruption != 'true':", details_source)
    self.assertIn("_get_filtered_bare_fiber_interruption_impacts(", details_source)
    self.assertIn("queryset.filter(pk__in=bare_fiber_fault_ids)", details_source)
```

- [ ] **Step 2: 测试四卡片下钻属性**

```python
def test_four_cards_configure_bare_fiber_fault_drilldown(self) -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    self.assertIn("const bareFiberMetricElements = [", source)
    self.assertIn("totalCountEl, distinctCountEl, totalDurationEl, distinctDurationEl", source)
    self.assertIn("metric.dataset.filterField = 'bare_fiber_interruption';", source)
    self.assertIn("metric.dataset.filterValue = 'true';", source)
    self.assertIn("metric.dataset.detailScope = 'bare_fiber_interruption';", source)
    self.assertIn("metric.dataset.filterLabel = '裸纤业务中断';", source)
```

- [ ] **Step 3: 测试子公司范围复用**

在子公司测试中断言明细调用包含：

```python
self.assertIn("branch_company_scope=scope == 'branch_company'", details_source)
```

- [ ] **Step 4: 验证 RED**

Run: `python -m unittest tests.test_statistics_bare_fiber_interruption tests.test_statistics_branch_company`

Expected: 新增断言因共享函数、接口范围和卡片属性尚不存在而失败。

### Task 2: 提取统计与明细共用筛选

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Test: `tests/test_statistics_bare_fiber_interruption.py`

- [ ] **Step 1: 新增带类型提示的筛选函数**

```python
def _get_filtered_bare_fiber_interruption_impacts(
    start_date: datetime,
    end_date: datetime,
    selected_provinces: list[str],
    branch_company_scope: bool = False,
) -> list[OtnFaultImpact]:
    impacts = OtnFaultImpact.objects.select_related(
        "otn_fault", "otn_fault__province"
    ).filter(
        service_interruption_time__gte=start_date,
        service_interruption_time__lt=end_date,
        service_type=ServiceTypeChoices.BARE_FIBER,
        otn_fault__is_suspended=False,
    ).exclude(
        otn_fault__fault_status=FaultStatusChoices.SUSPENDED,
    ).exclude(
        business_impact=BusinessImpactChoices.NOT_INTERRUPTED,
    )
    if selected_provinces:
        impacts = impacts.filter(otn_fault__province__name__in=selected_provinces)
    filtered_impacts: list[OtnFaultImpact] = []
    for impact in impacts:
        fault = impact.otn_fault
        if branch_company_scope and (
            _branch_province_for_fault(fault) not in BRANCH_PROVINCE_NAMES
            or _should_exclude_for_branch(fault)
        ):
            continue
        if (
            fault.interruption_reason == "cable_rectification"
            and fault.interruption_reason_detail == "planned_reporting"
            and impact.coordination_status == "approved"
        ):
            continue
        filtered_impacts.append(impact)
    return filtered_impacts
```

- [ ] **Step 2: 概览函数调用共享筛选**

```python
filtered_impacts = _get_filtered_bare_fiber_interruption_impacts(
    start_date=start_date,
    end_date=end_date,
    selected_provinces=selected_provinces,
    branch_company_scope=branch_company_scope,
)
```

保留现有四项聚合公式，删除重复筛选循环。

- [ ] **Step 3: 运行定向测试**

Run: `python -m unittest tests.test_statistics_bare_fiber_interruption`

Expected: 共享口径断言通过，尚未实现的接口和前端断言继续失败。

### Task 3: 扩展故障明细 API

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Test: `tests/test_statistics_bare_fiber_interruption.py`
- Test: `tests/test_statistics_branch_company.py`

- [ ] **Step 1: 提前解析新范围参数并调整时间过滤**

```python
bare_fiber_interruption = request.GET.get("bare_fiber_interruption")
scope = request.GET.get("scope")
qs = OtnFault.objects.select_related(...).prefetch_related("interruption_location")
if bare_fiber_interruption != "true":
    qs = qs.filter(
        fault_occurrence_time__gte=start_date,
        fault_occurrence_time__lt=end_date,
    )
```

- [ ] **Step 2: 按影响记录关联故障 ID 过滤**

在 `apply_detail_filters()` 开头加入：

```python
if bare_fiber_interruption == "true":
    filtered_impacts = _get_filtered_bare_fiber_interruption_impacts(
        start_date=start_date,
        end_date=end_date,
        selected_provinces=selected_provinces,
        branch_company_scope=scope == "branch_company",
    )
    bare_fiber_fault_ids = {
        impact.otn_fault_id
        for impact in filtered_impacts
        if impact.otn_fault_id is not None
    }
    queryset = queryset.filter(pk__in=bare_fiber_fault_ids)
```

保留现有排序、重复标记、子公司过滤和序列化。

- [ ] **Step 3: 验证后端 GREEN**

Run: `python -m unittest tests.test_statistics_bare_fiber_interruption tests.test_statistics_branch_company`

Expected: 后端新增断言通过，前端断言仍失败。

### Task 4: 配置四卡片交互和筛选提示

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Test: `tests/test_statistics_bare_fiber_interruption.py`

- [ ] **Step 1: 统一设置四张卡片属性**

在 `renderBareFiberInterruption()` 中加入：

```javascript
const bareFiberMetricElements = [
    totalCountEl, distinctCountEl, totalDurationEl, distinctDurationEl
];
bareFiberMetricElements.forEach(valueElement => {
    const metric = valueElement && valueElement.closest('.statistics-drill-metric');
    if (!metric) return;
    metric.dataset.filterField = 'bare_fiber_interruption';
    metric.dataset.filterValue = 'true';
    metric.dataset.detailScope = 'bare_fiber_interruption';
    metric.dataset.filterLabel = '裸纤业务中断';
});
```

- [ ] **Step 2: 增加两个明细区域的筛选名称**

物理故障分支加入：

```javascript
else if (activeFilterField === 'bare_fiber_interruption') filterName = '业务影响';
```

子公司分支对 `activeBranchCompanyFilterField` 加入同等映射。

- [ ] **Step 3: 验证前端 GREEN**

Run: `python -m unittest tests.test_statistics_bare_fiber_interruption tests.test_statistics_branch_company`

Expected: 两个模块全部通过。

### Task 5: 完整验证与收尾

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 运行统计模块测试**

Run: `python -m unittest discover -s tests -p "test_statistics_*.py"`

Expected: 0 failures，0 errors。

- [ ] **Step 2: 编译与语法检查**

Run: `python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_bare_fiber_interruption.py tests/test_statistics_branch_company.py`

Expected: 退出码 0。

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

Expected: 退出码 0。

- [ ] **Step 3: 差异检查**

Run: `git diff --check`

Expected: 无空白错误。

Run: `git status --short`

Expected: 仅显示本需求文件和用户已有改动，不暂存、不提交。

- [ ] **Step 4: 更新项目计划**

全部验证成功后，把 `PLAN.md` 中本需求五项改为 `[x]`。
