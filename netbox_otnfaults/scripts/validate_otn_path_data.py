#!/usr/bin/env python
"""
验证 OTN 路径数据的完整性和质量
用于确认数据源替换后的可用性
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from netbox_otnfaults.models import OtnPath
from netbox_otnfaults.services.otn_path_graph import get_otn_path_graph_service


def validate_otn_paths():
    """验证 OTN 路径数据"""
    print("=" * 60)
    print("OTN 路径数据验证")
    print("=" * 60)
    
    # 1. 统计总数
    total_paths = OtnPath.objects.count()
    print(f"\n📊 总路径数量: {total_paths}")
    
    # 2. 检查 geometry 字段
    valid_paths = OtnPath.objects.exclude(geometry__isnull=True).exclude(geometry={})
    valid_count = valid_paths.count()
    invalid_count = total_paths - valid_count
    
    print(f"✅ 有效路径（含 geometry）: {valid_count}")
    print(f"⚠️  无效路径（缺 geometry）: {invalid_count}")
    
    if valid_count == 0:
        print("\n❌ 错误：未找到任何有效路径数据！")
        print("   请确保已导入 OtnPath 数据并填充 geometry 字段。")
        return False
    
    # 3. 检查数据格式
    print(f"\n🔍 检查数据格式（前 5 条）...")
    for i, path in enumerate(valid_paths[:5], 1):
        geom = path.geometry
        geom_type = geom.get('type') if isinstance(geom, dict) else 'Unknown'
        coords = geom.get('coordinates', []) if isinstance(geom, dict) else []
        coord_count = len(coords)
        
        print(f"  {i}. {path.name}")
        print(f"     - 类型: {geom_type}")
        print(f"     - 坐标点数: {coord_count}")
        print(f"     - A端: {path.site_a.name}, Z端: {path.site_z.name}")
    
    # 4. 测试服务加载
    print(f"\n🚀 测试 OtnPathGraphService 服务...")
    try:
        service = get_otn_path_graph_service()
        
        if service.is_available():
            print(f"✅ 服务已成功加载")
            
            # 显示图统计信息
            if service._graph:
                node_count = service._graph.number_of_nodes()
                edge_count = service._graph.number_of_edges()
                print(f"   - 图节点数: {node_count}")
                print(f"   - 图边数: {edge_count}")
        else:
            print(f"⚠️  服务不可用（可能是 NetworkX 未安装或图为空）")
            return False
            
    except Exception as e:
        print(f"❌ 服务加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 地理覆盖范围分析
    print(f"\n🗺️  地理覆盖范围分析...")
    lngs = []
    lats = []
    
    for path in valid_paths:
        coords = path.geometry.get('coordinates', [])
        for coord in coords:
            if len(coord) >= 2:
                lngs.append(coord[0])
                lats.append(coord[1])
    
    if lngs and lats:
        print(f"   - 经度范围: {min(lngs):.4f} ~ {max(lngs):.4f}")
        print(f"   - 纬度范围: {min(lats):.4f} ~ {max(lats):.4f}")
    
    print("\n" + "=" * 60)
    print("✅ 数据验证完成")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = validate_otn_paths()
    sys.exit(0 if success else 1)
