# 子公司统计增加北京京宽排除项 Implementation Plan

> **For agentic workers:** 在当前工作区按 TDD 逐项执行；遵循项目约定，不创建 worktree，不暂存或提交。

**Goal:** 将“北京京宽网络科技有限公司”加入子公司统计统一排除名单。

**Architecture:** 保持现有 `EXCLUDED_HANDLING_UNITS` 精确名称集合与 `_is_branch_company_fault()` 调用链不变，只扩展一个集合成员。通过现有源码级回归测试锁定名单，确保汇总、绩效和明细共享相同规则。

**Tech Stack:** Python、Django/NetBox 插件、unittest

---

### Task 1: 扩展排除名单

**Files:**
- Modify: `tests/test_statistics_branch_company.py:382`
- Modify: `netbox_otnfaults/statistics_views.py:208`

- [x] **Step 1: 写入失败测试**

在 `test_backend_filters_out_specific_maintenance_companies_in_branch_statistics` 中增加：

```python
self.assertIn("'北京京宽网络科技有限公司'", source)
```

- [x] **Step 2: 验证测试按预期失败**

Run: `python -m unittest tests.test_statistics_branch_company.StatisticsBranchCompanyTestCase.test_backend_filters_out_specific_maintenance_companies_in_branch_statistics -v`

Expected: FAIL，提示源码中缺少 `北京京宽网络科技有限公司`。

- [x] **Step 3: 最小实现**

在 `EXCLUDED_HANDLING_UNITS` 中增加：

```python
'北京京宽网络科技有限公司',
```

- [x] **Step 4: 验证定向测试通过**

Run: `python -m unittest tests.test_statistics_branch_company.StatisticsBranchCompanyTestCase.test_backend_filters_out_specific_maintenance_companies_in_branch_statistics -v`

Expected: PASS。

- [x] **Step 5: 验证相关测试与语法**

Run: `python -m unittest tests.test_statistics_branch_company -q`

Expected: 全部 PASS。

Run: `python -m py_compile netbox_otnfaults/statistics_views.py tests/test_statistics_branch_company.py`

Expected: exit code 0。
