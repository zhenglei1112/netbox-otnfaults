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
    return `<span class="kpi-trend ${trendClass}">vs last week ${signPrefix}${formatNumber(numericDiff)}${escapeHtml(suffix)}</span>`;
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
    setText("generated-at-display", data?.generated_at || "Auto summary");
}

function renderKPIs(data) {
    const summary = data?.summary ?? {};
    const selfBuilt = summary.self_built ?? {};
    const leased = summary.leased ?? {};

    setText("kpi-total-cnt", formatNumber(summary.total_count));
    setHtml("kpi-total-diff", renderTrendBadge(summary.diff_count, " items"));
    setText("kpi-total-dur", formatDuration(summary.total_duration));
    setHtml("kpi-total-dur-diff", renderTrendBadge(summary.diff_duration, " h"));
    setText("kpi-self-built", `${formatNumber(selfBuilt.count)} items / ${formatDuration(selfBuilt.duration)} h`);
    setText("kpi-leased", `${formatNumber(leased.count)} items / ${formatDuration(leased.duration)} h`);
}

function renderChart(dataList) {
    const chartDom = getElement("reasonsChart");
    if (!chartDom) {
        return;
    }

    const safeData = Array.isArray(dataList) ? dataList : [];
    if (safeData.length === 0) {
        renderEmptyState(chartDom, "No cause-analysis data is available for this week.");
        return;
    }

    const maxValue = Math.max(...safeData.map((item) => Number(item.value ?? 0)), 1);
    chartDom.innerHTML = safeData
        .map((item) => {
            const name = escapeHtml(item.name ?? "Unknown");
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
        renderEmptyState(container, "No province data is available for this week.");
        return;
    }

    container.innerHTML = safeProvinces
        .map((province) => `
            <article class="province-card">
                <div class="prov-name">${escapeHtml(province.province || "Unknown")}</div>
                <div class="prov-stats">
                    <div>Count: ${formatNumber(province.count)}</div>
                    <div>Duration: ${formatDuration(province.duration)} h</div>
                    <div>Main cause: ${escapeHtml(province.main_reason || "Unknown")}</div>
                    <div class="prov-path">${escapeHtml(province.paths || "No path info")}</div>
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
    setText("no-const-dur-info", `* Non-construction outage duration: ${formatDuration(noConstDur)} hours`);

    if (safeEvents.length === 0) {
        renderEmptyState(container, "No outage above 8 hours was found for this week.");
        return;
    }

    container.innerHTML = safeEvents
        .map((event) => `
            <article class="event-item">
                <div><span class="event-num">${escapeHtml(event.loc || "Unknown")}</span></div>
                <div class="prov-path">${escapeHtml(event.prov || "Unknown province")}, ${formatDuration(event.duration)} h, ${escapeHtml(event.reason || "Unknown reason")}, ${escapeHtml(event.details || "No summary")}</div>
            </article>
        `)
        .join("");
}

function renderStatusLabel(service) {
    if (service.status === "jitter") {
        return '<span class="status-tag status-yellow">!</span>Jitter';
    }

    return '<span class="status-tag status-red">X</span>Outage';
}

function renderBareFiberRow(service) {
    const serviceName = escapeHtml(service.name || "Unknown service");
    const segmentText = escapeHtml(service.segments || "No location info");

    if (service.status === "jitter") {
        return `
            <tr>
                <td class="col-service">${serviceName}</td>
                <td>${renderStatusLabel(service)}</td>
                <td>-</td>
                <td>Jitter ${formatNumber(service.jitter_cnt)} times</td>
                <td>-</td>
                <td>${segmentText}</td>
            </tr>
        `;
    }

    const jitterSuffix = Number(service.jitter_cnt ?? 0) > 0 ? ` / jitter ${formatNumber(service.jitter_cnt)} times` : "";
    return `
        <tr>
            <td class="col-service">${serviceName}</td>
            <td>${renderStatusLabel(service)}</td>
            <td>Outage ${formatNumber(service.break_cnt)} times${jitterSuffix}</td>
            <td>Blocked ${formatNumber(service.block_cnt)} times</td>
            <td>${formatDuration(service.duration)} h</td>
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
        renderTableEmptyState("No bare-fiber impact data is available for this week.");
        return;
    }

    tbody.innerHTML = safeServices.map((service) => renderBareFiberRow(service)).join("");
}

function renderPageError(error) {
    console.error("Weekly report fetch error:", error);
    renderEmptyState(getElement("reasonsChart"), "The weekly report data could not be loaded.", true);
    renderEmptyState(getElement("provinces-container"), "Province data could not be loaded.", true);
    renderEmptyState(getElement("major-events-container"), "Major events could not be loaded.", true);
    renderTableEmptyState("Bare-fiber impact data could not be loaded.", true);
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