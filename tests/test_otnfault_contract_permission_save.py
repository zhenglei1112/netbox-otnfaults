import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"


class OtnFaultContractPermissionSaveTestCase(unittest.TestCase):
    def test_fault_form_contract_field_allows_current_contract_during_cleaning(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8")
        field_source = forms_source.split("class CurrentContractDynamicModelChoiceField", 1)[1].split(
            "class OtnFaultForm", 1
        )[0]
        form_source = forms_source.split("class OtnFaultForm(NetBoxModelForm):", 1)[1].split(
            "class OtnFaultImportForm", 1
        )[0]
        contract_field = form_source.split("contract = CurrentContractDynamicModelChoiceField(", 1)[1].split(
            "recovery_mode = forms.MultipleChoiceField", 1
        )[0]

        self.assertIn("DynamicModelChoiceField", field_source)
        self.assertIn("def to_python(self, value: Any) -> Any:", field_source)
        self.assertIn("except ValidationError", field_source)
        self.assertIn("str(value) == str(current_contract_id)", field_source)
        self.assertIn("Contract.objects.filter(pk=current_contract_id).first()", field_source)
        self.assertIn("contract = CurrentContractDynamicModelChoiceField(", form_source)
        self.assertIn("self.fields['contract'].current_contract_id = contract_id", form_source)
        self.assertIn("queryset=Contract.objects.all()", contract_field)

    def test_fault_contract_dynamic_filter_remains_limited_by_handling_unit(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8")
        form_source = forms_source.split("class OtnFaultForm(NetBoxModelForm):", 1)[1].split(
            "class OtnFaultImportForm", 1
        )[0]
        contract_field = form_source.split("contract = CurrentContractDynamicModelChoiceField(", 1)[1].split(
            "recovery_mode = forms.MultipleChoiceField", 1
        )[0]

        self.assertIn("query_params={", contract_field)
        self.assertIn("'external_party_object': '$handling_unit'", contract_field)


if __name__ == "__main__":
    unittest.main()
