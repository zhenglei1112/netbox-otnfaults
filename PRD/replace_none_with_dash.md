# 实施计划: 修改空值显示为“—”

## 背景
用户反馈在详情页等位置，空值显示为“NONE”，要求统一修改为“—”。

## 修改范围
1. **详情模版 (Templates)**: `otnfault.html`, `otnpath.html`, `otnpathgroup.html`, `barefiberservice.html`, `circuitservice.html` 等。
2. **表格定义 (tables.py)**: 确保所有列在值为空时显示“—”。
3. **视图逻辑 (views.py)**: 统一 Map 数据和 API 返回值中的空值占位符。
4. **前端脚本 (JS)**: 修改弹出框和面板中的空值占位符。

## 具体任务清单 (Task List)
- [x] 修改 `otnpathgroup.html` (部分完成)
- [x] 修改 `otnpath.html` (部分完成)
- [x] 修改 `barefiberservice.html` (部分完成)
- [x] 修改 `circuitservice.html` (部分完成)
- [ ] 修复 `otnpathgroup.html` 中的 JS 语法错误 (lint fix)
- [ ] 补齐 `otnfault.html` 中的空值处理
- [ ] 补齐 `otnfaultimpact.html` 中的空值处理
- [ ] 修改 `tables.py`，为普通列添加 `default='—'`
- [ ] 修改 `views.py`，将 `-` 替换为 `—`
- [ ] 修改 `PopupTemplates.js` 和 `panels.js` 中的空值处理

## 思考过程 (Thought)
由于没有找到硬编码的 "NONE"，猜测其来自于 Django 在渲染 `None` 时的缺省行为（或受特定 Localization/Translation 影响）。通过显式指定 `default:"—"` 过滤器，可以强制覆盖此行为，确保用户界面的一致性。
