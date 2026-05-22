import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultDetailSummaryTimesSourceTestCase(unittest.TestCase):
    def test_summary_times_and_durations_use_updated_layout(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        timeline_index = template_text.index('<div class="timeline-container py-4" style="position: relative;">')
        self.assertIn('<div class="d-flex align-items-center justify-content-center mt-3 pt-2 border-top">', template_text)
        duration_index = template_text.index('<div class="d-flex align-items-center justify-content-center mt-3 pt-2 border-top">')
        self.assertLess(timeline_index, duration_index)

        self.assertIn('class="timeline-time-highlight fw-bold"', template_text)
        self.assertIn('{% if forloop.first or forloop.counter == 5 %}', template_text)
        self.assertIn('{% if step.highlight_date %}{{ step.highlight_date }}{% else %}&nbsp;{% endif %}', template_text)
        self.assertIn('{{ step.highlight_time|default:"—" }}', template_text)
        self.assertIn("position: relative;", template_text)
        self.assertIn("position: absolute;", template_text)
        self.assertIn("left: 0;", template_text)
        self.assertIn("right: 0;", template_text)
        self.assertIn("top: 0;", template_text)
        self.assertIn("bottom: 0;", template_text)
        self.assertIn("height: 2.3em;", template_text)
        self.assertNotIn("min-height: 2.3em;", template_text)
        self.assertIn("width: 100%;", template_text)
        self.assertIn('height: 84px;', template_text)
        self.assertIn('top: 48px;', template_text)

        highlight_index = template_text.index('{% if forloop.first or forloop.counter == 5 %}')
        label_index = template_text.index('<div class="timeline-label fw-semibold text-body mb-0"')
        self.assertLess(highlight_index, label_index)

        self.assertIn('<span class="fw-semibold text-muted small me-2">故障历时:</span>', template_text)
        self.assertIn('<span class="fw-semibold text-muted small me-2">处理历时:</span>', template_text)

    def test_detail_renders_all_fault_time_fields_as_rows(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn('<h5 class="card-header">时间记录</h5>', template_text)
        time_record_block = template_text.split('<h5 class="card-header">时间记录</h5>', 1)[1].split('</table>', 1)[0]

        expected_rows = {
            "故障起始时间": "object.fault_occurrence_time",
            "处理派发时间": "object.dispatch_time",
            "维修出发时间": "object.departure_time",
            "到达现场时间": "object.arrival_time",
            "故障修复时间": "object.repair_time",
            "故障恢复时间": "object.fault_recovery_time",
            "封包完成时间": "object.closure_time",
            "故障历时": "object.fault_duration",
            "处理历时": "object.processing_duration",
        }
        for label, field_marker in expected_rows.items():
            self.assertIn(label, time_record_block)
            self.assertIn(field_marker, time_record_block)


if __name__ == "__main__":
    unittest.main()
