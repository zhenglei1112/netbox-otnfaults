import ast
import unittest
from pathlib import Path
from types import FunctionType


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"


def _load_format_duration_units() -> FunctionType:
    module = ast.parse(MODELS_PATH.read_text(encoding="utf-8-sig"))
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_format_duration_units":
            namespace: dict[str, object] = {}
            compiled = compile(ast.Module(body=[node], type_ignores=[]), str(MODELS_PATH), "exec")
            exec(compiled, namespace)
            return namespace["_format_duration_units"]  # type: ignore[return-value]
    raise AssertionError("_format_duration_units helper not found")


class DurationZeroUnitsSourceTestCase(unittest.TestCase):
    def test_only_leading_zero_units_are_removed_from_duration_text(self) -> None:
        format_duration_units = _load_format_duration_units()

        self.assertEqual(format_duration_units(0, 3, 1, 19), "3小时1分19秒")
        self.assertEqual(format_duration_units(0, 3, 0, 19), "3小时0分19秒")
        self.assertEqual(format_duration_units(0, 0, 1, 0), "1分0秒")
        self.assertEqual(format_duration_units(0, 0, 0, 19), "19秒")
        self.assertEqual(format_duration_units(1, 0, 0, 0), "1天0小时0分0秒")

    def test_duration_outputs_use_shared_zero_unit_formatter(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("_format_duration_units(days, hours, minutes, secs)", models_source)
        self.assertIn("_format_duration_units(days, hours, minutes, seconds)", models_source)
        self.assertNotIn('f"{days}天{hours}小时{minutes}分{secs}秒', models_source)
        self.assertNotIn('f"{days}天{hours}小时{minutes}分{seconds}秒', models_source)


if __name__ == "__main__":
    unittest.main()
