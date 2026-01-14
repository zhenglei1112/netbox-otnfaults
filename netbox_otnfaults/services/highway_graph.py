"""
高速公路图服务
加载 highways.geojson，构建 NetworkX 图用于路径计算
"""
import json
import os
import math
from functools import lru_cache
from pathlib import Path

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None


class HighwayGraphService:
    """高速公路图服务 - 单例模式"""
    
    _instance = None
    _graph = None
    _node_index = None  # 空间索引：用于快速查找最近节点
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._graph is None:
            self._load_graph()
    
    def _load_graph(self):
        """加载高速公路数据并构建图"""
        if not HAS_NETWORKX:
            print('[HighwayGraphService] NetworkX 未安装，路径计算不可用')
            return
        
        # 查找简化后的高速公路数据文件（优先）
        base_dir = Path(__file__).resolve().parent.parent.parent
        geojson_path = base_dir / 'highways_simplified.geojson'
        
        # 回退到其他文件
        if not geojson_path.exists():
            geojson_path = base_dir / 'highways_motorway_only.geojson'
        if not geojson_path.exists():
            geojson_path = base_dir / 'highways.geojson'
        
        if not geojson_path.exists():
            print(f'[HighwayGraphService] 未找到 {geojson_path}')
            return
        
        print(f'[HighwayGraphService] 正在加载 {geojson_path}...')
        
        # 构建图
        self._graph = nx.Graph()
        self._node_index = {}
        
        # 读取 GeoJSON
        edge_count = 0
        
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            highway_type = props.get('highway', 'motorway')
            
            geom = feature.get('geometry', {})
            if geom.get('type') != 'LineString':
                continue
            
            coords = geom.get('coordinates', [])
            if len(coords) < 2:
                continue
            
            # 将线段拆分为边
            for i in range(len(coords) - 1):
                coord1 = tuple(coords[i][:2])  # [lng, lat]
                coord2 = tuple(coords[i + 1][:2])
                
                # 添加节点
                node1 = self._get_or_create_node(coord1)
                node2 = self._get_or_create_node(coord2)
                
                # 计算边长度
                length = self._haversine(coord1, coord2)
                
                # 添加边
                self._graph.add_edge(node1, node2, weight=length, highway=highway_type)
                edge_count += 1
        
        node_count = self._graph.number_of_nodes()
        print(f'[HighwayGraphService] 图构建完成: {node_count} 节点, {edge_count} 边')
    
    def _get_or_create_node(self, coord):
        """获取或创建节点，使用坐标精度截断避免重复"""
        # 将坐标截断到 5 位小数（约 1 米精度）
        key = (round(coord[0], 5), round(coord[1], 5))
        
        if key not in self._node_index:
            self._node_index[key] = key
            self._graph.add_node(key, lng=key[0], lat=key[1])
        
        return key
    
    def _haversine(self, coord1, coord2):
        """计算两点间距离（米）"""
        R = 6371000
        lat1, lat2 = math.radians(coord1[1]), math.radians(coord2[1])
        dlat = math.radians(coord2[1] - coord1[1])
        dlng = math.radians(coord2[0] - coord1[0])
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def find_nearest_node(self, lng, lat, max_distance=50000):
        """查找最近的图节点（暴力搜索，后续可优化为 R-tree）"""
        if not self._graph:
            return None
        
        target = (lng, lat)
        min_dist = float('inf')
        nearest = None
        
        for node in self._graph.nodes():
            dist = self._haversine(target, node)
            if dist < min_dist and dist <= max_distance:
                min_dist = dist
                nearest = node
        
        return nearest
    
    def calculate_route(self, waypoints):
        """
        计算经过所有途经点的最短路径
        
        Args:
            waypoints: [{'lng': float, 'lat': float}, ...]
            
        Returns:
            {
                'success': bool,
                'route': {
                    'geometry': GeoJSON LineString,
                    'length_meters': float
                },
                'error': str (if failed)
            }
        """
        if not HAS_NETWORKX:
            return {'success': False, 'error': 'NetworkX 未安装'}
        
        if not self._graph or self._graph.number_of_nodes() == 0:
            return {'success': False, 'error': '高速公路图未加载'}
        
        if len(waypoints) < 2:
            return {'success': False, 'error': '至少需要两个途经点'}
        
        # 将途经点映射到图节点（增大搜索范围到 100km）
        route_nodes = []
        for wp in waypoints:
            node = self.find_nearest_node(wp['lng'], wp['lat'], max_distance=100000)
            if node is None:
                # 找不到最近节点，返回直线
                print(f'[HighwayGraphService] 途经点 ({wp["lng"]}, {wp["lat"]}) 附近没有高速公路，使用直线')
                return self._fallback_straight_line(waypoints)
            route_nodes.append(node)
        
        # 计算分段最短路径
        full_path = [route_nodes[0]]
        total_length = 0
        
        for i in range(len(route_nodes) - 1):
            try:
                path = nx.shortest_path(self._graph, route_nodes[i], route_nodes[i+1], weight='weight')
                # 跳过第一个节点（已在上一段末尾）
                full_path.extend(path[1:])
                
                # 累加长度
                for j in range(len(path) - 1):
                    edge_data = self._graph.get_edge_data(path[j], path[j+1])
                    total_length += edge_data.get('weight', 0)
                    
            except nx.NetworkXNoPath:
                # 无可达路径，返回直线
                print(f'[HighwayGraphService] 节点 {i} 到 {i+1} 之间无可达路径，使用直线')
                return self._fallback_straight_line(waypoints)
        
        # 构建 GeoJSON 几何
        coordinates = [[node[0], node[1]] for node in full_path]
        
        return {
            'success': True,
            'route': {
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinates
                },
                'length_meters': total_length
            }
        }
    
    def _fallback_straight_line(self, waypoints):
        """返回直线连接作为降级方案"""
        coordinates = [[wp['lng'], wp['lat']] for wp in waypoints]
        
        # 计算直线距离
        total_length = 0
        for i in range(len(waypoints) - 1):
            coord1 = (waypoints[i]['lng'], waypoints[i]['lat'])
            coord2 = (waypoints[i+1]['lng'], waypoints[i+1]['lat'])
            total_length += self._haversine(coord1, coord2)
        
        return {
            'success': True,
            'route': {
                'geometry': {
                    'type': 'LineString',
                    'coordinates': coordinates
                },
                'length_meters': total_length
            },
            'fallback': True,
            'message': '使用直线连接'
        }
    
    def is_available(self):
        """检查服务是否可用"""
        return HAS_NETWORKX and self._graph is not None and self._graph.number_of_nodes() > 0


# 全局单例
_highway_graph_service = None

def get_highway_graph_service():
    """获取高速公路图服务单例"""
    global _highway_graph_service
    if _highway_graph_service is None:
        _highway_graph_service = HighwayGraphService()
    return _highway_graph_service
