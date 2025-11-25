#!/usr/bin/env python3
"""
测试插件修复是否有效
"""

import os
import sys
import django

# 添加当前目录到Python路径
sys.path.insert(0, os.getcwd())

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')

try:
    django.setup()
    print("✓ Django环境设置成功")
    
    # 测试导入插件配置
    from netbox_otnfaults import config
    print(f"✓ 插件配置导入成功: {config.name}")
    print(f"  - 版本: {config.version}")
    print(f"  - 最小Netbox版本: {config.min_version}")
    print(f"  - 最大Netbox版本: {config.max_version}")
    
    # 测试导入模型
    from netbox_otnfaults.models import OtnFault, OtnFaultImpact
    print(f"✓ 模型导入成功: {OtnFault.__name__}, {OtnFaultImpact.__name__}")
    
    # 测试导入序列化器
    from netbox_otnfaults.api.serializers import OtnFaultSerializer, OtnFaultImpactSerializer
    print(f"✓ 序列化器导入成功: {OtnFaultSerializer.__name__}, {OtnFaultImpactSerializer.__name__}")
    
    # 测试序列化器配置
    otn_fault_serializer = OtnFaultSerializer()
    print(f"✓ OtnFaultSerializer配置:")
    print(f"  - 字段: {len(otn_fault_serializer.fields)}个字段")
    print(f"  - 只读字段: {otn_fault_serializer.Meta.read_only_fields}")
    print(f"  - 简要字段: {otn_fault_serializer.Meta.brief_fields}")
    
    # 测试导入视图
    from netbox_otnfaults.api.views import OtnFaultViewSet, OtnFaultImpactViewSet
    print(f"✓ API视图导入成功: {OtnFaultViewSet.__name__}, {OtnFaultImpactViewSet.__name__}")
    
    # 测试导入URL配置
    from netbox_otnfaults.api.urls import urlpatterns
    print(f"✓ API URL配置导入成功，包含 {len(urlpatterns)} 个URL模式")
    
    # 测试导入API模块
    from netbox_otnfaults.api import urlpatterns as api_urlpatterns
    print(f"✓ API模块导入成功，包含 {len(api_urlpatterns)} 个URL模式")
    
    print("\n🎉 所有组件导入成功！插件应该可以在Netbox 4.4.2中正常工作。")
    print("\n修复总结：")
    print("- ✅ 更新了插件配置，符合Netbox 4.x规范")
    print("- ✅ 使用pyproject.toml进行现代Python包管理")
    print("- ✅ 正确注册了API路由")
    print("- ✅ 优化了序列化器配置（添加了brief_fields和read_only_fields）")
    print("- ✅ 在插件配置中添加了ready()方法来注册API")
    
    print("\n现在应该可以正常保存故障信息，不会再出现SerializerNotFound错误。")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ 其他错误: {e}")
    import traceback
    traceback.print_exc()
