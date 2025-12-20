"""
NetBox自定义脚本：调整故障时间分布

功能：
1. 将非"处理中"状态的故障数据的故障中断时间、故障恢复时间调整为2025-1-1至2025-12-5之间随机分布
2. 保持故障历时不变
3. 如果是光缆故障，同步调整处理派发时间、维修出发时间、到达现场时间（保持时间逻辑关系）
4. 如果是非光缆故障，清空光缆中断补充信息相关字段

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.adjust_fault_times
2. 选择脚本类：AdjustFaultTimes
3. 运行脚本
"""

import random
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from extras.scripts import Script, BooleanVar
from netbox_otnfaults.models import OtnFault, FaultStatusChoices, FaultCategoryChoices


class AdjustFaultTimes(Script):
    """
    调整故障时间分布的自定义脚本
    """
    
    class Meta:
        name = "调整故障时间分布"
        description = "将非处理中状态的故障时间调整到2025年1月1日至12月5日之间随机分布，保持故障历时不变"
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
        
        self.log_info("开始调整故障时间分布...")
        
        # 定义时间范围：2025-1-1 00:00:00 至 2025-12-5 23:59:59
        start_date = timezone.make_aware(datetime(2025, 1, 1, 0, 0, 0))
        end_date = timezone.make_aware(datetime(2025, 12, 5, 23, 59, 59))
        
        # 计算时间范围的总秒数
        time_range_seconds = int((end_date - start_date).total_seconds())
        
        self.log_info(f"目标时间范围: {start_date} 至 {end_date}")
        
        # 筛选非"处理中"状态的故障记录
        faults = list(OtnFault.objects.exclude(
            fault_status=FaultStatusChoices.PROCESSING
        ).order_by('fault_occurrence_time'))
        
        total = len(faults)
        self.log_info(f"找到 {total} 条非处理中状态的故障记录")
        
        if total == 0:
            self.log_warning("没有数据需要更新")
            return "没有找到符合条件的故障记录"
        
        update_list = []
        
        # 统计信息
        stats = {
            'fiber_updated': 0,        # 光缆故障更新数
            'non_fiber_updated': 0,    # 非光缆故障更新数
            'non_fiber_cleared': 0,    # 非光缆故障清空字段数
            'skipped_no_duration': 0,  # 跳过（无故障历时）
        }
        
        for fault in faults:
            # 检查是否有故障历时（需要有 fault_occurrence_time 和 fault_recovery_time）
            if not fault.fault_occurrence_time or not fault.fault_recovery_time:
                stats['skipped_no_duration'] += 1
                self.log_debug(f"跳过故障 {fault.fault_number}: 缺少故障时间或恢复时间")
                continue
            
            # 计算原始故障历时
            original_duration = fault.fault_recovery_time - fault.fault_occurrence_time
            original_duration_seconds = original_duration.total_seconds()
            
            # 生成新的故障中断时间（随机分布在时间范围内）
            # 需要确保新的恢复时间不超过结束日期
            max_offset = max(0, time_range_seconds - int(original_duration_seconds))
            if max_offset <= 0:
                # 如果故障历时超过整个时间范围，跳过
                stats['skipped_no_duration'] += 1
                self.log_warning(f"跳过故障 {fault.fault_number}: 故障历时 ({original_duration_seconds/3600:.2f}小时) 超过目标时间范围")
                continue
            
            random_offset = random.randint(0, max_offset)
            new_occurrence_time = start_date + timedelta(seconds=random_offset)
            new_recovery_time = new_occurrence_time + original_duration
            
            # 更新基本时间字段
            fault.fault_occurrence_time = new_occurrence_time
            fault.fault_recovery_time = new_recovery_time
            
            # 判断是否为光缆故障
            is_fiber_fault = (fault.fault_category == FaultCategoryChoices.CATEGORY_FIBER)
            
            if is_fiber_fault:
                # 光缆故障：同步调整处理派发时间、维修出发时间、到达现场时间
                self._adjust_fiber_fault_times(fault, new_occurrence_time, new_recovery_time, original_duration_seconds)
                stats['fiber_updated'] += 1
            else:
                # 非光缆故障：清空光缆中断补充信息相关字段
                self._clear_fiber_related_fields(fault)
                stats['non_fiber_updated'] += 1
                stats['non_fiber_cleared'] += 1
            
            update_list.append(fault)
            
            self.log_debug(
                f"故障 {fault.fault_number}: "
                f"原时间 {fault.fault_occurrence_time.strftime('%Y-%m-%d %H:%M')} -> "
                f"新时间 {new_occurrence_time.strftime('%Y-%m-%d %H:%M')}, "
                f"历时 {original_duration_seconds/3600:.2f}小时, "
                f"类型: {'光缆' if is_fiber_fault else '非光缆'}"
            )
        
        # 批量更新
        if update_list:
            self.log_info(f"准备更新 {len(update_list)} 条记录...")
            
            if dry_run:
                self.log_warning("预览模式：不会实际修改数据库")
            else:
                try:
                    with transaction.atomic():
                        # 更新所有相关字段
                        update_fields = [
                            'fault_occurrence_time',
                            'fault_recovery_time',
                            'dispatch_time',
                            'departure_time',
                            'arrival_time',
                            'cable_break_location',
                            'recovery_mode',
                            'resource_type',
                            'cable_route',
                        ]
                        OtnFault.objects.bulk_update(update_list, update_fields)
                    self.log_success(f"成功更新 {len(update_list)} 条记录！")
                except Exception as e:
                    self.log_failure(f"更新失败: {str(e)}")
                    raise
        else:
            self.log_info("所有记录已符合要求，无需更新")
        
        # 输出统计结果
        self.log_info("-" * 60)
        self.log_info("更新统计:")
        self.log_info(f"  光缆故障更新: {stats['fiber_updated']} 条")
        self.log_info(f"  非光缆故障更新: {stats['non_fiber_updated']} 条")
        self.log_info(f"  非光缆故障清空字段: {stats['non_fiber_cleared']} 条")
        self.log_info(f"  跳过（无有效历时）: {stats['skipped_no_duration']} 条")
        self.log_info("-" * 60)
        
        # 生成报告
        report_lines = []
        report_lines.append("# 故障时间调整报告\n")
        report_lines.append(f"**目标时间范围**: 2025-01-01 至 2025-12-05\n")
        report_lines.append(f"**符合条件总数**: {total}\n")
        report_lines.append(f"**实际更新数**: {len(update_list)}\n")
        report_lines.append(f"**预览模式**: {'是' if dry_run else '否'}\n")
        report_lines.append("\n## 更新分类\n")
        report_lines.append(f"- 光缆故障更新: {stats['fiber_updated']} 条")
        report_lines.append(f"- 非光缆故障更新: {stats['non_fiber_updated']} 条")
        report_lines.append(f"- 非光缆故障清空光缆字段: {stats['non_fiber_cleared']} 条")
        report_lines.append(f"- 跳过（无有效历时）: {stats['skipped_no_duration']} 条")
        
        return "\n".join(report_lines)
    
    def _adjust_fiber_fault_times(self, fault, new_occurrence_time, new_recovery_time, original_duration_seconds):
        """
        调整光缆故障的时间字段
        
        时间逻辑关系：
        fault_occurrence_time < dispatch_time < departure_time < arrival_time < fault_recovery_time
        
        按照比例在故障历时内分配这些时间点
        """
        if original_duration_seconds <= 0:
            # 如果历时为0或负数，清空这些字段
            fault.dispatch_time = None
            fault.departure_time = None
            fault.arrival_time = None
            return
        
        # 定义各阶段在总历时中的典型比例
        # 假设：派发(5-15%)、出发(15-30%)、到达(30-60%)，剩余时间为修复
        # 使用随机比例，确保逻辑顺序
        
        # 生成随机比例点（确保递增）
        dispatch_ratio = random.uniform(0.05, 0.15)
        departure_ratio = random.uniform(dispatch_ratio + 0.05, min(dispatch_ratio + 0.20, 0.40))
        arrival_ratio = random.uniform(departure_ratio + 0.05, min(departure_ratio + 0.30, 0.80))
        
        # 计算各时间点
        dispatch_offset = timedelta(seconds=original_duration_seconds * dispatch_ratio)
        departure_offset = timedelta(seconds=original_duration_seconds * departure_ratio)
        arrival_offset = timedelta(seconds=original_duration_seconds * arrival_ratio)
        
        fault.dispatch_time = new_occurrence_time + dispatch_offset
        fault.departure_time = new_occurrence_time + departure_offset
        fault.arrival_time = new_occurrence_time + arrival_offset
    
    def _clear_fiber_related_fields(self, fault):
        """
        清空非光缆故障的光缆中断补充信息相关字段
        
        需要清空的字段：
        - cable_break_location (光缆中断部位)
        - recovery_mode (恢复方式)
        - resource_type (资源类型)
        - cable_route (光缆路由属性)
        - dispatch_time (处理派发时间)
        - departure_time (维修出发时间)
        - arrival_time (到达现场时间)
        """
        fault.cable_break_location = None
        fault.recovery_mode = None
        fault.resource_type = None
        fault.cable_route = None
        fault.dispatch_time = None
        fault.departure_time = None
        fault.arrival_time = None
