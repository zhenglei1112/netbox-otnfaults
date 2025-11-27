#!/usr/bin/env python
"""
测试脚本：验证新添加的故障字段功能
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')

try:
    django.setup()
except Exception as e:
    print(f"无法设置Django环境: {e}")
    sys.exit(1)

from netbox_otnfaults.models import OtnFault
from django.contrib.auth import get_user_model
from dcim.models import Site, Region
from netbox_contract.models import ServiceProvider
from django.utils import timezone

def test_new_fields():
    """测试新字段功能"""
    print("=== 测试新故障字段功能 ===")
    
    # 检查模型字段
    print("\n1. 检查模型字段:")
    field_names = [field.name for field in OtnFault._meta.get_fields()]
    new_fields = [
        'province', 'urgency', 'first_report_source', 'planned',
        'line_manager', 'maintenance_mode', 'handling_unit',
        'dispatch_time', 'departure_time', 'arrival_time', 'repair_time',
        'timeout', 'timeout_reason', 'resource_type', 'cable_route',
        'handler', 'recovery_mode'
    ]
    
    for field in new_fields:
        if field in field_names:
            print(f"  ✓ {field} 字段存在")
        else:
            print(f"  ✗ {field} 字段缺失")
    
    # 测试字段选择项
    print("\n2. 检查字段选择项:")
    
    # 紧急程度选择项
    urgency_choices = dict(OtnFault.URGENCY_CHOICES)
    print(f"  紧急程度选择项: {urgency_choices}")
    
    # 第一报障来源选择项
    first_report_choices = dict(OtnFault.FIRST_REPORT_SOURCE_CHOICES)
    print(f"  第一报障来源选择项: {first_report_choices}")
    
    # 维护方式选择项
    maintenance_choices = dict(OtnFault.MAINTENANCE_MODE_CHOICES)
    print(f"  维护方式选择项: {maintenance_choices}")
    
    # 资源类型选择项
    resource_choices = dict(OtnFault.RESOURCE_TYPE_CHOICES)
    print(f"  资源类型选择项: {resource_choices}")
    
    # 光缆路由属性选择项
    cable_route_choices = dict(OtnFault.CABLE_ROUTE_CHOICES)
    print(f"  光缆路由属性选择项: {cable_route_choices}")
    
    # 恢复方式选择项
    recovery_choices = dict(OtnFault.RECOVERY_MODE_CHOICES)
    print(f"  恢复方式选择项: {recovery_choices}")
    
    # 测试计算属性
    print("\n3. 测试计算属性:")
    
    # 创建测试故障对象
    test_fault = OtnFault()
    
    # 测试修复用时计算
    test_fault.dispatch_time = timezone.now()
    test_fault.repair_time = timezone.now()
    
    repair_duration = test_fault.repair_duration
    print(f"  修复用时计算: {repair_duration}")
    
    # 测试紧急程度颜色
    test_fault.urgency = 'high'
    urgency_color = test_fault.get_urgency_color()
    print(f"  紧急程度颜色 (高): {urgency_color}")
    
    test_fault.urgency = 'medium'
    urgency_color = test_fault.get_urgency_color()
    print(f"  紧急程度颜色 (中): {urgency_color}")
    
    test_fault.urgency = 'low'
    urgency_color = test_fault.get_urgency_color()
    print(f"  紧急程度颜色 (低): {urgency_color}")
    
    print("\n4. 检查表单字段:")
    from netbox_otnfaults.forms import OtnFaultForm
    form = OtnFaultForm()
    form_fields = list(form.fields.keys())
    
    for field in new_fields:
        if field in form_fields:
            print(f"  ✓ {field} 在表单中存在")
        else:
            print(f"  ✗ {field} 在表单中缺失")
    
    print("\n5. 检查序列化器字段:")
    from netbox_otnfaults.api.serializers import OtnFaultSerializer
    serializer = OtnFaultSerializer()
    serializer_fields = list(serializer.fields.keys())
    
    for field in new_fields + ['repair_duration']:
        if field in serializer_fields:
            print(f"  ✓ {field} 在序列化器中存在")
        else:
            print(f"  ✗ {field} 在序列化器中缺失")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_new_fields()
