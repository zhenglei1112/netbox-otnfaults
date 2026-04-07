/**
 * Weekly report dashboard renderer.
 */

function getElement(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const element = getElement(id);
    if (element) {
        element.textContent = String(value);
    }
}

function setHtml(id, value) {
    const element = getElement(id);
    if (element) {
        element.innerHTML = value;
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function formatNumber(value) {
    const numericValue = Number(value ?? 0);
    if (!Number.isFinite(numericValue)) {
        return "0";
    }
    return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 1 }).format(numericValue);
}

function formatDuration(value) {
    const numericValue = Number(value ?? 0);
    if (!Number.isFinite(numericValue)) {
        return "0";
    }
    return Number.isInteger(numericValue) ? String(numericValue) : numericValue.toFixed(1);
}

function renderTrendBadge(diff, suffix = "") {
    const numericDiff = Number(diff ?? 0);
    const trendClass = numericDiff > 0 ? "trend-up" : numericDiff < 0 ? "trend-down" : "";
    const signPrefix = numericDiff > 0 ? "+" : "";
    return `<span class="kpi-trend ${trendClass}">较上周 ${signPrefix}${formatNumber(numericDiff)}${escapeHtml(suffix)}</span>`;
}

function renderEmptyState(container, message, isError = false) {
    if (!container) {
        return;
    }

    const errorModifier = isError ? " empty-state--error" : "";
    container.innerHTML = `<div class="empty-state${errorModifier}">${escapeHtml(message)}</div>`;
}

function renderTableEmptyState(message, isError = false) {
    const tbody = getElement("bare-fiber-tbody");
    if (!tbody) {
        return;
    }

    const errorModifier = isError ? " empty-state--error" : "";
    tbody.innerHTML = `
        <tr>
            <td colspan="6">
                <div class="empty-state${errorModifier}">${escapeHtml(message)}</div>
            </td>
        </tr>
    `;
}

function renderHeader(data) {
    const period = data?.period ?? {};
    setText("period-display", `${period.start ?? "--"} - ${period.end ?? "--"}`);
    setText("generated-at-display", data?.generated_at || "自动汇总");
}

function renderKPIs(data) {
    const summary = data?.summary ?? {};
    const selfBuilt = summary.self_built ?? {};
    const leased = summary.leased ?? {};

    setText("kpi-total-cnt", formatNumber(summary.total_count));
    setHtml("kpi-total-diff", renderTrendBadge(summary.diff_count, " 条"));
    setText("kpi-total-dur", formatDuration(summary.total_duration));
    setHtml("kpi-total-dur-diff", renderTrendBadge(summary.diff_duration, " 小时"));
    setText("kpi-self-built", `${formatNumber(selfBuilt.count)} 条 / ${formatDuration(selfBuilt.duration)} 小时`);
    setText("kpi-leased", `${formatNumber(leased.count)} 条 / ${formatDuration(leased.duration)} 小时`);
}

function renderChart(dataList) {
    const chartDom = getElement("reasonsChart");
    if (!chartDom) {
        return;
    }

    const safeData = Array.isArray(dataList) ? dataList : [];
    if (safeData.length === 0) {
        renderEmptyState(chartDom, "本周暂无原因分析数据。");
        return;
    }

    const maxValue = Math.max(...safeData.map((item) => Number(item.value ?? 0)), 1);
    chartDom.innerHTML = safeData
        .map((item) => {
            const name = escapeHtml(item.name ?? "未知");
            const value = Number(item.value ?? 0);
            const width = Math.max((value / maxValue) * 100, 6);
            return `
                <div style="display:grid;grid-template-columns:minmax(0,160px) 1fr auto;gap:12px;align-items:center;margin-bottom:12px;">
                    <div style="font-size:13px;color:#667382;word-break:break-word;">${name}</div>
                    <div style="height:10px;background:#e9eef5;border-radius:999px;overflow:hidden;">
                        <div style="width:${width}%;height:100%;background:linear-gradient(90deg,#206bc4,#4299e1);"></div>
                    </div>
                    <div style="font-size:13px;font-weight:700;color:#182433;">${formatNumber(value)}</div>
                </div>
            `;
        })
        .join("");
}

function renderProvinces(provinces) {
    const container = getElement("provinces-container");
    if (!container) {
        return;
    }

    const safeProvinces = Array.isArray(provinces) ? provinces : [];
    if (safeProvinces.length === 0) {
        renderEmptyState(container, "本周暂无省份数据。");
        return;
    }

    container.innerHTML = safeProvinces
        .map((province) => `
            <article class="province-card">
                <div class="prov-name">${escapeHtml(province.province || "未知")}</div>
                <div class="prov-stats">
                    <div>故障次数：${formatNumber(province.count)}</div>
                    <div>累计时长：${formatDuration(province.duration)} 小时</div>
                    <div>主要原因：${escapeHtml(province.main_reason || "未知")}</div>
                    <div class="prov-path">${escapeHtml(province.paths || "暂无路径信息")}</div>
                </div>
            </article>
        `)
        .join("");
}

function renderMajorEvents(events, noConstDur) {
    const container = getElement("major-events-container");
    if (!container) {
        return;
    }

    const safeEvents = Array.isArray(events) ? events : [];
    setText("no-const-dur-info", `* 非施工中断总时长：${formatDuration(noConstDur)} 小时`);

    if (safeEvents.length === 0) {
        renderEmptyState(container, "本周暂无超过 8 小时的重大事件。");
        return;
    }

    container.innerHTML = safeEvents
        .map((event) => `
            <article class="event-item">
                <div><span class="event-num">${escapeHtml(event.loc || "未知")}</span></div>
                <div class="prov-path">${escapeHtml(event.prov || "未知省份")}，${formatDuration(event.duration)} 小时，${escapeHtml(event.reason || "未知原因")}，${escapeHtml(event.details || "暂无摘要")}</div>
            </article>
        `)
        .join("");
}

function renderStatusLabel(service) {
    if (service.status === "jitter") {
        return '<span class="status-tag status-yellow">!</span>抖动';
    }

    return '<span class="status-tag status-red">X</span>中断';
}

function renderBareFiberRow(service) {
    const serviceName = escapeHtml(service.name || "未知业务");
    const segmentText = escapeHtml(service.segments || "暂无定位信息");

    if (service.status === "jitter") {
        return `
            <tr>
                <td class="col-service">${serviceName}</td>
                <td>${renderStatusLabel(service)}</td>
                <td>-</td>
                <td>抖动 ${formatNumber(service.jitter_cnt)} 次</td>
                <td>-</td>
                <td>${segmentText}</td>
            </tr>
        `;
    }

    const jitterSuffix = Number(service.jitter_cnt ?? 0) > 0 ? ` / 抖动 ${formatNumber(service.jitter_cnt)} 次` : "";
    return `
        <tr>
            <td class="col-service">${serviceName}</td>
            <td>${renderStatusLabel(service)}</td>
            <td>中断 ${formatNumber(service.break_cnt)} 次${jitterSuffix}</td>
            <td>阻断 ${formatNumber(service.block_cnt)} 次</td>
            <td>${formatDuration(service.duration)} 小时</td>
            <td>${segmentText}</td>
        </tr>
    `;
}

function renderBareFiberTable(services) {
    const tbody = getElement("bare-fiber-tbody");
    if (!tbody) {
        return;
    }

    const safeServices = Array.isArray(services) ? services : [];
    if (safeServices.length === 0) {
        renderTableEmptyState("本周暂无裸纤业务影响数据。");
        return;
    }

    tbody.innerHTML = safeServices.map((service) => renderBareFiberRow(service)).join("");
}

function renderPageError(error) {
    console.error("Weekly report fetch error:", error);
    renderEmptyState(getElement("reasonsChart"), "每周通报数据加载失败。", true);
    renderEmptyState(getElement("provinces-container"), "省份数据加载失败。", true);
    renderEmptyState(getElement("major-events-container"), "重大事件加载失败。", true);
    renderTableEmptyState("裸纤业务影响数据加载失败。", true);
}

async function fetchReportData() {
    try {
        const response = await fetch(window.WEEKLY_REPORT_API, {
            headers: { Accept: "application/json" },
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        renderHeader(data);
        renderKPIs(data);
        renderChart(data.reasons_analysis || []);
        renderProvinces(data.top_provinces || []);
        renderMajorEvents(data.major_events || [], data.summary?.no_const_duration ?? 0);
        renderBareFiberTable(data.bare_fiber || []);
    } catch (error) {
        renderPageError(error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    void fetchReportData();
});
