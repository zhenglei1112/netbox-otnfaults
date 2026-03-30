"""
NetBox自定义脚本：从ArcGIS FeatureServer导入站点信息

功能：
1. 从两个ArcGIS FeatureServer端点获取点信息
   - http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/0
   - http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/1
2. 提取每个点的O_NAME（站点名称）、O_LAT（纬度）、O_LNG（经度）
3. 在NetBox中查找站点（使用O_NAME）
4. 如果站点不存在，则创建新站点：
   - 名称：O_NAME
   - 缩写：随机生成的缩写（6位字母数字）
   - 状态：在线
   - 经纬度：使用O_LAT, O_LNG

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.import_sites_from_arcgis_simple
2. 选择脚本类：ImportSitesFromArcGIS
3. 运行脚本
"""

import math
import requests
import json
import random
import string
from decimal import Decimal
from django.contrib.auth import get_user_model
from dcim.models import Site
from dcim.choices import SiteStatusChoices
from extras.scripts import Script, BooleanVar, IntegerVar

# 空间去重距离阈值（米）
DISTANCE_THRESHOLD_METERS = 100


class ImportSitesFromArcGIS(Script):
    """
    从ArcGIS FeatureServer导入站点信息的自定义脚本
    """
    
    class Meta:
        name = "从ArcGIS导入站点信息"
        description = "从ArcGIS FeatureServer导入站点信息到NetBox"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际创建站点（默认：True）",
        default=True
    )
    
    max_sites = IntegerVar(
        label="最大导入数量",
        description="最大导入站点数量（0表示无限制）",
        default=0,
        min_value=0
    )
    
    def __init__(self):
        super().__init__()
        # ArcGIS端点URL
        self.endpoints = [
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/0/query?where=1%3D1&outFields=O_NAME,O_LAT,O_LNG&returnGeometry=true&f=json",
            "http://192.168.30.216:6080/arcgis/rest/services/OTN/OTN/FeatureServer/1/query?where=1%3D1&outFields=O_NAME,O_LAT,O_LNG&returnGeometry=true&f=json"
        ]
    
    def generate_random_slug(self, length=6):
        """
        生成随机缩写
        
        参数:
            length: 缩写长度
            
        返回:
            随机生成的缩写字符串
        """
        # 使用字母和数字生成随机字符串
        characters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        使用Haversine公式计算两个经纬度坐标之间的距离（米）
        
        参数:
            lat1, lon1: 第一个点的纬度和经度
            lat2, lon2: 第二个点的纬度和经度
            
        返回:
            两点之间的距离（米）
        """
        R = 6371000  # 地球平均半径（米）
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2
             + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def find_nearby_site(self, latitude: Decimal, longitude: Decimal,
                         existing_sites: list[dict]) -> dict | None:
        """
        在已有站点列表中查找距离阈值内的站点
        
        参数:
            latitude: 待检查点的纬度
            longitude: 待检查点的经度
            existing_sites: 已有站点列表，每项含 name/latitude/longitude
            
        返回:
            距离最近且在阈值内的站点字典，不存在则返回 None
        """
        if latitude is None or longitude is None:
            return None
        
        lat1 = float(latitude)
        lon1 = float(longitude)
        closest_site = None
        closest_distance = float('inf')
        
        for site in existing_sites:
            dist = self.haversine_distance(lat1, lon1, site['latitude'], site['longitude'])
            if dist < closest_distance:
                closest_distance = dist
                closest_site = site
        
        if closest_site and closest_distance <= DISTANCE_THRESHOLD_METERS:
            closest_site = {**closest_site, 'distance': closest_distance}
            return closest_site
        
        return None
    
    def load_existing_sites_with_coords(self) -> list[dict]:
        """
        预加载所有含经纬度的已有站点
        
        返回:
            站点字典列表，每项含 name/latitude/longitude
        """
        sites = Site.objects.exclude(
            latitude__isnull=True
        ).exclude(
            longitude__isnull=True
        ).values_list('name', 'latitude', 'longitude')
        
        return [
            {'name': name, 'latitude': float(lat), 'longitude': float(lng)}
            for name, lat, lng in sites
        ]
    
    def fetch_arcgis_data(self, endpoint_url):
        """
        从ArcGIS端点获取数据
        
        参数:
            endpoint_url: ArcGIS端点URL
            
        返回:
            特征列表，每个特征包含attributes和geometry
        """
        try:
            self.log_info(f"正在从ArcGIS端点获取数据: {endpoint_url}")
            response = requests.get(endpoint_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            self.log_success(f"成功获取 {len(features)} 个特征")
            return features
            
        except requests.exceptions.RequestException as e:
            self.log_failure(f"获取ArcGIS数据失败: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            self.log_failure(f"解析JSON数据失败: {str(e)}")
            return []
    
    def extract_site_info(self, feature):
        """
        从ArcGIS特征中提取站点信息
        
        参数:
            feature: ArcGIS特征
            
        返回:
            站点信息字典，包含name, latitude, longitude
        """
        attributes = feature.get('attributes', {})
        geometry = feature.get('geometry', {})
        
        name = attributes.get('O_NAME', '').strip()
        latitude = attributes.get('O_LAT')
        longitude = attributes.get('O_LNG')
        
        # 如果attributes中没有经纬度，尝试从geometry中获取
        if latitude is None or longitude is None:
            if 'x' in geometry and 'y' in geometry:
                # ArcGIS geometry通常是Web Mercator投影，需要转换为WGS84
                # 这里简单处理，直接使用x,y作为经纬度（实际可能需要转换）
                longitude = geometry.get('x')
                latitude = geometry.get('y')
        
        # 验证数据
        if not name:
            return None
        
        # 确保经纬度是Decimal类型
        try:
            if latitude is not None:
                latitude = Decimal(str(latitude))
            if longitude is not None:
                longitude = Decimal(str(longitude))
        except (ValueError, TypeError):
            latitude = None
            longitude = None
        
        return {
            'name': name,
            'latitude': latitude,
            'longitude': longitude
        }
    
    def site_exists(self, site_name):
        """
        检查站点是否已存在
        
        参数:
            site_name: 站点名称
            
        返回:
            如果站点存在返回True，否则返回False
        """
        return Site.objects.filter(name=site_name).exists()
    
    def create_site(self, site_info, dry_run=True):
        """
        创建站点
        
        参数:
            site_info: 站点信息字典
            dry_run: 是否模拟运行
            
        返回:
            (成功与否, 消息)
        """
        original_name = site_info['name']
        latitude = site_info['latitude']
        longitude = site_info['longitude']
        
        # 处理名称冲突：不以名称查重，遇到重名自动添加后缀以满足唯一性
        name = original_name
        counter = 1
        while Site.objects.filter(name=name).exists():
            name = f"{original_name}-{counter}"
            counter += 1
            
        # 生成随机缩写
        slug = self.generate_random_slug()
        
        # 创建站点对象
        site_data = {
            'name': name,
            'slug': slug,
            'status': SiteStatusChoices.STATUS_ACTIVE,  # 在线状态
        }
        
        # 添加经纬度（如果可用），并限制精度
        if latitude is not None:
            # 限制纬度精度：最多6位小数，确保总位数不超过8位
            try:
                # 转换为字符串并限制小数位数
                lat_str = str(latitude)
                if '.' in lat_str:
                    integer_part, decimal_part = lat_str.split('.')
                    # 限制小数部分为6位
                    decimal_part = decimal_part[:6]
                    # 重新组合并转换为Decimal
                    latitude = Decimal(f"{integer_part}.{decimal_part}")
                site_data['latitude'] = latitude
            except (ValueError, TypeError, AttributeError) as e:
                self.log_warning(f"处理纬度数据失败 {name}: {e}")
                latitude = None
        
        if longitude is not None:
            # 限制经度精度：最多6位小数，确保总位数不超过9位
            try:
                # 转换为字符串并限制小数位数
                lng_str = str(longitude)
                if '.' in lng_str:
                    integer_part, decimal_part = lng_str.split('.')
                    # 限制小数部分为6位
                    decimal_part = decimal_part[:6]
                    # 重新组合并转换为Decimal
                    longitude = Decimal(f"{integer_part}.{decimal_part}")
                site_data['longitude'] = longitude
            except (ValueError, TypeError, AttributeError) as e:
                self.log_warning(f"处理经度数据失败 {name}: {e}")
                longitude = None
        
        try:
            if not dry_run:
                # 实际创建站点
                site = Site(**site_data)
                site.full_clean()  # 验证数据
                site.save()
                
                # 添加经纬度信息
                message = f"创建站点: {name} (缩写: {slug})"
                if latitude is not None and longitude is not None:
                    message += f" 坐标: {latitude}, {longitude}"
                return True, message
            else:
                # 模拟运行
                message = f"模拟创建站点: {name} (缩写: {slug})"
                if latitude is not None and longitude is not None:
                    message += f" 坐标: {latitude}, {longitude}"
                return True, message
                
        except Exception as e:
            error_msg = f"创建站点 {name} 失败: {str(e)}"
            return False, error_msg
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        max_sites = data['max_sites']
        
        self.log_info("开始从ArcGIS导入站点信息")
        
        # 预加载已有站点坐标（用于空间去重）
        existing_sites_with_coords = self.load_existing_sites_with_coords()
        self.log_info(f"已加载 {len(existing_sites_with_coords)} 个含坐标的已有站点（用于空间去重，阈值={DISTANCE_THRESHOLD_METERS}米）")
        
        # 收集所有站点信息
        all_sites_info = []
        
        # 从两个端点获取数据
        for endpoint in self.endpoints:
            features = self.fetch_arcgis_data(endpoint)
            
            for feature in features:
                site_info = self.extract_site_info(feature)
                if site_info:
                    all_sites_info.append(site_info)
        
        if not all_sites_info:
            return "错误：未从ArcGIS获取到任何站点信息"
        
        self.log_info(f"从ArcGIS共获取 {len(all_sites_info)} 个站点信息")
        
        # 记录名称重复明细，但不再按名称去重（因为仅以位置查重）
        name_count = {}  # 每个名称出现的次数
        for site_info in all_sites_info:
            name = site_info['name']
            name_count[name] = name_count.get(name, 0) + 1
        
        # 筛选出出现多次的名称
        duplicate_name_details = {
            name: count for name, count in name_count.items() if count > 1
        }
        
        self.log_info(f"数据源同名情况: 有 {len(duplicate_name_details)} 个名称存在重复。将保留全部进入位置查重。")
        if duplicate_name_details:
            for name, count in duplicate_name_details.items():
                self.log_info(f"  数据源重复: '{name}' 出现 {count} 次")
        
        # 限制导入数量
        if max_sites > 0:
            sites_to_process = all_sites_info[:max_sites]
            self.log_info(f"根据最大导入数量限制，将处理 {len(sites_to_process)} 个站点")
        else:
            sites_to_process = all_sites_info
        
        # 统计信息
        total_sites = len(sites_to_process)
        nearby_sites = 0
        created_sites = 0
        failed_sites = 0
        
        # 详细记录列表
        nearby_site_details = []     # 位置相近明细
        
        self.log_info(f"开始处理 {total_sites} 个站点...")
        
        # 处理每个站点
        for i, site_info in enumerate(sites_to_process):
            name = site_info['name']
            
            # 进度反馈
            if (i + 1) % 10 == 0:
                self.log_info(f"已处理 {i + 1}/{total_sites} 个站点...")
                        # 检查是否有位置相近的已有站点（空间去重）
            nearby = self.find_nearby_site(
                site_info['latitude'], site_info['longitude'],
                existing_sites_with_coords
            )
            if nearby:
                detail_msg = (
                    f"{name} ↔ {nearby['name']} "
                    f"(距离 {nearby['distance']:.1f}m)"
                )
                self.log_warning(
                    f"跳过站点: {name} — 与已有站点 '{nearby['name']}' "
                    f"距离仅 {nearby['distance']:.1f} 米（阈值 {DISTANCE_THRESHOLD_METERS} 米）"
                )
                nearby_sites += 1
                nearby_site_details.append(detail_msg)
                continue
            
            # 创建站点
            success, message = self.create_site(site_info, dry_run=(dry_run or not commit))
            
            # 新建成功后将站点加入空间去重列表，避免本批次内重复
            if success and site_info['latitude'] is not None and site_info['longitude'] is not None:
                existing_sites_with_coords.append({
                    'name': name,
                    'latitude': float(site_info['latitude']),
                    'longitude': float(site_info['longitude']),
                })
            
            if success:
                self.log_success(message)
                created_sites += 1
            else:
                self.log_warning(message)
                failed_sites += 1
        
        # 生成结果报告
        result_message = (
            f"导入完成！\n"
            f"• 从ArcGIS获取站点（处理总数）: {total_sites} 个\n"
            f"• 数据源同名重复: {len(duplicate_name_details)} 个名称\n"
            f"• 跳过站点（位置相近）: {nearby_sites} 个\n"
            f"• 成功创建站点: {created_sites} 个\n"
            f"• 创建失败站点: {failed_sites} 个\n"
        )
        
        # 附加数据源同名重复明细
        if duplicate_name_details:
            result_message += f"\n{'='*50}\n"
            result_message += f"数据源同名重复明细（只按位置去重，同名将被保留并自动加后缀）:\n"
            for idx, (name, count) in enumerate(
                sorted(duplicate_name_details.items(), key=lambda x: x[1], reverse=True), 1
            ):
                result_message += f"  {idx}. {name} （出现 {count} 次）\n"
        
        # 附加位置相近站点明细
        if nearby_site_details:
            result_message += f"\n{'='*50}\n"
            result_message += f"位置相近跳过站点明细（共 {len(nearby_site_details)} 个，阈值 {DISTANCE_THRESHOLD_METERS}m）:\n"
            for idx, detail in enumerate(nearby_site_details, 1):
                result_message += f"  {idx}. {detail}\n"
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，站点未实际创建。\n"
            result_message += "如需实际创建站点，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n站点已成功创建到NetBox数据库。"
        
        return result_message
