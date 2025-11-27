#!/usr/bin/env python3
"""
测试故障管理journal功能
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
    print("请确保在NetBox环境中运行此脚本")
    sys.exit(1)

from django.contrib.contenttypes.models import ContentType
from extras.models import JournalEntry
from netbox_otnfaults.models import OtnFault, OtnFaultImpact
from django.contrib.auth import get_user_model

def test_journal_functionality():
    """测试journal功能"""
    print("=== 测试故障管理Journal功能 ===\n")
    
    # 检查模型是否支持journaling
    print("1. 检查模型是否支持journaling:")
    print(f"   OtnFault 支持journaling: {hasattr(OtnFault, 'journal_entries')}")
    print(f"   OtnFaultImpact 支持journaling: {hasattr(OtnFaultImpact, 'journal_entries')}")
    
    # 检查JournalingMixin是否正确继承
    print("\n2. 检查JournalingMixin继承:")
    from netbox.models.features import has_feature
    otn_fault_ct = ContentType.objects.get_for_model(OtnFault)
    otn_fault_impact_ct = ContentType.objects.get_for_model(OtnFaultImpact)
    
    print(f"   OtnFault 支持journaling功能: {has_feature(otn_fault_ct, 'journaling')}")
    print(f"   OtnFaultImpact 支持journaling功能: {has_feature(otn_fault_impact_ct, 'journaling')}")
    
    # 检查序列化器是否包含journal_entries字段
    print("\n3. 检查序列化器字段:")
    from netbox_otnfaults.api.serializers import OtnFaultSerializer, OtnFaultImpactSerializer
    
    otn_fault_fields = OtnFaultSerializer().get_fields()
    otn_fault_impact_fields = OtnFaultImpactSerializer().get_fields()
    
    print(f"   OtnFaultSerializer 包含journal_entries字段: {'journal_entries' in otn_fault_fields}")
    print(f"   OtnFaultImpactSerializer 包含journal_entries字段: {'journal_entries' in otn_fault_impact_fields}")
    
    # 检查模板是否包含journal面板
    print("\n4. 检查模板文件:")
    otn_fault_template_path = 'netbox_otnfaults/templates/netbox_otnfaults/otnfault.html'
    otn_fault_impact_template_path = 'netbox_otnfaults/templates/netbox_otnfaults/otnfaultimpact.html'
    
    if os.path.exists(otn_fault_template_path):
        with open(otn_fault_template_path, 'r', encoding='utf-8') as f:
            otn_fault_template_content = f.read()
            has_journal_panel = '{% include \'inc/panels/journal.html\' %}' in otn_fault_template_content
            print(f"   OtnFault模板包含journal面板: {has_journal_panel}")
    
    if os.path.exists(otn_fault_impact_template_path):
        with open(otn_fault_impact_template_path, 'r', encoding='utf-8') as f:
            otn_fault_impact_template_content = f.read()
            has_journal_panel = '{% include \'inc/panels/journal.html\' %}' in otn_fault_impact_template_content
            print(f"   OtnFaultImpact模板包含journal面板: {has_journal_panel}")
    
    print("\n=== 测试完成 ===")

if __name__ == '__main__':
    test_journal_functionality()
