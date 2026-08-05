# 交接班逾期待实施割接检查实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` task-by-task. The repository `AGENTS.md` forbids branch, worktree, staging, commit, push, and PR actions unless explicitly requested, so this plan performs none of them.

**Goal:** 在生成交接班内容前检查当前用户可见的逾期待实施割接，通过警示窗口支持新窗口修改、跳过和再次检查。

**Architecture:** 新增插件自有只读检查服务与 JSON 视图，查询 `planned_cutover_time < server_now` 且状态为待实施的割接，并返回展示字段和现有编辑 URL。Dashboard 前端先调用检查视图，只有检查为空、用户跳过或复查倒计时完成后才复用原生成视图；警示窗口与交接内容窗口相互独立。

**Tech Stack:** Python 3、Django 5、NetBox 4 Dashboard widgets、Bootstrap 5、原生 JavaScript、`unittest` 源码级回归测试。

---

## 文件结构

- Modify `netbox_otnfaults/services/shift_handover.py`: 查询并映射逾期待实施割接。
- Modify `netbox_otnfaults/handover_views.py`: 新增登录保护的只读检查视图。
- Modify `netbox_otnfaults/urls.py`: 注册插件自有检查 URL。
- Modify `netbox_otnfaults/dashboard.py`: 向 widget 模板传入检查 URL。
- Modify `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`: 新增警示窗口、列表渲染、跳过、复查和倒计时状态流。
- Modify `tests/test_shift_handover_data_source.py`: 锁定查询、映射、视图和 URL。
- Modify `tests/test_dashboard_shift_handover_widget.py`: 锁定模板结构与前端状态流。
- Modify `PLAN.md`: 跟踪实施和验证状态。

## Task 1：逾期待实施割接查询与映射

**Files:**
- Modify: `tests/test_shift_handover_data_source.py`
- Modify: `netbox_otnfaults/services/shift_handover.py`

- [x] **Step 1: 写查询口径失败测试**

在 `ShiftHandoverDataSourceTestCase` 增加：

```python
def test_overdue_cutover_check_is_permission_limited_and_stably_ordered(self) -> None:
    self.assertIn('def get_overdue_pending_cutovers(', self.source)
    self.assertIn("CutoverTask.objects.restrict(user, 'view')", self.source)
    self.assertIn('status=CutoverStatusChoices.PENDING_IMPLEMENTATION', self.source)
    self.assertIn('planned_cutover_time__lt=now', self.source)
    self.assertIn(".select_related('province', 'interruption_location_a')", self.source)
    self.assertIn(".prefetch_related('interruption_location')", self.source)
    self.assertIn(".order_by('planned_cutover_time', 'pk')", self.source)
```

- [x] **Step 2: 写列表字段失败测试**

```python
def test_overdue_cutover_check_maps_az_ends_and_edit_url(self) -> None:
    self.assertIn("'cutover_no': _display(cutover.cutover_no)", self.source)
    self.assertIn("'planned_cutover_time': timezone.localtime(", self.source)
    self.assertIn("strftime('%Y-%m-%d %H:%M')", self.source)
    self.assertIn("'province': _display(cutover.province)", self.source)
    self.assertIn("'cutover_type': _display(cutover.get_cutover_type_display())", self.source)
    self.assertIn("'a_end': _display(cutover.interruption_location_a)", self.source)
    self.assertIn("'z_end': _joined_display(cutover.interruption_location.all())", self.source)
    self.assertIn("'location': _display(cutover.cutover_location)", self.source)
    self.assertIn("'edit_url': reverse(", self.source)
    self.assertIn("'plugins:netbox_otnfaults:cutovertask_edit'", self.source)
```

- [x] **Step 3: 运行测试确认 RED**

Run: `python -m unittest tests.test_shift_handover_data_source.ShiftHandoverDataSourceTestCase -v`

Expected: FAIL，因为 `get_overdue_pending_cutovers()` 尚不存在。

- [x] **Step 4: 实现显示 helper**

在 `shift_handover.py` 增加类型提示完整的 helper：

```python
def _display(value: object) -> str:
    text = str(value).strip() if value is not None else ''
    return text or '-'


def _joined_display(values: Any) -> str:
    names = tuple(_display(value) for value in values)
    visible_names = tuple(name for name in names if name != '-')
    return '、'.join(visible_names) if visible_names else '-'
```

同时导入 `reverse`：

```python
from django.urls import reverse
```

- [x] **Step 5: 实现权限受限查询和映射**

```python
def get_overdue_pending_cutovers(*, user: Any, now: datetime) -> list[dict[str, str]]:
    cutovers = (
        CutoverTask.objects.restrict(user, 'view')
        .filter(
            status=CutoverStatusChoices.PENDING_IMPLEMENTATION,
            planned_cutover_time__lt=now,
        )
        .select_related('province', 'interruption_location_a')
        .prefetch_related('interruption_location')
        .order_by('planned_cutover_time', 'pk')
    )
    return [
        {
            'cutover_no': _display(cutover.cutover_no),
            'planned_cutover_time': timezone.localtime(
                cutover.planned_cutover_time
            ).strftime('%Y-%m-%d %H:%M'),
            'province': _display(cutover.province),
            'cutover_type': _display(cutover.get_cutover_type_display()),
            'a_end': _display(cutover.interruption_location_a),
            'z_end': _joined_display(cutover.interruption_location.all()),
            'location': _display(cutover.cutover_location),
            'edit_url': reverse(
                'plugins:netbox_otnfaults:cutovertask_edit',
                args=[cutover.pk],
            ),
        }
        for cutover in cutovers
    ]
```

`planned_cutover_time__lt` 自动排除 `NULL`，无需额外过滤。

- [x] **Step 6: 运行数据服务测试确认 GREEN**

Run: `python -m unittest tests.test_shift_handover_data_source.ShiftHandoverDataSourceTestCase -v`

Expected: PASS。

## Task 2：检查视图、URL 和 widget 上下文

**Files:**
- Modify: `tests/test_shift_handover_data_source.py`
- Modify: `tests/test_dashboard_shift_handover_widget.py`
- Modify: `netbox_otnfaults/handover_views.py`
- Modify: `netbox_otnfaults/urls.py`
- Modify: `netbox_otnfaults/dashboard.py`

- [x] **Step 1: 写检查视图与 URL 失败测试**

在 `ShiftHandoverViewTestCase` 增加：

```python
def test_overdue_cutover_check_view_uses_server_time_and_safe_errors(self) -> None:
    self.assertIn(
        'class ShiftHandoverOverdueCutoverCheckView(LoginRequiredMixin, View):',
        self.view_source,
    )
    self.assertIn('now = timezone.localtime()', self.view_source)
    self.assertIn('get_overdue_pending_cutovers(', self.view_source)
    self.assertIn('user=request.user,', self.view_source)
    self.assertIn("return JsonResponse({'cutovers': cutovers})", self.view_source)
    self.assertIn("logger.exception('Failed to check overdue cutovers')", self.view_source)
    self.assertIn('检查逾期待实施割接失败，请稍后重试。', self.view_source)

def test_url_registers_plugin_owned_overdue_check_endpoint(self) -> None:
    self.assertIn("'dashboard/shift-handover/check-overdue-cutovers/'", self.url_source)
    self.assertIn(
        'handover_views.ShiftHandoverOverdueCutoverCheckView.as_view()',
        self.url_source,
    )
    self.assertIn(
        "name='dashboard_shift_handover_check_overdue_cutovers'",
        self.url_source,
    )
```

- [x] **Step 2: 写 widget 检查 URL 失败测试**

在 `DashboardShiftHandoverWidgetTestCase.test_widget_is_registered_with_compact_dimensions_and_context` 增加：

```python
self.assertIn('check_url = reverse(', self.dashboard_source)
self.assertIn(
    "'plugins:netbox_otnfaults:dashboard_shift_handover_check_overdue_cutovers'",
    self.dashboard_source,
)
self.assertIn("'check_url': check_url", self.dashboard_source)
self.assertIn('data-check-url="{{ check_url }}"', self.template_source)
```

- [x] **Step 3: 运行测试确认 RED**

Run: `python -m unittest tests.test_shift_handover_data_source.ShiftHandoverViewTestCase tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_widget_is_registered_with_compact_dimensions_and_context -v`

Expected: FAIL，因为检查视图、URL 和上下文尚未注册。

- [x] **Step 4: 实现只读检查视图**

在 `handover_views.py` 导入服务并新增：

```python
from .services.shift_handover import (
    generate_shift_handover_text,
    get_overdue_pending_cutovers,
)


class ShiftHandoverOverdueCutoverCheckView(LoginRequiredMixin, View):
    """Return overdue pending cutovers visible to the current user."""

    def get(self, request: HttpRequest) -> JsonResponse:
        try:
            cutovers = get_overdue_pending_cutovers(
                user=request.user,
                now=timezone.localtime(),
            )
            return JsonResponse({'cutovers': cutovers})
        except Exception:
            logger.exception('Failed to check overdue cutovers')
            return JsonResponse(
                {'error': '检查逾期待实施割接失败，请稍后重试。'},
                status=500,
            )
```

- [x] **Step 5: 注册插件 URL**

在生成 URL 之前加入：

```python
path(
    'dashboard/shift-handover/check-overdue-cutovers/',
    handover_views.ShiftHandoverOverdueCutoverCheckView.as_view(),
    name='dashboard_shift_handover_check_overdue_cutovers',
),
```

- [x] **Step 6: 向 widget 传入检查 URL**

在 `OtnShiftHandoverWidget.render()` 中 reverse 并加入上下文：

```python
check_url = reverse(
    'plugins:netbox_otnfaults:dashboard_shift_handover_check_overdue_cutovers'
)
```

```python
{
    'default_shift': default_shift,
    'generate_url': generate_url,
    'check_url': check_url,
}
```

模板根节点加入：

```html
data-check-url="{{ check_url }}"
```

- [x] **Step 7: 运行视图和 widget 上下文测试确认 GREEN**

Run: `python -m unittest tests.test_shift_handover_data_source.ShiftHandoverViewTestCase tests.test_dashboard_shift_handover_widget.DashboardShiftHandoverWidgetTestCase.test_widget_is_registered_with_compact_dimensions_and_context -v`

Expected: PASS。

## Task 3：警示窗口结构和安全列表渲染

**Files:**
- Modify: `tests/test_dashboard_shift_handover_widget.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`

- [x] **Step 1: 写警示窗口结构失败测试**

```python
def test_template_has_overdue_cutover_warning_modal_and_required_columns(self) -> None:
    self.assertIn('id="shiftHandoverOverdueCutoverModal"', self.template_source)
    self.assertIn('data-bs-backdrop="static"', self.template_source)
    self.assertIn('data-bs-keyboard="false"', self.template_source)
    self.assertIn('下列割接可能已经实施完成，请检查修正状态', self.template_source)
    for heading in ('割接编号', '计划割接时间', '省份', '割接类型', 'A端', 'Z端', '割接地点'):
        self.assertIn(f'<th scope="col">{heading}</th>', self.template_source)
    self.assertIn('id="shiftHandoverOverdueCutoverRows"', self.template_source)
    self.assertIn('id="skipOverdueCutoverCheck"', self.template_source)
    self.assertIn('id="recheckOverdueCutovers"', self.template_source)
    self.assertNotIn('data-overdue-action="close"', self.template_source)
```

- [x] **Step 2: 写安全 DOM 渲染失败测试**

```python
def test_overdue_cutover_rows_use_text_content_and_new_window_edit_links(self) -> None:
    self.assertIn('function renderOverdueCutovers(cutovers)', self.template_source)
    self.assertIn("link.target = '_blank'", self.template_source)
    self.assertIn("link.rel = 'noopener'", self.template_source)
    self.assertIn('link.href = cutover.edit_url', self.template_source)
    self.assertIn('link.textContent = cutover.cutover_no', self.template_source)
    self.assertIn('cell.textContent = cutover[field]', self.template_source)
    self.assertNotIn('rowsElement.innerHTML', self.template_source)
```

- [x] **Step 3: 运行模板测试确认 RED**

Run: `python -m unittest tests.test_dashboard_shift_handover_widget -v`

Expected: FAIL，因为警示窗口和列表渲染尚不存在。

- [x] **Step 4: 增加警示窗口 HTML**

在交接内容窗口之前新增 `shiftHandoverOverdueCutoverModal`，使用 `modal-xl modal-dialog-scrollable`、静态遮罩和禁用 Escape。正文包含固定提示、`table-responsive` 表格、空错误区、隐藏成功区；footer 仅包含：

```html
<button class="btn btn-secondary" id="skipOverdueCutoverCheck" type="button">跳过</button>
<button class="btn btn-primary" id="recheckOverdueCutovers" type="button">
  <i class="mdi mdi-refresh me-1"></i>再次检查
</button>
```

- [x] **Step 5: 使用 DOM API 渲染列表**

```javascript
function renderOverdueCutovers(cutovers) {
  rowsElement.replaceChildren();
  cutovers.forEach(cutover => {
    const row = document.createElement('tr');
    const numberCell = document.createElement('td');
    const link = document.createElement('a');
    link.href = cutover.edit_url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = cutover.cutover_no;
    numberCell.appendChild(link);
    row.appendChild(numberCell);
    ['planned_cutover_time', 'province', 'cutover_type', 'a_end', 'z_end', 'location']
      .forEach(field => {
        const cell = document.createElement('td');
        cell.textContent = cutover[field];
        row.appendChild(cell);
      });
    rowsElement.appendChild(row);
  });
}
```

- [x] **Step 6: 增加警示窗口 Bootstrap/DOM 回退**

保留现有交接内容窗口 helper，新增 `showOverdueCutoverModal()` 和 `hideOverdueCutoverModal()`：Bootstrap 存在时用 `{backdrop: 'static', keyboard: false}`；不存在时手工添加/移除 `.show`、`modal-open` 和独立 backdrop。不得给 backdrop 注册关闭事件。

- [x] **Step 7: 运行模板结构测试确认 GREEN**

Run: `python -m unittest tests.test_dashboard_shift_handover_widget -v`

Expected: PASS。

## Task 4：先检查后生成、跳过、复查与倒计时

**Files:**
- Modify: `tests/test_dashboard_shift_handover_widget.py`
- Modify: `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`

- [x] **Step 1: 写首次检查与跳过失败测试**

```python
def test_generate_flow_checks_overdue_cutovers_before_generating(self) -> None:
    self.assertIn('const checkUrl = root.dataset.checkUrl;', self.template_source)
    self.assertIn('async function fetchOverdueCutovers()', self.template_source)
    self.assertIn('const cutovers = await fetchOverdueCutovers();', self.template_source)
    self.assertIn('if (cutovers.length)', self.template_source)
    self.assertIn('showOverdueCutoverModal()', self.template_source)
    self.assertIn('await generateShiftHandoverContent()', self.template_source)
    self.assertIn("skipButton.addEventListener('click'", self.template_source)

def test_initial_empty_check_has_no_countdown_delay(self) -> None:
    initial_flow = self.template_source.split(
        "generateButton.addEventListener('click'", 1
    )[1].split("skipButton.addEventListener('click'", 1)[0]
    self.assertNotIn('startCompletedCheckCountdown()', initial_flow)
```

- [x] **Step 2: 写再次检查和 5 秒倒计时失败测试**

```python
def test_recheck_refreshes_rows_or_starts_five_second_countdown(self) -> None:
    self.assertIn("recheckButton.addEventListener('click'", self.template_source)
    self.assertIn('renderOverdueCutovers(cutovers)', self.template_source)
    self.assertIn('startCompletedCheckCountdown()', self.template_source)
    self.assertIn('let remainingSeconds = 5;', self.template_source)
    self.assertIn('window.setInterval(', self.template_source)
    self.assertIn('已经完成检查，${remainingSeconds}秒后自动进入交接班信息窗口。', self.template_source)
    self.assertIn('actionsElement.classList.add(', self.template_source)
```

- [x] **Step 3: 写错误和按钮恢复失败测试**

```python
def test_check_failures_restore_the_correct_controls(self) -> None:
    self.assertIn('function resetGenerateButton()', self.template_source)
    self.assertIn('function setWarningButtonsDisabled(disabled)', self.template_source)
    self.assertIn('warningError.textContent = error.message', self.template_source)
    self.assertIn('setWarningButtonsDisabled(false)', self.template_source)
    self.assertIn('resetGenerateButton()', self.template_source)
```

- [x] **Step 4: 运行状态流测试确认 RED**

Run: `python -m unittest tests.test_dashboard_shift_handover_widget -v`

Expected: FAIL，因为检查、跳过、复查和倒计时逻辑尚不存在。

- [x] **Step 5: 抽取原生成请求**

将现有 fetch 生成逻辑放入：

```javascript
async function generateShiftHandoverContent() {
  const params = new URLSearchParams({ shift_start: input.value });
  const response = await fetch(`${generateUrl}?${params.toString()}`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || '生成交接班内容失败，请稍后重试。');
  output.value = payload.text;
  showShiftHandoverModal();
  resetGenerateButton();
}
```

- [x] **Step 6: 实现检查请求和首次状态流**

```javascript
async function fetchOverdueCutovers() {
  const response = await fetch(checkUrl, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || '检查逾期待实施割接失败，请稍后重试。');
  return payload.cutovers;
}
```

首次点击验证班次后禁用生成按钮并检查；有记录时渲染和打开警示窗口，生成按钮保持禁用；无记录时直接 `await generateShiftHandoverContent()`。异常写入 widget 错误区并 `resetGenerateButton()`。

- [x] **Step 7: 实现跳过和复查**

“跳过”隐藏警示窗口后调用生成函数。“再次检查”清空警示错误、禁用两个按钮并请求：有记录则刷新列表并恢复按钮；无记录则隐藏 footer 操作并调用倒计时。请求失败写入警示错误区并恢复两个按钮。

- [x] **Step 8: 实现 5 秒倒计时**

```javascript
function startCompletedCheckCountdown() {
  actionsElement.classList.add('d-none');
  tableElement.classList.add('d-none');
  successElement.classList.remove('d-none');
  let remainingSeconds = 5;
  const renderCountdown = () => {
    successElement.textContent = `已经完成检查，${remainingSeconds}秒后自动进入交接班信息窗口。`;
  };
  renderCountdown();
  const timer = window.setInterval(async () => {
    remainingSeconds -= 1;
    if (remainingSeconds > 0) {
      renderCountdown();
      return;
    }
    window.clearInterval(timer);
    hideOverdueCutoverModal();
    try {
      await generateShiftHandoverContent();
    } catch (error) {
      errorBox.textContent = error.message || '生成交接班内容失败，请稍后重试。';
      resetGenerateButton();
    }
  }, 1000);
}
```

- [x] **Step 9: 运行 widget 测试确认 GREEN**

Run: `python -m unittest tests.test_dashboard_shift_handover_widget -v`

Expected: PASS。

## Task 5：完整验证和计划收尾

**Files:**
- Modify: `PLAN.md`

- [x] **Step 1: 运行交接班和相关仪表盘回归**

Run:

```powershell
python -m unittest tests.test_shift_handover_text tests.test_shift_handover_data_source tests.test_dashboard_shift_handover_widget tests.test_dashboard_today_tomorrow_cutover_widget tests.test_dashboard_panel_order tests.test_cutover_report_text -v
```

Expected: 全部 PASS。

- [x] **Step 2: 运行 Python 编译检查**

Run:

```powershell
python -m py_compile netbox_otnfaults\services\shift_handover.py netbox_otnfaults\handover_views.py netbox_otnfaults\dashboard.py tests\test_shift_handover_data_source.py tests\test_dashboard_shift_handover_widget.py
```

Expected: 退出码 0，无输出。

- [x] **Step 3: 运行模板 JavaScript 解析检查**

Run:

```powershell
node -e "const fs=require('fs');const t=fs.readFileSync('netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html','utf8');new Function(t.split('<script>')[1].split('</script>')[0]);"
```

Expected: 退出码 0，无输出。

- [x] **Step 4: 运行差异检查**

Run: `git diff --check`

Expected: 退出码 0；允许 Git 仅提示现有 LF/CRLF 转换警告，不允许 whitespace error。

- [x] **Step 5: 人工验收记录**

在可用 NetBox 页面验证：首次无逾期直接进入；有逾期时列顺序、AZ 端和新窗口编辑链接正确；跳过直达；修改状态后复查为空显示 5 秒倒计时；复查仍有记录刷新；接口错误恢复按钮；Bootstrap 全局缺失时两个弹窗均可显示。此次 `http://localhost:50523/` 拒绝连接，浏览器验收未执行，已在 `PLAN.md` 记录。

- [x] **Step 6: 更新计划状态**

仅将具有测试或检查证据的本计划与 `PLAN.md` 项目标记为 `[x]`；不得暂存或提交。
