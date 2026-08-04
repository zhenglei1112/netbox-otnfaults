# 交接班小组件实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` task-by-task. The repository `AGENTS.md` forbids branch, worktree, staging, commit, push, and PR actions unless explicitly requested, so this plan performs none of them.

**Goal:** 在 NetBox 首页增加可选班次时间、实时生成六章交接文本并复制的“交接班”小组件。

**Architecture:** 无框架依赖的班次计算和文本格式化放入独立服务；权限受限的 Django queryset 聚合放入数据服务；插件内只读 JSON 视图供 Dashboard widget 调用。模板只负责时间选择、前后班次切换、加载/错误状态、Bootstrap 弹窗和剪贴板反馈。

**Tech Stack:** Python 3、Django 5、NetBox 4 Dashboard widgets、Bootstrap 5、原生 JavaScript、`pytest`。

---

## 文件结构

- Create `netbox_otnfaults/services/shift_handover_text.py`: DTO、班次时间和六章文本格式化。
- Create `netbox_otnfaults/services/shift_handover.py`: 权限受限的数据查询和 DTO 映射。
- Create `netbox_otnfaults/handover_views.py`: 班次参数校验和 JSON 响应。
- Create `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`: 小组件、弹窗和 JavaScript。
- Modify `netbox_otnfaults/dashboard.py`: 注册 `OtnShiftHandoverWidget`。
- Modify `netbox_otnfaults/urls.py`: 注册生成 URL。
- Create `tests/test_shift_handover_text.py`: 纯函数和最终文本测试。
- Create `tests/test_shift_handover_data_source.py`: 查询与视图源码回归测试。
- Create `tests/test_dashboard_shift_handover_widget.py`: widget 和模板交互测试。
- Modify `PLAN.md`: 跟踪 TDD、实现和验证状态。

## Task 1：班次计算和纯文本格式化

**Files:** `tests/test_shift_handover_text.py`, `netbox_otnfaults/services/shift_handover_text.py`

- [ ] 写失败测试：11:59 默认昨日 18:00，12:00 默认今日 09:00。
- [ ] 写失败测试：向上用 `direction=-1` 选择严格早于所选值的最近 09:00/18:00；向下用 `direction=1` 选择严格晚于所选值的最近班次点；覆盖跨日和手工选择 14:30。
- [ ] 运行 `python -m pytest tests/test_shift_handover_text.py -q`，确认因模块不存在而失败。
- [ ] 实现以下班次 API：

```python
SHIFT_HOURS: tuple[int, int] = (9, 18)


def default_shift_start(now: datetime) -> datetime:
    target_date = now.date() if now.time() >= time(12) else now.date() - timedelta(days=1)
    target_hour = 9 if now.time() >= time(12) else 18
    return now.replace(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=target_hour,
        minute=0,
        second=0,
        microsecond=0,
    )


def adjacent_shift_start(selected: datetime, *, direction: int) -> datetime:
    if direction not in (-1, 1):
        raise ValueError('direction 必须为 -1 或 1')
    candidates = [
        selected.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=offset)
        for offset in (-1, 0, 1)
        for hour in SHIFT_HOURS
    ]
    eligible = [value for value in candidates if value < selected] if direction == -1 else [value for value in candidates if value > selected]
    return max(eligible) if direction == -1 else min(eligible)


def handover_window_end(now: datetime) -> datetime:
    target_date = now.date() + timedelta(days=2)
    return now.replace(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
```

- [ ] 运行定向测试，确认班次用例通过。
- [ ] 写失败测试并定义 frozen dataclass `FaultHandoverItem`、`CutoverHandoverItem`、`HeavyDutyHandoverItem` 所需字段；类型与设计文档一致。
- [ ] 写失败测试：`latest_timeline_stage()` 从阶段 tuple 末尾向前返回最后一个非空时间；全部为空时返回 `None`。
- [ ] 写失败测试：构造本班/历史各一条故障、裸纤/电路割接、重保、通知及缺失字段，断言完整六章、连续编号、`-`、影响业务去重、阶段时间、固定手机交接。
- [ ] 写失败测试：空集合仍生成全部章节；章节二至五正文为 `无`。
- [ ] 运行定向测试，确认因格式化 API 缺失而失败。
- [ ] 实现 `latest_timeline_stage(stages)`：反向遍历 `(阶段名, datetime | None)`，返回第一个非空 `(阶段名, datetime)`。
- [ ] 实现 `build_handover_text(...)`：按 `fault.occurred_at >= shift_start` 拆分计数；以 `enumerate(..., start=1)` 生成中文全角编号；按顺序生成故障说明、两个割接分组、重保、通知和手机交接；章节三日期使用 `handover_window_end(now) - timedelta(days=1)` 并显示 `24:00`；空集合写 `无`；字段空值经 `_display()` 变为 `-`。
- [ ] 运行 `python -m pytest tests/test_shift_handover_text.py -q`，确认全部通过。

## Task 2：权限受限的数据聚合

**Files:** `tests/test_shift_handover_data_source.py`, `netbox_otnfaults/services/shift_handover.py`

- [ ] 写源码级失败测试，锁定故障查询：

```python
assert "OtnFault.objects.restrict(user, 'view')" in source
assert 'fault_status=FaultStatusChoices.PROCESSING' in source
assert 'is_suspended=False' in source
assert "'impacts__bare_fiber_service'" in source
assert "'impacts__circuit_service'" in source
```

- [ ] 写源码级失败测试，锁定割接查询：

```python
assert "CutoverTask.objects.restrict(user, 'view')" in source
assert 'status=CutoverStatusChoices.PENDING_IMPLEMENTATION' in source
assert 'planned_cutover_time__gte=now' in source
assert 'planned_cutover_time__lt=window_end' in source
```

- [ ] 写源码级失败测试，锁定重保查询：

```python
assert "HeavyDuty.objects.restrict(user, 'view')" in source
assert 'end_time__gte=now' in source
assert 'start_time__lt=window_end' in source
assert 'HeavyDutyTypeChoices.IMPORTANT' in source
assert 'HeavyDutyTypeChoices.COMPANY_NOTICE' in source
```

- [ ] 断言源码包含故障时间线真实字段顺序、光纤封包阶段、首次出现顺序去重、裸纤优先分组、无业务割接落入其他组、用户全名回退用户名和 `build_handover_text()` 调用。
- [ ] 运行 `python -m pytest tests/test_shift_handover_data_source.py -q`，确认因数据服务不存在而失败。
- [ ] 实现 `generate_shift_handover_text(*, user: Any, shift_start: datetime, now: datetime) -> str`。
- [ ] 故障 queryset 使用 `restrict`、`PROCESSING`、`is_suspended=False`、影响业务预取和 `fault_occurrence_time, pk` 稳定排序。
- [ ] 将每条故障映射为 DTO：一级原因显示值；裸纤名称和电路 `special_line_name or name` 去重；时间线依次为故障起始、处理派发、维修出发、到达现场、故障恢复，光纤类追加封包完成时间。
- [ ] 割接 queryset 使用 `[now, handover_window_end(now))`、待实施状态、province/A 端 select、Z 端/impacts prefetch 和 `planned_cutover_time, pk` 排序。
- [ ] 有任一裸纤影响的割接进入 `bare_fiber_cutovers`；其他割接（含无影响记录）进入 `other_cutovers`；不得重复。
- [ ] 重保 queryset 使用 `end_time__gte=now`、`start_time__lt=window_end`，映射 `important` 与 `notice`，排除 `memo`。
- [ ] 用户名使用 `user.get_full_name().strip() or user.get_username()`，调用纯文本格式化器。
- [ ] 运行数据服务测试，确认全部通过。

## Task 3：只读生成视图和 URL

**Files:** `tests/test_shift_handover_data_source.py`, `netbox_otnfaults/handover_views.py`, `netbox_otnfaults/urls.py`

- [ ] 写失败测试，断言 `ShiftHandoverGenerateView(LoginRequiredMixin, View)`、`request.GET.get('shift_start', '')`、`parse_datetime`、naive 时间 `make_aware`、400 中文错误、`timezone.localtime()`、成功 `{'text': text}` 和通用 500 错误。
- [ ] 写失败测试，断言 URL 为 `dashboard/shift-handover/generate/`，名称为 `dashboard_shift_handover_generate`，并显式引用 `handover_views.ShiftHandoverGenerateView.as_view()`。
- [ ] 运行数据服务测试，确认视图/URL 缺失导致失败。
- [ ] 实现只读 GET 视图：登录保护；解析班次；非法值返回 `{'error': '班次开始时间格式无效。'}`/400；后端获取本地 `now`；调用数据服务；成功返回 JSON；异常写 logger 并返回通用错误/500，不回显堆栈。
- [ ] 在 `urls.py` 导入 `handover_views` 并注册上述 path。
- [ ] 运行数据服务测试，确认全部通过。

## Task 4：Dashboard widget 和前端交互

**Files:** `tests/test_dashboard_shift_handover_widget.py`, `netbox_otnfaults/dashboard.py`, `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`

- [ ] 写失败测试，断言 `@register_widget`、类名、`default_title = "交接班"`、`width = 2`、`height = 2`、`default_shift_start(now)`、生成 URL reverse 及模板路径。
- [ ] 写失败测试，断言模板仅有一个 `datetime-local`，含 `previous`/`next` 两箭头、生成按钮、错误区、`shiftHandoverModal` 和正文容器。
- [ ] 写失败测试，断言 footer 中 `copyShiftHandoverText` 位于关闭按钮之前；成功/失败分别短时显示“已复制”“复制失败”；模板不出现重复的“前一个班次/后一个班次”正文说明。
- [ ] 写失败测试，断言 JavaScript 按 09:00/18:00 严格前后切换、跨日、`URLSearchParams`、fetch、加载禁用、Bootstrap Modal 和 1500ms 恢复文案。
- [ ] 运行 `python -m pytest tests/test_dashboard_shift_handover_widget.py -q`，确认 widget/template 缺失导致失败。
- [ ] 在 `dashboard.py` 注册 `OtnShiftHandoverWidget`；render 以服务器本地时间计算默认班次，格式化为 `Y-m-d\TH:i`，传入生成 URL；异常写 logger 并返回通用 alert。
- [ ] 使用 Bootstrap 5 和 NetBox CSS 变量实现紧凑卡片：时间输入右侧仅保留上下箭头，不增加重复说明。
- [ ] 实现前端：读取/设置本地日期时间；箭头选择严格相邻班次；生成时禁用按钮；GET 请求并显示错误；成功打开弹窗；复制按钮反馈后恢复；按钮顺序为复制在左、关闭在右。
- [ ] 运行 widget 测试，确认全部通过。

## Task 5：验证和计划收尾

**Files:** `PLAN.md`

- [ ] 运行 `python -m pytest tests/test_shift_handover_text.py tests/test_shift_handover_data_source.py tests/test_dashboard_shift_handover_widget.py -q`，预期全部 PASS。
- [ ] 运行 `python -m pytest tests/test_dashboard_today_tomorrow_cutover_widget.py tests/test_dashboard_panel_order.py tests/test_cutover_report_text.py -q`，预期全部 PASS。
- [ ] 运行 `python -m compileall -q netbox_otnfaults tests`，预期退出码 0 且无输出。
- [ ] 运行 `git diff --check`，预期退出码 0 且无输出。
- [ ] 在可用 NetBox 环境人工验证上午/下午默认值、手工时间、箭头跨日、生成加载态、完整六章、弹窗按钮顺序、复制反馈、暗色模式和窄宽度。当前环境无 NetBox 时明确记录未执行。
- [ ] 仅将有验证证据的 `PLAN.md` 项目改为 `[x]`；不得暂存或提交。

## Task 6：精简故障计数文案并修复复制兼容性

**Files:** `tests/test_shift_handover_text.py`, `tests/test_dashboard_shift_handover_widget.py`, `netbox_otnfaults/services/shift_handover_text.py`, `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`, `PLAN.md`

- [x] 修改文本格式测试，断言计数行为保留但生成内容不包含 `【当班新增故障，正在处理】` 和 `【非本班次故障即历史遗留】`。
- [x] 修改模板源码测试，要求复制实现包含 `navigator.clipboard && window.isSecureContext`、隐藏 `textarea`、`document.execCommand('copy')`，并在 Clipboard API 被拒绝时调用回退函数。
- [x] 运行两项定向测试，确认分别因旧计数文案和缺少复制回退而失败。
- [x] 将计数文本改为：

```python
f'本班移交待处理故障{current_fault_count}起，另有前期班次移交需接续处理故障{historical_fault_count}起。（请在信息系统核对清点）'
```

- [x] 参照今明割接小组件增加返回布尔值的隐藏文本框复制函数，并采用以下顺序：

```javascript
async function copyShiftHandoverText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      // Continue with the DOM fallback.
    }
  }
  return fallbackCopy(text);
}
```

- [x] 回退函数必须在 `finally` 中移除临时文本框，并以 `document.execCommand('copy')` 返回值判断成功或失败；点击处理器据此显示“已复制”或“复制失败”。
- [x] 运行交接班及相关仪表盘测试、Python 编译、JavaScript 语法和 `git diff --check`，确认全部通过后更新 `PLAN.md`；不得暂存或提交。

## Task 7：清理数据库文字空白并紧凑显示日期时间

**Files:** `tests/test_shift_handover_text.py`, `netbox_otnfaults/services/shift_handover_text.py`, `PLAN.md`

- [x] 增加失败测试，输入含空格和制表符的用户显示名、故障字段、业务名称、割接字段及重保字段，断言输出删除这些横向空白但保留换行。
- [x] 更新现有时间断言，要求截至时间、故障处理进度、割接计划时间和重保时间使用 `YYYY年M月D日HH:mm:ss`；处理进度时间与阶段名称直接相连。
- [x] 增加固定排版断言，确保首行仍含 `接班人: 李四    截至`，手机交接仍为 `数量:  2        完好性: 正常  有损坏`。
- [x] 运行 `python -m unittest tests.test_shift_handover_text -v`，确认因旧格式保留数据库文字空白及日期时间空格而失败。
- [x] 新增 `_compact_text(value: object) -> str`，删除除 `\r`、`\n` 外的 Unicode 空白；让 `_display()` 与 `_unique_text()` 统一复用该函数。
- [x] 将 `_format_datetime()` 改为日期与时刻直接拼接，并删除处理进度时间与阶段名称之间的额外空格；不得修改首行和手机交接行中的固定排版空格。
- [x] 运行交接班及相关仪表盘测试、Python/JavaScript 语法检查和 `git diff --check`，确认通过后更新 `PLAN.md`；不得暂存或提交。

## Task 8：为复制按钮增加状态图标

**Files:** `tests/test_dashboard_shift_handover_widget.py`, `netbox_otnfaults/templates/netbox_otnfaults/inc/dashboard_shift_handover_widget.html`, `PLAN.md`

- [x] 增加失败测试，断言按钮默认 HTML 包含 `<i class="mdi mdi-content-copy me-1"></i>复制内容`，成功反馈包含 `<i class="mdi mdi-check me-1"></i>已复制`。
- [x] 增加失败测试，断言默认状态使用 `copyButton.innerHTML` 保存与恢复，避免 `textContent` 恢复时丢失复制图标。
- [x] 运行 `python -m unittest tests.test_dashboard_shift_handover_widget -v`，确认因模板缺少图标而失败。
- [x] 在复制按钮中加入 `mdi-content-copy` 图标，将默认标签保存为按钮初始 `innerHTML`。
- [x] 成功时将按钮 `innerHTML` 切换为 `mdi-check` 图标和“已复制”；失败时显示“复制失败”；1.5 秒后恢复初始 HTML。不得修改 Clipboard API 与隐藏文本框回退逻辑。
- [x] 运行交接班及相关仪表盘测试、JavaScript 语法和 `git diff --check`，确认通过后更新 `PLAN.md`；不得暂存或提交。

## Task 9：无关联业务故障显示线路组网

**Files:** `tests/test_shift_handover_text.py`, `netbox_otnfaults/services/shift_handover_text.py`, `PLAN.md`

- [x] 修改故障文本测试，断言空业务集合或业务名称均为空时输出 `影响：线路组网`，且不再出现 `影响：-线路`。
- [x] 保留有关联业务时的现有格式断言，例如 `影响：业务甲、业务乙线路`。
- [x] 运行 `python -m unittest tests.test_shift_handover_text -v`，确认因旧实现输出 `影响：-线路` 而失败。
- [x] 在 `_format_faults()` 内单独构建影响文案：`_unique_text()` 返回 `-` 时使用 `线路组网`，否则在业务名称后追加 `线路`；不得修改 `_unique_text()` 或其他章节缺失值规则。
- [x] 运行交接班及相关仪表盘测试、Python/JavaScript 语法检查和 `git diff --check`，确认通过后更新 `PLAN.md`；不得暂存或提交。
