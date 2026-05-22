import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "migrations"
    / "0074_drop_legacy_cutovertask_maintenance_unit.py"
)


class CutoverLegacyMigrationTestCase(unittest.TestCase):
    def test_legacy_maintenance_unit_column_is_removed_safely(self) -> None:
        migration = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn("maintenance_unit", migration)
        self.assertIn("information_schema.columns", migration)
        self.assertIn(
            "ALTER TABLE netbox_otnfaults_cutovertask DROP COLUMN maintenance_unit",
            migration,
        )
        self.assertIn("ADD COLUMN IF NOT EXISTS maintenance_unit", migration)


if __name__ == "__main__":
    unittest.main()
