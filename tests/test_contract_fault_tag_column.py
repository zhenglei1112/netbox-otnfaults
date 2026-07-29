import ast
from pathlib import Path


TABLES_PATH = Path(__file__).resolve().parents[1] / 'netbox_otnfaults' / 'tables.py'


def _class_node(tree, name):
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == name
    )


def _assigned_value(class_node, name):
    return next(
        ast.literal_eval(node.value)
        for node in class_node.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )


def test_contract_fault_table_exposes_tags():
    tree = ast.parse(TABLES_PATH.read_text(encoding='utf-8'))
    table = _class_node(tree, 'ContractOtnFaultTable')
    meta = next(
        node
        for node in table.body
        if isinstance(node, ast.ClassDef) and node.name == 'Meta'
    )

    tag_assignment = next(
        node
        for node in table.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'tags' for target in node.targets)
    )
    fields = _assigned_value(meta, 'fields')
    default_columns = _assigned_value(meta, 'default_columns')

    assert isinstance(tag_assignment.value, ast.Call)
    assert 'tags' in fields
    assert 'tags' in default_columns
