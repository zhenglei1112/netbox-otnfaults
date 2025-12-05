"""
NetBox自定义脚本：上周故障统计报告

功能：
1. 统计上一周（周日为起始日，周六为终止日）的故障情况
2. 筛选故障发生时间在上一周内的所有故障记录
3. 分离已恢复和未恢复的故障，单独列出未恢复故障编号
4. 统计以下指标：故障总数量、故障总历时、平均故障历时
5. 按多个维度分组统计：省份、故障分类、中断原因、第一报障来源、计划内、资源类型、光缆路由属性
6. 按故障涉及业务分组统计：故障数量、总历时
7. 结果以Markdown形式输出表格

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.weekly_fault_report
2. 选择脚本类：WeeklyFaultReport
3. 配置参数（可选）
4. 运行脚本
"""

import datetime
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from dcim.models import Region
from tenancy.models import Tenant
from extras.scripts import Script, DateVar, BooleanVar, ChoiceVar
from netbox_otnfaults.models import OtnFault, OtnFaultImpact, FaultCategoryChoices


class WeeklyFaultReport(Script):
    """
    上周故障统计报告的自定义脚本
    """
    
    class Meta:
        name = "上周故障统计报告"
        description = "统计上一周（周日到周六）的故障情况，按多个维度分组统计"
        commit_default = False
    
    # 脚本参数
    report_date = DateVar(
        label="统计基准日期",
        description="用于计算上一周范围的基准日期（默认为今天）",
        required=False
    )
    
    include_unresolved = BooleanVar(
        label="包含未恢复故障",
        description="是否在统计中包含未恢复故障的历时（默认：否，只单独列出）",
        default=False
    )
    
    output_format = ChoiceVar(
        label="输出格式",
        description="统计结果的输出格式",
        choices=[
            ('markdown', 'Markdown表格'),
            ('text', '纯文本'),
        ],
        default='markdown'
    )
    
    def __init__(self):
        super().__init__()
        
        # 字段显示名称映射
        self.field_display_names = {
            # 故障分类
            'power': '电力故障',
            'fiber': '光缆故障',
            'pigtail': '尾纤故障',
            'device': '设备故障',
            'other': '其他故障',
            
            # 中断原因
            'road_construction': '道路施工',
            'sabotage': '人为破坏',
            'line_rectification': '线路整改',
            'misoperation': '误操作',
            'power_supply': '供电故障',
            'municipal_construction': '市政施工',
            'rodent_damage': '鼠害',
            'natural_disaster': '自然灾害',
            
            # 第一报障来源
            'national_backbone': '国干网网管',
            'future_network': '未来网络网管',
            'customer_support': '客户保障',
            'other': '其他',
            
            # 计划内
            True: '是',
            False: '否',
            
            # 资源类型
            'self_built': '自建光缆',
            'coordinated': '协调资源',
            'leased': '租赁纤芯',
            
            # 光缆路由属性
            'highway': '高速公路',
            'non_highway': '非高速',
        }
    
    def calculate_last_week_range(self, base_date):
        """计算上一周的日期范围（周日到周六）"""
        # 计算基准日期是星期几（0=周一，6=周日）
        weekday = base_date.weekday()
        
        # 计算上周六的日期（基准日期往前推(weekday+1)天）
        days_to_last_saturday = weekday + 1
        last_saturday = base_date - datetime.timedelta(days=days_to_last_saturday)
        
        # 计算上周日的日期（上周六往前推6天）
        last_sunday = last_saturday - datetime.timedelta(days=6)
        
        # 设置时间范围（周日00:00:00到周六23:59:59）
        last_week_start = datetime.datetime.combine(last_sunday, datetime.time.min)
        last_week_end = datetime.datetime.combine(last_saturday, datetime.time.max)
        
        return last_week_start, last_week_end

    def calculate_last_month_range(self, base_date):
        """计算上个月的日期范围"""
        # 获取本月第一天
        this_month_start = base_date.replace(day=1)
        
        # 获取上个月最后一天
        last_month_end_date = this_month_start - datetime.timedelta(days=1)
        
        # 获取上个月第一天
        last_month_start_date = last_month_end_date.replace(day=1)
        
        # 设置时间范围
        last_month_start = datetime.datetime.combine(last_month_start_date, datetime.time.min)
        last_month_end = datetime.datetime.combine(last_month_end_date, datetime.time.max)
        
        return last_month_start, last_month_end
    
    def query_faults(self, start_time, end_time):
        """查询时间范围内的故障记录"""
        self.log_info(f"正在查询 {start_time.date()} 至 {end_time.date()} 期间的故障记录...")
        
        # 查询故障发生时间在指定范围内的所有故障记录
        faults = OtnFault.objects.filter(
            fault_occurrence_time__gte=start_time,
            fault_occurrence_time__lte=end_time
        ).select_related('province').prefetch_related('impacts')
        
        all_faults = list(faults)
        
        # 分离已恢复和未恢复的故障
        unresolved_faults = [f for f in all_faults if not f.fault_recovery_time]
        resolved_faults = [f for f in all_faults if f.fault_recovery_time]
        
        self.log_success(f"查询完成：共 {len(all_faults)} 条故障记录")
        self.log_info(f"• 已恢复故障：{len(resolved_faults)} 条")
        self.log_info(f"• 未恢复故障：{len(unresolved_faults)} 条")
        
        return all_faults, resolved_faults, unresolved_faults
    
    def calculate_fault_duration_hours(self, fault):
        """计算故障历时（小时）"""
        if fault.fault_occurrence_time and fault.fault_recovery_time:
            duration = fault.fault_recovery_time - fault.fault_occurrence_time
            total_hours = duration.total_seconds() / 3600
            return Decimal(str(round(total_hours, 2)))
        return Decimal('0.00')
    
    def get_field_display_name(self, value):
        """获取字段的显示名称"""
        if value is None:
            return "未设置"
        return self.field_display_names.get(value, str(value))
    
    def calculate_overall_statistics(self, all_faults, resolved_faults, unresolved_faults):
        """计算总体统计信息"""
        total_faults = len(all_faults)
        
        # 计算总历时（根据参数决定是否包含未恢复故障）
        if self.include_unresolved:
            faults_for_duration = all_faults
        else:
            faults_for_duration = resolved_faults
        
        total_duration = Decimal('0.00')
        for fault in faults_for_duration:
            total_duration += self.calculate_fault_duration_hours(fault)
        
        # 计算平均历时
        avg_duration = Decimal('0.00')
        if len(faults_for_duration) > 0:
            avg_duration = total_duration / len(faults_for_duration)
        
        return {
            'total_faults': total_faults,
            'total_duration': total_duration,
            'avg_duration': avg_duration,
            'resolved_faults': len(resolved_faults),
            'unresolved_faults': len(unresolved_faults),
        }
    
    def group_statistics_by_field(self, resolved_faults, field_getter):
        """按指定字段分组统计"""
        groups = {}
        
        for fault in resolved_faults:
            # 获取字段值
            field_value = field_getter(fault)
            
            # 获取显示名称
            display_name = self.get_field_display_name(field_value)
            
            # 初始化分组
            if display_name not in groups:
                groups[display_name] = {
                    'count': 0,
                    'total_duration': Decimal('0.00'),
                }
            
            # 累加统计
            groups[display_name]['count'] += 1
            groups[display_name]['total_duration'] += self.calculate_fault_duration_hours(fault)
        
        # 计算平均历时
        for group_name, stats in groups.items():
            if stats['count'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['count']
            else:
                stats['avg_duration'] = Decimal('0.00')
        
        return groups
    
    def group_statistics_by_province(self, resolved_faults):
        """按省份分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.province.name if fault.province else None
        )
    
    def group_statistics_by_category(self, resolved_faults):
        """按故障分类分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.fault_category
        )
    
    def group_statistics_by_reason(self, resolved_faults):
        """按中断原因分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.interruption_reason
        )
    
    def group_statistics_by_report_source(self, resolved_faults):
        """按第一报障来源分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.first_report_source
        )
    
    def group_statistics_by_planned(self, resolved_faults):
        """按计划内分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.planned
        )
    
    def group_statistics_by_resource_type(self, resolved_faults):
        """按资源类型分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.resource_type
        )
    
    def group_statistics_by_cable_route(self, resolved_faults):
        """按光缆路由属性分组统计"""
        return self.group_statistics_by_field(
            resolved_faults,
            lambda fault: fault.cable_route
        )
    
    def group_statistics_by_service(self, resolved_faults, period_duration_hours=None):
        """按涉及业务分组统计"""
        service_groups = {}
        
        # 遍历所有故障记录
        for fault in resolved_faults:
            # 获取故障历时
            fault_duration = self.calculate_fault_duration_hours(fault)
            
            # 遍历故障影响的业务
            for impact in fault.impacts.all():
                service_name = impact.impacted_service.name if impact.impacted_service else "未知业务"
                
                # 初始化业务分组
                if service_name not in service_groups:
                    service_groups[service_name] = {
                        'count': 0,
                        'total_duration': Decimal('0.00'),
                    }
                
                # 计算业务中断时长
                # 优先使用业务恢复时间 - 业务中断时间
                if impact.service_recovery_time and impact.service_interruption_time:
                    service_duration_seconds = (impact.service_recovery_time - impact.service_interruption_time).total_seconds()
                    service_duration = Decimal(str(round(service_duration_seconds / 3600, 2)))
                else:
                    # 如果未设置业务时间，回退到故障历时
                    service_duration = fault_duration
                
                # 累加统计（每个故障对每个业务只计一次）
                service_groups[service_name]['count'] += 1
                service_groups[service_name]['total_duration'] += service_duration
        
        # 计算 SLA
        if period_duration_hours:
            for service_name, stats in service_groups.items():
                total_duration = stats['total_duration']
                # SLA = 1 - (中断时长 / 总时长)
                if period_duration_hours > 0:
                    sla = (Decimal('1') - (total_duration / Decimal(str(period_duration_hours)))) * 100
                    # 确保 SLA 不小于 0
                    stats['sla'] = max(Decimal('0.00'), sla)
                else:
                    stats['sla'] = Decimal('0.00')
        
        return service_groups

    def calculate_stats_for_period(self, start_time, end_time):
        """计算指定时间段内的所有统计信息"""
        # 计算周期总时长（小时）
        period_duration = end_time - start_time
        period_duration_hours = period_duration.total_seconds() / 3600
        
        # 查询数据
        all_faults, resolved_faults, unresolved_faults = self.query_faults(start_time, end_time)
        
        if not all_faults:
            return None
            
        # 计算统计信息
        stats = {
            'period_start': start_time,
            'period_end': end_time,
            'overall': self.calculate_overall_statistics(all_faults, resolved_faults, unresolved_faults),
            'by_province': self.group_statistics_by_province(resolved_faults),
            'by_category': self.group_statistics_by_category(resolved_faults),
            'by_reason': self.group_statistics_by_reason(resolved_faults),
            'by_report_source': self.group_statistics_by_report_source(resolved_faults),
            'by_planned': self.group_statistics_by_planned(resolved_faults),
            'by_resource_type': self.group_statistics_by_resource_type(resolved_faults),
            'by_cable_route': self.group_statistics_by_cable_route(resolved_faults),
            'by_service': self.group_statistics_by_service(resolved_faults, period_duration_hours),
            'unresolved_faults': unresolved_faults
        }
        
        return stats
    
    def generate_markdown_table(self, title, headers, rows):
        """生成Markdown表格"""
        table = f"### {title}\n\n"
        table += "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        for row in rows:
            table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        
        return table + "\n"
    
    def generate_markdown_report_section(self, title, stats):
        """生成Markdown格式的报告章节"""
        report = f"## {title}（{stats['period_start'].date()} 至 {stats['period_end'].date()}）\n\n"
        
        # 总体统计
        overall = stats['overall']
        report += self.generate_markdown_table(
            "总体统计",
            ["指标", "数值"],
            [
                ["故障总数", overall['total_faults']],
                ["已恢复故障", overall['resolved_faults']],
                ["未恢复故障", overall['unresolved_faults']],
                ["故障总历时", f"{overall['total_duration']:.2f}小时"],
                ["平均故障历时", f"{overall['avg_duration']:.2f}小时"],
            ]
        )
        
        # 未恢复故障列表
        if stats['unresolved_faults']:
            report += "### 未恢复故障列表\n\n"
            for fault in stats['unresolved_faults']:
                report += f"- {fault.fault_number}\n"
            report += "\n"
        
        # 按省份统计
        if stats['by_province']:
            rows = []
            for province_name, province_stats in sorted(stats['by_province'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    province_name,
                    province_stats['count'],
                    f"{province_stats['total_duration']:.2f}",
                    f"{province_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按省份统计",
                ["省份", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按故障分类统计
        if stats['by_category']:
            rows = []
            for category_name, category_stats in sorted(stats['by_category'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    category_name,
                    category_stats['count'],
                    f"{category_stats['total_duration']:.2f}",
                    f"{category_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按故障分类统计",
                ["分类", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按中断原因统计
        if stats['by_reason']:
            rows = []
            for reason_name, reason_stats in sorted(stats['by_reason'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    reason_name,
                    reason_stats['count'],
                    f"{reason_stats['total_duration']:.2f}",
                    f"{reason_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按中断原因统计",
                ["中断原因", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按第一报障来源统计
        if stats['by_report_source']:
            rows = []
            for source_name, source_stats in sorted(stats['by_report_source'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    source_name,
                    source_stats['count'],
                    f"{source_stats['total_duration']:.2f}",
                    f"{source_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按第一报障来源统计",
                ["报障来源", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按计划内统计
        if stats['by_planned']:
            rows = []
            for planned_name, planned_stats in sorted(stats['by_planned'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    planned_name,
                    planned_stats['count'],
                    f"{planned_stats['total_duration']:.2f}",
                    f"{planned_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按计划内统计",
                ["计划内", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按资源类型统计
        if stats['by_resource_type']:
            rows = []
            for resource_name, resource_stats in sorted(stats['by_resource_type'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    resource_name,
                    resource_stats['count'],
                    f"{resource_stats['total_duration']:.2f}",
                    f"{resource_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按资源类型统计",
                ["资源类型", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按光缆路由属性统计
        if stats['by_cable_route']:
            rows = []
            for route_name, route_stats in sorted(stats['by_cable_route'].items(), key=lambda x: x[1]['count'], reverse=True):
                rows.append([
                    route_name,
                    route_stats['count'],
                    f"{route_stats['total_duration']:.2f}",
                    f"{route_stats['avg_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按光缆路由属性统计",
                ["光缆路由", "故障数量", "总历时(小时)", "平均历时(小时)"],
                rows
            )
        
        # 按涉及业务统计
        if stats['by_service']:
            rows = []
            headers = ["业务名称", "故障数量", "总历时(小时)"]
            
            # 检查是否有 SLA 数据
            has_sla = any('sla' in s for s in stats['by_service'].values())
            if has_sla:
                headers.append("SLA (%)")
            
            for service_name, service_stats in sorted(stats['by_service'].items(), key=lambda x: x[1]['count'], reverse=True):
                row = [
                    service_name,
                    service_stats['count'],
                    f"{service_stats['total_duration']:.2f}",
                ]
                if has_sla:
                    sla_value = service_stats.get('sla')
                    row.append(f"{sla_value:.4f}" if sla_value is not None else "-")
                rows.append(row)
                
            report += self.generate_markdown_table(
                "按涉及业务统计",
                headers,
                rows
            )
        
        return report
    
    def run(self, data, commit):
        """脚本主入口"""
        # 获取统计基准日期
        report_date = data.get('report_date')
        if report_date:
            base_date = report_date
        else:
            base_date = timezone.now().date()
        
        # 获取脚本参数
        self.include_unresolved = data['include_unresolved']
        output_format = data['output_format']
        
        report_parts = []
        report_parts.append(f"# 故障统计报告")
        report_parts.append(f"统计基准日期：{base_date}\n")
        
        # 1. 计算上一周统计
        last_week_start, last_week_end = self.calculate_last_week_range(base_date)
        self.log_info(f"正在计算上周统计（{last_week_start.date()} 至 {last_week_end.date()}）...")
        
        week_stats = self.calculate_stats_for_period(last_week_start, last_week_end)
        
        if week_stats:
            if output_format == 'markdown':
                report_parts.append(self.generate_markdown_report_section("上周统计", week_stats))
            else:
                report_parts.append(self.generate_text_report_section("上周统计", week_stats))
        else:
            msg = f"上周（{last_week_start.date()} 至 {last_week_end.date()}）没有故障记录"
            self.log_warning(msg)
            report_parts.append(f"## 上周统计\n\n{msg}\n")

        # 2. 计算上个月统计
        last_month_start, last_month_end = self.calculate_last_month_range(base_date)
        self.log_info(f"正在计算上月统计（{last_month_start.date()} 至 {last_month_end.date()}）...")
        
        month_stats = self.calculate_stats_for_period(last_month_start, last_month_end)
        
        if month_stats:
            if output_format == 'markdown':
                report_parts.append(self.generate_markdown_report_section("上月统计", month_stats))
            else:
                report_parts.append(self.generate_text_report_section("上月统计", month_stats))
        else:
            msg = f"上月（{last_month_start.date()} 至 {last_month_end.date()}）没有故障记录"
            self.log_warning(msg)
            report_parts.append(f"## 上月统计\n\n{msg}\n")
            
        return "\n".join(report_parts)
    
    def generate_text_report_section(self, title, stats):
        """生成纯文本格式的报告章节"""
        overall = stats['overall']
        
        report_lines = []
        report_lines.append(f"{title}（{stats['period_start'].date()} 至 {stats['period_end'].date()}）")
        report_lines.append("-" * 60)
        report_lines.append("")
        
        # 总体统计
        report_lines.append("总体统计：")
        report_lines.append(f"  故障总数：{overall['total_faults']}")
        report_lines.append(f"  已恢复故障：{overall['resolved_faults']}")
        report_lines.append(f"  未恢复故障：{overall['unresolved_faults']}")
        report_lines.append(f"  故障总历时：{overall['total_duration']:.2f}小时")
        report_lines.append(f"  平均故障历时：{overall['avg_duration']:.2f}小时")
        report_lines.append("")
        
        # 未恢复故障列表
        if stats['unresolved_faults']:
            report_lines.append("未恢复故障列表：")
            for fault in stats['unresolved_faults']:
                report_lines.append(f"  - {fault.fault_number}")
            report_lines.append("")
        
        # 按省份统计
        if stats['by_province']:
            report_lines.append("按省份统计：")
            for province_name, province_stats in sorted(stats['by_province'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {province_name}: {province_stats['count']}次, "
                                  f"总历时{province_stats['total_duration']:.2f}小时, "
                                  f"平均{province_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按故障分类统计
        if stats['by_category']:
            report_lines.append("按故障分类统计：")
            for category_name, category_stats in sorted(stats['by_category'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {category_name}: {category_stats['count']}次, "
                                  f"总历时{category_stats['total_duration']:.2f}小时, "
                                  f"平均{category_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按中断原因统计
        if stats['by_reason']:
            report_lines.append("按中断原因统计：")
            for reason_name, reason_stats in sorted(stats['by_reason'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {reason_name}: {reason_stats['count']}次, "
                                  f"总历时{reason_stats['total_duration']:.2f}小时, "
                                  f"平均{reason_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按第一报障来源统计
        if stats['by_report_source']:
            report_lines.append("按第一报障来源统计：")
            for source_name, source_stats in sorted(stats['by_report_source'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {source_name}: {source_stats['count']}次, "
                                  f"总历时{source_stats['total_duration']:.2f}小时, "
                                  f"平均{source_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按计划内统计
        if stats['by_planned']:
            report_lines.append("按计划内统计：")
            for planned_name, planned_stats in sorted(stats['by_planned'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {planned_name}: {planned_stats['count']}次, "
                                  f"总历时{planned_stats['total_duration']:.2f}小时, "
                                  f"平均{planned_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按资源类型统计
        if stats['by_resource_type']:
            report_lines.append("按资源类型统计：")
            for resource_name, resource_stats in sorted(stats['by_resource_type'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {resource_name}: {resource_stats['count']}次, "
                                  f"总历时{resource_stats['total_duration']:.2f}小时, "
                                  f"平均{resource_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按光缆路由属性统计
        if stats['by_cable_route']:
            report_lines.append("按光缆路由属性统计：")
            for route_name, route_stats in sorted(stats['by_cable_route'].items(), key=lambda x: x[1]['count'], reverse=True):
                report_lines.append(f"  {route_name}: {route_stats['count']}次, "
                                  f"总历时{route_stats['total_duration']:.2f}小时, "
                                  f"平均{route_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按涉及业务统计
        if stats['by_service']:
            report_lines.append("按涉及业务统计：")
            for service_name, service_stats in sorted(stats['by_service'].items(), key=lambda x: x[1]['count'], reverse=True):
                line = f"  {service_name}: {service_stats['count']}次, 总历时{service_stats['total_duration']:.2f}小时"
                if 'sla' in service_stats:
                    line += f", SLA {service_stats['sla']:.4f}%"
                report_lines.append(line)
            report_lines.append("")
        
        return "\n".join(report_lines)
