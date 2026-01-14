"""
筛选 highways.geojson，只保留高速公路（motorway/motorway_link）
删除国道（trunk/trunk_link）
"""
import json
from pathlib import Path

def filter_highways():
    # 文件路径
    input_file = Path(__file__).parent.parent / 'highways.geojson'
    output_file = Path(__file__).parent.parent / 'highways_motorway_only.geojson'
    
    print(f'读取: {input_file}')
    print(f'文件大小: {input_file.stat().st_size / 1024 / 1024:.1f} MB')
    
    # 读取原始文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    original_count = len(data.get('features', []))
    print(f'原始 features 数量: {original_count}')
    
    # 筛选高速公路
    filtered_features = []
    highway_types = {}
    
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        highway_type = props.get('highway', '')
        
        # 统计类型
        highway_types[highway_type] = highway_types.get(highway_type, 0) + 1
        
        # 只保留 motorway 和 motorway_link
        if highway_type in ('motorway', 'motorway_link'):
            filtered_features.append(feature)
    
    # 打印统计
    print('\n道路类型统计:')
    for t, count in sorted(highway_types.items(), key=lambda x: -x[1]):
        print(f'  {t}: {count}')
    
    # 构建输出
    output_data = {
        'type': 'FeatureCollection',
        'name': 'highways_motorway_only',
        'crs': data.get('crs'),
        'features': filtered_features
    }
    
    filtered_count = len(filtered_features)
    print(f'\n筛选后 features 数量: {filtered_count} ({filtered_count/original_count*100:.1f}%)')
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    
    print(f'输出文件: {output_file}')
    print(f'输出大小: {output_file.stat().st_size / 1024 / 1024:.1f} MB')
    
    print('\n完成！请将 highway_graph.py 中的文件路径更新为 highways_motorway_only.geojson')

if __name__ == '__main__':
    filter_highways()
