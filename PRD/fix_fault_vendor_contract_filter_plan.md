# 故障模型列表“代维方/租赁方”及“代维/租赁合同”筛选无效修复方案

此方案旨在解决故障模型列表筛选功能中，“代维方/租赁方”和“代维/租赁合同”两个下拉框由于未正确匹配第三方 `netbox_contract` 插件的 API 路径而导致 404 无法加载数据的问题；同时解决由于在同一个筛选表单中重复包含该两个字段导致生成的 DOM ID 冲突、进一步引起筛选失效的问题。

## 需求背景与问题原因
1. **API路径推导错误**：
   在 Netbox 4.x 下，`DynamicModelChoiceField` 默认使用 `netbox_contract` 的 app_label 来推导 API 端点路径，但第三方 `netbox-contract` 插件的 `PluginConfig` 中注册的 `base_url` 被显式重写为了 `'contracts'`。因此，原本推导出的 `/api/plugins/netbox-contract/` 返回 404，而真正的端点是 `/api/plugins/contracts/serviceproviders/` 和 `/api/plugins/contracts/contracts/`。
2. **DOM ID冲突**：
   在故障筛选表单 `OtnFaultFilterForm` 的 `fieldsets` 中，`handling_unit` 和 `contract` 字段被配置在两个 FieldSet 里（“线路主管补充信息”和“供电故障补充信息”）。这使得列表页侧边栏中这两个输入框被渲染了两次。由于 HTML ID 与 Name 重复，导致 TomSelect 初始化监听与表单解析完全失效，导致筛选框无法正常工作。

## 拟议更改

### 1. 修改 `netbox_otnfaults/forms.py`

#### A. 移除 `OtnFaultFilterForm` 的重复渲染字段
在 `OtnFaultFilterForm` 的 `fieldsets` 中移除“供电故障补充信息”的 `'handling_unit'` 和 `'contract'`：
```python
        FieldSet(
            'power_data_type', 'root_cause_analysis', 'rectification_status', 'rectification_measures',
            'rectification_description', 'rectification_subject', 'rectification_progress',
            'planned_completion_date', 'actual_completion_date', 'rectification_completion_description',
            'power_recovery_mode', 'power_maintenance_mode',
            name='供电故障补充信息'
        ),
```

#### B. 显式绑定 `data-url` API 路径
在涉及的几个 Form 初始化方法 `__init__` 中显式重写 `data-url` 属性：
- **`OtnFaultForm.__init__`**：
  ```python
  if 'handling_unit' in self.fields:
      self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
  if 'contract' in self.fields:
      self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'
  ```
- **`OtnFaultBulkEditForm.__init__`**（新增该方法）：
  ```python
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      if 'handling_unit' in self.fields:
          self.fields['handling_unit'].widget.attrs['data-url'] = '/api/plugins/contracts/serviceproviders/'
      if 'contract' in self.fields:
          self.fields['contract'].widget.attrs['data-url'] = '/api/plugins/contracts/contracts/'
  ```
- **`OtnFaultFilterForm.__init__`**：
  同上追加显式绑定。
- **`CutoverTaskForm.__init__`**：
  同上追加显式绑定。

## 验证与测试
1. **单元测试与回归检查**：
   - 运行已有的字段检查与模板测试，验证在 `OtnFaultForm` 里面保留的两个 FieldSet 定义（供动态 Relocation 用）仍然合规。
   - 命令：`.\.venv\Scripts\python.exe -m unittest tests/test_otnfault_power_contract_fields.py`
2. **页面检查**：
   - 查看列表页，侧边栏只显示一个代维方和合同筛选框，且能够正常下拉读取数据。
