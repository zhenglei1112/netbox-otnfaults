/**
 * OTN 大屏 - 智能播控引擎 (Directing Engine)
 * 
 * 基于状态机的自动化播控系统，管理摄像机视角自动流转。
 * 
 * 状态流:
 *   GLOBAL_CRUISE → FAULT_INTERRUPT → CAMERA_FLIGHT → FAULT_ANALYSIS → (返回巡航)
 *   无故障时保持 GLOBAL_CRUISE 循环
 */
window.DirectingEngine = (function () {
    'use strict';

    /* ── 状态常量 ── */
    const STATE = {
        GLOBAL_CRUISE: 'GLOBAL_CRUISE',
        FAULT_INTERRUPT: 'FAULT_INTERRUPT',
        CAMERA_FLIGHT: 'CAMERA_FLIGHT',
        FAULT_ANALYSIS: 'FAULT_ANALYSIS',
    };

    /* ── 状态中文名 ── */
    const STATE_NAMES = {
        GLOBAL_CRUISE: '全局巡航',
        FAULT_INTERRUPT: '故障捕获',
        CAMERA_FLIGHT: '视角飞行',
        FAULT_ANALYSIS: '故障聚焦',
    };



    /* ── 内部状态 ── */
    let currentState = STATE.GLOBAL_CRUISE;
    let cruiseBearing = 0;
    let faultQueue = [];         // 按优先级排序的故障队列
    let currentFault = null;     // 当前展示中的故障
    let lastShownFaultIds = [];  // 已展示过的故障ID
    let timer = null;
    let running = false;
    let paused = false;

    /* ── 回调 ── */
    let onStateChange = function () { };
    let onFaultFocus = function () { };
    let onFaultLeave = function () { };

    /* ── 时间参数 (ms) ── */
    const CRUISE_ROTATE_DURATION = 40000;   // 巡航旋转周期
    const FAULT_DWELL_BASE = 20000;         // 故障基础停留时间
    const FAULT_DWELL_CRITICAL = 40000;     // 致命故障停留时间
    const CRUISE_DWELL_TIME = 20000;        // 巡航停留时间（用于检查故障队列）
    const CONFIG = window.DASHBOARD_CONFIG;

    /**
     * 启动播控引擎
     */
    function start(callbacks) {
        onStateChange = callbacks.onStateChange || function () { };
        onFaultFocus = callbacks.onFaultFocus || function () { };
        onFaultLeave = callbacks.onFaultLeave || function () { };

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
     * 更新故障队列（由数据刷新触发）
     */
    function updateFaultQueue(faults) {
        // 已按优先级排序
        faultQueue = faults.slice();

        // 检测新的高优故障，触发中断
        if (faultQueue.length > 0 && _shouldInterrupt()) {
            _triggerFaultInterrupt();
        }
    }

    /**
     * 手动跳转到指定故障
     */
    function focusOnFault(fault) {
        if (timer) clearTimeout(timer);
        currentFault = fault;
        _setState(STATE.CAMERA_FLIGHT);
        _executeCameraFlight();
    }

    /**
     * 获取当前状态
     */
    function getState() {
        return { state: currentState, stateName: STATE_NAMES[currentState], fault: currentFault };
    }

    /* ═══ 状态机核心 ═══ */

    function _setState(newState) {
        const oldState = currentState;
        currentState = newState;
        onStateChange({
            from: oldState,
            to: newState,
            name: STATE_NAMES[newState],
            fault: currentFault,
        });
    }

    function _runStateMachine() {
        if (!running || paused) return;
        if (timer) clearTimeout(timer);

        switch (currentState) {
            case STATE.GLOBAL_CRUISE:
                _executeGlobalCruise();
                break;
            case STATE.FAULT_INTERRUPT:
                _executeFaultInterrupt();
                break;
            case STATE.CAMERA_FLIGHT:
                _executeCameraFlight();
                break;
            case STATE.FAULT_ANALYSIS:
                _executeFaultAnalysis();
                break;
        }
    }

    /* ── 全局巡航 ── */
    let cruiseStep = 0;           // 巡航步数计数，用于计算摆动序列

    function _executeGlobalCruise() {
        // 飞回全国视图 (MapEngine.resetView 现在保持当前角度)
        MapEngine.resetView().then(function () {
            // 始终以初始化位置 (Bearing = 0) 作为摆动的中心基准
            // 摆动序列: 0 -> 10 -> -10 -> 10 ...
            var swingRange = 10;
            var targetBearing = 0;

            if (cruiseStep > 0) {
                // 如果不是第一次进入巡航，则在 10 和 -10 之间交替
                targetBearing = (cruiseStep % 2 === 1) ? swingRange : -swingRange;
            } else {
                // 第一次进入巡航，先向正向偏转
                targetBearing = swingRange;
            }

            cruiseStep++;

            // 执行极慢速旋转
            MapEngine.rotateTo(targetBearing, 25000);

            // 等待后检查故障队列，有故障则切换到故障流程，否则继续巡航
            timer = setTimeout(function () {
                if (faultQueue.length > 0) {
                    _setState(STATE.FAULT_INTERRUPT);
                } else {
                    // 无故障，继续全国巡航
                    _setState(STATE.GLOBAL_CRUISE);
                }
                _runStateMachine();
            }, CRUISE_DWELL_TIME);
        });
    }

    /* ── 故障中断检测 ── */
    function _shouldInterrupt() {
        if (currentState === STATE.FAULT_ANALYSIS || currentState === STATE.CAMERA_FLIGHT) {
            // 只允许更高优先级故障抢占
            if (currentFault && faultQueue.length > 0) {
                return faultQueue[0].priority_score > currentFault.priority_score * 1.5;
            }
            return false;
        }
        // 检查是否有未展示过的故障
        var topFault = faultQueue[0];
        if (topFault && lastShownFaultIds.indexOf(topFault.id) === -1) {
            return true;
        }
        return false;
    }

    function _triggerFaultInterrupt() {
        if (timer) clearTimeout(timer);
        _setState(STATE.FAULT_INTERRUPT);
        _runStateMachine();
    }

    /* ── 故障中断处理 ── */
    function _executeFaultInterrupt() {
        // 从队列中取出最高优先级且未展示过的故障
        currentFault = null;
        for (var i = 0; i < faultQueue.length; i++) {
            if (lastShownFaultIds.indexOf(faultQueue[i].id) === -1) {
                currentFault = faultQueue[i];
                break;
            }
        }

        if (!currentFault && faultQueue.length > 0) {
            // 所有故障已展示过，重置记录并取第一个
            lastShownFaultIds = [];
            currentFault = faultQueue[0];
        }

        if (!currentFault) {
            // 无故障可展示，回到巡航
            _setState(STATE.GLOBAL_CRUISE);
            _runStateMachine();
            return;
        }

        lastShownFaultIds.push(currentFault.id);
        _setState(STATE.CAMERA_FLIGHT);
        _runStateMachine();
    }

    /* ── 摄像机飞行 ── */
    function _executeCameraFlight() {
        if (!currentFault) {
            _setState(STATE.GLOBAL_CRUISE);
            _runStateMachine();
            return;
        }

        // 计算飞行时间（基于距离）
        var map = MapEngine.getMap();
        var currentCenter = map ? map.getCenter() : { lng: CONFIG.mapCenter[0], lat: CONFIG.mapCenter[1] };
        var dx = currentFault.lng - currentCenter.lng;
        var dy = currentFault.lat - currentCenter.lat;
        var distance = Math.sqrt(dx * dx + dy * dy);
        var duration = Math.min(6000, Math.max(3000, distance * 300));

        MapEngine.flyTo(currentFault.lng, currentFault.lat, 8, {
            duration: duration,
            pitch: 55,
        }).then(function () {
            _setState(STATE.FAULT_ANALYSIS);
            _runStateMachine();
        });
    }

    /* ── 故障深度分析 ── */
    function _executeFaultAnalysis() {
        if (!currentFault) {
            _setState(STATE.GLOBAL_CRUISE);
            _runStateMachine();
            return;
        }

        // 通知外部展示故障详情
        onFaultFocus(currentFault);

        // 计算停留时间
        var dwellTime = FAULT_DWELL_BASE;
        if (currentFault.severity === 'critical') {
            dwellTime = FAULT_DWELL_CRITICAL;
        } else if (currentFault.severity === 'major') {
            dwellTime = 30000;
        }

        timer = setTimeout(function () {
            onFaultLeave(currentFault);
            currentFault = null;

            // 检查是否还有更多故障要展示
            var hasMore = faultQueue.some(function (f) {
                return lastShownFaultIds.indexOf(f.id) === -1;
            });

            if (hasMore) {
                _setState(STATE.FAULT_INTERRUPT);
            } else {
                _setState(STATE.GLOBAL_CRUISE);
            }
            _runStateMachine();
        }, dwellTime);
    }

    return {
        STATE,
        start,
        stop,
        togglePause,
        updateFaultQueue,
        focusOnFault,
        getState
    };
})();
