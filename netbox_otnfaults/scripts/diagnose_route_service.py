#!/usr/bin/env python
"""
诊断路径计算服务问题
检查所有可能导致服务不可用的原因
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()


def check_networkx():
    """检查 NetworkX 是否安装"""
    print("\n" + "="*60)
    print("1. 检查 NetworkX 依赖")
    print("="*60)
    
    try:
        import networkx as nx
        print(f"✅ NetworkX 已安装")
        print(f"   版本: {nx.__version__}")
        return True
    except ImportError:
        print(f"❌ NetworkX 未安装")
        print(f"   请运行: pip install networkx")
        return False


def check_otn_path_data():
    """检查 OtnPath 数据"""
    print("\n" + "="*60)
    print("2. 检查 OtnPath 数据")
    print("="*60)
    
    from netbox_otnfaults.models import OtnPath
    
    total = OtnPath.objects.count()
    valid = OtnPath.objects.exclude(geometry__isnull=True).exclude(geometry={}).count()
    
    print(f"   总路径数: {total}")
    print(f"   有效路径数（含 geometry）: {valid}")
    
    if valid == 0:
        print(f"\n❌ 没有有效路径数据！")
        print(f"   请运行: python manage.py runscript import_otn_paths")
        print(f"   或手动创建测试数据")
        return False
    elif valid < 10:
        print(f"\n⚠️  路径数据较少，可能影响路径计算覆盖范围")
    else:
        print(f"\n✅ 路径数据充足")
    
    # 显示前3条路径
    print(f"\n   前 3 条路径：")
    for i, path in enumerate(OtnPath.objects.exclude(geometry__isnull=True)[:3], 1):
        geom = path.geometry
        coords = geom.get('coordinates', []) if isinstance(geom, dict) else []
        print(f"   {i}. {path.name} - {len(coords)} 个坐标点")
    
    return True


def check_service_initialization():
    """检查服务初始化"""
    print("\n" + "="*60)
    print("3. 检查服务初始化")
    print("="*60)
    
    try:
        from netbox_otnfaults.services.otn_path_graph import get_otn_path_graph_service
        
        print("   正在初始化服务...")
        service = get_otn_path_graph_service()
        
        if service.is_available():
            print(f"✅ 服务初始化成功")
            
            if service._graph:
                nodes = service._graph.number_of_nodes()
                edges = service._graph.number_of_edges()
                print(f"   - 图节点数: {nodes}")
                print(f"   - 图边数: {edges}")
                
                if nodes == 0:
                    print(f"\n⚠️  图为空，请检查路径数据格式")
                    return False
            
            return True
        else:
            print(f"❌ 服务不可用")
            print(f"   可能原因：")
            print(f"   1. NetworkX 未安装")
            print(f"   2. 路径数据为空")
            print(f"   3. 图构建失败（查看控制台错误日志）")
            return False
            
    except Exception as e:
        print(f"❌ 服务初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_route_calculation():
    """测试路径计算"""
    print("\n" + "="*60)
    print("4. 测试路径计算功能")
    print("="*60)
    
    try:
        from netbox_otnfaults.services.otn_path_graph import get_otn_path_graph_service
        
        service = get_otn_path_graph_service()
        
        if not service.is_available():
            print("⏭️  跳过测试（服务不可用）")
            return False
        
        # 测试两个随机点
        waypoints = [
            {'lng': 116.4074, 'lat': 39.9042},  # 北京
            {'lng': 121.4737, 'lat': 31.2304}   # 上海
        ]
        
        print(f"   测试计算路径: 北京 -> 上海")
        result = service.calculate_route(waypoints)
        
        if result['success']:
            if result.get('fallback'):
                print(f"⚠️  使用降级方案（直线连接）")
                print(f"   原因: {result.get('message', '未知')}")
                return False
            else:
                print(f"✅ 路径计算成功")
                length = result['route']['length_meters']
                print(f"   - 路径长度: {length/1000:.2f} 公里")
                coords = result['route']['geometry']['coordinates']
                print(f"   - 路径节点数: {len(coords)}")
                return True
        else:
            print(f"❌ 路径计算失败")
            print(f"   错误: {result.get('error', '未知')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主诊断流程"""
    print("\n" + "="*60)
    print("路径计算服务诊断工具")
    print("="*60)
    
    results = {
        'networkx': check_networkx(),
        'data': check_otn_path_data(),
        'service': check_service_initialization(),
        'calculation': test_route_calculation()
    }
    
    print("\n" + "="*60)
    print("诊断结果汇总")
    print("="*60)
    
    print(f"   NetworkX 依赖: {'✅ 通过' if results['networkx'] else '❌ 失败'}")
    print(f"   OtnPath 数据: {'✅ 通过' if results['data'] else '❌ 失败'}")
    print(f"   服务初始化: {'✅ 通过' if results['service'] else '❌ 失败'}")
    print(f"   路径计算: {'✅ 通过' if results['calculation'] else '❌ 失败'}")
    
    if all(results.values()):
        print(f"\n🎉 所有检查通过！服务运行正常")
        print(f"\n如果前端仍显示错误，请：")
        print(f"   1. 重启 NetBox 服务")
        print(f"   2. 清除浏览器缓存")
        print(f"   3. 检查浏览器控制台的详细错误信息")
    else:
        print(f"\n⚠️  发现问题，请根据上述提示修复")
        print(f"\n详细排查指南请查看: troubleshooting.md")
    
    print("="*60 + "\n")
    
    return all(results.values())


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
