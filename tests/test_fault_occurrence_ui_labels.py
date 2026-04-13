from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
POPUP_TEMPLATES_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "services"
    / "PopupTemplates.js"
)
DASHBOARD_PANELS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard"
    / "panels.js"
)
FAULT_IMPACT_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "otnfaultimpact.html"
)


class FaultOccurrenceUiLabelsTestCase(unittest.TestCase):
    def test_fault_occurrence_ui_labels_use_start_time_wording(self) -> None:
        self.assertIn("label='故障起始时间'", FORMS_PATH.read_text(encoding="utf-8"))

        tables_source = TABLES_PATH.read_text(encoding="utf-8")
        self.assertIn("verbose_name='故障起始时间'", tables_source)
        self.assertIn("('故障起始', getattr(record, 'fault_occurrence_time', None))", tables_source)
        self.assertNotIn("verbose_name='故障中断时间'", tables_source)

        models_source = MODELS_PATH.read_text(encoding="utf-8")
        self.assertIn("verbose_name='故障起始时间'", models_source)
        self.assertIn("labels = ['故障起始', '处理派发', '维修出发', '到达现场', '故障恢复']", models_source)

        popup_source = POPUP_TEMPLATES_PATH.read_text(encoding="utf-8")
        self.assertIn('<span class="popup-label">起始</span>', popup_source)
        self.assertNotIn('<span class="popup-label">中断</span>', popup_source)

        dashboard_source = DASHBOARD_PANELS_PATH.read_text(encoding="utf-8")
        self.assertIn("focus-label\">起始</span>", dashboard_source)
        self.assertIn("{ label: '故障起始', time: fault.occurrence_time, required: true }", dashboard_source)
        self.assertNotIn("focus-label\">发生</span>", dashboard_source)
        self.assertNotIn("{ label: '故障发现', time: fault.occurrence_time, required: true }", dashboard_source)

    def test_business_fault_time_label_remains_unchanged(self) -> None:
        self.assertIn("label='业务故障时间'", FORMS_PATH.read_text(encoding='utf-8'))
        self.assertIn("verbose_name='业务故障时间'", TABLES_PATH.read_text(encoding='utf-8'))
        self.assertIn("verbose_name='业务故障时间'", MODELS_PATH.read_text(encoding='utf-8'))
        self.assertIn(
            "<th scope=\"row\">业务故障时间</th>",
            FAULT_IMPACT_TEMPLATE_PATH.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
