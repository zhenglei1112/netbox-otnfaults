"""
NetBox自定义脚本：根据故障位置A端站点的地区信息更新故障的省份字段

功能：
1. 遍历所有OTN故障记录
2. 对于每个故障，获取故障位置A端站点（interruption_location_a）
3. 获取该站点的地区（region）信息
4. 将站点的地区信息更新到故障的省份（province）字段
5. 支持模拟运行和批量处理

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.update_fault_provinces_from_sites
2. 选择脚本类：UpdateFaultProvincesFromSites
3. 运行脚本
"""

from dcim.models import Site, Region
from extras.scripts import Script, BooleanVar, IntegerVar, ChoiceVar
from netbox_otnfaults.models import OtnFault


class UpdateFaultProvincesFromSites(Script):
    """
    根据故障位置A端站点的地区信息更新故障的省份字段的自定义脚本
    """
    
    class Meta:
        name = "根据站点地区更新故障省份"
        description = "根据故障位置A端站点的地区信息，更新故障信息的省份字段"
        commit_default = False
        scheduling_enabled = True
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际更新故障省份（默认：True）",
        default=True
    )
    
    batch_size = IntegerVar(
        label="批量大小",
        description="每次批量处理的故障数量（0表示一次性处理所有故障）",
        default=50,
        min_value=0
    )
    
    max_faults = IntegerVar(
        label="最大处理数量",
        description="最大处理故障数量（0表示无限制）",
        default=0,
        min_value=0
    )
    
    update_strategy = ChoiceVar(
        label="更新策略",
        description="当站点没有地区信息时的处理方式",
        choices=[
            ('skip', '跳过（不更新）'),
            ('clear', '清空省份字段'),
        ],
        default='skip'
    )
    
    def __init__(self):
        super().__init__()
    
    def get_faults_to_process(self):
        """
        获取需要处理的故障记录
        
        返回:
            QuerySet: 需要处理的故障记录
        """
        # 获取所有故障记录
        all_faults = OtnFault.objects.all().order_by('fault_number')
        
        # 如果需要，可以添加筛选条件
        # 例如：只处理province为空的故障
        # all_faults = all_faults.filter(province__isnull=True)
        
        return all_faults
    
    def process_fault(self, fault, dry_run=True):
        """
        处理单个故障记录
        
        参数:
            fault: OtnFault对象
            dry_run: 是否模拟运行
            
        返回:
            (成功与否, 消息)
        """
        try:
            # 获取故障位置A端站点
            site_a = fault.interruption_location_a
            
            if not site_a:
                return False, f"故障 {fault.fault_number} 没有故障位置A端站点"
            
            # 获取站点的地区信息
            site_region = site_a.region
            
            if not site_region:
                # 站点没有地区信息
                if self.update_strategy == 'clear':
                    # 清空故障的省份字段
                    if not dry_run:
                        fault.province = None
                        fault.save()
                    return True, f"故障 {fault.fault_number}: 站点 {site_a.name} 无地区信息，已清空省份字段"
                else:
                    # 跳过
                    return True, f"故障 {fault.fault_number}: 站点 {site_a.name} 无地区信息，已跳过"
            
            # 检查是否需要更新
            if fault.province == site_region:
                return True, f"故障 {fault.fault_number}: 省份字段已为 {site_region.name}，无需更新"
            
            # 更新故障的省份字段
            if not dry_run:
                fault.province = site_region
                fault.save()
                return True, f"故障 {fault.fault_number}: 已更新省份为 {site_region.name}（来自站点 {site_a.name}）"
            else:
                return True, f"故障 {fault.fault_number}: 模拟更新省份为 {site_region.name}（来自站点 {site_a.name}）"
                
        except Exception as e:
            return False, f"处理故障 {fault.fault_number} 时发生异常: {str(e)}"
    
    def run(self, data, commit):
        """
        脚本主入口
        """
        # 读取脚本参数
        dry_run = data['dry_run']
        batch_size = data['batch_size']
        max_faults = data['max_faults']
        update_strategy = data['update_strategy']
        
        self.log_info("开始根据站点地区信息更新故障省份字段")
        self.log_info(f"参数: dry_run={dry_run}, batch_size={batch_size}, "
                     f"max_faults={max_faults}, update_strategy={update_strategy}")
        
        # 获取所有故障记录
        all_faults = self.get_faults_to_process()
        total_faults = all_faults.count()
        
        self.log_info(f"NetBox中共有 {total_faults} 条故障记录")
        
        if total_faults == 0:
            return "错误：没有找到故障记录"
        
        # 限制处理数量
        if max_faults > 0:
            faults_to_process = all_faults[:max_faults]
            self.log_info(f"根据最大处理数量限制，将处理 {len(faults_to_process)} 条故障记录")
        else:
            faults_to_process = all_faults
        
        # 统计信息
        total_to_process = len(faults_to_process)
        processed = 0
        successful = 0
        failed = 0
        skipped_no_site = 0
        skipped_no_region = 0
        already_correct = 0
        updated = 0
        cleared = 0
        
        self.log_info(f"开始处理 {total_to_process} 条故障记录...")
        
        # 处理每个故障
        for i, fault in enumerate(faults_to_process):
            processed += 1
            
            # 进度反馈
            if processed % 10 == 0 or processed == total_to_process:
                self.log_info(f"已处理 {processed}/{total_to_process} 条故障记录...")
            
            # 处理故障
            success, message = self.process_fault(fault, dry_run=(dry_run or not commit))
            
            if success:
                successful += 1
                
                # 根据消息内容分类
                if "无需更新" in message:
                    already_correct += 1
                    self.log_info(f"{message}")
                elif "清空省份字段" in message:
                    cleared += 1
                    self.log_warning(f"{message}")
                elif "无地区信息" in message and "已跳过" in message:
                    skipped_no_region += 1
                    self.log_warning(f"{message}")
                elif "模拟更新" in message:
                    updated += 1
                    self.log_success(f"{message}")
                elif "已更新省份" in message:
                    updated += 1
                    self.log_success(f"{message}")
                elif "没有故障位置A端站点" in message:
                    skipped_no_site += 1
                    self.log_warning(f"{message}")
                else:
                    self.log_info(f"{message}")
            else:
                failed += 1
                self.log_failure(f"{message}")
            
            # 注意：NetBox会自动处理事务，不需要手动调用transaction.commit()
            # 当commit=True时，NetBox会在一个原子事务块中运行脚本
            # 手动调用transaction.commit()会导致TransactionManagementError
        
        # 生成结果报告
        result_message = (
            f"处理完成！\n"
            f"• 总故障记录数: {total_faults} 条\n"
            f"• 处理故障记录数: {total_to_process} 条\n"
            f"• 成功处理: {successful} 条\n"
            f"• 失败: {failed} 条\n"
            f"\n"
            f"详细统计:\n"
            f"• 跳过（无A端站点）: {skipped_no_site} 条\n"
            f"• 跳过（站点无地区信息）: {skipped_no_region} 条\n"
            f"• 已正确无需更新: {already_correct} 条\n"
            f"• 清空省份字段: {cleared} 条\n"
            f"• 成功更新: {updated} 条\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，故障省份字段未实际更新。\n"
            result_message += "如需实际更新，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n故障省份字段已成功更新。"
        
        return result_message


# 脚本测试函数（可选）
if __name__ == "__main__":
    # 仅用于本地测试
    print("此脚本需要在NetBox环境中运行")
