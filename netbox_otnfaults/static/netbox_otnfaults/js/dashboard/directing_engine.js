/**
 * OTN 大屏 - 智能播控引擎 (Directing Engine)
 * 
 * 基于综合事件（故障、割接、重保）进行自上而下的顺次自动轮播与聚焦联动。
 */
window.DirectingEngine = (function () {
    'use strict';

    /* ── 状态常量 ── */
    const STATE = {
        GLOBAL_CRUISE: 'GLOBAL_CRUISE',      // 全局巡航 (用于无事件时，或割接/重保聚焦展示时)
        CAMERA_FLIGHT: 'CAMERA_FLIGHT',      // 视角飞行 (针对故障事件飞往站点)
        FAULT_ANALYSIS: 'FAULT_ANALYSIS',    // 事件聚焦/分析
    };

    /* ── 状态中文名 ── */
    const STATE_NAMES = {
        GLOBAL_CRUISE: '全局巡航',
        CAMERA_FLIGHT: '视角飞行',
        FAULT_ANALYSIS: '事件聚焦',
    };

    /* ── 内部状态 ── */
    let currentState = STATE.GLOBAL_CRUISE;
    let eventQueue = [];         // 综合事件队列，按优先级排序
    let currentEvent = null;     // 当前展示中的事件
    let currentIndex = -1;       // 当前轮播的事件索引
    let timer = null;
    let running = false;
    let paused = false;

    /* ── 回调 ── */
    let onStateChange = function () { };
    let onEventFocus = function () { };
    let onEventLeave = function () { };

    /* ── 时间参数 (ms) ── */
    const FAULT_DWELL_BASE = 20000;         // 故障基础停留时间
    const FAULT_DWELL_CRITICAL = 40000;     // 致命故障停留时间
    const EVENT_DWELL_DEFAULT = 20000;      // 割接、重保等默认停留时间
    const CRUISE_DWELL_TIME = 20000;        // 纯巡航停留时间（无事件时）
    const FAULT_FOCUS_SITE_LABEL_ZOOM_MARGIN = 2.5;
    const CONFIG = window.DASHBOARD_CONFIG;

    /**
     * 启动播控引擎
     */
    function start(callbacks) {
        onStateChange = callbacks.onStateChange || function () { };
        onEventFocus = callbacks.onEventFocus || callbacks.onFaultFocus || function () { };
        onEventLeave = callbacks.onEventLeave || callbacks.onFaultLeave || function () { };

        running = true;
        paused = false;
        _setState(STATE.GLOBAL_CRUISE);
        _runStateMachine();
    }

    /**
     * 停止播控引擎
     */
    function stop() {
        running = false;
        if (timer) clearTimeout(timer);
    }

    /**
     * 暂停/恢复
     */
    function togglePause() {
        paused = !paused;
        if (!paused) _runStateMachine();
        return paused;
    }

    /**
     * 更新综合事件队列
     */
    function updateEventQueue(events) {
        eventQueue = (events || []).slice(0, 12); // 只取前12个

        if (eventQueue.length === 0) {
            currentEvent = null;
            currentIndex = -1;
            if (currentState !== STATE.GLOBAL_CRUISE) {
                _setState(STATE.GLOBAL_CRUISE);
                _runStateMachine();
            }
            return;
        }

        if (currentEvent) {
            // 在新队列中查找当前事件
            var foundIndex = -1;
            for (var i = 0; i < eventQueue.length; i++) {
                if (eventQueue[i].key === currentEvent.key) {
                    foundIndex = i;
                    break;
                }
            }

            if (foundIndex !== -1) {
                // 找到了，更新索引并保持数据最新，但不打断当前的轮播定时器
                currentIndex = foundIndex;
                currentEvent = eventQueue[currentIndex];
            } else {
                // 当前聚焦的事件已不存在（如故障清除或重保结束），重置为首个事件并重新运行
                currentIndex = 0;
                currentEvent = eventQueue[0];
                _setState(STATE.GLOBAL_CRUISE);
                _runStateMachine();
            }
        } else {
            // 首次获得数据，开始播放首个事件
            currentIndex = 0;
            currentEvent = eventQueue[0];
            _setState(STATE.GLOBAL_CRUISE);
            _runStateMachine();
        }
    }

    /**
     * 手动跳转到指定事件（接管）
     */
    function focusOnEvent(event) {
        if (!event) return;
        if (timer) clearTimeout(timer);

        // 查找在当前队列中的 index
        var foundIndex = -1;
        for (var i = 0; i < eventQueue.length; i++) {
            if (eventQueue[i].key === event.key) {
                foundIndex = i;
                break;
            }
        }

        if (foundIndex !== -1) {
            currentIndex = foundIndex;
            currentEvent = eventQueue[currentIndex];
        } else {
            // 兜底（如果不在前12个中）
            currentEvent = event;
        }

        // 根据类型决定是否飞行
        if (currentEvent.type === 'fault' || currentEvent.type === 'cutover') {
            _setState(STATE.CAMERA_FLIGHT);
        } else {
            _setState(STATE.GLOBAL_CRUISE, currentEvent.badge + '播控');
        }
        _runStateMachine();
    }

    /**
     * 获取当前状态（提供给状态栏指示器等）
     */
    function getState() {
        return {
            state: currentState,
            stateName: STATE_NAMES[currentState],
            event: currentEvent,
            fault: (currentEvent && currentEvent.type === 'fault') ? currentEvent.raw : null
        };
    }

    /* ═══ 状态机核心 ═══ */

    function _setState(newState, customName) {
        const oldState = currentState;
        currentState = newState;
        onStateChange({
            from: oldState,
            to: newState,
            name: customName || STATE_NAMES[newState],
            event: currentEvent,
            fault: (currentEvent && currentEvent.type === 'fault') ? currentEvent.raw : null
        });
    }

    function _runStateMachine() {
        if (!running || paused) return;
        if (timer) clearTimeout(timer);

        if (eventQueue.length === 0) {
            // 暂无任何活跃事件，执行纯巡航
            _executePureCruise();
            return;
        }

        // 纠正越界索引
        if (currentIndex < 0 || currentIndex >= eventQueue.length) {
            currentIndex = 0;
        }
        currentEvent = eventQueue[currentIndex];

        if (currentEvent.type === 'fault' || currentEvent.type === 'cutover') {
            // 故障与割接事件：需要进行视点飞行与精准分析
            if (currentState === STATE.GLOBAL_CRUISE) {
                _setState(STATE.CAMERA_FLIGHT);
                _executeCameraFlight();
            } else if (currentState === STATE.CAMERA_FLIGHT) {
                _executeCameraFlight();
            } else {
                _executeEventFocus();
            }
        } else {
            // 重保事件：不需要摄像头飞行动效，直接在大地图视角下聚焦轮播
            _setState(STATE.GLOBAL_CRUISE, currentEvent.badge + '播控');
            _executeNonFaultEventFocus();
        }
    }

    /* ── 纯巡航（无运行事件时） ── */
    function _executePureCruise() {
        MapEngine.resetView().then(function () {
            // 执行极慢速旋转
            MapEngine.rotateTo(10, 25000);
            timer = setTimeout(function () {
                _runStateMachine();
            }, CRUISE_DWELL_TIME);
        });
    }

    /* ── 摄像机飞行（飞往故障点） ── */
    function _executeCameraFlight() {
        var fault = currentEvent.raw;
        var map = MapEngine.getMap();
        if (!fault || fault.lng == null || fault.lat == null) {
            // 割接或故障缺失坐标时，无法飞行，直接进入事件聚焦状态
            _setState(STATE.FAULT_ANALYSIS);
            _runStateMachine();
            return;
        }
        var currentCenter = map ? map.getCenter() : { lng: CONFIG.mapCenter[0], lat: CONFIG.mapCenter[1] };
        var dx = fault.lng - currentCenter.lng;
        var dy = fault.lat - currentCenter.lat;
        var distance = Math.sqrt(dx * dx + dy * dy);
        var duration = Math.min(6000, Math.max(3000, distance * 300));
        var faultFocusZoom = MapEngine.getSiteLabelMinZoom() + FAULT_FOCUS_SITE_LABEL_ZOOM_MARGIN;

        MapEngine.flyTo(fault.lng, fault.lat, faultFocusZoom, {
            duration: duration,
            pitch: 55,
        }).then(function () {
            _setState(STATE.FAULT_ANALYSIS);
            _runStateMachine();
        });
    }

    /* ── 故障事件深度分析 ── */
    function _executeEventFocus() {
        // 通知外部展示事件与高亮
        onEventFocus(currentEvent);

        // 计算停留时间
        var dwellTime = FAULT_DWELL_BASE;
        var fault = currentEvent.raw;
        if (fault.severity === 'critical') {
            dwellTime = FAULT_DWELL_CRITICAL;
        } else if (fault.severity === 'major') {
            dwellTime = 30000;
        }

        timer = setTimeout(function () {
            onEventLeave(currentEvent);
            // 自上而下切换到下一个事件
            currentIndex = (currentIndex + 1) % eventQueue.length;
            _setState(STATE.GLOBAL_CRUISE); // 下一个事件切换前恢复默认 Cruise
            _runStateMachine();
        }, dwellTime);
    }

    /* ── 割接、重保事件非飞行聚焦 ── */
    function _executeNonFaultEventFocus() {
        // 保证地图返回全国视图并执行背景巡航旋转，消除上一个故障聚焦的局部摄像机状态
        MapEngine.resetView().then(function () {
            MapEngine.rotateTo(10, 20000);
        });

        // 通知外部展示事件与高亮
        onEventFocus(currentEvent);

        // 重保/割接停留 20 秒
        var dwellTime = EVENT_DWELL_DEFAULT;

        timer = setTimeout(function () {
            onEventLeave(currentEvent);
            // 自上而下切换到下一个事件
            currentIndex = (currentIndex + 1) % eventQueue.length;
            _runStateMachine();
        }, dwellTime);
    }

    return {
        STATE,
        start,
        stop,
        togglePause,
        updateEventQueue,
        focusOnEvent,
        getState
    };
})();
