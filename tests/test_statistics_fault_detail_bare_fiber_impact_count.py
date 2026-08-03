import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "statistics_dashboard.html"
)
JS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "statistics_dashboard.js"
)


class StatisticsFaultDetailBareFiberImpactCountTestCase(unittest.TestCase):
    def test_backend_annotates_interrupted_distinct_bare_fiber_services(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("def _annotate_bare_fiber_impact_count(", source)
        helper_source = source.split(
            "def _annotate_bare_fiber_impact_count(", 1
        )[1].split("\n\n\ndef _get_impact_level_display", 1)[0]
        details_source = source.split("class FaultStatisticsDetailsAPI", 1)[1].split(
            "\n\nclass FaultStatisticsServiceDetailsAPI", 1
        )[0]
        self.assertIn("Count(", helper_source)
        self.assertIn("'impacts__bare_fiber_service'", helper_source)
        self.assertIn(
            "impacts__service_type=ServiceTypeChoices.BARE_FIBER", helper_source
        )
        self.assertIn(
            "impacts__business_impact=BusinessImpactChoices.INTERRUPTED",
            helper_source,
        )
        self.assertIn("impacts__bare_fiber_service__isnull=False", helper_source)
        self.assertIn("distinct=True", helper_source)
        self.assertGreaterEqual(
            details_source.count("_annotate_bare_fiber_impact_count("), 2
        )
        self.assertGreaterEqual(
            details_source.count("'bare_fiber_impact_count':"), 2
        )

    def test_physical_detail_tables_include_bare_fiber_impact_column(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertEqual(template.count("<th>裸纤业务中断</th>"), 2)
        self.assertEqual(template.count('colspan="12"'), 2)
        self.assertEqual(
            len(
                re.findall(
                    r"<th>站点 \(A -> Z\)</th>\s*"
                    r"<th>裸纤业务中断</th>\s*<th>标签</th>",
                    template,
                )
            ),
            2,
        )

    def test_frontend_formats_bare_fiber_impact_count(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function formatBareFiberImpactCount(value)", source)
        self.assertIn("return count > 0 ? String(count) : '-';", source)
        self.assertGreaterEqual(
            source.count(
                "formatBareFiberImpactCount(item.bare_fiber_impact_count)"
            ),
            2,
        )

        physical_rows = source.split(
            "function renderDetailsTableHtml(results)", 1
        )[1].split("function renderDetailRows(details, emptyText)", 1)[0]
        branch_rows = source.split(
            "function renderDetailRows(details, emptyText)", 1
        )[1].split("async function loadBranchDetails()", 1)[0]
        for rows_source in (physical_rows, branch_rows):
            station_position = rows_source.index(
                "<td><small>${item.site_a}${item.site_z ? "
            )
            impact_position = rows_source.index(
                "<td>${formatBareFiberImpactCount(item.bare_fiber_impact_count)}</td>"
            )
            badges_position = rows_source.index("<td>${badges}</td>")
            self.assertLess(
                station_position,
                impact_position,
                "裸纤业务中断列必须位于站点列之后",
            )
            self.assertLess(
                impact_position, badges_position, "标签列必须位于数量列之后"
            )


if __name__ == "__main__":
    unittest.main()
