import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
EDIT_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class OtnFaultSuspendedFieldSourceTestCase(unittest.TestCase):
    def test_model_declares_boolean_suspended_flag_after_status_and_auto_sets_true(self) -> None:
        source = _read(MODELS_PATH)

        status_marker = "fault_status = models.CharField("
        suspended_marker = "is_suspended = models.BooleanField("
        self.assertLess(source.index(status_marker), source.index(suspended_marker))
        self.assertIn("default=False", source)
        self.assertIn("verbose_name='挂起'", source)
        self.assertIn("help_text='该故障为挂起故障，不计入故障时长统计'", source)
        self.assertIn("if self.fault_status == FaultStatusChoices.SUSPENDED:", source)
        self.assertIn("self.is_suspended = True", source)

    def test_forms_filters_and_serializer_expose_suspended_flag_after_status(self) -> None:
        forms_source = _read(FORMS_PATH)
        filtersets_source = _read(FILTERSETS_PATH)
        serializers_source = _read(SERIALIZERS_PATH)

        self.assertIn("'fault_status', 'is_suspended'", forms_source)
        self.assertIn("'fault_status', 'is_suspended'", filtersets_source)
        self.assertIn("'fault_status', 'is_suspended', 'status_color'", serializers_source)
        self.assertIn("'fault_status', 'is_suspended'", serializers_source)

    def test_edit_and_detail_templates_place_suspended_flag_after_status(self) -> None:
        edit_source = _read(EDIT_TEMPLATE_PATH)
        detail_source = _read(DETAIL_TEMPLATE_PATH)

        status_field = "{% render_field form.fault_status %}"
        suspended_field = "{% render_field form.is_suspended %}"
        self.assertLess(edit_source.index(status_field), edit_source.index(suspended_field))
        self.assertIn("const SUSPENDED_STATUS = 'suspended';", edit_source)
        self.assertIn("suspendedInput.checked = true;", edit_source)

        status_badge = "{% badge object.get_fault_status_display bg_color=object.get_fault_status_color %}"
        suspended_label = "is_suspended"
        self.assertLess(detail_source.index(status_badge), detail_source.index(suspended_label))


if __name__ == "__main__":
    unittest.main()
