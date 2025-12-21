"""
NetBox自定义脚本：根据故障坐标和路径几何数据修正故障站点

功能：
1. 检查故障对象的 A 端站点、Z 端站点是否都有值
2. 如果 AZ 端点在路径对象中找不到对应对象（需要检查 AZ 和 ZA 两个方向）
3. 则根据故障的经纬度坐标查找路径对象中的空间几何数据字段
4. 若故障点落在某条路径上，将故障的 AZ 端站点设置为路径的 AZ 端站点
5. 如果存在多条匹配路径，将相同站点设为故障的 A 端，不同的站点设为故障的 Z 端

使用方式：
在 NetBox 的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.fix_fault_sites_by_path
2. 选择脚本类：FixFaultSitesByPath
3. 运行脚本
"""

import math
from decimal import Decimal
from dcim.models import Site
from extras.scripts import Script, BooleanVar, IntegerVar
from netbox_otnfaults.models import OtnFault, OtnPath


class FixFaultSitesByPath(Script):
    """
    根据故障坐标和路径几何数据修正故障站点的自定义脚本
    """
    
    class Meta:
        name = "根据路径修正故障站点"
        description = "检查故障的AZ端站点是否在路径对象中存在，若不存在则根据故障坐标匹配路径并修正站点"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际修改数据库（默认：True）",
        default=True
    )
    
    distance_threshold = IntegerVar(
        label="距离阈值（米）",
        description="判断故障点是否落在路径上的距离阈值，单位：米（默认：500）",
        default=500,
        min_value=50,
        max_value=5000
    )
    
    verbose = BooleanVar(
        label="详细日志",
        description="输出详细日志信息，用于调试（默认：False）",
        default=False
    )
    
    def __init__(self):
        super().__init__()
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        使用 Haversine 公式计算两个经纬度坐标之间的距离（单位：米）
        
        参数:
            lat1, lon1: 第一个点的纬度和经度
            lat2, lon2: 第二个点的纬度和经度
            
        返回:
            两点之间的距离（米）
        """
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
        
        # 地球半径（米）
        R = 6371000.0
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def point_to_segment_distance(self, point_lat, point_lon, seg_lat1, seg_lon1, seg_lat2, seg_lon2):
        """
        计算点到线段的最短距离（米）
        
        使用投影法计算点到线段的垂直距离，如果投影点不在线段上，则返回到端点的最短距离
        
        参数:
            point_lat, point_lon: 点的纬度和经度
            seg_lat1, seg_lon1: 线段起点的纬度和经度
            seg_lat2, seg_lon2: 线段终点的纬度和经度
            
        返回:
            点到线段的最短距离（米）
        """
        # 将经纬度转换为本地平面坐标（简化计算）
        # 使用线段中点作为参考点
        ref_lat = (float(seg_lat1) + float(seg_lat2)) / 2
        
        # 纬度方向：1度 ≈ 111320 米
        # 经度方向：1度 ≈ 111320 * cos(纬度) 米
        lat_scale = 111320.0
        lon_scale = 111320.0 * math.cos(math.radians(ref_lat))
        
        # 转换为本地坐标
        px = (float(point_lon) - float(seg_lon1)) * lon_scale
        py = (float(point_lat) - float(seg_lat1)) * lat_scale
        
        ax = 0
        ay = 0
        bx = (float(seg_lon2) - float(seg_lon1)) * lon_scale
        by = (float(seg_lat2) - float(seg_lat1)) * lat_scale
        
        # 计算线段长度的平方
        seg_len_sq = bx * bx + by * by
        
        if seg_len_sq == 0:
            # 线段退化为点
            return math.sqrt(px * px + py * py)
        
        # 计算投影参数 t
        t = max(0, min(1, (px * bx + py * by) / seg_len_sq))
        
        # 计算投影点
        proj_x = ax + t * bx
        proj_y = ay + t * by
        
        # 计算距离
        dx = px - proj_x
        dy = py - proj_y
        
        return math.sqrt(dx * dx + dy * dy)
    
    def point_to_line_distance(self, point_lat, point_lon, geometry):
        """
        计算点到整条路径的最短距离（米）
        
        参数:
            point_lat, point_lon: 点的纬度和经度
            geometry: GeoJSON LineString 格式的坐标数组，如 [[lon1, lat1], [lon2, lat2], ...]
            
        返回:
            点到路径的最短距离（米）
        """
        if not geometry or not isinstance(geometry, list) or len(geometry) < 2:
            return float('inf')
        
        min_distance = float('inf')
        
        # 遍历所有线段
        for i in range(len(geometry) - 1):
            try:
                # GeoJSON 格式：[lon, lat]
                seg_lon1, seg_lat1 = geometry[i][0], geometry[i][1]
                seg_lon2, seg_lat2 = geometry[i + 1][0], geometry[i + 1][1]
                
                distance = self.point_to_segment_distance(
                    point_lat, point_lon,
                    seg_lat1, seg_lon1,
                    seg_lat2, seg_lon2
                )
                
                if distance < min_distance:
                    min_distance = distance
            except (IndexError, TypeError):
                continue
        
        return min_distance
    
    def check_path_exists(self, site_a, sites_z):
        """
        检查 A 端站点和 Z 端站点对应的路径是否存在（考虑 AZ 和 ZA 两个方向）
        
        参数:
            site_a: A 端站点
            sites_z: Z 端站点列表
            
        返回:
            True 如果所有 AZ 组合都能在路径中找到匹配，否则 False
        """
        if not site_a or not sites_z:
            return False
        
        for site_z in sites_z:
            # 检查 A->Z 方向
            path_az = OtnPath.objects.filter(site_a=site_a, site_z=site_z).exists()
            # 检查 Z->A 方向
            path_za = OtnPath.objects.filter(site_a=site_z, site_z=site_a).exists()
            
            if not path_az and not path_za:
                return False
        
        return True
    
    def find_paths_containing_point(self, fault_lat, fault_lon, distance_threshold):
        """
        查找包含（或接近）故障点的所有路径
        
        参数:
            fault_lat, fault_lon: 故障点的纬度和经度
            distance_threshold: 距离阈值（米）
            
        返回:
            包含故障点的路径列表，每个元素为 (path, distance)
        """
        matching_paths = []
        
        # 获取所有有几何数据的路径
        paths = OtnPath.objects.exclude(geometry__isnull=True)
        
        for path in paths:
            try:
                distance = self.point_to_line_distance(
                    fault_lat, fault_lon, path.geometry
                )
                
                if distance <= distance_threshold:
                    matching_paths.append((path, distance))
            except Exception:
                continue
        
        # 按距离排序
        matching_paths.sort(key=lambda x: x[1])
        
        return matching_paths
    
    def determine_az_sites_from_paths(self, matching_paths):
        """
        从多条匹配路径中确定 A 端和 Z 端站点
        
        策略：
        - 如果只有一条路径，直接使用该路径的 AZ 端站点
        - 如果有多条路径，找出相同的站点作为 A 端，不同的站点作为 Z 端
        
        参数:
            matching_paths: 匹配的路径列表，每个元素为 (path, distance)
            
        返回:
            (a_site, z_sites_list) 或 (None, None) 如果无法确定
        """
        if not matching_paths:
            return None, None
        
        if len(matching_paths) == 1:
            path = matching_paths[0][0]
            return path.site_a, [path.site_z]
        
        # 多条路径：统计所有站点出现的次数
        site_counts = {}
        all_sites = set()
        
        for path, _ in matching_paths:
            all_sites.add(path.site_a)
            all_sites.add(path.site_z)
            
            site_counts[path.site_a] = site_counts.get(path.site_a, 0) + 1
            site_counts[path.site_z] = site_counts.get(path.site_z, 0) + 1
        
        # 找出出现次数最多的站点作为 A 端
        # 如果有多个站点出现次数相同，取第一个
        max_count = 0
        a_site = None
        
        for site, count in site_counts.items():
            if count > max_count:
                max_count = count
                a_site = site
        
        # 其他站点作为 Z 端
        z_sites = [site for site in all_sites if site != a_site]
        
        if not a_site or not z_sites:
            return None, None
        
        return a_site, z_sites
    
    def get_target_faults(self, distance_threshold, verbose=False):
        """
        获取需要处理的故障记录
        
        条件：
        1. 有 A 端站点和 Z 端站点
        2. 有经纬度坐标
        3. AZ 端点在路径对象中找不到对应路径
        
        返回:
            需要处理的故障记录列表
        """
        self.log_info("正在扫描故障记录...")
        
        # 获取有 A 端站点、Z 端站点、且有经纬度的故障
        faults = OtnFault.objects.filter(
            interruption_location_a__isnull=False,
            interruption_latitude__isnull=False,
            interruption_longitude__isnull=False
        )
        
        target_faults = []
        
        for fault in faults:
            # 检查是否有 Z 端站点
            z_sites = list(fault.interruption_location.all())
            if not z_sites:
                continue
            
            # 检查 AZ 端点是否在路径对象中存在
            if not self.check_path_exists(fault.interruption_location_a, z_sites):
                target_faults.append(fault)
                
                if verbose:
                    z_site_names = [s.name for s in z_sites]
                    self.log_info(
                        f"故障 {fault.fault_number}：A端={fault.interruption_location_a.name}, "
                        f"Z端={z_site_names} 在路径对象中找不到匹配"
                    )
        
        self.log_info(f"扫描完成：共 {faults.count()} 条有 A/Z 端站点的故障记录")
        self.log_info(f"需要修正的故障记录：{len(target_faults)} 条")
        
        return target_faults
    
    def process_fault(self, fault, distance_threshold, dry_run=True, verbose=False):
        """
        处理单个故障记录
        
        参数:
            fault: 故障记录
            distance_threshold: 距离阈值（米）
            dry_run: 是否模拟运行
            verbose: 是否输出详细日志
            
        返回:
            (成功与否, 消息)
        """
        try:
            fault_lat = fault.interruption_latitude
            fault_lon = fault.interruption_longitude
            
            if verbose:
                self.log_info(f"处理故障 {fault.fault_number}，坐标：({fault_lat}, {fault_lon})")
            
            # 查找包含故障点的路径
            matching_paths = self.find_paths_containing_point(
                fault_lat, fault_lon, distance_threshold
            )
            
            if not matching_paths:
                return False, f"故障 {fault.fault_number}：在距离阈值 {distance_threshold} 米内未找到匹配的路径"
            
            if verbose:
                path_info = ", ".join([
                    f"{p.name}({p.site_a.name}-{p.site_z.name}, {d:.0f}m)" 
                    for p, d in matching_paths
                ])
                self.log_info(f"找到 {len(matching_paths)} 条匹配路径：{path_info}")
            
            # 确定 AZ 端站点
            new_a_site, new_z_sites = self.determine_az_sites_from_paths(matching_paths)
            
            if not new_a_site or not new_z_sites:
                return False, f"故障 {fault.fault_number}：无法从匹配路径中确定 AZ 端站点"
            
            # 记录当前状态
            old_a_site = fault.interruption_location_a
            old_z_sites = list(fault.interruption_location.all())
            old_z_site_names = [s.name for s in old_z_sites]
            new_z_site_names = [s.name for s in new_z_sites]
            
            # 检查是否需要更新
            if (old_a_site == new_a_site and 
                set(old_z_sites) == set(new_z_sites)):
                return True, f"故障 {fault.fault_number}：站点信息无需更新"
            
            # 执行更新
            if not dry_run:
                try:
                    fault.interruption_location_a = new_a_site
                    fault.save()
                    fault.interruption_location.set(new_z_sites)
                    fault.save()
                    
                    # 验证更新
                    fault.refresh_from_db()
                    
                    updated_a_site = fault.interruption_location_a
                    updated_z_sites = list(fault.interruption_location.all())
                    
                    if (updated_a_site == new_a_site and 
                        set(updated_z_sites) == set(new_z_sites)):
                        return True, (
                            f"故障 {fault.fault_number} 已成功更新：\n"
                            f"  A端站点：{old_a_site.name} → {new_a_site.name}\n"
                            f"  Z端站点：{old_z_site_names} → {new_z_site_names}"
                        )
                    else:
                        return False, f"故障 {fault.fault_number}：更新验证失败"
                        
                except Exception as e:
                    return False, f"故障 {fault.fault_number} 更新时出错：{str(e)}"
            else:
                return True, (
                    f"模拟：故障 {fault.fault_number} 将更新：\n"
                    f"  A端站点：{old_a_site.name} → {new_a_site.name}\n"
                    f"  Z端站点：{old_z_site_names} → {new_z_site_names}\n"
                    f"  匹配路径数：{len(matching_paths)}"
                )
                
        except Exception as e:
            return False, f"处理故障 {fault.fault_number} 时发生异常：{str(e)}"
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        dry_run = data['dry_run']
        distance_threshold = data['distance_threshold']
        verbose = data['verbose']
        
        self.log_info("开始根据路径修正故障站点")
        self.log_info(f"距离阈值：{distance_threshold} 米")
        
        # 获取需要处理的故障记录
        target_faults = self.get_target_faults(distance_threshold, verbose)
        
        if not target_faults:
            return "没有找到需要修正的故障记录（所有故障的 AZ 端站点都能在路径对象中找到匹配）"
        
        # 统计信息
        total_to_process = len(target_faults)
        successful_updates = 0
        failed_updates = 0
        skipped_faults = 0
        
        self.log_info(f"开始处理 {total_to_process} 条故障记录...")
        
        # 处理每个故障记录
        for i, fault in enumerate(target_faults):
            if (i + 1) % 10 == 0:
                self.log_info(f"已处理 {i + 1}/{total_to_process} 条故障记录...")
            
            is_success, message = self.process_fault(
                fault, 
                distance_threshold,
                dry_run=(dry_run or not commit),
                verbose=verbose
            )
            
            if is_success:
                if "无需更新" in message:
                    self.log_info(message)
                    skipped_faults += 1
                else:
                    self.log_success(message)
                    successful_updates += 1
            else:
                self.log_warning(message)
                failed_updates += 1
        
        # 生成结果报告
        result_message = (
            f"处理完成！\n"
            f"• 需要修正的故障记录：{total_to_process} 条\n"
            f"• 成功更新：{successful_updates} 条\n"
            f"• 更新失败：{failed_updates} 条\n"
            f"• 无需更新：{skipped_faults} 条\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，数据未实际保存到数据库。\n"
            result_message += "如需实际保存，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n数据已成功保存到数据库。"
        
        if verbose:
            result_message += f"\n\n详细模式已启用，请查看上方日志了解每个故障的处理详情。"
        
        return result_message
