from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class CutoverGenerateFaultPlanTestCase(unittest.TestCase):
    def test_otnfault_has_source_cutover_task_relation(self) -> None:
        text = read("netbox_otnfaults/models.py")
        otn_fault = text.split("class OtnFault(", 1)[1].split("class ServiceTypeChoices", 1)[0]

        self.assertIn("source_cutover_task = models.ForeignKey(", otn_fault)
        self.assertTrue("to='CutoverTask'" in otn_fault or 'to="CutoverTask"' in otn_fault)
        self.assertIn("related_name='generated_faults'", otn_fault)
        self.assertIn("on_delete=models.SET_NULL", otn_fault)

    def test_generation_form_excludes_rectification_fields(self) -> None:
        text = read("netbox_otnfaults/forms.py")

        self.assertIn("class CutoverFaultGenerationForm", text)
        form = text.split("class CutoverFaultGenerationForm", 1)[1].split("\n\nclass ", 1)[0]
        self.assertIn("fault_occurrence_time", form)
        self.assertIn("fault_recovery_time", form)
        self.assertNotIn("rectification_status", form)
        self.assertNotIn("rectification_measures", form)
        self.assertNotIn("rectification_description", form)

    def test_generation_service_has_transaction_and_no_rectification_mapping(self) -> None:
        service_path = REPO_ROOT / "netbox_otnfaults" / "services" / "cutover_fault_generation.py"

        self.assertTrue(service_path.exists())
        text = service_path.read_text(encoding="utf-8")
        self.assertIn("def build_fault_initial_data(", text)
        self.assertIn("def create_fault_from_cutover(", text)
        self.assertIn("transaction.atomic()", text)
        self.assertIn("source_cutover_task", text)
        self.assertNotIn("rectification_status", text)
        self.assertNotIn("rectification_measures", text)

    def test_generation_service_prefills_cutover_report_as_reported(self) -> None:
        text = read("netbox_otnfaults/services/cutover_fault_generation.py")

        self.assertIn("CutoverReportStatusChoices", text)
        self.assertIn("'cutover_report_status': CutoverReportStatusChoices.REPORTED", text)

    def test_fault_occurrence_time_prefers_cutover_start_time(self) -> None:
        text = read("netbox_otnfaults/services/cutover_fault_generation.py")
        helper = text.split("def _fault_occurrence_time(", 1)[1].split("\n\n", 1)[0]

        self.assertIn("cutover.started_at or cutover.planned_cutover_time", helper)

    def test_generate_fault_route_precedes_cutover_detail_include(self) -> None:
        text = read("netbox_otnfaults/urls.py")

        self.assertIn("cutovertask_generate_fault", text)
        generate_index = text.index("cutovertask_generate_fault")
        detail_index = text.index("cutovers/<int:pk>/', include")
        self.assertLess(generate_index, detail_index)

    def test_templates_expose_generation_flow(self) -> None:
        cutover_detail = read("netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html")
        confirm_path = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "cutovertask_generate_fault.html"
        fault_detail = read("netbox_otnfaults/templates/netbox_otnfaults/otnfault.html")

        self.assertIn("cutovertask_generate_fault", cutover_detail)
        self.assertTrue(confirm_path.exists())
        confirm = confirm_path.read_text(encoding="utf-8")
        self.assertIn("确认生成故障", confirm)
        self.assertIn("影响业务", confirm)
        self.assertTrue("source_cutover_task" in fault_detail or "来源割接" in fault_detail)

    def test_confirmation_template_uses_chinese_datetime_format(self) -> None:
        confirm = read("netbox_otnfaults/templates/netbox_otnfaults/cutovertask_generate_fault.html")

        self.assertIn('object.planned_cutover_time|date:"Y年n月j日 H:i"', confirm)
        self.assertIn('impact.service_interruption_time|date:"Y年n月j日 H:i"', confirm)
        self.assertIn('impact.service_recovery_time|date:"Y年n月j日 H:i"', confirm)


if __name__ == "__main__":
    unittest.main()
