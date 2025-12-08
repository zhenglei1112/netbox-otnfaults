"""
NetBox自定义脚本：生成OTN故障测试数据

功能：
1. 从NetBox系统读取现有数据（用户、站点、省份、业务、服务提供商）
2. 生成1000余条故障记录（可配置数量）
3. 每条故障关联1-5条业务影响记录
4. 所有时间字段按照业务逻辑顺序生成
5. GPS坐标在中国境内随机生成，重点省份权重更高

使用方式：
在NetBox的"自定义脚本"界面中：
1. 选择脚本模块：netbox_otnfaults.scripts.generate_fault_data
2. 选择脚本类：GenerateFaultData
3. 配置参数（可选）
4. 运行脚本
"""

import random
import datetime
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from dcim.models import Site
from dcim.models import Region
from tenancy.models import Tenant
from netbox_contract.models import ServiceProvider
from extras.scripts import Script, ChoiceVar, IntegerVar, BooleanVar
from netbox_otnfaults.models import OtnFault, OtnFaultImpact


class GenerateFaultData(Script):
    """
    生成OTN故障测试数据的自定义脚本
    """
    
    class Meta:
        name = "生成OTN故障测试数据"
        description = "生成1000余条OTN故障记录及关联的业务影响记录"
        commit_default = False
    
    # 脚本参数
    fault_count = IntegerVar(
        label="故障数量",
        description="要生成的故障记录数量（默认：1000）",
        default=1000,
        min_value=1,
        max_value=5000
    )
    
    start_date = ChoiceVar(
        label="起始日期",
        description="故障中断时间的起始日期",
        choices=[
            ('2025-10-01', '2025年10月1日'),
            ('2025-10-15', '2025年10月15日'),
            ('2025-11-01', '2025年11月1日'),
        ],
        default='2025-10-01'
    )
    
    end_date = ChoiceVar(
        label="结束日期",
        description="故障中断时间的结束日期",
        choices=[
            ('2025-11-15', '2025年11月15日'),
            ('2025-11-30', '2025年11月30日'),
            ('2025-12-03', '2025年12月3日'),
        ],
        default='2025-12-03'
    )
    
    clear_existing = BooleanVar(
        label="清除现有数据",
        description="是否清除现有的故障和业务影响记录（谨慎使用）",
        default=False
    )
    
    def __init__(self):
        super().__init__()
        self.users = []
        self.sites = []
        self.provinces = []
        self.tenants = []
        self.service_providers = []
        
        # 重点省份（权重更高）
        self.key_provinces = ['广东', '河北', '湖南', '广西']
        
        # 故障分类选项
        self.fault_categories = [
            'power',    # 电力故障
            'fiber',    # 光缆故障
            'pigtail',  # 尾纤故障
            'device',   # 设备故障
            'other',    # 其他故障
        ]
        
        # 故障原因选项
        self.interruption_reasons = [
            'road_construction',      # 道路施工
            'sabotage',               # 人为破坏
            'line_rectification',     # 线路整改
            'misoperation',           # 误操作
            'power_supply',           # 供电故障
            'municipal_construction', # 市政施工
            'rodent_damage',          # 鼠害
            'natural_disaster',       # 自然灾害
        ]
        
        # 紧急程度选项
        self.urgency_levels = ['high', 'medium', 'low']
        
        # 第一报障来源选项
        self.report_sources = [
            'national_backbone',  # 国干网网管
            'future_network',     # 未来网络网管
            'customer_support',   # 客户报障
            'other',              # 其他
        ]
        
        # 维护方式选项
        self.maintenance_modes = [
            'outsourced',      # 代维
            'coordinated',     # 协调
            'self_maintained', # 自维
        ]
        
        # 资源类型选项
        self.resource_types = [
            'self_built',   # 自建光缆
            'coordinated',  # 协调资源
            'leased',       # 租赁纤芯
        ]
        
        # 恢复方式选项
        self.recovery_modes = [
            'fusion_splicing',          # 熔接恢复
            'tail_fiber_replacement',   # 更换尾纤恢复
            'processing',               # 处理恢复
            'fiber_adjustment',         # 调纤恢复
            'automatic',                # 自动恢复
            'unknown',                  # 无法查明
            'not_provided',             # 未提供
        ]
        
        # 中国GPS坐标范围
        self.china_bounds = {
            'min_lon': Decimal('73.0'),   # 最西经度
            'max_lon': Decimal('135.0'),  # 最东经度
            'min_lat': Decimal('18.0'),   # 最南纬度
            'max_lat': Decimal('53.0'),   # 最北纬度
        }
        
        # 重点省份的GPS中心点（用于生成附近坐标）
        self.province_centers = {
            '广东': {'lon': Decimal('113.27'), 'lat': Decimal('23.13')},
            '河北': {'lon': Decimal('114.48'), 'lat': Decimal('38.03')},
            '湖南': {'lon': Decimal('112.98'), 'lat': Decimal('28.20')},
            '广西': {'lon': Decimal('108.37'), 'lat': Decimal('22.82')},
        }
    
    def load_system_data(self):
        """从NetBox系统读取现有数据"""
        self.log_info("正在读取系统数据...")
        
        # 读取用户
        User = get_user_model()
        self.users = list(User.objects.all())
        if not self.users:
            self.log_failure("系统中没有用户数据，请先创建用户")
            return False
        
        # 读取站点
        self.sites = list(Site.objects.all())
        if not self.sites:
            self.log_warning("系统中没有站点数据，故障的故障位置将为空")
        
        # 读取省份（顶级区域）
        self.provinces = list(Region.objects.filter(parent__isnull=True))
        if not self.provinces:
            self.log_warning("系统中没有省份数据，故障的省份字段将为空")
        
        # 读取业务（租户）
        self.tenants = list(Tenant.objects.all())
        if not self.tenants:
            self.log_failure("系统中没有业务数据，无法生成业务影响记录")
            return False
        
        # 读取服务提供商
        self.service_providers = list(ServiceProvider.objects.all())
        if not self.service_providers:
            self.log_warning("系统中没有服务提供商数据，处理单位字段将为空")
        
        self.log_success(f"系统数据读取完成：用户({len(self.users)})、站点({len(self.sites)})、"
                        f"省份({len(self.provinces)})、业务({len(self.tenants)})、"
                        f"服务提供商({len(self.service_providers)})")
        return True
    
    def generate_random_time(self, start_date, end_date):
        """在指定日期范围内生成随机时间"""
        start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # 计算时间差（天数）
        delta_days = (end_dt - start_dt).days
        if delta_days <= 0:
            random_days = 0
        else:
            random_days = random.randint(0, delta_days)
        
        # 生成随机日期
        random_date = start_dt + datetime.timedelta(days=random_days)
        
        # 生成随机时间（小时、分钟、秒）
        random_hour = random.randint(0, 23)
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)
        
        return random_date.replace(hour=random_hour, minute=random_minute, second=random_second)
    
    def generate_gps_coordinates(self, province_name=None):
        """生成随机GPS坐标"""
        if province_name and province_name in self.province_centers:
            # 如果是重点省份，在中心点附近生成
            center = self.province_centers[province_name]
            lon = center['lon'] + Decimal(random.uniform(-2.0, 2.0))  # ±2度范围
            lat = center['lat'] + Decimal(random.uniform(-2.0, 2.0))  # ±2度范围
        else:
            # 普通随机生成
            lon = Decimal(str(random.uniform(
                float(self.china_bounds['min_lon']),
                float(self.china_bounds['max_lon'])
            )))
            lat = Decimal(str(random.uniform(
                float(self.china_bounds['min_lat']),
                float(self.china_bounds['max_lat'])
            )))
        
        # 确保在边界内
        lon = max(self.china_bounds['min_lon'], min(self.china_bounds['max_lon'], lon))
        lat = max(self.china_bounds['min_lat'], min(self.china_bounds['max_lat'], lat))
        
        return lon, lat
    
    def select_province(self):
        """选择省份，重点省份权重更高"""
        if not self.provinces:
            return None
        
        # 计算权重：重点省份各20%，其他省份共享20%
        if random.random() < 0.8:  # 80%概率选择重点省份
            # 从重点省份名称中随机选择一个
            province_name = random.choice(self.key_provinces)
            # 查找对应的省份对象
            for province in self.provinces:
                if province.name == province_name:
                    return province
            # 如果找不到，随机选择一个
            return random.choice(self.provinces)
        else:  # 20%概率选择其他省份
            other_provinces = [p for p in self.provinces if p.name not in self.key_provinces]
            if other_provinces:
                return random.choice(other_provinces)
            else:
                return random.choice(self.provinces)
    
    def generate_fault_details(self):
        """生成故障详细情况文本"""
        templates = [
            "光缆在{}附近被施工挖断，导致{}方向业务故障。",
            "设备{}端口故障，影响{}业务传输。",
            "{}地区电力故障，导致设备断电，业务故障。",
            "光缆在{}处被车辆挂断，需要紧急抢修。",
            "{}设备软件故障，需要重启恢复。",
            "尾纤在{}机房被误拔，导致业务故障。",
            "{}地区自然灾害导致光缆故障。",
        ]
        
        locations = ["高速公路旁", "市政施工区域", "农田", "山区", "城区", "工业园区"]
        directions = ["北京至上海", "广州至深圳", "武汉至长沙", "成都至重庆", "东部至西部"]
        
        template = random.choice(templates)
        return template.format(random.choice(locations), random.choice(directions))
    
    def generate_time_sequence(self, fault_occurrence_time):
        """根据故障中断时间生成时间序列"""
        # 故障历时：1分钟到50小时之间随机
        duration_minutes = random.randint(1, 50 * 60)  # 转换为分钟
        
        # 故障恢复时间 = 故障中断时间 + 故障历时
        fault_recovery_time = fault_occurrence_time + datetime.timedelta(minutes=duration_minutes)
        
        # 处理派发时间：在故障中断时间后的0-30分钟内随机
        dispatch_delay = random.randint(0, 30)
        dispatch_time = fault_occurrence_time + datetime.timedelta(minutes=dispatch_delay)
        
        # 维修出发时间：在处理派发时间后的5-60分钟内随机
        departure_delay = random.randint(5, 60)
        departure_time = dispatch_time + datetime.timedelta(minutes=departure_delay)
        
        # 到达现场时间：在维修出发时间后的30-180分钟内随机（考虑路程）
        arrival_delay = random.randint(30, 180)
        arrival_time = departure_time + datetime.timedelta(minutes=arrival_delay)
        
        # 故障修复时间：在到达现场时间后的10-300分钟内随机
        repair_delay = random.randint(10, 300)
        repair_time = arrival_time + datetime.timedelta(minutes=repair_delay)
        
        # 确保修复时间不晚于恢复时间（如果晚于，则调整）
        if repair_time > fault_recovery_time:
            repair_time = fault_recovery_time
        
        return {
            'fault_recovery_time': fault_recovery_time,
            'dispatch_time': dispatch_time,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'repair_time': repair_time,
        }
    
    def create_fault_record(self, index, start_date, end_date):
        """创建一条故障记录"""
        # 生成故障中断时间
        fault_occurrence_time = self.generate_random_time(
            start_date,
            end_date
        )
        
        # 生成时间序列
        time_sequence = self.generate_time_sequence(fault_occurrence_time)
        
        # 选择省份并生成GPS坐标
        province = self.select_province()
        province_name = province.name if province else None
        longitude, latitude = self.generate_gps_coordinates(province_name)
        
        # 生成唯一的故障编号
        # 使用UUID确保唯一性，避免与现有数据冲突
        import uuid
        fault_number = f"FTEST{uuid.uuid4().hex[:12].upper()}"
        
        # 随机选择故障位置（站点） - 每个故障关联1-3个站点
        selected_sites = []
        if self.sites:
            # 随机选择1-3个站点
            num_sites = random.randint(1, min(3, len(self.sites)))
            selected_sites = random.sample(self.sites, num_sites)
        
        # 创建故障记录
        fault = OtnFault(
            # 故障编号（必须唯一）
            fault_number=fault_number,
            
            # 基础信息
            duty_officer=random.choice(self.users),
            fault_occurrence_time=fault_occurrence_time,
            
            # 分类信息
            fault_category=random.choice(self.fault_categories),
            interruption_reason=random.choice(self.interruption_reasons),
            fault_details=self.generate_fault_details(),
            
            # 位置信息
            interruption_longitude=longitude,
            interruption_latitude=latitude,
            province=province,
            
            # 管理信息
            urgency=random.choice(self.urgency_levels),
            first_report_source=random.choice(self.report_sources),
            planned=random.choice([True, False]),
            line_manager=random.choice(self.users) if self.users else None,
            maintenance_mode=random.choice(self.maintenance_modes),
            handling_unit=random.choice(self.service_providers) if self.service_providers else None,
            
            # 时间序列
            fault_recovery_time=time_sequence['fault_recovery_time'],
            dispatch_time=time_sequence['dispatch_time'],
            departure_time=time_sequence['departure_time'],
            arrival_time=time_sequence['arrival_time'],
            repair_time=time_sequence['repair_time'],
            
            # 修复信息
            timeout=random.choice([True, False]),
            timeout_reason="交通拥堵导致延误" if random.random() > 0.7 else "",
            resource_type=random.choice(self.resource_types),
            cable_route=random.choice(['highway', 'non_highway']),
            handler=f"维修人员{random.randint(1, 100)}",
            recovery_mode=random.choice(self.recovery_modes),
            
            # 其他
            comments=f"测试数据 #{index+1}，生成时间：{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return fault, selected_sites
    
    def create_impact_records(self, fault, fault_index):
        """为故障创建业务影响记录"""
        impacts = []
        
        # 每条故障关联1-5条业务影响
        impact_count = random.randint(1, 5)
        
        for i in range(impact_count):
            # 业务故障时间略晚于故障中断时间（0-5分钟）
            service_interruption_delay = random.randint(0, 5)
            service_interruption_time = fault.fault_occurrence_time + datetime.timedelta(
                minutes=service_interruption_delay
            )
            
            # 业务恢复时间略早于故障恢复时间（0-10分钟）
            service_recovery_advance = random.randint(0, 10)
            service_recovery_time = fault.fault_recovery_time - datetime.timedelta(
                minutes=service_recovery_advance
            )
            
            impact = OtnFaultImpact(
                otn_fault=fault,
                impacted_service=random.choice(self.tenants),
                service_interruption_time=service_interruption_time,
                service_recovery_time=service_recovery_time,
                comments=f"故障 #{fault_index+1} 影响的业务 #{i+1}"
            )
            
            impacts.append(impact)
        
        return impacts
    
    def set_fault_sites_relationships(self, fault_sites_mapping):
        """为故障记录设置站点关系"""
        if not fault_sites_mapping:
            return
        
        self.log_info("正在设置故障位置关系...")
        
        for fault_number, sites in fault_sites_mapping.items():
            try:
                # 根据故障编号查找故障记录
                fault = OtnFault.objects.get(fault_number=fault_number)
                # 设置多对多关系
                fault.interruption_location.set(sites)
                fault.save()
            except OtnFault.DoesNotExist:
                self.log_warning(f"未找到故障记录：{fault_number}")
            except Exception as e:
                self.log_warning(f"设置故障 {fault_number} 的站点关系时出错：{str(e)}")
        
        self.log_success(f"已为 {len(fault_sites_mapping)} 条故障记录设置故障位置关系")
    
    def clear_existing_data(self):
        """清除现有的故障和业务影响记录"""
        self.log_info("正在清除现有数据...")
        
        # 删除业务影响记录
        impact_count = OtnFaultImpact.objects.count()
        OtnFaultImpact.objects.all().delete()
        self.log_success(f"已删除 {impact_count} 条业务影响记录")
        
        # 删除故障记录
        fault_count = OtnFault.objects.count()
        OtnFault.objects.all().delete()
        self.log_success(f"已删除 {fault_count} 条故障记录")
    
    def run(self, data, commit):
        """脚本主入口"""
        # 读取脚本参数
        fault_count = data['fault_count']
        clear_existing = data['clear_existing']
        
        # 清除现有数据（如果用户选择）
        if clear_existing:
            self.clear_existing_data()
        
        # 读取系统数据
        if not self.load_system_data():
            return "系统数据读取失败，请检查NetBox数据库"
        
        # 检查必要数据
        if not self.users:
            return "错误：系统中没有用户数据，请先创建用户"
        if not self.tenants:
            return "错误：系统中没有业务数据，请先创建业务（租户）"
        
        # 生成故障记录
        self.log_info(f"开始生成 {fault_count} 条故障记录...")
        faults = []
        fault_sites_mapping = {}  # 存储故障编号和站点的映射关系
        impacts = []
        
        for i in range(fault_count):
            # 创建故障记录和站点选择
            fault, selected_sites = self.create_fault_record(i, data['start_date'], data['end_date'])
            faults.append(fault)
            
            # 存储故障编号和站点的映射关系
            if selected_sites:
                fault_sites_mapping[fault.fault_number] = selected_sites
            
            # 创建业务影响记录
            fault_impacts = self.create_impact_records(fault, i)
            impacts.extend(fault_impacts)
            
            # 进度反馈
            if (i + 1) % 100 == 0:
                self.log_info(f"已生成 {i + 1} 条故障记录...")
        
        # 批量保存故障记录
        self.log_info("正在保存故障记录到数据库...")
        if commit:
            OtnFault.objects.bulk_create(faults)
            self.log_success(f"成功创建 {len(faults)} 条故障记录")
            
            # 为故障记录设置站点关系
            if fault_sites_mapping:
                self.set_fault_sites_relationships(fault_sites_mapping)
            else:
                self.log_warning("系统中没有站点数据，故障的故障位置字段将为空")
        else:
            self.log_info(f"模拟模式：将创建 {len(faults)} 条故障记录")
            if fault_sites_mapping:
                self.log_info(f"模拟模式：将为 {len(fault_sites_mapping)} 条故障记录设置故障位置关系")
            else:
                self.log_warning("模拟模式：系统中没有站点数据，故障的故障位置字段将为空")
        
        # 批量保存业务影响记录
        self.log_info("正在保存业务影响记录到数据库...")
        if commit:
            OtnFaultImpact.objects.bulk_create(impacts)
            self.log_success(f"成功创建 {len(impacts)} 条业务影响记录")
        else:
            self.log_info(f"模拟模式：将创建 {len(impacts)} 条业务影响记录")
        
        # 统计信息
        total_impacts = len(impacts)
        avg_impacts_per_fault = total_impacts / len(faults) if faults else 0
        total_faults_with_sites = len(fault_sites_mapping)
        
        result_message = (
            f"数据生成完成！\n"
            f"• 故障记录：{len(faults)} 条\n"
            f"• 业务影响记录：{total_impacts} 条\n"
            f"• 平均每条故障影响业务：{avg_impacts_per_fault:.1f} 条\n"
            f"• 设置故障位置的故障：{total_faults_with_sites} 条\n"
            f"• 时间范围：{data['start_date']} 至 {data['end_date']}\n"
        )
        
        if not commit:
            result_message += "\n注意：当前为模拟模式，数据未实际保存到数据库。\n"
            result_message += "如需实际保存，请勾选'提交更改'选项。"
        
        return result_message
