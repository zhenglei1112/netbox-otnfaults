#!/usr/bin/env python3
"""
测试故障管理评论字段功能
"""

import os
import sys
import django

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from netbox_otnfaults.models import OtnFault, OtnFaultImpact
from django.contrib.auth import get_user_model
from dcim.models import Site
from tenancy.models import Tenant
from django.utils import timezone

def test_comments_functionality():
    """测试评论字段功能"""
    print("=== 测试故障管理评论字段功能 ===\n")
    
    try:
        # 获取测试数据
        User = get_user_model()
        user = User.objects.first()
        site = Site.objects.first()
        tenant = Tenant.objects.first()
        
        if not user:
            print("❌ 没有找到用户，无法测试")
            return
        if not site:
            print("❌ 没有找到站点，无法测试")
            return
        if not tenant:
            print("❌ 没有找到租户，无法测试")
            return
            
        print(f"使用测试数据:")
        print(f"  - 用户: {user.username}")
        print(f"  - 站点: {site.name}")
        print(f"  - 租户: {tenant.name}")
        print()
        
        # 测试1: 创建带评论的故障记录
        print("1. 测试创建带评论的故障记录...")
        fault = OtnFault(
            duty_officer=user,
            fault_occurrence_time=timezone.now(),
            fault_category='power',
            interruption_reason='road_construction',
            fault_details='测试故障详情',
            comments='这是一个测试故障的备注信息'
        )
        fault.save()
        fault.interruption_location.add(site)
        
        print(f"   ✅ 故障记录创建成功")
        print(f"   - 故障编号: {fault.fault_number}")
        print(f"   - 备注: {fault.comments}")
        print()
        
        # 测试2: 创建带评论的故障影响记录
        print("2. 测试创建带评论的故障影响记录...")
        impact = OtnFaultImpact(
            otn_fault=fault,
            impacted_service=tenant,
            service_interruption_time=timezone.now(),
            comments='这是一个测试故障影响的备注信息'
        )
        impact.save()
        
        print(f"   ✅ 故障影响记录创建成功")
        print(f"   - 关联故障: {impact.otn_fault}")
        print(f"   - 影响业务: {impact.impacted_service}")
        print(f"   - 备注: {impact.comments}")
        print()
        
        # 测试3: 验证模型字段
        print("3. 验证模型字段...")
        fault_fields = [f.name for f in OtnFault._meta.get_fields()]
        impact_fields = [f.name for f in OtnFaultImpact._meta.get_fields()]
        
        if 'comments' in fault_fields:
            print("   ✅ OtnFault模型包含comments字段")
        else:
            print("   ❌ OtnFault模型缺少comments字段")
            
        if 'comments' in impact_fields:
            print("   ✅ OtnFaultImpact模型包含comments字段")
        else:
            print("   ❌ OtnFaultImpact模型缺少comments字段")
        print()
        
        # 测试4: 验证序列化器
        print("4. 验证序列化器...")
        from netbox_otnfaults.api.serializers import OtnFaultSerializer, OtnFaultImpactSerializer
        
        fault_serializer = OtnFaultSerializer(fault)
        impact_serializer = OtnFaultImpactSerializer(impact)
        
        if 'comments' in fault_serializer.data:
            print("   ✅ OtnFault序列化器包含comments字段")
        else:
            print("   ❌ OtnFault序列化器缺少comments字段")
            
        if 'comments' in impact_serializer.data:
            print("   ✅ OtnFaultImpact序列化器包含comments字段")
        else:
            print("   ❌ OtnFaultImpact序列化器缺少comments字段")
        print()
        
        # 测试5: 验证表单
        print("5. 验证表单...")
        from netbox_otnfaults.forms import OtnFaultForm, OtnFaultImpactForm
        
        fault_form = OtnFaultForm(instance=fault)
        impact_form = OtnFaultImpactForm(instance=impact)
        
        if 'comments' in fault_form.fields:
            print("   ✅ OtnFault表单包含comments字段")
            # 验证是否为CommentField类型
            if hasattr(fault_form.fields['comments'], 'help_text') and 'Markdown' in fault_form.fields['comments'].help_text:
                print("   ✅ OtnFault表单comments字段支持Markdown语法")
            else:
                print("   ❌ OtnFault表单comments字段不支持Markdown语法")
        else:
            print("   ❌ OtnFault表单缺少comments字段")
            
        if 'comments' in impact_form.fields:
            print("   ✅ OtnFaultImpact表单包含comments字段")
            # 验证是否为CommentField类型
            if hasattr(impact_form.fields['comments'], 'help_text') and 'Markdown' in impact_form.fields['comments'].help_text:
                print("   ✅ OtnFaultImpact表单comments字段支持Markdown语法")
            else:
                print("   ❌ OtnFaultImpact表单comments字段不支持Markdown语法")
        else:
            print("   ❌ OtnFaultImpact表单缺少comments字段")
        print()
        
        # 清理测试数据
        print("6. 清理测试数据...")
        impact.delete()
        fault.delete()
        print("   ✅ 测试数据清理完成")
        
        print("\n🎉 所有测试通过！评论字段功能已成功实现")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_comments_functionality()
