import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
NAVIGATION_PATH = REPO_ROOT / "netbox_otnfaults" / "navigation.py"
VIEW_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard_v2_views.py"
PLUGIN_CONFIG_PATH = REPO_ROOT / "netbox_otnfaults" / "__init__.py"
TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "dashboard_v2.html"
)
CSS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "css"
    / "dashboard_v2.css"
)
HEADER_ICON_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "img"
    / "dashboard-v2-otn-ring.svg"
)
APP_JS_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "static"
    / "netbox_otnfaults"
    / "js"
    / "dashboard_v2"
    / "app.js"
)
MAP_JS_PATH = APP_JS_PATH.with_name("map_engine.js")
STARFIELD_JS_PATH = APP_JS_PATH.with_name("starfield.js")
GALAXY_JS_PATH = APP_JS_PATH.with_name("galaxy.js")
SKY_CONTROL_JS_PATH = APP_JS_PATH.with_name("sky_control.js")
DAY_NIGHT_JS_PATH = APP_JS_PATH.with_name("day_night_layer.js")
DAY_NIGHT_CONTROL_JS_PATH = APP_JS_PATH.with_name("day_night_control.js")
DATA_SERVICE_JS_PATH = APP_JS_PATH.with_name("data_service.js")
DEBUG_PANEL_JS_PATH = APP_JS_PATH.with_name("debug_panel.js")
INFO_DRAWER_JS_PATH = APP_JS_PATH.with_name("info_drawer.js")
MAPLIBRE_ESM_PATH = APP_JS_PATH.parents[2] / "lib" / "maplibre-gl-v6.js"
MAPLIBRE_SHARED_ESM_PATH = APP_JS_PATH.parents[2] / "lib" / "maplibre-gl-shared-v6.js"
MAPLIBRE_WORKER_ESM_PATH = APP_JS_PATH.parents[2] / "lib" / "maplibre-gl-worker-v6.js"
OLD_TEMPLATE_PATH = TEMPLATE_PATH.with_name("dashboard.html")


class DashboardV2ShellTestCase(unittest.TestCase):
    def test_default_map_assets_use_the_original_local_map_service(self) -> None:
        plugin_config = PLUGIN_CONFIG_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "'local_tiles_url': '/maps/china.pmtiles'",
            plugin_config,
        )
        self.assertIn(
            "'local_glyphs_url': '/maps/fonts/{fontstack}/{range}.pbf'",
            plugin_config,
        )
        self.assertIn(
            "'otn_paths_pmtiles_url': '/maps/otn_paths.pmtiles'",
            plugin_config,
        )
        self.assertIn("'dashboard_v2_map_center': [103.0, 34.3]", plugin_config)
        self.assertIn("'dashboard_v2_map_zoom': 4.0", plugin_config)
        self.assertIn("'dashboard_v2_basemap_mode': 'protomaps'", plugin_config)
        self.assertIn(
            "'dashboard_v2_protomaps_tiles_url': '/maps/protomaps-z0-z6.pmtiles'",
            plugin_config,
        )
        self.assertIn(
            "'dashboard_v2_china_provinces_pmtiles_url': '/maps/china_provinces.pmtiles'",
            plugin_config,
        )
        self.assertNotIn("'dashboard_v2_map_pitch'", plugin_config)
        self.assertIn("'dashboard_v2_map_bearing': 0.0", plugin_config)
        self.assertNotIn("'dashboard_v2_debug'", plugin_config)

    def test_new_route_and_menu_are_parallel_to_legacy_dashboard(self) -> None:
        urls = URLS_PATH.read_text(encoding="utf-8")
        navigation = NAVIGATION_PATH.read_text(encoding="utf-8")

        self.assertIn("from . import dashboard_v2_views", urls)
        self.assertIn(
            "path('dashboard-v2/', dashboard_v2_views.DashboardV2PageView.as_view(), name='dashboard_v2')",
            urls,
        )
        self.assertIn(
            "path('dashboard-v2/data/', dashboard_v2_views.DashboardV2DataView.as_view(), name='dashboard_v2_data')",
            urls,
        )
        self.assertIn(
            "path('dashboard/', dashboard_views.DashboardPageView.as_view(), name='dashboard')",
            urls,
        )
        self.assertIn("link='plugins:netbox_otnfaults:dashboard_v2'", navigation)
        self.assertIn("link_text='态势大屏（新版）'", navigation)
        self.assertIn("link='plugins:netbox_otnfaults:dashboard'", navigation)

    def test_new_page_has_its_own_view_template_and_assets(self) -> None:
        self.assertTrue(VIEW_PATH.exists())
        self.assertTrue(TEMPLATE_PATH.exists())
        self.assertTrue(CSS_PATH.exists())
        self.assertTrue(APP_JS_PATH.exists())
        self.assertTrue(MAP_JS_PATH.exists())
        self.assertTrue(DATA_SERVICE_JS_PATH.exists())
        self.assertTrue(DEBUG_PANEL_JS_PATH.exists())
        self.assertTrue(INFO_DRAWER_JS_PATH.exists())

        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("netbox_otnfaults/css/dashboard_v2.css", template)
        self.assertIn("netbox_otnfaults/js/dashboard_v2/app.js", template)
        self.assertIn("?v=20260907-callout-content-v1", template)
        self.assertIn("app.js' %}?v=20260907-callout-content-v1", template)
        self.assertNotIn("netbox_otnfaults/css/dashboard.css", template)
        self.assertNotIn("js/dashboard/dashboard_app.js", template)
        self.assertNotIn("dashboard_data", template)
        self.assertIn("netbox_otnfaults/lib/pmtiles.js", template)
        self.assertNotIn("netbox_otnfaults/lib/maplibre-gl.js", template)

        view = VIEW_PATH.read_text(encoding="utf-8") + (VIEW_PATH.parent / "services" / "dashboard_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("from django.templatetags.static import static", view)
        self.assertIn("from django.urls import reverse", view)
        self.assertNotIn('"provinceGeoJsonUrl"', view)
        self.assertIn('"dataUrl": reverse("plugins:netbox_otnfaults:dashboard_v2_data")', view)
        self.assertIn("class DashboardV2DataView", view)
        self.assertIn("Site.objects.exclude(", view)
        self.assertIn('values("id", "name", "latitude", "longitude")', view)
        self.assertIn("fault_occurrence_time__gte=year_start", view)
        self.assertIn("fault_occurrence_time__gte=today_start", view)
        self.assertIn("fault_status=FaultStatusChoices.PROCESSING", view)
        self.assertIn("service_recovery_time__isnull=True", view)
        self.assertIn('"processing_faults": processing_faults', view)
        self.assertIn('"otnPathsPmtilesUrl": plugin_settings.get(', view)
        self.assertIn('"otn_paths_pmtiles_url", "/maps/otn_paths.pmtiles"', view)
        self.assertIn('"chinaProvincesPmtilesUrl": plugin_settings.get(', view)
        self.assertIn(
            '"dashboard_v2_china_provinces_pmtiles_url",',
            view,
        )
        self.assertIn('"/maps/china_provinces.pmtiles"', view)
        self.assertIn(
            '"useLocalBasemap": plugin_settings.get("use_local_basemap", False)',
            view,
        )
        self.assertIn('"basemapMode": plugin_settings.get(', view)
        self.assertIn('"dashboard_v2_basemap_mode", "protomaps"', view)
        self.assertIn('"protomapsTilesUrl": plugin_settings.get(', view)
        self.assertIn('"/maps/protomaps-z0-z6.pmtiles"', view)
        self.assertIn(
            '"localTilesUrl": plugin_settings.get("local_tiles_url", "/maps/china.pmtiles")',
            view,
        )
        self.assertIn(
            '"localGlyphsUrl": plugin_settings.get(',
            view,
        )
        self.assertIn(
            '"mapCenter": plugin_settings.get("dashboard_v2_map_center", [103.0, 34.3])',
            view,
        )
        self.assertIn('"mapZoom": plugin_settings.get("dashboard_v2_map_zoom", 4.0)', view)
        self.assertNotIn('"mapPitch"', view)
        self.assertIn(
            '"mapBearing": plugin_settings.get("dashboard_v2_map_bearing", 0.0)',
            view,
        )
        self.assertNotIn('"debugEnabled"', view)
        self.assertNotIn('"refreshInterval"', view)

    def test_template_keeps_title_and_exposes_full_map_shell(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("中交信通网络运行态势图", template)
        self.assertNotIn("自动化监控 · 智能播控", template)
        self.assertNotIn("◆", template)
        self.assertIn('id="dashboard-v2-header"', template)
        self.assertNotIn('id="dashboard-v2-information"', template)
        self.assertNotIn("信息显示区", template)
        self.assertNotIn("等待功能接入", template)
        self.assertIn('id="dashboard-v2-map-stage"', template)
        self.assertIn('id="dashboard-v2-map"', template)
        self.assertIn('class="dashboard-v2-map-tools"', template)
        self.assertIn('id="dashboard-v2-map-home"', template)
        self.assertIn('id="dashboard-v2-map-graticule"', template)
        self.assertIn('aria-label="恢复初始视野"', template)
        self.assertIn('aria-label="显示经纬网"', template)
        self.assertIn('aria-pressed="false"', template)
        self.assertIn('id="dashboard-v2-map-status"', template)
        self.assertIn('id="dashboard-v2-info-drawer"', template)
        self.assertIn('id="dashboard-v2-info-drawer-toggle"', template)
        self.assertIn('id="dashboard-v2-info-drawer-content"', template)
        self.assertIn('id="dashboard-v2-info-total-faults"', template)
        self.assertIn('id="dashboard-v2-info-processing-faults"', template)
        self.assertIn('id="dashboard-v2-info-today-faults"', template)
        self.assertIn('id="dashboard-v2-info-business-interruptions"', template)
        self.assertIn('id="dashboard-v2-info-fault-list"', template)
        self.assertIn('aria-expanded="false"', template)
        self.assertIn("网络信息", template)
        self.assertIn('id="dashboard-v2-debug-panel"', template)
        self.assertIn('id="dashboard-v2-debug-toggle"', template)
        self.assertIn('id="dashboard-v2-debug-content"', template)
        self.assertIn('id="dashboard-v2-debug-longitude"', template)
        self.assertIn('id="dashboard-v2-debug-latitude"', template)
        self.assertIn('id="dashboard-v2-debug-zoom"', template)
        self.assertIn('id="dashboard-v2-debug-pitch"', template)
        self.assertIn('id="dashboard-v2-debug-pitch" type="number" value="0" readonly', template)
        self.assertIn('id="dashboard-v2-debug-bearing"', template)
        self.assertIn('id="dashboard-v2-debug-bearing" type="number" value="0" readonly', template)
        self.assertIn('id="dashboard-v2-debug-apply"', template)
        self.assertIn('id="dashboard-v2-debug-reset"', template)
        self.assertIn('id="dashboard-v2-debug-fps-current"', template)
        self.assertIn('id="dashboard-v2-debug-fps-average"', template)
        self.assertIn('id="dashboard-v2-debug-fps-minimum"', template)
        self.assertIn('id="dashboard-v2-debug-data-simulation"', template)
        self.assertIn('{{ dashboard_v2_config|json_script:"dashboard-v2-config" }}', template)

    def test_stylesheet_uses_full_map_layout_and_existing_visual_tokens(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("inset: var(--header-height) 0 0;", css)
        self.assertNotIn("grid-template-columns: clamp(360px, 31%, 780px)", css)
        self.assertNotIn("#dashboard-v2-information", css)
        self.assertIn("--bg-deep: #060a14;", css)
        self.assertIn("--accent: #00d2ff;", css.lower())
        self.assertIn("'Rajdhani'", css)
        self.assertIn("'JetBrains Mono'", css)
        self.assertIn("'Noto Sans SC'", css)
        self.assertIn("#dashboard-v2-map-stage", css)
        self.assertIn("width: 100%;", css)
        self.assertIn("height: 100%;", css)
        main_styles = css.split("#dashboard-v2-main {", 1)[1].split("}", 1)[0]
        map_stage_styles = css.split("#dashboard-v2-map-stage {", 1)[1].split("}", 1)[0]
        self.assertNotIn("padding:", main_styles)
        self.assertNotIn("gap:", main_styles)
        self.assertNotIn("border:", map_stage_styles)
        self.assertNotIn("border-radius:", map_stage_styles)
        self.assertIn('id="dashboard-v2-starfield"', template)
        self.assertIn('id="dashboard-v2-galaxy"', template)
        self.assertIn('id="dashboard-v2-map-sky"', template)
        self.assertIn('id="dashboard-v2-sky-status"', template)
        self.assertIn('data-sky-mode="full"', template)
        self.assertIn('id="dashboard-v2-map-day-night"', template)
        self.assertIn('id="dashboard-v2-day-night-status"', template)
        self.assertIn('id="dashboard-v2-map-base-network"', template)
        self.assertIn('id="dashboard-v2-base-network-status"', template)
        self.assertIn('aria-pressed="true"', template)
        self.assertIn("#dashboard-v2-starfield", css)
        self.assertIn("#dashboard-v2-galaxy", css)
        self.assertIn(".dashboard-v2-map-tools", css)
        self.assertIn(".dashboard-v2-map-tool-button", css)
        self.assertIn("bottom: 12px;", css)
        self.assertIn("left: 12px;", css)
        self.assertIn("width: 24px;", css)
        self.assertIn("height: 24px;", css)
        self.assertIn('#dashboard-v2-map-graticule[aria-pressed="true"]::after', css)
        self.assertIn('#dashboard-v2-map-day-night[aria-pressed="true"]::after', css)
        self.assertIn('#dashboard-v2-map-base-network[aria-pressed="true"]::after', css)
        self.assertIn(".dashboard-v2-map-tool-status", css)
        self.assertIn('id="dashboard-v2-graticule-status"', template)
        self.assertIn("经纬度 关闭", template)
        self.assertIn("#dashboard-v2-map-graticule:hover + .dashboard-v2-map-tool-status", css)
        self.assertIn("#dashboard-v2-map-day-night:hover + .dashboard-v2-map-tool-status", css)
        self.assertIn("#dashboard-v2-map-base-network:hover + .dashboard-v2-map-tool-status", css)
        self.assertIn("font: 600 8px var(--font-ui);", css)
        self.assertIn("transition: opacity 280ms ease, visibility 0s linear 280ms;", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("align-items: center;", css)
        self.assertIn("line-height: 0;", css)
        self.assertIn("padding: 0;", css)
        self.assertNotIn(".dashboard-v2-map-tool-button:hover", css)
        self.assertNotIn(".dashboard-v2-map-tool-button:active", css)
        self.assertIn(".dashboard-v2-debug-performance", css)
        self.assertIn(".dashboard-v2-info-drawer", css)
        self.assertIn(".dashboard-v2-info-drawer.is-open", css)
        self.assertIn("repeating-linear-gradient", css)
        self.assertIn("transition: width", css)
        drawer_styles = css.split(".dashboard-v2-info-drawer {", 1)[1].split("}", 1)[0]
        self.assertIn("top: 12px;", drawer_styles)
        self.assertIn("left: 0;", drawer_styles)
        self.assertNotIn("right: 0;", drawer_styles)
        self.assertNotIn("bottom: 12px;", drawer_styles)
        self.assertIn("--drawer-rail-width: clamp(20px, 0.8vw, 26px);", drawer_styles)
        self.assertIn("height: clamp(70px, 7vh, 96px);", drawer_styles)
        self.assertIn("?v=20260907-callout-content-v1", template)
        open_drawer_styles = css.split(".dashboard-v2-info-drawer.is-open {", 1)[1].split("}", 1)[0]
        fault_list_styles = css.split(".dashboard-v2-info-fault-list {", 1)[1].split("}", 1)[0]
        fault_card_styles = css.split(".dashboard-v2-fault-card {", 1)[1].split("}", 1)[0]
        self.assertIn("height: auto;", open_drawer_styles)
        self.assertIn("flex: 0 0 auto;", fault_list_styles)
        self.assertNotIn("height: 100%;", fault_card_styles)

    def test_header_uses_a_compact_left_brand_navigation_layout(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertTrue(HEADER_ICON_PATH.exists())
        self.assertIn("dashboard-v2-otn-ring.svg", template)
        self.assertIn('class="dashboard-v2-brand-icon"', template)
        self.assertIn("--header-height: 46px;", css)
        self.assertIn("grid-template-columns: auto minmax(0, 1fr) auto;", css)
        self.assertIn("grid-column: 1;", css)
        self.assertIn("justify-self: end;", css)
        self.assertIn("border-top: 3px solid #31465a;", css)
        self.assertIn(".dashboard-v2-brand-icon", css)
        self.assertNotIn(".dashboard-v2-heading p", css)

    def test_map_module_is_isolated_and_initializes_a_local_basemap_globe(self) -> None:
        self.assertTrue(MAP_JS_PATH.exists())
        source = (MAP_JS_PATH.read_text(encoding="utf-8") + MAP_JS_PATH.with_name("fault_overlays.js").read_text(encoding="utf-8"))

        self.assertIn("export async function initializeDashboardV2Map", source)
        self.assertIn("type: 'globe'", source)
        self.assertIn("alidade_smooth_dark_local.json", source)
        self.assertIn("localTilesUrl = config.localTilesUrl || '/maps/china.pmtiles'", source)
        self.assertIn("config.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf'", source)
        self.assertIn("china_local", source)
        self.assertIn("protomaps_z0_z6", source)
        self.assertIn("config.otnPathsPmtilesUrl || '/maps/otn_paths.pmtiles'", source)
        self.assertIn("config.chinaProvincesPmtilesUrl || '/maps/china_provinces.pmtiles'", source)
        self.assertIn("'source-layer': 'china_provinces'", source)
        self.assertIn("id: CHINA_PROVINCES_GLOW_LAYER_ID", source)
        self.assertIn("id: CHINA_PROVINCES_MAIN_LAYER_ID", source)
        self.assertIn("'source-layer': 'otn_paths'", source)
        self.assertIn("id: OTN_PATHS_GLOW_LAYER_ID", source)
        self.assertIn("id: OTN_PATHS_MAIN_LAYER_ID", source)
        self.assertIn("id: SITES_GLOW_LAYER_ID", source)
        self.assertIn("id: SITES_CORE_LAYER_ID", source)
        self.assertIn("id: SITES_LABEL_LAYER_ID", source)
        self.assertIn("const SITE_LABEL_FONT = 'HarmonyOS Sans SC Regular'", source)
        self.assertIn("'text-font': [SITE_LABEL_FONT]", source)
        self.assertIn("'text-allow-overlap': false", source)
        self.assertIn("'text-ignore-placement': false", source)
        self.assertIn("config.localGlyphsUrl || '/maps/fonts/{fontstack}/{range}.pbf'", source)
        self.assertIn("export function renderDashboardV2Sites", source)
        self.assertIn("new maplibregl.Marker({", source)
        self.assertIn("'source-layer': 'earth'", source)
        self.assertIn("'source-layer': 'boundaries'", source)
        self.assertIn("'source-layer': 'roads'", source)
        self.assertIn("id: 'landuse_base'", source)
        self.assertIn("id: 'water'", source)
        self.assertIn("id: 'boundary'", source)
        self.assertNotIn("id: 'place_label'", source)
        self.assertNotIn("'text-font': ['Open Sans Regular']", source)
        self.assertIn("'atmosphere-blend'", source)
        self.assertIn("new maplibregl.Map({", source)
        self.assertIn("container: 'dashboard-v2-map'", source)
        self.assertNotIn("dragPan.disable()", source)
        self.assertNotIn("scrollZoom.disable()", source)
        self.assertNotIn("dragRotate.disable()", source)
        self.assertNotIn("touchZoomRotate.disable()", source)
        self.assertNotIn("boxZoom.disable()", source)
        self.assertNotIn("doubleClickZoom.disable()", source)
        self.assertIn("map.on('error'", source)
        self.assertNotIn("addSource(", source)
        self.assertIn("new pmtiles.Protocol()", source)
        self.assertIn("maplibregl.addProtocol('pmtiles'", source)
        self.assertNotIn("renderSites", source)
        self.assertNotIn("renderFaultPaths", source)
        self.assertNotIn("window.MapEngine", source)
        self.assertNotIn("DashboardDataAPI", source)

    def test_app_reads_json_config_and_starts_clock_and_map(self) -> None:
        self.assertTrue(APP_JS_PATH.exists())
        source = APP_JS_PATH.read_text(encoding="utf-8")

        self.assertIn("JSON.parse(configNode.textContent)", source)
        self.assertIn("initializeDashboardV2Map(config", source)
        self.assertIn("../../lib/maplibre-gl-v6.js?v=20260831-mime-v2", source)
        self.assertNotIn("../../lib/maplibre-gl.mjs", source)
        self.assertIn("globalThis.maplibregl = maplibreglModule", source)
        self.assertIn("./map_engine.js?v=20260907-callout-content-v1", source)
        self.assertIn("./frame_rate_limiter.js?v=20260907-callout-content-v1", source)
        self.assertIn("./data_service.js?v=20260907-callout-content-v1", source)
        self.assertIn("./debug_panel.js?v=20260907-callout-content-v1", source)
        self.assertIn("./mock_fault_data.js?v=20260907-callout-content-v1", source)
        self.assertIn("./info_drawer.js?v=20260907-callout-content-v1", source)
        self.assertIn("./refresh_controller.js?v=20260907-callout-content-v1", source)
        self.assertIn("initializeDashboardV2InfoDrawer()", source)
        self.assertIn("./starfield.js?v=20260907-callout-content-v1", source)
        self.assertIn("./galaxy.js?v=20260907-callout-content-v1", source)
        self.assertIn("./sky_control.js?v=20260907-callout-content-v1", source)
        self.assertIn("./day_night_layer.js?v=20260907-callout-content-v1", source)
        self.assertIn("./day_night_control.js?v=20260907-callout-content-v1", source)
        self.assertTrue(STARFIELD_JS_PATH.exists())
        self.assertTrue(GALAXY_JS_PATH.exists())
        self.assertTrue(SKY_CONTROL_JS_PATH.exists())
        self.assertTrue(DAY_NIGHT_JS_PATH.exists())
        self.assertTrue(DAY_NIGHT_CONTROL_JS_PATH.exists())
        self.assertIn("initializeDashboardV2DebugPanel(map, {", source)
        self.assertIn("onDataSimulationChange(enabled)", source)
        self.assertIn("isDashboardV2DebugEnabled(window.location.search)", source)
        self.assertIn("fetchDashboardV2Data(config.dataUrl, options)", source)
        self.assertIn("reconcileDashboardData(latestDashboardData, data)", source)
        self.assertIn("renderDashboardV2Sites(map, data.sites)", source)
        self.assertIn("renderDashboardV2ProcessingFaults(map,", source)
        self.assertIn("initializeDashboardV2InfoDrawer()", source)
        self.assertNotIn("onActiveFaultChange(fault, index)", source)
        self.assertNotIn("setDashboardV2ActiveProcessingFault", source)
        self.assertIn("infoDrawer?.render(simulatedData)", source)
        self.assertIn("infoDrawer?.render(latestDashboardData)", source)
        self.assertIn("infoDrawer?.showError({ preserveData: hasDashboardData })", source)
        self.assertIn("intervalMs: 30000", source)
        self.assertNotIn("renderFaultPaths", source)
        self.assertNotIn("reportDashboardV2DataStatus", source)
        self.assertIn("createDashboardMapRefresher", source)
        self.assertIn("startDashboardAutoRefresh", source)
        self.assertIn("setInterval(updateClock, 1000)", source)
        self.assertNotIn("dashboard_data", source)

    def test_fault_focus_uses_radar_callout_and_reduced_motion_styles(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")
        source = (MAP_JS_PATH.read_text(encoding="utf-8") + MAP_JS_PATH.with_name("fault_overlays.js").read_text(encoding="utf-8"))
        map_source = (MAP_JS_PATH.read_text(encoding="utf-8") + MAP_JS_PATH.with_name("fault_overlays.js").read_text(encoding="utf-8"))

        self.assertIn(".dashboard-v2-fault-focus-radar", css)
        self.assertIn(".dashboard-v2-fault-callout", css)
        self.assertIn(".dashboard-v2-fault-callout-warning", css)
        self.assertIn("@keyframes dashboard-v2-fault-radar-pulse", css)
        self.assertIn("const PROCESSING_FAULT_INFO_MIN_ZOOM = 3.9", source)
        self.assertIn("zoom >= PROCESSING_FAULT_INFO_MIN_ZOOM", source)
        self.assertIn("createProcessingFaultFocus(map, fault, index)", source)
        self.assertIn("map.on?.('zoom', processingFaultFocusMoveHandler)", source)
        self.assertIn("new globalThis.ResizeObserver", source)
        self.assertIn("scheduleProcessingFaultFocusLayout(map)", source)
        self.assertIn("--fault-callout-x", css)
        self.assertIn("--fault-leader-angle", css)
        self.assertIn(".dashboard-v2-fault-focus.is-left .dashboard-v2-fault-callout-warning", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("opacityWhenCovered: 0", map_source)
        self.assertIn("faultFocusRoute(fault)", map_source)
        self.assertIn("buildPlacementCandidates", map_source)
        self.assertIn("scorePlacement", map_source)
        self.assertNotIn("dashboard-v2-fault-focus-index", map_source)
        self.assertNotIn(".dashboard-v2-fault-focus-index", css)
        self.assertIn("networkObstructionScore", map_source)
        self.assertIn("queryRenderedFeatures", map_source)
        self.assertIn("PROCESSING_FAULT_NETWORK_CANDIDATE_LIMIT = 8", map_source)
        self.assertIn("processingFaultNetworkLayoutDirty", map_source)

    def test_legacy_template_is_not_rewritten_as_v2(self) -> None:
        legacy = OLD_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertNotIn("dashboard_v2.css", legacy)
        self.assertNotIn("js/dashboard_v2/app.js", legacy)

    def test_maplibre_esm_runtime_removes_globe_gpu_readback_probe(self) -> None:
        self.assertTrue(MAPLIBRE_ESM_PATH.exists())
        self.assertTrue(MAPLIBRE_SHARED_ESM_PATH.exists())
        self.assertTrue(MAPLIBRE_WORKER_ESM_PATH.exists())

        runtime = MAPLIBRE_ESM_PATH.read_text(encoding="utf-8")
        shared_runtime = MAPLIBRE_SHARED_ESM_PATH.read_text(encoding="utf-8")
        self.assertIn("MapLibre GL JS", runtime)
        self.assertIn("v6.6.0/LICENSE.txt", runtime)
        self.assertIn("./maplibre-gl-shared-v6.js", runtime)
        self.assertIn("maplibre-gl-worker-v6.js", runtime)
        self.assertNotIn(".mjs", runtime)
        self.assertNotIn("projectionErrorMeasurement", runtime + shared_runtime)
        self.assertNotIn("STREAM_READ", runtime + shared_runtime)


if __name__ == "__main__":
    unittest.main()
