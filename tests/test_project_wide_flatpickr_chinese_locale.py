import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "netbox_otnfaults"
TEMPLATE_ROOT = PLUGIN_ROOT / "templates" / "netbox_otnfaults"
VIEWS_PATH = PLUGIN_ROOT / "views.py"


def _class_block(source: str, class_name: str) -> str:
    match = re.search(
        rf"^class {class_name}\b.*?(?=^class |\Z)",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Class not found: {class_name}")
    return match.group(0)


class ProjectWideFlatpickrChineseLocaleTestCase(unittest.TestCase):
    def test_shared_datetime_templates_load_locale_without_default_now(self) -> None:
        expected_parents = {
            "datetime_object_list.html": "generic/object_list.html",
            "datetime_object_edit.html": "generic/object_edit.html",
            "datetime_bulk_edit.html": "generic/bulk_edit.html",
        }

        for filename, parent in expected_parents.items():
            with self.subTest(filename=filename):
                template = (TEMPLATE_ROOT / filename).read_text(encoding="utf-8-sig")
                self.assertIn(f"{{% extends '{parent}' %}}", template)
                self.assertIn(
                    "{% include 'netbox_otnfaults/inc/flatpickr_zh.html' with disable_default_now=True %}",
                    template,
                )

    def test_generic_views_with_datetime_fields_use_shared_templates(self) -> None:
        views = VIEWS_PATH.read_text(encoding="utf-8-sig")
        expected_templates = {
            "CutoverTaskListView": "netbox_otnfaults/datetime_object_list.html",
            "CutoverImpactListView": "netbox_otnfaults/datetime_object_list.html",
            "HeavyDutyEditView": "netbox_otnfaults/datetime_object_edit.html",
            "OtnFaultBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "OtnFaultImpactBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "BareFiberServiceBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "CircuitServiceBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "CutoverTaskBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "CutoverImpactBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
            "HeavyDutyBulkEditView": "netbox_otnfaults/datetime_bulk_edit.html",
        }

        for view_name, template_name in expected_templates.items():
            with self.subTest(view=view_name):
                block = _class_block(views, view_name)
                self.assertIn(f"template_name = '{template_name}'", block)

    def test_custom_datetime_templates_load_locale_without_default_now(self) -> None:
        for filename in (
            "otnfault_list.html",
            "otnfaultimpact_list.html",
            "heavyduty_list.html",
            "cutovertask_generate_fault.html",
        ):
            with self.subTest(filename=filename):
                template = (TEMPLATE_ROOT / filename).read_text(encoding="utf-8-sig")
                self.assertIn(
                    "{% include 'netbox_otnfaults/inc/flatpickr_zh.html' with disable_default_now=True %}",
                    template,
                )


if __name__ == "__main__":
    unittest.main()
