# 复制本组增加预告标题 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让今明割接小组件的“复制本组”内容包含当前 24 小时预告标题。

**Architecture:** 保留后端报告数据、业务分组和“复制全部”逻辑。前端从当前完整报告文本读取首行标题，在复制本组时拼接“标题 + 空行 + 本组正文”，不拼接业务分组标题。

**Tech Stack:** Django 模板、原生 JavaScript、Python `unittest`

---

### Task 1: 复制本组拼接预告标题

**Files:**
- Modify: `tests/test_dashboard_today_tomorrow_cutover_widget.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_today_tomorrow_cutover_widget.html`

- [ ] **Step 1:** 在小组件测试中断言存在 `const reportTitleText = activeReportText.split('\\n', 1)[0];`，并断言复制调用为 `copyReportText(\`${reportTitleText}\\n\\n${group.text}\`, copyGroupButton);`。
- [ ] **Step 2:** 运行 `python -m unittest tests.test_dashboard_today_tomorrow_cutover_widget -v`，预期因旧代码仍复制 `group.text` 而失败。
- [ ] **Step 3:** 在 `renderReportGroups()` 中接收预告标题，并只为“复制本组”拼接标题、空行和正文。
- [ ] **Step 4:** 重跑定向测试，预期全部通过。
- [ ] **Step 5:** 运行 Python 编译检查和 `git diff --check`。

> 本计划明确不实现“待实施 / 全部”筛选控件，也不改变业务分组标题在弹窗中的展示。

