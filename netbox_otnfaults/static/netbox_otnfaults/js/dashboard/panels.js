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

    /**
     * 构建事件队列详情文本（不含标题前缀，避免与 event-title 重复）
     */
    function _buildEventDetailText(e) {
        if (e.type === 'cutover') {
            return (e.time_text || '') + ' | ' + (e.location || '') +
                (e.impact_count ? ' | 影响业务 ' + e.impact_count + ' 项' : '');
        }
        if (e.type === 'heavy_duty') {
            return (e.time_text || '') + ' | ' + (e.description || '');
        }
        if (e.type === 'fault') {
            return (e.site_text || '') +
                (e.duration ? ' | 历时' + e.duration : '') + ' | ' + (e.status || '');
        }
        var siteText = e.site_a || '';
        if (e.sites_z && e.sites_z.length > 0) {
            siteText += ' → ' + e.sites_z.join('、');
        }
        return siteText + ' | ' + e.time +
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
            
            // 重新设计割接优先级分数，确保临近割接能够脱颖而出
            var priority = 150;
            if (minutes >= 0 && minutes < 1440) {
                // 24小时内即将实施的割接优先级评分设为 320 ~ 344，挤进前列
                priority = 320 + (24 - minutes / 60);
            } else if (minutes >= 0) {
                // 24小时以外的割接评分设为 150 ~ 200，在突发故障较少时补位展示
                priority = 200 - (minutes / 1440) * 50;
                if (priority < 150) priority = 150;
            }

            events.push({
                type: 'cutover',
                key: 'cutover-' + cutover.id,
                badge: '割接',
                title: cutover.cutover_no || '计划割接',
                status: cutover.status_display || '',
                color: '#F59E0B',
                priority: priority,
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
                priority: 350, // 重保为当前正值守的重要任务，优先级调为 350 排在顶层
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

    function highlightEventItem(eventKey) {
        var container = document.getElementById('event-queue');
        if (!container) return;
        container.querySelectorAll('.event-item').forEach(function (el) {
            if (el.dataset.eventKey === eventKey) {
                el.classList.add('active');
                el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                el.classList.remove('active');
            }
        });
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

        container.innerHTML = events.slice(0, 12).map(function (event) {
            return '<div class="event-item event-item--' + event.type +
                '" data-event-key="' + event.key + '">' +
                '<span class="event-badge">' + event.badge + '</span>' +
                '<div class="event-info">' +
                '<div class="event-title">' + event.title + '</div>' +
                '<div class="event-detail">' + _buildEventDetailText(event) + '</div>' +
                '</div>' +
                '</div>';
        }).join('');

        container.querySelectorAll('.event-item').forEach(function (item) {
            item.addEventListener('click', function () {
                var key = this.dataset.eventKey;
                var event = events.find(function (candidate) { return candidate.key === key; });
                if (event && window.DirectingEngine) {
                    window.DirectingEngine.focusOnEvent(event);
                }
            });
        });
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
        
        // 支持高分屏（4K/Retina）和自适应宽度，防止缩放模糊
        var rect = canvas.parentElement.getBoundingClientRect();
        var w = Math.max(1, rect.width);
        var h = Math.max(1, rect.height);
        var dpr = window.devicePixelRatio || 1;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        ctx.scale(dpr, dpr);
        // 计算缩放比例因子（以 1080p 下侧边栏默认宽度 320px 为基准）
        var chartScale = Math.max(1, w / 320);

        var padding = { 
            top: 10 * chartScale, 
            right: 10 * chartScale, 
            bottom: 20 * chartScale, 
            left: 30 * chartScale 
        };
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
        ctx.lineWidth = 1.5 * chartScale;
        ctx.shadowColor = 'rgba(0, 210, 255, 0.5)';
        ctx.shadowBlur = 4 * chartScale;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 数据点
        points.forEach(function (p) {
            if (p.value > 0) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2 * chartScale, 0, Math.PI * 2);
                ctx.fillStyle = '#00D2FF';
                ctx.fill();
            }
        });

        // X轴标签（每6小时）
        ctx.fillStyle = 'rgba(140, 160, 180, 0.5)';
        ctx.font = (9 * chartScale) + 'px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        for (var i = 0; i < points.length; i += 6) {
            ctx.fillText(points[i].label, points[i].x, h - 4 * chartScale);
        }

        // Y轴
        ctx.textAlign = 'right';
        ctx.fillText(maxVal, padding.left - 4 * chartScale, padding.top + 8 * chartScale);
        ctx.fillText('0', padding.left - 4 * chartScale, h - padding.bottom);
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
            '<div class="focus-row"><span class="focus-label">站点</span><span class="focus-value">' + (cutover.site_a || '') + ' → ' + (cutover.sites_z || []).join('、') + '</span></div>' +
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

    /* ═══ 割接计划模块渲染 ═══ */

    /**
     * 格式化倒计时文本
     */
    function _formatCountdown(minutes) {
        if (minutes < 0) return null;
        var days = Math.floor(minutes / 1440);
        var hours = Math.floor((minutes % 1440) / 60);
        var mins = minutes % 60;
        var parts = [];
        if (days > 0) parts.push(days + '天');
        if (hours > 0) parts.push(hours + '小时');
        parts.push(mins + '分');
        return parts.join('');
    }

    /**
     * 渲染割接空状态卡片
     */
    function _renderCutoverEmpty(container) {
        var text = LayoutManager.EMPTY_TEXT.cutover;
        container.innerHTML =
            '<div class="empty-state-rich">' +
            '<div class="empty-state-icon">📋</div>' +
            '<div class="empty-state-title">' + text.title + '</div>' +
            (text.subtitle ? '<div class="empty-state-subtitle">' + text.subtitle + '</div>' : '') +
            '</div>';
    }

    /**
     * 渲染割接卡片列表 (1-3条)
     */
    function _renderCutoverCardList(container, cutovers) {
        container.innerHTML = cutovers.map(function (c) {
            var isUrgent = c.minutes_until >= 0 && c.minutes_until < 1440;
            var countdownText = _formatCountdown(c.minutes_until);
            var statusClass = c.status === 'applying' ? ' status-applying' : '';

            var html = '<div class="cutover-card-item">' +
                '<div class="cutover-card-header">' +
                '<span class="cutover-card-no">' + (c.cutover_no || '计划割接') + '</span>' +
                '<span class="cutover-card-status' + statusClass + '">' + (c.status_display || '待实施') + '</span>' +
                '</div>' +
                '<div class="cutover-card-row"><span class="cutover-card-label">时间</span><span class="cutover-card-value">' + (c.planned_time_display || '') + '</span></div>' +
                '<div class="cutover-card-row"><span class="cutover-card-label">地点</span><span class="cutover-card-value">' + (c.location || c.site_a || '') + '</span></div>' +
                '<div class="cutover-card-row"><span class="cutover-card-label">影响</span><span class="cutover-card-value">' + (c.impact_count || 0) + ' 项业务</span></div>';

            if (countdownText) {
                html += '<div class="cutover-countdown' + (isUrgent ? ' urgent' : '') + '">⏱ T-' + countdownText + '</div>';
            }

            html += '</div>';
            return html;
        }).join('');
    }

    /**
     * 渲染割接紧凑列表 (4-8条)
     */
    function _renderCutoverCompactList(container, cutovers) {
        container.innerHTML = cutovers.map(function (c) {
            return '<div class="cutover-compact-item">' +
                '<span class="cutover-compact-time">' + (c.planned_time_display || '') + '</span>' +
                '<span class="cutover-compact-info"><span class="cutover-compact-no">' + (c.cutover_no || '') + '</span> ' + (c.location || c.site_a || '') + '</span>' +
                '<span class="cutover-compact-impact">' + (c.impact_count || 0) + '</span>' +
                '</div>';
        }).join('');
    }

    /**
     * 渲染割接分组滚动 (>8条)
     */
    function _renderCutoverGroupedScroll(container, cutovers) {
        var within24h = 0;
        var within7d = 0;
        var applying = 0;
        var pending = 0;
        cutovers.forEach(function (c) {
            if (c.minutes_until >= 0 && c.minutes_until < 1440) within24h++;
            if (c.minutes_until >= 0 && c.minutes_until < 10080) within7d++;
            if (c.status === 'applying') applying++;
            if (c.status === 'pending_implementation') pending++;
        });

        var summaryHTML =
            '<div class="cutover-group-summary">' +
            '<div class="cutover-group-item"><span class="cutover-group-count">' + within24h + '</span><span class="cutover-group-label">未来24小时</span></div>' +
            '<div class="cutover-group-item"><span class="cutover-group-count">' + within7d + '</span><span class="cutover-group-label">未来7天</span></div>' +
            '<div class="cutover-group-item"><span class="cutover-group-count">' + applying + '</span><span class="cutover-group-label">申请中</span></div>' +
            '<div class="cutover-group-item"><span class="cutover-group-count">' + pending + '</span><span class="cutover-group-label">待实施</span></div>' +
            '</div>';

        var top5 = cutovers.slice(0, 5);
        var listHTML = '<div class="cutover-scroll-list">' +
            '<div class="cutover-scroll-divider">最近割接</div>' +
            top5.map(function (c) {
                return '<div class="cutover-compact-item">' +
                    '<span class="cutover-compact-time">' + (c.planned_time_display || '') + '</span>' +
                    '<span class="cutover-compact-info"><span class="cutover-compact-no">' + (c.cutover_no || '') + '</span> ' + (c.location || c.site_a || '') + '</span>' +
                    '<span class="cutover-compact-impact">' + (c.impact_count || 0) + '</span>' +
                    '</div>';
            }).join('') +
            '</div>';

        container.innerHTML = summaryHTML + listHTML;
    }

    /**
     * 更新割接计划模块
     */
    function updateCutoverPlan(cutovers) {
        var container = document.getElementById('cutover-plan-content');
        var badge = document.getElementById('cutover-count-badge');
        if (!container) return;

        var count = cutovers.length;

        if (badge) {
            badge.textContent = count > 0 ? count : '';
        }

        if (count === 0) {
            _renderCutoverEmpty(container);
        } else if (count <= 3) {
            _renderCutoverCardList(container, cutovers);
        } else if (count <= 8) {
            _renderCutoverCompactList(container, cutovers);
        } else {
            _renderCutoverGroupedScroll(container, cutovers);
        }
    }

    /* ═══ 底部重保信息条渲染 ═══ */

    /**
     * 更新底部重保信息条
     */
    function updateHeavyDutyBar(heavyDuties) {
        var container = document.getElementById('heavy-duty-bar-content');
        if (!container) return;

        var count = heavyDuties.length;

        if (count === 0) {
            container.innerHTML = '<span class="heavy-duty-quiet-text">近期暂无重保任务 · 当前网络按常规运行策略保障</span>';
        } else if (count <= 2) {
            container.innerHTML = heavyDuties.map(function (hd) {
                return '<div class="heavy-duty-hcard">' +
                    '<span class="heavy-duty-hcard-name">' + hd.name + '</span>' +
                    '<span class="heavy-duty-hcard-time">' + hd.start_time_display + ' 至 ' + hd.end_time_display + '</span>' +
                    '</div>';
            }).join('');
        } else if (count <= 5) {
            container.innerHTML = heavyDuties.map(function (hd) {
                return '<span class="heavy-duty-list-item">' +
                    '<span class="heavy-duty-list-dot"></span>' +
                    '<span class="heavy-duty-list-name">' + hd.name + '</span>' +
                    '<span class="heavy-duty-list-time">' + hd.start_time_display + ' 至 ' + hd.end_time_display + '</span>' +
                    '</span>';
            }).join('');
        } else {
            var statsHTML =
                '<div class="heavy-duty-group-stats">' +
                '<div class="heavy-duty-group-stat"><span class="heavy-duty-group-stat-count">' + count + '</span><span class="heavy-duty-group-stat-label">进行中</span></div>' +
                '</div>';

            var itemsHTML = heavyDuties.map(function (hd) {
                return '<span class="heavy-duty-carousel-item">' +
                    '🛡️ ' + hd.name + ' · ' + hd.start_time_display + ' 至 ' + hd.end_time_display +
                    '</span>';
            }).join('');

            container.innerHTML = statsHTML +
                '<div class="heavy-duty-carousel"><div class="heavy-duty-carousel-track">' +
                itemsHTML + itemsHTML +
                '</div></div>';
        }
    }

    /* ═══ 辅助信息卡片渲染 ═══ */

    /**
     * 更新辅助信息卡片（无割接/无重保时补位）
     */
    function updateAuxiliaryInfo(data) {
        var container = document.getElementById('auxiliary-info-content');
        if (!container) return;

        var state = LayoutManager.getState();
        if (state.layout !== LayoutManager.LAYOUT.NO_CUTOVER &&
            state.layout !== LayoutManager.LAYOUT.OVERVIEW) {
            return;
        }

        var summary = data.summary || {};
        var statusText = LayoutManager.EMPTY_TEXT.overview;

        var bannerTitle = statusText.title;
        var bannerSubtitle = '';
        if (state.layout === LayoutManager.LAYOUT.NO_CUTOVER) {
            bannerTitle = LayoutManager.EMPTY_TEXT.cutover.title;
            bannerSubtitle = LayoutManager.EMPTY_TEXT.cutover.subtitle;
        }

        container.innerHTML =
            '<div class="auxiliary-overview">' +
            '<div class="auxiliary-status-banner">' +
            '<div class="auxiliary-status-title">' + bannerTitle + '</div>' +
            (bannerSubtitle ? '<div class="auxiliary-status-subtitle">' + bannerSubtitle + '</div>' : '') +
            '</div>' +
            '<div class="auxiliary-metrics">' +
            '<div class="auxiliary-metric-item"><span class="auxiliary-metric-value">' + (summary.active_faults || 0) + '</span><span class="auxiliary-metric-label">处理中故障</span></div>' +
            '<div class="auxiliary-metric-item"><span class="auxiliary-metric-value">' + (summary.health_score || 0) + '%</span><span class="auxiliary-metric-label">健康指数</span></div>' +
            '<div class="auxiliary-metric-item"><span class="auxiliary-metric-value">' + (summary.total_faults || 0) + '</span><span class="auxiliary-metric-label">年度故障总数</span></div>' +
            '<div class="auxiliary-metric-item"><span class="auxiliary-metric-value">' + (summary.temporary_recovery_faults || 0) + '</span><span class="auxiliary-metric-label">临时恢复</span></div>' +
            '</div>' +
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
        highlightEventItem,
        showEventFocus,
        showFaultFocus,
        clearFaultFocus,
        updateFaultQueue,
        updateCutoverPlan,
        updateHeavyDutyBar,
        updateAuxiliaryInfo
    };
})();
