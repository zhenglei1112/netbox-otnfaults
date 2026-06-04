/**
 * OTN 大屏 - 布局与数据调试控制台
 * 
 * 仅在 URL 带有 ?debug=true 或 localStorage.debug == 'true' 时激活。
 * 允许在无 NetBox 数据环境时切换 5 种弹性布局状态进行前端验证。
 */
(function () {
    'use strict';

    // 检查是否开启调试模式
    var isDebug = window.location.search.indexOf('debug=true') !== -1 || 
                  localStorage.getItem('debug') === 'true';

    if (!isDebug) {
        return; // 非调试模式下直接退出，不引入任何多余逻辑
    }

    console.log('%c[Dashboard Debug] 调试模式已开启！可使用悬浮面板测试各种布局。', 'color: #00d2ff; font-weight: bold;');

    // 静态后备数据（防止大屏第一帧无 API 响应）
    var BACKUP_SITES = [
        { id: 1, name: "北京核心站", lat: 39.9042, lng: 116.4074 },
        { id: 2, name: "上海核心站", lat: 31.2304, lng: 121.4737 },
        { id: 3, name: "广州核心站", lat: 23.1291, lng: 113.2644 },
        { id: 4, name: "成都传输节点", lat: 30.5728, lng: 104.0668 },
        { id: 5, name: "武汉传输节点", lat: 30.5928, lng: 114.3055 }
    ];

    var BACKUP_TREND = [];
    for (var i = 24; i > 0; i--) {
        var time = new Date(Date.now() - i * 3600000);
        BACKUP_TREND.push({
            hour: String(time.getHours()).padStart(2, '0') + ':00',
            count: Math.floor(Math.random() * 3)
        });
    }

    // 基础结构生成器
    function createBaseData(cutovers, heavyDuties, faults) {
        cutovers = cutovers || [];
        heavyDuties = heavyDuties || [];
        faults = faults || [];

        return {
            timestamp: new Date().toISOString(),
            summary: {
                total_faults: faults.length + 12,
                active_faults: faults.length,
                temporary_recovery_faults: 8,
                suspended_faults: 4,
                upcoming_cutovers: cutovers.length,
                active_heavy_duties: heavyDuties.length,
                health_score: Math.max(0, 100 - faults.length * 5)
            },
            active_faults: faults,
            trend_24h: BACKUP_TREND,
            sites: BACKUP_SITES,
            fault_paths: [],
            ticker_events: faults.map(function(f) {
                return {
                    fault_number: f.fault_number,
                    category: f.category_display,
                    site_a: f.site_a,
                    sites_z: f.sites_z,
                    time: "刚刚",
                    duration: "进行中",
                    status: "处理中",
                    severity: f.severity
                };
            }),
            cutovers: cutovers,
            heavy_duties: heavyDuties
        };
    }

    // 1. 标准满屏数据
    var dataFull = createBaseData(
        [
            {
                id: 101,
                cutover_no: "CUT-20260604-01",
                status: "applying",
                status_display: "审批中",
                planned_cutover_time: new Date(Date.now() + 7200000).toISOString(),
                planned_time_display: "今日 14:00",
                minutes_until: 120,
                province: "北京市",
                location: "北京核心A机房 传输设备升级",
                site_a: "北京核心站",
                sites_z: ["上海核心站"],
                impact_count: 5,
                implementation_unit: "北京传输维护班",
                contact: "张工 (13800000000)"
            },
            {
                id: 102,
                cutover_no: "CUT-20260605-02",
                status: "pending_implementation",
                status_display: "待实施",
                planned_cutover_time: new Date(Date.now() + 86400000).toISOString(),
                planned_time_display: "明日 04:00",
                minutes_until: 1440,
                province: "广东省",
                location: "广州核心站 光缆割接",
                site_a: "广州核心站",
                sites_z: ["深圳主控站"],
                impact_count: 2,
                implementation_unit: "广东传输维护组",
                contact: "李工 (13900000000)"
            }
        ],
        [
            {
                id: 201,
                name: "2026年夏季重要高考期间业务保障",
                description: "全国高考保障期间，要求全网封网，停止一切常规割接和变更，加强核心链路监测。",
                start_time_display: "06月07日 00:00",
                end_time_display: "06月09日 18:00"
            }
        ],
        [
            {
                id: 1,
                fault_number: "FLT-20260604-01",
                lat: 31.2304,
                lng: 121.4737,
                category: "fiber_break",
                category_display: "光缆中断",
                status: "processing",
                status_display: "处理中",
                urgency: "high",
                urgency_display: "高紧急",
                severity: "critical",
                priority_score: 8.5,
                site_a: "北京核心站",
                sites_z: ["上海核心站"],
                province: "上海市",
                reason: "市政施工开挖造成光缆中断",
                occurrence_time: new Date().toISOString(),
                impact_count: 4,
                impact_names: ["京沪干线 bare_fiber", "京沪备用链路 circuit"],
                details: "上海核心站至北京核心站方向，第 4 芯和第 5 芯衰耗巨大，经排查光缆已彻底中断，抢修人员已出发。"
            }
        ]
    );

    // 2. 无割接数据
    var dataNoCutover = createBaseData(
        [],
        [
            {
                id: 201,
                name: "2026年夏季重要高考期间业务保障",
                description: "全国高考保障期间，要求全网封网，停止一切常规割接和变更，加强核心链路监测。",
                start_time_display: "06月07日 00:00",
                end_time_display: "06月09日 18:00"
            }
        ],
        [
            {
                id: 1,
                fault_number: "FLT-20260604-01",
                lat: 31.2304,
                lng: 121.4737,
                category: "power_fault",
                category_display: "供电故障",
                status: "processing",
                status_display: "处理中",
                urgency: "medium",
                urgency_display: "中紧急",
                severity: "major",
                priority_score: 5.0,
                site_a: "广州核心站",
                sites_z: ["深圳主控站"],
                province: "广东省",
                reason: "机房配电箱短路故障",
                occurrence_time: new Date().toISOString(),
                impact_count: 1,
                impact_names: ["广深普通专线"],
                details: "广州核心站蓄电池供电中，市电中断已超过 10 分钟，抢修班组正在调集应急发电机前往现场。"
            }
        ]
    );

    // 3. 无重保数据
    var dataNoHeavy = createBaseData(
        dataFull.cutovers,
        [],
        dataFull.active_faults
    );

    // 4. 运行总览模式 (无割接、无重保、无故障)
    var dataOverview = createBaseData([], [], []);

    // 5. 极限负载数据 (割接数量 > 8, 重保数量 > 5)
    var maxCutovers = [];
    for (var k = 1; k <= 9; k++) {
        var statusVal = k % 2 === 0 ? "applying" : "pending_implementation";
        var statusDisp = k % 2 === 0 ? "审批中" : "待实施";
        maxCutovers.push({
            id: 100 + k,
            cutover_no: "CUT-2026060" + k + "-0" + k,
            status: statusVal,
            status_display: statusDisp,
            planned_cutover_time: new Date(Date.now() + k * 3600000 * 6).toISOString(),
            planned_time_display: "06-0" + (4 + Math.floor(k/3)) + " 0" + (k+1) + ":00",
            minutes_until: k * 360,
            province: ["北京市", "上海市", "广东省", "湖北省", "四川省"][k % 5],
            location: "节点 " + k + " 设备维护升级与光缆线路割接",
            site_a: ["北京核心站", "上海核心站", "广州核心站", "武汉传输节点", "成都传输节点"][k % 5],
            sites_z: [["上海核心站", "北京核心站", "深圳主控站", "南京站点", "重庆站点"][k % 5]],
            impact_count: k % 3,
            implementation_unit: "传输维护 " + k + " 组",
            contact: "联系人 " + k + " (1390000000" + k + ")"
        });
    }

    var maxHeavyDuties = [];
    var names = ["高考网络安全保障", "中非合作论坛峰会通信保障", "台风蓝色预警三级响应", "跨国光缆出口链路保驾护航", "国庆假期全网大检查", "南方暴雨防汛专项应急重保"];
    for (var m = 0; m < names.length; m++) {
        maxHeavyDuties.push({
            id: 300 + m,
            name: (m + 1) + ". " + names[m],
            description: "特级或一级重保指令，要求保障期间内重要客户业务零中断，关键站点双路电源保驾。",
            start_time_display: "06月" + (10 + m) + "日 00:00",
            end_time_display: "06月" + (12 + m) + "日 23:59"
        });
    }

    var dataMax = createBaseData(maxCutovers, maxHeavyDuties, dataFull.active_faults);


    // 注入 DOM 调试面板
    function injectPanel() {
        var html = 
            '<div id="dashboard-debug-panel" class="debug-panel folded">' +
            '    <div class="debug-panel-toggle" id="debug-panel-toggle">🔧 调试</div>' +
            '    <div class="debug-panel-body">' +
            '        <div class="debug-panel-title">布局与数据调试</div>' +
            '        <div class="debug-btn-group">' +
            '            <button class="debug-btn" id="btn-dbg-full" data-state="full">1. 标准满屏</button>' +
            '            <button class="debug-btn" id="btn-dbg-nocut" data-state="no_cutover">2. 无割接计划</button>' +
            '            <button class="debug-btn" id="btn-dbg-noheavy" data-state="no_heavy">3. 无重保任务</button>' +
            '            <button class="debug-btn" id="btn-dbg-overview" data-state="overview">4. 运行总览模式</button>' +
            '            <button class="debug-btn" id="btn-dbg-max" data-state="max_data">5. 极限负载模式</button>' +
            '        </div>' +
            '        <hr class="debug-divider"/>' +
            '        <div class="debug-btn-group">' +
            '            <button class="debug-btn debug-btn-danger" id="btn-dbg-realtime">🔌 恢复实时数据</button>' +
            '        </div>' +
            '    </div>' +
            '</div>';

        var css = 
            '.debug-panel {' +
            '    position: fixed;' +
            '    left: 20px;' +
            '    bottom: 50px;' +
            '    z-index: 99999;' +
            '    background: rgba(10, 25, 50, 0.85);' +
            '    backdrop-filter: blur(10px);' +
            '    -webkit-backdrop-filter: blur(10px);' +
            '    border: 1px solid rgba(0, 210, 255, 0.3);' +
            '    border-radius: 8px;' +
            '    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), inset 0 0 10px rgba(0, 210, 255, 0.1);' +
            '    width: 200px;' +
            '    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s;' +
            '    font-family: "Noto Sans SC", sans-serif;' +
            '}' +
            '.debug-panel.folded {' +
            '    transform: translateY(calc(100% - 32px));' +
            '}' +
            '.debug-panel-toggle {' +
            '    background: rgba(0, 210, 255, 0.15);' +
            '    color: #00d2ff;' +
            '    padding: 6px 12px;' +
            '    font-size: 12px;' +
            '    font-weight: bold;' +
            '    cursor: pointer;' +
            '    text-align: center;' +
            '    border-bottom: 1px solid rgba(0, 210, 255, 0.2);' +
            '    border-top-left-radius: 7px;' +
            '    border-top-right-radius: 7px;' +
            '    user-select: none;' +
            '    transition: background 0.2s;' +
            '}' +
            '.debug-panel-toggle:hover {' +
            '    background: rgba(0, 210, 255, 0.3);' +
            '}' +
            '.debug-panel-body {' +
            '    padding: 12px;' +
            '}' +
            '.debug-panel-title {' +
            '    font-size: 11px;' +
            '    color: #8b9bb4;' +
            '    margin-bottom: 8px;' +
            '    text-transform: uppercase;' +
            '    letter-spacing: 0.5px;' +
            '    border-left: 2px solid #00d2ff;' +
            '    padding-left: 6px;' +
            '}' +
            '.debug-btn-group {' +
            '    display: flex;' +
            '    flex-direction: column;' +
            '    gap: 6px;' +
            '}' +
            '.debug-btn {' +
            '    background: rgba(255, 255, 255, 0.05);' +
            '    border: 1px solid rgba(255, 255, 255, 0.1);' +
            '    border-radius: 4px;' +
            '    color: #c8d2e6;' +
            '    padding: 6px 8px;' +
            '    font-size: 11px;' +
            '    text-align: left;' +
            '    cursor: pointer;' +
            '    transition: all 0.2s;' +
            '    outline: none;' +
            '}' +
            '.debug-btn:hover {' +
            '    background: rgba(0, 210, 255, 0.1);' +
            '    border-color: rgba(0, 210, 255, 0.4);' +
            '    color: #ffffff;' +
            '}' +
            '.debug-btn.active {' +
            '    background: rgba(0, 210, 255, 0.2);' +
            '    border-color: #00d2ff;' +
            '    color: #ffffff;' +
            '    box-shadow: 0 0 8px rgba(0, 210, 255, 0.3);' +
            '    font-weight: bold;' +
            '}' +
            '.debug-btn-danger {' +
            '    background: rgba(255, 30, 30, 0.1);' +
            '    border-color: rgba(255, 30, 30, 0.2);' +
            '    color: #ff8b8b;' +
            '    text-align: center;' +
            '    margin-top: 4px;' +
            '}' +
            '.debug-btn-danger:hover {' +
            '    background: rgba(255, 30, 30, 0.25);' +
            '    border-color: #ff1e1e;' +
            '    color: #ffffff;' +
            '}' +
            '.debug-divider {' +
            '    border: 0;' +
            '    border-top: 1px solid rgba(255, 255, 255, 0.08);' +
            '    margin: 8px 0;' +
            '}';

        // 注入 CSS
        var styleEl = document.createElement('style');
        styleEl.type = 'text/css';
        styleEl.innerHTML = css;
        document.head.appendChild(styleEl);

        // 注入 HTML
        var div = document.createElement('div');
        div.innerHTML = html;
        document.body.appendChild(div.firstChild);

        // 绑定折叠切换
        var toggle = document.getElementById('debug-panel-toggle');
        var panel = document.getElementById('dashboard-debug-panel');
        if (toggle && panel) {
            toggle.addEventListener('click', function () {
                panel.classList.toggle('folded');
            });
        }

        // 清除所有激活状态
        function clearActive() {
            var btns = document.querySelectorAll('.debug-btn');
            for (var idx = 0; idx < btns.length; idx++) {
                btns[idx].classList.remove('active');
            }
        }

        // 绑定数据切换逻辑
        function bindBtn(id, data, activeCls) {
            var btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', function () {
                    clearActive();
                    btn.classList.add('active');
                    
                    // 暂停大屏常规的自动刷新轮询
                    if (window.DashboardApp && window.DashboardApp.stopPolling) {
                        window.DashboardApp.stopPolling();
                    }

                    // 注入 Mock 数据
                    if (window.DashboardApp && window.DashboardApp.processData) {
                        console.log('[Dashboard Debug] 注入 Mock 数据状态: ' + id);
                        window.DashboardApp.processData(data);
                    } else {
                        console.warn('[Dashboard Debug] DashboardApp.processData 暂不可用');
                    }
                });
            }
        }

        bindBtn('btn-dbg-full', dataFull);
        bindBtn('btn-dbg-nocut', dataNoCutover);
        bindBtn('btn-dbg-noheavy', dataNoHeavy);
        bindBtn('btn-dbg-overview', dataOverview);
        bindBtn('btn-dbg-max', dataMax);

        // 绑定恢复实时数据
        var btnRealtime = document.getElementById('btn-dbg-realtime');
        if (btnRealtime) {
            btnRealtime.addEventListener('click', function () {
                clearActive();
                btnRealtime.classList.add('active');

                // 启动轮询并拉取最新数据
                if (window.DashboardApp) {
                    if (window.DashboardApp.startPolling) {
                        window.DashboardApp.startPolling();
                    }
                    if (window.DashboardApp.fetchData) {
                        window.DashboardApp.fetchData();
                    }
                }
                setTimeout(clearActive, 1000);
            });
        }
    }

    // 页面完全加载后注入调试面板
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectPanel);
    } else {
        injectPanel();
    }

})();
