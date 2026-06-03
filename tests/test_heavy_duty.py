import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
TABLES_PATH = REPO_ROOT / "netbox_otnfaults" / "tables.py"
FORMS_PATH = REPO_ROOT / "netbox_otnfaults" / "forms.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"
SERIALIZERS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "serializers.py"
API_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "views.py"
API_URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "api" / "urls.py"
DASHBOARD_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_views.py"
DASHBOARD_HTML_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "dashboard.html"
DASHBOARD_CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "dashboard.css"
DASHBOARD_JS_PANELS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "panels.js"
DASHBOARD_JS_APP_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "dashboard" / "dashboard_app.js"
HEAVY_DUTY_LIST_HTML_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "heavyduty_list.html"
HEAVY_DUTY_DETAIL_HTML_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "heavyduty.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _class_block(source: str, class_name: str) -> str:
    start = source.index(f"class {class_name}(")
    next_class = source.find("\nclass ", start + 1)
    return source[start:] if next_class == -1 else source[start:next_class]


class HeavyDutySourceCodeTestCase(unittest.TestCase):

    def test_model_definition(self) -> None:
        source = _read(MODELS_PATH)
        heavy_duty_source = _class_block(source, "HeavyDuty")
        self.assertIn("class HeavyDuty(NetBoxModel):", heavy_duty_source)
        self.assertIn("name = models.CharField(", heavy_duty_source)
        self.assertIn("start_time = models.DateTimeField(", heavy_duty_source)
        self.assertIn("end_time = models.DateTimeField(", heavy_duty_source)
        self.assertIn("description = models.TextField(", heavy_duty_source)
        self.assertIn("comments = models.TextField(", heavy_duty_source)
        self.assertIn("sites = models.ManyToManyField(", heavy_duty_source)
        self.assertIn("circuit_services = models.ManyToManyField(", heavy_duty_source)
        self.assertIn("bare_fiber_services = models.ManyToManyField(", heavy_duty_source)
        self.assertIn("def clean(self) -> None:", heavy_duty_source)
        self.assertIn("if self.end_time < self.start_time:", heavy_duty_source)

    def test_table_definition_and_column_rules(self) -> None:
        source = _read(TABLES_PATH)
        self.assertIn("class HeavyDutyTable(NetBoxTable):", source)
        self.assertIn("class HeavyDutySiteTable(NetBoxTable):", source)
        self.assertIn("from dcim.models import Site", source)
        
        # 确保 actions 永远保持为最后一列 (规范 6.5)
        normalized_source = source.replace(" ", "").replace("\n", "").replace("\r", "").replace('"', "'")
        self.assertIn("'bare_fiber_services','actions'", normalized_source)

        # 校验自定义分页样式隐藏逻辑 (规范 6.3)
        self.assertIn(".table-container ul.pagination, .table-responsive ul.pagination {", _read(HEAVY_DUTY_LIST_HTML_PATH))
        self.assertIn(".sites-table-container ul.pagination,", _read(HEAVY_DUTY_DETAIL_HTML_PATH))

    def test_forms_and_filtersets(self) -> None:
        forms_source = _read(FORMS_PATH)
        self.assertIn("class HeavyDutyForm(NetBoxModelForm):", forms_source)
        self.assertIn("class HeavyDutyFilterForm(NetBoxModelFilterSetForm):", forms_source)
        self.assertIn("class HeavyDutyImportForm(NetBoxModelImportForm):", forms_source)
        self.assertIn("class HeavyDutyBulkEditForm(NetBoxModelBulkEditForm):", forms_source)
        self.assertIn("'comments', 'tags'", forms_source)

        filter_source = _read(FILTERSETS_PATH)
        self.assertIn("class HeavyDutyFilterSet(NetBoxModelFilterSet):", filter_source)
        self.assertIn("Q(comments__icontains=value)", filter_source)

    def test_views_and_routes(self) -> None:
        views_source = _read(VIEWS_PATH)
        self.assertIn("class HeavyDutyListView", views_source)
        self.assertIn("class HeavyDutyView(generic.ObjectView):", views_source)
        self.assertIn("class HeavyDutyEditView(generic.ObjectEditView):", views_source)
        self.assertIn("class HeavyDutyDeleteView(generic.ObjectDeleteView):", views_source)

        urls_source = _read(URLS_PATH)
        self.assertIn("heavyduty", urls_source)

    def test_navigation(self) -> None:
        nav_source = _read(NAVIGATION_PATH)
        self.assertIn("link='plugins:netbox_otnfaults:heavyduty_list'", nav_source)
        self.assertIn("link_text='重要保障'", nav_source)

    def test_api_components(self) -> None:
        serializers_source = _read(SERIALIZERS_PATH)
        self.assertIn("class HeavyDutySerializer(NetBoxModelSerializer):", serializers_source)
        self.assertIn("'comments', 'tags', 'custom_fields'", serializers_source)

        api_views_source = _read(API_VIEWS_PATH)
        self.assertIn("class HeavyDutyViewSet(NetBoxModelViewSet):", api_views_source)

        api_urls_source = _read(API_URLS_PATH)
        self.assertIn("heavy-duties", api_urls_source)

    def test_dashboard_integration(self) -> None:
        db_views_source = _read(DASHBOARD_VIEWS_PATH)
        self.assertIn("start_time__lte=now", db_views_source)
        self.assertIn("end_time__gte=now", db_views_source)
        self.assertIn("'heavy_duties'", db_views_source)

        db_html_source = _read(DASHBOARD_HTML_PATH)
        self.assertIn('id="heavy-duty-banner"', db_html_source)

        db_css_source = _read(DASHBOARD_CSS_PATH)
        self.assertIn(".heavy-duty-banner", db_css_source)
        self.assertIn("banner-scroll", db_css_source)

        db_js_panels_source = _read(DASHBOARD_JS_PANELS_PATH)
        self.assertIn("updateHeavyDuty(heavyDuties)", db_js_panels_source)

        db_js_app_source = _read(DASHBOARD_JS_APP_PATH)
        self.assertIn("Panels.updateHeavyDuty(data.heavy_duties || [])", db_js_app_source)


if __name__ == "__main__":
    unittest.main()
