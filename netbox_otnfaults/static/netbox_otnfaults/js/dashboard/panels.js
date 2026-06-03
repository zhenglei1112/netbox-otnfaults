/**
 * OTN 大屏 - 数据面板渲染模块
 * 
 * 负责左翼（宏观态势）和右翼（微观详情）的数据渲染。
 */
window.Panels = (function () {
    'use strict';

    const COLORS = window.DASHBOARD_CONFIG.colors;

    function _getStatusColor(status) {
        return COLORS.status_colors[status] || '#FADB14';
    }

    /**
     * 更新左翼面板 - 宏观态势
     */
    function updateOverview(data) {
        updateSituationMetrics(data.summary || {});
    }

    function updateSituationMetrics(summary) {
        _updateHealthGauge(summary || {});
    }

    /**
     * 更新重保通知横幅
     */
    let _lastHeavyDutyDataStr = '';

    function updateHeavyDuty(heavyDuties) {
        const banner = document.getElementById('heavy-duty-banner');
        const track = document.getElementById('heavy-duty-text');
        if (!banner || !track) return;

        const currentDataStr = JSON.stringify(heavyDuties);
        if (_lastHeavyDutyDataStr === currentDataStr) return;
        _lastHeavyDutyDataStr = currentDataStr;

        if (!heavyDuties || heavyDuties.length === 0) {
            banner.classList.add('hidden');
            track.innerHTML = '';
            return;
        }

        banner.classList.remove('hidden');

        var itemsHTML = heavyDuties.map(function (hd) {
            var timeRange = hd.start_time_display + ' 至 ' + hd.end_time_display;
            return '<span class="banner-text-item">【' + hd.name + '】保障时段：' + timeRange + '。内容：' + hd.description + '</span>';
        }).join('');

        track.innerHTML =
            '<div class="banner-text-group">' + itemsHTML + '</div>' +
            '<div class="banner-text-group">' + itemsHTML + '</div>';

        track.style.animation = 'none';
        track.offsetHeight; // reflow

        var group = track.querySelector('.banner-text-group');
        if (group) {
            var groupWidth = group.offsetWidth;
            var duration = Math.max(20, groupWidth / 40);
            track.style.animation = 'banner-scroll ' + duration + 's linear infinite';
        }
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

        // 生成结构摘要（仅包含故障编号），用于判断是否需要重建DOM
        const currentSummaryStr = events.map(function (e) { return e.key || e.fault_number || e.title; }).join(',');
        const isStructureChanged = (currentSummaryStr !== _lastTickerSummaryStr);
        _lastTickerSummaryStr = currentSummaryStr;

        if (isStructureChanged) {
            // 结构变化（故障增减/顺序改变）→ 重建DOM并重启动画
            // 构建两组相同内容实现无缝循环
            var itemsHTML = events.map(function (e) {
                return _buildTickerItemHTML(e);
            }).join('');
            container.innerHTML =
                '<span class="ticker-group">' + itemsHTML + '</span>' +
                '<span class="ticker-group">' + itemsHTML + '</span>';

            container.style.animation = 'none';
            container.offsetHeight; // reflow
            // 只需滚动一组的宽度（即容器总宽的50%），动画循环时无缝衔接
            var groupWidth = container.querySelector('.ticker-group').offsetWidth;
            var duration = Math.max(30, groupWidth / 50);
            container.style.animation = 'ticker-scroll ' + duration + 's linear infinite';
        } else {
            // 结构未变（仅历时/状态等文本更新）→ 原地更新两组DOM文本，保持动画连续
            var groups = container.querySelectorAll('.ticker-group');
            groups.forEach(function (group) {
                var items = group.querySelectorAll('.ticker-item');
                events.forEach(function (e, i) {
                    if (items[i]) {
                        var textNode = items[i].querySelector('.ticker-text');
                        if (textNode) {
                            textNode.textContent = _buildTickerText(e);
                        }
                    }
                });
            });
        }
    }

    /**
     * 构建单条 Ticker 项的完整 HTML
     */
    function _buildTickerItemHTML(e) {
        const color = e.color || COLORS.alert_colors[e.severity] || '#FADB14';
        return '<span class="ticker-item">' +
            '<span class="ticker-severity-dot" style="background:' + color +
            ';box-shadow:0 0 4px ' + color + '"></span>' +
            '<span class="ticker-fault-number">' + (e.badge || e.fault_number || '') + '</span>' +
            '<span class="ticker-text">' + _buildTickerText(e) + '</span>' +
            '</span>';
    }

    /**
     * 构建 Ticker 项的可变文本部分
     */
    function _buildTickerText(e) {
        if (e.type === 'cutover') {
            return e.title + ' | ' + (e.time_text || '') + ' | ' + (e.location || '') +
                (e.impact_count ? ' | 影响业务 ' + e.impact_count + ' 项' : '');
        }
        if (e.type === 'heavy_duty') {
            return e.title + ' | ' + (e.time_text || '') + ' | ' + (e.description || '');
        }
        if (e.type === 'fault') {
            return e.title + ' | ' + (e.site_text || '') +
                (e.duration ? ' | 历时' + e.duration : '') + ' | ' + (e.status || '');
        }
        var siteText = e.site_a || '';
        if (e.sites_z && e.sites_z.length > 0) {
            siteText += ' → ' + e.sites_z.join('、');
        }
        return e.category + ' | ' + siteText + ' | ' + e.time +
            (e.duration ? ' | 历时' + e.duration : '') + ' | ' + e.status;
    }

    function _buildDashboardEvents(data) {
        var events = [];
        (data.active_faults || []).forEach(function (fault) {
            var siteText = fault.site_a || '';
            if (fault.sites_z && fault.sites_z.length > 0) {
                siteText += ' → ' + fault.sites_z.join('、');
            }
            events.push({
                type: 'fault',
                key: 'fault-' + fault.id,
                badge: '故障',
                title: fault.fault_number || '处理中故障',
                status: fault.status_display || '',
                severity: fault.severity || 'major',
                color: COLORS.alert_colors[fault.severity || 'major'] || '#FF1E1E',
                priority: 300 + (fault.priority_score || 0),
                site_text: siteText,
                duration: fault.duration || '',
                raw: fault
            });
        });

        (data.cutovers || []).forEach(function (cutover) {
            var minutes = Number(cutover.minutes_until || 0);
            var timeText = minutes >= 0 && minutes < 1440
                ? 'T-' + Math.floor(minutes / 60) + '小时' + (minutes % 60) + '分'
                : (cutover.planned_time_display || '');
            events.push({
                type: 'cutover',
                key: 'cutover-' + cutover.id,
                badge: '割接',
                title: cutover.cutover_no || '计划割接',
                status: cutover.status_display || '',
                color: '#F59E0B',
                priority: 200 - Math.max(minutes, 0) / 60,
                time_text: timeText,
                location: cutover.location || '',
                impact_count: cutover.impact_count || 0,
                raw: cutover
            });
        });

        (data.heavy_duties || []).forEach(function (heavyDuty) {
            events.push({
                type: 'heavy_duty',
                key: 'heavy-duty-' + heavyDuty.id,
                badge: '重保',
                title: heavyDuty.name || '重保信息',
                status: '进行中',
                color: '#10B981',
                priority: 100,
                time_text: (heavyDuty.start_time_display || '') + ' 至 ' + (heavyDuty.end_time_display || ''),
                description: heavyDuty.description || '',
                raw: heavyDuty
            });
        });

        events.sort(function (a, b) { return b.priority - a.priority; });
        return events;
    }

    function buildDashboardEvents(data) {
        return _buildDashboardEvents(data || {});
    }

    function updateEventQueue(data) {
        var events = _buildDashboardEvents(data || {});
        var container = document.getElementById('event-queue');
        if (!container) return;

        if (events.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-text">暂无运行事件</div></div>';
            showEventFocus(null);
            return;
        }

        container.innerHTML = events.slice(0, 12).map(function (event, index) {
            return '<div class="event-item event-item--' + event.type + (index === 0 ? ' active' : '') +
                '" data-event-key="' + event.key + '">' +
                '<span class="event-badge">' + event.badge + '</span>' +
                '<div class="event-info">' +
                '<div class="event-title">' + event.title + '</div>' +
                '<div class="event-detail">' + _buildTickerText(event) + '</div>' +
                '</div>' +
                '</div>';
        }).join('');

        container.querySelectorAll('.event-item').forEach(function (item) {
            item.addEventListener('click', function () {
                var key = this.dataset.eventKey;
                var event = events.find(function (candidate) { return candidate.key === key; });
                container.querySelectorAll('.event-item').forEach(function (el) { el.classList.remove('active'); });
                this.classList.add('active');
                showEventFocus(event);
            });
        });

        showEventFocus(events[0]);
    }

    function showEventFocus(event) {
        var el = document.getElementById('event-focus-content');
        if (!el) return;
        if (!event) {
            el.innerHTML = '<div class="empty-state"><div class="empty-text">等待事件数据...</div></div>';
            return;
        }
        if (event.type === 'cutover') {
            _renderCutoverFocus(el, event.raw);
        } else if (event.type === 'heavy_duty') {
            _renderHeavyDutyFocus(el, event.raw);
        } else {
            _renderFaultFocus(el, event.raw);
        }
    }

    /**
     * 显示焦点故障详情（右翼面板）
     */
    function showFaultFocus(fault) {
        showEventFocus(fault ? {
            type: 'fault',
            raw: fault
        } : null);
    }

    /**
     * 清除焦点故障
     */
    function clearFaultFocus() {
        showEventFocus(null);
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
            var color = _getStatusColor(f.status);
            var activeClass = (f.id === activeFaultId) ? ' active' : '';
            return '<div class="queue-item' + activeClass + '" data-fault-id="' + f.id + '">' +
                '<span class="queue-severity" style="background:' + color + ';box-shadow:0 0 4px ' + color + '"></span>' +
                '<div class="queue-info">' +
                '<div class="queue-number">' + f.fault_number + '</div>' +
                '<div class="queue-detail">' + (f.status_display || '') + ' · ' + (f.category_display || '') + ' · ' + (f.site_a || '') + '</div>' +
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

        var cutovers = document.getElementById('stat-upcoming-cutovers');
        if (cutovers) cutovers.textContent = summary.upcoming_cutovers || 0;

        var heavyDuties = document.getElementById('stat-active-heavy-duties');
        if (heavyDuties) heavyDuties.textContent = summary.active_heavy_duties || 0;
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

    function updateTrendChart(trendData) {
        _updateTrendChart(trendData || []);
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

        var statusColor = _getStatusColor(fault.status);
        var occurTime = fault.occurrence_time ? new Date(fault.occurrence_time).toLocaleString('zh-CN') : '未知';

        el.innerHTML = '<div class="focus-info">' +
            '<div class="focus-header">' +
            '<span class="focus-severity-badge" style="background:' + statusColor + '">' + (fault.status_display || '未知状态') + '</span>' +
            '<span class="focus-fault-number">' + fault.fault_number + '</span>' +
            '</div>' +
            '<div class="focus-row"><span class="focus-label">分类</span><span class="focus-value">' + (fault.category_display || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">A端</span><span class="focus-value">' + (fault.site_a || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">Z端</span><span class="focus-value">' + (fault.sites_z || []).join('、') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">省份</span><span class="focus-value">' + (fault.province || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">原因</span><span class="focus-value">' + (fault.reason || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">起始</span><span class="focus-value">' + occurTime + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">历时</span><span class="focus-value">' + (fault.duration || '处理中') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">处理人</span><span class="focus-value">' + (fault.handler || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">代维方/租赁方</span><span class="focus-value">' + (fault.handling_unit || '') + '</span></div>' +
            '</div>';
    }

    function _renderFaultFocus(el, fault) {
        if (!fault) {
            el.innerHTML = '<div class="empty-state"><div class="empty-text">暂无故障数据</div></div>';
            return;
        }
        var statusColor = _getStatusColor(fault.status);
        var occurTime = fault.occurrence_time ? new Date(fault.occurrence_time).toLocaleString('zh-CN') : '未知';
        el.innerHTML = '<div class="focus-info">' +
            '<div class="focus-header">' +
            '<span class="focus-severity-badge" style="background:' + statusColor + '">' + (fault.status_display || '处理中') + '</span>' +
            '<span class="focus-fault-number">' + (fault.fault_number || '') + '</span>' +
            '</div>' +
            '<div class="focus-row"><span class="focus-label">类型</span><span class="focus-value">' + (fault.category_display || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">站点</span><span class="focus-value">' + (fault.site_a || '') + ' → ' + (fault.sites_z || []).join('、') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">起始</span><span class="focus-value">' + occurTime + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">历时</span><span class="focus-value">' + (fault.duration || '处理中') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">影响</span><span class="focus-value">' + (fault.impact_count || 0) + ' 项业务</span></div>' +
            '<div class="focus-row"><span class="focus-label">处理人</span><span class="focus-value">' + (fault.handler || '') + '</span></div>' +
            '</div>';
    }

    function _renderCutoverFocus(el, cutover) {
        if (!cutover) {
            el.innerHTML = '<div class="empty-state"><div class="empty-text">暂无割接数据</div></div>';
            return;
        }
        el.innerHTML = '<div class="focus-info">' +
            '<div class="focus-header">' +
            '<span class="focus-severity-badge event-badge-cutover">' + (cutover.status_display || '待实施') + '</span>' +
            '<span class="focus-fault-number">' + (cutover.cutover_no || '计划割接') + '</span>' +
            '</div>' +
            '<div class="focus-row"><span class="focus-label">时间</span><span class="focus-value">' + (cutover.planned_time_display || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">地点</span><span class="focus-value">' + (cutover.location || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">A端</span><span class="focus-value">' + (cutover.site_a || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">Z端</span><span class="focus-value">' + (cutover.sites_z || []).join('、') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">影响</span><span class="focus-value">' + (cutover.impact_count || 0) + ' 项业务</span></div>' +
            '<div class="focus-row"><span class="focus-label">实施</span><span class="focus-value">' + (cutover.implementation_unit || '') + '</span></div>' +
            '</div>';
    }

    function _renderHeavyDutyFocus(el, heavyDuty) {
        if (!heavyDuty) {
            el.innerHTML = '<div class="empty-state"><div class="empty-text">暂无重保数据</div></div>';
            return;
        }
        el.innerHTML = '<div class="focus-info">' +
            '<div class="focus-header">' +
            '<span class="focus-severity-badge event-badge-heavy">进行中</span>' +
            '<span class="focus-fault-number">' + (heavyDuty.name || '重保信息') + '</span>' +
            '</div>' +
            '<div class="focus-row"><span class="focus-label">开始</span><span class="focus-value">' + (heavyDuty.start_time_display || '') + '</span></div>' +
            '<div class="focus-row"><span class="focus-label">结束</span><span class="focus-value">' + (heavyDuty.end_time_display || '') + '</span></div>' +
            '<div class="event-description">' + (heavyDuty.description || '') + '</div>' +
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
            { label: '故障起始', time: fault.occurrence_time, required: true },
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
                var timeStr = s.time ? new Date(s.time).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
                return '<div class="timeline-item ' + cls + '">' +
                    '<div class="timeline-label">' + s.label + '</div>' +
                    '<div class="timeline-time">' + timeStr + '</div>' +
                    '</div>';
            }).join('') +
            '</div>';
    }

    return {
        updateOverview,
        updateSituationMetrics,
        updateTrendChart,
        updateTicker,
        updateHeavyDuty,
        buildDashboardEvents,
        updateEventQueue,
        showEventFocus,
        showFaultFocus,
        clearFaultFocus,
        updateFaultQueue
    };
})();
