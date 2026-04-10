# 电路业务模型排序与业务门类调整需求文档

## 1. 需求背景
为了优化电路业务（`CircuitService`）在列表视图中的展示效果，以及满足业务门类分类的特定排序要求。现需要修改系统默认排序规则，并调整业务门类的相关配置信息。

## 2. 目标与范围
- **默认列表排序调整**：所有涉及电路业务的列表，其默认排序优先级依次为：`业务门类` > `业务组` > `专线名称`。
- **业务门类自定义排序**：业务门类字段需要支持自定义排序顺序。
- **业务门类枚举项调整**：增加新的门类“部机关”，并将现有的“航信”更名为“中航信”。

## 3. 详细设计方案

### 3.1 模型元属性修改 (Meta.ordering)
在 `CircuitService` 模型的 `Meta` 类中，将原本基于专线名称和编号的排序策略重构为：
```python
ordering = ('business_category', 'service_group', 'special_line_name')
```

### 3.2 自定义业务门类排序映射 (BusinessCategoryChoices)
Django 基于数据库原生的 Enum 进行字符级排序。为了不依赖复杂的 QuerySet 视图重新注入（影响API端和Table表头点击的响应逻辑），直接干预数据表层的词法排序策略。通过给原有的 key 添加以两位补零数字前缀 `01_` 到 `11_` 的方式，令框架原生的 `ORDER BY` 满足客户的强制顺序：
1. `01_ministry_province_transport` (部省传输)
2. `02_commercial_other` (商业其他)
3. `03_maritime_service` (海事业务)
4. `04_road_network_service` (路网业务)
5. `05_legacy_ruijie_service` (老锐捷业务)
6. `06_travelsky` (中航信 - 名称修正)
7. `07_jinhang` (金航)
8. `08_lanxun` (缆讯)
9. `09_commercial_100g` (商业百G)
10. `10_changhang` (长航)
11. `11_ministry_organ` (部机关 - 新增)

### 3.3 测试用例同步更新
更新涉及到 `BusinessCategoryChoices` 在 `tests/test_circuit_service_external_business.py` 中的硬编码验证数组，加入"中航信"和"部机关"以保证原有单元测试正常通过。

## 4. 迁移指南
> **注意**：更改 `Choices` 枚举的底层键名会触发 Django schema 层面的变更要求。您需要在您的运行环境中执行以下迁移命令以同步底层数据结构：
```bash
python manage.py makemigrations netbox_otnfaults
python manage.py migrate
```
