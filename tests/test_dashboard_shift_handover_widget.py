from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / 'netbox_otnfaults' / 'dashboard.py'
TEMPLATE_PATH = (
    REPO_ROOT
    / 'netbox_otnfaults'
    / 'templates'
    / 'netbox_otnfaults'
    / 'inc'
    / 'dashboard_shift_handover_widget.html'
)


class DashboardShiftHandoverWidgetTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard_source = DASHBOARD_PATH.read_text(encoding='utf-8')
        self.template_source = TEMPLATE_PATH.read_text(encoding='utf-8')

    def test_widget_is_registered_with_compact_dimensions_and_context(self) -> None:
        self.assertIn('@register_widget\nclass OtnShiftHandoverWidget(DashboardWidget):', self.dashboard_source)
        self.assertIn('default_title = "交接班"', self.dashboard_source)
        self.assertIn('width = 2', self.dashboard_source)
        self.assertIn('height = 2', self.dashboard_source)
        self.assertIn('default_shift_start(now)', self.dashboard_source)
        self.assertIn("strftime('%Y-%m-%dT%H:%M')", self.dashboard_source)
        self.assertIn('generate_url = reverse(', self.dashboard_source)
        self.assertIn(
            "'plugins:netbox_otnfaults:dashboard_shift_handover_generate'",
            self.dashboard_source,
        )
        self.assertIn('check_url = reverse(', self.dashboard_source)
        self.assertIn(
            "'plugins:netbox_otnfaults:dashboard_shift_handover_check_overdue_cutovers'",
            self.dashboard_source,
        )
        self.assertIn("'check_url': check_url", self.dashboard_source)
        self.assertIn('data-check-url="{{ check_url }}"', self.template_source)
        self.assertIn(
            "'netbox_otnfaults/inc/dashboard_shift_handover_widget.html'",
            self.dashboard_source,
        )
        self.assertIn('交接班小组件加载失败，请稍后重试。', self.dashboard_source)

    def test_template_has_one_time_input_and_two_compact_arrow_buttons(self) -> None:
        self.assertEqual(self.template_source.count('type="datetime-local"'), 1)
        self.assertIn('id="shiftHandoverStart"', self.template_source)
        self.assertIn('data-shift-direction="previous"', self.template_source)
        self.assertIn('data-shift-direction="next"', self.template_source)
        self.assertIn('aria-label="前一个班次"', self.template_source)
        self.assertIn('aria-label="后一个班次"', self.template_source)
        self.assertNotIn('>▲ 前一个班次<', self.template_source)
        self.assertNotIn('>▼ 后一个班次<', self.template_source)
        self.assertIn('id="generateShiftHandover"', self.template_source)
        self.assertIn('生成交接班内容', self.template_source)
        self.assertIn('id="shiftHandoverError"', self.template_source)

    def test_template_exposes_result_modal_and_copy_button_before_close(self) -> None:
        self.assertIn('id="shiftHandoverModal"', self.template_source)
        self.assertIn('id="shiftHandoverText"', self.template_source)
        footer = self.template_source.split('<div class="modal-footer">', 1)[1].split('</div>', 1)[0]
        self.assertLess(
            footer.index('id="copyShiftHandoverText"'),
            footer.index('data-bs-dismiss="modal"'),
        )
        self.assertIn('复制内容', footer)
        self.assertIn('关闭', footer)

    def test_script_switches_strict_adjacent_shifts_and_fetches_current_data(self) -> None:
        self.assertIn("direction === 'previous'", self.template_source)
        self.assertIn('selectedHour > 18', self.template_source)
        self.assertIn('selectedHour > 9', self.template_source)
        self.assertIn('selectedHour < 9', self.template_source)
        self.assertIn('selectedHour < 18', self.template_source)
        self.assertIn("new URLSearchParams({ shift_start: input.value })", self.template_source)
        self.assertIn('fetch(`${generateUrl}?${params.toString()}`', self.template_source)
        self.assertIn('generateButton.disabled = true', self.template_source)
        self.assertIn('showShiftHandoverModal()', self.template_source)

    def test_modal_has_a_dom_fallback_when_bootstrap_global_is_unavailable(self) -> None:
        self.assertIn('if (window.bootstrap && window.bootstrap.Modal)', self.template_source)
        self.assertIn(
            'window.bootstrap.Modal.getOrCreateInstance(modalElement).show()',
            self.template_source,
        )
        self.assertIn("modalElement.classList.add('show')", self.template_source)
        self.assertIn("manualBackdrop.className = 'modal-backdrop fade show'", self.template_source)
        self.assertIn('data-handover-action="close"', self.template_source)
        self.assertIn('hideShiftHandoverModalFallback', self.template_source)
        source_without_guarded_call = self.template_source.replace(
            'window.bootstrap.Modal.getOrCreateInstance(modalElement).show()',
            '',
        )
        self.assertNotIn(
            'bootstrap.Modal.getOrCreateInstance(modalElement).show()',
            source_without_guarded_call,
        )

    def test_copy_button_shows_short_success_or_failure_feedback(self) -> None:
        self.assertIn(
            '<i class="mdi mdi-content-copy me-1"></i>复制内容',
            self.template_source,
        )
        self.assertIn('function fallbackCopy(text)', self.template_source)
        self.assertIn("document.createElement('textarea')", self.template_source)
        self.assertIn("document.execCommand('copy')", self.template_source)
        self.assertIn('navigator.clipboard && window.isSecureContext', self.template_source)
        self.assertIn('await navigator.clipboard.writeText(text)', self.template_source)
        self.assertIn('return fallbackCopy(text)', self.template_source)
        self.assertIn('const copyLabel = copyButton.innerHTML;', self.template_source)
        self.assertIn(
            "copyButton.innerHTML = '<i class=\"mdi mdi-check me-1\"></i>已复制'",
            self.template_source,
        )
        self.assertIn('copyButton.innerHTML = copyLabel', self.template_source)
        self.assertIn("setCopyFeedback('复制失败')", self.template_source)
        self.assertIn('}, 1500)', self.template_source)

    def test_template_has_overdue_cutover_warning_modal_and_required_columns(self) -> None:
        self.assertIn('id="shiftHandoverOverdueCutoverModal"', self.template_source)
        self.assertIn('data-bs-backdrop="static"', self.template_source)
        self.assertIn('data-bs-keyboard="false"', self.template_source)
        self.assertIn('下列割接可能已经实施完成，请检查修正状态', self.template_source)
        for heading in ('割接编号', '计划割接时间', '省份', '割接类型', 'A端', 'Z端', '割接地点'):
            self.assertIn(f'<th scope="col">{heading}</th>', self.template_source)
        self.assertIn('id="shiftHandoverOverdueCutoverRows"', self.template_source)
        self.assertIn('id="skipOverdueCutoverCheck"', self.template_source)
        self.assertIn('id="recheckOverdueCutovers"', self.template_source)
        self.assertNotIn('data-overdue-action="close"', self.template_source)

    def test_overdue_cutover_rows_use_text_content_and_new_window_edit_links(self) -> None:
        self.assertIn('function renderOverdueCutovers(cutovers)', self.template_source)
        self.assertIn("link.target = '_blank'", self.template_source)
        self.assertIn("link.rel = 'noopener'", self.template_source)
        self.assertIn('link.href = cutover.edit_url', self.template_source)
        self.assertIn('link.textContent = cutover.cutover_no', self.template_source)
        self.assertIn('cell.textContent = cutover[field]', self.template_source)
        self.assertNotIn('overdueRows.innerHTML', self.template_source)

    def test_generate_flow_checks_overdue_cutovers_before_generating(self) -> None:
        self.assertIn('const checkUrl = root.dataset.checkUrl;', self.template_source)
        self.assertIn('async function fetchOverdueCutovers()', self.template_source)
        self.assertIn('const cutovers = await fetchOverdueCutovers();', self.template_source)
        self.assertIn('if (cutovers.length)', self.template_source)
        self.assertIn('showOverdueCutoverModal()', self.template_source)
        self.assertIn('await generateShiftHandoverContent()', self.template_source)
        self.assertIn("skipButton.addEventListener('click'", self.template_source)

    def test_recheck_refreshes_rows_or_starts_five_second_countdown(self) -> None:
        self.assertIn("recheckButton.addEventListener('click'", self.template_source)
        self.assertIn('renderOverdueCutovers(cutovers)', self.template_source)
        self.assertIn('startCompletedCheckCountdown()', self.template_source)
        self.assertIn('let remainingSeconds = 5;', self.template_source)
        self.assertIn('window.setInterval(', self.template_source)
        self.assertIn(
            '已经完成检查，${remainingSeconds}秒后自动进入交接班信息窗口。',
            self.template_source,
        )

    def test_check_failures_restore_the_correct_controls(self) -> None:
        self.assertIn('function resetGenerateButton()', self.template_source)
        self.assertIn('function setWarningButtonsDisabled(disabled)', self.template_source)
        self.assertIn('warningError.textContent = error.message', self.template_source)
        self.assertIn('setWarningButtonsDisabled(false)', self.template_source)
        self.assertIn('resetGenerateButton()', self.template_source)

    def test_warning_modal_has_a_dom_fallback_without_dismiss_handlers(self) -> None:
        self.assertIn('function showOverdueCutoverModal()', self.template_source)
        self.assertIn('function hideOverdueCutoverModal()', self.template_source)
        self.assertIn("overdueModalElement.classList.add('show')", self.template_source)
        self.assertIn("overdueBackdrop.className = 'modal-backdrop fade show'", self.template_source)
        self.assertNotIn("if (event.target === overdueModalElement)", self.template_source)


if __name__ == '__main__':
    unittest.main()
