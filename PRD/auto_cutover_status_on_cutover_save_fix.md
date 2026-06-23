# 修复割接保存时 property 'url' 报错的 PRD 需求文档

## 1. 背景与问题分析
在编辑并保存割接任务时，系统试图自动流转状态为“待实施”并弹出提示框。现有的实现通过拦截 `post()` 重定向返回并在 Location 头部追加 `auto_set_pending=true`。由于部分 Netbox 环境（尤其是 Django 5.0 / Netbox 4.6.2）对重定向响应对象的 `.url` 属性有限制（缺少 setter），导致部分中间件或路由在解析该 Location 头部时引发了 `AttributeError: property 'url' of 'HttpResponseRedirect' object has no setter`。

为了彻底解决这一兼容性问题，我们将基于 **KISS 原则**，改用更为健壮安全的 **Django Session** 传递该一次性提示状态，避免在 `Location` 头部中追加冗余的查询参数，消除底层报错的可能。

## 2. 拟做出的变更

### 2.1 后端视图变更 (netbox_otnfaults/views.py)
- **`CutoverTaskEditView.post()`**:
  - 移除对返回的 `response['Location']` 追加参数的逻辑。
  - 改为在检测到状态自动流转成功后，设置 `request.session['cutover_auto_set_pending'] = True`。
  - 直接原样返回 `super().post(...)`。
- **`CutoverTaskView.get_extra_context()`**:
  - 读取并从 session 中删除标记：`show_auto_set_pending = request.session.pop('cutover_auto_set_pending', False)`。
  - 将 `show_auto_set_pending` 传给模板 Context。

### 2.2 前端模板变更 (netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html)
- 移除通过 JS 读取 URL 参数 `auto_set_pending` 的代码及 `window.history.replaceState` 相关的清理参数逻辑。
- 改为通过 Django 模板标签直接判定：
  ```html
  {% if show_auto_set_pending %}
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.showCutoverStatusNoticeModal);
  } else {
    window.showCutoverStatusNoticeModal();
  }
  {% endif %}
  ```

### 2.3 单元测试变更 (tests/test_cutover_status_auto_set.py)
- 调整测试对 `views.py` 与 `cutovertask.html` 的断言代码，验证 Session 设置逻辑与模板标签的直接注入，使静态断言全部保持正确通过。

## 3. 验证计划

### 自动验证
- 运行测试指令：
  `.\.venv\Scripts\python.exe -m unittest tests/test_cutover_status_auto_set.py`
  确保所有静态检查都为 OK 状态。

### 手动验证
- 保存割接记录并触发状态自动转换，进入详情页面。
- 确认：
  1. 系统在详情页不报任何 `AttributeError` 错误。
  2. 依然弹出模态框提示用户自动变更，并显示 3 秒倒计时自动关闭。
  3. URL 中无冗余的 `?auto_set_pending=true` 参数。
  4. 刷新详情页不会再次弹窗。
