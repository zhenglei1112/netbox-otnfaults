import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "netbox_otnfaults" / "dashboard.py"
WIDGET_TEMPLATE_PATH = (
    REPO_ROOT
    / "netbox_otnfaults"
    / "templates"
    / "netbox_otnfaults"
    / "inc"
    / "dashboard_today_tomorrow_cutover_widget.html"
)


class DashboardTodayTomorrowCutoverWidgetTestCase(unittest.TestCase):
    def test_today_tomorrow_widget_queries_cutovers_with_prefetches(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("class OtnTodayTomorrowCutoverWidget(DashboardWidget):", source)
        self.assertIn(".select_related('province', 'line_supervisor', 'interruption_location_a')", source)
        self.assertIn(".prefetch_related('interruption_location')", source)

    def test_today_tomorrow_widget_prepares_site_information(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("site_a_name = cutover.interruption_location_a.name if cutover.interruption_location_a else '无'", source)
        self.assertIn("site_z_names = [site.name for site in cutover.interruption_location.all()]", source)
        self.assertIn("site_z_display = ', '.join(site_z_names) if site_z_names else '无'", source)
        self.assertIn("'site_a': site_a_name,", source)
        self.assertIn("'site_z': site_z_display,", source)

    def test_widget_builds_pending_cutover_reports_for_nine_and_eighteen(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("def _get_cutover_report_window(report_date: date, report_hour: int)", source)
        self.assertIn("status=CutoverStatusChoices.PENDING_IMPLEMENTATION", source)
        self.assertIn("planned_cutover_time__gte=window_start", source)
        self.assertIn("planned_cutover_time__lt=window_end", source)
        self.assertIn("_build_cutover_report(request, today, 9)", source)
        self.assertIn("_build_cutover_report(request, today, 18)", source)

    def test_widget_report_groups_bare_fiber_impacts_by_tenant_group(self) -> None:
        source = DASHBOARD_PATH.read_text(encoding="utf-8")

        self.assertIn("'impacts__bare_fiber_service__tenant_group'", source)
        self.assertIn("impact.bare_fiber_service.tenant_group", source)
        self.assertIn("impact.bare_fiber_service.name", source)
        self.assertIn("impact.circuit_service.special_line_name", source)
        self.assertIn("impact.service_site_a.name", source)
        self.assertIn("impact.service_site_z.all()", source)
        self.assertIn("group_lines.setdefault(group_name, []).append(report_line)", source)
        self.assertIn("group_cutover_ids.setdefault(group_name, set()).add(cutover.pk)", source)
        self.assertIn("'cutover_count': len(group_cutover_ids[group_name])", source)
        self.assertIn("group_text = '\\n\\n'.join(lines)", source)
        self.assertIn("f\"【{group['name']}（割接数量：{group['cutover_count']}）】\\n\"", source)
        self.assertIn("report_groups.append({", source)
        self.assertIn("'groups': report_groups,", source)
        self.assertIn(
            "build_cutover_report_title",
            source,
        )
        self.assertIn("planned_time = timezone.localtime(cutover.planned_cutover_time)", source)
        self.assertIn("item_number=len(group_lines.get(group_name, [])) + 1,", source)
        self.assertIn("report_line = build_cutover_report_line(", source)
        self.assertIn("province=province,", source)
        self.assertIn("reason=reason,", source)
        self.assertIn("service_name=service_name,", source)
        self.assertIn("site_a=site_a,", source)
        self.assertIn("site_z=site_z,", source)
        self.assertIn("cutover_type=cutover.get_cutover_type_display(),", source)
        self.assertIn("location=cutover.cutover_location or '未填写割接地点',", source)
        self.assertIn("report_title = build_cutover_report_title(window_start, window_end)", source)
        self.assertIn("f'{report_title}\\n\\n'", source)
        self.assertNotIn("影响[{service_name}：A{site_a}→Z{site_z}]", source)

    def test_template_exposes_report_buttons_modal_and_copy_action(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('data-report-hour="9"', template_source)
        self.assertIn('data-report-hour="18"', template_source)
        self.assertIn('id="cutoverReportModal"', template_source)
        self.assertIn('id="cutoverReportText"', template_source)
        self.assertIn('id="cutoverReportGroups"', template_source)
        self.assertIn("copyGroupButton.className = 'btn btn-outline-primary btn-sm copy-cutover-report-group'", template_source)
        self.assertIn('id="copyAllCutoverReports"', template_source)
        self.assertIn("navigator.clipboard.writeText", template_source)
        self.assertIn("9点通报", template_source)
        self.assertIn("18点通报", template_source)

    def test_copy_group_includes_report_title_without_group_heading(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("const reportTitleText = activeReportText.split('\\n', 1)[0];", template_source)
        self.assertIn(
            "copyReportText(`${reportTitleText}\\n\\n${group.text}`, copyGroupButton);",
            template_source,
        )

    def test_report_buttons_use_distinct_high_contrast_time_styles_and_icons(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("otn-cutover-report-button-nine", template_source)
        self.assertIn("otn-cutover-report-button-eighteen", template_source)
        self.assertIn("mdi-clock-time-nine-outline", template_source)
        self.assertIn("mdi-clock-time-six-outline", template_source)
        self.assertIn("otn-cutover-report-time-icon", template_source)
        self.assertIn("otn-cutover-report-count", template_source)
        self.assertIn("{{ nine_report.cutover_count }}项割接", template_source)
        self.assertIn("{{ eighteen_report.cutover_count }}项割接", template_source)
        self.assertIn("html[data-bs-theme=\"dark\"] .otn-cutover-report-button-nine", template_source)
        self.assertIn("html[data-bs-theme=\"dark\"] .otn-cutover-report-button-eighteen", template_source)
    def test_report_buttons_wrap_count_when_widget_is_narrow(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")
        button_block = template_source.split(".otn-cutover-report-button {", 1)[1].split("}", 1)[0]
        main_block = template_source.split(".otn-cutover-report-button-main {", 1)[1].split("}", 1)[0]
        count_block = template_source.split(".otn-cutover-report-count {", 1)[1].split("}", 1)[0]

        self.assertIn("flex-wrap: wrap;", button_block)
        self.assertIn("min-width: max-content;", main_block)
        self.assertIn("margin-left: auto;", count_block)
    def test_report_modal_places_24_hour_title_before_chinese_window(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")
        modal_header = template_source.split('<div class="modal-header', 1)[1].split('</div>', 1)[0]

        title_position = modal_header.index('id="cutoverReportModalLabel"')
        window_position = modal_header.index('id="cutoverReportWindow"')
        self.assertLess(title_position, window_position)
        self.assertIn('date:"Y年n月j日 G:i"', template_source)
        self.assertIn("reportTitle.textContent = '24小时割接预告';", template_source)
        self.assertIn("reportWindow.textContent = `（${reportWindows[hour]}）`;", template_source)
        self.assertNotIn("`${reportDates[hour]}${hour}点割接通报`", template_source)
        self.assertNotIn("`筛选范围：${reportWindows[hour]}`", template_source)
    def test_report_modal_shows_all_groups_and_keeps_close_button_on_the_far_right(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("groups.forEach((group, index) =>", template_source)
        self.assertIn("copy-cutover-report-group", template_source)
        self.assertNotIn("copyCurrentCutoverReport", template_source)
        modal_footer = template_source.split('<div class="modal-footer', 1)[1].split('</div>', 1)[0]
        copy_all_position = modal_footer.index('id="copyAllCutoverReports"')
        close_position = modal_footer.index('data-report-action="close"')
        self.assertLess(copy_all_position, close_position)
    def test_today_tomorrow_template_renders_site_information(self) -> None:
        template_source = WIDGET_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cutover-sites", template_source)
        self.assertIn(".otn-cutover-site-tag", template_source)
        self.assertIn("{{ cutover.site_a }}", template_source)
        self.assertIn("{{ cutover.site_z }}", template_source)


if __name__ == "__main__":
    unittest.main()
