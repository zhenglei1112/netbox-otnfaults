import shutil
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FAULT_MODE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "modes"
    / "fault_mode.js"
)


class FaultModeJavaScriptSyntaxTestCase(unittest.TestCase):
    def test_fault_mode_script_has_valid_javascript_syntax(self) -> None:
        if shutil.which("node") is None:
            self.skipTest("node executable is not available")

        result = subprocess.run(
            ["node", "--check", str(FAULT_MODE_PATH)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            result.stderr or result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
