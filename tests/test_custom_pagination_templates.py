import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults"

DETAIL_TEMPLATE_SCOPES = {
    "otnfault.html": ("impacts-table-container", "site-faults-table-container"),
    "cutovertask.html": ("impacts-table-container",),
    "barefiberservice.html": ("fault-impacts-table-container",),
    "circuitservice.html": ("fault-impacts-table-container",),
    "heavyduty.html": (
        "sites-table-container",
        "circuits-table-container",
        "bare-fibers-table-container",
    ),
    "otnpathgroup.html": ("paths-table-container", "sites-table-container"),
}

LIST_TEMPLATES = (
    "barefiberservice_list.html",
    "circuitservice_list.html",
    "heavyduty_list.html",
)


def _read_template(name: str) -> str:
    return (TEMPLATE_ROOT / name).read_text(encoding="utf-8-sig")


class CustomPaginationTemplateTestCase(unittest.TestCase):
    def test_detail_tables_hide_default_pagination_with_compatible_selectors(self) -> None:
        for template_name, scopes in DETAIL_TEMPLATE_SCOPES.items():
            with self.subTest(template=template_name):
                template_text = _read_template(template_name)

                for scope in scopes:
                    self.assertIn(f".{scope} ul.pagination", template_text)
                    self.assertIn(f".{scope} .pagination", template_text)

                self.assertIn(
                    "card-footer d-flex justify-content-between align-items-center noprint",
                    template_text,
                )

    def test_object_lists_hide_default_pagination_and_keep_custom_footer(self) -> None:
        selectors = (
            ".table-container ul.pagination",
            ".table-container .pagination",
            ".table-responsive ul.pagination",
            ".table-responsive .pagination",
        )

        for template_name in LIST_TEMPLATES:
            with self.subTest(template=template_name):
                template_text = _read_template(template_name)

                for selector in selectors:
                    self.assertIn(selector, template_text)

                self.assertIn("custom-pagination", template_text)

    def test_cutover_detail_loads_pagination_css_through_head_block(self) -> None:
        template_text = _read_template("cutovertask.html")

        self.assertIn("{% block head %}", template_text)
        self.assertIn("{{ block.super }}", template_text)
        self.assertNotIn("{% block extra_styles %}", template_text)

    def test_path_group_pagination_has_no_stray_character_before_per_page(self) -> None:
        template_text = _read_template("otnpathgroup.html")

        expected_footer_transition = (
            "共 {{ paths_table.paginator.count }}</span>\n"
            '        <div class="dropdown">'
        )
        self.assertIn(expected_footer_transition, template_text)


if __name__ == "__main__":
    unittest.main()
