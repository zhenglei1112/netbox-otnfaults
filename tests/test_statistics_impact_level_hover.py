import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "statistics_dashboard.html"
)


def _css_rule(source: str, selector: str) -> str:
    start = source.index(selector)
    return source[start:].split("}", 1)[0]


class StatisticsImpactLevelHoverTestCase(unittest.TestCase):
    def test_summary_tiles_use_ring_chart_style_hover_emphasis(self) -> None:
        source = TEMPLATE_PATH.read_text(encoding="utf-8")
        base_rule = _css_rule(source, ".impact-level-block-item {")
        emphasis_selector = (
            ".impact-level-block-item:hover,\n"
            "  .impact-level-block-item:focus-visible {"
        )

        self.assertIn(emphasis_selector, source)
        emphasis_rule = _css_rule(source, emphasis_selector)

        self.assertIn("inset 0 0 0 2px transparent", base_rule)
        self.assertIn("transform: translateY(-2px) scale(1.03);", emphasis_rule)
        self.assertIn("inset 0 0 0 2px #ffffff", emphasis_rule)
        self.assertIn("0 8px 18px rgba(15, 23, 42, 0.32)", emphasis_rule)
        self.assertIn("z-index: 2;", emphasis_rule)
        self.assertNotIn("opacity:", emphasis_rule)

    def test_statistics_stylesheet_cache_version_is_incremented(self) -> None:
        source = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics_dashboard.css' %}?v=35", source)


if __name__ == "__main__":
    unittest.main()
