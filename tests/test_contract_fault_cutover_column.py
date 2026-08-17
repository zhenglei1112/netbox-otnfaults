import ast
from pathlib import Path
from types import SimpleNamespace


TABLES_PATH = Path(__file__).resolve().parents[1] / "netbox_otnfaults" / "tables.py"


def _tables_source() -> str:
    return TABLES_PATH.read_text(encoding="utf-8")


def _tables_tree() -> ast.Module:
    return ast.parse(_tables_source())


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
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    )
    return ast.literal_eval(assignment.value)


def _function_node(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _planned_cutover_predicate():
    function = _function_node(_tables_tree(), "_is_planned_cutover")
    namespace: dict[str, object] = {}
    exec(
        compile(
            ast.Module(body=[function], type_ignores=[]),
            str(TABLES_PATH),
            "exec",
        ),
        namespace,
    )
    return namespace["_is_planned_cutover"]


def _cutover_renderer():
    tree = _tables_tree()
    table = _class_node(tree, "ContractOtnFaultTable")
    method = next(
        node
        for node in table.body
        if isinstance(node, ast.FunctionDef) and node.name == "render_cutover"
    )
    predicate = _planned_cutover_predicate()
    def django_6_format_html(format_string, *args, **kwargs):
        if not args and not kwargs:
            raise TypeError("args or kwargs must be provided.")
        return format_string.format(*args, **kwargs)

    namespace = {
        "OtnFault": object,
        "_is_planned_cutover": predicate,
        "format_html": django_6_format_html,
    }
    exec(
        compile(
            ast.Module(body=[method], type_ignores=[]),
            str(TABLES_PATH),
            "exec",
        ),
        namespace,
    )
    return namespace["render_cutover"]


def _fault(primary: str | None, secondary: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        interruption_reason=primary,
        interruption_reason_detail=secondary,
    )


def test_planned_cutover_requires_both_matching_reasons():
    predicate = _planned_cutover_predicate()

    assert predicate(_fault("cable_rectification", "planned_reporting"))
    assert not predicate(_fault("cable_rectification", "unplanned_reporting"))
    assert not predicate(_fault("construction", "planned_reporting"))
    assert not predicate(_fault(None, None))


def test_cutover_renderer_shows_only_matching_fault_as_green_check():
    render_cutover = _cutover_renderer()

    matching = render_cutover(None, _fault("cable_rectification", "planned_reporting"))
    assert 'class="mdi mdi-check-bold text-success"' in matching
    assert 'aria-label="割接"' in matching
    assert render_cutover(None, _fault("cable_rectification", "unplanned_reporting")) == ""
    assert render_cutover(None, _fault("construction", "planned_reporting")) == ""


def _assigned_call(table: ast.ClassDef, name: str) -> ast.Call:
    assignment = next(
        node
        for node in table.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    )
    assert isinstance(assignment.value, ast.Call)
    return assignment.value


def _call_name(call: ast.Call) -> str:
    assert isinstance(call.func, ast.Attribute)
    assert isinstance(call.func.value, ast.Name)
    return f"{call.func.value.id}.{call.func.attr}"


def _call_keywords(call: ast.Call) -> dict[str, object]:
    return {
        keyword.arg: ast.literal_eval(keyword.value)
        for keyword in call.keywords
    }


def test_contract_fault_table_uses_confirmed_column_order():
    tree = _tables_tree()
    table = _class_node(tree, "ContractOtnFaultTable")
    fields = _meta_tuple(table, "fields")
    default_columns = _meta_tuple(table, "default_columns")
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


def test_contract_fault_table_excludes_inherited_id_column():
    table = _class_node(_tables_tree(), "ContractOtnFaultTable")

    assert _meta_tuple(table, "exclude") == ("id",)


def test_contract_fault_table_uses_linked_endpoint_columns():
    table = _class_node(_tables_tree(), "ContractOtnFaultTable")
    endpoint_a = _assigned_call(table, "interruption_location_a")
    endpoint_z = _assigned_call(table, "interruption_location")

    assert _call_name(endpoint_a) == "tables.Column"
    assert _call_keywords(endpoint_a) == {
        "linkify": True,
        "verbose_name": "故障位置A端站点",
    }
    assert _call_name(endpoint_z) == "columns.ManyToManyColumn"
    assert _call_keywords(endpoint_z) == {
        "linkify_item": True,
        "verbose_name": "故障位置Z端站点",
    }


def test_contract_fault_cutover_column_is_non_orderable():
    cutover = _assigned_call(
        _class_node(_tables_tree(), "ContractOtnFaultTable"),
        "cutover",
    )

    assert _call_keywords(cutover) == {
        "verbose_name": "割接",
        "orderable": False,
        "empty_values": (),
    }


def test_site_history_table_keeps_its_progress_column():
    table = _class_node(_tables_tree(), "SiteHistoryFaultTable")
    progress = _assigned_call(table, "progress")

    assert _call_name(progress) == "tables.Column"
    assert _call_keywords(progress) == {
        "verbose_name": "处理进度",
        "orderable": False,
        "empty_values": (),
    }
