# 割接保存时自动设置状态为“待实施”及3秒模态提示弹窗需求与设计文档 (优化版)

## 1. 业务背景
在光传送网（OTN）故障和割接管理的日常业务流程中，割接任务（`CutoverTask`）能否开始实施，取决于该割接的影响业务（`CutoverImpact`）是否全部经过批准或已处于强制割接状态。

为了提升操作人员的审批效率，降低手动切换状态的繁琐操作，系统需要实现：**编辑割接保存时，如果割接影响业务均已就绪（全部已批准或强制割接），自动将割接状态更新为“待实施”并弹出模态框通知用户**。

---

## 2. 详细需求

### 2.1 状态变更逻辑
当用户对割接记录进行编辑并保存时，系统需要检查并决定是否自动将该割接任务状态变更为“待实施”：
- **触发入口**：Web 端割接编辑页面保存表单动作。
- **判断条件**：
  1. 当前割接的影响业务（`CutoverImpact`）中**有数据记录**（即影响业务的数量 > 0）。
  2. 该割接的所有影响业务记录中，每条记录的协调状态（`coordination_status`）均为“已批准” (`approved`) 或“强制割接” (`forced`)。
- **执行效果**：
  - 如果上述条件均满足，且该割接任务的当前状态不为“待实施” (`pending_implementation`)，则系统自动将其状态修改为“待实施”，并保存入库。

### 2.2 前端模态提示
状态发生自动流转后，系统需要在 Web 端重定向跳转至割接详情页时，提供高可视化的提示：
- **提示形式**：弹出遮罩的模态窗口（Modal），参照设置新的割接时间模态窗口设计，**不允许使用**原生 JavaScript 的 `alert()` 或 `confirm()` 默认弹出窗。
- **提示内容**：“所有影响业务均已批准（含强制割接），本次割接状态已被自动设置为待实施”。
- **传参方式**：通过在重定向的 URL 中追加参数 `?auto_set_pending=true` 将提示信息路由到前端。不采用 Django messages 框架传递，从而**彻底避免在详情页产生无用提示文本的残留**。
- **人机交互**：
  1. 详情页加载时，前端 JS 检测 URL 中是否带有 `auto_set_pending=true`。
  2. 若包含该参数，**立即通过 `window.history.replaceState` 清空 URL 中的提示参数**，避免用户在此详情页刷新时再次弹出该模态窗。
  3. 模态窗底部显示一个“关闭 (3s)”的控制按钮。
  4. 模态窗展示时，按钮内显示3秒倒计时。秒数依次递减，倒计时结束后模态窗自动关闭并清理定时器。
  5. 用户亦可在倒计时期间通过点击“关闭”按钮，或者点击模态框周围的背景遮罩区域提前关闭提示窗。

---

## 3. 技术设计方案

### 3.1 后端修改

#### 1. 数据库模型层面 (`models.py`)
在 `CutoverTask` 的 `save` 方法中处理割接任务状态的维护逻辑：
```python
    def save(self, *args: Any, **kwargs: Any) -> None:
        # 关联割接任务状态的自动维护
        if self.pk:
            impacts = self.impacts.all()
            # 必须存在影响业务，且所有影响业务都为已批准或强制割接
            if impacts.exists() and not impacts.exclude(coordination_status__in=['approved', 'forced']).exists():
                self.status = CutoverStatusChoices.PENDING_IMPLEMENTATION

        # 割接的基本保存流程
        if self.cutover_no:
            super().save(*args, **kwargs)
            return
        
        # ... 原来的生成编号并保存的逻辑 ...
```

#### 2. 编辑视图层面 (`views.py`)
重写 `CutoverTaskEditView` 的 `post` 方法，用于在保存成功后识别状态变化并在重定向的 URL 后追加提示参数：
```python
    def post(self, request, *args, **kwargs):
        obj = self.get_object(**kwargs)
        old_status = None
        if obj.pk:
            old_status = obj.status
            
        response = super().post(request, *args, **kwargs)
        
        if isinstance(response, HttpResponseRedirect):
            if obj.pk:
                obj.refresh_from_db()
                new_status = obj.status
                # 检测割接状态是否因为本次保存被更新为“待实施”
                if old_status != 'pending_implementation' and new_status == 'pending_implementation':
                    separator = '&' if '?' in response.url else '?'
                    response.url = f"{response.url}{separator}auto_set_pending=true"
        return response
```

### 3.2 前端修改

#### 详情模板层面 (`cutovertask.html`)
追加模态框的展示控制。

1. **模态框 HTML 与 CSS**：
```html
<style>
  #cutoverStatusNoticeBackdrop {
    background-color: #808080;
    opacity: 0.5;
    position: fixed;
    top: 0;
    left: 0;
    z-index: 1040;
    width: 100vw;
    height: 100vh;
  }
  .cutover-status-notice-dialog {
    width: min(500px, calc(100vw - 2rem));
    max-width: 500px;
  }
  .cutover-status-notice-btn {
    width: 120px;
  }
</style>
```

2. **倒计时 JS 注入**：
在详情页内容下方加入 Bootstrap 5 模态窗口并在加载完成时检查触发：
- 使用 `URLSearchParams(window.location.search)` 检测是否携带 `auto_set_pending` 标志。
- 若有，调用 `window.history.replaceState` 清空参数。
- 启动倒计时定时器控制模态框自动淡出。

---

## 4. 验证计划
1. **测试用例 1 (不满足条件)**：对一个影响业务协调状态含有“待协调”或“未批准”的割接进行编辑并保存，重定向至割接详情页时，页面不包含 `auto_set_pending=true` 参数，不弹出模态窗。
2. **测试用例 2 (满足条件-状态自动更新并弹起倒计时)**：将割接所有影响业务的协调状态置为“已批准”或“强制割接”。编辑该割接的任意非状态字段，点击保存。重定向到详情页时，URL 包含提示参数并立即被 JS 擦除。页面弹出了模态通知窗口，倒计时自 3 递减为 0 后自动淡出，状态变更为“待实施”。
3. **测试用例 3 (刷新页面防重复触发)**：在满足条件弹窗展示后，手动点击关闭，随后在浏览器中按 F5 刷新详情页。模态窗不再弹起，确保良好的交互体验。
