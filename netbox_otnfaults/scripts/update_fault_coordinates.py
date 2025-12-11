"""
NetBox自定义脚本：更新特定故障分类的坐标信息

功能：
1. 遍历所有故障记录
2. 如果故障分类为电力故障、空调故障和设备故障（power, pigtail, device）
3. 那么将故障位置Z端站点信息清除
4. 同时使用故障位置A端站点的经纬度信息填充故障的经纬度信息

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.update_fault_coordinates
2. 选择脚本类：UpdateFaultCoordinates
3. 运行脚本
"""

from django.contrib.auth import get_user_model
from dcim.models import Site
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFault, FaultCategoryChoices


class UpdateFaultCoordinates(Script):
    """
    更新特定故障分类的坐标信息的自定义脚本
    """
    
    class Meta:
        name = "更新故障坐标信息"
        description = "对于电力、空调、设备故障，清除Z端站点并使用A端站点坐标填充故障坐标"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际修改数据库（默认：True）",
        default=True
    )
    
    verbose = BooleanVar(
        label="详细日志",
        description="输出详细日志信息，用于调试（默认：False）",
        default=False
    )
    
    def __init__(self):
        super().__init__()
    
    def get_target_faults(self):
        """
        获取需要处理的故障记录
        
        返回:
            需要处理的故障记录列表
        """
        self.log_info("正在扫描故障记录...")
        
        # 定义需要处理的故障分类
        target_categories = [
            FaultCategoryChoices.CATEGORY_POWER,      # 电力故障
            FaultCategoryChoices.CATEGORY_PIGTAIL,    # 空调故障
            FaultCategoryChoices.CATEGORY_DEVICE,     # 设备故障
        ]
        
        # 获取所有故障记录
        all_faults = OtnFault.objects.all()
        total_faults = all_faults.count()
        
        # 筛选目标故障分类的故障记录
        target_faults = []
        for fault in all_faults:
            if fault.fault_category in target_categories:
                target_faults.append(fault)
        
        self.log_info(f"扫描完成：共 {total_faults} 条故障记录")
        self.log_info(f"目标故障分类（电力、空调、设备）的故障记录：{len(target_faults)} 条")
        
        return target_faults
    
    def process_fault(self, fault, dry_run=True, verbose=False):
        """
        处理单个故障记录
        
        参数:
            fault: 故障记录
            dry_run: 是否模拟运行
            verbose: 是否输出详细日志
            
        返回:
            (成功与否, 消息)
        """
        try:
            # 获取故障分类名称
            category_display = fault.get_fault_category_display() if fault.fault_category else "未知"
            
            # 检查是否有A端站点
            if not fault.interruption_location_a:
                return False, f"故障 {fault.fault_number}（{category_display}）没有A端站点，无法获取坐标"
            
            # 检查A端站点是否有经纬度信息
            a_site = fault.interruption_location_a
            if a_site.latitude is None or a_site.longitude is None:
                return False, f"故障 {fault.fault_number}（{category_display}）的A端站点 {a_site.name} 缺少经纬度信息"
            
            # 记录当前状态
            current_z_sites = list(fault.interruption_location.all())
            current_z_site_names = [site.name for site in current_z_sites]
            current_lat = fault.interruption_latitude
            current_lon = fault.interruption_longitude
            
            # 详细日志：显示当前状态
            if verbose:
                self.log_info(f"故障 {fault.fault_number} 当前状态：")
                self.log_info(f"  分类：{category_display}")
                self.log_info(f"  A端站点：{a_site.name} (ID: {a_site.id})")
                self.log_info(f"  A端站点坐标：纬度={a_site.latitude}, 经度={a_site.longitude}")
                self.log_info(f"  Z端站点：{current_z_site_names}")
                self.log_info(f"  当前故障坐标：纬度={current_lat}, 经度={current_lon}")
            
            # 准备更新操作
            operations = []
            
            # 操作1：清除Z端站点
            if current_z_sites:
                operations.append(f"清除Z端站点：{current_z_site_names}")
            
            # 操作2：使用A端站点坐标填充故障坐标
            new_lat = a_site.latitude
            new_lon = a_site.longitude
            coordinate_updated = False
            
            if current_lat != new_lat or current_lon != new_lon:
                operations.append(f"更新故障坐标：({current_lat}, {current_lon}) → ({new_lat}, {new_lon})")
                coordinate_updated = True
            
            # 如果没有需要执行的操作
            if not operations:
                return True, f"故障 {fault.fault_number}（{category_display}）无需更新"
            
            # 执行更新操作
            if not dry_run:
                try:
                    # 清除Z端站点
                    if current_z_sites:
                        fault.interruption_location.clear()
                    
                    # 更新故障坐标
                    if coordinate_updated:
                        fault.interruption_latitude = new_lat
                        fault.interruption_longitude = new_lon
                    
                    # 保存更改
                    fault.save()
                    
                    # 验证更新
                    fault.refresh_from_db()
                    
                    # 验证Z端站点是否已清除
                    updated_z_sites = list(fault.interruption_location.all())
                    z_site_cleared = len(updated_z_sites) == 0
                    
                    # 验证坐标是否已更新
                    lat_updated = fault.interruption_latitude == new_lat
                    lon_updated = fault.interruption_longitude == new_lon
                    
                    if z_site_cleared and lat_updated and lon_updated:
                        success_message = f"故障 {fault.fault_number}（{category_display}）已成功更新："
                        if current_z_sites:
                            success_message += f"清除了Z端站点，"
                        if coordinate_updated:
                            success_message += f"使用A端站点坐标({new_lat}, {new_lon})更新了故障坐标"
                        
                        # 详细日志：显示更新后的状态
                        if verbose:
                            self.log_info(f"故障 {fault.fault_number} 更新后状态：")
                            self.log_info(f"  Z端站点：{list(fault.interruption_location.all())}")
                            self.log_info(f"  故障坐标：纬度={fault.interruption_latitude}, 经度={fault.interruption_longitude}")
                        
                        return True, success_message
                    else:
                        error_details = []
                        if not z_site_cleared:
                            error_details.append(f"Z端站点未正确清除")
                        if not lat_updated:
                            error_details.append(f"纬度未正确更新")
                        if not lon_updated:
                            error_details.append(f"经度未正确更新")
                        
                        return False, f"故障 {fault.fault_number}（{category_display}）更新验证失败：{', '.join(error_details)}"
                        
                except Exception as e:
                    return False, f"故障 {fault.fault_number}（{category_display}）更新时出错：{str(e)}"
            else:
                # 模拟运行，只记录日志
                sim_message = f"模拟：故障 {fault.fault_number}（{category_display}）将执行以下操作："
                for op in operations:
                    sim_message += f"\n  • {op}"
                return True, sim_message
                
        except Exception as e:
            return False, f"处理故障 {fault.fault_number} 时发生异常：{str(e)}"
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        verbose = data['verbose']
        
        self.log_info("开始更新故障坐标信息")
        self.log_info("目标故障分类：电力故障、空调故障、设备故障")
        
        # 获取需要处理的故障记录
        target_faults = self.get_target_faults()
        
        if not target_faults:
            return "没有找到目标故障分类（电力、空调、设备）的故障记录，无需处理"
        
        # 统计信息
        total_to_process = len(target_faults)
        successful_updates = 0
        failed_updates = 0
        skipped_faults = 0
        
        self.log_info(f"开始处理 {total_to_process} 条目标故障记录...")
        
        # 处理每个故障记录
        for i, fault in enumerate(target_faults):
            # 进度反馈
            if (i + 1) % 10 == 0:
                self.log_info(f"已处理 {i + 1}/{total_to_process} 条故障记录...")
            
            # 处理故障记录
            is_success, message = self.process_fault(
                fault, 
                dry_run=(dry_run or not commit),
                verbose=verbose
            )
            
            if is_success:
                self.log_success(message)
                successful_updates += 1
            else:
                self.log_warning(message)
                failed_updates += 1
        
        # 生成结果报告
        result_message = (
            f"处理完成！\n"
            f"• 目标故障分类（电力、空调、设备）的故障记录：{total_to_process} 条\n"
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
