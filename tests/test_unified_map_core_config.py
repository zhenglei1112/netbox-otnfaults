import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNIFIED_MAP_CORE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "unified_map_core.js"
)


class UnifiedMapCoreConfigTestCase(unittest.TestCase):
    def test_core_falls_back_to_compatibility_config_key(self) -> None:
        source = UNIFIED_MAP_CORE_PATH.read_text(encoding="utf-8")

        self.assertIn("window.OTNFaultMapConfig", source)
        self.assertIn("this._resolveConfig()", source)

    def test_core_reports_missing_config_before_reading_api_key(self) -> None:
        source = UNIFIED_MAP_CORE_PATH.read_text(encoding="utf-8")

        self.assertIn("地图配置未加载", source)
        self.assertIn("if (!this.config)", source)
        self.assertLess(source.index("if (!this.config)"), source.index("this.config.apiKey"))


if __name__ == "__main__":
    unittest.main()
