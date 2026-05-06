import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
EDIT_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"


class OtnFaultReviewOngoingImpactsSourceTestCase(unittest.TestCase):
    def test_form_blocks_review_by_matching_ongoing_impact_type(self) -> None:
        source = FORMS_PATH.read_text(encoding="utf-8-sig")
        form_source = source.split("class OtnFaultForm", 1)[1].split("class OtnFaultImportForm", 1)[0]

        self.assertIn("def _get_ongoing_impact_count(self, service_type: str) -> int:", form_source)
        self.assertIn("service_type=service_type", form_source)
        self.assertIn("ServiceTypeChoices.BARE_FIBER", form_source)
        self.assertIn("ServiceTypeChoices.CIRCUIT", form_source)
        self.assertIn("def clean(self) -> dict[str, Any]:", form_source)
        self.assertIn("cleaned_data.get('manager_reviewed')", form_source)
        self.assertIn("cleaned_data.get('noc_reviewed')", form_source)
        self.assertIn("'manager_reviewed':", form_source)
        self.assertIn("'noc_reviewed':", form_source)
        self.assertIn("该物理故障下仍有裸纤业务故障处于持续状态", form_source)
        self.assertIn("该物理故障下仍有电路业务故障处于持续状态", form_source)

    def test_edit_template_warns_for_both_review_checkboxes_with_ongoing_impacts(self) -> None:
        template = EDIT_TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("data-ongoing-impact-count", template)
        self.assertIn("data-ongoing-impact-warning", template)
        self.assertIn("const ongoingImpactCount = Number(checkEl.getAttribute(ongoingImpactCountAttr) || '0');", template)
        self.assertIn("alert(checkEl.getAttribute(ongoingImpactWarningAttr)", template)
        self.assertNotIn("checkId === 'id_manager_reviewed'", template)

    def test_edit_template_scrolls_to_first_error_field_on_load(self) -> None:
        template = EDIT_TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("function initErrorFieldFocus()", template)
        self.assertIn("document.querySelector('.is-invalid, .invalid-feedback, .text-danger')", template)
        self.assertIn("errorRow.scrollIntoView({ behavior: 'smooth', block: 'center' });", template)
        self.assertIn("focusTarget.focus({ preventScroll: true });", template)
        self.assertIn("setTimeout(initErrorFieldFocus, 250);", template)


if __name__ == "__main__":
    unittest.main()
