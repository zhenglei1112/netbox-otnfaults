from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
EDIT_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultPowerContractFieldsSourceTestCase(unittest.TestCase):
    def test_power_supplementary_group_includes_vendor_and_contract_fields(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8-sig")
        form_block = forms_source.split("class OtnFaultForm", 1)[1].split("class OtnFaultImportForm", 1)[0]
        power_fieldset = form_block.split("FieldSet(\n            'power_data_type'", 1)[1].split(
            "name='供电故障补充信息'", 1
        )[0]

        self.assertIn("'handling_unit'", power_fieldset)
        self.assertIn("'contract'", power_fieldset)

    def test_edit_template_renders_vendor_and_contract_once_for_dynamic_relocation(self) -> None:
        edit_template = EDIT_TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertEqual(edit_template.count("{% render_field form.handling_unit %}"), 1)
        self.assertEqual(edit_template.count("{% render_field form.contract %}"), 1)
        self.assertIn('id="fiber-contract-fields-anchor"', edit_template)
        self.assertIn('id="power-contract-fields-anchor"', edit_template)
        self.assertNotIn('id="shared-contract-fields"', edit_template)
        self.assertNotIn('style="display: contents;"', edit_template)
        self.assertIn("moveSharedContractFields(category)", edit_template)
        self.assertIn("getContractFieldNodes()", edit_template)
        self.assertIn("findDirectFieldColumns(select)", edit_template)
        self.assertIn("Array.from(row.children)", edit_template)
        self.assertIn("targetAnchor.parentNode.insertBefore(node, targetAnchor)", edit_template)

    def test_power_detail_section_shows_vendor_and_contract_fields(self) -> None:
        detail_template = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        power_detail_section = detail_template.split(
            '<h5 class="card-header">供电故障补充信息</h5>', 1
        )[1].split("</table>", 1)[0]

        self.assertIn("代维方/租赁方", power_detail_section)
        self.assertIn("代维/租赁合同", power_detail_section)
        self.assertIn("object.handling_unit", power_detail_section)
        self.assertIn("object.contract", power_detail_section)


if __name__ == "__main__":
    unittest.main()
