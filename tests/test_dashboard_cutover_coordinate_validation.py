import json
import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_ENGINE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "map_engine.js"
)


class DashboardCutoverCoordinateValidationTestCase(unittest.TestCase):
    def test_coordinate_parser_rejects_empty_and_non_numeric_values(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"function _parseMapCoordinate\(value\) \{.*?\n    \}",
            source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "dashboard map coordinate parser is missing")

        script = (
            f"{match.group(0)}\n"
            "console.log(JSON.stringify(["
            "_parseMapCoordinate(null),"
            "_parseMapCoordinate(undefined),"
            "_parseMapCoordinate(''),"
            "_parseMapCoordinate('   '),"
            "_parseMapCoordinate('not-a-number'),"
            "_parseMapCoordinate('114.5'),"
            "_parseMapCoordinate(30.25)"
            "]));"
        )
        result = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            [None, None, None, None, None, 114.5, 30.25],
        )

    def test_cutover_renderer_uses_coordinate_parser(self) -> None:
        source = MAP_ENGINE_PATH.read_text(encoding="utf-8")
        renderer = source.split("function renderCutoverMarkers", 1)[1].split(
            "function renderHeatmap", 1
        )[0]

        self.assertIn("var numericLat = _parseMapCoordinate(lat);", renderer)
        self.assertIn("var numericLng = _parseMapCoordinate(lng);", renderer)


if __name__ == "__main__":
    unittest.main()
