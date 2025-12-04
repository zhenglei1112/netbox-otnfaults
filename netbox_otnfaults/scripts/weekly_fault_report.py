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
        self.last_week_start = None
        self.last_week_end = None
        self.faults_in_period = []
        self.unresolved_faults = []
        self.resolved_faults = []
        
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
    
    def get_faults_in_period(self):
        """获取时间范围内的故障记录"""
        self.log_info(f"正在查询 {self.last_week_start.date()} 至 {self.last_week_end.date()} 期间的故障记录...")
        
        # 查询故障发生时间在上一周内的所有故障记录
        faults = OtnFault.objects.filter(
            fault_occurrence_time__gte=self.last_week_start,
            fault_occurrence_time__lte=self.last_week_end
        ).select_related('province').prefetch_related('impacts')
        
        self.faults_in_period = list(faults)
        
        # 分离已恢复和未恢复的故障
        self.unresolved_faults = [f for f in self.faults_in_period if not f.fault_recovery_time]
        self.resolved_faults = [f for f in self.faults_in_period if f.fault_recovery_time]
        
        self.log_success(f"查询完成：共 {len(self.faults_in_period)} 条故障记录")
        self.log_info(f"• 已恢复故障：{len(self.resolved_faults)} 条")
        self.log_info(f"• 未恢复故障：{len(self.unresolved_faults)} 条")
    
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
    
    def calculate_overall_statistics(self):
        """计算总体统计信息"""
        total_faults = len(self.faults_in_period)
        
        # 计算总历时（根据参数决定是否包含未恢复故障）
        if self.include_unresolved:
            faults_for_duration = self.faults_in_period
        else:
            faults_for_duration = self.resolved_faults
        
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
            'resolved_faults': len(self.resolved_faults),
            'unresolved_faults': len(self.unresolved_faults),
        }
    
    def group_statistics_by_field(self, field_name, field_getter):
        """按指定字段分组统计"""
        groups = {}
        
        for fault in self.resolved_faults:
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
    
    def group_statistics_by_province(self):
        """按省份分组统计"""
        return self.group_statistics_by_field(
            'province',
            lambda fault: fault.province.name if fault.province else None
        )
    
    def group_statistics_by_category(self):
        """按故障分类分组统计"""
        return self.group_statistics_by_field(
            'fault_category',
            lambda fault: fault.fault_category
        )
    
    def group_statistics_by_reason(self):
        """按中断原因分组统计"""
        return self.group_statistics_by_field(
            'interruption_reason',
            lambda fault: fault.interruption_reason
        )
    
    def group_statistics_by_report_source(self):
        """按第一报障来源分组统计"""
        return self.group_statistics_by_field(
            'first_report_source',
            lambda fault: fault.first_report_source
        )
    
    def group_statistics_by_planned(self):
        """按计划内分组统计"""
        return self.group_statistics_by_field(
            'planned',
            lambda fault: fault.planned
        )
    
    def group_statistics_by_resource_type(self):
        """按资源类型分组统计"""
        return self.group_statistics_by_field(
            'resource_type',
            lambda fault: fault.resource_type
        )
    
    def group_statistics_by_cable_route(self):
        """按光缆路由属性分组统计"""
        return self.group_statistics_by_field(
            'cable_route',
            lambda fault: fault.cable_route
        )
    
    def group_statistics_by_service(self):
        """按涉及业务分组统计"""
        service_groups = {}
        
        # 遍历所有故障记录
        for fault in self.resolved_faults:
            # 获取故障历时
            duration = self.calculate_fault_duration_hours(fault)
            
            # 遍历故障影响的业务
            for impact in fault.impacts.all():
                service_name = impact.impacted_service.name if impact.impacted_service else "未知业务"
                
                # 初始化业务分组
                if service_name not in service_groups:
                    service_groups[service_name] = {
                        'count': 0,
                        'total_duration': Decimal('0.00'),
                    }
                
                # 累加统计（每个故障对每个业务只计一次）
                service_groups[service_name]['count'] += 1
                service_groups[service_name]['total_duration'] += duration
        
        return service_groups
    
    def generate_markdown_table(self, title, headers, rows):
        """生成Markdown表格"""
        table = f"## {title}\n\n"
        table += "| " + " | ".join(headers) + " |\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        for row in rows:
            table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        
        return table + "\n"
    
    def generate_markdown_report(self, stats):
        """生成Markdown格式的报告"""
        report = f"# 上周故障统计报告（{self.last_week_start.date()} 至 {self.last_week_end.date()}）\n\n"
        
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
        if self.unresolved_faults:
            report += "## 未恢复故障列表\n\n"
            for fault in self.unresolved_faults:
                report += f"- {fault.fault_number}\n"
            report += "\n"
        
        # 按省份统计
        if stats['by_province']:
            rows = []
            for province_name, province_stats in sorted(stats['by_province'].items()):
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
            for category_name, category_stats in sorted(stats['by_category'].items()):
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
            for reason_name, reason_stats in sorted(stats['by_reason'].items()):
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
            for source_name, source_stats in sorted(stats['by_report_source'].items()):
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
            for planned_name, planned_stats in sorted(stats['by_planned'].items()):
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
            for resource_name, resource_stats in sorted(stats['by_resource_type'].items()):
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
            for route_name, route_stats in sorted(stats['by_cable_route'].items()):
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
            for service_name, service_stats in sorted(stats['by_service'].items()):
                rows.append([
                    service_name,
                    service_stats['count'],
                    f"{service_stats['total_duration']:.2f}",
                ])
            report += self.generate_markdown_table(
                "按涉及业务统计",
                ["业务名称", "故障数量", "总历时(小时)"],
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
        
        # 计算上一周日期范围
        self.last_week_start, self.last_week_end = self.calculate_last_week_range(base_date)
        self.log_info(f"统计时间范围：{self.last_week_start.date()}（周日）至 {self.last_week_end.date()}（周六）")
        
        # 获取时间范围内的故障记录
        self.get_faults_in_period()
        
        if not self.faults_in_period:
            return f"在 {self.last_week_start.date()} 至 {self.last_week_end.date()} 期间没有故障记录"
        
        # 获取脚本参数
        self.include_unresolved = data['include_unresolved']
        output_format = data['output_format']
        
        # 计算所有统计信息
        self.log_info("正在计算统计信息...")
        
        stats = {
            'overall': self.calculate_overall_statistics(),
            'by_province': self.group_statistics_by_province(),
            'by_category': self.group_statistics_by_category(),
            'by_reason': self.group_statistics_by_reason(),
            'by_report_source': self.group_statistics_by_report_source(),
            'by_planned': self.group_statistics_by_planned(),
            'by_resource_type': self.group_statistics_by_resource_type(),
            'by_cable_route': self.group_statistics_by_cable_route(),
            'by_service': self.group_statistics_by_service(),
        }
        
        self.log_success("统计信息计算完成")
        
        # 生成报告
        if output_format == 'markdown':
            report = self.generate_markdown_report(stats)
        else:
            # 纯文本格式（简化版）
            report = self.generate_text_report(stats)
        
        return report
    
    def generate_text_report(self, stats):
        """生成纯文本格式的报告"""
        overall = stats['overall']
        
        report_lines = []
        report_lines.append(f"上周故障统计报告（{self.last_week_start.date()} 至 {self.last_week_end.date()}）")
        report_lines.append("=" * 60)
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
        if self.unresolved_faults:
            report_lines.append("未恢复故障列表：")
            for fault in self.unresolved_faults:
                report_lines.append(f"  - {fault.fault_number}")
            report_lines.append("")
        
        # 按省份统计
        if stats['by_province']:
            report_lines.append("按省份统计：")
            for province_name, province_stats in sorted(stats['by_province'].items()):
                report_lines.append(f"  {province_name}: {province_stats['count']}次, "
                                  f"总历时{province_stats['total_duration']:.2f}小时, "
                                  f"平均{province_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按故障分类统计
        if stats['by_category']:
            report_lines.append("按故障分类统计：")
            for category_name, category_stats in sorted(stats['by_category'].items()):
                report_lines.append(f"  {category_name}: {category_stats['count']}次, "
                                  f"总历时{category_stats['total_duration']:.2f}小时, "
                                  f"平均{category_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按中断原因统计
        if stats['by_reason']:
            report_lines.append("按中断原因统计：")
            for reason_name, reason_stats in sorted(stats['by_reason'].items()):
                report_lines.append(f"  {reason_name}: {reason_stats['count']}次, "
                                  f"总历时{reason_stats['total_duration']:.2f}小时, "
                                  f"平均{reason_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按第一报障来源统计
        if stats['by_report_source']:
            report_lines.append("按第一报障来源统计：")
            for source_name, source_stats in sorted(stats['by_report_source'].items()):
                report_lines.append(f"  {source_name}: {source_stats['count']}次, "
                                  f"总历时{source_stats['total_duration']:.2f}小时, "
                                  f"平均{source_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按计划内统计
        if stats['by_planned']:
            report_lines.append("按计划内统计：")
            for planned_name, planned_stats in sorted(stats['by_planned'].items()):
                report_lines.append(f"  {planned_name}: {planned_stats['count']}次, "
                                  f"总历时{planned_stats['total_duration']:.2f}小时, "
                                  f"平均{planned_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按资源类型统计
        if stats['by_resource_type']:
            report_lines.append("按资源类型统计：")
            for resource_name, resource_stats in sorted(stats['by_resource_type'].items()):
                report_lines.append(f"  {resource_name}: {resource_stats['count']}次, "
                                  f"总历时{resource_stats['total_duration']:.2f}小时, "
                                  f"平均{resource_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按光缆路由属性统计
        if stats['by_cable_route']:
            report_lines.append("按光缆路由属性统计：")
            for route_name, route_stats in sorted(stats['by_cable_route'].items()):
                report_lines.append(f"  {route_name}: {route_stats['count']}次, "
                                  f"总历时{route_stats['total_duration']:.2f}小时, "
                                  f"平均{route_stats['avg_duration']:.2f}小时")
            report_lines.append("")
        
        # 按涉及业务统计
        if stats['by_service']:
            report_lines.append("按涉及业务统计：")
            for service_name, service_stats in sorted(stats['by_service'].items()):
                report_lines.append(f"  {service_name}: {service_stats['count']}次, "
                                  f"总历时{service_stats['total_duration']:.2f}小时")
            report_lines.append("")
        
        return "\n".join(report_lines)
