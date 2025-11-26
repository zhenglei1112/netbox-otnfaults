# GPS坐标功能实现总结

## 功能概述
为Netbox故障登记插件添加了GPS坐标功能，包括中断位置经度和纬度字段，以及在详情页面显示GPS坐标和地图链接。

## 实现的更改

### 1. 模型层 (models.py)
- 添加了两个新的DecimalField字段：
  - `interruption_longitude`: 中断位置经度，最大9位数字，6位小数
  - `interruption_latitude`: 中断位置纬度，最大8位数字，6位小数
- 两个字段均为可选字段（blank=True, null=True）
- 添加了中文帮助文本："GPS坐标（十进制格式, xx.yyyyyy）"

### 2. 表单层 (forms.py)
- 在OtnFaultForm的Meta.fields中添加了经纬度字段
- 确保新字段在创建和编辑故障时可用

### 3. API序列化器 (api/serializers.py)
- 在OtnFaultSerializer的fields列表中添加了经纬度字段
- 确保API接口能够返回和接收GPS坐标数据

### 4. 模板层 (templates/netbox_otnfaults/otnfault.html)
- 在故障详情页面添加了"GPS坐标"行
- 显示格式：纬度, 经度（例如：43.801308, 87.612625）
- 添加了地图图标按钮，点击在新窗口打开OpenStreetMap显示位置
- 当没有GPS坐标时显示"-"

### 5. 数据库迁移 
- `migrations/0002_add_gps_fields.py` - 添加新的经纬度字段到数据库
- `migrations/0004_fix_all_null_constraints.py` - 修复所有可选字段的null约束问题（故障分类、中断原因、故障详细情况）

## 功能特点

### GPS坐标显示
- 在故障详情页面以"纬度, 经度"格式显示
- 使用DecimalField确保精度（6位小数）
- 支持中国境内的GPS坐标格式

### 地图集成
- 使用OpenStreetMap作为默认地图服务
- 点击地图图标在新窗口打开地图
- 地图链接格式：`https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}&zoom=15`
- 默认缩放级别为15，提供详细视图

### 用户体验
- 地图图标使用Material Design图标库的`mdi-map-marker`
- 按钮样式为`btn btn-sm btn-outline-secondary`
- 鼠标悬停显示提示："在地图中查看位置"

## 技术细节

### 字段配置
```python
interruption_longitude = models.DecimalField(
    max_digits=9,  # 支持-180.000000到180.000000
    decimal_places=6,
    blank=True,
    null=True,
    verbose_name='中断位置经度',
    help_text='GPS坐标（十进制格式, xx.yyyyyy）'
)

interruption_latitude = models.DecimalField(
    max_digits=8,  # 支持-90.000000到90.000000
    decimal_places=6,
    blank=True,
    null=True,
    verbose_name='中断位置纬度',
    help_text='GPS坐标（十进制格式, xx.yyyyyy）'
)
```

### 模板实现
```html
<tr>
  <th scope="row">GPS坐标</th>
  <td>
    {% if object.interruption_longitude and object.interruption_latitude %}
      {{ object.interruption_latitude }}, {{ object.interruption_longitude }}
      <a href="https://www.openstreetmap.org/?mlat={{ object.interruption_latitude }}&mlon={{ object.interruption_longitude }}&zoom=15" 
         target="_blank" 
         class="btn btn-sm btn-outline-secondary ms-2"
         title="在地图中查看位置">
        <i class="mdi mdi-map-marker"></i>
      </a>
    {% else %}
      -
    {% endif %}
  </td>
</tr>
```

## 部署说明

1. 应用数据库迁移：
   ```bash
   python manage.py migrate netbox_otnfaults
   ```

2. 重启Netbox服务以加载新的模板和表单配置

3. 验证功能：
   - 创建或编辑故障记录，填写GPS坐标
   - 查看故障详情页面，确认GPS坐标显示正常
   - 点击地图图标验证地图链接正常工作

## 测试脚本
提供了`test_gps_functionality.py`脚本用于验证功能实现。

## 兼容性
- 与现有故障记录完全兼容
- 不影响现有功能
- 向后兼容，新字段为可选字段
