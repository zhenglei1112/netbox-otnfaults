# 需求文档：割接详情页列表分页组件统一化

## 1. 业务背景与问题
在排查系统时，发现割接详情页（`cutovertask.html`）下方的“影响业务”列表依然在使用 `django_tables2` 的默认分页组件。当关联的影响业务记录数较多（超过25条）时，会在页面上渲染出不符合规范的 `1 2 3 next` 字符样式，同样违背了 `AGENTS.md` 规范。

## 2. 需求目标
1. 隐藏割接详情页下“影响业务”列表的原生分页器。
2. 引入符合 Netbox UI 设计的自定义分页器。
3. 自定义分页器需要包括三个要素：
   - 页码导航（`‹ 1 2 ... 5 6 7 ... 10 ›` 样式）
   - 显示信息（`显示 X-Y 共 Z` 格式）
   - 每页显示条数选择（下拉框支持 25/50/100/250/500）
4. 保证在切换每页数量时，能正确生效并保留请求状态。

## 3. 实现规范与范围

### 后端控制器改动
- 文件：`netbox_otnfaults/views.py`
- 控制器类：`CutoverTaskView`
- 具体逻辑：
  - 从 `request.GET` 中获取 `per_page`（优先全局 `per_page`，兼容原有的 `impact-per_page`）并安全转换为整数。
  - 从 `request.GET` 中获取页码 `page`（兼容原有的 `impact-page`）。
  - 通过 `table.paginate(page=..., per_page=...)` 执行分页。
  - 在返回的上下文中增加全局 `per_page`。

### 前端模板改动
- 文件：`netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html`
- 具体逻辑：
  - 增加/注入 CSS 隐藏原生分页：
    ```css
    .impacts-table-container ul.pagination {
      display: none !important;
    }
    ```
  - 在 `impacts_table` 下方引入包装了自定义分页的 card-footer 结构。
  - 页码跳转链接应该正确地传递 `page` 和 `per_page` 参数。
