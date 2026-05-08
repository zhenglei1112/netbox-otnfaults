from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"


class OtnFaultRecoveryModeResponseMeasuresSourceTestCase(unittest.TestCase):
    def test_model_keeps_recovery_mode_field_with_response_measure_choices(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        choices_source = source.split("class RecoveryModeChoices", 1)[1].split("class OtnFault", 1)[0]
        field_source = source.split("recovery_mode = ArrayField(", 1)[1].split("closure_time", 1)[0]

        self.assertIn("from django.contrib.postgres.fields import ArrayField", source)
        self.assertIn("from django.contrib.postgres.indexes import GinIndex", source)
        self.assertIn("EMERGENCY_GENERATION = 'emergency_generation'", choices_source)
        self.assertIn("BATTERY_POWER = 'battery_power'", choices_source)
        self.assertIn("UTILITY_POWER_RESTORED = 'utility_power_restored'", choices_source)
        self.assertIn("ONSITE_HANDLING = 'onsite_handling'", choices_source)
        self.assertIn("(EMERGENCY_GENERATION, '应急发电'", choices_source)
        self.assertIn("(BATTERY_POWER, '电池供电'", choices_source)
        self.assertIn("(UTILITY_POWER_RESTORED, '市电恢复'", choices_source)
        self.assertIn("(ONSITE_HANDLING, '现场处置'", choices_source)
        self.assertIn("base_field=models.CharField(", field_source)
        self.assertIn("verbose_name='应对措施'", field_source)
        self.assertIn("default=list", field_source)
        self.assertIn("GinIndex(fields=['recovery_mode'])", source)

    def test_forms_use_multi_select_response_measure_label(self) -> None:
        source = FORMS_PATH.read_text(encoding="utf-8-sig")
        edit_template = (REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html").read_text(encoding="utf-8-sig")

        self.assertIn("recovery_mode = forms.MultipleChoiceField(", source)
        self.assertIn("choices=RecoveryModeChoices", source)
        self.assertIn("from django.contrib.postgres.forms import SimpleArrayField", source)
        self.assertIn("recovery_mode = SimpleArrayField(", source)
        self.assertIn("label='应对措施'", source)
        self.assertIn("widget=forms.SelectMultiple()", source)
        self.assertIn("def clean_recovery_mode(self) -> list[str]:", source)
        self.assertIn("return list(value)", source)
        power_section = edit_template.split('id="power-supplementary-info"', 1)[1].split('id="fault-review-info"', 1)[0]
        pre_power_section = edit_template.split('id="power-supplementary-info"', 1)[0]

        self.assertNotIn("{% render_field form.recovery_mode %}", pre_power_section)
        self.assertIn("{% render_field form.recovery_mode %}", power_section)
        self.assertNotIn("{% render_field form.power_recovery_mode %}", edit_template)

    def test_display_filter_and_migration_use_array_values(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8-sig")
        filtersets_source = (REPO_ROOT / "netbox_otnfaults" / "filtersets.py").read_text(encoding="utf-8-sig")
        tables_source = TABLES_PATH.read_text(encoding="utf-8-sig")
        template_source = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        power_detail_section = template_source.split("{% if object.is_power_fault %}", 1)[1]
        migration_source = (
            REPO_ROOT
            / "netbox_otnfaults"
            / "migrations"
            / "0057_alter_otnfault_recovery_mode_response_measures.py"
        ).read_text(encoding="utf-8-sig")

        self.assertIn("def get_recovery_mode_display(self) -> str:", models_source)
        self.assertIn("return '、'.join(", models_source)
        self.assertIn("recovery_mode__overlap=value", filtersets_source)
        self.assertIn("verbose_name='应对措施'", tables_source)
        self.assertIn("<th scope=\"row\">应对措施</th>", template_source)
        self.assertIn("{% load otnfault_display %}", template_source)
        self.assertIn("object.recovery_mode|otnfault_choice_labels:\"recovery_mode\"", power_detail_section)
        self.assertIn("class=\"badge rounded-pill border bg-body text-body\"", power_detail_section)
        self.assertNotIn("object.get_recovery_mode_display", power_detail_section)
        self.assertNotIn("object.get_recovery_mode_color", power_detail_section)
        self.assertNotIn("object.power_recovery_mode", template_source)
        self.assertNotIn("get_power_recovery_mode_display", template_source)
        self.assertIn("string_to_array(recovery_mode, ',')", migration_source)
        using_clause = migration_source.split("TYPE varchar(40)[]", 1)[1].split("END;", 1)[0]
        self.assertNotIn("SELECT", using_clause)
        self.assertIn("UPDATE netbox_otnfaults_otnfault", migration_source)
        self.assertIn("array_remove(ARRAY[", migration_source)
        self.assertNotIn(" & ARRAY[", migration_source)
        self.assertLess(
            migration_source.index("SET NOT NULL"),
            migration_source.index("UPDATE netbox_otnfaults_otnfault"),
        )
        self.assertLess(
            migration_source.index("CREATE INDEX netbox_otnf_recovery_732470_gin"),
            migration_source.index("UPDATE netbox_otnfaults_otnfault"),
        )
        self.assertIn("DROP INDEX IF EXISTS netbox_otnf_recovery_732470_gin", migration_source)


if __name__ == "__main__":
    unittest.main()
