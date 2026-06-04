/**
 * OTN 大屏 - 布局管理器
 *
 * 根据数据状态自动判定并切换大屏布局模式，实现弹性自适应。
 * 
 * 布局状态：
 *   STATE_FULL        - 割接+重保都有数据（标准满屏）
 *   STATE_NO_CUTOVER  - 无割接，有重保（右侧收缩+地图放大）
 *   STATE_NO_HEAVY    - 有割接，无重保（底部收缩）
 *   STATE_OVERVIEW    - 都没有（运行总览模式）
 */
window.LayoutManager = (function () {
    'use strict';

    /** @type {string} 当前布局状态 */
    let _currentLayout = '';

    /** @type {string} 当前割接显示模式 */
    let _currentCutoverMode = '';

    /** @type {string} 当前重保显示模式 */
    let _currentHeavyDutyMode = '';

    /** 布局状态常量 */
    const LAYOUT = {
        FULL: 'layout-full',
        NO_CUTOVER: 'layout-no-cutover',
        NO_HEAVY: 'layout-no-heavy',
        OVERVIEW: 'layout-overview',
    };

    /** 割接模块显示模式 */
    const CUTOVER_MODE = {
        EMPTY: 'empty-card',
        CARD_LIST: 'card-list',
        COMPACT_LIST: 'compact-list',
        GROUPED_SCROLL: 'grouped-scroll',
    };

    /** 重保模块显示模式 */
    const HEAVY_DUTY_MODE = {
        QUIET_HINT: 'quiet-hint',
        HORIZONTAL_CARDS: 'horizontal-cards',
        BOTTOM_LIST: 'bottom-list',
        CAROUSEL_GROUPED: 'carousel-grouped',
    };

    /** 空状态文案 */
    const EMPTY_TEXT = {
        cutover: {
            title: '未来7天暂无割接计划',
            subtitle: '',
        },
        heavy_duty: {
            title: '近期暂无重保任务',
            subtitle: '当前网络按常规运行策略保障',
        },
        overview: {
            title: '当前网络处于常规运行监控状态',
            subtitle: '所有系统运行正常',
        },
    };

    /**
     * 根据数据判定布局状态
     * @param {Object} data - API 返回的完整数据
     * @returns {string} 布局状态类名
     */
    function _determineLayout(data) {
        var hasCutovers = (data.cutovers || []).length > 0;
        var hasHeavyDuties = (data.heavy_duties || []).length > 0;

        if (hasCutovers && hasHeavyDuties) return LAYOUT.FULL;
        if (!hasCutovers && hasHeavyDuties) return LAYOUT.NO_CUTOVER;
        if (hasCutovers && !hasHeavyDuties) return LAYOUT.NO_HEAVY;
        return LAYOUT.OVERVIEW;
    }

    /**
     * 根据割接数量判定显示模式
     * @param {number} count - 割接数量
     * @returns {string} 显示模式
     */
    function _determineCutoverMode(count) {
        if (count === 0) return CUTOVER_MODE.EMPTY;
        if (count <= 3) return CUTOVER_MODE.CARD_LIST;
        if (count <= 8) return CUTOVER_MODE.COMPACT_LIST;
        return CUTOVER_MODE.GROUPED_SCROLL;
    }

    /**
     * 根据重保数量判定显示模式
     * @param {number} count - 重保数量
     * @returns {string} 显示模式
     */
    function _determineHeavyDutyMode(count) {
        if (count === 0) return HEAVY_DUTY_MODE.QUIET_HINT;
        if (count <= 2) return HEAVY_DUTY_MODE.HORIZONTAL_CARDS;
        if (count <= 5) return HEAVY_DUTY_MODE.BOTTOM_LIST;
        return HEAVY_DUTY_MODE.CAROUSEL_GROUPED;
    }

    /**
     * 应用布局状态到 DOM
     * @param {string} layout - 布局状态类名
     */
    function _applyLayout(layout) {
        var main = document.getElementById('main-content');
        var body = document.body;
        if (!main) return;

        // 移除所有布局类
        Object.values(LAYOUT).forEach(function (cls) {
            main.classList.remove(cls);
            body.classList.remove(cls);
        });

        // 应用新布局
        main.classList.add(layout);
        body.classList.add(layout);
    }

    /**
     * 更新辅助信息卡片可见性（仅在没有割接任务且无处理中故障时才显示）
     * @param {Object} data - API 返回的完整数据
     */
    function _updateAuxiliaryVisibility(data) {
        var auxCard = document.getElementById('auxiliary-info-card');
        if (!auxCard) return;

        var cutoverCount = (data.cutovers || []).length;
        var activeFaults = (data.summary && typeof data.summary.active_faults !== 'undefined') ? data.summary.active_faults : 0;

        if (cutoverCount === 0 && activeFaults === 0) {
            auxCard.classList.remove('hidden');
        } else {
            auxCard.classList.add('hidden');
        }
    }

    /**
     * 主更新入口：根据数据更新布局
     * @param {Object} data - API 返回的完整数据
     */
    function update(data) {
        var newLayout = _determineLayout(data);
        var cutoverCount = (data.cutovers || []).length;
        var heavyDutyCount = (data.heavy_duties || []).length;
        var newCutoverMode = _determineCutoverMode(cutoverCount);
        var newHeavyDutyMode = _determineHeavyDutyMode(heavyDutyCount);

        // 仅在状态变化时切换
        if (newLayout !== _currentLayout) {
            console.log('[Layout] 布局切换:', _currentLayout || '(初始)', '→', newLayout);
            _currentLayout = newLayout;
            _applyLayout(newLayout);
        }

        // 每次更新数据时都重新判定辅助信息卡片的可见性
        _updateAuxiliaryVisibility(data);

        _currentCutoverMode = newCutoverMode;
        _currentHeavyDutyMode = newHeavyDutyMode;
    }

    /**
     * 获取当前状态
     */
    function getState() {
        return {
            layout: _currentLayout,
            cutoverMode: _currentCutoverMode,
            heavyDutyMode: _currentHeavyDutyMode,
        };
    }

    return {
        update: update,
        getState: getState,
        LAYOUT: LAYOUT,
        CUTOVER_MODE: CUTOVER_MODE,
        HEAVY_DUTY_MODE: HEAVY_DUTY_MODE,
        EMPTY_TEXT: EMPTY_TEXT,
    };
})();
