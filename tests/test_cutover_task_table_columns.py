import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_FIELD_CALLS = {
    "ArrayField",
    "CharField",
    "DateTimeField",
    "DecimalField",
    "ForeignKey",
    "JSONField",
    "ManyToManyField",
    "PositiveIntegerField",
    "TaggableManager",
    "TextField",
}
EXPECTED_DEFAULT_COLUMNS = (
    "cutover_no",
    "status",
    "cutover_type",
    "planned_cutover_time",
    "province",
    "cutover_location",
    "management_unit",
    "implementation_unit",
    "cutover_contact",
    "cutover_result",
    "is_timeout",
    "line_supervisor",
)


def _class_node(path: str, class_name: str) -> ast.ClassDef:
    module = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )


def _call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute):
        return function.attr
    return ""


def _cutover_model_fields() -> set[str]:
    model = _class_node("netbox_otnfaults/models.py", "CutoverTask")
    fields: set[str] = set()
    for node in model.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and _call_name(node.value) in MODEL_FIELD_CALLS:
            fields.add(target.id)
    return fields


def _meta_tuple(class_node: ast.ClassDef, name: str) -> tuple[str, ...]:
    meta = next(
        node
        for node in class_node.body
        if isinstance(node, ast.ClassDef) and node.name == "Meta"
    )
    assignment = next(
        node
        for node in meta.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    assert isinstance(assignment.value, (ast.Tuple, ast.List))
    return tuple(
        element.value
        for element in assignment.value.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    )


class CutoverTaskTableColumnsTestCase(unittest.TestCase):
    def test_all_model_fields_are_configurable_without_expanding_defaults(self) -> None:
        table = _class_node("netbox_otnfaults/tables.py", "CutoverTaskTable")
        table_fields = _meta_tuple(table, "fields")
        missing_fields = _cutover_model_fields() - set(table_fields)

        self.assertFalse(
            missing_fields,
            f"割接列表列设置缺少字段: {sorted(missing_fields)}",
        )
        self.assertEqual(table_fields[-1], "actions")
        self.assertEqual(
            _meta_tuple(table, "default_columns"),
            EXPECTED_DEFAULT_COLUMNS,
        )


if __name__ == "__main__":
    unittest.main()
