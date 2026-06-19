import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATISTICS_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"

class StatisticsDrillDownResourceTypeTestCase(unittest.TestCase):
    def test_resource_type_aliases_mappings(self) -> None:
        source = STATISTICS_VIEWS_PATH.read_text(encoding="utf-8")
        
        # 校验 resource_type_aliases 定义
        self.assertIn("resource_type_aliases: dict[str, str] = {", source)
        
        # 提取 resource_type_aliases 字典块
        start = source.index("resource_type_aliases: dict[str, str] = {")
        end = source.index("}", start)
        dict_content = source[start:end+1]
        
        # 校验简写与完整字面量映射
        self.assertIn("'自建': ResourceTypeChoices.SELF_BUILT", dict_content)
        self.assertIn("'自建光缆': ResourceTypeChoices.SELF_BUILT", dict_content)
        self.assertIn("'协调': ResourceTypeChoices.COORDINATED", dict_content)
        self.assertIn("'协调资源': ResourceTypeChoices.COORDINATED", dict_content)
        self.assertIn("'租赁': ResourceTypeChoices.LEASED", dict_content)
        self.assertIn("'租赁纤芯': ResourceTypeChoices.LEASED", dict_content)
        self.assertIn("'未填写': 'unfilled'", dict_content)

if __name__ == "__main__":
    unittest.main()
