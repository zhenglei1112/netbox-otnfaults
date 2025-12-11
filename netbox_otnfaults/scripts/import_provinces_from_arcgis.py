"""
NetBox自定义脚本：从ArcGIS FeatureServer导入省份信息到地区模型

功能：
1. 从ArcGIS FeatureServer获取全国省份数据
   - http://192.168.70.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0
2. 提取每个省份的PR_Name（省份名称）
3. 在NetBox中查找地区（使用名称）
4. 如果地区不存在，则创建新地区：
   - 名称：PR_Name
   - 父级：无（顶级地区）
   - 缩写：随机生成的缩写（6位字母数字）
   - 描述：从ArcGIS导入的省份数据

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.import_provinces_from_arcgis
2. 选择脚本类：ImportProvincesFromArcGIS
3. 运行脚本
"""

import requests
import json
import random
import string
from decimal import Decimal
from django.contrib.auth import get_user_model
from dcim.models import Region
from extras.scripts import Script, BooleanVar, IntegerVar


class ImportProvincesFromArcGIS(Script):
    """
    从ArcGIS FeatureServer导入省份信息到NetBox地区模型的自定义脚本
    """
    
    class Meta:
        name = "从ArcGIS导入省份信息"
        description = "从ArcGIS FeatureServer导入全国省份信息到NetBox地区模型"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际创建地区（默认：True）",
        default=True
    )
    
    max_provinces = IntegerVar(
        label="最大导入数量",
        description="最大导入省份数量（0表示无限制）",
        default=0,
        min_value=0
    )
    
    def __init__(self):
        super().__init__()
        # ArcGIS端点URL - 全国省份图
        self.endpoint = "http://192.168.70.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0/query?where=1%3D1&outFields=PR_Name&returnGeometry=false&f=json"
    
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
    
    def fetch_arcgis_data(self, endpoint_url):
        """
        从ArcGIS端点获取数据
        
        参数:
            endpoint_url: ArcGIS端点URL
            
        返回:
            特征列表，每个特征包含attributes
        """
        try:
            self.log_info(f"正在从ArcGIS端点获取数据: {endpoint_url}")
            response = requests.get(endpoint_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            self.log_success(f"成功获取 {len(features)} 个省份特征")
            return features
            
        except requests.exceptions.RequestException as e:
            self.log_failure(f"获取ArcGIS数据失败: {str(e)}")
            return []
        except json.JSONDecodeError as e:
            self.log_failure(f"解析JSON数据失败: {str(e)}")
            return []
    
    def extract_province_info(self, feature):
        """
        从ArcGIS特征中提取省份信息
        
        参数:
            feature: ArcGIS特征
            
        返回:
            省份信息字典，包含name
        """
        attributes = feature.get('attributes', {})
        
        # 注意：字段名是 PR_NAME（大写），不是 PR_Name
        name = attributes.get('PR_NAME', '').strip()
        
        # 验证数据
        if not name:
            return None
        
        return {
            'name': name
        }
    
    def region_exists(self, region_name):
        """
        检查地区是否已存在
        
        参数:
            region_name: 地区名称
            
        返回:
            如果地区存在返回True，否则返回False
        """
        return Region.objects.filter(name=region_name).exists()
    
    def create_region(self, province_info, dry_run=True):
        """
        创建地区
        
        参数:
            province_info: 省份信息字典
            dry_run: 是否模拟运行
            
        返回:
            (成功与否, 消息)
        """
        name = province_info['name']
        
        # 生成随机缩写
        slug = self.generate_random_slug()
        
        # 创建地区对象
        region_data = {
            'name': name,
            'slug': slug,
            'description': f"从ArcGIS导入的省份数据: {name}",
            'parent': None  # 顶级地区，没有父级
        }
        
        try:
            if not dry_run:
                # 实际创建地区
                region = Region(**region_data)
                region.full_clean()  # 验证数据
                region.save()
                
                message = f"创建地区: {name} (缩写: {slug})"
                return True, message
            else:
                # 模拟运行
                message = f"模拟创建地区: {name} (缩写: {slug})"
                return True, message
                
        except Exception as e:
            error_msg = f"创建地区 {name} 失败: {str(e)}"
            return False, error_msg
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        max_provinces = data['max_provinces']
        
        self.log_info("开始从ArcGIS导入省份信息到地区模型")
        
        # 从ArcGIS端点获取数据
        features = self.fetch_arcgis_data(self.endpoint)
        
        if not features:
            return "错误：未从ArcGIS获取到任何省份信息"
        
        self.log_info(f"从ArcGIS共获取 {len(features)} 个省份特征")
        
        # 提取省份信息
        all_provinces_info = []
        for feature in features:
            province_info = self.extract_province_info(feature)
            if province_info:
                all_provinces_info.append(province_info)
        
        if not all_provinces_info:
            return "错误：未能从ArcGIS特征中提取到有效的省份信息"
        
        self.log_info(f"成功提取 {len(all_provinces_info)} 个省份信息")
        
        # 去重（按名称）
        unique_provinces = {}
        for province_info in all_provinces_info:
            name = province_info['name']
            if name not in unique_provinces:
                unique_provinces[name] = province_info
        
        self.log_info(f"去重后剩余 {len(unique_provinces)} 个唯一省份")
        
        # 限制导入数量
        if max_provinces > 0:
            provinces_to_process = list(unique_provinces.values())[:max_provinces]
            self.log_info(f"根据最大导入数量限制，将处理 {len(provinces_to_process)} 个省份")
        else:
            provinces_to_process = list(unique_provinces.values())
        
        # 统计信息
        total_provinces = len(provinces_to_process)
        existing_regions = 0
        created_regions = 0
        failed_regions = 0
        
        self.log_info(f"开始处理 {total_provinces} 个省份...")
        
        # 处理每个省份
        for i, province_info in enumerate(provinces_to_process):
            name = province_info['name']
            
            # 进度反馈
            if (i + 1) % 5 == 0:
                self.log_info(f"已处理 {i + 1}/{total_provinces} 个省份...")
            
            # 检查地区是否已存在
            if self.region_exists(name):
                self.log_success(f"地区已存在: {name}")
                existing_regions += 1
                continue
            
            # 创建地区
            success, message = self.create_region(province_info, dry_run=(dry_run or not commit))
            
            if success:
                self.log_success(message)
                created_regions += 1
            else:
                self.log_warning(message)
                failed_regions += 1
        
        # 生成结果报告
        result_message = (
            f"导入完成！\n"
            f"• 从ArcGIS获取省份: {len(all_provinces_info)} 个\n"
            f"• 去重后唯一省份: {len(unique_provinces)} 个\n"
            f"• 处理省份总数: {total_provinces} 个\n"
            f"• 已存在地区: {existing_regions} 个\n"
            f"• 成功创建地区: {created_regions} 个\n"
            f"• 创建失败地区: {failed_regions} 个\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，地区未实际创建。\n"
            result_message += "如需实际创建地区，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n地区已成功创建到NetBox数据库。"
        
        return result_message
