import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultTimelineDispatchIconSourceTestCase(unittest.TestCase):
    def test_dispatch_step_uses_account_icon(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("{% elif forloop.counter == 2 %}mdi-account{% elif forloop.counter == 3 %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 2 %}mdi-account-wrench{% elif forloop.counter == 3 %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 2 %}mdi-cellphone{% elif forloop.counter == 3 %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 2 %}mdi-phone{% elif forloop.counter == 3 %}", template_text)
        self.assertNotIn("{% elif forloop.counter == 2 %}mdi-refresh{% elif forloop.counter == 3 %}", template_text)


if __name__ == "__main__":
    unittest.main()
