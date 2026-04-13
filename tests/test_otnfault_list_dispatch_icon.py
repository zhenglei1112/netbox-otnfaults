import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"


class OtnFaultListDispatchIconSourceTestCase(unittest.TestCase):
    def test_fault_tables_use_account_icon_for_dispatch_step(self) -> None:
        tables_text = TABLES_PATH.read_text(encoding="utf-8-sig")

        self.assertGreaterEqual(tables_text.count("'mdi-account'"), 2)
        self.assertNotIn("['mdi-flash', 'mdi-account-wrench', 'mdi-truck', 'mdi-map-marker', 'mdi-restore-alert']", tables_text)
        self.assertNotIn("['mdi-flash', 'mdi-cellphone', 'mdi-truck', 'mdi-map-marker', 'mdi-restore-alert']", tables_text)
        self.assertNotIn("['mdi-flash', 'mdi-phone', 'mdi-truck', 'mdi-map-marker', 'mdi-restore-alert']", tables_text)
        self.assertNotIn("['mdi-flash', 'mdi-refresh', 'mdi-truck', 'mdi-map-marker', 'mdi-restore-alert']", tables_text)


if __name__ == "__main__":
    unittest.main()
