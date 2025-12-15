from extras.scripts import Script, ObjectVar
from netbox_otnfaults.models import OtnFault
import random
import requests
import json
from requests.exceptions import RequestException

class RandomizeFaultCoordinates(Script):
    class Meta:
        name = "随机化故障坐标 (Randomize Fault Coordinates)"
        description = "将所有故障模型的经纬度坐标设置为随机位于OTN网络线服务上的点。"
        commit_default = True

    def fetch_arcgis_line_segments(self, url):
        """
        从ArcGIS服务获取线几何数据，返回线段列表
        每个线段为 [(lon1, lat1), (lon2, lat2)]
        """
        try:
            self.log_info(f"正在从ArcGIS服务获取数据: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            geojson = response.json()
            
            segments = []
            features = geojson.get('features', [])
            
            if not features:
                self.log_warning(f"从 {url} 获取的数据中没有要素")
                return segments
            
            for feature in features:
                geometry = feature.get('geometry', {})
                geometry_type = geometry.get('type')
                coordinates = geometry.get('coordinates', [])
                
                if geometry_type == 'LineString':
                    # 将连续的线点转换为线段
                    for i in range(len(coordinates) - 1):
                        # ArcGIS GeoJSON使用 [longitude, latitude] 顺序
                        pt1 = coordinates[i]
                        pt2 = coordinates[i + 1]
                        segments.append([pt1, pt2])
                elif geometry_type == 'MultiLineString':
                    for line in coordinates:
                        for i in range(len(line) - 1):
                            pt1 = line[i]
                            pt2 = line[i + 1]
                            segments.append([pt1, pt2])
                else:
                    self.log_debug(f"跳过非线几何类型: {geometry_type}")
            
            self.log_success(f"从 {url} 获取了 {len(segments)} 个线段")
            return segments
            
        except RequestException as e:
            self.log_failure(f"无法从ArcGIS服务获取数据: {e}")
            return []
        except json.JSONDecodeError as e:
            self.log_failure(f"解析ArcGIS响应JSON失败: {e}")
            return []
        except Exception as e:
            self.log_failure(f"获取ArcGIS数据时发生未知错误: {e}")
            return []

    def get_fallback_segments(self):
        """
        备用数据：如果ArcGIS服务不可用，使用硬编码的高速公路坐标点
        返回格式：[[[lon1, lat1], [lon2, lat2]], ...]
        """
        highways = {
            "G15 (沈海高速)": [
                (41.8057, 123.4315), # 沈阳
                (38.9140, 121.6147), # 大连
                (37.4638, 121.4479), # 烟台
                (36.0671, 120.3826), # 青岛
                (35.2975, 119.3368), # 日照
                (34.5967, 119.2214), # 连云港
                (33.3472, 120.1636), # 盐城
                (31.9802, 120.8943), # 南通
                (31.2304, 121.4737), # 上海
                (29.8683, 121.5440), # 宁波
                (28.0053, 120.6994), # 温州
                (26.0745, 119.2965), # 福州
                (24.4798, 118.0894), # 厦门
                (23.3668, 116.6820), # 汕头
                (22.5431, 114.0579), # 深圳
                (23.1291, 113.2644), # 广州
                (21.1965, 110.4045), # 湛江
                (20.0174, 110.3492), # 海口
            ],
            "G2 (京沪高速)": [
                (39.9042, 116.4074), # 北京
                (39.0842, 117.2009), # 天津
                (36.6512, 117.1201), # 济南
                (34.2044, 117.2857), # 徐州
                (32.3946, 119.4124), # 扬州
                (31.2304, 121.4737), # 上海
            ],
            "G4 (京港澳高速)": [
                (39.9042, 116.4074), # 北京
                (38.0423, 114.5149), # 石家庄
                (34.7466, 113.6253), # 郑州
                (30.5928, 114.3055), # 武汉
                (28.2282, 112.9388), # 长沙
                (23.1291, 113.2644), # 广州
                (22.5431, 114.0579), # 深圳
            ],
            "G5 (京昆高速)": [
                (39.9042, 116.4074), # 北京
                (37.8706, 112.5489), # 太原
                (34.3416, 108.9398), # 西安
                (30.6586, 104.0648), # 成都
                (25.0453, 102.7097), # 昆明
            ],
            "G65 (包茂高速)": [
                (40.6575, 109.8404), # 包头
                (38.2856, 109.7303), # 榆林
                (34.3416, 108.9398), # 西安
                (29.5630, 106.5516), # 重庆
                (26.6470, 106.6302), # 贵阳
                (22.8170, 108.3665), # 南宁
                (21.6628, 110.9258), # 茂名
            ],
            "G20 (青银高速)": [
                (36.0671, 120.3826), # 青岛
                (36.6512, 117.1201), # 济南
                (38.0423, 114.5149), # 石家庄
                (37.8706, 112.5489), # 太原
                (38.4872, 106.2309), # 银川
            ],
            "G30 (连霍高速)": [
                (34.5967, 119.2214), # 连云港
                (34.7466, 113.6253), # 郑州
                (34.3416, 108.9398), # 西安
                (36.0611, 103.8343), # 兰州
                (43.8256, 87.6168),  # 乌鲁木齐
                (44.1685, 80.5286),  # 霍尔果斯
            ],
            "G42 (沪蓉高速)": [
                (31.2304, 121.4737), # 上海
                (32.0603, 118.7969), # 南京
                (31.8206, 117.2272), # 合肥
                (30.5928, 114.3055), # 武汉
                (30.6586, 104.0648), # 成都
            ],
            "G60 (沪昆高速)": [
                (31.2304, 121.4737), # 上海
                (30.2741, 120.1551), # 杭州
                (28.6829, 115.8582), # 南昌
                (28.2282, 112.9388), # 长沙
                (26.6470, 106.6302), # 贵阳
                (25.0453, 102.7097), # 昆明
            ],
            "G80 (广昆高速)": [
                (23.1291, 113.2644), # 广州
                (22.8170, 108.3665), # 南宁
                (25.0453, 102.7097), # 昆明
            ]
        }
        
        segments = []
        for highway_name, points in highways.items():
            # 将 (lat, lon) 转换为 [lon, lat] 格式
            points_lonlat = [[lon, lat] for lat, lon in points]
            
            # 生成线段
            for i in range(len(points_lonlat) - 1):
                segments.append([points_lonlat[i], points_lonlat[i + 1]])
        
        self.log_info(f"使用备用数据，共 {len(segments)} 个线段")
        return segments

    def run(self, data, commit):
        # ArcGIS服务URL（GeoJSON格式）
        ARCGIS_URLS = [
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/2/query?where=1%3D1&outFields=*&f=geojson",
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/3/query?where=1%3D1&outFields=*&f=geojson"
        ]
        
        # 1. 获取ArcGIS线段数据
        all_segments = []
        for url in ARCGIS_URLS:
            segments = self.fetch_arcgis_line_segments(url)
            all_segments.extend(segments)
        
        # 2. 如果没有获取到数据，使用回退数据
        if not all_segments:
            self.log_warning("无法从ArcGIS服务获取数据，使用备用坐标点")
            all_segments = self.get_fallback_segments()
        
        if not all_segments:
            self.log_failure("没有可用的线段数据，无法继续")
            return
        
        self.log_info(f"总共获取了 {len(all_segments)} 个线段用于随机化坐标")
        
        # 3. 获取所有故障对象
        faults = OtnFault.objects.all()
        fault_count = faults.count()
        
        self.log_info(f"开始更新 {fault_count} 个故障对象的坐标...")
        
        # 4. 创建热点区域（使故障分布更加不均衡）
        # 定义热点区域：某些线段会被更频繁地选择
        hotspot_multiplier = 5  # 热点区域的线段被选择的概率是普通区域的5倍
        
        # 分析线段的地理分布，识别可能的密集区域
        # 简单实现：根据线段中心点的经纬度划分区域
        segment_centers = []
        for segment in all_segments:
            pt1, pt2 = segment
            center_lon = (pt1[0] + pt2[0]) / 2
            center_lat = (pt1[1] + pt2[1]) / 2
            segment_centers.append((center_lon, center_lat))
        
        # 识别热点区域（例如：东部沿海地区、大城市周边）
        # 定义热点区域边界（经度，纬度）
        hotspot_regions = [
            # 长三角地区
            {"min_lon": 118.0, "max_lon": 122.0, "min_lat": 30.0, "max_lat": 32.5, "weight": 8},
            # 珠三角地区
            {"min_lon": 112.5, "max_lon": 114.5, "min_lat": 22.0, "max_lat": 24.0, "weight": 7},
            # 京津冀地区
            {"min_lon": 115.5, "max_lon": 118.0, "min_lat": 38.5, "max_lat": 40.5, "weight": 6},
            # 成渝地区
            {"min_lon": 103.5, "max_lon": 107.0, "min_lat": 29.0, "max_lat": 31.5, "weight": 5},
        ]
        
        # 为每个线段分配权重
        segment_weights = []
        for i, (center_lon, center_lat) in enumerate(segment_centers):
            weight = 1.0  # 基础权重
            
            # 检查是否在热点区域内
            for region in hotspot_regions:
                if (region["min_lon"] <= center_lon <= region["max_lon"] and
                    region["min_lat"] <= center_lat <= region["max_lat"]):
                    weight = region["weight"]
                    break
            
            segment_weights.append(weight)
        
        # 创建加权选择列表
        weighted_segments = []
        for i, segment in enumerate(all_segments):
            weight = segment_weights[i]
            # 根据权重重复添加线段到选择列表
            for _ in range(int(weight)):
                weighted_segments.append(segment)
        
        self.log_info(f"加权选择列表包含 {len(weighted_segments)} 个条目（原始 {len(all_segments)} 个线段）")
        
        # 5. 更新故障坐标（使用加权选择）
        updated_count = 0
        hotspot_faults = 0
        
        for fault in faults:
            try:
                # 使用加权随机选择线段
                segment = random.choice(weighted_segments)
                pt1, pt2 = segment
                
                # 在线段上进行线性插值
                t = random.random()  # 0 到 1 之间的随机比例
                lon = pt1[0] + (pt2[0] - pt1[0]) * t
                lat = pt1[1] + (pt2[1] - pt1[1]) * t
                
                # 添加微小的随机偏移（模拟真实故障位置）
                # 0.002 度约等于 200米
                lat += random.uniform(-0.002, 0.002)
                lon += random.uniform(-0.002, 0.002)
                
                # 确保坐标在中国境内合理范围
                lat = max(15.0, min(55.0, lat))  # 纬度范围：15°N - 55°N
                lon = max(70.0, min(140.0, lon))  # 经度范围：70°E - 140°E
                
                # 检查是否在热点区域内
                in_hotspot = False
                for region in hotspot_regions:
                    if (region["min_lon"] <= lon <= region["max_lon"] and
                        region["min_lat"] <= lat <= region["max_lat"]):
                        in_hotspot = True
                        hotspot_faults += 1
                        break
                
                # 更新故障坐标
                fault.interruption_latitude = lat
                fault.interruption_longitude = lon
                
                if commit:
                    fault.save()
                
                updated_count += 1
                if updated_count % 10 == 0:
                    self.log_success(f"已更新 {updated_count}/{fault_count} 个故障坐标")
                    
            except Exception as e:
                self.log_failure(f"更新故障 {fault.fault_number} 坐标时出错: {e}")
                continue
        
        self.log_success(f"处理完成。成功更新了 {updated_count}/{fault_count} 个故障对象的坐标")
        
        # 6. 统计信息
        if all_segments and updated_count > 0:
            # 计算平均每个线段分配了多少故障点
            avg_per_segment = updated_count / len(all_segments)
            self.log_info(f"平均每个线段分配了 {avg_per_segment:.2f} 个故障点")
            
            # 热点区域统计
            hotspot_percentage = (hotspot_faults / updated_count * 100) if updated_count > 0 else 0
            self.log_info(f"热点区域故障分布：{hotspot_faults}/{updated_count} ({hotspot_percentage:.1f}%)")
            
            # 显示热点区域详情
            self.log_info("热点区域定义：")
            for i, region in enumerate(hotspot_regions):
                self.log_info(f"  区域{i+1}: 经度[{region['min_lon']:.1f}-{region['max_lon']:.1f}], "
                            f"纬度[{region['min_lat']:.1f}-{region['max_lat']:.1f}], 权重:{region['weight']}")
            
            # 显示一些示例坐标
            if updated_count >= 3:
                sample_faults = faults[:3]
                for i, fault in enumerate(sample_faults):
                    # 检查示例故障是否在热点区域
                    in_hotspot = "热点区域" if any(
                        region["min_lon"] <= fault.interruption_longitude <= region["max_lon"] and
                        region["min_lat"] <= fault.interruption_latitude <= region["max_lat"]
                        for region in hotspot_regions
                    ) else "普通区域"
                    
                    self.log_info(f"示例 {i+1}: 故障 {fault.fault_number} -> "
                                f"({fault.interruption_latitude:.6f}, {fault.interruption_longitude:.6f}) [{in_hotspot}]")
