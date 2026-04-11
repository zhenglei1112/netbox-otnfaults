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
        // 更新左翼面板
        Panels.updateOverview(data);

        // 更新底部 Ticker
        Panels.updateTicker(data.ticker_events || []);

        // 更新地图图层
        MapEngine.renderSites(data.sites || []);
        MapEngine.renderFaultPaths(data.fault_paths || []);
        MapEngine.renderHeatmap(data.closed_fault_points || []);
        MapEngine.renderFaultMarkers(data.active_faults || []);

        // 更新播控引擎的故障队列
        DirectingEngine.updateFaultQueue(data.active_faults || []);

        // 更新故障队列面板
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

            onFaultFocus: function (fault) {
                console.log('[Directing] 故障聚焦:', fault.fault_number);

                // 显示右翼面板详情
                Panels.showFaultFocus(fault);

                // 触发视觉特效
                Effects.triggerShockwave(fault.lng, fault.lat, fault.severity);
                if (fault.severity === 'critical') {
                    Effects.flashCriticalAlert();
                }

                // 更新队列高亮
                if (lastData) {
                    Panels.updateFaultQueue(lastData.active_faults || [], fault.id);
                }
            },

            onFaultLeave: function (fault) {
                console.log('[Directing] 离开故障:', fault.fault_number);
                Panels.clearFaultFocus();

                if (lastData) {
                    Panels.updateFaultQueue(lastData.active_faults || [], null);
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

})();
