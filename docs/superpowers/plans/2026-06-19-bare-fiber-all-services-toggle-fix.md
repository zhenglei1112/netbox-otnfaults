# 裸纤业务“全部业务”切换修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复故障统计裸纤业务页“发生故障业务/全部业务”切换无效，同时保留默认只加载故障业务的性能优化。

**Architecture:** 复用现有业务统计聚合接口，通过 `include_all_bare_fiber=1` 显式请求全部裸纤业务。前端仅在用户选择“全部业务”时请求全量数据，并按统计参数缓存；默认请求和电路业务行为不变。

**Tech Stack:** Django 5、NetBox 4 插件、原生 JavaScript、Python unittest/pytest。

---

### Task 1: 锁定后端按需全量行为

**Files:**
- Modify: `tests/test_statistics_service_sorting.py`
- Modify: `tests/test_statistics_cable_break_overview.py`

- [ ] **Step 1: 写入失败测试**

在源码级测试中断言：

```python
assert "include_all_bare_fiber = request.GET.get('include_all_bare_fiber') == '1'" in source
assert "if include_all_bare_fiber:" in source
assert "for service in BareFiberService.objects.select_related('tenant_group').order_by('name'):" in source
```

同时检查该初始化循环位于 `if include_all_bare_fiber:` 分支中，且默认受影响业务聚合逻辑仍存在。

- [ ] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m pytest tests/test_statistics_service_sorting.py tests/test_statistics_cable_break_overview.py -q
```

Expected: FAIL，提示缺少 `include_all_bare_fiber` 参数解析或条件分支。

- [ ] **Step 3: 暂不修改生产代码**

确认失败原因是功能缺失，而不是测试路径、编码或语法错误。

### Task 2: 实现后端按需初始化全部裸纤业务

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py:2192-2344`

- [ ] **Step 1: 解析显式全量参数**

在 `ServiceStatisticsDataAPI.get()` 开头加入：

```python
include_all_bare_fiber: bool = request.GET.get('include_all_bare_fiber') == '1'
```

- [ ] **Step 2: 条件初始化全部裸纤业务**

在 `initialize_service_stats()` 定义后、遍历当前周期 impacts 前加入：

```python
if include_all_bare_fiber:
    for service in BareFiberService.objects.select_related('tenant_group').order_by('name'):
        svc_key = f'bf_{service.pk}'
        svc_group_label = service.tenant_group.name if service.tenant_group else '未分组'
        service_map[svc_key] = initialize_service_stats(
            service.name,
            '裸纤业务',
            svc_group_label,
            0,
        )
```

当前周期 impacts 继续覆盖或累加对应业务数据；电路业务不做全量初始化。

- [ ] **Step 3: 运行后端测试确认 GREEN**

Run:

```powershell
python -m pytest tests/test_statistics_service_sorting.py tests/test_statistics_cable_break_overview.py -q
```

Expected: PASS。

### Task 3: 锁定前端按需请求与缓存行为

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`

- [ ] **Step 1: 写入失败测试**

在裸纤范围切换测试中加入以下行为断言：

```python
self.assertIn("let bareFiberAllServicesLoaded = false;", source)
self.assertIn("if (includeAllBareFiber) url += '&include_all_bare_fiber=1';", source)
self.assertIn("bareFiberAllServicesLoaded = includeAllBareFiber;", source)
self.assertIn("loadServiceData({ includeAllBareFiber: true });", source)
self.assertIn("if (bareFiberAllServicesLoaded)", source)
```

并锁定统计参数变化时，全量加载状态会由下一次接口结果重新确定。

- [ ] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m pytest tests/test_statistics_cable_break_overview.py::StatisticsCableBreakOverviewTestCase::test_bare_fiber_service_tab_exposes_card_scope_toggle -q
```

Expected: FAIL，提示缺少全量加载状态和带参数请求。

### Task 4: 实现前端按需请求和本地切换

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:3490-3535`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js:4211-4217`

- [ ] **Step 1: 增加全量加载状态**

在业务统计状态中加入：

```javascript
let bareFiberAllServicesLoaded = false;
```

- [ ] **Step 2: 扩展聚合加载函数**

将加载函数改为接受选项：

```javascript
async function loadServiceData({ includeAllBareFiber = bareFiberServiceCardScope === 'all' } = {}) {
    // ...
    if (includeAllBareFiber) url += '&include_all_bare_fiber=1';
    // 成功应用响应后：
    bareFiberAllServicesLoaded = includeAllBareFiber;
}
```

只有请求成功并应用数据后才更新 `bareFiberAllServicesLoaded`。

- [ ] **Step 3: 修改范围切换事件**

切换到“全部业务”时：

```javascript
if (bareFiberServiceCardScope === 'all' && !bareFiberAllServicesLoaded) {
    loadServiceData({ includeAllBareFiber: true });
    return;
}
renderBareFiberServiceCards();
```

切回“发生故障业务”时直接使用全量缓存过滤，不重复请求。

- [ ] **Step 4: 运行前端回归测试确认 GREEN**

Run:

```powershell
python -m pytest tests/test_statistics_cable_break_overview.py::StatisticsCableBreakOverviewTestCase::test_bare_fiber_service_tab_exposes_card_scope_toggle -q
```

Expected: PASS。

### Task 5: 更新项目计划并完成验证

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 更新项目计划**

在 `PLAN.md` 顶部增加本次修复条目，记录回归测试、后端显式全量参数、前端按需加载与验证结果。

- [ ] **Step 2: 运行定向测试**

Run:

```powershell
python -m pytest tests/test_statistics_service_sorting.py tests/test_statistics_cable_break_overview.py -q
```

Expected: PASS，0 failures。

- [ ] **Step 3: 运行语法检查**

Run:

```powershell
node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js
python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_service_sorting.py tests/test_statistics_cable_break_overview.py
```

Expected: 两条命令均退出码 0。

- [ ] **Step 4: 检查差异**

Run:

```powershell
git diff --check
git status --short
```

Expected: 无空白错误，仅包含本次计划内文件。
