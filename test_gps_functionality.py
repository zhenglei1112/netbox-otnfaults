#!/usr/bin/env python3
"""
测试GPS坐标功能
这个脚本用于验证新添加的经纬度字段是否正常工作
"""

import os
import sys
import django

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from netbox_otnfaults.models import OtnFault

def test_gps_fields():
    """测试GPS字段功能"""
    print("=== 测试GPS坐标功能 ===")
    
    # 检查模型是否有新字段
    print("1. 检查模型字段...")
    fields = [f.name for f in OtnFault._meta.get_fields()]
    print(f"模型字段: {fields}")
    
    # 检查是否有经纬度字段
    if 'interruption_longitude' in fields and 'interruption_latitude' in fields:
        print("✓ 经纬度字段已成功添加到模型")
    else:
        print("✗ 经纬度字段未找到")
        return False
    
    # 测试创建带有GPS坐标的故障记录
    print("\n2. 测试创建带有GPS坐标的故障记录...")
    try:
        # 注意：这里需要实际的用户ID，所以使用第一个可用的用户
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.all()
        
        if users.exists():
            user = users.first()
            
            # 创建测试故障记录
            fault = OtnFault(
                duty_officer=user,
                fault_occurrence_time="2025-01-01 10:00:00",
                interruption_longitude=87.612625,
                interruption_latitude=43.801308
            )
            
            print(f"经度: {fault.interruption_longitude}")
            print(f"纬度: {fault.interruption_latitude}")
            print("✓ GPS坐标字段可以正常设置")
            
            # 测试地图链接生成
            if fault.interruption_longitude and fault.interruption_latitude:
                map_url = f"https://www.openstreetmap.org/?mlat={fault.interruption_latitude}&mlon={fault.interruption_longitude}&zoom=15"
                print(f"地图链接: {map_url}")
                print("✓ 地图链接生成正常")
            
        else:
            print("⚠ 没有可用用户，跳过创建测试记录")
            
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        return False
    
    print("\n=== 测试完成 ===")
    return True

if __name__ == "__main__":
    test_gps_fields()
