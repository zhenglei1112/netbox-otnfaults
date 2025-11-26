#!/usr/bin/env python3
"""
测试故障管理标签字段功能
"""

import os
import sys
import django

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from netbox_otnfaults.models import OtnFault, OtnFaultImpact
from django.contrib.auth import get_user_model
from dcim.models import Site
from tenancy.models import Tenant

def test_tags_functionality():
    """测试标签字段功能"""
    print("=== 测试故障管理标签字段功能 ===")
    
    try:
        # 获取测试数据
        User = get_user_model()
        user = User.objects.first()
        site = Site.objects.first()
        tenant = Tenant.objects.first()
        
        if not user or not site or not tenant:
            print("警告：缺少测试数据，无法创建测试对象")
            return
        
        # 创建测试故障
        print("1. 创建测试故障...")
        fault = OtnFault(
            duty_officer=user,
            fault_occurrence_time="2025-01-01 10:00:00",
            fault_category="power"
        )
        fault.save()
        fault.interruption_location.add(site)
        
        # 测试标签功能
        print("2. 测试标签功能...")
        fault.tags.add("紧急", "电力故障", "主干线路")
        print(f"  故障标签: {[tag.name for tag in fault.tags.all()]}")
        
        # 创建测试故障影响
        print("3. 创建测试故障影响...")
        impact = OtnFaultImpact(
            otn_fault=fault,
            impacted_service=tenant,
            service_interruption_time="2025-01-01 10:00:00"
        )
        impact.save()
        
        # 测试故障影响标签功能
        print("4. 测试故障影响标签功能...")
        impact.tags.add("业务中断", "重要客户")
        print(f"  故障影响标签: {[tag.name for tag in impact.tags.all()]}")
        
        # 测试标签查询
        print("5. 测试标签查询...")
        urgent_faults = OtnFault.objects.filter(tags__name="紧急")
        print(f"  紧急故障数量: {urgent_faults.count()}")
        
        print("\n✅ 标签字段功能测试完成！")
        
        # 清理测试数据
        print("6. 清理测试数据...")
        impact.delete()
        fault.delete()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tags_functionality()
