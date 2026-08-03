# 故障明细显示裸纤业务中断数量 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development task-by-task and superpowers:verification-before-completion before reporting success. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在物理故障和子公司故障明细中显示每条故障实际中断的去重裸纤业务数量，数量为 0 时显示 `-`。

**Architecture:** 使用独立查询注解函数为 `OtnFault` 添加带条件的去重 `Count`，并复用于当前故障和历史重复故障查询。API 返回统一字段，前端共享格式化函数在两种故障行中渲染；只调整物理故障和子公司表格列数。

**Tech Stack:** Python、Django ORM、NetBox 4、原生 JavaScript、Django 模板、unittest 源码回归测试。

---

### Task 1: 增加失败回归测试

**Files:**
- Create: `tests/test_statistics_fault_detail_bare_fiber_impact_count.py`

- [ ] **Step 1: 锁定后端条件聚合和两个结果分支**

```python
def test_backend_annotates_interrupted_distinct_bare_fiber_services(self) -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")
    helper_source = source.split(
        "def _annotate_bare_fiber_impact_count(", 1
    )[1].split("\n\n\ndef _get_impact_level_display", 1)[0]
    details_source = source.split("class FaultStatisticsDetailsAPI", 1)[1].split(
        "\n\nclass FaultStatisticsServiceDetailsAPI", 1
    )[0]
    self.assertIn("Count(", helper_source)
    self.assertIn("'impacts__bare_fiber_service'", helper_source)
    self.assertIn("impacts__service_type=ServiceTypeChoices.BARE_FIBER", helper_source)
    self.assertIn("impacts__business_impact=BusinessImpactChoices.INTERRUPTED", helper_source)
    self.assertIn("distinct=True", helper_source)
    self.assertGreaterEqual(details_source.count("'bare_fiber_impact_count':"), 2)
```

- [ ] **Step 2: 锁定表头、列位置和物理表列数**

```python
def test_physical_detail_tables_include_bare_fiber_impact_column(self) -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    self.assertEqual(template.count("<th>裸纤业务中断</th>"), 2)
    self.assertEqual(template.count('colspan="12"'), 2)
    self.assertRegex(
        template,
        r"<th>站点 \(A -> Z\)</th>\s*<th>裸纤业务中断</th>\s*<th>标签</th>",
    )
```

- [ ] **Step 3: 锁定前端 0 显示横线并覆盖两种行**

```python
def test_frontend_formats_bare_fiber_impact_count(self) -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    self.assertIn("function formatBareFiberImpactCount(value)", source)
    self.assertIn("return count > 0 ? String(count) : '-';", source)
    self.assertGreaterEqual(
        source.count("formatBareFiberImpactCount(item.bare_fiber_impact_count)"), 2
    )
```

- [ ] **Step 4: 运行测试并验证 RED**

Run: `python -m unittest tests.test_statistics_fault_detail_bare_fiber_impact_count`

Expected: 3 个测试因注解函数、返回字段、表头和渲染函数不存在而失败。

### Task 2: 实现后端聚合与字段返回

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`
- Test: `tests/test_statistics_fault_detail_bare_fiber_impact_count.py`

- [ ] **Step 1: 增加复用注解函数**

```python
def _annotate_bare_fiber_impact_count(queryset: QuerySet) -> QuerySet:
    return queryset.annotate(
        bare_fiber_impact_count=Count(
            'impacts__bare_fiber_service',
            filter=Q(
                impacts__service_type=ServiceTypeChoices.BARE_FIBER,
                impacts__business_impact=BusinessImpactChoices.INTERRUPTED,
                impacts__bare_fiber_service__isnull=False,
            ),
            distinct=True,
        )
    )
```

- [ ] **Step 2: 注解当前和历史故障查询**

在 `FaultStatisticsDetailsAPI` 的基础 `qs` 和 `preceding_qs` 上调用：

```python
qs = _annotate_bare_fiber_impact_count(qs)
preceding_qs = _annotate_bare_fiber_impact_count(preceding_qs)
```

- [ ] **Step 3: 在两个结果序列化分支返回整数**

```python
'bare_fiber_impact_count': int(
    getattr(fault, 'bare_fiber_impact_count', 0) or 0
),
```

- [ ] **Step 4: 运行测试确认后端断言通过**

Run: `python -m unittest tests.test_statistics_fault_detail_bare_fiber_impact_count`

Expected: 后端测试通过，模板和前端测试仍失败。

### Task 3: 实现两张表的列和渲染

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Test: `tests/test_statistics_fault_detail_bare_fiber_impact_count.py`

- [ ] **Step 1: 增加两个表头并调整模板加载列数**

在物理故障和子公司故障表中，把：

```html
<th>站点 (A -> Z)</th>
<th>标签</th>
```

改为：

```html
<th>站点 (A -> Z)</th>
<th>裸纤业务中断</th>
<th>标签</th>
```

两张表加载行的 `colspan` 从 `11` 攽为 `12`，业务故障表保持原值。

- [ ] **Step 2: 增加共享显示格式化函数**

```javascript
function formatBareFiberImpactCount(value) {
    const count = Number(value || 0);
    return count > 0 ? String(count) : '-';
}
```

- [ ] **Step 3: 在当前故障和历史故障行中增加单元格**

在站点列和标签列之间加入：

```javascript
<td>${formatBareFiberImpactCount(item.bare_fiber_impact_count)}</td>
```

同时把物理故障和子公司故障的加载、失败、空结果行 `colspan` 调整为 `12`，不修改业务明细的 11/8 列逻辑。

- [ ] **Step 4: 运行定向测试确认 GREEN**

Run: `python -m unittest tests.test_statistics_fault_detail_bare_fiber_impact_count`

Expected: 3 个测试全部通过。

### Task 4: 完整验证与收尾

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 运行全部统计测试**

Run: `python -m unittest discover -s tests -p "test_statistics_*.py"`

Expected: 0 failures，0 errors。

- [ ] **Step 2: 编译和语法检查**

Run: `python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_fault_detail_bare_fiber_impact_count.py`

Expected: 退出码 0。

Run: `node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

Expected: 退出码 0。

- [ ] **Step 3: 差异、索引和范围检查**

Run: `git diff --check`

Expected: 无空白错误。

Run: `git diff --cached --quiet`

Expected: 退出码 0，索引为空。

- [ ] **Step 4: 更新计划完成状态并代码审查**

全部验证通过后更新 `PLAN.md`，并检查 Count 聚合、历史行字段、两张物理表列数以及业务表未受影响。
