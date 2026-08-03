import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCALE_TEMPLATE = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "flatpickr_zh.html"
)
LIST_TEMPLATE = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "otnfault_list.html"
)
EDIT_TEMPLATE = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "otnfault_edit.html"
)


class OtnFaultListDateTimeLocaleTestCase(unittest.TestCase):
    def test_list_loads_chinese_locale_without_defaulting_current_time(self) -> None:
        template = LIST_TEMPLATE.read_text(encoding="utf-8-sig")

        self.assertIn(
            "{% include 'netbox_otnfaults/inc/flatpickr_zh.html' with disable_default_now=True %}",
            template,
        )

    def test_locale_template_guards_only_the_default_now_hook(self) -> None:
        template = LOCALE_TEMPLATE.read_text(encoding="utf-8-sig")
        locale_position = template.index("fp.set('locale', zhLocale);")
        guard_position = template.index("{% if not disable_default_now %}")
        hook_position = template.index("var origOnOpen = fp.config.onOpen || [];")
        end_guard_position = template.index("{% endif %}", hook_position)

        self.assertLess(locale_position, guard_position)
        self.assertLess(guard_position, hook_position)
        self.assertLess(hook_position, end_guard_position)

    def test_fault_edit_keeps_default_now_behavior(self) -> None:
        template = EDIT_TEMPLATE.read_text(encoding="utf-8-sig")

        self.assertIn(
            "{% include 'netbox_otnfaults/inc/flatpickr_zh.html' %}",
            template,
        )
        self.assertNotIn("disable_default_now=True", template)


if __name__ == "__main__":
    unittest.main()
