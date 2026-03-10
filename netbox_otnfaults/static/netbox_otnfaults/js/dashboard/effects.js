/**
 * OTN 大屏 - 视觉特效模块
 * 
 * 故障脉冲、冲击波、光流增强、面板动画等。
 */
window.Effects = (function () {
    'use strict';

    const COLORS = window.DASHBOARD_CONFIG.colors;
    let shockwaveContainer = null;

    /**
     * 初始化特效系统
     */
    function init() {
        // 冲击波容器
        shockwaveContainer = document.createElement('div');
        shockwaveContainer.id = 'shockwave-container';
        shockwaveContainer.style.cssText = 'position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:5;overflow:hidden;';
        var mapStage = document.getElementById('map-stage');
        if (mapStage) mapStage.appendChild(shockwaveContainer);
    }

    /**
     * 触发故障冲击波效果
     */
    function triggerShockwave(lng, lat, severity) {
        var map = MapEngine.getMap();
        if (!map || !shockwaveContainer) return;

        var point = map.project([lng, lat]);
        var color = COLORS.alert_colors[severity] || '#FADB14';

        // 创建冲击波元素
        var wave = document.createElement('div');
        wave.style.cssText =
            'position:absolute;' +
            'left:' + point.x + 'px;top:' + point.y + 'px;' +
            'width:200px;height:200px;' +
            'margin-left:-100px;margin-top:-100px;' +
            'border-radius:50%;' +
            'border:3px solid ' + color + ';' +
            'box-shadow: 0 0 20px ' + color + ', inset 0 0 20px ' + color + ';' +
            'opacity:0;' +
            'transform:scale(0);' +
            'animation: shockwave 2s ease-out forwards;';

        shockwaveContainer.appendChild(wave);

        // 第二波（延迟）
        setTimeout(function () {
            var wave2 = wave.cloneNode();
            wave2.style.animationDelay = '0.3s';
            shockwaveContainer.appendChild(wave2);
            setTimeout(function () { wave2.remove(); }, 2500);
        }, 300);

        // 清理
        setTimeout(function () { wave.remove(); }, 2500);
    }

    /**
     * 全屏红色闪烁（致命告警）
     */
    function flashCriticalAlert() {
        var overlay = document.createElement('div');
        overlay.style.cssText =
            'position:fixed;top:0;left:0;right:0;bottom:0;' +
            'background:radial-gradient(ellipse at center, rgba(255,30,30,0.15) 0%, transparent 70%);' +
            'z-index:999;pointer-events:none;' +
            'animation: pulse-critical 0.5s ease-in-out 3;';

        document.body.appendChild(overlay);
        setTimeout(function () { overlay.remove(); }, 1600);
    }

    /**
     * 面板入场动画
     */
    function animatePanelIn(element) {
        if (!element) return;
        element.style.opacity = '0';
        element.style.transform = 'translateY(10px)';
        element.style.transition = 'opacity 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)';

        requestAnimationFrame(function () {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        });
    }

    /**
     * 数字递增动画
     */
    function animateNumber(element, targetValue, duration) {
        if (!element) return;
        var startValue = parseInt(element.textContent) || 0;
        var startTime = Date.now();
        duration = duration || 1000;

        function update() {
            var elapsed = Date.now() - startTime;
            var progress = Math.min(elapsed / duration, 1);
            // easeOutQuart
            var eased = 1 - Math.pow(1 - progress, 4);
            var current = Math.round(startValue + (targetValue - startValue) * eased);
            element.textContent = current;
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    }

    /**
     * 更新播控指示器
     */
    function updateDirectingIndicator(stateInfo) {
        var icon = document.getElementById('directing-icon');
        var text = document.getElementById('directing-text');
        if (!icon || !text) return;

        text.textContent = stateInfo.name;

        switch (stateInfo.to) {
            case 'GLOBAL_CRUISE':
                icon.textContent = '⟳';
                icon.style.animation = 'spin 3s linear infinite';
                icon.style.color = 'var(--color-normal)';
                break;
            case 'REGION_TOUR':
                icon.textContent = '⊕';
                icon.style.animation = 'breathe-major 2s ease-in-out infinite';
                icon.style.color = 'var(--color-normal)';
                break;
            case 'FAULT_INTERRUPT':
            case 'CAMERA_FLIGHT':
                icon.textContent = '⚡';
                icon.style.animation = 'pulse-critical 0.8s ease-in-out infinite';
                icon.style.color = 'var(--color-critical)';
                break;
            case 'FAULT_ANALYSIS':
                icon.textContent = '◎';
                icon.style.animation = 'pulse-dot 2s ease-in-out infinite';
                icon.style.color = 'var(--color-major)';
                text.textContent = stateInfo.name + (stateInfo.fault ? ' · ' + stateInfo.fault.fault_number : '');
                break;
        }
    }

    return {
        init,
        triggerShockwave,
        flashCriticalAlert,
        animatePanelIn,
        animateNumber,
        updateDirectingIndicator
    };
})();
