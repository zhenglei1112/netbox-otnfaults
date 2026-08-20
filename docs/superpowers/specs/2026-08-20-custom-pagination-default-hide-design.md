# 自定义分页统一隐藏默认分页设计

## 目标

所有已经提供自定义分页组件的详情页和列表页必须隐藏 django-tables2 或 NetBox 自动生成的默认分页，仅显示页面自己的 NetBox 风格 `card-footer` 分页。

## 范围

详情页：

- `netbox_otnfaults/templates/netbox_otnfaults/otnfault.html`
- `netbox_otnfaults/templates/netbox_otnfaults/cutovertask.html`
- `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice.html`
- `netbox_otnfaults/templates/netbox_otnfaults/circuitservice.html`
- `netbox_otnfaults/templates/netbox_otnfaults/heavyduty.html`
- `netbox_otnfaults/templates/netbox_otnfaults/otnpathgroup.html`

列表页：

- `netbox_otnfaults/templates/netbox_otnfaults/barefiberservice_list.html`
- `netbox_otnfaults/templates/netbox_otnfaults/circuitservice_list.html`
- `netbox_otnfaults/templates/netbox_otnfaults/heavyduty_list.html`

不包含没有自定义分页的页面，也不修改 NetBox 核心模板。

## 方案

每个表格容器同时匹配标签限定和标签无关的分页类：

```css
.table-scope ul.pagination,
.table-scope .pagination {
  display: none !important;
}
```

默认分页位于 `.table-scope` 内，自定义分页位于其外部的 `.card-footer`，因此隐藏规则不会影响自定义分页。列表页同时覆盖 `.table-container`、`.table-responsive` 及 NetBox 可能输出的默认卡片 footer；自定义 footer 继续通过 `.custom-pagination` 排除。

割接详情页的样式块由无效的 `extra_styles` 改为 NetBox 4.x 支持的 `head`，并保留 `{{ block.super }}`。其他在 `content` 内输出样式的页面维持现有结构。

## 测试

- 静态模板回归测试逐页验证默认分页隐藏选择器存在。
- 验证详情页自定义分页仍位于表格容器外。
- 验证列表页保留 `.custom-pagination`，且默认 card footer 的隐藏规则不会匹配它。
- 割接详情测试验证使用 `head`、包含 `{{ block.super }}`，且不再使用 `extra_styles`。
- 运行相关分页测试及 `git diff --check`。

## 成功标准

- 上述 9 个页面只显示自定义分页。
- 自定义页码、上一页/下一页和每页数量选择保持现有行为。
- 不修改分页查询参数、视图逻辑或数据范围。
