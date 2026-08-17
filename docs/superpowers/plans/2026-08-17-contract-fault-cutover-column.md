# 外购合同关联故障“割接”列 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在外购合同详情页的关联故障列表中，用单个“割接”列标识“光缆整改 + 计划报备”的故障。

**Architecture:** 将条件判断实现为 `tables.py` 中的纯函数，由 `ContractOtnFaultTable` 的无数据源展示列调用。列表查询、故障模型和数据库结构不变；测试通过执行纯判断函数并检查表格声明覆盖行为和列顺序。

**Tech Stack:** Python 3.10+、django-tables2、NetBox `NetBoxTable`、pytest、Python AST

---

## 文件结构

- 修改 `netbox_otnfaults/tables.py`：定义计划割接判断函数以及关联故障表的“割接”列和渲染方法。
- 新建 `tests/test_contract_fault_cutover_column.py`：验证判断逻辑、绿色对勾表现以及表格列配置。

### Task 1: 为计划割接判断与列配置编写失败测试

**Files:**
- Create: `tests/test_contract_fault_cutover_column.py`
- Test: `tests/test_contract_fault_cutover_column.py`

- [ ] **Step 1: 写入失败测试**

```python
import ast
from pathlib import Path
from types import SimpleNamespace


TABLES_PATH = Path(__file__).resolve().parents[1] / "netbox_otnfaults" / "tables.py"


def _tables_tree() -> ast.Module:
    return ast.parse(TABLES_PATH.read_text(encoding="utf-8"))


def _class_node(tree: ast.Module, name: str) -> ast.ClassDef:
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _meta_tuple(table: ast.ClassDef, name: str) -> tuple[str, ...]:
    meta = next(
        node
        for node in table.body
        if isinstance(node, ast.ClassDef) and node.name == "Meta"
    )
    assignment = next(
        node
        for node in meta.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def _planned_cutover_predicate():
    tree = _tables_tree()
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_is_planned_cutover"
    )
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(TABLES_PATH), "exec"), namespace)
    return namespace["_is_planned_cutover"]


def test_planned_cutover_requires_both_matching_reasons():
    predicate = _planned_cutover_predicate()

    assert predicate(SimpleNamespace(
        interruption_reason="cable_rectification",
        interruption_reason_detail="planned_reporting",
    ))
    assert not predicate(SimpleNamespace(
        interruption_reason="cable_rectification",
        interruption_reason_detail="unplanned_reporting",
    ))
    assert not predicate(SimpleNamespace(
        interruption_reason="construction",
        interruption_reason_detail="planned_reporting",
    ))


def test_contract_fault_table_exposes_cutover_after_category():
    tree = _tables_tree()
    table = _class_node(tree, "ContractOtnFaultTable")
    fields = _meta_tuple(table, "fields")
    default_columns = _meta_tuple(table, "default_columns")
    source = ast.get_source_segment(TABLES_PATH.read_text(encoding="utf-8"), table)

    assert fields.index("cutover") == fields.index("fault_category") + 1
    assert default_columns.index("cutover") == default_columns.index("fault_category") + 1
    assert "verbose_name='割接'" in source
    assert "orderable=False" in source
    assert "mdi-check-bold text-success" in source
    assert "return ''" in source
```

- [ ] **Step 2: 运行测试并确认因功能缺失而失败**

Run: `python -m pytest tests/test_contract_fault_cutover_column.py -q`

Expected: FAIL，错误指出找不到 `_is_planned_cutover`。

### Task 2: 实现“割接”计算列

**Files:**
- Modify: `netbox_otnfaults/tables.py:17`
- Modify: `netbox_otnfaults/tables.py:510-575`
- Test: `tests/test_contract_fault_cutover_column.py`

- [ ] **Step 1: 在通用显示辅助函数旁新增纯判断函数**

```python
def _is_planned_cutover(record: object) -> bool:
    return (
        getattr(record, 'interruption_reason', None) == 'cable_rectification'
        and getattr(record, 'interruption_reason_detail', None) == 'planned_reporting'
    )
```

- [ ] **Step 2: 在 `ContractOtnFaultTable` 中声明展示列**

将其放在 `fault_category` 后：

```python
    cutover = tables.Column(
        verbose_name='割接',
        orderable=False,
        empty_values=(),
    )
```

并将 `'cutover'` 同时放入 `Meta.fields` 与 `Meta.default_columns` 的 `'fault_category'` 后。

- [ ] **Step 3: 增加最小渲染实现**

```python
    def render_cutover(self, record: OtnFault):
        if not _is_planned_cutover(record):
            return ''
        return format_html(
            '<i class="mdi mdi-check-bold text-success" aria-label="割接"></i>'
        )
```

- [ ] **Step 4: 运行目标测试并确认通过**

Run: `python -m pytest tests/test_contract_fault_cutover_column.py -q`

Expected: `2 passed`。

### Task 3: 回归验证

**Files:**
- Test: `tests/test_contract_fault_cutover_column.py`
- Test: `tests/test_contract_fault_tag_column.py`
- Test: `tests/test_contract_fault_payment_filter.py`

- [ ] **Step 1: 运行关联故障列表相关测试**

Run: `python -m pytest tests/test_contract_fault_cutover_column.py tests/test_contract_fault_tag_column.py tests/test_contract_fault_payment_filter.py -q`

Expected: 全部通过，无错误或警告。

- [ ] **Step 2: 运行完整测试集**

Run: `python -m pytest -q`

Expected: 全部通过；若存在与本改动无关的既有失败，记录准确的失败测试和错误信息。

- [ ] **Step 3: 检查改动范围**

Run: `git diff --check && git status --short && git diff -- netbox_otnfaults/tables.py tests/test_contract_fault_cutover_column.py`

Expected: `git diff --check` 无输出；除设计、计划、目标测试和表格实现外没有本任务引入的文件。按仓库约定不暂存、不提交、不推送。
