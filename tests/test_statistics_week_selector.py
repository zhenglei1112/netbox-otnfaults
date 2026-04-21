from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "statistics_dashboard.html"
VIEWS_PATH = REPO_ROOT / "netbox_otnfaults" / "statistics_views.py"
JS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "js" / "statistics_dashboard.js"
CSS_PATH = REPO_ROOT / "netbox_otnfaults" / "static" / "netbox_otnfaults" / "css" / "statistics_dashboard.css"


def test_statistics_dashboard_uses_single_calendar_date_selector() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert '<select id="filterType"' in template
    assert 'type="date" id="filterDate"' in template
    assert 'value="{{ default_date }}"' in template
    assert 'id="btn-prev-period"' in template
    assert 'id="btn-next-period"' in template
    assert 'title="上一周期"' in template
    assert 'title="下一周期"' in template
    assert '<option value="half"' in template
    assert '<option value="quarter"' in template
    assert 'id="filterYear"' not in template
    assert 'id="filterMonth"' not in template
    assert 'id="filterWeek"' not in template


def test_statistics_page_context_provides_default_calendar_date() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "default_date: date" in source
    assert "'default_date': default_date.isoformat()" in source
    assert "default_filter_type = 'week'" in source
    assert "default_date: date = timezone.localdate()" in source
    assert "if now.day <= 7:" not in source
    assert "last_week_date = now - timedelta(days=7)" not in source
    assert "'years': years" not in source
    assert "'weeks': weeks" not in source


def test_statistics_dashboard_builds_time_params_from_selected_calendar_date() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "const inputDate = document.getElementById('filterDate');" in source
    assert "function getHalfYearPart(month)" in source
    assert "function getQuarterPart(month)" in source
    assert "function getIsoWeekParts(dateValue)" in source
    assert "const selectedDate = inputDate.value;" in source
    assert "if (type === 'year')" in source
    assert "if (type === 'half')" in source
    assert "if (type === 'quarter')" in source
    assert "if (type === 'month')" in source
    assert "if (type === 'week')" in source
    assert "filter_type=half&year=${year}&half=${getHalfYearPart(month)}" in source
    assert "filter_type=quarter&year=${year}&quarter=${getQuarterPart(month)}" in source
    assert "filter_type=week&year=${iso.year}&week=${iso.week}" in source
    assert "selYear" not in source
    assert "selMonth" not in source
    assert "inputWeek" not in source


def test_statistics_dashboard_supports_period_shortcut_shift() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "const btnPrevPeriod = document.getElementById('btn-prev-period');" in source
    assert "const btnNextPeriod = document.getElementById('btn-next-period');" in source
    assert "function shiftSelectedPeriod(direction)" in source
    assert "if (type === 'year')" in source
    assert "date.setUTCFullYear(date.getUTCFullYear() + direction);" in source
    assert "if (type === 'half')" in source
    assert "date.setUTCMonth(date.getUTCMonth() + (direction * 6));" in source
    assert "if (type === 'quarter')" in source
    assert "date.setUTCMonth(date.getUTCMonth() + (direction * 3));" in source
    assert "if (type === 'month')" in source
    assert "date.setUTCMonth(date.getUTCMonth() + direction);" in source
    assert "if (type === 'week')" in source
    assert "date.setUTCDate(date.getUTCDate() + (direction * 7));" in source
    assert "inputDate.value = formatInputDate(date);" in source
    assert "loadActiveTab();" in source
    assert "btnPrevPeriod.addEventListener('click', () => shiftSelectedPeriod(-1));" in source
    assert "btnNextPeriod.addEventListener('click', () => shiftSelectedPeriod(1));" in source


def test_statistics_dashboard_formats_period_label_by_filter_type() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "function formatStatisticsPeriodLabel(type, dateValue, period)" in source
    assert "function getHalfYearLabel(half)" in source
    assert "${formatPeriodFlag('半年统计')} ${year}年${getHalfYearLabel(half)}（${rangeStart}至${rangeEnd}）" in source
    assert "${formatPeriodFlag('季度统计')} ${year}年第${quarter}季度（${rangeStart}至${rangeEnd}）" in source
    assert "${formatPeriodFlag('年统计')} ${year}年（${rangeStart}至${rangeEnd}）" in source
    assert "${formatPeriodFlag('月统计')} ${year}年${month}月（${rangeStart}至${rangeEnd}）" in source
    assert "${formatPeriodFlag('周统计')} ${weekYear}年${weekMonth}月${weekOrdinalLabel}（${rangeStart}至${rangeEnd}）" in source
    assert "const weekOrdinalLabels = ['第一周', '第二周', '第三周', '第四周', '第五周', '第六周'];" in source
    assert "periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);" in source
    assert "数据范围:" not in source


def test_statistics_backend_supports_half_and_quarter_ranges() -> None:
    source = VIEWS_PATH.read_text(encoding="utf-8")

    assert "elif filter_type == 'half':" in source
    assert "half = int(request.GET.get('half'" in source
    assert "start_month = 1 if half == 1 else 7" in source
    assert "end_month = 7 if half == 1 else 1" in source
    assert "prev_start_year = year - 1 if half == 1 else year" in source
    assert "prev_start_month = 7 if half == 1 else 1" in source
    assert "elif filter_type == 'quarter':" in source
    assert "quarter = int(request.GET.get('quarter'" in source
    assert "start_month = (quarter - 1) * 3 + 1" in source
    assert "prev_quarter = 4 if quarter == 1 else quarter - 1" in source
    assert "prev_year = year - 1 if quarter == 1 else year" in source


def test_statistics_dashboard_renders_week_type_as_success_flag() -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert "function formatPeriodFlag(label)" in source
    assert '<span class="statistics-period-flag">${label}</span>' in source
    assert "formatPeriodFlag('周统计')" in source
    assert "formatPeriodFlag('年统计')" in source
    assert "formatPeriodFlag('半年统计')" in source
    assert "formatPeriodFlag('季度统计')" in source
    assert "formatPeriodFlag('月统计')" in source
    assert "periodEl.innerHTML = formatStatisticsPeriodLabel(selFilterType.value, inputDate.value, data.period);" in source
    assert "periodEl.textContent = formatStatisticsPeriodLabel" not in source
    assert ".statistics-period-flag" in css
    assert "color: var(--tblr-success) !important;" in css
    assert "background-color: rgba(var(--tblr-success-rgb), 0.12);" in css
    assert "border: 1px solid rgba(var(--tblr-success-rgb), 0.3);" in css


def test_statistics_dashboard_period_label_uses_api_period_end_status() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "function formatPeriodEndDate(periodEnd, fallbackDate)" in source
    assert "function formatApiDate(dateValue)" in source
    assert "return `${parts[0]}.${parts[1]}.${parts[2]}`;" in source
    assert "return formatApiDate(periodEnd);" in source
    assert "return periodEnd;" in source
    assert "const rangeStart = formatPeriodStartDate(period, weekStart);" in source
    assert "const rangeEnd = formatPeriodEndDate(period && period.end, weekEnd);" in source
    assert "（${rangeStart}至${rangeEnd}）" in source


def test_statistics_dashboard_current_period_uses_success_color() -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert "function updatePeriodLabelState(periodEl, period)" in source
    assert "if (period && period.end === '当前')" in source
    assert "periodEl.classList.add('statistics-period-label--current');" in source
    assert "periodEl.classList.remove('statistics-period-label--current');" in source
    assert ".statistics-period-label--current .statistics-period-flag" in css


def test_statistics_dashboard_future_period_uses_warning_color() -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert "else if (period && period.is_future)" in source
    assert "periodEl.classList.add('statistics-period-label--future');" in source
    assert "periodEl.classList.remove('statistics-period-label--future');" in source
    assert ".statistics-period-label--future" in css
    assert ".statistics-period-label--future .statistics-period-flag" in css


def test_statistics_dashboard_labels_cross_month_week_by_week_end_month() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "const weekLabelDate = weekEnd;" in source
    assert "const weekYear = weekLabelDate.getUTCFullYear();" in source
    assert "const weekMonth = weekLabelDate.getUTCMonth() + 1;" in source
    assert "const weekOrdinalNumber = getMonthWeekOrdinal(weekStart, weekLabelDate);" in source


def test_statistics_period_label_is_inline_with_page_title() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert '<h2 class="page-title statistics-title mb-1">' in template
    assert '<span class="statistics-title-text">故障统计</span>' in template
    assert '<span class="statistics-period-label" id="period-display">' in template
    assert '<div class="text-muted">' not in template
    assert ".statistics-period-label" in css
    assert "justify-content: center;" in css
    assert "font-size: 0.82em;" in css
    assert "vertical-align: baseline;" in css
    assert "periodEl.classList.add('bg-light', 'text-dark')" not in JS_PATH.read_text(encoding="utf-8")


def test_statistics_dashboard_renders_overall_summary_card() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    source = JS_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert "statistics-overall-card" in template
    assert "总体情况" in template
    assert 'id="kpi-overall-total"' in template
    assert "起物理故障" in template
    assert 'id="kpi-overall-categories"' in template
    assert "function renderOverallSummary(kpis, chartsData)" in source
    assert "renderOverallSummary(data.kpis, data.charts);" in source
    assert "overallTotal.textContent = kpis.total_count;" in source
    assert "const categories = (chartsData && chartsData.category) || [];" in source
    assert 'separator.textContent = "|";' in source
    assert "stat.textContent = `${item.name} ${item.value}`;" in source
    assert ".statistics-overall-categories" in css
    assert ".statistics-overall-separator" in css
