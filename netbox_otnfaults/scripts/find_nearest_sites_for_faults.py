"""
NetBox自定义脚本：根据故障位置经纬度查找最近站点

功能：
1. 遍历所有故障记录
2. 对于每个有经纬度的故障，计算其与所有有经纬度的站点之间的距离
3. 找到距离最近的两个站点
4. 将最近站点设为故障位置A端站点，第二近站点设为故障位置Z端站点
5. 支持覆盖已有站点关联

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.find_nearest_sites_for_faults
2. 选择脚本类：FindNearestSitesForFaults
3. 运行脚本
"""

import math
from decimal import Decimal
from django.contrib.auth import get_user_model
from dcim.models import Site
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFault


class FindNearestSitesForFaults(Script):
    """
    根据故障位置经纬度查找最近站点的自定义脚本
    """
    
    class Meta:
        name = "根据故障位置查找最近站点"
        description = "根据故障位置经纬度查找最近的两个站点并设置为A/Z端站点"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际修改数据库（默认：True）",
        default=True
    )
    
    overwrite = BooleanVar(
        label="覆盖已有站点关联",
        description="覆盖故障记录已有的站点关联（默认：True）",
        default=True
    )
    
    verbose = BooleanVar(
        label="详细日志",
        description="输出详细日志信息，用于调试（默认：False）",
        default=False
    )
    
    def __init__(self):
        super().__init__()
        self.sites_with_coords = []
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        使用Haversine公式计算两个经纬度坐标之间的距离（单位：公里）
        
        参数:
            lat1, lon1: 第一个点的纬度和经度（十进制）
            lat2, lon2: 第二个点的纬度和经度（十进制）
            
        返回:
            两点之间的距离（公里）
        """
        # 将十进制转换为浮点数
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
        
        # 地球半径（公里）
        R = 6371.0
        
        # 将角度转换为弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 计算差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine公式
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # 计算距离
        distance = R * c
        return distance
    
    def load_sites_with_coordinates(self):
        """
        加载所有有经纬度坐标的站点
        
        返回:
            包含站点和坐标的列表
        """
        self.log_info("正在加载有经纬度坐标的站点...")
        
        # 查询所有有经纬度的站点
        sites = Site.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
        
        site_list = []
        for site in sites:
            try:
                # 确保经纬度是有效的Decimal类型
                lat = site.latitude
                lon = site.longitude
                
                if lat is not None and lon is not None:
                    site_list.append({
                        'site': site,
                        'latitude': lat,
                        'longitude': lon
                    })
            except (AttributeError, ValueError, TypeError):
                # 跳过无效的站点
                continue
        
        self.log_success(f"成功加载 {len(site_list)} 个有经纬度坐标的站点")
        return site_list
    
    def get_faults_to_process(self, overwrite):
        """
        获取需要处理的故障记录
        
        参数:
            overwrite: 是否覆盖已有站点关联
            
        返回:
            需要处理的故障记录列表
        """
        self.log_info("正在扫描故障记录...")
        
        # 获取所有有经纬度的故障记录
        faults = OtnFault.objects.exclude(
            interruption_latitude__isnull=True
        ).exclude(
            interruption_longitude__isnull=True
        )
        
        faults_to_process = []
        for fault in faults:
            # 根据overwrite参数决定是否处理已有站点关联的故障
            if overwrite:
                # 覆盖模式：处理所有有经纬度的故障
                faults_to_process.append(fault)
            else:
                # 非覆盖模式：只处理没有站点关联的故障
                if not fault.interruption_location.exists() and not fault.interruption_location_a:
                    faults_to_process.append(fault)
        
        self.log_info(f"扫描完成：共 {faults.count()} 条有经纬度的故障记录")
        self.log_info(f"将处理 {len(faults_to_process)} 条故障记录")
        
        return faults_to_process
    
    def find_nearest_sites(self, fault_lat, fault_lon, sites_with_coords):
        """
        查找距离故障位置最近的两个站点
        
        参数:
            fault_lat: 故障纬度
            fault_lon: 故障经度
            sites_with_coords: 站点列表（包含站点对象和坐标）
            
        返回:
            (最近站点, 第二近站点) 或 (None, None) 如果没有足够站点
        """
        if len(sites_with_coords) < 2:
            self.log_warning(f"站点数量不足（{len(sites_with_coords)}个），需要至少2个站点")
            return None, None
        
        # 计算故障到每个站点的距离
        distances = []
        for site_data in sites_with_coords:
            try:
                distance = self.haversine_distance(
                    fault_lat, fault_lon,
                    site_data['latitude'], site_data['longitude']
                )
                distances.append({
                    'site': site_data['site'],
                    'distance': distance
                })
            except (ValueError, TypeError) as e:
                # 跳过计算失败的站点
                continue
        
        if len(distances) < 2:
            self.log_warning(f"有效站点数量不足（{len(distances)}个），无法找到两个最近站点")
            return None, None
        
        # 按距离排序
        distances.sort(key=lambda x: x['distance'])
        
        # 返回最近的两个站点
        nearest_site = distances[0]['site']
        second_nearest_site = distances[1]['site']
        
        # 检查两个站点是否相同（虽然概率很低，但需要处理）
        if nearest_site == second_nearest_site:
            if len(distances) >= 3:
                # 如果前两个站点相同，取第三个站点作为第二近站点
                second_nearest_site = distances[2]['site']
                self.log_warning(f"最近的两个站点相同，使用第三近站点作为Z端站点")
            else:
                self.log_warning(f"最近的两个站点相同且没有其他可用站点")
                return None, None
        
        return nearest_site, second_nearest_site
    
    def update_fault_sites(self, fault, nearest_site, second_nearest_site, dry_run=True, verbose=False):
        """
        更新故障记录的站点关联
        
        参数:
            fault: 故障记录
            nearest_site: 最近站点（设为A端）
            second_nearest_site: 第二近站点（设为Z端）
            dry_run: 是否模拟运行
            verbose: 是否输出详细日志
            
        返回:
            (成功与否, 消息)
        """
        try:
            if not dry_run:
                # 记录详细调试信息
                debug_info = []
                debug_info.append(f"故障ID: {fault.id}, 编号: {fault.fault_number}")
                debug_info.append(f"A端站点: {nearest_site.name} (ID: {nearest_site.id})")
                debug_info.append(f"Z端站点: {second_nearest_site.name} (ID: {second_nearest_site.id})")
                
                # 保存当前状态用于比较
                original_a_site_id = fault.interruption_location_a.id if fault.interruption_location_a else None
                original_z_site_ids = list(fault.interruption_location.values_list('id', flat=True))
                
                # 实际更新数据库
                # 第一步：设置A端站点（外键字段）
                fault.interruption_location_a = nearest_site
                
                # 第二步：保存故障记录以保存外键字段
                fault.save()
                
                # 第三步：设置Z端站点（多对多字段）
                # 使用set()方法，参考fill_missing_sites.py中的做法
                fault.interruption_location.set([second_nearest_site])
                
                # 第四步：再次保存以确保多对多字段保存
                fault.save()
                
                # 重新从数据库加载以验证保存成功
                fault.refresh_from_db()
                
                # 验证A端站点是否已设置 - 使用ID比较更可靠
                current_a_site_id = fault.interruption_location_a.id if fault.interruption_location_a else None
                current_z_site_ids = list(fault.interruption_location.values_list('id', flat=True))
                
                a_site_set = current_a_site_id == nearest_site.id
                z_site_set = second_nearest_site.id in current_z_site_ids
                
                debug_info.append(f"原始A端站点ID: {original_a_site_id}")
                debug_info.append(f"原始Z端站点IDs: {original_z_site_ids}")
                debug_info.append(f"当前A端站点ID: {current_a_site_id}")
                debug_info.append(f"当前Z端站点IDs: {current_z_site_ids}")
                debug_info.append(f"A端设置成功: {a_site_set}")
                debug_info.append(f"Z端设置成功: {z_site_set}")
                
                if a_site_set and z_site_set:
                    success_message = (
                        f"故障 {fault.fault_number} 已成功更新："
                        f"A端站点={nearest_site.name} ({nearest_site.latitude}, {nearest_site.longitude}), "
                        f"Z端站点={second_nearest_site.name} ({second_nearest_site.latitude}, {second_nearest_site.longitude})"
                    )
                    # 在详细模式下记录调试信息
                    if verbose:
                        self.log_info(f"调试信息: {' | '.join(debug_info)}")
                    return True, success_message
                else:
                    error_details = []
                    if not a_site_set:
                        error_details.append(f"A端站点未正确设置 (期望ID: {nearest_site.id}, 实际ID: {current_a_site_id})")
                    if not z_site_set:
                        error_details.append(f"Z端站点未正确设置 (期望ID: {second_nearest_site.id}, 实际IDs: {current_z_site_ids})")
                    
                    # 记录详细的调试信息
                    debug_message = f"调试信息: {' | '.join(debug_info)}"
                    error_message = f"故障 {fault.fault_number} 更新验证失败：{', '.join(error_details)}"
                    
                    # 在详细模式下记录错误
                    if verbose:
                        self.log_warning(f"{error_message} | {debug_message}")
                    
                    return False, error_message
                    
            else:
                # 模拟运行，只记录日志
                return True, (
                    f"模拟：故障 {fault.fault_number} 将更新："
                    f"A端站点={nearest_site.name} ({nearest_site.latitude}, {nearest_site.longitude}), "
                    f"Z端站点={second_nearest_site.name} ({second_nearest_site.latitude}, {second_nearest_site.longitude})"
                )
        except Exception as e:
            import traceback
            error_details = f"更新故障 {fault.fault_number} 时出错：{str(e)}\n{traceback.format_exc()}"
            # 在详细模式下记录完整错误信息
            if verbose:
                self.log_failure(error_details)
            return False, f"更新故障 {fault.fault_number} 时出错：{str(e)}"
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        overwrite = data['overwrite']
        verbose = data['verbose']
        
        self.log_info("开始根据故障位置查找最近站点")
        
        # 加载有经纬度的站点
        sites_with_coords = self.load_sites_with_coordinates()
        
        if len(sites_with_coords) < 2:
            return f"错误：系统中只有 {len(sites_with_coords)} 个有经纬度的站点，需要至少2个站点才能运行"
        
        # 获取需要处理的故障记录
        faults_to_process = self.get_faults_to_process(overwrite)
        
        if not faults_to_process:
            if overwrite:
                return "所有有经纬度的故障记录都已处理完成，无需更新"
            else:
                return "没有需要处理的故障记录（可能所有故障都已有关联站点，或没有有经纬度的故障）"
        
        # 统计信息
        total_to_process = len(faults_to_process)
        successful_updates = 0
        failed_updates = 0
        skipped_faults = 0
        
        self.log_info(f"开始为 {total_to_process} 条故障记录查找最近站点...")
        
        # 处理每个故障记录
        for i, fault in enumerate(faults_to_process):
            # 进度反馈
            if (i + 1) % 10 == 0:
                self.log_info(f"已处理 {i + 1}/{total_to_process} 条故障记录...")
            
            try:
                # 获取故障经纬度
                fault_lat = fault.interruption_latitude
                fault_lon = fault.interruption_longitude
                
                if fault_lat is None or fault_lon is None:
                    self.log_warning(f"故障 {fault.fault_number} 缺少经纬度信息，跳过")
                    skipped_faults += 1
                    continue
                
                # 详细日志：显示故障位置
                if verbose:
                    self.log_info(f"故障 {fault.fault_number} 位置：纬度={fault_lat}, 经度={fault_lon}")
                
                # 查找最近的两个站点
                nearest_site, second_nearest_site = self.find_nearest_sites(
                    fault_lat, fault_lon, sites_with_coords
                )
                
                if nearest_site is None or second_nearest_site is None:
                    self.log_warning(f"故障 {fault.fault_number} 无法找到两个最近站点，跳过")
                    skipped_faults += 1
                    continue
                
                # 详细日志：显示找到的站点
                if verbose:
                    self.log_info(f"故障 {fault.fault_number} 找到站点：A端={nearest_site.name}, Z端={second_nearest_site.name}")
                
                # 计算距离用于日志
                distance_a = self.haversine_distance(
                    fault_lat, fault_lon,
                    nearest_site.latitude, nearest_site.longitude
                )
                distance_z = self.haversine_distance(
                    fault_lat, fault_lon,
                    second_nearest_site.latitude, second_nearest_site.longitude
                )
                
                # 详细日志：显示距离
                if verbose:
                    self.log_info(f"故障 {fault.fault_number} 距离：A端={distance_a:.2f}km, Z端={distance_z:.2f}km")
                
                # 检查故障当前状态
                if verbose:
                    current_a_site = fault.interruption_location_a
                    current_z_sites = list(fault.interruption_location.all())
                    self.log_info(f"故障 {fault.fault_number} 当前状态：A端={current_a_site.name if current_a_site else '无'}, Z端={[s.name for s in current_z_sites]}")
                
                # 更新故障记录
                is_success, message = self.update_fault_sites(
                    fault, nearest_site, second_nearest_site, 
                    dry_run=(dry_run or not commit),
                    verbose=verbose
                )
                
                if is_success:
                    # 添加距离信息到日志
                    detailed_message = f"{message}，距离：A端={distance_a:.2f}km，Z端={distance_z:.2f}km"
                    self.log_success(detailed_message)
                    successful_updates += 1
                    
                    # 详细日志：显示更新后的状态
                    if verbose and not dry_run and commit:
                        fault.refresh_from_db()
                        updated_a_site = fault.interruption_location_a
                        updated_z_sites = list(fault.interruption_location.all())
                        self.log_info(f"故障 {fault.fault_number} 更新后状态：A端={updated_a_site.name if updated_a_site else '无'}, Z端={[s.name for s in updated_z_sites]}")
                        
                else:
                    self.log_warning(message)
                    failed_updates += 1
                    
            except Exception as e:
                error_msg = f"处理故障 {fault.fault_number} 时发生异常：{str(e)}"
                self.log_failure(error_msg)
                failed_updates += 1
        
        # 生成结果报告
        result_message = (
            f"处理完成！\n"
            f"• 有经纬度的站点数量：{len(sites_with_coords)} 个\n"
            f"• 有经纬度的故障记录：{OtnFault.objects.exclude(interruption_latitude__isnull=True).exclude(interruption_longitude__isnull=True).count()} 条\n"
            f"• 需要处理的故障记录：{total_to_process} 条\n"
            f"• 成功更新：{successful_updates} 条\n"
            f"• 更新失败：{failed_updates} 条\n"
            f"• 跳过处理：{skipped_faults} 条\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，数据未实际保存到数据库。\n"
            result_message += "如需实际保存，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n数据已成功保存到数据库。"
        
        # 详细日志：总结
        if verbose:
            result_message += f"\n\n详细模式已启用，请查看上方日志了解每个故障的处理详情。"
        
        return result_message
