from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
DETAIL_TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault.html"
MIGRATION_PATH = REPO_ROOT / "netbox_otnfaults" / "migrations" / "0058_alter_otnfault_power_data_type_provider.py"


class OtnFaultPowerDataTypeProviderSourceTestCase(unittest.TestCase):
    def test_power_data_type_choices_are_power_equipment_providers(self) -> None:
        source = MODELS_PATH.read_text(encoding="utf-8-sig")
        choices_source = source.split("class PowerDataTypeChoices", 1)[1].split("class PowerRecoveryModeChoices", 1)[0]
        field_source = source.split("power_data_type = models.CharField(", 1)[1].split("power_recovery_mode", 1)[0]

        self.assertIn("OWNED = 'owned_equipment'", choices_source)
        self.assertIn("PHASE_ONE_SUPPORTING = 'phase_one_supporting'", choices_source)
        self.assertIn("THIRD_PARTY = 'third_party_provided'", choices_source)
        self.assertIn("(OWNED, '自有设备'", choices_source)
        self.assertIn("(PHASE_ONE_SUPPORTING, '一期配套'", choices_source)
        self.assertIn("(THIRD_PARTY, '三方提供'", choices_source)
        self.assertNotIn("自建配套", choices_source)
        self.assertNotIn("外部配套", choices_source)
        self.assertIn("verbose_name='供电设备提供方'", field_source)

    def test_forms_template_and_migration_use_provider_label(self) -> None:
        forms_source = FORMS_PATH.read_text(encoding="utf-8-sig")
        template_source = DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        migration_source = MIGRATION_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("label='供电设备提供方'", forms_source)
        self.assertIn("<th scope=\"row\">供电设备提供方</th>", template_source)
        self.assertIn("verbose_name='供电设备提供方'", migration_source)
        self.assertIn("('owned_equipment', '自有设备')", migration_source)
        self.assertIn("UPDATE netbox_otnfaults_otnfault", migration_source)


if __name__ == "__main__":
    unittest.main()
