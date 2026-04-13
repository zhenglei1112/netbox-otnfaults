import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultTimelineRecoveryIconSourceTestCase(unittest.TestCase):
    def test_recovery_step_uses_restore_alert_icon(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("{% elif forloop.counter == 5 %}mdi-restore-alert{% else %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 5 %}mdi-restore{% else %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 5 %}mdi-check{% else %}", template_text)


if __name__ == "__main__":
    unittest.main()
