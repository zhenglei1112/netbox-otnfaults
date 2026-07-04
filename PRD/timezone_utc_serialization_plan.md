# 统一将日期时间型字段在保存前转换为 UTC 的实施计划 (已更新)

为了解决由于时区信息差异，导致 NetBox 审计日志中产生不必要的变更对比问题，并根据代码审查反馈进行针对性改进。

## 审查反馈回应与方案调整

### P1: 时区转换执行顺序的不确定性
- **原方案**：通过 `pre_save` 信号处理器。由于 Django 的信号执行顺序与注册顺序相关，NetBox 的审计日志快照信号可能先于我们的 pre_save 执行，导致记录的依然是转换前带 `+08:00` 时区的属性。
- **改进方案**：在 `netbox_otnfaults/models.py` 中引入统一的抽象基类 `OtnBaseModel`，重写其 `save()` 方法。让本插件中所有的模型均继承自该基类。这能 100% 保证在模型执行具体的 `save()` 写入动作及触发任何 pre_save 信号之前，完成时区向 UTC 的转换。

### P2: 单元测试局限性
- **原方案**：仅做 AST 语法检测，无法进行行为验证。
- **改进方案**：在 `tests/test_datetime_utc_save.py` 中，除了保留对 `OtnBaseModel` 的 AST 结构和属性调用验证，还通过 Mock 一个具有字段元数据与 aware datetime 的 Dummy 实例来测试 UTC 转换逻辑本身的行为，验证其转换结果的正确性，以及对非本插件模型进行忽略的行为。

## 方案设计

1. **引入统一基类**：
   在 `netbox_otnfaults/models.py` 中，定义一个继承自 `NetBoxModel` 的抽象类 `OtnBaseModel`：
   ```python
   class OtnBaseModel(NetBoxModel):
       class Meta:
           abstract = True

       def save(self, *args, **kwargs):
           # 在写入数据库前将所有 DateTimeField 的 aware datetime 统一转为 UTC
           for field in self._meta.fields:
               if isinstance(field, models.DateTimeField):
                   val = getattr(self, field.name)
                   if isinstance(val, datetime.datetime) and timezone.is_aware(val):
                       setattr(self, field.name, val.astimezone(datetime.timezone.utc))
           super().save(*args, **kwargs)
   ```

2. **更新所有插件模型**：
   将 `models.py` 内原先继承自 `NetBoxModel` 的 11 个模型统一改为继承 `OtnBaseModel`。
   - `CutoverTask`
   - `OtnFault`
   - `OtnFaultImpact`
   - `OtnPathGroup`
   - `OtnPathGroupSite`
   - `OtnPath`
   - `OtnMapPreference`
   - `BareFiberService`
   - `CircuitService`
   - `CutoverImpact`
   - `HeavyDuty`

3. **清理 `signals.py`**：
   移除先前在 `netbox_otnfaults/signals.py` 中添加的 `pre_save` 相关逻辑。

## 拟议的修改

### 修改 `netbox_otnfaults/models.py`
定义 `OtnBaseModel`，并修改上述 11 个模型类的继承关系。

### 修改 `netbox_otnfaults/signals.py`
回滚 `pre_save` 的改动，恢复文件。

### 修改 `tests/test_datetime_utc_save.py`
更新测试。除验证 `models.py` 中定义并应用了 `OtnBaseModel` 的 AST 静态结构外，增加基于 Mock 实例的行为验证，覆盖：
- 转换函数能够将带有 `Asia/Shanghai` 时区的 datetime 正确规范化为 UTC，且具体表示的时间瞬间保持不变。
- 对非本插件模型的忽略行为验证。

## 验证计划

### 自动化测试
运行全局测试：
```bash
.\.venv\Scripts\python.exe tests/test_runner.py
```
确保包含新行为测试的用例执行成功。
