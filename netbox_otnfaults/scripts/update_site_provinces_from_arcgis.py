"""
NetBox自定义脚本：根据站点经纬度更新省份地区信息

功能：
1. 遍历NetBox中的所有站点（Site模型）
2. 对于有经纬度信息的站点，使用ArcGIS省份面图层进行空间查询
3. 查询站点坐标所在的省份
4. 根据省份名称查找或创建地区（Region）对象
5. 更新站点的地区（region）属性

ArcGIS服务：
- http://192.168.70.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0
  这是一个全国省份的面图层，包含PR_NAME字段（省份名称）

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.update_site_provinces_from_arcgis
2. 选择脚本类：UpdateSiteProvincesFromArcGIS
3. 运行脚本
"""

import requests
import json
import time
from decimal import Decimal
from django.db import transaction
from dcim.models import Site, Region
from extras.scripts import Script, BooleanVar, IntegerVar, ChoiceVar


class UpdateSiteProvincesFromArcGIS(Script):
    """
    根据站点经纬度更新省份地区信息的自定义脚本
    """
    
    class Meta:
        name = "根据经纬度更新站点省份"
        description = "使用ArcGIS省份面图层，根据站点经纬度查询并更新站点地区属性"
        commit_default = False
        scheduling_enabled = True
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际更新站点地区（默认：True）",
        default=True
    )
    
    batch_size = IntegerVar(
        label="批量大小",
        description="每次批量处理的站点数量（0表示一次性处理所有站点）",
        default=50,
        min_value=0
    )
    
    max_sites = IntegerVar(
        label="最大处理数量",
        description="最大处理站点数量（0表示无限制）",
        default=0,
        min_value=0
    )
    
    region_creation = ChoiceVar(
        label="地区创建策略",
        description="当省份对应的地区不存在时的处理方式",
        choices=[
            ('skip', '跳过（不创建新地区）'),
            ('create', '创建新地区'),
        ],
        default='skip'
    )
    
    def __init__(self):
        super().__init__()
        # ArcGIS省份面图层服务URL
        self.arcgis_url = "http://192.168.70.216:6080/arcgis/rest/services/OTN/province/FeatureServer/0"
    
    def build_spatial_query_url(self, longitude, latitude):
        """
        构建ArcGIS空间查询URL
        
        参数:
            longitude: 经度（Decimal或float）
            latitude: 纬度（Decimal或float）
            
        返回:
            完整的查询URL
        """
        # 构建几何参数
        geometry = {
            "x": float(longitude),
            "y": float(latitude),
            "spatialReference": {"wkid": 4326}  # WGS84坐标系
        }
        
        # URL编码参数
        params = {
            "geometry": json.dumps(geometry),
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "returnGeometry": "false",
            "outFields": "PR_NAME",
            "f": "json"
        }
        
        # 构建查询URL
        query_url = f"{self.arcgis_url}/query"
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        return f"{query_url}?{param_string}"
    
    def query_province_by_point(self, longitude, latitude):
        """
        根据经纬度查询省份
        
        参数:
            longitude: 经度
            latitude: 纬度
            
        返回:
            (成功与否, 省份名称或错误消息)
        """
        try:
            # 构建查询URL
            query_url = self.build_spatial_query_url(longitude, latitude)
            
            # 发送查询请求
            self.log_debug(f"查询URL: {query_url}")
            response = requests.get(query_url, timeout=30)
            response.raise_for_status()
            
            # 解析响应
            data = response.json()
            
            # 检查是否有错误
            if 'error' in data:
                error_msg = data['error'].get('message', '未知错误')
                return False, f"ArcGIS查询错误: {error_msg}"
            
            # 获取特征
            features = data.get('features', [])
            
            if not features:
                return False, "未找到包含该点的省份"
            
            # 提取省份名称
            # 注意：字段名可能是PR_NAME（大写）或PR_Name
            feature = features[0]
            attributes = feature.get('attributes', {})
            
            # 尝试不同的字段名
            province_name = attributes.get('PR_NAME') or attributes.get('PR_Name')
            
            if not province_name:
                return False, "省份名称字段为空"
            
            return True, province_name.strip()
            
        except requests.exceptions.RequestException as e:
            return False, f"网络请求失败: {str(e)}"
        except json.JSONDecodeError as e:
            return False, f"JSON解析失败: {str(e)}"
        except Exception as e:
            return False, f"查询失败: {str(e)}"
    
    def get_or_create_region(self, province_name, create_if_missing=True):
        """
        根据省份名称获取或创建Region对象
        
        参数:
            province_name: 省份名称
            create_if_missing: 是否创建不存在的地区
            
        返回:
            (Region对象, 是否为新创建, 消息)
        """
        try:
            # 查找地区
            region = Region.objects.filter(name=province_name).first()
            
            if region:
                return region, False, f"找到地区: {province_name}"
            
            # 地区不存在，根据策略处理
            if not create_if_missing:
                return None, False, f"地区不存在且设置为不创建: {province_name}"
            
            # 创建新地区
            # 生成slug（使用省份名称的拼音首字母或简化名称）
            # 这里简单处理，使用名称的前6个字符（去除空格）
            slug_base = province_name.replace(" ", "").replace("省", "").replace("市", "")
            slug = slug_base[:6].lower() if slug_base else "region"
            
            # 确保slug唯一
            original_slug = slug
            counter = 1
            while Region.objects.filter(slug=slug).exists():
                slug = f"{original_slug}{counter}"
                counter += 1
            
            # 创建地区
            region = Region(
                name=province_name,
                slug=slug,
                description=f"从ArcGIS导入的省份: {province_name}",
                parent=None  # 顶级地区
            )
            
            region.full_clean()
            region.save()
            
            return region, True, f"创建新地区: {province_name} (slug: {slug})"
            
        except Exception as e:
            return None, False, f"处理地区失败 {province_name}: {str(e)}"
    
    def update_site_region(self, site, region, dry_run=True):
        """
        更新站点的region字段
        
        参数:
            site: Site对象
            region: Region对象
            dry_run: 是否模拟运行
            
        返回:
            (成功与否, 消息)
        """
        try:
            # 检查是否需要更新
            if site.region == region:
                return True, f"站点地区已为 {region.name}，无需更新"
            
            # 更新站点
            if not dry_run:
                site.region = region
                site.save()
                
                return True, f"更新站点地区为 {region.name}"
            else:
                return True, f"模拟更新站点地区为 {region.name}"
                
        except Exception as e:
            return False, f"更新站点地区失败 {site.name}: {str(e)}"
    
    def validate_coordinates(self, latitude, longitude):
        """
        验证经纬度坐标是否有效
        
        参数:
            latitude: 纬度
            longitude: 经度
            
        返回:
            (是否有效, 错误消息)
        """
        if latitude is None or longitude is None:
            return False, "经纬度为空"
        
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # 中国大致经纬度范围
            if not (3.86 <= lat <= 53.55):  # 中国纬度范围
                return False, f"纬度 {lat} 超出中国范围"
            if not (73.66 <= lng <= 135.05):  # 中国经度范围
                return False, f"经度 {lng} 超出中国范围"
            
            return True, "坐标有效"
            
        except (ValueError, TypeError):
            return False, "经纬度格式无效"
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        batch_size = data['batch_size']
        max_sites = data['max_sites']
        region_creation = data['region_creation']
        
        self.log_info("开始根据经纬度更新站点省份信息")
        self.log_info(f"参数: dry_run={dry_run}, batch_size={batch_size}, "
                     f"max_sites={max_sites}, region_creation={region_creation}")
        
        # 获取所有站点
        all_sites = Site.objects.all().order_by('name')
        total_sites = all_sites.count()
        
        self.log_info(f"NetBox中共有 {total_sites} 个站点")
        
        # 筛选有经纬度的站点
        sites_with_coords = []
        for site in all_sites:
            if site.latitude is not None and site.longitude is not None:
                # 验证坐标
                valid, msg = self.validate_coordinates(site.latitude, site.longitude)
                if valid:
                    sites_with_coords.append(site)
                else:
                    self.log_debug(f"站点 {site.name} 坐标无效: {msg}")
        
        sites_count = len(sites_with_coords)
        self.log_info(f"其中有 {sites_count} 个站点有有效经纬度坐标")
        
        if sites_count == 0:
            return "错误：没有找到有有效经纬度坐标的站点"
        
        # 限制处理数量
        if max_sites > 0:
            sites_to_process = sites_with_coords[:max_sites]
            self.log_info(f"根据最大处理数量限制，将处理 {len(sites_to_process)} 个站点")
        else:
            sites_to_process = sites_with_coords
        
        # 统计信息
        total_to_process = len(sites_to_process)
        processed = 0
        successful = 0
        skipped_no_coords = total_sites - sites_count
        skipped_invalid_coords = sites_count - total_to_process if max_sites > 0 else 0
        skipped_no_province = 0
        skipped_region_creation = 0
        failed = 0
        updated = 0
        already_correct = 0
        
        self.log_info(f"开始处理 {total_to_process} 个站点...")
        
        # 处理每个站点
        for i, site in enumerate(sites_to_process):
            processed += 1
            
            # 进度反馈
            if processed % 10 == 0 or processed == total_to_process:
                self.log_info(f"已处理 {processed}/{total_to_process} 个站点...")
            
            try:
                # 查询省份
                success, result = self.query_province_by_point(
                    site.longitude, 
                    site.latitude
                )
                
                if not success:
                    self.log_warning(f"站点 {site.name} 查询省份失败: {result}")
                    skipped_no_province += 1
                    continue
                
                province_name = result
                self.log_debug(f"站点 {site.name} 位于省份: {province_name}")
                
                # 获取或创建地区
                create_if_missing = (region_creation == 'create')
                region, created, region_msg = self.get_or_create_region(
                    province_name, 
                    create_if_missing
                )
                
                if region is None:
                    self.log_warning(f"站点 {site.name}: {region_msg}")
                    skipped_region_creation += 1
                    continue
                
                if created:
                    self.log_success(f"站点 {site.name}: {region_msg}")
                
                # 更新站点地区
                update_success, update_msg = self.update_site_region(
                    site, 
                    region, 
                    dry_run=(dry_run or not commit)
                )
                
                if update_success:
                    if "无需更新" in update_msg:
                        already_correct += 1
                        self.log_info(f"站点 {site.name}: {update_msg}")
                    else:
                        updated += 1
                        self.log_success(f"站点 {site.name}: {update_msg}")
                    successful += 1
                else:
                    failed += 1
                    self.log_warning(f"站点 {site.name}: {update_msg}")
                
                # 批量提交（如果启用且不是模拟运行）
                if batch_size > 0 and processed % batch_size == 0 and not dry_run and commit:
                    self.log_info(f"提交第 {processed//batch_size} 批更改...")
                    transaction.commit()
                
                # 避免请求过快
                time.sleep(0.1)
                
            except Exception as e:
                failed += 1
                self.log_failure(f"处理站点 {site.name} 时发生异常: {str(e)}")
        
        # 生成结果报告
        result_message = (
            f"处理完成！\n"
            f"• 总站点数: {total_sites} 个\n"
            f"• 有经纬度站点: {sites_count} 个\n"
            f"• 处理站点数: {total_to_process} 个\n"
            f"• 成功处理: {successful} 个\n"
            f"• 失败: {failed} 个\n"
            f"\n"
            f"详细统计:\n"
            f"• 跳过（无坐标）: {skipped_no_coords} 个\n"
            f"• 跳过（无效坐标）: {skipped_invalid_coords} 个\n"
            f"• 跳过（未找到省份）: {skipped_no_province} 个\n"
            f"• 跳过（地区创建策略）: {skipped_region_creation} 个\n"
            f"• 已正确无需更新: {already_correct} 个\n"
            f"• 成功更新: {updated} 个\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，站点地区未实际更新。\n"
            result_message += "如需实际更新，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n站点地区已成功更新。"
        
        return result_message


# 脚本测试函数（可选）
if __name__ == "__main__":
    # 仅用于本地测试
    print("此脚本需要在NetBox环境中运行")
