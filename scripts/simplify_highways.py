"""
简化高速公路网络为单线网络
合并双向车道，减少数据量，提高连通性
"""
import json
from pathlib import Path
from collections import defaultdict
import math

def simplify_highways():
    input_file = Path(__file__).parent.parent / 'highways_motorway_only.geojson'
    output_file = Path(__file__).parent.parent / 'highways_simplified.geojson'
    
    print(f'读取: {input_file}')
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f'原始 features 数量: {len(data["features"])}')
    
    # 使用边缓存去重（基于端点坐标）
    edges = {}
    
    for feature in data['features']:
        if feature['geometry']['type'] != 'LineString':
            continue
        
        coords = feature['geometry']['coordinates']
        if len(coords) < 2:
            continue
        
        # 提取起点和终点（忽略中间点，简化为直线段）
        start = tuple(round(c, 4) for c in coords[0][:2])
        end = tuple(round(c, 4) for c in coords[-1][:2])
        
        # 创建无方向的边键（小端在前）
        edge_key = tuple(sorted([start, end]))
        
        # 如果边已存在，保留较长的版本
        if edge_key in edges:
            existing_coords = edges[edge_key]
            if len(coords) > len(existing_coords):
                edges[edge_key] = coords
        else:
            edges[edge_key] = coords
    
    print(f'去重后边数量: {len(edges)}')
    
    # 进一步简化：合并线段
    # 使用节点度数来识别可合并的线段
    node_degree = defaultdict(int)
    for edge_key in edges:
        node_degree[edge_key[0]] += 1
        node_degree[edge_key[1]] += 1
    
    # 构建简化后的 features
    simplified_features = []
    for edge_key, coords in edges.items():
        feature = {
            'type': 'Feature',
            'properties': {
                'highway': 'motorway'
            },
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            }
        }
        simplified_features.append(feature)
    
    output_data = {
        'type': 'FeatureCollection',
        'name': 'highways_simplified',
        'crs': data.get('crs'),
        'features': simplified_features
    }
    
    print(f'简化后 features 数量: {len(simplified_features)} ({len(simplified_features)/len(data["features"])*100:.1f}%)')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    
    print(f'输出文件: {output_file}')
    print(f'输出大小: {output_file.stat().st_size / 1024 / 1024:.1f} MB')

if __name__ == '__main__':
    simplify_highways()
