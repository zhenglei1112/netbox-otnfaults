/**
 * OTN 大屏 - 数据面板渲染模块
 * 
 * 负责左翼（宏观态势）和右翼（微观详情）的数据渲染。
 */
window.Panels = (function () {
    'use strict';

    const COLORS = window.DASHBOARD_CONFIG.colors;

    /**
     * 更新左翼面板 - 宏观态势
     */
    function updateOverview(data) {
        _updateHealthGauge(data.summary);
        _updateCategoryChart(data.category_stats);
        _updateTrendChart(data.trend_24h);
        _updateProvinceList(data.province_stats);
    }

    /**
     * 更新底部 Ticker
     */
    let _lastTickerDataStr = '';
    let _lastTickerSummaryStr = '';

    function updateTicker(events) {
        const container = document.getElementById('ticker-content');
        if (!container) return;

        // 生成数据的完整标识，用于判断内容是否有任何变化
        const currentDataStr = JSON.stringify(events);
        if (_lastTickerDataStr === currentDataStr) return;
        _lastTickerDataStr = currentDataStr;

        // 生成结构摘要（仅包含故障编号），用于判断是否需要重置动画进度
        // 如果结构没变，只是个别字词（如时间、状态）变了，则不重置动画
        const currentSummaryStr = events.map(function (e) { return e.fault_number; }).join(',');
        const isStructureChanged = (currentSummaryStr !== _lastTickerSummaryStr);
        _lastTickerSummaryStr = currentSummaryStr;

        container.innerHTML = events.map(function (e) {
            const color = COLORS.alert_colors[e.severity] || '#FADB14';
            return '<span class="ticker-item">' +
                '<span class="ticker-severity-dot" style="background:' + color +
                ';box-shadow:0 0 4px ' + color + '"></span>' +
                '<span class="ticker-fault-number">' + e.fault_number + '</span>' +
                e.category + ' | ' + e.site_a + ' | ' + e.time + ' | ' + e.status +
                '</span>';
        }).join('');

        // 仅在结构发生变化（增减项目/顺序变化）时重启滚动动画
        // 这样可以根据新的宽度计算正确的时长，并确保完整展示
        if (isStructureChanged) {
            container.style.animation = 'none';
            container.offsetHeight; // reflow
            var totalWidth = container.scrollWidth;
            var duration = Math.max(30, totalWidth / 50); // 基于宽度计算
            container.style.animation = 'ticker-scroll ' + duration + 's linear infinite';
        }
    }

    /**
     * 显示焦点故障详情（右翼面板）
     */
    function showFaultFocus(fault) {
        _renderFocusCard(fault);
        _renderImpactCard(fault);
        _renderTimelineCard(fault);
    }

    /**
     * 清除焦点故障
     */
    function clearFaultFocus() {
        var el = document.getElementById('focus-content');
        if (el) el.innerHTML = '<div class="empty-state"><div class="empty-icon">⊘</div><div class="empty-text">等待故障事件...</div></div>';

        el = document.getElementById('impact-content');
        if (el) el.innerHTML = '<div class="empty-state"><div class="empty-icon">⊘</div><div class="empty-text">暂无数据</div></div>';

        el = document.getElementById('timeline-content');
        if (el) el.innerHTML = '<div class="empty-state"><div class="empty-icon">⊘</div><div class="empty-text">暂无数据</div></div>';
    }

    /**
     * 更新故障队列（右翼底部）
     */
    function updateFaultQueue(faults, activeFaultId) {
        var container = document.getElementById('fault-queue');
        if (!container) return;

        if (faults.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-text">无活跃故障</div></div>';
            return;
        }

        container.innerHTML = faults.slice(0, 10).map(function (f) {
            var color = COLORS.alert_colors[f.severity] || '#FADB14';
            var activeClass = (f.id === activeFaultId) ? ' active' : '';
            return '<div class="queue-item' + activeClass + '" data-fault-id="' + f.id + '">' +
                '<span class="queue-severity" style="background:' + color + ';box-shadow:0 0 4px ' + color + '"></span>' +
                '<div class="queue-info">' +
                '<div class="queue-number">' + f.fault_number + '</div>' +
                '<div class="queue-detail">' + (f.category_display || '') + ' · ' + (f.site_a || '') + '</div>' +
                '</div>' +
                '<span class="queue-score">' + f.priority_score + '</span>' +
                '</div>';
        }).join('');

        // 点击跳转
        container.querySelectorAll('.queue-item').forEach(function (item) {
            item.addEventListener('click', function () {
                var faultId = parseInt(this.dataset.faultId);
                var fault = faults.find(function (f) { return f.id === faultId; });
                if (fault) {
                    DirectingEngine.focusOnFault(fault);
                }
            });
        });
    }

    /* ═══ 内部渲染函数 ═══ */

    function _updateHealthGauge(summary) {
        var score = summary.health_score || 0;
        var el = document.getElementById('gauge-value');
        if (el) el.textContent = score;

        var fill = document.getElementById('gauge-fill');
        if (fill) {
            var circumference = 327; // 2 * PI * 52
            var offset = circumference - (circumference * score / 100);
            fill.style.strokeDashoffset = offset;

            // 颜色随健康度变化
            if (score >= 80) {
                fill.style.stroke = '#00D2FF';
            } else if (score >= 50) {
                fill.style.stroke = '#FADB14';
            } else if (score >= 20) {
                fill.style.stroke = '#FF8A00';
            } else {
                fill.style.stroke = '#FF1E1E';
            }
        }

        var active = document.getElementById('stat-active');
        if (active) active.textContent = summary.active_faults || 0;

        var closed = document.getElementById('stat-closed');
        if (closed) closed.textContent = summary.closed_faults || 0;

        var total = document.getElementById('stat-total');
        if (total) total.textContent = summary.total_faults || 0;
    }

    function _updateCategoryChart(stats) {
        var container = document.getElementById('category-chart');
        if (!container) return;

        var maxCount = Math.max.apply(null, stats.map(function (s) { return s.count; }).concat([1]));

        container.innerHTML = stats.map(function (s) {
            var cat = s.fault_category || 'unknown';
            var name = COLORS.category_names[cat] || cat;
            var color = COLORS.category_colors[cat] || '#555';
            var pct = (s.count / maxCount * 100).toFixed(0);

            return '<div class="bar-row">' +
                '<span class="bar-label">' + name + '</span>' +
                '<div class="bar-track"><div class="bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>' +
                '<span class="bar-count">' + s.count + '</span>' +
                '</div>';
        }).join('');
    }

    function _updateTrendChart(trendData) {
        var canvas = document.getElementById('trend-canvas');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var w = canvas.width;
        var h = canvas.height;
        var padding = { top: 10, right: 10, bottom: 20, left: 30 };
        var chartW = w - padding.left - padding.right;
        var chartH = h - padding.top - padding.bottom;

        ctx.clearRect(0, 0, w, h);

        if (!trendData || trendData.length === 0) return;

        var maxVal = Math.max.apply(null, trendData.map(function (d) { return d.count; }).concat([1]));
        var points = trendData.map(function (d, i) {
            return {
                x: padding.left + (i / (trendData.length - 1)) * chartW,
                y: padding.top + chartH - (d.count / maxVal) * chartH,
                value: d.count,
                label: d.hour
            };
        });

        // 渐变填充
        var gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
        gradient.addColorStop(0, 'rgba(0, 210, 255, 0.25)');
        gradient.addColorStop(1, 'rgba(0, 210, 255, 0)');

        ctx.beginPath();
        ctx.moveTo(points[0].x, h - padding.bottom);
        points.forEach(function (p) { ctx.lineTo(p.x, p.y); });
        ctx.lineTo(points[points.length - 1].x, h - padding.bottom);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // 线条
        ctx.beginPath();
        points.forEach(function (p, i) {
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        });
        ctx.strokeStyle = '#00D2FF';
        ctx.lineWidth = 1.5;
        ctx.shadowColor = 'rgba(0, 210, 255, 0.5)';
        ctx.shadowBlur = 4;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 数据点
        points.forEach(function (p) {
            if (p.value > 0) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                ctx.fillStyle = '#00D2FF';
                ctx.fill();
            }
        });

        // X轴标签（每6小时）
        ctx.fillStyle = 'rgba(140, 160, 180, 0.5)';
        ctx.font = '9px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        for (var i = 0; i < points.length; i += 6) {
            ctx.fillText(points[i].label, points[i].x, h - 4);
        }

        // Y轴
        ctx.textAlign = 'right';
        ctx.fillText(maxVal, padding.left - 4, padding.top + 8);
        ctx.fillText('0', padding.left - 4, h - padding.bottom);
    }

    function _updateProvinceList(stats) {
        var container = document.getElementById('province-list');
        if (!container) return;

        if (!stats || stats.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-text">无活跃故障</div></div>';
            return;
        }

        var maxCount = Math.max.apply(null, stats.map(function (s) { return s.count; }).concat([1]));

        container.innerHTML = stats.map(function (s) {
            var name = s.province__name || '未知';
            var colorIntensity = Math.min(255, Math.floor(s.count / maxCount * 200) + 55);
            var color = 'rgb(255, ' + (255 - colorIntensity) + ', ' + (255 - colorIntensity) + ')';
            return '<div class="province-row">' +
                '<span class="province-name">' + name + '</span>' +
                '<span class="province-count" style="color:' + color + '">' + s.count + '</span>' +
                '</div>';
        }).join('');
    }

    function _renderFocusCard(fault) {
        var el = document.getElementById('focus-content');
        if (!el) return;

        var severityColor = COLORS.alert_colors[fault.severity] || '#FADB14';
        var occurTime = fault.occurrence_time ? new Date(fault.occurrence_time).toLocaleString('zh-CN') : '未知';

        el.innerHTML = '<div class="focus-info">' +
            '<div class="focus-header">' +
            '<span class="focus-severity-badge" style="background:' + severityColor + '">' + (fault.urgency_display || '') + '</span>' +
            '<span class="focus-fault-number">' + fault.fault_number + '</span>' +
            '</div>' +
            '<div class="focus-row"><span class="focus-label">分类</span><span class="focus-value">' + (fault.category_display || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">A端</span><span class="focus-value">' + (fault.site_a || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">Z端</span><span class="focus-value">' + (fault.sites_z || []).join('、') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">省份</span><span class="focus-value">' + (fault.province || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">原因</span><span class="focus-value">' + (fault.reason || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">发生</span><span class="focus-value">' + occurTime + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">历时</span><span class="focus-value">' + (fault.duration || '处理中') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">处理人</span><span class="focus-value">' + (fault.handler || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">处理单位</span><span class="focus-value">' + (fault.handling_unit || '') + '</span></div>' +
            '</div>';
    }

    function _renderImpactCard(fault) {
        var el = document.getElementById('impact-content');
        if (!el) return;

        if (!fault.impact_names || fault.impact_names.length === 0) {
            el.innerHTML = '<div class="empty-state"><div class="empty-text">无受影响业务</div></div>';
            return;
        }

        el.innerHTML = '<div class="impact-list">' +
            fault.impact_names.map(function (name) {
                return '<div class="impact-item">' + name + '</div>';
            }).join('') +
            '</div>' +
            '<div style="margin-top:8px;font-size:10px;color:var(--text-dim)">共 ' + fault.impact_count + ' 个业务受影响</div>';
    }

    function _renderTimelineCard(fault) {
        var el = document.getElementById('timeline-content');
        if (!el) return;

        var steps = [
            { label: '故障发现', time: fault.occurrence_time, required: true },
            { label: '处理派发', time: fault.dispatch_time },
            { label: '维修出发', time: fault.departure_time },
            { label: '到达现场', time: fault.arrival_time },
            { label: '修复完成', time: fault.repair_time },
            { label: '故障恢复', time: fault.recovery_time },
        ];

        var lastCompleted = -1;
        steps.forEach(function (s, i) {
            if (s.time) lastCompleted = i;
        });

        el.innerHTML = '<div class="timeline">' +
            steps.map(function (s, i) {
                var cls = s.time ? 'completed' : (i === lastCompleted + 1 ? 'active' : '');
                var timeStr = s.time ? new Date(s.time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '--';
                return '<div class="timeline-item ' + cls + '">' +
                    '<div class="timeline-label">' + s.label + '</div>' +
                    '<div class="timeline-time">' + timeStr + '</div>' +
                    '</div>';
            }).join('') +
            '</div>';
    }

    return {
        updateOverview,
        updateTicker,
        showFaultFocus,
        clearFaultFocus,
        updateFaultQueue
    };
})();
