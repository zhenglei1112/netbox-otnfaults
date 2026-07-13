# 需求文档：故障详情页列表分页组件统一化

## 1. 业务背景与问题
当前 OTN 故障详情页（`otnfault.html`）下方的“站点历史故障”和“影响业务”列表依然在使用 `django_tables2` 的默认分页组件。这导致出现不一致的 `1 2 3 next` 字符样式，在 Netbox 的 UI 规范中是不允许的（不符合 `AGENTS.md` 规范）。

## 2. 需求目标
1. 隐藏故障详情页中所有子表格的默认分页器。
2. 引入符合 Netbox UI 设计的自定义分页器。
3. 自定义分页器需要包括三个要素：
   - 页码导航（`‹ 1 2 ... 5 6 7 ... 10 ›` 样式）
   - 显示信息（`显示 X-Y 共 Z` 格式）
   - 每页显示条数选择（下拉框支持 25/50/100/250/500）
4. 保证多个表格能够独立分页（页码参数解耦，例如 `impacts_page` 与 `site_page`）。
5. 切换分页或每页数量时，能正确保留其他查询参数（如 `site_time_filter`）。

## 3. 实现规范与范围

### 后端控制器改动
- 文件：`netbox_otnfaults/views.py`
- 控制器类：`OtnFaultView`
- 具体逻辑：
  - 从 `request.GET` 中获取 `per_page`（每页数量）并进行安全性转换。
  - 从 `request.GET` 中分别获取 `impacts_page` 和 `site_page` 页码。
  - 通过 `table.paginate(page=..., per_page=...)` 对两个表格分别独立执行分页。
  - 在返回的上下文中增加全局 `per_page`。

### 前端模板改动
- 文件：`netbox_otnfaults/templates/netbox_otnfaults/otnfault.html`
- 具体逻辑：
  - 增加 CSS 隐藏两者的原生分页：
    ```css
    .impacts-table-container ul.pagination,
    .site-faults-table-container ul.pagination {
      display: none !important;
    }
    ```
  - 对 `impacts_table` 和 `site_faults_table` 分别包装自定义的分页 footer。
  - 页码跳转链接应该妥善拼接所有当前需要的参数（`impacts_page`、`site_page`、`site_time_filter` 和 `per_page`）。
  - 对“站点历史故障”的页码切换链接，添加 `#site-history` 锚点，提升切换页面后的视口用户体验。
