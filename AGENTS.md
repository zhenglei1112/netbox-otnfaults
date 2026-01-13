# 地图弹窗淡入淡出动画实现

## 概述

本项目为故障分布图的三种类型弹窗实现了统一的淡入淡出动画效果:
- **故障弹窗**(悬停触发): 带延迟关闭机制
- **站点弹窗**(点击触发): 标准淡入淡出
- **路径弹窗**(点击/fly to触发): 标准淡入淡出

## 技术方案

### 1. CSS动画实现

**文件**: `netbox_otnfaults/static/netbox_otnfaults/css/fault_popup_animations.css`

**核心特点**:
- 使用`margin-top`替代`transform: translateY()`实现位移动画,避免与MapLibre Popup的`transform`定位冲突
- 支持三种弹窗类名: `.fault-popup-container`, `.stats-popup`, `.animated-popup`
- 使用GPU加速优化性能

**动画参数**:
```css
/* 淡入: 250ms, ease-out, 向上8px */
.popup-enter-active {
    animation: faultPopupFadeIn 250ms ease-out forwards;
}

/* 淡出: 200ms, ease-in, 向下8px */
.popup-leave-active {
    animation: faultPopupFadeOut 200ms ease-in forwards;
}
```

**关键帧定义**:
- `faultPopupFadeIn`: opacity 0→1, margin-top 8px→0
- `faultPopupFadeOut`: opacity 1→0, margin-top 0→8px

### 2. JavaScript实现

**文件**: `netbox_otnfaults/static/netbox_otnfaults/js/modes/fault_mode.js`

#### 2.1 故障弹窗(悬停触发)

**特殊机制**:
- **防抖标志**: `_isHandlingPopupInteraction` (100ms内只处理一次mouseenter)
- **故障ID防抖**: `currentFaultId` (避免鼠标事件循环)
- **延迟关闭**: `popupCloseTimer` (300ms延迟) + `popupRemoveTimer` (200ms动画)
- **取消关闭**: 鼠标移到弹窗上可清除定时器并反转动画

**核心代码**:
```javascript
// 显示时
requestAnimationFrame(() => {
  popupEl.classList.add('popup-enter-active');
});

// 淡入完成后清理类
popupEl.addEventListener('animationend', (e) => {
  if (e.animationName === 'faultPopupFadeIn') {
    popupEl.classList.remove('popup-enter-active');
  }
  // 注意:淡出动画结束不清理类,避免闪烁
}, { once: true });

// 关闭时
_startPopupCloseTimer() {
  setTimeout(() => {
    popupEl.classList.add('popup-leave-active');
    setTimeout(() => {
      popup.remove();
    }, 200); // 等待淡出动画完成
  }, 300); // 延迟关闭
}
```

#### 2.2 站点/路径弹窗(点击触发)

**实现方式**: 使用通用辅助函数 `_addPopupAnimation(popup)`

**核心代码**:
```javascript
_addPopupAnimation(popup) {
  const popupEl = popup.getElement();
  
  // 淡入动画
  requestAnimationFrame(() => {
    popupEl.classList.add('popup-enter-active');
  });
  
  // 清理淡入动画类
  popupEl.addEventListener('animationend', (e) => {
    if (e.animationName === 'faultPopupFadeIn') {
      popupEl.classList.remove('popup-enter-active');
    }
  }, { once: true });
  
  // 拦截关闭按钮,添加淡出动画
  const closeButton = popupEl.querySelector('.maplibregl-popup-close-button');
  if (closeButton) {
    closeButton.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      
      // 播放淡出动画
      popupEl.classList.add('popup-leave-active');
      
      // 动画完成后移除DOM
      setTimeout(() => {
        popup.remove();
      }, 200);
    });
  }
}

// 使用
const popup = new maplibregl.Popup(...)
  .setLngLat(...)
  .setHTML(...)
  .addTo(this.map);

this._addPopupAnimation(popup);
```

### 3. 关键问题解决

#### 3.1 弹窗定位错误
**问题**: 使用`transform: translateY()`导致弹窗固定在左上角  
**原因**: 与MapLibre Popup的`transform: translate()`定位冲突  
**解决**: 改用`margin-top`实现垂直位移

#### 3.2 淡出闪烁
**问题**: 淡出动画结束后弹窗闪现  
**原因**: `animationend`移除`popup-leave-active`类导致opacity恢复  
**解决**: 淡出动画结束不清理类,直接移除DOM

#### 3.3 动画重复播放
**问题**: 鼠标在弹窗淡入时就在弹窗上,导致mouseenter重复触发  
**原因**: 浏览器反复触发mouseenter事件  
**解决**: 添加100ms防抖标志`_isHandlingPopupInteraction`

#### 3.4 鼠标事件循环
**问题**: 弹窗覆盖故障图标,导致动画不停重复  
**原因**: 弹窗覆盖鼠标 → mouseleave → 鼠标微移 → mouseenter → 循环  
**解决**: 保存`currentFaultId`,相同故障不重复显示

#### 3.5 延迟关闭与淡出冲突
**问题**: 用户在淡出动画期间移到弹窗上无法取消关闭  
**原因**: 淡出动画的200ms移除定时器无法被取消  
**解决**: 添加`popupRemoveTimer`追踪,mouseenter时清除并反转动画

### 4. 配置常量

**文件**: `fault_mode.js`

```javascript
POPUP_ANIMATION: {
  FADE_IN_DURATION: 250,    // 淡入动画时长(ms)
  FADE_OUT_DURATION: 200,   // 淡出动画时长(ms)
  CLOSE_DELAY: 300,         // 延迟关闭时长(ms)
}
```

### 5. 事件监听器管理

**防止内存泄漏**:
```javascript
// 保存监听器引用
this.currentPopupListeners = {
  'animationend': handleAnimationEnd,
  'mouseenter': handleMouseEnter,
  'mouseleave': handleMouseLeave
};

// 清理
_cleanupPopupListeners() {
  if (this.currentPopupListeners && this.currentFaultPopup) {
    const popupEl = this.currentFaultPopup.getElement();
    Object.entries(this.currentPopupListeners).forEach(([event, handler]) => {
      popupEl.removeEventListener(event, handler);
    });
    this.currentPopupListeners = null;
  }
}
```

## 性能优化

- **GPU加速**: `backface-visibility: hidden`
- **will-change**: 提前告知浏览器变化属性
- **requestAnimationFrame**: 确保动画在浏览器重绘前执行
- **事件监听器清理**: 防止内存泄漏
- **防抖机制**: 避免重复处理事件

## 测试建议

1. **浏览器兼容性**: Chrome, Firefox, Edge, Safari
2. **性能**: 使用Chrome DevTools Performance监控帧率
3. **用户体验**:
   - 快速悬停切换故障点
   - 淡出期间移到弹窗上
   - 快速点击多个站点/路径
   - 鼠标在弹窗和故障图标重合位置

## 文件清单

### 新增
- `netbox_otnfaults/static/netbox_otnfaults/css/fault_popup_animations.css`

### 修改
- `netbox_otnfaults/templates/netbox_otnfaults/unified_map.html` - 引入CSS
- `netbox_otnfaults/static/netbox_otnfaults/js/modes/fault_mode.js` - 动画逻辑

## 扩展性

如需添加新的弹窗类型:
1. 确保弹窗有CSS类: `.stats-popup` 或 `.animated-popup`
2. 调用 `this._addPopupAnimation(popup)` 添加动画
3. CSS会自动应用到新弹窗

如需调整动画参数:
1. 修改 `POPUP_ANIMATION` 常量
2. 修改 `fault_popup_animations.css` 中的时长参数
3. 两处保持一致
