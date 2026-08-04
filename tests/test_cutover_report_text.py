import unittest
import runpy
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMATTER_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "cutover_report_text.py"
FORMATTER_NAMESPACE = runpy.run_path(str(FORMATTER_PATH))
build_cutover_report_line = FORMATTER_NAMESPACE["build_cutover_report_line"]
build_cutover_report_title = FORMATTER_NAMESPACE["build_cutover_report_title"]


class CutoverReportTextTestCase(unittest.TestCase):
    def test_builds_structured_report_and_removes_dynamic_whitespace(self) -> None:
        report = build_cutover_report_line(
            item_number=1,
            province=" 浙 江 ",
            cutover_type="光缆 割接",
            reason="宁波市 环城南路\t管廊施工",
            planned_time=datetime(2026, 7, 31, 20, 0),
            impact_minutes=240,
            service_name="华为 京汉广",
            site_a="宁 海",
            site_z="宁波 收费站",
            location="宁波市 环城南路 77号",
        )

        self.assertEqual(
            report,
            "（1）浙江（华为京汉广业务）\n"
            "    割接类型：光缆割接\n"
            "    计划时间：2026年7月31日 20:00，预计时长240分钟\n"
            "    中继段：A端宁海，Z端宁波收费站\n"
            "    割接地点：宁波市环城南路77号\n"
            "    割接原因：宁波市环城南路管廊施工",
        )
        self.assertNotIn("[", report)
        self.assertNotIn("]", report)
        self.assertNotIn("→", report)

    def test_formats_unlinked_business_without_duplicate_business_suffix(self) -> None:
        report = build_cutover_report_line(
            item_number=2,
            province="浙江",
            cutover_type="光缆割接",
            reason="管廊施工",
            planned_time=datetime(2026, 7, 31, 20, 0),
            impact_minutes=240,
            service_name="未关联业务",
            site_a="宁海",
            site_z="宁波收费站",
            location="环城南路",
        )

        self.assertIn("（2）浙江（未关联业务）", report)
        self.assertNotIn("未关联业务业务", report)

    def test_builds_24_hour_report_title_without_zero_padded_hour(self) -> None:
        title = build_cutover_report_title(
            datetime(2026, 8, 4, 9, 0),
            datetime(2026, 8, 5, 9, 0),
        )

        self.assertEqual(
            title,
            "24小时割接预告（2026年8月4日 9:00 至 2026年8月5日 9:00）",
        )


if __name__ == "__main__":
    unittest.main()
