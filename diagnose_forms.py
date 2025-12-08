#!/usr/bin/env python3
"""
诊断脚本 - 检查 forms.py 文件的导入问题
在服务器上运行此脚本: python3 diagnose_forms.py
"""

import sys
import traceback

print("=" * 60)
print("诊断 netbox_otnfaults.forms 导入问题")
print("=" * 60)

# 1. 检查文件是否存在
print("\n1. 检查文件路径...")
forms_path = "/mnt/shared-plugins/netbox-otnfaults/netbox_otnfaults/forms.py"
try:
    with open(forms_path, 'r') as f:
        content = f.read()
    print(f"✓ 文件存在: {forms_path}")
    print(f"  文件大小: {len(content)} 字节")
    print(f"  行数: {len(content.splitlines())} 行")
except Exception as e:
    print(f"✗ 无法读取文件: {e}")
    sys.exit(1)

# 2. 检查语法错误
print("\n2. 检查Python语法...")
try:
    compile(content, forms_path, 'exec')
    print("✓ 语法检查通过")
except SyntaxError as e:
    print(f"✗ 语法错误:")
    print(f"  行 {e.lineno}: {e.msg}")
    print(f"  {e.text}")
    sys.exit(1)

# 3. 尝试导入模块
print("\n3. 尝试导入模块...")
sys.path.insert(0, '/mnt/shared-plugins/netbox-otnfaults')
try:
    import netbox_otnfaults.forms as forms_module
    print("✓ 模块导入成功")
except Exception as e:
    print(f"✗ 模块导入失败:")
    print(traceback.format_exc())
    sys.exit(1)

# 4. 检查类是否存在
print("\n4. 检查表单类...")
expected_classes = [
    'OtnFaultForm',
    'OtnFaultImpactForm', 
    'OtnFaultFilterForm',
    'OtnFaultImpactFilterForm',
    'OtnFaultBulkEditForm',
    'OtnFaultImpactBulkEditForm',
    'OtnFaultImportForm',
    'OtnFaultImpactImportForm'
]

missing_classes = []
for class_name in expected_classes:
    if hasattr(forms_module, class_name):
        print(f"✓ {class_name} 存在")
    else:
        print(f"✗ {class_name} 缺失")
        missing_classes.append(class_name)

# 5. 显示所有可用的类和函数
print("\n5. 模块中的所有公开对象:")
public_items = [name for name in dir(forms_module) if not name.startswith('_')]
for item in public_items[:20]:  # 只显示前20个
    print(f"  - {item}")
if len(public_items) > 20:
    print(f"  ... 还有 {len(public_items) - 20} 个")

# 6. 总结
print("\n" + "=" * 60)
if missing_classes:
    print(f"✗ 诊断失败: 缺失 {len(missing_classes)} 个类")
    print("缺失的类:", ", ".join(missing_classes))
    print("\n建议:")
    print("1. 检查本地文件是否正确同步到服务器")
    print("2. 清除Python缓存: find /mnt/shared-plugins/netbox-otnfaults -name '*.pyc' -delete")
    print("3. 检查文件权限")
else:
    print("✓ 所有检查通过!")
print("=" * 60)
