# 故障列表“造成裸纤业务中断”筛选 Implementation Plan

> **For agentic workers:** 按本计划在当前工作区逐项执行；使用测试驱动开发，未经用户明确要求不创建分支、worktree 或 Git 提交。

**Goal:** 在故障列表筛选页面增加“造成裸纤业务中断”布尔选项，可筛选直接关联裸纤业务中断影响记录存在或不存在的故障。

**Architecture:** `OtnFaultFilterSet` 使用相关影响记录的 `Exists` 子查询判断数量是否大于 0，避免依赖列表视图注解并确保正反向筛选口径一致。`OtnFaultFilterForm` 使用可空布尔下拉框，并通过 `FieldSet` 顺序控制其位于故障起始时间和处理派发时间之间。

**Tech Stack:** Python 3、Django 5、django-filter、NetBox 4、pytest/unittest

---

### Task 1: 失败回归测试

**Files:**
- Create: `tests/test_otnfault_bare_fiber_interruption_filter.py`
- Inspect: `netbox_otnfaults/filtersets.py`
- Inspect: `netbox_otnfaults/forms.py`

- [ ] **Step 1: 编写筛选定义与查询口径测试**

新增源码结构回归测试，断言 FilterSet 定义 `caused_bare_fiber_interruption = django_filters.BooleanFilter(...)`，筛选方法同时使用 `ServiceTypeChoices.BARE_FIBER`、`BusinessImpactChoices.INTERRUPTED` 和 `Exists`，并分别处理 `True`、`False`、`None`。

- [ ] **Step 2: 编写表单标签与位置测试**

断言 `OtnFaultFilterForm` 定义标签“造成裸纤业务中断”，并且 `fieldsets` 内字段顺序满足 `fault_occurrence_time_before < caused_bare_fiber_interruption < dispatch_time`。

- [ ] **Step 3: 运行测试并确认按预期失败**

Run: `python -m pytest tests/test_otnfault_bare_fiber_interruption_filter.py -v`

Expected: FAIL，原因是 FilterSet 与表单尚未定义 `caused_bare_fiber_interruption`。

### Task 2: 最小实现

**Files:**
- Modify: `netbox_otnfaults/filtersets.py`
- Modify: `netbox_otnfaults/forms.py`
- Test: `tests/test_otnfault_bare_fiber_interruption_filter.py`

- [ ] **Step 1: 实现 FilterSet 字段与筛选方法**

从模型导入 `ServiceTypeChoices` 和 `BusinessImpactChoices`，定义布尔筛选字段。筛选方法构造关联子查询：

```python
matching_impacts = OtnFaultImpact.objects.filter(
    otn_fault_id=OuterRef('pk'),
    service_type=ServiceTypeChoices.BARE_FIBER,
    business_impact=BusinessImpactChoices.INTERRUPTED,
)
```

`value is None` 时返回原查询；`True` 时使用 `queryset.filter(Exists(matching_impacts))`；`False` 时使用 `queryset.filter(~Exists(matching_impacts))`。

- [ ] **Step 2: 实现表单字段并调整顺序**

在 `OtnFaultFilterForm` 增加可空布尔字段，标签为“造成裸纤业务中断”，控件选项为“--------- / 是 / 否”，并放在 `fault_occurrence_time_before` 之后、`dispatch_time` 之前。

- [ ] **Step 3: 运行定向测试并确认通过**

Run: `python -m pytest tests/test_otnfault_bare_fiber_interruption_filter.py -v`

Expected: PASS。

### Task 3: 回归与静态验证

**Files:**
- Verify: `netbox_otnfaults/filtersets.py`
- Verify: `netbox_otnfaults/forms.py`
- Verify: `tests/test_otnfault_bare_fiber_interruption_filter.py`

- [ ] **Step 1: 运行相邻筛选测试**

Run: `python -m pytest tests/test_otnfault_list_time_filters.py tests/test_otnfault_cutover_report_fields.py tests/test_otnfault_power_fault_fields.py tests/test_otnfault_bare_fiber_interruption_filter.py -v`

Expected: 全部 PASS。

- [ ] **Step 2: 运行 Python 编译检查**

Run: `python -m py_compile netbox_otnfaults/filtersets.py netbox_otnfaults/forms.py tests/test_otnfault_bare_fiber_interruption_filter.py`

Expected: exit code 0 且无语法错误。

- [ ] **Step 3: 检查最终差异和工作区状态**

Run: `git diff --check`

Expected: exit code 0，无空白错误；确认仅包含本功能相关修改及设计/计划文档。
