# 故障等级与事件汇总悬停效果实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让“故障等级与事件汇总”指标块具有白色描边、轻微放大、上浮和明显阴影，并让键盘聚焦获得同等反馈。

**Architecture:** 保留现有 HTML 指标卡片及下钻逻辑，仅修改模板内局部 CSS。新增源码级回归测试锁定交互样式，并提升 CSS 静态资源版本避免浏览器缓存旧样式。

**Tech Stack:** Django template、CSS、Python unittest/pytest

---

### Task 1: 锁定汇总卡片高亮行为

**Files:**
- Create: `tests/test_statistics_impact_level_hover.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/statistics_dashboard.html`
- Modify: `PLAN.md`

- [x] **Step 1: 写失败测试**

测试读取模板并断言基础卡片预留透明内描边，`:hover` 与 `:focus-visible` 共享白色内描边、`translateY(-2px) scale(1.03)`、高层级和增强阴影，同时不再降低透明度；并断言 CSS 缓存版本从 `v=34` 提升。

- [x] **Step 2: 验证测试按预期失败**

运行：`python -m pytest tests/test_statistics_impact_level_hover.py -q`

预期：因模板尚无新的描边、缩放和聚焦规则而失败。

- [x] **Step 3: 实现最小样式变更**

在模板局部样式中为 `.impact-level-block-item` 增加透明内描边，并将悬停规则扩展为：

```css
.impact-level-block-item:hover,
.impact-level-block-item:focus-visible {
    transform: translateY(-2px) scale(1.03);
    box-shadow: inset 0 0 0 2px #ffffff, 0 8px 18px rgba(15, 23, 42, 0.32);
    z-index: 2;
}
```

同时提升 transform/box-shadow 过渡质量、移除 hover 透明度降低，并把 CSS URL 版本提升至 `v=35`。

- [x] **Step 4: 验证定向测试转绿**

运行：`python -m pytest tests/test_statistics_impact_level_hover.py -q`

预期：全部通过。

- [x] **Step 5: 运行相关回归和差异检查**

运行：`python -m pytest tests/test_statistics_impact_level.py tests/test_statistics_impact_level_hover.py tests/test_statistics_dashboard_assets.py -q`

预期：全部通过。随后运行 `git diff --check` 并检查仅包含计划、测试、模板与设计文档的预期变更。

仓库约定禁止未经用户要求提交，因此本计划不包含暂存或提交步骤。
