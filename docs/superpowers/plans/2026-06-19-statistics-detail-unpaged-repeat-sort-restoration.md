# 故障统计明细取消分页与重复排序恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取消故障统计四张明细表分页，并恢复物理故障与子公司明细基于完整数据集的重复故障排序。

**Architecture:** 保留独立明细 API 和服务端筛选，但接口返回全部匹配结果。前端缓存物理及子公司完整明细，在本地执行时间/重复排序；业务明细直接渲染全量响应。

**Tech Stack:** Django 5、NetBox 4 插件、原生 JavaScript、Python unittest。

---

### Task 1: 锁定分页 UI 和分页状态移除

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `tests/test_statistics_branch_company.py`

- [ ] **Step 1: 写入失败测试**

增加断言，要求模板中不存在：

```python
for element_id in [
    "fault-pagination-list",
    "service-pagination-list",
    "circuit-pagination-list",
    "branch-pagination-list",
    "fault-per-page-dropdown",
    "service-per-page-dropdown",
    "circuit-per-page-dropdown",
    "branch-per-page-dropdown",
]:
    self.assertNotIn(f'id="{element_id}"', template)
```

前端源码中不存在 `renderPagination()` 和 `faultPage`、`branchPage`、`servicePage`、`circuitPage` 状态。

- [ ] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q
```

Expected: FAIL，指出分页 DOM 和分页状态仍存在。

### Task 2: 移除模板分页与前端分页框架

**Files:**
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`

- [ ] **Step 1: 删除四处分页 footer**

删除 `fault-*`、`service-*`、`circuit-*` 和 `branch-*` 的页码、显示信息及每页下拉控件。

- [ ] **Step 2: 删除分页状态与渲染器**

删除：

```javascript
let faultPage = 1;
let faultPerPage = 25;
let faultTotal = 0;
```

以及 branch/service/circuit 对应变量和 `renderPagination()`。

- [ ] **Step 3: 简化请求签名**

将请求 URL 中的：

```javascript
&page=${page}&per_page=${perPage}
```

移除。业务明细加载函数改为：

```javascript
async function loadServiceDetails(serviceType, ordering, tbodyId, badgeId, clearButtonId)
```

- [ ] **Step 4: 运行定向测试**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q
```

Expected: 分页移除相关断言 PASS。

### Task 3: 锁定后端全量响应

**Files:**
- Modify: `tests/test_statistics_cable_break_overview.py`

- [ ] **Step 1: 写入失败测试**

在 `FaultStatisticsDetailsAPI` 和 `ServiceStatisticsDetailsAPI` 源码块中断言：

```python
self.assertNotIn("page = int(request.GET.get('page', 1))", details_source)
self.assertNotIn("per_page = int(request.GET.get('per_page', 25))", details_source)
self.assertNotIn("page_faults = list(qs[start_index:end_index])", details_source)
self.assertNotIn("'pagination': {", details_source)
self.assertIn("current_faults = list(qs)", details_source)
```

业务明细接口对应断言 `page_impacts = list(impacts_qs)`。

- [ ] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview -q
```

Expected: FAIL，指出接口仍读取分页参数并切片。

### Task 4: 后端返回全量明细及关联历史重复故障

**Files:**
- Modify: `netbox_otnfaults/statistics_views.py`

- [ ] **Step 1: 移除分页切片**

故障明细改为：

```python
current_faults = list(qs)
```

业务明细改为：

```python
page_impacts = list(impacts_qs)
```

两个接口只返回 `{'results': results}`。

- [ ] **Step 2: 构建关联历史故障**

对于当前结果中的光缆故障，查询最早当前故障前 60 天至当前周期结束的候选故障，调用 `detect_repeat_faults()`。将 `matched_preceding_faults` 追加到响应并标记：

```python
'in_period': False
```

当前结果标记 `in_period=True`。

- [ ] **Step 3: 保持 scope 与筛选一致**

当 `scope=branch_company` 时，关联历史故障同样限制六省范围，并排除 `EXCLUDED_HANDLING_UNITS`。下钻省份筛选同样应用到历史候选。

- [ ] **Step 4: 运行后端源码测试**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q
```

Expected: PASS。

### Task 5: 恢复完整结果本地重复排序

**Files:**
- Modify: `netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js`
- Modify: `tests/test_statistics_cable_break_overview.py`
- Modify: `tests/test_statistics_branch_company.py`

- [ ] **Step 1: 写入失败测试**

锁定物理和子公司响应分别保存到：

```javascript
currentAllDetails = data.results || [];
currentBranchCompanyDetails = data.results || [];
```

锁定两个渲染函数调用：

```javascript
filteredDetails = sortDetailRows(filteredDetails, sortMode);
```

并要求 `loadFaultDetails()` / `loadBranchDetails()` 成功后调用对应本地渲染函数。

- [ ] **Step 2: 确认 RED**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q
```

- [ ] **Step 3: 恢复缓存和渲染**

`loadFaultDetails()` 保存完整结果后调用 `renderDetailsTable()`；`loadBranchDetails()` 保存完整结果后调用 `renderBranchCompanyDetailsTable()`。

两个渲染函数恢复本地：

```javascript
assignRepeatGroupColors(filteredDetails);
const sortMode = document.querySelector(...).value;
filteredDetails = sortDetailRows(filteredDetails, sortMode);
```

筛选结果局部统计使用最终完整结果计算。

- [ ] **Step 4: 修正重复组排序**

“按时间”对 `in_period !== false` 的记录按时间倒序；“按重复”将组内记录按时间倒序，组间按组内最新故障时间倒序。

- [ ] **Step 5: 运行测试**

Run:

```powershell
python -m unittest tests.test_statistics_cable_break_overview tests.test_statistics_branch_company -q
```

Expected: PASS。

### Task 6: 验证业务明细全量与既有回归

**Files:**
- Modify: `PLAN.md`

- [ ] **Step 1: 更新计划状态**

记录四处分页移除、重复排序恢复、业务明细全量加载和验证结果。

- [ ] **Step 2: 运行统计测试**

Run:

```powershell
python -m unittest tests.test_statistics_branch_company tests.test_statistics_cable_break_overview -q
```

Expected: 0 failures。

- [ ] **Step 3: 运行业务排序断言**

Run:

```powershell
@'
import runpy
ns = runpy.run_path('tests/test_statistics_service_sorting.py')
for name, value in ns.items():
    if name.startswith('test_') and callable(value):
        value()
        print(f'PASS {name}')
'@ | python -
```

Expected: 所有函数 PASS。

- [ ] **Step 4: 运行语法和差异检查**

Run:

```powershell
node --check netbox_otnfaults/static/netbox_otnfaults/js/statistics_dashboard.js
git diff --check
git status --short
```

Expected: 命令退出码 0，仅包含计划内文件。
