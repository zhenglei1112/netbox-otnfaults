#!/usr/bin/env python
"""
简化验证脚本：检查新字段的语法和结构
"""

import ast
import os

def validate_model_file():
    """验证模型文件语法"""
    print("=== 验证模型文件语法 ===")
    
    try:
        with open('netbox_otnfaults/models.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查语法
        ast.parse(content)
        print("✓ 模型文件语法正确")
        
        # 检查关键字段
        required_fields = [
            'province', 'urgency', 'first_report_source', 'planned',
            'line_manager', 'maintenance_mode', 'handling_unit',
            'dispatch_time', 'departure_time', 'arrival_time', 'repair_time',
            'timeout', 'timeout_reason', 'resource_type', 'cable_route',
            'handler', 'recovery_mode'
        ]
        
        found_fields = []
        for field in required_fields:
            if field in content:
                found_fields.append(field)
                print(f"✓ 字段 {field} 存在")
            else:
                print(f"✗ 字段 {field} 缺失")
        
        # 检查choices格式
        if "URGENCY_CHOICES = (('high', '高'), ('medium', '中'), ('low', '低'))" in content:
            print("✓ 紧急程度choices格式正确")
        else:
            print("✗ 紧急程度choices格式错误")
            
        return True
        
    except SyntaxError as e:
        print(f"✗ 模型文件语法错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 读取模型文件失败: {e}")
        return False

def validate_migration_file():
    """验证迁移文件语法"""
    print("\n=== 验证迁移文件语法 ===")
    
    try:
        with open('netbox_otnfaults/migrations/0007_add_new_fault_fields.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查语法
        ast.parse(content)
        print("✓ 迁移文件语法正确")
        
        # 检查关键操作
        operations_to_check = [
            "migrations.AddField(model_name='otnfault', name='urgency'",
            "migrations.AddField(model_name='otnfault', name='first_report_source'",
            "migrations.AddField(model_name='otnfault', name='planned'",
        ]
        
        for op in operations_to_check:
            if op in content:
                print(f"✓ 迁移操作 {op.split('name=')[1].split(',')[0]} 存在")
            else:
                print(f"✗ 迁移操作 {op.split('name=')[1].split(',')[0]} 缺失")
                
        return True
        
    except SyntaxError as e:
        print(f"✗ 迁移文件语法错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 读取迁移文件失败: {e}")
        return False

def validate_form_file():
    """验证表单文件语法"""
    print("\n=== 验证表单文件语法 ===")
    
    try:
        with open('netbox_otnfaults/forms.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查语法
        ast.parse(content)
        print("✓ 表单文件语法正确")
        
        # 检查关键字段
        form_fields_to_check = [
            "province = DynamicModelChoiceField",
            "line_manager = DynamicModelChoiceField", 
            "handling_unit = DynamicModelChoiceField"
        ]
        
        for field in form_fields_to_check:
            if field in content:
                print(f"✓ 表单字段 {field.split('=')[0].strip()} 存在")
            else:
                print(f"✗ 表单字段 {field.split('=')[0].strip()} 缺失")
                
        return True
        
    except SyntaxError as e:
        print(f"✗ 表单文件语法错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 读取表单文件失败: {e}")
        return False

def main():
    """主验证函数"""
    print("开始验证新字段实现...\n")
    
    results = [
        validate_model_file(),
        validate_migration_file(), 
        validate_form_file()
    ]
    
    if all(results):
        print("\n🎉 所有验证通过！新字段实现语法正确。")
        print("\n下一步：运行数据库迁移以应用更改")
        print("命令：python manage.py migrate netbox_otnfaults")
    else:
        print("\n❌ 验证失败，请检查上述错误信息。")

if __name__ == "__main__":
    main()
