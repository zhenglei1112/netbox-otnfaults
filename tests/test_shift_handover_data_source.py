from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = REPO_ROOT / 'netbox_otnfaults' / 'services' / 'shift_handover.py'
VIEW_PATH = REPO_ROOT / 'netbox_otnfaults' / 'handover_views.py'
URLS_PATH = REPO_ROOT / 'netbox_otnfaults' / 'urls.py'


class ShiftHandoverDataSourceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SERVICE_PATH.read_text(encoding='utf-8')

    def test_fault_query_is_permission_limited_processing_and_not_suspended(self) -> None:
        self.assertIn("OtnFault.objects.restrict(user, 'view')", self.source)
        self.assertIn('fault_status=FaultStatusChoices.PROCESSING', self.source)
        self.assertIn('is_suspended=False', self.source)
        self.assertIn("'impacts__bare_fiber_service'", self.source)
        self.assertIn("'impacts__circuit_service'", self.source)
        self.assertIn(".order_by('fault_occurrence_time', 'pk')", self.source)

    def test_fault_mapping_uses_model_timeline_order_and_business_names(self) -> None:
        expected_stage_lines = (
            "('故障起始', fault.fault_occurrence_time)",
            "('处理派发', fault.dispatch_time)",
            "('维修出发', fault.departure_time)",
            "('到达现场', fault.arrival_time)",
            "('故障恢复', fault.fault_recovery_time)",
            "stages.append(('封包完成时间', fault.closure_time))",
        )
        for line in expected_stage_lines:
            self.assertIn(line, self.source)
        self.assertIn('if fault.is_fiber_fault:', self.source)
        self.assertIn('impact.bare_fiber_service.name', self.source)
        self.assertIn('impact.circuit_service.special_line_name', self.source)
        self.assertIn('or impact.circuit_service.name', self.source)
        self.assertIn('_ordered_unique(service_names)', self.source)
        self.assertIn('latest_timeline_stage(tuple(stages))', self.source)

    def test_cutover_query_uses_pending_window_and_bare_fiber_priority(self) -> None:
        self.assertIn("CutoverTask.objects.restrict(user, 'view')", self.source)
        self.assertIn('status=CutoverStatusChoices.PENDING_IMPLEMENTATION', self.source)
        self.assertIn('planned_cutover_time__gte=now', self.source)
        self.assertIn('planned_cutover_time__lt=window_end', self.source)
        self.assertIn("'interruption_location'", self.source)
        self.assertIn("'impacts__bare_fiber_service'", self.source)
        self.assertIn("'impacts__circuit_service'", self.source)
        self.assertIn(".order_by('planned_cutover_time', 'pk')", self.source)
        self.assertIn('if bare_fiber_services:', self.source)
        self.assertIn('bare_fiber_cutovers.append(item)', self.source)
        self.assertIn('other_cutovers.append(item)', self.source)

    def test_heavy_duty_query_uses_permission_type_and_overlap_window(self) -> None:
        self.assertIn("HeavyDuty.objects.restrict(user, 'view')", self.source)
        self.assertIn('end_time__gte=now', self.source)
        self.assertIn('start_time__lt=window_end', self.source)
        self.assertIn(".order_by('start_time', 'pk')", self.source)
        self.assertIn('HeavyDutyTypeChoices.IMPORTANT', self.source)
        self.assertIn('HeavyDutyTypeChoices.COMPANY_NOTICE', self.source)
        self.assertNotIn('HeavyDutyTypeChoices.DUTY_MEMO', self.source)

    def test_generator_uses_display_name_fallback_and_formatter(self) -> None:
        self.assertIn("user.get_full_name().strip() or user.get_username()", self.source)
        self.assertIn('window_end = handover_window_end(now)', self.source)
        self.assertIn('return build_handover_text(', self.source)
        self.assertIn('shift_start=shift_start,', self.source)

    def test_overdue_cutover_check_is_permission_limited_and_stably_ordered(self) -> None:
        self.assertIn('def get_overdue_pending_cutovers(', self.source)
        self.assertIn("CutoverTask.objects.restrict(user, 'view')", self.source)
        self.assertIn('status=CutoverStatusChoices.PENDING_IMPLEMENTATION', self.source)
        self.assertIn('planned_cutover_time__lt=now', self.source)
        self.assertIn(".select_related('province', 'interruption_location_a')", self.source)
        self.assertIn(".prefetch_related('interruption_location')", self.source)
        self.assertIn(".order_by('planned_cutover_time', 'pk')", self.source)

    def test_overdue_cutover_check_maps_az_ends_and_edit_url(self) -> None:
        self.assertIn("'cutover_no': _display(cutover.cutover_no)", self.source)
        self.assertIn("strftime('%Y-%m-%d %H:%M')", self.source)
        self.assertIn("'province': _display(cutover.province)", self.source)
        self.assertIn("'cutover_type': _display(cutover.get_cutover_type_display())", self.source)
        self.assertIn("'a_end': _display(cutover.interruption_location_a)", self.source)
        self.assertIn("'z_end': _joined_display(cutover.interruption_location.all())", self.source)
        self.assertIn("'location': _display(cutover.cutover_location)", self.source)
        self.assertIn("'edit_url': reverse(", self.source)
        self.assertIn("'plugins:netbox_otnfaults:cutovertask_edit'", self.source)


class ShiftHandoverViewTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.view_source = VIEW_PATH.read_text(encoding='utf-8')
        self.url_source = URLS_PATH.read_text(encoding='utf-8')

    def test_view_parses_shift_start_and_uses_server_local_time(self) -> None:
        self.assertIn(
            'class ShiftHandoverGenerateView(LoginRequiredMixin, View):',
            self.view_source,
        )
        self.assertIn("shift_start_text = request.GET.get('shift_start', '')", self.view_source)
        self.assertIn('shift_start = parse_datetime(shift_start_text)', self.view_source)
        self.assertIn('if shift_start is None:', self.view_source)
        self.assertIn('timezone.make_aware(', self.view_source)
        self.assertIn('timezone.get_current_timezone()', self.view_source)
        self.assertIn('now = timezone.localtime()', self.view_source)
        self.assertIn('generate_shift_handover_text(', self.view_source)
        self.assertIn('user=request.user,', self.view_source)

    def test_view_returns_json_and_safe_errors(self) -> None:
        self.assertIn(
            "return JsonResponse({'error': '班次开始时间格式无效。'}, status=400)",
            self.view_source,
        )
        self.assertIn("return JsonResponse({'text': text})", self.view_source)
        self.assertIn("logger.exception('Failed to generate shift handover text')", self.view_source)
        self.assertIn("'生成交接班内容失败，请稍后重试。'", self.view_source)
        self.assertNotIn('traceback.format_exc()', self.view_source)

    def test_url_registers_plugin_owned_generate_endpoint(self) -> None:
        self.assertIn('from . import handover_views', self.url_source)
        self.assertIn("'dashboard/shift-handover/generate/'", self.url_source)
        self.assertIn(
            'handover_views.ShiftHandoverGenerateView.as_view()',
            self.url_source,
        )
        self.assertIn("name='dashboard_shift_handover_generate'", self.url_source)

    def test_overdue_cutover_check_view_uses_server_time_and_safe_errors(self) -> None:
        self.assertIn(
            'class ShiftHandoverOverdueCutoverCheckView(LoginRequiredMixin, View):',
            self.view_source,
        )
        self.assertIn('now = timezone.localtime()', self.view_source)
        self.assertIn('get_overdue_pending_cutovers(', self.view_source)
        self.assertIn('user=request.user,', self.view_source)
        self.assertIn("return JsonResponse({'cutovers': cutovers})", self.view_source)
        self.assertIn("logger.exception('Failed to check overdue cutovers')", self.view_source)
        self.assertIn('检查逾期待实施割接失败，请稍后重试。', self.view_source)

    def test_url_registers_plugin_owned_overdue_check_endpoint(self) -> None:
        self.assertIn(
            "'dashboard/shift-handover/check-overdue-cutovers/'",
            self.url_source,
        )
        self.assertIn(
            'handover_views.ShiftHandoverOverdueCutoverCheckView.as_view()',
            self.url_source,
        )
        self.assertIn(
            "name='dashboard_shift_handover_check_overdue_cutovers'",
            self.url_source,
        )


if __name__ == '__main__':
    unittest.main()
