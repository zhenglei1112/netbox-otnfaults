import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfault_edit.html"


class OtnFaultOperationsManagerDefaultsSourceTestCase(unittest.TestCase):
    def test_initial_load_applies_defaults_for_current_fault_category(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("applyOperationsManagerDefaults(", template_text)
        self.assertIn("const initialCategoryValue = categoryTS.getValue();", template_text)
        self.assertIn("applyOperationsManagerDefaults(initialCategoryValue, { preserveExisting: true });", template_text)

    def test_failed_user_resolution_preserves_existing_operations_manager_selection(self) -> None:
        template_text = TEMPLATE_PATH.read_text(encoding="utf-8-sig")

        self.assertIn("const existingValues = opsManagerTS.getValue();", template_text)
        self.assertIn("if (validUsers.length === 0) {", template_text)
        self.assertIn("opsManagerTS.setValue(existingValues);", template_text)
        self.assertNotIn("opsManagerTS.clear();\n                \n                const fetchUser", template_text)


if __name__ == "__main__":
    unittest.main()
