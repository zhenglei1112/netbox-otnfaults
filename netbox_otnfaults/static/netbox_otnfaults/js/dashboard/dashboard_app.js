/**
 * OTN 大屏 - 主入口模块
 *
 * 初始化所有子系统，管理数据轮询，协调各模块间的交互。
 */
(function () {
    'use strict';

    const CONFIG = window.DASHBOARD_CONFIG;
    let dataTimer = null;
    let lastData = null;

    /**
     * 应用启动
     */
    document.addEventListener('DOMContentLoaded', function () {
        console.log('[Dashboard] 大屏系统启动');

        // 1. 启动时钟
        _startClock();

        // 2. 初始化特效系统
        Effects.init();

        // 3. 初始化地图
        MapEngine.init();

        // 4. 首次加载数据
        _fetchData().then(function () {
            // 5. 数据就绪后启动播控引擎
            _startDirectingEngine();

            // 6. 设置定时刷新
            dataTimer = setInterval(_fetchData, CONFIG.refreshInterval);

            // 7. 更新连接状态
            _setConnectionStatus(true);
        }).catch(function (err) {
            console.error('[Dashboard] 首次数据加载失败:', err);
            _setConnectionStatus(false);
            // 即使数据加载失败也启动播控（空数据巡航模式）
            _startDirectingEngine();
            // 重试
            dataTimer = setInterval(_fetchData, CONFIG.refreshInterval);
        });
    });

    /**
     * 获取数据
     */
    function _fetchData() {
        return fetch(CONFIG.dataUrl, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function (data) {
                lastData = data;
                _setConnectionStatus(true);
                _processData(data);
            })
            .catch(function (err) {
                console.warn('[Dashboard] 数据获取失败:', err);
                _setConnectionStatus(false);
            });
    }

    /**
     * 处理数据并分发给各模块
     */
    function _processData(data) {
        // 更新布局状态（必须在面板渲染前执行）
        LayoutManager.update(data);

        // 更新运行看板核心数字
        Panels.updateSituationMetrics(data.summary || {});
        Panels.updateTrendChart(data.trend_24h || []);

        // 更新底部综合事件 Ticker
        Panels.updateTicker(Panels.buildDashboardEvents(data));

        // 更新底部重保信息条（弹性模块）
        Panels.updateHeavyDutyBar(data.heavy_duties || []);

        // 更新割接计划模块（弹性模块）
        Panels.updateCutoverPlan(data.cutovers || []);

        // 更新辅助信息卡片（无割接/运行总览模式下补位）
        Panels.updateAuxiliaryInfo(data);

        // 更新地图图层
        MapEngine.renderSites(data.sites || []);
        MapEngine.renderFaultPaths(data.fault_paths || []);
        MapEngine.renderCutoverMarkers(data.cutovers || [], data.sites || []);
        MapEngine.renderFaultMarkers(data.active_faults || []);

        // 更新播控引擎的综合事件队列
        var events = Panels.buildDashboardEvents(data);
        DirectingEngine.updateEventQueue(events);

        // 更新右侧综合事件队列
        Panels.updateEventQueue(data);

        // 保持故障播控高亮状态
        var currentState = DirectingEngine.getState();
        var activeFaultId = currentState.fault ? currentState.fault.id : null;
        Panels.updateFaultQueue(data.active_faults || [], activeFaultId);
    }

    /**
     * 启动播控引擎
     */
    function _startDirectingEngine() {
        DirectingEngine.start({
            onStateChange: function (stateInfo) {
                console.log('[Directing] 状态变更:', stateInfo.from, '→', stateInfo.to);
                Effects.updateDirectingIndicator(stateInfo);
            },

            onEventFocus: function (event) {
                console.log('[Directing] 事件聚焦:', event.title, '类型:', event.type);

                // 1. 同步高亮综合事件队列中的对应 DOM 节点
                Panels.highlightEventItem(event.key);

                // 2. 更新右下角焦点详情卡片
                Panels.showEventFocus(event);

                // 3. 地图飞行与特效处理
                if (event.type === 'fault') {
                    var fault = event.raw;
                    MapEngine.focusFaultSites(fault);

                    // 触发视觉特效
                    Effects.triggerShockwave(fault.lng, fault.lat, fault.severity);
                    if (fault.severity === 'critical') {
                        Effects.flashCriticalAlert();
                    }

                    // 额外同步右下角纯故障队列（如有）的高亮
                    if (lastData) {
                        Panels.updateFaultQueue(lastData.active_faults || [], fault.id);
                    }
                } else if (event.type === 'cutover') {
                    var cutover = event.raw;
                    // 割接同样高亮其 A/Z 端站点，但不触发故障类红色告警特效
                    MapEngine.focusFaultSites(cutover);
                    if (lastData) {
                        Panels.updateFaultQueue(lastData.active_faults || [], null);
                    }
                } else {
                    // 重保等其它非飞行聚焦事件：确保地图清除先前的站点聚焦，飞回全国视角
                    MapEngine.clearFaultSiteFocus();
                    if (lastData) {
                        Panels.updateFaultQueue(lastData.active_faults || [], null);
                    }
                }
            },

            onEventLeave: function (event) {
                console.log('[Directing] 离开事件:', event.title);
                if (event.type === 'fault' || event.type === 'cutover') {
                    // 延迟清除地图聚焦到下一渲染帧，避免与 flyTo 摄像机动画竞态
                    requestAnimationFrame(function () {
                        MapEngine.clearFaultSiteFocus();
                    });
                }
            }
        });
    }

    /**
     * 实时时钟
     */
    function _startClock() {
        function update() {
            var now = new Date();
            var dateEl = document.getElementById('current-date');
            var timeEl = document.getElementById('current-time');

            if (dateEl) {
                dateEl.textContent = now.getFullYear() + '/' +
                    String(now.getMonth() + 1).padStart(2, '0') + '/' +
                    String(now.getDate()).padStart(2, '0') + ' ' +
                    ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][now.getDay()];
            }

            if (timeEl) {
                timeEl.textContent =
                    String(now.getHours()).padStart(2, '0') + ':' +
                    String(now.getMinutes()).padStart(2, '0') + ':' +
                    String(now.getSeconds()).padStart(2, '0');
            }
        }

        update();
        setInterval(update, 1000);
    }

    /**
     * 连接状态
     */
    function _setConnectionStatus(connected) {
        var dot = document.getElementById('connection-dot');
        var text = document.getElementById('connection-text');

        if (dot) {
            dot.className = 'status-dot' + (connected ? '' : ' disconnected');
        }

        if (text) {
            text.textContent = connected ? '数据在线' : '数据断联';
        }
    }

    // 暴露全局接口以支持调试和外部协调
    window.DashboardApp = {
        processData: _processData,
        fetchData: _fetchData,
        stopPolling: function () {
            if (dataTimer) {
                clearInterval(dataTimer);
                dataTimer = null;
                console.log('[Dashboard] 轮询已暂停 (调试模式)');
            }
        },
        startPolling: function () {
            if (dataTimer) clearInterval(dataTimer);
            dataTimer = setInterval(_fetchData, CONFIG.refreshInterval);
            console.log('[Dashboard] 轮询已恢复');
        }
    };

})();
