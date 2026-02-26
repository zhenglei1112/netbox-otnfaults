/**
 * 故障图标SVG模板
 * 用于SDF动态着色的纯白色图标
 */

const FAULT_SVG_ICONS = {
  fiber_break: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M 9 16 Q 11.5 12, 16 16 T 23 16" stroke="white" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="9" cy="16" r="1.2" fill="white"/>
    <circle cx="23" cy="16" r="1.2" fill="white"/>
  </svg>`,

  fiber_degradation: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M 9 16 Q 11.5 12, 16 16 T 23 16" stroke="white" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="9" cy="16" r="1.2" fill="white"/>
    <circle cx="23" cy="16" r="1.2" fill="white"/>
  </svg>`,

  fiber_jitter: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M 9 16 Q 11.5 12, 16 16 T 23 16" stroke="white" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="9" cy="16" r="1.2" fill="white"/>
    <circle cx="23" cy="16" r="1.2" fill="white"/>
  </svg>`,

  power_fault: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M 17 10 L 13 17 L 16 17 L 15 22 L 19 15 L 16 15 Z" fill="white"/>
  </svg>`,

  ac_fault: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <g stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <line x1="16" y1="9" x2="16" y2="23"/>
      <line x1="9.9" y1="12.5" x2="22.1" y2="19.5"/>
      <line x1="9.9" y1="19.5" x2="22.1" y2="12.5"/>
      <line x1="10" y1="16" x2="22" y2="16"/>
      <line x1="13" y1="10.5" x2="19" y2="21.5"/>
      <line x1="13" y1="21.5" x2="19" y2="10.5"/>
      <circle cx="16" cy="16" r="1.5" fill="white"/>
    </g>
  </svg>`,

  device_fault: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <rect x="11" y="11" width="10" height="10" fill="white" stroke="white" stroke-width="0.5"/>
    <g stroke="white" stroke-width="1.2" stroke-linecap="round">
      <line x1="14" y1="11" x2="14" y2="8"/>
      <line x1="18" y1="11" x2="18" y2="8"/>
      <line x1="14" y1="21" x2="14" y2="24"/>
      <line x1="18" y1="21" x2="18" y2="24"/>
      <line x1="11" y1="14" x2="8" y2="14"/>
      <line x1="11" y1="18" x2="8" y2="18"/>
      <line x1="21" y1="14" x2="24" y2="14"/>
      <line x1="21" y1="18" x2="24" y2="18"/>
    </g>
  </svg>`,

  other: `<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <circle cx="16" cy="16" r="6" stroke="white" stroke-width="1.8" fill="none"/>
  </svg>`
};

// 导出到全局
window.FAULT_SVG_ICONS = FAULT_SVG_ICONS;
