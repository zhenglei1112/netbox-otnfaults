"""
NetBox自定义脚本：为现有故障记录填充缺失的中断位置站点信息

功能：
1. 扫描所有现有的OTN故障记录
2. 检查哪些故障记录缺少中断位置（AZ端机房）信息
3. 为这些故障记录随机分配2-3个站点作为中断位置
4. 更新数据库中的故障记录

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.fill_missing_sites
2. 选择脚本类：FillMissingSites
3. 运行脚本
"""

import random
from django.contrib.auth import get_user_model
from dcim.models import Site
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFault


class FillMissingSites(Script):
    """
    为现有故障记录填充缺失的中断位置站点信息的自定义脚本
    """
    
    class Meta:
        name = "填充缺失的中断位置站点信息"
        description = "为现有故障记录填充缺失的中断位置（AZ端机房）站点信息"
        commit_default = False
    
    # 脚本参数
    dry_run = BooleanVar(
        label="模拟运行",
        description="模拟运行，不实际修改数据库（默认：True）",
        default=True
    )
    
    def __init__(self):
        super().__init__()
        self.sites = []
        self.users = []
    
    def load_system_data(self):
        """从NetBox系统读取现有数据"""
        self.log_info("正在读取系统数据...")
        
        # 读取站点
        self.sites = list(Site.objects.all())
        if not self.sites:
            self.log_failure("系统中没有站点数据，无法填充中断位置信息")
            return False
        
        # 读取用户（用于日志记录）
        User = get_user_model()
        self.users = list(User.objects.all())
        
        self.log_success(f"系统数据读取完成：站点({len(self.sites)})、用户({len(self.users)})")
        return True
    
    def get_faults_without_sites(self):
        """获取没有中断位置站点信息的故障记录"""
        self.log_info("正在扫描故障记录...")
        
        # 获取所有故障记录
        all_faults = OtnFault.objects.all()
        total_faults = all_faults.count()
        
        # 筛选没有中断位置站点信息的故障记录
        faults_without_sites = []
        for fault in all_faults:
            # 检查中断位置字段是否为空
            if not fault.interruption_location.exists():
                faults_without_sites.append(fault)
        
        self.log_info(f"扫描完成：共 {total_faults} 条故障记录，其中 {len(faults_without_sites)} 条缺少中断位置信息")
        return faults_without_sites
    
    def select_random_sites(self, fault):
        """为故障记录随机选择2-3个站点"""
        if not self.sites:
            return []
        
        # 随机选择2-3个站点
        num_sites = random.randint(2, min(3, len(self.sites)))
        selected_sites = random.sample(self.sites, num_sites)
        
        return selected_sites
    
    def update_fault_sites(self, fault, selected_sites, dry_run=True):
        """更新故障记录的中断位置站点信息"""
        try:
            if not dry_run:
                # 实际更新数据库
                fault.interruption_location.set(selected_sites)
                fault.save()
                return True, f"故障 {fault.fault_number} 已更新：添加了 {len(selected_sites)} 个中断位置"
            else:
                # 模拟运行，只记录日志
                return True, f"模拟：故障 {fault.fault_number} 将添加 {len(selected_sites)} 个中断位置"
        except Exception as e:
            return False, f"更新故障 {fault.fault_number} 时出错：{str(e)}"
    
    def run(self, data, commit):
        """脚本主入口"""
        # 读取脚本参数
        dry_run = data['dry_run']
        
        # 读取系统数据
        if not self.load_system_data():
            return "系统数据读取失败，请检查NetBox数据库"
        
        # 获取没有中断位置站点信息的故障记录
        faults_without_sites = self.get_faults_without_sites()
        
        if not faults_without_sites:
            return "所有故障记录都已包含中断位置信息，无需更新"
        
        # 统计信息
        total_to_update = len(faults_without_sites)
        successful_updates = 0
        failed_updates = 0
        
        self.log_info(f"开始为 {total_to_update} 条故障记录填充中断位置信息...")
        
        # 为每个故障记录填充站点信息
        for i, fault in enumerate(faults_without_sites):
            # 随机选择站点
            selected_sites = self.select_random_sites(fault)
            
            if not selected_sites:
                self.log_warning(f"故障 {fault.fault_number}：无法选择站点，系统中可能没有站点数据")
                failed_updates += 1
                continue
            
            # 更新故障记录
            is_success, message = self.update_fault_sites(fault, selected_sites, dry_run=(dry_run or not commit))
            
            if is_success:
                self.log_success(message)
                successful_updates += 1
            else:
                self.log_warning(message)
                failed_updates += 1
            
            # 进度反馈
            if (i + 1) % 50 == 0:
                self.log_info(f"已处理 {i + 1}/{total_to_update} 条故障记录...")
        
        # 统计信息
        result_message = (
            f"填充完成！\n"
            f"• 扫描故障记录：{len(faults_without_sites) + OtnFault.objects.filter(interruption_location__isnull=False).count()} 条\n"
            f"• 缺少中断位置的故障：{total_to_update} 条\n"
            f"• 成功填充：{successful_updates} 条\n"
            f"• 填充失败：{failed_updates} 条\n"
        )
        
        if dry_run or not commit:
            result_message += "\n注意：当前为模拟模式，数据未实际保存到数据库。\n"
            result_message += "如需实际保存，请取消勾选'模拟运行'选项并勾选'提交更改'选项。"
        else:
            result_message += "\n数据已成功保存到数据库。"
        
        return result_message
