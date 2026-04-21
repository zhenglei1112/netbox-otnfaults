import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
APP_VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "views.py"
URLS_PATH = REPO_ROOT / "netbox_otnfaults" / "urls.py"
MAP_MODES_PATH = REPO_ROOT / "netbox_otnfaults" / "map_modes.py"
FAULT_MODE_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "modes" / "fault_mode.js"
FAULT_LEGEND_CONTROL_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "controls" / "FaultLegendControl.js"
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"
STATISTICS_MAP_MODE_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "modes" / "statistics_cable_break_mode.js"


class StatisticsCableBreakOverviewTestCase(unittest.TestCase):
    def test_backend_builds_cable_break_overview_with_required_scope_and_buckets(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("FaultStatusChoices", source)
        self.assertIn("cable_break_faults = [", source)
        self.assertIn("f.fault_category == FaultCategoryChoices.FIBER_BREAK", source)
        self.assertIn("f.fault_status != FaultStatusChoices.SUSPENDED", source)
        self.assertIn("def _compute_cable_break_overview(faults: list, now) -> dict:", source)
        self.assertIn("cable_break_overview = _compute_cable_break_overview(faults, now)", source)
        self.assertIn("'cable_break_overview': cable_break_overview", source)
        self.assertIn("'prev_cable_break_overview': prev_cable_break_overview", source)
        self.assertIn("'total_count': cb_count", source)
        self.assertIn("'total_duration': round(total_duration, 2)", source)
        self.assertIn("'long_duration_total': round(long_duration_total, 2)", source)
        self.assertIn("'long_duration_bucket_durations': long_duration_bucket_durations", source)
        self.assertIn("'avg_metrics': avg_metrics", source)
        self.assertIn("'6-8小时': 0", source)
        self.assertIn("'8-10小时': 0", source)
        self.assertIn("'10-12小时': 0", source)
        self.assertIn("'12小时以上': 0", source)

    def test_template_contains_cable_break_overview_section_and_cards(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("statistics-cable-break-overview", template)
        self.assertIn("光缆中断概览", template)
        cable_break_header = template.split('<section class="statistics-cable-break-overview', 1)[1].split('<div class="statistics-cable-break-summary-grid', 1)[0]
        self.assertIn('<h3 class="h4 mb-0 d-inline-flex align-items-center gap-2">', cable_break_header)
        self.assertIn("光缆中断概览", cable_break_header.split('id="statistics-cable-break-map-btn"', 1)[0])
        self.assertNotIn("justify-content-between", cable_break_header)
        self.assertIn('id="cable-break-total-count"', template)
        self.assertIn('id="cable-break-count-flex-list"', template)
        self.assertIn('id="cable-break-duration-flex-list"', template)
        self.assertIn('id="cable-break-long-total"', template)
        self.assertIn('id="cable-break-long-flex-list"', template)
        self.assertIn('id="cable-break-total-duration"', template)
        self.assertIn('id="cable-break-long-duration-total"', template)
        self.assertIn('id="cable-break-long-duration-flex-list"', template)
        self.assertIn('id="cable-break-overall-avg"', template)
        self.assertIn('id="cable-break-valid-avg"', template)
        self.assertIn('id="cable-break-daytime-avg"', template)
        self.assertIn('id="cable-break-nighttime-avg"', template)
        self.assertIn('id="cable-break-construction-avg"', template)
        self.assertIn('id="cable-break-noncons-avg"', template)

    def test_dashboard_script_renders_cable_break_overview(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("renderCableBreakOverview(data.cable_break_overview, data.prev_cable_break_overview);", source)
        self.assertIn("function renderCableBreakOverview(overview, prevOverview)", source)
        self.assertIn("document.getElementById('cable-break-total-count')", source)
        self.assertIn("document.getElementById('cable-break-count-flex-list')", source)
        self.assertIn("overview.long_duration_buckets || {}", source)
        self.assertIn("overview.long_duration_bucket_durations || {}", source)
        self.assertIn("document.getElementById('cable-break-long-duration-total')", source)
        self.assertIn("document.getElementById('cable-break-long-duration-flex-list')", source)
        self.assertIn("const orderedBuckets = ['6-8小时', '8-10小时', '10-12小时', '12小时以上'];", source)
        self.assertIn("longTotal += count;", source)
        self.assertIn("longTotalEl.textContent = longTotal;", source)
        self.assertIn("longDurationTotalEl.textContent = longDurationTotal.toFixed(2);", source)

    def test_cable_break_group_layout_uses_bottom_labels_and_short_separators(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('class="statistics-kpi-grouped-list', template)
        self.assertIn("function buildGroupedFlexLayout(groups)", source)
        self.assertIn('class="statistics-kpi-group"', source)
        self.assertIn("statistics-kpi-group-title", source)
        self.assertIn("statistics-kpi-group-separator", source)
        self.assertNotIn("badge bg-light text-secondary border px-2 py-1 statistics-kpi-group-title", source)
        self.assertNotIn("badge bg-light text-secondary border px-2 py-1 statistics-kpi-group-title", template)
        self.assertIn("letter-spacing: 0.08em;", css)
        self.assertIn("pointer-events: none;", css)
        self.assertIn("margin-top: 0.45rem;", css)
        self.assertIn("gap: 0.85rem;", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("flex: 1 1 0;", css)
        self.assertIn("transform: translateX(-0.5rem);", css)

    def test_cable_break_first_row_uses_asymmetric_two_card_layout(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        cable_break_section = template.split('<section class="statistics-cable-break-overview mb-4">', 1)[1].split("</section>", 1)[0]

        self.assertIn("statistics-cable-break-summary-grid", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card-primary", cable_break_section)
        self.assertIn("statistics-cable-break-summary-card-secondary", cable_break_section)
        self.assertIn("statistics-cable-break-row", cable_break_section)
        self.assertIn("statistics-cable-break-main", cable_break_section)
        self.assertNotIn("overflow-auto", cable_break_section)
        self.assertIn(".statistics-cable-break-summary-grid", css)
        self.assertIn("grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);", css)
        self.assertIn("gap: 1rem;", css)
        self.assertIn("flex: 0 0 220px;", css)

    def test_duration_and_long_duration_cards_share_one_row(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        duration_grid = template.split('id="cable-break-total-duration"', 1)[1].split('<div class="card p-0 shadow-sm statistics-cable-break-summary-card mb-4">', 1)[0]

        self.assertIn('id="cable-break-long-duration-total"', duration_grid)
        self.assertIn("statistics-cable-break-summary-grid", duration_grid)
        self.assertIn(".statistics-cable-break-summary-grid", css)

    def test_dashboard_script_preserves_metric_id_nodes_when_rendering_trends(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function renderTrendBesideMetric(metricEl, currentValue, previousValue)", source)
        self.assertNotIn("totalArrowEl.innerHTML", source)
        self.assertNotIn("longArrowEl.innerHTML", source)
        self.assertNotIn("durArrowEl.innerHTML", source)
        self.assertNotIn("avgArrowEl.innerHTML", source)

    def test_dashboard_script_renders_trend_arrows_with_diff_values(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")

        self.assertIn("function formatTrendDiff(currentVal, prevVal)", source)
        self.assertIn("const diff = cur - prev;", source)
        self.assertIn("return Number.isInteger(diff) ? String(diff) : diff.toFixed(2);", source)
        self.assertIn("${symbol}${formatTrendDiff(cur, prev)}", source)

    def test_trend_diff_renders_below_metrics_to_reduce_width(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn('class="statistics-kpi-trend-row', source)
        self.assertIn("metricTrendContainer", source)
        self.assertIn("metricTrendContainer.parentElement.insertBefore(trendEl, metricTrendContainer.nextSibling);", source)
        self.assertIn(".statistics-kpi-trend-row", css)

    def test_submetric_numbers_use_larger_font_size(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('<div class="fs-3 fw-bold ${colorClass} lh-1">', source)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-valid-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-daytime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-nighttime-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-construction-avg"', template)
        self.assertIn('class="fs-3 fw-bold text-indigo lh-1" id="cable-break-noncons-avg"', template)

    def test_duration_reason_group_label_uses_reason_top3(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        overview_source = source.split("function renderCharts")[0]

        self.assertIn("原因TOP3", overview_source)
        self.assertNotIn("一级原因", overview_source)

    def test_physical_fault_summary_always_returns_all_categories_in_required_order(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        expected_order = [
            "FaultCategoryChoices.FIBER_BREAK, '光缆中断'",
            "FaultCategoryChoices.FIBER_DEGRADATION, '光缆劣化'",
            "FaultCategoryChoices.FIBER_JITTER, '光缆抖动'",
            "FaultCategoryChoices.AC_FAULT, '空调故障'",
            "FaultCategoryChoices.POWER_FAULT, '供电故障'",
            "FaultCategoryChoices.DEVICE_FAULT, '设备故障'",
        ]

        self.assertIn("FAULT_CATEGORY_SUMMARY_ORDER", source)
        self.assertIn("def _build_fault_category_summary(", source)
        self.assertIn("category_counts: dict[str, dict[str, int | float]]", source)
        self.assertIn("'count': 0", source)
        self.assertIn("'charts': {", source)
        self.assertIn("'category': overall_category_stats", source)
        self.assertIn("'category': prev_overall_category_stats", source)
        self.assertNotIn("sorted(overall_category_stats.items(), key=lambda item: item[1]['count'], reverse=True)", source)
        self.assertNotIn("sorted(prev_overall_category_stats.items(), key=lambda item: item[1]['count'], reverse=True)", source)

        previous_index = -1
        for item in expected_order:
            current_index = source.index(item)
            self.assertGreater(current_index, previous_index)
            previous_index = current_index

    def test_physical_fault_summary_submetric_numbers_use_same_color_as_other_cards(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        overall_source = source.split("function renderOverallSummary", 1)[1].split("function formatTrendDiff", 1)[0]

        self.assertIn('buildFlexGroup(categories, "起", "故障分类", "text-indigo", prevCategories)', overall_source)
        self.assertNotIn('buildFlexGroup(categories, "起", "故障分类", "text-secondary", prevCategories)', overall_source)

    def test_cable_attribute_groups_use_fixed_source_order(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        expected_order = [
            "'自控'",
            "'第三方'",
            "'其他/未填'",
        ]

        self.assertIn("SOURCE_SUMMARY_ORDER: list[str]", source)
        self.assertIn("def _ordered_source_items(counts: dict[str, int | float])", source)
        self.assertIn("'source_counts': _ordered_source_items(source_counts)", source)
        self.assertIn("'source_duration_counts': _ordered_source_items(source_duration)", source)
        self.assertNotIn("'source_counts': _sorted_count_items(source_counts)", source)
        self.assertNotIn("'source_duration_counts': _sorted_count_items(source_duration)", source)

        order_source = source.split("SOURCE_SUMMARY_ORDER", 1)[1].split("def _sorted_count_items", 1)[0]
        previous_index = -1
        for item in expected_order:
            current_index = order_source.index(item)
            self.assertGreater(current_index, previous_index)
            previous_index = current_index

    def test_repeat_fault_metric_is_embedded_in_cable_break_count_card(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        source = JS_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        count_main = template.split('<div class="statistics-cable-break-main', 1)[1].split('id="cable-break-count-flex-list"', 1)[0]

        self.assertIn('id="card-repeat-faults"', count_main)
        self.assertIn('statistics-break-main-metrics', count_main)
        self.assertIn('statistics-break-main-metric-primary', count_main)
        self.assertIn('statistics-break-main-metric-secondary', count_main)
        self.assertIn('statistics-repeat-inline', count_main)
        self.assertIn('id="kpi-repeat-faults"', count_main)
        self.assertIn('id="kpi-repeat-faults-diff"', count_main)
        self.assertIn('statistics-repeat-value-row', count_main)
        self.assertIn('statistics-repeat-diff-row', count_main)
        self.assertIn('>重复<', count_main)
        self.assertNotIn('重复光缆故障', count_main)
        self.assertIn('class="fs-2 fw-bold text-indigo me-1 lh-1" id="kpi-repeat-faults"', count_main)
        self.assertNotIn('class="display-5 fw-bold text-indigo lh-1" id="kpi-repeat-faults"', count_main)
        self.assertNotIn('class="display-6 fw-bold text-indigo me-1 lh-1" id="kpi-repeat-faults"', count_main)
        self.assertNotIn('card p-3 shadow-sm text-start h-100 d-flex flex-column" id="card-repeat-faults"', template)
        self.assertIn("function renderCompactMetricDiff(elId, current, prev)", source)
        self.assertIn("renderCompactMetricDiff('kpi-repeat-faults-diff', kpis.repeat_faults_count, prevKpis.repeat_faults_count);", source)
        self.assertNotIn("renderDiff('kpi-repeat-faults-diff', kpis.repeat_faults_count, prevKpis.repeat_faults_count", source)
        self.assertIn(".statistics-break-main-metrics", css)
        self.assertIn(".statistics-break-main-metric-secondary", css)
        self.assertIn(".statistics-repeat-inline", css)
        self.assertIn(".statistics-repeat-value-row", css)
        self.assertIn(".statistics-repeat-diff-row", css)
        self.assertIn("min-height: 14px;", css)
        self.assertIn("padding-top: 0.95rem;", css)

    def test_histogram_reserves_headroom_for_top_labels(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        histogram_source = source.split("if (overview.histogram && chartHistogram)", 1)[1].split("function renderCharts", 1)[0]

        self.assertIn("const histogramMaxValue = Math.max", histogram_source)
        self.assertIn("grid: { top: 62", histogram_source)
        self.assertIn("max: histogramMaxValue > 0 ? Math.ceil(histogramMaxValue * 1.25) : 1", histogram_source)

    def test_reason_and_resource_pies_show_count_and_percent_labels(self) -> None:
        source = JS_PATH.read_text(encoding="utf-8")
        chart_source = source.split("function renderCharts(chartsData)", 1)[1].split("// ---------------- 渲染下钻表格", 1)[0]

        self.assertIn("function formatPieSliceLabel(params)", source)
        self.assertIn("return `${params.name}\\n${params.value}次 ${params.percent}%`;", source)
        self.assertGreaterEqual(chart_source.count("formatter: formatPieSliceLabel"), 2)
        self.assertGreaterEqual(chart_source.count("label: {"), 2)
        self.assertIn("alignTo: 'edge'", chart_source)

    def test_overview_metrics_are_clickable_detail_filters(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        source = JS_PATH.read_text(encoding="utf-8")
        views = VIEWS_PATH.read_text(encoding="utf-8")

        for detail_field in [
            "'source_group': source_group",
            "'duration_bucket': duration_bucket",
            "'is_valid_duration': duration_hours > 0.5",
            "'occurrence_period': occurrence_period",
            "'cause_group': cause_group",
        ]:
            self.assertIn(detail_field, views)

        for static_filter in [
            'data-filter-field="category" data-filter-value="光缆中断"',
            'data-filter-field="is_repeat" data-filter-value="true"',
            'data-filter-field="is_long" data-filter-value="true"',
            'data-filter-field="is_valid_duration" data-filter-value="true"',
            'data-filter-field="occurrence_period" data-filter-value="日间"',
            'data-filter-field="occurrence_period" data-filter-value="夜间"',
            'data-filter-field="cause_group" data-filter-value="施工类"',
            'data-filter-field="cause_group" data-filter-value="非施工类"',
        ]:
            self.assertIn(static_filter, template)

        self.assertIn("document.addEventListener('click', function(event)", source)
        self.assertIn("const metric = event.target.closest('.statistics-drill-metric');", source)
        self.assertIn("handleMetricFilterClick(metric);", source)
        self.assertIn("function handleMetricFilterClick(metric)", source)
        self.assertIn("function normalizeFilterValue(fieldName, value)", source)
        self.assertIn("function applyDetailFilter(item, fieldName, value)", source)
        self.assertIn("buildFlexItemCore(val, unit, name, colorClass, prevVal, filterField, name)", source)
        self.assertIn('buildFlexGroup(reasonTop3, "起", "原因TOP3", "text-indigo", prevReasonTop3, "reason")', source)
        self.assertIn('buildFlexGroup(sourceCounts, "起", "光缆属性", "text-indigo", prevSourceCounts, "source_group")', source)
        self.assertIn('buildFlexGroup(longItems, "起", "历时分布", "text-indigo", prevLongItems, "duration_bucket")', source)
        self.assertIn('buildFlexGroup(durReasonItems, "时", "原因TOP3", "text-indigo", prevDurReasonItems, "reason")', source)
        self.assertIn('buildFlexGroup(durSourceItems, "时", "光缆属性", "text-indigo", prevDurSourceItems, "source_group")', source)

    def test_statistics_cards_disable_text_selection_but_keep_tables_selectable(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn(".page-statistics .card", css)
        self.assertIn("-webkit-user-select: none;", css)
        self.assertIn("-moz-user-select: none;", css)
        self.assertIn("user-select: none;", css)
        self.assertIn(".page-statistics .table-responsive", css)
        self.assertIn("user-select: text;", css)

    def test_cable_break_map_uses_shared_queryset_scope(self) -> None:
        source = VIEWS_PATH.read_text(encoding="utf-8")

        self.assertIn("def get_cable_break_base_queryset(start_date, end_date)", source)
        self.assertIn("fault_occurrence_time__gte=start_date", source)
        self.assertIn("fault_occurrence_time__lt=end_date", source)
        self.assertIn("fault_category=FaultCategoryChoices.FIBER_BREAK", source)
        self.assertIn("exclude(fault_status=FaultStatusChoices.SUSPENDED)", source)
        self.assertIn("faults = list(get_cable_break_base_queryset(start_date, end_date))", source)
        self.assertNotIn("qs = qs_all.filter(fault_category=FaultCategoryChoices.FIBER_BREAK)", source)

    def test_statistics_cable_break_map_routes_and_context_are_declared(self) -> None:
        stats_source = VIEWS_PATH.read_text(encoding="utf-8")
        views_source = APP_VIEWS_PATH.read_text(encoding="utf-8")
        urls_source = URLS_PATH.read_text(encoding="utf-8")

        self.assertIn("'statistics_cable_break_map_url': reverse('plugins:netbox_otnfaults:statistics_cable_break_map')", stats_source)
        self.assertIn("class StatisticsCableBreakMapView(PermissionRequiredMixin, View):", views_source)
        self.assertIn("get_mode_config('statistics_cable_break')", views_source)
        self.assertIn("'map_mode': 'statistics_cable_break'", views_source)
        self.assertIn("'is_embedded_map': request.GET.get('modal') == 'true'", views_source)
        self.assertIn("'disable_3d_buildings': True", views_source)
        self.assertIn("class StatisticsCableBreakMapDataAPI(PermissionRequiredMixin, View):", views_source)
        self.assertIn("get_cable_break_base_queryset(start_date, end_date)", views_source)
        self.assertIn("skipped_count", views_source)
        self.assertIn("path('statistics/cable-break-map/', views.StatisticsCableBreakMapView.as_view(), name='statistics_cable_break_map')", urls_source)
        self.assertIn("path('statistics/cable-break-map-data/', views.StatisticsCableBreakMapDataAPI.as_view(), name='statistics_cable_break_map_data')", urls_source)

    def test_statistics_cable_break_map_mode_is_isolated_from_fault_mode_controls(self) -> None:
        map_modes = MAP_MODES_PATH.read_text(encoding="utf-8")

        self.assertIn("'statistics_cable_break': {", map_modes)
        mode_block = map_modes.split("'statistics_cable_break': {", 1)[1].split("},", 1)[0]

        self.assertIn("'title': '光缆中断故障地图'", mode_block)
        self.assertIn("'plugin_file': 'statistics_cable_break_mode.js?v=10'", mode_block)
        self.assertIn("'projection': 'mercator'", mode_block)
        self.assertIn("'services/FaultDataService.js'", mode_block)
        self.assertIn("'controls/FaultLegendControl.js'", mode_block)
        self.assertNotIn("fault_icons.js", mode_block)
        self.assertNotIn("LayerToggleControl.js", mode_block)
        self.assertNotIn("FaultStatisticsControl.js", mode_block)

    def test_statistics_cable_break_map_keeps_province_paths_and_sites_but_disables_3d_buildings(self) -> None:
        views_source = APP_VIEWS_PATH.read_text(encoding="utf-8")
        template = (REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html").read_text(encoding="utf-8")
        core_source = (REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "unified_map_core.js").read_text(encoding="utf-8")
        user_geojson_block = core_source.split("if (this.config.userGeojsonUrl)", 1)[1].split("// A. OTN", 1)[0]

        self.assertIn("'disable_3d_buildings': True", views_source)
        self.assertIn("disable3dBuildings: {{ disable_3d_buildings|yesno:\"true,false\" }}", template)
        self.assertIn("userGeojsonUrl: '{% static \"netbox_otnfaults/data/中国_省.geojson\" %}'", template)
        self.assertIn("id: \"user-geojson-fill\"", user_geojson_block)
        self.assertIn("\"fill-color\": \"#2c3e50\"", user_geojson_block)
        self.assertIn("\"fill-opacity\": 0.05", user_geojson_block)
        self.assertIn("id: \"user-geojson-line\"", user_geojson_block)
        self.assertIn("\"line-color\": \"rgba(90, 140, 190, 0.7)\"", user_geojson_block)
        self.assertIn("firstSymbolId", user_geojson_block)
        self.assertNotIn("buildingFirstSymbolId", user_geojson_block)
        self.assertIn("id: \"otn-paths-layer\"", core_source)
        self.assertIn("id: \"netbox-sites-layer\"", core_source)
        self.assertIn("if (this.config.disable3dBuildings) return;", core_source)
        self.assertNotIn("disableSharedLayers", template)
        self.assertNotIn("disableSharedLayers", core_source)

    def test_statistics_dashboard_contains_cable_break_map_modal_with_loading(self) -> None:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        source = JS_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")

        self.assertIn("window.STATISTICS_CABLE_BREAK_MAP_URL", template)
        self.assertIn("statistics-cable-break-map-btn", template)
        self.assertIn("statisticsCableBreakMapModal", template)
        self.assertIn("modal-dialog modal-xl modal-dialog-centered", template)
        self.assertNotIn("modal-fullscreen-lg-down statistics-cable-break-map-dialog", template)
        self.assertIn("mdi mdi-map-marker-radius me-1", template)
        self.assertIn('id="statisticsCableBreakMapCloseBtn" aria-label="Close"', template)
        self.assertIn("statistics-cable-break-map-iframe", template)
        self.assertIn("statistics-cable-break-map-loading", template)
        self.assertIn("打开光缆中断地图", template)
        self.assertIn("const btnCableBreakMap = document.getElementById('statistics-cable-break-map-btn');", source)
        self.assertIn("const cableBreakMapCloseBtn = document.getElementById('statisticsCableBreakMapCloseBtn');", source)
        self.assertIn("const cableBreakMapIframe = document.getElementById('statistics-cable-break-map-iframe');", source)
        self.assertIn("function openCableBreakMapModal()", source)
        self.assertIn("window.STATISTICS_CABLE_BREAK_MAP_URL", source)
        self.assertIn("modal=true&${buildTimeParams()}", source)
        self.assertIn("showCableBreakMapModalFallback()", source)
        self.assertNotIn("window.bootstrap.Modal.getOrCreateInstance", source)
        self.assertIn("function showCableBreakMapModalFallback()", source)
        self.assertIn("cableBreakMapModal.classList.add('show');", source)
        self.assertIn("cableBreakMapManualBackdrop.className = 'modal-backdrop fade show';", source)
        self.assertIn("cableBreakMapManualBackdrop.style.opacity = '0.85';", source)
        self.assertIn("cableBreakMapModal.setAttribute('aria-hidden', 'false');", source)
        self.assertIn("if (event.target === cableBreakMapModal) closeCableBreakMapModal();", source)
        self.assertIn("cableBreakMapIframe.src = 'about:blank';", source)
        self.assertIn("hideCableBreakMapModalFallback();", source)
        self.assertIn("cableBreakMapIframe.addEventListener('load'", source)
        self.assertIn("statistics-cable-break-map-loading", css)
        self.assertIn("statistics-cable-break-map-frame-wrap", css)
        self.assertIn("height: 70vh;", css)

    def test_unified_map_preserves_embedded_map_query_params(self) -> None:
        unified_map_template = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "unified_map.html"
        template = unified_map_template.read_text(encoding="utf-8")

        self.assertIn("mapDataUrl: '{{ map_data_url|escapejs }}'", template)
        self.assertNotIn("mapDataUrl: '{{ map_data_url }}'", template)

    def test_statistics_cable_break_map_plugin_handles_iframe_and_skipped_count(self) -> None:
        self.assertTrue(STATISTICS_MAP_MODE_PATH.exists())
        source = STATISTICS_MAP_MODE_PATH.read_text(encoding="utf-8")

        self.assertIn("const StatisticsCableBreakModePlugin = {", source)
        self.assertIn("FaultDataService.convertToFeatures", source)
        self.assertIn("this._addFaultLayer();", source)
        self.assertIn("_addFaultLayer()", source)
        self.assertIn("_createTeardropIcon(fillColor)", source)
        self.assertIn("type: \"geojson\"", source)
        self.assertIn("cluster: true", source)
        self.assertIn("id: \"cable-break-faults-layer\"", source)
        self.assertIn("FAULT_STATUS_COLORS.processing", source)
        self.assertIn("FAULT_STATUS_COLORS.temporary_recovery", source)
        self.assertIn("FAULT_STATUS_COLORS.suspended", source)
        self.assertIn("FAULT_STATUS_COLORS.closed", source)
        self.assertIn("\"icon-image\": iconImageExpr", source)
        self.assertIn("map.on(\"mouseenter\", layerId", source)
        self.assertIn("map.on(\"mouseleave\", layerId", source)
        self.assertIn("_startPopupCloseTimer()", source)
        self.assertIn("this.popupCloseTimer = setTimeout", source)
        self.assertIn("this.currentPopup.remove();", source)
        self.assertIn("popupElement.addEventListener(\"mouseenter\"", source)
        self.assertIn("popupElement.addEventListener(\"mouseleave\"", source)
        self.assertIn("map.on(\"click\", layerId", source)
        self.assertNotIn("_loadStandardMarkerSymbol", source)
        self.assertNotIn("_loadFaultIcons", source)
        self.assertNotIn('new maplibregl.Marker({ color: "#dc3545" })', source)
        self.assertIn("target=\"_parent\"", source)
        self.assertIn("skipped_count", source)
        self.assertIn("class CableBreakSkippedCountControl", source)
        self.assertIn("onAdd(map)", source)
        self.assertIn("map.addControl(this.skippedCountControl, 'bottom-left');", source)
        self.assertIn("fitBounds", source)
        self.assertNotIn("alert(", source)
        self.assertIn("window.initOTNMap(StatisticsCableBreakModePlugin);", source)

    def test_statistics_cable_break_legend_shows_only_statuses_without_affecting_fault_mode(self) -> None:
        statistics_source = STATISTICS_MAP_MODE_PATH.read_text(encoding="utf-8")
        fault_mode_source = FAULT_MODE_PATH.read_text(encoding="utf-8")
        legend_source = FAULT_LEGEND_CONTROL_PATH.read_text(encoding="utf-8")

        self.assertIn("constructor(options = {})", legend_source)
        self.assertIn("this.showCategories = options.showCategories !== false;", legend_source)
        self.assertIn("this.showStatuses = options.showStatuses !== false;", legend_source)
        self.assertIn("this.showCategories ? `", legend_source)
        self.assertIn("this.showStatuses ? `", legend_source)
        self.assertIn("new FaultLegendControl({ showCategories: false, showStatuses: true })", statistics_source)
        self.assertIn("new FaultLegendControl();", fault_mode_source)


if __name__ == "__main__":
    unittest.main()
