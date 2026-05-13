import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
CORE_CONFIG_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "core" / "config.js"
FAULT_LEGEND_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "controls" / "FaultLegendControl.js"
)
DASHBOARD_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"


class FaultStatusLabelsTestCase(unittest.TestCase):
    def test_suspended_fault_status_display_label_is_delayed_disposal(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8-sig")
        dashboard_views_source = DASHBOARD_VIEWS_PATH.read_text(encoding="utf-8-sig")
        core_config_source = CORE_CONFIG_PATH.read_text(encoding="utf-8-sig")
        fault_legend_source = FAULT_LEGEND_PATH.read_text(encoding="utf-8-sig")
        dashboard_template_source = DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("(SUSPENDED, '延后处置', 'yellow')", models_source)
        self.assertIn("'suspended': '延后处置'", dashboard_views_source)
        self.assertIn('suspended: "延后处置"', core_config_source)
        self.assertIn("FAULT_STATUS_NAMES?.suspended || '延后处置'", fault_legend_source)
        self.assertIn('<span class="stat-label">延后处置</span>', dashboard_template_source)


if __name__ == "__main__":
    unittest.main()
