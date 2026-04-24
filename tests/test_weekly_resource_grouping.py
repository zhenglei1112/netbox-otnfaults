import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WEEKLY_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "weekly_report_views.py"
WEEKLY_SCRIPT_PATH = REPO_ROOT / "netbox_otnfaults" / "scripts" / "weekly_report.py"
WEEKLY_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "weekly_report_dashboard.html"
WEEKLY_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "weekly_report_dashboard.js"


class WeeklyResourceGroupingTestCase(unittest.TestCase):
    def test_weekly_report_view_counts_and_durations_use_unified_groups(self) -> None:
        source = WEEKLY_VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("from .statistics_views import _source_group_for_fault", source)
        self.assertIn("self_controlled_count = sum(", source)
        self.assertIn("third_party_count = sum(", source)
        self.assertIn("_source_group_for_fault(fault) == \"自控\"", source)
        self.assertIn("_source_group_for_fault(fault) == \"第三方\"", source)
        self.assertIn("self_controlled_duration = sum(", source)
        self.assertIn("third_party_duration = sum(", source)
        self.assertIn('"self_controlled": {', source)
        self.assertIn('"third_party": {', source)
        self.assertNotIn("fault.resource_type == ResourceTypeChoices.SELF_BUILT", source)
        self.assertNotIn(
            "fault.resource_type in (ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED)",
            source,
        )

    def test_weekly_report_script_uses_same_grouping_and_updated_copy(self) -> None:
        source = WEEKLY_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("from netbox_otnfaults.statistics_views import _source_group_for_fault", source)
        self.assertIn("self_controlled_count = sum(", source)
        self.assertIn("third_party_count = sum(", source)
        self.assertIn("_source_group_for_fault(f) == \"自控\"", source)
        self.assertIn("_source_group_for_fault(f) == \"第三方\"", source)
        self.assertIn("self_controlled_dur = sum(", source)
        self.assertIn("third_party_dur = sum(", source)
        self.assertIn("其中自控光缆中断{self_controlled_count}次，第三方光缆中断{third_party_count}次", source)
        self.assertIn("其中自控光缆中断{self_controlled_dur:.1f}小时，第三方光缆中断{third_party_dur:.1f}小时", source)
        self.assertNotIn("协调和租赁纤芯中断", source)
        self.assertNotIn("fault.resource_type in [ResourceTypeChoices.COORDINATED, ResourceTypeChoices.LEASED]", source)

    def test_weekly_dashboard_labels_and_renderer_match_unified_names(self) -> None:
        template = WEEKLY_TEMPLATE_PATH.read_text(encoding="utf-8")
        source = WEEKLY_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("自控", template)
        self.assertIn("第三方", template)
        self.assertNotIn("协调 / 租赁", template)
        self.assertIn("const selfControlled = summary.self_controlled ?? {};", source)
        self.assertIn("const thirdParty = summary.third_party ?? {};", source)
        self.assertIn('setText("kpi-self-built"', source)
        self.assertIn('setText("kpi-leased"', source)
        self.assertIn("formatNumber(selfControlled.count)", source)
        self.assertIn("formatDuration(selfControlled.duration)", source)
        self.assertIn("formatNumber(thirdParty.count)", source)
        self.assertIn("formatDuration(thirdParty.duration)", source)
        self.assertNotIn("const selfBuilt = summary.self_built ?? {};", source)
        self.assertNotIn("const leased = summary.leased ?? {};", source)


if __name__ == "__main__":
    unittest.main()
