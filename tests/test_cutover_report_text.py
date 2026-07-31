import unittest
import runpy
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMATTER_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "cutover_report_text.py"
FORMATTER_NAMESPACE = runpy.run_path(str(FORMATTER_PATH))
build_cutover_report_line = FORMATTER_NAMESPACE["build_cutover_report_line"]


class CutoverReportTextTestCase(unittest.TestCase):
    def test_builds_written_report_and_removes_all_dynamic_whitespace(self) -> None:
        report = build_cutover_report_line(
            province=" 浙 江 ",
            reason="宁波市 环城南路\t管廊施工",
            planned_time=datetime(2026, 7, 31, 20, 0),
            impact_minutes=240,
            service_name="华为 京汉广",
            site_a="宁 海",
            site_z="宁波 收费站",
        )

        self.assertEqual(
            report,
            "浙江割接报备：因宁波市环城南路管廊施工影响，需实施光缆割接，"
            "计划于2026年7月31日20:00开始，预计影响时长240分钟，"
            "影响华为京汉广业务，A端宁海，Z端宁波收费站。",
        )
        self.assertNotIn(" ", report)
        self.assertNotIn("[", report)
        self.assertNotIn("]", report)
        self.assertNotIn("→", report)

    def test_reports_no_business_impact_when_service_is_unlinked(self) -> None:
        report = build_cutover_report_line(
            province="浙江",
            reason="管廊施工",
            planned_time=datetime(2026, 7, 31, 20, 0),
            impact_minutes=240,
            service_name="未关联业务",
            site_a="宁海",
            site_z="宁波收费站",
        )

        self.assertEqual(
            report,
            "浙江割接报备：因管廊施工影响，需实施光缆割接，"
            "计划于2026年7月31日20:00开始，预计影响时长240分钟，"
            "不影响业务，A端宁海，Z端宁波收费站。",
        )
        self.assertNotIn("影响未关联业务业务", report)


if __name__ == "__main__":
    unittest.main()
