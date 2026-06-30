from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"


class OtnFaultImpactTimePopulateTestCase(unittest.TestCase):
    def test_model_clean_auto_populates_time(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8")
        self.assertIn("def clean(self):", models_source)
        
        # 验证是否包含自动填充故障起始时间的逻辑
        self.assertIn("self.service_interruption_time = self.otn_fault.fault_occurrence_time", models_source)
        # 验证是否包含自动填充故障恢复时间的逻辑
        self.assertIn("self.service_recovery_time = self.otn_fault.fault_recovery_time", models_source)
        # 验证是否包含自动填充业务站点A的逻辑
        self.assertIn("self.service_site_a = self.otn_fault.interruption_location_a", models_source)
        # 验证是否在 clean 方法中有 self.otn_fault 的前置检查
        self.assertIn("if hasattr(self, 'otn_fault') and self.otn_fault:", models_source)

    def test_form_clean_auto_populates_time(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8")
        self.assertIn("class OtnFaultImpactForm", forms_source)
        
        # 验证表单的 clean 方法中是否包含从 otn_fault 自动填充时间与站点的逻辑
        self.assertIn("otn_fault = cleaned_data.get('otn_fault')", forms_source)
        self.assertIn("cleaned_data['service_interruption_time'] = otn_fault.fault_occurrence_time", forms_source)
        self.assertIn("cleaned_data['service_recovery_time'] = otn_fault.fault_recovery_time", forms_source)
        self.assertIn("cleaned_data['service_site_a'] = otn_fault.interruption_location_a", forms_source)
        self.assertIn("cleaned_data['service_site_z'] = list(otn_fault.interruption_location.all())", forms_source)

    def test_frontend_js_auto_populates_time(self) -> None:
        template_path = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfaultimpact_edit.html"
        template_source = template_path.read_text(encoding="utf-8")
        
        # 验证是否包含监听选择框、获取数据并自动填充的 JS 代码片段
        self.assertIn("const faultSelect = document.getElementById('id_otn_fault');", template_source)
        self.assertIn("fetch(`/api/plugins/otnfaults/faults/${faultId}/`)", template_source)
        self.assertIn("element._flatpickr.setDate(date, true);", template_source)
        self.assertIn("const isEditMode = {% if object.pk %}true{% else %}false{% endif %};", template_source)
        self.assertIn("currentUrl.searchParams.set('otn_fault', faultId);", template_source)
        self.assertIn("window.location.href = currentUrl.toString();", template_source)


if __name__ == "__main__":
    unittest.main()
