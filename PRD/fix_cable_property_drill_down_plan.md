# 修复物理故障统计光缆属性下钻明细不正确方案

解决在物理故障看板中，点击“光缆属性”（如自建光缆、协调资源、租赁纤芯）卡片或图表下钻时，下方故障明细数据为空且提示“口径核对不一致”的问题。

## 1. 问题背景
在物理故障统计页面，当用户点击“光缆属性”饼图或指标卡片（例如“自建光缆”时），前端会将 `resource_type="自建光缆"` 作为 Query Parameter 发送给后端的故障明细下钻 API：`/api/plugins/otnfaults/statistics-details/`。

然而，在后端的下钻 API `FaultStatisticsDetailsAPI` 中，其别名映射字典 `resource_type_aliases` 定义如下：
```python
resource_type_aliases: dict[str, str] = {
    '自建': ResourceTypeChoices.SELF_BUILT,
    '协调': ResourceTypeChoices.COORDINATED,
    '租赁': ResourceTypeChoices.LEASED,
    '未填写': 'unfilled',
}
```
该字典未能包含完整的“自建光缆”、“协调资源”、“租赁纤芯”的中文到数据库常量的映射。导致接口在过滤时无法识别，直接将 “自建光缆” 传递给 ORM 过滤，从而无法匹配到数据库中存储的值 `self_built`，最终查出的明细起数为 0，造成前后端口径核对不一致的现象。

## 2. 改造方案

### 后端代码修改
修改 `netbox_otnfaults/statistics_views.py` 中的 `resource_type_aliases` 字典，扩展映射内容，使其兼容完整名称和简写名称：

```python
        resource_type_aliases: dict[str, str] = {
            '自建': ResourceTypeChoices.SELF_BUILT,
            '自建光缆': ResourceTypeChoices.SELF_BUILT,
            '协调': ResourceTypeChoices.COORDINATED,
            '协调资源': ResourceTypeChoices.COORDINATED,
            '租赁': ResourceTypeChoices.LEASED,
            '租赁纤芯': ResourceTypeChoices.LEASED,
            '未填写': 'unfilled',
        }
```

## 3. 验证方案
在项目测试框架或通过临时 Django 模拟脚本，传入 `resource_type='自建光缆'` 等参数，验证返回的 JSON 中 `results` 的过滤结果符合预期。
