# 需求文档 - 为过滤按钮添加边框

## 背景
在 `BareFiberService` 和 `CircuitService` 的详情页中，时间过滤按钮（全部、本周等）目前的边框不明晰，只有下边框，缺乏顶部和右侧的边界感。

## 目标
为过滤按钮组提供清晰的四周边框，提升界面的辨识度和交互感知。

## 方案
将现有的 `btn-ghost-primary` 类替换为 Bootstrap 的 `btn-outline-primary` 类。

## 修改详情

### 1. BareFiberService 模板
文件：`netbox_otnfaults/templates/netbox_otnfaults/barefiberservice.html`
修改内容：
```html
<!-- 修改前 -->
<a href="?time_filter=all" class="btn btn-ghost-primary ...">全部</a>
<!-- 修改后 -->
<a href="?time_filter=all" class="btn btn-outline-primary ...">全部</a>
```
(对所有 6 个过滤按钮进行相同修改)

### 2. CircuitService 模板
文件：`netbox_otnfaults/templates/netbox_otnfaults/circuitservice.html`
修改内容：
## 计费时间格式修改

### 目标
将裸纤业务和电路业务的计费时间显示从英文/标准格式（如 March 13, 2026 或 2026-03-13）修改为中文“年月日”形式（如 2026年3月13日）。

### 修改详情

#### 1. 详情页模板
文件：`barefiberservice.html` 和 `circuitservice.html`
修改内容：在 `billing_start_time` 和 `billing_end_time` 变量后添加 `|date:"Y年n月j日"` 过滤器。

#### 2. 列表页表格
文件：`tables.py`
修改内容：将 `BareFiberServiceTable` 和 `CircuitServiceTable` 中计费时间列的 `format` 属性从 `'Y-m-d'` 修改为 `'Y年n月j日'`。

