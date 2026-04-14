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
        self.assertIn("flex-direction: column;", template_text)
        self.assertIn("min-height: 1.15em;", template_text)
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


if __name__ == "__main__":
    unittest.main()
