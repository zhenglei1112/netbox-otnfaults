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
MIGRATION_PATH = REPO_ROOT / "netbox_otnfaults" / "migrations" / "0060_otnfault_power_rectification_fields.py"


class OtnFaultPowerRectificationFieldsSourceTestCase(unittest.TestCase):
    def test_model_defines_rectification_choices_and_fields(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")

        for class_name, labels in {
            "PowerRectificationStatusChoices": ["无需整改", "需要整改", "重复合并"],
            "PowerRectificationMeasureChoices": ["更换电源", "更换电池", "电池扩容", "电源扩容", "增加动环", "其他"],
            "PowerRectificationSubjectChoices": ["本部", "子公司", "外单位"],
            "PowerRectificationProgressChoices": ["未实施", "进行中", "已完成", "挂起"],
        }.items():
            choices_source = source.split(f"class {class_name}", 1)[1].split("class ", 1)[0]
            for label in labels:
                self.assertIn(label, choices_source)

        expected_fields = [
            "rectification_status = models.CharField(",
            "rectification_measures = ArrayField(",
            "rectification_description = models.TextField(",
            "rectification_subject = models.CharField(",
            "rectification_progress = models.CharField(",
            "planned_completion_date = models.DateField(",
            "actual_completion_date = models.DateField(",
            "rectification_completion_description = models.TextField(",
        ]
        for field in expected_fields:
            self.assertIn(field, source)

        self.assertIn("choices=PowerRectificationMeasureChoices", source)
        self.assertIn("default=list", source)
        self.assertIn("GinIndex(fields=['rectification_measures'])", source)
        self.assertIn("def get_rectification_measures_display(self) -> str:", source)
        self.assertIn("def get_rectification_measures_color(self) -> str | None:", source)

    def test_ui_filter_table_api_and_migration_include_fields(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8-sig")
        filtersets_source = FILTERSETS_PATH.read_text(encoding="utf-8-sig")
        tables_source = TABLES_PATH.read_text(encoding="utf-8-sig")
        serializers_source = SERIALIZERS_PATH.read_text(encoding="utf-8-sig")
        edit_template = EDIT_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        detail_template = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        migration_source = MIGRATION_PATH.read_text(encoding="utf-8-sig")

        field_names = [
            "rectification_status",
            "rectification_measures",
            "rectification_description",
            "rectification_subject",
            "rectification_progress",
            "planned_completion_date",
            "actual_completion_date",
            "rectification_completion_description",
        ]
        for field_name in field_names:
            self.assertIn(field_name, forms_source)
            self.assertIn(field_name, filtersets_source)
            self.assertIn(field_name, tables_source)
            self.assertIn(field_name, serializers_source)
            self.assertIn(f"name='{field_name}'", migration_source)

        self.assertIn("rectification_measures = forms.MultipleChoiceField(", forms_source)
        self.assertIn("rectification_measures = SimpleArrayField(", forms_source)
        self.assertIn("def clean_rectification_measures(self) -> list[str]:", forms_source)
        self.assertIn("rectification_measures = django_filters.MultipleChoiceFilter(", filtersets_source)
        self.assertIn("rectification_measures__overlap=value", filtersets_source)
        self.assertIn("rectification_measures = tables.Column(", tables_source)
        self.assertIn("rectification_measures = serializers.ListField(", serializers_source)

        power_edit_section = edit_template.split('id="power-supplementary-info"', 1)[1].split('id="fault-review-info"', 1)[0]
        for field_name in field_names:
            self.assertIn(f"{{% render_field form.{field_name} %}}", power_edit_section)

        power_detail_section = detail_template.split("{% if object.is_power_fault %}", 1)[1]
        for label in ["是否整改", "整改措施", "措施描述", "整改主体", "整改进度", "计划完成时间", "实际完成时间", "整改完成情况描述"]:
            self.assertIn(label, power_detail_section)
        self.assertIn("object.rectification_measures|otnfault_choice_labels:\"rectification_measures\"", power_detail_section)
        self.assertIn("GinIndex(fields=['rectification_measures']", migration_source)


if __name__ == "__main__":
    unittest.main()
