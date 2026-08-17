# 外购合同关联故障列布局 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按确认顺序精简外购合同关联故障列表，移除 ID 与处理进度，并增加 A/Z 端站点链接列。

**Architecture:** 仅调整 `ContractOtnFaultTable` 的列声明和元数据顺序，并在关联故障查询中预加载两个站点关系。模型、数据库和通用故障列表保持不变。

**Tech Stack:** Python 3.10+、django-tables2、NetBox `NetBoxTable`、pytest、Python AST

---

## 文件结构

- 修改 `netbox_otnfaults/tables.py`：声明 A/Z 端站点列并设置最终字段顺序。
- 修改 `netbox_otnfaults/template_content.py`：预加载 A/Z 端站点关系。
- 修改 `tests/test_contract_fault_cutover_column.py`：验证最终列集合、顺序和链接列类型。
- 修改 `tests/test_contract_fault_payment_filter.py`：验证关联故障查询预加载站点。

### Task 1: 用失败测试锁定最终列布局

**Files:**
- Modify: `tests/test_contract_fault_cutover_column.py`
- Modify: `tests/test_contract_fault_payment_filter.py`

- [ ] **Step 1: 将表格测试改为精确验证最终字段顺序**

```python
expected_columns = (
    "fault_number",
    "duty_officer",
    "fault_occurrence_time",
    "fault_duration",
    "fault_category",
    "cutover",
    "interruption_location_a",
    "interruption_location",
    "urgency",
    "fault_status",
    "tags",
)
assert fields == expected_columns
assert default_columns == expected_columns
```

解析 `interruption_location_a` 与 `interruption_location` 的赋值，验证前者调用 `tables.Column(linkify=True, verbose_name='故障位置A端站点')`，后者调用 `columns.ManyToManyColumn(linkify_item=True, verbose_name='故障位置Z端站点')`。

- [ ] **Step 2: 更新查询测试以要求站点预加载**

```python
assert ".select_related('duty_officer', 'interruption_location_a')" in source
assert ".prefetch_related('interruption_location', 'tags')" in source
```

- [ ] **Step 3: 运行测试并确认因旧布局失败**

Run: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -p no:cacheprovider tests/test_contract_fault_cutover_column.py tests/test_contract_fault_payment_filter.py -q`

Expected: FAIL，差异包含旧字段 `pk`、`progress`，并缺少两个站点列及预加载。

### Task 2: 实现最终列布局和查询预加载

**Files:**
- Modify: `netbox_otnfaults/tables.py:520-580`
- Modify: `netbox_otnfaults/template_content.py:65-80`

- [ ] **Step 1: 在关联故障表中声明站点链接列**

```python
interruption_location_a = tables.Column(
    linkify=True,
    verbose_name='故障位置A端站点',
)
interruption_location = columns.ManyToManyColumn(
    linkify_item=True,
    verbose_name='故障位置Z端站点',
)
```

- [ ] **Step 2: 将 `fields` 与 `default_columns` 统一为最终顺序**

```python
(
    'fault_number', 'duty_officer', 'fault_occurrence_time',
    'fault_duration', 'fault_category', 'cutover',
    'interruption_location_a', 'interruption_location',
    'urgency', 'fault_status', 'tags',
)
```

该元组不包含 `pk`、`progress`、`is_suspended`；后者本就不是默认显示列，也从此精简表的可配置列中一并移除，以保证可用列与用户确认的最终列完全一致。

- [ ] **Step 3: 为关联故障查询预加载站点**

```python
.select_related('duty_officer', 'interruption_location_a')
.prefetch_related('interruption_location', 'tags')
```

- [ ] **Step 4: 运行目标测试并确认通过**

Run: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -p no:cacheprovider tests/test_contract_fault_cutover_column.py tests/test_contract_fault_payment_filter.py -q`

Expected: 全部通过。

### Task 3: 回归与静态验证

**Files:**
- Test: `tests/test_contract_fault_cutover_column.py`
- Test: `tests/test_contract_fault_tag_column.py`
- Test: `tests/test_contract_fault_payment_filter.py`

- [ ] **Step 1: 运行关联故障回归测试**

Run: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -p no:cacheprovider tests/test_contract_fault_cutover_column.py tests/test_contract_fault_tag_column.py tests/test_contract_fault_payment_filter.py -q`

Expected: 全部通过。

- [ ] **Step 2: 运行 Ruff 与 diff 检查**

Run: `python -m ruff check --no-cache --ignore F401 netbox_otnfaults/tables.py netbox_otnfaults/template_content.py tests/test_contract_fault_cutover_column.py tests/test_contract_fault_payment_filter.py`

Expected: `All checks passed!`。

Run: `git diff --check`

Expected: 无空白错误。按仓库约定不暂存、不提交、不推送。
