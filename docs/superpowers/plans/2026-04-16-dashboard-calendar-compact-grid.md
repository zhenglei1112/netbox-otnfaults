# Dashboard Calendar Compact Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the fault calendar widget render daily fault dots in a compact grid so busy days stay readable without truncating dots.

**Architecture:** Keep the existing widget data flow unchanged and limit the change to the calendar widget template. Lock the new layout with a source-level test first, then update the inline CSS to use a compact grid with smaller dots and reserved space for the dot area.

**Tech Stack:** Django template, inline CSS, Python `unittest`

---

### Task 1: Lock Compact Grid Template Requirements

**Files:**
- Modify: `D:\Src\netbox-otnfaults\tests\test_dashboard_calendar_widget.py`
- Test: `D:\Src\netbox-otnfaults\tests\test_dashboard_calendar_widget.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_calendar_widget_template_uses_compact_dot_grid_layout(self) -> None:
        template_source = CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(".otn-cal-dots {", template_source)
        self.assertIn("display: grid;", template_source)
        self.assertIn("grid-template-columns: repeat(4, 1fr);", template_source)
        self.assertIn("min-height: 17px;", template_source)
        self.assertIn("width: 5px; height: 5px;", template_source)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_dashboard_calendar_widget`
Expected: FAIL because the template still uses `display: flex;` and larger dots.

- [ ] **Step 3: Write minimal implementation**

```python
CALENDAR_TEMPLATE_PATH = (
    REPO_ROOT / "netbox_otnfaults" / "templates" / "netbox_otnfaults" / "inc" / "dashboard_calendar_widget.html"
)
```

- [ ] **Step 4: Run test to verify it still fails for the expected reason**

Run: `python -m unittest tests.test_dashboard_calendar_widget`
Expected: FAIL only on the missing compact-grid CSS assertions.

### Task 2: Implement Compact Grid Styling

**Files:**
- Modify: `D:\Src\netbox-otnfaults\netbox_otnfaults\templates\netbox_otnfaults\inc\dashboard_calendar_widget.html`
- Modify: `D:\Src\netbox-otnfaults\PLAN.md`
- Test: `D:\Src\netbox-otnfaults\tests\test_dashboard_calendar_widget.py`

- [ ] **Step 1: Update the template CSS**

```html
.otn-cal td { text-align: center; vertical-align: top; padding: 1px; height: 44px; position: relative; }
.otn-cal-day {
  font-size: .72rem; color: var(--nbx-body-color, #495057); font-weight: 500;
  height: 18px; line-height: 18px; margin-bottom: 2px; text-align: center;
}
.otn-cal-dots {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  justify-items: center;
  align-content: start;
  gap: 1px;
  min-height: 17px;
  padding: 0 2px;
}
.otn-cal-dot {
  width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 1px rgba(0,0,0,.25);
}
```

- [ ] **Step 2: Mark the local repo plan entry complete**

```markdown
## 故障月历紧凑网格样式优化

- [x] 为 `dashboard_calendar_widget.html` 增加源码级失败测试，覆盖月历圆点容器改为紧凑网格布局
- [x] 先运行新增测试，确认当前模板仍使用松散 `flex-wrap` 圆点布局
- [x] 调整月历模板样式，使用固定列数紧凑网格、小尺寸圆点和稳定点阵高度
- [x] 运行定向测试，确认月历多故障日期的模板结构已更新
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m unittest tests.test_dashboard_calendar_widget`
Expected: PASS

- [ ] **Step 4: Review the diff**

Run: `git diff -- D:\Src\netbox-otnfaults\tests\test_dashboard_calendar_widget.py D:\Src\netbox-otnfaults\netbox_otnfaults\templates\netbox_otnfaults\inc\dashboard_calendar_widget.html D:\Src\netbox-otnfaults\PLAN.md`
Expected: Only the template, the source-level test, and the local plan entry change.
