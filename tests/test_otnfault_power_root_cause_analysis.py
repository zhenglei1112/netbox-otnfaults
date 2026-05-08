from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
EDIT_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"
MIGRATION_PATH = REPO_ROOT / "netbox_otnfaults" / "migrations" / "0059_otnfault_power_root_cause_analysis.py"


class OtnFaultPowerRootCauseAnalysisSourceTestCase(unittest.TestCase):
    def test_model_defines_array_field_and_choices(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        choices_source = source.split("class PowerRootCauseAnalysisChoices", 1)[1].split("class PowerRecoveryModeChoices", 1)[0]
        field_source = source.split("root_cause_analysis = ArrayField(", 1)[1].split("power_recovery_mode", 1)[0]

        expected_labels = [
            "开关电源故障",
            "整流模块故障",
            "电池耗尽",
            "无电池",
            "电池备电时间不足",
            "机房供电测试",
            "国网供电检修",
            "空开跳闸",
            "UPS故障",
            "市电停电",
            "自然灾害",
            "人为误操作",
            "其他",
        ]
        for label in expected_labels:
            self.assertIn(label, choices_source)

        self.assertIn("key = 'OtnFault.root_cause_analysis'", choices_source)
        self.assertIn("base_field=models.CharField(", field_source)
        self.assertIn("choices=PowerRootCauseAnalysisChoices", field_source)
        self.assertIn("default=list", field_source)
        self.assertIn("verbose_name='根因分析'", field_source)
        self.assertIn("GinIndex(fields=['root_cause_analysis'])", source)
        self.assertIn("def get_root_cause_analysis_display(self) -> str:", source)
        self.assertIn("def get_root_cause_analysis_color(self) -> str | None:", source)

    def test_forms_filtersets_tables_api_and_templates_include_field(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8-sig")
        filtersets_source = FILTERSETS_PATH.read_text(encoding="utf-8-sig")
        tables_source = TABLES_PATH.read_text(encoding="utf-8-sig")
        serializers_source = SERIALIZERS_PATH.read_text(encoding="utf-8-sig")
        edit_template = EDIT_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        detail_template = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        migration_source = MIGRATION_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("PowerRootCauseAnalysisChoices", forms_source)
        self.assertIn("root_cause_analysis = forms.MultipleChoiceField(", forms_source)
        self.assertIn("root_cause_analysis = SimpleArrayField(", forms_source)
        self.assertIn("label='根因分析'", forms_source)
        self.assertIn("def clean_root_cause_analysis(self) -> list[str]:", forms_source)
        self.assertIn("'power_data_type', 'root_cause_analysis', 'recovery_mode'", forms_source)
        self.assertIn("'recovery_mode', 'root_cause_analysis'", forms_source)

        self.assertIn("root_cause_analysis = django_filters.MultipleChoiceFilter(", filtersets_source)
        self.assertIn("root_cause_analysis__overlap=value", filtersets_source)

        self.assertIn("root_cause_analysis = tables.Column(", tables_source)
        self.assertIn("verbose_name='根因分析'", tables_source)
        self.assertIn("'root_cause_analysis'", tables_source)

        self.assertIn("root_cause_analysis = serializers.ListField(", serializers_source)
        self.assertIn("'root_cause_analysis'", serializers_source)

        power_edit_section = edit_template.split('id="power-supplementary-info"', 1)[1].split('id="fault-review-info"', 1)[0]
        self.assertIn("{% render_field form.root_cause_analysis %}", power_edit_section)

        power_detail_section = detail_template.split("{% if object.is_power_fault %}", 1)[1]
        self.assertIn("<th scope=\"row\">根因分析</th>", power_detail_section)
        self.assertIn("{% load otnfault_display %}", detail_template)
        self.assertIn("object.root_cause_analysis|otnfault_choice_labels:\"root_cause_analysis\"", power_detail_section)
        self.assertIn("class=\"badge rounded-pill border bg-body text-body\"", power_detail_section)
        self.assertNotIn("object.get_root_cause_analysis_display", power_detail_section)
        self.assertNotIn("object.get_root_cause_analysis_color", power_detail_section)

        self.assertIn("migrations.AddField(", migration_source)
        self.assertIn("name='root_cause_analysis'", migration_source)
        self.assertIn("GinIndex(fields=['root_cause_analysis']", migration_source)


if __name__ == "__main__":
    unittest.main()
