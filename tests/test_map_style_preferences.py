import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "netbox_otnfaults" / "models.py"
FILTERSETS_PATH = REPO_ROOT / "netbox_otnfaults" / "filtersets.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
SERVICE_PATH = REPO_ROOT / "netbox_otnfaults" / "services" / "map_preferences.py"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html"
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
CORE_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "unified_map_core.js"
STYLE_SERVICE_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "services" / "MapStylePreferenceService.js"
STYLE_CONTROL_JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "controls" / "MapStylePreferenceControl.js"
MIGRATION_PATH = REPO_ROOT / "netbox_otnfaults" / "migrations" / "0054_otnmappreference.py"


class MapStylePreferenceSourceTestCase(unittest.TestCase):
    def test_model_filterset_service_and_endpoint_contract(self) -> None:
        models_source = MODELS_PATH.read_text(encoding="utf-8")
        filtersets_source = FILTERSETS_PATH.read_text(encoding="utf-8")
        urls_source = URLS_PATH.read_text(encoding="utf-8")
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        self.assertTrue(SERVICE_PATH.exists(), f"Missing file: {SERVICE_PATH}")
        service_source = SERVICE_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnMapPreference(NetBoxModel):", models_source)
        self.assertIn("related_name='otn_map_preferences'", models_source)
        self.assertIn("style_config = models.JSONField(", models_source)
        self.assertIn("schema_version = models.PositiveSmallIntegerField(default=1)", models_source)
        self.assertIn("tags = models.JSONField(default=list, blank=True)", models_source)
        self.assertIn("fields=('user', 'map_mode')", models_source)
        self.assertIn("name='unique_otn_map_preference_user_mode'", models_source)
        self.assertIn("def save(self, *args, **kwargs) -> None:", models_source)
        self.assertIn("self.tags = []", models_source)
        self.assertIn("self.custom_field_data = {}", models_source)
        self.assertIn("def get_absolute_url(self) -> str:", models_source)

        self.assertIn("class OtnMapPreferenceFilterSet(django_filters.FilterSet):", filtersets_source)
        self.assertIn("model = OtnMapPreference", filtersets_source)
        self.assertIn("fields = ('id', 'user', 'map_mode', 'schema_version')", filtersets_source)

        self.assertIn("MAP_STYLE_SCHEMA_VERSION: int = 1", service_source)
        self.assertIn("DEFAULT_MAP_STYLE_CONFIG", service_source)
        self.assertIn('"circleRadius": 3', service_source)
        self.assertIn("def normalize_map_style_config(", service_source)
        self.assertIn("def get_user_map_style_config(", service_source)
        self.assertIn("def save_user_map_style_config(", service_source)
        self.assertIn("def build_map_preference_context(", service_source)
        self.assertNotIn("update_or_create(", service_source)
        self.assertIn("preference = OtnMapPreference(", service_source)
        self.assertIn("tags=[]", service_source)
        self.assertIn("custom_field_data={}", service_source)
        self.assertIn("reverse('plugins:netbox_otnfaults:map_preferences'", service_source)

        self.assertIn("path('map/preferences/<str:map_mode>/', views.MapPreferenceView.as_view(), name='map_preferences')", urls_source)
        self.assertIn("class MapPreferenceView(PermissionRequiredMixin, View):", views_source)
        self.assertIn("get_user_map_style_config(request.user, map_mode)", views_source)
        self.assertIn("save_user_map_style_config(request.user, map_mode, raw_style_config)", views_source)
        self.assertIn("logger.exception(\"Failed to save map style preference", views_source)
        self.assertIn("return JsonResponse({'error': message}, status=500)", views_source)
        self.assertNotIn("user_id = request.GET", views_source)

    def test_map_views_template_and_assets_are_wired(self) -> None:
        views_source = VIEWS_PATH.read_text(encoding="utf-8")
        template_source = TEMPLATE_PATH.read_text(encoding="utf-8")
        modes_source = MAP_MODES_PATH.read_text(encoding="utf-8")
        core_source = CORE_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("build_map_preference_context", views_source)
        self.assertIn("**build_map_preference_context(request, 'fault')", views_source)
        self.assertIn("**build_map_preference_context(request, 'statistics_cable_break')", views_source)
        self.assertIn("**build_map_preference_context(request, map_mode)", views_source)
        self.assertIn("**build_map_preference_context(request, 'route_editor')", views_source)

        self.assertIn('mapStylePreferences: {{ map_style_preferences|default:"{}"|safe }}', template_source)
        self.assertIn("mapPreferencesUrl: '{{ map_preferences_url|escapejs }}'", template_source)
        self.assertIn("csrfToken: '{{ csrf_token|escapejs }}'", template_source)

        self.assertIn("'services/MapStylePreferenceService.js'", modes_source)
        self.assertIn("'controls/MapStylePreferenceControl.js'", modes_source)
        self.assertIn("this.mapStylePreferenceService = null;", core_source)
        self.assertIn("this._initMapStylePreferences();", core_source)
        self.assertLess(core_source.index("this._initMapStylePreferences();"), core_source.index("this._initSharedLayers();"))
        self.assertIn("new MapStylePreferenceService(this.map, this.config)", core_source)
        self.assertIn("new MapStylePreferenceControl({", core_source)
        self.assertIn("csrfToken: this.config.csrfToken", core_source)

    def test_frontend_service_and_control_cover_v1_layers_and_actions(self) -> None:
        self.assertTrue(STYLE_SERVICE_JS_PATH.exists(), f"Missing file: {STYLE_SERVICE_JS_PATH}")
        self.assertTrue(STYLE_CONTROL_JS_PATH.exists(), f"Missing file: {STYLE_CONTROL_JS_PATH}")
        service_source = STYLE_SERVICE_JS_PATH.read_text(encoding="utf-8")
        control_source = STYLE_CONTROL_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("class MapStylePreferenceService", service_source)
        self.assertIn("DEFAULT_MAP_STYLE_CONFIG", service_source)
        self.assertIn("circleRadius: 3", service_source)
        for layer_id in [
            "user-geojson-fill",
            "user-geojson-line",
            "netbox-sites-layer",
            "netbox-sites-labels",
            "otn-paths-layer",
            "otn-paths-highlight-outline",
            "otn-paths-highlight-layer",
        ]:
            self.assertIn(layer_id, service_source)
        self.assertIn("apply(config)", service_source)
        self.assertIn("resetToDefaults()", service_source)

        self.assertIn("class MapStylePreferenceControl", control_source)
        self.assertIn('this.container.style.overflow = "visible";', control_source)
        self.assertIn('input.addEventListener("input", () => {', control_source)
        self.assertIn("this.preview();", control_source)
        self.assertIn('menu.className = "view-control-menu map-style-menu card shadow bg-body p-2 border border-secondary-subtle";', control_source)
        self.assertIn("document.body.appendChild(menu);", control_source)
        self.assertNotIn("this.container.appendChild(menu);", control_source)
        self.assertIn('menu.addEventListener("click", (event) => event.stopPropagation());', control_source)
        self.assertIn("this.positionMenu();", control_source)
        self.assertIn("const buttonRect = this.container.getBoundingClientRect();", control_source)
        self.assertIn('this.menu.style.right = "auto";', control_source)
        self.assertIn('window.addEventListener("resize", this.boundPositionMenu);', control_source)
        self.assertNotIn("btn-warning", control_source)
        self.assertNotIn("rgba(28, 96", control_source)
        self.assertIn('section.appendChild(this.createVisibilityField(group.key, fieldKey, labelText));', control_source)
        self.assertIn('section.appendChild(this.createRangeField(group.key, fieldKey, labelText, attrs));', control_source)
        self.assertIn('input.type = "range";', control_source)
        self.assertIn('valueBadge.className = "map-style-range-value";', control_source)
        self.assertIn('swatch.className = "map-style-color-swatch";', control_source)
        self.assertIn('element.updateSwatch(element.value);', control_source)
        self.assertNotIn(', "number"', control_source)
        self.assertIn('actions.className = "map-style-actions";', control_source)
        self.assertIn("createActionButton", control_source)
        self.assertIn("地图样式", control_source)
        self.assertIn("恢复默认", control_source)
        self.assertIn("保存默认", control_source)
        self.assertIn("fetch(this.preferencesUrl", control_source)
        self.assertIn("X-CSRFToken", control_source)
        self.assertIn("const payload = await this.parseJsonResponse(response);", control_source)
        self.assertIn("async parseJsonResponse(response)", control_source)
        self.assertIn("constructor({ mapStylePreferenceService, preferencesUrl, csrfToken })", control_source)
        self.assertIn("this.csrfToken = csrfToken || \"\";", control_source)
        self.assertIn("return match ? decodeURIComponent(match[1]) : this.csrfToken;", control_source)
        self.assertIn("province", control_source)
        self.assertIn("sites", control_source)
        self.assertIn("paths", control_source)

    def test_migration_exists(self) -> None:
        self.assertTrue(MIGRATION_PATH.exists(), f"Missing migration: {MIGRATION_PATH}")


if __name__ == "__main__":
    unittest.main()
