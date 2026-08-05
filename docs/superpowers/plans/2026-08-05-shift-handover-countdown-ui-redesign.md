# 交接班核对完成倒计时 UI 改造实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` task-by-task. The repository `AGENTS.md` forbids branch, worktree, staging, commit, push, and PR actions unless explicitly requested, so this plan performs none of them.

**Goal:** 将复查通过后的简单文字倒计时改为保留割接列表、逐行绿色核对标识、顶部成功状态和可点击绿色按钮倒计时。

**Architecture:** 保持现有后端检查接口和数据结构不变，只调整交接班模板的 HTML、CSS 与 JavaScript 状态机。复查为空后把当前表格转换为只读核对完成状态，由同一个绿色按钮承担倒计时显示和“立即进入”操作，并通过单次完成保护统一按钮点击与计时器到期路径。

**Tech Stack:** NetBox 4 Dashboard widget、Bootstrap 5、MDI 图标、原生 JavaScript、Python `unittest` 源码级回归测试。

---

## 文件结构

- Modify `tests/test_dashboard_shift_handover_widget.py`: 锁定成功状态、列表核对标识、按钮倒计时、立即进入和防重复行为。
- Modify `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`: 实现方案 A 的视觉样式和状态流。
- Modify `PLAN.md`: 记录实施与验证结果。

## Task 1：核对完成视觉状态

**Files:**
- Modify: `tests/test_dashboard_shift_handover_widget.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`

- [x] **Step 1: 写保留列表和绿色核对标识失败测试**

在 `DashboardShiftHandoverWidgetTestCase` 增加：

```python
def test_completed_check_keeps_rows_and_marks_them_as_verified(self) -> None:
    self.assertIn('id="shiftHandoverOverdueCutoverBanner"', self.template_source)
    self.assertIn('id="shiftHandoverOverdueCutoverBannerIcon"', self.template_source)
    self.assertIn('id="shiftHandoverOverdueCutoverBannerText"', self.template_source)
    self.assertIn('<th class="text-center" scope="col">核对</th>', self.template_source)
    self.assertIn("statusCell.className = 'text-center'", self.template_source)
    self.assertIn("row.classList.add('table-success')", self.template_source)
    self.assertIn("statusIcon.className = 'mdi mdi-check-circle text-success'", self.template_source)
    self.assertIn("bannerText.textContent = '已完成逾期待实施割接核对'", self.template_source)
    self.assertNotIn("overdueTable.classList.add('d-none')", self.template_source)
    self.assertNotIn('id="shiftHandoverOverdueCutoverSuccess"', self.template_source)
```

- [x] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m unittest tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_completed_check_keeps_rows_and_marks_them_as_verified -v
```

Expected: FAIL，因为当前实现隐藏表格并显示独立成功文字块。

- [x] **Step 3: 增加状态栏、核对列和倒计时按钮结构**

将现有黄色提示改为可切换状态的节点：

```html
<div class="alert alert-warning" id="shiftHandoverOverdueCutoverBanner" role="alert">
  <i class="mdi mdi-alert-outline me-1" id="shiftHandoverOverdueCutoverBannerIcon"></i>
  <span id="shiftHandoverOverdueCutoverBannerText">下列割接可能已经实施完成，请检查修正状态</span>
</div>
```

在表格首列加入：

```html
<th class="text-center" scope="col">核对</th>
```

删除 `shiftHandoverOverdueCutoverSuccess` 独立成功提示。在“再次检查”按钮内保留固定标签和进度条节点：

```html
<button class="btn btn-primary position-relative overflow-hidden" id="recheckOverdueCutovers" type="button">
  <span id="recheckOverdueCutoversLabel"><i class="mdi mdi-refresh me-1"></i>再次检查</span>
  <span class="otn-overdue-countdown-progress" id="shiftHandoverCountdownProgress"></span>
</button>
```

- [x] **Step 4: 渲染空核对单元格并实现成功样式切换**

`renderOverdueCutovers()` 在编号单元格前创建状态单元格：

```javascript
const statusCell = document.createElement('td');
statusCell.className = 'text-center';
statusCell.dataset.overdueCheckStatus = '';
row.appendChild(statusCell);
```

新增：

```javascript
function markOverdueCutoversVerified() {
  overdueRows.querySelectorAll('tr').forEach(row => {
    row.classList.add('table-success');
    const statusCell = row.querySelector('[data-overdue-check-status]');
    const statusIcon = document.createElement('i');
    statusIcon.className = 'mdi mdi-check-circle text-success';
    statusIcon.setAttribute('aria-label', '已核对');
    statusCell.replaceChildren(statusIcon);
  });
  bannerElement.classList.remove('alert-warning');
  bannerElement.classList.add('alert-success');
  bannerIcon.className = 'mdi mdi-check-circle me-1';
  bannerText.textContent = '已完成逾期待实施割接核对';
}
```

- [x] **Step 5: 运行视觉状态测试确认 GREEN**

Run:

```powershell
python -m unittest tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_completed_check_keeps_rows_and_marks_them_as_verified -v
```

Expected: PASS。

## Task 2：可点击按钮倒计时与单次完成保护

**Files:**
- Modify: `tests/test_dashboard_shift_handover_widget.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`

- [x] **Step 1: 写按钮倒计时和立即进入失败测试**

```python
def test_completed_check_countdown_is_shown_on_clickable_button(self) -> None:
    self.assertIn('id="recheckOverdueCutoversLabel"', self.template_source)
    self.assertIn('id="shiftHandoverCountdownProgress"', self.template_source)
    self.assertIn("skipButton.classList.add('d-none')", self.template_source)
    self.assertIn("recheckButton.classList.replace('btn-primary', 'btn-success')", self.template_source)
    self.assertIn('recheckButton.disabled = false', self.template_source)
    self.assertIn('`<i class="mdi mdi-check me-1"></i>已核对 · ${remainingSeconds}秒后进入`', self.template_source)
    self.assertIn("if (completionCountdownActive)", self.template_source)
    self.assertIn('await finishCompletedCheck()', self.template_source)


def test_completed_check_uses_progress_and_single_shot_generation(self) -> None:
    self.assertIn('let completionTimer = null;', self.template_source)
    self.assertIn('let completionGenerationStarted = false;', self.template_source)
    self.assertIn('if (completionGenerationStarted) return;', self.template_source)
    self.assertIn('completionGenerationStarted = true;', self.template_source)
    self.assertIn('window.clearInterval(completionTimer)', self.template_source)
    self.assertIn('countdownProgress.style.width =', self.template_source)
    self.assertIn('completionCountdownActive = false;', self.template_source)
```

- [x] **Step 2: 运行测试确认 RED**

Run:

```powershell
python -m unittest tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_completed_check_countdown_is_shown_on_clickable_button tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_completed_check_uses_progress_and_single_shot_generation -v
```

Expected: FAIL，因为倒计时仍位于独立文字块，且按钮不可用于立即进入。

- [x] **Step 3: 增加倒计时按钮进度样式**

```css
.otn-overdue-countdown-progress {
  background: rgba(255, 255, 255, .45);
  bottom: 0;
  height: 3px;
  left: 0;
  position: absolute;
  transition: width .25s linear;
  width: 0;
}
```

- [x] **Step 4: 实现统一完成入口和单次保护**

声明状态：

```javascript
let completionTimer = null;
let completionCountdownActive = false;
let completionGenerationStarted = false;
```

实现统一入口：

```javascript
async function finishCompletedCheck() {
  if (completionGenerationStarted) return;
  completionGenerationStarted = true;
  completionCountdownActive = false;
  if (completionTimer !== null) {
    window.clearInterval(completionTimer);
    completionTimer = null;
  }
  hideOverdueCutoverModal();
  generateButton.textContent = '正在生成…';
  try {
    await generateShiftHandoverContent();
  } catch (error) {
    errorBox.textContent = error.message || '生成交接班内容失败，请稍后重试。';
    resetGenerateButton();
  }
}
```

- [x] **Step 5: 将复查按钮切换为可点击倒计时按钮**

`startCompletedCheckCountdown()` 调用 `markOverdueCutoversVerified()`，隐藏跳过按钮，保留 footer，切换按钮颜色并启用按钮。每秒更新：

```javascript
function renderCompletedCountdown(remainingSeconds) {
  recheckLabel.innerHTML = `<i class="mdi mdi-check me-1"></i>已核对 · ${remainingSeconds}秒后进入`;
  countdownProgress.style.width = `${(remainingSeconds / 5) * 100}%`;
}
```

计时器到 0 时调用 `void finishCompletedCheck()`；`recheckButton` 原点击处理器最前面增加：

```javascript
if (completionCountdownActive) {
  await finishCompletedCheck();
  return;
}
```

- [x] **Step 6: 恢复下一次检查的初始状态**

`resetWarningState()` 清理计时器和标志，恢复黄色警示、初始按钮标签/颜色、显示跳过按钮并将进度设为 `0%`：

```javascript
completionCountdownActive = false;
completionGenerationStarted = false;
if (completionTimer !== null) window.clearInterval(completionTimer);
completionTimer = null;
bannerElement.classList.remove('alert-success');
bannerElement.classList.add('alert-warning');
bannerIcon.className = 'mdi mdi-alert-outline me-1';
bannerText.textContent = '下列割接可能已经实施完成，请检查修正状态';
skipButton.classList.remove('d-none');
recheckButton.classList.replace('btn-success', 'btn-primary');
recheckLabel.innerHTML = recheckLabelDefault;
countdownProgress.style.width = '0%';
```

- [x] **Step 7: 运行 widget 测试确认 GREEN**

Run:

```powershell
python -m unittest tests.test_dashboard_shift_handover_widget -v
```

Expected: PASS。

## Task 3：完整验证和计划收尾

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 运行相关回归测试**

Run:

```powershell
python -m unittest tests.test_shift_handover_text tests.test_shift_handover_data_source tests.test_dashboard_shift_handover_widget tests.test_dashboard_today_tomorrow_cutover_widget tests.test_dashboard_panel_order tests.test_cutover_report_text -v
```

Expected: 全部 PASS。

- [x] **Step 2: 运行 Python 与 JavaScript 语法检查**

Run:

```powershell
python -m py_compile netbox_otnfaults\dashboard.py tests\test_dashboard_shift_handover_widget.py
node -e "const fs=require('fs');const t=fs.readFileSync('netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html','utf8');new Function(t.split('<script>')[1].split('</script>')[0]);"
```

Expected: 两个命令退出码均为 0，无输出。

- [x] **Step 3: 运行差异检查**

Run: `git diff --check`

Expected: 退出码 0；允许 Git 提示现有 LF/CRLF 转换，不允许 whitespace error。

- [x] **Step 4: 浏览器验收或记录环境限制**

在可用 NetBox 页面触发逾期列表并复查为空，确认列表保留、逐行绿色对勾、顶部绿色状态、按钮倒计时与进度条、按钮立即进入、自动进入和无重复请求。此次 `http://localhost:50523/` 请求超时，浏览器验收未执行，已在 `PLAN.md` 记录。

- [x] **Step 5: 更新计划状态**

仅把有测试或检查证据的本计划与 `PLAN.md` 项目标记为 `[x]`；不得暂存或提交。
