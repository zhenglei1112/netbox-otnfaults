import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"Class {class_name} not found")


def _find_assignment(class_node: ast.ClassDef, target_name: str) -> ast.AST:
    for node in class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == target_name:
            return node.value
    raise AssertionError(f"Assignment {target_name} not found in {class_node.name}")


class OtnFaultPowerReasonTreeSourceTestCase(unittest.TestCase):
    def test_model_defines_power_fault_reason_tree(self) -> None:
        module = _parse_module(MODELS_PATH)
        class_node = _find_class(module, "OtnFault")

        reason_choices = ast.literal_eval(_find_assignment(class_node, "INTERRUPTION_REASON_CHOICES"))
        detail_choices = ast.literal_eval(_find_assignment(class_node, "INTERRUPTION_REASON_DETAIL_CHOICES"))
        category_to_reason_map = ast.literal_eval(_find_assignment(class_node, "CATEGORY_TO_REASON_MAP"))
        reason_to_detail_map = ast.literal_eval(_find_assignment(class_node, "REASON_TO_DETAIL_MAP"))

        expected_power_reasons = [
            "ac_fault_power",
            "power_equipment_fault",
            "misoperation_power",
            "natural_disaster_power",
            "unknown_power",
            "power_equipment_rectification",
        ]
        self.assertEqual(category_to_reason_map["power_fault"], expected_power_reasons)

        for value, label in [
            ("ac_fault_power", "交流故障"),
            ("power_equipment_fault", "电源设备故障"),
            ("misoperation_power", "误操作"),
            ("natural_disaster_power", "自然灾害"),
            ("unknown_power", "不详"),
            ("power_equipment_rectification", "电源设备整改"),
        ]:
            self.assertIn((value, label), reason_choices)

        expected_details = {
            "room_power_test": "机房供电测试",
            "grid_power_maintenance": "国网供电检修",
            "breaker_trip": "空开跳闸",
            "ups_fault": "UPS故障",
            "mains_power_outage": "市电停电",
            "natural_disaster_power_detail": "自然灾害",
            "manual_misoperation": "人为误操作",
            "other_power": "其他",
            "switching_power_fault": "开关电源故障",
            "rectifier_module_fault": "整流模块故障",
            "human_caused": "人为导致",
            "power_flood": "洪水",
            "power_rainstorm": "暴雨",
            "power_lightning": "雷击",
            "power_relocation": "搬迁",
            "switching_power_rectification": "开关电源整改",
            "battery_rectification": "电池整改",
            "owner_unit_rectification": "业主单位整改",
        }
        for value, label in expected_details.items():
            self.assertIn((value, label), detail_choices)

        self.assertEqual(
            reason_to_detail_map["ac_fault_power"],
            [
                "room_power_test",
                "grid_power_maintenance",
                "breaker_trip",
                "ups_fault",
                "mains_power_outage",
                "natural_disaster_power_detail",
                "manual_misoperation",
                "other_power",
            ],
        )
        self.assertEqual(reason_to_detail_map["power_equipment_fault"], ["switching_power_fault", "rectifier_module_fault"])
        self.assertEqual(reason_to_detail_map["misoperation_power"], ["human_caused"])
        self.assertEqual(reason_to_detail_map["natural_disaster_power"], ["power_flood", "power_rainstorm", "power_lightning"])
        self.assertEqual(reason_to_detail_map["unknown_power"], [])
        self.assertEqual(
            reason_to_detail_map["power_equipment_rectification"],
            [
                "power_relocation",
                "grid_power_maintenance",
                "switching_power_rectification",
                "battery_rectification",
                "owner_unit_rectification",
                "mains_power_outage",
            ],
        )

    def test_edit_template_uses_same_power_fault_reason_tree(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("'power_fault': ['ac_fault_power', 'power_equipment_fault',", template_text)
        self.assertIn("'unknown_power', 'power_equipment_rectification']", template_text)
        self.assertIn("'ac_fault_power': ['room_power_test', 'grid_power_maintenance',", template_text)
        self.assertIn("'power_equipment_fault': ['switching_power_fault', 'rectifier_module_fault']", template_text)
        self.assertIn("'misoperation_power': ['human_caused']", template_text)
        self.assertIn("'natural_disaster_power': ['power_flood', 'power_rainstorm', 'power_lightning']", template_text)
        self.assertIn("'unknown_power': []", template_text)
        self.assertIn("'power_equipment_rectification': ['power_relocation', 'grid_power_maintenance',", template_text)


if __name__ == "__main__":
    unittest.main()
