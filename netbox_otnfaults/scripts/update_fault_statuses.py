"""
NetBox自定义脚本：批量更新故障处理状态

功能：
1. 将所有故障的处理状态修改为"关闭"
2. 随机选择约10%的数据修改为"临时恢复"
3. 随机选择约1%的数据修改为"挂起"
4. 将最近的10条数据修改为"处理中"

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.update_fault_statuses
2. 选择脚本类：UpdateFaultStatuses
3. 运行脚本
"""

import random
from django.db import transaction
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFault


class UpdateFaultStatuses(Script):
    """
    批量更新故障处理状态的自定义脚本
    """
    
    class Meta:
        name = "批量更新故障处理状态"
        description = "将所有故障状态修改为关闭，随机选择10%为临时恢复，1%为挂起，最近10条为处理中"
        commit_default = True
    
    # 脚本参数
    dry_run = BooleanVar(
        label="预览模式",
        description="仅预览更新结果，不实际修改数据库",
        default=False
    )
    
    def run(self, data, commit):
        """脚本主入口"""
        dry_run = data['dry_run']
        
        self.log_info("开始更新故障状态...")
        
        # 获取所有故障记录，按中断时间倒序排列（最近的在前）
        faults = list(OtnFault.objects.all().order_by('-fault_occurrence_time'))
        total = len(faults)
        self.log_info(f"找到 {total} 条故障记录")
        
        if total == 0:
            self.log_warning("没有数据需要更新")
            return "没有找到任何故障记录"

        update_list = []
        
        stats = {
            'processing': 0,
            'temporary_recovery': 0,
            'suspended': 0,
            'closed': 0
        }

        for index, fault in enumerate(faults):
            original_status = fault.fault_status
            new_status = 'closed'  # 默认为关闭
            
            # 最近的10条修改为处理中
            if index < 10:
                new_status = 'processing'
            else:
                # 生成 0.0 到 1.0 之间的随机数
                r = random.random()
                
                # 约 1% 的概率挂起
                if r < 0.01:
                    new_status = 'suspended'
                # 约 10% 的概率临时恢复 (0.01 到 0.11 之间区间为 0.10)
                elif r < 0.11: 
                    new_status = 'temporary_recovery'
                # 其余为关闭
                else:
                    new_status = 'closed'
                    
            # 统计
            stats[new_status] += 1
            
            # 如果状态有变化，加入更新列表
            if fault.fault_status != new_status:
                fault.fault_status = new_status
                update_list.append(fault)
                self.log_debug(f"故障 {fault.fault_number}: {original_status} -> {new_status}")

        # 批量更新
        if update_list:
            self.log_info(f"准备更新 {len(update_list)} 条记录...")
            
            if dry_run:
                self.log_warning("预览模式：不会实际修改数据库")
            else:
                try:
                    with transaction.atomic():
                        OtnFault.objects.bulk_update(update_list, ['fault_status'])
                    self.log_success(f"成功更新 {len(update_list)} 条记录！")
                except Exception as e:
                    self.log_failure(f"更新失败: {str(e)}")
                    raise
        else:
            self.log_info("所有记录状态已符合要求，无需更新")

        # 输出统计结果
        self.log_info("-" * 60)
        self.log_info("更新后状态统计:")
        self.log_info(f"  处理中 (processing): {stats['processing']} 条 (含最近10条)")
        self.log_info(f"  临时恢复 (temporary_recovery): {stats['temporary_recovery']} 条")
        self.log_info(f"  挂起 (suspended): {stats['suspended']} 条")
        self.log_info(f"  关闭 (closed): {stats['closed']} 条")
        self.log_info("-" * 60)
        
        # 生成报告
        report_lines = []
        report_lines.append("# 故障状态更新报告\n")
        report_lines.append(f"**总记录数**: {total}\n")
        report_lines.append(f"**更新记录数**: {len(update_list)}\n")
        report_lines.append(f"**预览模式**: {'是' if dry_run else '否'}\n")
        report_lines.append("\n## 状态分布\n")
        report_lines.append(f"- 处理中: {stats['processing']} 条")
        report_lines.append(f"- 临时恢复: {stats['temporary_recovery']} 条")
        report_lines.append(f"- 挂起: {stats['suspended']} 条")
        report_lines.append(f"- 关闭: {stats['closed']} 条")
        
        return "\n".join(report_lines)
